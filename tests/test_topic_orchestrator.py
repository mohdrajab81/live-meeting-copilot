"""
Tests for definitions-only app.controller.topic_orchestrator.TopicOrchestrator.
"""

import threading
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.controller.topic_orchestrator import TopicOrchestrator


def _make_orch():
    orch = TopicOrchestrator(
        lock=threading.RLock(),
        broadcast=AsyncMock(),
        broadcast_log=AsyncMock(),
        get_finals=MagicMock(return_value=[]),
        preview_text=MagicMock(side_effect=lambda s: s),
    )
    return orch


def test_normalize_name():
    assert TopicOrchestrator._normalize_name("  Project   Update ") == "project update"
    assert TopicOrchestrator._normalize_name("") == ""


def test_configure_with_definitions_dedupes_and_normalizes():
    orch = _make_orch()
    out = orch.configure(
        agenda=[],
        enabled=True,
        allow_new_topics=True,
        interval_sec=120,
        definitions=[
            {"id": "A", "name": "Budget", "priority": "mandatory", "expected_duration_min": 5, "order": 4},
            {"id": "A", "name": "budget", "priority": "optional", "expected_duration_min": 2, "order": 0},
            {"name": "Timeline", "priority": "weird", "expected_duration_min": -5, "order": 1},
        ],
    )
    assert out["settings_saved"] is True
    assert [d["name"] for d in out["definitions"]] == ["Timeline", "Budget"]
    assert out["definitions"][0]["priority"] == "normal"
    assert out["definitions"][0]["expected_duration_min"] == 0
    assert out["definitions"][1]["priority"] == "high"
    assert len({d["id"] for d in out["definitions"]}) == 2
    assert out["agenda"] == ["Timeline", "Budget"]
    assert out["items"] == []


def test_configure_with_agenda_and_no_definitions_creates_stubs():
    orch = _make_orch()
    out = orch.configure(
        agenda=[" Risks ", "Risks", "Timeline"],
        enabled=False,
        allow_new_topics=False,
        interval_sec=60,
        definitions=None,
    )
    assert [d["name"] for d in out["definitions"]] == ["Risks", "Timeline"]
    assert out["agenda"] == ["Risks", "Timeline"]
    assert out["settings_saved"] is True


def test_configure_with_empty_definitions_and_no_agenda_clears_all():
    orch = _make_orch()
    orch.configure(
        agenda=[],
        enabled=False,
        allow_new_topics=False,
        interval_sec=60,
        definitions=[{"name": "One"}],
    )
    out = orch.configure(
        agenda=[],
        enabled=False,
        allow_new_topics=False,
        interval_sec=60,
        definitions=[],
    )
    assert out["definitions"] == []
    assert out["agenda"] == []


def test_payload_unlocked_has_compatibility_fields():
    orch = _make_orch()
    out = orch.payload_unlocked()
    assert out["configured"] is False
    assert out["settings_saved"] is False
    assert out["enabled"] is False
    assert out["allow_new_topics"] is False
    assert out["interval_sec"] == 60
    assert out["pending"] is False
    assert out["last_run_ts"] == 0.0
    assert out["last_final_index"] == 0
    assert out["last_error"] == ""
    assert out["definitions"] == []
    assert out["items"] == []
    assert out["runs"] == []


def test_clear_resets_definitions():
    orch = _make_orch()
    orch.configure(
        agenda=[],
        enabled=False,
        allow_new_topics=False,
        interval_sec=60,
        definitions=[{"name": "Ops"}],
    )
    orch.clear()
    out = orch.payload_unlocked()
    assert out["definitions"] == []
    assert out["agenda"] == []
    assert out["settings_saved"] is False


def test_clear_for_transcript_keeps_definitions_and_clears_items():
    orch = _make_orch()
    orch.configure(
        agenda=[],
        enabled=False,
        allow_new_topics=False,
        interval_sec=60,
        definitions=[{"name": "Ops"}],
    )
    orch.topics_items = [{"name": "Ops", "status": "active"}]
    orch.clear_for_transcript_unlocked()
    assert orch.topics_definitions != []
    assert orch.topics_items == []


@pytest.mark.asyncio
async def test_analyze_now_not_supported():
    orch = _make_orch()
    with pytest.raises(RuntimeError, match="disabled"):
        await orch.analyze_now()


def test_prepare_call_unlocked_returns_none_and_finalize_noop():
    orch = _make_orch()
    assert orch.prepare_call_unlocked(0.0, trigger="manual") is None
    assert orch.finalize_on_stop_unlocked() is None
