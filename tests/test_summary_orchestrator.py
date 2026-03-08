"""
Unit tests for app.controller.summary_orchestrator.SummaryOrchestrator.

Covers: clear_unlocked, snapshot_unlocked, _build_transcript_text_unlocked,
_build_topic_breakdown_unlocked, run_summary (enabled/disabled/empty/success/error/pending-guard),
run_summary_now (guard checks).
"""

import threading
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import RuntimeConfig
from app.controller.summary_orchestrator import SummaryOrchestrator
from app.services.summary import SummaryResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_orch(
    *,
    is_configured: bool = True,
    summary_enabled: bool = True,
    finals: list | None = None,
    topic_defs: list | None = None,
    topic_items: list | None = None,
) -> tuple[SummaryOrchestrator, MagicMock, AsyncMock, AsyncMock]:
    lock = threading.RLock()
    summary_svc = MagicMock()
    summary_svc.is_configured = is_configured

    broadcast = AsyncMock()
    broadcast_log = AsyncMock()

    if finals is None:
        finals = []
    if topic_defs is None:
        topic_defs = []
    if topic_items is None:
        topic_items = []

    get_finals = MagicMock(return_value=finals)
    get_config = lambda: RuntimeConfig(summary_enabled=summary_enabled)
    # Return safe copies, as the real lambda does in AppController.
    get_topics = MagicMock(return_value=(list(topic_defs), list(topic_items)))

    orch = SummaryOrchestrator(
        lock=lock,
        summary_service=summary_svc,
        broadcast=broadcast,
        broadcast_log=broadcast_log,
        get_finals=get_finals,
        get_config=get_config,
        get_topics=get_topics,
    )
    return orch, summary_svc, broadcast, broadcast_log


def _make_result(**kwargs) -> SummaryResult:
    defaults = dict(
        executive_summary="Good meeting.",
        key_points=["point A", "point B"],
        action_items=[{"item": "Follow up", "owner": "Alice", "due_date_text": None, "due_date": None}],
        topic_key_points=[],
        keywords=[],
        entities=[],
        decisions_made=[],
        risks_and_blockers=[],
        key_terms_defined=[],
        metadata={"meeting_type": "General", "sentiment_arc": None},
        total_ms=1200,
        response_id="resp_xyz",
    )
    defaults.update(kwargs)
    return SummaryResult(**defaults)


# ---------------------------------------------------------------------------
# clear_unlocked
# ---------------------------------------------------------------------------

def test_clear_unlocked_resets_all_state():
    orch, _, _, _ = _make_orch()
    orch.summary_pending = True
    orch.summary_result = {"executive_summary": "old"}
    orch.summary_generated_ts = 1.0
    orch.summary_error = "prev error"
    orch.topic_breakdown = [{"name": "Intro"}]
    orch.agenda_adherence_pct = 80.0
    orch.meeting_insights = {"health": {"score_0_100": 90}}
    orch.keyword_index = [{"keyword": "alpha", "occurrences": 2}]

    orch.clear_unlocked()

    assert orch.summary_pending is False
    assert orch.summary_result is None
    assert orch.summary_generated_ts is None
    assert orch.summary_error == ""
    assert orch.topic_breakdown == []
    assert orch.agenda_adherence_pct is None
    assert orch.meeting_insights == {}
    assert orch.keyword_index == []


# ---------------------------------------------------------------------------
# snapshot_unlocked
# ---------------------------------------------------------------------------

def test_snapshot_unlocked_returns_correct_keys():
    orch, _, _, _ = _make_orch()
    snap = orch.snapshot_unlocked()
    assert "configured" in snap
    assert "pending" in snap
    assert "error" in snap
    assert "generated_ts" in snap
    assert "result" in snap
    assert "executive_summary" in snap
    assert "key_points" in snap
    assert "action_items" in snap
    assert "entities" in snap
    assert "meeting_insights" in snap
    assert "keyword_index" in snap


def test_snapshot_unlocked_configured_reflects_service():
    orch, svc, _, _ = _make_orch(is_configured=True)
    snap = orch.snapshot_unlocked()
    assert snap["configured"] is True

    svc.is_configured = False
    snap2 = orch.snapshot_unlocked()
    assert snap2["configured"] is False


