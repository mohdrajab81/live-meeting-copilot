"""
AppController — thin wiring layer.

Owns no domain logic. Creates each sub-module, wires their dependencies,
and exposes the public API surface used by routes.py and websocket.py.
"""

import asyncio
import threading
from pathlib import Path
from typing import Any

from fastapi import WebSocket

from app.config import RuntimeConfig, Settings
from app.services.coach import CoachService
from app.services.speech import SpeechService
from app.services.topic_tracker import TopicTrackerService
from app.services.translation_pipeline import TranslationPipeline

from .broadcast_service import BroadcastService
from .config_store import ConfigStore
from .coach_orchestrator import CoachOrchestrator
from .session_manager import SessionManager
from .topic_orchestrator import TopicOrchestrator
from .transcript_store import TranscriptStore


class AppController:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

        # Single shared lock — all modules that need cross-cutting atomicity share it.
        self.lock = threading.RLock()

        # ── Independent modules (own their own locks) ─────────────────────────
        self.config_store = ConfigStore(settings_path=Path("web_translator_settings.json"))
        self.broadcast_svc = BroadcastService()

        # ── Services ──────────────────────────────────────────────────────────
        self.coach = CoachService.from_environment()
        self.topic_tracker = TopicTrackerService.from_environment()

        # ── Shared-lock modules (receive the RLock) ────────────────────────────
        self.transcript_store = TranscriptStore(
            lock=self.lock,
            broadcast=self.broadcast_svc.broadcast,
            broadcast_log=self.broadcast_svc.broadcast_log,
            emit_trace_async=self.broadcast_svc.emit_trace_async,
            get_debug=self.config_store.get_debug,
        )

        self.translation = TranslationPipeline(
            settings=settings,
            apply_translation_result=self.transcript_store.apply_translation_result,
            log=self.broadcast_svc.broadcast_log,
        )
        # Late-bind translation into transcript_store (needed for is_current_partial check).
        self.transcript_store.translation = self.translation

        self.coach_orch = CoachOrchestrator(
            lock=self.lock,
            coach=self.coach,
            broadcast=self.broadcast_svc.broadcast,
            broadcast_log=self.broadcast_svc.broadcast_log,
            broadcast_from_thread=self.broadcast_svc.broadcast_from_thread,
            append_log=self.broadcast_svc.append_log,
            get_finals=self.transcript_store.get_finals,
            get_config=self.config_store.get,
            preview_text=self.broadcast_svc.preview_text,
        )

        self.topic_orch = TopicOrchestrator(
            lock=self.lock,
            topic_tracker=self.topic_tracker,
            broadcast=self.broadcast_svc.broadcast,
            broadcast_log=self.broadcast_svc.broadcast_log,
            get_finals=self.transcript_store.get_finals,
            preview_text=self.broadcast_svc.preview_text,
        )

        self.session_mgr = SessionManager(
            lock=self.lock,
            speech=SpeechService(
                settings=settings,
                on_event=self._handle_speech_event_internal,
                get_runtime_config=self.config_store.get,
            ),
            translation=self.translation,
            transcript_store=self.transcript_store,
            coach_orch=self.coach_orch,
            topic_orch=self.topic_orch,
            broadcast=self.broadcast_svc.broadcast,
            broadcast_from_thread=self.broadcast_svc.broadcast_from_thread,
            broadcast_log=self.broadcast_svc.broadcast_log,
            append_log=self.broadcast_svc.append_log,
            emit_trace_from_thread=self.broadcast_svc.emit_trace_from_thread,
            get_config=self.config_store.get,
            coach=self.coach,
        )

        # Late-bind telemetry context so translation callbacks broadcast real ws/status/running.
        self.transcript_store._get_telemetry_context = lambda: (
            len(self.broadcast_svc.connections),
            self.session_mgr.status,
            self.session_mgr.running,
        )

    # ── Internal event bridge ─────────────────────────────────────────────────

    def _handle_speech_event_internal(self, payload: dict[str, Any]) -> None:
        """Bridge from SpeechService callback into SessionManager."""
        self.session_mgr.handle_speech_event(payload)

    # ── Loop wiring (called from lifespan) ────────────────────────────────────

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self.broadcast_svc.loop = loop
        self.session_mgr.loop = loop
        self.coach_orch.loop = loop

    # ── Public API: config ────────────────────────────────────────────────────

    def get_config(self) -> dict[str, Any]:
        return self.config_store.dump()

    def get_runtime_config(self) -> RuntimeConfig:
        return self.config_store.get()

    def set_config(self, config: RuntimeConfig) -> None:
        self.config_store.set(config)

    def reset_config_to_defaults(self) -> dict[str, Any]:
        return self.config_store.reset()

    def save_config_to_disk(self) -> str:
        return self.config_store.save_to_disk()

    def reload_config_from_disk(self) -> dict[str, Any]:
        return self.config_store.reload_from_disk()

    # ── Public API: session ───────────────────────────────────────────────────

    @property
    def running(self) -> bool:
        return self.session_mgr.running

    @property
    def status(self) -> str:
        return self.session_mgr.status

    def start(self) -> bool:
        return self.session_mgr.start()

    def stop(self) -> bool:
        return self.session_mgr.stop()

    async def stop_async(self) -> bool:
        return await self.session_mgr.stop_async()

    # ── Public API: transcript ────────────────────────────────────────────────

    def clear_transcript(self) -> None:
        with self.lock:
            self.transcript_store.clear_unlocked()
            self.translation.reset_unlocked()
            self.coach_orch.reset_sent_index_unlocked(new_index=0)
            self.coach_orch.clear_queued_trigger_unlocked()
            self.topic_orch.clear_for_transcript_unlocked()
        self.coach.clear_conversation()
        self.topic_tracker.clear_conversation()

    def clear_logs(self) -> None:
        self.broadcast_svc.clear_logs()

    # ── Public API: coach ─────────────────────────────────────────────────────

    def clear_coach(self) -> None:
        self.coach_orch.clear(coach_service=self.coach)

    async def request_coach(self, prompt: str, speaker_label: str = "Manual") -> dict[str, Any]:
        return await self.coach_orch.request_manual(prompt=prompt, speaker_label=speaker_label)

    # ── Public API: topics ────────────────────────────────────────────────────

    def configure_topics(
        self,
        *,
        agenda: list[str],
        enabled: bool,
        allow_new_topics: bool,
        chunk_mode: str = "since_last",
        interval_sec: int,
        window_sec: int,
        definitions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return self.topic_orch.configure(
            agenda=agenda,
            enabled=enabled,
            allow_new_topics=allow_new_topics,
            chunk_mode=chunk_mode,
            interval_sec=interval_sec,
            window_sec=window_sec,
            definitions=definitions,
        )

    async def analyze_topics_now(self) -> dict[str, Any]:
        return await self.topic_orch.analyze_now()

    def clear_topics(self) -> None:
        self.topic_orch.clear(topic_tracker=self.topic_tracker)

    # ── Public API: WebSocket ─────────────────────────────────────────────────

    async def connect_websocket(self, websocket: WebSocket) -> None:
        await self.broadcast_svc.connect(websocket)

    def disconnect_websocket(self, websocket: WebSocket) -> None:
        self.broadcast_svc.disconnect(websocket)

    # ── Public API: broadcast (used by routes) ────────────────────────────────

    async def broadcast(self, payload: dict[str, Any]) -> None:
        await self.broadcast_svc.broadcast(payload)

    async def broadcast_log(self, level: str, message: str) -> None:
        await self.broadcast_svc.broadcast_log(level, message)

    # ── Watchdog ──────────────────────────────────────────────────────────────

    async def watchdog_loop(self) -> None:
        await self.session_mgr.watchdog_loop()

    # ── Snapshot ──────────────────────────────────────────────────────────────

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            ts_snap = self.transcript_store.snapshot_unlocked()
            session_snap = self.session_mgr.snapshot_unlocked()
            coach_snap = self.coach_orch.snapshot_unlocked()
            topic_snap = self.topic_orch.payload_unlocked()
            telemetry = self.transcript_store.build_telemetry_unlocked(
                ws_connections=len(self.broadcast_svc.connections),
                status=session_snap["status"],
                running=session_snap["running"],
            )
        return {
            "type": "snapshot",
            "status": session_snap["status"],
            "running": session_snap["running"],
            "session_started_ts": session_snap["session_started_ts"],
            "config": self.config_store.dump(),
            "en_live": ts_snap["en_live"],
            "ar_live": ts_snap["ar_live"],
            "live_partials": ts_snap["live_partials"],
            "finals": ts_snap["finals"],
            "logs": self.broadcast_svc.get_logs(),
            "recording": session_snap["recording"],
            "coach": coach_snap,
            "topics": topic_snap,
            "telemetry": telemetry,
        }
