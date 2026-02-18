"""
Shared pytest configuration and fixtures.

Sets required Azure env vars before any imports so Settings() always resolves,
and provides common building blocks used across test modules.
"""

import os
import threading

# Set required env vars before any app module is imported.
# These are fakes — no real Azure calls are made in unit tests.
os.environ.setdefault("SPEECH_KEY", "test-speech-key")
os.environ.setdefault("SPEECH_REGION", "eastus")

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.config import RuntimeConfig, Settings


# ---------------------------------------------------------------------------
# Primitive fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def shared_lock():
    return threading.RLock()


@pytest.fixture
def runtime_config():
    return RuntimeConfig()


@pytest.fixture
def settings():
    return Settings()


# ---------------------------------------------------------------------------
# Callback stubs used by controller constructors
# ---------------------------------------------------------------------------

@pytest.fixture
def async_broadcast():
    return AsyncMock()


@pytest.fixture
def async_broadcast_log():
    return AsyncMock()


@pytest.fixture
def sync_append_log():
    """Mimics BroadcastService.append_log — returns the log dict."""
    def _append(level: str, message: str):
        return {"type": "log", "level": level, "message": message, "ts": 0.0}
    return _append


@pytest.fixture
def sync_broadcast_from_thread():
    return MagicMock()


@pytest.fixture
def sync_preview_text():
    def _preview(text: str, max_len: int = 220) -> str:
        cleaned = " ".join(str(text or "").split())
        return cleaned[:max_len] if len(cleaned) > max_len else cleaned
    return _preview
