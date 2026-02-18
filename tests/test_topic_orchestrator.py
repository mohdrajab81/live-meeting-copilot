"""
Tests for app.controller.topic_orchestrator.TopicOrchestrator.

This is the most complex module — tests cover normalisation helpers, configure(),
prepare_call_unlocked(), merge logic, time allocation, auto-cover, and lifecycle
actions (clear, finalize_on_stop, analyze_now error cases).
"""

import threading
import time
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.controller.topic_orchestrator import TopicOrchestrator


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def _make_tracker(is_configured=False):
    tracker = MagicMock()
    tracker.is_configured = is_configured
    tracker.clear_conversation = MagicMock()
    return tracker


def _make_orchestrator(tracker=None, finals=None):
    lock = threading.RLock()
    tracker = tracker or _make_tracker()
    finals_list = list(finals or [])
    orch = TopicOrchestrator(
        lock=lock,
        topic_tracker=tracker,
        broadcast=AsyncMock(),
        broadcast_log=AsyncMock(),
        get_finals=lambda: finals_list,
        preview_text=lambda text, n=220: text[:n],
    )
    return orch


def _final(en="hello world", ts=None, speaker="default", speaker_label="Speaker"):
    ts = ts or time.time()
    return {
        "en": en,
        "ar": "",
        "speaker": speaker,
        "speaker_label": speaker_label,
        "segment_id": "seg-1",
        "revision": 1,
        "ts": ts,
        "start_ts": ts - 5.0,
    }


def _configured_orch(agenda=None, allow_new=True, finals=None):
    """Return an orchestrator that has been configure()d and is ready to run."""
    tracker = _make_tracker(is_configured=True)
    orch = _make_orchestrator(tracker=tracker, finals=finals or [])
    orch.configure(
        agenda=agenda or ["Alpha", "Beta"],
        enabled=True,
        allow_new_topics=allow_new,
        interval_sec=60,
        window_sec=90,
    )
    return orch


# ===========================================================================
# 1. Pure normalization helpers
# ===========================================================================

class TestNormalizeName:
    def test_lowercases(self):
        assert TopicOrchestrator._normalize_name("Hello World") == "hello world"

    def test_strips_whitespace(self):
        assert TopicOrchestrator._normalize_name("  foo  ") == "foo"

    def test_collapses_internal_whitespace(self):
        assert TopicOrchestrator._normalize_name("a  b   c") == "a b c"

    def test_empty_string(self):
        assert TopicOrchestrator._normalize_name("") == ""

    def test_none_coercion(self):
        assert TopicOrchestrator._normalize_name(None) == ""  # type: ignore


class TestIsUsableNewName:
    def test_valid_name(self):
        assert TopicOrchestrator._is_usable_new_name("Project Roadmap")

    def test_single_char_too_short(self):
        assert not TopicOrchestrator._is_usable_new_name("a")

    def test_exactly_two_chars_ok(self):
        assert TopicOrchestrator._is_usable_new_name("ab")

    def test_too_long(self):
        assert not TopicOrchestrator._is_usable_new_name("x" * 81)

    def test_exactly_80_chars_ok(self):
        assert TopicOrchestrator._is_usable_new_name("a" * 80)

    @pytest.mark.parametrize("name", ["topic", "new topic", "unknown", "other", "misc", "miscellaneous"])
    def test_reserved_words_rejected(self, name):
        assert not TopicOrchestrator._is_usable_new_name(name)

    def test_reserved_word_case_insensitive(self):
        assert not TopicOrchestrator._is_usable_new_name("TOPIC")


class TestNormalizeStatus:
    @pytest.mark.parametrize("value,expected", [
        ("active", "active"),
        ("covered", "covered"),
        ("not_started", "not_started"),
        ("ACTIVE", "active"),
        ("Covered", "covered"),
    ])
    def test_valid_statuses(self, value, expected):
        assert TopicOrchestrator._normalize_status(value) == expected

    def test_invalid_returns_default(self):
        assert TopicOrchestrator._normalize_status("bad_value") == "not_started"

    def test_none_returns_default(self):
        assert TopicOrchestrator._normalize_status(None) == "not_started"

    def test_custom_default(self):
        assert TopicOrchestrator._normalize_status("bad", default="active") == "active"


