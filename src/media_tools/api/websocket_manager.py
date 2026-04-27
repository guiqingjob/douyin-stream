import asyncio
import logging
from typing import List
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)

# 跟踪所有后台任务，防止 GC 导致静默失败
_background_tasks: set[asyncio.Task] = set()


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._stats = {"connected": 0, "disconnected": 0, "broadcast_success": 0, "broadcast_failed": 0}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self._stats["connected"] += 1

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self._stats["disconnected"] += 1

    def get_stats(self) -> dict:
        return {
            "active_connections": len(self.active_connections),
            **self._stats
        }

    async def broadcast(self, message: dict):
        dead_connections = []
        for conn in self.active_connections:
            try:
                if conn.client_state == WebSocketState.DISCONNECTED:
                    dead_connections.append(conn)
            except (AttributeError, RuntimeError):
                dead_connections.append(conn)

        for conn in dead_connections:
            self.disconnect(conn)

        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
                self._stats["broadcast_success"] += 1
            except (ConnectionResetError, OSError, BrokenPipeError, RuntimeError) as e:
                logger.info(f"WebSocket 连接已关闭，移除连接: {id(connection)}")
                self.disconnect(connection)
                self._stats["broadcast_failed"] += 1


manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    async def _heartbeat():
        try:
            while True:
                await asyncio.sleep(20)
                try:
                    await websocket.send_json({"type": "ping"})
                except (ConnectionResetError, OSError, BrokenPipeError) as e:
                    logger.warning(f"WebSocket ping failed: {e}")
                    break
        except asyncio.CancelledError:
            logger.debug("Heartbeat task cancelled")
        except (RuntimeError, OSError):
            logger.exception("Heartbeat task unexpected error")

    heartbeat_task = asyncio.create_task(_heartbeat())
    _background_tasks.add(heartbeat_task)
    heartbeat_task.add_done_callback(lambda t: _background_tasks.discard(t))

    try:
        while True:
            data = await websocket.receive_text()
            if data:
                logger.debug(f"WebSocket received: {data[:50]}...")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except (RuntimeError, OSError) as e:
        logger.exception(f"WebSocket unexpected error: {e}")
    finally:
        manager.disconnect(websocket)
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
