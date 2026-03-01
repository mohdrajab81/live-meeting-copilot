import json
import os
import threading
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class TopicTrackerResult:
    payload: dict[str, Any]
    conversation_id: str | None
    response_id: str | None
    total_ms: int


class TopicTrackerService:
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
        self._conversation_id: str | None = None
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
                    "Missing topic tracker dependencies. Install azure-ai-projects and azure-identity."
                ) from ex

            credential = DefaultAzureCredential()
            project_client = AIProjectClient(
                endpoint=self._project_endpoint,
                credential=credential,
            )
            self._project_client = project_client
            self._openai_client = project_client.get_openai_client()
            return self._openai_client

    def _get_conversations_create_fn(self):
        client = self._ensure_client()
        conversations = getattr(client, "conversations", None)
        create_fn = getattr(conversations, "create", None) if conversations is not None else None
        if not callable(create_fn):
            raise RuntimeError(
                "OpenAI client does not support conversations.create(). "
                "Upgrade the client/runtime used by Azure AI Projects."
            )
        return create_fn

    def _ensure_conversation_id(self) -> str | None:
        with self._state_lock:
            if self._conversation_id:
                return self._conversation_id
            create_fn = self._get_conversations_create_fn()
            conversation = create_fn()
            conversation_id = (
                getattr(conversation, "id", None)
                or getattr(conversation, "conversation_id", None)
            )
            if not conversation_id:
                raise RuntimeError("conversations.create() returned no conversation id.")
            self._conversation_id = conversation_id
            return self._conversation_id

    def clear_conversation(self) -> None:
        with self._state_lock:
            self._conversation_id = None

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

    def _extract_json(self, text: str) -> dict[str, Any]:
        raw = str(text or "").strip()
        if not raw:
            raise RuntimeError("Topic tracker returned empty response.")
        lower = raw.lower()
        refusal_markers = (
            "i'm sorry",
            "i cannot",
            "i can't",
            "content policy",
            "not able to",
            "inappropriate",
            "safety",
        )
        if not raw.startswith("{") and any(marker in lower for marker in refusal_markers):
            raise RuntimeError(
                f"Topic tracker content filter blocked response: {raw[:160]}"
            )
        try:
            return json.loads(raw)
        except Exception:
            pass

        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end <= start:
            raise RuntimeError("Topic tracker returned non-JSON output.")
        try:
            return json.loads(raw[start : end + 1])
        except Exception as ex:
            raise RuntimeError("Topic tracker response JSON parse failed.") from ex

    @staticmethod
    def _topic_output_schema() -> dict[str, Any]:
        # Keep schema strict enough to force shape, but compatible with current merge logic.
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["topics"],
            "properties": {
                "topics": {
                    "type": "array",
                    "maxItems": 30,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "name",
                            "status",
                            "topic_presence",
                            "match_confidence",
                            "key_statements",
                        ],
                        "properties": {
                            "name": {"type": "string", "minLength": 1, "maxLength": 120},
                            "suggested_name": {
                                "type": "string",
                                "minLength": 1,
                                "maxLength": 120,
                            },
                            "short_description": {
                                "type": "string",
                                "minLength": 1,
                                "maxLength": 240,
                            },
                            "status": {
                                "type": "string",
                                "enum": ["not_started", "active", "covered"],
                            },
                            "topic_presence": {"type": "boolean"},
                            "match_confidence": {
                                "type": "number",
                                "minimum": 0.0,
                                "maximum": 1.0,
                            },
                            "key_statements": {
                                "type": "array",
                                "maxItems": 20,
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": ["ts", "speaker", "text"],
                                    "properties": {
                                        "ts": {"type": "number"},
                                        "speaker": {
                                            "type": "string",
                                            "minLength": 1,
                                            "maxLength": 80,
                                        },
                                        "text": {
                                            "type": "string",
                                            "minLength": 1,
                                            "maxLength": 160,
                                        },
                                    },
                                },
                            },
                        },
                    },
                }
            },
        }

    @staticmethod
    def _is_schema_unsupported_error(ex: Exception) -> bool:
        text = str(ex or "").strip().lower()
        if not text:
            return False
        markers = (
            "json_schema",
            "json schema",
            "json_object",
            "response_format",
            "response format",
            "unknown parameter",
            "unsupported parameter",
            "invalid parameter",
            "text.format",
            "does not support",
        )
        return any(marker in text for marker in markers)

    def _is_retryable_error(self, ex: Exception) -> bool:
        text = str(ex or "").strip().lower()
        if not text:
            return False
        retry_markers = (
            "error code: 429",
            "error code: 500",
            "error code: 502",
            "error code: 503",
            "error code: 504",
            "server_error",
            "rate_limit",
            "timeout",
            "timed out",
            "connection reset",
            "temporarily unavailable",
            "content filter blocked",
        )
        return any(marker in text for marker in retry_markers)

    def ask_update(self, context: dict[str, Any]) -> TopicTrackerResult:
        if not self.is_configured:
            raise RuntimeError(
                "Topic tracker is not configured. Set PROJECT_ENDPOINT and TOPIC_AGENT_NAME."
            )

        with self._state_lock:
            client = self._ensure_client()
            conversation_id = self._ensure_conversation_id()
            prompt = "Input context JSON:\n" + json.dumps(context, ensure_ascii=False)

            params: dict[str, Any] = {
                "input": prompt,
                "extra_body": {
                    "agent": {
                        self._agent_key: self._agent_ref,
                        "type": "agent_reference",
                    }
                },
            }
            if conversation_id:
                params["conversation"] = conversation_id

            variants: list[tuple[str, dict[str, Any]]] = []
            uses_agent_reference = bool(
                isinstance(params.get("extra_body"), dict)
                and isinstance(params["extra_body"].get("agent"), dict)
            )
            # Azure agent-routed Responses rejects "text" payload fields.
            # Keep plain mode whenever an agent is specified.
            if not uses_agent_reference:
                schema_params = dict(params)
                schema_params["text"] = {
                    "format": {
                        "type": "json_schema",
                        "name": "meeting_topic_tracker_output",
                        "strict": True,
                        "schema": self._topic_output_schema(),
                    }
                }
                variants.append(("json_schema", schema_params))

                json_mode_params = dict(params)
                json_mode_params["text"] = {"format": {"type": "json_object"}}
                variants.append(("json_object", json_mode_params))
            variants.append(("plain", dict(params)))

            t0 = time.perf_counter()
            response = None
            last_error: Exception | None = None
            max_attempts = 3
            for mode, call_params in variants:
                for attempt in range(1, max_attempts + 1):
                    try:
                        response = client.responses.create(**call_params)
                        break
                    except Exception as ex:
                        last_error = ex
                        if mode in {"json_schema", "json_object"} and self._is_schema_unsupported_error(ex):
                            # Backend/runtime does not accept structured format args; fall back.
                            break
                        if attempt >= max_attempts or (not self._is_retryable_error(ex)):
                            raise
                        # Backoff to smooth over transient upstream errors.
                        time.sleep(2.0 * attempt)
                if response is not None:
                    break
            total_ms = int((time.perf_counter() - t0) * 1000)
            if response is None:
                if last_error is not None:
                    raise last_error
                raise RuntimeError("Topic tracker call failed without response.")
            payload = self._extract_json(getattr(response, "output_text", None) or "")
            response_id = getattr(response, "id", None)
            response_conversation_id = getattr(response, "conversation_id", None)
            if response_conversation_id:
                self._conversation_id = response_conversation_id
            return TopicTrackerResult(
                payload=payload,
                conversation_id=self._conversation_id,
                response_id=response_id,
                total_ms=total_ms,
            )

    @classmethod
    def from_environment(cls) -> "TopicTrackerService":
        project_endpoint = os.getenv("PROJECT_ENDPOINT") or ""
        agent_ref = os.getenv("TOPIC_AGENT_NAME") or ""
        return cls(
            project_endpoint=project_endpoint,
            agent_ref=agent_ref,
        )

