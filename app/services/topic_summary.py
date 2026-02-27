"""Helpers for definition-driven summary topic coverage."""

from __future__ import annotations

from typing import Any


def _norm(value: Any) -> str:
    return " ".join(str(value or "").split()).strip().lower()


def parse_topic_definitions(raw_defs: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in raw_defs or []:
        if not isinstance(row, dict):
            continue
        name = " ".join(str(row.get("name") or "").split()).strip()
        if not name:
            continue
        key = _norm(name)
        if key in seen:
            continue
        seen.add(key)
        try:
            expected = max(0, int(row.get("expected_duration_min") or 0))
        except (TypeError, ValueError):
            expected = 0
        out.append(
            {
                "name": name,
                "expected_duration_min": expected,
            }
        )
    return out


def build_expected_agenda_context(topic_defs: list[dict[str, Any]] | None) -> str:
    defs = parse_topic_definitions(topic_defs)
    if not defs:
        return ""
    lines = ["EXPECTED AGENDA TOPICS (user-defined):"]
    for row in defs:
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        # Intentionally omit planned minutes from prompt context to reduce leakage
        # into model-estimated durations.
        lines.append(f"- {name}")
    return "\n".join(lines)


def build_topic_breakdown_from_definitions(
    topic_defs: list[dict[str, Any]] | None,
    topic_groups: list[dict[str, Any]] | None,
) -> tuple[list[dict[str, Any]], float | None]:
    defs = parse_topic_definitions(topic_defs)
    groups = [row for row in (topic_groups or []) if isinstance(row, dict)]

    group_map: dict[str, dict[str, Any]] = {}
    unplanned: list[dict[str, Any]] = []

    for row in groups:
        name = " ".join(str(row.get("topic_name") or "").split()).strip()
        if not name:
            continue
        key = _norm(name)
        est_raw = row.get("estimated_duration_minutes")
        actual_min = 0.0
        if est_raw is not None and str(est_raw).strip() != "":
            try:
                actual_min = max(0.0, round(float(est_raw), 1))
            except (TypeError, ValueError):
                actual_min = 0.0
        candidate = {
            "name": name,
            "actual_min": actual_min,
        }
        if key not in group_map:
            group_map[key] = candidate
        else:
            # Keep the higher estimate if model emitted duplicates.
            if float(candidate["actual_min"]) > float(group_map[key]["actual_min"]):
                group_map[key] = candidate

    breakdown: list[dict[str, Any]] = []
    planned_pairs: list[tuple[float, int]] = []

    for row in defs:
        name = str(row.get("name") or "").strip()
        key = _norm(name)
        planned = int(row.get("expected_duration_min") or 0)
        planned_min: int | None = planned if planned > 0 else None
        grp = group_map.pop(key, None)
        actual = float(grp["actual_min"]) if grp is not None else 0.0
        if planned_min is not None and actual <= 0.0:
            status = "skipped"
        elif actual > 0.0:
            status = "covered"
        else:
            status = "not_started"
        over_under = round(actual - planned_min, 1) if planned_min is not None else None
        breakdown.append(
            {
                "name": name,
                "planned_min": planned_min,
                "actual_min": round(actual, 1),
                "status": status,
                "over_under_min": over_under,
            }
        )
        if planned_min is not None:
            planned_pairs.append((actual, planned_min))

    for grp in group_map.values():
        unplanned.append(
            {
                "name": str(grp["name"]),
                "planned_min": None,
                "actual_min": round(float(grp["actual_min"]), 1),
                "status": "inferred",
                "over_under_min": None,
            }
        )
    unplanned.sort(key=lambda row: str(row["name"]).lower())
    breakdown.extend(unplanned)

    adherence: float | None = None
    if planned_pairs:
        total_planned = sum(planned for _, planned in planned_pairs)
        if total_planned > 0:
            used_within = sum(min(actual, planned) for actual, planned in planned_pairs)
            adherence = round(100.0 * used_within / total_planned, 1)

    return breakdown, adherence


def prepare_transcript_utterances(
    rows: list[dict[str, Any]] | None,
    *,
    max_items: int = 500,
) -> list[dict[str, Any]]:
    """Normalize transcript rows and attach deterministic utterance IDs."""
    normalized: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        text = " ".join(str(row.get("text") or "").split()).strip()
        if not text:
            continue
        try:
            ts = float(row.get("ts") or 0.0)
        except (TypeError, ValueError):
            ts = 0.0
        try:
            start_ts = float(row.get("start_ts", ts) or ts)
        except (TypeError, ValueError):
            start_ts = ts
        try:
            end_ts = float(row.get("end_ts", ts) or ts)
        except (TypeError, ValueError):
            end_ts = ts
        if start_ts <= 0 and ts > 0:
            start_ts = ts
        if ts <= 0 and start_ts > 0:
            ts = start_ts
        if end_ts < start_ts:
            end_ts = start_ts
        if ts < end_ts:
            ts = end_ts
        if ts < start_ts:
            ts = start_ts
        duration_sec = row.get("duration_sec")
        try:
            duration_val = max(0.0, float(duration_sec))
        except (TypeError, ValueError):
            duration_val = max(0.0, end_ts - start_ts)
        normalized.append(
            {
                "ts": ts,
                "start_ts": start_ts,
                "end_ts": end_ts,
                "duration_sec": duration_val,
                "speaker_label": " ".join(str(row.get("speaker_label") or "Speaker").split()).strip()
                or "Speaker",
                "text": text,
            }
        )

    normalized.sort(
        key=lambda row: (
            float(row.get("start_ts") or row.get("ts") or 0.0),
            float(row.get("ts") or 0.0),
        )
    )
    if max_items > 0 and len(normalized) > max_items:
        normalized = normalized[-max_items:]

    with_ids: list[dict[str, Any]] = []
    for idx, row in enumerate(normalized, start=1):
        out = dict(row)
        out["utterance_id"] = f"U{idx:04d}"
        with_ids.append(out)
    return with_ids


def render_transcript_for_prompt(rows: list[dict[str, Any]] | None) -> str:
    if not rows:
        return ""
    baseline = float(rows[0].get("start_ts") or rows[0].get("ts") or 0.0)
    lines: list[str] = []
    for row in rows:
        start_ts = float(row.get("start_ts") or row.get("ts") or 0.0)
        elapsed = max(0.0, start_ts - baseline)
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        label = str(row.get("speaker_label") or "Speaker")
        text = str(row.get("text") or "").strip()
        utterance_id = str(row.get("utterance_id") or "").strip()
        if not text:
            continue
        if utterance_id:
            # Keep ID in a fixed position right after timestamp for better model consistency.
            lines.append(f"[{mins:02d}:{secs:02d}] [id:{utterance_id}] {label}: {text}")
        else:
            lines.append(f"[{mins:02d}:{secs:02d}] {label}: {text}")
    return "\n".join(lines)


def apply_topic_durations_from_utterance_ids(
    topic_groups: list[dict[str, Any]] | None,
    rows: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Set topic estimated_duration_minutes from deterministic utterance durations only.

    If a topic has no valid utterance_ids in this transcript, duration is None.
    """
    id_to_duration: dict[str, float] = {}
    all_ids_in_order: list[str] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        uid = str(row.get("utterance_id") or "").strip().upper()
        if not uid:
            continue
        try:
            duration = max(0.0, float(row.get("duration_sec") or 0.0))
        except (TypeError, ValueError):
            duration = 0.0
        id_to_duration[uid] = duration
        all_ids_in_order.append(uid)

    out: list[dict[str, Any]] = []
    globally_assigned: set[str] = set()
    for group in topic_groups or []:
        if not isinstance(group, dict):
            continue
        topic = dict(group)
        raw_ids = topic.get("utterance_ids")
        if isinstance(raw_ids, list):
            ids_source = raw_ids
        elif isinstance(raw_ids, str):
            ids_source = [part.strip() for part in raw_ids.replace(",", " ").split()]
        else:
            ids_source = []

        normalized_ids: list[str] = []
        seen_ids: set[str] = set()
        for raw in ids_source:
            uid = str(raw or "").strip().upper()
            if not uid or uid in seen_ids:
                continue
            seen_ids.add(uid)
            if uid not in id_to_duration:
                continue
            # Guarantee one-to-one assignment across topics:
            # first topic that claims an id keeps it.
            if uid in globally_assigned:
                continue
            globally_assigned.add(uid)
            normalized_ids.append(uid)
        topic["utterance_ids"] = normalized_ids

        matched = normalized_ids
        if matched:
            total_sec = sum(id_to_duration[uid] for uid in matched)
            topic["estimated_duration_minutes"] = round(total_sec / 60.0, 1)
        else:
            topic["estimated_duration_minutes"] = None
        out.append(topic)

    # Ensure full speech coverage even when the model omits some utterances.
    missing_ids = [uid for uid in all_ids_in_order if uid not in globally_assigned]
    # Only auto-fill when the model produced at least some valid id assignments.
    # If it produced none, keep legacy behavior and do not force an "Other" bucket.
    if missing_ids and globally_assigned:
        total_sec = sum(id_to_duration[uid] for uid in missing_ids)
        out.append(
            {
                "topic_name": "Unassigned / Other",
                "estimated_duration_minutes": round(total_sec / 60.0, 1),
                "utterance_ids": missing_ids,
                "origin": "Inferred",
                "key_points": [],
            }
        )
    return out
