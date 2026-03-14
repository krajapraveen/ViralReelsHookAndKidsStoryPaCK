"""
Engagement Analytics Routes
Tracks and reports on: challenge completion rate, streak retention,
creations per user, remix rate, upgrade CTA clicks, template usage.
"""
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from shared import db, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/engagement-analytics", tags=["engagement-analytics"])


class CTAClickEvent(BaseModel):
    cta_type: str  # upgrade_banner, buy_credits, plans_page, subscribe
    source_page: str  # dashboard, reel_generator, etc.


class TemplateUsageEvent(BaseModel):
    template_id: str
    template_name: str
    source_page: str


# ─── Track CTA clicks ──────────────────────────────────────────────────
@router.post("/track-cta")
async def track_cta_click(req: CTAClickEvent, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("id") or str(current_user.get("_id"))
    await db.engagement_events.insert_one({
        "user_id": user_id,
        "event_type": "cta_click",
        "cta_type": req.cta_type,
        "source_page": req.source_page,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"tracked": True}


# ─── Track template usage ──────────────────────────────────────────────
@router.post("/track-template")
async def track_template_usage(req: TemplateUsageEvent, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("id") or str(current_user.get("_id"))
    await db.engagement_events.insert_one({
        "user_id": user_id,
        "event_type": "template_usage",
        "template_id": req.template_id,
        "template_name": req.template_name,
        "source_page": req.source_page,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"tracked": True}


# ─── Admin Analytics Dashboard ──────────────────────────────────────────
@router.get("/report")
async def get_engagement_report(current_user: dict = Depends(get_current_user)):
    """Full engagement analytics report for admin users."""
    user_role = current_user.get("role", "")
    if user_role not in ("ADMIN", "admin"):
        raise HTTPException(status_code=403, detail="Admin access required")

    now = datetime.now(timezone.utc)
    day_ago = (now - timedelta(days=1)).isoformat()
    week_ago = (now - timedelta(days=7)).isoformat()
    month_ago = (now - timedelta(days=30)).isoformat()

    # --- Challenge Completion Rate ---
    total_challenges_issued = await db.daily_challenges.count_documents({})
    total_completions = await db.challenge_completions.count_documents({})
    completions_today = await db.challenge_completions.count_documents({"completed_at": {"$gte": day_ago}})
    completions_week = await db.challenge_completions.count_documents({"completed_at": {"$gte": week_ago}})

    # --- Streak Retention ---
    active_streaks = await db.creation_streaks.count_documents({"current_streak": {"$gte": 1}})
    streaks_7d = await db.creation_streaks.count_documents({"current_streak": {"$gte": 7}})
    streaks_14d = await db.creation_streaks.count_documents({"current_streak": {"$gte": 14}})
    streaks_30d = await db.creation_streaks.count_documents({"current_streak": {"$gte": 30}})

    # --- Creations Per User ---
    pipeline_creations = [
        {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
        {"$group": {"_id": None, "avg": {"$avg": "$count"}, "total_users": {"$sum": 1}, "total_creations": {"$sum": "$count"}}},
    ]
    creations_agg = await db.generation_jobs.aggregate(pipeline_creations).to_list(length=1)
    creations_per_user = creations_agg[0] if creations_agg else {"avg": 0, "total_users": 0, "total_creations": 0}

    # --- Remix Rate ---
    total_remixes = await db.remix_events.count_documents({})
    total_generations = creations_per_user.get("total_creations", 0)
    remix_rate = round(total_remixes / max(total_generations, 1) * 100, 1)

    # Remix breakdown by type
    remix_by_type_pipeline = [
        {"$group": {"_id": "$variation_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    remix_by_type = {d["_id"]: d["count"] async for d in db.remix_events.aggregate(remix_by_type_pipeline)}

    # Average remix chain length  
    remix_chain_pipeline = [
        {"$match": {"original_generation_id": {"$ne": None}}},
        {"$group": {"_id": "$original_generation_id", "chain_length": {"$sum": 1}}},
        {"$group": {"_id": None, "avg_chain": {"$avg": "$chain_length"}, "max_chain": {"$max": "$chain_length"}}},
    ]
    chain_data = await db.remix_events.aggregate(remix_chain_pipeline).to_list(length=1)
    avg_chain = chain_data[0] if chain_data else {"avg_chain": 0, "max_chain": 0}

    # --- CTA Click Rate ---
    cta_clicks = await db.engagement_events.count_documents({"event_type": "cta_click"})
    cta_by_type_pipeline = [
        {"$match": {"event_type": "cta_click"}},
        {"$group": {"_id": "$cta_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    cta_by_type = {d["_id"]: d["count"] async for d in db.engagement_events.aggregate(cta_by_type_pipeline)}

    # --- Template Usage ---
    template_pipeline = [
        {"$match": {"event_type": "template_usage"}},
        {"$group": {"_id": "$template_name", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    top_templates = {d["_id"]: d["count"] async for d in db.engagement_events.aggregate(template_pipeline)}

    # --- Variation Click Rate ---
    variation_clicks_today = await db.remix_events.count_documents({"created_at": {"$gte": day_ago}})
    variation_clicks_week = await db.remix_events.count_documents({"created_at": {"$gte": week_ago}})

    # --- Cross-tool conversions ---
    cross_tool = await db.remix_events.count_documents({"$expr": {"$ne": ["$source_tool", "$target_tool"]}})

    return {
        "generated_at": now.isoformat(),
        "challenge_completion": {
            "total_challenges": total_challenges_issued,
            "total_completions": total_completions,
            "completions_today": completions_today,
            "completions_this_week": completions_week,
            "completion_rate": round(total_completions / max(total_challenges_issued, 1) * 100, 1),
        },
        "streak_retention": {
            "active_streaks": active_streaks,
            "7_day_streaks": streaks_7d,
            "14_day_streaks": streaks_14d,
            "30_day_streaks": streaks_30d,
        },
        "creations": {
            "total_creations": creations_per_user.get("total_creations", 0),
            "total_users_with_creations": creations_per_user.get("total_users", 0),
            "avg_creations_per_user": round(creations_per_user.get("avg", 0), 1),
        },
        "remix_engine": {
            "total_remixes": total_remixes,
            "remix_rate_percent": remix_rate,
            "remixes_by_type": remix_by_type,
            "avg_remix_chain_length": round(avg_chain.get("avg_chain", 0), 1),
            "max_remix_chain_length": avg_chain.get("max_chain", 0),
            "cross_tool_conversions": cross_tool,
            "variation_clicks_today": variation_clicks_today,
            "variation_clicks_this_week": variation_clicks_week,
        },
        "cta_performance": {
            "total_clicks": cta_clicks,
            "clicks_by_type": cta_by_type,
        },
        "template_usage": {
            "top_templates": top_templates,
        },
    }
