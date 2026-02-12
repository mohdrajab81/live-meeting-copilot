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

    def _should_trigger_coach_unlocked(self, item: dict[str, Any]) -> bool:
        if not self.config.coach_enabled:
            return False
        if not self.coach.is_configured:
            return False
        if not self._is_meaningful_coach_turn_unlocked(item):
            return False
        if self.coach_pending:
            return False
        now = time.time()
        if now - self.coach_last_run_ts < float(self.config.coach_cooldown_sec):
            return False

        trigger = self.config.coach_trigger_speaker
        speaker = str(item.get("speaker", "default") or "default")
        if trigger == "any":
            return True
        return trigger == speaker

    def _is_meaningful_coach_turn_unlocked(self, item: dict[str, Any]) -> bool:
        text = str(item.get("en", "") or "").strip().lower()
        if not text:
            return False

        words = [w for w in text.replace("?", " ").replace(".", " ").split() if w]
        if len(words) < 4:
            return False

        greeting_starts = (
            "hello",
            "hi",
            "hey",
            "good morning",
            "good afternoon",
            "good evening",
            "thank you",
            "thanks",
        )
        question_cues = (
            "?",
            "please",
            "can you",
            "could you",
            "would you",
            "tell me",
            "describe",
            "introduce",
            "what",
            "why",
            "how",
            "when",
            "where",
        )

        if text.startswith(greeting_starts):
            # Skip short opening pleasantries unless they already contain a clear request.
            if not any(cue in text for cue in question_cues):
                return False

        return True

    def _build_coach_prompt_unlocked(self, trigger_item: dict[str, Any]) -> str:
        turns = self.finals[-self.config.coach_max_turns :]
        lines: list[str] = []
        for turn in turns:
            label = str(turn.get("speaker_label", "Speaker") or "Speaker")
            en = str(turn.get("en", "") or "").strip()
            ar = str(turn.get("ar", "") or "").strip()
            text = en or ar
            if not text:
                continue
            ts = time.strftime("%H:%M:%S", time.localtime(float(turn.get("ts") or time.time())))
            lines.append(f"[{ts}] {label}: {text}")

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

        return "\n".join(
            [
                "You are my live interview copilot.",
                "Use my stored profile knowledge from the connected agent tools.",
                instruction,
                "",
                "Latest interviewer utterance:",
                f"{trigger_label}: {trigger_en}",
                "",
                "Recent conversation context:",
                "\n".join(lines) if lines else "(no recent turns)",
                "",
                "Return format:",
                "1) Suggested reply (short)",
                "2) 2-4 bullet proof points from my background",
                "3) One follow-up question I can ask (optional)",
            ]
        )

    def _next_coach_group_id_unlocked(self) -> str:
        self.coach_group_seq += 1
        return f"coach-{int(time.time())}-{self.coach_group_seq}"

    def _build_quick_hint_unlocked(self, trigger_item: dict[str, Any]) -> str:
        text = str(trigger_item.get("en", "") or "").strip()
        low = text.lower()
        if any(k in low for k in ("introduce yourself", "tell me about yourself", "summarize your background")):
            return (
                "Quick draft: 1) one-line intro, 2) years/domain focus, 3) one high-impact result, "
                "4) why this role. Keep it under 60-90 seconds."
            )
        if any(k in low for k in ("why should we hire", "why you", "why are you a good fit")):
            return (
                "Quick draft: match role needs to your strengths + one measurable outcome + close with readiness."
            )
        if "?" in text or any(
            k in low
            for k in ("can you", "could you", "would you", "what", "why", "how", "describe", "please")
        ):
            return (
                "Quick draft: acknowledge question, answer in 2-3 points, give one concrete project proof."
            )
        return "Quick tip: stay concise, answer directly, then add one verified proof point."

    async def _run_coach(
        self,
        prompt: str,
        trigger_item: dict[str, Any],
        group_id: str,
        trigger_ts: float,
    ) -> None:
        try:
            run_start = time.time()
            send_ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(run_start))
            await self.broadcast_log(
                "info",
                (
                    "Coach deep send: "
                    f"group={group_id}, send_ts={send_ts}, "
                    f"trigger={trigger_item.get('speaker_label', 'Speaker')}, "
                    f"trigger_text={str(trigger_item.get('en', '') or '').strip()}"
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
        except Exception as ex:
            await self.broadcast_log("error", f"Coach request failed: {ex}")
        finally:
            with self.lock:
                self.coach_pending = False

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
            coach_prompt = ""
            coach_group_id = ""
            coach_trigger_ts = 0.0
            quick_hint: dict[str, Any] | None = None
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
                trigger_coach = self._should_trigger_coach_unlocked(item)
                if trigger_coach:
                    self.coach_pending = True
                    self.coach_last_run_ts = time.time()
                    coach_trigger_ts = self.coach_last_run_ts
                    coach_group_id = self._next_coach_group_id_unlocked()
                    coach_prompt = self._build_coach_prompt_unlocked(item)
                    quick_hint = {
                        "type": "coach",
                        "hint_kind": "quick",
                        "group_id": coach_group_id,
                        "ts": time.time(),
                        "speaker": str(item.get("speaker", "default") or "default"),
                        "speaker_label": str(
                            item.get("speaker_label", "Speaker") or "Speaker"
                        ),
                        "trigger_en": str(item.get("en", "") or ""),
                        "suggestion": self._build_quick_hint_unlocked(item),
                    }
                    self.coach_hints.append(quick_hint)
                    if len(self.coach_hints) > 120:
                        self.coach_hints = self.coach_hints[-120:]
            self._broadcast_from_thread(item)
            if quick_hint:
                self._broadcast_from_thread(quick_hint)
                self._broadcast_from_thread(
                    self._append_log(
                        "info",
                        (
                            "Coach quick hint trace: "
                            f"group={coach_group_id}, trigger={item['speaker_label']}, "
                            f"text_len={len(item['en'])}, prompt_chars={len(coach_prompt)}"
                        ),
                    )
                )
            if trigger_coach:
                loop = self.loop
                if loop and loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        self._run_coach(
                            coach_prompt,
                            item,
                            coach_group_id,
                            coach_trigger_ts,
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
        return self.speech.start_recognition()

    def stop(self) -> bool:
        return self.speech.stop_recognition()

    def clear_logs(self) -> None:
        with self.lock:
            self.logs = []

    def clear_transcript(self) -> None:
        with self.lock:
            self.finals = []
            self.en_live = ""
            self.ar_live = ""
            self.live_partials = {}

    def clear_coach(self) -> None:
        with self.lock:
            self.coach_hints = []
            self.coach_pending = False
            self.coach_last_run_ts = 0.0
        self.coach.clear_conversation()

    async def request_coach(self, prompt: str, speaker_label: str = "Manual") -> dict[str, Any]:
        send_ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        await self.broadcast_log(
            "info",
            f"Coach manual send: send_ts={send_ts}, speaker_label={speaker_label}, prompt={prompt}",
        )
        result = await asyncio.to_thread(self.coach.ask, prompt)
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
