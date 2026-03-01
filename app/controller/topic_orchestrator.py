"""
TopicOrchestrator — owns all topic-tracking state and logic.

State (13 variables): topics_enabled, topics_allow_new,
topics_interval_sec, topics_pending, topics_last_run_ts,
topics_last_final_idx, topics_last_error, topics_agenda, topics_definitions,
topics_items, topics_runtime_meta, topics_settings_saved, topics_runs.

Shares the AppController RLock for all state mutations.
"""

import asyncio
import math
import re
import threading
import time
from typing import Any, Awaitable, Callable, Literal

from app.services.topic_tracker import TopicTrackerService


BroadcastCallback = Callable[[dict[str, Any]], Awaitable[None]]
BroadcastLogCallback = Callable[[str, str], Awaitable[None]]


class TopicOrchestrator:
    _VALID_TOPIC_STATUSES = {"not_started", "active", "covered"}

    def __init__(
        self,
        lock: threading.RLock,
        topic_tracker: TopicTrackerService,
        broadcast: BroadcastCallback,
        broadcast_log: BroadcastLogCallback,
        get_finals: Callable[[], list[dict[str, Any]]],
        preview_text: Callable[[str], str],
    ) -> None:
        self._lock = lock
        self._topic_tracker = topic_tracker
        self._broadcast = broadcast
        self._broadcast_log = broadcast_log
        self._get_finals = get_finals
        self._preview_text = preview_text

        # Topic state (protected by shared lock)
        self.topics_enabled = False
        self.topics_allow_new = True
        self.topics_interval_sec = 60
        self.topics_pending = False
        self.topics_last_run_ts = 0.0
        self.topics_last_final_idx = 0
        self.topics_last_error = ""
        self.topics_agenda: list[str] = []
        self.topics_definitions: list[dict[str, Any]] = []
        self.topics_items: list[dict[str, Any]] = []
        self.topics_runtime_meta: dict[str, dict[str, int]] = {}
        self.topics_settings_saved = False
        self.topics_runs: list[dict[str, Any]] = []
        self.topics_session_started_ts: float = 0.0

    @property
    def is_tracker_configured(self) -> bool:
        return self._topic_tracker.is_configured

    # ── Pure normalisation helpers ────────────────────────────────────────────

    @staticmethod
    def _normalize_name(value: str) -> str:
        return " ".join(str(value or "").strip().split()).lower()

    @staticmethod
    def _is_usable_new_name(value: str) -> bool:
        name = " ".join(str(value or "").split()).strip()
        if len(name) < 2 or len(name) > 80:
            return False
        key = " ".join(name.strip().split()).lower()
        if not key:
            return False
        if key in {"topic", "new topic", "unknown", "other", "misc", "miscellaneous"}:
            return False
        return True

    @staticmethod
    def _normalize_comments(value: Any, *, max_chars: int = 100) -> str:
        text = " ".join(str(value or "").split()).strip()
        if not text:
            return ""
        if len(text) <= max_chars:
            return text
        return text[:max_chars].rstrip()

    @classmethod
    def _normalize_status(
        cls,
        value: Any,
        *,
        default: Literal["not_started", "active", "covered"] = "not_started",
    ) -> str:
        status = str(value or default).strip().lower()
        if status not in cls._VALID_TOPIC_STATUSES:
            return default
        return status

    def _normalize_definition(
        self, raw: dict[str, Any], *, fallback_order: int = 0
    ) -> dict[str, Any] | None:
        if not isinstance(raw, dict):
            return None
        name = " ".join(str(raw.get("name", "") or "").split()).strip()
        if not name:
            return None
        raw_id = " ".join(str(raw.get("id", "") or "").split()).strip()
        if raw_id:
            safe_id = raw_id[:80]
        else:
            slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            safe_id = slug[:64] or f"topic-{fallback_order + 1}"
        try:
            expected_duration = max(0, min(600, int(raw.get("expected_duration_min", 0) or 0)))
        except Exception:
            expected_duration = 0
        priority = str(raw.get("priority", "normal") or "normal").strip().lower()
        if priority == "mandatory":
            priority = "high"
        elif priority == "optional":
            priority = "normal"
        if priority not in {"low", "normal", "high"}:
            priority = "normal"
        comments = str(raw.get("comments", "") or "").strip()[:400]
        try:
            order = max(0, min(10_000, int(raw.get("order", fallback_order) or fallback_order)))
        except Exception:
            order = fallback_order
        return {
            "id": safe_id,
            "name": name,
            "expected_duration_min": expected_duration,
            "priority": priority,
            "comments": comments,
            "order": order,
        }

    def _normalize_definitions(
        self,
        definitions: list[dict[str, Any]],
        *,
        fallback_agenda: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        seen_name_keys: set[str] = set()
        seen_ids: set[str] = set()
        for idx, raw in enumerate(definitions):
            item = self._normalize_definition(raw, fallback_order=idx)
            if item is None:
                continue
            name_key = self._normalize_name(item["name"])
            if not name_key or name_key in seen_name_keys:
                continue
            candidate_id = str(item.get("id") or f"topic-{idx + 1}")
            if candidate_id in seen_ids:
                suffix = 2
                while f"{candidate_id}-{suffix}" in seen_ids:
                    suffix += 1
                candidate_id = f"{candidate_id}-{suffix}"
            item["id"] = candidate_id
            seen_name_keys.add(name_key)
            seen_ids.add(candidate_id)
            normalized.append(item)
        if not normalized and fallback_agenda:
            for idx, raw_name in enumerate(fallback_agenda[:80]):
                name = " ".join(str(raw_name or "").split()).strip()
                if not name:
                    continue
                key = self._normalize_name(name)
                if key in seen_name_keys:
                    continue
                seen_name_keys.add(key)
                normalized.append(
                    {
                        "id": f"topic-{idx + 1}",
                        "name": name,
                        "expected_duration_min": 0,
                        "priority": "normal",
                        "comments": "",
                        "order": idx,
                    }
                )
        normalized.sort(
            key=lambda row: (
                int(row.get("order", 0) or 0),
                self._normalize_name(str(row.get("name", ""))),
            )
        )
        for idx, row in enumerate(normalized):
            row["order"] = idx
        return normalized[:80]

    def _agenda_from_definitions_unlocked(self) -> list[str]:
        agenda_names: list[str] = []
        seen: set[str] = set()
        for row in sorted(
            self.topics_definitions,
            key=lambda item: (
                int(item.get("order", 0) or 0),
                self._normalize_name(item.get("name", "")),
            ),
        ):
            name = " ".join(str(row.get("name", "") or "").split()).strip()
            if not name:
                continue
            key = self._normalize_name(name)
            if key in seen:
                continue
            seen.add(key)
            agenda_names.append(name)
            if len(agenda_names) >= 20:
                break
        return agenda_names

    @staticmethod
    def _latest_statement_ts(statements: list[Any]) -> float:
        latest = 0.0
        for row in statements:
            if not isinstance(row, dict):
                continue
            try:
                ts = float(row.get("ts", 0) or 0)
            except Exception:
                ts = 0.0
            if ts > latest:
                latest = ts
        return latest

    def _with_derived_fields_unlocked(
        self, items: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        agenda_keys = {self._normalize_name(name) for name in self.topics_agenda}
        out: list[dict[str, Any]] = []
        for raw in items:
            if not isinstance(raw, dict):
                continue
            item = dict(raw)
            name = " ".join(str(item.get("name", "") or "").split()).strip()
            if not name:
                continue
            statements = list(item.get("key_statements", []) or [])
            latest_statement_ts = self._latest_statement_ts(statements)
            try:
                updated_ts = float(item.get("updated_ts", 0) or 0)
            except Exception:
                updated_ts = 0.0
            origin = str(item.get("origin", "") or "").strip().lower()
            if origin not in {"agenda", "custom"}:
                origin = "agenda" if self._normalize_name(name) in agenda_keys else "custom"
            latest_activity_ts = float(item.get("latest_activity_ts", 0) or 0)
            if latest_activity_ts <= 0:
                latest_activity_ts = latest_statement_ts if latest_statement_ts > 0 else updated_ts
            try:
                statement_count = int(item.get("statement_count", len(statements)) or len(statements))
            except Exception:
                statement_count = len(statements)
            item["name"] = name
            item["origin"] = origin
            item["latest_activity_ts"] = latest_activity_ts
            item["statement_count"] = statement_count
            out.append(item)
        return out

    def _build_recent_context_unlocked(self) -> dict[str, Any] | None:
        active_candidates: list[dict[str, Any]] = []
        for raw in self.topics_items:
            if not isinstance(raw, dict):
                continue
            status = str(raw.get("status", "not_started") or "not_started").strip().lower()
            if status != "active":
                continue
            topic_name = " ".join(str(raw.get("name", "") or "").split()).strip()
            if not topic_name:
                continue
            topic_key = self._normalize_name(topic_name)
            statements = list(raw.get("key_statements", []) or [])
            latest_statement_ts = self._latest_statement_ts(statements)
            try:
                updated_ts = float(raw.get("updated_ts", 0) or 0)
            except Exception:
                updated_ts = 0.0
            latest_activity_ts = max(latest_statement_ts, updated_ts)
            scope = ""
            for row in self.topics_definitions:
                if not isinstance(row, dict):
                    continue
                if self._normalize_name(str(row.get("name", "") or "")) != topic_key:
                    continue
                scope = " ".join(str(row.get("comments", "") or "").split()).strip()
                break
            if not scope:
                scope = self._normalize_comments(raw.get("comments", ""))
            last_statements: list[str] = []
            statements_sorted = sorted(
                [row for row in statements if isinstance(row, dict)],
                key=lambda row: float(row.get("ts", 0) or 0),
                reverse=True,
            )
            for row in statements_sorted[:6]:
                text = " ".join(str(row.get("text", "") or "").split()).strip()
                if text:
                    last_statements.append(text)
            active_candidates.append(
                {
                    "topic": topic_name,
                    "scope": scope,
                    "last_statements": last_statements,
                    "latest_activity_ts": latest_activity_ts,
                }
            )
        if not active_candidates:
            return None
        active_candidates.sort(
            key=lambda row: float(row.get("latest_activity_ts", 0) or 0),
            reverse=True,
        )
        top_active = active_candidates[:3]
        most_recent = top_active[0]
        active_topics = [
            {
                "topic": str(row.get("topic", "") or ""),
                "scope": str(row.get("scope", "") or ""),
                "last_statements": list(row.get("last_statements", []) or []),
            }
            for row in top_active
            if str(row.get("topic", "") or "").strip()
        ]
        return {
            "active_topic": str(most_recent.get("topic", "") or ""),
            "scope": str(most_recent.get("scope", "") or ""),
            "last_statements": list(most_recent.get("last_statements", []) or []),
            "active_topics": active_topics,
        }

    def payload_unlocked(self) -> dict[str, Any]:
        return {
            "configured": self._topic_tracker.is_configured,
            "settings_saved": bool(self.topics_settings_saved),
            "enabled": self.topics_enabled,
            "allow_new_topics": self.topics_allow_new,
            "interval_sec": self.topics_interval_sec,
            "pending": self.topics_pending,
            "last_run_ts": self.topics_last_run_ts,
            "last_final_index": self.topics_last_final_idx,
            "last_error": self.topics_last_error,
            "agenda": list(self.topics_agenda),
            "definitions": [dict(row) for row in self.topics_definitions],
            "items": self._with_derived_fields_unlocked(self.topics_items),
            "runs": list(self.topics_runs),
        }

    def _append_run_unlocked(self, run: dict[str, Any]) -> None:
        self.topics_runs.append(run)
        if len(self.topics_runs) > 160:
            self.topics_runs = self.topics_runs[-160:]

    def _meta_unlocked(self, key: str) -> dict[str, int]:
        row = self.topics_runtime_meta.get(key)
        if isinstance(row, dict):
            return row
        row = {"absent_runs": 0, "absent_seconds": 0}
        self.topics_runtime_meta[key] = row
        return row

    def _reset_items_unlocked(self) -> None:
        now_ts = time.time()
        self.topics_items = [
            {
                "name": name,
                "status": "not_started",
                "time_seconds": 0,
                "comments": "",
                "key_statements": [],
                "updated_ts": now_ts,
            }
            for name in self.topics_agenda
        ]

    def _context_items_unlocked(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for raw in self.topics_items:
            if not isinstance(raw, dict):
                continue
            name = " ".join(str(raw.get("name", "") or "").split()).strip()
            if not name:
                continue
            status = self._normalize_status(raw.get("status"), default="not_started")
            try:
                time_seconds = max(0, int(raw.get("time_seconds", 0) or 0))
            except Exception:
                time_seconds = 0
            statements = list(raw.get("key_statements", []) or [])
            latest_statement_ts = self._latest_statement_ts(statements)
            try:
                updated_ts = float(raw.get("updated_ts", 0) or 0)
            except Exception:
                updated_ts = 0.0
            latest_activity_ts = max(latest_statement_ts, updated_ts)
            comments = self._normalize_comments(raw.get("comments", ""))
            out.append(
                {
                    "name": name,
                    "comments": comments,
                    "status": status,
                    "time_seconds": time_seconds,
                    "statement_count": len(statements),
                    "latest_activity_ts": latest_activity_ts,
                }
            )
        return out[:40]

    @staticmethod
    def _filter_statements_to_chunk(
        rows: list[dict[str, Any]],
        *,
        chunk_min_ts: float,
        chunk_max_ts: float,
    ) -> list[dict[str, Any]]:
        if chunk_min_ts <= 0 or chunk_max_ts <= 0 or chunk_max_ts < chunk_min_ts:
            return []
        out: list[dict[str, Any]] = []
        min_ts = chunk_min_ts - 1.0
        max_ts = chunk_max_ts + 1.0
        for row in rows:
            if not isinstance(row, dict):
                continue
            text = " ".join(str(row.get("text", "") or "").split()).strip()
            if not text:
                continue
            try:
                ts = float(row.get("ts", 0) or 0)
            except Exception:
                ts = 0.0
            if ts <= 0 or ts < min_ts or ts > max_ts:
                continue
            speaker = (
                " ".join(str(row.get("speaker", "Speaker") or "Speaker").split()).strip()
                or "Speaker"
            )
            out.append({"ts": ts, "speaker": speaker, "text": text})
        return out

    @staticmethod
    def _statement_signature(
        rows: list[dict[str, Any]],
    ) -> tuple[tuple[Any, ...], ...]:
        sig: list[tuple[Any, ...]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            text = " ".join(str(row.get("text", "") or "").split()).strip().lower()
            if not text:
                continue
            speaker = (
                " ".join(str(row.get("speaker", "Speaker") or "Speaker").split())
                .strip()
                .lower()
            )
            try:
                ts = round(float(row.get("ts", 0) or 0), 3)
            except Exception:
                ts = 0.0
            sig.append((ts, speaker, text))
        return tuple(sig)

    @staticmethod
    def _merge_statements(
        existing_rows: list[dict[str, Any]],
        incoming_rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in list(existing_rows or []) + list(incoming_rows or []):
            if not isinstance(row, dict):
                continue
            text = " ".join(str(row.get("text", "") or "").split()).strip()
            if not text:
                continue
            speaker = (
                " ".join(str(row.get("speaker", "Speaker") or "Speaker").split()).strip()
                or "Speaker"
            )
            try:
                ts = float(row.get("ts", 0) or 0)
            except Exception:
                ts = 0.0
            key = f"{speaker}:{text.lower()}"
            if key in seen:
                continue
            seen.add(key)
            merged.append({"ts": ts, "speaker": speaker, "text": text})
        merged.sort(key=lambda item: float(item.get("ts", 0) or 0), reverse=True)
        return merged[:20]

    def _normalize_item(self, item: dict[str, Any], now_ts: float) -> dict[str, Any] | None:
        name = " ".join(str(item.get("name", "") or "").split()).strip()
        if not name:
            return None
        suggested_name = " ".join(str(item.get("suggested_name", "") or "").split()).strip()
        if suggested_name and not self._is_usable_new_name(suggested_name):
            suggested_name = ""
        comments = self._normalize_comments(
            item.get("short_description", item.get("comments", ""))
        )
        status = self._normalize_status(item.get("status"), default="active")
        try:
            match_confidence = float(item.get("match_confidence", 1.0) or 0.0)
        except Exception:
            match_confidence = 0.0
        if math.isnan(match_confidence) or math.isinf(match_confidence):
            match_confidence = 0.0
        match_confidence = max(0.0, min(1.0, match_confidence))
        statements: list[dict[str, Any]] = []
        for row in list(item.get("key_statements", []) or [])[:20]:
            if not isinstance(row, dict):
                continue
            text = " ".join(str(row.get("text", "") or "").split()).strip()
            if not text:
                continue
            try:
                ts = float(row.get("ts", now_ts) or now_ts)
            except Exception:
                ts = now_ts
            speaker = (
                " ".join(str(row.get("speaker", "Speaker") or "Speaker").split()).strip()
                or "Speaker"
            )
            statements.append({"ts": ts, "speaker": speaker, "text": text})
        raw_presence = item.get("topic_presence", None)
        if isinstance(raw_presence, bool):
            topic_presence = raw_presence
        elif raw_presence is None:
            topic_presence = bool(statements) or status in {"active", "covered"}
        else:
            topic_presence = str(raw_presence).strip().lower() in {"1", "true", "yes", "y", "on"}
        out = {
            "name": name,
            "status": status,
            "topic_presence": topic_presence,
            "match_confidence": match_confidence,
            "key_statements": statements,
            "updated_ts": now_ts,
        }
        if suggested_name:
            out["suggested_name"] = suggested_name
        if comments:
            out["comments"] = comments
        return out

    def _trace_summary(self, topic_call: dict[str, Any]) -> str:
        turns = list(topic_call.get("chunk_turns", []) or [])
        latest = turns[-1] if turns else {}
        latest_text = (
            str(latest.get("en", "") or "").strip()
            or str(latest.get("ar", "") or "").strip()
        )
        latest_speaker = str(latest.get("speaker", "-") or "-")
        recent = topic_call.get("recent_context", {}) or {}
        recent_topic = str(recent.get("active_topic", "") or "").strip()
        return (
            f"trigger={str(topic_call.get('trigger', 'manual'))}, "
            f"agenda={len(list(topic_call.get('agenda', []) or []))}, "
            f"current_topics={len(list(topic_call.get('current_topics', []) or []))}, "
            f"chunk_turns={len(turns)}, "
            f"chunk_seconds={int(topic_call.get('chunk_seconds', 0) or 0)}, "
            f"chunk_active_seconds={int(topic_call.get('chunk_active_seconds', 0) or 0)}, "
            f"from_idx={int(topic_call.get('from_final_index', 0) or 0)}, "
            f"to_idx={int(topic_call.get('to_final_index', 0) or 0)}, "
            f"gap_seconds={int(topic_call.get('gap_seconds', 0) or 0)}, "
            f"possible_context_reset={bool(topic_call.get('possible_context_reset', False))}, "
            f"recent_topic={recent_topic or '-'}, "
            f"allow_new={bool(topic_call.get('allow_new_topics', True))}, "
            f"latest_speaker={latest_speaker}, "
            f"latest_preview={self._preview_text(latest_text, 120) if latest_text else '-'}"
        )

    def _agent_input_from_call(self, topic_call: dict[str, Any]) -> dict[str, Any]:
        agenda: list[str] = []
        for raw_name in list(topic_call.get("agenda", []) or []):
            name = " ".join(str(raw_name or "").split()).strip()
            if name:
                agenda.append(name)

        definitions: list[dict[str, Any]] = []
        for raw in list(topic_call.get("definitions", []) or []):
            if not isinstance(raw, dict):
                continue
            name = " ".join(str(raw.get("name", "") or "").split()).strip()
            if not name:
                continue
            definition = {"name": name}
            comments = self._normalize_comments(raw.get("comments", ""), max_chars=400)
            if comments:
                definition["comments"] = comments
            definitions.append(definition)

        current_topics: list[dict[str, Any]] = []
        for raw in list(topic_call.get("current_topics", []) or []):
            if not isinstance(raw, dict):
                continue
            name = " ".join(str(raw.get("name", "") or "").split()).strip()
            if not name:
                continue
            status = self._normalize_status(raw.get("status"), default="not_started")
            topic_row = {"name": name, "status": status}
            comments = self._normalize_comments(raw.get("comments", ""), max_chars=160)
            if comments:
                topic_row["comments"] = comments
            current_topics.append(topic_row)

        chunk_turns: list[dict[str, Any]] = []
        for raw in list(topic_call.get("chunk_turns", []) or []):
            if not isinstance(raw, dict):
                continue
            text = str(raw.get("en", "") or "")
            try:
                ts = float(raw.get("ts", 0) or 0)
            except Exception:
                ts = 0.0
            speaker = (
                " ".join(str(raw.get("speaker", "Speaker") or "Speaker").split()).strip()
                or "Speaker"
            )
            chunk_turns.append({"ts": ts, "speaker": speaker, "en": text})

        payload: dict[str, Any] = {
            "agenda": agenda,
            "definitions": definitions,
            "allow_new_topics": bool(topic_call.get("allow_new_topics", True)),
            "current_topics": current_topics,
            "chunk_turns": chunk_turns,
            "possible_context_reset": bool(topic_call.get("possible_context_reset", False)),
        }
        recent_context = topic_call.get("recent_context")
        if isinstance(recent_context, dict) and recent_context:
            payload["recent_context"] = recent_context
        return payload

    # ── Call preparation ──────────────────────────────────────────────────────

    def prepare_call_unlocked(
        self,
        now_ts: float,
        *,
        trigger: Literal["auto", "manual"],
    ) -> dict[str, Any] | None:
        if self.topics_pending:
            return None
        if not self._topic_tracker.is_configured:
            return None
        if not self.topics_settings_saved:
            return None
        if trigger == "auto" and not self.topics_enabled:
            return None
        if not self.topics_allow_new and not self.topics_agenda:
            return None

        finals = self._get_finals()
        from_idx = max(0, min(len(finals), int(self.topics_last_final_idx or 0)))
        turns_source = list(finals[from_idx:])

        chunk_turns = [
            {
                "ts": float(turn.get("ts") or now_ts),
                "start_ts": float(turn.get("start_ts", turn.get("ts") or now_ts) or now_ts),
                "speaker": str(turn.get("speaker_label", "Speaker") or "Speaker"),
                "en": str(turn.get("en", "") or ""),
            }
            for turn in turns_source
        ]
        if not chunk_turns:
            return None

        to_idx = len(finals)
        first_ts = float(chunk_turns[0].get("ts", now_ts) or now_ts)
        first_start_ts = float(chunk_turns[0].get("start_ts", first_ts) or first_ts)
        last_ts = float(chunk_turns[-1].get("ts", now_ts) or now_ts)
        span_start_ts = min(first_ts, first_start_ts)
        prev_boundary_ts = 0.0
        if from_idx > 0:
            prev_idx = min(len(finals) - 1, from_idx - 1)
            if prev_idx >= 0:
                prev_row = finals[prev_idx]
                try:
                    prev_ts = float(prev_row.get("ts", first_ts) or first_ts)
                except Exception:
                    prev_ts = first_ts
                if prev_ts > 0:
                    prev_boundary_ts = prev_ts
                if prev_ts > 0:
                    span_start_ts = min(first_ts, prev_ts)
        # First agent run of this session: clamp span to session start.
        # Handles both a brand-new session (from_idx==0) and a restart where
        # the transcript was kept (from_idx>0, prev finals from old session).
        if (
            self.topics_session_started_ts > 0
            and self.topics_last_run_ts < self.topics_session_started_ts
        ):
            span_start_ts = min(first_ts, self.topics_session_started_ts)
        chunk_delta = max(0.0, float(last_ts - span_start_ts))
        chunk_seconds = max(0, int(chunk_delta))
        active_delta = 0.0
        for row in chunk_turns:
            try:
                turn_ts = float(row.get("ts", 0) or 0)
            except Exception:
                turn_ts = 0.0
            try:
                turn_start_ts = float(row.get("start_ts", turn_ts) or turn_ts)
            except Exception:
                turn_start_ts = turn_ts
            if turn_ts <= 0:
                continue
            active_delta += max(0.0, turn_ts - min(turn_start_ts, turn_ts))
        chunk_active_seconds = max(0, int(active_delta))
        gap_seconds = 0
        if prev_boundary_ts > 0:
            gap_seconds = max(0, int(first_ts - prev_boundary_ts))
        possible_context_reset = gap_seconds > 45
        recent_context = self._build_recent_context_unlocked()

        self.topics_pending = True
        self.topics_last_run_ts = now_ts
        topic_call = {
            "trigger": trigger,
            "from_final_index": from_idx,
            "to_final_index": to_idx,
            "chunk_seconds": chunk_seconds,
            "chunk_active_seconds": chunk_active_seconds,
            "agenda": list(self.topics_agenda),
            "definitions": [dict(row) for row in self.topics_definitions],
            "allow_new_topics": self.topics_allow_new,
            "current_topics": self._context_items_unlocked(),
            "chunk_turns": chunk_turns,
            "gap_seconds": gap_seconds,
            "possible_context_reset": possible_context_reset,
        }
        if recent_context:
            topic_call["recent_context"] = recent_context
        return topic_call

    # ── Async runner ─────────────────────────────────────────────────────────

    # ── Async runner — phase helpers (called under the shared lock) ──────────────

    def _normalize_results(
        self, items_raw: list[Any], now_ts: float
    ) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for raw in items_raw[:30]:
            if not isinstance(raw, dict):
                continue
            item = self._normalize_item(raw, now_ts)
            if item:
                normalized.append(item)
        return normalized

    def _extract_chunk_ctx_unlocked(
        self, topic_call: dict[str, Any]
    ) -> dict[str, Any]:
        chunk_turns_raw = list(topic_call.get("chunk_turns", []) or [])
        chunk_ts_values: list[float] = []
        for row in chunk_turns_raw:
            if not isinstance(row, dict):
                continue
            try:
                ts = float(row.get("ts", 0) or 0)
            except Exception:
                ts = 0.0
            if ts > 0:
                chunk_ts_values.append(ts)
        return {
            "trigger": str(topic_call.get("trigger", "manual") or "manual"),
            "from_idx": int(topic_call.get("from_final_index", 0) or 0),
            "to_idx": int(topic_call.get("to_final_index", 0) or 0),
            "chunk_turns_raw": chunk_turns_raw,
            "chunk_turns_count": len(chunk_turns_raw),
            "chunk_seconds": int(topic_call.get("chunk_seconds", 0) or 0),
            "chunk_active_seconds": int(topic_call.get("chunk_active_seconds", 0) or 0),
            "gap_seconds": int(topic_call.get("gap_seconds", 0) or 0),
            "possible_context_reset": bool(topic_call.get("possible_context_reset", False)),
            "chunk_min_ts": min(chunk_ts_values) if chunk_ts_values else 0.0,
            "chunk_max_ts": max(chunk_ts_values) if chunk_ts_values else 0.0,
        }

    def _index_existing_unlocked(
        self,
    ) -> tuple[dict[str, dict[str, Any]], list[str], list[str], set[str]]:
        existing_by_key: dict[str, dict[str, Any]] = {}
        ordered_keys: list[str] = []
        for item in self.topics_items:
            if not isinstance(item, dict):
                continue
            key = self._normalize_name(item.get("name", ""))
            if not key:
                continue
            existing_by_key[key] = dict(item)
            ordered_keys.append(key)
        agenda_keys: list[str] = []
        for name in self.topics_agenda:
            key = self._normalize_name(name)
            if not key:
                continue
            if key not in agenda_keys:
                agenda_keys.append(key)
        known_topic_keys: set[str] = set(agenda_keys) | set(existing_by_key.keys())
        return existing_by_key, ordered_keys, agenda_keys, known_topic_keys

    def _resolve_names_unlocked(
        self,
        normalized: list[dict[str, Any]],
        known_topic_keys: set[str],
    ) -> dict[str, dict[str, Any]]:
        normalized_by_key: dict[str, dict[str, Any]] = {}
        for item in normalized:
            incoming = dict(item)
            raw_key = self._normalize_name(incoming.get("name", ""))
            if not raw_key:
                continue
            key = raw_key
            suggested_name = " ".join(
                str(incoming.get("suggested_name", "") or "").split()
            ).strip()
            suggested_key = self._normalize_name(suggested_name) if suggested_name else ""
            if suggested_key:
                if suggested_key in known_topic_keys:
                    key = suggested_key
                elif raw_key not in known_topic_keys:
                    key = suggested_key
                    incoming["name"] = suggested_name
            normalized_by_key[key] = incoming
        return normalized_by_key

    def _build_baseline_unlocked(
        self,
        agenda_keys: list[str],
        ordered_keys: list[str],
        existing_by_key: dict[str, dict[str, Any]],
        now_ts: float,
    ) -> tuple[dict[str, dict[str, Any]], list[str]]:
        merged_by_key: dict[str, dict[str, Any]] = {}
        final_order: list[str] = []
        for key in agenda_keys:
            existing = existing_by_key.get(key)
            if existing:
                merged_by_key[key] = dict(existing)
            else:
                agenda_name = next(
                    (
                        name
                        for name in self.topics_agenda
                        if self._normalize_name(name) == key
                    ),
                    key.title(),
                )
                merged_by_key[key] = {
                    "name": agenda_name,
                    "status": "not_started",
                    "time_seconds": 0,
                    "comments": "",
                    "key_statements": [],
                    "updated_ts": now_ts,
                }
            final_order.append(key)
        for key in ordered_keys:
            if key in merged_by_key:
                continue
            merged_by_key[key] = dict(existing_by_key[key])
            final_order.append(key)
        return merged_by_key, final_order

    def _classify_incoming_unlocked(
        self,
        normalized_by_key: dict[str, dict[str, Any]],
        known_topic_keys: set[str],
        chunk_min_ts: float,
        chunk_max_ts: float,
        confidence_threshold: float,
    ) -> tuple[dict[str, dict[str, Any]], list[str], int, int, int]:
        incoming_meta: dict[str, dict[str, Any]] = {}
        participant_keys: list[str] = []
        dropped_low_confidence = 0
        dropped_custom_disabled = 0
        dropped_invalid_name = 0
        for key, incoming in normalized_by_key.items():
            incoming_statements_raw = list(incoming.get("key_statements", []) or [])
            incoming_statements = self._filter_statements_to_chunk(
                incoming_statements_raw,
                chunk_min_ts=chunk_min_ts,
                chunk_max_ts=chunk_max_ts,
            )
            incoming_has_new_detail = bool(incoming_statements)
            incoming_presence = bool(incoming.get("topic_presence", False))
            try:
                incoming_confidence = float(incoming.get("match_confidence", 1.0) or 0.0)
            except Exception:
                incoming_confidence = 0.0
            incoming_confidence = max(0.0, min(1.0, incoming_confidence))
            incoming_status = self._normalize_status(incoming.get("status"), default="active")
            if (incoming_has_new_detail or incoming_presence) and incoming_status == "not_started":
                incoming_status = "active"
            incoming_name = str(incoming.get("name", "Topic") or "Topic")
            incoming_comments = self._normalize_comments(
                incoming.get("comments", incoming.get("short_description", ""))
            )
            is_known_topic = key in known_topic_keys
            usable_new_name = self._is_usable_new_name(incoming_name)
            allow_assignment = True
            create_new_candidate = False
            if incoming_confidence < confidence_threshold:
                if self.topics_allow_new and (not is_known_topic) and usable_new_name:
                    create_new_candidate = True
                else:
                    allow_assignment = False
                    dropped_low_confidence += 1
            elif not is_known_topic:
                if not self.topics_allow_new:
                    allow_assignment = False
                    dropped_custom_disabled += 1
                elif not usable_new_name:
                    allow_assignment = False
                    dropped_invalid_name += 1
                else:
                    create_new_candidate = True
            is_participant = allow_assignment and incoming_presence
            incoming_meta[key] = {
                "incoming": incoming,
                "incoming_statements": incoming_statements,
                "incoming_has_new_detail": incoming_has_new_detail,
                "incoming_presence": incoming_presence,
                "incoming_confidence": incoming_confidence,
                "incoming_status": incoming_status,
                "incoming_comments": incoming_comments,
                "allow_assignment": allow_assignment,
                "create_new_candidate": create_new_candidate,
                "is_participant": is_participant,
            }
            if is_participant:
                participant_keys.append(key)
        return incoming_meta, participant_keys, dropped_low_confidence, dropped_custom_disabled, dropped_invalid_name

    def _allocate_time_unlocked(
        self,
        participant_keys: list[str],
        incoming_meta: dict[str, dict[str, Any]],
        chunk_turns_raw: list[Any],
        chunk_seconds: int,
        chunk_active_seconds: int,
        dropped_low_confidence: int,
        dropped_custom_disabled: int,
        dropped_invalid_name: int,
    ) -> tuple[dict[str, int], str, int]:
        allocated_seconds_by_key: dict[str, int] = {}
        allocatable_seconds = max(0, int(chunk_seconds))
        if allocatable_seconds <= 0:
            allocatable_seconds = max(0, int(chunk_active_seconds))
        if allocatable_seconds > 0 and participant_keys:
            turn_duration_by_ts: dict[float, float] = {}
            for row in chunk_turns_raw:
                if not isinstance(row, dict):
                    continue
                try:
                    turn_ts = float(row.get("ts", 0) or 0)
                except Exception:
                    turn_ts = 0.0
                try:
                    turn_start_ts = float(row.get("start_ts", turn_ts) or turn_ts)
                except Exception:
                    turn_start_ts = turn_ts
                if turn_ts <= 0:
                    continue
                turn_duration = max(0.0, turn_ts - min(turn_start_ts, turn_ts))
                ts_key = round(turn_ts, 3)
                prev_dur = float(turn_duration_by_ts.get(ts_key, 0.0) or 0.0)
                if turn_duration > prev_dur:
                    turn_duration_by_ts[ts_key] = turn_duration
            weights: dict[str, float] = {}
            for key in participant_keys:
                meta = incoming_meta.get(key) or {}
                weight = 0.0
                seen_ts_keys: set[float] = set()
                for row in list(meta.get("incoming_statements", []) or []):
                    if not isinstance(row, dict):
                        continue
                    try:
                        ts = float(row.get("ts", 0) or 0)
                    except Exception:
                        ts = 0.0
                    if ts <= 0:
                        continue
                    ts_key = round(ts, 3)
                    if ts_key in seen_ts_keys:
                        continue
                    seen_ts_keys.add(ts_key)
                    weight += float(turn_duration_by_ts.get(ts_key, 0.0) or 0.0)
                if weight <= 0.0 and bool(meta.get("incoming_presence", False)):
                    weight = 1.0
                weights[key] = max(0.0, weight)
            total_weight = sum(weights.values())
            if total_weight > 0:
                base_alloc: dict[str, int] = {}
                fractions: list[tuple[float, str]] = []
                allocated_floor = 0
                for key in participant_keys:
                    share = (allocatable_seconds * weights.get(key, 0.0)) / total_weight
                    base = int(math.floor(share))
                    base_alloc[key] = base
                    allocated_floor += base
                    fractions.append((share - base, key))
                remainder = max(0, allocatable_seconds - allocated_floor)
                fractions.sort(key=lambda row: (row[0], row[1]), reverse=True)
                for idx in range(remainder):
                    pick_key = fractions[idx % len(fractions)][1]
                    base_alloc[pick_key] = int(base_alloc.get(pick_key, 0) or 0) + 1
                allocated_seconds_by_key = base_alloc
                allocation_basis = "topic_presence_weighted"
            else:
                base_share = allocatable_seconds // len(participant_keys)
                remainder = allocatable_seconds % len(participant_keys)
                for idx, key in enumerate(participant_keys):
                    allocated_seconds_by_key[key] = base_share + (1 if idx < remainder else 0)
                allocation_basis = "topic_presence_equal"
        elif participant_keys:
            allocation_basis = "topic_presence_zero_active"
        elif dropped_low_confidence > 0:
            allocation_basis = "unassigned_low_confidence"
        elif dropped_custom_disabled > 0:
            allocation_basis = "unassigned_custom_disabled"
        elif dropped_invalid_name > 0:
            allocation_basis = "unassigned_invalid_name"
        else:
            allocation_basis = "unassigned_no_presence"
        allocated_total = sum(allocated_seconds_by_key.values())
        unassigned_seconds = max(0, int(allocatable_seconds - allocated_total))
        return allocated_seconds_by_key, allocation_basis, unassigned_seconds

    def _apply_merge_unlocked(
        self,
        normalized_by_key: dict[str, dict[str, Any]],
        merged_by_key: dict[str, dict[str, Any]],
        final_order: list[str],
        incoming_meta: dict[str, dict[str, Any]],
        allocated_seconds_by_key: dict[str, int],
        confidence_threshold: float,
        now_ts: float,
        status_rank: dict[str, int],
    ) -> tuple[int, int, int, list[dict[str, Any]], set[str], set[str]]:
        new_topics = 0
        updated_topics = 0
        unchanged_topics = 0
        transitions: list[dict[str, Any]] = []
        updated_keys: set[str] = set()
        unchanged_keys: set[str] = set()
        for key, incoming in normalized_by_key.items():
            meta = incoming_meta.get(key) or {}
            existing = merged_by_key.get(key)
            incoming_statements = list(meta.get("incoming_statements", []) or [])
            incoming_has_new_detail = bool(meta.get("incoming_has_new_detail", False))
            incoming_presence = bool(meta.get("incoming_presence", False))
            incoming_status = str(meta.get("incoming_status", "active") or "active")
            incoming_confidence = float(meta.get("incoming_confidence", 0.0) or 0.0)
            incoming_comments = self._normalize_comments(meta.get("incoming_comments", ""))
            allow_assignment = bool(meta.get("allow_assignment", False))
            create_new_candidate = bool(meta.get("create_new_candidate", False))
            allocated_seconds = max(0, int(allocated_seconds_by_key.get(key, 0) or 0))
            if not allow_assignment:
                continue
            if existing is None:
                if not self.topics_allow_new or not create_new_candidate:
                    continue
                if not incoming_presence and not incoming_has_new_detail:
                    continue
                merged_by_key[key] = {
                    "name": str(incoming.get("name", "Topic") or "Topic"),
                    "status": incoming_status,
                    "time_seconds": allocated_seconds,
                    "comments": incoming_comments,
                    "key_statements": incoming_statements[:20],
                    "updated_ts": now_ts,
                }
                final_order.append(key)
                new_topics += 1
                transitions.append(
                    {
                        "topic": str(incoming.get("name", "Topic") or "Topic"),
                        "from": "none",
                        "to": incoming_status,
                        "reason": "new_topic",
                    }
                )
                continue
            prev_time = max(0, int(existing.get("time_seconds", 0) or 0))
            prev_status = self._normalize_status(existing.get("status"), default="not_started")
            try:
                prev_updated_ts = float(existing.get("updated_ts", now_ts) or now_ts)
            except Exception:
                prev_updated_ts = now_ts
            next_time = prev_time + allocated_seconds if allocated_seconds > 0 else prev_time
            status_reason = ""
            if (
                prev_status == "covered"
                and incoming_presence
                and incoming_confidence >= confidence_threshold
            ):
                next_status = "active"
                status_reason = "reopened"
            else:
                next_status = incoming_status
                if status_rank.get(prev_status, 0) > status_rank.get(next_status, 0):
                    next_status = prev_status
                elif prev_status != "covered" and next_status == "covered":
                    status_reason = "explicit_close"
                elif prev_status == "not_started" and next_status == "active":
                    status_reason = "presence_match"
            prev_statements = list(existing.get("key_statements", []) or [])
            next_statements = self._merge_statements(prev_statements, incoming_statements)
            statements_changed = (
                self._statement_signature(prev_statements)
                != self._statement_signature(next_statements)
            )
            changed = (
                next_time != prev_time
                or next_status != prev_status
                or statements_changed
            )
            next_updated_ts = now_ts if changed else prev_updated_ts
            merged_by_key[key] = {
                "name": str(
                    existing.get("name", incoming.get("name", "Topic"))
                    or incoming.get("name", "Topic")
                ),
                "status": next_status,
                "time_seconds": next_time,
                "comments": self._normalize_comments(existing.get("comments", "")),
                "key_statements": next_statements,
                "updated_ts": next_updated_ts,
            }
            if prev_status != next_status:
                transitions.append(
                    {
                        "topic": str(
                            existing.get("name", incoming.get("name", "Topic"))
                            or incoming.get("name", "Topic")
                        ),
                        "from": prev_status,
                        "to": next_status,
                        "reason": status_reason or "status_update",
                    }
                )
            if changed:
                updated_topics += 1
                updated_keys.add(key)
            else:
                unchanged_topics += 1
                unchanged_keys.add(key)
        return new_topics, updated_topics, unchanged_topics, transitions, updated_keys, unchanged_keys

    def _apply_auto_cover_unlocked(
        self,
        merged_by_key: dict[str, dict[str, Any]],
        participant_keys: list[str],
        incoming_meta: dict[str, dict[str, Any]],
        chunk_seconds: int,
        confidence_threshold: float,
        now_ts: float,
        transitions: list[dict[str, Any]],
        updated_keys: set[str],
        unchanged_keys: set[str],
        updated_topics: int,
        unchanged_topics: int,
    ) -> tuple[int, int]:
        participant_key_set = set(participant_keys)
        auto_cover_runs_threshold = 5
        auto_cover_seconds_threshold = 180
        for key, item in merged_by_key.items():
            if not isinstance(item, dict):
                continue
            item_name = str(item.get("name", "Topic") or "Topic")
            item_status = self._normalize_status(item.get("status"), default="not_started")
            meta_row = self._meta_unlocked(key)
            if key in participant_key_set:
                meta_row["absent_runs"] = 0
                meta_row["absent_seconds"] = 0
                continue
            if item_status != "active":
                continue
            meta_row["absent_runs"] = int(meta_row.get("absent_runs", 0) or 0) + 1
            meta_row["absent_seconds"] = int(
                meta_row.get("absent_seconds", 0) or 0
            ) + max(0, int(chunk_seconds))
            incoming_for_key = incoming_meta.get(key) or {}
            topic_confidence = float(
                incoming_for_key.get("incoming_confidence", 0.0) or 0.0
            )
            other_active_present = any(p_key != key for p_key in participant_key_set)
            can_auto_cover = (
                len(merged_by_key) > 1
                and other_active_present
                and meta_row["absent_runs"] >= auto_cover_runs_threshold
                and meta_row["absent_seconds"] > auto_cover_seconds_threshold
                and topic_confidence < confidence_threshold
            )
            if not can_auto_cover:
                continue
            item["status"] = "covered"
            item["updated_ts"] = now_ts
            meta_row["absent_runs"] = 0
            meta_row["absent_seconds"] = 0
            if key in unchanged_keys:
                unchanged_keys.remove(key)
                unchanged_topics = max(0, unchanged_topics - 1)
            if key not in updated_keys:
                updated_keys.add(key)
                updated_topics += 1
            transitions.append(
                {
                    "topic": item_name,
                    "from": "active",
                    "to": "covered",
                    "reason": "inactive_runs",
                }
            )
        return updated_topics, unchanged_topics

    def _finalize_merged_state_unlocked(
        self,
        merged_by_key: dict[str, dict[str, Any]],
        final_order: list[str],
    ) -> None:
        ordered: list[dict[str, Any]] = []
        seen_keys: set[str] = set()
        for key in final_order:
            if key in seen_keys:
                continue
            seen_keys.add(key)
            item = merged_by_key.get(key)
            if not isinstance(item, dict):
                continue
            ordered.append(item)
        self.topics_items = ordered[:40]
        next_meta: dict[str, dict[str, int]] = {}
        for item in self.topics_items:
            if not isinstance(item, dict):
                continue
            key = self._normalize_name(str(item.get("name", "") or ""))
            if not key:
                continue
            prev_meta = self.topics_runtime_meta.get(key) or {
                "absent_runs": 0,
                "absent_seconds": 0,
            }
            next_meta[key] = {
                "absent_runs": max(0, int(prev_meta.get("absent_runs", 0) or 0)),
                "absent_seconds": max(0, int(prev_meta.get("absent_seconds", 0) or 0)),
            }
        self.topics_runtime_meta = next_meta

    async def run_update(self, topic_call: dict[str, Any]) -> None:
        confidence_threshold = 0.65
        status_rank = {"not_started": 0, "active": 1, "covered": 2}
        transition_rows: list[dict[str, Any]] = []
        try:
            send_ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
            await self._broadcast_log(
                "info",
                f"Topics agent send: send_ts={send_ts}, {self._trace_summary(topic_call)}",
            )
            agent_input = self._agent_input_from_call(topic_call)
            result = await asyncio.to_thread(self._topic_tracker.ask_update, agent_input)
            payload = result.payload if isinstance(result.payload, dict) else {}
            items_raw = list(payload.get("topics", []) or [])
            now_ts = time.time()
            normalized = self._normalize_results(items_raw, now_ts)

            with self._lock:
                ctx = self._extract_chunk_ctx_unlocked(topic_call)
                existing_by_key, ordered_keys, agenda_keys, known_topic_keys = (
                    self._index_existing_unlocked()
                )
                normalized_by_key = self._resolve_names_unlocked(normalized, known_topic_keys)
                merged_by_key, final_order = self._build_baseline_unlocked(
                    agenda_keys, ordered_keys, existing_by_key, now_ts
                )
                (
                    incoming_meta,
                    participant_keys,
                    dropped_low_confidence,
                    dropped_custom_disabled,
                    dropped_invalid_name,
                ) = self._classify_incoming_unlocked(
                    normalized_by_key,
                    known_topic_keys,
                    ctx["chunk_min_ts"],
                    ctx["chunk_max_ts"],
                    confidence_threshold,
                )
                allocated_seconds_by_key, _, _ = (
                    self._allocate_time_unlocked(
                        participant_keys,
                        incoming_meta,
                        ctx["chunk_turns_raw"],
                        ctx["chunk_seconds"],
                        ctx["chunk_active_seconds"],
                        dropped_low_confidence,
                        dropped_custom_disabled,
                        dropped_invalid_name,
                    )
                )
                (
                    new_topics,
                    updated_topics,
                    unchanged_topics,
                    transitions,
                    updated_keys,
                    unchanged_keys,
                ) = self._apply_merge_unlocked(
                    normalized_by_key,
                    merged_by_key,
                    final_order,
                    incoming_meta,
                    allocated_seconds_by_key,
                    confidence_threshold,
                    now_ts,
                    status_rank,
                )
                updated_topics, unchanged_topics = self._apply_auto_cover_unlocked(
                    merged_by_key,
                    participant_keys,
                    incoming_meta,
                    ctx["chunk_seconds"],
                    confidence_threshold,
                    now_ts,
                    transitions,
                    updated_keys,
                    unchanged_keys,
                    updated_topics,
                    unchanged_topics,
                )
                self._finalize_merged_state_unlocked(merged_by_key, final_order)
                self.topics_last_error = ""
                self.topics_pending = False
                self.topics_last_final_idx = max(self.topics_last_final_idx, ctx["to_idx"])
                self._append_run_unlocked(
                    {
                        "ts": now_ts,
                        "trigger": ctx["trigger"],
                        "status": "success",
                        "from_final_index": ctx["from_idx"],
                        "to_final_index": ctx["to_idx"],
                        "chunk_turns": ctx["chunk_turns_count"],
                        "chunk_seconds": ctx["chunk_seconds"],
                        "chunk_active_seconds": ctx["chunk_active_seconds"],
                        "possible_context_reset": ctx["possible_context_reset"],
                        "allow_new_topics": self.topics_allow_new,
                        "new_topics": new_topics,
                        "updated_topics": updated_topics,
                        "unchanged_topics": unchanged_topics,
                        "response_id": result.response_id or "",
                        "conversation_id": result.conversation_id or "",
                        "total_ms": int(result.total_ms or 0),
                    }
                )
                transition_rows = list(transitions)
                out = {"type": "topics_update", "topics": self.payload_unlocked()}
            await self._broadcast(out)
            for row in transition_rows[:16]:
                await self._broadcast_log(
                    "info",
                    (
                        "Topic transition: "
                        f"{str(row.get('topic', 'Topic'))} "
                        f"{str(row.get('from', '-'))} -> {str(row.get('to', '-'))} "
                        f"(reason={str(row.get('reason', 'status_update'))})"
                    ),
                )
            recv_ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
            await self._broadcast_log(
                "info",
                (
                    "Topics agent reply: "
                    f"recv_ts={recv_ts}, total_ms={result.total_ms}, "
                    f"response_id={result.response_id or '-'}, "
                    f"conversation_id={result.conversation_id or '-'}, "
                    f"returned_topics={len(items_raw)}, normalized_topics={len(normalized)}, "
                    f"stored_topics={len(out['topics']['items'])}"
                ),
            )
            await self._broadcast_log(
                "debug",
                (
                    "Topics updated: "
                    f"items={len(out['topics']['items'])}, "
                    f"chunk_turns={len(topic_call.get('chunk_turns', []))}, "
                    f"total_ms={result.total_ms}"
                ),
            )
        except Exception as ex:
            with self._lock:
                ctx = self._extract_chunk_ctx_unlocked(topic_call)
                self.topics_pending = False
                self.topics_last_error = str(ex)
                self._append_run_unlocked(
                    {
                        "ts": time.time(),
                        "trigger": ctx["trigger"],
                        "status": "error",
                        "from_final_index": ctx["from_idx"],
                        "to_final_index": ctx["to_idx"],
                        "chunk_turns": ctx["chunk_turns_count"],
                        "chunk_seconds": ctx["chunk_seconds"],
                        "chunk_active_seconds": ctx["chunk_active_seconds"],
                        "possible_context_reset": ctx["possible_context_reset"],
                        "allow_new_topics": self.topics_allow_new,
                        "new_topics": 0,
                        "updated_topics": 0,
                        "unchanged_topics": 0,
                        "error": str(ex),
                        "response_id": "",
                        "conversation_id": "",
                        "total_ms": 0,
                    }
                )
                out = {"type": "topics_update", "topics": self.payload_unlocked()}
            await self._broadcast(out)
            await self._broadcast_log("error", f"Topics update failed: {ex}")

    @staticmethod
    def _stubs_from_agenda(agenda: list[str]) -> list[dict[str, Any]]:
        return [
            {
                "name": name,
                "expected_duration_min": 0,
                "priority": "normal",
                "comments": "",
                "order": idx,
            }
            for idx, name in enumerate(agenda)
        ]

    # ── Public actions ────────────────────────────────────────────────────────

    def configure(
        self,
        *,
        agenda: list[str],
        enabled: bool,
        allow_new_topics: bool,
        interval_sec: int,
        definitions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        cleaned_agenda: list[str] = []
        seen: set[str] = set()
        for raw in agenda:
            name = " ".join(str(raw or "").split()).strip()
            if not name:
                continue
            key = self._normalize_name(name)
            if key in seen:
                continue
            seen.add(key)
            cleaned_agenda.append(name)
        raw_definitions = None
        if definitions is not None:
            raw_definitions = [row for row in definitions if isinstance(row, dict)]
        with self._lock:
            prev_by_name = {
                self._normalize_name(str(item.get("name", ""))): item
                for item in self.topics_items
                if isinstance(item, dict)
            }
            self.topics_enabled = bool(enabled)
            self.topics_allow_new = bool(allow_new_topics)
            self.topics_interval_sec = max(30, min(300, int(interval_sec)))

            if raw_definitions is not None:
                if raw_definitions:
                    self.topics_definitions = self._normalize_definitions(
                        raw_definitions, fallback_agenda=cleaned_agenda
                    )
                elif cleaned_agenda:
                    self.topics_definitions = self._normalize_definitions(
                        self._stubs_from_agenda(cleaned_agenda),
                        fallback_agenda=cleaned_agenda,
                    )
                else:
                    self.topics_definitions = []
                if cleaned_agenda:
                    self.topics_agenda = cleaned_agenda[:20]
                else:
                    self.topics_agenda = self._agenda_from_definitions_unlocked()
            elif cleaned_agenda:
                self.topics_definitions = self._normalize_definitions(
                    self._stubs_from_agenda(cleaned_agenda),
                    fallback_agenda=cleaned_agenda,
                )
                self.topics_agenda = cleaned_agenda[:20]
            else:
                self.topics_definitions = self._normalize_definitions(
                    [dict(row) for row in self.topics_definitions],
                    fallback_agenda=self.topics_agenda,
                )
                self.topics_agenda = self._agenda_from_definitions_unlocked()

            self.topics_last_error = ""
            self.topics_pending = False
            self.topics_settings_saved = True
            now_ts = time.time()
            rebuilt: list[dict[str, Any]] = []
            for name in self.topics_agenda:
                existing = prev_by_name.get(self._normalize_name(name))
                if existing:
                    rebuilt.append(
                        {
                            "name": name,
                            "status": str(existing.get("status", "not_started") or "not_started"),
                            "time_seconds": int(existing.get("time_seconds", 0) or 0),
                            "comments": self._normalize_comments(existing.get("comments", "")),
                            "key_statements": list(existing.get("key_statements", []) or [])[:20],
                            "updated_ts": now_ts,
                        }
                    )
                else:
                    rebuilt.append(
                        {
                            "name": name,
                            "status": "not_started",
                            "time_seconds": 0,
                            "comments": "",
                            "key_statements": [],
                            "updated_ts": now_ts,
                        }
                    )
            if self.topics_allow_new:
                agenda_keys = {self._normalize_name(name) for name in self.topics_agenda}
                for key, existing in prev_by_name.items():
                    if key in agenda_keys:
                        continue
                    rebuilt.append(
                        {
                            "name": str(existing.get("name", "Topic") or "Topic"),
                            "status": str(existing.get("status", "active") or "active"),
                            "time_seconds": int(existing.get("time_seconds", 0) or 0),
                            "comments": self._normalize_comments(existing.get("comments", "")),
                            "key_statements": list(existing.get("key_statements", []) or [])[:20],
                            "updated_ts": now_ts,
                        }
                    )
            self.topics_items = rebuilt[:40]
            self.topics_runtime_meta = {
                self._normalize_name(str(item.get("name", "") or "")): {
                    "absent_runs": 0,
                    "absent_seconds": 0,
                }
                for item in self.topics_items
                if isinstance(item, dict)
                and self._normalize_name(str(item.get("name", "") or ""))
            }
            return self.payload_unlocked()

    async def analyze_now(self) -> dict[str, Any]:
        with self._lock:
            if self.topics_pending:
                raise RuntimeError("Topic analysis is already running. Please wait and retry.")
            if not self.topics_settings_saved:
                raise RuntimeError("Save topic settings first.")
            if not self.topics_allow_new and not self.topics_agenda:
                raise RuntimeError(
                    "Custom topics are disabled and no definitions exist. "
                    "Add at least one definition or allow custom topics."
                )
            topic_call = self.prepare_call_unlocked(time.time(), trigger="manual")
        if not topic_call:
            raise RuntimeError(
                "No new transcript chunk since the last analysis. Speak more, then retry."
            )
        await self.run_update(topic_call)
        with self._lock:
            return self.payload_unlocked()

    def clear(self, topic_tracker: TopicTrackerService) -> None:
        with self._lock:
            self.topics_pending = False
            self.topics_last_run_ts = 0.0
            self.topics_last_error = ""
            self.topics_last_final_idx = 0
            self.topics_runs = []
            self.topics_runtime_meta = {}
            self._reset_items_unlocked()
        topic_tracker.clear_conversation()

    def finalize_on_stop_unlocked(self) -> None:
        now_ts = time.time()
        for item in self.topics_items:
            if not isinstance(item, dict):
                continue
            status = self._normalize_status(item.get("status"), default="not_started")
            if status != "active":
                continue
            item["status"] = "covered"
            item["updated_ts"] = now_ts
        for key, meta in self.topics_runtime_meta.items():
            if not isinstance(meta, dict):
                continue
            self.topics_runtime_meta[key] = {"absent_runs": 0, "absent_seconds": 0}

    def clear_for_transcript_unlocked(self) -> None:
        """Called from clear_transcript coordinator — resets topic cursor/run state."""
        self.topics_pending = False
        self.topics_last_run_ts = 0.0
        self.topics_last_final_idx = 0
        self.topics_runs = []
        self.topics_runtime_meta = {}
        self._reset_items_unlocked()
