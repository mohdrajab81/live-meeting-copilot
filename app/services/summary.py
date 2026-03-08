import json
import os
import re
import threading
import time
from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass
class SummaryResult:
    executive_summary: str
    key_points: list[str]
    action_items: list[dict[str, Any]]
    topic_key_points: list[dict[str, Any]]
    keywords: list[str]
    entities: list[dict[str, Any]]
    decisions_made: list[str]
    risks_and_blockers: list[str]
    key_terms_defined: list[dict[str, Any]]
    metadata: dict[str, Any]
    total_ms: int
    response_id: str | None


_PROMPT_TEMPLATE = """\
You are a meeting intelligence analyst. Analyze the meeting transcript below. \
Timestamps show elapsed time from session start in [MM:SS] format. \
Respond with ONLY a valid JSON object — no markdown, no commentary.

SESSION_DATE:
{session_date_iso}

Schema:
{{
  "metadata": {{
    "meeting_type": "<one of: Interview, Project Management, Training, Executive, General>",
    "sentiment_arc": "<one sentence describing tone progression, or null>"
  }},
  "executive_summary": "<one concise paragraph summarizing the core outcome>",
  "key_points": ["<point 1>", "<point 2>"],
  "topic_key_points": [
    {{
      "topic_name": "<topic title>",
      "utterance_ids": ["<U0001>", "<U0002>"],
      "origin": "<Agenda or Inferred>",
      "key_points": ["<point 1>", "<point 2>"]
    }}
  ],
  "keywords": ["<high-signal keyword or phrase>"],
  "entities": [
    {{
      "type": "<one of: PERSON, ORG, LOCATION, DATE_TIME, PRODUCT, EVENT, MONEY, PERCENT>",
      "text": "<entity text as stated in transcript>",
      "mentions": "<integer count or null>"
    }}
  ],
  "action_items": [
    {{
      "item": "<action>",
      "owner": "<name or role, or null>",
      "due_date_text": "<exact due-date phrase from transcript, or null>",
      "due_date": "<YYYY-MM-DD or null>"
    }}
  ],
  "decisions_made": ["<explicit decision 1>"],
  "risks_and_blockers": ["<explicit risk or blocker 1>"],
  "key_terms_defined": [
    {{"term": "<term>", "definition": "<definition as stated in the transcript>"}}
  ]
}}

Rules:
- Respond with valid JSON only. No prose outside the JSON object.
- key_points: max 10 items, one sentence each.
- topic_key_points:
  - Always return an array (or []).
  - Each item must include topic_name, origin, key_points, and utterance_ids.
  - utterance_ids must come only from transcript markers [id:UXXXX].
  - Use only ids inside VALID_UTTERANCE_ID_RANGES below; never invent, offset, or renumber ids.
  - COVERAGE: every transcript id must appear in exactly one topic's utterance_ids.
  - No skipped ids, no duplicated ids across topics.
  - If an utterance is ambiguous, assign it to the nearest related topic.
- If EXPECTED AGENDA TOPICS are present, map matching content to those names when appropriate, but keep meaningful inferred topics not represented by agenda names.
- keywords: max 20 high-signal terms/phrases; exclude generic filler words.
- entities:
  - max 30 items; allowed types only: PERSON, ORG, LOCATION, DATE_TIME, PRODUCT, EVENT, MONEY, PERCENT.
  - extract only explicit mentions from transcript text (no inferred entities).
  - keep canonical deduplicated forms.
- action_items:
  - due_date_text must copy the exact date phrase from the transcript when present.
  - due_date must be YYYY-MM-DD only when confidently grounded by transcript text.
  - Resolve relative dates like "Friday" or "next Monday" against SESSION_DATE only when unambiguous.
  - If a date is ambiguous, corrupted, or cannot be grounded confidently, set due_date to null.
- action_items, decisions_made, risks_and_blockers, key_terms_defined: include only explicit evidence from transcript; use [] when none.
- metadata.sentiment_arc: one sentence max, or null if too short.

VALID_UTTERANCE_ID_RANGES:
{valid_utterance_id_ranges}

TRANSCRIPT:
{transcript}
"""


