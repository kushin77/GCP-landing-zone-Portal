"""
WebSocket support for real-time updates.
"""
import logging
from typing import Dict, List

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str = None):
        """Accept new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)

        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(websocket)

        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket, user_id: str = None):
        """Remove WebSocket connection."""
        self.active_connections.remove(websocket)

        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].remove(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")

    async def send_to_user(self, message: dict, user_id: str):
        """Send message to all connections of a specific user."""
        if user_id in self.user_connections:
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to user {user_id}: {e}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connections."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting: {e}")
                disconnected.append(connection)

        # Clean up disconnected connections
        for connection in disconnected:
            try:
                self.active_connections.remove(connection)
            except ValueError:
                pass


# Global connection manager
manager = ConnectionManager()


async def notify_cost_update(data: dict):
    """Notify all clients of cost updates."""
    await manager.broadcast({"type": "cost_update", "data": data})


async def notify_compliance_change(data: dict):
    """Notify all clients of compliance changes."""
    await manager.broadcast({"type": "compliance_change", "data": data})


async def notify_workflow_update(workflow_id: str, status: str, user_id: str = None):
    """Notify about workflow status changes."""
    message = {"type": "workflow_update", "data": {"workflow_id": workflow_id, "status": status}}

    if user_id:
        await manager.send_to_user(message, user_id)
    else:
        await manager.broadcast(message)