def test_snapshot_unlocked_flattens_summary_result():
    orch, _, _, _ = _make_orch()
    orch.summary_result = {
        "executive_summary": "Summary text",
        "key_points": ["k1", "k2"],
        "action_items": [{"item": "do x", "owner": "A", "due_date_text": None, "due_date": None}],
    }
    snap = orch.snapshot_unlocked()
    assert snap["executive_summary"] == "Summary text"
    assert snap["key_points"] == ["k1", "k2"]
    assert len(snap["action_items"]) == 1


# ---------------------------------------------------------------------------
# _build_transcript_text_unlocked
# ---------------------------------------------------------------------------

def test_build_transcript_text_formats_correctly():
    ts = time.mktime(time.strptime("2026-02-26 10:30:00", "%Y-%m-%d %H:%M:%S"))
    finals = [
        {"ts": ts, "speaker_label": "You", "en": "Hello world"},
        {"ts": ts + 1, "speaker_label": "Remote", "en": "Hi there"},
    ]
    orch, _, _, _ = _make_orch(finals=finals)
    text = orch._build_transcript_text_unlocked()
    assert "You: Hello world" in text
    assert "Remote: Hi there" in text


def test_build_transcript_text_skips_empty_entries():
    ts = time.time()
    finals = [
        {"ts": ts, "speaker_label": "You", "en": ""},
        {"ts": ts, "speaker_label": "Remote", "en": "Real text"},
    ]
    orch, _, _, _ = _make_orch(finals=finals)
    text = orch._build_transcript_text_unlocked()
    assert "You:" not in text
    assert "Remote: Real text" in text


def test_build_transcript_text_caps_at_500_entries():
    ts = time.time()
    finals = [{"ts": ts, "speaker_label": "S", "en": f"line {i}"} for i in range(600)]
    orch, _, _, _ = _make_orch(finals=finals)
    text = orch._build_transcript_text_unlocked()
    lines = [l for l in text.splitlines() if l.strip()]
    assert len(lines) == 500


def test_build_transcript_text_uses_elapsed_timestamps():
    base_ts = 1000.0
    finals = [
        {"ts": base_ts, "start_ts": base_ts, "speaker_label": "You", "en": "Hello"},
        {"ts": base_ts + 90, "start_ts": base_ts + 90, "speaker_label": "Remote", "en": "Hi"},
    ]
    orch, _, _, _ = _make_orch(finals=finals)
    text = orch._build_transcript_text_unlocked()
    assert "[00:00] [id:U0001] You: Hello" in text
    assert "[01:30] [id:U0002] Remote: Hi" in text


def test_build_transcript_text_falls_back_to_ts_when_no_start_ts():
    base_ts = 1000.0
    finals = [
        {"ts": base_ts, "speaker_label": "You", "en": "Hello"},
        {"ts": base_ts + 60, "speaker_label": "Remote", "en": "Hi"},
    ]
    orch, _, _, _ = _make_orch(finals=finals)
    text = orch._build_transcript_text_unlocked()
    assert "[00:00] [id:U0001] You: Hello" in text
    assert "[01:00] [id:U0002] Remote: Hi" in text


def test_build_transcript_text_sorts_by_start_ts_for_dual_channel():
    # Simulate dual-mode: remote utterance arrives first (ts=10) but local
    # utterance started earlier (start_ts=7). Must appear in speech order
    # and timestamps must be distinct (no clamping collapse).
    finals = [
        {"ts": 10.0, "start_ts": 9.0, "speaker_label": "Remote", "en": "Second speaker"},
        {"ts": 11.0, "start_ts": 7.0, "speaker_label": "Local", "en": "First speaker"},
    ]
    orch, _, _, _ = _make_orch(finals=finals)
    text = orch._build_transcript_text_unlocked()
    # Ordering: local started at t=7, remote at t=9 → local must come first
    local_pos = text.index("First speaker")
    remote_pos = text.index("Second speaker")
    assert local_pos < remote_pos, "Local (earlier start_ts) must appear before Remote in prompt"
    # Timestamps: baseline=7, local=[00:00], remote=[00:02] — must be distinct
    assert "[00:00] [id:U0001] Local: First speaker" in text
    assert "[00:02] [id:U0002] Remote: Second speaker" in text


def test_build_transcript_text_returns_empty_for_no_finals():
    orch, _, _, _ = _make_orch(finals=[])
    assert orch._build_transcript_text_unlocked() == ""


# ---------------------------------------------------------------------------
# snapshot_unlocked — new fields
# ---------------------------------------------------------------------------

