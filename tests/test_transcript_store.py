"""
Tests for app.controller.transcript_store.TranscriptStore.
"""

import threading
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.controller.transcript_store import TranscriptStore


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def store():
    lock = threading.RLock()
    s = TranscriptStore(
        lock=lock,
        broadcast=AsyncMock(),
        broadcast_log=AsyncMock(),
        emit_trace_async=AsyncMock(),
        get_debug=lambda: False,
    )
    return s


def _final(en="hello", speaker="default", ts=None, segment_id="s1", revision=1):
    ts = ts or time.time()
    return {
        "en": en,
        "ar": "",
        "speaker": speaker,
        "speaker_label": "Speaker",
        "segment_id": segment_id,
        "revision": revision,
        "ts": ts,
        "start_ts": ts - 1.0,
    }


# ---------------------------------------------------------------------------
# append_final_unlocked
# ---------------------------------------------------------------------------

class TestAppendFinal:
    def test_appends_item(self, store):
        store.append_final_unlocked(_final("hi"), max_finals=100)
        assert len(store.finals) == 1
        assert store.finals[0]["en"] == "hi"

    def test_stores_required_fields(self, store):
        store.append_final_unlocked(_final(), max_finals=100)
        item = store.finals[0]
        for field in ("en", "ar", "speaker", "speaker_label", "segment_id", "revision", "ts", "start_ts"):
            assert field in item

    def test_initializes_shadow_translation_field(self, store):
        store.append_final_unlocked(_final(), max_finals=100)
        assert store.finals[0]["shadow_translation"] is None

    def test_stores_enriched_timing_fields(self, store):
        ts = time.time()
        payload = _final(ts=ts)
        payload.update(
            {
                "end_ts": ts - 0.2,
                "duration_sec": 0.8,
                "offset_sec": 12.5,
                "timing_source": "offset",
                "recognizer_session_id": "session-1",
                "recognizer_anchor_ts": ts - 20.0,
            }
        )
        store.append_final_unlocked(payload, max_finals=100)
        item = store.finals[0]
        assert item["end_ts"] == pytest.approx(ts - 0.2)
        assert item["duration_sec"] == pytest.approx(0.8)
        assert item["offset_sec"] == pytest.approx(12.5)
        assert item["timing_source"] == "offset"
        assert item["recognizer_session_id"] == "session-1"
        assert item["recognizer_anchor_ts"] == pytest.approx(ts - 20.0)

    def test_caps_at_max_finals(self, store):
        for i in range(10):
            store.append_final_unlocked(_final(f"turn {i}", segment_id=f"s{i}"), max_finals=5)
        assert len(store.finals) == 5

    def test_cap_keeps_newest_entries(self, store):
        for i in range(10):
            store.append_final_unlocked(_final(f"turn {i}", segment_id=f"s{i}"), max_finals=5)
        assert store.finals[-1]["en"] == "turn 9"
        assert store.finals[0]["en"] == "turn 5"

    def test_clears_en_live_after_final(self, store):
        store.en_live = "partial text"
        store.append_final_unlocked(_final(), max_finals=100)
        assert store.en_live == ""

    def test_clears_ar_live_after_final(self, store):
        store.ar_live = "arabic partial"
        store.append_final_unlocked(_final(), max_finals=100)
        assert store.ar_live == ""

    def test_removes_speaker_from_live_partials(self, store):
        store.live_partials["default"] = {"en": "in progress"}
        store.append_final_unlocked(_final(speaker="default"), max_finals=100)
        assert "default" not in store.live_partials

    def test_does_not_remove_other_speaker_partial(self, store):
        store.live_partials["remote"] = {"en": "still active"}
        store.append_final_unlocked(_final(speaker="local"), max_finals=100)
        assert "remote" in store.live_partials

    def test_updates_last_speech_activity_ts(self, store):
        before = store.last_speech_activity_ts
        time.sleep(0.01)
        store.append_final_unlocked(_final("non-empty"), max_finals=100)
        assert store.last_speech_activity_ts > before

    def test_empty_en_does_not_update_activity_ts(self, store):
        before = store.last_speech_activity_ts
        store.append_final_unlocked(_final(""), max_finals=100)
        assert store.last_speech_activity_ts == before

    def test_get_finals_count(self, store):
        store.append_final_unlocked(_final(segment_id="a"), max_finals=100)
        store.append_final_unlocked(_final(segment_id="b"), max_finals=100)
        assert store.get_finals_count() == 2

    def test_get_finals_slice(self, store):
        for i in range(5):
            store.append_final_unlocked(_final(f"t{i}", segment_id=f"s{i}"), max_finals=100)
        sliced = store.get_finals_slice(1, 3)
        assert len(sliced) == 2
        assert sliced[0]["en"] == "t1"