class TestNormalizeComments:
    def test_short_text_unchanged(self):
        assert TopicOrchestrator._normalize_comments("hello") == "hello"

    def test_truncated_at_max_chars(self):
        text = "a" * 150
        result = TopicOrchestrator._normalize_comments(text, max_chars=100)
        assert len(result) <= 100

    def test_empty_input(self):
        assert TopicOrchestrator._normalize_comments("") == ""

    def test_none_input(self):
        assert TopicOrchestrator._normalize_comments(None) == ""  # type: ignore

    def test_whitespace_collapsed(self):
        assert TopicOrchestrator._normalize_comments("  hello   world  ") == "hello world"


# ===========================================================================
# 2. _normalize_definition / _normalize_definitions
# ===========================================================================

class TestNormalizeDefinition:
    def setup_method(self):
        self.orch = _make_orchestrator()

    def test_none_returns_none(self):
        assert self.orch._normalize_definition(None) is None  # type: ignore

    def test_non_dict_returns_none(self):
        assert self.orch._normalize_definition("not a dict") is None  # type: ignore

    def test_empty_name_returns_none(self):
        assert self.orch._normalize_definition({"name": ""}) is None

    def test_whitespace_name_returns_none(self):
        assert self.orch._normalize_definition({"name": "   "}) is None

    def test_valid_returns_dict(self):
        result = self.orch._normalize_definition({"name": "Budget Review"})
        assert result is not None
        assert result["name"] == "Budget Review"

    def test_auto_generates_slug_id(self):
        result = self.orch._normalize_definition({"name": "Project Kickoff"})
        assert result["id"] == "project-kickoff"

    def test_explicit_id_preserved(self):
        result = self.orch._normalize_definition({"name": "T", "id": "my-id"})
        assert result["id"] == "my-id"

    def test_mandatory_priority_maps_to_high(self):
        result = self.orch._normalize_definition({"name": "T", "priority": "mandatory"})
        assert result["priority"] == "high"

    def test_optional_priority_maps_to_normal(self):
        result = self.orch._normalize_definition({"name": "T", "priority": "optional"})
        assert result["priority"] == "normal"

    def test_invalid_priority_maps_to_normal(self):
        result = self.orch._normalize_definition({"name": "T", "priority": "super"})
        assert result["priority"] == "normal"

    def test_duration_clamped_at_600(self):
        result = self.orch._normalize_definition({"name": "T", "expected_duration_min": 999})
        assert result["expected_duration_min"] == 600

    def test_negative_duration_clamped_to_zero(self):
        result = self.orch._normalize_definition({"name": "T", "expected_duration_min": -5})
        assert result["expected_duration_min"] == 0


class TestNormalizeDefinitions:
    def setup_method(self):
        self.orch = _make_orchestrator()

    def test_deduplicates_by_name(self):
        defs = [{"name": "Budget"}, {"name": "Budget"}, {"name": "Timeline"}]
        result = self.orch._normalize_definitions(defs)
        names = [r["name"] for r in result]
        assert names.count("Budget") == 1
        assert len(result) == 2

    def test_case_insensitive_dedup(self):
        defs = [{"name": "Budget"}, {"name": "BUDGET"}]
        result = self.orch._normalize_definitions(defs)
        assert len(result) == 1

    def test_caps_at_80(self):
        defs = [{"name": f"Topic {i}"} for i in range(100)]
        result = self.orch._normalize_definitions(defs)
        assert len(result) <= 80

    def test_sorted_by_order_then_name(self):
        defs = [
            {"name": "Bravo", "order": 2},
            {"name": "Alpha", "order": 1},
        ]
        result = self.orch._normalize_definitions(defs)
        assert result[0]["name"] == "Alpha"
        assert result[1]["name"] == "Bravo"

    def test_order_reassigned_sequentially(self):
        defs = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
        result = self.orch._normalize_definitions(defs)
        assert result[0]["order"] == 0
        assert result[1]["order"] == 1
        assert result[2]["order"] == 2

    def test_fallback_agenda_used_when_defs_empty(self):
        result = self.orch._normalize_definitions([], fallback_agenda=["Alpha", "Beta"])
        names = [r["name"] for r in result]
        assert "Alpha" in names
        assert "Beta" in names

    def test_empty_definitions_no_fallback_returns_empty(self):
        result = self.orch._normalize_definitions([])
        assert result == []

    def test_id_collision_resolved_with_suffix(self):
        defs = [
            {"name": "Alpha", "id": "alpha"},
            {"name": "Alpha2", "id": "alpha"},  # same id, different name
        ]
        result = self.orch._normalize_definitions(defs)
        ids = [r["id"] for r in result]
        assert len(set(ids)) == len(ids)  # all unique


