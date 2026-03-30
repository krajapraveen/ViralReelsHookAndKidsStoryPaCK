"""
Retention Analytics API — The 5 key metrics that determine whether users stay or leave.

1. Avg Session Time
2. Scroll Depth Distribution
3. Hook CTR (Click-Through Rate)
4. Continue Rate
5. First 10-Second Drop-Off Rate

All metrics support: trends over time, device segmentation (mobile/desktop), new vs returning.
Data sources: `sessions`, `growth_events`, `preview_events`, `user_homepage_profile`.
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from typing import Optional
import logging

from shared import db, get_admin_user

logger = logging.getLogger("retention_analytics")
router = APIRouter(prefix="/admin/retention", tags=["Retention Analytics"])


def _now():
    return datetime.now(timezone.utc)


# ─── SESSION TRACKING ───────────────────────────────────────────────────

class SessionEvent(BaseModel):
    session_id: str
    event: str  # "start", "heartbeat", "end"
    scroll_depth: Optional[int] = None
    device: Optional[str] = None  # "mobile" or "desktop"
    actions: Optional[int] = None
    user_agent: Optional[str] = None


@router.post("/session")
async def track_session(data: SessionEvent):
    """Track session start, heartbeat, and end events.
    Frontend sends: start (on mount), heartbeat (every 30s), end (on unmount/visibility change).
    Open to all users (including anonymous)."""
    now = _now().isoformat()

    if data.event == "start":
        await db.sessions.update_one(
            {"session_id": data.session_id},
            {"$set": {
                "session_id": data.session_id,
                "started_at": now,
                "last_heartbeat": now,
                "device": data.device or "unknown",
                "scroll_depth": 0,
                "actions": 0,
                "duration_seconds": 0,
                "status": "active",
            }, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
    elif data.event == "heartbeat":
        # Calculate duration from start
        session = await db.sessions.find_one({"session_id": data.session_id}, {"_id": 0, "started_at": 1})
        duration = 0
        if session and session.get("started_at"):
            try:
                start = datetime.fromisoformat(session["started_at"].replace("Z", "+00:00"))
                duration = (_now() - start).total_seconds()
            except Exception:
                pass
        update = {
            "last_heartbeat": now,
            "duration_seconds": duration,
            "status": "active",
        }
        if data.scroll_depth is not None:
            update["scroll_depth"] = data.scroll_depth
        if data.actions is not None:
            update["actions"] = data.actions
        await db.sessions.update_one(
            {"session_id": data.session_id},
            {"$set": update},
        )
    elif data.event == "end":
        session = await db.sessions.find_one({"session_id": data.session_id}, {"_id": 0, "started_at": 1})
        duration = 0
        if session and session.get("started_at"):
            try:
                start = datetime.fromisoformat(session["started_at"].replace("Z", "+00:00"))
                duration = (_now() - start).total_seconds()
            except Exception:
                pass
        update = {
            "ended_at": now,
            "duration_seconds": duration,
            "status": "ended",
        }
        if data.scroll_depth is not None:
            update["scroll_depth"] = data.scroll_depth
        if data.actions is not None:
            update["actions"] = data.actions
        await db.sessions.update_one(
            {"session_id": data.session_id},
            {"$set": update},
        )

    return {"success": True}


# ─── RETENTION DASHBOARD METRICS ─────────────────────────────────────────

@router.get("/dashboard")
async def get_retention_dashboard(
    days: int = Query(7, ge=1, le=90),
    admin: dict = Depends(get_admin_user),
):
    """The 5 key retention metrics with trends and segmentation."""
    cutoff = (_now() - timedelta(days=days)).isoformat()

    # ── 1. AVG SESSION TIME ──
    session_pipeline = [
        {"$match": {"started_at": {"$gte": cutoff}, "duration_seconds": {"$gt": 0}}},
        {"$group": {
            "_id": None,
            "avg_duration": {"$avg": "$duration_seconds"},
            "median_duration": {"$avg": "$duration_seconds"},  # approx
            "total_sessions": {"$sum": 1},
            "total_duration": {"$sum": "$duration_seconds"},
        }},
    ]
    session_stats = await db.sessions.aggregate(session_pipeline).to_list(1)
    avg_session = session_stats[0] if session_stats else {"avg_duration": 0, "total_sessions": 0, "total_duration": 0}

    # Session time by device
    device_pipeline = [
        {"$match": {"started_at": {"$gte": cutoff}, "duration_seconds": {"$gt": 0}}},
        {"$group": {
            "_id": "$device",
            "avg_duration": {"$avg": "$duration_seconds"},
            "count": {"$sum": 1},
        }},
    ]
    device_stats = await db.sessions.aggregate(device_pipeline).to_list(10)
    device_breakdown = {d["_id"]: {"avg_seconds": round(d["avg_duration"], 1), "count": d["count"]} for d in device_stats}

    # ── 2. SCROLL DEPTH DISTRIBUTION ──
    scroll_pipeline = [
        {"$match": {"started_at": {"$gte": cutoff}, "scroll_depth": {"$gt": 0}}},
        {"$bucket": {
            "groupBy": "$scroll_depth",
            "boundaries": [0, 2, 5, 10, 20, 50, 100],
            "default": "100+",
            "output": {"count": {"$sum": 1}},
        }},
    ]
    scroll_dist = await db.sessions.aggregate(scroll_pipeline).to_list(20)
    scroll_buckets = {}
    bucket_labels = {0: "0-1", 2: "2-4", 5: "5-9", 10: "10-19", 20: "20-49", 50: "50-99", "100+": "100+"}
    for b in scroll_dist:
        label = bucket_labels.get(b["_id"], str(b["_id"]))
        scroll_buckets[label] = b["count"]

    # ── 3. HOOK CTR ──
    # From growth_events: impressions vs continue_click for hooks
    hook_impressions = await db.growth_events.count_documents({
        "event_type": "impression",
        "timestamp": {"$gte": cutoff},
    })
    hook_clicks = await db.growth_events.count_documents({
        "event_type": {"$in": ["continue", "continue_click", "click"]},
        "timestamp": {"$gte": cutoff},
    })
    hook_ctr = round((hook_clicks / hook_impressions * 100), 2) if hook_impressions > 0 else None

    # ── 4. CONTINUE RATE ──
    total_views = await db.growth_events.count_documents({
        "event_type": {"$in": ["impression", "click", "card_click"]},
        "timestamp": {"$gte": cutoff},
    })
    total_continues = await db.growth_events.count_documents({
        "event_type": {"$in": ["continue", "continue_click"]},
        "timestamp": {"$gte": cutoff},
    })
    continue_rate = round((total_continues / total_views * 100), 2) if total_views > 0 else None

    # ── 5. FIRST 10-SECOND DROP-OFF RATE ──
    total_sessions_period = await db.sessions.count_documents({"started_at": {"$gte": cutoff}, "duration_seconds": {"$gt": 0}})
    dropped_10s = await db.sessions.count_documents({
        "started_at": {"$gte": cutoff},
        "duration_seconds": {"$gt": 0, "$lt": 10},
    })
    dropoff_10s_rate = round((dropped_10s / total_sessions_period * 100), 1) if total_sessions_period > 0 else None

    # ── DAILY TRENDS (last N days) ──
    trends = []
    for i in range(min(days, 30)):
        day_start = (_now() - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        ds = day_start.isoformat()
        de = day_end.isoformat()

        day_sessions = await db.sessions.count_documents({"started_at": {"$gte": ds, "$lt": de}, "duration_seconds": {"$gt": 0}})
        day_avg_pipe = [
            {"$match": {"started_at": {"$gte": ds, "$lt": de}, "duration_seconds": {"$gt": 0}}},
            {"$group": {"_id": None, "avg": {"$avg": "$duration_seconds"}}},
        ]
        day_avg_res = await db.sessions.aggregate(day_avg_pipe).to_list(1)
        day_avg = round(day_avg_res[0]["avg"], 1) if day_avg_res else 0

        day_impressions = await db.growth_events.count_documents({"event_type": "impression", "timestamp": {"$gte": ds, "$lt": de}})
        day_clicks = await db.growth_events.count_documents({"event_type": {"$in": ["continue", "continue_click", "click"]}, "timestamp": {"$gte": ds, "$lt": de}})
        day_ctr = round((day_clicks / day_impressions * 100), 2) if day_impressions > 0 else 0

        day_dropped = await db.sessions.count_documents({"started_at": {"$gte": ds, "$lt": de}, "duration_seconds": {"$gt": 0, "$lt": 10}})
        day_dropoff = round((day_dropped / day_sessions * 100), 1) if day_sessions > 0 else 0

        trends.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "sessions": day_sessions,
            "avg_session_seconds": day_avg,
            "hook_ctr": day_ctr,
            "dropoff_10s": day_dropoff,
        })

    trends.reverse()  # oldest first

    # ── SESSION TIME DISTRIBUTION (for retention curve) ──
    retention_buckets_def = [
        (0, 10, "0-10s"),
        (10, 30, "10-30s"),
        (30, 60, "30-60s"),
        (60, 180, "1-3min"),
        (180, 300, "3-5min"),
        (300, 600, "5-10min"),
        (600, 99999, "10min+"),
    ]
    retention_curve = []
    for low, high, label in retention_buckets_def:
        count = await db.sessions.count_documents({
            "started_at": {"$gte": cutoff},
            "duration_seconds": {"$gte": low, "$lt": high},
        })
        retention_curve.append({"bucket": label, "count": count})

    # ── PREVIEW ANALYTICS ──
    preview_impressions = await db.preview_events.count_documents({"event_type": "preview_impression", "timestamp": {"$gte": cutoff}})
    preview_plays = await db.preview_events.count_documents({"event_type": "preview_play", "timestamp": {"$gte": cutoff}})
    preview_clicks = await db.preview_events.count_documents({"event_type": "preview_click", "timestamp": {"$gte": cutoff}})
    preview_play_rate = round((preview_plays / preview_impressions * 100), 1) if preview_impressions > 0 else None
    preview_click_rate = round((preview_clicks / preview_plays * 100), 1) if preview_plays > 0 else None

    return {
        "period_days": days,
        "metrics": {
            "avg_session_time": {
                "seconds": round(avg_session.get("avg_duration", 0), 1),
                "total_sessions": avg_session.get("total_sessions", 0),
                "device_breakdown": device_breakdown,
                "target": "180+ seconds (3 min = good, 5 min = strong, 8 min = viral)",
            },
            "scroll_depth": {
                "distribution": scroll_buckets,
                "target": "50%+ users reaching depth 5+",
            },
            "hook_ctr": {
                "rate": hook_ctr,
                "impressions": hook_impressions,
                "clicks": hook_clicks,
                "target": "15%+ CTR",
            },
            "continue_rate": {
                "rate": continue_rate,
                "views": total_views,
                "continues": total_continues,
                "target": "10%+ continue rate",
            },
            "dropoff_10s": {
                "rate": dropoff_10s_rate,
                "dropped": dropped_10s,
                "total_sessions": total_sessions_period,
                "target": "<10% drop-off in first 10 seconds",
            },
        },
        "retention_curve": retention_curve,
        "preview_analytics": {
            "impressions": preview_impressions,
            "plays": preview_plays,
            "clicks": preview_clicks,
            "play_rate": preview_play_rate,
            "click_conversion": preview_click_rate,
        },
        "trends": trends,
    }
