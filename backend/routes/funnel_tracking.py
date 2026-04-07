"""
Funnel Tracking — Activation → Conversion Pipeline
Tracks 9 events from landing to payment with timestamps + session_id.
"""
from fastapi import APIRouter, Depends, Request
from datetime import datetime, timezone, timedelta
from typing import Optional
import uuid
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared import db, logger, get_current_user, get_admin_user

router = APIRouter(prefix="/funnel", tags=["Funnel Tracking"])

FUNNEL_STEPS = [
    "landing_view",
    "first_action_click",
    "generation_started",
    "generation_completed",
    "result_viewed",
    "second_action",
    "paywall_viewed",
    "payment_started",
    "payment_success",
]


@router.post("/track")
async def track_funnel_event(request: Request):
    """Track a funnel event. Works for both authenticated and anonymous users."""
    body = await request.json()
    step = body.get("step")
    if step not in FUNNEL_STEPS:
        return {"success": False, "error": f"Invalid step: {step}"}

    session_id = body.get("session_id") or str(uuid.uuid4())
    user_id = body.get("user_id")
    meta = body.get("meta", {})

    # Try to get user from token if available
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer ") and not user_id:
        try:
            from shared import verify_token
            token_data = verify_token(auth.split(" ")[1])
            user_id = token_data.get("sub")
        except Exception:
            pass

    event = {
        "step": step,
        "step_index": FUNNEL_STEPS.index(step),
        "session_id": session_id,
        "user_id": user_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "meta": meta,
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent", "")[:200],
    }

    await db.funnel_events.insert_one(event)
    return {"success": True, "session_id": session_id}


@router.get("/metrics")
async def get_funnel_metrics(
    user: dict = Depends(get_admin_user),
    days: int = 7,
):
    """Admin endpoint: conversion % and drop-off % per step"""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    pipeline = [
        {"$match": {"timestamp": {"$gte": cutoff}}},
        {"$group": {
            "_id": {"session_id": "$session_id", "step": "$step"},
        }},
        {"$group": {
            "_id": "$_id.step",
            "unique_sessions": {"$sum": 1},
        }},
    ]

    step_counts = {}
    async for doc in db.funnel_events.aggregate(pipeline):
        step_counts[doc["_id"]] = doc["unique_sessions"]

    # Build funnel with conversion rates
    funnel = []
    prev_count = None
    for step in FUNNEL_STEPS:
        count = step_counts.get(step, 0)
        conversion = round((count / prev_count * 100), 1) if prev_count and prev_count > 0 else 100.0
        drop_off = round(100 - conversion, 1) if prev_count else 0.0
        funnel.append({
            "step": step,
            "count": count,
            "conversion_pct": conversion,
            "drop_off_pct": drop_off,
        })
        if prev_count is None and count > 0:
            prev_count = count
        elif count > 0:
            prev_count = count

    # Total unique sessions and users
    total_sessions = await db.funnel_events.aggregate([
        {"$match": {"timestamp": {"$gte": cutoff}}},
        {"$group": {"_id": "$session_id"}},
        {"$count": "total"},
    ]).to_list(1)

    total_users = await db.funnel_events.aggregate([
        {"$match": {"timestamp": {"$gte": cutoff}, "user_id": {"$ne": None}}},
        {"$group": {"_id": "$user_id"}},
        {"$count": "total"},
    ]).to_list(1)

    return {
        "period_days": days,
        "total_sessions": total_sessions[0]["total"] if total_sessions else 0,
        "total_users": total_users[0]["total"] if total_users else 0,
        "funnel": funnel,
        "biggest_drop_off": max(funnel, key=lambda x: x["drop_off_pct"])["step"] if any(f["count"] > 0 for f in funnel) else None,
    }
