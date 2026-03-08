"""
Tests for app.controller.coach_orchestrator.CoachOrchestrator.
"""

import threading
import time
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.config import RuntimeConfig
from app.controller.coach_orchestrator import CoachOrchestrator


# ---------------------------------------------------------------------------
# Factory helper
# ---------------------------------------------------------------------------

def _make_coach(is_configured=True, supports_conv=True):
    coach = MagicMock()
    coach.is_configured = is_configured
    coach.supports_conversations_create.return_value = supports_conv
    coach.get_chain_state.return_value = {}
    coach.ask = MagicMock(return_value=MagicMock(
        text="great answer",
        response_id="resp-1",
        conversation_id="conv-1",
        create_ms=50,
        approve_ms=10,
        approval_rounds=1,
        approval_count=1,
        total_ms=200,
    ))
    return coach


def _make_orchestrator(coach=None, finals=None):
    lock = threading.RLock()
    coach = coach or _make_coach()
    finals_list = list(finals or [])
    orch = CoachOrchestrator(
        lock=lock,
        coach=coach,
        broadcast=AsyncMock(),
        broadcast_log=AsyncMock(),
        broadcast_from_thread=MagicMock(),
        append_log=MagicMock(return_value={"type": "log", "level": "debug", "message": "", "ts": 0.0}),
        get_finals=lambda: finals_list,
        get_config=lambda: RuntimeConfig(),
        preview_text=lambda t, n=220: t[:n],
    )
    return orch


def _final_item(speaker="remote", en="tell me about yourself"):
    return {
        "speaker": speaker,
        "speaker_label": "Interviewer" if speaker == "remote" else "You",
        "en": en,
        "ar": "",
        "ts": time.time(),
        "segment_id": "seg-1",
        "revision": 1,
    }


# ---------------------------------------------------------------------------
# _append_hint_unlocked / cap at 120
# ---------------------------------------------------------------------------

class TestHintCap:
    def test_hints_capped_at_120(self):
        orch = _make_orchestrator()
        for i in range(130):
            orch._append_hint_unlocked({"ts": float(i), "suggestion": f"hint {i}"})
        assert len(orch.coach_hints) == 120

    def test_cap_keeps_newest_entries(self):
        orch = _make_orchestrator()
        for i in range(130):
            orch._append_hint_unlocked({"ts": float(i), "suggestion": f"hint {i}"})
        assert orch.coach_hints[-1]["suggestion"] == "hint 129"
        assert orch.coach_hints[0]["suggestion"] == "hint 10"

    def test_below_cap_all_kept(self):
        orch = _make_orchestrator()
        for i in range(10):
            orch._append_hint_unlocked({"ts": float(i), "suggestion": f"hint {i}"})
        assert len(orch.coach_hints) == 10


# ---------------------------------------------------------------------------
# should_trigger_unlocked
# ---------------------------------------------------------------------------

