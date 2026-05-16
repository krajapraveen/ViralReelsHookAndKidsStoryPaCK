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
    # ═══ V5 — P0 Speed SLA (Apr 2026 founder directive) ═══
    "speed_sla_met",          # CTA→paint, CTA→wow, teaser ready under threshold
    "speed_sla_breached",     # Same but over budget — RED LOG
    "cta_to_first_paint",     # Time CTA click → demo painted
    "cta_to_wow",             # Time CTA click → real personalized story rendered
    "teaser_ready",           # Time CTA click → quick-generate response received
    # ═══ V6 — P1 Revenue Conversion Sprint (Apr 26, 2026) ═══
    "video_cta_variant_impression",     # Outcome-led video CTA seen by engaged user
    "video_reward_preview_shown",       # Visual reward overlay opened
    "video_reward_preview_cta_clicked", # User confirmed intent → checkout
    "video_reward_preview_dismissed",
    # ═══ V7 — P1.6 Trust + Urgency (Apr 26, 2026) ═══
    "purchase_survey_shown",            # Post-payment 1-question modal shown
    "purchase_survey_submitted",        # User answered the survey
    "purchase_survey_dismissed",        # User closed without answering
    # ═══ V8 — P1.7 Payment Choke-Point Telemetry (Apr 26, 2026) ═══
    "login_page_loaded",                # /login mounted (paid_intent flag in meta)
    "cashfree_checkout_opened",         # Cashfree SDK modal actually opened
    "cashfree_checkout_failed",         # Cashfree returned an error (not user-cancel)
    "checkout_exit_survey_shown",       # Returned to billing without payment
    "checkout_exit_survey_submitted",
    "checkout_exit_survey_dismissed",
    # ═══ V9 — P0 In-Product Guided Experience (Apr 26, 2026) ═══
    "guide_opened",                     # ActionGuide drawer opened
    "guide_completed",                  # User confirmed primary CTA
    "skipped_guide",                    # Closed without confirming
    "started_after_guide",              # Story-to-Video CTA after guide
    "remix_after_guide",                # Remix CTA after guide
    "continue_after_guide",             # Continue CTA after guide
    "battle_after_guide",               # Battle CTA after guide
    # ═══ V10 — Photo Trailer share funnel (2026-04-29 founder directive) ═══
    # Public /trailer/:slug funnel: distribution measurement + paid-tier proof.
    "share_page_view",                  # /trailer/:slug rendered
    "video_play_clicked",               # User pressed play (video element fired play)
    "watch_25",                         # Reached 25% of duration
    "watch_50",                         # Reached 50% of duration
    "watch_75",                         # Reached 75% of duration
    "completed_watch",                  # Reached 99%+ (treat as completion)
    "make_your_own_clicked",            # CTA in share-page hit
    "whatsapp_share_clicked",           # WA share button on share page
    "native_share_clicked",             # navigator.share / Copy on share page
    # signup_started + signup_completed already exist above (V4)
    "first_trailer_created",            # First COMPLETED trailer per user
    # Paywall + plan
    "photo_trailer_paywall_shown",
    "photo_trailer_paywall_upgrade_clicked",
    "photo_trailer_quota_exhausted",
    "photo_trailer_plan_blocked",
    "photo_trailer_prompt_blocked",
    "photo_trailer_shared",
    "photo_trailer_whatsapp_share_clicked",
    "photo_trailer_page_viewed",
    "photo_trailer_generation_started",
    # ═══ V11 — Low-credit revenue UX (2026-04-29) ═══
    "photo_trailer_low_credit_seen",
    "photo_trailer_buy_credit_clicked",
    "photo_trailer_subscribe_clicked",
    "photo_trailer_duration_downgraded",
    "photo_trailer_credit_fail_recovered",
    # Generation start failures (2026-04-29) — every "Could not start" needs
    # a measurable code so we can see WHY users bounce on Generate
    "photo_trailer_start_failed",
    # Download conversion (2026-04-29) — confirms the result deliverable
    # actually leaves the system as a downloaded file
    "photo_trailer_download_clicked",
    # Auto-recovery from reliability sprint
    "photo_trailer_auto_requeued",
    # ═══ V12 — Mandatory Subscription / Zero Free Credits Policy (2026-05) ═══
    "free_user_blocked_post_policy_first",   # First time a user hits the new block
    "free_user_blocked_post_policy_repeat",  # Subsequent blocks in same session
    "pricing_page_opened_from_block",        # User clicked Subscribe CTA on the modal
    # Public Creator Tools grid (Landing page) — measures interest per tool
    "public_creator_tool_clicked",
    # Credit-gate modal — revenue P0 routing fix (2026-05)
    "credit_gate_buy_credits_clicked",
    "credit_gate_view_plans_clicked",
    "billing_section_opened_from_gate",
    # ═══ V13 — P0 Activation Funnel Re-Spine (2026-05) ═══
    # Founder directive 2026-05: a single canonical activation chain with
    # explicit abandonment attribution. Mirrors the brief verbatim.
    "hero_cta_clicked",
    "story_prompt_started",
    "story_first_keystroke",
    "story_prompt_submitted",
    "story_generation_abandoned",
    "story_publish_clicked",
    "story_published",
    # Share-loop instrumentation (per-channel)
    "share_sheet_opened",
    "share_channel_selected",
    "share_link_copied",
    "share_link_opened",
    "continued_from_share",
    "reshared_story",
    # Performance SLA telemetry — explicit names from the founder brief
    "prompt_to_teaser",                  # ms from prompt_submitted → first teaser visible
    "generation_total_latency",          # ms full server-side generation
    "generation_failure_reason",         # explicit error code/category emitted on failure
    # P0-4 May 2026 — anonymous pre-wow flow
    "session_resurrected",               # anon session restored from localStorage <24h
    # P0 2026-05-16 — "View Progress" / "Leave & come back later" trust bug fix
    "progress_cta_clicked",              # user clicked any progress CTA on /my-space card
    "progress_view_opened",              # the CTA produced visible navigation/focus
    "progress_view_failed",              # handler exception or missing job_id
]


# ─── 2026-05 V13 — Canonical abandonment reason taxonomy ─────────────
# Founder directive: NO generic buckets. Every dropoff must map to one of
# these explicit reasons. Anything outside this list is treated as
# `unmapped_reason` in the diagnostics and surfaces as a red flag for
# the agent to add a new canonical case.
ABANDONMENT_REASONS = {
    "auth_wall_before_preview",        # user hit signup before first wow
    "upload_confusion",                # uploaded image but never selected an option
    "generation_timeout",              # client-side >15s timeout
    "teaser_latency_gt_5s",            # teaser took longer than 5s SLA
    "prompt_unclear",                  # user typed then deleted everything
    "empty_state_no_examples",         # blank input + no example prompts visible
    "mobile_keyboard_overlap",         # mobile keyboard covered submit button
    "payment_wall_pre_wow",            # paywall fired before first generation
    "story_generation_failed",         # backend returned non-200
    "user_idle_after_prompt",          # >60s of inactivity after typing
    "user_navigated_away",             # page unload before generation finished
    "rage_clicked_cta_no_progress",    # 3+ rapid CTA clicks without state change
    "unmapped_reason",                 # catch-all — flag for agent to triage
}


