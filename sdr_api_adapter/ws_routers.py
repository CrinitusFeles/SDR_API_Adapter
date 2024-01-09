
from fastapi import APIRouter
from fastapi.websockets import WebSocket, WebSocketDisconnect
from loguru import logger

router: APIRouter = APIRouter(tags=["WebSocket"])

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.info(f'ws client connected {websocket.client}')
    try:
        while True:
            data: str = await websocket.receive_text()

    except WebSocketDisconnect:
        logger.info(f"Client #{websocket.client} left the chat")