def test_snapshot_unlocked_includes_new_fields():
    orch, _, _, _ = _make_orch()
    orch.summary_result = {
        "executive_summary": "Good.",
        "key_points": [],
        "action_items": [],
        "entities": [{"type": "PERSON", "text": "Alice", "mentions": 1}],
        "decisions_made": ["Go ahead with plan"],
        "risks_and_blockers": ["Budget uncertain"],
        "key_terms_defined": [{"term": "RAG", "definition": "Retrieval Augmented Generation"}],
        "metadata": {"meeting_type": "Project Management", "sentiment_arc": "Positive"},
    }
    snap = orch.snapshot_unlocked()
    assert len(snap["entities"]) == 1
    assert snap["entities"][0]["type"] == "PERSON"
    assert snap["decisions_made"] == ["Go ahead with plan"]
    assert snap["risks_and_blockers"] == ["Budget uncertain"]
    assert len(snap["key_terms_defined"]) == 1
    assert snap["key_terms_defined"][0]["term"] == "RAG"
    assert snap["metadata"]["meeting_type"] == "Project Management"


def test_snapshot_unlocked_new_fields_default_empty_when_no_result():
    orch, _, _, _ = _make_orch()
    snap = orch.snapshot_unlocked()
    assert snap["entities"] == []
    assert snap["decisions_made"] == []
    assert snap["risks_and_blockers"] == []
    assert snap["key_terms_defined"] == []
    assert snap["metadata"] == {}
    assert snap["meeting_insights"] == {}
    assert snap["keyword_index"] == []


# ---------------------------------------------------------------------------
# run_summary — skip paths
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_summary_skips_when_disabled():
    orch, svc, broadcast, broadcast_log = _make_orch(summary_enabled=False)
    await orch.run_summary()
    svc.generate.assert_not_called()
    broadcast.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_summary_logs_warning_when_not_configured():
    orch, svc, broadcast, broadcast_log = _make_orch(is_configured=False)
    await orch.run_summary()
    svc.generate.assert_not_called()
    broadcast_log.assert_awaited_once()
    args = broadcast_log.await_args.args
    assert args[0] == "warning"


@pytest.mark.asyncio
async def test_run_summary_skips_when_already_pending():
    orch, svc, broadcast, broadcast_log = _make_orch()
    orch.summary_pending = True
    await orch.run_summary()
    svc.generate.assert_not_called()


@pytest.mark.asyncio
async def test_run_summary_skips_when_empty_transcript():
    orch, svc, broadcast, broadcast_log = _make_orch(finals=[])
    await orch.run_summary()
    svc.generate.assert_not_called()
    broadcast_log.assert_awaited()
    last_call = broadcast_log.await_args_list[-1]
    assert "empty" in last_call.args[1].lower()


# ---------------------------------------------------------------------------
# run_summary — success
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_summary_success_broadcasts_and_updates_state():
    ts = time.time()
    finals = [{"ts": ts, "speaker_label": "You", "en": "Hello world"}]
    orch, svc, broadcast, broadcast_log = _make_orch(finals=finals)
    result = _make_result()
    svc.generate.return_value = result

    await orch.run_summary()

    assert orch.summary_pending is False
    assert orch.summary_result is not None
    assert orch.summary_result["executive_summary"] == "Good meeting."
    assert orch.summary_generated_ts is not None
    assert orch.summary_error == ""
    broadcast.assert_awaited_once()
    payload = broadcast.await_args.args[0]
    assert payload["type"] == "summary"
    assert payload["executive_summary"] == "Good meeting."
    assert payload["key_points"] == ["point A", "point B"]
    assert len(payload["action_items"]) == 1
    assert isinstance(payload["meeting_insights"], dict)
    assert isinstance(payload["keyword_index"], list)


@pytest.mark.asyncio
async def test_run_summary_success_broadcasts_new_fields():
    ts = time.time()
    finals = [{"ts": ts, "speaker_label": "You", "en": "Hello world"}]
    orch, svc, broadcast, _ = _make_orch(finals=finals)
    result = _make_result(
        keywords=["education"],
        entities=[{"type": "PERSON", "text": "Alice", "mentions": 2}],
        decisions_made=["Deploy by Friday"],
        risks_and_blockers=["Team capacity low"],
        key_terms_defined=[{"term": "CI", "definition": "Continuous Integration"}],
        metadata={"meeting_type": "Project Management", "sentiment_arc": "Focused"},
    )
    svc.generate.return_value = result

    await orch.run_summary()

    payload = broadcast.await_args.args[0]
    assert payload["keywords"] == ["education"]
    assert payload["entities"][0]["text"] == "Alice"
    assert payload["decisions_made"] == ["Deploy by Friday"]
    assert payload["risks_and_blockers"] == ["Team capacity low"]
    assert len(payload["key_terms_defined"]) == 1
    assert payload["metadata"]["meeting_type"] == "Project Management"


