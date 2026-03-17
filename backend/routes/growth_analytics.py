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
    event: str  # page_view, remix_click, tool_open_prefilled, generate_click, signup_triggered, signup_completed, creation_completed
    session_id: str
    source_slug: Optional[str] = None
    tool: Optional[str] = None
    user_id: Optional[str] = None
    meta: Optional[dict] = None

VALID_EVENTS = {
    "page_view", "remix_click", "tool_open_prefilled",
    "generate_click", "signup_triggered", "signup_completed",
    "creation_completed", "share_click",
}

# ─── TRACK EVENT ─────────────────────────────────────────────────────────────

@router.post("/event")
async def track_event(data: GrowthEvent, request: Request):
    """Track a single growth funnel event."""
    if data.event not in VALID_EVENTS:
        raise HTTPException(status_code=400, detail=f"Invalid event: {data.event}")

    doc = {
        "id": str(uuid.uuid4()),
        "event": data.event,
        "session_id": data.session_id,
        "source_slug": data.source_slug,
        "tool": data.tool,
        "user_id": data.user_id,
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
    """Track multiple events at once."""
    docs = []
    for e in data.events[:50]:  # Max 50 per batch
        if e.event not in VALID_EVENTS:
            continue
        docs.append({
            "id": str(uuid.uuid4()),
            "event": e.event,
            "session_id": e.session_id,
            "source_slug": e.source_slug,
            "tool": e.tool,
            "user_id": e.user_id,
            "meta": e.meta or {},
            "ip": request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    if docs:
        await db.growth_events.insert_many(docs)
    return {"success": True, "tracked": len(docs)}


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
