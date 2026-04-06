"""
Experience Feedback Routes — Post-usage feedback capture
POST /api/feedback/experience  — Submit feedback (authenticated)
GET  /api/admin/feedback        — List feedback (admin)
GET  /api/admin/feedback/unread-count — Unread count (admin)
POST /api/admin/feedback/{id}/mark-read — Mark as read (admin)
POST /api/admin/feedback/mark-read-bulk — Bulk mark as read (admin)
"""
from fastapi import APIRouter, HTTPException, Request, Query, Depends
from datetime import datetime, timezone
from typing import Optional
import uuid
import re

from shared import db, logger, get_current_user, get_admin_user

router = APIRouter(tags=["Experience Feedback"])

VALID_RATINGS = ["great", "good", "okay", "poor"]
VALID_REUSE = ["yes", "maybe", "no"]
VALID_SOURCES = ["logout_prompt", "idle_prompt", "manual_feedback"]


def sanitize(text: str, max_len: int = 2000) -> str:
    if not text:
        return ""
    text = text.strip()
    text = re.sub(r'<[^>]+>', '', text)
    return text[:max_len]


# ─── Submit Experience Feedback ───────────────────────────────
@router.post("/feedback/experience")
async def submit_experience_feedback(request: Request, user: dict = Depends(get_current_user)):
    body = await request.json()

    rating = (body.get("rating") or "").strip().lower()
    liked = sanitize(body.get("liked", ""))
    improvements = sanitize(body.get("improvements", ""))
    reuse_intent = (body.get("reuse_intent") or "").strip().lower()
    feature_context = body.get("feature_context") or []
    session_id = sanitize(body.get("session_id", ""), 200)
    source = (body.get("source") or "").strip().lower()
    meta = body.get("meta") or {}

    errors = {}
    if rating not in VALID_RATINGS:
        errors["rating"] = f"Must be one of: {', '.join(VALID_RATINGS)}"
    if not improvements or len(improvements.strip()) < 3:
        errors["improvements"] = "This field is required (min 3 characters)"
    if reuse_intent not in VALID_REUSE:
        errors["reuse_intent"] = f"Must be one of: {', '.join(VALID_REUSE)}"
    if source not in VALID_SOURCES:
        errors["source"] = f"Must be one of: {', '.join(VALID_SOURCES)}"
    if not session_id:
        errors["session_id"] = "Session ID is required"

    if errors:
        return {"success": False, "message": "Invalid request", "errors": errors}

    if not isinstance(feature_context, list):
        feature_context = []
    feature_context = list(set([str(f)[:100] for f in feature_context[:20]]))

    user_id = user.get("id", str(user.get("_id", "")))
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    daily_count = await db.user_feedback.count_documents({
        "user_id": user_id,
        "created_at": {"$gte": today_start.isoformat()}
    })
    if daily_count >= 3:
        raise HTTPException(status_code=429, detail="Too many feedback submissions. Please try later.")

    feedback_id = str(uuid.uuid4())
    doc = {
        "id": feedback_id,
        "user_id": user_id,
        "user_email": (user.get("email") or "").lower(),
        "rating": rating,
        "liked": liked,
        "improvements": improvements,
        "reuse_intent": reuse_intent,
        "feature_context": feature_context,
        "source": source,
        "session_id": session_id,
        "read_by_admin": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "meta": {
            "browser": sanitize(str(meta.get("browser", "")), 300),
            "device": sanitize(str(meta.get("device", "")), 50),
            "plan_type": sanitize(str(meta.get("plan_type", "")), 50),
            "credits_remaining": int(meta.get("credits_remaining", 0)) if str(meta.get("credits_remaining", "")).replace("-", "").isdigit() else 0,
            "idle_seconds": int(meta.get("idle_seconds", 0)) if str(meta.get("idle_seconds", "")).replace("-", "").isdigit() else 0,
        }
    }

    await db.user_feedback.insert_one(doc)
    logger.info(f"Feedback saved from {doc['user_email']} | rating={rating} | source={source}")

    return {
        "success": True,
        "message": "Feedback saved",
        "data": {
            "feedback_id": feedback_id,
            "read_by_admin": False
        }
    }


# ─── Admin: List Feedback ─────────────────────────────────────
@router.get("/admin/feedback")
async def admin_list_feedback(
    admin: dict = Depends(get_admin_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    rating: Optional[str] = None,
    source: Optional[str] = None,
    read_by_admin: Optional[str] = None,
    search: Optional[str] = None,
):
    query = {}
    if rating and rating in VALID_RATINGS:
        query["rating"] = rating
    if source and source in VALID_SOURCES:
        query["source"] = source
    if read_by_admin in ["true", "false"]:
        query["read_by_admin"] = (read_by_admin == "true")
    if search and search.strip():
        escaped = re.escape(search.strip())
        query["$or"] = [
            {"user_email": {"$regex": escaped, "$options": "i"}},
            {"liked": {"$regex": escaped, "$options": "i"}},
            {"improvements": {"$regex": escaped, "$options": "i"}},
        ]

    total = await db.user_feedback.count_documents(query)
    cursor = db.user_feedback.find(query, {"_id": 0}).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size)
    items = await cursor.to_list(length=page_size)

    return {
        "success": True,
        "data": {
            "items": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "has_next": page * page_size < total
            }
        }
    }


# ─── Admin: Unread Count ──────────────────────────────────────
@router.get("/admin/feedback/unread-count")
async def admin_unread_count(admin: dict = Depends(get_admin_user)):
    count = await db.user_feedback.count_documents({"read_by_admin": False})
    return {"success": True, "data": {"unread_count": count}}


# ─── Admin: Mark as Read ──────────────────────────────────────
@router.post("/admin/feedback/{feedback_id}/mark-read")
async def admin_mark_read(feedback_id: str, admin: dict = Depends(get_admin_user)):
    result = await db.user_feedback.update_one(
        {"id": feedback_id},
        {"$set": {"read_by_admin": True, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return {"success": True, "message": "Feedback marked as read"}


# ─── Admin: Bulk Mark Read ────────────────────────────────────
@router.post("/admin/feedback/mark-read-bulk")
async def admin_mark_read_bulk(request: Request, admin: dict = Depends(get_admin_user)):
    body = await request.json()
    ids = body.get("feedback_ids", [])
    if not ids or not isinstance(ids, list):
        raise HTTPException(status_code=400, detail="feedback_ids array required")
    result = await db.user_feedback.update_many(
        {"id": {"$in": ids[:100]}},
        {"$set": {"read_by_admin": True, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"success": True, "message": f"{result.modified_count} feedback marked as read"}