# ===========================================================================
# 3. configure()
# ===========================================================================

class TestConfigure:
    def test_sets_enabled(self):
        orch = _make_orchestrator()
        orch.configure(agenda=["A"], enabled=True, allow_new_topics=True, interval_sec=60, window_sec=90)
        assert orch.topics_enabled is True

    def test_sets_allow_new_topics(self):
        orch = _make_orchestrator()
        orch.configure(agenda=["A"], enabled=True, allow_new_topics=False, interval_sec=60, window_sec=90)
        assert orch.topics_allow_new is False

    def test_sets_chunk_mode_window(self):
        orch = _make_orchestrator()
        orch.configure(agenda=["A"], enabled=True, allow_new_topics=True,
                       chunk_mode="window", interval_sec=60, window_sec=90)
        assert orch.topics_chunk_mode == "window"

    def test_default_chunk_mode_is_since_last(self):
        orch = _make_orchestrator()
        orch.configure(agenda=["A"], enabled=True, allow_new_topics=True, interval_sec=60, window_sec=90)
        assert orch.topics_chunk_mode == "since_last"

    def test_sets_interval_sec(self):
        orch = _make_orchestrator()
        orch.configure(agenda=["A"], enabled=True, allow_new_topics=True, interval_sec=90, window_sec=90)
        assert orch.topics_interval_sec == 90

    def test_interval_clamped_to_minimum_30(self):
        orch = _make_orchestrator()
        orch.configure(agenda=["A"], enabled=True, allow_new_topics=True, interval_sec=5, window_sec=60)
        assert orch.topics_interval_sec == 30

    def test_interval_clamped_to_maximum_300(self):
        orch = _make_orchestrator()
        orch.configure(agenda=["A"], enabled=True, allow_new_topics=True, interval_sec=9999, window_sec=60)
        assert orch.topics_interval_sec == 300

    def test_marks_settings_saved(self):
        orch = _make_orchestrator()
        assert orch.topics_settings_saved is False
        orch.configure(agenda=["A"], enabled=True, allow_new_topics=True, interval_sec=60, window_sec=90)
        assert orch.topics_settings_saved is True

    def test_deduplicates_agenda(self):
        orch = _make_orchestrator()
        orch.configure(agenda=["A", "A", "B"], enabled=True, allow_new_topics=True, interval_sec=60, window_sec=90)
        assert orch.topics_agenda.count("A") == 1
        assert len(orch.topics_agenda) == 2

    def test_caps_agenda_at_20(self):
        orch = _make_orchestrator()
        orch.configure(agenda=[f"T{i}" for i in range(30)], enabled=True,
                       allow_new_topics=True, interval_sec=60, window_sec=90)
        assert len(orch.topics_agenda) == 20

    def test_creates_stub_items_for_agenda(self):
        orch = _make_orchestrator()
        orch.configure(agenda=["Alpha", "Beta"], enabled=True, allow_new_topics=True, interval_sec=60, window_sec=90)
        names = [item["name"] for item in orch.topics_items]
        assert "Alpha" in names
        assert "Beta" in names

    def test_all_stub_items_start_as_not_started(self):
        orch = _make_orchestrator()
        orch.configure(agenda=["Alpha", "Beta"], enabled=True, allow_new_topics=True, interval_sec=60, window_sec=90)
        for item in orch.topics_items:
            assert item["status"] == "not_started"

    def test_preserves_status_for_known_agenda_topic(self):
        orch = _make_orchestrator()
        orch.configure(agenda=["Alpha"], enabled=True, allow_new_topics=True, interval_sec=60, window_sec=90)
        orch.topics_items[0]["status"] = "active"
        orch.topics_items[0]["time_seconds"] = 120
        # Reconfigure same agenda
        orch.configure(agenda=["Alpha"], enabled=True, allow_new_topics=True, interval_sec=60, window_sec=90)
        assert orch.topics_items[0]["status"] == "active"
        assert orch.topics_items[0]["time_seconds"] == 120

    def test_resets_pending_and_error(self):
        orch = _make_orchestrator()
        orch.topics_pending = True
        orch.topics_last_error = "previous error"
        orch.configure(agenda=["A"], enabled=True, allow_new_topics=True, interval_sec=60, window_sec=90)
        assert orch.topics_pending is False
        assert orch.topics_last_error == ""

    def test_returns_payload_dict(self):
        orch = _make_orchestrator()
        result = orch.configure(agenda=["A"], enabled=True, allow_new_topics=True, interval_sec=60, window_sec=90)
        assert isinstance(result, dict)
        assert "items" in result

    def test_with_definitions_overrides_agenda_items(self):
        orch = _make_orchestrator()
        defs = [{"name": "Budget", "priority": "high"}, {"name": "Timeline"}]
        orch.configure(agenda=["Budget", "Timeline"], enabled=True, allow_new_topics=True,
                       interval_sec=60, window_sec=90, definitions=defs)
        assert len(orch.topics_definitions) == 2
        assert orch.topics_definitions[0]["name"] in ("Budget", "Timeline")


