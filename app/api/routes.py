import asyncio
import csv
import io
import json
import threading
import time
from collections import deque
from typing import Literal

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from app.api.auth import require_http_auth
from app.config import RuntimeConfig
from app.services.meeting_insights import build_keyword_index, build_meeting_insights
from app.services.topic_summary import (
    apply_topic_durations_from_utterance_ids,
    build_expected_agenda_context,
    build_topic_breakdown_from_definitions,
    prepare_transcript_utterances,
    render_transcript_for_prompt,
)
from app.utils.audio_devices import list_capture_devices

router = APIRouter(dependencies=[Depends(require_http_auth)])
_coach_rate_lock = threading.Lock()
_summary_rate_lock = threading.Lock()
_coach_rate_window_sec = 60
_coach_rate_limit = 6
_coach_rate_buckets: dict[str, deque[float]] = {}
_summary_rate_window_sec = 60
_summary_rate_limit = 2
_summary_rate_buckets: dict[str, deque[float]] = {}


def _enforce_rate_limit(
    request: Request,
    *,
    lock: threading.Lock,
    buckets: dict[str, deque[float]],
    window_sec: int,
    limit: int,
    detail: str,
) -> None:
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    cutoff = now - window_sec

    with lock:
        # Expire stale timestamps and remove empty buckets to bound memory.
        for key, candidate in list(buckets.items()):
            while candidate and candidate[0] <= cutoff:
                candidate.popleft()
            if not candidate:
                buckets.pop(key, None)

        bucket = buckets.get(client_ip)
        if bucket is None:
            bucket = deque()
            buckets[client_ip] = bucket

        if len(bucket) >= limit:
            raise HTTPException(status_code=429, detail=detail)
        bucket.append(now)


def _enforce_coach_rate_limit(request: Request) -> None:
    _enforce_rate_limit(
        request,
        lock=_coach_rate_lock,
        buckets=_coach_rate_buckets,
        window_sec=_coach_rate_window_sec,
        limit=_coach_rate_limit,
        detail="Rate limit exceeded for /coach/ask. Try again in about a minute.",
    )


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
    return {"ok": True, "config": controller.get_config()}


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
    started = await asyncio.to_thread(controller.start)
    if started:
        await controller.broadcast_log("info", "Start requested from web")
    return {"ok": True, "started": started}


@router.post("/stop")
async def stop(request: Request) -> dict:
    controller = request.app.state.controller
    stopped = await controller.stop_async()
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


class TopicDefinitionPayload(BaseModel):
    id: str = Field(default="", max_length=80)
    name: str = Field(min_length=1, max_length=120)
    expected_duration_min: int = Field(default=0, ge=0, le=600)
    priority: Literal["low", "normal", "high", "mandatory", "optional"] = "normal"
    comments: str = Field(default="", max_length=400)
    order: int = Field(default=0, ge=0, le=10_000)


class TopicsConfigureRequest(BaseModel):
    definitions: list[TopicDefinitionPayload] = Field(default_factory=list, max_length=80)


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
            detail="Coach is not configured. Set PROJECT_ENDPOINT and GUIDANCE_AGENT_NAME.",
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
        agenda=[],
        enabled=False,
        allow_new_topics=False,
        interval_sec=60,
        definitions=[row.model_dump() for row in payload.definitions],
    )
    await controller.broadcast({"type": "topics_update", "topics": topics})
    await controller.broadcast_log(
        "info",
        (
            "Topic definitions saved: "
            f"definitions={len(topics.get('definitions', []))}"
        ),
    )
    return {"ok": True, "topics": topics}


@router.post("/topics/clear")
async def clear_topics(request: Request) -> dict:
    controller = request.app.state.controller
    controller.clear_topics()
    topics = controller.snapshot().get("topics", {})
    await controller.broadcast({"type": "topics_update", "topics": topics})
    await controller.broadcast_log("info", "Topics cleared from web")
    return {"ok": True, "topics": topics}


# ── Summary routes ────────────────────────────────────────────────────────────

