from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.config import RuntimeConfig
from app.utils.audio_devices import list_capture_devices

router = APIRouter()


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
    prompt: str
    speaker_label: str = "Manual"


@router.post("/coach/ask")
async def ask_coach(payload: CoachAskRequest, request: Request) -> dict:
    controller = request.app.state.controller
    if not controller.coach.is_configured:
        raise HTTPException(
            status_code=412,
            detail="Coach is not configured. Set PROJECT_ENDPOINT, MODEL_DEPLOYMENT_NAME, and AGENT_ID/AGENT_NAME.",
        )
    try:
        hint = await controller.request_coach(
            prompt=payload.prompt.strip(),
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
