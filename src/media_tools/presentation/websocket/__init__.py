"""表示层 - WebSocket 实时推送"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Set

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        """建立连接"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket 连接建立，当前连接数: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """断开连接"""
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket 连接断开，当前连接数: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """广播消息到所有连接"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"广播消息失败: {e}")
                self.disconnect(connection)
    
    async def send_to(self, websocket: WebSocket, message: Dict[str, Any]):
        """发送消息到指定连接"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            self.disconnect(websocket)


class TaskProgressBroadcaster:
    """任务进度广播器"""
    
    def __init__(self):
        self._manager = ConnectionManager()
        self._progress_cache: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket):
        """建立连接"""
        await self._manager.connect(websocket)
        
        # 发送缓存的进度
        for task_id, progress in self._progress_cache.items():
            await self._manager.send_to(websocket, {
                "type": "progress",
                "task_id": task_id,
                "progress": progress,
            })
    
    def disconnect(self, websocket: WebSocket):
        """断开连接"""
        self._manager.disconnect(websocket)
    
    async def update_progress(self, task_id: str, progress: Dict[str, Any]):
        """更新任务进度并广播"""
        self._progress_cache[task_id] = progress
        
        message = {
            "type": "progress",
            "task_id": task_id,
            "progress": progress,
        }
        await self._manager.broadcast(message)
    
    async def task_completed(self, task_id: str, success: bool, error_message: str = ""):
        """任务完成通知"""
        message = {
            "type": "completed",
            "task_id": task_id,
            "success": success,
            "error_message": error_message,
        }
        await self._manager.broadcast(message)
        
        # 清理缓存
        if task_id in self._progress_cache:
            del self._progress_cache[task_id]
    
    async def send_error(self, task_id: str, error: str):
        """发送错误消息"""
        message = {
            "type": "error",
            "task_id": task_id,
            "error": error,
        }
        await self._manager.broadcast(message)


# 全局实例
_task_broadcaster = TaskProgressBroadcaster()


def get_task_broadcaster() -> TaskProgressBroadcaster:
    """获取任务进度广播器实例"""
    return _task_broadcaster