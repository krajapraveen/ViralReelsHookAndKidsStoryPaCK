"""
Admin Metrics API — Truth-based, real-time metrics for the admin control center.
Every metric has: definition, formula, data source, refresh frequency, empty state rule.
"""
from fastapi import APIRouter, Depends, Query
from datetime import datetime, timezone, timedelta
import logging

from shared import db, get_admin_user

logger = logging.getLogger("creatorstudio.admin_metrics")
router = APIRouter(prefix="/admin/metrics", tags=["Admin Metrics"])


def _now():
    return datetime.now(timezone.utc)


def _ago(hours=0, days=0, minutes=0):
    return _now() - timedelta(hours=hours, days=days, minutes=minutes)


def _today_start():
    now = _now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _safe_rate(num, den):
    if not den:
        return None
    return round(num / den * 100, 1)


# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTIVE SUMMARY — Core snapshot
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/summary")
async def get_executive_summary(days: int = Query(30, ge=1, le=365), admin: dict = Depends(get_admin_user)):
    """Executive snapshot: users, revenue, generations, satisfaction."""
    cutoff = _ago(days=days)
    today_start = _today_start()

    # Total users (live DB count)
    total_users = await db.users.count_documents({"role": {"$ne": "deleted"}})
    new_users_today = await db.users.count_documents({"created_at": {"$gte": today_start.isoformat()}})
    new_users_period = await db.users.count_documents({"created_at": {"$gte": cutoff.isoformat()}})

    # Active users (24h) — users with any activity log
    active_24h = 0
    try:
        pipeline = [
            {"$match": {"timestamp": {"$gte": _ago(hours=24).isoformat()}}},
            {"$group": {"_id": "$user_id"}},
            {"$count": "total"}
        ]
        result = await db.activity_logs.aggregate(pipeline).to_list(1)
        active_24h = result[0]["total"] if result else 0
    except Exception:
        # Fallback: count users with recent login
        active_24h = await db.users.count_documents({"last_login": {"$gte": _ago(hours=24).isoformat()}})

    # Active sessions (last 15 min)
    active_sessions = 0
    try:
        active_sessions = await db.user_sessions.count_documents({
            "last_activity": {"$gte": _ago(minutes=15).isoformat()},
            "status": "active"
        })
    except Exception:
        active_sessions = 0

    # Generations
    total_generations = await db.pipeline_jobs.count_documents({"created_at": {"$gte": cutoff.isoformat()}})
    completed_generations = await db.pipeline_jobs.count_documents({
        "created_at": {"$gte": cutoff.isoformat()},
        "status": "READY"
    })
    failed_generations = await db.pipeline_jobs.count_documents({
        "created_at": {"$gte": cutoff.isoformat()},
        "status": "FAILED"
    })
    success_rate = _safe_rate(completed_generations, total_generations)
    failure_rate = _safe_rate(failed_generations, total_generations)

    # Revenue (from payments)
    revenue_pipeline = [
        {"$match": {"status": "paid", "created_at": {"$gte": cutoff.isoformat()}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    rev_result = await db.payments.aggregate(revenue_pipeline).to_list(1)
    total_revenue = rev_result[0]["total"] if rev_result else 0

    rev_today_pipeline = [
        {"$match": {"status": "paid", "created_at": {"$gte": today_start.isoformat()}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    rev_today_result = await db.payments.aggregate(rev_today_pipeline).to_list(1)
    revenue_today = rev_today_result[0]["total"] if rev_today_result else 0

    # Satisfaction (from real ratings only — truth-based)
    # Formula: avg_rating = avg(real rating values), satisfaction_pct = (avg_rating / 5) * 100
    # Minimum 5 ratings required for meaningful metric
    avg_rating = None
    rating_count = 0
    satisfaction_pct = None
    try:
        rating_pipeline = [
            {"$match": {"rating": {"$exists": True, "$gte": 1, "$lte": 5}}},
            {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}}
        ]
        rat_result = await db.feedback.aggregate(rating_pipeline).to_list(1)
        if rat_result and rat_result[0]["count"] >= 5:
            avg_rating = round(rat_result[0]["avg"], 1)
            rating_count = rat_result[0]["count"]
            satisfaction_pct = round((avg_rating / 5) * 100)
        elif rat_result:
            rating_count = rat_result[0]["count"]
    except Exception:
        pass

    return {
        "success": True,
        "period_days": days,
        "timestamp": _now().isoformat(),
        "total_users": total_users,
        "new_users_today": new_users_today,
        "new_users_period": new_users_period,
        "active_users_24h": active_24h,
        "active_sessions": active_sessions,
        "total_generations": total_generations,
        "completed_generations": completed_generations,
        "failed_generations": failed_generations,
        "success_rate": success_rate,
        "failure_rate": failure_rate,
        "total_revenue": total_revenue,
        "revenue_today": revenue_today,
        "avg_rating": avg_rating,
        "rating_count": rating_count,
        "satisfaction_pct": satisfaction_pct,
        "satisfaction_note": "Not enough ratings yet" if rating_count < 5 else None,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# GROWTH FUNNEL
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/funnel")
async def get_growth_funnel(days: int = Query(7, ge=1, le=90), admin: dict = Depends(get_admin_user)):
    """Growth funnel: page views → remix clicks → tool opens → generate → signup → complete → share."""
    cutoff = _ago(days=days)
    match = {"timestamp": {"$gte": cutoff.isoformat()}}

    async def count_events(event_name):
        return await db.growth_events.count_documents({**match, "event": event_name})

    page_views = await count_events("page_view")
    remix_clicks = await count_events("remix_click")
    tool_opens_prefilled = await count_events("tool_open_prefilled")
    generate_clicks = await count_events("generate_click")
    signup_completed = await count_events("signup_completed")
    creation_completed = await count_events("creation_completed")
    share_clicks = await count_events("share_click")

    # Funnel rates
    remix_rate = _safe_rate(remix_clicks, page_views)
    tool_open_rate = _safe_rate(tool_opens_prefilled, remix_clicks)
    generate_rate = _safe_rate(generate_clicks, tool_opens_prefilled or page_views)
    signup_rate = _safe_rate(signup_completed, generate_clicks)
    completion_rate = _safe_rate(creation_completed, generate_clicks or signup_completed)
    share_rate = _safe_rate(share_clicks, creation_completed)

    # Viral coefficient (K)
    unique_creators = 0
    try:
        cr_pipeline = [
            {"$match": {**match, "event": "share_click"}},
            {"$group": {"_id": "$user_id"}},
            {"$count": "total"}
        ]
        cr_result = await db.growth_events.aggregate(cr_pipeline).to_list(1)
        unique_creators = cr_result[0]["total"] if cr_result else 0
    except Exception:
        pass

    avg_shares = round(share_clicks / unique_creators, 2) if unique_creators else None
    new_from_shares = await count_events("signup_from_share")
    shared_link_visitors = await count_events("shared_link_visit")
    visitor_to_creator = _safe_rate(new_from_shares, shared_link_visitors)
    viral_k = round(avg_shares * (visitor_to_creator / 100), 3) if avg_shares and visitor_to_creator else None

    return {
        "success": True,
        "period_days": days,
        "timestamp": _now().isoformat(),
        "page_views": page_views,
        "remix_clicks": remix_clicks,
        "tool_opens_prefilled": tool_opens_prefilled,
        "generate_clicks": generate_clicks,
        "signup_completed": signup_completed,
        "creation_completed": creation_completed,
        "share_clicks": share_clicks,
        "remix_rate": remix_rate,
        "tool_open_rate": tool_open_rate,
        "generate_rate": generate_rate,
        "signup_rate": signup_rate,
        "completion_rate": completion_rate,
        "share_rate": share_rate,
        "viral_coefficient_k": viral_k,
        "avg_shares_per_creator": avg_shares,
        "unique_creators": unique_creators,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# RELIABILITY — Jobs, workers, health
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/reliability")
async def get_reliability_metrics(admin: dict = Depends(get_admin_user)):
    """Reliability: queue, workers, stuck jobs, failure rate, render times."""

    # Queue depth
    queue_depth = await db.pipeline_jobs.count_documents({
        "status": {"$in": ["queued", "QUEUED", "planning", "PLANNING", "generating", "GENERATING"]}
    })

    # Active/stuck jobs
    stuck_threshold = _ago(minutes=30)
    active_jobs = await db.pipeline_jobs.count_documents({
        "status": {"$in": ["queued", "QUEUED", "planning", "PLANNING", "generating", "GENERATING", "processing"]}
    })
    stuck_jobs = await db.pipeline_jobs.count_documents({
        "status": {"$in": ["queued", "QUEUED", "planning", "PLANNING", "generating", "GENERATING", "processing"]},
        "updated_at": {"$lte": stuck_threshold.isoformat()}
    })

    # Avg/Max render time (last 24h completed jobs)
    render_pipeline = [
        {"$match": {
            "status": "READY",
            "completed_at": {"$gte": _ago(hours=24).isoformat()},
            "started_at": {"$exists": True}
        }},
        {"$project": {
            "tool": "$tool_type",
            "duration_str_start": "$started_at",
            "duration_str_end": "$completed_at",
        }},
    ]
    render_jobs = await db.pipeline_jobs.aggregate(render_pipeline).to_list(100)

    # Compute durations
    tool_durations = {}
    all_durations = []
    for job in render_jobs:
        try:
            start = datetime.fromisoformat(str(job.get("duration_str_start", "")))
            end = datetime.fromisoformat(str(job.get("duration_str_end", "")))
            dur_s = (end - start).total_seconds()
            if dur_s > 0:
                tool = job.get("tool", "unknown")
                tool_durations.setdefault(tool, []).append(dur_s)
                all_durations.append(dur_s)
        except (ValueError, TypeError):
            pass

    avg_render = round(sum(all_durations) / len(all_durations), 1) if all_durations else None
    max_render = round(max(all_durations), 1) if all_durations else None

    tool_stats = {}
    for tool, durs in tool_durations.items():
        tool_stats[tool] = {
            "avg_seconds": round(sum(durs) / len(durs), 1),
            "max_seconds": round(max(durs), 1),
            "count": len(durs),
        }

    # Deep health - check core services
    health_checks = {}
    try:
        await db.users.find_one({}, {"_id": 1})
        health_checks["database"] = "healthy"
    except Exception:
        health_checks["database"] = "critical"

    health_checks["queue"] = "healthy" if queue_depth < 50 else ("degraded" if queue_depth < 200 else "critical")
    health_checks["stuck_jobs"] = "healthy" if stuck_jobs == 0 else ("degraded" if stuck_jobs < 5 else "critical")

    overall = "healthy"
    if any(v == "critical" for v in health_checks.values()):
        overall = "critical"
    elif any(v == "degraded" for v in health_checks.values()):
        overall = "degraded"

    return {
        "success": True,
        "timestamp": _now().isoformat(),
        "queue_depth": queue_depth,
        "active_jobs": active_jobs,
        "stuck_jobs": stuck_jobs,
        "avg_render_seconds": avg_render,
        "max_render_seconds": max_render,
        "tool_render_stats": tool_stats,
        "health_checks": health_checks,
        "overall_health": overall,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# REVENUE — Cashfree truth (single source of truth)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/revenue")
async def get_revenue_metrics(days: int = Query(30, ge=1, le=365), admin: dict = Depends(get_admin_user)):
    """Revenue: total from Cashfree, successful/failed payments, today's revenue."""
    today_start = _today_start()

    # Successful payments (PAID orders from Cashfree)
    paid_orders = await db.orders.find(
        {"status": "PAID", "gateway": "cashfree"},
        {"_id": 0, "amount": 1, "currency": 1, "credits": 1, "paidAt": 1, "productId": 1, "userId": 1}
    ).to_list(10000)

    total_revenue_inr = sum(o.get("amount", 0) for o in paid_orders if o.get("currency") == "INR")
    total_revenue_usd = sum(o.get("amount", 0) for o in paid_orders if o.get("currency") == "USD")
    total_credits_sold = sum(o.get("credits", 0) for o in paid_orders)
    successful_payments = len(paid_orders)

    # Today's revenue
    today_orders = [o for o in paid_orders if o.get("paidAt", "") >= today_start.isoformat()]
    revenue_today_inr = sum(o.get("amount", 0) for o in today_orders if o.get("currency") == "INR")

    # Failed payments
    failed_payments = await db.orders.count_documents({"status": "FAILED", "gateway": "cashfree"})

    # Pending payments
    pending_payments = await db.orders.count_documents({"status": {"$in": ["ACTIVE", "PROCESSING"]}, "gateway": "cashfree"})

    # Payment success rate
    total_attempts = successful_payments + failed_payments
    success_rate = _safe_rate(successful_payments, total_attempts)

    # Paying users
    paying_user_ids = set(o.get("userId") for o in paid_orders if o.get("userId"))
    paying_users = len(paying_user_ids)

    total_users = await db.users.count_documents({"role": {"$ne": "deleted"}})
    arpu = round(total_revenue_inr / paying_users, 2) if paying_users else None
    conversion_rate = _safe_rate(paying_users, total_users)

    # Recent payments (last 10)
    recent = await db.orders.find(
        {"gateway": "cashfree", "status": "PAID"},
        {"_id": 0, "order_id": 1, "amount": 1, "currency": 1, "credits": 1, "productId": 1, "paidAt": 1}
    ).sort("paidAt", -1).limit(10).to_list(10)

    return {
        "success": True,
        "period_days": days,
        "timestamp": _now().isoformat(),
        "total_revenue_inr": total_revenue_inr,
        "total_revenue_usd": total_revenue_usd,
        "total_credits_sold": total_credits_sold,
        "successful_payments": successful_payments,
        "failed_payments": failed_payments,
        "pending_payments": pending_payments,
        "payment_success_rate": success_rate,
        "revenue_today_inr": revenue_today_inr,
        "today_payments": len(today_orders),
        "paying_users": paying_users,
        "total_users": total_users,
        "arpu": arpu,
        "conversion_rate": conversion_rate,
        "recent_payments": recent,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# STORY & CHARACTER INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/series")
async def get_series_metrics(admin: dict = Depends(get_admin_user)):
    """Story series & character intelligence metrics."""

    # Active series
    active_series = await db.story_series.count_documents({"status": "active"})
    total_series = await db.story_series.count_documents({})

    # Episodes
    total_episodes = await db.story_episodes.count_documents({})

    # Avg episodes per series
    avg_episodes = round(total_episodes / total_series, 1) if total_series else None

    # Series with 2+ episodes (continuation rate)
    continuation_pipeline = [
        {"$group": {"_id": "$series_id", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gte": 2}}},
        {"$count": "total"}
    ]
    cont_result = await db.story_episodes.aggregate(continuation_pipeline).to_list(1)
    series_with_continuation = cont_result[0]["total"] if cont_result else 0
    continuation_rate = _safe_rate(series_with_continuation, total_series)

    # Characters
    total_characters = await db.character_profiles.count_documents({"status": "active"})
    auto_extracted = await db.character_profiles.count_documents({"auto_extracted": True})

    # Character reuse (characters in 2+ episodes)
    reuse_pipeline = [
        {"$group": {"_id": "$character_id", "episodes": {"$sum": 1}}},
        {"$match": {"episodes": {"$gte": 2}}},
        {"$count": "total"}
    ]
    reuse_result = await db.character_memory_logs.aggregate(reuse_pipeline).to_list(1)
    reused_characters = reuse_result[0]["total"] if reuse_result else 0
    reuse_rate = _safe_rate(reused_characters, total_characters)

    # Continuity validations
    total_validations = await db.continuity_validations.count_documents({})
    passed_validations = await db.continuity_validations.count_documents({"passed": True})
    continuity_pass_rate = _safe_rate(passed_validations, total_validations)

    # Most reused character
    top_char_pipeline = [
        {"$group": {"_id": "$character_id", "usage": {"$sum": 1}}},
        {"$sort": {"usage": -1}},
        {"$limit": 1}
    ]
    top_char_result = await db.character_memory_logs.aggregate(top_char_pipeline).to_list(1)
    most_reused = None
    if top_char_result:
        char_id = top_char_result[0]["_id"]
        char_doc = await db.character_profiles.find_one(
            {"character_id": char_id}, {"_id": 0, "name": 1, "character_id": 1}
        )
        if char_doc:
            most_reused = {"name": char_doc.get("name"), "character_id": char_id, "usage": top_char_result[0]["usage"]}

    # Rewards claimed
    rewards_claimed = await db.series_rewards.count_documents({})

    return {
        "success": True,
        "timestamp": _now().isoformat(),
        "active_series": active_series,
        "total_series": total_series,
        "total_episodes": total_episodes,
        "avg_episodes_per_series": avg_episodes,
        "continuation_rate": continuation_rate,
        "total_characters": total_characters,
        "auto_extracted_characters": auto_extracted,
        "reused_characters": reused_characters,
        "character_reuse_rate": reuse_rate,
        "continuity_pass_rate": continuity_pass_rate,
        "most_reused_character": most_reused,
        "rewards_claimed": rewards_claimed,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MODERATION & SAFETY
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/safety")
async def get_safety_metrics(admin: dict = Depends(get_admin_user)):
    """Moderation, abuse, and safety metrics."""

    blocked_prompts = await db.blocked_requests.count_documents({})
    flagged_requests = await db.flagged_requests.count_documents({})
    consent_characters = await db.character_safety_profiles.count_documents({"is_user_uploaded_likeness": True})
    ip_rejections = await db.blocked_requests.count_documents({"reason": {"$regex": "copyright|ip_risk", "$options": "i"}})

    total_requests = await db.pipeline_jobs.count_documents({})
    safety_flag_rate = _safe_rate(flagged_requests, total_requests)

    return {
        "success": True,
        "timestamp": _now().isoformat(),
        "blocked_prompts": blocked_prompts,
        "flagged_requests": flagged_requests,
        "safety_flag_rate": safety_flag_rate,
        "consent_required_characters": consent_characters,
        "ip_risk_rejections": ip_rejections,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CREDIT METRICS — Usage truth
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/credits")
async def get_credit_metrics(admin: dict = Depends(get_admin_user)):
    """Credits: issued, consumed, avg per user, top users."""

    # All users' credit data
    users_pipeline = [
        {"$match": {"role": {"$ne": "deleted"}}},
        {"$group": {
            "_id": None,
            "total_current_credits": {"$sum": {"$ifNull": ["$credits", 0]}},
            "user_count": {"$sum": 1},
        }}
    ]
    agg = await db.users.aggregate(users_pipeline).to_list(1)
    stats = agg[0] if agg else {"total_current_credits": 0, "user_count": 0}

    # Credits consumed (from credit_transactions — negative amounts)
    consumed_pipeline = [
        {"$unwind": "$credit_transactions"},
        {"$match": {"credit_transactions.amount": {"$lt": 0}}},
        {"$group": {"_id": None, "total_consumed": {"$sum": {"$abs": "$credit_transactions.amount"}}}}
    ]
    consumed_agg = await db.users.aggregate(consumed_pipeline).to_list(1)
    total_consumed = consumed_agg[0]["total_consumed"] if consumed_agg else 0

    # Credits issued (from credit_transactions — positive amounts)
    issued_pipeline = [
        {"$unwind": "$credit_transactions"},
        {"$match": {"credit_transactions.amount": {"$gt": 0}}},
        {"$group": {"_id": None, "total_issued": {"$sum": "$credit_transactions.amount"}}}
    ]
    issued_agg = await db.users.aggregate(issued_pipeline).to_list(1)
    total_issued = issued_agg[0]["total_issued"] if issued_agg else 0

    avg_credits = round(stats["total_current_credits"] / max(stats["user_count"], 1), 1)

    # Top users by usage (most credits consumed)
    top_users_pipeline = [
        {"$match": {"role": {"$ne": "deleted"}, "credit_transactions": {"$exists": True}}},
        {"$project": {
            "_id": 0, "id": 1, "email": 1, "name": 1, "credits": 1,
            "total_spent": {
                "$reduce": {
                    "input": {"$filter": {"input": {"$ifNull": ["$credit_transactions", []]}, "cond": {"$lt": ["$$this.amount", 0]}}},
                    "initialValue": 0,
                    "in": {"$add": ["$$value", {"$abs": "$$this.amount"}]}
                }
            }
        }},
        {"$sort": {"total_spent": -1}},
        {"$limit": 10}
    ]
    top_users = await db.users.aggregate(top_users_pipeline).to_list(10)

    return {
        "success": True,
        "timestamp": _now().isoformat(),
        "total_credits_issued": total_issued,
        "total_credits_consumed": total_consumed,
        "total_current_balance": stats["total_current_credits"],
        "avg_credits_per_user": avg_credits,
        "total_users": stats["user_count"],
        "top_users_by_usage": top_users,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CONVERSION METRICS — Free → Paid
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/conversion")
async def get_conversion_metrics(admin: dict = Depends(get_admin_user)):
    """Conversion: free→paid rate, top-up purchase rate."""

    total_users = await db.users.count_documents({"role": {"$ne": "deleted"}})

    # Users who made at least 1 payment
    paying_users = await db.orders.distinct("userId", {"status": "PAID", "gateway": "cashfree"})
    paying_count = len(paying_users)

    free_to_paid_rate = _safe_rate(paying_count, total_users)

    # Top-up purchase rate (users who bought top-ups)
    topup_users = await db.orders.distinct("userId", {"status": "PAID", "gateway": "cashfree", "productId": {"$regex": "^topup_"}})
    topup_rate = _safe_rate(len(topup_users), total_users)

    # Subscription purchase rate
    sub_users = await db.orders.distinct("userId", {"status": "PAID", "gateway": "cashfree", "productId": {"$regex": "_monthly$"}})
    sub_rate = _safe_rate(len(sub_users), total_users)

    # Repeat purchasers
    repeat_pipeline = [
        {"$match": {"status": "PAID", "gateway": "cashfree"}},
        {"$group": {"_id": "$userId", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}},
        {"$count": "repeat_buyers"}
    ]
    repeat_agg = await db.orders.aggregate(repeat_pipeline).to_list(1)
    repeat_buyers = repeat_agg[0]["repeat_buyers"] if repeat_agg else 0

    return {
        "success": True,
        "timestamp": _now().isoformat(),
        "total_users": total_users,
        "paying_users": paying_count,
        "free_to_paid_rate": free_to_paid_rate,
        "topup_purchase_rate": topup_rate,
        "subscription_rate": sub_rate,
        "repeat_buyers": repeat_buyers,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CREDIT RESET — Admin action
# ═══════════════════════════════════════════════════════════════════════════════

from pydantic import BaseModel as _BaseModel

class CreditResetRequest(_BaseModel):
    credits: int = 50
    dry_run: bool = False

@router.post("/credit-reset")
async def reset_credits(request: CreditResetRequest, admin: dict = Depends(get_admin_user)):
    """Reset credits to N for all normal users. Excludes admin/test/uat/dev roles."""

    excluded_roles = ["admin", "test", "uat", "dev", "demo", "ADMIN", "TEST", "UAT", "DEV", "DEMO", "Admin", "Test", "Demo"]

    # Build filter: exclude admin/test/uat/dev/demo (case-insensitive)
    filter_query = {
        "role": {"$nin": excluded_roles},
        "email": {"$not": {"$regex": "^(admin@|test@|uat@|dev@|demo@)", "$options": "i"}}
    }

    # Count affected users
    affected_count = await db.users.count_documents(filter_query)

    if request.dry_run:
        return {
            "success": True,
            "dry_run": True,
            "affected_users": affected_count,
            "new_credits": request.credits,
        }

    # Execute reset
    result = await db.users.update_many(
        filter_query,
        {
            "$set": {"credits": request.credits, "show_credit_banner": True},
            "$push": {
                "credit_transactions": {
                    "amount": request.credits,
                    "description": f"Credit reset to {request.credits} by admin",
                    "timestamp": _now(),
                    "type": "ADMIN_RESET"
                }
            }
        }
    )

    # Audit log
    await db.audit_logs.insert_one({
        "action": "credit_reset",
        "admin_id": admin.get("id"),
        "admin_email": admin.get("email"),
        "affected_users": result.modified_count,
        "new_credits": request.credits,
        "excluded_roles": excluded_roles,
        "timestamp": _now().isoformat(),
    })

    logger.info(f"Credit reset executed: {result.modified_count} users reset to {request.credits} credits by {admin.get('email')}")

    return {
        "success": True,
        "affected_users": result.modified_count,
        "new_credits": request.credits,
        "message": f"Reset {result.modified_count} users to {request.credits} credits. Excluded: admin/test/uat/dev."
    }



# ═══════════════════════════════════════════════════════════════════════════════
# STORY CHAIN LEADERBOARD
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/leaderboard")
async def get_leaderboard(admin: dict = Depends(get_admin_user)):
    """Story chain leaderboard: top continued stories and top continuers."""

    # Top continued stories (by remix_count)
    top_stories_pipeline = [
        {"$match": {"status": "COMPLETED", "remix_count": {"$gt": 0}}},
        {"$sort": {"remix_count": -1}},
        {"$limit": 10},
        {"$project": {
            "_id": 0,
            "job_id": 1,
            "title": 1,
            "user_id": 1,
            "continuations": {"$ifNull": ["$remix_count", 0]},
            "views": {"$ifNull": ["$views", 0]},
            "created_at": 1,
        }}
    ]
    top_stories_raw = await db.pipeline_jobs.aggregate(top_stories_pipeline).to_list(10)

    # Enrich with creator names
    top_stories = []
    for story in top_stories_raw:
        creator_name = "Anonymous"
        if story.get("user_id"):
            user = await db.users.find_one({"id": story["user_id"]}, {"_id": 0, "name": 1})
            if user:
                creator_name = user.get("name", "Anonymous")
        top_stories.append({
            "job_id": story.get("job_id"),
            "title": story.get("title", "Untitled"),
            "creator_name": creator_name,
            "continuations": story.get("continuations", 0),
            "views": story.get("views", 0),
        })

    # Top continuers (users who made the most remixes)
    top_continuers_pipeline = [
        {"$match": {"remix_parent_id": {"$exists": True, "$ne": None}}},
        {"$group": {"_id": "$user_id", "continuation_count": {"$sum": 1}}},
        {"$sort": {"continuation_count": -1}},
        {"$limit": 10},
    ]
    top_continuers_raw = await db.pipeline_jobs.aggregate(top_continuers_pipeline).to_list(10)

    top_continuers = []
    for entry in top_continuers_raw:
        uid = entry.get("_id")
        name = "Anonymous"
        if uid:
            user = await db.users.find_one({"id": uid}, {"_id": 0, "name": 1})
            if user:
                name = user.get("name", "Anonymous")
        top_continuers.append({
            "user_id": uid,
            "name": name,
            "continuation_count": entry.get("continuation_count", 0),
        })

    # Overall stats
    total_continuations = await db.pipeline_jobs.count_documents({"remix_parent_id": {"$exists": True, "$ne": None}})

    unique_continuers_pipeline = [
        {"$match": {"remix_parent_id": {"$exists": True, "$ne": None}}},
        {"$group": {"_id": "$user_id"}},
        {"$count": "total"},
    ]
    uc_result = await db.pipeline_jobs.aggregate(unique_continuers_pipeline).to_list(1)
    unique_continuers = uc_result[0]["total"] if uc_result else 0

    stories_with_cont = await db.pipeline_jobs.count_documents({"remix_count": {"$gt": 0}})

    # Avg chain length
    avg_chain_pipeline = [
        {"$match": {"remix_count": {"$gt": 0}}},
        {"$group": {"_id": None, "avg": {"$avg": "$remix_count"}}},
    ]
    avg_result = await db.pipeline_jobs.aggregate(avg_chain_pipeline).to_list(1)
    avg_chain_length = round(avg_result[0]["avg"], 1) if avg_result else None

    return {
        "success": True,
        "timestamp": _now().isoformat(),
        "top_stories": top_stories,
        "top_continuers": top_continuers,
        "total_continuations": total_continuations,
        "unique_continuers": unique_continuers,
        "stories_with_continuations": stories_with_cont,
        "avg_chain_length": avg_chain_length,
    }



@router.get("/share-rewards")
async def admin_share_rewards(user: dict = Depends(get_admin_user)):
    """Share reward metrics for admin dashboard."""
    now = _now()
    seven_days_ago = (now - timedelta(days=7)).isoformat()

    total_share_rewards = await db.share_rewards.count_documents({"credits_awarded": 5})
    total_cont_rewards = await db.share_rewards.count_documents({"type": "continuation_reward"})
    total_signup_rewards = await db.share_rewards.count_documents({"type": "signup_referral"})
    total_credits = (total_share_rewards * 5) + (total_cont_rewards * 15) + (total_signup_rewards * 25)

    # 7-day window
    share_7d = await db.share_rewards.count_documents({"credits_awarded": 5, "timestamp": {"$gte": seven_days_ago}})
    cont_7d = await db.share_rewards.count_documents({"type": "continuation_reward", "timestamp": {"$gte": seven_days_ago}})
    signup_7d = await db.share_rewards.count_documents({"type": "signup_referral", "timestamp": {"$gte": seven_days_ago}})

    # Unique sharers
    pipeline = [{"$match": {"credits_awarded": 5}}, {"$group": {"_id": "$user_id"}}, {"$count": "total"}]
    unique_res = await db.share_rewards.aggregate(pipeline).to_list(1)
    unique_sharers = unique_res[0]["total"] if unique_res else 0

    return {
        "total_share_rewards": total_share_rewards,
        "total_continuation_rewards": total_cont_rewards,
        "total_signup_rewards": total_signup_rewards,
        "total_credits_given": total_credits,
        "unique_sharers": unique_sharers,
        "last_7_days": {
            "shares": share_7d,
            "continuations": cont_7d,
            "signups": signup_7d,
        },
    }



# ═══════════════════════════════════════════════════════════════════════════════
# PHOTO TO COMIC HEALTH — P1.5-D Observability
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/comic-health")
async def get_comic_health(days: int = Query(7, ge=1, le=90), admin: dict = Depends(get_admin_user)):
    """
    Photo to Comic production health metrics.
    Computed from real data: photo_to_comic_jobs, consistency_logs, quality_cache, comic_events.
    """
    cutoff = _ago(days=days).isoformat()

    # ── Job Success Rate ──
    total_jobs = await db.photo_to_comic_jobs.count_documents({"createdAt": {"$gte": cutoff}})
    completed = await db.photo_to_comic_jobs.count_documents({"createdAt": {"$gte": cutoff}, "status": {"$in": ["COMPLETED", "READY_WITH_WARNINGS"]}})
    partial = await db.photo_to_comic_jobs.count_documents({"createdAt": {"$gte": cutoff}, "status": "PARTIAL_READY"})
    failed = await db.photo_to_comic_jobs.count_documents({"createdAt": {"$gte": cutoff}, "status": "FAILED"})
    success_rate = _safe_rate(completed + partial, total_jobs)
    full_failure_rate = _safe_rate(failed, total_jobs)

    # ── Fallback & Retry Rates ──
    fallback_jobs = await db.photo_to_comic_jobs.count_documents({"createdAt": {"$gte": cutoff}, "has_fallback": True})
    retry_jobs = await db.photo_to_comic_jobs.count_documents({"createdAt": {"$gte": cutoff}, "has_retries": True})
    fallback_trigger_rate = _safe_rate(fallback_jobs, total_jobs)

    # Panel-level retry rate via aggregation
    retry_pipeline = [
        {"$match": {"createdAt": {"$gte": cutoff}, "panels": {"$exists": True}}},
        {"$project": {
            "total_panels": {"$size": {"$ifNull": ["$panels", []]}},
            "retried_panels": {"$size": {"$filter": {"input": {"$ifNull": ["$panels", []]}, "as": "p", "cond": {"$gt": [{"$ifNull": ["$$p.retries", 0]}, 0]}}}},
            "fallback_panels": {"$size": {"$filter": {"input": {"$ifNull": ["$panels", []]}, "as": "p", "cond": {"$eq": [{"$ifNull": ["$$p.fallback", False]}, True]}}}},
        }},
        {"$group": {"_id": None, "total_p": {"$sum": "$total_panels"}, "retried_p": {"$sum": "$retried_panels"}, "fallback_p": {"$sum": "$fallback_panels"}}}
    ]
    panel_stats = await db.photo_to_comic_jobs.aggregate(retry_pipeline).to_list(1)
    total_panels_all = panel_stats[0]["total_p"] if panel_stats else 0
    retried_panels_all = panel_stats[0]["retried_p"] if panel_stats else 0
    fallback_panels_all = panel_stats[0]["fallback_p"] if panel_stats else 0
    panel_retry_rate = _safe_rate(retried_panels_all, total_panels_all)

    # ── Job Quality Distribution ──
    quality_pipeline = [
        {"$match": {"createdAt": {"$gte": cutoff}, "job_quality": {"$exists": True}}},
        {"$group": {"_id": "$job_quality", "count": {"$sum": 1}}}
    ]
    quality_res = await db.photo_to_comic_jobs.aggregate(quality_pipeline).to_list(10)
    quality_dist = {r["_id"]: r["count"] for r in quality_res if r["_id"]}

    # ── Style Failure Rate ──
    style_pipeline = [
        {"$match": {"createdAt": {"$gte": cutoff}, "style": {"$exists": True}}},
        {"$group": {
            "_id": "$style",
            "total": {"$sum": 1},
            "failed": {"$sum": {"$cond": [{"$eq": ["$status", "FAILED"]}, 1, 0]}},
            "completed": {"$sum": {"$cond": [{"$in": ["$status", ["COMPLETED", "READY_WITH_WARNINGS"]]}, 1, 0]}},
            "with_fallback": {"$sum": {"$cond": [{"$eq": [{"$ifNull": ["$has_fallback", False]}, True]}, 1, 0]}},
        }}
    ]
    style_res = await db.photo_to_comic_jobs.aggregate(style_pipeline).to_list(20)
    style_breakdown = {}
    for s in style_res:
        sid = s["_id"] or "unknown"
        style_breakdown[sid] = {
            "total": s["total"],
            "failed": s["failed"],
            "completed": s["completed"],
            "with_fallback": s["with_fallback"],
            "failure_rate": _safe_rate(s["failed"], s["total"]),
        }

    # ── Average Generation Time ──
    time_jobs = await db.photo_to_comic_jobs.find(
        {"createdAt": {"$gte": cutoff}, "status": {"$in": ["COMPLETED", "READY_WITH_WARNINGS", "PARTIAL_READY"]}, "updatedAt": {"$exists": True}},
        {"_id": 0, "createdAt": 1, "updatedAt": 1, "stage_timing": 1}
    ).limit(100).to_list(100)

    avg_time = None
    if time_jobs:
        durations = []
        for j in time_jobs:
            # Prefer stage_timing.total_seconds if available
            st = j.get("stage_timing", {})
            if isinstance(st, dict) and st.get("total_seconds"):
                durations.append(st["total_seconds"])
            else:
                try:
                    start = datetime.fromisoformat(j["createdAt"].replace("Z", "+00:00")) if isinstance(j["createdAt"], str) else j["createdAt"]
                    end = datetime.fromisoformat(j["updatedAt"].replace("Z", "+00:00")) if isinstance(j["updatedAt"], str) else j["updatedAt"]
                    d = (end - start).total_seconds()
                    if 0 < d < 600:
                        durations.append(d)
                except Exception:
                    pass
        if durations:
            avg_time = round(sum(durations) / len(durations), 1)

    # ── Consistency Drift ──
    consistency_logs = await db.consistency_logs.find(
        {"created_at": {"$gte": cutoff}},
        {"_id": 0, "avg_similarity": 1, "retry_needed": 1, "no_face_panels": 1, "accepted": 1, "borderline": 1, "total_panels": 1, "style": 1, "source_face_detected": 1}
    ).limit(200).to_list(200)

    avg_similarity = None
    consistency_retry_rate = None
    no_face_panel_rate = None
    no_face_source_rate = None
    drift_by_style = {}

    if consistency_logs:
        sims = [entry["avg_similarity"] for entry in consistency_logs if entry.get("avg_similarity", 0) > 0]
        if sims:
            avg_similarity = round(sum(sims) / len(sims), 4)

        total_panels_checked = sum(entry.get("total_panels", 0) for entry in consistency_logs)
        total_retries = sum(entry.get("retry_needed", 0) for entry in consistency_logs)
        total_no_face = sum(entry.get("no_face_panels", 0) for entry in consistency_logs)
        total_source_no_face = sum(1 for entry in consistency_logs if not entry.get("source_face_detected", True))

        consistency_retry_rate = _safe_rate(total_retries, total_panels_checked)
        no_face_panel_rate = _safe_rate(total_no_face, total_panels_checked)
        no_face_source_rate = _safe_rate(total_source_no_face, len(consistency_logs))
        for entry in consistency_logs:
            s = entry.get("style", "unknown")
            if s not in drift_by_style:
                drift_by_style[s] = {"count": 0, "total_sim": 0, "retries": 0, "no_face": 0}
            drift_by_style[s]["count"] += 1
            drift_by_style[s]["total_sim"] += entry.get("avg_similarity", 0)
            drift_by_style[s]["retries"] += entry.get("retry_needed", 0)
            drift_by_style[s]["no_face"] += entry.get("no_face_panels", 0)

        for s in drift_by_style:
            c = drift_by_style[s]["count"]
            drift_by_style[s]["avg_similarity"] = round(drift_by_style[s]["total_sim"] / c, 4) if c else 0
            del drift_by_style[s]["total_sim"]

    # ── Quality Check Stats ──
    quality_total = await db.quality_cache.count_documents({})
    quality_agg = [
        {"$group": {"_id": "$result.overall", "count": {"$sum": 1}}}
    ]
    quality_qres = await db.quality_cache.aggregate(quality_agg).to_list(10)
    quality_breakdown = {r["_id"]: r["count"] for r in quality_qres if r["_id"]}

    # ── PDF Export Stats ──
    pdf_downloads = await db.comic_events.count_documents({"event_type": "pdf_download_click", "created_at": {"$gte": cutoff}})
    pdf_success = await db.comic_events.count_documents({"event_type": "pdf_download_success", "created_at": {"$gte": cutoff}})
    pdf_fail = await db.comic_events.count_documents({"event_type": "pdf_download_fail", "created_at": {"$gte": cutoff}})
    pdf_success_rate = _safe_rate(pdf_success, pdf_downloads) if pdf_downloads else None

    # ── Event Counts ──
    style_clicks = await db.comic_events.count_documents({"event_type": "preview_strip_style_click", "created_at": {"$gte": cutoff}})
    generate_after_preview = await db.comic_events.count_documents({"event_type": "generate_after_preview", "created_at": {"$gte": cutoff}})
    result_views = await db.comic_events.count_documents({"event_type": "result_page_view", "created_at": {"$gte": cutoff}})
    png_downloads = await db.comic_events.count_documents({"event_type": "png_download_click", "created_at": {"$gte": cutoff}})
    script_downloads = await db.comic_events.count_documents({"event_type": "script_download_click", "created_at": {"$gte": cutoff}})

    # ── Alerts ──
    alerts = []
    if success_rate is not None and success_rate < 80:
        alerts.append({"level": "critical", "message": f"Job success rate is {success_rate}% (below 80% threshold)"})
    if fallback_trigger_rate is not None and fallback_trigger_rate > 25:
        alerts.append({"level": "warning", "message": f"Fallback trigger rate is {fallback_trigger_rate}% (above 25% threshold)"})
    if panel_retry_rate is not None and panel_retry_rate > 30:
        alerts.append({"level": "warning", "message": f"Panel retry rate is {panel_retry_rate}% (above 30% threshold)"})
    if avg_time is not None and avg_time > 120:
        alerts.append({"level": "warning", "message": f"Average generation time is {avg_time}s (above 120s threshold)"})
    if full_failure_rate is not None and full_failure_rate > 15:
        alerts.append({"level": "critical", "message": f"Full failure rate is {full_failure_rate}% (above 15% threshold)"})

    # ── Smart Repair Metrics (from comic_panel_attempts) ──
    smart_repair_metrics = None
    attempt_docs = await db.comic_panel_attempts.find(
        {"created_at": {"$gte": cutoff}},
        {"_id": 0, "stage": 1, "accepted": 1, "diagnostics": 1,
         "result.latency_ms": 1, "input_context.model_tier": 1}
    ).limit(1000).to_list(1000)

    if attempt_docs:
        primary_attempts = [a for a in attempt_docs if a.get("stage") == "PRIMARY"]
        repair_attempts = [a for a in attempt_docs if "REPAIR" in (a.get("stage") or "")]
        fallback_attempts = [a for a in attempt_docs if a.get("stage") == "FALLBACK"]

        primary_pass = sum(1 for a in primary_attempts if a.get("accepted"))
        repair_pass = sum(1 for a in repair_attempts if a.get("accepted"))
        fallback_pass = sum(1 for a in fallback_attempts if a.get("accepted"))

        # Failure type frequency
        failure_freq = {}
        for a in attempt_docs:
            for ft in a.get("diagnostics", {}).get("failure_types_in", []):
                failure_freq[ft] = failure_freq.get(ft, 0) + 1

        # Risk bucket breakdown from routing_summary in jobs
        risk_pipeline = [
            {"$match": {"createdAt": {"$gte": cutoff}, "input_risk_bucket": {"$exists": True}}},
            {"$group": {
                "_id": "$input_risk_bucket",
                "count": {"$sum": 1},
                "avg_pqs": {"$avg": "$validation_quality.perceived_quality_score"},
            }}
        ]
        risk_breakdown = {}
        try:
            risk_docs = await db.photo_to_comic_jobs.aggregate(risk_pipeline).to_list(10)
            for r in risk_docs:
                risk_breakdown[r["_id"]] = {
                    "jobs": r["count"],
                    "avg_pqs": round(r["avg_pqs"], 1) if r.get("avg_pqs") else None,
                }
        except Exception:
            pass

        smart_repair_metrics = {
            "total_attempts": len(attempt_docs),
            "primary": {"attempts": len(primary_attempts), "accepted": primary_pass,
                       "pass_rate": _safe_rate(primary_pass, len(primary_attempts))},
            "repair": {"attempts": len(repair_attempts), "accepted": repair_pass,
                      "pass_rate": _safe_rate(repair_pass, len(repair_attempts))},
            "fallback": {"attempts": len(fallback_attempts), "accepted": fallback_pass,
                        "pass_rate": _safe_rate(fallback_pass, len(fallback_attempts))},
            "failure_type_frequency": dict(sorted(failure_freq.items(), key=lambda x: x[1], reverse=True)),
            "risk_bucket_breakdown": risk_breakdown,
        }

        # Smart repair specific alerts
        if primary_attempts and _safe_rate(primary_pass, len(primary_attempts)) < 60:
            alerts.append({"level": "warning",
                          "message": f"Primary pass rate is {_safe_rate(primary_pass, len(primary_attempts))}% (below 60%)"})
        if repair_attempts and _safe_rate(repair_pass, len(repair_attempts)) < 50:
            alerts.append({"level": "warning",
                          "message": f"Repair success rate is {_safe_rate(repair_pass, len(repair_attempts))}% (below 50%)"})

    # ── Validation Quality Aggregates (5 Dimensions) ──
    vq_pipeline = [
        {"$match": {"createdAt": {"$gte": cutoff}, "validation_quality": {"$exists": True}}},
        {"$project": {
            "pqs": "$validation_quality.perceived_quality_score",
            "nc": "$validation_quality.narrative_coherence.score",
            "sc": "$validation_quality.style_consistency_score",
            "flp": "$validation_quality.fallback_latency_penalty_ms",
            "uis_pass": "$validation_quality.ui_emotional_safety.passed",
        }}
    ]
    vq_jobs = await db.photo_to_comic_jobs.aggregate(vq_pipeline).to_list(500)

    validation_quality_agg = None
    if vq_jobs:
        pqs_vals = [j["pqs"] for j in vq_jobs if j.get("pqs") is not None]
        nc_vals = [j["nc"] for j in vq_jobs if j.get("nc") is not None]
        sc_vals = [j["sc"] for j in vq_jobs if j.get("sc") is not None and j["sc"] is not None]
        flp_vals = [j["flp"] for j in vq_jobs if j.get("flp") is not None and j["flp"] != 0]
        uis_vals = [j["uis_pass"] for j in vq_jobs if j.get("uis_pass") is not None]

        validation_quality_agg = {
            "jobs_with_scores": len(vq_jobs),
            "perceived_quality": {
                "avg": round(sum(pqs_vals) / len(pqs_vals), 2) if pqs_vals else None,
                "min": min(pqs_vals) if pqs_vals else None,
                "max": max(pqs_vals) if pqs_vals else None,
                "distribution": {str(i): pqs_vals.count(i) for i in range(1, 6)},
            },
            "narrative_coherence": {
                "avg": round(sum(nc_vals) / len(nc_vals), 2) if nc_vals else None,
            },
            "style_consistency": {
                "avg": round(sum(sc_vals) / len(sc_vals), 4) if sc_vals else None,
            },
            "fallback_latency": {
                "avg_penalty_ms": round(sum(flp_vals) / len(flp_vals)) if flp_vals else None,
                "max_penalty_ms": max(flp_vals) if flp_vals else None,
            },
            "ui_emotional_safety": {
                "pass_rate": _safe_rate(sum(1 for v in uis_vals if v), len(uis_vals)),
                "violations": sum(1 for v in uis_vals if not v),
            },
        }

        # Add validation quality alerts
        if pqs_vals and (sum(pqs_vals) / len(pqs_vals)) < 3:
            alerts.append({"level": "warning", "message": f"Average perceived quality score is {sum(pqs_vals)/len(pqs_vals):.1f}/5 (below 3.0 threshold)"})
        if flp_vals and (sum(flp_vals) / len(flp_vals)) > 15000:
            alerts.append({"level": "warning", "message": f"Average fallback latency penalty is {sum(flp_vals)/len(flp_vals):.0f}ms (above 15s threshold)"})

    # ── Recent Fallback Validations ──
    recent_validations = await db.fallback_validations.find(
        {"status": "COMPLETED"},
        {"_id": 0, "validation_id": 1, "mode": 1, "overall_verdict": 1, "started_at": 1,
         "validation_quality": 1,
         "summary": 1, "repair_triggered": 1, "fallback_triggered": 1}
    ).sort("started_at", -1).limit(5).to_list(5)
    return {
        "period_days": days,
        "jobs": {
            "total": total_jobs,
            "completed": completed,
            "partial": partial,
            "failed": failed,
            "success_rate": success_rate,
            "full_failure_rate": full_failure_rate,
        },
        "reliability": {
            "fallback_trigger_rate": fallback_trigger_rate,
            "fallback_jobs": fallback_jobs,
            "retry_jobs": retry_jobs,
            "panel_retry_rate": panel_retry_rate,
            "retried_panels": retried_panels_all,
            "fallback_panels": fallback_panels_all,
            "total_panels": total_panels_all,
        },
        "job_quality": quality_dist,
        "style_breakdown": style_breakdown,
        "performance": {
            "avg_generation_time_seconds": avg_time,
        },
        "consistency": {
            "avg_similarity": avg_similarity,
            "consistency_retry_rate": consistency_retry_rate,
            "no_face_panel_rate": no_face_panel_rate,
            "no_face_source_rate": no_face_source_rate,
            "drift_by_style": drift_by_style,
        },
        "validation_quality": validation_quality_agg,
        "smart_repair": smart_repair_metrics,
        "recent_validations": recent_validations,
        "quality_check": {
            "total_checks": quality_total,
            "breakdown": quality_breakdown,
        },
        "downloads": {
            "pdf_attempts": pdf_downloads,
            "pdf_success": pdf_success,
            "pdf_fail": pdf_fail,
            "pdf_success_rate": pdf_success_rate,
            "png_downloads": png_downloads,
            "script_downloads": script_downloads,
        },
        "conversion": {
            "style_clicks": style_clicks,
            "generate_after_preview": generate_after_preview,
            "result_views": result_views,
        },
        "alerts": alerts,
        "empty_state": total_jobs == 0,
        "empty_message": "No Photo to Comic jobs in this period" if total_jobs == 0 else None,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SAFETY PIPELINE DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/safety-overview")
async def safety_overview(
    hours: int = Query(24, ge=1, le=720),
    admin: dict = Depends(get_admin_user),
):
    """Safety pipeline metrics: rewrites, blocks, output validations."""
    since = _ago(hours=hours)

    # Input safety events
    pipeline = [
        {"$match": {"timestamp": {"$gte": since.isoformat()}}},
        {"$group": {
            "_id": "$decision",
            "count": {"$sum": 1},
        }},
    ]
    safety_stats = {}
    async for doc in db.safety_events.aggregate(pipeline):
        safety_stats[doc["_id"]] = doc["count"]

    # By feature
    feature_pipeline = [
        {"$match": {"timestamp": {"$gte": since.isoformat()}}},
        {"$group": {
            "_id": {"feature": "$feature_name", "decision": "$decision"},
            "count": {"$sum": 1},
        }},
    ]
    by_feature = {}
    async for doc in db.safety_events.aggregate(feature_pipeline):
        feat = doc["_id"]["feature"]
        dec = doc["_id"]["decision"]
        by_feature.setdefault(feat, {})[dec] = doc["count"]

    # Output validation events
    ov_pipeline = [
        {"$match": {"timestamp": {"$gte": since.isoformat()}}},
        {"$group": {
            "_id": "$action_taken",
            "count": {"$sum": 1},
            "total_leaked": {"$sum": "$leaked_terms"},
        }},
    ]
    output_stats = {}
    async for doc in db.output_validation_events.aggregate(ov_pipeline):
        output_stats[doc["_id"]] = {
            "count": doc["count"],
            "leaked_terms": doc["total_leaked"],
        }

    total_events = sum(safety_stats.values())

    return {
        "period_hours": hours,
        "input_safety": {
            "total_events": total_events,
            "allowed": safety_stats.get("ALLOW", 0),
            "rewritten": safety_stats.get("REWRITE", 0),
            "blocked": safety_stats.get("BLOCK", 0),
            "rewrite_rate": _safe_rate(safety_stats.get("REWRITE", 0), total_events),
            "block_rate": _safe_rate(safety_stats.get("BLOCK", 0), total_events),
        },
        "by_feature": by_feature,
        "output_validation": {
            "none": output_stats.get("none", {}).get("count", 0),
            "rewritten": output_stats.get("rewritten", {}).get("count", 0),
            "total_leaked_terms": sum(v.get("leaked_terms", 0) for v in output_stats.values()),
        },
        "empty_state": total_events == 0,
        "empty_message": "No safety events recorded in this period" if total_events == 0 else None,
    }


@router.get("/safety-events")
async def safety_events_list(
    limit: int = Query(50, ge=1, le=200),
    decision: str = Query(None, regex="^(ALLOW|REWRITE|BLOCK)$"),
    feature: str = Query(None),
    admin: dict = Depends(get_admin_user),
):
    """List recent safety events for admin review."""
    query = {}
    if decision:
        query["decision"] = decision
    if feature:
        query["feature_name"] = feature

    events = []
    cursor = db.safety_events.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit)
    async for doc in cursor:
        events.append(doc)

    return {"events": events, "count": len(events)}
