"""
Admin Media Security — Dashboard endpoints for media access oversight.

Provides: overview stats, access event logs, abuse flags management,
per-user investigation, token revocation, and user suspension.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from shared import db, get_admin_user
from services.media_token_service import (
    revoke_user_tokens, suspend_user_media, unsuspend_user_media,
)

logger = logging.getLogger("creatorstudio.media_admin")
router = APIRouter(prefix="/admin/media", tags=["Admin Media Security"])


@router.get("/overview")
async def media_overview(hours: int = 24, admin: dict = Depends(get_admin_user)):
    """Overview: tokens issued, downloads, denials, flags."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    pipeline = [
        {"$match": {"timestamp": {"$gte": since}}},
        {"$group": {"_id": "$action", "count": {"$sum": 1}, "users": {"$addToSet": "$user_id"}}},
    ]
    action_results = await db.media_access_log.aggregate(pipeline).to_list(50)
    action_summary = {}
    for r in action_results:
        action_summary[r["_id"]] = {"count": r["count"], "unique_users": len(r["users"])}

    # Top risk users (most download tokens)
    top_pipeline = [
        {"$match": {"timestamp": {"$gte": since}, "action": {"$in": ["download_token_issued", "download_token"]}}},
        {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}, {"$limit": 10},
    ]
    top_users = await db.media_access_log.aggregate(top_pipeline).to_list(10)

    denied = await db.media_access_log.count_documents({
        "timestamp": {"$gte": since},
        "action": {"$in": ["download_denied", "download_rate_limited"]},
    })
    open_flags = await db.media_abuse_flags.count_documents({"status": "open"})
    active_tokens = await db.media_tokens.count_documents({"status": "active", "expires_at": {"$gt": datetime.now(timezone.utc)}})
    active_sessions = await db.user_media_sessions.count_documents({
        "status": "active", "last_active": {"$gte": datetime.now(timezone.utc) - timedelta(minutes=10)},
    })
    active_suspensions = await db.media_suspensions.count_documents({
        "status": "active", "expires_at": {"$gt": datetime.now(timezone.utc)},
    })

    return {
        "hours": hours,
        "action_summary": action_summary,
        "top_risk_users": [{"user_id": u["_id"], "downloads": u["count"]} for u in top_users],
        "denied_events": denied,
        "open_abuse_flags": open_flags,
        "active_tokens": active_tokens,
        "active_sessions": active_sessions,
        "active_suspensions": active_suspensions,
    }


@router.get("/access-events")
async def media_access_events(
    user_id: Optional[str] = None, action: Optional[str] = None,
    hours: int = 24, limit: int = 100,
    admin: dict = Depends(get_admin_user),
):
    """Detailed access event log with filters."""
    query = {"timestamp": {"$gte": datetime.now(timezone.utc) - timedelta(hours=hours)}}
    if user_id:
        query["user_id"] = user_id
    if action:
        query["action"] = action

    logs = await db.media_access_log.find(query, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    for log in logs:
        if isinstance(log.get("timestamp"), datetime):
            log["timestamp"] = log["timestamp"].isoformat()
    return {"events": logs, "count": len(logs)}


@router.get("/abuse-flags")
async def media_abuse_flags(status: str = "open", limit: int = 50, admin: dict = Depends(get_admin_user)):
    query = {} if status == "all" else {"status": status}
    flags = await db.media_abuse_flags.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    for f in flags:
        if isinstance(f.get("created_at"), datetime):
            f["created_at"] = f["created_at"].isoformat()
    return {"flags": flags, "count": len(flags)}


@router.get("/user/{user_id}")
async def media_user_detail(user_id: str, admin: dict = Depends(get_admin_user)):
    """Per-user investigation: sessions, tokens, downloads, flags."""
    now = datetime.now(timezone.utc)
    one_day = now - timedelta(hours=24)

    user = await db.users.find_one({"id": user_id}, {"_id": 0, "id": 1, "email": 1, "role": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    sessions = await db.user_media_sessions.find(
        {"user_id": user_id}, {"_id": 0}
    ).sort("started_at", -1).to_list(20)
    for s in sessions:
        for k in ("started_at", "last_active", "terminated_at"):
            if isinstance(s.get(k), datetime):
                s[k] = s[k].isoformat()

    tokens = await db.media_tokens.find(
        {"user_id": user_id, "created_at": {"$gte": one_day}}, {"_id": 0, "token_hash": 0}
    ).sort("created_at", -1).to_list(50)
    for t in tokens:
        for k in ("created_at", "expires_at", "last_used_at", "revoked_at"):
            if isinstance(t.get(k), datetime):
                t[k] = t[k].isoformat()

    recent_events = await db.media_access_log.find(
        {"user_id": user_id, "timestamp": {"$gte": one_day}}, {"_id": 0}
    ).sort("timestamp", -1).to_list(50)
    for e in recent_events:
        if isinstance(e.get("timestamp"), datetime):
            e["timestamp"] = e["timestamp"].isoformat()

    flags = await db.media_abuse_flags.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).to_list(20)
    for f in flags:
        if isinstance(f.get("created_at"), datetime):
            f["created_at"] = f["created_at"].isoformat()

    suspension = await db.media_suspensions.find_one(
        {"user_id": user_id, "status": "active", "expires_at": {"$gt": now}}, {"_id": 0}
    )
    if suspension:
        for k in ("created_at", "expires_at"):
            if isinstance(suspension.get(k), datetime):
                suspension[k] = suspension[k].isoformat()

    distinct_ips = await db.media_access_log.distinct("ip", {"user_id": user_id, "timestamp": {"$gte": one_day}})

    return {
        "user": user,
        "sessions": sessions,
        "tokens_24h": tokens,
        "events_24h": recent_events,
        "flags": flags,
        "active_suspension": suspension,
        "unique_ips_24h": len(distinct_ips),
    }


class RevokeTokensRequest(BaseModel):
    user_id: str
    reason: str = "admin_action"

class SuspendMediaRequest(BaseModel):
    user_id: str
    duration_minutes: int = 60
    reason: str = "admin_action"

class ResolveFlagRequest(BaseModel):
    flag_id: str


@router.post("/tokens/revoke")
async def admin_revoke_tokens(req: RevokeTokensRequest, admin: dict = Depends(get_admin_user)):
    count = await revoke_user_tokens(req.user_id, reason=req.reason)
    return {"revoked": count, "user_id": req.user_id}


@router.post("/users/suspend-media")
async def admin_suspend_media(req: SuspendMediaRequest, admin: dict = Depends(get_admin_user)):
    result = await suspend_user_media(req.user_id, req.duration_minutes, req.reason)
    return result


@router.post("/users/unsuspend-media")
async def admin_unsuspend_media(req: RevokeTokensRequest, admin: dict = Depends(get_admin_user)):
    success = await unsuspend_user_media(req.user_id)
    return {"success": success, "user_id": req.user_id}


@router.post("/flags/resolve")
async def admin_resolve_flag(req: ResolveFlagRequest, admin: dict = Depends(get_admin_user)):
    result = await db.media_abuse_flags.update_one(
        {"flag_id": req.flag_id},
        {"$set": {"status": "resolved", "resolved_by": str(admin["id"]),
                  "resolved_at": datetime.now(timezone.utc)}},
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Flag not found")
    return {"resolved": True}
