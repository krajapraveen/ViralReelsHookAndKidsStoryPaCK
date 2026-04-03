"""
Production Metrics — Validation Phase Dashboard
Tracks real job-level data for Brand Kit Generator and Photo to Comic.
No synthetic data. Shows "Not enough data" when insufficient.
"""
from fastapi import APIRouter, Depends, Query
from datetime import datetime, timezone, timedelta
import logging

from shared import db, get_admin_user

logger = logging.getLogger("creatorstudio.production_metrics")
router = APIRouter(prefix="/production-metrics", tags=["Production Metrics"])


def _now():
    return datetime.now(timezone.utc)


def _ago(**kwargs):
    return _now() - timedelta(**kwargs)


def _safe_pct(num, den):
    if not den:
        return None
    return round(num / den * 100, 1)


def _safe_avg(values):
    if not values:
        return None
    return round(sum(values) / len(values), 1)


# ═══════════════════════════════════════════════════════════════
# OVERVIEW — Both features combined
# ═══════════════════════════════════════════════════════════════

@router.get("/overview")
async def get_overview(days: int = Query(30, ge=1, le=365), admin: dict = Depends(get_admin_user)):
    cutoff = _ago(days=days).isoformat()

    # Brand Kit counts
    bk_total = await db.brand_kit_jobs.count_documents({"created_at": {"$gte": cutoff}})
    bk_success = await db.brand_kit_jobs.count_documents({
        "created_at": {"$gte": cutoff},
        "status": {"$in": ["READY", "PARTIAL_READY"]}
    })
    bk_failed = await db.brand_kit_jobs.count_documents({
        "created_at": {"$gte": cutoff},
        "status": "FAILED"
    })

    # Photo to Comic counts
    ptc_total = await db.photo_to_comic_jobs.count_documents({"createdAt": {"$gte": cutoff}})
    ptc_success = await db.photo_to_comic_jobs.count_documents({
        "createdAt": {"$gte": cutoff},
        "status": "COMPLETED"
    })
    ptc_failed = await db.photo_to_comic_jobs.count_documents({
        "createdAt": {"$gte": cutoff},
        "status": "FAILED"
    })

    total = bk_total + ptc_total
    success = bk_success + ptc_success
    failed = bk_failed + ptc_failed

    # Credits consumed
    bk_credits_pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}, "status": {"$in": ["READY", "PARTIAL_READY", "FAILED"]}}},
        {"$group": {"_id": None, "total": {"$sum": "$credits_charged"}}}
    ]
    bk_credits_result = await db.brand_kit_jobs.aggregate(bk_credits_pipeline).to_list(1)
    bk_credits = bk_credits_result[0]["total"] if bk_credits_result else 0

    ptc_credits_pipeline = [
        {"$match": {"createdAt": {"$gte": cutoff}}},
        {"$group": {"_id": None, "total": {"$sum": "$cost"}}}
    ]
    ptc_credits_result = await db.photo_to_comic_jobs.aggregate(ptc_credits_pipeline).to_list(1)
    ptc_credits = ptc_credits_result[0]["total"] if ptc_credits_result else 0

    # Downloads
    bk_downloads = await db.production_events.count_documents({
        "event": "download",
        "feature": "brand_kit",
        "timestamp": {"$gte": cutoff}
    })
    ptc_downloads = await db.photo_to_comic_jobs.count_documents({
        "createdAt": {"$gte": cutoff},
        "downloaded": True
    })

    # Jobs over time (daily buckets for the period)
    bk_daily = await _daily_counts(db.brand_kit_jobs, "created_at", cutoff, days)
    ptc_daily = await _daily_counts(db.photo_to_comic_jobs, "createdAt", cutoff, days)

    return {
        "period_days": days,
        "totals": {
            "jobs": total,
            "success": success,
            "failed": failed,
            "success_rate": _safe_pct(success, total),
            "credits_consumed": bk_credits + ptc_credits,
            "downloads": bk_downloads + ptc_downloads,
        },
        "brand_kit": {
            "jobs": bk_total,
            "success": bk_success,
            "failed": bk_failed,
            "success_rate": _safe_pct(bk_success, bk_total),
            "credits": bk_credits,
            "downloads": bk_downloads,
        },
        "photo_to_comic": {
            "jobs": ptc_total,
            "success": ptc_success,
            "failed": ptc_failed,
            "success_rate": _safe_pct(ptc_success, ptc_total),
            "credits": ptc_credits,
            "downloads": ptc_downloads,
        },
        "daily_trend": {
            "brand_kit": bk_daily,
            "photo_to_comic": ptc_daily,
        },
        "target": {"goal": 200, "current": total, "progress_pct": _safe_pct(total, 200)},
    }


