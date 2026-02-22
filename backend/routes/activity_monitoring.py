"""
Real-time User Activity Monitoring Module
Tracks user sessions, actions, and provides live dashboard data
"""
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import uuid
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user, get_admin_user

router = APIRouter(prefix="/activity", tags=["Activity Monitoring"])

# In-memory store for real-time tracking
active_sessions: Dict[str, dict] = {}
activity_buffer: List[dict] = []
connected_admins: List[WebSocket] = []


class ActivityEvent(BaseModel):
    event_type: str = Field(..., description="Type of event: page_view, action, error")
    page: Optional[str] = None
    action: Optional[str] = None
    metadata: Optional[dict] = {}


async def broadcast_to_admins(message: dict):
    """Broadcast activity updates to connected admin dashboards"""
    disconnected = []
    for ws in connected_admins:
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        connected_admins.remove(ws)


async def record_activity(user_id: str, event_type: str, data: dict):
    """Record user activity and broadcast to admins"""
    activity = {
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "eventType": event_type,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Add to buffer for batch insert
    activity_buffer.append(activity)
    
    # Update active session
    if user_id in active_sessions:
        active_sessions[user_id]["lastActivity"] = activity["timestamp"]
        active_sessions[user_id]["activityCount"] = active_sessions[user_id].get("activityCount", 0) + 1
    
    # Broadcast to admin dashboards
    await broadcast_to_admins({
        "type": "activity",
        "data": activity
    })
    
    # Batch insert to DB every 10 events
    if len(activity_buffer) >= 10:
        await flush_activity_buffer()


async def flush_activity_buffer():
    """Flush activity buffer to database"""
    global activity_buffer
    if activity_buffer:
        try:
            await db.user_activities.insert_many(activity_buffer)
            activity_buffer = []
        except Exception as e:
            logger.error(f"Failed to flush activity buffer: {e}")


@router.post("/track")
async def track_activity(
    event: ActivityEvent,
    user: dict = Depends(get_current_user)
):
    """Track user activity from frontend"""
    await record_activity(user["id"], event.event_type, {
        "page": event.page,
        "action": event.action,
        "metadata": event.metadata
    })
    return {"success": True}


@router.post("/session/start")
async def start_session(user: dict = Depends(get_current_user)):
    """Start or update user session"""
    user_id = user["id"]
    now = datetime.now(timezone.utc).isoformat()
    
    # Get user info
    user_info = await db.users.find_one(
        {"id": user_id},
        {"_id": 0, "name": 1, "email": 1, "plan": 1}
    )
    
    session = {
        "userId": user_id,
        "userName": user_info.get("name", "Unknown") if user_info else "Unknown",
        "userEmail": user_info.get("email", "") if user_info else "",
        "plan": user_info.get("plan", "free") if user_info else "free",
        "startTime": now,
        "lastActivity": now,
        "activityCount": 0,
        "currentPage": "dashboard"
    }
    
    active_sessions[user_id] = session
    
    # Broadcast session start
    await broadcast_to_admins({
        "type": "session_start",
        "data": {
            "userId": user_id,
            "userName": session["userName"],
            "plan": session["plan"]
        }
    })
    
    return {"success": True, "sessionId": user_id}


@router.post("/session/end")
async def end_session(user: dict = Depends(get_current_user)):
    """End user session"""
    user_id = user["id"]
    
    if user_id in active_sessions:
        session = active_sessions.pop(user_id)
        
        # Calculate session duration
        start = datetime.fromisoformat(session["startTime"].replace("Z", "+00:00"))
        duration = (datetime.now(timezone.utc) - start).total_seconds()
        
        # Store session summary
        await db.session_history.insert_one({
            "userId": user_id,
            "startTime": session["startTime"],
            "endTime": datetime.now(timezone.utc).isoformat(),
            "duration": duration,
            "activityCount": session["activityCount"]
        })
        
        # Broadcast session end
        await broadcast_to_admins({
            "type": "session_end",
            "data": {"userId": user_id}
        })
    
    return {"success": True}


@router.post("/heartbeat")
async def session_heartbeat(
    page: str = "unknown",
    user: dict = Depends(get_current_user)
):
    """Update session heartbeat"""
    user_id = user["id"]
    
    if user_id in active_sessions:
        active_sessions[user_id]["lastActivity"] = datetime.now(timezone.utc).isoformat()
        active_sessions[user_id]["currentPage"] = page
    
    return {"success": True}


# Admin Endpoints

@router.get("/admin/live")
async def get_live_activity(admin: dict = Depends(get_admin_user)):
    """Get current live activity data"""
    now = datetime.now(timezone.utc)
    
    # Clean stale sessions (no activity in 5 minutes)
    stale_threshold = (now - timedelta(minutes=5)).isoformat()
    stale_users = [
        uid for uid, session in active_sessions.items()
        if session["lastActivity"] < stale_threshold
    ]
    for uid in stale_users:
        active_sessions.pop(uid, None)
    
    # Get active sessions data
    sessions_list = []
    for uid, session in active_sessions.items():
        sessions_list.append({
            "userId": uid,
            "userName": session.get("userName", "Unknown"),
            "plan": session.get("plan", "free"),
            "currentPage": session.get("currentPage", "unknown"),
            "activityCount": session.get("activityCount", 0),
            "sessionDuration": (
                now - datetime.fromisoformat(session["startTime"].replace("Z", "+00:00"))
            ).total_seconds()
        })
    
    # Get recent activities
    recent_activities = await db.user_activities.find(
        {},
        {"_id": 0}
    ).sort("timestamp", -1).limit(50).to_list(50)
    
    return {
        "activeSessions": sessions_list,
        "activeUsersCount": len(active_sessions),
        "recentActivities": recent_activities,
        "timestamp": now.isoformat()
    }


@router.get("/admin/stats")
async def get_activity_stats(
    period: str = "today",
    admin: dict = Depends(get_admin_user)
):
    """Get activity statistics for a period"""
    now = datetime.now(timezone.utc)
    
    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start = now - timedelta(days=7)
    elif period == "month":
        start = now - timedelta(days=30)
    else:
        start = now - timedelta(days=1)
    
    # Get activity counts by type
    pipeline = [
        {"$match": {"timestamp": {"$gte": start.isoformat()}}},
        {"$group": {
            "_id": "$eventType",
            "count": {"$sum": 1}
        }}
    ]
    activity_by_type = await db.user_activities.aggregate(pipeline).to_list(100)
    
    # Get page views
    page_pipeline = [
        {"$match": {
            "timestamp": {"$gte": start.isoformat()},
            "eventType": "page_view"
        }},
        {"$group": {
            "_id": "$data.page",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    top_pages = await db.user_activities.aggregate(page_pipeline).to_list(10)
    
    # Get unique users
    unique_users = await db.user_activities.distinct(
        "userId",
        {"timestamp": {"$gte": start.isoformat()}}
    )
    
    # Get session stats
    sessions = await db.session_history.find(
        {"startTime": {"$gte": start.isoformat()}},
        {"_id": 0}
    ).to_list(1000)
    
    avg_duration = 0
    if sessions:
        total_duration = sum(s.get("duration", 0) for s in sessions)
        avg_duration = total_duration / len(sessions)
    
    return {
        "period": period,
        "activityByType": {item["_id"]: item["count"] for item in activity_by_type},
        "topPages": [{"page": item["_id"], "views": item["count"]} for item in top_pages],
        "uniqueUsers": len(unique_users),
        "totalSessions": len(sessions),
        "avgSessionDuration": round(avg_duration, 2),
        "activeNow": len(active_sessions)
    }


@router.get("/admin/user/{user_id}")
async def get_user_activity(
    user_id: str,
    admin: dict = Depends(get_admin_user)
):
    """Get detailed activity for a specific user"""
    # Get user info
    user = await db.users.find_one(
        {"id": user_id},
        {"_id": 0, "password": 0}
    )
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get recent activities
    activities = await db.user_activities.find(
        {"userId": user_id},
        {"_id": 0}
    ).sort("timestamp", -1).limit(100).to_list(100)
    
    # Get session history
    sessions = await db.session_history.find(
        {"userId": user_id},
        {"_id": 0}
    ).sort("startTime", -1).limit(20).to_list(20)
    
    # Check if currently active
    is_active = user_id in active_sessions
    current_session = active_sessions.get(user_id)
    
    return {
        "user": user,
        "recentActivities": activities,
        "sessionHistory": sessions,
        "isCurrentlyActive": is_active,
        "currentSession": current_session
    }


@router.websocket("/admin/ws")
async def admin_activity_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time admin dashboard updates"""
    await websocket.accept()
    
    # Verify admin (simple token check)
    try:
        auth_message = await asyncio.wait_for(websocket.receive_json(), timeout=10)
        token = auth_message.get("token")
        
        # Validate token and check admin role
        from shared import decode_token
        payload = decode_token(token)
        if not payload:
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
        if not user or user.get("role") != "ADMIN":
            await websocket.close(code=4003, reason="Admin access required")
            return
        
        connected_admins.append(websocket)
        
        # Send initial data
        await websocket.send_json({
            "type": "init",
            "data": {
                "activeSessions": len(active_sessions),
                "connectedAdmins": len(connected_admins)
            }
        })
        
        # Keep connection alive
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_json(), timeout=60)
                
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({
                    "type": "heartbeat",
                    "activeSessions": len(active_sessions)
                })
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if websocket in connected_admins:
            connected_admins.remove(websocket)


# Background task to flush buffer periodically
async def periodic_flush():
    """Periodically flush activity buffer"""
    while True:
        await asyncio.sleep(30)
        await flush_activity_buffer()


# Startup task
async def start_activity_monitoring():
    """Start activity monitoring background tasks"""
    asyncio.create_task(periodic_flush())
    logger.info("Activity monitoring started")
