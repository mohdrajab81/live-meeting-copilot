"""
Integration tests for the REST API routes.

Builds a minimal FastAPI test app with a mocked AppController so no real
Azure credentials or speech SDK are needed.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from app.api.routes import router as api_router


# ---------------------------------------------------------------------------
# Mock controller factory
# ---------------------------------------------------------------------------

def _make_controller(running=False):
    ctrl = MagicMock()
    ctrl.running = running

    ctrl.snapshot.return_value = {
        "type": "snapshot",
        "status": "idle",
        "running": running,
        "session_started_ts": 0.0,
        "config": {},
        "en_live": "",
        "ar_live": "",
        "live_partials": [],
        "finals": [],
        "logs": [],
        "recording": {"started_ts": None, "accumulated_ms": 0, "total_ms": 0},
        "coach": {"configured": False, "pending": False, "hints": [], "queued": False,
                  "last_sent_final_idx": 0},
        "topics": {"definitions": []},
        "telemetry": {},
    }
    ctrl.get_config.return_value = {}
    ctrl.start = MagicMock(return_value=True)
    ctrl.stop = MagicMock(return_value=True)
    ctrl.stop_async = AsyncMock(return_value=True)
    ctrl.clear_logs = MagicMock()
    ctrl.clear_transcript = MagicMock()
    ctrl.clear_coach = MagicMock()
    ctrl.clear_topics = MagicMock()
    ctrl.save_config_to_disk = MagicMock(return_value="web_translator_settings.json")
    ctrl.reload_config_from_disk = MagicMock(return_value={})
    ctrl.reset_config_to_defaults = MagicMock(return_value={})
    ctrl.set_config = MagicMock()
    ctrl.broadcast_log = AsyncMock()
    ctrl.broadcast = AsyncMock()

    ctrl.coach = MagicMock()
    ctrl.coach.is_configured = False

    ctrl.request_coach = AsyncMock(return_value={"suggestion": "test hint", "ts": 1.0,
                                                   "type": "coach"})
    ctrl.configure_topics = MagicMock(return_value={
        "definitions": [],
    })

    from app.config import RuntimeConfig
    ctrl.get_runtime_config = MagicMock(return_value=RuntimeConfig())
    ctrl.summary_service = MagicMock()
    ctrl.summary_service.is_configured = True
    _default_summary_snap = {
        "configured": True, "pending": False, "error": "",
        "generated_ts": None, "result": None,
    }
    ctrl.generate_summary = AsyncMock(return_value=_default_summary_snap)
    ctrl.clear_summary = MagicMock()
    ctrl.summary_snapshot = MagicMock(return_value=_default_summary_snap)
    return ctrl


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """TestClient with loopback-only auth."""
    app = FastAPI()
    app.include_router(api_router, prefix="/api")
    ctrl = _make_controller()
    app.state.controller = ctrl
    return TestClient(app), ctrl


@pytest.fixture
def client_running():
    """TestClient with a running controller."""
    app = FastAPI()
    app.include_router(api_router, prefix="/api")
    ctrl = _make_controller(running=True)
    app.state.controller = ctrl
    return TestClient(app), ctrl


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class TestAuth:
    def test_loopback_testclient_passes(self, client):
        tc, _ = client
        r = tc.get("/api/state")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/state
# ---------------------------------------------------------------------------

class TestGetState:
    def test_returns_200(self, client):
        tc, _ = client
        r = tc.get("/api/state")
        assert r.status_code == 200

    def test_returns_snapshot_from_controller(self, client):
        tc, ctrl = client
        r = tc.get("/api/state")
        ctrl.snapshot.assert_called_once()


# ---------------------------------------------------------------------------
# GET /api/config
# ---------------------------------------------------------------------------

class TestGetConfig:
    def test_returns_200(self, client):
        tc, _ = client
        r = tc.get("/api/config")
        assert r.status_code == 200

    def test_calls_get_config(self, client):
        tc, ctrl = client
        tc.get("/api/config")
        ctrl.get_config.assert_called_once()


# ---------------------------------------------------------------------------
# PUT /api/config
# ---------------------------------------------------------------------------

class TestPutConfig:
    def test_returns_200_when_not_running(self, client):
        tc, _ = client
        r = tc.put("/api/config", json={"capture_mode": "single"})
        assert r.status_code == 200

    def test_returns_409_when_running(self, client_running):
        tc, _ = client_running
        r = tc.put("/api/config", json={"capture_mode": "single"})
        assert r.status_code == 409

    def test_calls_set_config(self, client):
        tc, ctrl = client
        tc.put("/api/config", json={"capture_mode": "single"})
        ctrl.set_config.assert_called_once()


# ---------------------------------------------------------------------------
# POST /api/config/save
# ---------------------------------------------------------------------------

class TestSaveConfig:
    def test_returns_200(self, client):
        tc, _ = client
        r = tc.post("/api/config/save")
        assert r.status_code == 200

    def test_response_contains_config(self, client):
        tc, _ = client
        r = tc.post("/api/config/save")
        assert "config" in r.json()


# ---------------------------------------------------------------------------
# POST /api/config/reload
# ---------------------------------------------------------------------------

class TestReloadConfig:
    def test_returns_200_when_not_running(self, client):
        tc, _ = client
        r = tc.post("/api/config/reload")
        assert r.status_code == 200

    def test_returns_409_when_running(self, client_running):
        tc, _ = client_running
        r = tc.post("/api/config/reload")
        assert r.status_code == 409

    def test_returns_404_when_file_not_found(self, client):
        tc, ctrl = client
        ctrl.reload_config_from_disk.side_effect = FileNotFoundError("not found")
        r = tc.post("/api/config/reload")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/config/reset-defaults
# ---------------------------------------------------------------------------

class TestResetDefaults:
    def test_returns_200_when_not_running(self, client):
        tc, _ = client
        r = tc.post("/api/config/reset-defaults")
        assert r.status_code == 200

    def test_returns_409_when_running(self, client_running):
        tc, _ = client_running
        r = tc.post("/api/config/reset-defaults")
        assert r.status_code == 409


# ---------------------------------------------------------------------------
# POST /api/start / /api/stop
# ---------------------------------------------------------------------------

class TestStartStop:
    def test_start_returns_200(self, client):
        tc, _ = client
        r = tc.post("/api/start")
        assert r.status_code == 200

    def test_start_response_has_started_field(self, client):
        tc, _ = client
        r = tc.post("/api/start")
        assert "started" in r.json()

    def test_stop_returns_200(self, client):
        tc, _ = client
        r = tc.post("/api/stop")
        assert r.status_code == 200

    def test_stop_response_has_stopped_field(self, client):
        tc, _ = client
        r = tc.post("/api/stop")
        assert "stopped" in r.json()

    def test_stop_response_has_auto_summary_scheduled_field(self, client):
        tc, _ = client
        r = tc.post("/api/stop")
        assert "auto_summary_scheduled" in r.json()

    def test_stop_false_but_not_running_schedules_auto_summary(self, client, monkeypatch):
        import app.api.routes as routes_mod
        monkeypatch.setattr(routes_mod.asyncio, "sleep", AsyncMock(return_value=None))
        tc, ctrl = client
        ctrl.stop.return_value = False
        ctrl.running = False

        r = tc.post("/api/stop")
        data = r.json()
        assert r.status_code == 200
        assert data["stopped"] is False
        assert data["auto_summary_scheduled"] is True

    def test_stop_false_and_still_running_defers_auto_summary(self, client, monkeypatch):
        import app.api.routes as routes_mod
        monkeypatch.setattr(routes_mod.asyncio, "sleep", AsyncMock(return_value=None))
        tc, ctrl = client
        ctrl.stop.return_value = False
        ctrl.running = True

        r = tc.post("/api/stop")
        data = r.json()
        assert r.status_code == 200
        assert data["stopped"] is False
        assert data["auto_summary_scheduled"] is False


# ---------------------------------------------------------------------------
# POST /api/logs/clear
# ---------------------------------------------------------------------------

class TestClearLogs:
    def test_returns_200(self, client):
        tc, _ = client
        r = tc.post("/api/logs/clear")
        assert r.status_code == 200

    def test_calls_clear_logs(self, client):
        tc, ctrl = client
        tc.post("/api/logs/clear")
        ctrl.clear_logs.assert_called_once()


# ---------------------------------------------------------------------------
# POST /api/transcript/clear
# ---------------------------------------------------------------------------

class TestClearTranscript:
    def test_returns_200(self, client):
        tc, _ = client
        r = tc.post("/api/transcript/clear")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# POST /api/coach/clear
# ---------------------------------------------------------------------------

class TestClearCoach:
    def test_returns_200(self, client):
        tc, _ = client
        r = tc.post("/api/coach/clear")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# POST /api/coach/ask
# ---------------------------------------------------------------------------

class TestCoachAsk:
    def test_returns_412_when_coach_not_configured(self, client):
        tc, _ = client  # ctrl.coach.is_configured = False by default
        r = tc.post("/api/coach/ask", json={"prompt": "hello"})
        assert r.status_code == 412

    def test_returns_200_when_coach_configured(self, client):
        tc, ctrl = client
        ctrl.coach.is_configured = True
        r = tc.post("/api/coach/ask", json={"prompt": "what should I say?"})
        assert r.status_code == 200

    def test_empty_prompt_returns_422(self, client):
        tc, ctrl = client
        ctrl.coach.is_configured = True
        r = tc.post("/api/coach/ask", json={"prompt": "   "})
        assert r.status_code == 422

    def test_missing_prompt_returns_422(self, client):
        tc, _ = client
        r = tc.post("/api/coach/ask", json={})
        assert r.status_code == 422

    def test_prompt_too_long_returns_422(self, client):
        tc, ctrl = client
        ctrl.coach.is_configured = True
        r = tc.post("/api/coach/ask", json={"prompt": "x" * 2001})
        assert r.status_code == 422

    def test_502_on_agent_exception(self, client):
        tc, ctrl = client
        ctrl.coach.is_configured = True
        ctrl.request_coach.side_effect = Exception("agent error")
        r = tc.post("/api/coach/ask", json={"prompt": "hello"})
        assert r.status_code == 502


# ---------------------------------------------------------------------------
# POST /api/topics/configure
# ---------------------------------------------------------------------------

class TestTopicsConfigure:
    def test_returns_200(self, client):
        tc, _ = client
        r = tc.post("/api/topics/configure", json={
            "definitions": [
                {"name": "Budget", "expected_duration_min": 5, "priority": "normal", "order": 0, "comments": "", "id": "budget"}
            ],
        })
        assert r.status_code == 200

    def test_calls_configure_topics(self, client):
        tc, ctrl = client
        defs = [{"name": "A", "expected_duration_min": 1, "priority": "normal", "order": 0, "comments": "", "id": "a"}]
        tc.post("/api/topics/configure", json={"definitions": defs})
        ctrl.configure_topics.assert_called_once_with(
            agenda=[],
            enabled=False,
            allow_new_topics=False,
            interval_sec=60,
            definitions=defs,
        )

    def test_definitions_capped_at_80(self, client):
        tc, _ = client
        defs = [{"name": f"T{i}", "expected_duration_min": 0, "priority": "normal",
                 "order": i, "comments": "", "id": ""} for i in range(90)]
        r = tc.post("/api/topics/configure", json={"definitions": defs})
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/topics/clear
# ---------------------------------------------------------------------------

class TestTopicsClear:
    def test_returns_200(self, client):
        tc, _ = client
        r = tc.post("/api/topics/clear")
        assert r.status_code == 200

    def test_calls_clear_topics(self, client):
        tc, ctrl = client
        tc.post("/api/topics/clear")
        ctrl.clear_topics.assert_called_once()


# ---------------------------------------------------------------------------
# GET /api/audio/devices
# ---------------------------------------------------------------------------

class TestAudioDevices:
    def test_returns_200(self, client, monkeypatch):
        from app.utils import audio_devices
        monkeypatch.setattr(audio_devices, "list_capture_devices", lambda: [])
        tc, _ = client
        r = tc.get("/api/audio/devices")
        assert r.status_code == 200

    def test_response_has_devices_key(self, client, monkeypatch):
        from app.utils import audio_devices
        monkeypatch.setattr(audio_devices, "list_capture_devices", lambda: [{"id": "1", "name": "Mic"}])
        tc, _ = client
        r = tc.get("/api/audio/devices")
        assert "devices" in r.json()


# ---------------------------------------------------------------------------
# POST /api/summary/generate
# ---------------------------------------------------------------------------

class TestSummaryGenerate:
    def test_returns_200_when_configured(self, client):
        tc, _ = client
        r = tc.post("/api/summary/generate")
        assert r.status_code == 200

    def test_response_has_ok_and_summary(self, client):
        tc, _ = client
        r = tc.post("/api/summary/generate")
        data = r.json()
        assert data.get("ok") is True
        assert "summary" in data

    def test_returns_412_when_summary_disabled(self, client, monkeypatch):
        import app.api.routes as routes_mod
        monkeypatch.setattr(routes_mod, "_summary_rate_buckets", {})
        from app.config import RuntimeConfig
        tc, ctrl = client
        ctrl.get_runtime_config.return_value = RuntimeConfig(summary_enabled=False)
        r = tc.post("/api/summary/generate")
        assert r.status_code == 412

    def test_returns_412_when_not_configured(self, client, monkeypatch):
        import app.api.routes as routes_mod
        monkeypatch.setattr(routes_mod, "_summary_rate_buckets", {})
        tc, ctrl = client
        ctrl.summary_service.is_configured = False
        r = tc.post("/api/summary/generate")
        assert r.status_code == 412

    def test_returns_409_on_value_error(self, client, monkeypatch):
        import app.api.routes as routes_mod
        monkeypatch.setattr(routes_mod, "_summary_rate_buckets", {})
        from unittest.mock import AsyncMock
        tc, ctrl = client
        ctrl.generate_summary = AsyncMock(side_effect=ValueError("already pending"))
        r = tc.post("/api/summary/generate")
        assert r.status_code == 409

    def test_returns_502_on_unexpected_error(self, client, monkeypatch):
        import app.api.routes as routes_mod
        monkeypatch.setattr(routes_mod, "_summary_rate_buckets", {})
        from unittest.mock import AsyncMock
        tc, ctrl = client
        ctrl.generate_summary = AsyncMock(side_effect=RuntimeError("Azure error"))
        r = tc.post("/api/summary/generate")
        assert r.status_code == 502

    def test_rate_limit_returns_429_after_2_requests(self, client, monkeypatch):
        import app.api.routes as routes_mod
        monkeypatch.setattr(routes_mod, "_summary_rate_buckets", {})
        tc, _ = client
        tc.post("/api/summary/generate")
        tc.post("/api/summary/generate")
        r = tc.post("/api/summary/generate")
        assert r.status_code == 429


# ---------------------------------------------------------------------------
# POST /api/summary/clear
# ---------------------------------------------------------------------------

class TestSummaryClear:
    def test_returns_200(self, client):
        tc, _ = client
        r = tc.post("/api/summary/clear")
        assert r.status_code == 200

    def test_calls_clear_summary(self, client):
        tc, ctrl = client
        tc.post("/api/summary/clear")
        ctrl.clear_summary.assert_called_once()

    def test_broadcasts_summary_cleared(self, client):
        tc, ctrl = client
        tc.post("/api/summary/clear")
        ctrl.broadcast.assert_awaited_once()
        payload = ctrl.broadcast.await_args.args[0]
        assert payload["type"] == "summary_cleared"


# ---------------------------------------------------------------------------
# GET /api/summary
# ---------------------------------------------------------------------------

class TestGetSummary:
    def test_returns_200(self, client):
        tc, _ = client
        r = tc.get("/api/summary")
        assert r.status_code == 200

    def test_response_has_summary_key(self, client):
        tc, _ = client
        r = tc.get("/api/summary")
        assert "summary" in r.json()

    def test_calls_summary_snapshot(self, client):
        tc, ctrl = client
        tc.get("/api/summary")
        ctrl.summary_snapshot.assert_called_once()


# ---------------------------------------------------------------------------
# POST /api/summary/from-transcript
# ---------------------------------------------------------------------------

_VALID_CSV = (
    "index,speaker,speaker_label,time_local,time_unix_sec,bookmarked,bookmark_note,english,arabic\n"
    "0,A,Interviewer,2024-01-01 10:00:00,1704067200.0,False,,Hello world,\n"
    "1,B,Candidate,2024-01-01 10:01:00,1704067260.0,False,,Thank you for having me,\n"
)
_VALID_ENRICHED_CSV = (
    "index,speaker,speaker_label,time_local,time_unix_sec,start_unix_sec,end_unix_sec,duration_sec,offset_sec,timing_source,recognizer_session_id,bookmarked,bookmark_note,english,arabic\n"
    "0,A,Interviewer,2024-01-01 10:00:00,1704067200.0,1704067195.0,1704067200.0,5.0,0.0,offset,session-a,False,,Hello world,\n"
    "1,B,Candidate,2024-01-01 10:01:00,1704067260.0,1704067205.0,1704067212.0,7.0,10.0,offset,session-b,False,,Thank you for having me,\n"
)

_MOCK_RESULT = MagicMock(
    executive_summary="Good meeting.",
    key_points=["Point A"],
    action_items=[],
    topic_key_points=[{"topic_name": "Intro", "estimated_duration_minutes": 2.0, "origin": "Inferred", "key_points": ["Point A"]}],
    keywords=["education", "creativity"],
    entities=[{"type": "PERSON", "text": "Alice", "mentions": 1}],
    decisions_made=["Decision 1"],
    risks_and_blockers=[],
    key_terms_defined=[],
    metadata={"meeting_type": "interview", "sentiment_arc": None},
    total_ms=1234,
)


class TestSummaryFromTranscript:
    def _post(self, tc, csv_text=_VALID_CSV, filename="transcript.csv"):
        return tc.post(
            "/api/summary/from-transcript",
            files={"file": (filename, csv_text.encode(), "text/csv")},
        )

    def test_returns_200_on_valid_csv(self, client, monkeypatch):
        import app.api.routes as routes_mod
        monkeypatch.setattr(routes_mod, "_summary_rate_buckets", {})
        tc, ctrl = client
        ctrl.summary_service.generate = MagicMock(return_value=_MOCK_RESULT)
        r = self._post(tc)
        assert r.status_code == 200

    def test_response_shape(self, client, monkeypatch):
        import app.api.routes as routes_mod
        monkeypatch.setattr(routes_mod, "_summary_rate_buckets", {})
        tc, ctrl = client
        ctrl.summary_service.generate = MagicMock(return_value=_MOCK_RESULT)
        data = self._post(tc).json()
        assert data.get("ok") is True
        result = data.get("result", {})
        for key in ("executive_summary", "key_points", "action_items",
                    "topic_key_points", "keywords", "topic_breakdown", "agenda_adherence_pct",
                    "entities", "decisions_made", "risks_and_blockers", "key_terms_defined",
                    "meeting_insights", "keyword_index",
                    "metadata", "total_ms"):
            assert key in result, f"missing key: {key}"

    def test_returns_412_when_not_configured(self, client, monkeypatch):
        import app.api.routes as routes_mod
        monkeypatch.setattr(routes_mod, "_summary_rate_buckets", {})
        tc, ctrl = client
        ctrl.summary_service.is_configured = False
        r = self._post(tc)
        assert r.status_code == 412

    def test_returns_413_when_file_too_large(self, client, monkeypatch):
        import app.api.routes as routes_mod
        monkeypatch.setattr(routes_mod, "_summary_rate_buckets", {})
        tc, ctrl = client
        big = "x" * (5 * 1024 * 1024 + 2)
        r = self._post(tc, csv_text=big)
        assert r.status_code == 413

    def test_returns_400_on_empty_transcript(self, client, monkeypatch):
        import app.api.routes as routes_mod
        monkeypatch.setattr(routes_mod, "_summary_rate_buckets", {})
        tc, ctrl = client
        # CSV with headers but no usable rows
        empty_csv = "index,speaker,speaker_label,time_local,time_unix_sec,bookmarked,bookmark_note,english,arabic\n"
        r = self._post(tc, csv_text=empty_csv)
        assert r.status_code == 400

    def test_returns_400_on_non_utf8(self, client, monkeypatch):
        import app.api.routes as routes_mod
        monkeypatch.setattr(routes_mod, "_summary_rate_buckets", {})
        tc, ctrl = client
        r = tc.post(
            "/api/summary/from-transcript",
            files={"file": ("t.csv", b"\xff\xfe invalid latin1", "text/csv")},
        )
        assert r.status_code == 400

    def test_returns_502_when_generate_raises(self, client, monkeypatch):
        import app.api.routes as routes_mod
        monkeypatch.setattr(routes_mod, "_summary_rate_buckets", {})
        tc, ctrl = client
        ctrl.summary_service.generate = MagicMock(side_effect=RuntimeError("Azure down"))
        r = self._post(tc)
        assert r.status_code == 502

    def test_rate_limit_returns_429(self, client, monkeypatch):
        import app.api.routes as routes_mod
        monkeypatch.setattr(routes_mod, "_summary_rate_buckets", {})
        tc, ctrl = client
        ctrl.summary_service.generate = MagicMock(return_value=_MOCK_RESULT)
        self._post(tc)
        self._post(tc)
        r = self._post(tc)
        assert r.status_code == 429

    def test_shares_rate_limit_pool_with_generate(self, client, monkeypatch):
        """Consuming the pool via /generate should block /from-transcript."""
        import app.api.routes as routes_mod
        monkeypatch.setattr(routes_mod, "_summary_rate_buckets", {})
        tc, ctrl = client
        ctrl.summary_service.generate = MagicMock(return_value=_MOCK_RESULT)
        tc.post("/api/summary/generate")
        tc.post("/api/summary/generate")
        r = self._post(tc)
        assert r.status_code == 429

    def test_does_not_mutate_session_summary(self, client, monkeypatch):
        """from-transcript must NOT call generate_summary on the controller."""
        import app.api.routes as routes_mod
        monkeypatch.setattr(routes_mod, "_summary_rate_buckets", {})
        tc, ctrl = client
        ctrl.summary_service.generate = MagicMock(return_value=_MOCK_RESULT)
        self._post(tc)
        ctrl.generate_summary.assert_not_called()

    def test_strips_bom_from_utf8_sig(self, client, monkeypatch):
        import app.api.routes as routes_mod
        monkeypatch.setattr(routes_mod, "_summary_rate_buckets", {})
        tc, ctrl = client
        ctrl.summary_service.generate = MagicMock(return_value=_MOCK_RESULT)
        bom_csv = b"\xef\xbb\xbf" + _VALID_CSV.encode()
        r = tc.post(
            "/api/summary/from-transcript",
            files={"file": ("t.csv", bom_csv, "text/csv")},
        )
        assert r.status_code == 200

    def test_accepts_topics_definitions_json_and_passes_context(self, client, monkeypatch):
        import app.api.routes as routes_mod
        monkeypatch.setattr(routes_mod, "_summary_rate_buckets", {})
        tc, ctrl = client
        ctrl.summary_service.generate = MagicMock(return_value=_MOCK_RESULT)
        defs = '[{"name":"Introduction","expected_duration_min":5}]'
        r = tc.post(
            "/api/summary/from-transcript",
            files={"file": ("t.csv", _VALID_CSV.encode(), "text/csv")},
            data={"topics_definitions_json": defs},
        )
        assert r.status_code == 200
        ctrl.summary_service.generate.assert_called_once()
        arg = ctrl.summary_service.generate.call_args.args[0]
        kwargs = ctrl.summary_service.generate.call_args.kwargs
        assert "EXPECTED AGENDA TOPICS (user-defined):" in arg
        assert "- Introduction" in arg
        assert "5 min planned" not in arg
        assert kwargs["session_date_iso"] == "2024-01-01"

    def test_enriched_csv_uses_start_time_for_elapsed_timeline(self, client, monkeypatch):
        import app.api.routes as routes_mod
        monkeypatch.setattr(routes_mod, "_summary_rate_buckets", {})
        tc, ctrl = client
        ctrl.summary_service.generate = MagicMock(return_value=_MOCK_RESULT)
        r = self._post(tc, csv_text=_VALID_ENRICHED_CSV)
        assert r.status_code == 200
        arg = ctrl.summary_service.generate.call_args.args[0]
        kwargs = ctrl.summary_service.generate.call_args.kwargs
        assert "[00:00] [id:U0001] Interviewer: Hello world" in arg
        # start_unix_sec delta: 1704067205 - 1704067195 = 10 seconds
        assert "[00:10] [id:U0002] Candidate: Thank you for having me" in arg
        assert "[id:U0001]" in arg
        assert "[id:U0002]" in arg
        assert kwargs["session_date_iso"] == "2024-01-01"

    def test_from_transcript_computes_topic_minutes_from_utterance_ids(self, client, monkeypatch):
        import app.api.routes as routes_mod
        monkeypatch.setattr(routes_mod, "_summary_rate_buckets", {})
        tc, ctrl = client
        result = MagicMock(
            executive_summary="Good meeting.",
            key_points=["Point A"],
            action_items=[],
            topic_key_points=[
                {
                    "topic_name": "Intro",
                    "estimated_duration_minutes": None,
                    "utterance_ids": ["U0001", "U0002"],
                    "origin": "Inferred",
                    "key_points": ["Point A"],
                }
            ],
            keywords=[],
            entities=[],
            decisions_made=[],
            risks_and_blockers=[],
            key_terms_defined=[],
            metadata={"meeting_type": "Training", "sentiment_arc": None},
            total_ms=123,
        )
        ctrl.summary_service.generate = MagicMock(return_value=result)
        data = self._post(tc, csv_text=_VALID_ENRICHED_CSV).json()
        topic = data["result"]["topic_key_points"][0]
        # coverage_with_gaps default:
        # duration_sec = 5 + 7 = 12 sec, plus inter-utterance gap 5 sec (same topic)
        # total 17 sec -> 0.3 min
        assert topic["estimated_duration_minutes"] == 0.3
