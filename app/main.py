import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
import threading
import time
from typing import Any

from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from app.api.routes import router as api_router
from app.api.websocket import websocket_endpoint
from app.config import RuntimeConfig, Settings
from app.services.coach import CoachService
from app.services.speech import SpeechService

load_dotenv()


class AppController:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.settings_path = Path("web_translator_settings.json")
        self.lock = threading.RLock()
        self.loop: asyncio.AbstractEventLoop | None = None
        self.connections: set[WebSocket] = set()

        self.config = RuntimeConfig()
        self.status = "idle"
        self.running = False
        self.en_live = ""
        self.ar_live = ""
        self.live_partials: dict[str, dict[str, Any]] = {}
        self.finals: list[dict[str, Any]] = []
        self.logs: list[dict[str, Any]] = []
        self.session_started_ts = time.time()
        self.record_started_ts: float | None = None
        self.record_accumulated_ms = 0
        self.coach = CoachService.from_environment()
        self.coach_hints: list[dict[str, Any]] = []
        self.coach_pending = False
        self.coach_last_run_ts = 0.0
        self.coach_group_seq = 0
        self.coach_last_sent_final_idx = 0
        self.coach_queued_trigger: dict[str, Any] | None = None

        self.speech = SpeechService(
            settings=settings,
            on_event=self.handle_speech_event,
            get_runtime_config=self.get_runtime_config,
        )

    def _record_total_ms_unlocked(self) -> int:
        total_ms = self.record_accumulated_ms
        if self.record_started_ts is not None:
            total_ms += int((time.time() - self.record_started_ts) * 1000)
        return int(total_ms)

    def get_runtime_config(self) -> RuntimeConfig:
        with self.lock:
            return RuntimeConfig.model_validate(self.config.model_dump())

    def get_config(self) -> dict[str, Any]:
        with self.lock:
            return self.config.model_dump()

    def set_config(self, config: RuntimeConfig) -> None:
        with self.lock:
            self.config = config

    def save_config_to_disk(self) -> str:
        with self.lock:
            config = self.config.model_dump()
        self.settings_path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return self.settings_path.name

    def reload_config_from_disk(self) -> dict[str, Any]:
        if not self.settings_path.exists():
            raise FileNotFoundError(
                f"Settings file not found: {self.settings_path.name}. Save config first."
            )
        raw = json.loads(self.settings_path.read_text(encoding="utf-8"))
        cfg = RuntimeConfig.model_validate(raw)
        with self.lock:
            self.config = cfg
        return cfg.model_dump()

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "type": "snapshot",
                "status": self.status,
                "running": self.running,
                "session_started_ts": self.session_started_ts,
                "config": self.config.model_dump(),
                "en_live": self.en_live,
                "ar_live": self.ar_live,
                "live_partials": list(self.live_partials.values()),
                "finals": list(self.finals),
                "logs": list(self.logs),
                "recording": {
                    "started_ts": self.record_started_ts,
                    "accumulated_ms": self.record_accumulated_ms,
                    "total_ms": self._record_total_ms_unlocked(),
                },
                "coach": {
                    "configured": self.coach.is_configured,
                    "pending": self.coach_pending,
                    "queued": self.coach_queued_trigger is not None,
                    "last_sent_final_idx": self.coach_last_sent_final_idx,
                    "hints": list(self.coach_hints),
                },
            }

    def _append_log(self, level: str, message: str) -> dict[str, Any]:
        item = {
            "type": "log",
            "level": level,
            "message": message,
            "ts": time.time(),
        }
        with self.lock:
            self.logs.append(item)
            if len(self.logs) > 1000:
                self.logs = self.logs[-1000:]
        return item

    async def broadcast(self, payload: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        data = json.dumps(payload, ensure_ascii=False)
        for ws in list(self.connections):
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.connections.discard(ws)

    async def broadcast_log(self, level: str, message: str) -> None:
        await self.broadcast(self._append_log(level, message))

    def _broadcast_from_thread(self, payload: dict[str, Any]) -> None:
        loop = self.loop
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast(payload), loop)

    def _should_trigger_coach_unlocked(
        self,
        item: dict[str, Any],
        *,
        ignore_busy: bool = False,
        ignore_cooldown: bool = False,
    ) -> bool:
        if not self.config.coach_enabled:
            return False
        if not self.coach.is_configured:
            return False
        if (not ignore_busy) and self.coach_pending:
            return False
        if not ignore_cooldown:
            now = time.time()
            if now - self.coach_last_run_ts < float(self.config.coach_cooldown_sec):
                return False

        trigger = self.config.coach_trigger_speaker
        speaker = str(item.get("speaker", "default") or "default")
        if trigger == "any":
            return True
        return trigger == speaker

    def _has_text_unlocked(self, item: dict[str, Any]) -> bool:
        text = (
            str(item.get("en", "") or "").strip()
            or str(item.get("ar", "") or "").strip()
        )
        return bool(text)

    def _build_coach_prompt_unlocked(
        self,
        trigger_item: dict[str, Any],
        delta_turns: list[dict[str, Any]],
        *,
        session_start: bool,
    ) -> str:
        delta_lines: list[str] = []
        for turn in delta_turns:
            label = str(turn.get("speaker_label", "Speaker") or "Speaker")
            en = str(turn.get("en", "") or "").strip()
            ar = str(turn.get("ar", "") or "").strip()
            text = en or ar
            if not text:
                continue
            ts = time.strftime("%H:%M:%S", time.localtime(float(turn.get("ts") or time.time())))
            delta_lines.append(f"[{ts}] {label}: {text}")

        trigger_label = str(trigger_item.get("speaker_label", "Speaker") or "Speaker")
        trigger_en = (
            str(trigger_item.get("en", "") or "").strip()
            or str(trigger_item.get("ar", "") or "").strip()
        )
        instruction = str(self.config.coach_instruction or "").strip()
        if not instruction:
            instruction = (
                "Give a short suggested reply for me, tailored to my profile. "
                "Use concise bullets and keep claims truthful to known background."
            )
        if session_start:
            return "\n".join(
                [
                    "You are my live interview copilot.",
                    "Use my stored profile knowledge from the connected agent tools.",
                    instruction,
                    "",
                    "Latest interviewer utterance:",
                    f"{trigger_label}: {trigger_en}",
                    "",
                    "Session transcript update:",
                    "This is the full transcript from session start.",
                    "\n".join(delta_lines) if delta_lines else "(no new turns)",
                    "",
                    "Return format:",
                    "1) Suggested reply (short)",
                    "2) Exactly 2 bullet proof points from my background",
                    "3) One follow-up question I can ask (optional)",
                ]
            )

        return "\n".join(
            [
                "Latest interviewer utterance:",
                f"{trigger_label}: {trigger_en}",
                "",
                "Session transcript update:",
                "This is only the new transcript delta since last update.",
                "\n".join(delta_lines) if delta_lines else "(no new turns)",
            ]
        )

    def _next_coach_group_id_unlocked(self) -> str:
        self.coach_group_seq += 1
        return f"coach-{int(time.time())}-{self.coach_group_seq}"

    def _prepare_coach_call_unlocked(
        self,
        trigger_item: dict[str, Any],
        *,
        ignore_cooldown: bool = False,
    ) -> tuple[str, str, float, int] | None:
        if not self._has_text_unlocked(trigger_item):
            return None
        if not self._should_trigger_coach_unlocked(
            trigger_item,
            ignore_busy=False,
            ignore_cooldown=ignore_cooldown,
        ):
            return None

        end_idx = len(self.finals)
        start_idx = int(self.coach_last_sent_final_idx)
        if start_idx < 0:
            start_idx = 0
        if start_idx > end_idx:
            start_idx = end_idx
        delta_turns = self.finals[start_idx:end_idx]
        if not delta_turns:
            return None

        session_start = start_idx == 0
        coach_prompt = self._build_coach_prompt_unlocked(
            trigger_item,
            delta_turns,
            session_start=session_start,
        )

        self.coach_pending = True
        self.coach_last_run_ts = time.time()
        coach_group_id = self._next_coach_group_id_unlocked()
        return coach_prompt, coach_group_id, self.coach_last_run_ts, end_idx

    async def _run_coach(
        self,
        prompt: str,
        trigger_item: dict[str, Any],
        group_id: str,
        trigger_ts: float,
        inflight_end_idx: int,
    ) -> None:
        try:
            run_start = time.time()
            send_ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(run_start))
            chain = self.coach.get_chain_state()
            await self.broadcast_log(
                "info",
                (
                    "Coach deep send: "
                    f"group={group_id}, send_ts={send_ts}, "
                    f"trigger={trigger_item.get('speaker_label', 'Speaker')}, "
                    f"trigger_text={str(trigger_item.get('en', '') or '').strip()}, "
                    f"req_conversation_id={chain.get('conversation_id') or '-'}, "
                    f"req_previous_response_id={chain.get('previous_response_id') or '-'}"
                ),
            )
            result = await asyncio.to_thread(self.coach.ask, prompt)
            hint = {
                "type": "coach",
                "hint_kind": "deep",
                "group_id": group_id,
                "ts": time.time(),
                "speaker": str(trigger_item.get("speaker", "default") or "default"),
                "speaker_label": str(
                    trigger_item.get("speaker_label", "Speaker") or "Speaker"
                ),
                "trigger_en": str(trigger_item.get("en", "") or ""),
                "suggestion": result.text,
            }
            with self.lock:
                self.coach_hints.append(hint)
                if len(self.coach_hints) > 120:
                    self.coach_hints = self.coach_hints[-120:]
            await self.broadcast(hint)
            recv_ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
            await self.broadcast_log(
                "info",
                (
                    "Coach deep reply: "
                    f"group={group_id}, recv_ts={recv_ts}, "
                    f"response_id={result.response_id or '-'}, "
                    f"conversation_id={result.conversation_id or '-'}, "
                    f"reply_text={result.text}"
                ),
            )
            queue_ms = int((run_start - trigger_ts) * 1000)
            end_to_end_ms = int((time.time() - trigger_ts) * 1000)
            await self.broadcast_log(
                "info",
                (
                    "Coach deep hint trace: "
                    f"group={group_id}, queue_ms={queue_ms}, "
                    f"create_ms={result.create_ms}, approve_ms={result.approve_ms}, "
                    f"approval_rounds={result.approval_rounds}, approval_count={result.approval_count}, "
                    f"total_ms={result.total_ms}, end_to_end_ms={end_to_end_ms}"
                ),
            )
            with self.lock:
                if inflight_end_idx > self.coach_last_sent_final_idx:
                    self.coach_last_sent_final_idx = inflight_end_idx
        except Exception as ex:
            await self.broadcast_log("error", f"Coach request failed: {ex}")
        finally:
            queued: dict[str, Any] | None = None
            next_call: tuple[str, str, float, int] | None = None
            with self.lock:
                self.coach_pending = False
                queued = self.coach_queued_trigger
                self.coach_queued_trigger = None
                if queued:
                    next_call = self._prepare_coach_call_unlocked(
                        queued,
                        ignore_cooldown=True,
                    )

            if queued and not next_call:
                await self.broadcast_log(
                    "debug",
                    "Queued coach trigger dropped (not eligible by current settings).",
                )

            if next_call:
                next_prompt, next_group_id, next_trigger_ts, next_end_idx = next_call
                await self.broadcast_log(
                    "info",
                    (
                        "Coach queued trigger resumed: "
                        f"group={next_group_id}, trigger={queued.get('speaker_label', 'Speaker')}, "
                        f"trigger_text={str(queued.get('en', '') or '').strip()}"
                    ),
                )
                await self._run_coach(
                    next_prompt,
                    queued or {},
                    next_group_id,
                    next_trigger_ts,
                    next_end_idx,
                )

    def handle_speech_event(self, payload: dict[str, Any]) -> None:
        kind = payload.get("type")
        if kind == "status":
            with self.lock:
                was_running = self.running
                self.status = str(payload.get("status", self.status))
                now_running = bool(payload.get("running", False))
                self.running = now_running
                now_ts = time.time()
                if now_running and not was_running and self.record_started_ts is None:
                    self.record_started_ts = now_ts
                if not now_running and was_running and self.record_started_ts is not None:
                    self.record_accumulated_ms += int(
                        (now_ts - self.record_started_ts) * 1000
                    )
                    self.record_started_ts = None
                recording = {
                    "started_ts": self.record_started_ts,
                    "accumulated_ms": self.record_accumulated_ms,
                    "total_ms": self._record_total_ms_unlocked(),
                }
            self._broadcast_from_thread(
                {
                    "type": "status",
                    "status": self.status,
                    "running": self.running,
                    "recording": recording,
                }
            )
            return

        if kind == "partial":
            with self.lock:
                en = str(payload.get("en", "") or "")
                ar = str(payload.get("ar", "") or "")
                speaker = str(payload.get("speaker", "default") or "default")
                speaker_label = str(payload.get("speaker_label", "Speaker") or "Speaker")
                prev = self.live_partials.get(speaker, {})
                merged_en = en or str(prev.get("en", "") or "")
                merged_ar = ar or str(prev.get("ar", "") or "")
                if en:
                    self.en_live = en
                if ar:
                    self.ar_live = ar
                self.live_partials[speaker] = {
                    "speaker": speaker,
                    "speaker_label": speaker_label,
                    "en": merged_en,
                    "ar": merged_ar,
                    "ts": time.time(),
                }
                out = {
                    "type": "partial",
                    "speaker": speaker,
                    "speaker_label": speaker_label,
                    "en": merged_en,
                    "ar": merged_ar,
                }
            self._broadcast_from_thread(out)
            return

        if kind == "final":
            trigger_coach = False
            coach_call: tuple[str, str, float, int] | None = None
            queued_while_busy = False
            item = {
                "type": "final",
                "en": str(payload.get("en", "") or ""),
                "ar": str(payload.get("ar", "") or ""),
                "speaker": str(payload.get("speaker", "default") or "default"),
                "speaker_label": str(payload.get("speaker_label", "Speaker") or "Speaker"),
                "ts": payload.get("ts") or time.time(),
            }
            with self.lock:
                self.finals.append(
                    {
                        "en": item["en"],
                        "ar": item["ar"],
                        "speaker": item["speaker"],
                        "speaker_label": item["speaker_label"],
                        "ts": item["ts"],
                    }
                )
                if len(self.finals) > self.config.max_finals:
                    self.finals = self.finals[-self.config.max_finals :]
                self.en_live = ""
                self.ar_live = ""
                self.live_partials.pop(item["speaker"], None)
                is_candidate = self._should_trigger_coach_unlocked(
                    item,
                    ignore_busy=True,
                )
                if is_candidate:
                    if self.coach_pending:
                        self.coach_queued_trigger = dict(item)
                        queued_while_busy = True
                    else:
                        coach_call = self._prepare_coach_call_unlocked(item)
                        trigger_coach = coach_call is not None
            self._broadcast_from_thread(item)
            if queued_while_busy:
                self._broadcast_from_thread(
                    self._append_log(
                        "debug",
                        (
                            "Coach trigger queued while busy: "
                            f"trigger={item['speaker_label']}, text={item['en']}"
                        ),
                    )
                )
            if trigger_coach and coach_call:
                coach_prompt, coach_group_id, coach_trigger_ts, inflight_end_idx = coach_call
                loop = self.loop
                if loop and loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        self._run_coach(
                            coach_prompt,
                            item,
                            coach_group_id,
                            coach_trigger_ts,
                            inflight_end_idx,
                        ),
                        loop,
                    )
            return

        if kind == "log":
            item = self._append_log(
                str(payload.get("level", "info")),
                str(payload.get("message", "")),
            )
            self._broadcast_from_thread(item)

    def start(self) -> bool:
        if self.config.coach_enabled and not self.coach.supports_conversations_create():
            self._broadcast_from_thread(
                self._append_log(
                    "error",
                    (
                        "Start blocked: coach requires conversations.create() support, "
                        "but current client/runtime does not provide it."
                    ),
                )
            )
            return False

        session_conversation_id: str | None = None
        if self.config.coach_enabled:
            try:
                session_conversation_id = self.coach.ensure_session()
            except Exception as ex:
                self._broadcast_from_thread(
                    self._append_log(
                        "error",
                        f"Start blocked: failed to initialize coach session via conversations.create(): {ex}",
                    )
                )
                return False

        started = self.speech.start_recognition()
        if not started:
            return False
        with self.lock:
            self.session_started_ts = time.time()
            self.coach_pending = False
            self.coach_last_run_ts = 0.0
            self.coach_last_sent_final_idx = len(self.finals)
            self.coach_queued_trigger = None
        if self.config.coach_enabled:
            self._broadcast_from_thread(
                self._append_log(
                    "info",
                    f"Coach session active: conversation_id={session_conversation_id or '-'}",
                )
            )
        return True

    def stop(self) -> bool:
        stopped = self.speech.stop_recognition()
        if not stopped:
            return False
        with self.lock:
            self.coach_pending = False
            self.coach_last_run_ts = 0.0
            self.coach_queued_trigger = None
        self.coach.clear_conversation()
        return True

    def clear_logs(self) -> None:
        with self.lock:
            self.logs = []

    def clear_transcript(self) -> None:
        with self.lock:
            self.finals = []
            self.en_live = ""
            self.ar_live = ""
            self.live_partials = {}
            self.coach_last_sent_final_idx = 0
            self.coach_queued_trigger = None
        self.coach.clear_conversation()

    def clear_coach(self) -> None:
        with self.lock:
            self.coach_hints = []
            self.coach_pending = False
            self.coach_last_run_ts = 0.0
            self.coach_last_sent_final_idx = len(self.finals)
            self.coach_queued_trigger = None
        self.coach.clear_conversation()

    async def request_coach(self, prompt: str, speaker_label: str = "Manual") -> dict[str, Any]:
        manual_prompt = "\n".join(
            [
                "Manual user message (same conversation):",
                str(prompt or "").strip(),
            ]
        )
        send_ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        chain = self.coach.get_chain_state()
        await self.broadcast_log(
            "info",
            (
                "Coach manual send: "
                f"send_ts={send_ts}, speaker_label={speaker_label}, "
                f"req_conversation_id={chain.get('conversation_id') or '-'}, "
                f"req_previous_response_id={chain.get('previous_response_id') or '-'}, "
                f"prompt={prompt}"
            ),
        )
        result = await asyncio.to_thread(self.coach.ask, manual_prompt)
        hint = {
            "type": "coach",
            "hint_kind": "manual",
            "group_id": "",
            "ts": time.time(),
            "speaker": "manual",
            "speaker_label": speaker_label or "Manual",
            "trigger_en": "",
            "suggestion": result.text,
        }
        with self.lock:
            self.coach_hints.append(hint)
            if len(self.coach_hints) > 120:
                self.coach_hints = self.coach_hints[-120:]
        await self.broadcast(hint)
        recv_ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        await self.broadcast_log(
            "info",
            (
                "Coach manual reply: "
                f"recv_ts={recv_ts}, total_ms={result.total_ms}, "
                f"create_ms={result.create_ms}, approve_ms={result.approve_ms}, "
                f"approval_rounds={result.approval_rounds}, approval_count={result.approval_count}, "
                f"response_id={result.response_id or '-'}, conversation_id={result.conversation_id or '-'}, "
                f"reply_text={result.text}"
            ),
        )
        return hint

    async def connect_websocket(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect_websocket(self, websocket: WebSocket) -> None:
        self.connections.discard(websocket)


settings = Settings()
controller = AppController(settings=settings)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    controller.loop = asyncio.get_running_loop()
    controller._append_log("info", "App started")
    try:
        controller.reload_config_from_disk()
        controller._append_log(
            "info", f"Loaded settings from {controller.settings_path.name}"
        )
    except FileNotFoundError:
        controller._append_log(
            "info", f"No settings file found ({controller.settings_path.name}); using defaults"
        )
    except Exception as ex:
        controller._append_log("error", f"Failed to load settings file: {ex}")
    yield
    try:
        controller.coach.close()
    except Exception:
        pass


app = FastAPI(title="Speech Translator", lifespan=lifespan)
app.state.controller = controller

# 1) API routes first
app.include_router(api_router, prefix="/api", tags=["api"])

# 2) WebSocket route second
app.websocket("/ws")(websocket_endpoint)

# 3) Static mount last
app.mount("/", StaticFiles(directory="static", html=True), name="static")
