"""
Production System Health & Observability Dashboard API
Provides real-time visibility into:
- Queue depth per queue type
- Worker concurrency / busy status
- p50/p95/p99 latency per queue
- Error rates & dead letter queue
- DB health (connections, slow queries)
- Generation completion times by feature
- Request throughput
"""
from fastapi import APIRouter, Depends, Query
from datetime import datetime, timezone, timedelta
import os, sys, time, asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared import db, get_admin_user

router = APIRouter(prefix="/admin/system-health", tags=["System Health"])

# In-memory request latency tracker
_request_latencies = []
_request_counts = {"total": 0, "errors": 0}
_startup_time = time.time()


def record_request(latency_ms: float, is_error: bool = False):
    """Called by middleware to record request latency."""
    _request_latencies.append(latency_ms)
    if len(_request_latencies) > 1000:
        _request_latencies.pop(0)
    _request_counts["total"] += 1
    if is_error:
        _request_counts["errors"] += 1


def _percentile(data, pct):
    if not data:
        return 0
    s = sorted(data)
    idx = int(len(s) * pct / 100)
    return round(s[min(idx, len(s) - 1)], 2)


@router.get("/overview")
async def system_health_overview(user: dict = Depends(get_admin_user)):
    """Full system health dashboard — queue + worker + DB + throughput."""
    now = datetime.now(timezone.utc)

    # 1. Queue health — queued job counts by type
    queue_pipeline = [
        {"$match": {"status": "QUEUED"}},
        {"$group": {"_id": "$jobType", "count": {"$sum": 1}}},
    ]
    queue_depth = {}
    total_queued = 0
    async for doc in db.genstudio_jobs.aggregate(queue_pipeline):
        queue_depth[doc["_id"] or "unknown"] = doc["count"]
        total_queued += doc["count"]

    # Also check comic_storybook_v2_jobs
    comic_queued = await db.comic_storybook_v2_jobs.count_documents({"status": "QUEUED"})

    # 2. Processing jobs (worker busy status)
    processing_pipeline = [
        {"$match": {"status": "PROCESSING"}},
        {"$group": {"_id": "$queueType", "count": {"$sum": 1}}},
    ]
    workers_busy = {}
    total_processing = 0
    async for doc in db.genstudio_jobs.aggregate(processing_pipeline):
        workers_busy[doc["_id"] or "unknown"] = doc["count"]
        total_processing += doc["count"]

    # 3. Dead letter queue size
    dead_letter_count = await db.dead_letter_jobs.count_documents({})
    recent_dead = await db.dead_letter_jobs.count_documents({
        "dead_at": {"$gte": (now - timedelta(hours=24)).isoformat()}
    })

    # 4. Job completion times (last 1 hour, by type)
    hour_ago = (now - timedelta(hours=1)).isoformat()
    completion_pipeline = [
        {"$match": {
            "status": "COMPLETED",
            "completedAt": {"$gte": hour_ago},
            "startedAt": {"$exists": True},
        }},
        {"$project": {
            "jobType": 1,
            "duration": {"$subtract": [
                {"$dateFromString": {"dateString": "$completedAt"}},
                {"$dateFromString": {"dateString": "$startedAt"}},
            ]},
        }},
        {"$group": {
            "_id": "$jobType",
            "avg_ms": {"$avg": "$duration"},
            "max_ms": {"$max": "$duration"},
            "count": {"$sum": 1},
        }},
    ]
    completion_times = {}
    try:
        async for doc in db.genstudio_jobs.aggregate(completion_pipeline):
            jt = doc["_id"] or "unknown"
            completion_times[jt] = {
                "avg_s": round((doc["avg_ms"] or 0) / 1000, 2),
                "max_s": round((doc["max_ms"] or 0) / 1000, 2),
                "count_last_hour": doc["count"],
            }
    except Exception:
        pass  # If date parsing fails, skip gracefully

    # 5. Failed jobs (last 24h)
    day_ago = (now - timedelta(hours=24)).isoformat()
    failed_24h = await db.genstudio_jobs.count_documents({
        "status": {"$in": ["FAILED", "DEAD_LETTER"]},
        "completedAt": {"$gte": day_ago},
    })
    completed_24h = await db.genstudio_jobs.count_documents({
        "status": "COMPLETED",
        "completedAt": {"$gte": day_ago},
    })
    error_rate = round(failed_24h / max(failed_24h + completed_24h, 1) * 100, 2)

    # 6. DB health
    try:
        db_ping_start = time.time()
        await db.command("ping")
        db_latency = round((time.time() - db_ping_start) * 1000, 2)
        db_stats = await db.command("dbStats")
        db_health = {
            "status": "UP" if db_latency < 500 else "DEGRADED",
            "ping_ms": db_latency,
            "data_size_mb": round(db_stats.get("dataSize", 0) / (1024 * 1024), 2),
            "index_size_mb": round(db_stats.get("indexSize", 0) / (1024 * 1024), 2),
            "collections": db_stats.get("collections", 0),
        }
    except Exception as e:
        db_health = {"status": "DOWN", "error": str(e)}

    # 7. Request latency percentiles
    request_health = {
        "total_requests": _request_counts["total"],
        "total_errors": _request_counts["errors"],
        "error_rate_pct": round(_request_counts["errors"] / max(_request_counts["total"], 1) * 100, 2),
        "p50_ms": _percentile(_request_latencies, 50),
        "p95_ms": _percentile(_request_latencies, 95),
        "p99_ms": _percentile(_request_latencies, 99),
        "sample_size": len(_request_latencies),
    }

    # 8. Uptime
    uptime_seconds = round(time.time() - _startup_time)

    # 9. Stuck jobs (processing for > timeout)
    stuck_cutoff = (now - timedelta(minutes=15)).isoformat()
    stuck_jobs = await db.genstudio_jobs.count_documents({
        "status": "PROCESSING",
        "startedAt": {"$lt": stuck_cutoff},
    })

    # 10. Asset access rate (abuse monitoring)
    access_1h = await db.asset_access_log.count_documents({
        "timestamp": {"$gte": hour_ago},
    })
    abuse_1h = await db.abuse_events.count_documents({
        "timestamp": {"$gte": hour_ago},
    })

    return {
        "timestamp": now.isoformat(),
        "uptime_seconds": uptime_seconds,
        "queues": {
            "total_queued": total_queued + comic_queued,
            "depth_by_type": queue_depth,
            "comic_storybook_queued": comic_queued,
        },
        "workers": {
            "total_processing": total_processing,
            "busy_by_queue": workers_busy,
            "stuck_jobs": stuck_jobs,
        },
        "completion_times": completion_times,
        "errors": {
            "failed_24h": failed_24h,
            "completed_24h": completed_24h,
            "error_rate_pct": error_rate,
        },
        "dead_letter": {
            "total": dead_letter_count,
            "last_24h": recent_dead,
        },
        "database": db_health,
        "request_latency": request_health,
        "asset_access": {
            "accesses_last_hour": access_1h,
            "abuse_events_last_hour": abuse_1h,
        },
    }


