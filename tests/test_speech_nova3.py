from app.config import RuntimeConfig, Settings
from app.services.speech_nova3 import Nova3SpeechService


def _settings(**overrides):
    base = {
        "ai_services_key": "k",
        "ai_services_region": "eastus",
    }
    base.update(overrides)
    return Settings(**base)


def test_start_returns_false_when_nova_key_missing() -> None:
    events: list[dict] = []
    svc = Nova3SpeechService(
        settings=_settings(nova3_api_key=""),
        on_event=events.append,
        get_runtime_config=lambda: RuntimeConfig(),
    )
    svc._settings.nova3_api_key = ""  # Ensure env fallback cannot override during tests.

    assert svc.start_recognition() is False
    assert svc.running is False
    messages = [str(e.get("message", "")) for e in events if e.get("type") == "log"]
    assert any("NOVA3_API_KEY is not set" in msg for msg in messages)


def test_format_event_summary_extracts_transcript_fields() -> None:
    payload = {
        "type": "Results",
        "is_final": True,
        "speech_final": False,
        "start": 1.2,
        "duration": 0.8,
        "channel_index": [0, 0],
        "channel": {
            "alternatives": [
                {"transcript": "hello from nova three", "confidence": 0.91}
            ]
        },
    }

    summary = Nova3SpeechService._format_event_summary("Transcript", payload)
    assert "event=Transcript" in summary
    assert "is_final=True" in summary
    assert "speech_final=False" in summary
    assert "transcript='hello from nova three'" in summary


def test_format_event_summary_includes_speaker_ids_when_present() -> None:
    payload = {
        "channel": {
            "alternatives": [
                {
                    "transcript": "hello there",
                    "words": [
                        {"word": "hello", "speaker": 0},
                        {"word": "there", "speaker": 1},
                        {"word": "again", "speaker": 1},
                    ],
                }
            ]
        }
    }
    summary = Nova3SpeechService._format_event_summary("Transcript", payload)
    assert "speakers=[0, 1]" in summary


def test_build_live_options_uses_configured_language_and_diarize() -> None:
    svc = Nova3SpeechService(
        settings=_settings(nova3_api_key="x"),
        on_event=lambda _e: None,
        get_runtime_config=lambda: RuntimeConfig(end_silence_ms=300),
    )

    options = svc._build_live_options(
        RuntimeConfig(end_silence_ms=300),
        sample_rate=48000,
        channels=1,
    )
    assert options["model"] == "nova-3"
    assert options["language"] == "en-US"
    assert options["diarize"] == "true"
    assert options["sample_rate"] == "48000"
    assert options["channels"] == "1"
    assert options["endpointing"] == "300"
    assert options["utterance_end_ms"] == "1000"


def test_build_live_options_respects_large_end_silence() -> None:
    svc = Nova3SpeechService(
        settings=_settings(nova3_api_key="x"),
        on_event=lambda _e: None,
        get_runtime_config=lambda: RuntimeConfig(end_silence_ms=1000),
    )
    options = svc._build_live_options(
        RuntimeConfig(end_silence_ms=1000),
        sample_rate=16000,
        channels=1,
    )
    assert options["endpointing"] == "1000"
    assert options["utterance_end_ms"] == "1000"


def test_integrate_results_event_emits_partial_with_stream_mapping() -> None:
    events: list[dict] = []
    svc = Nova3SpeechService(
        settings=_settings(nova3_api_key="x"),
        on_event=events.append,
        get_runtime_config=lambda: RuntimeConfig(),
    )
    payload = {
        "type": "Results",
        "is_final": False,
        "speech_final": False,
        "start": 1.0,
        "duration": 0.7,
        "channel": {"alternatives": [{"transcript": "hello there"}]},
    }
    svc._integrate_results_event("wasapi_loopback", payload)
    out = [e for e in events if e.get("type") == "partial"]
    assert len(out) == 1
    assert out[0]["speaker"] == "remote"
    assert out[0]["speaker_label"] == "Remote"
    assert out[0]["en"] == "hello there"