@pytest.mark.asyncio
async def test_run_summary_success_logs_info():
    ts = time.time()
    finals = [{"ts": ts, "speaker_label": "You", "en": "Hello"}]
    orch, svc, broadcast, broadcast_log = _make_orch(finals=finals)
    svc.generate.return_value = _make_result()

    await orch.run_summary()

    log_calls = [c.args for c in broadcast_log.await_args_list]
    levels = [c[0] for c in log_calls]
    assert "info" in levels


@pytest.mark.asyncio
async def test_run_summary_builds_keyword_index_from_terms_and_transcript():
    ts = time.time()
    finals = [
        {"ts": ts, "speaker_label": "You", "en": "We should improve communication."},
        {"ts": ts + 4, "speaker_label": "Remote", "en": "Communication quality matters."},
    ]
    orch, svc, broadcast, _ = _make_orch(finals=finals)
    svc.generate.return_value = _make_result(
        key_terms_defined=[{"term": "Communication", "definition": "Exchange of ideas"}],
    )

    await orch.run_summary()

    payload = broadcast.await_args.args[0]
    keywords = payload["keyword_index"]
    assert any(str(row.get("keyword", "")).lower() == "communication" for row in keywords)


@pytest.mark.asyncio
async def test_run_summary_builds_keyword_index_from_entities_and_transcript():
    ts = time.time()
    finals = [
        {"ts": ts, "speaker_label": "You", "en": "Alice discussed rollout in London."},
        {"ts": ts + 3, "speaker_label": "Remote", "en": "London risks were reviewed by Alice."},
    ]
    orch, svc, broadcast, _ = _make_orch(finals=finals)
    svc.generate.return_value = _make_result(
        key_terms_defined=[],
        keywords=[],
        entities=[{"type": "PERSON", "text": "Alice", "mentions": 2}],
    )

    await orch.run_summary()

    payload = broadcast.await_args.args[0]
    keywords = payload["keyword_index"]
    assert any(str(row.get("keyword", "")).lower() == "alice" for row in keywords)


# ---------------------------------------------------------------------------
# run_summary — error
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_summary_error_broadcasts_error_type():
    ts = time.time()
    finals = [{"ts": ts, "speaker_label": "You", "en": "Some text"}]
    orch, svc, broadcast, broadcast_log = _make_orch(finals=finals)
    svc.generate.side_effect = RuntimeError("Azure timeout")

    await orch.run_summary()

    assert orch.summary_pending is False
    assert "Azure timeout" in orch.summary_error
    broadcast.assert_awaited_once()
    err_payload = broadcast.await_args.args[0]
    assert err_payload["type"] == "summary"
    assert "Azure timeout" in err_payload["error"]
    assert err_payload["generated_ts"] is None


# ---------------------------------------------------------------------------
# run_summary_now
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_summary_now_raises_when_pending():
    orch, _, _, _ = _make_orch()
    orch.summary_pending = True
    with pytest.raises(ValueError, match="in progress"):
        await orch.run_summary_now()


@pytest.mark.asyncio
async def test_run_summary_now_raises_when_not_configured():
    orch, _, _, _ = _make_orch(is_configured=False)
    with pytest.raises(ValueError, match="not configured"):
        await orch.run_summary_now()


@pytest.mark.asyncio
async def test_run_summary_now_returns_snapshot():
    ts = time.time()
    finals = [{"ts": ts, "speaker_label": "You", "en": "Hello"}]
    orch, svc, _, _ = _make_orch(finals=finals)
    svc.generate.return_value = _make_result()

    result = await orch.run_summary_now()

    assert isinstance(result, dict)
    assert "configured" in result
    assert "pending" in result


# ---------------------------------------------------------------------------
# _build_topic_breakdown_unlocked
# ---------------------------------------------------------------------------

def test_breakdown_empty_when_no_get_topics():
    """get_topics=None → no breakdown, no adherence."""
    lock = threading.RLock()
    svc = MagicMock()
    svc.is_configured = True
    orch = SummaryOrchestrator(
        lock=lock,
        summary_service=svc,
        broadcast=AsyncMock(),
        broadcast_log=AsyncMock(),
        get_finals=MagicMock(return_value=[]),
        get_config=lambda: RuntimeConfig(),
        get_topics=None,
    )
    bd, adh = orch._build_topic_breakdown_unlocked()
    assert bd == []
    assert adh is None