class TestShouldTrigger:
    def test_returns_false_when_coach_disabled(self):
        orch = _make_orchestrator()
        config = RuntimeConfig(coach_enabled=False)
        assert not orch.should_trigger_unlocked({"speaker": "remote"}, config)

    def test_returns_false_when_not_configured(self):
        orch = _make_orchestrator(coach=_make_coach(is_configured=False))
        config = RuntimeConfig(coach_enabled=True)
        assert not orch.should_trigger_unlocked({"speaker": "remote"}, config)

    def test_returns_false_within_cooldown(self):
        orch = _make_orchestrator()
        orch.coach_last_run_ts = time.time()  # just ran
        config = RuntimeConfig(coach_enabled=True, coach_cooldown_sec=30)
        assert not orch.should_trigger_unlocked({"speaker": "remote"}, config)

    def test_returns_true_after_cooldown_expired(self):
        orch = _make_orchestrator()
        orch.coach_last_run_ts = time.time() - 60  # long ago
        config = RuntimeConfig(coach_enabled=True, coach_cooldown_sec=10,
                               coach_trigger_speaker="remote")
        assert orch.should_trigger_unlocked({"speaker": "remote"}, config)

    def test_returns_false_when_busy_and_not_ignored(self):
        orch = _make_orchestrator()
        orch.coach_pending = True
        orch.coach_last_run_ts = 0
        config = RuntimeConfig(coach_enabled=True, coach_cooldown_sec=0)
        assert not orch.should_trigger_unlocked({"speaker": "remote"}, config)

    def test_returns_true_when_busy_but_ignore_busy(self):
        orch = _make_orchestrator()
        orch.coach_pending = True
        orch.coach_last_run_ts = 0
        config = RuntimeConfig(coach_enabled=True, coach_cooldown_sec=0,
                               coach_trigger_speaker="remote")
        assert orch.should_trigger_unlocked({"speaker": "remote"}, config, ignore_busy=True)

    def test_speaker_filter_any_accepts_all(self):
        orch = _make_orchestrator()
        orch.coach_last_run_ts = 0
        config = RuntimeConfig(coach_enabled=True, coach_trigger_speaker="any", coach_cooldown_sec=0)
        assert orch.should_trigger_unlocked({"speaker": "local"}, config)
        assert orch.should_trigger_unlocked({"speaker": "remote"}, config)
        assert orch.should_trigger_unlocked({"speaker": "default"}, config)

    def test_speaker_filter_remote_rejects_local(self):
        orch = _make_orchestrator()
        orch.coach_last_run_ts = 0
        config = RuntimeConfig(coach_enabled=True, coach_trigger_speaker="remote", coach_cooldown_sec=0)
        assert not orch.should_trigger_unlocked({"speaker": "local"}, config)

    def test_speaker_filter_local_accepts_local(self):
        orch = _make_orchestrator()
        orch.coach_last_run_ts = 0
        config = RuntimeConfig(coach_enabled=True, coach_trigger_speaker="local", coach_cooldown_sec=0)
        assert orch.should_trigger_unlocked({"speaker": "local"}, config)

    def test_single_mode_default_speaker_ignores_trigger_filter(self):
        orch = _make_orchestrator()
        orch.coach_last_run_ts = 0
        config = RuntimeConfig(
            coach_enabled=True,
            capture_mode="single",
            coach_trigger_speaker="remote",
            coach_cooldown_sec=0,
        )
        assert orch.should_trigger_unlocked({"speaker": "default"}, config)

    def test_ignore_cooldown_bypasses_cooldown(self):
        orch = _make_orchestrator()
        orch.coach_last_run_ts = time.time()  # just ran
        config = RuntimeConfig(coach_enabled=True, coach_cooldown_sec=30,
                               coach_trigger_speaker="remote")
        assert orch.should_trigger_unlocked(
            {"speaker": "remote"}, config, ignore_cooldown=True
        )


# ---------------------------------------------------------------------------
# reset_runtime_unlocked
# ---------------------------------------------------------------------------

class TestResetRuntime:
    def test_resets_pending_to_false(self):
        finals = [_final_item()]
        orch = _make_orchestrator(finals=finals)
        orch.coach_pending = True
        orch.reset_runtime_unlocked(keep_history=True)
        assert orch.coach_pending is False

    def test_resets_last_run_ts_to_zero(self):
        orch = _make_orchestrator()
        orch.coach_last_run_ts = 999.0
        orch.reset_runtime_unlocked(keep_history=True)
        assert orch.coach_last_run_ts == 0.0

    def test_resets_sent_index_to_finals_length(self):
        finals = [_final_item(), _final_item()]
        orch = _make_orchestrator(finals=finals)
        orch.coach_last_sent_final_idx = 0
        orch.reset_runtime_unlocked(keep_history=True)
        assert orch.coach_last_sent_final_idx == 2

    def test_clears_queued_trigger(self):
        orch = _make_orchestrator()
        orch.coach_queued_trigger = {"speaker": "remote"}
        orch.reset_runtime_unlocked(keep_history=True)
        assert orch.coach_queued_trigger is None

    def test_keep_history_true_preserves_hints(self):
        orch = _make_orchestrator()
        orch._append_hint_unlocked({"ts": 1.0, "suggestion": "keep me"})
        orch.reset_runtime_unlocked(keep_history=True)
        assert len(orch.coach_hints) == 1

    def test_keep_history_false_clears_hints(self):
        orch = _make_orchestrator()
        orch._append_hint_unlocked({"ts": 1.0, "suggestion": "gone"})
        orch.reset_runtime_unlocked(keep_history=False)
        assert len(orch.coach_hints) == 0


# ---------------------------------------------------------------------------
# prepare_call_unlocked
# ---------------------------------------------------------------------------

