"""
Tests for app.controller.broadcast_service.BroadcastService.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.controller.broadcast_service import BroadcastService


@pytest.fixture
def svc():
    return BroadcastService()


# ---------------------------------------------------------------------------
# append_log / get_logs / clear_logs
# ---------------------------------------------------------------------------

class TestLogging:
    def test_append_log_returns_correct_structure(self, svc):
        item = svc.append_log("info", "hello world")
        assert item["type"] == "log"
        assert item["level"] == "info"
        assert item["message"] == "hello world"
        assert "ts" in item

    def test_get_logs_returns_appended_items(self, svc):
        svc.append_log("warning", "msg1")
        svc.append_log("error", "msg2")
        logs = svc.get_logs()
        assert len(logs) == 2
        assert logs[0]["message"] == "msg1"
        assert logs[1]["message"] == "msg2"

    def test_append_log_caps_at_1000(self, svc):
        for i in range(1010):
            svc.append_log("debug", f"msg {i}")
        assert len(svc.get_logs()) == 1000

    def test_cap_keeps_newest_entries(self, svc):
        for i in range(1010):
            svc.append_log("debug", f"msg {i}")
        logs = svc.get_logs()
        assert logs[0]["message"] == "msg 10"   # oldest kept
        assert logs[-1]["message"] == "msg 1009"  # newest

    def test_get_logs_returns_copy(self, svc):
        svc.append_log("info", "a")
        logs = svc.get_logs()
        logs.clear()
        # Original must be unaffected
        assert len(svc.get_logs()) == 1

    def test_clear_logs_empties_buffer(self, svc):
        svc.append_log("info", "x")
        svc.clear_logs()
        assert svc.get_logs() == []

    def test_clear_then_append_works(self, svc):
        svc.append_log("info", "first")
        svc.clear_logs()
        svc.append_log("info", "second")
        logs = svc.get_logs()
        assert len(logs) == 1
        assert logs[0]["message"] == "second"


# ---------------------------------------------------------------------------
# preview_text
# ---------------------------------------------------------------------------

class TestPreviewText:
    def test_short_text_unchanged(self):
        assert BroadcastService.preview_text("hello") == "hello"

    def test_long_text_truncated(self):
        long = "a" * 300
        result = BroadcastService.preview_text(long)
        assert result.endswith("...")
        assert len(result) == 220  # preview_text returns exactly max_len total

    def test_custom_max_len(self):
        result = BroadcastService.preview_text("abcdef", 4)
        assert result == "a..."
        assert len(result) == 4

    def test_whitespace_collapsed(self):
        result = BroadcastService.preview_text("  hello   world  ")
        assert result == "hello world"

    def test_empty_string(self):
        assert BroadcastService.preview_text("") == ""

    def test_none_like_coercion(self):
        assert BroadcastService.preview_text(None) == ""  # type: ignore[arg-type]

    def test_exact_max_len_not_truncated(self):
        text = "a" * 220
        result = BroadcastService.preview_text(text)
        assert result == text
        assert not result.endswith("...")


# ---------------------------------------------------------------------------
# broadcast_from_thread  (fire-and-forget path)
# ---------------------------------------------------------------------------

class TestBroadcastFromThread:
    def test_no_loop_does_nothing(self, svc):
        svc.loop = None
        svc.broadcast_from_thread({"type": "test"})  # must not raise

    def test_loop_not_running_does_nothing(self, svc):
        mock_loop = MagicMock()
        mock_loop.is_running.return_value = False
        svc.loop = mock_loop
        svc.broadcast_from_thread({"type": "test"})  # must not raise


# ---------------------------------------------------------------------------
# emit_trace_from_thread / emit_trace_async  (debug guard)
# ---------------------------------------------------------------------------

class TestEmitTrace:
    def test_emit_trace_from_thread_skips_when_debug_false(self, svc):
        svc.loop = None  # ensure no dispatch
        before = len(svc.get_logs())
        svc.emit_trace_from_thread({"type": "partial"}, channel="test", debug=False)
        assert len(svc.get_logs()) == before

    def test_emit_trace_from_thread_appends_log_when_debug_true(self, svc):
        # Loop not set so fire-and-forget won't actually send,
        # but append_log is called before dispatch.
        before = len(svc.get_logs())
        svc.emit_trace_from_thread({"type": "partial", "speaker": "X"}, channel="test", debug=True)
        assert len(svc.get_logs()) == before + 1
        log = svc.get_logs()[-1]
        assert "channel=test" in log["message"]

    async def test_emit_trace_async_skips_when_debug_false(self, svc):
        before = len(svc.get_logs())
        await svc.emit_trace_async({"type": "partial"}, channel="test", debug=False)
        assert len(svc.get_logs()) == before


# ---------------------------------------------------------------------------
# connect / disconnect
# ---------------------------------------------------------------------------

class TestConnections:
    def test_disconnect_unknown_ws_does_not_raise(self, svc):
        ws = MagicMock()
        svc.disconnect(ws)  # must not raise — uses discard

    def test_disconnect_removes_connection(self, svc):
        ws = MagicMock()
        svc.connections.add(ws)
        assert ws in svc.connections
        svc.disconnect(ws)
        assert ws not in svc.connections


# ---------------------------------------------------------------------------
# broadcast (async — uses asyncio)
# ---------------------------------------------------------------------------

class TestBroadcast:
    async def test_broadcast_sends_to_all_connections(self, svc):
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        svc.connections = {ws1, ws2}
        await svc.broadcast({"type": "test", "value": 1})
        ws1.send_text.assert_awaited_once()
        ws2.send_text.assert_awaited_once()

    async def test_broadcast_removes_dead_connection(self, svc):
        ws_good = AsyncMock()
        ws_dead = AsyncMock()
        ws_dead.send_text.side_effect = Exception("disconnected")
        svc.connections = {ws_good, ws_dead}
        await svc.broadcast({"type": "test"})
        assert ws_dead not in svc.connections
        assert ws_good in svc.connections

    async def test_broadcast_log_appends_and_sends(self, svc):
        ws = AsyncMock()
        svc.connections = {ws}
        await svc.broadcast_log("info", "hello broadcast")
        logs = svc.get_logs()
        assert any(l["message"] == "hello broadcast" for l in logs)
        ws.send_text.assert_awaited_once()
