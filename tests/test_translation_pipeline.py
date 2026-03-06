"""
Tests for app.services.translation_pipeline.TranslationPipeline.

Focuses on the pure-logic methods (prepare_partial_unlocked, prepare_final_unlocked,
is_current_partial_unlocked, reset_unlocked) without making real HTTP calls.
"""

import threading
import time
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.config import RuntimeConfig, Settings
from app.services.translation_pipeline import TranslationPipeline


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def pipeline(settings):
    return TranslationPipeline(
        settings=settings,
        apply_translation_result=AsyncMock(),
    )


@pytest.fixture
def cfg():
    return RuntimeConfig()


# ---------------------------------------------------------------------------
# prepare_partial_unlocked
# ---------------------------------------------------------------------------

class TestPreparePartialUnlocked:
    def test_creates_segment_on_first_call(self, pipeline, cfg):
        out, req = pipeline.prepare_partial_unlocked(
            speaker="default", speaker_label="Speaker",
            en="hello", prev_ar="",
            now_ts=time.time(), cfg=cfg,
        )
        assert out["type"] == "partial"
        assert out["en"] == "hello"
        assert out["speaker"] == "default"
        assert "segment_id" in out
        assert out["revision"] == 1

    def test_first_partial_returns_translation_req(self, pipeline, cfg):
        _, req = pipeline.prepare_partial_unlocked(
            speaker="default", speaker_label="Speaker",
            en="hi", prev_ar="",
            now_ts=time.time(), cfg=cfg,
        )
        assert req is not None
        assert req["kind"] == "partial"
        assert req["text"] == "hi"

    def test_revision_increments_on_subsequent_calls(self, pipeline, cfg):
        t = time.time()
        pipeline.prepare_partial_unlocked(
            speaker="default", speaker_label="S", en="a", prev_ar="",
            now_ts=t, cfg=cfg,
        )
        out2, _ = pipeline.prepare_partial_unlocked(
            speaker="default", speaker_label="S", en="ab", prev_ar="",
            now_ts=t + 1, cfg=cfg,
        )
        assert out2["revision"] == 2

    def test_different_speakers_have_independent_segments(self, pipeline, cfg):
        t = time.time()
        out_a, _ = pipeline.prepare_partial_unlocked(
            speaker="local", speaker_label="L", en="hi", prev_ar="",
            now_ts=t, cfg=cfg,
        )
        out_b, _ = pipeline.prepare_partial_unlocked(
            speaker="remote", speaker_label="R", en="hello", prev_ar="",
            now_ts=t, cfg=cfg,
        )
        assert out_a["segment_id"] != out_b["segment_id"]

    def test_throttle_suppresses_req_when_ar_already_exists(self, pipeline, cfg):
        t = time.time()
        # First call — no prev_ar, so req is always returned
        pipeline.prepare_partial_unlocked(
            speaker="default", speaker_label="S", en="hi", prev_ar="",
            now_ts=t, cfg=cfg,
        )
        # Very shortly after — prev_ar present so throttle applies
        _, req = pipeline.prepare_partial_unlocked(
            speaker="default", speaker_label="S", en="hi there", prev_ar="arabic",
            now_ts=t + 0.1, cfg=cfg,  # 0.1s << 0.6s default throttle
        )
        assert req is None

    def test_req_emitted_again_after_throttle_window(self, pipeline, cfg):
        t = time.time()
        pipeline.prepare_partial_unlocked(
            speaker="default", speaker_label="S", en="hi", prev_ar="",
            now_ts=t, cfg=cfg,
        )
        # After throttle window has passed
        _, req = pipeline.prepare_partial_unlocked(
            speaker="default", speaker_label="S", en="hi there", prev_ar="arabic",
            now_ts=t + 1.0, cfg=cfg,  # 1.0s > 0.6s threshold
        )
        assert req is not None

    def test_generation_set_in_req(self, pipeline, cfg):
        gen_before = pipeline._generation
        _, req = pipeline.prepare_partial_unlocked(
            speaker="default", speaker_label="S", en="hi", prev_ar="",
            now_ts=time.time(), cfg=cfg,
        )
        assert req["generation"] == gen_before

    def test_segment_id_consistent_across_revisions(self, pipeline, cfg):
        t = time.time()
        out1, _ = pipeline.prepare_partial_unlocked(
            speaker="default", speaker_label="S", en="a", prev_ar="",
            now_ts=t, cfg=cfg,
        )
        out2, _ = pipeline.prepare_partial_unlocked(
            speaker="default", speaker_label="S", en="ab", prev_ar="",
            now_ts=t + 1, cfg=cfg,
        )
        assert out1["segment_id"] == out2["segment_id"]