def test_breakdown_empty_when_no_items():
    orch, _, _, _ = _make_orch(topic_defs=[{"name": "Intro", "expected_duration_min": 5}], topic_items=[])
    bd, adh = orch._build_topic_breakdown_unlocked()
    assert bd == []
    assert adh is None


def test_breakdown_skips_nameless_items():
    items = [{"name": "", "status": "covered", "time_seconds": 60}]
    orch, _, _, _ = _make_orch(topic_items=items)
    bd, _ = orch._build_topic_breakdown_unlocked()
    assert bd == []


def test_breakdown_planned_none_when_not_in_definitions():
    """Topic in items but no matching definition → planned_min=None, over_under_min=None."""
    items = [{"name": "Ad-hoc", "status": "covered", "time_seconds": 120}]
    orch, _, _, _ = _make_orch(topic_items=items)
    bd, adh = orch._build_topic_breakdown_unlocked()
    assert len(bd) == 1
    assert bd[0]["planned_min"] is None
    assert bd[0]["over_under_min"] is None
    assert bd[0]["actual_min"] == 2.0
    assert adh is None  # no planned topics → adherence undefined


def test_breakdown_planned_none_when_definition_has_zero_duration():
    """expected_duration_min=0 is treated as 'not set' (None)."""
    defs = [{"name": "Intro", "expected_duration_min": 0}]
    items = [{"name": "Intro", "status": "covered", "time_seconds": 180}]
    orch, _, _, _ = _make_orch(topic_defs=defs, topic_items=items)
    bd, adh = orch._build_topic_breakdown_unlocked()
    assert bd[0]["planned_min"] is None
    assert bd[0]["over_under_min"] is None
    assert adh is None


def test_breakdown_skipped_derived_when_planned_and_not_started():
    """planned > 0 and actual == 0 and status == not_started → status becomes 'skipped'."""
    defs = [{"name": "Q&A", "expected_duration_min": 10}]
    items = [{"name": "Q&A", "status": "not_started", "time_seconds": 0}]
    orch, _, _, _ = _make_orch(topic_defs=defs, topic_items=items)
    bd, _ = orch._build_topic_breakdown_unlocked()
    assert bd[0]["status"] == "skipped"
    assert bd[0]["actual_min"] == 0.0
    assert bd[0]["planned_min"] == 10


def test_breakdown_not_started_kept_when_no_planned():
    """status not_started is NOT flipped to skipped when planned_min is None (no plan)."""
    items = [{"name": "Freestyle", "status": "not_started", "time_seconds": 0}]
    orch, _, _, _ = _make_orch(topic_items=items)
    bd, _ = orch._build_topic_breakdown_unlocked()
    assert bd[0]["status"] == "not_started"


def test_breakdown_over_when_actual_exceeds_planned():
    """planned > 0, actual > planned → positive over_under_min."""
    defs = [{"name": "Deep Dive", "expected_duration_min": 10}]
    items = [{"name": "Deep Dive", "status": "covered", "time_seconds": 900}]  # 15 min
    orch, _, _, _ = _make_orch(topic_defs=defs, topic_items=items)
    bd, _ = orch._build_topic_breakdown_unlocked()
    assert bd[0]["actual_min"] == 15.0
    assert bd[0]["planned_min"] == 10
    assert bd[0]["over_under_min"] == 5.0   # positive → over budget


def test_breakdown_under_when_actual_below_planned():
    """planned > 0, actual < planned → negative over_under_min."""
    defs = [{"name": "Q&A", "expected_duration_min": 15}]
    items = [{"name": "Q&A", "status": "covered", "time_seconds": 360}]  # 6 min
    orch, _, _, _ = _make_orch(topic_defs=defs, topic_items=items)
    bd, _ = orch._build_topic_breakdown_unlocked()
    assert bd[0]["actual_min"] == 6.0
    assert bd[0]["planned_min"] == 15
    assert bd[0]["over_under_min"] == -9.0  # negative → under budget


def test_breakdown_exact_match_over_under_is_zero():
    """planned == actual → over_under_min == 0.0."""
    defs = [{"name": "Intro", "expected_duration_min": 5}]
    items = [{"name": "Intro", "status": "covered", "time_seconds": 300}]  # exactly 5 min
    orch, _, _, _ = _make_orch(topic_defs=defs, topic_items=items)
    bd, _ = orch._build_topic_breakdown_unlocked()
    assert bd[0]["over_under_min"] == 0.0


