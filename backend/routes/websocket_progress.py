"""
WebSocket Real-Time Progress Notifications
Provides live updates during long-running generation jobs.
"""

import os
import json
import asyncio
from datetime import datetime, timezone
from typing import Dict, Set, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from jose import jwt, JWTError

from shared import db, logger

router = APIRouter(tags=["WebSocket Progress"])

# JWT Secret for auth validation
JWT_SECRET = os.environ.get("JWT_SECRET", "your-secret-key-here")
JWT_ALGORITHM = "HS256"

# Connection manager for WebSocket clients
class ConnectionManager:
    def __init__(self):
        # Map: job_id -> set of websocket connections
        self.job_connections: Dict[str, Set[WebSocket]] = {}
        # Map: user_id -> set of websocket connections
        self.user_connections: Dict[str, Set[WebSocket]] = {}
        # Map: websocket -> user_id
        self.socket_to_user: Dict[WebSocket, str] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str, job_id: Optional[str] = None):
        """Connect a client and optionally subscribe to a job"""
        await websocket.accept()
        
        # Track user connection
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)
        self.socket_to_user[websocket] = user_id
        
        # Subscribe to specific job if provided
        if job_id:
            if job_id not in self.job_connections:
                self.job_connections[job_id] = set()
            self.job_connections[job_id].add(websocket)
        
        logger.info(f"WebSocket connected: user={user_id}, job={job_id}")
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a client and clean up subscriptions"""
        user_id = self.socket_to_user.get(websocket)
        
        # Remove from user connections
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # Remove from job connections
        for job_id, connections in list(self.job_connections.items()):
            connections.discard(websocket)
            if not connections:
                del self.job_connections[job_id]
        
        # Remove socket mapping
        if websocket in self.socket_to_user:
            del self.socket_to_user[websocket]
        
        logger.info(f"WebSocket disconnected: user={user_id}")
    
    def subscribe_to_job(self, websocket: WebSocket, job_id: str):
        """Subscribe a connected client to a specific job"""
        if job_id not in self.job_connections:
            self.job_connections[job_id] = set()
        self.job_connections[job_id].add(websocket)
    
    async def send_to_job(self, job_id: str, message: dict):
        """Send a message to all clients subscribed to a job"""
        if job_id in self.job_connections:
            disconnected = []
            for websocket in self.job_connections[job_id]:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send to websocket: {e}")
                    disconnected.append(websocket)
            
            # Clean up disconnected sockets
            for ws in disconnected:
                self.disconnect(ws)
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send a message to all connections of a specific user"""
        if user_id in self.user_connections:
            disconnected = []
            for websocket in self.user_connections[user_id]:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send to websocket: {e}")
                    disconnected.append(websocket)
            
            # Clean up disconnected sockets
            for ws in disconnected:
                self.disconnect(ws)
    
    async def broadcast_progress(
        self,
        job_id: str,
        user_id: str,
        stage: str,
        progress: int,
        current_step: int,
        total_steps: int,
        message: str,
        status: str = "running",
        estimated_remaining: Optional[str] = None,
        metadata: Optional[dict] = None
    ):
        """Broadcast a progress update to job subscribers"""
        payload = {
            "type": "progress",
            "job_id": job_id,
            "user_id": user_id,
            "stage": stage,
            "progress": progress,
            "current_step": current_step,
            "total_steps": total_steps,
            "message": message,
            "status": status,
            "estimated_remaining": estimated_remaining,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Send to job subscribers
        await self.send_to_job(job_id, payload)
        
        # Also send to user (in case they reconnected)
        await self.send_to_user(user_id, payload)
        
        # Log for debugging
        logger.info(f"Progress broadcast: job={job_id}, stage={stage}, progress={progress}%")


# Global connection manager
manager = ConnectionManager()


def verify_token(token: str) -> Optional[dict]:
    """Verify JWT token and return user data"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        return None


@router.websocket("/ws/progress")
async def websocket_progress_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    job_id: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time progress updates.
    
    Connect with: ws://host/ws/progress?token=<jwt_token>&job_id=<optional_job_id>
    
    Messages received:
    - {"type": "subscribe", "job_id": "..."}  - Subscribe to a job
    - {"type": "ping"}  - Keep-alive
    
    Messages sent:
    - {"type": "progress", "stage": "...", "progress": 50, ...}
    - {"type": "complete", "job_id": "...", "result": {...}}
    - {"type": "error", "job_id": "...", "message": "..."}
    """
    # Verify token
    user_data = verify_token(token)
    if not user_data:
        await websocket.close(code=4001, reason="Invalid authentication token")
        return
    
    user_id = user_data.get("user_id") or user_data.get("sub")
    if not user_id:
        await websocket.close(code=4001, reason="Invalid user in token")
        return
    
    # Connect and optionally subscribe to job
    await manager.connect(websocket, user_id, job_id)
    
    # Send connection confirmation
    await websocket.send_json({
        "type": "connected",
        "user_id": user_id,
        "job_id": job_id,
        "message": "Connected to progress updates"
    })
    
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_json()
            
            msg_type = data.get("type")
            
            if msg_type == "subscribe":
                # Subscribe to a new job
                new_job_id = data.get("job_id")
                if new_job_id:
                    manager.subscribe_to_job(websocket, new_job_id)
                    await websocket.send_json({
                        "type": "subscribed",
                        "job_id": new_job_id
                    })
            
            elif msg_type == "ping":
                # Respond to keep-alive
                await websocket.send_json({"type": "pong"})
            
            elif msg_type == "unsubscribe":
                # Unsubscribe from a job
                unsub_job_id = data.get("job_id")
                if unsub_job_id and unsub_job_id in manager.job_connections:
                    manager.job_connections[unsub_job_id].discard(websocket)
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "job_id": unsub_job_id
                    })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# =============================================================================
