"""
TranscriptStore — owns transcript state and translation metrics.

State: finals, live_partials, en_live, ar_live, translation metrics,
       speaker activity timestamps, bleed-suppress window.

Shares the AppController RLock for all mutations.
"""

import os
import time
import threading
from collections import deque
from typing import Any, Awaitable, Callable

from app.config import RuntimeConfig
from app.services.translation_pipeline import TranslationPipeline


BroadcastCallback = Callable[[dict[str, Any]], Awaitable[None]]
BroadcastLogCallback = Callable[[str, str], Awaitable[None]]
EmitTraceCallback = Callable[..., Awaitable[None]]


class TranscriptStore:
    def __init__(
        self,
        lock: threading.RLock,
        broadcast: BroadcastCallback,
        broadcast_log: BroadcastLogCallback,
        emit_trace_async: EmitTraceCallback,
        get_debug: Callable[[], bool],
    ) -> None:
        self._lock = lock
        self._broadcast = broadcast
        self._broadcast_log = broadcast_log
        self._emit_trace_async = emit_trace_async
        self._get_debug = get_debug

        # Late-bound after TranslationPipeline is created (avoids circular dep).
        self.translation: TranslationPipeline | None = None
        # Late-bound to supply live ws/status/running for telemetry broadcasts.
        self._get_telemetry_context: Callable[[], tuple[int, str, bool]] | None = None

        # Transcript state
        self.finals: list[dict[str, Any]] = []
        self.live_partials: dict[str, dict[str, Any]] = {}
        self.en_live = ""
        self.ar_live = ""

        # Speaker timing (for dual-mode bleed suppression)
        self._speaker_last_activity_ts: dict[str, float] = {
            "local": 0.0,
            "remote": 0.0,
            "default": 0.0,
        }
        self._bleed_suppress_window_sec = 1.6
        self.last_speech_activity_ts = time.time()

        # Translation metrics
        self.translation_latency_ms: deque[int] = deque(maxlen=240)
        self.translation_latest_ms: int | None = None
        self.translation_chars: int = 0
        self.translation_events: int = 0
        self.translation_cost_per_million_usd: float | None = self._load_cost_rate()

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _load_cost_rate() -> float | None:
        raw = (os.getenv("TRANSLATION_COST_PER_MILLION_USD", "") or "").strip()
        if not raw:
            return None
        try:
            value = float(raw)
        except Exception:
            return None
        return value if value > 0 else None

    def _median_ms_unlocked(self) -> int | None:
        if not self.translation_latency_ms:
            return None
        values = sorted(self.translation_latency_ms)
        n = len(values)
        mid = n // 2
        if n % 2 == 1:
            return int(values[mid])
        return int((values[mid - 1] + values[mid]) / 2)

    def _record_metrics_unlocked(self, req: dict[str, Any], now_ts: float) -> None:
        trigger_ts = float(req.get("trigger_ts", 0.0) or 0.0)
        if trigger_ts > 0.0:
            total_ms = max(0, int((now_ts - trigger_ts) * 1000))
            self.translation_latest_ms = total_ms
            self.translation_latency_ms.append(total_ms)
        text = str(req.get("text", "") or "")
        self.translation_chars += len(text)
        self.translation_events += 1

    def _refresh_live_buffers_unlocked(self) -> None:
        if not self.live_partials:
            self.en_live = ""
            self.ar_live = ""
            return
        entries = sorted(
            self.live_partials.values(),
            key=lambda item: float(item.get("ts", 0.0) or 0.0),
        )
        latest = entries[-1]
        self.en_live = str(latest.get("en", "") or "")
        self.ar_live = str(latest.get("ar", "") or "")

    # ── Public reads ──────────────────────────────────────────────────────────

    def get_finals(self) -> list[dict[str, Any]]:
        """Return the finals list directly (caller must hold the shared lock; do not mutate)."""
        return self.finals

    def get_finals_slice(self, start: int, end: int) -> list[dict[str, Any]]:
        return list(self.finals[start:end])

    def get_finals_count(self) -> int:
        return len(self.finals)

    # ── Mutations (called while holding the shared lock) ─────────────────────

    def append_final_unlocked(self, item: dict[str, Any], max_finals: int) -> None:
        start_ts = float(item.get("start_ts", item["ts"]) or item["ts"])
        ts = float(item.get("ts", time.time()) or time.time())
        if start_ts > ts:
            start_ts = ts
        if start_ts < 0:
            start_ts = 0.0
        end_ts = float(item.get("end_ts", ts) or ts)
        if end_ts < start_ts:
            end_ts = start_ts
        if end_ts > ts:
            end_ts = ts
        duration_sec = item.get("duration_sec")
        try:
            normalized_duration_sec = max(0.0, float(duration_sec))
        except Exception:
            normalized_duration_sec = max(0.0, end_ts - start_ts)
        offset_sec = item.get("offset_sec")
        try:
            normalized_offset_sec: float | None = max(0.0, float(offset_sec))
        except Exception:
            normalized_offset_sec = None
        try:
            recognizer_anchor_ts = float(item.get("recognizer_anchor_ts", 0.0) or 0.0)
        except Exception:
            recognizer_anchor_ts = 0.0

        self.finals.append(
            {
                "en": item["en"],
                "ar": item["ar"],
                "speaker": item["speaker"],
                "speaker_label": item["speaker_label"],
                "segment_id": item["segment_id"],
                "revision": item["revision"],
                "ts": ts,
                "start_ts": start_ts,
                "end_ts": end_ts,
                "duration_sec": normalized_duration_sec,
                "offset_sec": normalized_offset_sec,
                "timing_source": str(item.get("timing_source", "event_only") or "event_only"),
                "recognizer_session_id": str(item.get("recognizer_session_id", "") or ""),
                "recognizer_anchor_ts": recognizer_anchor_ts,
            }
        )
        if len(self.finals) > max_finals:
            self.finals = self.finals[-max_finals:]
        self.live_partials.pop(item["speaker"], None)
        self._refresh_live_buffers_unlocked()
        if item["en"] or item["ar"]:
            self.last_speech_activity_ts = time.time()

    def update_speaker_activity_unlocked(
        self, speaker: str, now_ts: float, *, has_speech: bool = True
    ) -> None:
        self._speaker_last_activity_ts[speaker] = now_ts
        if has_speech:
            self.last_speech_activity_ts = now_ts

    def should_suppress_dual_local_unlocked(
        self, payload: dict[str, Any], capture_mode: str
    ) -> bool:
        if capture_mode != "dual":
            return False
        speaker = str(payload.get("speaker", "default") or "default")
        if speaker != "local":
            return False
        remote_live = self.live_partials.get("remote")
        if remote_live and str(remote_live.get("en", "") or "").strip():
            return True
        now_ts = time.time()
        remote_ts = float(self._speaker_last_activity_ts.get("remote", 0.0) or 0.0)
        if remote_ts <= 0:
            return False
        return (now_ts - remote_ts) <= float(self._bleed_suppress_window_sec)

    def clear_unlocked(self) -> None:
        self.finals = []
        self.en_live = ""
        self.ar_live = ""
        self.live_partials = {}

    def clear_live_partial_unlocked(self, speaker: str) -> dict[str, Any] | None:
        removed = self.live_partials.pop(speaker, None)
        self._refresh_live_buffers_unlocked()
        if removed is None:
            return None
        return {
            "speaker": str(removed.get("speaker", speaker) or speaker),
            "speaker_label": str(removed.get("speaker_label", "Speaker") or "Speaker"),
            "segment_id": str(removed.get("segment_id", "") or ""),
            "revision": int(removed.get("revision", 0) or 0),
        }

    # ── Translation result callback (async, called from TranslationPipeline) ──

    async def apply_translation_result(
        self, req: dict[str, Any], ar_text: str
    ) -> None:
        kind = str(req.get("kind", "partial") or "partial")
        speaker = str(req.get("speaker", "default") or "default")
        segment_id = str(req.get("segment_id", "") or "")
        revision = int(req.get("revision", 0) or 0)
        translated = (ar_text or "").strip()
        debug = self._get_debug()

        if kind == "partial":
            out: dict[str, Any] | None = None
            telemetry: dict[str, Any] | None = None
            with self._lock:
                if self.translation is None:
                    return
                if not self.translation.is_current_partial_unlocked(req, self.live_partials):
                    return
                now_ts = time.time()
                partial = self.live_partials.get(speaker)
                if partial is None:
                    return
                prev_ar_revision = int(partial.get("ar_revision", 0) or 0)
                if revision < prev_ar_revision:
                    return
                partial["ar"] = translated
                partial["ar_revision"] = revision
                partial["ts"] = now_ts
                out = {
                    "type": "partial",
                    "speaker": speaker,
                    "speaker_label": partial.get("speaker_label", "Speaker"),
                    "segment_id": segment_id,
                    "revision": int(partial.get("revision", revision) or revision),
                    "en": partial.get("en", ""),
                    "ar": translated,
                }
                if translated:
                    self.ar_live = translated
                self._record_metrics_unlocked(req, now_ts)
                ws_c, st, ru = self._get_telemetry_context() if self._get_telemetry_context else (0, "", False)
                telemetry = self.build_telemetry_unlocked(
                    ws_connections=ws_c, status=st, running=ru
                )
            if out:
                await self._broadcast(out)
                await self._emit_trace_async(out, channel="translation_partial", debug=debug)
            if telemetry:
                await self._broadcast(telemetry)
            return

        # Final patch
        out_final: dict[str, Any] | None = None
        telemetry_final: dict[str, Any] | None = None
        with self._lock:
            now_ts = time.time()
            target_idx = -1
            for idx in range(len(self.finals) - 1, -1, -1):
                item = self.finals[idx]
                if str(item.get("segment_id", "")) != segment_id:
                    continue
                if int(item.get("revision", 0)) != revision:
                    continue
                target_idx = idx
                break
            if target_idx < 0:
                return
            if translated:
                self.finals[target_idx]["ar"] = translated
            out_final = dict(self.finals[target_idx])
            self._record_metrics_unlocked(req, now_ts)
            ws_c, st, ru = self._get_telemetry_context() if self._get_telemetry_context else (0, "", False)
            telemetry_final = self.build_telemetry_unlocked(
                ws_connections=ws_c, status=st, running=ru
            )
        payload = {"type": "final_patch", **out_final}
        await self._broadcast(payload)
        await self._emit_trace_async(payload, channel="translation_final_patch", debug=debug)
        if telemetry_final:
            await self._broadcast(telemetry_final)

    # ── Snapshot helpers ──────────────────────────────────────────────────────

    def snapshot_unlocked(self) -> dict[str, Any]:
        return {
            "en_live": self.en_live,
            "ar_live": self.ar_live,
            "live_partials": list(self.live_partials.values()),
            "finals": list(self.finals),
        }

    def build_telemetry_unlocked(
        self,
        *,
        ws_connections: int,
        status: str,
        running: bool,
    ) -> dict[str, Any]:
        estimated_cost_usd: float | None = None
        if self.translation_cost_per_million_usd is not None:
            estimated_cost_usd = round(
                (self.translation_chars / 1_000_000.0)
                * self.translation_cost_per_million_usd,
                4,
            )
        return {
            "type": "telemetry",
            "ws_connections": ws_connections,
            "recognition_status": status,
            "recognition_running": running,
            "translation_latest_ms": self.translation_latest_ms,
            "translation_p50_ms": self._median_ms_unlocked(),
            "translation_samples": len(self.translation_latency_ms),
            "translation_chars": self.translation_chars,
            "estimated_cost_usd": estimated_cost_usd,
        }