# ---------------------------------------------------------------------------
# prepare_final_unlocked
# ---------------------------------------------------------------------------

class TestPrepareFinalUnlocked:
    def test_creates_final_item(self, pipeline):
        t = time.time()
        item, req = pipeline.prepare_final_unlocked(
            speaker="default", speaker_label="Speaker", en="finished", ts=t
        )
        assert item["type"] == "final"
        assert item["en"] == "finished"
        assert item["ar"] == ""
        assert item["speaker"] == "default"

    def test_final_returns_translation_req(self, pipeline):
        item, req = pipeline.prepare_final_unlocked(
            speaker="default", speaker_label="S", en="done", ts=time.time()
        )
        assert req is not None
        assert req["kind"] == "final"
        assert req["text"] == "done"

    def test_empty_en_returns_no_req(self, pipeline):
        _, req = pipeline.prepare_final_unlocked(
            speaker="default", speaker_label="S", en="", ts=time.time()
        )
        assert req is None

    def test_final_clears_active_segment(self, pipeline, cfg):
        t = time.time()
        pipeline.prepare_partial_unlocked(
            speaker="default", speaker_label="S", en="start", prev_ar="",
            now_ts=t, cfg=cfg,
        )
        assert "default" in pipeline.active_segments
        pipeline.prepare_final_unlocked(
            speaker="default", speaker_label="S", en="end", ts=t + 1,
        )
        assert "default" not in pipeline.active_segments

    def test_final_uses_segment_id_from_preceding_partial(self, pipeline, cfg):
        t = time.time()
        out_partial, _ = pipeline.prepare_partial_unlocked(
            speaker="default", speaker_label="S", en="start", prev_ar="",
            now_ts=t, cfg=cfg,
        )
        item, _ = pipeline.prepare_final_unlocked(
            speaker="default", speaker_label="S", en="end", ts=t + 1,
        )
        assert item["segment_id"] == out_partial["segment_id"]

    def test_final_without_preceding_partial_creates_new_segment(self, pipeline):
        item, req = pipeline.prepare_final_unlocked(
            speaker="remote", speaker_label="R", en="standalone final", ts=time.time()
        )
        assert item["segment_id"] != ""
        assert req is not None

    def test_final_clears_partial_throttle_for_speaker(self, pipeline, cfg):
        t = time.time()
        pipeline.prepare_partial_unlocked(
            speaker="default", speaker_label="S", en="hi", prev_ar="",
            now_ts=t, cfg=cfg,
        )
        assert "default" in pipeline.partial_translate_last_emit_ts
        pipeline.prepare_final_unlocked(
            speaker="default", speaker_label="S", en="bye", ts=t + 1,
        )
        assert "default" not in pipeline.partial_translate_last_emit_ts


# ---------------------------------------------------------------------------
# reset_unlocked
# ---------------------------------------------------------------------------