# ---------------------------------------------------------------------------
# Adherence formula
# ---------------------------------------------------------------------------

def test_adherence_null_when_no_planned_topics():
    items = [{"name": "Intro", "status": "covered", "time_seconds": 120}]
    orch, _, _, _ = _make_orch(topic_items=items)
    _, adh = orch._build_topic_breakdown_unlocked()
    assert adh is None


def test_adherence_100_when_all_within_budget():
    """Both topics used exactly their budget → 100%."""
    defs = [
        {"name": "A", "expected_duration_min": 10},
        {"name": "B", "expected_duration_min": 10},
    ]
    items = [
        {"name": "A", "status": "covered", "time_seconds": 600},  # 10 min
        {"name": "B", "status": "covered", "time_seconds": 600},  # 10 min
    ]
    orch, _, _, _ = _make_orch(topic_defs=defs, topic_items=items)
    _, adh = orch._build_topic_breakdown_unlocked()
    assert adh == 100.0


def test_adherence_continuous_formula():
    """
    Two planned topics:
      A: actual=8 / planned=10  → min(8,10)=8
      B: actual=12 / planned=10 → min(12,10)=10
    adherence = (8+10)/(10+10)*100 = 90%
    """
    defs = [
        {"name": "A", "expected_duration_min": 10},
        {"name": "B", "expected_duration_min": 10},
    ]
    items = [
        {"name": "A", "status": "covered", "time_seconds": 480},   # 8 min
        {"name": "B", "status": "covered", "time_seconds": 720},   # 12 min
    ]
    orch, _, _, _ = _make_orch(topic_defs=defs, topic_items=items)
    _, adh = orch._build_topic_breakdown_unlocked()
    assert adh == 90.0


def test_adherence_skipped_topics_count_as_zero_usage():
    """
    Skipped topic (actual=0, planned=10) contributes 0 to numerator.
    A: actual=10, planned=10 → min=10
    B: actual=0,  planned=10 → min=0  (skipped)
    adherence = (10+0)/(10+10)*100 = 50%
    """
    defs = [
        {"name": "A", "expected_duration_min": 10},
        {"name": "B", "expected_duration_min": 10},
    ]
    items = [
        {"name": "A", "status": "covered", "time_seconds": 600},
        {"name": "B", "status": "not_started", "time_seconds": 0},
    ]
    orch, _, _, _ = _make_orch(topic_defs=defs, topic_items=items)
    _, adh = orch._build_topic_breakdown_unlocked()
    assert adh == 50.0


def test_adherence_unplanned_topics_excluded_from_formula():
    """Topics without a definition (planned_min=None) do not affect adherence."""
    defs = [{"name": "Planned", "expected_duration_min": 10}]
    items = [
        {"name": "Planned", "status": "covered", "time_seconds": 600},   # 10/10 min
        {"name": "Unplanned", "status": "covered", "time_seconds": 1200}, # 20 min, no plan
    ]
    orch, _, _, _ = _make_orch(topic_defs=defs, topic_items=items)
    _, adh = orch._build_topic_breakdown_unlocked()
    assert adh == 100.0  # only planned topic at exactly budget


def test_adherence_counts_planned_definitions_with_no_item():
    """
    A planned definition with no corresponding item must be treated as skipped
    (actual=0) so the denominator reflects the full planned agenda.
    Only A has an item; B is defined but missing from items entirely.
      A: actual=10/planned=10 → min=10
      B: actual=0 /planned=10 → min=0  (synthetic skipped)
    adherence = (10+0)/(10+10)*100 = 50%  (not 100% which wrong code would give)
    """
    defs = [
        {"name": "A", "expected_duration_min": 10},
        {"name": "B", "expected_duration_min": 10},
    ]
    items = [
        {"name": "A", "status": "covered", "time_seconds": 600},
        # B intentionally absent from items
    ]
    orch, _, _, _ = _make_orch(topic_defs=defs, topic_items=items)
    bd, adh = orch._build_topic_breakdown_unlocked()
    names = [t["name"] for t in bd]
    assert "B" in names, "Synthetic skipped entry must be added for missing planned topic"
    b_entry = next(t for t in bd if t["name"] == "B")
    assert b_entry["status"] == "skipped"
    assert b_entry["actual_min"] == 0.0
    assert b_entry["over_under_min"] == -10.0
    assert adh == 50.0