def test_integrate_results_event_live_partial_includes_cached_final_chunks() -> None:
    events: list[dict] = []
    svc = Nova3SpeechService(
        settings=_settings(nova3_api_key="x"),
        on_event=events.append,
        get_runtime_config=lambda: RuntimeConfig(),
    )

    svc._integrate_results_event(
        "wasapi_loopback",
        {
            "type": "Results",
            "is_final": True,
            "speech_final": False,
            "start": 2.0,
            "duration": 1.0,
            "channel": {"alternatives": [{"transcript": "statement one"}]},
        },
    )
    svc._integrate_results_event(
        "wasapi_loopback",
        {
            "type": "Results",
            "is_final": True,
            "speech_final": False,
            "start": 4.0,
            "duration": 1.0,
            "channel": {"alternatives": [{"transcript": "statement two"}]},
        },
    )
    svc._integrate_results_event(
        "wasapi_loopback",
        {
            "type": "Results",
            "is_final": False,
            "speech_final": False,
            "start": 5.0,
            "duration": 0.8,
            "channel": {"alternatives": [{"transcript": "partial tail"}]},
        },
    )

    partials = [e for e in events if e.get("type") == "partial"]
    assert partials[-1]["en"] == "statement one statement two partial tail"


def test_integrate_results_event_emits_final_with_timing_and_request_id() -> None:
    events: list[dict] = []
    svc = Nova3SpeechService(
        settings=_settings(nova3_api_key="x"),
        on_event=events.append,
        get_runtime_config=lambda: RuntimeConfig(),
    )
    state = svc._ensure_stream_state("local_mic")
    state.anchor_ts = 1000.0
    payload = {
        "type": "Results",
        "is_final": True,
        "speech_final": True,
        "start": 2.0,
        "duration": 0.8,
        "metadata": {"request_id": "req-123"},
        "channel": {
            "alternatives": [
                {
                    "transcript": "final text",
                    "words": [{"speaker": 1}],
                }
            ]
        },
    }
    svc._integrate_results_event("local_mic", payload)
    out = [e for e in events if e.get("type") == "final"]
    assert len(out) == 1
    assert out[0]["speaker"] == "local"
    assert out[0]["speaker_label"] == "You"
    assert out[0]["speaker_sub_id"] == "local[1]"
    assert out[0]["recognizer_session_id"] == "req-123"
    assert out[0]["timing_source"] == "offset"
    assert out[0]["start_ts"] == 1002.0
    assert out[0]["end_ts"] == 1002.8
    assert out[0]["duration_sec"] == 0.8
    assert out[0]["offset_sec"] == 2.0


def test_integrate_results_event_flushes_cached_non_speech_final_chunks() -> None:
    events: list[dict] = []
    svc = Nova3SpeechService(
        settings=_settings(nova3_api_key="x"),
        on_event=events.append,
        get_runtime_config=lambda: RuntimeConfig(),
    )
    state = svc._ensure_stream_state("wasapi_loopback")
    state.anchor_ts = 1000.0

    svc._integrate_results_event(
        "wasapi_loopback",
        {
            "type": "Results",
            "is_final": True,
            "speech_final": False,
            "start": 2.0,
            "duration": 1.0,
            "channel": {"alternatives": [{"transcript": "first chunk"}]},
        },
    )
    svc._integrate_results_event(
        "wasapi_loopback",
        {
            "type": "Results",
            "is_final": True,
            "speech_final": False,
            "start": 3.0,
            "duration": 1.5,
            "channel": {"alternatives": [{"transcript": "second chunk"}]},
        },
    )
    svc._integrate_results_event(
        "wasapi_loopback",
        {
            "type": "Results",
            "is_final": True,
            "speech_final": True,
            "start": 3.0,
            "duration": 1.5,
            "metadata": {"request_id": "req-123"},
            "channel": {"alternatives": [{"transcript": "second chunk"}]},
        },
    )

    partials = [e for e in events if e.get("type") == "partial"]
    finals = [e for e in events if e.get("type") == "final"]
    assert partials[-1]["en"] == "first chunk second chunk"
    assert len(finals) == 1
    assert finals[0]["en"] == "first chunk second chunk"
    assert finals[0]["start_ts"] == 1002.0
    assert finals[0]["end_ts"] == 1004.5
    assert finals[0]["duration_sec"] == 2.5
    assert finals[0]["offset_sec"] == 2.0


