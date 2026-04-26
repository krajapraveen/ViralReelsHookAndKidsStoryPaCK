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
    # ═══ V4 — P0 Activation Funnel (Apr 2026 — exact founder names) ═══
    "landing_cta_clicked",
    "signup_modal_opened",
    "signup_started",
    "signup_success",
    "signup_failed",
    "google_signin_clicked",
    "google_signin_success",
    "google_signin_failed",
    "google_popup_closed",
    "google_popup_blocked",
    "dashboard_loaded",
    "prompt_input_focused",
    "prompt_started_typing",
    "prompt_submitted",
    "story_generation_completed",
    "story_generation_failed",
    "continue_story_clicked",
    "checkout_started",
    "session_abandoned",
    "auth_redirect_loop_detected",
    # ═══ V4 — Frontend error intelligence ═══
    "uncaught_js_error",
    "api_4xx",
    "api_5xx",
    "spinner_over_8_seconds",
    "rage_click_detected",
    "double_click_detected",
]


# Canonical activation-funnel ordering (founder spec). Used by /activation-funnel
# for stage-by-stage drop-off analysis. NOT the full ALLOWED_STEPS list.
ACTIVATION_FUNNEL_ORDER = [
    ("landing_view",                "Landing"),
    ("landing_cta_clicked",         "CTA Clicked"),
    ("signup_modal_opened",         "Signup Opened"),
    ("signup_success",              "Signup Success"),
    ("dashboard_loaded",            "Dashboard Loaded"),
    ("prompt_submitted",            "Prompt Submitted"),
    ("story_generation_started",    "Story Started"),
    ("story_generation_completed",  "Story Completed"),
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

    # Detect browser + device from UA (lightweight, no external deps)
    def _detect_browser(ua_str: str) -> str:
        ua_l = ua_str.lower()
        if "edg/" in ua_l:
            return "edge"
        if "chrome/" in ua_l and "safari/" in ua_l:
            return "chrome"
        if "firefox/" in ua_l:
            return "firefox"
        if "safari/" in ua_l and "version/" in ua_l:
            return "safari"
        if "opera" in ua_l or "opr/" in ua_l:
            return "opera"
        return "other"

    def _detect_device(ua_str: str) -> str:
        ua_l = ua_str.lower()
        if any(x in ua_l for x in ["iphone", "android", "ipod", "blackberry", "iemobile"]):
            return "mobile"
        if "ipad" in ua_l or ("tablet" in ua_l and "mobile" not in ua_l):
            return "tablet"
        return "desktop"

    browser = ctx.get("browser") or _detect_browser(ua)
    device_type = ctx.get("device_type") or _detect_device(ua)

    # Country from CF-IPCountry / X-Country headers (Cloudflare/ingress hints)
    country = (
        request.headers.get("cf-ipcountry")
        or request.headers.get("x-country")
        or ctx.get("country")
        or "unknown"
    )

    # Server-side dedup: critical once-per-session events
    DEDUP_EVENTS = {"session_started", "session_ended", "typing_started", "dashboard_loaded"}
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
        "device_type": device_type,
        "browser": browser,
        "country": country,
        "traffic_source": ctx.get("traffic_source", "unknown"),
        "utm_source": ctx.get("utm_source"),
        "utm_campaign": ctx.get("utm_campaign"),
        "utm_medium": ctx.get("utm_medium"),
        "page": ctx.get("page", ctx.get("source_page", "unknown")),
        "variant_seen": ctx.get("variant_seen"),
        "time_since_landing_ms": ctx.get("time_since_landing_ms"),
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
        # Unique viewers = widest reasonable funnel top. Captures passive impressions
        # on public share pages (autoplay-muted may not fire onPlay on Safari/iOS).
        unique_viewers = max(plays, p25)
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
            "unique_viewers": unique_viewers,
            "progress_25": p25,
            "progress_50": p50,
            "progress_75": p75,
            "completions_100": p100,
            "completion_pct": _pct(p100, plays),
            "hold_rate_50": _pct(p50, plays),     # % who held past 50%
            "hold_rate_75": _pct(p75, plays),     # % who held past 75%
            "share_clicks": precise_shares,
            "share_per_play": _pct(precise_shares, plays),
            # NORTH STAR METRIC (per founder directive Apr 23):
            # shares / unique viewers → the single best signal for public distribution health.
            "view_to_share_rate": _pct(precise_shares, unique_viewers),
            "regen_clicks": regens,
            "regen_per_play": _pct(regens, plays),
        })

    # Step 4: category rollups
    from collections import defaultdict
    cat_agg = defaultdict(lambda: {
        "plays": 0, "unique_viewers": 0, "progress_25": 0, "progress_50": 0, "progress_75": 0,
        "completions_100": 0, "share_clicks": 0, "regen_clicks": 0, "video_count": 0,
    })
    for v in videos:
        c = v["category"]
        cat_agg[c]["plays"] += v["plays"]
        cat_agg[c]["unique_viewers"] += v["unique_viewers"]
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
        viewers = d["unique_viewers"] or 1
        category_rollups.append({
            "category": c,
            "videos": d["video_count"],
            "plays": d["plays"],
            "unique_viewers": d["unique_viewers"],
            "completion_pct": round(d["completions_100"] / plays * 100, 1) if d["plays"] else 0.0,
            "hold_rate_50": round(d["progress_50"] / plays * 100, 1) if d["plays"] else 0.0,
            "share_per_play": round(d["share_clicks"] / plays * 100, 1) if d["plays"] else 0.0,
            # NORTH STAR: view-to-share rate (founder directive Apr 23)
            "view_to_share_rate": round(d["share_clicks"] / viewers * 100, 1) if d["unique_viewers"] else 0.0,
            "regen_per_play": round(d["regen_clicks"] / plays * 100, 1) if d["plays"] else 0.0,
            "share_clicks": d["share_clicks"],
            "regen_clicks": d["regen_clicks"],
        })
    # Sort categories by the north-star metric, then by volume (tiebreak)
    category_rollups.sort(key=lambda r: (r["view_to_share_rate"], r["unique_viewers"]), reverse=True)

    # Step 5: leaderboards (top 5 each)
    def _top(key, n=5, min_plays=1):
        return sorted(
            [v for v in videos if v["plays"] >= min_plays],
            key=lambda x: x[key],
            reverse=True,
        )[:n]

    leaderboards = {
        # NORTH STAR: lead with view-to-share rate
        "top_view_to_share": _top("view_to_share_rate"),
        "top_finished": _top("completion_pct"),
        "top_shared": _top("share_clicks"),
        "top_hold_rate": _top("hold_rate_50"),
        "top_regen": _top("regen_clicks"),
    }

    # Global north-star aggregate (all videos in window)
    total_viewers = sum(v["unique_viewers"] for v in videos)
    total_shares = sum(v["share_clicks"] for v in videos)
    north_star = {
        "view_to_share_rate": round(total_shares / total_viewers * 100, 2) if total_viewers else 0.0,
        "total_unique_viewers": total_viewers,
        "total_share_clicks": total_shares,
    }

    return {
        "success": True,
        "period_days": days,
        "filter_category": category,
        "video_count": len(videos),
        "north_star": north_star,
        "videos": sorted(videos, key=lambda v: v["plays"], reverse=True),
        "category_rollups": category_rollups,
        "leaderboards": leaderboards,
    }


