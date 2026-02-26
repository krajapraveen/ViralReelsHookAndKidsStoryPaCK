"""
CreatorStudio AI - User Analytics & Ratings API
================================================
Comprehensive analytics for understanding user behavior, satisfaction, and feature usage.

Features:
- Rating distribution with user identification
- Feature usage tracking per user  
- Feature failure correlation with ratings
- Session analytics (login/logout duration)
- Geographic distribution (privacy-safe)
- Happiness analytics per feature
- Mandatory feedback for low ratings
- CSV export functionality

Admin Endpoints (A5):
- GET /admin/ratings/summary
- GET /admin/ratings/list
- GET /admin/users/:userId/sessions
- GET /admin/feature-events
- GET /admin/ratings/drilldown/:ratingId
- GET /admin/ratings/export/csv
"""
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import hashlib
import uuid
import os
import sys
import io
import csv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_admin_user, get_current_user

router = APIRouter(prefix="/admin/user-analytics", tags=["Admin - User Analytics"])

# Also create a user-facing router for submitting ratings
user_router = APIRouter(prefix="/user-analytics", tags=["User Analytics"])


# ============================================
# MODELS
# ============================================

class RatingReasonType:
    GENERATION_FAILED = "generation_failed"
    POOR_QUALITY = "poor_quality"
    TOO_SLOW = "too_slow"
    CONFUSING_UI = "confusing_ui"
    CREDITS_ISSUE = "credits_issue"
    DOWNLOAD_FAILED = "download_failed"
    OTHER = "other"


class RatingCreate(BaseModel):
    """Rating submission with mandatory feedback for 1-2 stars"""
    rating: int = Field(..., ge=1, le=5)
    feature_key: Optional[str] = None
    reason_type: Optional[str] = None  # Required for 1-2 stars
    comment: Optional[str] = None  # Required for 1-2 stars if reason_type is OTHER
    related_request_id: Optional[str] = None


class FeatureEventCreate(BaseModel):
    """Track a feature event"""
    feature_key: str
    event_type: str  # FEATURE_OPENED, GENERATE_CLICKED, GENERATION_SUCCESS, etc.
    status: Optional[str] = "success"
    latency_ms: Optional[int] = None
    error_code: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# ============================================
# HELPER FUNCTIONS
# ============================================

def hash_ip(ip_address: str) -> str:
    """Create a privacy-safe hash of IP address"""
    if not ip_address:
        return None
    # Use SHA256 with a salt for privacy
    salt = os.environ.get("IP_HASH_SALT", "creatorstudio_privacy_salt_2026")
    return hashlib.sha256(f"{salt}:{ip_address}".encode()).hexdigest()[:16]


async def get_approximate_location(ip_address: str) -> Dict[str, str]:
    """Get approximate location from IP (using cached geo data)"""
    if not ip_address:
        return {}
    
    try:
        # Check cache first
        ip_hash = hash_ip(ip_address)
        cached = await db.ip_geo_cache.find_one({"ip_hash": ip_hash}, {"_id": 0})
        if cached:
            return {
                "country": cached.get("country"),
                "region": cached.get("region"),
                "city": cached.get("city")
            }
        
        # Fetch from ip-api.com (free, 45 req/min)
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://ip-api.com/json/{ip_address}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                location = {
                    "country": data.get("country"),
                    "region": data.get("regionName"),
                    "city": data.get("city")
                }
                
                # Cache for 72 hours
                await db.ip_geo_cache.update_one(
                    {"ip_hash": ip_hash},
                    {"$set": {
                        "ip_hash": ip_hash,
                        **location,
                        "cached_at": datetime.now(timezone.utc).isoformat()
                    }},
                    upsert=True
                )
                
                return location
    except Exception as e:
        logger.warning(f"Geo lookup failed: {e}")
    
    return {}


