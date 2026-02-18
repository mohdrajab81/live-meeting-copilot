"""
ConfigStore — owns RuntimeConfig load/save/reload/reset.

Fully independent: no deps on other controller modules.
Has its own lock so config reads never block on the main AppController lock.
"""

import json
import threading
from pathlib import Path
from typing import Any

from app.config import RuntimeConfig


class ConfigStore:
    def __init__(self, settings_path: Path) -> None:
        self._lock = threading.RLock()
        self._settings_path = settings_path
        self._config = RuntimeConfig()

    # ── Read ──────────────────────────────────────────────────────────────────

    def get(self) -> RuntimeConfig:
        """Return a validated copy of the current config."""
        with self._lock:
            return RuntimeConfig.model_validate(self._config.model_dump())

    def dump(self) -> dict[str, Any]:
        with self._lock:
            return self._config.model_dump()

    def get_debug(self) -> bool:
        with self._lock:
            return bool(self._config.debug)

    # ── Write ─────────────────────────────────────────────────────────────────

    def set(self, config: RuntimeConfig) -> None:
        with self._lock:
            self._config = config

    def reset(self) -> dict[str, Any]:
        cfg = RuntimeConfig()
        with self._lock:
            self._config = cfg
        return cfg.model_dump()

    # ── Persistence ───────────────────────────────────────────────────────────

    def save_to_disk(self) -> str:
        with self._lock:
            config = self._config.model_dump()
        self._settings_path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return self._settings_path.name

    def reload_from_disk(self) -> dict[str, Any]:
        if not self._settings_path.exists():
            raise FileNotFoundError(
                f"Settings file not found: {self._settings_path.name}. Save config first."
            )
        raw = json.loads(self._settings_path.read_text(encoding="utf-8"))
        cfg = RuntimeConfig.model_validate(raw)
        with self._lock:
            self._config = cfg
        return cfg.model_dump()
