"""
Admin WebSocket — Real-time dashboard updates.
Pushes metric summaries to connected admin clients.
"""
import asyncio
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import jwt
import os

from shared import db

router = APIRouter(tags=["admin-ws"])
logger = logging.getLogger("admin_ws")

JWT_SECRET = os.environ.get("JWT_SECRET", "")

# Active admin connections
_admin_connections: list[WebSocket] = []


async def _verify_admin_ws(websocket: WebSocket) -> bool:
    """Verify the WebSocket connection is from an admin user."""
    token = websocket.query_params.get("token", "")
    if not token:
        return False
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("user_id") or payload.get("sub")
        if not user_id:
            return False
        user = await db.users.find_one({"id": user_id}, {"_id": 0, "role": 1})
        return user and user.get("role") == "admin"
    except Exception:
        return False


async def _get_live_snapshot():
    """Quick snapshot for live dashboard push."""
    now = datetime.now(timezone.utc)
    fifteen_min_ago = (now - __import__("datetime").timedelta(minutes=15)).isoformat()
    one_hour_ago = (now - __import__("datetime").timedelta(hours=1)).isoformat()

    # Active sessions
    active_sessions = 0
    try:
        active_sessions = await db.user_sessions.count_documents({
            "last_activity": {"$gte": fifteen_min_ago},
            "status": "active"
        })
    except Exception:
        pass

    # Queue depth
    queue_depth = await db.pipeline_jobs.count_documents({
        "status": {"$in": ["queued", "QUEUED", "planning", "PLANNING", "generating", "GENERATING"]}
    })

    # Recent completions (last hour)
    recent_completions = await db.pipeline_jobs.count_documents({
        "status": "READY",
        "completed_at": {"$gte": one_hour_ago}
    })

    # Recent events (last 15 min)
    recent_events = await db.growth_events.count_documents({
        "timestamp": {"$gte": fifteen_min_ago}
    })

    return {
        "type": "live_snapshot",
        "timestamp": now.isoformat(),
        "active_sessions": active_sessions,
        "queue_depth": queue_depth,
        "recent_completions_1h": recent_completions,
        "recent_events_15m": recent_events,
    }


@router.websocket("/ws/admin/live")
async def admin_live_ws(websocket: WebSocket):
    """WebSocket endpoint for live admin dashboard updates."""
    is_admin = await _verify_admin_ws(websocket)
    if not is_admin:
        await websocket.close(code=4003, reason="Admin access required")
        return

    await websocket.accept()
    _admin_connections.append(websocket)
    logger.info(f"Admin WS connected. Total: {len(_admin_connections)}")

    try:
        # Send initial snapshot
        snapshot = await _get_live_snapshot()
        await websocket.send_json(snapshot)

        # Keep alive and push updates every 10 seconds
        while True:
            await asyncio.sleep(10)
            try:
                snapshot = await _get_live_snapshot()
                await websocket.send_json(snapshot)
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"Admin WS error: {e}")
    finally:
        if websocket in _admin_connections:
            _admin_connections.remove(websocket)
        logger.info(f"Admin WS disconnected. Total: {len(_admin_connections)}")


async def broadcast_admin_event(event_data: dict):
    """Broadcast an event to all connected admin WebSocket clients."""
    dead = []
    for ws in _admin_connections:
        try:
            await ws.send_json(event_data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _admin_connections.remove(ws)