async def get_user_info(user_id: str) -> Dict[str, Any]:
    """Get user details by ID"""
    if not user_id:
        return {"email": "Anonymous", "name": "Anonymous User", "plan": "unknown"}
    
    user = await db.users.find_one(
        {"id": user_id},
        {"_id": 0, "email": 1, "name": 1, "id": 1, "plan": 1, "role": 1}
    )
    return user or {"email": "Unknown", "name": "Unknown User", "plan": "unknown"}


async def get_session_for_user(user_id: str, around_time: str = None) -> Dict[str, Any]:
    """Get the session info for a user around a specific time"""
    if not user_id:
        return {}
    
    query = {"user_id": user_id}
    if around_time:
        query["login_at"] = {"$lte": around_time}
    
    session = await db.user_sessions.find_one(
        query,
        {"_id": 0},
        sort=[("login_at", -1)]
    )
    
    return session or {}


async def get_recent_feature_events(user_id: str, session_id: str = None, limit: int = 20) -> List[Dict]:
    """Get recent feature events for a user"""
    query = {"user_id": user_id}
    if session_id:
        query["session_id"] = session_id
    
    events = await db.feature_events.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return events


# ============================================
# USER-FACING ENDPOINTS (Rating Submission)
# ============================================

@user_router.post("/session/start")
async def start_session(request: Request, user: dict = Depends(get_current_user)):
    """Start a new user session for tracking"""
    try:
        # Get client info
        user_agent = request.headers.get("user-agent", "")
        ip_address = request.client.host if request.client else None
        
        # Determine device type from user agent
        device_type = "desktop"
        if "Mobile" in user_agent:
            device_type = "mobile"
        elif "Tablet" in user_agent or "iPad" in user_agent:
            device_type = "tablet"
        
        # Determine platform
        platform = f"web_{device_type}"
        
        # Get browser
        browser = "unknown"
        if "Chrome" in user_agent:
            browser = "Chrome"
        elif "Safari" in user_agent:
            browser = "Safari"
        elif "Firefox" in user_agent:
            browser = "Firefox"
        elif "Edge" in user_agent:
            browser = "Edge"
        
        # Get approximate location (privacy-safe)
        approx_location = await get_approximate_location(ip_address)
        
        session_id = str(uuid.uuid4())
        session = {
            "session_id": session_id,
            "user_id": user["id"],
            "login_at": datetime.now(timezone.utc).isoformat(),
            "logout_at": None,
            "device_type": device_type,
            "platform": platform,
            "browser": browser,
            "user_agent": user_agent[:500],  # Truncate
            "approx_location": approx_location,
            "ip_hash": hash_ip(ip_address)
        }
        
        await db.user_sessions.insert_one(session)
        
        return {"success": True, "session_id": session_id}
        
    except Exception as e:
        logger.error(f"Session start error: {e}")
        return {"success": False, "error": str(e)}


@user_router.post("/session/end")
async def end_session(session_id: str, user: dict = Depends(get_current_user)):
    """End a user session"""
    try:
        await db.user_sessions.update_one(
            {"session_id": session_id, "user_id": user["id"]},
            {"$set": {"logout_at": datetime.now(timezone.utc).isoformat()}}
        )
        return {"success": True}
    except Exception as e:
        logger.error(f"Session end error: {e}")
        return {"success": False, "error": str(e)}


