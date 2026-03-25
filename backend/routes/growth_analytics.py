"""
Growth Analytics — Funnel Event Tracking & Viral Metrics
Tracks: page_view → remix_click → tool_open_prefilled → generate_click → signup → creation_completed
"""

import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional
from shared import db

logger = logging.getLogger("growth_analytics")
router = APIRouter(prefix="/growth", tags=["growth-analytics"])

# ─── EVENT MODEL ─────────────────────────────────────────────────────────────

class GrowthEvent(BaseModel):
    event: str
    session_id: str
    user_id: Optional[str] = None
    anonymous_id: Optional[str] = None
    source_page: Optional[str] = None
    source_slug: Optional[str] = None
    tool_type: Optional[str] = None
    creation_type: Optional[str] = None
    series_id: Optional[str] = None
    character_id: Optional[str] = None
    origin: Optional[str] = None  # direct | share_page | public_character_page | series_page
    origin_slug: Optional[str] = None
    origin_character_id: Optional[str] = None
    origin_series_id: Optional[str] = None
    referrer_slug: Optional[str] = None
    ab_variant: Optional[str] = None
    idempotency_key: Optional[str] = None
    meta: Optional[dict] = None

VALID_EVENTS = {
    "page_view", "remix_click", "tool_open_prefilled",
    "generate_click", "signup_triggered", "signup_completed",
    "creation_completed", "share_click", "continue_click",
    "add_twist_click", "make_funny_click", "next_episode_click",
}

# ─── TRACK EVENT ─────────────────────────────────────────────────────────────

