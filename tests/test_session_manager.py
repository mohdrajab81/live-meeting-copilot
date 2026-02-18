"""
Targeted tests for app.controller.session_manager.SessionManager.

Focuses on high-risk lifecycle paths:
- stop_async final topic flush behavior
- _do_finalize side effects and idempotency
- SDK self-stop finalization trigger from status event
"""

import threading
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.config import RuntimeConfig
from app.controller.session_manager import SessionManager


def _make_session_manager():
    lock = threading.RLock()
    speech = MagicMock()
    speech.stop_recognition.return_value = True
    speech.start_recognition.return_value = True

    translation = MagicMock()
    transcript_store = MagicMock()
    transcript_store.last_speech_activity_ts = 0.0
    transcript_store.get_finals_count.return_value = 0

    coach_orch = MagicMock()

    topic_orch = MagicMock()
    topic_orch.topics_enabled = True
    topic_orch.is_tracker_configured = True
    topic_orch.topics_pending = False
    topic_orch.topics_items = [{"name": "Alpha", "status": "active"}]
    topic_orch.payload_unlocked.side_effect = lambda: list(topic_orch.topics_items)
    topic_orch.prepare_call_unlocked.return_value = None
    topic_orch.run_update = AsyncMock()

    broadcast = AsyncMock()
    broadcast_from_thread = MagicMock()
    broadcast_log = AsyncMock()
    append_log = MagicMock(return_value={"type": "log", "level": "info", "message": "x", "ts": 0.0})
    emit_trace_from_thread = MagicMock()
    coach = MagicMock()

    mgr = SessionManager(
        lock=lock,
        speech=speech,
        translation=translation,
        transcript_store=transcript_store,
        coach_orch=coach_orch,
        topic_orch=topic_orch,
        broadcast=broadcast,
        broadcast_from_thread=broadcast_from_thread,
        broadcast_log=broadcast_log,
        append_log=append_log,
        emit_trace_from_thread=emit_trace_from_thread,
        get_config=lambda: RuntimeConfig(),
        coach=coach,
    )
    return mgr, speech, translation, coach_orch, topic_orch, broadcast_from_thread, coach


@pytest.mark.asyncio
async def test_stop_async_runs_topic_flush_when_call_available():
    mgr, speech, _, _, topic_orch, _, _ = _make_session_manager()
    topic_orch.prepare_call_unlocked.return_value = {"trigger": "auto", "chunk_turns": []}
    mgr._do_finalize = MagicMock()

    result = await mgr.stop_async()

    assert result is True
    speech.stop_recognition.assert_called_once()
    topic_orch.prepare_call_unlocked.assert_called_once()
    assert topic_orch.prepare_call_unlocked.call_args.kwargs.get("trigger") == "auto"
    topic_orch.run_update.assert_awaited_once_with({"trigger": "auto", "chunk_turns": []})
    mgr._do_finalize.assert_called_once()


@pytest.mark.asyncio
async def test_stop_async_skips_topic_flush_when_no_call():
    mgr, _, _, _, topic_orch, _, _ = _make_session_manager()
    topic_orch.prepare_call_unlocked.return_value = None
    mgr._do_finalize = MagicMock()

    result = await mgr.stop_async()

    assert result is True
    topic_orch.run_update.assert_not_awaited()
    mgr._do_finalize.assert_called_once()


def test_do_finalize_covers_active_topics_and_broadcasts_topics_update():
    mgr, _, translation, coach_orch, topic_orch, broadcast_from_thread, coach = _make_session_manager()
    topic_orch.topics_pending = True

    def _finalize_side_effect():
        for row in topic_orch.topics_items:
            if row.get("status") == "active":
                row["status"] = "covered"

    topic_orch.finalize_on_stop_unlocked.side_effect = _finalize_side_effect

    mgr._do_finalize()

    assert topic_orch.topics_pending is False
    assert topic_orch.topics_items[0]["status"] == "covered"
    coach_orch.reset_runtime_unlocked.assert_called_once_with(keep_history=True)
    translation.reset_unlocked.assert_called_once()
    coach.clear_conversation.assert_called_once()
    broadcast_from_thread.assert_called_once()
    payload = broadcast_from_thread.call_args.args[0]
    assert payload["type"] == "topics_update"
    assert payload["topics"][0]["status"] == "covered"


def test_do_finalize_is_idempotent():
    mgr, _, _, coach_orch, topic_orch, broadcast_from_thread, coach = _make_session_manager()

    mgr._do_finalize()
    mgr._do_finalize()

    assert topic_orch.finalize_on_stop_unlocked.call_count == 2
    assert coach_orch.reset_runtime_unlocked.call_count == 2
    assert coach.clear_conversation.call_count == 2
    assert broadcast_from_thread.call_count == 2


def test_status_event_running_to_stopped_triggers_finalize():
    mgr, _, _, _, _, broadcast_from_thread, _ = _make_session_manager()
    mgr.running = True
    mgr.status = "running"
    mgr.record_started_ts = time.time() - 1.0
    mgr._do_finalize = MagicMock()

    mgr.handle_speech_event({"type": "status", "status": "stopped", "running": False})

    assert mgr.running is False
    assert mgr.record_started_ts is None
    mgr._do_finalize.assert_called_once()
    broadcast_from_thread.assert_called_once()
    status_payload = broadcast_from_thread.call_args.args[0]
    assert status_payload["type"] == "status"
    assert status_payload["running"] is False
