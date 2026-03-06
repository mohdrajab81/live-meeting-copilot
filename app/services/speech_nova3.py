import importlib
import json
import sys
import threading
import time
import traceback
from dataclasses import dataclass
from typing import Any, Callable

from app.config import RuntimeConfig, Settings


EventCallback = Callable[[dict[str, Any]], None]
ConfigProvider = Callable[[], RuntimeConfig]

# PyAudio instances are intentionally never terminated during the process lifetime.
# PyAudio.__del__() calls Pa_Terminate() which can crash on Windows WASAPI if any
# internal PortAudio callback threads are still winding down.  We park spent
# instances here instead, letting the OS reclaim them when the process exits.
_pa_graveyard: list[Any] = []


@dataclass
class _NovaStream:
    name: str
    socket: Any
    context: Any
    audio_stream: Any
    listener_thread: threading.Thread
    pump_thread: threading.Thread
    keepalive_thread: threading.Thread
    sample_rate: int
    channels: int
    device_index: int
    device_name: str
    blocksize: int


@dataclass
class _NovaStreamState:
    anchor_ts: float
    request_id: str
    last_partial_signature: tuple[Any, ...] | None
    last_final_signature: tuple[Any, ...] | None
    pending_final_chunks: list[dict[str, Any]]
    last_live_partial_text: str
    last_live_partial_start_raw: float | None
    last_live_partial_end_raw: float | None
    last_live_partial_speaker_id: int | None


