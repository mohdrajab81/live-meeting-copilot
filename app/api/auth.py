import ipaddress
import os
import secrets
from typing import Mapping

from fastapi import HTTPException, Request, WebSocket


def _configured_token() -> str:
    return str(os.getenv("API_AUTH_TOKEN", "") or "").strip()


def _extract_bearer_token(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    lower = raw.lower()
    if not lower.startswith("bearer "):
        return ""
    return raw[7:].strip()


def _extract_token_from_headers(headers: Mapping[str, str]) -> str:
    auth_value = _extract_bearer_token(headers.get("authorization", ""))
    if auth_value:
        return auth_value
    return str(headers.get("x-api-key", "") or "").strip()


def _extract_token_from_query(query_params: Mapping[str, str]) -> str:
    token = str(query_params.get("token", "") or "").strip()
    if token:
        return token
    return str(query_params.get("api_token", "") or "").strip()


def _is_loopback_host(host: str) -> bool:
    cleaned = str(host or "").strip()
    if not cleaned:
        return False
    cleaned = cleaned.split("%", 1)[0].strip().lower()
    if cleaned in {"localhost", "testclient"}:
        return True
    try:
        return bool(ipaddress.ip_address(cleaned).is_loopback)
    except Exception:
        return False


def _request_client_host(request: Request) -> str:
    client = request.client
    if client is None:
        return ""
    return str(client.host or "").strip()


def _websocket_client_host(websocket: WebSocket) -> str:
    client = websocket.client
    if client is None:
        return ""
    return str(client.host or "").strip()


def _is_valid_token(provided_token: str, expected_token: str) -> bool:
    if not provided_token or not expected_token:
        return False
    try:
        return secrets.compare_digest(provided_token, expected_token)
    except Exception:
        return False


def require_http_auth(request: Request) -> None:
    expected_token = _configured_token()
    provided_token = _extract_token_from_headers(request.headers) or _extract_token_from_query(
        request.query_params
    )

    if expected_token:
        if _is_valid_token(provided_token, expected_token):
            return
        raise HTTPException(status_code=401, detail="Unauthorized")

    if _is_loopback_host(_request_client_host(request)):
        return
    raise HTTPException(
        status_code=401,
        detail=(
            "Unauthorized. API is restricted to localhost unless API_AUTH_TOKEN is set "
            "and provided as Bearer token, X-API-Key header, or token query parameter."
        ),
    )


def is_websocket_authorized(websocket: WebSocket) -> bool:
    expected_token = _configured_token()
    provided_token = _extract_token_from_headers(websocket.headers) or _extract_token_from_query(
        websocket.query_params
    )

    if expected_token:
        return _is_valid_token(provided_token, expected_token)
    return _is_loopback_host(_websocket_client_host(websocket))
