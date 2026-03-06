import ipaddress

from fastapi import HTTPException, Request, WebSocket


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


def require_http_auth(request: Request) -> None:
    if _is_loopback_host(_request_client_host(request)):
        return
    raise HTTPException(
        status_code=401,
        detail="Unauthorized. API is restricted to localhost only.",
    )


def is_websocket_authorized(websocket: WebSocket) -> bool:
    return _is_loopback_host(_websocket_client_host(websocket))