def test_integrate_results_event_appends_unique_speech_final_tail() -> None:
    events: list[dict] = []
    svc = Nova3SpeechService(
        settings=_settings(nova3_api_key="x"),
        on_event=events.append,
        get_runtime_config=lambda: RuntimeConfig(),
    )

    svc._integrate_results_event(
        "wasapi_loopback",
        {
            "type": "Results",
            "is_final": True,
            "speech_final": False,
            "start": 10.0,
            "duration": 1.0,
            "channel": {"alternatives": [{"transcript": "some users were logged out unexpectedly. And second,"}]},
        },
    )
    svc._integrate_results_event(
        "wasapi_loopback",
        {
            "type": "Results",
            "is_final": True,
            "speech_final": True,
            "start": 13.32,
            "duration": 2.65,
            "channel": {"alternatives": [{"transcript": "checkout failed on slower networks."}]},
        },
    )

    finals = [e for e in events if e.get("type") == "final"]
    assert len(finals) == 1
    assert finals[0]["en"] == (
        "some users were logged out unexpectedly. And second, "
        "checkout failed on slower networks."
    )


def test_integrate_results_event_uses_speech_final_text_when_cache_empty() -> None:
    events: list[dict] = []
    svc = Nova3SpeechService(
        settings=_settings(nova3_api_key="x"),
        on_event=events.append,
        get_runtime_config=lambda: RuntimeConfig(),
    )

    svc._integrate_results_event(
        "wasapi_loopback",
        {
            "type": "Results",
            "is_final": True,
            "speech_final": True,
            "start": 1.0,
            "duration": 0.9,
            "channel": {"alternatives": [{"transcript": "direct final"}]},
        },
    )

    finals = [e for e in events if e.get("type") == "final"]
    assert len(finals) == 1
    assert finals[0]["en"] == "direct final"


def test_integrate_results_event_flushes_last_live_partial_when_speech_final_is_empty() -> None:
    events: list[dict] = []
    svc = Nova3SpeechService(
        settings=_settings(nova3_api_key="x"),
        on_event=events.append,
        get_runtime_config=lambda: RuntimeConfig(),
    )
    state = svc._ensure_stream_state("wasapi_loopback")
    state.anchor_ts = 1000.0

    svc._integrate_results_event(
        "wasapi_loopback",
        {
            "type": "Results",
            "is_final": False,
            "speech_final": False,
            "start": 60.06,
            "duration": 1.0399971,
            "channel": {"alternatives": [{"transcript": "Topic two,"}]},
        },
    )
    svc._integrate_results_event(
        "wasapi_loopback",
        {
            "type": "Results",
            "is_final": True,
            "speech_final": True,
            "start": 60.06,
            "duration": 3.2199974,
            "channel": {"alternatives": [{"transcript": ""}]},
        },
    )

    finals = [e for e in events if e.get("type") == "final"]
    assert len(finals) == 1
    assert finals[0]["en"] == "Topic two,"
    assert finals[0]["start_ts"] == 1060.06


def test_integrate_results_event_empty_partial_clears_live_when_no_cached_chunks() -> None:
    events: list[dict] = []
    svc = Nova3SpeechService(
        settings=_settings(nova3_api_key="x"),
        on_event=events.append,
        get_runtime_config=lambda: RuntimeConfig(),
    )

    svc._integrate_results_event(
        "wasapi_loopback",
        {
            "type": "Results",
            "is_final": False,
            "speech_final": False,
            "start": 10.0,
            "duration": 1.0,
            "channel": {"alternatives": [{"transcript": "Topic two,"}]},
        },
    )
    svc._integrate_results_event(
        "wasapi_loopback",
        {
            "type": "Results",
            "is_final": False,
            "speech_final": False,
            "start": 10.0,
            "duration": 2.0,
            "channel": {"alternatives": [{"transcript": ""}]},
        },
    )

    clears = [e for e in events if e.get("type") == "partial_clear"]
    assert len(clears) == 1
    assert clears[0]["speaker"] == "remote"
    assert clears[0]["reason"] == "nova_empty_partial"


def test_integrate_results_event_empty_partial_keeps_cached_final_chunks_live() -> None:
    events: list[dict] = []
    svc = Nova3SpeechService(
        settings=_settings(nova3_api_key="x"),
        on_event=events.append,
        get_runtime_config=lambda: RuntimeConfig(),
    )

    svc._integrate_results_event(
        "wasapi_loopback",
        {
            "type": "Results",
            "is_final": True,
            "speech_final": False,
            "start": 2.0,
            "duration": 1.0,
            "channel": {"alternatives": [{"transcript": "statement one"}]},
        },
    )
    svc._integrate_results_event(
        "wasapi_loopback",
        {
            "type": "Results",
            "is_final": False,
            "speech_final": False,
            "start": 3.0,
            "duration": 1.0,
            "channel": {"alternatives": [{"transcript": ""}]},
        },
    )

    partials = [e for e in events if e.get("type") == "partial"]
    assert partials[-1]["en"] == "statement one"


