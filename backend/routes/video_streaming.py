"""
Video Streaming Protection Routes
==================================
Secure video delivery with:
- Signed streaming URLs
- Access logging
- No raw file URL exposure
- Range request support for seeking
"""
import os
import mimetypes
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
import aiofiles
import aiofiles.os

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, get_current_user
from services.video_protection import (
    generate_video_token,
    validate_video_token,
    get_video_stream_url,
    log_video_playback,
    VIDEO_URL_EXPIRY_SECONDS,
    CHUNK_SIZE
)

router = APIRouter(prefix="/video-stream", tags=["video-streaming"])


@router.get("/config")
async def get_streaming_config():
    """Get video streaming configuration"""
    return {
        "chunk_size": CHUNK_SIZE,
        "url_expiry_seconds": VIDEO_URL_EXPIRY_SECONDS,
        "supported_formats": ["mp4", "webm", "mov"],
        "max_quality": "1080p",
        "require_auth": True
    }


@router.post("/get-url/{video_id}")
async def get_video_url(
    video_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get a signed streaming URL for a video
    The URL expires after VIDEO_URL_EXPIRY_SECONDS
    """
    user_id = user.get("id")
    
    result = await get_video_stream_url(db, user_id, video_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Video not found"))
    
    return result


@router.get("/{token}")
async def stream_video(
    token: str,
    request: Request
):
    """
    Stream video content using signed token
    Supports range requests for seeking
    """
    # Validate token
    token_data = validate_video_token(token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid or expired video token")
    
    user_id = token_data["user_id"]
    video_id = token_data["video_id"]
    
    # Get video file path
    video = await db.user_videos.find_one({"_id": video_id, "user_id": user_id})
    if not video:
        video = await db.generated_videos.find_one({"_id": video_id, "user_id": user_id})
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    file_path = video.get("file_path")
    if not file_path or not await aiofiles.os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    
    # Get file info
    file_size = await aiofiles.os.path.getsize(file_path)
    content_type = mimetypes.guess_type(file_path)[0] or "video/mp4"
    
    # Handle range request
    range_header = request.headers.get("range")
    
    if range_header:
        # Parse range header
        range_match = range_header.replace("bytes=", "").split("-")
        start = int(range_match[0])
        end = int(range_match[1]) if range_match[1] else file_size - 1
        
        # Clamp values
        start = max(0, start)
        end = min(end, file_size - 1)
        chunk_size = end - start + 1
        
        # Log playback event
        await log_video_playback(db, user_id, video_id, "seek", start / file_size * 100)
        
        async def stream_range():
            async with aiofiles.open(file_path, "rb") as f:
                await f.seek(start)
                remaining = chunk_size
                while remaining > 0:
                    read_size = min(CHUNK_SIZE, remaining)
                    data = await f.read(read_size)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data
        
        return StreamingResponse(
            stream_range(),
            status_code=206,
            media_type=content_type,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(chunk_size),
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff"
            }
        )
    else:
        # Full file streaming
        await log_video_playback(db, user_id, video_id, "start", 0)
        
        async def stream_full():
            async with aiofiles.open(file_path, "rb") as f:
                while True:
                    data = await f.read(CHUNK_SIZE)
                    if not data:
                        break
                    yield data
        
        return StreamingResponse(
            stream_full(),
            media_type=content_type,
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff"
            }
        )


@router.post("/playback/{video_id}")
async def log_playback_event(
    video_id: str,
    event: str,
    position: float = 0,
    user: dict = Depends(get_current_user)
):
    """
    Log video playback events for analytics
    Events: start, pause, seek, complete, buffer
    """
    user_id = user.get("id")
    
    valid_events = ["start", "pause", "seek", "complete", "buffer", "error"]
    if event not in valid_events:
        raise HTTPException(status_code=400, detail="Invalid event type")
    
    await log_video_playback(db, user_id, video_id, event, position)
    
    return {"success": True, "logged": event}


@router.get("/stats/{video_id}")
async def get_video_stats(
    video_id: str,
    user: dict = Depends(get_current_user)
):
    """Get playback statistics for a video (owner only)"""
    user_id = user.get("id")
    
    # Verify ownership
    video = await db.user_videos.find_one({"_id": video_id, "user_id": user_id})
    if not video:
        video = await db.generated_videos.find_one({"_id": video_id, "user_id": user_id})
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Get playback logs
    pipeline = [
        {"$match": {"video_id": video_id}},
        {"$group": {
            "_id": "$event",
            "count": {"$sum": 1}
        }}
    ]
    
    events = await db.video_playback_logs.aggregate(pipeline).to_list(20)
    
    total_plays = await db.video_playback_logs.count_documents({
        "video_id": video_id,
        "event": "start"
    })
    
    completions = await db.video_playback_logs.count_documents({
        "video_id": video_id,
        "event": "complete"
    })
    
    return {
        "video_id": video_id,
        "total_plays": total_plays,
        "completions": completions,
        "completion_rate": (completions / total_plays * 100) if total_plays > 0 else 0,
        "events": {e["_id"]: e["count"] for e in events}
    }
