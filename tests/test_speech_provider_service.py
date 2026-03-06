from __future__ import annotations

from app.config import RuntimeConfig, Settings
from app.services.speech_provider import SpeechProviderService


class _FakeBackend:
    def __init__(self, *, start_result: bool = True, running: bool = False) -> None:
        self._start_result = start_result
        self._running = running
        self.start_calls = 0
        self.stop_calls = 0

    @property
    def running(self) -> bool:
        return self._running

    def start_recognition(self) -> bool:
        self.start_calls += 1
        if self._start_result:
            self._running = True
        return self._start_result

    def stop_recognition(self) -> bool:
        self.stop_calls += 1
        was_running = self._running
        self._running = False
        return was_running


def _settings() -> Settings:
    return Settings(
        ai_services_key="k",
        ai_services_region="eastus",
    )


def test_start_uses_azure_when_selected() -> None:
    events: list[dict] = []
    azure = _FakeBackend(start_result=True)
    nova3 = _FakeBackend(start_result=True)
    svc = SpeechProviderService(
        settings=_settings(),
        on_event=events.append,
        get_runtime_config=lambda: RuntimeConfig(speech_provider="azure"),
        azure_backend=azure,
        nova3_backend=nova3,
    )

    assert svc.start_recognition() is True
    assert svc.active_provider == "azure"
    assert azure.start_calls == 1
    assert nova3.start_calls == 0


def test_start_nova3_falls_back_to_azure_when_unavailable() -> None:
    events: list[dict] = []
    azure = _FakeBackend(start_result=True)
    nova3 = _FakeBackend(start_result=False)
    svc = SpeechProviderService(
        settings=_settings(),
        on_event=events.append,
        get_runtime_config=lambda: RuntimeConfig(speech_provider="nova3"),
        azure_backend=azure,
        nova3_backend=nova3,
    )

    assert svc.start_recognition() is True
    assert svc.active_provider == "azure"
    assert nova3.start_calls == 1
    assert azure.start_calls == 1
    log_messages = [str(evt.get("message", "")) for evt in events if evt.get("type") == "log"]
    assert any("Nova-3 unavailable" in msg for msg in log_messages)


def test_unknown_provider_falls_back_to_azure() -> None:
    events: list[dict] = []
    azure = _FakeBackend(start_result=True)
    nova3 = _FakeBackend(start_result=False)
    svc = SpeechProviderService(
        settings=_settings(),
        on_event=events.append,
        get_runtime_config=lambda: RuntimeConfig.model_validate({"speech_provider": "azure", "capture_mode": "single"}),
        azure_backend=azure,
        nova3_backend=nova3,
    )

    class _BadCfg:
        speech_provider = "bad-provider"

    # Simulate bad value arriving from older persisted config.
    svc._get_runtime_config = lambda: _BadCfg()  # type: ignore[method-assign]
    assert svc.start_recognition() is True
    assert azure.start_calls == 1
    log_messages = [str(evt.get("message", "")) for evt in events if evt.get("type") == "log"]
    assert any("Unknown speech provider" in msg for msg in log_messages)


def test_stop_uses_active_backend() -> None:
    events: list[dict] = []
    azure = _FakeBackend(start_result=True, running=True)
    nova3 = _FakeBackend(start_result=False, running=False)
    svc = SpeechProviderService(
        settings=_settings(),
        on_event=events.append,
        get_runtime_config=lambda: RuntimeConfig(speech_provider="azure"),
        azure_backend=azure,
        nova3_backend=nova3,
    )
    svc._active_provider = "azure"  # type: ignore[attr-defined]

    assert svc.stop_recognition() is True
    assert azure.stop_calls == 1
    assert nova3.stop_calls == 0
    assert svc.active_provider == "none"
