"""
CreatorStudio AI - User Analytics & Feedback API
=================================================
Comprehensive analytics for understanding user behavior, satisfaction, and feature usage.

Features:
- Rating distribution with user identification
- Feature usage tracking per user
- Feature failure correlation with ratings
- Session analytics (login/logout duration)
- Geographic distribution
- Happiness analytics per feature
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_admin_user

router = APIRouter(prefix="/admin/user-analytics", tags=["Admin - User Analytics"])


# ============================================
# MODELS
# ============================================

class UserFeedbackDetail(BaseModel):
    user_id: Optional[str]
    email: Optional[str]
    name: Optional[str]
    rating: int
    comment: Optional[str]
    feature_used: Optional[str]
    feature_failed: Optional[str]
    created_at: str
    session_duration_minutes: Optional[int]
    location: Optional[Dict[str, str]]


class FeatureHappinessScore(BaseModel):
    feature: str
    total_uses: int
    success_count: int
    failure_count: int
    average_rating: float
    happiness_score: float  # Calculated as (success_rate * avg_rating) / 5
    common_issues: List[str]


# ============================================
# HELPER FUNCTIONS
# ============================================

async def get_user_info(user_id: str) -> Dict[str, Any]:
    """Get user details by ID"""
    if not user_id:
        return {"email": "Anonymous", "name": "Anonymous User"}
    
    user = await db.users.find_one(
        {"id": user_id},
        {"_id": 0, "email": 1, "name": 1, "id": 1}
    )
    return user or {"email": "Unknown", "name": "Unknown User"}


async def get_user_session_info(user_id: str, feedback_time: str) -> Dict[str, Any]:
    """Get session info for a user around the time of feedback"""
    if not user_id or not feedback_time:
        return {}
    
    try:
        feedback_dt = datetime.fromisoformat(feedback_time.replace("Z", "+00:00"))
        
        # Find the login activity closest to feedback time
        session = await db.login_activity.find_one(
            {
                "user_id": user_id,
                "status": "SUCCESS",
                "timestamp": {"$lte": feedback_time}
            },
            {"_id": 0},
            sort=[("timestamp", -1)]
        )
        
        if session:
            login_time = datetime.fromisoformat(session.get("timestamp", "").replace("Z", "+00:00"))
            duration = (feedback_dt - login_time).total_seconds() / 60
            
            return {
                "session_duration_minutes": int(duration),
                "location": {
                    "country": session.get("country"),
                    "city": session.get("city"),
                    "region": session.get("region")
                },
                "device": session.get("device_type"),
                "browser": session.get("browser"),
                "ip_address": session.get("ip_address")
            }
    except Exception as e:
        logger.warning(f"Error getting session info: {e}")
    
    return {}


async def get_user_feature_usage(user_id: str, before_time: str = None) -> Dict[str, Any]:
    """Get features used by a user before giving feedback"""
    if not user_id:
        return {"features_used": [], "features_failed": []}
    
    query = {"user_id": user_id}
    if before_time:
        query["created_at"] = {"$lte": before_time}
    
    # Get recent generations (features used)
    generations = await db.generations.find(
        query,
        {"_id": 0, "type": 1, "status": 1, "created_at": 1}
    ).sort("created_at", -1).limit(20).to_list(20)
    
    features_used = []
    features_failed = []
    
    for gen in generations:
        feature = gen.get("type", "unknown")
        if feature not in features_used:
            features_used.append(feature)
        
        if gen.get("status") in ["failed", "error"]:
            if feature not in features_failed:
                features_failed.append(feature)
    
    return {
        "features_used": features_used,
        "features_failed": features_failed
    }


# ============================================
# ENDPOINTS
# ============================================

@router.get("/feedback-details")
async def get_detailed_feedback(
    days: int = Query(default=30, ge=1, le=365),
    min_rating: Optional[int] = Query(default=None, ge=1, le=5),
    max_rating: Optional[int] = Query(default=None, ge=1, le=5),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get detailed feedback with user identification, feature usage, and session info
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    query = {"rating": {"$exists": True}}
    if min_rating:
        query["rating"] = {"$gte": min_rating}
    if max_rating:
        query.setdefault("rating", {})["$lte"] = max_rating
    
    feedbacks = await db.feedback.find(
        query,
        {"_id": 0}
    ).sort("createdAt", -1).limit(500).to_list(500)
    
    detailed_feedbacks = []
    
    for fb in feedbacks:
        user_id = fb.get("userId")
        feedback_time = fb.get("createdAt", "")
        
        # Get user info
        user_info = await get_user_info(user_id)
        
        # Get session info
        session_info = await get_user_session_info(user_id, feedback_time)
        
        # Get feature usage
        feature_usage = await get_user_feature_usage(user_id, feedback_time)
        
        detailed_feedbacks.append({
            "feedback_id": fb.get("id"),
            "user_id": user_id,
            "email": fb.get("email") or user_info.get("email"),
            "name": user_info.get("name", "Unknown"),
            "rating": fb.get("rating"),
            "comment": fb.get("message") or fb.get("suggestion", "No comment provided"),
            "category": fb.get("category"),
            "features_used": feature_usage.get("features_used", []),
            "features_failed": feature_usage.get("features_failed", []),
            "session_duration_minutes": session_info.get("session_duration_minutes"),
            "location": session_info.get("location"),
            "device": session_info.get("device"),
            "browser": session_info.get("browser"),
            "created_at": feedback_time
        })
    
    return {
        "total": len(detailed_feedbacks),
        "feedbacks": detailed_feedbacks
    }


@router.get("/feature-happiness")
async def get_feature_happiness_scores(
    days: int = Query(default=30, ge=1, le=365),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get happiness scores for each feature based on success rate and user ratings
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    # Get all generation types and their success/failure counts
    pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {
            "_id": "$type",
            "total": {"$sum": 1},
            "success": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}},
            "failed": {"$sum": {"$cond": [{"$in": ["$status", ["failed", "error"]]}, 1, 0]}}
        }}
    ]
    
    generation_stats = await db.generations.aggregate(pipeline).to_list(100)
    
    # Get feedback ratings correlated with features
    feature_ratings = {}
    feedbacks = await db.feedback.find(
        {"rating": {"$exists": True}, "createdAt": {"$gte": cutoff}},
        {"_id": 0, "userId": 1, "rating": 1, "createdAt": 1, "message": 1}
    ).to_list(500)
    
    for fb in feedbacks:
        user_id = fb.get("userId")
        if user_id:
            # Get features used by this user
            usage = await get_user_feature_usage(user_id, fb.get("createdAt"))
            for feature in usage.get("features_used", []):
                if feature not in feature_ratings:
                    feature_ratings[feature] = {"ratings": [], "issues": []}
                feature_ratings[feature]["ratings"].append(fb.get("rating", 0))
                
                # If low rating and feature failed, track the issue
                if fb.get("rating", 5) <= 2 and feature in usage.get("features_failed", []):
                    issue = fb.get("message", "Unknown issue")[:100]
                    if issue and issue not in feature_ratings[feature]["issues"]:
                        feature_ratings[feature]["issues"].append(issue)
    
    # Calculate happiness scores
    happiness_data = []
    
    for stat in generation_stats:
        feature = stat["_id"] or "unknown"
        total = stat["total"]
        success = stat["success"]
        failed = stat["failed"]
        
        success_rate = (success / total) * 100 if total > 0 else 0
        
        # Get average rating for this feature
        ratings = feature_ratings.get(feature, {}).get("ratings", [])
        avg_rating = sum(ratings) / len(ratings) if ratings else 3.0  # Default to 3 if no ratings
        
        # Calculate happiness score (0-100)
        happiness_score = (success_rate * 0.6) + ((avg_rating / 5) * 40)
        
        happiness_data.append({
            "feature": feature,
            "display_name": feature.replace("_", " ").title(),
            "total_uses": total,
            "success_count": success,
            "failure_count": failed,
            "success_rate": round(success_rate, 1),
            "average_rating": round(avg_rating, 2),
            "happiness_score": round(happiness_score, 1),
            "common_issues": feature_ratings.get(feature, {}).get("issues", [])[:5],
            "rating_count": len(ratings)
        })
    
    # Sort by happiness score
    happiness_data.sort(key=lambda x: x["happiness_score"], reverse=True)
    
    # Separate into happy and unhappy features
    happy_features = [f for f in happiness_data if f["happiness_score"] >= 70]
    unhappy_features = [f for f in happiness_data if f["happiness_score"] < 70]
    unhappy_features.reverse()  # Most unhappy first
    
    return {
        "happy_features": happy_features[:10],
        "unhappy_features": unhappy_features[:10],
        "all_features": happiness_data,
        "period_days": days
    }


@router.get("/user-sessions")
async def get_user_sessions_analytics(
    days: int = Query(default=7, ge=1, le=90),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get session analytics including duration, location, and activity
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    # Get login activities
    sessions = await db.login_activity.find(
        {
            "status": "SUCCESS",
            "timestamp": {"$gte": cutoff}
        },
        {"_id": 0}
    ).sort("timestamp", -1).limit(500).to_list(500)
    
    # Group sessions by user
    user_sessions = {}
    for session in sessions:
        user_id = session.get("user_id")
        if not user_id:
            continue
        
        if user_id not in user_sessions:
            user_sessions[user_id] = {
                "sessions": [],
                "locations": set(),
                "devices": set(),
                "total_duration": 0
            }
        
        user_sessions[user_id]["sessions"].append(session)
        
        if session.get("country"):
            user_sessions[user_id]["locations"].add(f"{session.get('city', 'Unknown')}, {session.get('country')}")
        if session.get("device_type"):
            user_sessions[user_id]["devices"].add(session.get("device_type"))
    
    # Calculate session durations and compile results
    session_analytics = []
    
    for user_id, data in user_sessions.items():
        user_info = await get_user_info(user_id)
        
        # Estimate session duration (time between consecutive logins or 30 min default)
        total_duration = 0
        for i, sess in enumerate(data["sessions"]):
            if i + 1 < len(data["sessions"]):
                try:
                    current = datetime.fromisoformat(sess["timestamp"].replace("Z", "+00:00"))
                    next_sess = datetime.fromisoformat(data["sessions"][i + 1]["timestamp"].replace("Z", "+00:00"))
                    duration = (current - next_sess).total_seconds() / 60
                    if duration > 0 and duration < 480:  # Max 8 hours
                        total_duration += duration
                except:
                    total_duration += 30  # Default 30 min
            else:
                total_duration += 30
        
        latest_session = data["sessions"][0] if data["sessions"] else {}
        
        session_analytics.append({
            "user_id": user_id,
            "email": user_info.get("email"),
            "name": user_info.get("name"),
            "session_count": len(data["sessions"]),
            "total_duration_minutes": int(total_duration),
            "avg_session_minutes": int(total_duration / len(data["sessions"])) if data["sessions"] else 0,
            "locations": list(data["locations"])[:5],
            "devices": list(data["devices"]),
            "last_login": latest_session.get("timestamp"),
            "last_location": {
                "country": latest_session.get("country"),
                "city": latest_session.get("city"),
                "region": latest_session.get("region")
            },
            "last_device": latest_session.get("device_type"),
            "last_browser": latest_session.get("browser")
        })
    
    # Sort by session count
    session_analytics.sort(key=lambda x: x["session_count"], reverse=True)
    
    # Calculate summary stats
    total_sessions = sum(u["session_count"] for u in session_analytics)
    avg_duration = sum(u["avg_session_minutes"] for u in session_analytics) / len(session_analytics) if session_analytics else 0
    
    # Location distribution
    location_counts = {}
    for user in session_analytics:
        for loc in user["locations"]:
            country = loc.split(", ")[-1] if ", " in loc else loc
            location_counts[country] = location_counts.get(country, 0) + 1
    
    top_locations = sorted(location_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        "summary": {
            "total_users": len(session_analytics),
            "total_sessions": total_sessions,
            "avg_session_duration_minutes": round(avg_duration, 1),
            "top_locations": [{"country": loc, "count": count} for loc, count in top_locations]
        },
        "users": session_analytics[:100],
        "period_days": days
    }


@router.get("/rating-users")
async def get_users_who_rated(
    rating: Optional[int] = Query(default=None, ge=1, le=5),
    days: int = Query(default=30, ge=1, le=365),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get list of users who provided ratings with their details
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    query = {"rating": {"$exists": True}, "createdAt": {"$gte": cutoff}}
    if rating:
        query["rating"] = rating
    
    feedbacks = await db.feedback.find(
        query,
        {"_id": 0}
    ).sort("createdAt", -1).to_list(500)
    
    rating_users = []
    
    for fb in feedbacks:
        user_id = fb.get("userId")
        user_info = await get_user_info(user_id) if user_id else {"email": fb.get("email"), "name": "Guest"}
        session_info = await get_user_session_info(user_id, fb.get("createdAt")) if user_id else {}
        feature_usage = await get_user_feature_usage(user_id, fb.get("createdAt")) if user_id else {}
        
        rating_users.append({
            "user_id": user_id,
            "email": fb.get("email") or user_info.get("email"),
            "name": user_info.get("name", "Guest"),
            "rating": fb.get("rating"),
            "comment": fb.get("message") or fb.get("suggestion", "No comment"),
            "features_used": feature_usage.get("features_used", []),
            "features_failed": feature_usage.get("features_failed", []),
            "session_duration": session_info.get("session_duration_minutes"),
            "location": session_info.get("location"),
            "device": session_info.get("device"),
            "rated_at": fb.get("createdAt")
        })
    
    # Group by rating
    by_rating = {1: [], 2: [], 3: [], 4: [], 5: []}
    for user in rating_users:
        r = user.get("rating", 0)
        if 1 <= r <= 5:
            by_rating[r].append(user)
    
    return {
        "total_ratings": len(rating_users),
        "by_rating": {
            "5_star": len(by_rating[5]),
            "4_star": len(by_rating[4]),
            "3_star": len(by_rating[3]),
            "2_star": len(by_rating[2]),
            "1_star": len(by_rating[1])
        },
        "users": rating_users,
        "period_days": days
    }


@router.get("/feature-failures")
async def get_feature_failures(
    days: int = Query(default=7, ge=1, le=90),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get features that failed for users, correlated with their ratings
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    # Get failed generations
    failures = await db.generations.find(
        {
            "status": {"$in": ["failed", "error"]},
            "created_at": {"$gte": cutoff}
        },
        {"_id": 0, "user_id": 1, "type": 1, "error": 1, "created_at": 1}
    ).sort("created_at", -1).limit(500).to_list(500)
    
    # Group by feature and get user feedback
    feature_failures = {}
    
    for fail in failures:
        feature = fail.get("type", "unknown")
        user_id = fail.get("user_id")
        
        if feature not in feature_failures:
            feature_failures[feature] = {
                "total_failures": 0,
                "affected_users": set(),
                "errors": [],
                "user_ratings": []
            }
        
        feature_failures[feature]["total_failures"] += 1
        if user_id:
            feature_failures[feature]["affected_users"].add(user_id)
        
        error = fail.get("error", "Unknown error")[:100]
        if error not in feature_failures[feature]["errors"]:
            feature_failures[feature]["errors"].append(error)
    
    # Get user ratings for affected users
    for feature, data in feature_failures.items():
        for user_id in data["affected_users"]:
            user_feedback = await db.feedback.find_one(
                {"userId": user_id, "rating": {"$exists": True}},
                {"_id": 0, "rating": 1}
            )
            if user_feedback:
                data["user_ratings"].append(user_feedback.get("rating", 0))
    
    # Compile results
    results = []
    for feature, data in feature_failures.items():
        avg_rating = sum(data["user_ratings"]) / len(data["user_ratings"]) if data["user_ratings"] else None
        
        results.append({
            "feature": feature,
            "display_name": feature.replace("_", " ").title(),
            "total_failures": data["total_failures"],
            "affected_users_count": len(data["affected_users"]),
            "common_errors": data["errors"][:5],
            "avg_user_rating": round(avg_rating, 2) if avg_rating else "No ratings",
            "impact_severity": "High" if data["total_failures"] > 10 or (avg_rating and avg_rating < 3) else "Medium" if data["total_failures"] > 5 else "Low"
        })
    
    # Sort by failure count
    results.sort(key=lambda x: x["total_failures"], reverse=True)
    
    return {
        "total_failures": sum(r["total_failures"] for r in results),
        "total_affected_users": len(set().union(*[set(d["affected_users"]) for d in feature_failures.values()])) if feature_failures else 0,
        "features": results,
        "period_days": days
    }


@router.get("/dashboard-summary")
async def get_analytics_dashboard_summary(
    days: int = Query(default=7, ge=1, le=90),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get summary dashboard data for user analytics
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    # Total ratings
    total_ratings = await db.feedback.count_documents({"rating": {"$exists": True}, "createdAt": {"$gte": cutoff}})
    
    # Average rating
    ratings_list = await db.feedback.find(
        {"rating": {"$exists": True}, "createdAt": {"$gte": cutoff}},
        {"_id": 0, "rating": 1}
    ).to_list(1000)
    avg_rating = sum(r.get("rating", 0) for r in ratings_list) / len(ratings_list) if ratings_list else 0
    
    # Rating distribution
    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in ratings_list:
        rating = r.get("rating", 0)
        if 1 <= rating <= 5:
            distribution[rating] += 1
    
    # Total sessions
    total_sessions = await db.login_activity.count_documents({"status": "SUCCESS", "timestamp": {"$gte": cutoff}})
    
    # Unique users who logged in
    unique_users = len(await db.login_activity.distinct("user_id", {"status": "SUCCESS", "timestamp": {"$gte": cutoff}}))
    
    # Total failures
    total_failures = await db.generations.count_documents({"status": {"$in": ["failed", "error"]}, "created_at": {"$gte": cutoff}})
    
    # NPS calculation
    promoters = distribution.get(5, 0) + distribution.get(4, 0)
    detractors = distribution.get(1, 0) + distribution.get(2, 0)
    nps = ((promoters - detractors) / total_ratings * 100) if total_ratings > 0 else 0
    
    return {
        "period_days": days,
        "ratings": {
            "total": total_ratings,
            "average": round(avg_rating, 2),
            "distribution": distribution,
            "nps_score": round(nps, 1)
        },
        "sessions": {
            "total": total_sessions,
            "unique_users": unique_users
        },
        "failures": {
            "total": total_failures
        },
        "satisfaction_percentage": round((avg_rating / 5) * 100, 1) if avg_rating else 0
    }