class Nova3SpeechService:
    """Nova-3 live STT logging tap using hardcoded dual capture sources.

    Current mode:
    - Open two independent Nova-3 websocket streams.
    - Stream raw PCM16 from:
      1) default input microphone
      2) default WASAPI loopback output
    - Log all Nova events and raw payloads in detail.
    - Do NOT emit transcript partial/final events yet.
    """

    def __init__(
        self,
        settings: Settings,
        on_event: EventCallback,
        get_runtime_config: ConfigProvider,
    ) -> None:
        self._settings = settings
        self._on_event = on_event
        self._get_runtime_config = get_runtime_config
        self._lock = threading.RLock()
        self._running = False
        self._stop_event = threading.Event()
        self._streams: list[_NovaStream] = []
        self._stream_state: dict[str, _NovaStreamState] = {}
        self._pa: Any | None = None

    @property
    def running(self) -> bool:
        with self._lock:
            return self._running

    def _emit(self, payload: dict[str, Any]) -> None:
        self._on_event(payload)

    def _emit_log(self, level: str, message: str) -> None:
        self._emit({"type": "log", "level": level, "message": message})

    @staticmethod
    def _truncate(text: str, max_len: int = 220) -> str:
        value = str(text or "")
        return value if len(value) <= max_len else f"{value[: max_len - 3]}..."

    @staticmethod
    def _to_payload(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (dict, list, str, int, float, bool)):
            return value
        for attr in ("to_dict", "model_dump", "dict"):
            fn = getattr(value, attr, None)
            if callable(fn):
                try:
                    return fn()
                except Exception:
                    pass
        if hasattr(value, "__dict__"):
            try:
                return {
                    str(k): v
                    for k, v in vars(value).items()
                    if not str(k).startswith("_")
                }
            except Exception:
                pass
        return str(value)

    @staticmethod
    def _event_transcript_preview(payload: Any) -> str:
        if not isinstance(payload, dict):
            return ""
        channel = payload.get("channel")
        if not isinstance(channel, dict):
            return ""
        alternatives = channel.get("alternatives")
        if not isinstance(alternatives, list) or not alternatives:
            return ""
        first = alternatives[0] if isinstance(alternatives[0], dict) else {}
        transcript = str(first.get("transcript", "") or "").strip()
        if not transcript:
            return ""
        return transcript

    @staticmethod
    def _event_speaker_ids(payload: Any) -> list[int]:
        if not isinstance(payload, dict):
            return []
        channel = payload.get("channel")
        if not isinstance(channel, dict):
            return []
        alternatives = channel.get("alternatives")
        if not isinstance(alternatives, list) or not alternatives:
            return []
        first = alternatives[0] if isinstance(alternatives[0], dict) else {}
        words = first.get("words")
        if not isinstance(words, list):
            return []
        speakers: set[int] = set()
        for word in words:
            if not isinstance(word, dict):
                continue
            raw = word.get("speaker")
            if isinstance(raw, bool):
                continue
            try:
                speakers.add(int(raw))
            except Exception:
                continue
        return sorted(speakers)

    @classmethod
    def _format_event_summary(cls, event_name: str, payload: Any) -> str:
        if isinstance(payload, dict):
            keys = list(payload.keys())[:10]
            parts: list[str] = [f"event={event_name}", f"keys={keys}"]
            msg_type = str(payload.get("type", "") or "").strip()
            if msg_type:
                parts.append(f"type={msg_type}")
            if "is_final" in payload:
                parts.append(f"is_final={bool(payload.get('is_final'))}")
            if "speech_final" in payload:
                parts.append(f"speech_final={bool(payload.get('speech_final'))}")
            if "start" in payload:
                parts.append(f"start={payload.get('start')}")
            if "duration" in payload:
                parts.append(f"duration={payload.get('duration')}")
            if "channel_index" in payload:
                parts.append(f"channel_index={payload.get('channel_index')}")
            transcript = cls._event_transcript_preview(payload)
            if transcript:
                parts.append(f"transcript='{cls._truncate(transcript, 140)}'")
            speaker_ids = cls._event_speaker_ids(payload)
            if speaker_ids:
                parts.append(f"speakers={speaker_ids}")
            return " | ".join(parts)
        if isinstance(payload, list):
            return f"event={event_name} | payload=list[{len(payload)}]"
        return f"event={event_name} | payload={cls._truncate(str(payload), 200)}"

    def _log_nova_event(self, event_name: str, payload: Any) -> None:
        summary = self._format_event_summary(event_name, payload)
        self._emit_log("info", f"[Nova3] {summary}")
        try:
            raw = json.dumps(payload, ensure_ascii=True, default=str)
        except Exception:
            raw = str(payload)
        self._emit_log("debug", f"[Nova3][raw:{event_name}] {self._truncate(raw, 4000)}")

    @staticmethod
    def _build_live_options(
        cfg: RuntimeConfig, *, sample_rate: int, channels: int
    ) -> dict[str, str]:
        endpointing_ms = max(10, int(cfg.end_silence_ms))
        # Deepgram hosted live endpoint requires utterance_end_ms >= 1000ms.
        utterance_end_ms = max(1000, int(cfg.end_silence_ms))
        language = str(getattr(cfg, "recognition_language", "") or "").strip().replace("_", "-")
        if not language:
            language = "multi"
        return {
            "model": "nova-3",
            "language": language,
            "diarize": "true",
            "punctuate": "true",
            "smart_format": "true",
            "interim_results": "true",
            "vad_events": "true",
            "endpointing": str(endpointing_ms),
            "utterance_end_ms": str(utterance_end_ms),
            "encoding": "linear16",
            "sample_rate": str(int(sample_rate)),
            "channels": str(int(channels)),
        }

    def _log_governance(self, cfg: RuntimeConfig) -> None:
        active = [
            f"recognition_language={cfg.recognition_language}",
            f"end_silence_ms={cfg.end_silence_ms}",
            f"local_speaker_label='{str(cfg.local_speaker_label or 'You').strip() or 'You'}'",
            f"remote_speaker_label='{str(cfg.remote_speaker_label or 'Remote').strip() or 'Remote'}'",
        ]
        self._emit_log("info", f"[Nova3] Governance active settings: {', '.join(active)}.")

        forced: list[str] = []
        ignored: list[str] = []

        # Current Nova-3 preview implementation is intentionally fixed to
        # dual capture: default local mic + default WASAPI loopback.
        if str(cfg.capture_mode or "").strip().lower() != "dual":
            forced.append("capture_mode forced to dual")

        if str(cfg.audio_source or "").strip().lower() != "default":
            ignored.append("audio_source")
        if str(cfg.input_device_id or "").strip():
            ignored.append("input_device_id")
        if str(cfg.local_input_device_id or "").strip():
            ignored.append("local_input_device_id")
        if str(cfg.remote_input_device_id or "").strip():
            ignored.append("remote_input_device_id")
        if str(cfg.recognition_language or "").strip().lower() == "multi":
            self._emit_log(
                "warning",
                "[Nova3] recognition_language is set to multi; this can reduce accuracy for monolingual calls.",
            )

        if forced:
            self._emit_log("warning", f"[Nova3] Governance forced behavior: {', '.join(forced)}.")
        if ignored:
            self._emit_log("warning", f"[Nova3] Governance ignored settings: {', '.join(ignored)}.")

    def _ensure_stream_state(self, stream_name: str) -> _NovaStreamState:
        with self._lock:
            state = self._stream_state.get(stream_name)
            if state is None:
                state = _NovaStreamState(
                    anchor_ts=time.time(),
                    request_id="",
                    last_partial_signature=None,
                    last_final_signature=None,
                    pending_final_chunks=[],
                    last_live_partial_text="",
                    last_live_partial_start_raw=None,
                    last_live_partial_end_raw=None,
                    last_live_partial_speaker_id=None,
                )
                self._stream_state[stream_name] = state
            return state

    @staticmethod
    def _safe_non_negative_float(value: Any) -> float | None:
        try:
            parsed = float(value)
        except Exception:
            return None
        if parsed < 0:
            return None
        return parsed

    @staticmethod
    def _first_alternative(payload: dict[str, Any]) -> dict[str, Any]:
        channel = payload.get("channel")
        if not isinstance(channel, dict):
            return {}
        alternatives = channel.get("alternatives")
        if not isinstance(alternatives, list) or not alternatives:
            return {}
        first = alternatives[0]
        return first if isinstance(first, dict) else {}

    @classmethod
    def _dominant_word_speaker_id(cls, payload: dict[str, Any]) -> int | None:
        alt = cls._first_alternative(payload)
        words = alt.get("words")
        if not isinstance(words, list):
            return None
        counts: dict[int, int] = {}
        order: list[int] = []
        for word in words:
            if not isinstance(word, dict):
                continue
            raw = word.get("speaker")
            if isinstance(raw, bool):
                continue
            try:
                sid = int(raw)
            except Exception:
                continue
            if sid not in counts:
                counts[sid] = 0
                order.append(sid)
            counts[sid] += 1
        if not counts:
            return None
        return max(order, key=lambda sid: (counts.get(sid, 0), -order.index(sid)))

    @staticmethod
    def _request_id_from_payload(payload: dict[str, Any]) -> str:
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            return ""
        return str(metadata.get("request_id", "") or "").strip()

    def _speaker_for_stream(self, stream_name: str) -> tuple[str, str]:
        cfg = self._get_runtime_config()
        if stream_name == "local_mic":
            label = str(cfg.local_speaker_label or "You").strip() or "You"
            return "local", label
        if stream_name == "wasapi_loopback":
            label = str(cfg.remote_speaker_label or "Remote").strip() or "Remote"
            return "remote", label
        return "default", "Speaker"

    def _build_timing(
        self, stream_name: str, payload: dict[str, Any]
    ) -> tuple[float, float, float, float, float | None, str, float]:
        now_ts = time.time()
        state = self._ensure_stream_state(stream_name)
        anchor_ts = float(state.anchor_ts or now_ts)
        offset_sec = self._safe_non_negative_float(payload.get("start"))
        duration_sec = self._safe_non_negative_float(payload.get("duration")) or 0.0
        timing_source = "event_only"
        start_ts = now_ts
        end_ts = now_ts
        if offset_sec is not None:
            timing_source = "offset"
            start_ts = max(0.0, anchor_ts + offset_sec)
            end_ts = start_ts + duration_sec if duration_sec > 0 else start_ts
        elif duration_sec > 0:
            timing_source = "duration_backfill"
            start_ts = max(0.0, now_ts - duration_sec)
            end_ts = now_ts
        if start_ts > now_ts:
            start_ts = now_ts
        if end_ts > now_ts:
            end_ts = now_ts
        if end_ts < start_ts:
            end_ts = start_ts
        if duration_sec <= 0.0:
            duration_sec = max(0.0, end_ts - start_ts)
        return (
            now_ts,
            start_ts,
            end_ts,
            duration_sec,
            offset_sec,
            timing_source,
            anchor_ts,
        )

    @staticmethod
    def _combine_cached_transcripts(chunks: list[dict[str, Any]]) -> str:
        parts = [str(chunk.get("transcript", "") or "").strip() for chunk in chunks]
        return " ".join(part for part in parts if part).strip()

    @staticmethod
    def _append_unique_tail(base: str, addition: str) -> str:
        left = str(base or "").strip()
        right = str(addition or "").strip()
        if not left:
            return right
        if not right:
            return left
        left_lower = left.lower()
        right_lower = right.lower()
        if left_lower.endswith(right_lower):
            return left
        if right_lower.startswith(left_lower):
            return right
        max_overlap = min(len(left), len(right))
        overlap = 0
        for size in range(max_overlap, 0, -1):
            if left_lower[-size:] == right_lower[:size]:
                overlap = size
                break
        if overlap:
            return f"{left}{right[overlap:]}".strip()
        return f"{left} {right}".strip()

    @staticmethod
    def _cached_speaker_id(chunks: list[dict[str, Any]]) -> int | None:
        speaker_votes: dict[int, int] = {}
        speaker_order: list[int] = []
        for chunk in chunks:
            sid = chunk.get("speaker_id")
            if sid is None:
                continue
            speaker_votes[sid] = speaker_votes.get(sid, 0) + 1
            if sid not in speaker_order:
                speaker_order.append(sid)
        if not speaker_votes:
            return None
        return max(
            speaker_order,
            key=lambda sid: (speaker_votes.get(sid, 0), -speaker_order.index(sid)),
        )

    def _emit_final_from_parts(
        self,
        *,
        stream_name: str,
        state: _NovaStreamState,
        speaker_key: str,
        speaker_label: str,
        speaker_sub_id: str,
        payload: dict[str, Any],
        final_text: str,
        start_raw_values: list[float],
        end_raw_values: list[float],
        speech_final: bool,
    ) -> None:
        (
            now_ts,
            start_ts,
            end_ts,
            duration_sec,
            offset_sec,
            timing_source,
            anchor_ts,
        ) = self._build_timing(stream_name, payload)
        if start_raw_values:
            earliest_start = min(start_raw_values)
            start_ts = max(0.0, anchor_ts + earliest_start)
            offset_sec = earliest_start
            timing_source = "offset"
        if end_raw_values:
            latest_end = max(end_raw_values)
            end_ts = max(start_ts, min(max(0.0, anchor_ts + latest_end), now_ts))
            duration_sec = max(0.0, end_ts - start_ts)
        start_ts = round(start_ts, 6)
        end_ts = round(end_ts, 6)
        duration_sec = round(max(0.0, duration_sec), 6)
        self._emit(
            {
                "type": "final",
                "speaker": speaker_key,
                "speaker_label": speaker_label,
                "speaker_sub_id": speaker_sub_id,
                "source_stream": stream_name,
                "en": final_text,
                "ar": "",
                "ts": now_ts,
                "start_ts": start_ts,
                "end_ts": end_ts,
                "duration_sec": duration_sec,
                "offset_sec": offset_sec,
                "timing_source": timing_source,
                "recognizer_session_id": str(state.request_id or ""),
                "recognizer_anchor_ts": anchor_ts,
                "speech_final": speech_final,
            }
        )

    def _integrate_results_event(self, stream_name: str, payload: dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            return
        is_final = bool(payload.get("is_final"))
        speech_final = bool(payload.get("speech_final"))
        state = self._ensure_stream_state(stream_name)
        req_id = self._request_id_from_payload(payload)
        if req_id:
            state.request_id = req_id
        transcript = self._event_transcript_preview(payload)
        start_raw = self._safe_non_negative_float(payload.get("start"))
        duration_raw = self._safe_non_negative_float(payload.get("duration"))
        end_raw = start_raw + (duration_raw or 0.0) if start_raw is not None else None
        speaker_key, speaker_label = self._speaker_for_stream(stream_name)
        dominant_sid = self._dominant_word_speaker_id(payload)
        speaker_sub_id = f"{speaker_key}[{dominant_sid}]" if dominant_sid is not None else ""
        if not transcript:
            if not is_final and not speech_final:
                cached_text = self._combine_cached_transcripts(state.pending_final_chunks)
                if cached_text:
                    cached_sid = self._cached_speaker_id(state.pending_final_chunks)
                    if cached_sid is not None:
                        speaker_sub_id = f"{speaker_key}[{cached_sid}]"
                    self._emit(
                        {
                            "type": "partial",
                            "speaker": speaker_key,
                            "speaker_label": speaker_label,
                            "speaker_sub_id": speaker_sub_id,
                            "source_stream": stream_name,
                            "en": cached_text,
                            "ar": "",
                        }
                    )
                else:
                    self._emit(
                        {
                            "type": "partial_clear",
                            "speaker": speaker_key,
                            "speaker_label": speaker_label,
                            "reason": "nova_empty_partial",
                        }
                    )
                return
            if is_final and speech_final:
                cached_chunks = list(state.pending_final_chunks)
                state.pending_final_chunks = []
                cached_text = self._combine_cached_transcripts(cached_chunks)
                final_text = self._append_unique_tail(cached_text, state.last_live_partial_text)
                if not final_text:
                    return
                cached_start_values = [
                    float(chunk["start_raw"])
                    for chunk in cached_chunks
                    if chunk.get("start_raw") is not None
                ]
                cached_end_values = [
                    float(chunk["end_raw"])
                    for chunk in cached_chunks
                    if chunk.get("end_raw") is not None
                ]
                if state.last_live_partial_start_raw is not None:
                    cached_start_values.append(float(state.last_live_partial_start_raw))
                if state.last_live_partial_end_raw is not None:
                    cached_end_values.append(float(state.last_live_partial_end_raw))
                cached_sid = self._cached_speaker_id(cached_chunks)
                if cached_sid is None:
                    cached_sid = state.last_live_partial_speaker_id
                if cached_sid is not None:
                    speaker_sub_id = f"{speaker_key}[{cached_sid}]"
                self._emit_final_from_parts(
                    stream_name=stream_name,
                    state=state,
                    speaker_key=speaker_key,
                    speaker_label=speaker_label,
                    speaker_sub_id=speaker_sub_id,
                    payload=payload,
                    final_text=final_text,
                    start_raw_values=cached_start_values,
                    end_raw_values=cached_end_values,
                    speech_final=speech_final,
                )
                state.last_live_partial_text = ""
                state.last_live_partial_start_raw = None
                state.last_live_partial_end_raw = None
                state.last_live_partial_speaker_id = None
            return
        signature = (transcript, start_raw, duration_raw, is_final, speech_final)
        if is_final:
            if state.last_final_signature == signature:
                return
            state.last_final_signature = signature
            state.last_partial_signature = None
        else:
            if state.last_partial_signature == signature:
                return
            state.last_partial_signature = signature

        if not is_final:
            cached_text = self._combine_cached_transcripts(state.pending_final_chunks)
            live_text = self._append_unique_tail(cached_text, transcript)
            cached_sid = self._cached_speaker_id(state.pending_final_chunks)
            if cached_sid is not None:
                speaker_sub_id = f"{speaker_key}[{cached_sid}]"
            state.last_live_partial_text = transcript
            state.last_live_partial_start_raw = start_raw
            state.last_live_partial_end_raw = end_raw
            state.last_live_partial_speaker_id = dominant_sid
            self._emit(
                {
                    "type": "partial",
                    "speaker": speaker_key,
                    "speaker_label": speaker_label,
                    "speaker_sub_id": speaker_sub_id,
                    "source_stream": stream_name,
                    "en": live_text,
                    "ar": "",
                }
            )
            return

        end_raw = start_raw + (duration_raw or 0.0) if start_raw is not None else None
        if not speech_final:
            replaced = False
            if start_raw is not None:
                for idx, chunk in enumerate(state.pending_final_chunks):
                    chunk_start = chunk.get("start_raw")
                    if chunk_start is None:
                        continue
                    if abs(float(chunk_start) - start_raw) < 1e-6:
                        state.pending_final_chunks[idx] = {
                            "start_raw": start_raw,
                            "end_raw": end_raw,
                            "transcript": transcript,
                            "speaker_id": dominant_sid,
                        }
                        replaced = True
                        break
            if not replaced:
                state.pending_final_chunks.append(
                    {
                        "start_raw": start_raw,
                        "end_raw": end_raw,
                        "transcript": transcript,
                        "speaker_id": dominant_sid,
                    }
                )
                state.pending_final_chunks.sort(
                    key=lambda chunk: float("inf")
                    if chunk.get("start_raw") is None
                    else float(chunk["start_raw"])
                )
            state.last_live_partial_text = ""
            state.last_live_partial_start_raw = None
            state.last_live_partial_end_raw = None
            state.last_live_partial_speaker_id = None
            cached_text = self._combine_cached_transcripts(state.pending_final_chunks)
            cached_sid = self._cached_speaker_id(state.pending_final_chunks)
            cached_sub_id = (
                f"{speaker_key}[{cached_sid}]" if cached_sid is not None else speaker_sub_id
            )
            self._emit(
                {
                    "type": "partial",
                    "speaker": speaker_key,
                    "speaker_label": speaker_label,
                    "speaker_sub_id": cached_sub_id,
                    "source_stream": stream_name,
                    "en": cached_text,
                    "ar": "",
                }
            )
            return

        cached_chunks = list(state.pending_final_chunks)
        state.pending_final_chunks = []
        cached_text = self._combine_cached_transcripts(cached_chunks)
        final_text = self._append_unique_tail(cached_text, transcript)
        cached_start_values = [
            float(chunk["start_raw"])
            for chunk in cached_chunks
            if chunk.get("start_raw") is not None
        ]
        cached_end_values = [
            float(chunk["end_raw"])
            for chunk in cached_chunks
            if chunk.get("end_raw") is not None
        ]
        cached_sid = self._cached_speaker_id(cached_chunks)
        if cached_sid is not None:
            speaker_sub_id = f"{speaker_key}[{cached_sid}]"
        self._emit_final_from_parts(
            stream_name=stream_name,
            state=state,
            speaker_key=speaker_key,
            speaker_label=speaker_label,
            speaker_sub_id=speaker_sub_id,
            payload=payload,
            final_text=final_text,
            start_raw_values=cached_start_values,
            end_raw_values=cached_end_values,
            speech_final=speech_final,
        )
        state.last_live_partial_text = ""
        state.last_live_partial_start_raw = None
        state.last_live_partial_end_raw = None
        state.last_live_partial_speaker_id = None

    def _shutdown(self, *, status: str, level: str, message: str) -> bool:
        with self._lock:
            had_runtime = self._running or bool(self._streams) or (self._pa is not None)
            self._running = False
            self._stop_event.set()
            streams = list(self._streams)
            self._streams = []
            self._stream_state = {}
            pa = self._pa   # keep a local reference — prevents __del__ while streams are open
            self._pa = None

        for stream in streams:
            self._close_stream(stream)

        # Park the spent PyAudio instance so PyAudio.__del__() → Pa_Terminate() is
        # never called during the process lifetime.  Pa_Terminate() can segfault on
        # Windows WASAPI if any internal PortAudio callback threads are still alive.
        # The OS reclaims all resources when the process exits.
        if pa is not None:
            _pa_graveyard.append(pa)

        if had_runtime:
            self._emit_log(level, message)
            self._emit({"type": "status", "status": status, "running": False})
        return had_runtime

    def _close_stream(self, stream: _NovaStream) -> None:
        try:
            stream.socket.send_finalize()
        except Exception:
            pass
        try:
            stream.socket.send_close_stream()
        except Exception:
            pass
        # IMPORTANT: join workers before touching the PortAudio stream object.
        # Closing a WASAPI stream while another thread is inside read() can
        # trigger a native access violation on Windows.
        current = threading.current_thread()
        for worker in (stream.pump_thread, stream.listener_thread, stream.keepalive_thread):
            if worker.is_alive() and worker is not current:
                worker.join(timeout=1.5)

        # Only close audio stream once the pump thread is fully out of read().
        if stream.pump_thread.is_alive():
            self._emit_log(
                "warning",
                (
                    f"[Nova3] Pump thread did not stop in time for '{stream.name}'. "
                    "Skipping immediate audio stream close to avoid native crash."
                ),
            )
            return

        try:
            stream.audio_stream.stop_stream()
        except Exception:
            pass
        try:
            stream.audio_stream.close()
        except Exception:
            pass

        # DO NOT call context.__exit__() here.
        # Deepgram/websockets sync teardown currently hits a race on Windows
        # during stop (observed access violation in websocket close/join path).
        # send_finalize/send_close_stream above is sufficient for this build.

    def _event_name_from_message(self, stream_name: str, payload: Any) -> str:
        if isinstance(payload, dict):
            msg_type = str(payload.get("type", "") or "").strip()
            if msg_type:
                return f"{stream_name}:{msg_type}"
        return f"{stream_name}:message"

    def _register_handlers(self, stream_name: str, socket: Any, event_type: Any) -> None:
        def on_open(_payload: Any) -> None:
            state = self._ensure_stream_state(stream_name)
            state.anchor_ts = time.time()
            self._log_nova_event(f"{stream_name}:open", {"type": "Open"})

        def on_message(payload: Any) -> None:
            parsed = self._to_payload(payload)
            self._log_nova_event(self._event_name_from_message(stream_name, parsed), parsed)
            if not isinstance(parsed, dict):
                return
            msg_type = str(parsed.get("type", "") or "")
            if msg_type == "Results":
                self._integrate_results_event(stream_name, parsed)
                return
            if msg_type == "SpeechStarted":
                speaker_key, speaker_label = self._speaker_for_stream(stream_name)
                self._emit(
                    {
                        "type": "activity",
                        "speaker": speaker_key,
                        "speaker_label": speaker_label,
                        "source_stream": stream_name,
                        "has_speech": True,
                        "ts": time.time(),
                    }
                )

        def on_error(payload: Any) -> None:
            if self._stop_event.is_set():
                self._emit_log(
                    "debug",
                    f"[Nova3] Ignoring stream error during shutdown ({stream_name}).",
                )
                return
            parsed = self._to_payload(payload)
            self._log_nova_event(f"{stream_name}:error", parsed)
            self._shutdown(
                status="error",
                level="error",
                message=f"[Nova3] Stream '{stream_name}' closed due to error.",
            )

        def on_close(_payload: Any) -> None:
            self._log_nova_event(f"{stream_name}:close", {"type": "Close"})

        socket.on(event_type.OPEN, on_open)
        socket.on(event_type.MESSAGE, on_message)
        socket.on(event_type.ERROR, on_error)
        socket.on(event_type.CLOSE, on_close)

    def _run_listener(self, stream_name: str, socket: Any) -> None:
        try:
            socket.start_listening()
        except Exception as ex:
            if self._stop_event.is_set():
                return
            self._emit_log("error", f"[Nova3] Listener failed for '{stream_name}': {ex}")
            self._emit_log("debug", traceback.format_exc(limit=3))
            self._shutdown(
                status="error",
                level="error",
                message=f"[Nova3] Listener crashed for '{stream_name}'.",
            )

    def _run_keepalive(self, stream: _NovaStream) -> None:
        # Deepgram may close idle listen streams (NET0001) when no audio bytes
        # are sent for a while. KeepAlive prevents that during silent periods.
        interval_sec = 5.0
        while not self._stop_event.wait(interval_sec):
            try:
                stream.socket.send_keep_alive()
            except Exception as ex:
                if self._stop_event.is_set():
                    return
                self._emit_log(
                    "debug",
                    f"[Nova3] KeepAlive failed ({stream.name}): {ex}",
                )
                return

    def _pump_audio(self, stream: _NovaStream) -> None:
        while not self._stop_event.is_set():
            try:
                audio_chunk = stream.audio_stream.read(
                    stream.blocksize, exception_on_overflow=False
                )
            except Exception as ex:
                if self._stop_event.is_set():
                    return
                self._emit_log(
                    "error",
                    f"[Nova3] Audio read failed ({stream.name}): {ex}",
                )
                self._emit_log("debug", traceback.format_exc(limit=3))
                self._shutdown(
                    status="error",
                    level="error",
                    message=f"[Nova3] Audio capture stopped for '{stream.name}'.",
                )
                return
            if not audio_chunk:
                continue
            try:
                stream.socket.send_media(audio_chunk)
            except Exception as ex:
                if self._stop_event.is_set():
                    return
                self._emit_log(
                    "error",
                    f"[Nova3] Websocket send failed ({stream.name}): {ex}",
                )
                self._emit_log("debug", traceback.format_exc(limit=3))
                self._shutdown(
                    status="error",
                    level="error",
                    message=f"[Nova3] Websocket send failed for '{stream.name}'.",
                )
                return

    def _open_stream(
        self,
        *,
        client: Any,
        event_type: Any,
        pyaudio_module: Any,
        pa: Any,
        cfg: RuntimeConfig,
        name: str,
        device_info: dict[str, Any],
        device_index: int,
    ) -> _NovaStream:
        sample_rate = max(8000, int(float(device_info.get("defaultSampleRate", 16000))))
        max_in = int(device_info.get("maxInputChannels", 1) or 1)
        channels = max(1, min(1, max_in))
        blocksize = max(256, sample_rate // 10)
        connect_kwargs = self._build_live_options(
            cfg, sample_rate=sample_rate, channels=channels
        )
        self._emit_log(
            "debug",
            (
                f"[Nova3] Opening stream '{name}' with options: "
                f"{json.dumps(connect_kwargs, ensure_ascii=True)}"
            ),
        )

        context = client.listen.v1.connect(**connect_kwargs)
        socket = context.__enter__()
        self._register_handlers(name, socket, event_type)

        pcm16_format = getattr(pyaudio_module, "paInt16", None)
        if pcm16_format is None:
            raise RuntimeError("pyaudiowpatch is missing paInt16 format constant.")

        audio_stream = pa.open(
            format=pcm16_format,
            channels=channels,
            rate=sample_rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=blocksize,
            start=True,
        )

        stream = _NovaStream(
            name=name,
            socket=socket,
            context=context,
            audio_stream=audio_stream,
            listener_thread=threading.Thread(target=lambda: None, daemon=True),
            pump_thread=threading.Thread(target=lambda: None, daemon=True),
            keepalive_thread=threading.Thread(target=lambda: None, daemon=True),
            sample_rate=sample_rate,
            channels=channels,
            device_index=device_index,
            device_name=str(device_info.get("name", "") or f"device-{device_index}"),
            blocksize=blocksize,
        )
        stream.listener_thread = threading.Thread(
            target=self._run_listener,
            args=(name, socket),
            daemon=True,
        )
        stream.pump_thread = threading.Thread(
            target=self._pump_audio,
            args=(stream,),
            daemon=True,
        )
        stream.keepalive_thread = threading.Thread(
            target=self._run_keepalive,
            args=(stream,),
            daemon=True,
        )
        stream.listener_thread.start()
        stream.pump_thread.start()
        stream.keepalive_thread.start()
        return stream

    def start_recognition(self) -> bool:
        with self._lock:
            if self._running:
                return False
        self._stop_event.clear()

        api_key = str(self._settings.nova3_api_key or "").strip()
        if not api_key:
            self._emit_log("warning", "NOVA3_API_KEY is not set. Nova-3 cannot start.")
            return False

        try:
            deepgram = importlib.import_module("deepgram")
            socket_mod = importlib.import_module("deepgram.listen.v1.socket_client")
            pyaudio = importlib.import_module("pyaudiowpatch")
        except Exception as ex:
            self._emit_log(
                "warning",
                (
                    "Nova-3 requires packages: deepgram-sdk and pyaudiowpatch. "
                    f"Import failure: {type(ex).__name__}: {ex}"
                ),
            )
            self._emit_log("debug", f"[Nova3] Runtime interpreter: {sys.executable}")
            return False

        deepgram_client_cls = getattr(deepgram, "DeepgramClient", None)
        event_type = getattr(socket_mod, "EventType", None)
        py_audio_cls = getattr(pyaudio, "PyAudio", None)
        if not callable(deepgram_client_cls) or event_type is None or not callable(py_audio_cls):
            self._emit_log(
                "warning",
                "Unsupported Deepgram/PyAudio runtime shape for Nova-3.",
            )
            return False

        local_stream: _NovaStream | None = None
        loop_stream: _NovaStream | None = None
        pa: Any | None = None
        try:
            self._emit({"type": "status", "status": "starting", "running": True})
            cfg = self._get_runtime_config()
            self._log_governance(cfg)
            client = deepgram_client_cls(api_key=api_key)
            pa = py_audio_cls()

            local_device = pa.get_default_input_device_info()
            loopback_device = pa.get_default_wasapi_loopback()

            local_stream = self._open_stream(
                client=client,
                event_type=event_type,
                pyaudio_module=pyaudio,
                pa=pa,
                cfg=cfg,
                name="local_mic",
                device_info=local_device,
                device_index=int(local_device.get("index")),
            )
            loop_stream = self._open_stream(
                client=client,
                event_type=event_type,
                pyaudio_module=pyaudio,
                pa=pa,
                cfg=cfg,
                name="wasapi_loopback",
                device_info=loopback_device,
                device_index=int(loopback_device.get("index")),
            )

            with self._lock:
                self._pa = pa
                self._streams = [local_stream, loop_stream]
                self._running = True

            self._emit_log(
                "info",
                (
                    "[Nova3] Started hardcoded dual capture: "
                    f"local='{local_stream.device_name}' ({local_stream.sample_rate}Hz), "
                    f"loopback='{loop_stream.device_name}' ({loop_stream.sample_rate}Hz)."
                ),
            )
            self._emit_log(
                "info",
                (
                    "[Nova3] Event logging is active. "
                    "Transcript integration is enabled for non-empty Results events."
                ),
            )
            self._emit({"type": "status", "status": "listening", "running": True})
            return True
        except Exception as ex:
            self._emit_log("error", f"Nova-3 start failed: {ex}")
            self._emit_log("debug", traceback.format_exc(limit=3))
            # Ensure any partially-open stream workers can exit during cleanup.
            self._stop_event.set()
            if local_stream is not None:
                self._close_stream(local_stream)
            if loop_stream is not None:
                self._close_stream(loop_stream)
            # Park pa so __del__ → Pa_Terminate() is never called — see _shutdown().
            if pa is not None:
                _pa_graveyard.append(pa)
            self._emit({"type": "status", "status": "error", "running": False})
            return False

    def stop_recognition(self) -> bool:
        return self._shutdown(
            status="stopped",
            level="info",
            message="[Nova3] Stopped.",
        )
