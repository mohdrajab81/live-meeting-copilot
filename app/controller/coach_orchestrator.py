"""
CoachOrchestrator — owns all coach scheduling state and logic.

State: coach_pending, coach_hints, coach_last_run_ts, coach_group_seq,
       coach_last_sent_final_idx, coach_queued_trigger.

Shares the AppController RLock for all state mutations.
"""

import asyncio
import threading
import time
from typing import Any, Awaitable, Callable

from app.config import RuntimeConfig
from app.services.coach import CoachService


BroadcastCallback = Callable[[dict[str, Any]], Awaitable[None]]
BroadcastLogCallback = Callable[[str, str], Awaitable[None]]
BroadcastFromThreadCallback = Callable[[dict[str, Any]], None]
AppendLogCallback = Callable[[str, str], dict[str, Any]]


class CoachOrchestrator:
    def __init__(
        self,
        lock: threading.RLock,
        coach: CoachService,
        broadcast: BroadcastCallback,
        broadcast_log: BroadcastLogCallback,
        broadcast_from_thread: BroadcastFromThreadCallback,
        append_log: AppendLogCallback,
        get_finals: Callable[[], list[dict[str, Any]]],
        get_config: Callable[[], RuntimeConfig],
        preview_text: Callable[[str], str],
    ) -> None:
        self._lock = lock
        self._coach = coach
        self._broadcast = broadcast
        self._broadcast_log = broadcast_log
        self._broadcast_from_thread = broadcast_from_thread
        self._append_log = append_log
        self._get_finals = get_finals
        self._get_config = get_config
        self._preview_text = preview_text

        self.loop: asyncio.AbstractEventLoop | None = None

        # Coach state (protected by shared lock)
        self.coach_pending = False
        self.coach_hints: list[dict[str, Any]] = []
        self.coach_last_run_ts = 0.0
        self.coach_group_seq = 0
        self.coach_last_sent_final_idx = 0
        self.coach_queued_trigger: dict[str, Any] | None = None

    # ── State helpers called while holding the shared lock ────────────────────

    def reset_sent_index_unlocked(self, new_index: int) -> None:
        self.coach_last_sent_final_idx = new_index

    def clear_queued_trigger_unlocked(self) -> None:
        self.coach_queued_trigger = None

    def reset_runtime_unlocked(self, *, keep_history: bool) -> None:
        if not keep_history:
            self.coach_hints = []
        self.coach_pending = False
        self.coach_last_run_ts = 0.0
        finals = self._get_finals()
        self.coach_last_sent_final_idx = len(finals)
        self.coach_queued_trigger = None

    def _append_hint_unlocked(self, hint: dict[str, Any]) -> None:
        self.coach_hints.append(hint)
        if len(self.coach_hints) > 120:
            self.coach_hints = self.coach_hints[-120:]

    def _next_group_id_unlocked(self) -> str:
        self.coach_group_seq += 1
        return f"coach-{int(time.time())}-{self.coach_group_seq}"

    # ── Trigger logic ─────────────────────────────────────────────────────────

    def should_trigger_unlocked(
        self,
        item: dict[str, Any],
        config: RuntimeConfig,
        *,
        ignore_busy: bool = False,
        ignore_cooldown: bool = False,
    ) -> bool:
        if not config.coach_enabled:
            return False
        if not self._coach.is_configured:
            return False
        if (not ignore_busy) and self.coach_pending:
            return False
        if not ignore_cooldown:
            now = time.time()
            if now - self.coach_last_run_ts < float(config.coach_cooldown_sec):
                return False
        trigger = config.coach_trigger_speaker
        speaker = str(item.get("speaker", "default") or "default")
        if trigger == "any":
            return True
        return trigger == speaker

    @staticmethod
    def _has_text(item: dict[str, Any]) -> bool:
        text = (
            str(item.get("en", "") or "").strip()
            or str(item.get("ar", "") or "").strip()
        )
        return bool(text)

    def _build_prompt_unlocked(
        self,
        trigger_item: dict[str, Any],
        delta_turns: list[dict[str, Any]],
        config: RuntimeConfig,
        *,
        session_start: bool,
    ) -> str:
        delta_lines: list[str] = []
        for turn in delta_turns:
            label = str(turn.get("speaker_label", "Speaker") or "Speaker")
            en = str(turn.get("en", "") or "").strip()
            ar = str(turn.get("ar", "") or "").strip()
            text = en or ar
            if not text:
                continue
            ts = time.strftime("%H:%M:%S", time.localtime(float(turn.get("ts") or time.time())))
            delta_lines.append(f"[{ts}] {label}: {text}")

        trigger_label = str(trigger_item.get("speaker_label", "Speaker") or "Speaker")
        trigger_en = (
            str(trigger_item.get("en", "") or "").strip()
            or str(trigger_item.get("ar", "") or "").strip()
        )
        instruction = str(config.coach_instruction or "").strip()
        if not instruction:
            instruction = (
                "Give a short suggested reply for me, tailored to my profile. "
                "Use concise bullets and keep claims truthful to known background."
            )
        if session_start:
            return "\n".join(
                [
                    "You are my live meeting copilot.",
                    "Use my stored profile knowledge from the connected agent tools.",
                    instruction,
                    "",
                    "Latest remote-speaker utterance:",
                    f"{trigger_label}: {trigger_en}",
                    "",
                    "Session transcript update:",
                    "This is the full transcript from session start.",
                    "\n".join(delta_lines) if delta_lines else "(no new turns)",
                    "",
                    "Return format:",
                    "1) Suggested reply (short)",
                    "2) Exactly 2 bullet proof points from my background",
                    "3) One follow-up question I can ask (optional)",
                ]
            )
        return "\n".join(
            [
                "Latest remote-speaker utterance:",
                f"{trigger_label}: {trigger_en}",
                "",
                "Session transcript update:",
                "This is only the new transcript delta since last update.",
                "\n".join(delta_lines) if delta_lines else "(no new turns)",
            ]
        )

    def prepare_call_unlocked(
        self,
        trigger_item: dict[str, Any],
        config: RuntimeConfig,
        *,
        ignore_cooldown: bool = False,
    ) -> tuple[str, str, float, int] | None:
        if not self._has_text(trigger_item):
            return None
        if not self.should_trigger_unlocked(
            trigger_item, config, ignore_busy=False, ignore_cooldown=ignore_cooldown
        ):
            return None

        finals = self._get_finals()
        end_idx = len(finals)
        start_idx = max(0, int(self.coach_last_sent_final_idx))
        if start_idx > end_idx:
            start_idx = end_idx
        delta_turns = finals[start_idx:end_idx]
        if not delta_turns:
            return None

        max_turns = max(2, int(config.coach_max_turns))
        if len(delta_turns) > max_turns:
            delta_turns = delta_turns[-max_turns:]

        session_start = start_idx == 0
        coach_prompt = self._build_prompt_unlocked(
            trigger_item, delta_turns, config, session_start=session_start
        )
        self.coach_pending = True
        self.coach_last_run_ts = time.time()
        coach_group_id = self._next_group_id_unlocked()
        return coach_prompt, coach_group_id, self.coach_last_run_ts, end_idx

    # ── Async runner ──────────────────────────────────────────────────────────

    async def run_coach(
        self,
        prompt: str,
        trigger_item: dict[str, Any],
        group_id: str,
        trigger_ts: float,
        inflight_end_idx: int,
    ) -> None:
        config = self._get_config()
        try:
            run_start = time.time()
            send_ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(run_start))
            chain = self._coach.get_chain_state()
            await self._broadcast_log(
                "info",
                (
                    "Coach deep send: "
                    f"group={group_id}, send_ts={send_ts}, "
                    f"trigger={trigger_item.get('speaker_label', 'Speaker')}, "
                    f"trigger_text={self._preview_text(str(trigger_item.get('en', '') or '').strip())}, "
                    f"req_conversation_id={chain.get('conversation_id') or '-'}, "
                    f"req_previous_response_id={chain.get('previous_response_id') or '-'}"
                ),
            )
            result = await asyncio.to_thread(self._coach.ask, prompt)
            hint = {
                "type": "coach",
                "group_id": group_id,
                "ts": time.time(),
                "speaker": str(trigger_item.get("speaker", "default") or "default"),
                "speaker_label": str(
                    trigger_item.get("speaker_label", "Speaker") or "Speaker"
                ),
                "trigger_en": str(trigger_item.get("en", "") or ""),
                "suggestion": result.text,
            }
            with self._lock:
                self._append_hint_unlocked(hint)
            await self._broadcast(hint)
            recv_ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
            await self._broadcast_log(
                "info",
                (
                    "Coach deep reply: "
                    f"group={group_id}, recv_ts={recv_ts}, "
                    f"response_id={result.response_id or '-'}, "
                    f"conversation_id={result.conversation_id or '-'}, "
                    f"reply_preview={self._preview_text(result.text)}"
                ),
            )
            queue_ms = int((run_start - trigger_ts) * 1000)
            end_to_end_ms = int((time.time() - trigger_ts) * 1000)
            await self._broadcast_log(
                "info",
                (
                    "Coach deep hint trace: "
                    f"group={group_id}, queue_ms={queue_ms}, "
                    f"create_ms={result.create_ms}, approve_ms={result.approve_ms}, "
                    f"approval_rounds={result.approval_rounds}, approval_count={result.approval_count}, "
                    f"total_ms={result.total_ms}, end_to_end_ms={end_to_end_ms}"
                ),
            )
            with self._lock:
                if inflight_end_idx > self.coach_last_sent_final_idx:
                    self.coach_last_sent_final_idx = inflight_end_idx
        except Exception as ex:
            await self._broadcast_log("error", f"Coach request failed: {ex}")
        finally:
            queued: dict[str, Any] | None = None
            next_call: tuple[str, str, float, int] | None = None
            with self._lock:
                self.coach_pending = False
                queued = self.coach_queued_trigger
                self.coach_queued_trigger = None
                if queued:
                    next_call = self.prepare_call_unlocked(
                        queued, config, ignore_cooldown=True
                    )
            if queued and not next_call:
                await self._broadcast_log(
                    "debug",
                    "Queued coach trigger dropped (not eligible by current settings).",
                )
            if next_call:
                next_prompt, next_group_id, next_trigger_ts, next_end_idx = next_call
                await self._broadcast_log(
                    "info",
                    (
                        "Coach queued trigger resumed: "
                        f"group={next_group_id}, trigger={queued.get('speaker_label', 'Speaker')}, "  # type: ignore[union-attr]
                        f"trigger_text={str(queued.get('en', '') or '').strip()}"  # type: ignore[union-attr]
                    ),
                )
                await self.run_coach(
                    next_prompt,
                    queued or {},
                    next_group_id,
                    next_trigger_ts,
                    next_end_idx,
                )

    def schedule_from_thread(
        self,
        item: dict[str, Any],
        coach_call: tuple[str, str, float, int] | None,
        queued_while_busy: bool,
    ) -> None:
        if queued_while_busy:
            self._broadcast_from_thread(
                self._append_log(
                    "debug",
                    (
                        "Coach trigger queued while busy: "
                        f"trigger={item['speaker_label']}, text={item['en']}"
                    ),
                )
            )
        if not coach_call:
            return
        coach_prompt, coach_group_id, coach_trigger_ts, inflight_end_idx = coach_call
        loop = self.loop
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self.run_coach(
                    coach_prompt,
                    item,
                    coach_group_id,
                    coach_trigger_ts,
                    inflight_end_idx,
                ),
                loop,
            )

    # ── Public actions ────────────────────────────────────────────────────────

    def clear(self, coach_service: CoachService) -> None:
        with self._lock:
            self.reset_runtime_unlocked(keep_history=False)
        coach_service.clear_conversation()

    async def request_manual(
        self, prompt: str, speaker_label: str = "Manual"
    ) -> dict[str, Any]:
        manual_prompt = "\n".join(
            ["Manual user message (same conversation):", str(prompt or "").strip()]
        )
        send_ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        chain = self._coach.get_chain_state()
        await self._broadcast_log(
            "info",
            (
                "Coach manual send: "
                f"send_ts={send_ts}, speaker_label={speaker_label}, "
                f"req_conversation_id={chain.get('conversation_id') or '-'}, "
                f"req_previous_response_id={chain.get('previous_response_id') or '-'}, "
                f"prompt={self._preview_text(prompt)}"
            ),
        )
        result = await asyncio.to_thread(self._coach.ask, manual_prompt)
        hint = {
            "type": "coach",
            "group_id": "",
            "ts": time.time(),
            "speaker": "manual",
            "speaker_label": speaker_label or "Manual",
            "trigger_en": "",
            "suggestion": result.text,
        }
        with self._lock:
            self._append_hint_unlocked(hint)
        await self._broadcast(hint)
        recv_ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        await self._broadcast_log(
            "info",
            (
                "Coach manual reply: "
                f"recv_ts={recv_ts}, total_ms={result.total_ms}, "
                f"create_ms={result.create_ms}, approve_ms={result.approve_ms}, "
                f"approval_rounds={result.approval_rounds}, approval_count={result.approval_count}, "
                f"response_id={result.response_id or '-'}, conversation_id={result.conversation_id or '-'}, "
                f"reply_preview={self._preview_text(result.text)}"
            ),
        )
        return hint

    # ── Snapshot ──────────────────────────────────────────────────────────────

    def snapshot_unlocked(self) -> dict[str, Any]:
        return {
            "configured": self._coach.is_configured,
            "pending": self.coach_pending,
            "queued": self.coach_queued_trigger is not None,
            "last_sent_final_idx": self.coach_last_sent_final_idx,
            "hints": list(self.coach_hints),
        }
