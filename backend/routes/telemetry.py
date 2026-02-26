"""
CreatorStudio AI - Feature Events & Session Tracking
=====================================================
Comprehensive telemetry system for tracking user behavior,
feature usage, and correlating with ratings.

Database Collections:
- sessions: User login sessions with location
- feature_events: All feature interactions
- ratings: Enhanced rating system with context
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user, get_optional_user, get_admin_user

router = APIRouter(prefix="/telemetry", tags=["Telemetry & Events"])


# ============================================
# MODELS
# ============================================

class FeatureEvent(BaseModel):
    """Track individual feature interactions"""
    featureKey: str = Field(..., description="Feature identifier (e.g., 'reel_generator', 'comic_storybook')")
    eventType: str = Field(..., description="Event type (OPENED, STARTED, SUCCESS, FAILED, etc.)")
    status: str = Field(default="SUCCESS", description="SUCCESS, FAILED, PENDING, PARTIAL")
    latencyMs: Optional[int] = Field(None, description="Request latency in milliseconds")
    errorCode: Optional[str] = Field(None, description="Standardized error code if failed")
    errorMessage: Optional[str] = Field(None, description="Human-readable error message")
    requestId: Optional[str] = Field(None, description="Request/job correlation ID")
    metadata: Optional[Dict] = Field(default_factory=dict, description="Additional context")

class EnhancedRating(BaseModel):
    """Enhanced rating with mandatory context for low ratings"""
    rating: int = Field(..., ge=1, le=5, description="Star rating 1-5")
    featureKey: str = Field(..., description="Feature being rated")
    reasonType: Optional[str] = Field(None, description="Issue category for 1-2 star ratings")
    comment: Optional[str] = Field(None, description="User comment (required for 1-2 stars)")
    relatedRequestId: Optional[str] = Field(None, description="Related job/payment/request ID")
    attachmentUrl: Optional[str] = Field(None, description="Screenshot attachment URL")

class SessionStart(BaseModel):
    """Session initialization data"""
    platform: str = Field(default="web", description="web, mobile, tablet")
    deviceType: Optional[str] = Field(None, description="Device type")
    browser: Optional[str] = Field(None, description="Browser name")
    screenResolution: Optional[str] = Field(None, description="Screen resolution")


# ============================================
# STANDARD ERROR CODES
# ============================================

ERROR_CODES = {
    "VALIDATION_ERROR": "Input validation failed",
    "PROVIDER_TIMEOUT": "AI/external provider timed out",
    "WORKER_FAILED": "Background worker job failed",
    "STORAGE_DOWNLOAD_FAILED": "File download/storage error",
    "UI_RENDER_FAILED": "UI rendering error",
    "PAYMENT_FAILED": "Payment processing failed",
    "CREDITS_INSUFFICIENT": "Not enough credits",
    "RATE_LIMITED": "Too many requests",
    "AUTH_FAILED": "Authentication failed",
    "UNKNOWN": "Unknown error"
}

FEATURE_KEYS = [
    "reel_generator",
    "story_generator", 
    "genstudio_t2i",
    "genstudio_t2v",
    "genstudio_i2v",
    "comic_storybook",
    "comix_ai",
    "twin_finder",
    "gif_maker",
    "billing",
    "profile",
    "dashboard",
    "export",
    "download"
]

REASON_TYPES = [
    "FEATURE_NOT_WORKING",
    "OUTPUT_QUALITY_POOR",
    "TOO_SLOW",
    "CREDITS_ISSUE",
    "UI_CONFUSING",
    "MISSING_FEATURE",
    "DOWNLOAD_FAILED",
    "PAYMENT_ISSUE",
    "OTHER"
]


# ============================================
# HELPER FUNCTIONS
# ============================================

def hash_ip(ip: str) -> str:
    """Hash IP for privacy - mask last octet and hash"""
    if not ip:
        return "unknown"
    parts = ip.split(".")
    if len(parts) == 4:
        masked = f"{parts[0]}.{parts[1]}.{parts[2]}.xxx"
    else:
        masked = ip[:len(ip)//2] + "xxx"
    return hashlib.sha256(masked.encode()).hexdigest()[:16]


async def get_location_from_ip(ip: str) -> Dict[str, str]:
    """Get approximate location from IP using ip-api.com"""
    if not ip or ip in ["127.0.0.1", "localhost"]:
        return {"country": "Local", "region": "", "city": ""}
    
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://ip-api.com/json/{ip}?fields=country,regionName,city", timeout=3.0)
            if response.status_code == 200:
                data = response.json()
                return {
                    "country": data.get("country", "Unknown"),
                    "region": data.get("regionName", ""),
                    "city": data.get("city", "")
                }
    except Exception as e:
        logger.warning(f"Geo lookup failed: {e}")
    
    return {"country": "Unknown", "region": "", "city": ""}


# ============================================
# SESSION ENDPOINTS
# ============================================

@router.post("/session/start")
async def start_session(
    request: Request,
    data: SessionStart,
    current_user: dict = Depends(get_optional_user)
):
    """
    Start a new tracking session for the user
    Called on app load/login
    """
    session_id = str(uuid.uuid4())
    user_id = current_user["id"] if current_user else None
    
    # Get client info
    client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
    if "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    
    user_agent = request.headers.get("User-Agent", "")
    
    # Get approximate location
    location = await get_location_from_ip(client_ip)
    
    session_doc = {
        "sessionId": session_id,
        "userId": user_id,
        "loginAt": datetime.now(timezone.utc).isoformat(),
        "lastSeenAt": datetime.now(timezone.utc).isoformat(),
        "logoutAt": None,
        "platform": data.platform,
        "deviceType": data.deviceType,
        "browser": data.browser,
        "screenResolution": data.screenResolution,
        "userAgent": user_agent[:200],  # Truncate
        "ipHash": hash_ip(client_ip),
        "location": location,
        "eventCount": 0,
        "featuresUsed": [],
        "lastFeature": None,
        "lastAction": None,
        "lastError": None
    }
    
    await db.sessions.insert_one(session_doc)
    
    return {
        "sessionId": session_id,
        "location": location
    }


@router.post("/session/heartbeat")
async def session_heartbeat(
    session_id: str = Query(...),
    current_user: dict = Depends(get_optional_user)
):
    """
    Update session last seen time
    Called periodically to track active sessions
    """
    await db.sessions.update_one(
        {"sessionId": session_id},
        {
            "$set": {
                "lastSeenAt": datetime.now(timezone.utc).isoformat(),
                "userId": current_user["id"] if current_user else None
            }
        }
    )
    return {"success": True}


@router.post("/session/end")
async def end_session(
    session_id: str = Query(...),
    current_user: dict = Depends(get_optional_user)
):
    """
    End a session (on logout or window close)
    """
    await db.sessions.update_one(
        {"sessionId": session_id},
        {
            "$set": {
                "logoutAt": datetime.now(timezone.utc).isoformat(),
                "lastSeenAt": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    return {"success": True}


# ============================================
# FEATURE EVENT TRACKING
# ============================================

@router.post("/event")
async def track_feature_event(
    request: Request,
    data: FeatureEvent,
    session_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_optional_user)
):
    """
    Track a feature event (open, generate, download, etc.)
    """
    user_id = current_user["id"] if current_user else None
    
    event_doc = {
        "eventId": str(uuid.uuid4()),
        "sessionId": session_id,
        "userId": user_id,
        "featureKey": data.featureKey,
        "eventType": data.eventType,
        "status": data.status,
        "latencyMs": data.latencyMs,
        "errorCode": data.errorCode if data.status == "FAILED" else None,
        "errorMessage": data.errorMessage[:500] if data.errorMessage else None,
        "requestId": data.requestId,
        "metadata": data.metadata or {},
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.feature_events.insert_one(event_doc)
    
    # Update session with latest activity
    if session_id:
        update = {
            "$set": {
                "lastSeenAt": datetime.now(timezone.utc).isoformat(),
                "lastFeature": data.featureKey,
                "lastAction": data.eventType
            },
            "$inc": {"eventCount": 1},
            "$addToSet": {"featuresUsed": data.featureKey}
        }
        
        if data.status == "FAILED":
            update["$set"]["lastError"] = {
                "code": data.errorCode,
                "message": data.errorMessage[:200] if data.errorMessage else None,
                "feature": data.featureKey,
                "time": datetime.now(timezone.utc).isoformat()
            }
        
        await db.sessions.update_one({"sessionId": session_id}, update)
    
    return {"success": True, "eventId": event_doc["eventId"]}


@router.post("/event/batch")
async def track_events_batch(
    events: List[FeatureEvent],
    session_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_optional_user)
):
    """
    Track multiple events in batch
    """
    user_id = current_user["id"] if current_user else None
    now = datetime.now(timezone.utc).isoformat()
    
    docs = []
    features_used = set()
    
    for event in events[:50]:  # Max 50 events per batch
        docs.append({
            "eventId": str(uuid.uuid4()),
            "sessionId": session_id,
            "userId": user_id,
            "featureKey": event.featureKey,
            "eventType": event.eventType,
            "status": event.status,
            "latencyMs": event.latencyMs,
            "errorCode": event.errorCode,
            "errorMessage": event.errorMessage[:500] if event.errorMessage else None,
            "requestId": event.requestId,
            "metadata": event.metadata or {},
            "createdAt": now
        })
        features_used.add(event.featureKey)
    
    if docs:
        await db.feature_events.insert_many(docs)
    
    # Update session
    if session_id and features_used:
        await db.sessions.update_one(
            {"sessionId": session_id},
            {
                "$set": {"lastSeenAt": now},
                "$inc": {"eventCount": len(docs)},
                "$addToSet": {"featuresUsed": {"$each": list(features_used)}}
            }
        )
    
    return {"success": True, "count": len(docs)}


# ============================================
# ENHANCED RATING SYSTEM
# ============================================

@router.post("/rating")
async def submit_enhanced_rating(
    data: EnhancedRating,
    session_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_optional_user)
):
    """
    Submit an enhanced rating with context
    
    For 1-2 star ratings:
    - reasonType is REQUIRED
    - comment is REQUIRED (min 10 chars)
    """
    # Validation for low ratings
    if data.rating <= 2:
        if not data.reasonType:
            raise HTTPException(
                status_code=400, 
                detail="Please select a reason for your low rating"
            )
        if not data.comment or len(data.comment.strip()) < 10:
            raise HTTPException(
                status_code=400,
                detail="Please provide at least 10 characters explaining the issue"
            )
    
    user_id = current_user["id"] if current_user else None
    user_email = current_user.get("email") if current_user else None
    user_name = current_user.get("name") if current_user else None
    
    # Get session context
    session_context = {}
    if session_id:
        session = await db.sessions.find_one({"sessionId": session_id}, {"_id": 0})
        if session:
            session_context = {
                "platform": session.get("platform"),
                "deviceType": session.get("deviceType"),
                "browser": session.get("browser"),
                "location": session.get("location"),
                "featuresUsed": session.get("featuresUsed", []),
                "lastError": session.get("lastError"),
                "sessionDurationMinutes": None
            }
            
            # Calculate session duration
            if session.get("loginAt"):
                try:
                    login = datetime.fromisoformat(session["loginAt"].replace("Z", "+00:00"))
                    duration = (datetime.now(timezone.utc) - login).total_seconds() / 60
                    session_context["sessionDurationMinutes"] = int(duration)
                except:
                    pass
    
    # Get related request context
    request_context = {}
    if data.relatedRequestId:
        # Try to find related job/generation/payment
        for collection_name in ["generations", "storybook_jobs", "payments"]:
            try:
                collection = getattr(db, collection_name)
                doc = await collection.find_one(
                    {"$or": [{"id": data.relatedRequestId}, {"jobId": data.relatedRequestId}]},
                    {"_id": 0, "status": 1, "error": 1, "type": 1, "createdAt": 1}
                )
                if doc:
                    request_context = {
                        "collection": collection_name,
                        "status": doc.get("status"),
                        "error": doc.get("error"),
                        "type": doc.get("type")
                    }
                    break
            except:
                pass
    
    rating_doc = {
        "ratingId": str(uuid.uuid4()),
        "userId": user_id,
        "userEmail": user_email,
        "userName": user_name,
        "sessionId": session_id,
        "featureKey": data.featureKey,
        "rating": data.rating,
        "reasonType": data.reasonType,
        "comment": data.comment,
        "attachmentUrl": data.attachmentUrl,
        "relatedRequestId": data.relatedRequestId,
        "sessionContext": session_context,
        "requestContext": request_context,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.ratings.insert_one(rating_doc)
    
    # Also store in legacy feedback for backwards compatibility
    await db.feedback.insert_one({
        "id": rating_doc["ratingId"],
        "type": "rating",
        "rating": data.rating,
        "category": data.featureKey,
        "message": data.comment,
        "email": user_email,
        "userId": user_id,
        "metadata": {
            "reasonType": data.reasonType,
            "sessionId": session_id,
            "relatedRequestId": data.relatedRequestId
        },
        "createdAt": rating_doc["createdAt"]
    })
    
    return {
        "success": True,
        "ratingId": rating_doc["ratingId"],
        "message": "Thank you for your feedback!"
    }


@router.get("/rating/config")
async def get_rating_config():
    """
    Get rating configuration (reason types, feature keys)
    """
    return {
        "reasonTypes": REASON_TYPES,
        "featureKeys": FEATURE_KEYS,
        "errorCodes": ERROR_CODES,
        "minCommentLength": 10,
        "requireReasonForRating": [1, 2]
    }


# ============================================
# INDEXES (Run on startup)
# ============================================

async def create_telemetry_indexes():
    """Create indexes for telemetry collections"""
    try:
        # Sessions indexes
        await db.sessions.create_index("sessionId", unique=True)
        await db.sessions.create_index("userId")
        await db.sessions.create_index("loginAt")
        await db.sessions.create_index([("userId", 1), ("loginAt", -1)])
        
        # Feature events indexes
        await db.feature_events.create_index("createdAt")
        await db.feature_events.create_index([("featureKey", 1), ("createdAt", -1)])
        await db.feature_events.create_index([("userId", 1), ("createdAt", -1)])
        await db.feature_events.create_index([("status", 1), ("featureKey", 1)])
        await db.feature_events.create_index("sessionId")
        
        # Ratings indexes
        await db.ratings.create_index("createdAt")
        await db.ratings.create_index([("featureKey", 1), ("createdAt", -1)])
        await db.ratings.create_index([("rating", 1), ("featureKey", 1)])
        await db.ratings.create_index([("userId", 1), ("createdAt", -1)])
        await db.ratings.create_index("sessionId")
        
        logger.info("Telemetry indexes created")
    except Exception as e:
        logger.warning(f"Index creation warning: {e}")


__all__ = [
    'router',
    'create_telemetry_indexes',
    'ERROR_CODES',
    'FEATURE_KEYS',
    'REASON_TYPES'
]
