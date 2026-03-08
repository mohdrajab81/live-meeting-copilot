"""
Tests for app.services.shadow_translation_pipeline.ShadowFinalTranslationPipeline.

Focuses on config gating and client/request behavior; no real Azure calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import Settings
from app.services.shadow_translation_pipeline import ShadowFinalTranslationPipeline


@pytest.fixture
def shadow_settings():
    return Settings(
        AZURE_AI_SERVICES_KEY="test-key",
        PROJECT_ENDPOINT="https://example.services.ai.azure.com/api/projects/test",
        SHADOW_FINAL_TRANSLATION_ENABLED=True,
        SHADOW_FINAL_TRANSLATION_MODEL="gpt-4.1-mini",
        OPENAI_API_VERSION="2024-10-21",
    )


@pytest.fixture
def pipeline(shadow_settings):
    return ShadowFinalTranslationPipeline(
        settings=shadow_settings,
        apply_shadow_result=AsyncMock(),
        log=AsyncMock(),
    )


def test_is_configured_true_when_enabled_and_model_present(pipeline):
    assert pipeline.is_configured is True


def test_is_configured_false_when_disabled(shadow_settings):
    shadow_settings.shadow_final_translation_enabled = False
    pipeline = ShadowFinalTranslationPipeline(
        settings=shadow_settings,
        apply_shadow_result=AsyncMock(),
    )
    assert pipeline.is_configured is False


def test_build_request_returns_none_for_empty_text(pipeline):
    req = pipeline.build_request(
        speaker="remote",
        segment_id="seg-1",
        revision=1,
        text="   ",
        trigger_ts=123.0,
    )
    assert req is None


def test_build_request_populates_expected_fields(pipeline):
    req = pipeline.build_request(
        speaker="remote",
        segment_id="seg-1",
        revision=2,
        text="Project launch is on track.",
        trigger_ts=123.0,
        debug=True,
    )
    assert req is not None
    assert req["kind"] == "final_shadow"
    assert req["speaker"] == "remote"
    assert req["segment_id"] == "seg-1"
    assert req["revision"] == 2
    assert req["provider"] == "azure_openai_shadow"
    assert req["model"] == "gpt-4.1-mini"
    assert req["debug"] is True


def test_reset_unlocked_increments_generation(pipeline):
    before = pipeline._generation
    pipeline.reset_unlocked()
    assert pipeline._generation == before + 1


def test_ensure_client_builds_direct_azure_openai_client(shadow_settings):
    fake_openai_client = MagicMock()

    with patch("openai.AzureOpenAI", return_value=fake_openai_client) as factory:
        pipeline = ShadowFinalTranslationPipeline(
            settings=shadow_settings,
            apply_shadow_result=AsyncMock(),
        )
        client = pipeline._ensure_client()

    assert client is fake_openai_client
    factory.assert_called_once_with(
        azure_endpoint="https://example.services.ai.azure.com",
        api_key="test-key",
        api_version="2024-10-21",
    )


def test_derive_resource_endpoint_strips_project_path():
    value = ShadowFinalTranslationPipeline._derive_resource_endpoint(
        "https://example.services.ai.azure.com/api/projects/test-project"
    )
    assert value == "https://example.services.ai.azure.com"


def test_derive_resource_endpoint_accepts_plain_resource_url():
    value = ShadowFinalTranslationPipeline._derive_resource_endpoint(
        "https://example.services.ai.azure.com"
    )
    assert value == "https://example.services.ai.azure.com"
