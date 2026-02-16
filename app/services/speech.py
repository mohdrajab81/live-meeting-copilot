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
        for kwargs in (
            {"speech_key": self._settings.speech_key, "region": self._settings.speech_region},
            {"subscription": self._settings.speech_key, "region": self._settings.speech_region},
        ):
            try:
                config = speech_sdk.SpeechConfig(**kwargs)
                break
            except TypeError:
                continue
        else:
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
        for kwargs in (
            {"speech_config": config, "audio_config": audio},
        ):
            try:
                return speech_sdk.SpeechRecognizer(**kwargs)
            except TypeError:
                continue
        return speech_sdk.SpeechRecognizer(config, audio)

    def _make_audio_config_single(self, cfg: RuntimeConfig):
        if cfg.audio_source == "device_id" and (cfg.input_device_id or "").strip():
            return speech_sdk.audio.AudioConfig(device_name=cfg.input_device_id.strip())
        return speech_sdk.audio.AudioConfig(use_default_microphone=True)

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
    ) -> None:
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
            self._emit(
                {
                    "type": "final",
                    "speaker": speaker_key,
                    "speaker_label": speaker_label,
                    "en": en_text,
                    "ar": "",
                    "ts": time.time(),
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
            self._stop_event.set()

        recognizer.recognizing.connect(on_recognizing)
        recognizer.recognized.connect(on_recognized)
        recognizer.canceled.connect(on_canceled)

    def _start_single_mode(self, cfg: RuntimeConfig) -> list[speech_sdk.SpeechRecognizer]:
        config = self._make_speech_config(cfg)
        device_id = (cfg.input_device_id or "").strip()
        audio = self._make_audio_config_single(cfg)

        if cfg.audio_source == "device_id" and device_id:
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
            self._emit(
                {
                    "type": "log",
                    "level": "warning",
                    "message": "audio_source=device_id but no input_device_id set; using default microphone",
                }
            )
        else:
            self._emit(
                {
                    "type": "log",
                    "level": "info",
                    "message": "Using default system microphone input",
                }
            )

        recognizer = self._make_recognizer(config, audio)
        self._wire_handlers(recognizer, cfg, "default", "Speaker")
        recognizer.start_continuous_recognition_async().get()
        return [recognizer]

    def _start_dual_mode(self, cfg: RuntimeConfig) -> list[speech_sdk.SpeechRecognizer]:
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
                    f"[{local_label}] device: "
                    f"{self._device_display_name(local_device)}"
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

        local_cfg = self._make_speech_config(cfg)
        remote_cfg = self._make_speech_config(cfg)

        local_recognizer = self._make_recognizer(
            local_cfg,
            self._make_audio_config_device(local_device),
        )
        remote_recognizer = self._make_recognizer(
            remote_cfg,
            self._make_audio_config_device(remote_device),
        )

        self._wire_handlers(local_recognizer, cfg, "local", local_label)
        self._wire_handlers(remote_recognizer, cfg, "remote", remote_label)

        local_recognizer.start_continuous_recognition_async().get()
        remote_recognizer.start_continuous_recognition_async().get()
        return [local_recognizer, remote_recognizer]

    def _worker(self) -> None:
        cfg = self._get_runtime_config()
        recognizers: list[speech_sdk.SpeechRecognizer] = []
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
            if cfg.capture_mode == "dual":
                recognizers = self._start_dual_mode(cfg)
            else:
                recognizers = self._start_single_mode(cfg)

            with self._lock:
                self._recognizers = recognizers

            self._emit({"type": "log", "level": "info", "message": "Recognition started"})
            self._emit({"type": "status", "status": "listening", "running": True})

            while not self._stop_event.is_set():
                time.sleep(0.2)

            self._emit({"type": "log", "level": "info", "message": "Stopping recognition"})
            for recognizer in recognizers:
                recognizer.stop_continuous_recognition_async().get()

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
