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
