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
    # Viral loop steps
    "return_to_inspect",
    "share_revisit",
    # ═══ Phase 0: Consumption funnel baseline ═══
    "story_viewed",
    "story_card_clicked",
    "watch_started",
    "watch_completed_25",
    "watch_completed_50",
    "watch_completed_75",
    "watch_completed_100",
    "cta_clicked",
    "remix_clicked",
    "create_clicked",
    "scroll_depth_50",
    # Spectator conversion funnel
    "spectator_impression",
    "spectator_pressure_shown",
    "spectator_quick_shot",
    "spectator_to_player_conversion",
    # ═══ V2 Observability — feed + preview + battle funnel ═══
    "feed_card_impression",
    "preview_started",
    "preview_completed",
    "preview_failed",
    "entered_battle",
    "creation_started",
    "creation_abandoned",
    "battle_paywall_viewed",
    "battle_pack_selected",
    "battle_payment_success",
    "battle_payment_abandoned",
    "win_share_triggered",
    "return_trigger_sent",
    "return_trigger_clicked",
    # ═══ V3 — Core growth metrics (critical 7) ═══
    "typing_started",
    "generate_clicked",
    "postgen_cta_clicked",
    "battle_enter_clicked",
    "session_started",
    "session_ended",
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

    # Server-side dedup: critical once-per-session events
    DEDUP_EVENTS = {"session_started", "session_ended", "typing_started"}
    if step in DEDUP_EVENTS:
        existing = await db.funnel_events.find_one(
            {"session_id": session_id, "step": step}, {"_id": 1}
        )
        if existing:
            return {"success": True, "session_id": session_id, "dedup": True}

    event = {
        "event": step,
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
        "device_type": ctx.get("device_type", "unknown"),
        "traffic_source": ctx.get("traffic_source", "unknown"),
        "story_id": ctx.get("story_id"),
        "battle_id": ctx.get("battle_id"),
        "has_preview": ctx.get("has_preview"),
        "meta": ctx.get("meta", {}),
        "ip": request.client.host if request.client else None,
        "user_agent": ua[:200],
    }

    async def _bg_insert(e):
        try:
            await db.funnel_events.insert_one(e)
        except Exception:
            pass

    import asyncio
    asyncio.create_task(_bg_insert(event))
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



