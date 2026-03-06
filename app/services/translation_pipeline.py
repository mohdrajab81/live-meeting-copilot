import asyncio
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any, Awaitable, Callable

from app.config import RuntimeConfig, Settings


ApplyTranslationCallback = Callable[[dict[str, Any], str], Awaitable[None]]
LogCallback = Callable[[str, str], Awaitable[None]]
_TRANSLATOR_ENDPOINT = "https://api.cognitive.microsofttranslator.com"


class TranslationPipeline:
    def __init__(
        self,
        settings: Settings,
        apply_translation_result: ApplyTranslationCallback,
        log: LogCallback | None = None,
    ) -> None:
        self._settings = settings
        self._state_lock = threading.RLock()
        self._apply_translation_result = apply_translation_result
        self._log = log

        self.partial_translate_last_emit_ts: dict[str, float] = {}
        self.active_segments: dict[str, dict[str, Any]] = {}
        self.partial_inflight: dict[str, bool] = {}
        self.partial_backlog: dict[str, dict[str, Any]] = {}
        self.segment_seq = 0
        self.translate_seq = 0
        self._generation = 0
        self._last_queue_full_log_ts = 0.0
        self._last_translate_error_log_ts = 0.0

        self._loop: asyncio.AbstractEventLoop | None = None
        self._queue: asyncio.PriorityQueue[tuple[int, int, dict[str, Any]]] | None = None
        self._worker_task: asyncio.Task[None] | None = None

    def reset_unlocked(self) -> None:
        with self._state_lock:
            self._generation += 1
            self.partial_translate_last_emit_ts = {}
            self.active_segments = {}
            self.partial_inflight = {}
            self.partial_backlog = {}

    def discard_speaker_live_unlocked(self, speaker: str) -> None:
        """Drop live translation state for a single speaker.

        Used when a speaker's partial stream is explicitly suppressed/cleared so
        stale in-flight/backlog translation callbacks cannot patch UI state.
        """
        key = str(speaker or "default")
        with self._state_lock:
            self.partial_translate_last_emit_ts.pop(key, None)
            self.active_segments.pop(key, None)
            self.partial_backlog.pop(key, None)
            self.partial_inflight.pop(key, None)

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._queue = asyncio.PriorityQueue(maxsize=200)
        self._worker_task = asyncio.create_task(self._worker_loop())

    async def stop(self) -> None:
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        self._worker_task = None
        self._queue = None

    def _translator_headers(self) -> dict[str, str]:
        key = (self._settings.ai_services_key or "").strip()
        region = (self._settings.ai_services_region or "").strip()
        headers = {
            "Content-Type": "application/json",
            "X-ClientTraceId": str(uuid.uuid4()),
        }
        if key:
            headers["Ocp-Apim-Subscription-Key"] = key
        if region:
            headers["Ocp-Apim-Subscription-Region"] = region
        return headers

    def _translate_text_sync(self, text: str) -> tuple[str, str | None]:
        content = (text or "").strip()
        if not content:
            return "", None
        endpoint = _TRANSLATOR_ENDPOINT
        query = urllib.parse.urlencode(
            {"api-version": "3.0", "from": "en", "to": "ar"},
        )
        url = f"{endpoint}/translate?{query}"
        body = json.dumps([{"text": content}], ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url=url,
            data=body,
            headers=self._translator_headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
                translated = (
                    payload[0].get("translations", [{}])[0].get("text", "")
                    if payload
                    else ""
                )
                return translated, None
        except urllib.error.HTTPError as ex:
            detail = ""
            try:
                detail = ex.read().decode("utf-8", errors="replace").strip()
            except Exception:
                detail = ""
            message = f"HTTP {ex.code} ({ex.reason})"
            if detail:
                message = f"{message}: {detail[:200]}"
            return "", message
        except Exception as ex:
            return "", f"{type(ex).__name__}: {ex}"

    async def _log_throttled(
        self,
        level: str,
        message: str,
        *,
        bucket: str,
        min_interval_sec: float = 5.0,
    ) -> None:
        if not self._log:
            return
        now = time.time()
        if bucket == "queue_full":
            if now - self._last_queue_full_log_ts < min_interval_sec:
                return
            self._last_queue_full_log_ts = now
        elif bucket == "translate_error":
            if now - self._last_translate_error_log_ts < min_interval_sec:
                return
            self._last_translate_error_log_ts = now
        await self._log(level, message)

    async def _enqueue(self, req: dict[str, Any]) -> None:
        queue = self._queue
        if queue is None:
            return
        kind = str(req.get("kind", "partial") or "partial")
        speaker = str(req.get("speaker", "default") or "default")
        debug = bool(req.get("debug", False))

        if kind == "partial":
            backlog_replaced = False
            with self._state_lock:
                if self.partial_inflight.get(speaker, False):
                    self.partial_backlog[speaker] = req
                    backlog_replaced = True
                else:
                    self.partial_inflight[speaker] = True
            if backlog_replaced:
                if debug and self._log:
                    await self._log(
                        "debug",
                        (
                            "Translation perf backlog replaced: "
                            f"kind={kind}, speaker={speaker}, "
                            f"segment_id={req.get('segment_id', '')}, "
                            f"revision={req.get('revision', 0)}"
                        ),
                    )
                return
            if queue.full():
                with self._state_lock:
                    self.partial_inflight[speaker] = False
                await self._log_throttled(
                    "warning",
                    f"Translation queue is full; dropping partial for speaker '{speaker}'.",
                    bucket="queue_full",
                )
                return

        with self._state_lock:
            self.translate_seq += 1
            seq = self.translate_seq
        req["queue_seq"] = seq
        req["enqueue_ts"] = time.time()
        priority = 0 if kind == "final" else 1
        if debug and self._log:
            await self._log(
                "debug",
                (
                    "Translation perf enqueued: "
                    f"seq={seq}, kind={kind}, speaker={speaker}, "
                    f"segment_id={req.get('segment_id', '')}, "
                    f"revision={req.get('revision', 0)}, "
                    f"qsize_before={queue.qsize()}"
                ),
            )
        try:
            queue.put_nowait((priority, seq, req))
        except asyncio.QueueFull:
            if kind == "partial":
                with self._state_lock:
                    self.partial_inflight[speaker] = False
                await self._log_throttled(
                    "warning",
                    f"Translation queue is full; dropping partial for speaker '{speaker}'.",
                    bucket="queue_full",
                )
                return
            await self._log_throttled(
                "warning",
                "Translation queue is full; dropping final translation request.",
                bucket="queue_full",
            )

    def enqueue_from_thread(self, req: dict[str, Any]) -> None:
        loop = self._loop
        if not loop or not loop.is_running():
            return
        asyncio.run_coroutine_threadsafe(self._enqueue(req), loop)

    async def _worker_loop(self) -> None:
        queue = self._queue
        if queue is None:
            return
        while True:
            _priority, _seq, req = await queue.get()
            try:
                req_generation = int(req.get("generation", -1) or -1)
                with self._state_lock:
                    current_generation = self._generation
                if req_generation != current_generation:
                    continue
                debug = bool(req.get("debug", False))
                kind = str(req.get("kind", "partial") or "partial")
                speaker = str(req.get("speaker", "default") or "default")
                queue_seq = int(req.get("queue_seq", 0) or 0)
                enqueue_ts = float(req.get("enqueue_ts", 0.0) or 0.0)
                trigger_ts = float(req.get("trigger_ts", 0.0) or 0.0)
                now = time.time()
                queue_wait_ms = int((now - enqueue_ts) * 1000) if enqueue_ts else -1
                end_to_end_wait_ms = int((now - trigger_ts) * 1000) if trigger_ts else -1
                if debug and self._log:
                    await self._log(
                        "debug",
                        (
                            "Translation perf start: "
                            f"seq={queue_seq}, kind={kind}, speaker={speaker}, "
                            f"queue_wait_ms={queue_wait_ms}, "
                            f"since_trigger_ms={end_to_end_wait_ms}, "
                            f"text_len={len(str(req.get('text', '') or ''))}"
                        ),
                    )
                text = str(req.get("text", "") or "")
                translate_start = time.time()
                translated, error = await asyncio.to_thread(self._translate_text_sync, text)
                translate_ms = int((time.time() - translate_start) * 1000)
                if error:
                    await self._log_throttled(
                        "warning",
                        f"Translation {kind} failed: {error}",
                        bucket="translate_error",
                    )
                if debug and self._log:
                    total_from_trigger_ms = (
                        int((time.time() - trigger_ts) * 1000) if trigger_ts else -1
                    )
                    await self._log(
                        "debug",
                        (
                            "Translation perf done: "
                            f"seq={queue_seq}, kind={kind}, speaker={speaker}, "
                            f"translate_ms={translate_ms}, "
                            f"total_from_trigger_ms={total_from_trigger_ms}, "
                            f"translated_len={len(translated or '')}"
                        ),
                    )
                await self._apply_translation_result(req, translated)
            finally:
                kind = str(req.get("kind", "partial") or "partial")
                speaker = str(req.get("speaker", "default") or "default")
                queue.task_done()
                if kind == "partial":
                    backlog: dict[str, Any] | None = None
                    with self._state_lock:
                        self.partial_inflight[speaker] = False
                        backlog = self.partial_backlog.pop(speaker, None)
                    if backlog:
                        if bool(backlog.get("debug", False)) and self._log:
                            await self._log(
                                "debug",
                                (
                                    "Translation perf backlog dispatch: "
                                    f"speaker={speaker}, "
                                    f"segment_id={backlog.get('segment_id', '')}, "
                                    f"revision={backlog.get('revision', 0)}"
                                ),
                            )
                        await self._enqueue(backlog)

    def prepare_partial_unlocked(
        self,
        *,
        speaker: str,
        speaker_label: str,
        en: str,
        prev_ar: str,
        now_ts: float,
        cfg: RuntimeConfig,
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        with self._state_lock:
            seg = self.active_segments.get(speaker)
            if not seg:
                self.segment_seq += 1
                seg = {
                    "segment_id": f"{speaker}-{int(time.time())}-{self.segment_seq}",
                    "revision": 0,
                    "start_ts": now_ts,
                }
                self.active_segments[speaker] = seg
            else:
                try:
                    prev_start = float(seg.get("start_ts", now_ts) or now_ts)
                except Exception:
                    prev_start = now_ts
                seg["start_ts"] = min(prev_start, now_ts)
            seg["revision"] = int(seg.get("revision", 0)) + 1
            segment_id = str(seg.get("segment_id", ""))
            revision = int(seg.get("revision", 0))

            out = {
                "type": "partial",
                "speaker": speaker,
                "speaker_label": speaker_label,
                "segment_id": segment_id,
                "revision": revision,
                "en": en,
                "ar": prev_ar,
                "ts": now_ts,
            }

            req: dict[str, Any] | None = None
            throttle_sec = float(cfg.partial_translate_min_interval_sec)
            elapsed = now_ts - self.partial_translate_last_emit_ts.get(speaker, 0.0)
            # Send first partial for this segment immediately; throttle only follow-up updates.
            should_emit_now = not str(prev_ar or "").strip() or (elapsed >= throttle_sec)
            if should_emit_now:
                self.partial_translate_last_emit_ts[speaker] = now_ts
                req = {
                    "kind": "partial",
                    "speaker": speaker,
                    "segment_id": segment_id,
                    "revision": revision,
                    "generation": self._generation,
                    "text": en,
                    "trigger_ts": now_ts,
                    "debug": bool(cfg.debug),
                }
            return out, req

    def prepare_final_unlocked(
        self,
        *,
        speaker: str,
        speaker_label: str,
        en: str,
        ts: float,
        debug: bool = False,
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        with self._state_lock:
            seg = self.active_segments.pop(speaker, None)
            if seg:
                segment_id = str(seg.get("segment_id", ""))
                revision = int(seg.get("revision", 0)) + 1
                try:
                    start_ts = float(seg.get("start_ts", ts) or ts)
                except Exception:
                    start_ts = float(ts)
            else:
                self.segment_seq += 1
                segment_id = f"{speaker}-{int(time.time())}-{self.segment_seq}"
                revision = 1
                start_ts = float(ts)

            self.partial_translate_last_emit_ts.pop(speaker, None)
            item = {
                "type": "final",
                "speaker": speaker,
                "speaker_label": speaker_label,
                "segment_id": segment_id,
                "revision": revision,
                "en": en,
                "ar": "",
                "ts": ts,
                "start_ts": start_ts,
            }
            req = (
                {
                    "kind": "final",
                    "speaker": speaker,
                    "segment_id": segment_id,
                    "revision": revision,
                    "generation": self._generation,
                    "text": en,
                    "trigger_ts": ts,
                    "debug": bool(debug),
                }
                if en
                else None
            )
            return item, req

    def is_current_partial_unlocked(
        self,
        req: dict[str, Any],
        live_partials: dict[str, dict[str, Any]],
    ) -> bool:
        with self._state_lock:
            speaker = str(req.get("speaker", "default") or "default")
            segment_id = str(req.get("segment_id", "") or "")
            revision = int(req.get("revision", 0) or 0)

            seg = self.active_segments.get(speaker)
            if not seg:
                return False
            if str(seg.get("segment_id", "")) != segment_id:
                return False
            if int(seg.get("revision", 0)) < revision:
                return False

            partial = live_partials.get(speaker)
            if not partial:
                return False
            if str(partial.get("segment_id", "")) != segment_id:
                return False
            if int(partial.get("revision", 0)) < revision:
                return False
            return True
