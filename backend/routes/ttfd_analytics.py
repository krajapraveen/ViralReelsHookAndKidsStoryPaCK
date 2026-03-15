"""
TTFD Analytics & Engagement Tracking Routes
Tracks time-to-first-delight metrics, queue performance, and user engagement.
"""

import time
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional
from shared import db, get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ─── ENGAGEMENT TRACKING ────────────────────────────────────────────────

class TrackEventRequest(BaseModel):
    event_type: str = Field(..., pattern="^(preview_played|preview_watch_duration|export_started|export_completed|story_pack_downloaded|video_shared)$")
    value: Optional[float] = None  # duration in seconds for watch_duration, etc.


# In-memory throttle to avoid spamming (job_id + event_type -> last_ts)
_event_throttle = {}
THROTTLE_SECONDS = 10


@router.post("/track-event/{job_id}")
async def track_engagement_event(
    job_id: str,
    req: TrackEventRequest,
    current_user: dict = Depends(get_current_user)
):
    """Track a frontend engagement event for a job.
    Throttled to avoid spam. Deduplicates within throttle window."""
    user_id = current_user.get("id") or str(current_user.get("_id"))
    key = f"{job_id}:{req.event_type}:{user_id}"

    # Throttle: ignore duplicate events within window
    now = time.time()
    if key in _event_throttle and (now - _event_throttle[key]) < THROTTLE_SECONDS:
        return {"success": True, "throttled": True}
    _event_throttle[key] = now

    # Clean old throttle entries periodically
    if len(_event_throttle) > 10000:
        cutoff = now - THROTTLE_SECONDS * 2
        for k in list(_event_throttle):
            if _event_throttle[k] < cutoff:
                del _event_throttle[k]

    # Store event
    event = {
        "job_id": job_id,
        "user_id": user_id,
        "event_type": req.event_type,
        "value": req.value,
        "timestamp": datetime.now(timezone.utc),
    }
    await db.engagement_events.insert_one(event)

    # Also update job document with engagement flags (lightweight)
    update = {}
    if req.event_type == "preview_played":
        update["engagement.preview_played"] = True
    elif req.event_type == "preview_watch_duration":
        update["engagement.preview_watch_duration"] = req.value
    elif req.event_type == "export_started":
        update["engagement.export_started"] = True
        update["engagement.export_start_ts"] = now
    elif req.event_type == "export_completed":
        update["engagement.export_completed"] = True
    elif req.event_type == "story_pack_downloaded":
        update["engagement.story_pack_downloaded"] = True
    elif req.event_type == "video_shared":
        update["engagement.video_shared"] = True

    if update:
        await db.pipeline_jobs.update_one({"job_id": job_id}, {"$set": update})

    return {"success": True}


# ─── TTFD ANALYTICS DASHBOARD ──────────────────────────────────────────

