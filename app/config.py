from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ai_services_key: str = Field(default="", alias="AZURE_AI_SERVICES_KEY")
    ai_services_region: str = Field(default="", alias="AZURE_AI_SERVICES_REGION")

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
        "Give a short suggested reply for me, tailored to my profile. "
        "Use concise bullets and keep claims truthful to known background."
    )
    end_silence_ms: int = Field(default=250, ge=50, le=10000)
    initial_silence_ms: int = Field(default=3000, ge=1000, le=120000)
    max_finals: int = Field(default=5000, ge=100, le=10000)
    translation_enabled: bool = True
    summary_enabled: bool = True
    debug: bool = False
