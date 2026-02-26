"""
Unit tests for app.services.summary.SummaryService.

Covers: _extract_structured, _normalize_action_items, from_environment,
is_configured, close (no real Azure calls needed).
"""

import json
import os
import threading
from unittest.mock import MagicMock, patch

import pytest

from app.services.summary import SummaryResult, SummaryService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(**kwargs) -> SummaryService:
    defaults = dict(
        project_endpoint="https://example.openai.azure.com",
        model_deployment="gpt-4o",
        agent_ref="asst_abc123",
    )
    defaults.update(kwargs)
    return SummaryService(**defaults)


# ---------------------------------------------------------------------------
# is_configured
# ---------------------------------------------------------------------------

def test_is_configured_true_when_all_set():
    svc = _make_service()
    assert svc.is_configured is True


def test_is_configured_false_when_endpoint_missing():
    svc = _make_service(project_endpoint="")
    assert svc.is_configured is False


def test_is_configured_false_when_model_missing():
    svc = _make_service(model_deployment="")
    assert svc.is_configured is False


def test_is_configured_false_when_agent_missing():
    svc = _make_service(agent_ref="")
    assert svc.is_configured is False


# ---------------------------------------------------------------------------
# _extract_structured
# ---------------------------------------------------------------------------

def test_extract_structured_plain_json():
    svc = _make_service()
    payload = {"executive_summary": "Brief summary.", "key_points": ["p1"], "action_items": []}
    result = svc._extract_structured(json.dumps(payload))
    assert result["executive_summary"] == "Brief summary."
    assert result["key_points"] == ["p1"]


def test_extract_structured_strips_markdown_fences():
    svc = _make_service()
    payload = {"executive_summary": "S", "key_points": [], "action_items": []}
    text = f"```json\n{json.dumps(payload)}\n```"
    result = svc._extract_structured(text)
    assert result["executive_summary"] == "S"


def test_extract_structured_strips_plain_fences():
    svc = _make_service()
    payload = {"executive_summary": "X", "key_points": [], "action_items": []}
    text = f"```\n{json.dumps(payload)}\n```"
    result = svc._extract_structured(text)
    assert result["executive_summary"] == "X"


def test_extract_structured_raises_on_missing_executive_summary():
    svc = _make_service()
    payload = {"key_points": [], "action_items": []}
    with pytest.raises(ValueError, match="executive_summary"):
        svc._extract_structured(json.dumps(payload))


def test_extract_structured_raises_on_no_json():
    svc = _make_service()
    with pytest.raises(ValueError, match="No JSON object"):
        svc._extract_structured("no braces here")


def test_extract_structured_raises_on_invalid_json():
    svc = _make_service()
    with pytest.raises(ValueError, match="not valid JSON"):
        svc._extract_structured("{not valid json}")


# ---------------------------------------------------------------------------
# _normalize_action_items
# ---------------------------------------------------------------------------

def test_normalize_action_items_full():
    svc = _make_service()
    items = [{"item": "Fix bug", "owner": "Alice", "due_date": "2026-03-01"}]
    result = svc._normalize_action_items(items)
    assert len(result) == 1
    assert result[0]["item"] == "Fix bug"
    assert result[0]["owner"] == "Alice"
    assert result[0]["due_date"] == "2026-03-01"


def test_normalize_action_items_skips_non_dict():
    svc = _make_service()
    result = svc._normalize_action_items(["string", 42, None])
    assert result == []


def test_normalize_action_items_skips_empty_item():
    svc = _make_service()
    result = svc._normalize_action_items([{"item": "", "owner": "Bob"}])
    assert result == []


def test_normalize_action_items_due_date_none_when_blank():
    svc = _make_service()
    result = svc._normalize_action_items([{"item": "Task", "owner": "", "due_date": ""}])
    assert result[0]["due_date"] is None


# ---------------------------------------------------------------------------
# from_environment
# ---------------------------------------------------------------------------

def test_from_environment_reads_env_vars():
    env = {
        "PROJECT_ENDPOINT": "https://env-endpoint",
        "SUMMARY_MODEL_DEPLOYMENT_NAME": "gpt-4-env",
        "SUMMARY_AGENT_ID": "asst_env",
    }
    with patch.dict(os.environ, env, clear=False):
        svc = SummaryService.from_environment()
    assert svc._project_endpoint == "https://env-endpoint"
    assert svc._model_deployment == "gpt-4-env"
    assert svc._agent_ref == "asst_env"


def test_from_environment_falls_back_to_model_deployment_name():
    env = {
        "PROJECT_ENDPOINT": "https://ep",
        "MODEL_DEPLOYMENT_NAME": "gpt-4-fallback",
        "SUMMARY_AGENT_NAME": "my-agent",
    }
    clean_env = {k: v for k, v in os.environ.items() if k not in (
        "SUMMARY_MODEL_DEPLOYMENT_NAME", "AZURE_AI_MODEL_DEPLOYMENT_NAME"
    )}
    clean_env.update(env)
    with patch.dict(os.environ, clean_env, clear=True):
        svc = SummaryService.from_environment()
    assert svc._model_deployment == "gpt-4-fallback"


# ---------------------------------------------------------------------------
# agent_key detection
# ---------------------------------------------------------------------------

def test_agent_key_is_id_for_asst_prefix():
    svc = _make_service(agent_ref="asst_abc")
    assert svc._agent_key == "id"


def test_agent_key_is_name_for_non_asst():
    svc = _make_service(agent_ref="my-agent-name")
    assert svc._agent_key == "name"


# ---------------------------------------------------------------------------
# close — no exception even when clients are None
# ---------------------------------------------------------------------------

def test_close_with_no_clients_does_not_raise():
    svc = _make_service()
    svc.close()  # clients not initialized — should be a no-op


def test_close_calls_client_close_methods():
    svc = _make_service()
    mock_openai = MagicMock()
    mock_project = MagicMock()
    svc._openai_client = mock_openai
    svc._project_client = mock_project

    svc.close()

    mock_openai.close.assert_called_once()
    mock_project.close.assert_called_once()
    assert svc._openai_client is None
    assert svc._project_client is None
