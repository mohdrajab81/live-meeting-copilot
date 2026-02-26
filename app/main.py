import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from app.api.routes import router as api_router
from app.api.websocket import websocket_endpoint
from app.config import Settings, validate_environment
from app.controller import AppController

load_dotenv()

settings = Settings()
validate_environment(settings)
controller = AppController(settings=settings)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    loop = asyncio.get_running_loop()
    controller.set_event_loop(loop)
    controller.translation.start(loop)
    watchdog_task = asyncio.create_task(controller.watchdog_loop())
    controller.broadcast_svc.append_log("info", "App started")
    try:
        controller.reload_config_from_disk()
        controller.broadcast_svc.append_log(
            "info",
            f"Loaded settings from {controller.config_store._settings_path.name}",
        )
    except FileNotFoundError:
        controller.broadcast_svc.append_log(
            "info",
            f"No settings file found ({controller.config_store._settings_path.name}); using defaults",
        )
    except Exception as ex:
        controller.broadcast_svc.append_log("error", f"Failed to load settings file: {ex}")
    yield
    await controller.translation.stop()
    watchdog_task.cancel()
    try:
        await watchdog_task
    except asyncio.CancelledError:
        pass
    try:
        controller.coach.close()
    except Exception:
        pass
    try:
        controller.topic_tracker.close()
    except Exception:
        pass
    try:
        controller.summary_service.close()
    except Exception:
        pass


app = FastAPI(title="Speech Translator", lifespan=lifespan)
app.state.controller = controller


@app.middleware("http")
async def disable_http_cache(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path or ""
    if not path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


# 1) API routes first
app.include_router(api_router, prefix="/api", tags=["api"])

# 2) WebSocket route second
app.websocket("/ws")(websocket_endpoint)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon_ico() -> RedirectResponse:
    return RedirectResponse(url="/favicon.svg")


# 3) Static mount last
app.mount("/", StaticFiles(directory="static", html=True), name="static")
