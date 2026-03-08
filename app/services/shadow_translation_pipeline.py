import asyncio
import os
import threading
import time
from typing import Any, Awaitable, Callable
from urllib.parse import urlsplit, urlunsplit

from app.config import Settings


ApplyShadowTranslationCallback = Callable[[dict[str, Any], dict[str, Any]], Awaitable[None]]
LogCallback = Callable[[str, str], Awaitable[None]]


class ShadowFinalTranslationPipeline:
    def __init__(
        self,
        settings: Settings,
        apply_shadow_result: ApplyShadowTranslationCallback,
        log: LogCallback | None = None,
    ) -> None:
        self._settings = settings
        self._apply_shadow_result = apply_shadow_result
        self._log = log
        self._state_lock = threading.RLock()

        self._generation = 0
        self._queue_seq = 0
        self._loop: asyncio.AbstractEventLoop | None = None
        self._queue: asyncio.Queue[dict[str, Any]] | None = None
        self._worker_task: asyncio.Task[None] | None = None

        self._openai_client: Any = None
        self._last_queue_full_log_ts = 0.0
        self._last_error_log_ts = 0.0

    @property
    def is_configured(self) -> bool:
        return bool(
            self._settings.shadow_final_translation_enabled
            and self._settings.project_endpoint.strip()
            and self.model_name
        )

    @property
    def model_name(self) -> str:
        return (self._settings.shadow_final_translation_model or "").strip()

    @property
    def provider_name(self) -> str:
        return "azure_openai_shadow"

    def reset_unlocked(self) -> None:
        with self._state_lock:
            self._generation += 1

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._queue = asyncio.Queue(maxsize=120)
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
        self._close_clients()

    def build_request(
        self,
        *,
        speaker: str,
        segment_id: str,
        revision: int,
        text: str,
        trigger_ts: float,
        debug: bool = False,
    ) -> dict[str, Any] | None:
        content = (text or "").strip()
        if not self.is_configured or not content:
            return None
        return {
            "kind": "final_shadow",
            "speaker": str(speaker or "default"),
            "segment_id": str(segment_id or ""),
            "revision": int(revision or 0),
            "generation": self._generation,
            "text": content,
            "trigger_ts": float(trigger_ts or time.time()),
            "debug": bool(debug),
            "provider": self.provider_name,
            "model": self.model_name,
        }

    async def _enqueue(self, req: dict[str, Any]) -> None:
        queue = self._queue
        if queue is None or not self.is_configured:
            return
        if queue.full():
            await self._log_throttled(
                "warning",
                "Shadow final translation queue is full; dropping request.",
                bucket="queue_full",
            )
            return
        with self._state_lock:
            self._queue_seq += 1
            seq = self._queue_seq
        req["queue_seq"] = seq
        req["enqueue_ts"] = time.time()
        if bool(req.get("debug", False)) and self._log:
            await self._log(
                "debug",
                (
                    "Shadow translation enqueued: "
                    f"seq={seq}, segment_id={req.get('segment_id', '')}, "
                    f"revision={req.get('revision', 0)}, model={req.get('model', '')}"
                ),
            )
        try:
            queue.put_nowait(req)
        except asyncio.QueueFull:
            await self._log_throttled(
                "warning",
                "Shadow final translation queue is full; dropping request.",
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
            req = await queue.get()
            try:
                req_generation = int(req.get("generation", -1) or -1)
                with self._state_lock:
                    current_generation = self._generation
                if req_generation != current_generation:
                    continue

                debug = bool(req.get("debug", False))
                enqueue_ts = float(req.get("enqueue_ts", 0.0) or 0.0)
                trigger_ts = float(req.get("trigger_ts", 0.0) or 0.0)
                queue_wait_ms = int((time.time() - enqueue_ts) * 1000) if enqueue_ts else -1
                if debug and self._log:
                    await self._log(
                        "debug",
                        (
                            "Shadow translation start: "
                            f"seq={req.get('queue_seq', 0)}, "
                            f"segment_id={req.get('segment_id', '')}, "
                            f"queue_wait_ms={queue_wait_ms}, "
                            f"since_trigger_ms={int((time.time() - trigger_ts) * 1000) if trigger_ts else -1}, "
                            f"text_len={len(str(req.get('text', '') or ''))}"
                        ),
                    )

                translate_start = time.time()
                translated, error = await asyncio.to_thread(
                    self._translate_text_sync,
                    str(req.get("text", "") or ""),
                )
                latency_ms = int((time.time() - translate_start) * 1000)
                if not translated and not error:
                    error = "Empty translation response."
                if error:
                    await self._log_throttled(
                        "warning",
                        f"Shadow final translation failed: {error}",
                        bucket="translate_error",
                    )
                result = {
                    "provider": str(req.get("provider", self.provider_name) or self.provider_name),
                    "model": str(req.get("model", self.model_name) or self.model_name),
                    "status": "completed" if translated and not error else "failed",
                    "text": translated,
                    "latency_ms": latency_ms,
                    "error": error,
                }
                if debug and self._log:
                    await self._log(
                        "debug",
                        (
                            "Shadow translation done: "
                            f"seq={req.get('queue_seq', 0)}, "
                            f"segment_id={req.get('segment_id', '')}, "
                            f"latency_ms={latency_ms}, "
                            f"translated_len={len(translated or '')}"
                        ),
                    )
                await self._apply_shadow_result(req, result)
            finally:
                queue.task_done()

    def _ensure_client(self) -> Any:
        with self._state_lock:
            if self._openai_client is not None:
                return self._openai_client
            try:
                from openai import AzureOpenAI
            except Exception as ex:
                raise RuntimeError(
                    "Missing shadow translation dependencies. Install the openai package."
                ) from ex
            api_key = (self._settings.ai_services_key or "").strip()
            if not api_key:
                raise RuntimeError(
                    "Shadow translation requires AZURE_AI_SERVICES_KEY."
                )
            api_version = (self._settings.openai_api_version or "").strip() or "2024-10-21"
            resource_endpoint = self._derive_resource_endpoint(self._settings.project_endpoint)
            self._openai_client = AzureOpenAI(
                azure_endpoint=resource_endpoint,
                api_key=api_key,
                api_version=api_version,
            )
            return self._openai_client

    @staticmethod
    def _derive_resource_endpoint(project_endpoint: str) -> str:
        raw = (project_endpoint or "").strip()
        if not raw:
            raise RuntimeError("Shadow translation requires PROJECT_ENDPOINT.")
        marker = "/api/projects/"
        if marker in raw:
            return raw.split(marker, 1)[0].rstrip("/")
        parts = urlsplit(raw)
        if not parts.scheme or not parts.netloc:
            raise RuntimeError(
                "PROJECT_ENDPOINT is not a valid Azure AI project endpoint."
            )
        return urlunsplit((parts.scheme, parts.netloc, "", "", "")).rstrip("/")

    def _translate_text_sync(self, text: str) -> tuple[str, str | None]:
        content = (text or "").strip()
        if not content:
            return "", None
        try:
            client = self._ensure_client()
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Translate English meeting transcript text into natural professional Arabic. "
                            "Return Arabic only. Preserve names, brands, dates, numbers, and business terms. "
                            "Do not add commentary, bullets, or quotation marks."
                        ),
                    },
                    {"role": "user", "content": content},
                ],
                temperature=0,
                max_completion_tokens=max(120, min(600, len(content.split()) * 8)),
            )
            choices = getattr(response, "choices", None) or []
            if not choices:
                return "", "No completion choices returned."
            message = getattr(choices[0], "message", None)
            translated = getattr(message, "content", None) or ""
            return str(translated).strip(), None
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
            if now - self._last_error_log_ts < min_interval_sec:
                return
            self._last_error_log_ts = now
        await self._log(level, message)

    def _close_clients(self) -> None:
        with self._state_lock:
            openai_client = self._openai_client
            self._openai_client = None

        if openai_client is not None:
            close_fn = getattr(openai_client, "close", None)
            if callable(close_fn):
                try:
                    close_fn()
                except Exception:
                    pass