class TestResetUnlocked:
    def test_increments_generation(self, pipeline, cfg):
        gen_before = pipeline._generation
        pipeline.reset_unlocked()
        assert pipeline._generation == gen_before + 1

    def test_clears_active_segments(self, pipeline, cfg):
        pipeline.prepare_partial_unlocked(
            speaker="default", speaker_label="S", en="hi", prev_ar="",
            now_ts=time.time(), cfg=cfg,
        )
        pipeline.reset_unlocked()
        assert pipeline.active_segments == {}

    def test_clears_partial_inflight(self, pipeline, cfg):
        pipeline.partial_inflight["default"] = True
        pipeline.reset_unlocked()
        assert pipeline.partial_inflight == {}

    def test_clears_partial_backlog(self, pipeline):
        pipeline.partial_backlog["default"] = {"kind": "partial"}
        pipeline.reset_unlocked()
        assert pipeline.partial_backlog == {}

    def test_clears_throttle_timestamps(self, pipeline, cfg):
        pipeline.partial_translate_last_emit_ts["default"] = time.time()
        pipeline.reset_unlocked()
        assert pipeline.partial_translate_last_emit_ts == {}


# ---------------------------------------------------------------------------
# discard_speaker_live_unlocked
# ---------------------------------------------------------------------------

class TestDiscardSpeakerLiveUnlocked:
    def test_discards_only_target_speaker_state(self, pipeline, cfg):
        t = time.time()
        pipeline.prepare_partial_unlocked(
            speaker="local", speaker_label="You", en="local text", prev_ar="",
            now_ts=t, cfg=cfg,
        )
        pipeline.prepare_partial_unlocked(
            speaker="remote", speaker_label="Remote", en="remote text", prev_ar="",
            now_ts=t + 0.2, cfg=cfg,
        )
        pipeline.partial_backlog["local"] = {"kind": "partial", "speaker": "local"}
        pipeline.partial_inflight["local"] = True

        pipeline.discard_speaker_live_unlocked("local")

        assert "local" not in pipeline.active_segments
        assert "local" not in pipeline.partial_translate_last_emit_ts
        assert "local" not in pipeline.partial_backlog
        assert "local" not in pipeline.partial_inflight
        assert "remote" in pipeline.active_segments


# ---------------------------------------------------------------------------
# is_current_partial_unlocked
# ---------------------------------------------------------------------------

class TestIsCurrentPartialUnlocked:
    def test_returns_false_when_no_active_segment(self, pipeline):
        req = {"speaker": "default", "segment_id": "s1", "revision": 1}
        live_partials = {"default": {"segment_id": "s1", "revision": 1}}
        assert pipeline.is_current_partial_unlocked(req, live_partials) is False

    def test_returns_false_when_segment_id_mismatch(self, pipeline, cfg):
        t = time.time()
        pipeline.prepare_partial_unlocked(
            speaker="default", speaker_label="S", en="hi", prev_ar="",
            now_ts=t, cfg=cfg,
        )
        seg = pipeline.active_segments["default"]
        req = {"speaker": "default", "segment_id": "wrong-id", "revision": 1}
        live_partials = {"default": {"segment_id": seg["segment_id"], "revision": 1}}
        assert pipeline.is_current_partial_unlocked(req, live_partials) is False

    def test_returns_true_for_matching_current_partial(self, pipeline, cfg):
        t = time.time()
        out, _ = pipeline.prepare_partial_unlocked(
            speaker="default", speaker_label="S", en="hi", prev_ar="",
            now_ts=t, cfg=cfg,
        )
        req = {
            "speaker": "default",
            "segment_id": out["segment_id"],
            "revision": out["revision"],
        }
        live_partials = {
            "default": {
                "segment_id": out["segment_id"],
                "revision": out["revision"],
            }
        }
        assert pipeline.is_current_partial_unlocked(req, live_partials) is True

    def test_returns_false_when_partial_not_in_live_partials(self, pipeline, cfg):
        t = time.time()
        out, _ = pipeline.prepare_partial_unlocked(
            speaker="default", speaker_label="S", en="hi", prev_ar="",
            now_ts=t, cfg=cfg,
        )
        req = {
            "speaker": "default",
            "segment_id": out["segment_id"],
            "revision": out["revision"],
        }
        # live_partials is empty
        assert pipeline.is_current_partial_unlocked(req, {}) is False
