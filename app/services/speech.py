import threading
import time
import traceback
from typing import Any, Callable

import azure.cognitiveservices.speech as speech_sdk

from app.config import RuntimeConfig, Settings
from app.utils.audio_devices import list_capture_devices


EventCallback = Callable[[dict[str, Any]], None]
ConfigProvider = Callable[[], RuntimeConfig]


class SpeechService:
    def __init__(
        self,
        settings: Settings,
        on_event: EventCallback,
        get_runtime_config: ConfigProvider,
    ) -> None:
        self._settings = settings
        self._on_event = on_event
        self._get_runtime_config = get_runtime_config
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._recognizers: list[speech_sdk.SpeechRecognizer] = []
        self._lock = threading.RLock()
        self._running = False
        self._device_labels_by_id: dict[str, str] = {}
        self._last_partial_debug_ts: dict[str, float] = {}

    @property
    def running(self) -> bool:
        with self._lock:
            return self._running

    def start_recognition(self) -> bool:
        with self._lock:
            if self._running:
                return False
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._worker, daemon=True)
            self._thread.start()
            self._running = True
        return True

    def stop_recognition(self) -> bool:
        with self._lock:
            if not self._running and not self._thread:
                return False
            self._stop_event.set()
            recognizers = list(self._recognizers)

        for recognizer in recognizers:
            try:
                recognizer.stop_continuous_recognition_async()
            except Exception:
                pass
        return True

    def _emit(self, payload: dict[str, Any]) -> None:
        self._on_event(payload)

    def _make_speech_config(self, cfg: RuntimeConfig):
        try:
            config = speech_sdk.SpeechConfig(
                subscription=self._settings.speech_key,
                region=self._settings.speech_region,
            )
        except TypeError:
            config = speech_sdk.SpeechConfig(
                self._settings.speech_key,
                self._settings.speech_region,
            )

        config.speech_recognition_language = cfg.recognition_language
        config.set_property(
            speech_sdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs,
            str(cfg.end_silence_ms),
        )
        config.set_property(
            speech_sdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs,
            str(cfg.initial_silence_ms),
        )
        return config

    def _make_recognizer(self, config, audio):
        try:
            return speech_sdk.SpeechRecognizer(speech_config=config, audio_config=audio)
        except TypeError:
            return speech_sdk.SpeechRecognizer(config, audio)

    def _make_audio_config_device(self, device_id: str):
        cleaned = (device_id or "").strip()
        if not cleaned:
            raise ValueError("Device ID is required in dual mode")
        return speech_sdk.audio.AudioConfig(device_name=cleaned)

    def _refresh_device_labels(self) -> None:
        try:
            devices = list_capture_devices()
        except Exception:
            devices = []
        self._device_labels_by_id = {
            str(d.get("id", "") or "").strip(): str(d.get("label", "") or "").strip()
            for d in devices
            if str(d.get("id", "") or "").strip()
        }

    def _device_display_name(self, device_id: str) -> str:
        cleaned = str(device_id or "").strip()
        if not cleaned:
            return "unknown"
        label = self._device_labels_by_id.get(cleaned, "")
        if label:
            return label
        return "configured device"

    def _wire_handlers(
        self,
        recognizer: speech_sdk.SpeechRecognizer,
        cfg: RuntimeConfig,
        speaker_key: str,
        speaker_label: str,
        restart_event: threading.Event,
    ) -> None:
        timing_state: dict[str, Any] = {
            "anchor_ts": time.time(),
            "session_id": "",
        }

        def _safe_float(value: Any) -> float | None:
            try:
                parsed = float(value)
            except Exception:
                return None
            if parsed < 0:
                return None
            return parsed

        def on_recognizing(evt: Any) -> None:
            result = evt.result
            if not result or result.reason != speech_sdk.ResultReason.RecognizingSpeech:
                return
            en_text = (result.text or "").strip()
            if not en_text:
                return
            if cfg.debug:
                now = time.time()
                last = self._last_partial_debug_ts.get(speaker_key, 0.0)
                if now - last >= 1.0:
                    self._last_partial_debug_ts[speaker_key] = now
                    preview = en_text if len(en_text) <= 80 else f"{en_text[:77]}..."
                    self._emit(
                        {
                            "type": "log",
                            "level": "debug",
                            "message": (
                                f"[{speaker_label}] STT partial emitted: "
                                f"len={len(en_text)}, preview='{preview}'"
                            ),
                        }
                    )
            self._emit(
                {
                    "type": "partial",
                    "speaker": speaker_key,
                    "speaker_label": speaker_label,
                    "en": en_text,
                    "ar": "",
                }
            )

        def on_recognized(evt: Any) -> None:
            result = evt.result
            if not result or result.reason != speech_sdk.ResultReason.RecognizedSpeech:
                return
            en_text = (result.text or "").strip()
            if not en_text:
                return
            now_ts = time.time()
            offset_sec: float | None = None
            duration_sec = 0.0
            start_ts = now_ts
            end_ts = now_ts
            timing_source = "event_only"

            raw_offset_ticks = _safe_float(getattr(result, "offset", None))
            if raw_offset_ticks is not None:
                offset_sec = raw_offset_ticks / 10_000_000.0
            raw_duration_ticks = _safe_float(getattr(result, "duration", None))
            if raw_duration_ticks is not None:
                duration_sec = max(0.0, raw_duration_ticks / 10_000_000.0)

            anchor_ts = _safe_float(timing_state.get("anchor_ts")) or now_ts
            if offset_sec is not None:
                timing_source = "offset"
                start_ts = max(0.0, anchor_ts + offset_sec)
                if duration_sec > 0:
                    end_ts = start_ts + duration_sec
                else:
                    end_ts = start_ts
            elif duration_sec > 0:
                timing_source = "duration_backfill"
                start_ts = max(0.0, now_ts - duration_sec)
                end_ts = now_ts

            # Guard against local clock jitter and callback ordering.
            if start_ts > now_ts:
                start_ts = now_ts
            if end_ts > now_ts:
                end_ts = now_ts
            if end_ts < start_ts:
                end_ts = start_ts
            if duration_sec <= 0.0:
                duration_sec = max(0.0, end_ts - start_ts)

            self._emit(
                {
                    "type": "final",
                    "speaker": speaker_key,
                    "speaker_label": speaker_label,
                    "en": en_text,
                    "ar": "",
                    "ts": now_ts,
                    "start_ts": start_ts,
                    "end_ts": end_ts,
                    "duration_sec": duration_sec,
                    "offset_sec": offset_sec,
                    "timing_source": timing_source,
                    "recognizer_session_id": str(timing_state.get("session_id") or ""),
                    "recognizer_anchor_ts": anchor_ts,
                }
            )
            if cfg.debug:
                self._emit(
                    {
                        "type": "log",
                        "level": "debug",
                        "message": f"[{speaker_label}] Final recognized: EN='{en_text}'",
                    }
                )

        def on_session_started(evt: Any) -> None:
            timing_state["anchor_ts"] = time.time()
            timing_state["session_id"] = str(getattr(evt, "session_id", "") or "")
            if cfg.debug:
                self._emit(
                    {
                        "type": "log",
                        "level": "debug",
                        "message": (
                            f"[{speaker_label}] Session started: "
                            f"session_id={timing_state['session_id'] or '-'}"
                        ),
                    }
                )

        def on_canceled(evt: Any) -> None:
            details = evt.cancellation_details
            reason = str(details.reason)
            err = details.error_details or ""
            self._emit(
                {
                    "type": "log",
                    "level": "error",
                    "message": f"[{speaker_label}] Canceled: {reason}. {err}".strip(),
                }
            )
            # "client buffer exceeded" is a recoverable inactivity timeout.
            # Signal only this channel's restart_event so the other channel
            # (in dual mode) is never interrupted.
            if "client buffer exceeded" in err.lower():
                self._emit(
                    {
                        "type": "log",
                        "level": "info",
                        "message": (
                            f"[{speaker_label}] Buffer overflow due to silence — "
                            "auto-restarting this channel"
                        ),
                    }
                )
                restart_event.set()
            else:
                self._stop_event.set()

        recognizer.recognizing.connect(on_recognizing)
        recognizer.recognized.connect(on_recognized)
        recognizer.session_started.connect(on_session_started)
        recognizer.canceled.connect(on_canceled)

    def _start_single_mode(self, cfg: RuntimeConfig) -> list[dict]:
        restart_evt = threading.Event()
        device_id = (cfg.input_device_id or "").strip()

        if cfg.audio_source == "device_id" and device_id:
            def audio_factory() -> speech_sdk.audio.AudioConfig:
                return speech_sdk.audio.AudioConfig(device_name=device_id)

            self._emit(
                {
                    "type": "log",
                    "level": "info",
                    "message": (
                        "Using explicit input device: "
                        f"{self._device_display_name(device_id)}"
                    ),
                }
            )
        elif cfg.audio_source == "device_id" and not device_id:
            def audio_factory() -> speech_sdk.audio.AudioConfig:  # type: ignore[no-redef]
                return speech_sdk.audio.AudioConfig(use_default_microphone=True)

            self._emit(
                {
                    "type": "log",
                    "level": "warning",
                    "message": "audio_source=device_id but no input_device_id set; using default microphone",
                }
            )
        else:
            def audio_factory() -> speech_sdk.audio.AudioConfig:  # type: ignore[no-redef]
                return speech_sdk.audio.AudioConfig(use_default_microphone=True)

            self._emit(
                {
                    "type": "log",
                    "level": "info",
                    "message": "Using default system microphone input",
                }
            )

        config = self._make_speech_config(cfg)
        recognizer = self._make_recognizer(config, audio_factory())
        self._wire_handlers(recognizer, cfg, "default", "Speaker", restart_evt)
        recognizer.start_continuous_recognition_async().get()
        return [
            {
                "recognizer": recognizer,
                "restart_event": restart_evt,
                "audio_factory": audio_factory,
                "speaker_key": "default",
                "speaker_label": "Speaker",
            }
        ]

    def _start_dual_mode(self, cfg: RuntimeConfig) -> list[dict]:
        local_label = (cfg.local_speaker_label or "You").strip() or "You"
        remote_label = (cfg.remote_speaker_label or "Remote").strip() or "Remote"

        local_device = (cfg.local_input_device_id or "").strip()
        remote_device = (cfg.remote_input_device_id or "").strip()
        if not local_device or not remote_device:
            missing = []
            if not local_device:
                missing.append("local_input_device_id")
            if not remote_device:
                missing.append("remote_input_device_id")
            raise ValueError(
                (
                    "Dual mode requires both local_input_device_id and remote_input_device_id. "
                    f"Missing: {', '.join(missing)}"
                )
            )

        self._emit(
            {
                "type": "log",
                "level": "info",
                "message": f"Dual mode enabled: '{local_label}' + '{remote_label}'",
            }
        )
        self._emit(
            {
                "type": "log",
                "level": "info",
                "message": (
                    f"[{local_label}] device: {self._device_display_name(local_device)}"
                ),
            }
        )
        self._emit(
            {
                "type": "log",
                "level": "info",
                "message": (
                    f"[{remote_label}] device: "
                    f"{self._device_display_name(remote_device)}"
                ),
            }
        )

        local_restart = threading.Event()
        remote_restart = threading.Event()

        def local_audio_factory() -> speech_sdk.audio.AudioConfig:
            return self._make_audio_config_device(local_device)

        def remote_audio_factory() -> speech_sdk.audio.AudioConfig:
            return self._make_audio_config_device(remote_device)

        local_cfg = self._make_speech_config(cfg)
        remote_cfg = self._make_speech_config(cfg)

        local_recognizer = self._make_recognizer(local_cfg, local_audio_factory())
        remote_recognizer = self._make_recognizer(remote_cfg, remote_audio_factory())

        self._wire_handlers(local_recognizer, cfg, "local", local_label, local_restart)
        self._wire_handlers(
            remote_recognizer, cfg, "remote", remote_label, remote_restart
        )

        local_started = False
        remote_started = False
        try:
            local_recognizer.start_continuous_recognition_async().get()
            local_started = True
            remote_recognizer.start_continuous_recognition_async().get()
            remote_started = True
        except Exception:
            if remote_started:
                try:
                    remote_recognizer.stop_continuous_recognition_async().get()
                except Exception:
                    pass
            if local_started:
                try:
                    local_recognizer.stop_continuous_recognition_async().get()
                except Exception:
                    pass
            raise

        return [
            {
                "recognizer": local_recognizer,
                "restart_event": local_restart,
                "audio_factory": local_audio_factory,
                "speaker_key": "local",
                "speaker_label": local_label,
            },
            {
                "recognizer": remote_recognizer,
                "restart_event": remote_restart,
                "audio_factory": remote_audio_factory,
                "speaker_key": "remote",
                "speaker_label": remote_label,
            },
        ]

    def _restart_channel(self, ch: dict) -> None:
        """Stop one channel's recognizer and start a fresh one in its place.

        Mutates ch in-place so the caller's reference stays valid.
        The other channel(s) are never touched.
        """
        try:
            ch["recognizer"].stop_continuous_recognition_async().get()
        except Exception:
            pass
        new_evt = threading.Event()
        cfg = self._get_runtime_config()
        speech_cfg = self._make_speech_config(cfg)
        new_recognizer = self._make_recognizer(speech_cfg, ch["audio_factory"]())
        self._wire_handlers(
            new_recognizer, cfg, ch["speaker_key"], ch["speaker_label"], new_evt
        )
        new_recognizer.start_continuous_recognition_async().get()
        ch["recognizer"] = new_recognizer
        ch["restart_event"] = new_evt

    def _worker(self) -> None:
        self._emit(
            {
                "type": "log",
                "level": "info",
                "message": (
                    "Initializing Azure speech recognizer (STT mode) "
                    f"(sdk={getattr(speech_sdk, '__version__', 'unknown')})"
                ),
            }
        )
        self._emit({"type": "status", "status": "starting", "running": True})

        try:
            self._refresh_device_labels()
            cfg = self._get_runtime_config()

            if cfg.capture_mode == "dual":
                channels = self._start_dual_mode(cfg)
            else:
                channels = self._start_single_mode(cfg)

            with self._lock:
                self._recognizers = [ch["recognizer"] for ch in channels]

            self._emit(
                {"type": "log", "level": "info", "message": "Recognition started"}
            )
            self._emit({"type": "status", "status": "listening", "running": True})

            # Monitor loop: handle per-channel buffer-overflow restarts individually
            # so a silent channel never interrupts a healthy active one.
            while not self._stop_event.is_set():
                for ch in channels:
                    if ch["restart_event"].is_set():
                        ch["restart_event"].clear()
                        label = ch["speaker_label"]
                        self._emit(
                            {
                                "type": "log",
                                "level": "info",
                                "message": f"[{label}] Restarting recognition after buffer overflow...",
                            }
                        )
                        self._restart_channel(ch)
                        with self._lock:
                            self._recognizers = [c["recognizer"] for c in channels]
                        self._emit(
                            {
                                "type": "log",
                                "level": "info",
                                "message": f"[{label}] Recognition restarted",
                            }
                        )
                time.sleep(0.2)

            # Normal stop: tear down all channels.
            self._emit(
                {"type": "log", "level": "info", "message": "Stopping recognition"}
            )
            for ch in channels:
                try:
                    ch["recognizer"].stop_continuous_recognition_async().get()
                except Exception:
                    pass
            with self._lock:
                self._recognizers = []

        except Exception as ex:
            err_text = str(ex).strip()
            self._emit(
                {
                    "type": "log",
                    "level": "error",
                    "message": f"Worker error: {err_text or repr(ex)}",
                }
            )
            if err_text == "5":
                self._emit(
                    {
                        "type": "log",
                        "level": "error",
                        "message": (
                            "Likely microphone access issue: mic busy by another app "
                            "or permission denied."
                        ),
                    }
                )
            self._emit(
                {
                    "type": "log",
                    "level": "debug",
                    "message": traceback.format_exc(limit=3),
                }
            )
            self._emit({"type": "status", "status": f"error: {ex}", "running": False})
        finally:
            with self._lock:
                self._recognizers = []
                self._thread = None
                self._running = False
            self._emit({"type": "status", "status": "stopped", "running": False})
