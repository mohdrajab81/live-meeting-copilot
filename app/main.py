import asyncio
import json
from contextlib import asynccontextmanager
from collections import deque
from pathlib import Path
import os
import threading
import time
from typing import Any

from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from app.api.routes import router as api_router
from app.api.websocket import websocket_endpoint
from app.config import RuntimeConfig, Settings
from app.services.coach import CoachService
from app.services.speech import SpeechService
from app.services.topic_tracker import TopicTrackerService
from app.services.translation_pipeline import TranslationPipeline

load_dotenv()


class AppController:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.settings_path = Path("web_translator_settings.json")
        self.lock = threading.RLock()
        self.loop: asyncio.AbstractEventLoop | None = None
        self.connections: set[WebSocket] = set()

        self.config = RuntimeConfig()
        self.status = "idle"
        self.running = False
        self.en_live = ""
        self.ar_live = ""
        self.live_partials: dict[str, dict[str, Any]] = {}
        self.finals: list[dict[str, Any]] = []
        self.logs: list[dict[str, Any]] = []
        self.session_started_ts = time.time()
        self.record_started_ts: float | None = None
        self.record_accumulated_ms = 0
        self.coach = CoachService.from_environment()
        self.coach_hints: list[dict[str, Any]] = []
        self.coach_pending = False
        self.coach_last_run_ts = 0.0
        self.coach_group_seq = 0
        self.coach_last_sent_final_idx = 0
        self.coach_queued_trigger: dict[str, Any] | None = None
        self.topic_tracker = TopicTrackerService.from_environment()
        self.topics_enabled = False
        self.topics_allow_new = True
        self.topics_interval_sec = 60
        self.topics_window_sec = 90
        self.topics_pending = False
        self.topics_last_run_ts = 0.0
        self.topics_last_error = ""
        self.topics_agenda: list[str] = []
        self.topics_items: list[dict[str, Any]] = []
        self._speaker_last_activity_ts: dict[str, float] = {
            "local": 0.0,
            "remote": 0.0,
            "default": 0.0,
        }
        self._bleed_suppress_window_sec = 1.6
        self.last_speech_activity_ts = time.time()
        self.watchdog_task: asyncio.Task[None] | None = None
        self.translation = TranslationPipeline(
            settings=settings,
            lock=self.lock,
            apply_translation_result=self._apply_translation_result,
            log=self.broadcast_log,
        )
        self.translation_latency_ms: deque[int] = deque(maxlen=240)
        self.translation_latest_ms: int | None = None
        self.translation_chars: int = 0
        self.translation_events: int = 0
        self.translation_cost_per_million_usd: float | None = self._load_translation_cost_rate()

        self.speech = SpeechService(
            settings=settings,
            on_event=self.handle_speech_event,
            get_runtime_config=self.get_runtime_config,
        )

    def _load_translation_cost_rate(self) -> float | None:
        raw = (os.getenv("TRANSLATION_COST_PER_MILLION_USD", "") or "").strip()
        if not raw:
            return None
        try:
            value = float(raw)
        except Exception:
            return None
        return value if value > 0 else None

    def _median_ms_unlocked(self) -> int | None:
        if not self.translation_latency_ms:
            return None
        values = sorted(self.translation_latency_ms)
        n = len(values)
        mid = n // 2
        if n % 2 == 1:
            return int(values[mid])
        return int((values[mid - 1] + values[mid]) / 2)

    def _build_telemetry_unlocked(self) -> dict[str, Any]:
        estimated_cost_usd: float | None = None
        if self.translation_cost_per_million_usd is not None:
            estimated_cost_usd = round(
                (self.translation_chars / 1_000_000.0) * self.translation_cost_per_million_usd,
                4,
            )
        return {
            "type": "telemetry",
            "ws_connections": len(self.connections),
            "recognition_status": self.status,
            "recognition_running": self.running,
            "translation_latest_ms": self.translation_latest_ms,
            "translation_p50_ms": self._median_ms_unlocked(),
            "translation_samples": len(self.translation_latency_ms),
            "translation_chars": self.translation_chars,
            "estimated_cost_usd": estimated_cost_usd,
        }

    def _record_translation_metrics_unlocked(self, req: dict[str, Any], now_ts: float) -> dict[str, Any]:
        trigger_ts = float(req.get("trigger_ts", 0.0) or 0.0)
        if trigger_ts > 0.0:
            total_ms = max(0, int((now_ts - trigger_ts) * 1000))
            self.translation_latest_ms = total_ms
            self.translation_latency_ms.append(total_ms)
        text = str(req.get("text", "") or "")
        self.translation_chars += len(text)
        self.translation_events += 1
        return self._build_telemetry_unlocked()

    def _record_total_ms_unlocked(self) -> int:
        total_ms = self.record_accumulated_ms
        if self.record_started_ts is not None:
            total_ms += int((time.time() - self.record_started_ts) * 1000)
        return int(total_ms)

    async def _apply_translation_result(self, req: dict[str, Any], ar_text: str) -> None:
        kind = str(req.get("kind", "partial") or "partial")
        speaker = str(req.get("speaker", "default") or "default")
        segment_id = str(req.get("segment_id", "") or "")
        revision = int(req.get("revision", 0) or 0)
        translated = (ar_text or "").strip()
        telemetry: dict[str, Any] | None = None

        if kind == "partial":
            with self.lock:
                if not self.translation.is_current_partial_unlocked(req, self.live_partials):
                    return
                now_ts = time.time()
                partial = self.live_partials[speaker]
                prev_ar_revision = int(partial.get("ar_revision", 0) or 0)
                if revision < prev_ar_revision:
                    return
                partial["ar"] = translated
                partial["ar_revision"] = revision
                partial["ts"] = now_ts
                out = {
                    "type": "partial",
                    "speaker": speaker,
                    "speaker_label": partial.get("speaker_label", "Speaker"),
                    "segment_id": segment_id,
                    "revision": int(partial.get("revision", revision) or revision),
                    "en": partial.get("en", ""),
                    "ar": translated,
                }
                if translated:
                    self.ar_live = translated
                telemetry = self._record_translation_metrics_unlocked(req, now_ts)
            await self.broadcast(out)
            await self._emit_trace_async(out, channel="translation_partial")
            if telemetry:
                await self.broadcast(telemetry)
            return

        with self.lock:
            now_ts = time.time()
            target_idx = -1
            for idx in range(len(self.finals) - 1, -1, -1):
                item = self.finals[idx]
                if str(item.get("segment_id", "")) != segment_id:
                    continue
                if int(item.get("revision", 0)) != revision:
                    continue
                target_idx = idx
                break
            if target_idx < 0:
                return
            if translated:
                self.finals[target_idx]["ar"] = translated
            updated = dict(self.finals[target_idx])
            telemetry = self._record_translation_metrics_unlocked(req, now_ts)
        payload = {"type": "final_patch", **updated}
        await self.broadcast(payload)
        await self._emit_trace_async(payload, channel="translation_final_patch")
        if telemetry:
            await self.broadcast(telemetry)

    async def watchdog_loop(self) -> None:
        while True:
            await asyncio.sleep(1.0)
            reason: str | None = None
            topic_call: dict[str, Any] | None = None
            with self.lock:
                if not self.running:
                    continue
                now = time.time()
                silence_limit = int(self.config.auto_stop_silence_sec)
                max_session = int(self.config.max_session_sec)
                idle_for = now - self.last_speech_activity_ts
                run_for = now - self.session_started_ts
                if (
                    self.topics_enabled
                    and self.topics_agenda
                    and not self.topics_pending
                    and self.topic_tracker.is_configured
                    and (now - self.topics_last_run_ts) >= float(self.topics_interval_sec)
                ):
                    topic_call = self._prepare_topic_call_unlocked(now)
                if silence_limit > 0 and idle_for >= silence_limit:
                    reason = (
                        f"Auto-stopping after {silence_limit}s of inactivity to control costs."
                    )
                elif max_session > 0 and run_for >= max_session:
                    reason = (
                        f"Auto-stopping after {max_session}s max session duration to control costs."
                    )
            if not reason:
                if topic_call:
                    await self._run_topic_update(topic_call)
                continue
            if self.stop():
                await self.broadcast_log("warning", reason)

    def get_runtime_config(self) -> RuntimeConfig:
        with self.lock:
            return RuntimeConfig.model_validate(self.config.model_dump())

    def get_config(self) -> dict[str, Any]:
        with self.lock:
            return self.config.model_dump()

    def set_config(self, config: RuntimeConfig) -> None:
        with self.lock:
            self.config = config

    def reset_config_to_defaults(self) -> dict[str, Any]:
        cfg = RuntimeConfig()
        with self.lock:
            self.config = cfg
        return cfg.model_dump()

    def save_config_to_disk(self) -> str:
        with self.lock:
            config = self.config.model_dump()
        self.settings_path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return self.settings_path.name

    def reload_config_from_disk(self) -> dict[str, Any]:
        if not self.settings_path.exists():
            raise FileNotFoundError(
                f"Settings file not found: {self.settings_path.name}. Save config first."
            )
        raw = json.loads(self.settings_path.read_text(encoding="utf-8"))
        cfg = RuntimeConfig.model_validate(raw)
        with self.lock:
            self.config = cfg
        return cfg.model_dump()

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "type": "snapshot",
                "status": self.status,
                "running": self.running,
                "session_started_ts": self.session_started_ts,
                "config": self.config.model_dump(),
                "en_live": self.en_live,
                "ar_live": self.ar_live,
                "live_partials": list(self.live_partials.values()),
                "finals": list(self.finals),
                "logs": list(self.logs),
                "recording": {
                    "started_ts": self.record_started_ts,
                    "accumulated_ms": self.record_accumulated_ms,
                    "total_ms": self._record_total_ms_unlocked(),
                },
                "coach": {
                    "configured": self.coach.is_configured,
                    "pending": self.coach_pending,
                    "queued": self.coach_queued_trigger is not None,
                    "last_sent_final_idx": self.coach_last_sent_final_idx,
                    "hints": list(self.coach_hints),
                },
                "topics": {
                    "configured": self.topic_tracker.is_configured,
                    "enabled": self.topics_enabled,
                    "allow_new_topics": self.topics_allow_new,
                    "interval_sec": self.topics_interval_sec,
                    "window_sec": self.topics_window_sec,
                    "pending": self.topics_pending,
                    "last_run_ts": self.topics_last_run_ts,
                    "last_error": self.topics_last_error,
                    "agenda": list(self.topics_agenda),
                    "items": list(self.topics_items),
                },
                "telemetry": self._build_telemetry_unlocked(),
            }

    def _append_log(self, level: str, message: str) -> dict[str, Any]:
        item = {
            "type": "log",
            "level": level,
            "message": message,
            "ts": time.time(),
        }
        with self.lock:
            self.logs.append(item)
            if len(self.logs) > 1000:
                self.logs = self.logs[-1000:]
        return item

    def _emit_trace_from_thread(self, payload: dict[str, Any], *, channel: str) -> None:
        with self.lock:
            if not bool(self.config.debug):
                return
            conn_count = len(self.connections)
        self._broadcast_from_thread(self._make_emit_trace_log(payload, channel, conn_count))

    async def _emit_trace_async(self, payload: dict[str, Any], *, channel: str) -> None:
        with self.lock:
            if not bool(self.config.debug):
                return
            conn_count = len(self.connections)
        await self.broadcast(self._make_emit_trace_log(payload, channel, conn_count))

    def _make_emit_trace_log(
        self,
        payload: dict[str, Any],
        channel: str,
        conn_count: int,
    ) -> dict[str, Any]:
        msg_type = str(payload.get("type", ""))
        speaker = str(payload.get("speaker", "") or "")
        segment_id = str(payload.get("segment_id", "") or "")
        revision = int(payload.get("revision", 0) or 0)
        en_len = len(str(payload.get("en", "") or ""))
        ar_len = len(str(payload.get("ar", "") or ""))
        return self._append_log(
            "debug",
            (
                "UI emit: "
                f"channel={channel}, type={msg_type}, speaker={speaker or '-'}, "
                f"segment_id={segment_id or '-'}, revision={revision}, "
                f"en_len={en_len}, ar_len={ar_len}, connections={conn_count}"
            ),
        )

    def _preview_text(self, value: str, max_len: int = 220) -> str:
        cleaned = " ".join(str(value or "").split())
        if len(cleaned) <= max_len:
            return cleaned
        return f"{cleaned[: max_len - 3]}..."

    def _topic_trace_summary(self, topic_call: dict[str, Any]) -> str:
        turns = list(topic_call.get("window_turns", []) or [])
        latest = turns[-1] if turns else {}
        latest_text = (
            str(latest.get("en", "") or "").strip()
            or str(latest.get("ar", "") or "").strip()
        )
        latest_speaker = str(latest.get("speaker", "-") or "-")
        return (
            f"agenda={len(list(topic_call.get('agenda', []) or []))}, "
            f"current_topics={len(list(topic_call.get('current_topics', []) or []))}, "
            f"window_turns={len(turns)}, "
            f"window_seconds={int(topic_call.get('window_seconds', 0) or 0)}, "
            f"allow_new={bool(topic_call.get('allow_new_topics', True))}, "
            f"latest_speaker={latest_speaker}, "
            f"latest_preview={self._preview_text(latest_text, max_len=120) if latest_text else '-'}"
        )

    async def broadcast(self, payload: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        data = json.dumps(payload, ensure_ascii=False)
        for ws in list(self.connections):
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.connections.discard(ws)

    async def broadcast_log(self, level: str, message: str) -> None:
        await self.broadcast(self._append_log(level, message))

    def _broadcast_from_thread(self, payload: dict[str, Any]) -> None:
        loop = self.loop
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast(payload), loop)

    def _should_trigger_coach_unlocked(
        self,
        item: dict[str, Any],
        *,
        ignore_busy: bool = False,
        ignore_cooldown: bool = False,
    ) -> bool:
        if not self.config.coach_enabled:
            return False
        if not self.coach.is_configured:
            return False
        if (not ignore_busy) and self.coach_pending:
            return False
        if not ignore_cooldown:
            now = time.time()
            if now - self.coach_last_run_ts < float(self.config.coach_cooldown_sec):
                return False

        trigger = self.config.coach_trigger_speaker
        speaker = str(item.get("speaker", "default") or "default")
        if trigger == "any":
            return True
        return trigger == speaker

    def _has_text_unlocked(self, item: dict[str, Any]) -> bool:
        text = (
            str(item.get("en", "") or "").strip()
            or str(item.get("ar", "") or "").strip()
        )
        return bool(text)

    def _build_coach_prompt_unlocked(
        self,
        trigger_item: dict[str, Any],
        delta_turns: list[dict[str, Any]],
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
        instruction = str(self.config.coach_instruction or "").strip()
        if not instruction:
            instruction = (
                "Give a short suggested reply for me, tailored to my profile. "
                "Use concise bullets and keep claims truthful to known background."
            )
        if session_start:
            return "\n".join(
                [
                    "You are my live interview copilot.",
                    "Use my stored profile knowledge from the connected agent tools.",
                    instruction,
                    "",
                    "Latest interviewer utterance:",
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
                "Latest interviewer utterance:",
                f"{trigger_label}: {trigger_en}",
                "",
                "Session transcript update:",
                "This is only the new transcript delta since last update.",
                "\n".join(delta_lines) if delta_lines else "(no new turns)",
            ]
        )

    def _next_coach_group_id_unlocked(self) -> str:
        self.coach_group_seq += 1
        return f"coach-{int(time.time())}-{self.coach_group_seq}"

    def _prepare_coach_call_unlocked(
        self,
        trigger_item: dict[str, Any],
        *,
        ignore_cooldown: bool = False,
    ) -> tuple[str, str, float, int] | None:
        if not self._has_text_unlocked(trigger_item):
            return None
        if not self._should_trigger_coach_unlocked(
            trigger_item,
            ignore_busy=False,
            ignore_cooldown=ignore_cooldown,
        ):
            return None

        end_idx = len(self.finals)
        start_idx = int(self.coach_last_sent_final_idx)
        if start_idx < 0:
            start_idx = 0
        if start_idx > end_idx:
            start_idx = end_idx
        delta_turns = self.finals[start_idx:end_idx]
        if not delta_turns:
            return None
        max_turns = max(2, int(self.config.coach_max_turns))
        if len(delta_turns) > max_turns:
            delta_turns = delta_turns[-max_turns:]

        session_start = start_idx == 0
        coach_prompt = self._build_coach_prompt_unlocked(
            trigger_item,
            delta_turns,
            session_start=session_start,
        )

        self.coach_pending = True
        self.coach_last_run_ts = time.time()
        coach_group_id = self._next_coach_group_id_unlocked()
        return coach_prompt, coach_group_id, self.coach_last_run_ts, end_idx

    async def _run_coach(
        self,
        prompt: str,
        trigger_item: dict[str, Any],
        group_id: str,
        trigger_ts: float,
        inflight_end_idx: int,
    ) -> None:
        try:
            run_start = time.time()
            send_ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(run_start))
            chain = self.coach.get_chain_state()
            await self.broadcast_log(
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
            result = await asyncio.to_thread(self.coach.ask, prompt)
            hint = {
                "type": "coach",
                "hint_kind": "deep",
                "group_id": group_id,
                "ts": time.time(),
                "speaker": str(trigger_item.get("speaker", "default") or "default"),
                "speaker_label": str(
                    trigger_item.get("speaker_label", "Speaker") or "Speaker"
                ),
                "trigger_en": str(trigger_item.get("en", "") or ""),
                "suggestion": result.text,
            }
            with self.lock:
                self.coach_hints.append(hint)
                if len(self.coach_hints) > 120:
                    self.coach_hints = self.coach_hints[-120:]
            await self.broadcast(hint)
            recv_ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
            await self.broadcast_log(
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
            await self.broadcast_log(
                "info",
                (
                    "Coach deep hint trace: "
                    f"group={group_id}, queue_ms={queue_ms}, "
                    f"create_ms={result.create_ms}, approve_ms={result.approve_ms}, "
                    f"approval_rounds={result.approval_rounds}, approval_count={result.approval_count}, "
                    f"total_ms={result.total_ms}, end_to_end_ms={end_to_end_ms}"
                ),
            )
            with self.lock:
                if inflight_end_idx > self.coach_last_sent_final_idx:
                    self.coach_last_sent_final_idx = inflight_end_idx
        except Exception as ex:
            await self.broadcast_log("error", f"Coach request failed: {ex}")
        finally:
            queued: dict[str, Any] | None = None
            next_call: tuple[str, str, float, int] | None = None
            with self.lock:
                self.coach_pending = False
                queued = self.coach_queued_trigger
                self.coach_queued_trigger = None
                if queued:
                    next_call = self._prepare_coach_call_unlocked(
                        queued,
                        ignore_cooldown=True,
                    )

            if queued and not next_call:
                await self.broadcast_log(
                    "debug",
                    "Queued coach trigger dropped (not eligible by current settings).",
                )

            if next_call:
                next_prompt, next_group_id, next_trigger_ts, next_end_idx = next_call
                await self.broadcast_log(
                    "info",
                    (
                        "Coach queued trigger resumed: "
                        f"group={next_group_id}, trigger={queued.get('speaker_label', 'Speaker')}, "
                        f"trigger_text={str(queued.get('en', '') or '').strip()}"
                    ),
                )
                await self._run_coach(
                    next_prompt,
                    queued or {},
                    next_group_id,
                    next_trigger_ts,
                    next_end_idx,
                )

    def _append_coach_hint_unlocked(self, hint: dict[str, Any]) -> None:
        self.coach_hints.append(hint)
        if len(self.coach_hints) > 120:
            self.coach_hints = self.coach_hints[-120:]

    def _normalize_topic_name(self, value: str) -> str:
        return " ".join(str(value or "").strip().split()).lower()

    def _normalize_topic_item(self, item: dict[str, Any], now_ts: float) -> dict[str, Any] | None:
        name = " ".join(str(item.get("name", "") or "").split()).strip()
        if not name:
            return None
        status = str(item.get("status", "not_started") or "not_started").strip().lower()
        if status not in {"not_started", "active", "covered"}:
            status = "active"
        try:
            time_seconds = max(0, int(item.get("time_seconds", 0) or 0))
        except Exception:
            time_seconds = 0
        statements: list[dict[str, Any]] = []
        for row in list(item.get("key_statements", []) or [])[:6]:
            if not isinstance(row, dict):
                continue
            text = " ".join(str(row.get("text", "") or "").split()).strip()
            if not text:
                continue
            try:
                ts = float(row.get("ts", now_ts) or now_ts)
            except Exception:
                ts = now_ts
            speaker = " ".join(str(row.get("speaker", "Speaker") or "Speaker").split()).strip() or "Speaker"
            statements.append({"ts": ts, "speaker": speaker, "text": text})
        return {
            "name": name,
            "status": status,
            "time_seconds": time_seconds,
            "key_statements": statements,
            "updated_ts": now_ts,
        }

    def _prepare_topic_call_unlocked(self, now_ts: float) -> dict[str, Any] | None:
        if not self.topic_tracker.is_configured:
            return None
        if not self.topics_enabled:
            return None
        if not self.topics_agenda:
            return None
        since_ts = now_ts - float(self.topics_window_sec)
        window_turns = [
            {
                "ts": float(turn.get("ts") or now_ts),
                "speaker": str(turn.get("speaker_label", "Speaker") or "Speaker"),
                "en": str(turn.get("en", "") or ""),
            }
            for turn in self.finals
            if float(turn.get("ts") or 0.0) >= since_ts
        ]
        if not window_turns:
            return None
        self.topics_pending = True
        self.topics_last_run_ts = now_ts
        return {
            "agenda": list(self.topics_agenda),
            "allow_new_topics": self.topics_allow_new,
            "current_topics": list(self.topics_items),
            "window_turns": window_turns,
            "window_seconds": int(self.topics_window_sec),
            "now_ts": now_ts,
        }

    async def _run_topic_update(self, topic_call: dict[str, Any]) -> None:
        try:
            send_ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
            await self.broadcast_log(
                "info",
                (
                    "Topics agent send: "
                    f"send_ts={send_ts}, {self._topic_trace_summary(topic_call)}"
                ),
            )
            result = await asyncio.to_thread(self.topic_tracker.ask_update, topic_call)
            payload = result.payload if isinstance(result.payload, dict) else {}
            items_raw = list(payload.get("topics", []) or [])
            now_ts = time.time()
            normalized: list[dict[str, Any]] = []
            for raw in items_raw[:30]:
                if not isinstance(raw, dict):
                    continue
                item = self._normalize_topic_item(raw, now_ts)
                if item:
                    normalized.append(item)

            with self.lock:
                if normalized:
                    by_name = {self._normalize_topic_name(x["name"]): x for x in normalized}
                    ordered: list[dict[str, Any]] = []
                    used: set[str] = set()
                    for agenda_name in self.topics_agenda:
                        key = self._normalize_topic_name(agenda_name)
                        entry = by_name.get(key)
                        if entry is None:
                            # Preserve agenda visibility even when not discussed yet.
                            ordered.append(
                                {
                                    "name": agenda_name,
                                    "status": "not_started",
                                    "time_seconds": 0,
                                    "key_statements": [],
                                    "updated_ts": now_ts,
                                }
                            )
                            continue
                        ordered.append(entry)
                        used.add(key)
                    for entry in normalized:
                        key = self._normalize_topic_name(entry["name"])
                        if key in used:
                            continue
                        if not self.topics_allow_new:
                            continue
                        ordered.append(entry)
                    self.topics_items = ordered[:40]
                self.topics_last_error = ""
                self.topics_pending = False
                out = {
                    "type": "topics_update",
                    "topics": {
                        "configured": self.topic_tracker.is_configured,
                        "enabled": self.topics_enabled,
                        "allow_new_topics": self.topics_allow_new,
                        "interval_sec": self.topics_interval_sec,
                        "window_sec": self.topics_window_sec,
                        "pending": self.topics_pending,
                        "last_run_ts": self.topics_last_run_ts,
                        "last_error": self.topics_last_error,
                        "agenda": list(self.topics_agenda),
                        "items": list(self.topics_items),
                    },
                }
            await self.broadcast(out)
            recv_ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
            await self.broadcast_log(
                "info",
                (
                    "Topics agent reply: "
                    f"recv_ts={recv_ts}, total_ms={result.total_ms}, "
                    f"response_id={result.response_id or '-'}, "
                    f"conversation_id={result.conversation_id or '-'}, "
                    f"returned_topics={len(items_raw)}, normalized_topics={len(normalized)}, "
                    f"stored_topics={len(out['topics']['items'])}"
                ),
            )
            await self.broadcast_log(
                "debug",
                (
                    "Topics updated: "
                    f"items={len(out['topics']['items'])}, "
                    f"window_turns={len(topic_call.get('window_turns', []))}, "
                    f"total_ms={result.total_ms}"
                ),
            )
        except Exception as ex:
            with self.lock:
                self.topics_pending = False
                self.topics_last_error = str(ex)
                out = {
                    "type": "topics_update",
                    "topics": {
                        "configured": self.topic_tracker.is_configured,
                        "enabled": self.topics_enabled,
                        "allow_new_topics": self.topics_allow_new,
                        "interval_sec": self.topics_interval_sec,
                        "window_sec": self.topics_window_sec,
                        "pending": self.topics_pending,
                        "last_run_ts": self.topics_last_run_ts,
                        "last_error": self.topics_last_error,
                        "agenda": list(self.topics_agenda),
                        "items": list(self.topics_items),
                    },
                }
            await self.broadcast(out)
            await self.broadcast_log("error", f"Topics update failed: {ex}")

    def configure_topics(
        self,
        *,
        agenda: list[str],
        enabled: bool,
        allow_new_topics: bool,
        interval_sec: int,
        window_sec: int,
    ) -> dict[str, Any]:
        cleaned_agenda: list[str] = []
        seen: set[str] = set()
        for raw in agenda:
            name = " ".join(str(raw or "").split()).strip()
            if not name:
                continue
            key = self._normalize_topic_name(name)
            if key in seen:
                continue
            seen.add(key)
            cleaned_agenda.append(name)
        with self.lock:
            prev_by_name = {
                self._normalize_topic_name(str(item.get("name", ""))): item
                for item in self.topics_items
                if isinstance(item, dict)
            }
            self.topics_enabled = bool(enabled)
            self.topics_allow_new = bool(allow_new_topics)
            self.topics_interval_sec = max(30, min(300, int(interval_sec)))
            self.topics_window_sec = max(60, min(300, int(window_sec)))
            self.topics_agenda = cleaned_agenda[:20]
            self.topics_last_error = ""
            self.topics_pending = False
            now_ts = time.time()
            rebuilt: list[dict[str, Any]] = []
            for name in self.topics_agenda:
                existing = prev_by_name.get(self._normalize_topic_name(name))
                if existing:
                    rebuilt.append(
                        {
                            "name": name,
                            "status": str(existing.get("status", "not_started") or "not_started"),
                            "time_seconds": int(existing.get("time_seconds", 0) or 0),
                            "key_statements": list(existing.get("key_statements", []) or [])[:6],
                            "updated_ts": now_ts,
                        }
                    )
                else:
                    rebuilt.append(
                        {
                            "name": name,
                            "status": "not_started",
                            "time_seconds": 0,
                            "key_statements": [],
                            "updated_ts": now_ts,
                        }
                    )
            if self.topics_allow_new:
                agenda_keys = {self._normalize_topic_name(name) for name in self.topics_agenda}
                for key, existing in prev_by_name.items():
                    if key in agenda_keys:
                        continue
                    rebuilt.append(
                        {
                            "name": str(existing.get("name", "Topic") or "Topic"),
                            "status": str(existing.get("status", "active") or "active"),
                            "time_seconds": int(existing.get("time_seconds", 0) or 0),
                            "key_statements": list(existing.get("key_statements", []) or [])[:6],
                            "updated_ts": now_ts,
                        }
                    )
            self.topics_items = rebuilt[:40]
        self.topic_tracker.clear_conversation()
        return self.snapshot().get("topics", {})

    async def analyze_topics_now(self) -> dict[str, Any]:
        with self.lock:
            topic_call = self._prepare_topic_call_unlocked(time.time())
        if not topic_call:
            raise RuntimeError(
                "No recent transcript available for topic analysis. Speak first, then retry."
            )
        await self._run_topic_update(topic_call)
        with self.lock:
            return {
                "configured": self.topic_tracker.is_configured,
                "enabled": self.topics_enabled,
                "allow_new_topics": self.topics_allow_new,
                "interval_sec": self.topics_interval_sec,
                "window_sec": self.topics_window_sec,
                "pending": self.topics_pending,
                "last_run_ts": self.topics_last_run_ts,
                "last_error": self.topics_last_error,
                "agenda": list(self.topics_agenda),
                "items": list(self.topics_items),
            }

    def clear_topics(self) -> None:
        with self.lock:
            self.topics_pending = False
            self.topics_last_error = ""
            self.topics_items = []
        self.topic_tracker.clear_conversation()

    def _finalize_topics_on_stop_unlocked(self) -> None:
        now_ts = time.time()
        for item in self.topics_items:
            if str(item.get("status", "")).strip().lower() == "active":
                item["status"] = "covered"
                item["updated_ts"] = now_ts

    def _apply_status_event_unlocked(self, payload: dict[str, Any]) -> dict[str, Any]:
        was_running = self.running
        self.status = str(payload.get("status", self.status))
        now_running = bool(payload.get("running", False))
        self.running = now_running
        now_ts = time.time()
        if now_running and not was_running and self.record_started_ts is None:
            self.record_started_ts = now_ts
        if not now_running and was_running and self.record_started_ts is not None:
            self.record_accumulated_ms += int((now_ts - self.record_started_ts) * 1000)
            self.record_started_ts = None
        return {
            "started_ts": self.record_started_ts,
            "accumulated_ms": self.record_accumulated_ms,
            "total_ms": self._record_total_ms_unlocked(),
        }

    def _handle_partial_event(self, payload: dict[str, Any]) -> None:
        with self.lock:
            en = str(payload.get("en", "") or "")
            speaker = str(payload.get("speaker", "default") or "default")
            speaker_label = str(payload.get("speaker_label", "Speaker") or "Speaker")
            now_ts = time.time()
            self._speaker_last_activity_ts[speaker] = now_ts
            if not en:
                return
            prev = self.live_partials.get(speaker, {})
            self.last_speech_activity_ts = now_ts
            merged_en = en or str(prev.get("en", "") or "")
            merged_ar = str(prev.get("ar", "") or "")
            out, req = self.translation.prepare_partial_unlocked(
                speaker=speaker,
                speaker_label=speaker_label,
                en=merged_en,
                prev_ar=merged_ar,
                now_ts=now_ts,
                cfg=self.config,
            )
            self.en_live = merged_en
            self.live_partials[speaker] = dict(out)
        self._broadcast_from_thread(out)
        self._emit_trace_from_thread(out, channel="speech_partial")
        if req:
            self.translation.enqueue_from_thread(req)

    def _create_final_item(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "final",
            "en": str(payload.get("en", "") or ""),
            "ar": "",
            "speaker": str(payload.get("speaker", "default") or "default"),
            "speaker_label": str(payload.get("speaker_label", "Speaker") or "Speaker"),
            "ts": payload.get("ts") or time.time(),
        }

    def _should_suppress_dual_local_unlocked(self, payload: dict[str, Any]) -> bool:
        if self.config.capture_mode != "dual":
            return False
        speaker = str(payload.get("speaker", "default") or "default")
        if speaker != "local":
            return False
        # If a remote partial is still active (not yet finalized), treat local
        # recognitions as bleed and suppress them.
        remote_live = self.live_partials.get("remote")
        if remote_live and str(remote_live.get("en", "") or "").strip():
            return True
        now_ts = time.time()
        remote_ts = float(self._speaker_last_activity_ts.get("remote", 0.0) or 0.0)
        if remote_ts <= 0:
            return False
        return (now_ts - remote_ts) <= float(self._bleed_suppress_window_sec)

    def _append_final_unlocked(self, item: dict[str, Any]) -> None:
        self.finals.append(
            {
                "en": item["en"],
                "ar": item["ar"],
                "speaker": item["speaker"],
                "speaker_label": item["speaker_label"],
                "segment_id": item["segment_id"],
                "revision": item["revision"],
                "ts": item["ts"],
            }
        )
        if len(self.finals) > self.config.max_finals:
            self.finals = self.finals[-self.config.max_finals :]
        self.en_live = ""
        self.ar_live = ""
        self.live_partials.pop(item["speaker"], None)
        if item["en"] or item["ar"]:
            self.last_speech_activity_ts = time.time()

    def _schedule_coach_from_thread(
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
                self._run_coach(
                    coach_prompt,
                    item,
                    coach_group_id,
                    coach_trigger_ts,
                    inflight_end_idx,
                ),
                loop,
            )

    def _handle_final_event(self, payload: dict[str, Any]) -> None:
        coach_call: tuple[str, str, float, int] | None = None
        queued_while_busy = False
        item = self._create_final_item(payload)
        with self.lock:
            item, req = self.translation.prepare_final_unlocked(
                speaker=item["speaker"],
                speaker_label=item["speaker_label"],
                en=item["en"],
                ts=float(item["ts"]),
                debug=bool(self.config.debug),
            )
            self._append_final_unlocked(item)
            is_candidate = self._should_trigger_coach_unlocked(
                item,
                ignore_busy=True,
            )
            if is_candidate:
                if self.coach_pending:
                    self.coach_queued_trigger = dict(item)
                    queued_while_busy = True
                else:
                    coach_call = self._prepare_coach_call_unlocked(item)
        self._broadcast_from_thread(item)
        self._emit_trace_from_thread(item, channel="speech_final")
        if req:
            self.translation.enqueue_from_thread(req)
        self._schedule_coach_from_thread(item, coach_call, queued_while_busy)

    def _can_start_unlocked(self) -> tuple[bool, str]:
        if self.config.capture_mode == "dual":
            local_device = (self.config.local_input_device_id or "").strip()
            remote_device = (self.config.remote_input_device_id or "").strip()
            missing: list[str] = []
            if not local_device:
                missing.append("local_input_device_id")
            if not remote_device:
                missing.append("remote_input_device_id")
            if missing:
                return (
                    False,
                    (
                        "Start blocked: Dual Input mode requires both Local and Remote input devices. "
                        f"Missing: {', '.join(missing)}"
                    ),
                )
        if self.config.coach_enabled and not self.coach.is_configured:
            return (
                False,
                (
                    "Start blocked: coach is enabled but not configured. "
                    "Set PROJECT_ENDPOINT, MODEL_DEPLOYMENT_NAME, and AGENT_ID/AGENT_NAME."
                ),
            )
        if self.config.coach_enabled and not self.coach.supports_conversations_create():
            return (
                False,
                (
                    "Start blocked: coach requires conversations.create() support, "
                    "but current client/runtime does not provide it."
                ),
            )
        return True, ""

    def _reset_coach_runtime_unlocked(self, *, keep_history: bool) -> None:
        if not keep_history:
            self.coach_hints = []
        self.coach_pending = False
        self.coach_last_run_ts = 0.0
        self.coach_last_sent_final_idx = len(self.finals)
        self.coach_queued_trigger = None

    def handle_speech_event(self, payload: dict[str, Any]) -> None:
        kind = payload.get("type")
        if kind == "status":
            with self.lock:
                recording = self._apply_status_event_unlocked(payload)
            self._broadcast_from_thread(
                {
                    "type": "status",
                    "status": self.status,
                    "running": self.running,
                    "recording": recording,
                }
            )
            return

        if kind == "partial":
            with self.lock:
                if not self.running:
                    return
                if self._should_suppress_dual_local_unlocked(payload):
                    if bool(self.config.debug):
                        self._broadcast_from_thread(
                            self._append_log(
                                "debug",
                                "Suppressed local partial while remote active (dual-mode bleed guard).",
                            )
                        )
                    return
            self._handle_partial_event(payload)
            return

        if kind == "final":
            with self.lock:
                if not self.running:
                    return
                if self._should_suppress_dual_local_unlocked(payload):
                    if bool(self.config.debug):
                        self._broadcast_from_thread(
                            self._append_log(
                                "debug",
                                "Suppressed local final while remote active (dual-mode bleed guard).",
                            )
                        )
                    return
            self._handle_final_event(payload)
            return

        if kind == "log":
            item = self._append_log(
                str(payload.get("level", "info")),
                str(payload.get("message", "")),
            )
            self._broadcast_from_thread(item)

    def start(self) -> bool:
        can_start, message = self._can_start_unlocked()
        if not can_start:
            self._broadcast_from_thread(self._append_log("error", message))
            return False

        session_conversation_id: str | None = None
        if self.config.coach_enabled:
            try:
                session_conversation_id = self.coach.ensure_session()
            except Exception as ex:
                self._broadcast_from_thread(
                    self._append_log(
                        "error",
                        f"Start blocked: failed to initialize coach session via conversations.create(): {ex}",
                    )
                )
                return False

        started = self.speech.start_recognition()
        if not started:
            return False
        with self.lock:
            self.session_started_ts = time.time()
            self.last_speech_activity_ts = self.session_started_ts
            self.translation.reset_unlocked()
            self._reset_coach_runtime_unlocked(keep_history=True)
            self.topics_pending = False
            self.topics_last_error = ""
        if self.config.coach_enabled:
            self._broadcast_from_thread(
                self._append_log(
                    "info",
                    f"Coach session active: conversation_id={session_conversation_id or '-'}",
                )
            )
        if self.topics_enabled and self.topics_agenda:
            self.topic_tracker.clear_conversation()
            self._broadcast_from_thread(
                self._append_log("info", "Topics tracker session prepared.")
            )
        return True

    def stop(self) -> bool:
        stopped = self.speech.stop_recognition()
        if not stopped:
            return False
        with self.lock:
            self._reset_coach_runtime_unlocked(keep_history=True)
            self.translation.reset_unlocked()
            self.topics_pending = False
            self._finalize_topics_on_stop_unlocked()
            topics_payload = {
                "type": "topics_update",
                "topics": {
                    "configured": self.topic_tracker.is_configured,
                    "enabled": self.topics_enabled,
                    "allow_new_topics": self.topics_allow_new,
                    "interval_sec": self.topics_interval_sec,
                    "window_sec": self.topics_window_sec,
                    "pending": self.topics_pending,
                    "last_run_ts": self.topics_last_run_ts,
                    "last_error": self.topics_last_error,
                    "agenda": list(self.topics_agenda),
                    "items": list(self.topics_items),
                },
            }
        self.coach.clear_conversation()
        self.topic_tracker.clear_conversation()
        self._broadcast_from_thread(topics_payload)
        return True

    def clear_logs(self) -> None:
        with self.lock:
            self.logs = []

    def clear_transcript(self) -> None:
        with self.lock:
            self.finals = []
            self.en_live = ""
            self.ar_live = ""
            self.live_partials = {}
            self.translation.reset_unlocked()
            self.coach_last_sent_final_idx = 0
            self.coach_queued_trigger = None
            self.topics_pending = False
            self.topics_last_run_ts = 0.0
            self.topics_items = [
                {
                    "name": name,
                    "status": "not_started",
                    "time_seconds": 0,
                    "key_statements": [],
                    "updated_ts": time.time(),
                }
                for name in self.topics_agenda
            ]
        self.coach.clear_conversation()
        self.topic_tracker.clear_conversation()

    def clear_coach(self) -> None:
        with self.lock:
            self._reset_coach_runtime_unlocked(keep_history=False)
        self.coach.clear_conversation()

    async def request_coach(self, prompt: str, speaker_label: str = "Manual") -> dict[str, Any]:
        manual_prompt = "\n".join(
            [
                "Manual user message (same conversation):",
                str(prompt or "").strip(),
            ]
        )
        send_ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        chain = self.coach.get_chain_state()
        await self.broadcast_log(
            "info",
            (
                "Coach manual send: "
                f"send_ts={send_ts}, speaker_label={speaker_label}, "
                f"req_conversation_id={chain.get('conversation_id') or '-'}, "
                f"req_previous_response_id={chain.get('previous_response_id') or '-'}, "
                f"prompt={self._preview_text(prompt)}"
            ),
        )
        result = await asyncio.to_thread(self.coach.ask, manual_prompt)
        hint = {
            "type": "coach",
            "hint_kind": "manual",
            "group_id": "",
            "ts": time.time(),
            "speaker": "manual",
            "speaker_label": speaker_label or "Manual",
            "trigger_en": "",
            "suggestion": result.text,
        }
        with self.lock:
            self._append_coach_hint_unlocked(hint)
        await self.broadcast(hint)
        recv_ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        await self.broadcast_log(
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

    async def connect_websocket(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect_websocket(self, websocket: WebSocket) -> None:
        self.connections.discard(websocket)


settings = Settings()
controller = AppController(settings=settings)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    controller.loop = asyncio.get_running_loop()
    controller.translation.start(controller.loop)
    controller.watchdog_task = asyncio.create_task(controller.watchdog_loop())
    controller._append_log("info", "App started")
    try:
        controller.reload_config_from_disk()
        controller._append_log(
            "info", f"Loaded settings from {controller.settings_path.name}"
        )
    except FileNotFoundError:
        controller._append_log(
            "info", f"No settings file found ({controller.settings_path.name}); using defaults"
        )
    except Exception as ex:
        controller._append_log("error", f"Failed to load settings file: {ex}")
    yield
    await controller.translation.stop()
    if controller.watchdog_task:
        controller.watchdog_task.cancel()
        try:
            await controller.watchdog_task
        except asyncio.CancelledError:
            pass
    try:
        controller.coach.close()
    except Exception:
        pass
    try:
        controller.topic_tracker.close()
    except Exception:
        pass


app = FastAPI(title="Speech Translator", lifespan=lifespan)
app.state.controller = controller

# 1) API routes first
app.include_router(api_router, prefix="/api", tags=["api"])

# 2) WebSocket route second
app.websocket("/ws")(websocket_endpoint)

# 3) Static mount last
app.mount("/", StaticFiles(directory="static", html=True), name="static")
