import threading
import time
from collections import deque

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.config import RuntimeConfig
from app.utils.audio_devices import list_capture_devices

router = APIRouter()
_coach_rate_lock = threading.Lock()
_coach_rate_window_sec = 60
_coach_rate_limit = 6
_coach_rate_buckets: dict[str, deque[float]] = {}


def _enforce_coach_rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    cutoff = now - _coach_rate_window_sec

    with _coach_rate_lock:
        bucket = _coach_rate_buckets.get(client_ip)
        if bucket is None:
            bucket = deque()
            _coach_rate_buckets[client_ip] = bucket

        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

        if len(bucket) >= _coach_rate_limit:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded for /coach/ask. Try again in about a minute.",
            )
        bucket.append(now)


@router.get("/state")
def get_state(request: Request) -> dict:
    return request.app.state.controller.snapshot()


@router.get("/config")
def get_config(request: Request) -> dict:
    return request.app.state.controller.get_config()


@router.get("/audio/devices")
def get_audio_devices() -> dict:
    return {"devices": list_capture_devices()}


@router.put("/config")
async def put_config(config: RuntimeConfig, request: Request) -> dict:
    controller = request.app.state.controller
    if controller.running:
        raise HTTPException(status_code=409, detail="Stop app before changing config")
    controller.set_config(config)
    await controller.broadcast_log("info", "Configuration updated in memory")
    return {"ok": True, "config": controller.get_config()}


@router.post("/config/save")
async def save_config(request: Request) -> dict:
    controller = request.app.state.controller
    path = controller.save_config_to_disk()
    await controller.broadcast_log("info", f"Configuration saved to {path}")
    return {"ok": True, "path": path, "config": controller.get_config()}


@router.post("/config/reload")
async def reload_config(request: Request) -> dict:
    controller = request.app.state.controller
    if controller.running:
        raise HTTPException(status_code=409, detail="Stop app before reloading config")
    try:
        config = controller.reload_config_from_disk()
    except FileNotFoundError as ex:
        raise HTTPException(status_code=404, detail=str(ex))
    await controller.broadcast_log("info", "Configuration reloaded from disk")
    return {"ok": True, "config": config}


@router.post("/config/reset-defaults")
async def reset_config_defaults(request: Request) -> dict:
    controller = request.app.state.controller
    if controller.running:
        raise HTTPException(status_code=409, detail="Stop app before restoring defaults")
    config = controller.reset_config_to_defaults()
    await controller.broadcast_log("info", "Configuration restored to system defaults")
    return {"ok": True, "config": config}


@router.post("/start")
async def start(request: Request) -> dict:
    controller = request.app.state.controller
    started = controller.start()
    if started:
        await controller.broadcast_log("info", "Start requested from web")
    return {"ok": True, "started": started}


@router.post("/stop")
async def stop(request: Request) -> dict:
    controller = request.app.state.controller
    stopped = controller.stop()
    if stopped:
        await controller.broadcast_log("info", "Stop requested from web")
    return {"ok": True, "stopped": stopped}


@router.post("/logs/clear")
def clear_logs(request: Request) -> dict:
    request.app.state.controller.clear_logs()
    return {"ok": True}


@router.post("/transcript/clear")
async def clear_transcript(request: Request) -> dict:
    controller = request.app.state.controller
    controller.clear_transcript()
    await controller.broadcast_log("info", "Transcript cleared from web")
    return {"ok": True}


@router.post("/coach/clear")
async def clear_coach(request: Request) -> dict:
    controller = request.app.state.controller
    controller.clear_coach()
    await controller.broadcast_log("info", "Coach history cleared from web")
    return {"ok": True}


class CoachAskRequest(BaseModel):
    prompt: str = Field(max_length=2000)
    speaker_label: str = Field(default="Manual", max_length=64)


class TopicsConfigureRequest(BaseModel):
    agenda: list[str] = Field(default_factory=list, max_length=20)
    enabled: bool = True
    allow_new_topics: bool = True
    interval_sec: int = Field(default=60, ge=30, le=300)
    window_sec: int = Field(default=90, ge=60, le=300)


@router.post("/coach/ask")
async def ask_coach(payload: CoachAskRequest, request: Request) -> dict:
    _enforce_coach_rate_limit(request)
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="prompt must not be empty")

    controller = request.app.state.controller
    if not controller.coach.is_configured:
        raise HTTPException(
            status_code=412,
            detail="Coach is not configured. Set PROJECT_ENDPOINT, MODEL_DEPLOYMENT_NAME, and AGENT_ID/AGENT_NAME.",
        )
    try:
        hint = await controller.request_coach(
            prompt=prompt,
            speaker_label=payload.speaker_label.strip() or "Manual",
        )
    except Exception as ex:
        msg = str(ex)
        if "DefaultAzureCredential failed to retrieve a token" in msg:
            msg = (
                "Coach authentication failed. Sign in to the correct Azure tenant "
                "for AI Foundry, then retry. Example: "
                "az logout && az login --tenant \"7bff966e-1643-4ea5-b536-e449cd5de230\" "
                "--scope \"https://ai.azure.com/.default\""
            )
        raise HTTPException(status_code=502, detail=msg)
    return {"ok": True, "hint": hint}


@router.post("/topics/configure")
async def configure_topics(payload: TopicsConfigureRequest, request: Request) -> dict:
    controller = request.app.state.controller
    topics = controller.configure_topics(
        agenda=payload.agenda,
        enabled=payload.enabled,
        allow_new_topics=payload.allow_new_topics,
        interval_sec=payload.interval_sec,
        window_sec=payload.window_sec,
    )
    await controller.broadcast({"type": "topics_update", "topics": topics})
    await controller.broadcast_log(
        "info",
        (
            "Topics configured: "
            f"enabled={topics.get('enabled')}, agenda={len(topics.get('agenda', []))}, "
            f"allow_new={topics.get('allow_new_topics')}, "
            f"interval={topics.get('interval_sec')}s, window={topics.get('window_sec')}s"
        ),
    )
    return {"ok": True, "topics": topics}


@router.post("/topics/analyze-now")
async def analyze_topics_now(request: Request) -> dict:
    controller = request.app.state.controller
    try:
        topics = await controller.analyze_topics_now()
    except Exception as ex:
        raise HTTPException(status_code=409, detail=str(ex))
    return {"ok": True, "topics": topics}


@router.post("/topics/clear")
async def clear_topics(request: Request) -> dict:
    controller = request.app.state.controller
    controller.clear_topics()
    topics = controller.snapshot().get("topics", {})
    await controller.broadcast({"type": "topics_update", "topics": topics})
    await controller.broadcast_log("info", "Topics cleared from web")
    return {"ok": True, "topics": topics}