# ===========================================================================
# 4. payload_unlocked()
# ===========================================================================

class TestPayloadUnlocked:
    def test_contains_required_keys(self):
        orch = _configured_orch()
        payload = orch.payload_unlocked()
        for key in ("configured", "enabled", "agenda", "definitions", "items", "runs",
                    "pending", "last_run_ts", "allow_new_topics", "chunk_mode"):
            assert key in payload

    def test_items_reflect_configure(self):
        orch = _configured_orch(agenda=["X", "Y"])
        payload = orch.payload_unlocked()
        item_names = [i["name"] for i in payload["items"]]
        assert "X" in item_names
        assert "Y" in item_names

    def test_runs_starts_empty(self):
        orch = _configured_orch()
        assert orch.payload_unlocked()["runs"] == []


# ===========================================================================
# 5. prepare_call_unlocked()
# ===========================================================================

class TestPrepareCallUnlocked:
    def test_returns_none_when_tracker_not_configured(self):
        finals = [_final()]
        orch = _make_orchestrator(finals=finals)
        orch.topics_settings_saved = True
        orch.topics_agenda = ["A"]
        # tracker.is_configured = False (default)
        result = orch.prepare_call_unlocked(time.time(), trigger="manual")
        assert result is None

    def test_returns_none_when_settings_not_saved(self):
        tracker = _make_tracker(is_configured=True)
        finals = [_final()]
        orch = _make_orchestrator(tracker=tracker, finals=finals)
        orch.topics_settings_saved = False
        orch.topics_agenda = ["A"]
        result = orch.prepare_call_unlocked(time.time(), trigger="manual")
        assert result is None

    def test_returns_none_when_pending(self):
        tracker = _make_tracker(is_configured=True)
        finals = [_final()]
        orch = _configured_orch(finals=finals)
        orch._topic_tracker = tracker
        orch.topics_pending = True
        result = orch.prepare_call_unlocked(time.time(), trigger="manual")
        assert result is None

    def test_returns_none_when_no_finals(self):
        orch = _configured_orch(finals=[])
        result = orch.prepare_call_unlocked(time.time(), trigger="manual")
        assert result is None

    def test_returns_call_dict_when_finals_available(self):
        now = time.time()
        finals = [_final(ts=now - 5)]
        orch = _configured_orch(finals=finals)
        result = orch.prepare_call_unlocked(now, trigger="manual")
        assert result is not None
        assert result["trigger"] == "manual"
        assert len(result["chunk_turns"]) == 1

    def test_auto_trigger_returns_none_when_disabled(self):
        now = time.time()
        finals = [_final(ts=now - 5)]
        orch = _configured_orch(finals=finals)
        orch.topics_enabled = False
        result = orch.prepare_call_unlocked(now, trigger="auto")
        assert result is None

    def test_manual_trigger_ignores_enabled_flag(self):
        now = time.time()
        finals = [_final(ts=now - 5)]
        orch = _configured_orch(finals=finals)
        orch.topics_enabled = False
        result = orch.prepare_call_unlocked(now, trigger="manual")
        assert result is not None

    def test_sets_pending_after_call_prepared(self):
        now = time.time()
        finals = [_final(ts=now - 5)]
        orch = _configured_orch(finals=finals)
        orch.prepare_call_unlocked(now, trigger="manual")
        assert orch.topics_pending is True

    def test_updates_last_run_ts(self):
        now = time.time()
        finals = [_final(ts=now - 5)]
        orch = _configured_orch(finals=finals)
        before = orch.topics_last_run_ts
        orch.prepare_call_unlocked(now, trigger="manual")
        assert orch.topics_last_run_ts >= before

    def test_since_last_mode_uses_index_offset(self):
        now = time.time()
        finals = [_final(en=f"turn {i}", ts=now - (10 - i)) for i in range(5)]
        orch = _configured_orch(finals=finals)
        orch.topics_chunk_mode = "since_last"
        orch.topics_last_final_idx = 3  # skip first 3
        result = orch.prepare_call_unlocked(now, trigger="manual")
        assert result is not None
        assert len(result["chunk_turns"]) == 2  # only turns 3 and 4

    def test_window_mode_filters_by_time(self):
        now = time.time()
        finals = [
            _final(en="old", ts=now - 200),
            _final(en="recent", ts=now - 30),
        ]
        orch = _configured_orch(finals=finals)
        orch.topics_chunk_mode = "window"
        orch.topics_window_sec = 90
        result = orch.prepare_call_unlocked(now, trigger="manual")
        assert result is not None
        assert len(result["chunk_turns"]) == 1
        assert result["chunk_turns"][0]["en"] == "recent"

    def test_possible_context_reset_when_large_gap(self):
        now = time.time()
        # Two finals with a >45s gap between them
        finals = [
            _final(en="turn 0", ts=now - 120),
            _final(en="turn 1", ts=now - 5),
        ]
        orch = _configured_orch(finals=finals)
        orch.topics_chunk_mode = "since_last"
        orch.topics_last_final_idx = 1  # only process last turn
        result = orch.prepare_call_unlocked(now, trigger="manual")
        assert result is not None
        assert result["possible_context_reset"] is True

    def test_chunk_seconds_computed(self):
        now = time.time()
        finals = [
            _final(en="start", ts=now - 60, speaker_label="S"),
            _final(en="end", ts=now - 10, speaker_label="S"),
        ]
        orch = _configured_orch(finals=finals)
        result = orch.prepare_call_unlocked(now, trigger="manual")
        assert result is not None
        assert result["chunk_seconds"] > 0