@router.get("/queues")
async def queue_detail(user: dict = Depends(get_admin_user)):
    """Detailed queue-level health: depth, wait time, processing per queue."""
    now = datetime.now(timezone.utc)

    # Per-queue stats
    queues_info = {}
    queue_types = ["text", "image", "video", "audio", "export", "webhook", "analytics", "batch"]

    for qt in queue_types:
        # Count queued
        queued = await db.genstudio_jobs.count_documents({
            "status": "QUEUED",
            "queueType": qt,
        })
        # Count processing
        processing = await db.genstudio_jobs.count_documents({
            "status": "PROCESSING",
            "queueType": qt,
        })
        # Oldest queued job (wait time proxy)
        oldest = await db.genstudio_jobs.find_one(
            {"status": "QUEUED", "queueType": qt},
            {"_id": 0, "createdAt": 1},
            sort=[("createdAt", 1)],
        )
        wait_seconds = 0
        if oldest and oldest.get("createdAt"):
            try:
                created = datetime.fromisoformat(oldest["createdAt"].replace("Z", "+00:00"))
                wait_seconds = max(0, (now - created).total_seconds())
            except Exception:
                pass

        # Recent failures
        hour_ago = (now - timedelta(hours=1)).isoformat()
        failed_1h = await db.genstudio_jobs.count_documents({
            "status": {"$in": ["FAILED", "DEAD_LETTER"]},
            "queueType": qt,
            "completedAt": {"$gte": hour_ago},
        })

        queues_info[qt] = {
            "queued": queued,
            "processing": processing,
            "max_wait_seconds": round(wait_seconds),
            "failed_last_hour": failed_1h,
        }

    return {"timestamp": now.isoformat(), "queues": queues_info}


@router.get("/dead-letter")
async def dead_letter_detail(
    user: dict = Depends(get_admin_user),
    limit: int = Query(20, ge=1, le=100),
):
    """Admin: view dead letter queue contents."""
    jobs = await db.dead_letter_jobs.find(
        {}, {"_id": 0}
    ).sort("dead_at", -1).limit(limit).to_list(limit)
    total = await db.dead_letter_jobs.count_documents({})
    return {"total": total, "jobs": jobs}


@router.get("/stuck-jobs")
async def stuck_jobs_detail(user: dict = Depends(get_admin_user)):
    """Admin: view jobs stuck in PROCESSING for too long."""
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    stuck = await db.genstudio_jobs.find(
        {"status": "PROCESSING", "startedAt": {"$lt": cutoff}},
        {"_id": 0, "id": 1, "jobType": 1, "userId": 1, "startedAt": 1, "queueType": 1},
    ).limit(50).to_list(50)
    return {"count": len(stuck), "jobs": stuck}
