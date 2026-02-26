import json
import os
import re
import threading
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class SummaryResult:
    executive_summary: str
    key_points: list[str]
    action_items: list[dict[str, Any]]
    total_ms: int
    response_id: str | None


_PROMPT_TEMPLATE = """\
You are a meeting summarizer. Analyze the following interview or meeting transcript and \
respond with ONLY a JSON object — no markdown, no commentary — matching this schema exactly:
{{
  "executive_summary": "<one concise paragraph summarizing what was discussed>",
  "key_points": ["<point 1>", "<point 2>"],
  "action_items": [
    {{"item": "<action description>", "owner": "<name or role>", "due_date": "<YYYY-MM-DD or null>"}}
  ]
}}

Rules:
- key_points: max 10 items, each a single sentence.
- action_items: only include explicit commitments or follow-ups mentioned. Empty array if none.
- Respond with valid JSON only — no surrounding text.

TRANSCRIPT:
{transcript}
"""


class SummaryService:
    def __init__(
        self,
        project_endpoint: str,
        model_deployment: str,
        agent_ref: str,
    ) -> None:
        self._project_endpoint = project_endpoint.strip()
        self._model_deployment = model_deployment.strip()
        self._agent_ref = agent_ref.strip()
        self._agent_key = "id" if self._agent_ref.startswith("asst_") else "name"
        self._project_client: Any = None
        self._openai_client: Any = None
        self._state_lock = threading.RLock()

    @property
    def is_configured(self) -> bool:
        return bool(self._project_endpoint and self._model_deployment and self._agent_ref)

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

    def generate(self, transcript_text: str) -> SummaryResult:
        if not self.is_configured:
            raise RuntimeError(
                "Summary service is not configured. "
                "Set PROJECT_ENDPOINT, MODEL_DEPLOYMENT_NAME, and SUMMARY_AGENT_ID."
            )
        client = self._ensure_client()
        prompt = _PROMPT_TEMPLATE.format(transcript=transcript_text)
        total_start = time.perf_counter()
        response = client.responses.create(
            model=self._model_deployment,
            input=prompt,
            extra_body={
                "agent": {
                    self._agent_key: self._agent_ref,
                    "type": "agent_reference",
                }
            },
        )
        total_ms = int((time.perf_counter() - total_start) * 1000)
        response_id = getattr(response, "id", None)
        output_text = getattr(response, "output_text", None) or ""
        structured = self._extract_structured(output_text)
        return SummaryResult(
            executive_summary=str(structured.get("executive_summary", "") or ""),
            key_points=[str(p) for p in (structured.get("key_points") or []) if p],
            action_items=self._normalize_action_items(structured.get("action_items") or []),
            total_ms=total_ms,
            response_id=response_id,
        )

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
            raise ValueError(f"No JSON object found in summary response: {cleaned[:200]!r}")
        json_str = cleaned[brace_start : brace_end + 1]
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as ex:
            raise ValueError(f"Summary response is not valid JSON: {ex}") from ex
        if not isinstance(data, dict):
            raise ValueError("Summary response JSON is not an object.")
        if "executive_summary" not in data:
            raise ValueError("Summary response missing required key 'executive_summary'.")
        return data

    def _normalize_action_items(self, items: list[Any]) -> list[dict[str, Any]]:
        result = []
        for item in items:
            if not isinstance(item, dict):
                continue
            action_text = str(item.get("item", "") or "").strip()
            if not action_text:
                continue
            result.append(
                {
                    "item": action_text,
                    "owner": str(item.get("owner", "") or "").strip(),
                    "due_date": str(item.get("due_date", "") or "").strip() or None,
                }
            )
        return result

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
        project_endpoint = (
            os.getenv("PROJECT_ENDPOINT") or os.getenv("AZURE_AI_PROJECT_ENDPOINT") or ""
        )
        model_deployment = (
            os.getenv("SUMMARY_MODEL_DEPLOYMENT_NAME")
            or os.getenv("MODEL_DEPLOYMENT_NAME")
            or os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
            or ""
        )
        agent_ref = os.getenv("SUMMARY_AGENT_ID") or os.getenv("SUMMARY_AGENT_NAME") or ""
        return cls(
            project_endpoint=project_endpoint,
            model_deployment=model_deployment,
            agent_ref=agent_ref,
        )