@router.post("/summary/generate")
async def generate_summary(request: Request) -> dict:
    _enforce_rate_limit(
        request,
        lock=_summary_rate_lock,
        buckets=_summary_rate_buckets,
        window_sec=_summary_rate_window_sec,
        limit=_summary_rate_limit,
        detail="Rate limit exceeded for /summary/generate. Try again in about a minute.",
    )
    controller = request.app.state.controller
    config = controller.get_runtime_config()
    if not config.summary_enabled:
        raise HTTPException(status_code=412, detail="Summary is disabled in config.")
    if not controller.summary_service.is_configured:
        raise HTTPException(
            status_code=412,
            detail="Summary agent not configured. Set SUMMARY_AGENT_NAME and related env vars.",
        )
    try:
        snap = await controller.generate_summary()
    except ValueError as ex:
        raise HTTPException(status_code=409, detail=str(ex))
    except Exception as ex:
        raise HTTPException(status_code=502, detail=str(ex))
    return {"ok": True, "summary": snap}


@router.post("/summary/clear")
async def clear_summary(request: Request) -> dict:
    controller = request.app.state.controller
    controller.clear_summary()
    snap = controller.summary_snapshot()
    await controller.broadcast({"type": "summary_cleared"})
    await controller.broadcast_log("info", "Summary cleared from web")
    return {"ok": True, "summary": snap}


@router.get("/summary")
def get_summary(request: Request) -> dict:
    controller = request.app.state.controller
    return {"ok": True, "summary": controller.summary_snapshot()}


@router.post("/summary/from-transcript")
async def summary_from_transcript(
    request: Request,
    file: UploadFile,
    topics_definitions_json: str | None = Form(default=None),
) -> dict:
    """Generate a summary from an uploaded transcript CSV (exported by this app).

    Shares the same rate-limit pool as /summary/generate.
    Does NOT mutate session state — result is returned directly in the response.
    """
    _enforce_rate_limit(
        request,
        lock=_summary_rate_lock,
        buckets=_summary_rate_buckets,
        window_sec=_summary_rate_window_sec,
        limit=_summary_rate_limit,
        detail="Rate limit exceeded. Try again in about a minute.",
    )
    controller = request.app.state.controller
    if not controller.summary_service.is_configured:
        raise HTTPException(
            status_code=412,
            detail="Summary agent not configured. Set SUMMARY_AGENT_NAME and related env vars.",
        )

    _MAX_BYTES = 5 * 1024 * 1024  # 5 MB
    raw = await file.read(_MAX_BYTES + 1)
    if len(raw) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 5 MB).")
    try:
        text = raw.decode("utf-8-sig")  # strips BOM if present
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded.")

    try:
        transcript_rows = _parse_transcript_csv_rows(text)
    except Exception as ex:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {ex}")

    transcript_rows = prepare_transcript_utterances(transcript_rows, max_items=500)
    transcript_text = render_transcript_for_prompt(transcript_rows)
    if not transcript_text.strip():
        raise HTTPException(status_code=400, detail="Transcript is empty after parsing.")

    topic_defs = _parse_topics_definitions_json(topics_definitions_json)
    agenda_context = build_expected_agenda_context(topic_defs)
    if agenda_context:
        transcript_text = agenda_context + "\n\nTRANSCRIPT:\n" + transcript_text

    try:
        result = await asyncio.to_thread(
            controller.summary_service.generate, transcript_text
        )
    except Exception as ex:
        raise HTTPException(status_code=502, detail=f"Summary generation failed: {ex}")

    runtime_cfg = controller.get_runtime_config()
    resolved_topic_groups = apply_topic_durations_from_utterance_ids(
        result.topic_key_points,
        transcript_rows,
        duration_mode=runtime_cfg.summary_topic_duration_mode,
        gap_threshold_sec=runtime_cfg.summary_topic_gap_threshold_sec,
    )
    topic_breakdown, agenda_adherence_pct = build_topic_breakdown_from_definitions(
        topic_defs, resolved_topic_groups
    )

    return {
        "ok": True,
        "result": {
            "executive_summary": result.executive_summary,
            "key_points": result.key_points,
            "action_items": result.action_items,
            "topic_key_points": resolved_topic_groups,
            "keywords": result.keywords,
            "entities": result.entities,
            "decisions_made": result.decisions_made,
            "risks_and_blockers": result.risks_and_blockers,
            "key_terms_defined": result.key_terms_defined,
            "metadata": result.metadata,
            "topic_breakdown": topic_breakdown,
            "agenda_adherence_pct": agenda_adherence_pct,
            "meeting_insights": build_meeting_insights(transcript_rows),
            "keyword_index": build_keyword_index(
                transcript_rows,
                result.key_terms_defined,
                result.keywords,
                result.entities,
            ),
            "total_ms": result.total_ms,
        },
    }


