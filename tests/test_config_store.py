"""
Tests for app.controller.config_store.ConfigStore.
"""

import json
import tempfile
import os
import pytest
from pathlib import Path

from app.config import RuntimeConfig
from app.controller.config_store import ConfigStore


@pytest.fixture
def tmp_path_store():
    """ConfigStore using a NamedTemporaryFile so no system tmp-dir permissions are needed."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp_file = Path(f.name)
    # Remove it so the store starts with no file on disk
    tmp_file.unlink(missing_ok=True)
    store = ConfigStore(settings_path=tmp_file)
    yield store
    tmp_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Default state
# ---------------------------------------------------------------------------

class TestDefaults:
    def test_get_returns_default_config(self, tmp_path_store):
        cfg = tmp_path_store.get()
        assert cfg.capture_mode == "single"
        assert cfg.max_finals == 5000
        assert cfg.debug is False

    def test_dump_returns_dict(self, tmp_path_store):
        d = tmp_path_store.dump()
        assert isinstance(d, dict)
        assert "capture_mode" in d
        assert "max_finals" in d

    def test_get_debug_false_by_default(self, tmp_path_store):
        assert tmp_path_store.get_debug() is False

    def test_translation_enabled_true_by_default(self, tmp_path_store):
        assert tmp_path_store.get().translation_enabled is True


# ---------------------------------------------------------------------------
# set / get round-trip
# ---------------------------------------------------------------------------

class TestSetGet:
    def test_set_then_get_reflects_change(self, tmp_path_store):
        new_cfg = RuntimeConfig(debug=True, max_finals=200)
        tmp_path_store.set(new_cfg)
        loaded = tmp_path_store.get()
        assert loaded.debug is True
        assert loaded.max_finals == 200

    def test_get_returns_isolated_copy(self, tmp_path_store):
        cfg_a = tmp_path_store.get()
        cfg_b = tmp_path_store.get()
        assert cfg_a is not cfg_b

    def test_get_debug_true_after_set(self, tmp_path_store):
        tmp_path_store.set(RuntimeConfig(debug=True))
        assert tmp_path_store.get_debug() is True

    def test_set_coach_fields(self, tmp_path_store):
        cfg = RuntimeConfig(coach_enabled=True, coach_cooldown_sec=30)
        tmp_path_store.set(cfg)
        loaded = tmp_path_store.get()
        assert loaded.coach_enabled is True
        assert loaded.coach_cooldown_sec == 30


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------

class TestReset:
    def test_reset_reverts_to_defaults(self, tmp_path_store):
        tmp_path_store.set(RuntimeConfig(debug=True, max_finals=100))
        d = tmp_path_store.reset()
        assert d["debug"] is False
        assert d["max_finals"] == 5000

    def test_reset_returns_dict(self, tmp_path_store):
        result = tmp_path_store.reset()
        assert isinstance(result, dict)

    def test_get_after_reset_returns_defaults(self, tmp_path_store):
        tmp_path_store.set(RuntimeConfig(debug=True))
        tmp_path_store.reset()
        assert tmp_path_store.get().debug is False


# ---------------------------------------------------------------------------
# save_to_disk / reload_from_disk
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_save_creates_file(self, tmp_path_store):
        tmp_path_store.set(RuntimeConfig(debug=True))
        tmp_path_store.save_to_disk()
        assert tmp_path_store._settings_path.exists()

    def test_save_returns_filename(self, tmp_path_store):
        name = tmp_path_store.save_to_disk()
        assert isinstance(name, str)
        assert name.endswith(".json")

    def test_save_and_reload_round_trip(self, tmp_path_store):
        tmp_path_store.set(RuntimeConfig(debug=True, max_finals=333))
        tmp_path_store.save_to_disk()
        tmp_path_store.reset()
        assert tmp_path_store.get().debug is False
        tmp_path_store.reload_from_disk()
        cfg = tmp_path_store.get()
        assert cfg.debug is True
        assert cfg.max_finals == 333

    def test_reload_file_not_found_raises(self, tmp_path_store):
        with pytest.raises(FileNotFoundError):
            tmp_path_store.reload_from_disk()

    def test_saved_file_is_valid_json(self, tmp_path_store):
        tmp_path_store.save_to_disk()
        raw = json.loads(tmp_path_store._settings_path.read_text(encoding="utf-8"))
        assert "capture_mode" in raw

    def test_reload_validates_against_schema(self, tmp_path_store):
        # Write known values directly to the store's settings path
        tmp_path_store._settings_path.write_text(
            json.dumps({"capture_mode": "dual", "debug": True}),
            encoding="utf-8",
        )
        d = tmp_path_store.reload_from_disk()
        assert d["capture_mode"] == "dual"
        assert d["debug"] is True

    def test_reload_with_extra_keys_ignored(self, tmp_path_store):
        tmp_path_store._settings_path.write_text(
            json.dumps({"capture_mode": "single", "unknown_key": "ignored"}),
            encoding="utf-8",
        )
        # Should not raise — pydantic ignores extra fields
        d = tmp_path_store.reload_from_disk()
        assert d["capture_mode"] == "single"
