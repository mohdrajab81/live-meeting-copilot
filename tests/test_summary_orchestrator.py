"""
Unit tests for app.controller.summary_orchestrator.SummaryOrchestrator.

Covers: clear_unlocked, snapshot_unlocked, _build_transcript_text_unlocked,
run_summary (enabled/disabled/empty/success/error/pending-guard),
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
) -> tuple[SummaryOrchestrator, MagicMock, AsyncMock, AsyncMock]:
    lock = threading.RLock()
    summary_svc = MagicMock()
    summary_svc.is_configured = is_configured

    broadcast = AsyncMock()
    broadcast_log = AsyncMock()

    if finals is None:
        finals = []
    get_finals = MagicMock(return_value=finals)
    get_config = lambda: RuntimeConfig(summary_enabled=summary_enabled)

    orch = SummaryOrchestrator(
        lock=lock,
        summary_service=summary_svc,
        broadcast=broadcast,
        broadcast_log=broadcast_log,
        get_finals=get_finals,
        get_config=get_config,
    )
    return orch, summary_svc, broadcast, broadcast_log


def _make_result(**kwargs) -> SummaryResult:
    defaults = dict(
        executive_summary="Good meeting.",
        key_points=["point A", "point B"],
        action_items=[{"item": "Follow up", "owner": "Alice", "due_date": None}],
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

    orch.clear_unlocked()

    assert orch.summary_pending is False
    assert orch.summary_result is None
    assert orch.summary_generated_ts is None
    assert orch.summary_error == ""


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
        "action_items": [{"item": "do x", "owner": "A", "due_date": None}],
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
