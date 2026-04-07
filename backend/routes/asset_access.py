"""
Asset Access Logging & Abuse Detection Middleware
Logs every preview/download/stream/signed-url-issue event.
Detects suspicious access patterns and rate-limits abusers.
"""
from fastapi import APIRouter, Request, Depends, HTTPException
from datetime import datetime, timezone, timedelta
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared import db, logger, get_current_user, get_admin_user

router = APIRouter(prefix="/asset-access", tags=["Asset Access"])

# Rate limits
SAME_ASSET_LIMIT = 20       # max accesses to same asset in window
CROSS_ASSET_LIMIT = 100     # max accesses across assets in window
SIGNED_URL_LIMIT = 30       # max signed URL generations in window
WINDOW_SECONDS = 300         # 5 minute window


async def log_asset_access(
    user_id: str,
    asset_id: str,
    action_type: str,
    ip: str = None,
    user_agent: str = None,
    session_id: str = None,
    meta: dict = None,
):
    """Log an asset access event. Called by other routes."""
    event = {
        "user_id": user_id,
        "asset_id": asset_id,
        "action_type": action_type,  # preview, stream, download, signed_url_issue
        "ip": ip,
        "user_agent": (user_agent or "")[:200],
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "meta": meta or {},
    }
    await db.asset_access_log.insert_one(event)


async def check_abuse(user_id: str, asset_id: str = None) -> dict:
    """Check if user is abusing asset access. Returns {blocked, reason}."""
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=WINDOW_SECONDS)).isoformat()

    # Check same-asset rate
    if asset_id:
        same_count = await db.asset_access_log.count_documents({
            "user_id": user_id,
            "asset_id": asset_id,
            "timestamp": {"$gte": cutoff},
        })
        if same_count >= SAME_ASSET_LIMIT:
            await _flag_abuse(user_id, "same_asset_flood", asset_id, same_count)
            return {"blocked": True, "reason": "Too many requests for this asset. Please try again later."}

    # Check cross-asset rate
    cross_count = await db.asset_access_log.count_documents({
        "user_id": user_id,
        "timestamp": {"$gte": cutoff},
    })
    if cross_count >= CROSS_ASSET_LIMIT:
        await _flag_abuse(user_id, "cross_asset_flood", None, cross_count)
        return {"blocked": True, "reason": "Too many asset requests. Please try again later."}

    # Check signed URL generation rate
    signed_count = await db.asset_access_log.count_documents({
        "user_id": user_id,
        "action_type": "signed_url_issue",
        "timestamp": {"$gte": cutoff},
    })
    if signed_count >= SIGNED_URL_LIMIT:
        await _flag_abuse(user_id, "signed_url_abuse", None, signed_count)
        return {"blocked": True, "reason": "Too many download requests. Please try again later."}

    return {"blocked": False, "reason": None}


async def _flag_abuse(user_id: str, abuse_type: str, asset_id: str, count: int):
    """Record an abuse event for admin review."""
    await db.abuse_events.insert_one({
        "user_id": user_id,
        "abuse_type": abuse_type,
        "asset_id": asset_id,
        "count": count,
        "window_seconds": WINDOW_SECONDS,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    logger.warning(f"Abuse detected: user={user_id} type={abuse_type} count={count}")


@router.get("/admin/abuse-log")
async def get_abuse_log(
    user: dict = Depends(get_admin_user),
    limit: int = 50,
):
    """Admin: view recent abuse events."""
    events = await db.abuse_events.find(
        {}, {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    return {"events": events, "count": len(events)}


@router.get("/admin/access-stats")
async def get_access_stats(
    user: dict = Depends(get_admin_user),
    hours: int = 24,
):
    """Admin: asset access statistics."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    pipeline = [
        {"$match": {"timestamp": {"$gte": cutoff}}},
        {"$group": {"_id": "$action_type", "count": {"$sum": 1}}},
    ]
    by_type = {}
    async for doc in db.asset_access_log.aggregate(pipeline):
        by_type[doc["_id"]] = doc["count"]

    total = sum(by_type.values())
    abuse_count = await db.abuse_events.count_documents({"timestamp": {"$gte": cutoff}})

    return {
        "period_hours": hours,
        "total_accesses": total,
        "by_action_type": by_type,
        "abuse_events": abuse_count,
    }