# ===========================================================================
# 6. _merge_statements()
# ===========================================================================

class TestMergeStatements:
    def test_deduplicates_same_speaker_same_text(self):
        existing = [{"ts": 1.0, "speaker": "A", "text": "hello"}]
        incoming = [{"ts": 1.0, "speaker": "A", "text": "hello"}]
        result = TopicOrchestrator._merge_statements(existing, incoming)
        assert len(result) == 1

    def test_case_sensitive_dedup_on_text_lower(self):
        # dedup key is lowercase
        existing = [{"ts": 1.0, "speaker": "A", "text": "Hello"}]
        incoming = [{"ts": 2.0, "speaker": "A", "text": "hello"}]
        result = TopicOrchestrator._merge_statements(existing, incoming)
        assert len(result) == 1

    def test_keeps_different_texts(self):
        existing = [{"ts": 1.0, "speaker": "A", "text": "hello"}]
        incoming = [{"ts": 2.0, "speaker": "A", "text": "world"}]
        result = TopicOrchestrator._merge_statements(existing, incoming)
        assert len(result) == 2

    def test_caps_at_20(self):
        rows = [{"ts": float(i), "speaker": "A", "text": f"stmt {i}"} for i in range(30)]
        result = TopicOrchestrator._merge_statements(rows, [])
        assert len(result) <= 20

    def test_sorted_most_recent_first(self):
        rows = [
            {"ts": 1.0, "speaker": "A", "text": "first"},
            {"ts": 3.0, "speaker": "A", "text": "third"},
            {"ts": 2.0, "speaker": "A", "text": "second"},
        ]
        result = TopicOrchestrator._merge_statements(rows, [])
        assert result[0]["text"] == "third"
        assert result[-1]["text"] == "first"

    def test_ignores_invalid_rows(self):
        result = TopicOrchestrator._merge_statements(["not a dict", None], [])  # type: ignore
        assert result == []

    def test_ignores_empty_text_rows(self):
        rows = [{"ts": 1.0, "speaker": "A", "text": ""}]
        result = TopicOrchestrator._merge_statements(rows, [])
        assert result == []