class SummaryService:
    def __init__(
        self,
        project_endpoint: str,
        agent_ref: str,
    ) -> None:
        self._project_endpoint = project_endpoint.strip()
        self._agent_ref = agent_ref.strip()
        self._agent_key = "name"
        self._project_client: Any = None
        self._openai_client: Any = None
        self._state_lock = threading.RLock()

    @property
    def is_configured(self) -> bool:
        return bool(self._project_endpoint and self._agent_ref)

    def _ensure_client(self) -> Any:
        with self._state_lock:
            if self._openai_client is not None:
                return self._openai_client
            try:
                from azure.ai.projects import AIProjectClient
                from azure.identity import DefaultAzureCredential
            except Exception as ex:
                raise RuntimeError(
                    "Missing summary dependencies. Install azure-ai-projects and azure-identity."
                ) from ex
            credential = DefaultAzureCredential()
            project_client = AIProjectClient(
                endpoint=self._project_endpoint,
                credential=credential,
            )
            self._project_client = project_client
            self._openai_client = project_client.get_openai_client()
            return self._openai_client

    def _create_new_conversation_id(self, client: Any) -> str | None:
        conversations = getattr(client, "conversations", None)
        create_fn = (
            getattr(conversations, "create", None)
            if conversations is not None
            else None
        )
        if not callable(create_fn):
            return None
        conversation = create_fn()
        conversation_id = getattr(conversation, "id", None) or getattr(
            conversation, "conversation_id", None
        )
        if not conversation_id:
            return None
        return str(conversation_id)

    def generate(
        self,
        transcript_text: str,
        *,
        session_date_iso: str | None = None,
    ) -> SummaryResult:
        if not self.is_configured:
            raise RuntimeError(
                "Summary service is not configured. "
                "Set PROJECT_ENDPOINT and SUMMARY_AGENT_NAME."
            )
        client = self._ensure_client()
        session_date_value = self._normalize_session_date(session_date_iso)
        valid_utterance_id_ranges = self._extract_valid_utterance_id_ranges(
            transcript_text
        )
        prompt = _PROMPT_TEMPLATE.format(
            transcript=transcript_text,
            valid_utterance_id_ranges=valid_utterance_id_ranges,
            session_date_iso=session_date_value,
        )
        request_conversation_id = self._create_new_conversation_id(client)
        total_start = time.perf_counter()
        params: dict[str, Any] = {
            "input": prompt,
            "extra_body": {
                "agent": {
                    self._agent_key: self._agent_ref,
                    "type": "agent_reference",
                }
            },
        }
        if request_conversation_id:
            # Force a fresh conversation per summary run for trace isolation.
            params["conversation"] = request_conversation_id
        response = client.responses.create(**params)
        total_ms = int((time.perf_counter() - total_start) * 1000)
        response_id = getattr(response, "id", None)
        output_text = getattr(response, "output_text", None) or ""
        structured = self._extract_structured(output_text)
        return SummaryResult(
            executive_summary=str(structured.get("executive_summary", "") or ""),
            key_points=[str(p) for p in (structured.get("key_points") or []) if p],
            action_items=self._normalize_action_items(
                structured.get("action_items") or []
            ),
            topic_key_points=self._normalize_topic_key_points(
                structured.get("topic_key_points") or []
            ),
            keywords=self._normalize_keywords(structured.get("keywords") or []),
            entities=self._normalize_entities(structured.get("entities") or []),
            decisions_made=self._normalize_string_list(
                structured.get("decisions_made") or []
            ),
            risks_and_blockers=self._normalize_string_list(
                structured.get("risks_and_blockers") or []
            ),
            key_terms_defined=self._normalize_key_terms(
                structured.get("key_terms_defined") or []
            ),
            metadata=self._normalize_metadata(structured.get("metadata") or {}),
            total_ms=total_ms,
            response_id=response_id,
        )

    def _normalize_session_date(self, raw: str | None) -> str:
        value = " ".join(str(raw or "").split()).strip()
        if not value:
            return "unknown"
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError:
            return "unknown"

    def _extract_valid_utterance_id_ranges(self, transcript_text: str) -> str:
        found = re.findall(r"\[id:(U\d{1,6})\]", str(transcript_text or ""), flags=re.IGNORECASE)
        unique_nums: list[int] = []
        seen_nums: set[int] = set()
        for raw in found:
            uid = str(raw or "").upper()
            try:
                num = int(uid[1:])
            except Exception:
                continue
            if num <= 0 or num in seen_nums:
                continue
            seen_nums.add(num)
            unique_nums.append(num)
        if not unique_nums:
            return "None"
        nums = sorted(unique_nums)
        ranges: list[str] = []
        start = nums[0]
        prev = nums[0]
        for current in nums[1:]:
            if current == prev + 1:
                prev = current
                continue
            if start == prev:
                ranges.append(f"U{start:04d}")
            else:
                ranges.append(f"U{start:04d}-U{prev:04d}")
            start = current
            prev = current
        if start == prev:
            ranges.append(f"U{start:04d}")
        else:
            ranges.append(f"U{start:04d}-U{prev:04d}")
        return ", ".join(ranges)

    def _extract_structured(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()
        # Strip markdown code fences if present
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()
        # Find first {...}
        brace_start = cleaned.find("{")
        brace_end = cleaned.rfind("}")
        if brace_start == -1 or brace_end == -1:
            raise ValueError(
                f"No JSON object found in summary response: {cleaned[:200]!r}"
            )
        json_str = cleaned[brace_start : brace_end + 1]
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as ex:
            raise ValueError(f"Summary response is not valid JSON: {ex}") from ex
        if not isinstance(data, dict):
            raise ValueError("Summary response JSON is not an object.")
        if "executive_summary" not in data:
            raise ValueError(
                "Summary response missing required key 'executive_summary'."
            )
        return data

    def _normalize_action_items(self, items: list[Any]) -> list[dict[str, Any]]:
        result = []
        for item in items:
            if not isinstance(item, dict):
                continue
            action_text = str(item.get("item", "") or "").strip()
            if not action_text:
                continue
            due_date_text = (
                " ".join(str(item.get("due_date_text", "") or "").split()).strip()
                or None
            )
            due_date_raw = str(item.get("due_date", "") or "").strip() or None
            due_date = None
            if due_date_raw and due_date_text:
                try:
                    due_date = date.fromisoformat(due_date_raw).isoformat()
                except ValueError:
                    due_date = None
            result.append(
                {
                    "item": action_text,
                    "owner": str(item.get("owner", "") or "").strip(),
                    "due_date_text": due_date_text,
                    "due_date": due_date,
                }
            )
        return result

    def _normalize_string_list(self, items: list[Any]) -> list[str]:
        result = []
        for item in items:
            text = " ".join(str(item or "").split()).strip()
            if text:
                result.append(text)
        return result

    def _normalize_key_terms(self, items: list[Any]) -> list[dict[str, Any]]:
        result = []
        for item in items:
            if not isinstance(item, dict):
                continue
            term = " ".join(str(item.get("term", "") or "").split()).strip()
            if not term:
                continue
            definition = " ".join(str(item.get("definition", "") or "").split()).strip()
            result.append({"term": term, "definition": definition})
        return result

    def _normalize_metadata(self, raw: Any) -> dict[str, Any]:
        if not isinstance(raw, dict):
            return {"meeting_type": "", "sentiment_arc": None}
        valid_types = {
            "Interview",
            "Project Management",
            "Training",
            "Executive",
            "General",
        }
        meeting_type = str(raw.get("meeting_type", "") or "").strip()
        if meeting_type not in valid_types:
            meeting_type = ""
        sentiment = raw.get("sentiment_arc")
        sentiment_arc = " ".join(str(sentiment or "").split()).strip() or None
        return {"meeting_type": meeting_type, "sentiment_arc": sentiment_arc}

    def _normalize_topic_key_points(self, items: list[Any]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            topic_name = " ".join(str(item.get("topic_name", "") or "").split()).strip()
            if not topic_name:
                continue
            origin = " ".join(str(item.get("origin", "") or "").split()).strip().lower()
            if origin == "agenda":
                origin_value = "Agenda"
            else:
                origin_value = "Inferred"
            key_points = self._normalize_string_list(list(item.get("key_points") or []))
            utterance_ids = self._normalize_utterance_ids(item.get("utterance_ids"))
            result.append(
                {
                    "topic_name": topic_name,
                    # Deterministic-only durations: backend computes this from utterance_ids.
                    "estimated_duration_minutes": None,
                    "utterance_ids": utterance_ids,
                    "origin": origin_value,
                    "key_points": key_points,
                }
            )
        return result

    def _normalize_utterance_ids(self, raw: Any) -> list[str]:
        if isinstance(raw, list):
            source = raw
        elif isinstance(raw, str):
            source = raw.replace(",", " ").split()
        else:
            source = []
        out: list[str] = []
        seen: set[str] = set()
        for item in source:
            uid = " ".join(str(item or "").split()).strip().upper()
            if not uid:
                continue
            if not re.fullmatch(r"U\d{1,6}", uid):
                continue
            if uid in seen:
                continue
            seen.add(uid)
            out.append(uid)
        return out[:500]

    def _normalize_keywords(self, items: list[Any]) -> list[str]:
        blocked = {
            "think",
            "know",
            "really",
            "good",
            "said",
            "like",
            "just",
            "well",
            "yeah",
            "okay",
            "ok",
        }
        out: list[str] = []
        seen: set[str] = set()
        for item in items:
            text = " ".join(str(item or "").split()).strip()
            if not text:
                continue
            key = text.lower()
            if key in seen or key in blocked:
                continue
            if len(key) < 3:
                continue
            seen.add(key)
            out.append(text)
        return out[:20]

    def _normalize_entities(self, items: list[Any]) -> list[dict[str, Any]]:
        allowed_types = {
            "PERSON",
            "ORG",
            "LOCATION",
            "DATE_TIME",
            "PRODUCT",
            "EVENT",
            "MONEY",
            "PERCENT",
        }
        out: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            type_raw = " ".join(str(item.get("type", "") or "").split()).strip().upper()
            if type_raw not in allowed_types:
                continue
            text_raw = " ".join(str(item.get("text", "") or "").split()).strip()
            if not text_raw or len(text_raw) < 2:
                continue
            key = (type_raw, text_raw.lower())
            if key in seen:
                continue
            mentions_raw = item.get("mentions")
            mentions: int | None = None
            if mentions_raw is not None and str(mentions_raw).strip() != "":
                try:
                    mentions = max(1, int(mentions_raw))
                except (TypeError, ValueError):
                    mentions = None
            seen.add(key)
            out.append({"type": type_raw, "text": text_raw, "mentions": mentions})
        return out[:30]

    def close(self) -> None:
        with self._state_lock:
            client = self._openai_client
            project_client = self._project_client
            self._openai_client = None
            self._project_client = None
        if client is not None:
            close_fn = getattr(client, "close", None)
            if callable(close_fn):
                try:
                    close_fn()
                except Exception:
                    pass
        if project_client is not None:
            close_fn = getattr(project_client, "close", None)
            if callable(close_fn):
                try:
                    close_fn()
                except Exception:
                    pass

    @classmethod
    def from_environment(cls) -> "SummaryService":
        project_endpoint = os.getenv("PROJECT_ENDPOINT") or ""
        agent_ref = os.getenv("SUMMARY_AGENT_NAME") or ""
        return cls(
            project_endpoint=project_endpoint,
            agent_ref=agent_ref,
        )

