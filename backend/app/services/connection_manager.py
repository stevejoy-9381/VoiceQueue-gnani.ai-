"""WebSocket Connection Manager for live queue updates."""

import asyncio
from typing import List
from fastapi import WebSocket


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts messages."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._loop = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        try:
            self._loop = asyncio.get_running_loop()
        except Exception:
            pass

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()


def _dispatch_broadcast(message: dict):
    if not manager.active_connections:
        return
    loop = manager._loop
    if loop and not loop.is_closed():
        try:
            asyncio.run_coroutine_threadsafe(manager.broadcast(message), loop)
            return
        except Exception:
            pass
    try:
        curr_loop = asyncio.get_running_loop()
        curr_loop.create_task(manager.broadcast(message))
    except RuntimeError:
        pass


def broadcast_queue_change(date_str: str) -> None:
    """
    Sends a queue_changed event to all connected WebSocket clients.
    Safe to call from synchronous endpoint handlers.
    """
    _dispatch_broadcast({"type": "queue_changed", "date": date_str})


def broadcast_demo_reset() -> None:
    """Sends a demo_reset event to all connected WebSocket clients."""
    _dispatch_broadcast({"type": "demo_reset"})


def broadcast_voice_log(log_item: dict | None = None) -> None:
    """Broadcasts a voice activity log event to all connected WebSocket clients."""
    _dispatch_broadcast({"type": "voice_log", "log": log_item})


def broadcast_token_called(token_id: int, token_number: int | None = None) -> None:
    """
    Broadcasts a token_called event to all connected WebSocket clients when a token is called next.
    Format: {"type": "token_called", "token_id": token_id, "token_number": token_number}
    """
    msg = {"type": "token_called", "token_id": token_id}
    if token_number is not None:
        msg["token_number"] = token_number
    _dispatch_broadcast(msg)


