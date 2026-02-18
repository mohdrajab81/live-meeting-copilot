import json

from fastapi import WebSocket, WebSocketDisconnect

from app.api.auth import is_websocket_authorized


async def websocket_endpoint(websocket: WebSocket) -> None:
    if not is_websocket_authorized(websocket):
        await websocket.close(code=1008, reason="Unauthorized")
        return

    controller = websocket.app.state.controller
    await controller.connect_websocket(websocket)
    await websocket.send_text(json.dumps(controller.snapshot(), ensure_ascii=False))

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        controller.disconnect_websocket(websocket)
    except Exception:
        controller.disconnect_websocket(websocket)