@router.get("/ttfd")
async def get_ttfd_analytics(
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """Get TTFD analytics for admin dashboard.
    Returns averages, medians, daily trends, and performance vs targets."""
    if current_user.get("role") not in ("admin", "ADMIN"):
        raise HTTPException(status_code=403, detail="Admin only")

    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Aggregate TTFD metrics from completed/partial jobs
    pipeline = [
        {"$match": {
            "created_at": {"$gte": since},
            "ttfd_metrics": {"$exists": True},
            "ttfd_metrics.pipeline_start": {"$exists": True},
        }},
        {"$project": {
            "_id": 0,
            "status": 1,
            "queue_tier": 1,
            "ttfs": "$ttfd_metrics.time_to_first_scene",
            "ttfi": "$ttfd_metrics.time_to_first_image",
            "ttfv": "$ttfd_metrics.time_to_first_voice",
            "ttfp": "$ttfd_metrics.time_to_first_playable_preview",
            "total": "$ttfd_metrics.total_generation_time",
            "queue_wait": "$queue_wait_ms",
            "created_date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "engagement": 1,
        }},
    ]

    jobs = await db.pipeline_jobs.aggregate(pipeline).to_list(5000)

    if not jobs:
        return {"success": True, "data": {"jobs_analyzed": 0}}

    # Calculate averages and medians
    def avg_median(values):
        vals = [v for v in values if v is not None and v > 0]
        if not vals:
            return {"avg": None, "median": None, "p95": None, "count": 0}
        vals.sort()
        n = len(vals)
        return {
            "avg": round(sum(vals) / n, 2),
            "median": round(vals[n // 2], 2),
            "p95": round(vals[int(n * 0.95)], 2) if n > 1 else round(vals[0], 2),
            "count": n,
        }

    ttfs_vals = [j.get("ttfs") for j in jobs]
    ttfi_vals = [j.get("ttfi") for j in jobs]
    ttfv_vals = [j.get("ttfv") for j in jobs]
    ttfp_vals = [j.get("ttfp") for j in jobs]
    total_vals = [j.get("total") for j in jobs]

    # Queue wait times by tier
    queue_by_tier = {}
    for tier in ["FREE", "PAID", "ADMIN"]:
        tier_waits = [j.get("queue_wait", 0) for j in jobs if j.get("queue_tier") == tier and j.get("queue_wait")]
        queue_by_tier[tier.lower()] = avg_median(tier_waits)

    # Engagement rates
    total_jobs = len(jobs)
    preview_played = sum(1 for j in jobs if j.get("engagement", {}).get("preview_played"))
    export_started = sum(1 for j in jobs if j.get("engagement", {}).get("export_started"))
    export_completed = sum(1 for j in jobs if j.get("engagement", {}).get("export_completed"))
    pack_downloaded = sum(1 for j in jobs if j.get("engagement", {}).get("story_pack_downloaded"))
    video_shared = sum(1 for j in jobs if j.get("engagement", {}).get("video_shared"))

    # Export success rate
    completed = sum(1 for j in jobs if j.get("status") == "COMPLETED")
    partial = sum(1 for j in jobs if j.get("status") == "PARTIAL")
    failed = sum(1 for j in jobs if j.get("status") == "FAILED")
    export_success_rate = round(completed / total_jobs * 100, 1) if total_jobs > 0 else 0

    # Daily trends (last 14 days)
    daily = {}
    for j in jobs:
        d = j.get("created_date", "")
        if d not in daily:
            daily[d] = {"ttfs": [], "ttfi": [], "ttfp": [], "total": [], "count": 0}
        daily[d]["count"] += 1
        if j.get("ttfs"):
            daily[d]["ttfs"].append(j["ttfs"])
        if j.get("ttfi"):
            daily[d]["ttfi"].append(j["ttfi"])
        if j.get("ttfp"):
            daily[d]["ttfp"].append(j["ttfp"])
        if j.get("total"):
            daily[d]["total"].append(j["total"])

    daily_trends = []
    for d in sorted(daily.keys())[-14:]:
        v = daily[d]
        daily_trends.append({
            "date": d,
            "jobs": v["count"],
            "avg_ttfs": round(sum(v["ttfs"]) / len(v["ttfs"]), 2) if v["ttfs"] else None,
            "avg_ttfi": round(sum(v["ttfi"]) / len(v["ttfi"]), 2) if v["ttfi"] else None,
            "avg_ttfp": round(sum(v["ttfp"]) / len(v["ttfp"]), 2) if v["ttfp"] else None,
            "avg_total": round(sum(v["total"]) / len(v["total"]), 2) if v["total"] else None,
        })

    # Performance vs Targets
    ttfs_med = avg_median(ttfs_vals)["median"]
    ttfi_med = avg_median(ttfi_vals)["median"]
    ttfp_med = avg_median(ttfp_vals)["median"]

    targets = [
        {"metric": "Time to First Scene", "target": 5, "unit": "s", "current": ttfs_med, "status": "pass" if ttfs_med and ttfs_med < 5 else "fail"},
        {"metric": "Time to First Image", "target": 20, "unit": "s", "current": ttfi_med, "status": "pass" if ttfi_med and ttfi_med < 20 else "fail"},
        {"metric": "Time to Playable Preview", "target": 60, "unit": "s", "current": ttfp_med, "status": "pass" if ttfp_med and ttfp_med < 60 else "fail"},
        {"metric": "Export Success Rate", "target": 95, "unit": "%", "current": export_success_rate, "status": "pass" if export_success_rate >= 95 else "fail"},
    ]

    return {
        "success": True,
        "data": {
            "jobs_analyzed": total_jobs,
            "period_days": days,
            "ttfd": {
                "time_to_first_scene": avg_median(ttfs_vals),
                "time_to_first_image": avg_median(ttfi_vals),
                "time_to_first_voice": avg_median(ttfv_vals),
                "time_to_first_playable_preview": avg_median(ttfp_vals),
                "total_generation_time": avg_median(total_vals),
            },
            "queue_performance": queue_by_tier,
            "engagement": {
                "preview_play_rate": round(preview_played / total_jobs * 100, 1) if total_jobs else 0,
                "export_start_rate": round(export_started / total_jobs * 100, 1) if total_jobs else 0,
                "export_completion_rate": round(export_completed / max(export_started, 1) * 100, 1),
                "story_pack_download_rate": round(pack_downloaded / total_jobs * 100, 1) if total_jobs else 0,
                "share_rate": round(video_shared / total_jobs * 100, 1) if total_jobs else 0,
            },
            "pipeline_health": {
                "completed": completed,
                "partial": partial,
                "failed": failed,
                "export_success_rate": export_success_rate,
            },
            "targets": targets,
            "daily_trends": daily_trends,
        }
    }


# ─── QUEUE PERFORMANCE ──────────────────────────────────────────────────

@router.get("/queue")
async def get_queue_analytics(
    current_user: dict = Depends(get_current_user)
):
    """Get queue performance metrics for admin dashboard."""
    if current_user.get("role") not in ("admin", "ADMIN"):
        raise HTTPException(status_code=403, detail="Admin only")

    # Get worker stats
    try:
        from services.pipeline_worker import get_worker_stats
        stats = get_worker_stats()
    except Exception:
        stats = {}

    # Get queue depth
    queue_depth = await db.pipeline_jobs.count_documents({"status": "QUEUED"})
    processing = await db.pipeline_jobs.count_documents({"status": "PROCESSING"})

    # Recent queue waits by tier (last 24h)
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_jobs = await db.pipeline_jobs.find(
        {"created_at": {"$gte": since}, "queue_wait_ms": {"$exists": True}},
        {"_id": 0, "queue_tier": 1, "queue_wait_ms": 1}
    ).to_list(1000)

    tier_waits = {"FREE": [], "PAID": [], "ADMIN": []}
    for j in recent_jobs:
        tier = j.get("queue_tier", "FREE")
        wait = j.get("queue_wait_ms", 0)
        if tier in tier_waits:
            tier_waits[tier].append(wait)

    def summarize(vals):
        if not vals:
            return {"avg_ms": 0, "p95_ms": 0, "count": 0}
        vals.sort()
        return {
            "avg_ms": round(sum(vals) / len(vals)),
            "p95_ms": round(vals[int(len(vals) * 0.95)]) if len(vals) > 1 else vals[0],
            "count": len(vals),
        }

    return {
        "success": True,
        "data": {
            "queue_depth": queue_depth,
            "processing": processing,
            "worker_stats": stats,
            "tier_wait_times_24h": {
                "free": summarize(tier_waits["FREE"]),
                "paid": summarize(tier_waits["PAID"]),
                "admin": summarize(tier_waits["ADMIN"]),
            },
        }
    }


# ─── DAILY AGGREGATION ──────────────────────────────────────────────────

async def run_daily_aggregation():
    """Lightweight daily aggregation job. Called by background scheduler.
    Stores daily aggregates to avoid expensive reads on every dashboard load."""
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)

    jobs = await db.pipeline_jobs.find(
        {"created_at": {"$gte": yesterday, "$lt": today}, "ttfd_metrics": {"$exists": True}},
        {"_id": 0, "ttfd_metrics": 1, "status": 1, "queue_tier": 1, "queue_wait_ms": 1, "engagement": 1}
    ).to_list(10000)

    if not jobs:
        return

    total = len(jobs)
    def safe_avg(vals):
        v = [x for x in vals if x and x > 0]
        return round(sum(v) / len(v), 2) if v else None

    ttfs = [j.get("ttfd_metrics", {}).get("time_to_first_scene") for j in jobs]
    ttfi = [j.get("ttfd_metrics", {}).get("time_to_first_image") for j in jobs]
    ttfp = [j.get("ttfd_metrics", {}).get("time_to_first_playable_preview") for j in jobs]
    totals = [j.get("ttfd_metrics", {}).get("total_generation_time") for j in jobs]

    completed = sum(1 for j in jobs if j.get("status") == "COMPLETED")
    preview_played = sum(1 for j in jobs if j.get("engagement", {}).get("preview_played"))
    export_started = sum(1 for j in jobs if j.get("engagement", {}).get("export_started"))
    export_completed = sum(1 for j in jobs if j.get("engagement", {}).get("export_completed"))
    pack_downloaded = sum(1 for j in jobs if j.get("engagement", {}).get("story_pack_downloaded"))

    # Queue waits
    free_waits = [j["queue_wait_ms"] for j in jobs if j.get("queue_tier") == "FREE" and j.get("queue_wait_ms")]
    paid_waits = [j["queue_wait_ms"] for j in jobs if j.get("queue_tier") == "PAID" and j.get("queue_wait_ms")]

    agg = {
        "date": yesterday.strftime("%Y-%m-%d"),
        "total_jobs": total,
        "daily_avg_ttfs": safe_avg(ttfs),
        "daily_avg_ttfi": safe_avg(ttfi),
        "daily_avg_ttfp": safe_avg(ttfp),
        "daily_avg_total": safe_avg(totals),
        "daily_export_rate": round(completed / total * 100, 1) if total else 0,
        "daily_preview_play_rate": round(preview_played / total * 100, 1) if total else 0,
        "daily_export_start_rate": round(export_started / total * 100, 1) if total else 0,
        "daily_export_complete_rate": round(export_completed / max(export_started, 1) * 100, 1),
        "daily_pack_download_rate": round(pack_downloaded / total * 100, 1) if total else 0,
        "daily_queue_wait_free_avg": safe_avg(free_waits),
        "daily_queue_wait_paid_avg": safe_avg(paid_waits),
        "aggregated_at": datetime.now(timezone.utc),
    }

    await db.daily_analytics.update_one(
        {"date": agg["date"]},
        {"$set": agg},
        upsert=True
    )


@router.get("/daily-aggregates")
async def get_daily_aggregates(
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """Get pre-computed daily aggregates for fast dashboard loading."""
    if current_user.get("role") not in ("admin", "ADMIN"):
        raise HTTPException(status_code=403, detail="Admin only")

    since_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    aggs = await db.daily_analytics.find(
        {"date": {"$gte": since_date}},
        {"_id": 0}
    ).sort("date", 1).to_list(days)

    return {"success": True, "data": aggs}