# ---------------------------------------------------------------------------
# should_suppress_dual_local_unlocked
# ---------------------------------------------------------------------------

class TestShouldSuppressDualLocal:
    def test_single_mode_never_suppresses(self, store):
        payload = {"speaker": "local", "en": "hi"}
        assert store.should_suppress_dual_local_unlocked(payload, "single") is False

    def test_dual_mode_remote_speaker_never_suppressed(self, store):
        store.live_partials["remote"] = {"en": "remote speaking"}
        payload = {"speaker": "remote", "en": "hi"}
        assert store.should_suppress_dual_local_unlocked(payload, "dual") is False

    def test_dual_mode_default_speaker_never_suppressed(self, store):
        payload = {"speaker": "default", "en": "hi"}
        assert store.should_suppress_dual_local_unlocked(payload, "dual") is False

    def test_dual_mode_local_suppressed_when_remote_partial_active(self, store):
        store.live_partials["remote"] = {"en": "remote is talking"}
        payload = {"speaker": "local", "en": "hi"}
        assert store.should_suppress_dual_local_unlocked(payload, "dual") is True

    def test_dual_mode_local_not_suppressed_when_remote_partial_empty(self, store):
        store.live_partials["remote"] = {"en": ""}
        payload = {"speaker": "local", "en": "hi"}
        assert store.should_suppress_dual_local_unlocked(payload, "dual") is False

    def test_dual_mode_local_suppressed_by_very_recent_remote_activity(self, store):
        store._speaker_last_activity_ts["remote"] = time.time()  # just now
        payload = {"speaker": "local", "en": "hi"}
        assert store.should_suppress_dual_local_unlocked(payload, "dual") is True

    def test_dual_mode_local_not_suppressed_after_old_remote_activity(self, store):
        store._speaker_last_activity_ts["remote"] = time.time() - 10.0  # stale
        payload = {"speaker": "local", "en": "hi"}
        assert store.should_suppress_dual_local_unlocked(payload, "dual") is False

    def test_dual_mode_local_not_suppressed_when_remote_never_active(self, store):
        # remote ts is 0.0 (never spoke)
        payload = {"speaker": "local", "en": "hi"}
        assert store.should_suppress_dual_local_unlocked(payload, "dual") is False


# ---------------------------------------------------------------------------
# clear_unlocked
# ---------------------------------------------------------------------------

class TestClearUnlocked:
    def test_clears_finals(self, store):
        store.append_final_unlocked(_final(), max_finals=100)
        store.clear_unlocked()
        assert store.finals == []

    def test_clears_en_live(self, store):
        store.en_live = "live text"
        store.clear_unlocked()
        assert store.en_live == ""

    def test_clears_ar_live(self, store):
        store.ar_live = "ar text"
        store.clear_unlocked()
        assert store.ar_live == ""

    def test_clears_live_partials(self, store):
        store.live_partials["local"] = {"en": "talking"}
        store.clear_unlocked()
        assert store.live_partials == {}


class TestClearLivePartial:
    def test_removes_only_target_speaker(self, store):
        store.live_partials["local"] = {
            "speaker": "local",
            "speaker_label": "You",
            "segment_id": "seg-1",
            "revision": 2,
            "en": "stuck partial",
            "ar": "",
            "ts": 10.0,
        }
        store.live_partials["remote"] = {
            "speaker": "remote",
            "speaker_label": "Remote",
            "segment_id": "seg-2",
            "revision": 1,
            "en": "other partial",
            "ar": "ترجمة",
            "ts": 20.0,
        }
        store.en_live = "stuck partial"
        store.ar_live = ""

        removed = store.clear_live_partial_unlocked("local")

        assert removed == {
            "speaker": "local",
            "speaker_label": "You",
            "segment_id": "seg-1",
            "revision": 2,
        }
        assert "local" not in store.live_partials
        assert "remote" in store.live_partials
        assert store.en_live == "other partial"
        assert store.ar_live == "ترجمة"

    def test_returns_none_when_speaker_missing(self, store):
        assert store.clear_live_partial_unlocked("missing") is None


# ---------------------------------------------------------------------------
# build_telemetry_unlocked
# ---------------------------------------------------------------------------

