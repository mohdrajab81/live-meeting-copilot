from __future__ import annotations

import threading
import time
from types import SimpleNamespace

import azure.cognitiveservices.speech as speech_sdk

from app.config import RuntimeConfig, Settings
from app.services.speech import SpeechService


class _Signal:
    def __init__(self) -> None:
        self._handlers = []

    def connect(self, handler) -> None:
        self._handlers.append(handler)

    def emit(self, evt) -> None:
        for handler in list(self._handlers):
            handler(evt)


class _FakeRecognizer:
    def __init__(self) -> None:
        self.recognizing = _Signal()
        self.recognized = _Signal()
        self.session_started = _Signal()
        self.session_stopped = _Signal()
        self.canceled = _Signal()
        self.speech_start_detected = _Signal()
        self.speech_end_detected = _Signal()


def _settings() -> Settings:
    return Settings(
        ai_services_key="k",
        ai_services_region="eastus",
    )


def test_initial_session_ready_notifier_waits_for_all_channels() -> None:
    events: list[dict] = []
    svc = SpeechService(
        settings=_settings(),
        on_event=events.append,
        get_runtime_config=lambda: RuntimeConfig(),
    )

    notifier = svc._make_initial_session_ready_notifier(  # type: ignore[attr-defined]
        {"local", "remote"},
        start_requested_ts=time.time() - 0.1,
    )

    notifier("local", "You", "sess-local")
    assert not any(
        evt.get("type") == "status" and evt.get("status") == "listening"
        for evt in events
    )

    notifier("remote", "Remote", "sess-remote")

    listening = [
        evt for evt in events
        if evt.get("type") == "status" and evt.get("status") == "listening"
    ]
    assert len(listening) == 1
    ready_logs = [
        str(evt.get("message", ""))
        for evt in events
        if evt.get("type") == "log"
    ]
    assert any("Azure recognition session ready" in message for message in ready_logs)


def test_make_speech_config_applies_segmentation_silence_and_raw_profanity() -> None:
    svc = SpeechService(
        settings=_settings(),
        on_event=lambda _payload: None,
        get_runtime_config=lambda: RuntimeConfig(),
    )

    config = svc._make_speech_config(RuntimeConfig(end_silence_ms=500))  # type: ignore[attr-defined]

    assert (
        config.get_property(speech_sdk.PropertyId.Speech_SegmentationSilenceTimeoutMs)
        == "500"
    )
    assert (
        config.get_property(speech_sdk.PropertyId.SpeechServiceResponse_ProfanityOption)
        == "raw"
    )


def test_wire_handlers_emits_session_start_and_first_speech_timing_logs() -> None:
    events: list[dict] = []
    svc = SpeechService(
        settings=_settings(),
        on_event=events.append,
        get_runtime_config=lambda: RuntimeConfig(debug=True),
    )
    recognizer = _FakeRecognizer()
    restart_evt = threading.Event()
    ready_calls: list[tuple[str, str, str]] = []

    svc._wire_handlers(  # type: ignore[attr-defined]
        recognizer,
        RuntimeConfig(debug=True),
        "default",
        "Speaker",
        restart_evt,
        on_session_ready=lambda speaker_key, speaker_label, session_id: ready_calls.append(
            (speaker_key, speaker_label, session_id)
        ),
        start_requested_ts=time.time() - 0.2,
    )

    recognizer.session_started.emit(SimpleNamespace(session_id="sess-1"))
    recognizer.speech_start_detected.emit(SimpleNamespace(offset=10_000_000))
    recognizer.recognizing.emit(
        SimpleNamespace(
            result=SimpleNamespace(
                reason=speech_sdk.ResultReason.RecognizingSpeech,
                text="hello there",
                offset=10_000_000,
                duration=5_000_000,
            )
        )
    )

    messages = [
        str(evt.get("message", ""))
        for evt in events
        if evt.get("type") == "log"
    ]
    assert any("Session started:" in message and "startup_ms=" in message for message in messages)
    assert any("Speech start detected:" in message for message in messages)
    assert any("First partial emitted:" in message for message in messages)
    assert ready_calls == [("default", "Speaker", "sess-1")]


def test_worker_keeps_status_starting_until_session_ready() -> None:
    events: list[dict] = []
    svc = SpeechService(
        settings=_settings(),
        on_event=events.append,
        get_runtime_config=lambda: RuntimeConfig(capture_mode="single"),
    )

    svc._refresh_device_labels = lambda: None  # type: ignore[method-assign]

    def _fake_start_single_mode(cfg, *, on_session_ready=None, start_requested_ts=None):
        svc._stop_event.set()
        return []

    svc._start_single_mode = _fake_start_single_mode  # type: ignore[method-assign]
    svc._worker()

    statuses = [
        str(evt.get("status", ""))
        for evt in events
        if evt.get("type") == "status"
    ]
    assert statuses[0] == "starting"
    assert "listening" not in statuses
    assert statuses[-1] == "stopped"
