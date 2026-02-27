"""
Video Streaming Protection Service
- Secure video delivery
- Signed streaming URLs
- Access logging
- No raw file URL exposure
"""
import hashlib
import hmac
import time
import base64
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from bson import ObjectId

# Configuration
VIDEO_URL_SECRET = "video-streaming-secret-key-2026-secure"
VIDEO_URL_EXPIRY_SECONDS = 300  # 5 minutes for video streaming
CHUNK_SIZE = 1024 * 1024  # 1MB chunks

def generate_video_token(
    user_id: str,
    video_id: str,
    expiry_seconds: int = VIDEO_URL_EXPIRY_SECONDS
) -> str:
    """Generate signed token for video streaming"""
    expiry_time = int(time.time()) + expiry_seconds
    message = f"video:{user_id}:{video_id}:{expiry_time}"
    signature = hmac.new(
        VIDEO_URL_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()[:20]
    
    token = base64.urlsafe_b64encode(f"{message}:{signature}".encode()).decode()
    return token

def validate_video_token(token: str) -> Optional[Dict[str, str]]:
    """Validate video streaming token"""
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        parts = decoded.split(":")
        
        if len(parts) != 5 or parts[0] != "video":
            return None
        
        _, user_id, video_id, expiry_str, signature = parts
        expiry_time = int(expiry_str)
        
        # Check expiry
        if time.time() > expiry_time:
            return None
        
        # Verify signature
        message = f"video:{user_id}:{video_id}:{expiry_time}"
        expected_signature = hmac.new(
            VIDEO_URL_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()[:20]
        
        if not hmac.compare_digest(signature, expected_signature):
            return None
        
        return {"user_id": user_id, "video_id": video_id}
    except Exception:
        return None

async def get_video_stream_url(
    db,
    user_id: str,
    video_id: str
) -> Dict[str, Any]:
    """Get secure streaming URL for video"""
    
    # Verify user owns this video
    video = await db.user_videos.find_one({
        "_id": ObjectId(video_id),
        "user_id": user_id
    })
    
    if not video:
        video = await db.generated_videos.find_one({
            "_id": ObjectId(video_id),
            "user_id": user_id
        })
    
    if not video:
        return {"success": False, "error": "Video not found or access denied"}
    
    # Generate streaming token
    token = generate_video_token(user_id, video_id)
    
    # Log access
    await db.video_access_logs.insert_one({
        "user_id": user_id,
        "video_id": video_id,
        "action": "stream_url_generated",
        "timestamp": datetime.now(timezone.utc)
    })
    
    return {
        "success": True,
        "stream_url": f"/api/video-stream/{token}",
        "expires_in": VIDEO_URL_EXPIRY_SECONDS,
        "video_info": {
            "id": video_id,
            "title": video.get("title", "Video"),
            "duration": video.get("duration"),
            "format": video.get("format", "mp4")
        }
    }

async def log_video_playback(
    db,
    user_id: str,
    video_id: str,
    event: str,
    position: float = 0
):
    """Log video playback events"""
    await db.video_playback_logs.insert_one({
        "user_id": user_id,
        "video_id": video_id,
        "event": event,  # start, pause, seek, complete
        "position": position,
        "timestamp": datetime.now(timezone.utc)
    })

class VideoStreamConfig:
    """Video streaming configuration"""
    ALLOWED_FORMATS = ["mp4", "webm", "mov"]
    MAX_QUALITY = "1080p"
    ENABLE_WATERMARK = True
    ENABLE_DRM = False  # Not implementing full DRM
    
    # Rate limiting
    MAX_CONCURRENT_STREAMS = 3
    STREAM_RATE_LIMIT = 100  # requests per minute
    
    # Security
    REQUIRE_AUTH = True
    LOG_ALL_ACCESS = True
    BLOCK_DOWNLOAD_BUTTON = True
