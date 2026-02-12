from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    speech_key: str = Field(alias="SPEECH_KEY")
    speech_region: str = Field(alias="SPEECH_REGION")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class RuntimeConfig(BaseModel):
    capture_mode: Literal["single", "dual"] = "single"
    recognition_language: str = "en-US"
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
    coach_instruction: str = (
        "Give a short suggested reply for me, tailored to my profile. "
        "Use concise bullets and keep claims truthful to known background."
    )
    end_silence_ms: int = Field(default=250, ge=50, le=10000)
    initial_silence_ms: int = Field(default=3000, ge=1000, le=120000)
    max_finals: int = Field(default=200, ge=20, le=2000)
    debug: bool = False
