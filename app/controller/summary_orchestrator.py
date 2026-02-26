"""
SummaryOrchestrator — owns end-of-session summary state and generation.

State: summary_pending, summary_result, summary_generated_ts, summary_error.

Shares the AppController RLock for all state mutations.
"""

import asyncio
import threading
import time
from typing import Any, Awaitable, Callable

from app.config import RuntimeConfig
from app.services.summary import SummaryService

BroadcastCallback = Callable[[dict[str, Any]], Awaitable[None]]
BroadcastLogCallback = Callable[[str, str], Awaitable[None]]


class SummaryOrchestrator:
    def __init__(
        self,
        lock: threading.RLock,
        summary_service: SummaryService,
        broadcast: BroadcastCallback,
        broadcast_log: BroadcastLogCallback,
        get_finals: Callable[[], list[dict[str, Any]]],
        get_config: Callable[[], RuntimeConfig],
    ) -> None:
        self._lock = lock
        self._summary = summary_service
        self._broadcast = broadcast
        self._broadcast_log = broadcast_log
        self._get_finals = get_finals
        self._get_config = get_config

        # State (protected by shared lock)
        self.summary_pending: bool = False
        self.summary_result: dict[str, Any] | None = None
        self.summary_generated_ts: float | None = None
        self.summary_error: str = ""

    @property
    def is_configured(self) -> bool:
        return self._summary.is_configured

    def clear_unlocked(self) -> None:
        self.summary_pending = False
        self.summary_result = None
        self.summary_generated_ts = None
        self.summary_error = ""

    def snapshot_unlocked(self) -> dict[str, Any]:
        result = self.summary_result or {}
        return {
            "configured": self._summary.is_configured,
            "pending": self.summary_pending,
            "error": self.summary_error,
            "generated_ts": self.summary_generated_ts,
            # Flatten result for UI consumers and keep nested payload for compatibility.
            "executive_summary": str(result.get("executive_summary", "") or ""),
            "key_points": list(result.get("key_points") or []),
            "action_items": list(result.get("action_items") or []),
            "result": self.summary_result,
        }

    def _build_transcript_text_unlocked(self) -> str:
        finals = self._get_finals()
        lines = []
        for f in finals[-500:]:
            ts_str = time.strftime("%H:%M:%S", time.localtime(float(f.get("ts") or 0)))
            label = str(f.get("speaker_label") or "Speaker")
            text = str(f.get("en") or "").strip()
            if text:
                lines.append(f"[{ts_str}] {label}: {text}")
        return "\n".join(lines)

    async def run_summary(self) -> None:
        config = self._get_config()
        if not config.summary_enabled:
            return
        if not self._summary.is_configured:
            await self._broadcast_log(
                "warning",
                "Summary skipped: agent not configured (set SUMMARY_AGENT_ID).",
            )
            return
        with self._lock:
            if self.summary_pending:
                return
            self.summary_pending = True
            self.summary_error = ""
            transcript_text = self._build_transcript_text_unlocked()

        if not transcript_text.strip():
            with self._lock:
                self.summary_pending = False
            await self._broadcast_log("info", "Summary skipped: transcript is empty.")
            return

        await self._broadcast_log("info", "Summary generation started.")
        try:
            from app.services.summary import SummaryResult  # noqa: F401
            result: Any = await asyncio.to_thread(self._summary.generate, transcript_text)
            payload: dict[str, Any] = {
                "executive_summary": result.executive_summary,
                "key_points": result.key_points,
                "action_items": result.action_items,
                "generated_ts": time.time(),
                "total_ms": result.total_ms,
            }
            with self._lock:
                self.summary_pending = False
                self.summary_result = payload
                self.summary_generated_ts = payload["generated_ts"]
                self.summary_error = ""
            await self._broadcast({"type": "summary", **payload})
            await self._broadcast_log(
                "info",
                f"Summary generated: total_ms={result.total_ms}, "
                f"key_points={len(result.key_points)}, "
                f"action_items={len(result.action_items)}",
            )
        except Exception as ex:
            with self._lock:
                self.summary_pending = False
                self.summary_error = str(ex)
            await self._broadcast_log("error", f"Summary generation failed: {ex}")
            await self._broadcast({"type": "summary", "error": str(ex), "generated_ts": None})

    async def run_summary_now(self) -> dict[str, Any]:
        with self._lock:
            if self.summary_pending:
                raise ValueError("Summary generation already in progress.")
            if not self._summary.is_configured:
                raise ValueError(
                    "Summary agent not configured. Set SUMMARY_AGENT_ID and related env vars."
                )
        await self.run_summary()
        with self._lock:
            return self.snapshot_unlocked()