@user_router.post("/event")
async def track_feature_event(
    data: FeatureEventCreate,
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Track a feature event (A4)"""
    try:
        # Get current session
        session = await get_session_for_user(user["id"])
        session_id = session.get("session_id")
        
        event = {
            "event_id": str(uuid.uuid4()),
            "session_id": session_id,
            "user_id": user["id"],
            "feature_key": data.feature_key,
            "event_type": data.event_type,
            "status": data.status or "success",
            "latency_ms": data.latency_ms,
            "error_code": data.error_code,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": data.metadata or {}
        }
        
        await db.feature_events.insert_one(event)
        
        return {"success": True, "event_id": event["event_id"]}
        
    except Exception as e:
        logger.error(f"Event tracking error: {e}")
        return {"success": False, "error": str(e)}


@user_router.post("/rating")
async def submit_rating(
    data: RatingCreate,
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Submit a rating with mandatory feedback for 1-2 stars (A3)"""
    try:
        # Enforce mandatory feedback for low ratings
        if data.rating <= 2:
            if not data.reason_type:
                raise HTTPException(
                    status_code=400,
                    detail="For ratings of 1-2 stars, please provide a reason for your feedback"
                )
            if data.reason_type == "other" and not data.comment:
                raise HTTPException(
                    status_code=400,
                    detail="Please provide a comment explaining your feedback"
                )
        
        # Get current session
        session = await get_session_for_user(user["id"])
        session_id = session.get("session_id")
        
        rating = {
            "rating_id": str(uuid.uuid4()),
            "user_id": user["id"],
            "session_id": session_id,
            "feature_key": data.feature_key,
            "rating": data.rating,
            "reason_type": data.reason_type,
            "comment": data.comment,
            "attachment_url": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "related_request_id": data.related_request_id
        }
        
        await db.ratings.insert_one(rating)
        
        # Also save to legacy feedback collection for backwards compatibility
        legacy_feedback = {
            "id": rating["rating_id"],
            "type": "rating",
            "rating": data.rating,
            "category": data.feature_key or "general",
            "message": data.comment,
            "suggestion": data.reason_type,
            "email": None,
            "userId": user["id"],
            "createdAt": rating["created_at"]
        }
        await db.feedback.insert_one(legacy_feedback)
        
        return {
            "success": True,
            "message": "Thank you for your feedback!",
            "rating_id": rating["rating_id"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rating submission error: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit rating")


@user_router.get("/rating-reasons")
async def get_rating_reasons():
    """Get available reasons for low ratings"""
    return {
        "reasons": [
            {"key": "generation_failed", "label": "Generation failed or errored"},
            {"key": "poor_quality", "label": "Output quality was poor"},
            {"key": "too_slow", "label": "Generation was too slow"},
            {"key": "confusing_ui", "label": "Interface was confusing"},
            {"key": "credits_issue", "label": "Credits or payment issue"},
            {"key": "download_failed", "label": "Download failed"},
            {"key": "other", "label": "Other (please specify)"}
        ]
    }


# ============================================
# ADMIN ENDPOINTS (A5)
# ============================================

@router.get("/ratings/summary")
async def get_ratings_summary(
    days: int = Query(default=30, ge=1, le=365),
    feature_key: Optional[str] = None,
    platform: Optional[str] = None,
    user_type: Optional[str] = None,
    current_user: dict = Depends(get_admin_user)
):
    """
    Get rating summary with filters (A1, A5)
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    # Build query
    query = {"created_at": {"$gte": cutoff}}
    if feature_key:
        query["feature_key"] = feature_key
    
    # Get ratings
    ratings = await db.ratings.find(query, {"_id": 0}).to_list(10000)
    
    # Filter by platform/user_type if needed (requires joining with sessions/users)
    if platform or user_type:
        filtered_ratings = []
        for r in ratings:
            include = True
            
            if platform and r.get("session_id"):
                session = await db.user_sessions.find_one(
                    {"session_id": r["session_id"]},
                    {"_id": 0, "platform": 1}
                )
                if session and session.get("platform") != platform:
                    include = False
            
            if user_type and r.get("user_id"):
                user = await db.users.find_one(
                    {"id": r["user_id"]},
                    {"_id": 0, "plan": 1}
                )
                if user and user.get("plan") != user_type:
                    include = False
            
            if include:
                filtered_ratings.append(r)
        
        ratings = filtered_ratings
    
    # Calculate metrics
    total = len(ratings)
    if total == 0:
        return {
            "period_days": days,
            "total_ratings": 0,
            "average_rating": 0,
            "distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            "nps_score": 0,
            "satisfaction_percentage": 0,
            "low_rating_count": 0,
            "low_rating_percentage": 0
        }
    
    # Distribution
    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in ratings:
        rating_val = r.get("rating", 0)
        if 1 <= rating_val <= 5:
            distribution[rating_val] += 1
    
    # Average
    avg_rating = sum(r.get("rating", 0) for r in ratings) / total
    
    # NPS Score
    promoters = distribution[5] + distribution[4]
    detractors = distribution[1] + distribution[2]
    nps = ((promoters - detractors) / total) * 100
    
    # Low ratings
    low_count = distribution[1] + distribution[2]
    
    return {
        "period_days": days,
        "total_ratings": total,
        "average_rating": round(avg_rating, 2),
        "distribution": distribution,
        "nps_score": round(nps, 1),
        "satisfaction_percentage": round((avg_rating / 5) * 100, 1),
        "low_rating_count": low_count,
        "low_rating_percentage": round((low_count / total) * 100, 1) if total > 0 else 0
    }


@router.get("/ratings/list")
async def get_ratings_list(
    days: int = Query(default=30, ge=1, le=365),
    rating_filter: Optional[int] = Query(default=None, ge=1, le=5),
    feature_key: Optional[str] = None,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=50, ge=1, le=100),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get paginated list of ratings with user details (A1, A5)
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    query = {"created_at": {"$gte": cutoff}}
    if rating_filter:
        query["rating"] = rating_filter
    if feature_key:
        query["feature_key"] = feature_key
    
    total = await db.ratings.count_documents(query)
    
    ratings = await db.ratings.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).skip(page * size).limit(size).to_list(size)
    
    # Enrich with user info
    enriched = []
    for r in ratings:
        user_info = await get_user_info(r.get("user_id"))
        session_info = await get_session_for_user(r.get("user_id"), r.get("created_at"))
        
        enriched.append({
            **r,
            "user_email": user_info.get("email"),
            "user_name": user_info.get("name"),
            "user_plan": user_info.get("plan"),
            "device_type": session_info.get("device_type"),
            "platform": session_info.get("platform"),
            "approx_location": session_info.get("approx_location")
        })
    
    return {
        "total": total,
        "page": page,
        "size": size,
        "ratings": enriched
    }


@router.get("/ratings/drilldown/{rating_id}")
async def get_rating_drilldown(
    rating_id: str,
    current_user: dict = Depends(get_admin_user)
):
    """
    Get detailed drilldown for a specific rating (A1 - WHY low rating)
    Shows user details, feature used, output status, error codes, session analytics
    """
    # Get the rating
    rating = await db.ratings.find_one({"rating_id": rating_id}, {"_id": 0})
    if not rating:
        raise HTTPException(status_code=404, detail="Rating not found")
    
    user_id = rating.get("user_id")
    session_id = rating.get("session_id")
    rating_time = rating.get("created_at")
    
    # Get user info
    user_info = await get_user_info(user_id)
    
    # Get session info
    session = await db.user_sessions.find_one(
        {"session_id": session_id} if session_id else {"user_id": user_id},
        {"_id": 0}
    )
    
    # Calculate session duration
    session_duration = None
    if session:
        login_at = session.get("login_at")
        logout_at = session.get("logout_at") or rating_time
        if login_at and logout_at:
            try:
                login_dt = datetime.fromisoformat(login_at.replace("Z", "+00:00"))
                logout_dt = datetime.fromisoformat(logout_at.replace("Z", "+00:00"))
                session_duration = int((logout_dt - login_dt).total_seconds() / 60)
            except:
                pass
    
    # Get feature events before rating
    events = []
    if session_id:
        events = await db.feature_events.find(
            {"session_id": session_id, "created_at": {"$lte": rating_time}},
            {"_id": 0}
        ).sort("created_at", -1).limit(20).to_list(20)
    elif user_id:
        events = await db.feature_events.find(
            {"user_id": user_id, "created_at": {"$lte": rating_time}},
            {"_id": 0}
        ).sort("created_at", -1).limit(20).to_list(20)
    
    # Extract error codes
    error_codes = list(set(e.get("error_code") for e in events if e.get("error_code")))
    
    # Determine output status from events
    output_status = "unknown"
    for e in events:
        if e.get("event_type") == "GENERATION_SUCCESS":
            output_status = "success"
            break
        elif e.get("event_type") == "GENERATION_FAILED":
            output_status = "failed"
            break
    
    # Get related generation if available
    related_gen = None
    if rating.get("related_request_id"):
        related_gen = await db.generations.find_one(
            {"id": rating["related_request_id"]},
            {"_id": 0, "type": 1, "status": 1, "error": 1, "created_at": 1}
        )
    
    return {
        "rating_id": rating_id,
        "user_id": user_id,
        "user_email": user_info.get("email"),
        "user_name": user_info.get("name"),
        "user_type": user_info.get("plan"),
        "rating": rating.get("rating"),
        "reason_type": rating.get("reason_type"),
        "comment": rating.get("comment"),
        "feature_key": rating.get("feature_key"),
        "created_at": rating_time,
        
        "session_id": session_id,
        "session_duration_minutes": session_duration,
        "device_type": session.get("device_type") if session else None,
        "platform": session.get("platform") if session else None,
        "browser": session.get("browser") if session else None,
        
        "approx_location": session.get("approx_location") if session else None,
        
        "feature_events_before_rating": events,
        "output_status": output_status,
        "error_codes": error_codes,
        
        "related_generation": related_gen
    }


@router.get("/users/{user_id}/sessions")
async def get_user_sessions(
    user_id: str,
    days: int = Query(default=30, ge=1, le=365),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get all sessions for a specific user (A5)
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    sessions = await db.user_sessions.find(
        {"user_id": user_id, "login_at": {"$gte": cutoff}},
        {"_id": 0}
    ).sort("login_at", -1).to_list(100)
    
    # Get user info
    user_info = await get_user_info(user_id)
    
    # Calculate metrics
    total_sessions = len(sessions)
    total_duration = 0
    locations = set()
    devices = set()
    
    for s in sessions:
        if s.get("login_at") and s.get("logout_at"):
            try:
                login_dt = datetime.fromisoformat(s["login_at"].replace("Z", "+00:00"))
                logout_dt = datetime.fromisoformat(s["logout_at"].replace("Z", "+00:00"))
                total_duration += (logout_dt - login_dt).total_seconds() / 60
            except:
                total_duration += 30  # Default
        else:
            total_duration += 30
        
        if s.get("approx_location", {}).get("country"):
            locations.add(s["approx_location"]["country"])
        if s.get("device_type"):
            devices.add(s["device_type"])
    
    return {
        "user_id": user_id,
        "user_email": user_info.get("email"),
        "user_name": user_info.get("name"),
        "total_sessions": total_sessions,
        "total_duration_minutes": int(total_duration),
        "avg_session_minutes": int(total_duration / total_sessions) if total_sessions > 0 else 0,
        "locations": list(locations),
        "devices": list(devices),
        "sessions": sessions
    }


@router.get("/feature-events")
async def get_feature_events(
    days: int = Query(default=7, ge=1, le=90),
    feature_key: Optional[str] = None,
    event_type: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=100, ge=1, le=500),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get feature events with filters (A5)
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    query = {"created_at": {"$gte": cutoff}}
    if feature_key:
        query["feature_key"] = feature_key
    if event_type:
        query["event_type"] = event_type
    if status:
        query["status"] = status
    
    total = await db.feature_events.count_documents(query)
    
    events = await db.feature_events.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).skip(page * size).limit(size).to_list(size)
    
    return {
        "total": total,
        "page": page,
        "size": size,
        "events": events
    }


@router.get("/feature-happiness")
async def get_feature_happiness_report(
    days: int = Query(default=30, ge=1, le=365),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get Happy vs Unhappy features report (A1)
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    # Get feature event aggregates
    pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {
            "_id": "$feature_key",
            "total_events": {"$sum": 1},
            "success_count": {"$sum": {"$cond": [{"$eq": ["$status", "success"]}, 1, 0]}},
            "failed_count": {"$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}},
            "avg_latency": {"$avg": "$latency_ms"}
        }}
    ]
    
    event_stats = await db.feature_events.aggregate(pipeline).to_list(100)
    
    # Get ratings per feature
    rating_pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}, "feature_key": {"$ne": None}}},
        {"$group": {
            "_id": "$feature_key",
            "avg_rating": {"$avg": "$rating"},
            "rating_count": {"$sum": 1},
            "low_ratings": {"$sum": {"$cond": [{"$lte": ["$rating", 2]}, 1, 0]}}
        }}
    ]
    
    rating_stats = await db.ratings.aggregate(rating_pipeline).to_list(100)
    rating_map = {r["_id"]: r for r in rating_stats}
    
    # Get common issues per feature
    issue_pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}, "reason_type": {"$ne": None}}},
        {"$group": {
            "_id": {"feature": "$feature_key", "reason": "$reason_type"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}}
    ]
    
    issues = await db.ratings.aggregate(issue_pipeline).to_list(200)
    issue_map = {}
    for i in issues:
        feature = i["_id"]["feature"]
        if feature not in issue_map:
            issue_map[feature] = []
        issue_map[feature].append({"reason": i["_id"]["reason"], "count": i["count"]})
    
    # Calculate happiness scores
    features = []
    for stat in event_stats:
        feature_key = stat["_id"]
        if not feature_key:
            continue
        
        total = stat["total_events"]
        success = stat["success_count"]
        failed = stat["failed_count"]
        
        success_rate = (success / total * 100) if total > 0 else 0
        
        rating_info = rating_map.get(feature_key, {})
        avg_rating = rating_info.get("avg_rating", 3.0)
        rating_count = rating_info.get("rating_count", 0)
        low_ratings = rating_info.get("low_ratings", 0)
        
        # Happiness score: weighted combination of success rate and rating
        happiness_score = (success_rate * 0.6) + ((avg_rating / 5) * 40)
        
        features.append({
            "feature_key": feature_key,
            "display_name": feature_key.replace("_", " ").title(),
            "total_uses": total,
            "success_count": success,
            "failure_count": failed,
            "success_rate": round(success_rate, 1),
            "avg_rating": round(avg_rating, 2),
            "rating_count": rating_count,
            "low_rating_count": low_ratings,
            "happiness_score": round(happiness_score, 1),
            "avg_latency_ms": round(stat.get("avg_latency") or 0),
            "common_issues": issue_map.get(feature_key, [])[:5]
        })
    
    # Sort by happiness score
    features.sort(key=lambda x: x["happiness_score"], reverse=True)
    
    # Split into happy/unhappy
    happy_features = [f for f in features if f["happiness_score"] >= 70]
    unhappy_features = [f for f in features if f["happiness_score"] < 70]
    unhappy_features.reverse()  # Most unhappy first
    
    return {
        "happy_features": happy_features[:10],
        "unhappy_features": unhappy_features[:10],
        "all_features": features,
        "period_days": days
    }


@router.get("/dashboard-summary")
async def get_dashboard_summary(
    days: int = Query(default=7, ge=1, le=90),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get summary data for analytics dashboard (A1)
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    # Ratings summary
    ratings_summary = await get_ratings_summary(days=days, current_user=current_user)
    
    # Session summary
    total_sessions = await db.user_sessions.count_documents({"login_at": {"$gte": cutoff}})
    unique_users = len(await db.user_sessions.distinct("user_id", {"login_at": {"$gte": cutoff}}))
    
    # Feature events summary
    total_events = await db.feature_events.count_documents({"created_at": {"$gte": cutoff}})
    failed_events = await db.feature_events.count_documents({
        "created_at": {"$gte": cutoff},
        "status": "failed"
    })
    
    # Low ratings needing attention
    low_ratings = await db.ratings.find(
        {"created_at": {"$gte": cutoff}, "rating": {"$lte": 2}},
        {"_id": 0, "rating_id": 1, "rating": 1, "feature_key": 1, "reason_type": 1, "created_at": 1}
    ).sort("created_at", -1).limit(10).to_list(10)
    
    return {
        "period_days": days,
        "ratings": ratings_summary,
        "sessions": {
            "total": total_sessions,
            "unique_users": unique_users
        },
        "events": {
            "total": total_events,
            "failed": failed_events,
            "failure_rate": round((failed_events / total_events * 100), 1) if total_events > 0 else 0
        },
        "low_ratings_requiring_attention": low_ratings
    }


@router.get("/ratings/export/csv")
async def export_ratings_csv(
    days: int = Query(default=30, ge=1, le=365),
    rating_filter: Optional[int] = Query(default=None, ge=1, le=5),
    current_user: dict = Depends(get_admin_user)
):
    """
    Export ratings data as CSV (A6)
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    query = {"created_at": {"$gte": cutoff}}
    if rating_filter:
        query["rating"] = rating_filter
    
    ratings = await db.ratings.find(query, {"_id": 0}).sort("created_at", -1).to_list(10000)
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "Rating ID", "User ID", "Rating", "Feature", "Reason Type", 
        "Comment", "Created At", "Session ID", "Related Request ID"
    ])
    
    # Data rows
    for r in ratings:
        writer.writerow([
            r.get("rating_id"),
            r.get("user_id"),
            r.get("rating"),
            r.get("feature_key"),
            r.get("reason_type"),
            r.get("comment", ""),
            r.get("created_at"),
            r.get("session_id"),
            r.get("related_request_id")
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=ratings_export_{datetime.now().strftime('%Y%m%d')}.csv"
        }
    )


@router.delete("/ratings/reset")
async def reset_all_ratings(
    confirm: bool = Query(default=False),
    current_user: dict = Depends(get_admin_user)
):
    """
    Reset/clear all ratings data (requested by user)
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Please confirm by adding ?confirm=true to the request"
        )
    
    # Delete all ratings
    ratings_result = await db.ratings.delete_many({})
    
    # Also clear legacy feedback ratings
    feedback_result = await db.feedback.delete_many({"type": "rating"})
    
    logger.info(f"Admin {current_user['email']} reset all ratings: {ratings_result.deleted_count} ratings, {feedback_result.deleted_count} feedback entries")
    
    return {
        "success": True,
        "deleted_ratings": ratings_result.deleted_count,
        "deleted_feedback": feedback_result.deleted_count,
        "message": "All ratings have been reset"
    }


# Create database indexes on startup
async def create_analytics_indexes():
    """Create indexes for analytics collections"""
    try:
        # User sessions indexes
        await db.user_sessions.create_index("session_id", unique=True)
        await db.user_sessions.create_index([("user_id", 1), ("login_at", -1)])
        await db.user_sessions.create_index("login_at")
        
        # Feature events indexes
        await db.feature_events.create_index("event_id", unique=True)
        await db.feature_events.create_index([("user_id", 1), ("created_at", -1)])
        await db.feature_events.create_index([("session_id", 1), ("created_at", -1)])
        await db.feature_events.create_index([("feature_key", 1), ("event_type", 1)])
        await db.feature_events.create_index("created_at")
        
        # Ratings indexes
        await db.ratings.create_index("rating_id", unique=True)
        await db.ratings.create_index([("user_id", 1), ("created_at", -1)])
        await db.ratings.create_index([("rating", 1), ("created_at", -1)])
        await db.ratings.create_index([("feature_key", 1), ("rating", 1)])
        await db.ratings.create_index("created_at")
        
        logger.info("Analytics indexes created successfully")
    except Exception as e:
        logger.warning(f"Analytics index creation warning: {e}")
