"""
Growth Analytics — Funnel Event Tracking & Viral Metrics
Tracks: page_view → remix_click → tool_open_prefilled → generate_click → signup → creation_completed
"""

import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from shared import db
from services.personalization_service import update_profile_on_event

logger = logging.getLogger("growth_analytics")
router = APIRouter(prefix="/growth", tags=["growth-analytics"])

# ─── EVENT MODEL ─────────────────────────────────────────────────────────────

class GrowthEvent(BaseModel):
    event: str
    session_id: Optional[str] = None
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
    # ── Addiction Loop Events ──
    "impression", "click", "watch_start", "watch_complete",
    "continue", "share", "signup_from_share",
    # ── Growth Funnel Events ──
    "share_viewed", "cta_clicked", "first_video_created",
    "remix_clicked", "download_triggered", "whatsapp_shared",
    "referral_link_copied", "create_button_clicked",
}

# ─── TRACK EVENT ─────────────────────────────────────────────────────────────

@router.post("/event")
async def track_event(data: GrowthEvent, request: Request, background_tasks: BackgroundTasks):
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

    # ── Update user_homepage_profile for personalization ──
    if data.user_id:
        background_tasks.add_task(update_profile_on_event, db, data.user_id, data.event, data.meta or {})

    return {"success": True, "event_id": doc["id"]}


# ─── BATCH TRACK ─────────────────────────────────────────────────────────────

class BatchEvents(BaseModel):
    events: list[GrowthEvent]

@router.post("/events/batch")
async def track_batch(data: BatchEvents, request: Request, background_tasks: BackgroundTasks):
    """Track multiple events at once with deduplication."""
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
    docs = []
    profile_updates = []
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
        # Collect profile updates for authenticated events
        if e.user_id:
            profile_updates.append((e.user_id, e.event, e.meta or {}))
    if docs:
        await db.growth_events.insert_many(docs)

    # ── Update user_homepage_profile for personalization ──
    for user_id, event, meta in profile_updates:
        background_tasks.add_task(update_profile_on_event, db, user_id, event, meta)

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



# ═══════════════════════════════════════════════════════════════════════════════
# ADDICTION LOOP METRICS DASHBOARD
# Tracks: impression → click → watch_start → watch_complete → continue → share
# ═══════════════════════════════════════════════════════════════════════════════

LOOP_STAGES = ["impression", "click", "watch_start", "watch_complete", "continue", "share"]