class TestPrepareCallUnlocked:
    def test_returns_none_when_no_text_in_trigger(self):
        finals = [_final_item()]
        orch = _make_orchestrator(finals=finals)
        orch.coach_last_sent_final_idx = 0
        orch.coach_last_run_ts = 0
        config = RuntimeConfig(coach_enabled=True, coach_cooldown_sec=0,
                               coach_trigger_speaker="remote")
        item = {"speaker": "remote", "en": "", "ar": "", "speaker_label": "Int"}
        assert orch.prepare_call_unlocked(item, config) is None

    def test_returns_none_when_delta_is_empty(self):
        finals = [_final_item()]
        orch = _make_orchestrator(finals=finals)
        orch.coach_last_sent_final_idx = 1  # already at end
        orch.coach_last_run_ts = 0
        config = RuntimeConfig(coach_enabled=True, coach_cooldown_sec=0,
                               coach_trigger_speaker="remote")
        item = _final_item()
        assert orch.prepare_call_unlocked(item, config) is None

    def test_returns_tuple_with_prompt_and_group(self):
        finals = [_final_item("remote", "what is your strength?")]
        orch = _make_orchestrator(finals=finals)
        orch.coach_last_sent_final_idx = 0
        orch.coach_last_run_ts = 0
        config = RuntimeConfig(
            coach_enabled=True, coach_cooldown_sec=0,
            coach_trigger_speaker="remote", coach_max_turns=8,
        )
        item = _final_item("remote", "what is your strength?")
        result = orch.prepare_call_unlocked(item, config)
        assert result is not None
        prompt, group_id, trigger_ts, end_idx = result
        assert isinstance(prompt, str)
        assert "what is your strength?" in prompt
        assert group_id.startswith("coach-")
        assert end_idx == 1

    def test_first_prompt_uses_meeting_brief_and_full_transcript(self):
        finals = [
            _final_item("remote", "What is your strength?"),
            _final_item("local", "I lead backend delivery."),
        ]
        orch = _make_orchestrator(finals=finals)
        orch.coach_last_sent_final_idx = 0
        orch.coach_last_run_ts = 0
        config = RuntimeConfig(
            coach_enabled=True,
            coach_cooldown_sec=0,
            coach_trigger_speaker="remote",
            coach_instruction=(
                "Meeting date: 2026-03-06\n"
                "Attendees: Omar, Sara\n"
                "Meeting objective: Status review"
            ),
        )

        result = orch.prepare_call_unlocked(_final_item("remote", "What is your strength?"), config)

        assert result is not None
        prompt = result[0]
        assert "Pre-meeting context:" in prompt
        assert "Meeting date: 2026-03-06" in prompt
        assert "Latest triggering utterance:" in prompt
        assert "Meeting transcript (full, from session start):" in prompt
        assert "You are my live meeting copilot." not in prompt
        assert "Return format:" not in prompt

    def test_follow_up_prompt_uses_delta_only(self):
        finals = [
            _final_item("remote", "Earlier turn"),
            _final_item("remote", "Newest turn"),
        ]
        orch = _make_orchestrator(finals=finals)
        orch.coach_last_sent_final_idx = 1
        orch.coach_last_run_ts = 0
        config = RuntimeConfig(
            coach_enabled=True,
            coach_cooldown_sec=0,
            coach_trigger_speaker="remote",
            coach_instruction="Meeting date: 2026-03-06",
        )

        result = orch.prepare_call_unlocked(_final_item("remote", "Newest turn"), config)

        assert result is not None
        prompt = result[0]
        assert "Latest triggering utterance:" in prompt
        assert "Transcript delta since last update:" in prompt
        assert "Meeting transcript (full, from session start):" not in prompt
        assert "Pre-meeting context:" not in prompt
        assert "Earlier turn" not in prompt
        assert "Newest turn" in prompt

    def test_sets_coach_pending_after_call(self):
        finals = [_final_item()]
        orch = _make_orchestrator(finals=finals)
        orch.coach_last_sent_final_idx = 0
        orch.coach_last_run_ts = 0
        config = RuntimeConfig(
            coach_enabled=True, coach_cooldown_sec=0,
            coach_trigger_speaker="remote",
        )
        orch.prepare_call_unlocked(_final_item(), config)
        assert orch.coach_pending is True

    def test_prompt_truncated_by_max_turns(self):
        finals = [_final_item(en=f"turn {i}") for i in range(20)]
        orch = _make_orchestrator(finals=finals)
        orch.coach_last_sent_final_idx = 0
        orch.coach_last_run_ts = 0
        config = RuntimeConfig(
            coach_enabled=True, coach_cooldown_sec=0,
            coach_trigger_speaker="remote", coach_max_turns=3,
        )
        result = orch.prepare_call_unlocked(_final_item(), config)
        assert result is not None
        prompt = result[0]
        # Only last 3 turns should appear; early ones should not
        assert "turn 0" not in prompt

    def test_single_mode_default_speaker_still_prepares_call(self):
        finals = [_final_item("default", "single mode turn")]
        orch = _make_orchestrator(finals=finals)
        orch.coach_last_sent_final_idx = 0
        orch.coach_last_run_ts = 0
        config = RuntimeConfig(
            coach_enabled=True,
            capture_mode="single",
            coach_cooldown_sec=0,
            coach_trigger_speaker="remote",
        )

        result = orch.prepare_call_unlocked(_final_item("default", "single mode turn"), config)

        assert result is not None
        assert "single mode turn" in result[0]


