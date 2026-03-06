import threading
from typing import Any, Callable, Protocol

from app.config import RuntimeConfig, Settings

from .speech import SpeechService as AzureSpeechService
from .speech_nova3 import Nova3SpeechService


EventCallback = Callable[[dict[str, Any]], None]
ConfigProvider = Callable[[], RuntimeConfig]


class SpeechBackend(Protocol):
    @property
    def running(self) -> bool: ...

    def start_recognition(self) -> bool: ...

    def stop_recognition(self) -> bool: ...


class SpeechProviderService:
    """Provider router for STT engines.

    Current rollout behavior:
    - `azure`: use Azure Speech service directly.
    - `nova3`: attempt Nova-3 preview first, then auto-fallback to Azure.
    """

    def __init__(
        self,
        settings: Settings,
        on_event: EventCallback,
        get_runtime_config: ConfigProvider,
        *,
        azure_backend: SpeechBackend | None = None,
        nova3_backend: SpeechBackend | None = None,
    ) -> None:
        self._on_event = on_event
        self._get_runtime_config = get_runtime_config
        self._azure = (
            azure_backend
            if azure_backend is not None
            else AzureSpeechService(
                settings=settings,
                on_event=on_event,
                get_runtime_config=get_runtime_config,
            )
        )
        self._nova3 = (
            nova3_backend
            if nova3_backend is not None
            else Nova3SpeechService(
                settings=settings,
                on_event=on_event,
                get_runtime_config=get_runtime_config,
            )
        )
        self._lock = threading.RLock()
        self._active_provider: str | None = None

    def _emit_log(self, level: str, message: str) -> None:
        self._on_event({"type": "log", "level": level, "message": message})

    @property
    def running(self) -> bool:
        with self._lock:
            active = self._active_provider
        if active == "azure":
            return bool(self._azure.running)
        if active == "nova3":
            return bool(self._nova3.running)
        return bool(self._azure.running) or bool(self._nova3.running)

    @property
    def active_provider(self) -> str:
        with self._lock:
            return str(self._active_provider or "none")

    def _start_azure(self) -> bool:
        started = self._azure.start_recognition()
        if started:
            with self._lock:
                self._active_provider = "azure"
        return started

    def _start_nova3_with_fallback(self) -> bool:
        self._emit_log("info", "Speech provider selected: Nova-3 (preview).")
        started = self._nova3.start_recognition()
        if started:
            with self._lock:
                self._active_provider = "nova3"
            return True
        self._emit_log(
            "warning",
            "Nova-3 unavailable for live capture in this build. Falling back to Azure Speech.",
        )
        return self._start_azure()

    def start_recognition(self) -> bool:
        cfg = self._get_runtime_config()
        provider = str(getattr(cfg, "speech_provider", "azure") or "azure").strip().lower()
        if provider == "azure":
            self._emit_log("info", "Speech provider selected: Azure Speech.")
            return self._start_azure()
        if provider == "nova3":
            return self._start_nova3_with_fallback()
        self._emit_log(
            "warning",
            f"Unknown speech provider '{provider}'. Falling back to Azure Speech.",
        )
        return self._start_azure()

    def stop_recognition(self) -> bool:
        with self._lock:
            active = self._active_provider

        if active == "nova3":
            stopped = self._nova3.stop_recognition()
            with self._lock:
                if stopped or not self._nova3.running:
                    self._active_provider = None
            return stopped

        if active == "azure":
            stopped = self._azure.stop_recognition()
            with self._lock:
                if stopped or not self._azure.running:
                    self._active_provider = None
            return stopped

        # Unknown active provider: be defensive and request stop on both.
        stopped_nova3 = self._nova3.stop_recognition()
        stopped_azure = self._azure.stop_recognition()
        with self._lock:
            self._active_provider = None
        return bool(stopped_nova3 or stopped_azure)
