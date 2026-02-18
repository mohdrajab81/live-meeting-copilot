"""
BroadcastService — owns WebSocket connections, logs, and the event loop reference.

Has its own asyncio-safe state. No shared AppController lock needed here
because all connection mutations happen on the event loop.
"""

import asyncio
import json
import time
from typing import Any

from fastapi import WebSocket


class BroadcastService:
    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()
        self.loop: asyncio.AbstractEventLoop | None = None
        self._logs: list[dict[str, Any]] = []

    # ── WebSocket lifecycle ───────────────────────────────────────────────────

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections.discard(websocket)

    # ── Core broadcast ────────────────────────────────────────────────────────

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

    def broadcast_from_thread(self, payload: dict[str, Any]) -> None:
        loop = self.loop
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast(payload), loop)

    # ── Logging ───────────────────────────────────────────────────────────────

    def append_log(self, level: str, message: str) -> dict[str, Any]:
        item = {
            "type": "log",
            "level": level,
            "message": message,
            "ts": time.time(),
        }
        self._logs.append(item)
        if len(self._logs) > 1000:
            self._logs = self._logs[-1000:]
        return item

    async def broadcast_log(self, level: str, message: str) -> None:
        await self.broadcast(self.append_log(level, message))

    def get_logs(self) -> list[dict[str, Any]]:
        return list(self._logs)

    def clear_logs(self) -> None:
        self._logs = []

    # ── Debug trace helpers ───────────────────────────────────────────────────

    def emit_trace_from_thread(
        self, payload: dict[str, Any], *, channel: str, debug: bool
    ) -> None:
        if not debug:
            return
        log_item = self._make_trace_log(payload, channel)
        self.broadcast_from_thread(log_item)

    async def emit_trace_async(
        self, payload: dict[str, Any], *, channel: str, debug: bool
    ) -> None:
        if not debug:
            return
        await self.broadcast(self._make_trace_log(payload, channel))

    def _make_trace_log(self, payload: dict[str, Any], channel: str) -> dict[str, Any]:
        msg_type = str(payload.get("type", ""))
        speaker = str(payload.get("speaker", "") or "")
        segment_id = str(payload.get("segment_id", "") or "")
        revision = int(payload.get("revision", 0) or 0)
        en_len = len(str(payload.get("en", "") or ""))
        ar_len = len(str(payload.get("ar", "") or ""))
        return self.append_log(
            "debug",
            (
                "UI emit: "
                f"channel={channel}, type={msg_type}, speaker={speaker or '-'}, "
                f"segment_id={segment_id or '-'}, revision={revision}, "
                f"en_len={en_len}, ar_len={ar_len}, connections={len(self.connections)}"
            ),
        )

    # ── Utilities ─────────────────────────────────────────────────────────────

    @staticmethod
    def preview_text(value: str, max_len: int = 220) -> str:
        cleaned = " ".join(str(value or "").split())
        if len(cleaned) <= max_len:
            return cleaned
        return f"{cleaned[: max_len - 3]}..."
