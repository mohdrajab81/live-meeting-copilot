"""
SummaryOrchestrator — owns end-of-session summary state and generation.

State: summary_pending, summary_result, summary_generated_ts, summary_error,
       topic_breakdown, agenda_adherence_pct, meeting_insights, keyword_index.

Shares the AppController RLock for all state mutations.
"""

import asyncio
import threading
import time
from typing import Any, Awaitable, Callable

from app.config import RuntimeConfig
from app.services.meeting_insights import build_keyword_index, build_meeting_insights
from app.services.topic_summary import (
    apply_topic_durations_from_utterance_ids,
    build_expected_agenda_context,
    build_topic_breakdown_from_definitions,
    prepare_transcript_utterances,
    render_transcript_for_prompt,
)
from app.services.summary import SummaryService

BroadcastCallback = Callable[[dict[str, Any]], Awaitable[None]]
BroadcastLogCallback = Callable[[str, str], Awaitable[None]]
# Returns (definitions_copy, items_copy) — called under shared lock.
GetTopicsCallback = Callable[[], tuple[list[dict[str, Any]], list[dict[str, Any]]]]


class SummaryOrchestrator:
    def __init__(
        self,
        lock: threading.RLock,
        summary_service: SummaryService,
        broadcast: BroadcastCallback,
        broadcast_log: BroadcastLogCallback,
        get_finals: Callable[[], list[dict[str, Any]]],
        get_config: Callable[[], RuntimeConfig],
        get_topics: GetTopicsCallback | None = None,
    ) -> None:
        self._lock = lock
        self._summary = summary_service
        self._broadcast = broadcast
        self._broadcast_log = broadcast_log
        self._get_finals = get_finals
        self._get_config = get_config
        self._get_topics = get_topics

        # State (protected by shared lock)
        self.summary_pending: bool = False
        self.summary_result: dict[str, Any] | None = None
        self.summary_generated_ts: float | None = None
        self.summary_error: str = ""
        self.topic_breakdown: list[dict[str, Any]] = []
        self.agenda_adherence_pct: float | None = None
        self.meeting_insights: dict[str, Any] = {}
        self.keyword_index: list[dict[str, Any]] = []

    @property
    def is_configured(self) -> bool:
        return self._summary.is_configured

    def clear_unlocked(self) -> None:
        self.summary_pending = False
        self.summary_result = None
        self.summary_generated_ts = None
        self.summary_error = ""
        self.topic_breakdown = []
        self.agenda_adherence_pct = None
        self.meeting_insights = {}
        self.keyword_index = []

    def snapshot_unlocked(self) -> dict[str, Any]:
        result = self.summary_result or {}
        return {
            "configured": self._summary.is_configured,
            "pending": self.summary_pending,
            "error": self.summary_error,
            "generated_ts": self.summary_generated_ts,
            # Flatten result for UI consumers and keep nested payload for compatibility.
            "executive_summary": str(result.get("executive_summary", "") or ""),
            "key_points": list(result.get("key_points") or []),
            "action_items": list(result.get("action_items") or []),
            "topic_key_points": list(result.get("topic_key_points") or []),
            "keywords": list(result.get("keywords") or []),
            "entities": list(result.get("entities") or []),
            "decisions_made": list(result.get("decisions_made") or []),
            "risks_and_blockers": list(result.get("risks_and_blockers") or []),
            "key_terms_defined": list(result.get("key_terms_defined") or []),
            "metadata": dict(result.get("metadata") or {}),
            "topic_breakdown": list(self.topic_breakdown),
            "agenda_adherence_pct": self.agenda_adherence_pct,
            "meeting_insights": dict(result.get("meeting_insights") or self.meeting_insights or {}),
            "keyword_index": list(result.get("keyword_index") or self.keyword_index or []),
            "result": self.summary_result,
        }

    def _build_summary_entries_unlocked(self) -> list[dict[str, Any]]:
        finals = self._get_finals()
        if not finals:
            return []
        # Sort the window by start_ts so dual-channel utterances appear in speech order,
        # not arrival order (which can differ when two recognizers run in parallel).
        window = sorted(
            finals[-500:],
            key=lambda f: float(f.get("start_ts") or f.get("ts") or 0.0),
        )
        if not window:
            return []
        # Derive baseline from the earliest item in the sorted window, not finals[0].
        # Using finals[0] as baseline could make out-of-order items clamp to [00:00],
        # collapsing distinct events at the start of a dual-channel session.
        entries: list[dict[str, Any]] = []
        for f in window:
            item_ts = float(f.get("ts") or 0.0)
            start_ts = float(f.get("start_ts") or item_ts or 0.0)
            end_ts = float(f.get("end_ts") or item_ts or start_ts)
            if end_ts < start_ts:
                end_ts = start_ts
            duration_sec_raw = f.get("duration_sec")
            try:
                duration_sec = max(0.0, float(duration_sec_raw))
            except (TypeError, ValueError):
                duration_sec = max(0.0, end_ts - start_ts)
            label = str(f.get("speaker_label") or "Speaker")
            text = str(f.get("en") or "").strip()
            if text:
                entries.append(
                    {
                        "ts": item_ts,
                        "start_ts": start_ts,
                        "end_ts": end_ts,
                        "duration_sec": duration_sec,
                        "speaker_label": label,
                        "text": text,
                    }
                )
        return prepare_transcript_utterances(entries, max_items=500)

    @staticmethod
    def _render_transcript_text(entries: list[dict[str, Any]]) -> str:
        return render_transcript_for_prompt(entries)

    def _build_transcript_text_unlocked(self) -> str:
        return self._render_transcript_text(self._build_summary_entries_unlocked())

    def _get_topic_definitions_unlocked(self) -> list[dict[str, Any]]:
        if self._get_topics is None:
            return []
        definitions, _ = self._get_topics()
        return [dict(row) for row in definitions if isinstance(row, dict)]

    def _build_topic_breakdown_unlocked(
        self,
    ) -> tuple[list[dict[str, Any]], float | None]:
        """Legacy deterministic breakdown from tracker state.

        Kept for compatibility tests and troubleshooting. Live summary generation
        now uses definition-driven one-shot model grouping for final breakdown.
        """
        if self._get_topics is None:
            return [], None

        definitions, items = self._get_topics()
        if not items:
            return [], None

        def_map: dict[str, int] = {}
        def_names: dict[str, str] = {}
        for d in definitions:
            name = str(d.get("name") or "").strip()
            if not name:
                continue
            key = name.lower()
            try:
                planned = max(0, int(d.get("expected_duration_min") or 0))
            except (TypeError, ValueError):
                planned = 0
            def_map[key] = planned
            def_names[key] = name

        breakdown: list[dict[str, Any]] = []
        item_keys: set[str] = set()

        for item in items:
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            key = name.lower()
            item_keys.add(key)
            try:
                actual_sec = max(0, int(item.get("time_seconds") or 0))
            except (TypeError, ValueError):
                actual_sec = 0
            actual_min = round(actual_sec / 60, 1)
            status = str(item.get("status") or "not_started").strip().lower()
            planned_min: int | None = def_map.get(key, 0) or None
            if planned_min and actual_sec == 0 and status == "not_started":
                status = "skipped"
            over_under_min: float | None = None
            if planned_min:
                over_under_min = round(actual_min - planned_min, 1)
            breakdown.append(
                {
                    "name": name,
                    "planned_min": planned_min,
                    "actual_min": actual_min,
                    "status": status,
                    "over_under_min": over_under_min,
                }
            )

        for key, planned in def_map.items():
            if planned > 0 and key not in item_keys:
                breakdown.append(
                    {
                        "name": def_names[key],
                        "planned_min": planned,
                        "actual_min": 0.0,
                        "status": "skipped",
                        "over_under_min": round(0.0 - planned, 1),
                    }
                )

        planned_topics = [
            (b["actual_min"], b["planned_min"])
            for b in breakdown
            if b["planned_min"] is not None
        ]
        adherence: float | None = None
        if planned_topics:
            total_planned = sum(p for _, p in planned_topics)
            if total_planned > 0:
                used_within_budget = sum(min(a, p) for a, p in planned_topics)
                adherence = round(100.0 * used_within_budget / total_planned, 1)
        return breakdown, adherence

    def _fallback_breakdown_from_topic_groups(
        self, topic_groups: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Convert model-inferred topic groups to a UI-friendly breakdown."""
        fallback: list[dict[str, Any]] = []
        for group in topic_groups:
            name = str(group.get("topic_name") or "").strip()
            if not name:
                continue
            est_raw = group.get("estimated_duration_minutes")
            actual_min = 0.0
            if est_raw is not None and str(est_raw).strip() != "":
                try:
                    actual_min = max(0.0, round(float(est_raw), 1))
                except (TypeError, ValueError):
                    actual_min = 0.0
            fallback.append(
                {
                    "name": name,
                    "planned_min": None,
                    "actual_min": actual_min,
                    "status": "inferred",
                    "over_under_min": None,
                }
            )
        return fallback

    async def run_summary(self) -> None:
        config = self._get_config()
        if not config.summary_enabled:
            return
        if not self._summary.is_configured:
            await self._broadcast_log(
                "warning",
                "Summary skipped: agent not configured (set SUMMARY_AGENT_NAME).",
            )
            return
        with self._lock:
            if self.summary_pending:
                return
            self.summary_pending = True
            self.summary_error = ""
            entries = self._build_summary_entries_unlocked()
            transcript_text = self._render_transcript_text(entries)
            topic_defs = self._get_topic_definitions_unlocked()

        if not transcript_text.strip():
            with self._lock:
                self.summary_pending = False
            await self._broadcast_log("info", "Summary skipped: transcript is empty.")
            return

        # Prepend expected agenda context when topic definitions exist.
        agenda_context = build_expected_agenda_context(topic_defs)
        if agenda_context:
            transcript_text = agenda_context + "\n\nTRANSCRIPT:\n" + transcript_text

        await self._broadcast_log("info", "Summary generation started.")
        try:
            from app.services.summary import SummaryResult  # noqa: F401
            result: Any = await asyncio.to_thread(self._summary.generate, transcript_text)
            resolved_topic_groups = apply_topic_durations_from_utterance_ids(
                result.topic_key_points,
                entries,
            )
            final_breakdown, final_adherence = build_topic_breakdown_from_definitions(
                topic_defs, resolved_topic_groups
            )
            if not final_breakdown:
                final_breakdown = self._fallback_breakdown_from_topic_groups(
                    resolved_topic_groups
                )
            meeting_insights = build_meeting_insights(entries)
            keyword_index = build_keyword_index(
                entries,
                result.key_terms_defined,
                result.keywords,
                result.entities,
            )
            payload: dict[str, Any] = {
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
                "generated_ts": time.time(),
                "total_ms": result.total_ms,
                "topic_breakdown": final_breakdown,
                "agenda_adherence_pct": final_adherence,
                "meeting_insights": meeting_insights,
                "keyword_index": keyword_index,
            }
            with self._lock:
                self.summary_pending = False
                self.summary_result = payload
                self.summary_generated_ts = payload["generated_ts"]
                self.summary_error = ""
                self.topic_breakdown = final_breakdown
                self.agenda_adherence_pct = final_adherence
                self.meeting_insights = meeting_insights
                self.keyword_index = keyword_index
            await self._broadcast({"type": "summary", **payload})
            await self._broadcast_log(
                "info",
                f"Summary generated: total_ms={result.total_ms}, "
                f"key_points={len(result.key_points)}, "
                f"action_items={len(result.action_items)}, "
                f"topic_groups={len(resolved_topic_groups)}, "
                f"entities={len(result.entities)}, "
                f"decisions={len(result.decisions_made)}, "
                f"risks={len(result.risks_and_blockers)}, "
                f"terms={len(result.key_terms_defined)}, "
                f"topics={len(final_breakdown)}, "
                f"keywords={len(keyword_index)}",
            )
        except Exception as ex:
            with self._lock:
                self.summary_pending = False
                self.summary_error = str(ex)
            await self._broadcast_log("error", f"Summary generation failed: {ex}")
            await self._broadcast({"type": "summary", "error": str(ex), "generated_ts": None})

    async def run_summary_now(self) -> dict[str, Any]:
        with self._lock:
            if self.summary_pending:
                raise ValueError("Summary generation already in progress.")
            if not self._summary.is_configured:
                raise ValueError(
                    "Summary agent not configured. Set SUMMARY_AGENT_NAME and related env vars."
                )
        await self.run_summary()
        with self._lock:
            return self.snapshot_unlocked()

