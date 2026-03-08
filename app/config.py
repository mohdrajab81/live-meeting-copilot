from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ai_services_key: str = Field(default="", alias="AZURE_AI_SERVICES_KEY")
    ai_services_region: str = Field(default="", alias="AZURE_AI_SERVICES_REGION")
    nova3_api_key: str = Field(default="", alias="NOVA3_API_KEY")
    project_endpoint: str = Field(default="", alias="PROJECT_ENDPOINT")
    openai_api_version: str = Field(default="2024-10-21", alias="OPENAI_API_VERSION")
    shadow_final_translation_enabled: bool = Field(
        default=False,
        alias="SHADOW_FINAL_TRANSLATION_ENABLED",
    )
    shadow_final_translation_model: str = Field(
        default="",
        alias="SHADOW_FINAL_TRANSLATION_MODEL",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    ) 


EnglishRecognitionLanguage = Literal[
    "en-AU",
    "en-CA",
    "en-GB",
    "en-GH",
    "en-HK",
    "en-IE",
    "en-IN",
    "en-KE",
    "en-NG",
    "en-NZ",
    "en-PH",
    "en-SG",
    "en-TZ",
    "en-US",
    "en-ZA",
]


def validate_environment(settings: "Settings") -> None:
    errors = []
    if not settings.ai_services_key:
        errors.append("AZURE_AI_SERVICES_KEY is required (Azure AI Services key)")
    if not settings.ai_services_region:
        errors.append("AZURE_AI_SERVICES_REGION is required (e.g. 'eastus')")
    if errors:
        raise RuntimeError(
            "Configuration errors — check your .env file:\n"
            + "\n".join(f"  • {e}" for e in errors)
        )


class RuntimeConfig(BaseModel):
    class TopicDefinitionConfig(BaseModel):
        id: str = Field(default="", max_length=80)
        name: str = Field(min_length=1, max_length=120)
        expected_duration_min: int = Field(default=0, ge=0, le=600)
        priority: Literal["low", "normal", "high", "mandatory", "optional"] = "normal"
        comments: str = Field(default="", max_length=400)
        order: int = Field(default=0, ge=0, le=10_000)

    speech_provider: Literal["azure", "nova3"] = "azure"
    capture_mode: Literal["single", "dual"] = "single"
    recognition_language: EnglishRecognitionLanguage = "en-US"
    audio_source: Literal["default", "device_id"] = "default"
    input_device_id: str = ""
    local_input_device_id: str = ""
    remote_input_device_id: str = ""
    local_speaker_label: str = "You"
    remote_speaker_label: str = "Remote"
    coach_enabled: bool = False
    coach_trigger_speaker: Literal["remote", "local", "default", "any"] = "remote"
    coach_cooldown_sec: int = Field(default=8, ge=0, le=120)
    coach_max_turns: int = Field(default=8, ge=2, le=30)
    partial_translate_min_interval_sec: float = Field(default=0.6, ge=0.2, le=10.0)
    auto_stop_silence_sec: int = Field(default=75, ge=0, le=3600)
    max_session_sec: int = Field(default=3600, ge=300, le=10800)
    coach_instruction: str = (
        "Meeting date: \n"
        "Attendees: \n"
        "Meeting objective: \n"
        "Key topics on agenda: \n"
        "Background: \n"
        "My role in this meeting: "
    )
    end_silence_ms: int = Field(default=500, ge=200, le=1000)
    initial_silence_ms: int = Field(default=3000, ge=1000, le=120000)
    max_finals: int = Field(default=5000, ge=100, le=10000)
    translation_enabled: bool = True
    summary_enabled: bool = True
    summary_topic_duration_mode: Literal["speech_only", "coverage_with_gaps"] = "coverage_with_gaps"
    summary_topic_gap_threshold_sec: int = Field(default=30, ge=0, le=300)
    topic_definitions: list[TopicDefinitionConfig] = Field(default_factory=list, max_length=80)
    debug: bool = False