def test_breakdown_case_insensitive_definition_lookup():
    """Item name 'intro' must match definition 'Intro' (case drift tolerance)."""
    defs = [{"name": "Intro", "expected_duration_min": 5}]
    items = [{"name": "intro", "status": "covered", "time_seconds": 300}]
    orch, _, _, _ = _make_orch(topic_defs=defs, topic_items=items)
    bd, adh = orch._build_topic_breakdown_unlocked()
    assert len(bd) == 1
    assert bd[0]["planned_min"] == 5, "Case-insensitive match must resolve planned_min"
    assert bd[0]["over_under_min"] == 0.0
    assert adh == 100.0


# ---------------------------------------------------------------------------
# snapshot_unlocked — Phase 2 fields
# ---------------------------------------------------------------------------

def test_snapshot_includes_topic_breakdown_and_adherence():
    orch, _, _, _ = _make_orch()
    orch.topic_breakdown = [{"name": "Intro", "actual_min": 5.0, "planned_min": 5, "status": "covered", "over_under_min": 0.0}]
    orch.agenda_adherence_pct = 100.0
    snap = orch.snapshot_unlocked()
    assert len(snap["topic_breakdown"]) == 1
    assert snap["topic_breakdown"][0]["name"] == "Intro"
    assert snap["agenda_adherence_pct"] == 100.0


def test_snapshot_topic_breakdown_defaults_empty():
    orch, _, _, _ = _make_orch()
    snap = orch.snapshot_unlocked()
    assert snap["topic_breakdown"] == []
    assert snap["agenda_adherence_pct"] is None


# ---------------------------------------------------------------------------
# run_summary — topic breakdown included in broadcast payload
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_summary_broadcasts_topic_breakdown():
    ts = time.time()
    finals = [{"ts": ts, "speaker_label": "You", "en": "Hello"}]
    defs = [{"name": "Intro", "expected_duration_min": 5}]
    items = [{"name": "Intro", "status": "covered", "time_seconds": 600}]
    orch, svc, broadcast, _ = _make_orch(finals=finals, topic_defs=defs, topic_items=items)
    svc.generate.return_value = _make_result(
        topic_key_points=[
            {
                "topic_name": "Intro",
                "estimated_duration_minutes": 5.0,
                "origin": "Agenda",
                "key_points": [],
            }
        ]
    )

    await orch.run_summary()

    broadcast.assert_awaited_once()
    assert broadcast.await_args is not None
    payload = broadcast.await_args.args[0]
    assert "topic_breakdown" in payload
    assert len(payload["topic_breakdown"]) == 1
    assert payload["topic_breakdown"][0]["name"] == "Intro"
    assert payload["agenda_adherence_pct"] == 0.0


@pytest.mark.asyncio
async def test_run_summary_topic_breakdown_empty_when_no_topics():
    ts = time.time()
    finals = [{"ts": ts, "speaker_label": "You", "en": "Hello"}]
    orch, svc, broadcast, _ = _make_orch(finals=finals)
    svc.generate.return_value = _make_result()

    await orch.run_summary()

    broadcast.assert_awaited_once()
    assert broadcast.await_args is not None
    payload = broadcast.await_args.args[0]
    assert payload["topic_breakdown"] == []
    assert payload["agenda_adherence_pct"] is None


@pytest.mark.asyncio
async def test_run_summary_fallbacks_to_topic_groups_when_no_tracked_topics():
    ts = time.time()
    finals = [{"ts": ts, "speaker_label": "You", "en": "Hello"}]
    orch, svc, broadcast, _ = _make_orch(finals=finals)
    svc.generate.return_value = _make_result(
        topic_key_points=[
            {
                "topic_name": "Introduction",
                "estimated_duration_minutes": 3.5,
                "origin": "Inferred",
                "key_points": ["Context set"],
            }
        ]
    )

    await orch.run_summary()

    payload = broadcast.await_args.args[0]
    assert payload["topic_key_points"][0]["topic_name"] == "Introduction"
    assert len(payload["topic_breakdown"]) == 1
    assert payload["topic_breakdown"][0]["name"] == "Introduction"
    assert payload["topic_breakdown"][0]["status"] == "inferred"
    assert payload["topic_breakdown"][0]["actual_min"] == 0.0
    assert payload["agenda_adherence_pct"] is None


