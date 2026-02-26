"""
SessionManager — owns session lifecycle, speech event handling, and watchdog.

State: running, status, record_started_ts, record_accumulated_ms,
       session_started_ts, last_speech_activity_ts (mirrored from TranscriptStore),
       watchdog_task.

Shares the AppController RLock for all state mutations.
"""

import asyncio
import threading
import time
from typing import Any, Awaitable, Callable

from app.config import RuntimeConfig
from app.services.coach import CoachService
from app.services.speech import SpeechService
from app.services.translation_pipeline import TranslationPipeline

from .coach_orchestrator import CoachOrchestrator
from .topic_orchestrator import TopicOrchestrator
from .transcript_store import TranscriptStore


BroadcastCallback = Callable[[dict[str, Any]], Awaitable[None]]
BroadcastLogCallback = Callable[[str, str], Awaitable[None]]
BroadcastFromThreadCallback = Callable[[dict[str, Any]], None]
AppendLogCallback = Callable[[str, str], dict[str, Any]]
EmitTraceFromThreadCallback = Callable[..., None]


class SessionManager:
    def __init__(
        self,
        lock: threading.RLock,
        speech: SpeechService,
        translation: TranslationPipeline,
        transcript_store: TranscriptStore,
        coach_orch: CoachOrchestrator,
        topic_orch: TopicOrchestrator,
        broadcast: BroadcastCallback,
        broadcast_from_thread: BroadcastFromThreadCallback,
        broadcast_log: BroadcastLogCallback,
        append_log: AppendLogCallback,
        emit_trace_from_thread: EmitTraceFromThreadCallback,
        get_config: Callable[[], RuntimeConfig],
        coach: CoachService,
    ) -> None:
        self._lock = lock
        self._speech = speech
        self._translation = translation
        self._transcript = transcript_store
        self._coach_orch = coach_orch
        self._topic_orch = topic_orch
        self._broadcast = broadcast
        self._broadcast_from_thread = broadcast_from_thread
        self._broadcast_log = broadcast_log
        self._append_log = append_log
        self._emit_trace_from_thread = emit_trace_from_thread
        self._get_config = get_config
        self._coach = coach

        self.loop: asyncio.AbstractEventLoop | None = None
        self.watchdog_task: asyncio.Task[None] | None = None

        # Session state (protected by shared lock)
        self.running = False
        self.status = "idle"
        self.session_started_ts = time.time()
        self.record_started_ts: float | None = None
        self.record_accumulated_ms = 0

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _record_total_ms_unlocked(self) -> int:
        total_ms = self.record_accumulated_ms
        if self.record_started_ts is not None:
            total_ms += int((time.time() - self.record_started_ts) * 1000)
        return int(total_ms)

    def _can_start_unlocked(self, config: RuntimeConfig) -> tuple[bool, str]:
        if config.capture_mode == "dual":
            local_device = (config.local_input_device_id or "").strip()
            remote_device = (config.remote_input_device_id or "").strip()
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
        if config.coach_enabled and not self._coach.is_configured:
            return (
                False,
                (
                    "Start blocked: coach is enabled but not configured. "
                    "Set PROJECT_ENDPOINT, MODEL_DEPLOYMENT_NAME, and AGENT_ID/AGENT_NAME."
                ),
            )
        if config.coach_enabled and not self._coach.supports_conversations_create():
            return (
                False,
                (
                    "Start blocked: coach requires conversations.create() support, "
                    "but current client/runtime does not provide it."
                ),
            )
        return True, ""

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

    # ── Speech event handling ─────────────────────────────────────────────────

    def handle_speech_event(self, payload: dict[str, Any]) -> None:
        kind = payload.get("type")
        config = self._get_config()

        if kind == "status":
            with self._lock:
                was_running = self.running
                recording = self._apply_status_event_unlocked(payload)
            self._broadcast_from_thread(
                {
                    "type": "status",
                    "status": self.status,
                    "running": self.running,
                    "recording": recording,
                }
            )
            if was_running and not self.running:
                self._do_finalize()
            return

        if kind == "partial":
            with self._lock:
                if not self.running:
                    return
                if self._transcript.should_suppress_dual_local_unlocked(
                    payload, config.capture_mode
                ):
                    if config.debug:
                        self._broadcast_from_thread(
                            self._append_log(
                                "debug",
                                "Suppressed local partial while remote active (dual-mode bleed guard).",
                            )
                        )
                    return
            self._handle_partial_event(payload, config)
            return

        if kind == "final":
            with self._lock:
                if not self.running:
                    return
                if self._transcript.should_suppress_dual_local_unlocked(
                    payload, config.capture_mode
                ):
                    if config.debug:
                        self._broadcast_from_thread(
                            self._append_log(
                                "debug",
                                "Suppressed local final while remote active (dual-mode bleed guard).",
                            )
                        )
                    return
            self._handle_final_event(payload, config)
            return

        if kind == "log":
            item = self._append_log(
                str(payload.get("level", "info")),
                str(payload.get("message", "")),
            )
            self._broadcast_from_thread(item)

    def _create_final_item(self, payload: dict[str, Any]) -> dict[str, Any]:
        final_ts = float(payload.get("ts") or time.time())
        try:
            start_ts = float(payload.get("start_ts", final_ts) or final_ts)
        except Exception:
            start_ts = final_ts
        if start_ts <= 0:
            start_ts = final_ts
        speaker = str(payload.get("speaker", "default") or "default")
        fallback_segment_id = f"{speaker}-raw-{int(final_ts * 1000)}"
        return {
            "type": "final",
            "en": str(payload.get("en", "") or ""),
            "ar": "",
            "speaker": speaker,
            "speaker_label": str(payload.get("speaker_label", "Speaker") or "Speaker"),
            "segment_id": str(
                payload.get("segment_id", fallback_segment_id) or fallback_segment_id
            ),
            "revision": max(0, int(payload.get("revision", 0) or 0)),
            "ts": final_ts,
            "start_ts": min(start_ts, final_ts),
        }

    def _handle_partial_event(
        self, payload: dict[str, Any], config: RuntimeConfig
    ) -> None:
        with self._lock:
            en = str(payload.get("en", "") or "")
            speaker = str(payload.get("speaker", "default") or "default")
            speaker_label = str(payload.get("speaker_label", "Speaker") or "Speaker")
            now_ts = time.time()
            self._transcript.update_speaker_activity_unlocked(speaker, now_ts, has_speech=bool(en))
            if not en:
                return
            prev = self._transcript.live_partials.get(speaker, {})
            merged_en = en or str(prev.get("en", "") or "")
            merged_ar = str(prev.get("ar", "") or "")
            out, req = self._translation.prepare_partial_unlocked(
                speaker=speaker,
                speaker_label=speaker_label,
                en=merged_en,
                prev_ar=merged_ar,
                now_ts=now_ts,
                cfg=config,
            )
            self._transcript.en_live = merged_en
            self._transcript.live_partials[speaker] = dict(out)
        self._broadcast_from_thread(out)
        self._emit_trace_from_thread(
            out, channel="speech_partial", debug=config.debug
        )
        if req and config.translation_enabled:
            self._translation.enqueue_from_thread(req)

    def _handle_final_event(
        self, payload: dict[str, Any], config: RuntimeConfig
    ) -> None:
        coach_call: tuple[str, str, float, int] | None = None
        queued_while_busy = False
        item = self._create_final_item(payload)
        with self._lock:
            item, req = self._translation.prepare_final_unlocked(
                speaker=item["speaker"],
                speaker_label=item["speaker_label"],
                en=item["en"],
                ts=float(item["ts"]),
                debug=bool(config.debug),
            )
            self._transcript.append_final_unlocked(item, max_finals=config.max_finals)
            is_candidate = self._coach_orch.should_trigger_unlocked(
                item, config, ignore_busy=True
            )
            if is_candidate:
                if self._coach_orch.coach_pending:
                    self._coach_orch.coach_queued_trigger = dict(item)
                    queued_while_busy = True
                else:
                    coach_call = self._coach_orch.prepare_call_unlocked(item, config)
        self._broadcast_from_thread(item)
        self._emit_trace_from_thread(item, channel="speech_final", debug=config.debug)
        if req and config.translation_enabled:
            self._translation.enqueue_from_thread(req)
        self._coach_orch.schedule_from_thread(item, coach_call, queued_while_busy)

    # ── Session lifecycle ─────────────────────────────────────────────────────

    def start(self) -> bool:
        config = self._get_config()
        can_start, message = self._can_start_unlocked(config)
        if not can_start:
            self._broadcast_from_thread(self._append_log("error", message))
            return False

        session_conversation_id: str | None = None
        if config.coach_enabled:
            try:
                session_conversation_id = self._coach.ensure_session()
            except Exception as ex:
                self._broadcast_from_thread(
                    self._append_log(
                        "error",
                        f"Start blocked: failed to initialize coach session via conversations.create(): {ex}",
                    )
                )
                return False

        started = self._speech.start_recognition()
        if not started:
            return False

        with self._lock:
            self.session_started_ts = time.time()
            self._transcript.last_speech_activity_ts = self.session_started_ts
            self._translation.reset_unlocked()
            self._coach_orch.reset_runtime_unlocked(keep_history=True)
            self._topic_orch.topics_session_started_ts = self.session_started_ts
            self._topic_orch.topics_pending = False
            self._topic_orch.topics_last_error = ""
            self._topic_orch.topics_last_final_idx = max(
                0,
                min(
                    int(self._topic_orch.topics_last_final_idx or 0),
                    self._transcript.get_finals_count(),
                ),
            )

        if config.coach_enabled:
            self._broadcast_from_thread(
                self._append_log(
                    "info",
                    f"Coach session active: conversation_id={session_conversation_id or '-'}",
                )
            )
        return True

    def stop(self) -> bool:
        stopped = self._speech.stop_recognition()
        if not stopped:
            return False
        self._do_finalize()
        return True

    async def stop_async(self) -> bool:
        """Stop with a final topic-flush before finalizing."""
        stopped = self._speech.stop_recognition()
        if not stopped:
            return False
        topic_call = None
        with self._lock:
            if (
                self._topic_orch.topics_enabled
                and self._topic_orch.is_tracker_configured
                and not self._topic_orch.topics_pending
            ):
                topic_call = self._topic_orch.prepare_call_unlocked(
                    time.time(), trigger="auto"
                )
        if topic_call:
            try:
                await asyncio.wait_for(
                    self._topic_orch.run_update(topic_call), timeout=30.0
                )
            except Exception:
                pass  # flush failure must not block cleanup
        self._do_finalize()
        return True

    def _do_finalize(self) -> None:
        with self._lock:
            self._coach_orch.reset_runtime_unlocked(keep_history=True)
            self._translation.reset_unlocked()
            self._topic_orch.topics_pending = False
            self._topic_orch.finalize_on_stop_unlocked()
            topics_payload = {
                "type": "topics_update",
                "topics": self._topic_orch.payload_unlocked(),
            }
        self._coach.clear_conversation()
        self._broadcast_from_thread(topics_payload)

    # ── Watchdog ──────────────────────────────────────────────────────────────

    async def watchdog_loop(self) -> None:
        while True:
            await asyncio.sleep(1.0)
            reason: str | None = None
            topic_call: dict[str, Any] | None = None
            config = self._get_config()
            with self._lock:
                if not self.running:
                    continue
                now = time.time()
                silence_limit = int(config.auto_stop_silence_sec)
                max_session = int(config.max_session_sec)
                idle_for = now - self._transcript.last_speech_activity_ts
                run_for = now - self.session_started_ts
                if (
                    self._topic_orch.topics_enabled
                    and not self._topic_orch.topics_pending
                    and self._topic_orch.is_tracker_configured
                    and (now - self._topic_orch.topics_last_run_ts)
                    >= float(self._topic_orch.topics_interval_sec)
                ):
                    topic_call = self._topic_orch.prepare_call_unlocked(now, trigger="auto")
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
                    await self._topic_orch.run_update(topic_call)
                continue
            if await self.stop_async():
                await self._broadcast_log("warning", reason)

    # ── Snapshot ──────────────────────────────────────────────────────────────

    def snapshot_unlocked(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "running": self.running,
            "session_started_ts": self.session_started_ts,
            "recording": {
                "started_ts": self.record_started_ts,
                "accumulated_ms": self.record_accumulated_ms,
                "total_ms": self._record_total_ms_unlocked(),
            },
        }