def test_integrate_results_event_ignores_empty_transcript() -> None:
    events: list[dict] = []
    svc = Nova3SpeechService(
        settings=_settings(nova3_api_key="x"),
        on_event=events.append,
        get_runtime_config=lambda: RuntimeConfig(),
    )
    payload = {
        "type": "Results",
        "is_final": True,
        "channel": {"alternatives": [{"transcript": ""}]},
    }
    svc._integrate_results_event("local_mic", payload)
    assert not [e for e in events if e.get("type") in {"partial", "final"}]


def test_integrate_results_event_deduplicates_repeated_results() -> None:
    events: list[dict] = []
    svc = Nova3SpeechService(
        settings=_settings(nova3_api_key="x"),
        on_event=events.append,
        get_runtime_config=lambda: RuntimeConfig(),
    )
    payload = {
        "type": "Results",
        "is_final": False,
        "speech_final": False,
        "start": 1.5,
        "duration": 0.9,
        "channel": {"alternatives": [{"transcript": "same partial"}]},
    }
    svc._integrate_results_event("wasapi_loopback", payload)
    svc._integrate_results_event("wasapi_loopback", payload)
    out = [e for e in events if e.get("type") == "partial"]
    assert len(out) == 1


def test_register_handlers_emits_activity_on_speech_started() -> None:
    events: list[dict] = []
    svc = Nova3SpeechService(
        settings=_settings(nova3_api_key="x"),
        on_event=events.append,
        get_runtime_config=lambda: RuntimeConfig(),
    )

    class _EventType:
        OPEN = "open"
        MESSAGE = "message"
        ERROR = "error"
        CLOSE = "close"

    class _Socket:
        def __init__(self):
            self.handlers: dict[str, callable] = {}

        def on(self, event: str, cb):
            self.handlers[event] = cb

    socket = _Socket()
    svc._register_handlers("wasapi_loopback", socket, _EventType)
    socket.handlers[_EventType.MESSAGE]({"type": "SpeechStarted"})

    activity = [e for e in events if e.get("type") == "activity"]
    assert len(activity) == 1
    assert activity[0]["speaker"] == "remote"
    assert activity[0]["has_speech"] is True


def test_pump_audio_read_error_during_shutdown_is_ignored() -> None:
    events: list[dict] = []
    svc = Nova3SpeechService(
        settings=_settings(nova3_api_key="x"),
        on_event=events.append,
        get_runtime_config=lambda: RuntimeConfig(),
    )
    svc._stop_event.set()

    class _Audio:
        def read(self, *_args, **_kwargs):
            raise RuntimeError("stream closed")

    class _Socket:
        def send_media(self, _chunk: bytes) -> None:
            return None

    class _Stream:
        name = "local_mic"
        audio_stream = _Audio()
        socket = _Socket()
        blocksize = 1600

    svc._pump_audio(_Stream())  # type: ignore[arg-type]
    errors = [e for e in events if e.get("type") == "log" and e.get("level") == "error"]
    assert errors == []


def test_pump_audio_send_error_during_shutdown_is_ignored() -> None:
    events: list[dict] = []
    svc = Nova3SpeechService(
        settings=_settings(nova3_api_key="x"),
        on_event=events.append,
        get_runtime_config=lambda: RuntimeConfig(),
    )
    svc._stop_event.clear()

    class _Audio:
        def __init__(self):
            self._done = False

        def read(self, *_args, **_kwargs):
            if not self._done:
                self._done = True
                return b"\x00\x00" * 320
            return b""

    class _Socket:
        def __init__(self, owner: Nova3SpeechService):
            self._owner = owner

        def send_media(self, _chunk: bytes) -> None:
            self._owner._stop_event.set()
            raise RuntimeError("socket closed")

    class _Stream:
        name = "wasapi_loopback"
        blocksize = 1600

        def __init__(self, owner: Nova3SpeechService):
            self.audio_stream = _Audio()
            self.socket = _Socket(owner)

    svc._pump_audio(_Stream(svc))  # type: ignore[arg-type]
    errors = [e for e in events if e.get("type") == "log" and e.get("level") == "error"]
    assert errors == []
