import json
import os
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
        model_deployment: str,
        agent_ref: str,
    ) -> None:
        self._project_endpoint = project_endpoint.strip()
        self._model_deployment = model_deployment.strip()
        self._agent_ref = agent_ref.strip()
        self._agent_key = "id" if self._agent_ref.startswith("asst_") else "name"
        self._openai_client: Any = None
        self._conversation_id: str | None = None

    @property
    def is_configured(self) -> bool:
        return bool(self._project_endpoint and self._model_deployment and self._agent_ref)

    def _ensure_client(self) -> Any:
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
        self._conversation_id = None

    def close(self) -> None:
        client = self._openai_client
        if client is None:
            return
        close_fn = getattr(client, "close", None)
        if callable(close_fn):
            try:
                close_fn()
            except Exception:
                pass
        self._openai_client = None

    def _extract_json(self, text: str) -> dict[str, Any]:
        raw = str(text or "").strip()
        if not raw:
            raise RuntimeError("Topic tracker returned empty response.")
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

    def ask_update(self, context: dict[str, Any]) -> TopicTrackerResult:
        if not self.is_configured:
            raise RuntimeError(
                "Topic tracker is not configured. Set PROJECT_ENDPOINT, MODEL_DEPLOYMENT_NAME, and TOPIC_AGENT_ID/TOPIC_AGENT_NAME."
            )

        client = self._ensure_client()
        conversation_id = self._ensure_conversation_id()
        prompt = "\n".join(
            [
                "You are a meeting topic tracker.",
                "Return ONLY valid JSON. Do not include markdown or comments.",
                "Goals:",
                "1) Keep agenda topic names exact when matching existing topics.",
                "2) If allow_new_topics=false, do not create new topics.",
                "3) If allow_new_topics=true and no existing/agenda topic is a strong match, create a new topic.",
                "4) Treat matches below 0.50 confidence as not a strong match.",
                "5) Update time_seconds conservatively based on discussed content in the window.",
                "6) Keep key_statements short and useful.",
                "Schema:",
                "{",
                '  "topics": [',
                "    {",
                '      "name": "string",',
                '      "status": "not_started|active|covered",',
                '      "time_seconds": 0,',
                '      "key_statements": [',
                '        {"ts": 0, "speaker": "string", "text": "string"}',
                "      ]",
                "    }",
                "  ]",
                "}",
                "",
                "Input context JSON:",
                json.dumps(context, ensure_ascii=False),
            ]
        )

        params: dict[str, Any] = {
            "model": self._model_deployment,
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

        t0 = time.perf_counter()
        response = client.responses.create(**params)
        total_ms = int((time.perf_counter() - t0) * 1000)
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
        project_endpoint = (
            os.getenv("PROJECT_ENDPOINT")
            or os.getenv("AZURE_AI_PROJECT_ENDPOINT")
            or ""
        )
        model_deployment = (
            os.getenv("TOPIC_MODEL_DEPLOYMENT_NAME")
            or os.getenv("MODEL_DEPLOYMENT_NAME")
            or os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
            or ""
        )
        agent_ref = (
            os.getenv("TOPIC_AGENT_ID")
            or os.getenv("TOPIC_AGENT_NAME")
            or os.getenv("AGENT_ID")
            or os.getenv("AGENT_NAME")
            or "my-topics-agnet"
        )
        return cls(
            project_endpoint=project_endpoint,
            model_deployment=model_deployment,
            agent_ref=agent_ref,
        )