# ---------------------------------------------------------------------------
# snapshot_unlocked
# ---------------------------------------------------------------------------

class TestSnapshot:
    def test_snapshot_structure(self):
        orch = _make_orchestrator()
        snap = orch.snapshot_unlocked()
        assert "configured" in snap
        assert "pending" in snap
        assert "hints" in snap
        assert "last_sent_final_idx" in snap
        assert isinstance(snap["hints"], list)

    def test_queued_false_when_no_queued_trigger(self):
        orch = _make_orchestrator()
        snap = orch.snapshot_unlocked()
        assert snap["queued"] is False

    def test_queued_true_when_trigger_queued(self):
        orch = _make_orchestrator()
        orch.coach_queued_trigger = {"speaker": "remote"}
        snap = orch.snapshot_unlocked()
        assert snap["queued"] is True


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------

class TestClear:
    def test_clear_resets_hints_and_pending(self):
        orch = _make_orchestrator()
        orch._append_hint_unlocked({"ts": 1.0, "suggestion": "hint"})
        orch.coach_pending = True
        coach = _make_coach()
        orch.clear(coach_service=coach)
        assert orch.coach_hints == []
        assert orch.coach_pending is False

    def test_clear_calls_coach_clear_conversation(self):
        orch = _make_orchestrator()
        coach = _make_coach()
        orch.clear(coach_service=coach)
        coach.clear_conversation.assert_called_once()


@pytest.mark.asyncio
async def test_run_coach_logs_exact_prompt_when_debug_enabled():
    orch = _make_orchestrator()
    orch._get_config = lambda: RuntimeConfig(debug=True)
    prompt = "Exact prompt body"
    trigger = _final_item()

    await orch.run_coach(
        prompt,
        trigger,
        group_id="coach-1",
        trigger_ts=time.time(),
        inflight_end_idx=1,
    )

    messages = [call.args[1] for call in orch._broadcast_log.await_args_list]
    assert any("Coach deep prompt exact: group=coach-1" in msg for msg in messages)
    assert any("Exact prompt body" in msg for msg in messages)


@pytest.mark.asyncio
async def test_run_coach_drops_no_answer_needed_reply():
    coach = _make_coach()
    coach.ask.return_value = MagicMock(
        text="no_answer_needed",
        response_id="resp-1",
        conversation_id="conv-1",
        create_ms=50,
        approve_ms=10,
        approval_rounds=1,
        approval_count=1,
        total_ms=200,
    )
    orch = _make_orchestrator(coach=coach)

    await orch.run_coach(
        "Prompt",
        _final_item(),
        group_id="coach-2",
        trigger_ts=time.time(),
        inflight_end_idx=3,
    )

    assert orch.coach_hints == []
    orch._broadcast.assert_not_awaited()
    assert orch.coach_last_sent_final_idx == 3
    messages = [call.args[1] for call in orch._broadcast_log.await_args_list]
    assert any("reason=no_answer_needed" in msg for msg in messages)


@pytest.mark.asyncio
async def test_request_manual_logs_exact_prompt_when_debug_enabled():
    orch = _make_orchestrator()
    orch._get_config = lambda: RuntimeConfig(debug=True)

    await orch.request_manual(prompt="What happened in the meeting?", speaker_label="Manual")

    messages = [call.args[1] for call in orch._broadcast_log.await_args_list]
    assert any("Coach manual prompt exact:" in msg for msg in messages)
    assert any("Manual user message (same conversation):" in msg for msg in messages)
    assert any("What happened in the meeting?" in msg for msg in messages)


@pytest.mark.asyncio
async def test_request_manual_drops_no_answer_needed_reply():
    coach = _make_coach()
    coach.ask.return_value = MagicMock(
        text="no_answer_needed",
        response_id="resp-1",
        conversation_id="conv-1",
        create_ms=50,
        approve_ms=10,
        approval_rounds=1,
        approval_count=1,
        total_ms=200,
    )
    orch = _make_orchestrator(coach=coach)

    hint = await orch.request_manual(prompt="hello", speaker_label="Manual")

    assert hint is None
    assert orch.coach_hints == []
    orch._broadcast.assert_not_awaited()
    messages = [call.args[1] for call in orch._broadcast_log.await_args_list]
    assert any("Coach manual reply dropped: reason=no_answer_needed" in msg for msg in messages)