@router.post("/event")
async def track_event(data: GrowthEvent, request: Request):
    """Track a single growth funnel event with deduplication."""
    if data.event not in VALID_EVENTS:
        raise HTTPException(status_code=400, detail=f"Invalid event: {data.event}")

    # Deduplication: if idempotency_key provided, skip if already tracked
    if data.idempotency_key:
        exists = await db.growth_events.find_one(
            {"idempotency_key": data.idempotency_key}, {"_id": 1}
        )
        if exists:
            return {"success": True, "event_id": None, "deduplicated": True}

    doc = {
        "id": str(uuid.uuid4()),
        "event": data.event,
        "session_id": data.session_id,
        "user_id": data.user_id,
        "anonymous_id": data.anonymous_id,
        "source_page": data.source_page,
        "source_slug": data.source_slug,
        "tool_type": data.tool_type,
        "creation_type": data.creation_type,
        "series_id": data.series_id,
        "character_id": data.character_id,
        "origin": data.origin,
        "origin_slug": data.origin_slug,
        "origin_character_id": data.origin_character_id,
        "origin_series_id": data.origin_series_id,
        "referrer_slug": data.referrer_slug,
        "ab_variant": data.ab_variant,
        "idempotency_key": data.idempotency_key,
        "meta": data.meta or {},
        "ip": request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown"),
        "user_agent": request.headers.get("user-agent", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await db.growth_events.insert_one(doc)
    return {"success": True, "event_id": doc["id"]}


# ─── BATCH TRACK ─────────────────────────────────────────────────────────────

class BatchEvents(BaseModel):
    events: list[GrowthEvent]

@router.post("/events/batch")
async def track_batch(data: BatchEvents, request: Request):
    """Track multiple events at once with deduplication."""
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
    docs = []
    for e in data.events[:50]:
        if e.event not in VALID_EVENTS:
            continue
        # Skip duplicates
        if e.idempotency_key:
            exists = await db.growth_events.find_one(
                {"idempotency_key": e.idempotency_key}, {"_id": 1}
            )
            if exists:
                continue
        docs.append({
            "id": str(uuid.uuid4()),
            "event": e.event,
            "session_id": e.session_id,
            "user_id": e.user_id,
            "anonymous_id": e.anonymous_id,
            "source_page": e.source_page,
            "source_slug": e.source_slug,
            "tool_type": e.tool_type,
            "creation_type": e.creation_type,
            "series_id": e.series_id,
            "character_id": e.character_id,
            "origin": e.origin,
            "origin_slug": e.origin_slug,
            "origin_character_id": e.origin_character_id,
            "origin_series_id": e.origin_series_id,
            "referrer_slug": e.referrer_slug,
            "ab_variant": e.ab_variant,
            "idempotency_key": e.idempotency_key,
            "meta": e.meta or {},
            "ip": ip,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    if docs:
        await db.growth_events.insert_many(docs)
    return {"success": True, "tracked": len(docs)}


# ─── ANONYMOUS → USER LINKAGE ────────────────────────────────────────────────

class LinkSessionRequest(BaseModel):
    session_id: str
    user_id: str


@router.post("/link-session")
async def link_anonymous_session(data: LinkSessionRequest):
    """Link anonymous session events to a user account after signup/login.
    Preserves attribution lineage across the anonymous → authenticated boundary."""
    result = await db.growth_events.update_many(
        {"session_id": data.session_id, "user_id": None},
        {"$set": {"user_id": data.user_id, "linked_at": datetime.now(timezone.utc).isoformat()}}
    )
    logger.info(f"Linked {result.modified_count} events from session {data.session_id} to user {data.user_id}")
    return {"success": True, "linked_events": result.modified_count}


# ─── FUNNEL METRICS ──────────────────────────────────────────────────────────

@router.get("/metrics")
async def get_growth_metrics(
    days: int = Query(7, ge=1, le=90),
    tool: Optional[str] = Query(None),
):
    """Get funnel conversion metrics for the last N days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    match = {"timestamp": {"$gte": cutoff}}
    if tool:
        match["tool"] = tool

    pipeline = [
        {"$match": match},
        {"$group": {"_id": "$event", "count": {"$sum": 1}}},
    ]
    results = {}
    async for doc in db.growth_events.aggregate(pipeline):
        results[doc["_id"]] = doc["count"]

    pv = results.get("page_view", 0)
    rc = results.get("remix_click", 0)
    tp = results.get("tool_open_prefilled", 0)
    gc = results.get("generate_click", 0)
    st = results.get("signup_triggered", 0)
    sc = results.get("signup_completed", 0)
    cc = results.get("creation_completed", 0)
    sh = results.get("share_click", 0)

    def rate(num, den):
        return round(num / den * 100, 2) if den > 0 else 0

    return {
        "period_days": days,
        "tool_filter": tool,
        "raw_counts": {
            "page_views": pv,
            "remix_clicks": rc,
            "tool_opens_prefilled": tp,
            "generate_clicks": gc,
            "signups_triggered": st,
            "signups_completed": sc,
            "creations_completed": cc,
            "share_clicks": sh,
        },
        "conversion_rates": {
            "remix_click_rate": rate(rc, pv),
            "prefill_rate": rate(tp, rc),
            "generation_rate": rate(gc, tp),
            "signup_trigger_rate": rate(st, gc),
            "signup_completion_rate": rate(sc, st),
            "creation_rate": rate(cc, sc),
            "overall_conversion": rate(cc, pv),
        },
        "viral_metrics": {
            "viral_coefficient": 0,  # Calculated below
            "avg_shares_per_creation": 0,
            "signup_per_remix": rate(sc, rc),
        },
    }


# ─── VIRAL COEFFICIENT ──────────────────────────────────────────────────────

@router.get("/viral-coefficient")
async def get_viral_coefficient(days: int = Query(7, ge=1, le=90)):
    """Calculate the viral coefficient K = (avg shares per user) × (conversion rate per share)."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    # Count unique creators who shared
    share_pipeline = [
        {"$match": {"event": "share_click", "timestamp": {"$gte": cutoff}, "user_id": {"$ne": None}}},
        {"$group": {"_id": "$user_id", "shares": {"$sum": 1}}},
    ]
    sharers = []
    async for doc in db.growth_events.aggregate(share_pipeline):
        sharers.append(doc["shares"])

    total_sharers = len(sharers)
    total_shares = sum(sharers) if sharers else 0
    avg_shares = total_shares / total_sharers if total_sharers > 0 else 0

    # Count conversions from shared content
    page_views = await db.growth_events.count_documents({"event": "page_view", "timestamp": {"$gte": cutoff}})
    signups = await db.growth_events.count_documents({"event": "signup_completed", "timestamp": {"$gte": cutoff}})
    conversion_rate = signups / page_views if page_views > 0 else 0

    k = round(avg_shares * conversion_rate, 4)

    # Per-slug breakdown (top 10)
    slug_pipeline = [
        {"$match": {"event": "page_view", "source_slug": {"$ne": None}, "timestamp": {"$gte": cutoff}}},
        {"$group": {"_id": "$source_slug", "views": {"$sum": 1}}},
        {"$sort": {"views": -1}},
        {"$limit": 10},
    ]
    top_slugs = []
    async for doc in db.growth_events.aggregate(slug_pipeline):
        slug = doc["_id"]
        remix_count = await db.growth_events.count_documents({"event": "remix_click", "source_slug": slug, "timestamp": {"$gte": cutoff}})
        top_slugs.append({
            "slug": slug,
            "views": doc["views"],
            "remix_clicks": remix_count,
            "remix_rate": round(remix_count / doc["views"] * 100, 2) if doc["views"] > 0 else 0,
        })

    return {
        "period_days": days,
        "viral_coefficient_K": k,
        "interpretation": "exponential growth" if k > 1 else "growing" if k > 0.5 else "needs optimization" if k > 0 else "no data",
        "components": {
            "avg_shares_per_user": round(avg_shares, 2),
            "conversion_rate_per_share": round(conversion_rate * 100, 4),
            "unique_sharers": total_sharers,
            "total_shares": total_shares,
            "page_views": page_views,
            "signups_from_shares": signups,
        },
        "top_performing_slugs": top_slugs,
    }


# ─── FUNNEL VISUALIZATION DATA ──────────────────────────────────────────────

@router.get("/funnel")
async def get_funnel_data(days: int = Query(7, ge=1, le=90)):
    """Get funnel stages for visualization."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    stages = ["page_view", "remix_click", "tool_open_prefilled", "generate_click", "signup_completed", "creation_completed"]
    funnel = []
    for stage in stages:
        count = await db.growth_events.count_documents({"event": stage, "timestamp": {"$gte": cutoff}})
        funnel.append({"stage": stage, "count": count})

    return {"period_days": days, "funnel": funnel}


# ─── DAILY TRENDS ────────────────────────────────────────────────────────────

@router.get("/trends")
async def get_daily_trends(days: int = Query(7, ge=1, le=30)):
    """Get daily event counts for trending."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    pipeline = [
        {"$match": {"timestamp": {"$gte": cutoff}}},
        {"$addFields": {"date": {"$substr": ["$timestamp", 0, 10]}}},
        {"$group": {"_id": {"date": "$date", "event": "$event"}, "count": {"$sum": 1}}},
        {"$sort": {"_id.date": 1}},
    ]

    trends = {}
    async for doc in db.growth_events.aggregate(pipeline):
        date = doc["_id"]["date"]
        event = doc["_id"]["event"]
        if date not in trends:
            trends[date] = {}
        trends[date][event] = doc["count"]

    return {"period_days": days, "daily": trends}


# ─── SHARE REWARDS ───────────────────────────────────────────────────────────

from shared import get_current_user, add_credits

class ShareRewardRequest(BaseModel):
    job_id: str
    platform: str

@router.post("/share-reward")
async def claim_share_reward(data: ShareRewardRequest, user: dict = Depends(get_current_user)):
    """Award +5 credits for sharing a creation (once per job per user)."""
    user_id = user["id"]
    reward_key = f"share_reward:{user_id}:{data.job_id}"

    existing = await db.share_rewards.find_one({"reward_key": reward_key}, {"_id": 1})
    if existing:
        return {"success": True, "rewarded": False, "message": "Already claimed for this creation"}

    await db.share_rewards.insert_one({
        "reward_key": reward_key,
        "user_id": user_id,
        "job_id": data.job_id,
        "platform": data.platform,
        "credits_awarded": 5,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    await add_credits(user_id, 5, "Share reward — shared creation on " + data.platform)

    return {"success": True, "rewarded": True, "credits_awarded": 5, "message": "+5 credits for sharing!"}


@router.post("/continuation-reward")
async def continuation_reward(data: dict):
    """Award +10 credits to original creator when someone continues their story from a shared link."""
    parent_job_id = data.get("parent_job_id")
    continuer_session = data.get("session_id", "")
    if not parent_job_id:
        return {"success": False}

    parent_job = await db.pipeline_jobs.find_one(
        {"job_id": parent_job_id}, {"_id": 0, "user_id": 1}
    )
    if not parent_job or not parent_job.get("user_id"):
        return {"success": False, "message": "Parent job not found"}

    creator_id = parent_job["user_id"]
    reward_key = f"cont_reward:{creator_id}:{parent_job_id}:{continuer_session}"

    existing = await db.share_rewards.find_one({"reward_key": reward_key}, {"_id": 1})
    if existing:
        return {"success": True, "rewarded": False, "message": "Already rewarded"}

    await db.share_rewards.insert_one({
        "reward_key": reward_key,
        "user_id": creator_id,
        "source_job_id": parent_job_id,
        "continuer_session": continuer_session,
        "credits_awarded": 10,
        "type": "continuation_reward",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    await add_credits(creator_id, 10, "Continuation reward — someone continued your story")

    return {"success": True, "rewarded": True, "credits_awarded": 10}