# ===========================================================================
# 7. _append_run_unlocked cap at 160
# ===========================================================================

class TestAppendRunCap:
    def test_capped_at_160(self):
        orch = _make_orchestrator()
        for i in range(170):
            orch._append_run_unlocked({"ts": float(i), "trigger": "auto", "status": "success"})
        assert len(orch.topics_runs) == 160

    def test_keeps_newest_entries(self):
        orch = _make_orchestrator()
        for i in range(170):
            orch._append_run_unlocked({"ts": float(i), "trigger": "auto"})
        assert orch.topics_runs[0]["ts"] == 10.0  # oldest kept
        assert orch.topics_runs[-1]["ts"] == 169.0  # newest


# ===========================================================================
# 8. clear() and clear_for_transcript_unlocked()
# ===========================================================================

class TestClearActions:
    def test_clear_resets_runs(self):
        orch = _configured_orch()
        orch._append_run_unlocked({"ts": 1.0})
        tracker = _make_tracker()
        orch.clear(topic_tracker=tracker)
        assert orch.topics_runs == []

    def test_clear_resets_last_final_idx(self):
        orch = _configured_orch()
        orch.topics_last_final_idx = 99
        tracker = _make_tracker()
        orch.clear(topic_tracker=tracker)
        assert orch.topics_last_final_idx == 0

    def test_clear_resets_last_run_ts(self):
        orch = _configured_orch()
        orch.topics_last_run_ts = 999.0
        tracker = _make_tracker()
        orch.clear(topic_tracker=tracker)
        assert orch.topics_last_run_ts == 0.0

    def test_clear_resets_error(self):
        orch = _configured_orch()
        orch.topics_last_error = "some error"
        tracker = _make_tracker()
        orch.clear(topic_tracker=tracker)
        assert orch.topics_last_error == ""

    def test_clear_calls_tracker_clear_conversation(self):
        orch = _configured_orch()
        tracker = _make_tracker()
        orch.clear(topic_tracker=tracker)
        tracker.clear_conversation.assert_called_once()

    def test_clear_for_transcript_resets_cursor_and_pending(self):
        orch = _configured_orch()
        orch.topics_last_final_idx = 50
        orch.topics_pending = True
        orch.topics_last_run_ts = 42.0
        orch.clear_for_transcript_unlocked()
        assert orch.topics_last_final_idx == 0
        assert orch.topics_pending is False
        assert orch.topics_last_run_ts == 0.0

    def test_clear_for_transcript_resets_runs(self):
        orch = _configured_orch()
        orch._append_run_unlocked({"ts": 1.0})
        orch.clear_for_transcript_unlocked()
        assert orch.topics_runs == []


# ===========================================================================
# 9. finalize_on_stop_unlocked()
# ===========================================================================