class TestBuildTelemetry:
    def test_returns_correct_type_field(self, store):
        t = store.build_telemetry_unlocked(ws_connections=0, status="idle", running=False)
        assert t["type"] == "telemetry"

    def test_ws_connections_populated(self, store):
        t = store.build_telemetry_unlocked(ws_connections=3, status="idle", running=False)
        assert t["ws_connections"] == 3

    def test_status_and_running_populated(self, store):
        t = store.build_telemetry_unlocked(ws_connections=0, status="recognizing", running=True)
        assert t["recognition_status"] == "recognizing"
        assert t["recognition_running"] is True

    def test_no_cost_when_rate_not_set(self, store):
        store.translation_cost_per_million_usd = None
        t = store.build_telemetry_unlocked(ws_connections=0, status="idle", running=False)
        assert t["estimated_cost_usd"] is None

    def test_cost_computed_correctly(self, store):
        store.translation_cost_per_million_usd = 10.0
        store.translation_chars = 500_000  # half a million
        t = store.build_telemetry_unlocked(ws_connections=0, status="idle", running=False)
        assert t["estimated_cost_usd"] == pytest.approx(5.0)

    def test_zero_chars_cost_is_zero(self, store):
        store.translation_cost_per_million_usd = 10.0
        store.translation_chars = 0
        t = store.build_telemetry_unlocked(ws_connections=0, status="idle", running=False)
        assert t["estimated_cost_usd"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# _median_ms_unlocked
# ---------------------------------------------------------------------------

class TestMedianMs:
    def test_empty_returns_none(self, store):
        assert store._median_ms_unlocked() is None

    def test_single_value(self, store):
        store.translation_latency_ms.append(100)
        assert store._median_ms_unlocked() == 100

    def test_odd_count(self, store):
        store.translation_latency_ms.extend([300, 100, 200])
        assert store._median_ms_unlocked() == 200

    def test_even_count(self, store):
        store.translation_latency_ms.extend([100, 300])
        assert store._median_ms_unlocked() == 200

    def test_even_count_average(self, store):
        store.translation_latency_ms.extend([100, 200, 300, 400])
        assert store._median_ms_unlocked() == 250


# ---------------------------------------------------------------------------
# update_speaker_activity_unlocked
# ---------------------------------------------------------------------------

class TestSpeakerActivity:
    def test_updates_speaker_ts(self, store):
        now = time.time()
        store.update_speaker_activity_unlocked("local", now)
        assert store._speaker_last_activity_ts["local"] == now

    def test_has_speech_true_updates_global_activity(self, store):
        now = time.time() + 100
        store.update_speaker_activity_unlocked("default", now, has_speech=True)
        assert store.last_speech_activity_ts == now

    def test_has_speech_false_does_not_update_global_activity(self, store):
        before = store.last_speech_activity_ts
        store.update_speaker_activity_unlocked("default", time.time() + 100, has_speech=False)
        assert store.last_speech_activity_ts == before


class TestApplyShadowTranslationResult:
    @pytest.mark.asyncio
    async def test_patches_matching_final_and_broadcasts(self, store):
        store.append_final_unlocked(_final(segment_id="seg-1", revision=2), max_finals=100)
        req = {
            "segment_id": "seg-1",
            "revision": 2,
            "debug": False,
        }
        result = {
            "provider": "azure_openai_shadow",
            "model": "gpt-4.1-mini",
            "status": "completed",
            "text": "إطلاق المشروع يسير حسب الخطة.",
            "latency_ms": 1234,
            "error": None,
        }

        await store.apply_shadow_translation_result(req, result)

        assert store.finals[0]["shadow_translation"] == result
        assert store.finals[0]["ar"] == "إطلاق المشروع يسير حسب الخطة."
        store._broadcast.assert_awaited_once()
        payload = store._broadcast.await_args.args[0]
        assert payload["type"] == "final_shadow_patch"
        assert payload["segment_id"] == "seg-1"
        assert payload["ar"] == "إطلاق المشروع يسير حسب الخطة."

    @pytest.mark.asyncio
    async def test_ignores_missing_final(self, store):
        req = {"segment_id": "missing", "revision": 1, "debug": False}
        result = {
            "provider": "azure_openai_shadow",
            "model": "gpt-4.1-mini",
            "status": "completed",
            "text": "نص",
            "latency_ms": 50,
            "error": None,
        }

        await store.apply_shadow_translation_result(req, result)

        store._broadcast.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_failed_shadow_translation_does_not_override_visible_arabic(self, store):
        store.append_final_unlocked(_final(segment_id="seg-1", revision=2), max_finals=100)
        store.finals[0]["ar"] = "ترجمة أساسية"
        req = {"segment_id": "seg-1", "revision": 2, "debug": False}
        result = {
            "provider": "azure_openai_shadow",
            "model": "gpt-4.1-mini",
            "status": "failed",
            "text": "",
            "latency_ms": 200,
            "error": "NotFoundError: Error code: 404",
        }

        await store.apply_shadow_translation_result(req, result)

        assert store.finals[0]["ar"] == "ترجمة أساسية"
        assert store.finals[0]["shadow_translation"] == result
        payload = store._broadcast.await_args.args[0]
        assert payload["type"] == "final_shadow_patch"
        assert payload["ar"] == ""
