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

from app.services.summary import _PROMPT_TEMPLATE, SummaryResult, SummaryService


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
# _normalize_string_list
# ---------------------------------------------------------------------------

def test_normalize_string_list_strips_and_filters():
    svc = _make_service()
    result = svc._normalize_string_list(["  decision 1  ", "", "  ", "decision 2"])
    assert result == ["decision 1", "decision 2"]


def test_normalize_string_list_skips_none_and_empty():
    svc = _make_service()
    # None coerces to "" and is filtered; integers stringify to non-empty so are kept
    result = svc._normalize_string_list([None, "", "  ", "valid"])
    assert result == ["valid"]


def test_normalize_string_list_empty_input():
    svc = _make_service()
    assert svc._normalize_string_list([]) == []


# ---------------------------------------------------------------------------
# _normalize_key_terms
# ---------------------------------------------------------------------------

def test_normalize_key_terms_full():
    svc = _make_service()
    items = [{"term": "API", "definition": "Application Programming Interface"}]
    result = svc._normalize_key_terms(items)
    assert len(result) == 1
    assert result[0]["term"] == "API"
    assert result[0]["definition"] == "Application Programming Interface"


def test_normalize_key_terms_skips_empty_term():
    svc = _make_service()
    result = svc._normalize_key_terms([{"term": "", "definition": "something"}])
    assert result == []


def test_normalize_key_terms_skips_non_dict():
    svc = _make_service()
    result = svc._normalize_key_terms(["not a dict", 42])
    assert result == []


def test_normalize_key_terms_allows_empty_definition():
    svc = _make_service()
    result = svc._normalize_key_terms([{"term": "MVP", "definition": ""}])
    assert len(result) == 1
    assert result[0]["definition"] == ""


# ---------------------------------------------------------------------------
# _normalize_topic_key_points
# ---------------------------------------------------------------------------

def test_normalize_topic_key_points_full():
    svc = _make_service()
    items = [
        {
            "topic_name": "Intro",
            "estimated_duration_minutes": "3.25",
            "utterance_ids": ["u0001", "U0002", "bad-id", "U0002"],
            "origin": "Agenda",
            "key_points": ["A", "B"],
        }
    ]
    result = svc._normalize_topic_key_points(items)
    assert len(result) == 1
    assert result[0]["topic_name"] == "Intro"
    assert result[0]["estimated_duration_minutes"] is None
    assert result[0]["utterance_ids"] == ["U0001", "U0002"]
    assert result[0]["origin"] == "Agenda"
    assert result[0]["key_points"] == ["A", "B"]


def test_normalize_topic_key_points_defaults_origin_inferred():
    svc = _make_service()
    items = [{"topic_name": "Deep Dive", "estimated_duration_minutes": 5, "key_points": []}]
    result = svc._normalize_topic_key_points(items)
    assert result[0]["origin"] == "Inferred"
    assert result[0]["utterance_ids"] == []


def test_normalize_topic_key_points_skips_missing_topic_name():
    svc = _make_service()
    result = svc._normalize_topic_key_points([{"topic_name": "", "key_points": ["x"]}])
    assert result == []


def test_normalize_utterance_ids_from_string():
    svc = _make_service()
    ids = svc._normalize_utterance_ids("u1, U2 bad U003")
    assert ids == ["U1", "U2", "U003"]


# ---------------------------------------------------------------------------
# _normalize_metadata
# ---------------------------------------------------------------------------

def test_normalize_metadata_extracts_valid_fields():
    svc = _make_service()
    result = svc._normalize_metadata({"meeting_type": "Interview", "sentiment_arc": "Positive"})
    assert result["meeting_type"] == "Interview"
    assert result["sentiment_arc"] == "Positive"


def test_normalize_metadata_rejects_invalid_meeting_type():
    svc = _make_service()
    result = svc._normalize_metadata({"meeting_type": "Unknown Type", "sentiment_arc": None})
    assert result["meeting_type"] == ""


def test_normalize_metadata_handles_empty_dict():
    svc = _make_service()
    result = svc._normalize_metadata({})
    assert result.get("meeting_type") == ""
    assert result.get("sentiment_arc") is None


def test_normalize_metadata_handles_non_dict():
    svc = _make_service()
    result = svc._normalize_metadata(None)
    assert result.get("meeting_type") == ""


def test_normalize_metadata_strips_whitespace_from_sentiment():
    svc = _make_service()
    result = svc._normalize_metadata({"meeting_type": "General", "sentiment_arc": "  calm  "})
    assert result["sentiment_arc"] == "calm"


# ---------------------------------------------------------------------------
# _extract_structured — new fields
# ---------------------------------------------------------------------------

def test_extract_structured_new_fields_all_present():
    svc = _make_service()
    payload = {
        "executive_summary": "Good meeting.",
        "key_points": ["p1"],
        "topic_key_points": [
            {"topic_name": "Intro", "estimated_duration_minutes": 2, "origin": "Inferred", "key_points": ["p1"]}
        ],
        "keywords": ["education", "creativity"],
        "entities": [{"type": "PERSON", "text": "Alice", "mentions": 2}],
        "action_items": [],
        "decisions_made": ["Approved budget"],
        "risks_and_blockers": ["Timeline tight"],
        "key_terms_defined": [{"term": "MVP", "definition": "Minimum Viable Product"}],
        "metadata": {"meeting_type": "Project Management", "sentiment_arc": "Positive"},
    }
    result = svc._extract_structured(json.dumps(payload))
    assert result["decisions_made"] == ["Approved budget"]
    assert result["risks_and_blockers"] == ["Timeline tight"]
    assert result["key_terms_defined"][0]["term"] == "MVP"
    assert result["metadata"]["meeting_type"] == "Project Management"
    assert result["topic_key_points"][0]["topic_name"] == "Intro"
    assert result["keywords"] == ["education", "creativity"]
    assert result["entities"][0]["type"] == "PERSON"