def _parse_topics_definitions_json(raw: str | None) -> list[dict[str, object]]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    cleaned: list[dict[str, object]] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        try:
            expected = max(0, int(row.get("expected_duration_min") or 0))
        except (TypeError, ValueError):
            expected = 0
        cleaned.append({"name": name, "expected_duration_min": expected})
    return cleaned


def _parse_transcript_csv_rows(text: str) -> list[dict[str, object]]:
    """Parse exported transcript CSV into normalized transcript rows.

    Supports legacy CSV columns plus timing-enriched columns:
    - Legacy: time_unix_sec, speaker_label, english
    - Enriched: start_unix_sec, end_unix_sec, duration_sec, offset_sec
    Sorts by start_unix_sec (fallback time_unix_sec) and caps at 500 rows.
    """
    def _parse_float(raw: object) -> float | None:
        value = str(raw or "").strip()
        if not value:
            return None
        try:
            parsed = float(value)
        except ValueError:
            return None
        return parsed

    reader = csv.DictReader(io.StringIO(text))
    rows: list[dict[str, object]] = []
    for row in reader:
        english = (row.get("english") or "").strip()
        ts_raw = (
            row.get("time_unix_sec")
            or row.get("ts")
            or row.get("event_unix_sec")
            or ""
        )
        start_raw = (
            row.get("start_unix_sec")
            or row.get("start_ts")
            or row.get("start_time_unix_sec")
            or ""
        )
        end_raw = (
            row.get("end_unix_sec")
            or row.get("end_ts")
            or row.get("end_time_unix_sec")
            or ""
        )
        duration_raw = row.get("duration_sec") or ""
        offset_raw = row.get("offset_sec") or ""
        label = (row.get("speaker_label") or "Speaker").strip()
        if not english:
            continue
        ts = _parse_float(ts_raw)
        start_ts = _parse_float(start_raw)
        end_ts = _parse_float(end_raw)
        duration_sec = _parse_float(duration_raw)
        offset_sec = _parse_float(offset_raw)

        if ts is None and start_ts is None:
            continue

        if ts is None:
            ts = float(start_ts or 0.0)
        if start_ts is None:
            start_ts = float(ts)
        if end_ts is None:
            if duration_sec is not None and duration_sec > 0:
                end_ts = float(start_ts + duration_sec)
            else:
                end_ts = float(ts)
        if duration_sec is None:
            duration_sec = max(0.0, float(end_ts - start_ts))

        if end_ts < start_ts:
            end_ts = start_ts
        if ts < end_ts:
            ts = end_ts
        if ts < start_ts:
            ts = start_ts

        rows.append(
            {
                "ts": float(ts),
                "start_ts": float(start_ts),
                "end_ts": float(end_ts),
                "duration_sec": float(max(0.0, duration_sec)),
                "offset_sec": float(offset_sec) if offset_sec is not None and offset_sec >= 0 else None,
                "speaker_label": label or "Speaker",
                "text": english,
            }
        )

    if not rows:
        return []
    rows.sort(
        key=lambda r: (
            float(r.get("start_ts") or r.get("ts") or 0.0),
            float(r.get("ts") or 0.0),
        )
    )
    return rows[-500:]


def _rows_to_transcript_text(rows: list[dict[str, object]]) -> str:
    # Backward wrapper for tests/compatibility while prompt rendering moved to shared helper.
    return render_transcript_for_prompt(prepare_transcript_utterances(rows, max_items=500))