class TestFinalizeOnStop:
    def test_covers_active_topics(self):
        orch = _configured_orch(agenda=["Alpha", "Beta"])
        orch.topics_items[0]["status"] = "active"
        orch.finalize_on_stop_unlocked()
        assert orch.topics_items[0]["status"] == "covered"

    def test_leaves_not_started_unchanged(self):
        orch = _configured_orch(agenda=["Alpha"])
        orch.topics_items[0]["status"] = "not_started"
        orch.finalize_on_stop_unlocked()
        assert orch.topics_items[0]["status"] == "not_started"

    def test_leaves_covered_unchanged(self):
        orch = _configured_orch(agenda=["Alpha"])
        orch.topics_items[0]["status"] = "covered"
        orch.finalize_on_stop_unlocked()
        assert orch.topics_items[0]["status"] == "covered"

    def test_resets_runtime_meta_absent_counters(self):
        orch = _configured_orch(agenda=["Alpha"])
        key = "alpha"
        orch.topics_runtime_meta[key] = {"absent_runs": 5, "absent_seconds": 300}
        orch.finalize_on_stop_unlocked()
        assert orch.topics_runtime_meta[key]["absent_runs"] == 0
        assert orch.topics_runtime_meta[key]["absent_seconds"] == 0


# ===========================================================================
# 10. analyze_now() error cases
# ===========================================================================

class TestAnalyzeNowErrors:
    async def test_raises_when_pending(self):
        orch = _configured_orch()
        orch.topics_pending = True
        with pytest.raises(RuntimeError, match="already running"):
            await orch.analyze_now()

    async def test_raises_when_settings_not_saved(self):
        orch = _make_orchestrator()
        orch.topics_settings_saved = False
        with pytest.raises(RuntimeError, match="Save topic settings"):
            await orch.analyze_now()

    async def test_raises_when_no_finals_since_last(self):
        orch = _configured_orch(finals=[])
        with pytest.raises(RuntimeError):
            await orch.analyze_now()

    async def test_raises_when_allow_new_false_and_no_agenda(self):
        tracker = _make_tracker(is_configured=True)
        orch = _make_orchestrator(tracker=tracker)
        orch.topics_settings_saved = True
        orch.topics_allow_new = False
        orch.topics_agenda = []
        with pytest.raises(RuntimeError, match="Custom topics are disabled"):
            await orch.analyze_now()


# ===========================================================================
# 11. _agent_input_from_call() — payload minimisation
# ===========================================================================

class TestAgentInputFromCall:
    def setup_method(self):
        self.orch = _make_orchestrator()

    def test_contains_required_keys(self):
        topic_call = {
            "agenda": ["A", "B"],
            "definitions": [{"name": "A", "comments": "scope"}],
            "allow_new_topics": True,
            "current_topics": [{"name": "A", "status": "active"}],
            "chunk_turns": [{"ts": 1.0, "speaker": "S", "en": "hello"}],
            "possible_context_reset": False,
        }
        result = self.orch._agent_input_from_call(topic_call)
        assert "agenda" in result
        assert "definitions" in result
        assert "allow_new_topics" in result
        assert "current_topics" in result
        assert "chunk_turns" in result

    def test_empty_names_excluded_from_agenda(self):
        topic_call = {
            "agenda": ["", "Valid", "  "],
            "definitions": [],
            "allow_new_topics": True,
            "current_topics": [],
            "chunk_turns": [],
            "possible_context_reset": False,
        }
        result = self.orch._agent_input_from_call(topic_call)
        assert result["agenda"] == ["Valid"]

    def test_definition_without_comments_omits_key(self):
        topic_call = {
            "agenda": [],
            "definitions": [{"name": "A", "comments": ""}],
            "allow_new_topics": True,
            "current_topics": [],
            "chunk_turns": [],
            "possible_context_reset": False,
        }
        result = self.orch._agent_input_from_call(topic_call)
        assert "comments" not in result["definitions"][0]

    def test_recent_context_included_when_present(self):
        topic_call = {
            "agenda": [],
            "definitions": [],
            "allow_new_topics": True,
            "current_topics": [],
            "chunk_turns": [],
            "possible_context_reset": False,
            "recent_context": {"active_topic": "Budget"},
        }
        result = self.orch._agent_input_from_call(topic_call)
        assert "recent_context" in result
        assert result["recent_context"]["active_topic"] == "Budget"


# ===========================================================================
# 12. Agent response pipeline edge-cases
# ===========================================================================