async def _daily_counts(collection, date_field, cutoff, days):
    """Aggregate daily job counts."""
    pipeline = [
        {"$match": {date_field: {"$gte": cutoff}}},
        {"$addFields": {"_date_str": {"$substr": [f"${date_field}", 0, 10]}}},
        {"$group": {"_id": "$_date_str", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    results = await collection.aggregate(pipeline).to_list(days + 1)
    return [{"date": r["_id"], "count": r["count"]} for r in results]


# ═══════════════════════════════════════════════════════════════
# BRAND KIT GENERATOR — Detailed metrics
# ═══════════════════════════════════════════════════════════════

@router.get("/brand-kit")
async def get_brand_kit_metrics(days: int = Query(30, ge=1, le=365), admin: dict = Depends(get_admin_user)):
    cutoff = _ago(days=days).isoformat()

    total = await db.brand_kit_jobs.count_documents({"created_at": {"$gte": cutoff}})
    ready = await db.brand_kit_jobs.count_documents({"created_at": {"$gte": cutoff}, "status": "READY"})
    partial = await db.brand_kit_jobs.count_documents({"created_at": {"$gte": cutoff}, "status": "PARTIAL_READY"})
    failed = await db.brand_kit_jobs.count_documents({"created_at": {"$gte": cutoff}, "status": "FAILED"})
    generating = await db.brand_kit_jobs.count_documents({"created_at": {"$gte": cutoff}, "status": "GENERATING"})

    # Mode split
    fast_count = await db.brand_kit_jobs.count_documents({"created_at": {"$gte": cutoff}, "mode": "fast"})
    pro_count = await db.brand_kit_jobs.count_documents({"created_at": {"$gte": cutoff}, "mode": "pro"})

    # Timing: avg total generation time & time-to-first-artifact
    completed_jobs = await db.brand_kit_jobs.find(
        {"created_at": {"$gte": cutoff}, "status": {"$in": ["READY", "PARTIAL_READY"]}, "completed_at": {"$exists": True}},
        {"_id": 0, "created_at": 1, "completed_at": 1, "artifacts": 1, "mode": 1}
    ).to_list(500)

    total_times_ms = []
    first_artifact_times_ms = []
    artifact_latencies = {}
    artifact_statuses = {}

    for job in completed_jobs:
        try:
            created = datetime.fromisoformat(job["created_at"])
            completed = datetime.fromisoformat(job["completed_at"])
            total_ms = (completed - created).total_seconds() * 1000
            total_times_ms.append(total_ms)
        except Exception:
            pass

        # Per-artifact data
        for art_type, art in job.get("artifacts", {}).items():
            lat = art.get("latency_ms")
            status = art.get("status", "UNKNOWN")

            if art_type not in artifact_latencies:
                artifact_latencies[art_type] = []
                artifact_statuses[art_type] = {"READY": 0, "FALLBACK_READY": 0, "FAILED": 0}

            if lat:
                artifact_latencies[art_type].append(lat)
            if status in artifact_statuses[art_type]:
                artifact_statuses[art_type][status] += 1

        # Time to first useful artifact = min latency among READY artifacts
        ready_latencies = [
            art.get("latency_ms", 999999)
            for art in job.get("artifacts", {}).values()
            if art.get("status") in ("READY", "FALLBACK_READY") and art.get("latency_ms")
        ]
        if ready_latencies:
            first_artifact_times_ms.append(min(ready_latencies))

    # Per-artifact summary
    artifact_metrics = {}
    for art_type in artifact_latencies:
        lats = artifact_latencies[art_type]
        statuses = artifact_statuses[art_type]
        total_art = sum(statuses.values())
        artifact_metrics[art_type] = {
            "avg_latency_ms": _safe_avg(lats),
            "p50_latency_ms": sorted(lats)[len(lats) // 2] if lats else None,
            "p95_latency_ms": sorted(lats)[int(len(lats) * 0.95)] if lats else None,
            "success_rate": _safe_pct(statuses["READY"], total_art),
            "fallback_rate": _safe_pct(statuses["FALLBACK_READY"], total_art),
            "failure_rate": _safe_pct(statuses["FAILED"], total_art),
            "total": total_art,
        }

    # Downloads by type
    pdf_downloads = await db.production_events.count_documents({
        "event": "download", "feature": "brand_kit", "format": "pdf", "timestamp": {"$gte": cutoff}
    })
    zip_downloads = await db.production_events.count_documents({
        "event": "download", "feature": "brand_kit", "format": "zip", "timestamp": {"$gte": cutoff}
    })

    # Regenerate rate: users with >1 job
    regen_pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {"_id": "$userId", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}},
        {"$count": "regen_users"}
    ]
    regen_result = await db.brand_kit_jobs.aggregate(regen_pipeline).to_list(1)
    regen_users = regen_result[0]["regen_users"] if regen_result else 0

    unique_users_pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {"_id": "$userId"}},
        {"$count": "total"}
    ]
    unique_result = await db.brand_kit_jobs.aggregate(unique_users_pipeline).to_list(1)
    unique_users = unique_result[0]["total"] if unique_result else 0

    # Industry distribution
    industry_pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {"_id": "$brief.industry", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    industry_dist = await db.brand_kit_jobs.aggregate(industry_pipeline).to_list(10)

    return {
        "period_days": days,
        "total_jobs": total,
        "status_breakdown": {
            "ready": ready,
            "partial_ready": partial,
            "failed": failed,
            "generating": generating,
        },
        "success_rate": _safe_pct(ready + partial, total),
        "failure_rate": _safe_pct(failed, total),
        "mode_split": {
            "fast": fast_count,
            "pro": pro_count,
            "fast_pct": _safe_pct(fast_count, total),
            "pro_pct": _safe_pct(pro_count, total),
        },
        "timing": {
            "avg_total_ms": _safe_avg(total_times_ms),
            "avg_time_to_first_artifact_ms": _safe_avg(first_artifact_times_ms),
            "p50_total_ms": sorted(total_times_ms)[len(total_times_ms) // 2] if total_times_ms else None,
            "p95_total_ms": sorted(total_times_ms)[int(len(total_times_ms) * 0.95)] if total_times_ms else None,
        },
        "artifact_metrics": artifact_metrics,
        "downloads": {
            "pdf": pdf_downloads,
            "zip": zip_downloads,
            "total": pdf_downloads + zip_downloads,
            "download_rate": _safe_pct(pdf_downloads + zip_downloads, ready + partial),
        },
        "regenerate": {
            "users_with_multiple_jobs": regen_users,
            "unique_users": unique_users,
            "regenerate_rate": _safe_pct(regen_users, unique_users),
        },
        "industry_distribution": [{"industry": r["_id"] or "Unknown", "count": r["count"]} for r in industry_dist],
    }


# ═══════════════════════════════════════════════════════════════
# PHOTO TO COMIC — Detailed metrics
# ═══════════════════════════════════════════════════════════════

@router.get("/photo-to-comic")
async def get_photo_to_comic_metrics(days: int = Query(30, ge=1, le=365), admin: dict = Depends(get_admin_user)):
    cutoff = _ago(days=days).isoformat()

    total = await db.photo_to_comic_jobs.count_documents({"createdAt": {"$gte": cutoff}})
    completed = await db.photo_to_comic_jobs.count_documents({"createdAt": {"$gte": cutoff}, "status": "COMPLETED"})
    failed = await db.photo_to_comic_jobs.count_documents({"createdAt": {"$gte": cutoff}, "status": "FAILED"})
    processing = await db.photo_to_comic_jobs.count_documents({"createdAt": {"$gte": cutoff}, "status": {"$in": ["QUEUED", "PROCESSING"]}})

    # Type split (avatar vs strip)
    avatar_count = await db.photo_to_comic_jobs.count_documents({"createdAt": {"$gte": cutoff}, "type": "COMIC_AVATAR"})
    strip_count = await db.photo_to_comic_jobs.count_documents({"createdAt": {"$gte": cutoff}, "type": "COMIC_STRIP"})

    # Downloads
    downloaded = await db.photo_to_comic_jobs.count_documents({"createdAt": {"$gte": cutoff}, "downloaded": True})

    # Style popularity
    style_pipeline = [
        {"$match": {"createdAt": {"$gte": cutoff}}},
        {"$group": {"_id": "$style", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    style_dist = await db.photo_to_comic_jobs.aggregate(style_pipeline).to_list(10)

    # Timing: avg generation time (createdAt → updatedAt for completed jobs)
    completed_jobs = await db.photo_to_comic_jobs.find(
        {"createdAt": {"$gte": cutoff}, "status": "COMPLETED"},
        {"_id": 0, "createdAt": 1, "updatedAt": 1, "type": 1, "cost": 1}
    ).to_list(500)

    latencies_ms = []
    avatar_latencies = []
    strip_latencies = []
    for job in completed_jobs:
        try:
            created = datetime.fromisoformat(job["createdAt"])
            updated = datetime.fromisoformat(job["updatedAt"])
            lat = (updated - created).total_seconds() * 1000
            latencies_ms.append(lat)
            if job.get("type") == "COMIC_AVATAR":
                avatar_latencies.append(lat)
            else:
                strip_latencies.append(lat)
        except Exception:
            pass

    # Credits consumed
    credits_pipeline = [
        {"$match": {"createdAt": {"$gte": cutoff}}},
        {"$group": {"_id": None, "total": {"$sum": "$cost"}}}
    ]
    credits_result = await db.photo_to_comic_jobs.aggregate(credits_pipeline).to_list(1)
    total_credits = credits_result[0]["total"] if credits_result else 0

    # Unique users
    users_pipeline = [
        {"$match": {"createdAt": {"$gte": cutoff}}},
        {"$group": {"_id": "$userId"}},
        {"$count": "total"}
    ]
    users_result = await db.photo_to_comic_jobs.aggregate(users_pipeline).to_list(1)
    unique_users = users_result[0]["total"] if users_result else 0

    # Regenerate rate
    regen_pipeline = [
        {"$match": {"createdAt": {"$gte": cutoff}}},
        {"$group": {"_id": "$userId", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}},
        {"$count": "regen_users"}
    ]
    regen_result = await db.photo_to_comic_jobs.aggregate(regen_pipeline).to_list(1)
    regen_users = regen_result[0]["regen_users"] if regen_result else 0

    return {
        "period_days": days,
        "total_jobs": total,
        "status_breakdown": {
            "completed": completed,
            "failed": failed,
            "processing": processing,
        },
        "success_rate": _safe_pct(completed, total),
        "failure_rate": _safe_pct(failed, total),
        "type_split": {
            "avatar": avatar_count,
            "strip": strip_count,
            "avatar_pct": _safe_pct(avatar_count, total),
            "strip_pct": _safe_pct(strip_count, total),
        },
        "timing": {
            "avg_latency_ms": _safe_avg(latencies_ms),
            "p50_latency_ms": sorted(latencies_ms)[len(latencies_ms) // 2] if latencies_ms else None,
            "p95_latency_ms": sorted(latencies_ms)[int(len(latencies_ms) * 0.95)] if latencies_ms else None,
            "avatar_avg_ms": _safe_avg(avatar_latencies),
            "strip_avg_ms": _safe_avg(strip_latencies),
        },
        "downloads": {
            "downloaded": downloaded,
            "download_rate": _safe_pct(downloaded, completed),
        },
        "credits_consumed": total_credits,
        "users": {
            "unique": unique_users,
            "regen_users": regen_users,
            "regenerate_rate": _safe_pct(regen_users, unique_users),
        },
        "style_distribution": [{"style": r["_id"] or "Unknown", "count": r["count"]} for r in style_dist],
    }


# ═══════════════════════════════════════════════════════════════
# JOB LOG — Paginated list of all jobs
# ═══════════════════════════════════════════════════════════════

@router.get("/jobs")
async def get_job_log(
    feature: str = Query("all", pattern="^(all|brand_kit|photo_to_comic)$"),
    status: str = Query("all"),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    admin: dict = Depends(get_admin_user)
):
    skip = (page - 1) * limit
    jobs = []

    if feature in ("all", "brand_kit"):
        bk_query = {}
        if status != "all":
            bk_query["status"] = status.upper()
        bk_jobs = await db.brand_kit_jobs.find(
            bk_query,
            {"_id": 0, "artifacts": 0}
        ).sort("created_at", -1).to_list(500)

        for j in bk_jobs:
            jobs.append({
                "job_id": j.get("id"),
                "feature": "brand_kit",
                "user_id": j.get("userId"),
                "status": j.get("status"),
                "mode": j.get("mode"),
                "credits": j.get("credits_charged"),
                "created_at": j.get("created_at"),
                "completed_at": j.get("completed_at"),
                "total_artifacts": j.get("total_artifacts"),
                "completed_artifacts": j.get("completed_artifacts"),
                "business_name": j.get("brief", {}).get("business_name"),
                "industry": j.get("brief", {}).get("industry"),
            })

    if feature in ("all", "photo_to_comic"):
        ptc_query = {}
        if status != "all":
            ptc_query["status"] = status.upper()
        ptc_jobs = await db.photo_to_comic_jobs.find(
            ptc_query,
            {"_id": 0, "panels": 0, "source_photo": 0, "sourcePhoto": 0}
        ).sort("createdAt", -1).to_list(500)

        for j in ptc_jobs:
            jobs.append({
                "job_id": j.get("id"),
                "feature": "photo_to_comic",
                "user_id": j.get("userId"),
                "status": j.get("status"),
                "mode": j.get("type"),
                "credits": j.get("cost"),
                "created_at": j.get("createdAt"),
                "completed_at": j.get("updatedAt"),
                "downloaded": j.get("downloaded"),
                "style": j.get("style"),
            })

    # Sort all by created_at descending
    jobs.sort(key=lambda x: x.get("created_at") or "", reverse=True)

    total = len(jobs)
    paged = jobs[skip:skip + limit]

    return {
        "jobs": paged,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if total else 0,
    }


# ═══════════════════════════════════════════════════════════════
# EVENT TRACKING — Record download events
# ═══════════════════════════════════════════════════════════════

@router.post("/track-event")
async def track_event(event_data: dict, user: dict = Depends(get_admin_user)):
    """Internal event tracking for production metrics."""
    await db.production_events.insert_one({
        "event": event_data.get("event"),
        "feature": event_data.get("feature"),
        "format": event_data.get("format"),
        "job_id": event_data.get("job_id"),
        "user_id": user.get("id"),
        "timestamp": _now().isoformat(),
    })
    return {"success": True}
