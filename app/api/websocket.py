import json

from fastapi import WebSocket, WebSocketDisconnect


async def websocket_endpoint(websocket: WebSocket) -> None:
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