class TestNormalizeItem:
    def setup_method(self):
        self.orch = _make_orchestrator()

    def test_drops_item_when_name_empty(self):
        result = self.orch._normalize_item(
            {"name": "   ", "status": "active"},
            now_ts=100.0,
        )
        assert result is None

    def test_clamps_confidence_and_coerces_topic_presence(self):
        result = self.orch._normalize_item(
            {
                "name": "Budget Fit",
                "status": "not_started",
                "match_confidence": 2.7,
                "topic_presence": "yes",
                "key_statements": [],
            },
            now_ts=100.0,
        )
        assert result is not None
        assert result["match_confidence"] == 1.0
        assert result["topic_presence"] is True


class TestAgentMergePipeline:
    def test_apply_merge_reopens_covered_topic_on_high_confidence_presence(self):
        orch = _make_orchestrator()
        confidence_threshold = 0.65
        now_ts = 200.0

        normalized_by_key = {
            "alpha": {
                "name": "Alpha",
                "status": "active",
                "topic_presence": True,
                "match_confidence": 0.9,
                "key_statements": [{"ts": now_ts, "speaker": "S", "text": "alpha detail"}],
            }
        }
        merged_by_key = {
            "alpha": {
                "name": "Alpha",
                "status": "covered",
                "time_seconds": 10,
                "comments": "",
                "key_statements": [],
                "updated_ts": 10.0,
            }
        }
        final_order = ["alpha"]
        incoming_meta = {
            "alpha": {
                "incoming_statements": [{"ts": now_ts, "speaker": "S", "text": "alpha detail"}],
                "incoming_has_new_detail": True,
                "incoming_presence": True,
                "incoming_confidence": 0.9,
                "incoming_status": "active",
                "incoming_comments": "",
                "allow_assignment": True,
                "create_new_candidate": False,
            }
        }
        status_rank = {"not_started": 0, "active": 1, "covered": 2}

        _, updated_topics, _, transitions, _, _ = orch._apply_merge_unlocked(
            normalized_by_key=normalized_by_key,
            merged_by_key=merged_by_key,
            final_order=final_order,
            incoming_meta=incoming_meta,
            allocated_seconds_by_key={"alpha": 5},
            confidence_threshold=confidence_threshold,
            now_ts=now_ts,
            status_rank=status_rank,
        )

        assert updated_topics == 1
        assert merged_by_key["alpha"]["status"] == "active"
        assert merged_by_key["alpha"]["time_seconds"] == 15
        assert any(
            row["topic"] == "Alpha" and row["from"] == "covered" and row["to"] == "active"
            for row in transitions
        )

    def test_classify_then_merge_coerces_not_started_to_active_when_evidence_present(self):
        orch = _make_orchestrator()
        orch.topics_allow_new = True
        now_ts = 300.0

        normalized_by_key = {
            "alpha": {
                "name": "Alpha",
                "status": "not_started",
                "topic_presence": True,
                "match_confidence": 0.9,
                "key_statements": [],
            }
        }
        incoming_meta, _, _, _, _ = orch._classify_incoming_unlocked(
            normalized_by_key=normalized_by_key,
            known_topic_keys={"alpha"},
            chunk_min_ts=now_ts - 30.0,
            chunk_max_ts=now_ts + 30.0,
            confidence_threshold=0.65,
        )
        assert incoming_meta["alpha"]["incoming_status"] == "active"

        merged_by_key = {
            "alpha": {
                "name": "Alpha",
                "status": "not_started",
                "time_seconds": 0,
                "comments": "",
                "key_statements": [],
                "updated_ts": 10.0,
            }
        }
        status_rank = {"not_started": 0, "active": 1, "covered": 2}
        _, updated_topics, _, transitions, _, _ = orch._apply_merge_unlocked(
            normalized_by_key=normalized_by_key,
            merged_by_key=merged_by_key,
            final_order=["alpha"],
            incoming_meta=incoming_meta,
            allocated_seconds_by_key={},
            confidence_threshold=0.65,
            now_ts=now_ts,
            status_rank=status_rank,
        )

        assert updated_topics == 1
        assert merged_by_key["alpha"]["status"] == "active"
        assert any(
            row["topic"] == "Alpha" and row["from"] == "not_started" and row["to"] == "active"
            for row in transitions
        )