# HELPER FUNCTIONS FOR BROADCASTING PROGRESS
# =============================================================================

async def broadcast_scene_progress(
    job_id: str,
    user_id: str,
    current_scene: int,
    total_scenes: int,
    scene_name: str = ""
):
    """Broadcast scene generation progress"""
    progress = int((current_scene / total_scenes) * 100)
    await manager.broadcast_progress(
        job_id=job_id,
        user_id=user_id,
        stage="scene_generation",
        progress=progress,
        current_step=current_scene,
        total_steps=total_scenes,
        message=f"Generating scene {current_scene}/{total_scenes}" + (f": {scene_name}" if scene_name else ""),
        status="running",
        estimated_remaining=f"~{(total_scenes - current_scene) * 5}s"
    )


async def broadcast_image_progress(
    job_id: str,
    user_id: str,
    current_image: int,
    total_images: int
):
    """Broadcast image generation progress"""
    progress = int((current_image / total_images) * 100)
    await manager.broadcast_progress(
        job_id=job_id,
        user_id=user_id,
        stage="image_generation",
        progress=progress,
        current_step=current_image,
        total_steps=total_images,
        message=f"Creating scene image {current_image}/{total_images}",
        status="running",
        estimated_remaining=f"~{(total_images - current_image) * 10}s"
    )


async def broadcast_voice_progress(
    job_id: str,
    user_id: str,
    current_track: int,
    total_tracks: int
):
    """Broadcast voice generation progress"""
    progress = int((current_track / total_tracks) * 100)
    await manager.broadcast_progress(
        job_id=job_id,
        user_id=user_id,
        stage="voice_generation",
        progress=progress,
        current_step=current_track,
        total_steps=total_tracks,
        message=f"Recording narration {current_track}/{total_tracks}",
        status="running",
        estimated_remaining=f"~{(total_tracks - current_track) * 8}s"
    )


async def broadcast_video_progress(
    job_id: str,
    user_id: str,
    stage_name: str,
    progress: int,
    metadata: dict = None
):
    """Broadcast video assembly progress with optional detailed metadata"""
    stages = {
        "preparing": "Preparing scene assets...",
        "composing": "Composing video frames...",
        "audio_sync": "Synchronizing audio...",
        "music": "Adding background music...",
        "rendering": "Rendering final video...",
        "encoding": "Encoding and optimizing...",
        "uploading": "Uploading to cloud storage..."
    }
    
    # Use custom message from metadata if provided
    message = stages.get(stage_name, f"Processing: {stage_name}")
    if metadata and metadata.get("stage"):
        message = metadata.get("stage")
    
    await manager.broadcast_progress(
        job_id=job_id,
        user_id=user_id,
        stage="video_assembly",
        progress=progress,
        current_step=progress,
        total_steps=100,
        message=message,
        status="running",
        estimated_remaining=f"~{max(5, (100 - progress) // 10)}s"
    )


async def broadcast_completion(
    job_id: str,
    user_id: str,
    result_type: str,
    result_url: Optional[str] = None,
    metadata: Optional[dict] = None
):
    """Broadcast job completion"""
    await manager.broadcast_progress(
        job_id=job_id,
        user_id=user_id,
        stage="complete",
        progress=100,
        current_step=1,
        total_steps=1,
        message=f"{result_type} ready for download!",
        status="completed",
        metadata={
            "result_url": result_url,
            "result_type": result_type,
            **(metadata or {})
        }
    )


async def broadcast_error(
    job_id: str,
    user_id: str,
    error_message: str,
    stage: str = "unknown"
):
    """Broadcast job error"""
    await manager.broadcast_progress(
        job_id=job_id,
        user_id=user_id,
        stage=stage,
        progress=0,
        current_step=0,
        total_steps=1,
        message=error_message,
        status="failed"
    )


async def broadcast_asset_ready(
    job_id: str,
    user_id: str,
    asset_type: str,
    scene_number: int,
    data: dict
):
    """Broadcast that an individual asset is ready (scene/image/voice).
    This enables progressive delivery — frontend can show each asset as it arrives.
    
    asset_type: 'scene_ready' | 'image_ready' | 'voice_ready' | 'preview_ready'
    data: asset-specific payload (url, title, narration, duration, etc.)
    """
    payload = {
        "type": "asset_ready",
        "job_id": job_id,
        "user_id": user_id,
        "asset_type": asset_type,
        "scene_number": scene_number,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await manager.send_to_job(job_id, payload)
    await manager.send_to_user(user_id, payload)


# Export manager and helper functions
__all__ = [
    "router",
    "manager",
    "broadcast_scene_progress",
    "broadcast_image_progress",
    "broadcast_voice_progress",
    "broadcast_video_progress",
    "broadcast_completion",
    "broadcast_error",
    "broadcast_asset_ready"
]
