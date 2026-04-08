"""
Funnel Tracking — Activation → Conversion Pipeline
Tracks events from landing to payment with rich context:
user_id, session_id, plan_shown, source_page, generation_count, device.
"""
from fastapi import APIRouter, Depends, Request, Query
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
    # Instant Demo Experience events
    "demo_viewed",
    "story_generation_started",
    "story_generated_success",
    "story_generated_failed",
    "story_generation_timeout",
    "cta_continue_clicked",
    "cta_video_clicked",
    "cta_share_clicked",
    "login_prompt_shown",
    # Continue Story Loop events
    "continue_clicked",
    "story_part_generated",
    "paywall_teaser_shown",
    "paywall_shown",
    "paywall_dismissed",
    "paywall_converted",
    "exit_offer_shown",
    "discount_offer_shown",
    # Original funnel steps
    "generation_started",
    "generation_completed",
    "result_viewed",
    "second_action",
    "paywall_viewed",
    "plan_selected",
    "payment_started",
    "payment_abandoned",
    "payment_success",
]


@router.post("/track")
async def track_funnel_event(request: Request):
    """Track a funnel event with rich context. Works for both authenticated and anonymous users."""
    body = await request.json()
    step = body.get("step")
    if step not in FUNNEL_STEPS:
        return {"success": False, "error": f"Invalid step: {step}"}

    session_id = body.get("session_id") or str(uuid.uuid4())
    user_id = body.get("user_id")

    # Try to extract user from token if available
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer ") and not user_id:
        try:
            from shared import verify_token
            token_data = verify_token(auth_header.split(" ")[1])
            user_id = token_data.get("sub")
        except Exception:
            pass

    # Context fields for deep analysis
    ctx = body.get("context", {})
    ua = request.headers.get("user-agent", "")

    event = {
        "step": step,
        "step_index": FUNNEL_STEPS.index(step),
        "session_id": session_id,
        "user_id": user_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_page": ctx.get("source_page", "unknown"),
        "generation_count": ctx.get("generation_count", 0),
        "plan_shown": ctx.get("plan_shown"),
        "plan_selected": ctx.get("plan_selected"),
        "device": ctx.get("device", "unknown"),
        "meta": ctx.get("meta", {}),
        "ip": request.client.host if request.client else None,
        "user_agent": ua[:200],
    }

    await db.funnel_events.insert_one(event)
    return {"success": True, "session_id": session_id}


@router.get("/metrics")
async def get_funnel_metrics(
    user: dict = Depends(get_admin_user),
    days: int = Query(7, ge=1, le=90),
):
    """Admin endpoint: conversion % and drop-off % per step, with context breakdowns."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    # Unique sessions per step
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
    top_count = None
    for step in FUNNEL_STEPS:
        count = step_counts.get(step, 0)
        if top_count is None and count > 0:
            top_count = count
        conversion = round((count / top_count * 100), 1) if top_count and top_count > 0 else 0.0
        prev_step_count = funnel[-1]["count"] if funnel else top_count
        step_drop = round(100 - (count / prev_step_count * 100), 1) if prev_step_count and prev_step_count > 0 else 0.0
        funnel.append({
            "step": step,
            "count": count,
            "conversion_from_top_pct": conversion,
            "drop_off_from_prev_pct": max(0, step_drop),
        })

    # Device breakdown
    device_pipeline = [
        {"$match": {"timestamp": {"$gte": cutoff}}},
        {"$group": {"_id": "$device", "count": {"$sum": 1}}},
    ]
    device_breakdown = {}
    async for doc in db.funnel_events.aggregate(device_pipeline):
        device_breakdown[doc["_id"] or "unknown"] = doc["count"]

    # Source page breakdown
    source_pipeline = [
        {"$match": {"timestamp": {"$gte": cutoff}}},
        {"$group": {"_id": "$source_page", "count": {"$sum": 1}}},
    ]
    source_breakdown = {}
    async for doc in db.funnel_events.aggregate(source_pipeline):
        source_breakdown[doc["_id"] or "unknown"] = doc["count"]

    # Paywall micro-conversions
    paywall_steps = ["paywall_viewed", "plan_selected", "payment_started", "payment_abandoned", "payment_success"]
    paywall_funnel = []
    for ps in paywall_steps:
        paywall_funnel.append({"step": ps, "count": step_counts.get(ps, 0)})

    # Total unique sessions & users
    total_sessions_result = await db.funnel_events.aggregate([
        {"$match": {"timestamp": {"$gte": cutoff}}},
        {"$group": {"_id": "$session_id"}},
        {"$count": "total"},
    ]).to_list(1)

    total_users_result = await db.funnel_events.aggregate([
        {"$match": {"timestamp": {"$gte": cutoff}, "user_id": {"$ne": None}}},
        {"$group": {"_id": "$user_id"}},
        {"$count": "total"},
    ]).to_list(1)

    # Biggest drop-off
    drops = [f for f in funnel if f["count"] > 0]
    biggest_drop = max(drops, key=lambda x: x["drop_off_from_prev_pct"])["step"] if len(drops) > 1 else None

    return {
        "success": True,
        "period_days": days,
        "total_sessions": total_sessions_result[0]["total"] if total_sessions_result else 0,
        "total_users": total_users_result[0]["total"] if total_users_result else 0,
        "funnel": funnel,
        "biggest_drop_off": biggest_drop,
        "device_breakdown": device_breakdown,
        "source_breakdown": source_breakdown,
        "paywall_micro_funnel": paywall_funnel,
    }