@pytest.mark.asyncio
async def test_run_summary_computes_topic_minutes_from_utterance_ids():
    base = time.time()
    finals = [
        {
            "ts": base + 5.0,
            "start_ts": base + 0.0,
            "end_ts": base + 30.0,
            "duration_sec": 30.0,
            "speaker_label": "You",
            "en": "First point",
        },
        {
            "ts": base + 95.0,
            "start_ts": base + 30.0,
            "end_ts": base + 120.0,
            "duration_sec": 90.0,
            "speaker_label": "Remote",
            "en": "Second point",
        },
    ]
    orch, svc, broadcast, _ = _make_orch(finals=finals)
    svc.generate.return_value = _make_result(
        topic_key_points=[
            {
                "topic_name": "Main Discussion",
                "estimated_duration_minutes": None,
                "utterance_ids": ["U0001", "U0002"],
                "origin": "Inferred",
                "key_points": ["k1"],
            }
        ]
    )

    await orch.run_summary()

    payload = broadcast.await_args.args[0]
    assert payload["topic_key_points"][0]["estimated_duration_minutes"] == 2.0
    assert payload["topic_breakdown"][0]["name"] == "Main Discussion"
    assert payload["topic_breakdown"][0]["actual_min"] == 2.0


@pytest.mark.asyncio
async def test_run_summary_repairs_topic_coverage_and_corrects_origin():
    base = time.time()
    finals = [
        {
            "ts": base + 1.0,
            "start_ts": base + 0.0,
            "end_ts": base + 10.0,
            "duration_sec": 10.0,
            "speaker_label": "Remote",
            "en": "Topic one.",
        },
        {
            "ts": base + 12.0,
            "start_ts": base + 10.0,
            "end_ts": base + 20.0,
            "duration_sec": 10.0,
            "speaker_label": "Remote",
            "en": "Greeting filler.",
        },
        {
            "ts": base + 25.0,
            "start_ts": base + 20.0,
            "end_ts": base + 30.0,
            "duration_sec": 10.0,
            "speaker_label": "Remote",
            "en": "Marketing update.",
        },
        {
            "ts": base + 38.0,
            "start_ts": base + 30.0,
            "end_ts": base + 40.0,
            "duration_sec": 10.0,
            "speaker_label": "Remote",
            "en": "Operations next steps.",
        },
    ]
    defs = [
        {"name": "Project Status", "expected_duration_min": 2},
        {"name": "Marketing campaign", "expected_duration_min": 1},
    ]
    orch, svc, broadcast, _ = _make_orch(finals=finals, topic_defs=defs)
    svc.generate.return_value = _make_result(
        topic_key_points=[
            {
                "topic_name": "Project Status",
                "estimated_duration_minutes": None,
                "utterance_ids": ["U0001"],
                "origin": "Agenda",
                "key_points": ["k1"],
            },
            {
                "topic_name": "Marketing campaign",
                "estimated_duration_minutes": None,
                "utterance_ids": ["U0003"],
                "origin": "Agenda",
                "key_points": ["k2"],
            },
            {
                "topic_name": "Team operations and next steps",
                "estimated_duration_minutes": None,
                "utterance_ids": ["U0004"],
                "origin": "Agenda",
                "key_points": ["k3"],
            },
        ]
    )

    await orch.run_summary()

    payload = broadcast.await_args.args[0]
    topic_groups = payload["topic_key_points"]
    assert topic_groups[0]["utterance_ids"] == ["U0001", "U0002"]
    assert topic_groups[0]["origin"] == "Agenda"
    assert topic_groups[1]["utterance_ids"] == ["U0003"]
    assert topic_groups[1]["origin"] == "Agenda"
    assert topic_groups[2]["utterance_ids"] == ["U0004"]
    assert topic_groups[2]["origin"] == "Inferred"
    assert all(group["topic_name"] != "Unassigned / Other" for group in topic_groups)


# ---------------------------------------------------------------------------
# get_topics snapshot safety
# ---------------------------------------------------------------------------

def test_get_topics_returns_copies_not_mutable_reference():
    """get_topics must return independent copies; mutation of the returned list
    must not affect subsequent calls."""
    original_items = [{"name": "Intro", "status": "covered", "time_seconds": 60}]
    orch, _, _, _ = _make_orch(topic_items=original_items)
    # Rebuild get_topics as a real closure returning the same list each time.
    shared_list = [{"name": "Intro", "status": "covered", "time_seconds": 60}]
    orch._get_topics = lambda: ([], list(shared_list))

    _, items1 = orch._get_topics()
    items1.append({"name": "Injected", "status": "not_started", "time_seconds": 0})
    _, items2 = orch._get_topics()

    assert len(items2) == 1, "Mutation of first return must not affect second call"