def test_extract_structured_new_fields_absent_does_not_raise():
    svc = _make_service()
    payload = {"executive_summary": "Summary.", "key_points": [], "action_items": []}
    result = svc._extract_structured(json.dumps(payload))
    # Missing new fields must not raise — they'll be handled as None in generate()
    assert result.get("decisions_made") is None
    assert result.get("risks_and_blockers") is None
    assert result.get("key_terms_defined") is None
    assert result.get("metadata") is None
    assert result.get("topic_key_points") is None
    assert result.get("keywords") is None
    assert result.get("entities") is None


def test_normalize_keywords_dedup_and_blocked_words():
    svc = _make_service()
    items = ["Education", "education", "think", "Creativity", "", "AI strategy"]
    out = svc._normalize_keywords(items)
    assert out == ["Education", "Creativity", "AI strategy"]


def test_normalize_entities_filters_type_dedup_and_mentions():
    svc = _make_service()
    items = [
        {"type": "person", "text": "Alice", "mentions": "2"},
        {"type": "PERSON", "text": "alice", "mentions": 3},  # duplicate (case-insensitive text)
        {"type": "ORG", "text": "Contoso", "mentions": 1},
        {"type": "UNKNOWN", "text": "x", "mentions": 1},
        {"type": "LOCATION", "text": "", "mentions": 1},
    ]
    out = svc._normalize_entities(items)
    assert out == [
        {"type": "PERSON", "text": "Alice", "mentions": 2},
        {"type": "ORG", "text": "Contoso", "mentions": 1},
    ]


def test_prompt_template_formats_with_transcript_placeholder():
    out = _PROMPT_TEMPLATE.format(
        transcript="[00:00] You: hello",
        valid_utterance_id_ranges="U0001-U0002",
    )
    assert "TRANSCRIPT:" in out
    assert "[00:00] You: hello" in out
    assert "VALID_UTTERANCE_ID_RANGES" in out
    assert "U0001-U0002" in out


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


def test_create_new_conversation_id_from_id():
    svc = _make_service()
    client = MagicMock()
    client.conversations.create.return_value = MagicMock(id="conv_123")
    assert svc._create_new_conversation_id(client) == "conv_123"


def test_create_new_conversation_id_returns_none_when_unsupported():
    svc = _make_service()
    assert svc._create_new_conversation_id(object()) is None


def test_generate_passes_new_conversation_id_when_available():
    svc = _make_service()
    fake_client = MagicMock()
    fake_client.conversations.create.return_value = MagicMock(id="conv_abc")
    fake_client.responses.create.return_value = MagicMock(
        id="resp_1",
        output_text=json.dumps(
            {
                "executive_summary": "Summary.",
                "key_points": [],
                "action_items": [],
            }
        ),
    )
    with patch.object(svc, "_ensure_client", return_value=fake_client):
        result = svc.generate("hello")
    assert result.response_id == "resp_1"
    kwargs = fake_client.responses.create.call_args.kwargs
    assert kwargs.get("conversation") == "conv_abc"


def test_generate_omits_conversation_when_unavailable():
    svc = _make_service()
    fake_client = MagicMock()
    fake_client.conversations = None
    fake_client.responses.create.return_value = MagicMock(
        id="resp_2",
        output_text=json.dumps(
            {
                "executive_summary": "Summary.",
                "key_points": [],
                "action_items": [],
            }
        ),
    )
    with patch.object(svc, "_ensure_client", return_value=fake_client):
        svc.generate("hello")
    kwargs = fake_client.responses.create.call_args.kwargs
    assert "conversation" not in kwargs


def test_extract_valid_utterance_id_ranges_compacts_contiguous_ids():
    svc = _make_service()
    text = (
        "[00:00] Remote: A [id:U0003]\n"
        "[00:01] Remote: B [id:U0001]\n"
        "[00:02] Remote: C [id:U0002]\n"
        "[00:03] Remote: D [id:U0005]\n"
    )
    assert svc._extract_valid_utterance_id_ranges(text) == "U0001-U0003, U0005"


def test_generate_prompt_includes_valid_utterance_id_ranges_guard():
    svc = _make_service()
    fake_client = MagicMock()
    fake_client.conversations = None
    fake_client.responses.create.return_value = MagicMock(
        id="resp_guard",
        output_text=json.dumps(
            {
                "executive_summary": "Summary.",
                "key_points": [],
                "action_items": [],
            }
        ),
    )
    with patch.object(svc, "_ensure_client", return_value=fake_client):
        svc.generate("[00:00] Remote: x [id:U0001]\n[00:02] Remote: y [id:U0002]")
    kwargs = fake_client.responses.create.call_args.kwargs
    prompt = kwargs.get("input") or ""
    assert "VALID_UTTERANCE_ID_RANGES:" in prompt
    assert "U0001-U0002" in prompt
