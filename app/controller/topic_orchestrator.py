"""
TopicOrchestrator — definitions-only topic state.

Automatic/manual topic analysis has been removed. The orchestrator now keeps
topic definitions (agenda context) used by summary generation.
"""

import re
import threading
from typing import Any, Awaitable, Callable

BroadcastCallback = Callable[[dict[str, Any]], Awaitable[None]]
BroadcastLogCallback = Callable[[str, str], Awaitable[None]]


class TopicOrchestrator:
    def __init__(
        self,
        lock: threading.RLock,
        broadcast: BroadcastCallback,
        broadcast_log: BroadcastLogCallback,
        get_finals: Callable[[], list[dict[str, Any]]],
        preview_text: Callable[[str], str],
    ) -> None:
        self._lock = lock
        # Kept for constructor compatibility with existing wiring.
        self._broadcast = broadcast
        self._broadcast_log = broadcast_log
        self._get_finals = get_finals
        self._preview_text = preview_text

        self.topics_definitions: list[dict[str, Any]] = []
        self.topics_items: list[dict[str, Any]] = []
        self.topics_agenda: list[str] = []
        self.topics_settings_saved = False

    @property
    def is_tracker_configured(self) -> bool:
        return False

    @staticmethod
    def _normalize_name(value: Any) -> str:
        return " ".join(str(value or "").strip().split()).lower()

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

    def payload_unlocked(self) -> dict[str, Any]:
        # Keep compatibility fields so older clients do not break.
        return {
            "configured": bool(self.topics_settings_saved),
            "settings_saved": bool(self.topics_settings_saved),
            "enabled": False,
            "allow_new_topics": False,
            "interval_sec": 60,
            "pending": False,
            "last_run_ts": 0.0,
            "last_final_index": 0,
            "last_error": "",
            "agenda": list(self.topics_agenda),
            "definitions": [dict(row) for row in self.topics_definitions],
            "items": [dict(row) for row in self.topics_items],
            "runs": [],
        }

    def configure(
        self,
        *,
        agenda: list[str],
        enabled: bool,
        allow_new_topics: bool,
        interval_sec: int,
        definitions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        del enabled, allow_new_topics, interval_sec

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
            if raw_definitions is not None:
                if raw_definitions:
                    self.topics_definitions = self._normalize_definitions(
                        raw_definitions,
                        fallback_agenda=cleaned_agenda,
                    )
                elif cleaned_agenda:
                    self.topics_definitions = self._normalize_definitions(
                        self._stubs_from_agenda(cleaned_agenda),
                        fallback_agenda=cleaned_agenda,
                    )
                else:
                    self.topics_definitions = []
            elif cleaned_agenda:
                self.topics_definitions = self._normalize_definitions(
                    self._stubs_from_agenda(cleaned_agenda),
                    fallback_agenda=cleaned_agenda,
                )
            else:
                self.topics_definitions = self._normalize_definitions(
                    [dict(row) for row in self.topics_definitions],
                    fallback_agenda=self.topics_agenda,
                )

            if cleaned_agenda:
                self.topics_agenda = cleaned_agenda[:20]
            else:
                self.topics_agenda = self._agenda_from_definitions_unlocked()

            # There is no runtime analysis anymore; keep items empty.
            self.topics_items = []
            self.topics_settings_saved = True
            return self.payload_unlocked()

    async def analyze_now(self) -> dict[str, Any]:
        raise RuntimeError("Automatic topic analysis is disabled in definitions-only mode.")

    def prepare_call_unlocked(self, now_ts: float, *, trigger: str) -> None:
        del now_ts, trigger
        return None

    async def run_update(self, topic_call: dict[str, Any] | None) -> None:
        del topic_call
        return None

    def finalize_on_stop_unlocked(self) -> None:
        # No-op in definitions-only mode.
        return None

    def clear(self) -> None:
        with self._lock:
            self.topics_definitions = []
            self.topics_items = []
            self.topics_agenda = []
            self.topics_settings_saved = False

    def clear_for_transcript_unlocked(self) -> None:
        # Transcript clear should not delete topic definitions.
        self.topics_items = []