@router.get("/loop-dashboard")
async def get_loop_dashboard(days: int = Query(7, ge=1, le=90)):
    """Return all 7 sections of the Addiction Loop Metrics Dashboard in one call."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    base_match = {"timestamp": {"$gte": cutoff}}

    # ── Section 1+2: Funnel counts ──
    count_pipeline = [
        {"$match": {**base_match, "event": {"$in": LOOP_STAGES + ["signup_from_share"]}}},
        {"$group": {"_id": "$event", "count": {"$sum": 1}}},
    ]
    counts = {}
    async for doc in db.growth_events.aggregate(count_pipeline):
        counts[doc["_id"]] = doc["count"]

    imp = counts.get("impression", 0)
    clk = counts.get("click", 0)
    ws = counts.get("watch_start", 0)
    wc = counts.get("watch_complete", 0)
    cont = counts.get("continue", 0)
    shr = counts.get("share", 0)
    sfs = counts.get("signup_from_share", 0)

    def rate(num, den):
        return round(num / den * 100, 1) if den > 0 else 0

    click_rate = rate(clk, imp)
    completion_rate = rate(wc, ws)
    continue_rate = rate(cont, wc)
    share_rate = rate(shr, wc)

    # K-factor: new_users_from_shares / active_users
    active_users_pipeline = [
        {"$match": {**base_match, "user_id": {"$ne": None}}},
        {"$group": {"_id": "$user_id"}},
        {"$count": "total"},
    ]
    active_result = await db.growth_events.aggregate(active_users_pipeline).to_list(1)
    active_users = active_result[0]["total"] if active_result else 0
    k_factor = round(sfs / max(active_users, 1), 3)

    # ── Section 3: Drop-off analysis ──
    funnel_pairs = [
        ("click", "watch_start", clk, ws),
        ("watch_start", "watch_complete", ws, wc),
        ("watch_complete", "continue", wc, cont),
        ("continue", "share", cont, shr),
    ]
    dropoffs = []
    worst_drop = {"from": "", "to": "", "drop_pct": 0}
    for from_s, to_s, from_c, to_c in funnel_pairs:
        drop = rate(from_c - to_c, from_c) if from_c > 0 else 0
        entry = {"from": from_s, "to": to_s, "drop_pct": drop, "lost": from_c - to_c}
        dropoffs.append(entry)
        if drop > worst_drop["drop_pct"]:
            worst_drop = entry

    # ── Section 4: Top performing stories ──
    top_stories_pipeline = [
        {"$match": {**base_match, "event": {"$in": ["watch_complete", "continue", "share"]}, "meta.story_id": {"$ne": None}}},
        {"$group": {
            "_id": {"story_id": "$meta.story_id", "event": "$event"},
            "count": {"$sum": 1},
        }},
    ]
    story_stats = {}
    async for doc in db.growth_events.aggregate(top_stories_pipeline):
        sid = doc["_id"]["story_id"]
        evt = doc["_id"]["event"]
        if sid not in story_stats:
            story_stats[sid] = {"story_id": sid, "completions": 0, "continues": 0, "shares": 0}
        if evt == "watch_complete":
            story_stats[sid]["completions"] = doc["count"]
        elif evt == "continue":
            story_stats[sid]["continues"] = doc["count"]
        elif evt == "share":
            story_stats[sid]["shares"] = doc["count"]

    # Enrich with titles
    top_stories = sorted(story_stats.values(), key=lambda s: s["continues"], reverse=True)[:10]
    for s in top_stories:
        job = await db.story_engine_jobs.find_one({"job_id": s["story_id"]}, {"_id": 0, "title": 1})
        s["title"] = job.get("title", s["story_id"][:12]) if job else s["story_id"][:12]
        comp = s["completions"]
        s["continue_pct"] = rate(s["continues"], comp)
        s["share_pct"] = rate(s["shares"], comp)
        s["completion_pct"] = 0  # needs impression data per story

    # ── Section 5: Hook A/B performance ──
    hook_pipeline = [
        {"$match": {**base_match, "event": {"$in": ["impression", "click", "watch_complete", "continue"]}, "meta.hook_variant": {"$ne": None}}},
        {"$group": {
            "_id": {"hook": "$meta.hook_variant", "event": "$event"},
            "count": {"$sum": 1},
        }},
    ]
    hook_stats = {}
    async for doc in db.growth_events.aggregate(hook_pipeline):
        h = doc["_id"]["hook"]
        evt = doc["_id"]["event"]
        if h not in hook_stats:
            hook_stats[h] = {"hook": h, "impressions": 0, "clicks": 0, "completions": 0, "continues": 0}
        if evt == "impression":
            hook_stats[h]["impressions"] = doc["count"]
        elif evt == "click":
            hook_stats[h]["clicks"] = doc["count"]
        elif evt == "watch_complete":
            hook_stats[h]["completions"] = doc["count"]
        elif evt == "continue":
            hook_stats[h]["continues"] = doc["count"]

    hooks = []
    for h in hook_stats.values():
        h["ctr"] = rate(h["clicks"], h["impressions"])
        h["continue_pct"] = rate(h["continues"], h["completions"])
        hooks.append(h)
    hooks.sort(key=lambda x: x["continue_pct"], reverse=True)

    # ── Section 6: Category performance ──
    cat_pipeline = [
        {"$match": {**base_match, "event": {"$in": ["watch_complete", "continue", "share"]}, "meta.category": {"$ne": None}}},
        {"$group": {
            "_id": {"cat": "$meta.category", "event": "$event"},
            "count": {"$sum": 1},
        }},
    ]
    cat_stats = {}
    async for doc in db.growth_events.aggregate(cat_pipeline):
        c = doc["_id"]["cat"]
        evt = doc["_id"]["event"]
        if c not in cat_stats:
            cat_stats[c] = {"category": c, "completions": 0, "continues": 0, "shares": 0}
        if evt == "watch_complete":
            cat_stats[c]["completions"] = doc["count"]
        elif evt == "continue":
            cat_stats[c]["continues"] = doc["count"]
        elif evt == "share":
            cat_stats[c]["shares"] = doc["count"]

    categories = []
    for c in cat_stats.values():
        c["continue_pct"] = rate(c["continues"], c["completions"])
        c["share_pct"] = rate(c["shares"], c["completions"])
        categories.append(c)
    categories.sort(key=lambda x: x["continue_pct"], reverse=True)

    # ── Section 7: Real-time activity feed (last 20 events) ──
    recent_pipeline = [
        {"$match": {"event": {"$in": ["continue", "share", "watch_complete", "signup_from_share"]}}},
        {"$sort": {"timestamp": -1}},
        {"$limit": 20},
        {"$project": {"_id": 0, "event": 1, "timestamp": 1, "meta": 1, "ip": 1}},
    ]
    live_feed = []
    async for doc in db.growth_events.aggregate(recent_pipeline):
        live_feed.append({
            "event": doc["event"],
            "timestamp": doc.get("timestamp"),
            "story_title": (doc.get("meta") or {}).get("story_title", "a story"),
            "location": (doc.get("meta") or {}).get("location", ""),
        })

    return {
        "period_days": days,
        # Section 1: Growth Loop Health
        "health": {
            "continue_rate": continue_rate,
            "share_rate": share_rate,
            "k_factor": k_factor,
            "continue_benchmark": "strong" if continue_rate >= 25 else "weak" if continue_rate < 15 else "decent",
            "share_benchmark": "viral" if share_rate >= 15 else "good" if share_rate >= 5 else "weak",
            "k_benchmark": "viral" if k_factor >= 1 else "decent" if k_factor >= 0.3 else "weak",
        },
        # Section 2: Funnel
        "funnel": {
            "stages": [
                {"stage": "Impressions", "event": "impression", "count": imp},
                {"stage": "Clicks", "event": "click", "count": clk, "rate": click_rate},
                {"stage": "Watch Start", "event": "watch_start", "count": ws},
                {"stage": "Watch Complete", "event": "watch_complete", "count": wc, "rate": completion_rate},
                {"stage": "Continue", "event": "continue", "count": cont, "rate": continue_rate},
                {"stage": "Share", "event": "share", "count": shr, "rate": share_rate},
            ],
        },
        # Section 3: Drop-off
        "dropoffs": dropoffs,
        "worst_dropoff": worst_drop,
        # Section 4: Top stories
        "top_stories": top_stories[:10],
        # Section 5: Hook A/B
        "hooks": hooks[:10],
        # Section 6: Categories
        "categories": categories,
        # Section 7: Live feed
        "live_feed": live_feed,
        # Raw counts
        "raw": {"impressions": imp, "clicks": clk, "watch_starts": ws, "watch_completes": wc, "continues": cont, "shares": shr, "signups_from_share": sfs, "active_users": active_users},
    }


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
    """Award +15 credits to original creator when someone continues their story from a shared link."""
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
        "credits_awarded": 15,
        "type": "continuation_reward",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    await add_credits(creator_id, 15, "Continuation reward — someone continued your story (+15)")

    # Track K-factor event
    try:
        await db.growth_events.insert_one({
            "event": "share_to_continue",
            "source_job_id": parent_job_id,
            "creator_id": creator_id,
            "session_id": continuer_session,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass

    # Notify the original creator
    try:
        from routes.universe_routes import create_notification
        await create_notification(
            user_id=creator_id,
            ntype="continuation",
            title="Someone continued your story!",
            body="Your creation got a new continuation. +15 credits earned!",
            link=f"/v/{parent_job_id}",
        )
    except Exception:
        pass

    return {"success": True, "rewarded": True, "credits_awarded": 15}



# ─── SIGNUP REFERRAL REWARD ───────────────────────────────────────────────────

@router.post("/signup-referral-reward")
async def signup_referral_reward(data: dict):
    """Award +25 credits when a shared link leads to a new signup.
    Called during signup flow if referral source is detected."""
    referrer_job_id = data.get("referrer_job_id")
    new_user_id = data.get("new_user_id")
    if not referrer_job_id or not new_user_id:
        return {"success": False}

    parent_job = await db.pipeline_jobs.find_one(
        {"job_id": referrer_job_id}, {"_id": 0, "user_id": 1}
    )
    if not parent_job or not parent_job.get("user_id"):
        return {"success": False}

    referrer_id = parent_job["user_id"]
    if referrer_id == new_user_id:
        return {"success": False, "message": "Self-referral"}

    reward_key = f"signup_ref:{referrer_id}:{new_user_id}"
    existing = await db.share_rewards.find_one({"reward_key": reward_key}, {"_id": 1})
    if existing:
        return {"success": True, "rewarded": False, "message": "Already rewarded"}

    await db.share_rewards.insert_one({
        "reward_key": reward_key,
        "user_id": referrer_id,
        "new_user_id": new_user_id,
        "source_job_id": referrer_job_id,
        "credits_awarded": 25,
        "type": "signup_referral",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    await add_credits(referrer_id, 25, "Referral reward — friend signed up from your shared story (+25)")

    # Track K-factor event
    try:
        await db.growth_events.insert_one({
            "event": "share_to_signup",
            "referrer_id": referrer_id,
            "new_user_id": new_user_id,
            "source_job_id": referrer_job_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass

    try:
        from routes.universe_routes import create_notification
        await create_notification(
            user_id=referrer_id,
            ntype="referral",
            title="A friend signed up from your story!",
            body="+25 credits earned. Your story is spreading!",
            link="/app/dashboard",
        )
    except Exception:
        pass

    return {"success": True, "rewarded": True, "credits_awarded": 25}


# ─── K-FACTOR METRICS ────────────────────────────────────────────────────────

@router.get("/k-factor")
async def get_k_factor(user: dict = Depends(get_current_user)):
    """Get K-factor metrics for the current user and platform-wide."""
    user_id = user["id"]
    now = datetime.now(timezone.utc)
    seven_days_ago = (now - timedelta(days=7)).isoformat()

    # User metrics
    user_shares = await db.share_rewards.count_documents({
        "user_id": user_id, "type": {"$in": ["share_reward", None]},
    })
    user_continuations = await db.share_rewards.count_documents({
        "user_id": user_id, "type": "continuation_reward",
    })
    user_signups = await db.share_rewards.count_documents({
        "user_id": user_id, "type": "signup_referral",
    })

    # Platform-wide (last 7 days)
    total_shares_7d = await db.growth_events.count_documents({
        "event": "share_click", "timestamp": {"$gte": seven_days_ago},
    })
    total_cont_7d = await db.growth_events.count_documents({
        "event": "share_to_continue", "timestamp": {"$gte": seven_days_ago},
    })
    total_signups_7d = await db.growth_events.count_documents({
        "event": "share_to_signup", "timestamp": {"$gte": seven_days_ago},
    })

    # K-factor = (shares per user) * (conversion rate)
    share_to_continue_rate = (total_cont_7d / max(total_shares_7d, 1))
    share_to_signup_rate = (total_signups_7d / max(total_shares_7d, 1))

    return {
        "success": True,
        "user": {
            "total_shares": user_shares,
            "total_continuations_earned": user_continuations,
            "total_referral_signups": user_signups,
            "credits_from_virality": (user_shares * 5) + (user_continuations * 15) + (user_signups * 25),
        },
        "platform_7d": {
            "total_shares": total_shares_7d,
            "share_to_continue": total_cont_7d,
            "share_to_signup": total_signups_7d,
            "share_to_continue_rate": round(share_to_continue_rate, 4),
            "share_to_signup_rate": round(share_to_signup_rate, 4),
            "estimated_k_factor": round(share_to_continue_rate + share_to_signup_rate, 4),
        },
    }