@router.get("/reaction-dashboard")
async def reaction_dashboard(
    user: dict = Depends(get_admin_user),
    days: int = Query(30, ge=1, le=90),
    category: Optional[str] = Query(None, description="Filter by reaction_category/pacing_mode"),
):
    """
    Founder Reaction Dashboard — per-video + per-category engagement aggregate.

    Answers the founder's 4 questions for the 10-story reaction run:
      1. Which one did viewers finish watching?    → completion_pct (100% / play)
      2. Which one did viewers share?              → share_clicks
      3. Which one made them feel something?      → hold_rate (50–100% completion)
      4. Would they generate their own?           → regen_clicks (remix/create from viewer)

    Returns per-video rows sorted by each leaderboard, plus category rollups.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    # Step 1: count events per (story_id, event_name). Unique by session.
    # story_id is stored at TOP LEVEL on the event (funnelTracker extracts from extra.story_id
    # or extra.meta.story_id). meta.category is set by the caller for segmentation.
    match_stage = {"timestamp": {"$gte": cutoff}, "story_id": {"$ne": None}}
    if category:
        match_stage["meta.category"] = category

    pipe = [
        {"$match": match_stage},
        {"$group": {
            "_id": {"story_id": "$story_id", "step": "$step", "session": "$session_id"},
        }},
        {"$group": {
            "_id": {"story_id": "$_id.story_id", "step": "$_id.step"},
            "unique_sessions": {"$sum": 1},
        }},
    ]

    event_counts = {}  # story_id -> {step: unique_sessions}
    async for doc in db.funnel_events.aggregate(pipe):
        sid = doc["_id"]["story_id"]
        st = doc["_id"]["step"]
        event_counts.setdefault(sid, {})[st] = doc["unique_sessions"]

    story_ids = list(event_counts.keys())
    if not story_ids:
        return {
            "success": True,
            "period_days": days,
            "filter_category": category,
            "videos": [],
            "category_rollups": [],
            "leaderboards": {"top_finished": [], "top_shared": [], "top_hold_rate": [], "top_regen": []},
        }

    # Step 2: resolve job metadata
    jobs = {}
    async for j in db.pipeline_jobs.find(
        {"job_id": {"$in": story_ids}},
        {"_id": 0, "job_id": 1, "title": 1, "slug": 1, "pacing_mode": 1, "reaction_category": 1,
         "animation_style": 1, "output_url": 1, "estimated_scenes": 1}
    ):
        jobs[j["job_id"]] = j

    # Step 3: build per-video rows
    videos = []
    for sid in story_ids:
        ec = event_counts[sid]
        job = jobs.get(sid, {})
        plays = ec.get("watch_started", 0)
        if plays == 0:
            # fall back to 25% as "started" proxy if onPlay didn't fire
            plays = ec.get("watch_completed_25", 0)
        p25 = ec.get("watch_completed_25", 0)
        p50 = ec.get("watch_completed_50", 0)
        p75 = ec.get("watch_completed_75", 0)
        p100 = ec.get("watch_completed_100", 0)
        # Precise share clicks (one event per click, with channel metadata)
        precise_shares = ec.get("cta_share_clicked", 0)
        regens = ec.get("create_clicked", 0) + ec.get("remix_clicked", 0)

        def _pct(n, d):
            return round((n / d) * 100, 1) if d > 0 else 0.0

        videos.append({
            "story_id": sid,
            "title": job.get("title") or sid[:12],
            "slug": job.get("slug"),
            "category": job.get("reaction_category") or job.get("pacing_mode") or "unknown",
            "animation_style": job.get("animation_style"),
            "scenes": job.get("estimated_scenes"),
            "output_url": job.get("output_url"),
            "plays": plays,
            "progress_25": p25,
            "progress_50": p50,
            "progress_75": p75,
            "completions_100": p100,
            "completion_pct": _pct(p100, plays),
            "hold_rate_50": _pct(p50, plays),     # % who held past 50%
            "hold_rate_75": _pct(p75, plays),     # % who held past 75%
            "share_clicks": precise_shares,
            "share_per_play": _pct(precise_shares, plays),
            "regen_clicks": regens,
            "regen_per_play": _pct(regens, plays),
        })

    # Step 4: category rollups
    from collections import defaultdict
    cat_agg = defaultdict(lambda: {
        "plays": 0, "progress_25": 0, "progress_50": 0, "progress_75": 0,
        "completions_100": 0, "share_clicks": 0, "regen_clicks": 0, "video_count": 0,
    })
    for v in videos:
        c = v["category"]
        cat_agg[c]["plays"] += v["plays"]
        cat_agg[c]["progress_25"] += v["progress_25"]
        cat_agg[c]["progress_50"] += v["progress_50"]
        cat_agg[c]["progress_75"] += v["progress_75"]
        cat_agg[c]["completions_100"] += v["completions_100"]
        cat_agg[c]["share_clicks"] += v["share_clicks"]
        cat_agg[c]["regen_clicks"] += v["regen_clicks"]
        cat_agg[c]["video_count"] += 1
    category_rollups = []
    for c, d in cat_agg.items():
        plays = d["plays"] or 1  # prevent div by zero
        category_rollups.append({
            "category": c,
            "videos": d["video_count"],
            "plays": d["plays"],
            "completion_pct": round(d["completions_100"] / plays * 100, 1) if d["plays"] else 0.0,
            "hold_rate_50": round(d["progress_50"] / plays * 100, 1) if d["plays"] else 0.0,
            "share_per_play": round(d["share_clicks"] / plays * 100, 1) if d["plays"] else 0.0,
            "regen_per_play": round(d["regen_clicks"] / plays * 100, 1) if d["plays"] else 0.0,
            "share_clicks": d["share_clicks"],
            "regen_clicks": d["regen_clicks"],
        })
    category_rollups.sort(key=lambda r: r["plays"], reverse=True)

    # Step 5: leaderboards (top 5 each)
    def _top(key, n=5):
        return sorted([v for v in videos if v["plays"] > 0], key=lambda x: x[key], reverse=True)[:n]

    leaderboards = {
        "top_finished": _top("completion_pct"),
        "top_shared": _top("share_clicks"),
        "top_hold_rate": _top("hold_rate_50"),
        "top_regen": _top("regen_clicks"),
    }

    return {
        "success": True,
        "period_days": days,
        "filter_category": category,
        "video_count": len(videos),
        "videos": sorted(videos, key=lambda v: v["plays"], reverse=True),
        "category_rollups": category_rollups,
        "leaderboards": leaderboards,
    }
