"""
Conversion Analytics Dashboard — Decision-grade metrics.
No vanity charts. Every number traces to events or state transitions.

Metrics:
- Spectator → Player %
- Watch start/completion rates
- Stories per session
- CTA click-through rates (Make Your Version, Quick Shot, Next Episode)
- Queue rate + Queue-to-complete rate
- Funnel: impression → click → watch → create → complete

Admin-only. Filters: 24h / 7d / 30d.
"""
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from shared import db, get_current_user

logger = logging.getLogger("analytics_dashboard")
router = APIRouter(prefix="/analytics", tags=["analytics"])


def _time_filter(hours: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


@router.get("/conversion-dashboard")
async def conversion_dashboard(
    period: str = Query("24h", pattern="^(24h|7d|30d)$"),
    current_user: dict = Depends(get_current_user),
):
    """
    Conversion Analytics Dashboard — admin only.
    Every metric comes from actual tracked events or job state transitions.
    """
    role = (current_user.get("role") or "").upper()
    if role not in ("ADMIN", "SUPERADMIN"):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin only")

    hours = {"24h": 24, "7d": 168, "30d": 720}[period]
    since = _time_filter(hours)

    # ═══ 1. FUNNEL EVENTS (from funnel_events collection) ═══
    funnel_steps = [
        "story_viewed", "story_card_clicked", "watch_started",
        "watch_completed_50", "watch_completed_100",
        "cta_clicked", "remix_clicked", "create_clicked",
        "scroll_depth_50", "spectator_impression",
        "spectator_pressure_shown", "spectator_quick_shot",
        "spectator_to_player_conversion",
    ]

    funnel_counts = {}
    for step in funnel_steps:
        count = await db.funnel_events.count_documents({
            "step": step,
            "timestamp": {"$gte": since},
        })
        funnel_counts[step] = count

    # ═══ 2. CTA BREAKDOWN (from funnel_events with meta.type) ═══
    cta_pipeline = [
        {"$match": {"step": "cta_clicked", "timestamp": {"$gte": since}}},
        {"$group": {"_id": "$meta.type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    cta_breakdown = {}
    async for doc in db.funnel_events.aggregate(cta_pipeline):
        cta_breakdown[str(doc["_id"] or "unknown")] = doc["count"]

    # ═══ 3. SOURCE SECTION BREAKDOWN ═══
    source_pipeline = [
        {"$match": {"step": "story_card_clicked", "timestamp": {"$gte": since}}},
        {"$group": {"_id": "$meta.badge", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    source_breakdown = {}
    async for doc in db.funnel_events.aggregate(source_pipeline):
        source_breakdown[str(doc["_id"] or "unknown")] = doc["count"]

    # ═══ 4. JOB STATE METRICS (from story_engine_jobs) ═══
    total_created = await db.story_engine_jobs.count_documents({"created_at": {"$gte": since}})
    total_queued = await db.story_engine_jobs.count_documents({"state": "QUEUED", "created_at": {"$gte": since}})
    total_completed = await db.story_engine_jobs.count_documents({
        "state": {"$in": ["READY", "PARTIAL_READY"]},
        "created_at": {"$gte": since},
    })
    total_failed = await db.story_engine_jobs.count_documents({
        "state": {"$regex": "^FAILED"},
        "created_at": {"$gte": since},
    })

    # Jobs that were queued and then completed
    queue_completed = await db.story_engine_jobs.count_documents({
        "promoted_from_queue_at": {"$exists": True},
        "state": {"$in": ["READY", "PARTIAL_READY"]},
        "created_at": {"$gte": since},
    })
    queue_total = await db.story_engine_jobs.count_documents({
        "queued_at": {"$exists": True},
        "created_at": {"$gte": since},
    })

    # Branch entries (battles)
    branch_entries = await db.story_engine_jobs.count_documents({
        "continuation_type": "branch",
        "created_at": {"$gte": since},
    })
    quick_shot_entries = await db.analytics_events.count_documents({
        "event": "quick_shot_entry",
        "created_at": {"$gte": since},
    })

    # ═══ 5. SESSION METRICS ═══
    unique_sessions = await db.funnel_events.distinct("session_id", {"timestamp": {"$gte": since}})
    session_count = len(unique_sessions) if unique_sessions else 1

    # Unique users
    unique_users_pipeline = [
        {"$match": {"timestamp": {"$gte": since}, "user_id": {"$ne": None}}},
        {"$group": {"_id": "$user_id"}},
        {"$count": "total"},
    ]
    unique_users_result = await db.funnel_events.aggregate(unique_users_pipeline).to_list(1)
    unique_users = unique_users_result[0]["total"] if unique_users_result else 0

    # ═══ 6. COMPUTED METRICS (exact formulas) ═══
    impressions = funnel_counts.get("spectator_impression", 0) or funnel_counts.get("story_viewed", 0) or 1
    card_clicks = funnel_counts.get("story_card_clicked", 0)
    watch_starts = funnel_counts.get("watch_started", 0)
    watch_50 = funnel_counts.get("watch_completed_50", 0)
    watch_100 = funnel_counts.get("watch_completed_100", 0)
    spectator_to_player = funnel_counts.get("spectator_to_player_conversion", 0) + quick_shot_entries

    metrics = {
        # Core conversion
        "spectator_to_player_pct": round((spectator_to_player / max(impressions, 1)) * 100, 2),
        "spectator_to_player_pct_formula": "( spectator_conversions + quick_shots ) / spectator_impressions * 100",

        # Watch behavior
        "watch_start_rate": round((watch_starts / max(card_clicks, 1)) * 100, 2),
        "watch_start_rate_formula": "watch_started / story_card_clicked * 100",
        "watch_completion_50_pct": round((watch_50 / max(watch_starts, 1)) * 100, 2),
        "watch_completion_100_pct": round((watch_100 / max(watch_starts, 1)) * 100, 2),

        # Session depth
        "stories_per_session": round(card_clicks / max(session_count, 1), 2),
        "stories_per_session_formula": "story_card_clicked / unique_sessions",

        # CTA performance
        "make_your_version_ctr": round((cta_breakdown.get("make_your_version", 0) / max(impressions, 1)) * 100, 2),
        "quick_shot_ctr": round((quick_shot_entries / max(impressions, 1)) * 100, 2),
        "next_episode_ctr": round((cta_breakdown.get("next_episode", 0) / max(watch_100, 1)) * 100, 2),

        # Queue behavior
        "queue_rate": round((total_queued / max(total_created, 1)) * 100, 2),
        "queue_rate_formula": "QUEUED_jobs / total_jobs_created * 100",
        "queue_to_complete_rate": round((queue_completed / max(queue_total, 1)) * 100, 2),
        "queue_to_complete_formula": "queued_then_completed / total_queued * 100",
    }

    # ═══ 7. FUNNEL (ordered) ═══
    funnel = [
        {"step": "story_impression", "count": impressions, "source": "funnel_events.spectator_impression or story_viewed"},
        {"step": "story_card_clicked", "count": card_clicks, "source": "funnel_events.story_card_clicked"},
        {"step": "watch_started", "count": watch_starts, "source": "funnel_events.watch_started"},
        {"step": "watch_completed_50", "count": watch_50, "source": "funnel_events.watch_completed_50"},
        {"step": "watch_completed_100", "count": watch_100, "source": "funnel_events.watch_completed_100"},
        {"step": "make_your_version_clicked", "count": cta_breakdown.get("make_your_version", 0) + cta_breakdown.get("launch_branch", 0), "source": "funnel_events.cta_clicked type=make_your_version|launch_branch"},
        {"step": "entry_created", "count": branch_entries + quick_shot_entries, "source": "story_engine_jobs.continuation_type=branch + analytics_events.quick_shot_entry"},
        {"step": "queued", "count": total_queued, "source": "story_engine_jobs.state=QUEUED"},
        {"step": "completed", "count": total_completed, "source": "story_engine_jobs.state in [READY, PARTIAL_READY]"},
    ]

    return {
        "success": True,
        "period": period,
        "since": since,
        "metrics": metrics,
        "funnel": funnel,
        "cta_breakdown": cta_breakdown,
        "source_section_breakdown": source_breakdown,
        "job_stats": {
            "total_created": total_created,
            "total_queued": total_queued,
            "total_completed": total_completed,
            "total_failed": total_failed,
            "branch_entries": branch_entries,
            "quick_shot_entries": quick_shot_entries,
            "queue_completed": queue_completed,
        },
        "session_stats": {
            "unique_sessions": session_count,
            "unique_users": unique_users,
        },
    }
