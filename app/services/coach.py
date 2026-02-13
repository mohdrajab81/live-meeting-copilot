import os
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class CoachResult:
    text: str
    conversation_id: str | None
    response_id: str | None
    request_conversation_id: str | None
    request_previous_response_id: str | None
    total_ms: int
    create_ms: int
    approve_ms: int
    approval_rounds: int
    approval_count: int


class CoachService:
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
        self._conversation_id: str | None = None
        self._previous_response_id: str | None = None
        self._openai_client: Any = None

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
                "Missing coach dependencies. Install azure-ai-projects and azure-identity."
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

    def _auto_approve_mcp_if_needed(
        self, response: Any, max_rounds: int = 5
    ) -> tuple[Any, int, int, int]:
        client = self._ensure_client()
        rounds = 0
        approvals = 0
        start = time.perf_counter()
        for _ in range(max_rounds):
            output_items = getattr(response, "output", [])
            approval_requests = [
                item
                for item in output_items
                if getattr(item, "type", None) == "mcp_approval_request"
            ]
            if not approval_requests:
                approve_ms = int((time.perf_counter() - start) * 1000)
                return response, rounds, approvals, approve_ms

            rounds += 1
            for req in approval_requests:
                approvals += 1
                response = client.responses.create(
                    previous_response_id=response.id,
                    input=[
                        {
                            "type": "mcp_approval_response",
                            "approval_request_id": req.id,
                            "approve": True,
                        }
                    ],
                    extra_body={
                        "agent": {
                            self._agent_key: self._agent_ref,
                            "type": "agent_reference",
                        }
                    },
                )
        approve_ms = int((time.perf_counter() - start) * 1000)
        return response, rounds, approvals, approve_ms

    def ask(self, prompt: str) -> CoachResult:
        if not self.is_configured:
            raise RuntimeError(
                "Coach is not configured. Set PROJECT_ENDPOINT, MODEL_DEPLOYMENT_NAME, and AGENT_ID/AGENT_NAME."
            )
        client = self._ensure_client()

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
        request_conversation_id = self._ensure_conversation_id()
        request_previous_response_id = self._previous_response_id
        sent_previous_response_id: str | None = None
        if request_conversation_id:
            params["conversation"] = request_conversation_id
        elif request_previous_response_id:
            # Azure Responses API rejects sending both conversation and previous_response_id together.
            params["previous_response_id"] = request_previous_response_id
            sent_previous_response_id = request_previous_response_id

        total_start = time.perf_counter()
        create_start = time.perf_counter()
        response = client.responses.create(**params)
        create_ms = int((time.perf_counter() - create_start) * 1000)
        response, rounds, approvals, approve_ms = self._auto_approve_mcp_if_needed(response)
        total_ms = int((time.perf_counter() - total_start) * 1000)
        response_id = getattr(response, "id", None)
        response_conversation_id = getattr(response, "conversation_id", None)
        if response_conversation_id:
            self._conversation_id = response_conversation_id
        self._previous_response_id = response_id
        text = getattr(response, "output_text", None) or "(No text output returned.)"
        return CoachResult(
            text=text,
            conversation_id=self._conversation_id,
            response_id=response_id,
            request_conversation_id=request_conversation_id,
            request_previous_response_id=sent_previous_response_id,
            total_ms=total_ms,
            create_ms=create_ms,
            approve_ms=approve_ms,
            approval_rounds=rounds,
            approval_count=approvals,
        )

    def get_chain_state(self) -> dict[str, str | None]:
        # Report only fields that would be sent on the next ask() call.
        req_conversation_id = self._conversation_id
        req_previous = None if req_conversation_id else self._previous_response_id
        return {
            "conversation_id": req_conversation_id,
            "previous_response_id": req_previous,
        }

    def clear_conversation(self) -> None:
        self._conversation_id = None
        self._previous_response_id = None

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
            raise RuntimeError(
                "conversations.create() returned no conversation id."
            )
        self._conversation_id = conversation_id
        return self._conversation_id

    def start_session(self) -> str | None:
        self.clear_conversation()
        return self._ensure_conversation_id()

    def supports_conversations_create(self) -> bool:
        try:
            self._get_conversations_create_fn()
            return True
        except Exception:
            return False

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

    @classmethod
    def from_environment(cls) -> "CoachService":
        project_endpoint = (
            os.getenv("PROJECT_ENDPOINT")
            or os.getenv("AZURE_AI_PROJECT_ENDPOINT")
            or ""
        )
        model_deployment = (
            os.getenv("MODEL_DEPLOYMENT_NAME")
            or os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
            or ""
        )
        agent_ref = os.getenv("AGENT_ID") or os.getenv("AGENT_NAME") or "my-profile-agent"
        return cls(
            project_endpoint=project_endpoint,
            model_deployment=model_deployment,
            agent_ref=agent_ref,
        )