# Canonical activation-funnel ordering — V13 rewritten 2026-05 per founder
# brief. Six explicit steps from landing to publish, in order. Anything that
# breaks this order is the bug.
ACTIVATION_FUNNEL_ORDER = [
    ("landing_view",                  "Landing"),
    ("hero_cta_clicked",              "CTA Clicked"),
    ("story_prompt_started",          "Prompt Started"),
    ("story_prompt_submitted",        "Prompt Submitted"),
    ("story_generation_started",      "Generation Started"),
    ("story_generation_completed",    "Generation Completed"),
    ("story_published",               "Published"),
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
        # V13 2026-05 — explicit anonymous identifier (frontend-supplied,
        # persistent across page loads via localStorage). Captures real
        # anonymous-vs-auth split independent of user_id presence.
        "anonymous_id": ctx.get("anonymous_id") or body.get("anonymous_id"),
        "auth_state": ("authenticated" if user_id else "anonymous"),
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
        # V13 2026-05 — explicit telemetry fields from founder brief
        "latency_ms": ctx.get("latency_ms"),
        "generation_id": ctx.get("generation_id"),
        "abandonment_step": ctx.get("abandonment_step"),
        "abandonment_reason": ctx.get("abandonment_reason"),
        "share_channel": ctx.get("share_channel"),         # whatsapp | instagram | telegram | x | copy | native
        "share_story_id": ctx.get("share_story_id"),
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
            "auth_state": {"$first": "$auth_state"},
        }},
    ]
    session_timelines: dict = {}
    async for d in db.funnel_events.aggregate(pipe):
        sid = d["_id"]["session"]
        st = d["_id"]["step"]
        node = session_timelines.setdefault(sid, {"steps": {}, "device_type": d.get("device_type"),
                                                  "browser": d.get("browser"), "country": d.get("country"),
                                                  "auth_state": d.get("auth_state")})
        node["steps"][st] = d["ts"]
        # auth_state can be set on later events even if first event was anon
        if d.get("auth_state") == "authenticated":
            node["auth_state"] = "authenticated"

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
        p95_to_next_ms = None
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
                p95_to_next_ms = int(deltas[max(0, int(len(deltas) * 0.95) - 1)])

        mobile = sum(1 for s in sessions_at_stage if s.get("device_type") == "mobile")
        desktop = sum(1 for s in sessions_at_stage if s.get("device_type") == "desktop")
        tablet = sum(1 for s in sessions_at_stage if s.get("device_type") == "tablet")
        auth_sessions = sum(1 for s in sessions_at_stage if s.get("auth_state") == "authenticated")
        anon_sessions = count - auth_sessions

        stages.append({
            "step": step,
            "label": label,
            "sessions": count,
            "conversion_from_prev_pct": conv_pct,
            "median_to_next_ms": median_to_next_ms,
            "p95_to_next_ms": p95_to_next_ms,
            "mobile": mobile,
            "desktop": desktop,
            "tablet": tablet,
            "auth_sessions": auth_sessions,
            "anon_sessions": anon_sessions,
        })

    # ─── 2026-05 V13 — Red-alert thresholds from founder brief ────────
    # The brief specifies hard floors for each transition; flag any breach.
    RED_THRESHOLDS = {
        ("hero_cta_clicked", "story_prompt_started"): {"min_conv_pct": 60.0, "label": "CTA→Prompt Started"},
        ("story_prompt_submitted", "story_generation_started"): {"min_conv_pct": 85.0, "label": "Prompt Submitted→Generation Started"},
        ("story_generation_started", "story_generation_completed"): {"min_conv_pct": 90.0, "label": "Generation Success Rate"},
        ("story_prompt_submitted", "story_generation_completed"): {"max_median_ms": 8000, "label": "Median Generation Latency"},
    }
    red_alerts = []
    step_to_idx = {s["step"]: idx for idx, s in enumerate(stages)}
    for (from_step, to_step), rule in RED_THRESHOLDS.items():
        if from_step not in step_to_idx or to_step not in step_to_idx:
            continue
        from_s = stages[step_to_idx[from_step]]
        to_s = stages[step_to_idx[to_step]]
        if from_s["sessions"] == 0:
            continue
        conv = round((to_s["sessions"] / from_s["sessions"]) * 100, 1)
        if "min_conv_pct" in rule and conv < rule["min_conv_pct"]:
            red_alerts.append({
                "rule": rule["label"],
                "observed_pct": conv,
                "threshold_pct": rule["min_conv_pct"],
                "from_step": from_step,
                "to_step": to_step,
                "severity": "red",
            })
        if "max_median_ms" in rule and from_s.get("median_to_next_ms"):
            if from_s["median_to_next_ms"] > rule["max_median_ms"]:
                red_alerts.append({
                    "rule": rule["label"],
                    "observed_ms": from_s["median_to_next_ms"],
                    "threshold_ms": rule["max_median_ms"],
                    "from_step": from_step,
                    "to_step": to_step,
                    "severity": "red",
                })

    # ─── 2026-05 V13 — Abandonment-reason rollup ─────────────────────
    # Top reasons for each abandonment step, sourced from the
    # abandonment_step + abandonment_reason context fields on the events.
    abandon_pipe = [
        {"$match": {**base_match, "step": {"$in": ["story_generation_abandoned", "story_generation_failed", "story_generation_timeout"]},
                    "abandonment_reason": {"$ne": None}}},
        {"$group": {"_id": {"step": "$abandonment_step", "reason": "$abandonment_reason"},
                    "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 20},
    ]
    abandonment_breakdown = []
    unmapped_reasons = []
    async for d in db.funnel_events.aggregate(abandon_pipe):
        reason = d["_id"].get("reason")
        is_canonical = reason in ABANDONMENT_REASONS
        if not is_canonical and reason:
            unmapped_reasons.append({"reason": reason, "count": d["count"]})
        abandonment_breakdown.append({
            "abandonment_step": d["_id"].get("step"),
            "abandonment_reason": reason,
            "is_canonical": is_canonical,
            "count": d["count"],
        })

    # ─── 2026-05 V13 — Biggest-drop badge ────────────────────────────
    # Find the worst step-to-step conversion in the funnel so the UI can
    # highlight ONE concrete bottleneck instead of overwhelming the user.
    biggest_drop = None
    for i in range(1, len(stages)):
        prev = stages[i - 1]
        curr = stages[i]
        if prev["sessions"] == 0:
            continue
        conv = curr["sessions"] / prev["sessions"] * 100
        drop_pct = 100 - conv
        if biggest_drop is None or drop_pct > biggest_drop["drop_pct"]:
            biggest_drop = {
                "from_step": prev["step"],
                "from_label": prev["label"],
                "to_step": curr["step"],
                "to_label": curr["label"],
                "from_sessions": prev["sessions"],
                "to_sessions": curr["sessions"],
                "conversion_pct": round(conv, 1),
                "drop_pct": round(drop_pct, 1),
                "median_to_next_ms": prev.get("median_to_next_ms"),
                "p95_to_next_ms": prev.get("p95_to_next_ms"),
            }

    # ─── 2026-05 V13 — Rage-click + repeated-CTA detection ───────────
    # Count sessions where the same step fires >= 3 times within 5s of
    # the FIRST hit for that step. Strong UX-stuck signal.
    rage_pipe = [
        {"$match": {**base_match, "step": {"$in": ["hero_cta_clicked", "landing_cta_clicked", "first_action_click"]}}},
        {"$group": {"_id": {"session": "$session_id"}, "hits": {"$sum": 1},
                    "first": {"$min": "$timestamp"}, "last": {"$max": "$timestamp"}}},
        {"$match": {"hits": {"$gte": 3}}},
    ]
    rage_click_sessions = 0
    repeated_cta_sessions = 0
    async for d in db.funnel_events.aggregate(rage_pipe):
        repeated_cta_sessions += 1
        try:
            first = datetime.fromisoformat(d["first"])
            last = datetime.fromisoformat(d["last"])
            if (last - first).total_seconds() <= 5:
                rage_click_sessions += 1
        except Exception:
            pass

    # ─── 2026-05 V13 — Median time-to-abandon ────────────────────────
    # For sessions that hit `hero_cta_clicked` but never reached
    # `story_generation_completed`, how long did they stick around?
    drop_durations = []
    for sess in session_timelines.values():
        steps_hit = sess["steps"]
        if "hero_cta_clicked" in steps_hit and "story_generation_completed" not in steps_hit:
            ts_values = [v for v in steps_hit.values() if v]
            if len(ts_values) >= 2:
                try:
                    earliest = min(datetime.fromisoformat(t) for t in ts_values)
                    latest = max(datetime.fromisoformat(t) for t in ts_values)
                    drop_durations.append((latest - earliest).total_seconds() * 1000)
                except Exception:
                    pass
    median_time_to_abandon_ms = None
    if drop_durations:
        drop_durations.sort()
        median_time_to_abandon_ms = int(drop_durations[len(drop_durations) // 2])

    # ─── 2026-05 V13 — Mobile vs desktop abandonment heatmap ─────────
    # Per-step, what fraction of mobile vs desktop sessions DIE here?
    heatmap = []
    for i in range(len(stages) - 1):
        prev = stages[i]
        curr = stages[i + 1]
        # sessions that hit prev but NOT curr, split by device
        died_mobile = 0
        died_desktop = 0
        for sess in session_timelines.values():
            if prev["step"] in sess["steps"] and curr["step"] not in sess["steps"]:
                if sess.get("device_type") == "mobile":
                    died_mobile += 1
                elif sess.get("device_type") == "desktop":
                    died_desktop += 1
        heatmap.append({
            "from_step": prev["step"],
            "from_label": prev["label"],
            "mobile_died": died_mobile,
            "desktop_died": died_desktop,
            "mobile_total": prev.get("mobile", 0),
            "desktop_total": prev.get("desktop", 0),
            "mobile_death_pct": round((died_mobile / prev["mobile"]) * 100, 1) if prev.get("mobile") else 0.0,
            "desktop_death_pct": round((died_desktop / prev["desktop"]) * 100, 1) if prev.get("desktop") else 0.0,
        })

    top_exit = None
    top_exit_drop_count = 0
    for i in range(len(stages) - 1):
        drop = stages[i]["sessions"] - stages[i + 1]["sessions"]
        if drop > top_exit_drop_count:
            top_exit_drop_count = drop
            top_exit = {
                "after_step": stages[i]["label"],
                "drop_count": drop,
                "drop_pct": round((drop / stages[i]["sessions"]) * 100, 1) if stages[i]["sessions"] else 0.0,
            }

    # ─── 2026-05 V13.1 — Auth-wall detection (separate, above-the-fold) ───
    # The single most expensive failure mode: signup blocking the wow moment.
    # Count sessions that ever fired any of these explicit signals.
    auth_wall_pipe = [
        {"$match": {**base_match, "$or": [
            {"abandonment_reason": {"$in": ["auth_wall_before_preview", "payment_wall_pre_wow"]}},
            {"step": "auth_redirect_loop_detected"},
        ]}},
        {"$group": {
            "_id": {
                "reason": {"$ifNull": ["$abandonment_reason", "$step"]},
            },
            "sessions": {"$addToSet": "$session_id"},
        }},
        {"$project": {"reason": "$_id.reason", "_id": 0, "session_count": {"$size": "$sessions"}}},
    ]
    auth_wall_breakdown = []
    auth_wall_total_sessions = set()
    async for d in db.funnel_events.aggregate(auth_wall_pipe):
        auth_wall_breakdown.append(d)
    # Count unique sessions across all reasons
    auth_wall_session_pipe = [
        {"$match": {**base_match, "$or": [
            {"abandonment_reason": {"$in": ["auth_wall_before_preview", "payment_wall_pre_wow"]}},
            {"step": "auth_redirect_loop_detected"},
        ]}},
        {"$group": {"_id": "$session_id"}},
        {"$count": "total"},
    ]
    async for d in db.funnel_events.aggregate(auth_wall_session_pipe):
        auth_wall_total_sessions = d.get("total", 0)
    if isinstance(auth_wall_total_sessions, set):
        auth_wall_total_sessions = 0
    auth_wall_pct = 0.0
    landing_sessions = stages[0]["sessions"] if stages else 0
    if landing_sessions:
        auth_wall_pct = round((auth_wall_total_sessions / landing_sessions) * 100, 1)

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
        "speed_sla_breached",
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

    # ═══ Speed SLA roll-up (P0 #5) ═══
    # Compute median + p95 elapsed_ms per timing event, plus breach %.
    sla_events = ["cta_to_first_paint", "cta_to_wow", "teaser_ready"]
    sla_thresholds_ms = {"cta_to_first_paint": 1500, "cta_to_wow": 3000, "teaser_ready": 5000}
    speed_sla = []
    for ev in sla_events:
        cursor = db.funnel_events.find(
            {**base_match, "step": ev, "meta.elapsed_ms": {"$gte": 0}},
            {"_id": 0, "meta.elapsed_ms": 1},
        )
        elapsed = []
        async for d in cursor:
            v = (d.get("meta") or {}).get("elapsed_ms")
            if isinstance(v, (int, float)):
                elapsed.append(v)
        threshold = sla_thresholds_ms[ev]
        if elapsed:
            elapsed.sort()
            median = elapsed[len(elapsed) // 2]
            p95 = elapsed[max(0, int(len(elapsed) * 0.95) - 1)]
            breaches = sum(1 for e in elapsed if e > threshold)
            speed_sla.append({
                "event": ev,
                "threshold_ms": threshold,
                "samples": len(elapsed),
                "median_ms": int(median),
                "p95_ms": int(p95),
                "breach_count": breaches,
                "breach_pct": round((breaches / len(elapsed)) * 100, 1),
            })
        else:
            speed_sla.append({
                "event": ev, "threshold_ms": threshold, "samples": 0,
                "median_ms": None, "p95_ms": None, "breach_count": 0, "breach_pct": 0.0,
            })

    return {
        "success": True,
        "period_days": days,
        "filter": {"device_type": device_type, "browser": browser, "utm_source": utm_source},
        "stages": stages,
        "top_exit_step": top_exit,
        "browser_split": browser_split_sorted,
        "country_split": country_split_sorted,
        "error_breakdown": error_breakdown,
        "speed_sla": speed_sla,
        "red_alerts": red_alerts,
        "abandonment_breakdown": abandonment_breakdown,
        "unmapped_reasons": unmapped_reasons,
        "biggest_drop": biggest_drop,
        "rage_click_sessions": rage_click_sessions,
        "repeated_cta_sessions": repeated_cta_sessions,
        "median_time_to_abandon_ms": median_time_to_abandon_ms,
        "abandonment_heatmap": heatmap,
        "auth_wall": {
            "total_sessions": auth_wall_total_sessions,
            "pct_of_landing": auth_wall_pct,
            "breakdown": auth_wall_breakdown,
        },
        "canonical_abandonment_reasons": sorted(ABANDONMENT_REASONS),
        "total_sessions_seen": len(session_timelines),
    }


# ─── 2026-05 V13.1 — P0-4 Before / After Comparison ────────────────────
# Founder directive: when we ship the anonymous pre-wow flow we MUST be
# able to answer "did it work?" within 48h. This endpoint splits all the
# critical activation metrics into pre-P0-4 vs post-P0-4 cohorts based on
# a marker timestamp stored in `funnel_config.p04_launch_ts`.
@router.get("/p04-comparison")
async def p04_comparison(
    user: dict = Depends(get_admin_user),
    days_before: int = Query(7, ge=1, le=30, description="Days to look back from launch"),
    days_after: int = Query(7, ge=1, le=30, description="Days to look forward from launch"),
):
    cfg = await db.funnel_config.find_one({"_id": "p04"}, {"_id": 0})
    if not cfg or not cfg.get("p04_launch_ts"):
        return {
            "success": False,
            "error": "p04_launch_ts not set. POST /api/funnel/p04-launch to mark the flip moment.",
        }
    launch_ts = cfg["p04_launch_ts"]
    try:
        launch_dt = datetime.fromisoformat(launch_ts.replace("Z", "+00:00"))
    except Exception:
        return {"success": False, "error": f"Invalid launch ts: {launch_ts}"}

    pre_start = (launch_dt - timedelta(days=days_before)).isoformat()
    pre_end = launch_dt.isoformat()
    post_start = launch_dt.isoformat()
    post_end = (launch_dt + timedelta(days=days_after)).isoformat()

    async def _cohort_metrics(ts_start: str, ts_end: str) -> dict:
        base = {"timestamp": {"$gte": ts_start, "$lt": ts_end}}

        async def _unique(step: str, extra: dict | None = None) -> int:
            match = {**base, "step": step}
            if extra:
                match.update(extra)
            rows = await db.funnel_events.aggregate([
                {"$match": match},
                {"$group": {"_id": "$session_id"}},
                {"$count": "n"},
            ]).to_list(1)
            return rows[0]["n"] if rows else 0

        landing = await _unique("landing_view")
        cta = await _unique("hero_cta_clicked")
        prompt_started = await _unique("story_prompt_started")
        generated = await _unique("story_generation_completed") or await _unique("story_generated_success")
        published = await _unique("story_published")

        # Anon vs Auth split for generation completed
        anon_generated_rows = await db.funnel_events.aggregate([
            {"$match": {**base, "step": {"$in": ["story_generation_completed", "story_generated_success"]},
                        "auth_state": {"$ne": "authenticated"}}},
            {"$group": {"_id": "$session_id"}},
            {"$count": "n"},
        ]).to_list(1)
        auth_generated_rows = await db.funnel_events.aggregate([
            {"$match": {**base, "step": {"$in": ["story_generation_completed", "story_generated_success"]},
                        "auth_state": "authenticated"}},
            {"$group": {"_id": "$session_id"}},
            {"$count": "n"},
        ]).to_list(1)
        anon_generated = anon_generated_rows[0]["n"] if anon_generated_rows else 0
        auth_generated = auth_generated_rows[0]["n"] if auth_generated_rows else 0

        # Teaser latency (prompt_to_teaser median + p95)
        latency_rows = []
        cursor = db.funnel_events.find(
            {**base, "step": "prompt_to_teaser", "latency_ms": {"$gt": 0}},
            {"_id": 0, "latency_ms": 1},
        )
        async for d in cursor:
            v = d.get("latency_ms")
            if isinstance(v, (int, float)):
                latency_rows.append(v)
        latency_rows.sort()
        teaser_median = int(latency_rows[len(latency_rows) // 2]) if latency_rows else None
        teaser_p95 = int(latency_rows[max(0, int(len(latency_rows) * 0.95) - 1)]) if latency_rows else None

        # Abandonment: sessions that hit hero_cta but never reached generation_completed
        cta_sessions = await db.funnel_events.aggregate([
            {"$match": {**base, "step": "hero_cta_clicked"}},
            {"$group": {"_id": "$session_id"}},
        ]).to_list(None)
        completed_sessions = await db.funnel_events.aggregate([
            {"$match": {**base, "step": {"$in": ["story_generation_completed", "story_generated_success"]}}},
            {"$group": {"_id": "$session_id"}},
        ]).to_list(None)
        cta_set = {r["_id"] for r in cta_sessions}
        completed_set = {r["_id"] for r in completed_sessions}
        abandoned = len(cta_set - completed_set)
        abandonment_pct = round((abandoned / len(cta_set)) * 100, 1) if cta_set else 0.0

        # Auth-wall hits in this window
        auth_wall_rows = await db.funnel_events.aggregate([
            {"$match": {**base, "$or": [
                {"abandonment_reason": {"$in": ["auth_wall_before_preview", "payment_wall_pre_wow"]}},
                {"step": "auth_redirect_loop_detected"},
            ]}},
            {"$group": {"_id": "$session_id"}},
            {"$count": "n"},
        ]).to_list(1)
        auth_wall = auth_wall_rows[0]["n"] if auth_wall_rows else 0

        return {
            "landing_sessions": landing,
            "cta_clicked": cta,
            "prompt_started": prompt_started,
            "story_generated": generated,
            "story_published": published,
            "anon_generated": anon_generated,
            "auth_generated": auth_generated,
            "cta_to_generation_pct": round((generated / cta) * 100, 1) if cta else 0.0,
            "landing_to_generation_pct": round((generated / landing) * 100, 1) if landing else 0.0,
            "anon_share_of_generation_pct": round((anon_generated / generated) * 100, 1) if generated else 0.0,
            "teaser_median_ms": teaser_median,
            "teaser_p95_ms": teaser_p95,
            "abandoned_after_cta": abandoned,
            "abandonment_pct": abandonment_pct,
            "auth_wall_sessions": auth_wall,
        }

    pre = await _cohort_metrics(pre_start, pre_end)
    post = await _cohort_metrics(post_start, post_end)

    def _delta(post_v, pre_v):
        if post_v is None or pre_v is None:
            return None
        return round(post_v - pre_v, 1)

    deltas = {
        "story_generated_delta": post["story_generated"] - pre["story_generated"],
        "cta_to_generation_pct_delta": _delta(post["cta_to_generation_pct"], pre["cta_to_generation_pct"]),
        "landing_to_generation_pct_delta": _delta(post["landing_to_generation_pct"], pre["landing_to_generation_pct"]),
        "anon_share_of_generation_pct_delta": _delta(post["anon_share_of_generation_pct"], pre["anon_share_of_generation_pct"]),
        "teaser_median_ms_delta": _delta(post["teaser_median_ms"], pre["teaser_median_ms"]),
        "abandonment_pct_delta": _delta(post["abandonment_pct"], pre["abandonment_pct"]),
        "auth_wall_delta": post["auth_wall_sessions"] - pre["auth_wall_sessions"],
    }

    # Hard verdict — did P0-4 work?
    verdict_signals = []
    if deltas.get("cta_to_generation_pct_delta") is not None:
        if deltas["cta_to_generation_pct_delta"] >= 5.0:
            verdict_signals.append("CTA→Generation up by ≥5pp")
        elif deltas["cta_to_generation_pct_delta"] <= -2.0:
            verdict_signals.append("CTA→Generation regressed")
    if deltas.get("abandonment_pct_delta") is not None and deltas["abandonment_pct_delta"] <= -5.0:
        verdict_signals.append("Abandonment dropped ≥5pp")
    if deltas.get("auth_wall_delta") is not None and deltas["auth_wall_delta"] < 0:
        verdict_signals.append("Auth-wall hits reduced")

    if deltas.get("cta_to_generation_pct_delta") is not None and deltas["cta_to_generation_pct_delta"] >= 5.0:
        verdict = "IMPROVED"
    elif deltas.get("cta_to_generation_pct_delta") is not None and deltas["cta_to_generation_pct_delta"] <= -2.0:
        verdict = "REGRESSED"
    elif pre["landing_sessions"] < 50 or post["landing_sessions"] < 50:
        verdict = "INSUFFICIENT_DATA"
    else:
        verdict = "FLAT"

    return {
        "success": True,
        "p04_launch_ts": launch_ts,
        "window": {
            "pre_start": pre_start, "pre_end": pre_end,
            "post_start": post_start, "post_end": post_end,
            "days_before": days_before, "days_after": days_after,
        },
        "pre": pre,
        "post": post,
        "deltas": deltas,
        "verdict": verdict,
        "verdict_signals": verdict_signals,
    }


@router.post("/p04-launch")
async def p04_set_launch(
    user: dict = Depends(get_admin_user),
    ts: Optional[str] = Query(None, description="ISO8601 launch ts; defaults to now"),
):
    """Marks the moment P0-4 (anonymous pre-wow flow) goes live so the
    /p04-comparison endpoint can split metrics before/after."""
    launch_ts = ts or datetime.now(timezone.utc).isoformat()
    await db.funnel_config.update_one(
        {"_id": "p04"},
        {"$set": {"p04_launch_ts": launch_ts, "updated_by": user.get("id"), "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"success": True, "p04_launch_ts": launch_ts}


@router.get("/p04-launch")
async def p04_get_launch(user: dict = Depends(get_admin_user)):
    cfg = await db.funnel_config.find_one({"_id": "p04"}, {"_id": 0})
    return {"success": True, "p04_launch_ts": (cfg or {}).get("p04_launch_ts")}


@router.get("/revenue-conversion")
async def revenue_conversion(
    user: dict = Depends(get_admin_user),
    days: int = Query(7, ge=1, le=90),
):
    """
    P1 Revenue Conversion Sprint — strictly the 5 metrics the founder cares about
    for the next 72 hours:

      1. Story Completed → Video CTA Click %
      2. Video CTA Click → Checkout Start %
      3. Checkout Start → Payment %
      4. Share Click %
      5. Revenue / 100 visitors

    Plus a leaderboard of the outcome-led video CTA variants (P1.1 A/B test):
    impressions, clicks, CTR per variant.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    base = {"timestamp": {"$gte": cutoff}}

    async def _unique_sessions(step: str) -> int:
        agg = await db.funnel_events.aggregate([
            {"$match": {**base, "step": step}},
            {"$group": {"_id": "$session_id"}},
            {"$count": "n"},
        ]).to_list(1)
        return agg[0]["n"] if agg else 0

    async def _event_count(step: str) -> int:
        return await db.funnel_events.count_documents({**base, "step": step})

    # Sessions reaching each step
    landing_sessions   = await _unique_sessions("landing_view")
    completed_sessions = await _unique_sessions("story_generated_success")
    video_cta_sessions = await _unique_sessions("cta_video_clicked")
    checkout_sessions  = await _unique_sessions("checkout_started")
    payment_sessions   = await _unique_sessions("payment_success")
    share_clicks       = await _event_count("cta_share_clicked")

    # P1.7 — payment choke-point telemetry
    login_loaded_sessions   = await _unique_sessions("login_page_loaded")
    cashfree_open_sessions  = await _unique_sessions("cashfree_checkout_opened")
    cashfree_fail_sessions  = await _unique_sessions("cashfree_checkout_failed")
    payment_started_sessions = await _unique_sessions("payment_started")

    # Revenue: pull from a known orders / payments collection if present.
    # Fall back to a flat-rate estimate from payment_success count × ₹29
    # so the dashboard always shows a directional number.
    revenue_inr = 0.0
    try:
        async for doc in db.orders.find(
            {"status": "paid", "created_at": {"$gte": cutoff}},
            {"_id": 0, "amount_inr": 1, "amount": 1, "currency": 1},
        ):
            amt = doc.get("amount_inr") or doc.get("amount") or 0
            if (doc.get("currency") or "INR").upper() == "INR":
                revenue_inr += float(amt or 0)
    except Exception:
        pass
    if revenue_inr <= 0 and payment_sessions > 0:
        # Fallback proxy: assume ₹29 average (matches the visible CTA price)
        revenue_inr = payment_sessions * 29.0

    def _pct(n, d):
        return round((n / d) * 100, 1) if d > 0 else 0.0

    metrics = {
        "story_completed_to_video_cta_pct": _pct(video_cta_sessions, completed_sessions),
        "video_cta_to_checkout_pct":        _pct(checkout_sessions, video_cta_sessions),
        "checkout_to_payment_pct":          _pct(payment_sessions, checkout_sessions),
        "share_pct":                        _pct(share_clicks, completed_sessions),
        "revenue_per_100_visitors":         round((revenue_inr / landing_sessions * 100), 2) if landing_sessions > 0 else 0.0,
        # P1.7 — payment choke point precision
        "login_redirect_dropoff_pct":       round(100 - _pct(login_loaded_sessions, checkout_sessions), 1) if checkout_sessions > 0 else 0.0,
        "cashfree_opened_pct":              _pct(cashfree_open_sessions, payment_started_sessions),
        "cashfree_success_pct":             _pct(payment_sessions, cashfree_open_sessions),
        "cashfree_dropoff_pct":             round(100 - _pct(payment_sessions, cashfree_open_sessions), 1) if cashfree_open_sessions > 0 else 0.0,
    }

    # ─── P1.1 Outcome-led video CTA variant leaderboard ──────────────────
    variant_pipe = [
        {"$match": {**base, "step": {"$in": [
            "video_cta_variant_impression", "cta_video_clicked",
            "video_reward_preview_cta_clicked", "checkout_started",
        ]}, "meta.video_cta_variant": {"$ne": None}}},
        {"$group": {
            "_id": {"variant": "$meta.video_cta_variant", "step": "$step"},
            "sessions": {"$addToSet": "$session_id"},
        }},
        {"$project": {
            "variant": "$_id.variant", "step": "$_id.step",
            "unique_sessions": {"$size": "$sessions"}, "_id": 0,
        }},
    ]
    variant_buckets = {}
    async for d in db.funnel_events.aggregate(variant_pipe):
        v = d["variant"]
        node = variant_buckets.setdefault(v, {
            "variant": v, "impressions": 0, "clicks": 0,
            "preview_confirmed": 0, "checkouts": 0,
        })
        if d["step"] == "video_cta_variant_impression":
            node["impressions"] = d["unique_sessions"]
        elif d["step"] == "cta_video_clicked":
            node["clicks"] = d["unique_sessions"]
        elif d["step"] == "video_reward_preview_cta_clicked":
            node["preview_confirmed"] = d["unique_sessions"]
        elif d["step"] == "checkout_started":
            node["checkouts"] = d["unique_sessions"]

    video_cta_variants = []
    for v in variant_buckets.values():
        v["click_through_pct"]  = _pct(v["clicks"], v["impressions"])
        v["intent_confirm_pct"] = _pct(v["preview_confirmed"], v["clicks"])
        v["click_to_checkout_pct"] = _pct(v["checkouts"], v["clicks"])
        video_cta_variants.append(v)
    video_cta_variants.sort(key=lambda r: (r["click_through_pct"], r["impressions"]), reverse=True)

    return {
        "success": True,
        "period_days": days,
        "totals": {
            "landing_sessions": landing_sessions,
            "story_completed_sessions": completed_sessions,
            "video_cta_sessions": video_cta_sessions,
            "checkout_sessions": checkout_sessions,
            "payment_started_sessions": payment_started_sessions,
            "login_loaded_sessions": login_loaded_sessions,
            "cashfree_open_sessions": cashfree_open_sessions,
            "cashfree_fail_sessions": cashfree_fail_sessions,
            "payment_sessions": payment_sessions,
            "share_clicks": share_clicks,
            "revenue_inr": round(revenue_inr, 2),
        },
        "metrics": metrics,
        "video_cta_variants": video_cta_variants,
    }


# ─── P1.6 PURCHASE SURVEY ─────────────────────────────────────────────────

@router.post("/purchase-survey")
async def purchase_survey(request: Request):
    """
    Single-question post-payment survey. Founder spec: 'What made you buy today?'
    Choices: preview / price / story / needed_now / other (+ optional free-text).

    Stores in `purchase_surveys` collection AND fires a funnel event for the
    activation dashboard. Anonymous-friendly: tracks via session_id; user_id
    auto-extracted from JWT when present.
    """
    body = await request.json()
    answer = (body.get("answer") or "").strip().lower()
    note = (body.get("note") or "").strip()
    session_id = body.get("session_id") or str(uuid.uuid4())
    order_id = body.get("order_id")
    plan = body.get("plan")

    VALID = {"preview", "price", "story", "needed_now", "other"}
    if answer not in VALID:
        return {"success": False, "error": f"answer must be one of {sorted(VALID)}"}

    user_id = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            from shared import verify_token
            token_data = verify_token(auth_header.split(" ")[1])
            user_id = token_data.get("sub")
        except Exception:
            pass

    record = {
        "session_id": session_id,
        "user_id": user_id,
        "answer": answer,
        "note": note[:500],
        "order_id": order_id,
        "plan": plan,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_agent": request.headers.get("user-agent", "")[:200],
    }

    try:
        await db.purchase_surveys.insert_one(record)
    except Exception as e:
        logger.warning(f"purchase_survey insert failed: {e}")

    # Mirror to funnel for dashboard rollups
    try:
        await db.funnel_events.insert_one({
            "step": "purchase_survey_submitted",
            "event": "purchase_survey_submitted",
            "session_id": session_id,
            "user_id": user_id,
            "timestamp": record["timestamp"],
            "meta": {"answer": answer, "plan": plan, "order_id": order_id, "has_note": bool(note)},
        })
    except Exception:
        pass

    return {"success": True}


@router.get("/purchase-survey-summary")
async def purchase_survey_summary(
    user: dict = Depends(get_admin_user),
    days: int = Query(30, ge=1, le=365),
):
    """Admin rollup of post-payment survey answers — drives copy decisions."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    pipe = [
        {"$match": {"timestamp": {"$gte": cutoff}}},
        {"$group": {"_id": "$answer", "count": {"$sum": 1}}},
        {"$project": {"answer": "$_id", "_id": 0, "count": 1}},
    ]
    by_answer = []
    total = 0
    async for d in db.purchase_surveys.aggregate(pipe):
        by_answer.append(d)
        total += d["count"]
    by_answer.sort(key=lambda r: r["count"], reverse=True)
    for r in by_answer:
        r["pct"] = round((r["count"] / total) * 100, 1) if total else 0.0

    notes = []
    cursor = db.purchase_surveys.find(
        {"timestamp": {"$gte": cutoff}, "note": {"$ne": ""}},
        {"_id": 0, "answer": 1, "note": 1, "timestamp": 1, "plan": 1},
    ).sort("timestamp", -1).limit(40)
    async for d in cursor:
        notes.append(d)

    return {
        "success": True,
        "period_days": days,
        "total_responses": total,
        "by_answer": by_answer,
        "recent_notes": notes,
    }



# ─── P1.7 CHECKOUT EXIT SURVEY ────────────────────────────────────────────

@router.post("/checkout-exit-survey")
async def checkout_exit_survey(request: Request):
    """
    Fires when a user returns to the billing page WITHOUT completing payment.
    Founder spec: 'Anything stop you today?'
    Choices: price / payment_failed / needed_more_trust / just_browsing / other.
    """
    body = await request.json()
    answer = (body.get("answer") or "").strip().lower()
    note = (body.get("note") or "").strip()
    session_id = body.get("session_id") or str(uuid.uuid4())

    VALID = {"price", "payment_failed", "needed_more_trust", "just_browsing", "other"}
    if answer not in VALID:
        return {"success": False, "error": f"answer must be one of {sorted(VALID)}"}

    user_id = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            from shared import verify_token
            token_data = verify_token(auth_header.split(" ")[1])
            user_id = token_data.get("sub")
        except Exception:
            pass

    record = {
        "session_id": session_id,
        "user_id": user_id,
        "answer": answer,
        "note": note[:500],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await db.checkout_exit_surveys.insert_one(record)
    except Exception as e:
        logger.warning(f"checkout_exit_survey insert failed: {e}")

    try:
        await db.funnel_events.insert_one({
            "step": "checkout_exit_survey_submitted",
            "event": "checkout_exit_survey_submitted",
            "session_id": session_id,
            "user_id": user_id,
            "timestamp": record["timestamp"],
            "meta": {"answer": answer, "has_note": bool(note)},
        })
    except Exception:
        pass

    return {"success": True}


@router.get("/checkout-exit-survey-summary")
async def checkout_exit_survey_summary(
    user: dict = Depends(get_admin_user),
    days: int = Query(30, ge=1, le=365),
):
    """Admin rollup of checkout-exit objections — drives copy/UX decisions."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    pipe = [
        {"$match": {"timestamp": {"$gte": cutoff}}},
        {"$group": {"_id": "$answer", "count": {"$sum": 1}}},
        {"$project": {"answer": "$_id", "_id": 0, "count": 1}},
    ]
    by_answer, total = [], 0
    async for d in db.checkout_exit_surveys.aggregate(pipe):
        by_answer.append(d)
        total += d["count"]
    by_answer.sort(key=lambda r: r["count"], reverse=True)
    for r in by_answer:
        r["pct"] = round((r["count"] / total) * 100, 1) if total else 0.0

    notes = []
    cursor = db.checkout_exit_surveys.find(
        {"timestamp": {"$gte": cutoff}, "note": {"$ne": ""}},
        {"_id": 0, "answer": 1, "note": 1, "timestamp": 1},
    ).sort("timestamp", -1).limit(40)
    async for d in cursor:
        notes.append(d)

    return {
        "success": True,
        "period_days": days,
        "total_responses": total,
        "by_answer": by_answer,
        "recent_notes": notes,
    }


# ─── P1.7 PAID-FUNNEL SESSION REPLAY LITE ─────────────────────────────────

@router.get("/paid-funnel-sessions")
async def paid_funnel_sessions(
    user: dict = Depends(get_admin_user),
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Admin 'session replay lite' — last N sessions that hit
    `video_reward_preview_cta_clicked` (paid intent), with a chronological
    event timeline so the founder can reconstruct what each user did.

    Cheaper than a real session-replay tool, captures everything important.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    # Find sessions with paid intent
    intent_pipe = [
        {"$match": {"timestamp": {"$gte": cutoff}, "step": "video_reward_preview_cta_clicked"}},
        {"$group": {"_id": "$session_id", "first_intent_ts": {"$min": "$timestamp"}}},
        {"$sort": {"first_intent_ts": -1}},
        {"$limit": limit},
    ]
    session_ids = []
    intent_ts_map = {}
    async for d in db.funnel_events.aggregate(intent_pipe):
        session_ids.append(d["_id"])
        intent_ts_map[d["_id"]] = d["first_intent_ts"]

    if not session_ids:
        return {"success": True, "period_days": days, "sessions": []}

    # Pull each session's full timeline (capped at 80 events / session)
    sessions_out = []
    for sid in session_ids:
        timeline = []
        cursor = db.funnel_events.find(
            {"session_id": sid, "timestamp": {"$gte": cutoff}},
            {"_id": 0, "step": 1, "timestamp": 1, "device_type": 1, "browser": 1,
             "country": 1, "user_id": 1, "meta": 1, "page": 1},
        ).sort("timestamp", 1).limit(80)
        first_step, last_step = None, None
        device_type, browser, country, user_id_seen = None, None, None, None
        outcome = "intent_only"
        async for e in cursor:
            timeline.append({
                "step": e.get("step"),
                "ts": e.get("timestamp"),
                "page": e.get("page"),
                "meta": e.get("meta") or {},
            })
            first_step = first_step or e.get("step")
            last_step = e.get("step")
            device_type = device_type or e.get("device_type")
            browser = browser or e.get("browser")
            country = country or e.get("country")
            user_id_seen = user_id_seen or e.get("user_id")
            if e.get("step") == "payment_success":
                outcome = "paid"
            elif outcome == "intent_only" and e.get("step") in ("cashfree_checkout_failed", "payment_abandoned"):
                outcome = "abandoned"
        sessions_out.append({
            "session_id": sid,
            "user_id": user_id_seen,
            "device_type": device_type,
            "browser": browser,
            "country": country,
            "first_step": first_step,
            "last_step": last_step,
            "intent_ts": intent_ts_map.get(sid),
            "event_count": len(timeline),
            "outcome": outcome,
            "timeline": timeline,
        })

    return {
        "success": True,
        "period_days": days,
        "sessions": sessions_out,
    }



# ─── Photo Trailer Share-Funnel KPI pack ─────────────────────────────────────
# Founder directive 2026-04-29: "Need to know if YouStar actually spreads."
# Returns 5 conversion ratios + segmentation breakdowns over a rolling window.
# Read from `funnel_events` (existing collection) so no migration is needed.
@router.get("/youstar/kpis")
async def youstar_kpi_pack(
    user: dict = Depends(get_admin_user),
    days: int = Query(7, ge=1, le=90),
):
    """First-7-day KPI pack for the YouStar /trailer/:slug funnel.
    Read-only aggregation; safe to hammer."""
    from datetime import datetime, timezone, timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    async def _sessions(step: str, extra: dict | None = None) -> int:
        match = {"step": step, "timestamp": {"$gte": cutoff}}
        if extra: match.update(extra)
        rows = await db.funnel_events.aggregate([
            {"$match": match},
            {"$group": {"_id": "$session_id"}},
            {"$count": "n"},
        ]).to_list(1)
        return rows[0]["n"] if rows else 0

    views   = await _sessions("share_page_view")
    plays   = await _sessions("video_play_clicked")
    completes = await _sessions("completed_watch")
    cta_clicks  = await _sessions("make_your_own_clicked")
    wa_shares   = await _sessions("whatsapp_share_clicked")
    native_shares = await _sessions("native_share_clicked")
    signups       = await _sessions("signup_started")
    signups_done  = await _sessions("signup_success")
    first_trailers = await _sessions("first_trailer_created")

    def pct(n, d):
        if not d: return None
        return round(100.0 * n / d, 2)

    device_breakdown = {}
    async for d in db.funnel_events.aggregate([
        {"$match": {"step": "share_page_view", "timestamp": {"$gte": cutoff}}},
        {"$group": {"_id": "$device_type", "n": {"$sum": 1}}},
    ]):
        device_breakdown[d["_id"] or "unknown"] = d["n"]

    format_breakdown = {}
    async for d in db.funnel_events.aggregate([
        {"$match": {"step": "video_play_clicked", "timestamp": {"$gte": cutoff}}},
        {"$group": {"_id": "$meta.format", "n": {"$sum": 1}}},
    ]):
        format_breakdown[d["_id"] or "unknown"] = d["n"]

    source_breakdown = {}
    async for d in db.funnel_events.aggregate([
        {"$match": {"step": "share_page_view", "timestamp": {"$gte": cutoff}}},
        {"$group": {"_id": {"$ifNull": ["$utm_medium", "$traffic_source"]}, "n": {"$sum": 1}}},
    ]):
        source_breakdown[d["_id"] or "unknown"] = d["n"]

    plan_breakdown = {"FREE": 0, "PAID": 0, "PREMIUM": 0, "unknown": 0}
    async for d in db.funnel_events.aggregate([
        {"$match": {"step": "share_page_view", "timestamp": {"$gte": cutoff}}},
        {"$group": {"_id": "$meta.creator_plan", "n": {"$sum": 1}}},
    ]):
        k = d["_id"] or "unknown"
        plan_breakdown[k] = plan_breakdown.get(k, 0) + d["n"]

    duration_breakdown = {"20": 0, "60": 0, "90": 0, "other": 0}
    async for d in db.funnel_events.aggregate([
        {"$match": {"step": "share_page_view", "timestamp": {"$gte": cutoff}}},
        {"$group": {"_id": "$meta.duration", "n": {"$sum": 1}}},
    ]):
        k = str(d["_id"] or "other")
        bucket = k if k in duration_breakdown else "other"
        duration_breakdown[bucket] = duration_breakdown.get(bucket, 0) + d["n"]

    async def _share_rate(plan_filter: list) -> float:
        v = await db.funnel_events.aggregate([
            {"$match": {"step": "share_page_view", "timestamp": {"$gte": cutoff},
                        "meta.creator_plan": {"$in": plan_filter}}},
            {"$group": {"_id": "$session_id"}},
            {"$count": "n"},
        ]).to_list(1)
        s = await db.funnel_events.aggregate([
            {"$match": {"step": {"$in": ["whatsapp_share_clicked", "native_share_clicked"]},
                        "timestamp": {"$gte": cutoff},
                        "meta.creator_plan": {"$in": plan_filter}}},
            {"$group": {"_id": "$session_id"}},
            {"$count": "n"},
        ]).to_list(1)
        v_n = v[0]["n"] if v else 0
        s_n = s[0]["n"] if s else 0
        return pct(s_n, v_n)

    premium_share_rate = await _share_rate(["PREMIUM"])
    free_share_rate = await _share_rate(["FREE", "PAID"])

    return {
        "period_days": days,
        "cutoff": cutoff,
        "ratios": {
            "view_to_play_pct":          pct(plays, views),
            "play_to_signup_pct":        pct(signups, plays),
            "signup_to_first_trailer_pct": pct(first_trailers, signups_done),
            "view_to_share_pct":         pct(wa_shares + native_shares, views),
            "premium_share_rate_pct":    premium_share_rate,
            "free_share_rate_pct":       free_share_rate,
        },
        "volumes": {
            "share_page_view":   views,
            "video_play_clicked": plays,
            "completed_watch":   completes,
            "make_your_own_clicked": cta_clicks,
            "whatsapp_share_clicked": wa_shares,
            "native_share_clicked":   native_shares,
            "signup_started":         signups,
            "signup_success":         signups_done,
            "first_trailer_created":  first_trailers,
        },
        "segments": {
            "device":   device_breakdown,
            "format":   format_breakdown,
            "source":   source_breakdown,
            "creator_plan": plan_breakdown,
            "duration": duration_breakdown,
        },
    }



# ─── Photo Trailer Share-Funnel KPI pack ─────────────────────────────────────
# Founder directive 2026-04-29: "Need to know if YouStar actually spreads."
# Returns 5 conversion ratios + segmentation breakdowns over a rolling window.
# Read from `funnel_events` (existing collection) so no migration is needed.
@router.get("/youstar/kpis")
async def youstar_kpi_pack(
    user: dict = Depends(get_admin_user),
    days: int = Query(7, ge=1, le=90),
):
    """First-7-day KPI pack for the YouStar /trailer/:slug funnel.
    Read-only aggregation; safe to hammer."""
    from datetime import datetime, timezone, timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    async def _count(step: str, extra_match: dict | None = None) -> int:
        match = {"step": step, "timestamp": {"$gte": cutoff}}
        if extra_match: match.update(extra_match)
        n = await db.funnel_events.count_documents(match)
        return n

    # Distinct sessions per step (avoid counting the same viewer twice)
    async def _sessions(step: str, extra: dict | None = None) -> int:
        match = {"step": step, "timestamp": {"$gte": cutoff}}
        if extra: match.update(extra)
        rows = await db.funnel_events.aggregate([
            {"$match": match},
            {"$group": {"_id": "$session_id"}},
            {"$count": "n"},
        ]).to_list(1)
        return rows[0]["n"] if rows else 0

    views   = await _sessions("share_page_view")
    plays   = await _sessions("video_play_clicked")
    completes = await _sessions("completed_watch")
    cta_clicks  = await _sessions("make_your_own_clicked")
    