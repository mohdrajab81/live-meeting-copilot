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
        "topics": {"enabled": False, "items": [], "agenda": [], "runs": []},
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
        "enabled": True, "agenda": [], "definitions": [], "items": [],
        "allow_new_topics": True, "chunk_mode": "since_last",
        "interval_sec": 60, "window_sec": 90,
    })
    ctrl.analyze_topics_now = AsyncMock(return_value={
        "enabled": True, "items": [], "agenda": [], "runs": [],
    })
    return ctrl


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client(monkeypatch):
    """TestClient with loopback auth (no token required)."""
    monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
    app = FastAPI()
    app.include_router(api_router, prefix="/api")
    ctrl = _make_controller()
    app.state.controller = ctrl
    return TestClient(app), ctrl


@pytest.fixture
def client_running(monkeypatch):
    """TestClient with a running controller."""
    monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
    app = FastAPI()
    app.include_router(api_router, prefix="/api")
    ctrl = _make_controller(running=True)
    app.state.controller = ctrl
    return TestClient(app), ctrl


@pytest.fixture
def client_token(monkeypatch):
    """TestClient that requires token auth."""
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")
    app = FastAPI()
    app.include_router(api_router, prefix="/api")
    ctrl = _make_controller()
    app.state.controller = ctrl
    return TestClient(app), ctrl


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class TestAuth:
    def test_loopback_testclient_passes_without_token(self, client):
        tc, _ = client
        r = tc.get("/api/state")
        assert r.status_code == 200

    def test_token_mode_no_token_returns_401(self, client_token):
        tc, _ = client_token
        r = tc.get("/api/state")
        assert r.status_code == 401

    def test_token_mode_valid_bearer_passes(self, client_token):
        tc, _ = client_token
        r = tc.get("/api/state", headers={"Authorization": "Bearer test-token"})
        assert r.status_code == 200

    def test_token_mode_invalid_bearer_returns_401(self, client_token):
        tc, _ = client_token
        r = tc.get("/api/state", headers={"Authorization": "Bearer wrong"})
        assert r.status_code == 401

    def test_token_mode_x_api_key_passes(self, client_token):
        tc, _ = client_token
        r = tc.get("/api/state", headers={"X-API-Key": "test-token"})
        assert r.status_code == 200

    def test_token_mode_query_param_passes(self, client_token):
        tc, _ = client_token
        r = tc.get("/api/state", params={"token": "test-token"})
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
            "agenda": ["Budget", "Timeline"],
            "enabled": True,
            "allow_new_topics": True,
            "interval_sec": 60,
            "window_sec": 90,
        })
        assert r.status_code == 200

    def test_calls_configure_topics(self, client):
        tc, ctrl = client
        tc.post("/api/topics/configure", json={
            "agenda": ["A"],
            "enabled": True,
            "allow_new_topics": False,
            "interval_sec": 60,
            "window_sec": 90,
        })
        ctrl.configure_topics.assert_called_once()

    def test_agenda_capped_at_20_by_validation(self, client):
        tc, _ = client
        r = tc.post("/api/topics/configure", json={
            "agenda": [f"Topic {i}" for i in range(25)],  # over the max of 20
            "enabled": True,
            "allow_new_topics": True,
            "interval_sec": 60,
            "window_sec": 90,
        })
        assert r.status_code == 422

    def test_definitions_capped_at_80(self, client):
        tc, _ = client
        defs = [{"name": f"T{i}", "expected_duration_min": 0, "priority": "normal",
                 "order": i, "comments": "", "id": ""} for i in range(90)]
        r = tc.post("/api/topics/configure", json={
            "agenda": [],
            "enabled": True,
            "allow_new_topics": True,
            "interval_sec": 60,
            "window_sec": 90,
            "definitions": defs,
        })
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/topics/analyze-now
# ---------------------------------------------------------------------------

class TestTopicsAnalyzeNow:
    def test_returns_200(self, client):
        tc, _ = client
        r = tc.post("/api/topics/analyze-now")
        assert r.status_code == 200

    def test_returns_409_on_runtime_error(self, client):
        tc, ctrl = client
        ctrl.analyze_topics_now.side_effect = RuntimeError("already running")
        r = tc.post("/api/topics/analyze-now")
        assert r.status_code == 409

    def test_rate_limit_returns_429_after_4_requests(self, client, monkeypatch):
        """Rate limit for /topics/analyze-now is 4/min."""
        import app.api.routes as routes_mod
        monkeypatch.setattr(routes_mod, "_topics_rate_buckets", {})
        tc, _ = client
        for _ in range(4):
            r = tc.post("/api/topics/analyze-now")
            assert r.status_code == 200
        r = tc.post("/api/topics/analyze-now")
        assert r.status_code == 429


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