@router.get("/activation-funnel")
async def activation_funnel(
    user: dict = Depends(get_admin_user),
    days: int = Query(7, ge=1, le=90),
    device_type: Optional[str] = Query(None, description="mobile|desktop|tablet"),
    browser: Optional[str] = Query(None),
    utm_source: Optional[str] = Query(None),
):
    """
    P0 ACTIVATION FUNNEL — exact stage-by-stage drop-off for the founder's
    8-stage activation chain. Returns conversion %, median time per step,
    mobile/desktop split, browser split, top-exit step, and error counts.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    base_match = {"timestamp": {"$gte": cutoff}}
    if device_type:
        base_match["device_type"] = device_type
    if browser:
        base_match["browser"] = browser
    if utm_source:
        base_match["utm_source"] = utm_source

    funnel_steps = [s for s, _ in ACTIVATION_FUNNEL_ORDER]
    pipe = [
        {"$match": {**base_match, "step": {"$in": funnel_steps}}},
        {"$sort": {"timestamp": 1}},
        {"$group": {
            "_id": {"session": "$session_id", "step": "$step"},
            "ts": {"$first": "$timestamp"},
            "device_type": {"$first": "$device_type"},
            "browser": {"$first": "$browser"},
            "country": {"$first": "$country"},
        }},
    ]
    session_timelines: dict = {}
    async for d in db.funnel_events.aggregate(pipe):
        sid = d["_id"]["session"]
        st = d["_id"]["step"]
        node = session_timelines.setdefault(sid, {"steps": {}, "device_type": d.get("device_type"),
                                                  "browser": d.get("browser"), "country": d.get("country")})
        node["steps"][st] = d["ts"]

    stages = []
    prev_count = None
    for i, (step, label) in enumerate(ACTIVATION_FUNNEL_ORDER):
        sessions_at_stage = [s for s in session_timelines.values() if step in s["steps"]]
        count = len(sessions_at_stage)
        if i == 0:
            conv_pct = 100.0
        else:
            conv_pct = round((count / prev_count) * 100, 1) if prev_count else 0.0
        prev_count = count

        median_to_next_ms = None
        if i < len(ACTIVATION_FUNNEL_ORDER) - 1:
            next_step = ACTIVATION_FUNNEL_ORDER[i + 1][0]
            deltas = []
            for sess in session_timelines.values():
                a = sess["steps"].get(step)
                b = sess["steps"].get(next_step)
                if a and b and b > a:
                    try:
                        ta = datetime.fromisoformat(a)
                        tb = datetime.fromisoformat(b)
                        deltas.append((tb - ta).total_seconds() * 1000)
                    except Exception:
                        pass
            if deltas:
                deltas.sort()
                median_to_next_ms = int(deltas[len(deltas) // 2])

        mobile = sum(1 for s in sessions_at_stage if s.get("device_type") == "mobile")
        desktop = sum(1 for s in sessions_at_stage if s.get("device_type") == "desktop")
        tablet = sum(1 for s in sessions_at_stage if s.get("device_type") == "tablet")

        stages.append({
            "step": step,
            "label": label,
            "sessions": count,
            "conversion_from_prev_pct": conv_pct,
            "median_to_next_ms": median_to_next_ms,
            "mobile": mobile,
            "desktop": desktop,
            "tablet": tablet,
        })

    top_exit = None
    biggest_drop = 0
    for i in range(len(stages) - 1):
        drop = stages[i]["sessions"] - stages[i + 1]["sessions"]
        if drop > biggest_drop:
            biggest_drop = drop
            top_exit = {
                "after_step": stages[i]["label"],
                "drop_count": drop,
                "drop_pct": round((drop / stages[i]["sessions"]) * 100, 1) if stages[i]["sessions"] else 0.0,
            }

    browser_split: dict = {}
    for sess in session_timelines.values():
        if "landing_view" in sess["steps"]:
            b = sess.get("browser") or "unknown"
            browser_split[b] = browser_split.get(b, 0) + 1
    browser_split_sorted = sorted(
        [{"browser": k, "sessions": v} for k, v in browser_split.items()],
        key=lambda r: r["sessions"], reverse=True,
    )

    country_split: dict = {}
    for sess in session_timelines.values():
        if "landing_view" in sess["steps"]:
            c = sess.get("country") or "unknown"
            country_split[c] = country_split.get(c, 0) + 1
    country_split_sorted = sorted(
        [{"country": k, "sessions": v} for k, v in country_split.items()],
        key=lambda r: r["sessions"], reverse=True,
    )[:10]

    error_events = [
        "uncaught_js_error", "api_4xx", "api_5xx",
        "spinner_over_8_seconds", "rage_click_detected", "double_click_detected",
        "google_popup_blocked", "google_popup_closed", "auth_redirect_loop_detected",
        "google_signin_failed", "signup_failed",
    ]
    err_pipe = [
        {"$match": {**base_match, "step": {"$in": error_events}}},
        {"$group": {"_id": "$step", "count": {"$sum": 1},
                    "sessions": {"$addToSet": "$session_id"}}},
        {"$project": {"step": "$_id", "_id": 0, "count": 1,
                      "unique_sessions": {"$size": "$sessions"}}},
    ]
    error_breakdown = []
    async for d in db.funnel_events.aggregate(err_pipe):
        error_breakdown.append(d)
    error_breakdown.sort(key=lambda r: r["count"], reverse=True)

    return {
        "success": True,
        "period_days": days,
        "filter": {"device_type": device_type, "browser": browser, "utm_source": utm_source},
        "stages": stages,
        "top_exit_step": top_exit,
        "browser_split": browser_split_sorted,
        "country_split": country_split_sorted,
        "error_breakdown": error_breakdown,
        "total_sessions_seen": len(session_timelines),
    }

