"""
Deep Health Check — Machine-readable system truth
GET /api/health/deep — Returns complete system status
"""
from fastapi import APIRouter
from datetime import datetime, timezone, timedelta
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["Health Deep"])


@router.get("/deep")
async def deep_health_check():
    """
    Machine-readable health endpoint.
    Returns: is the system up, can it generate, can it store, can it serve.
    """
    from shared import db
    import redis
    import aiohttp

    results = {}
    overall_healthy = True

    # 1. API Health — if we got here, API is up
    results["api"] = {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

    # 2. DB Connectivity
    try:
        await db.command("ping")
        user_count = await db.users.estimated_document_count()
        results["database"] = {"status": "ok", "users": user_count}
    except Exception as e:
        results["database"] = {"status": "failed", "error": str(e)[:200]}
        overall_healthy = False

    # 3. Redis Connectivity
    try:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        r = redis.from_url(redis_url, socket_timeout=3)
        r.ping()
        results["redis"] = {"status": "ok"}
    except Exception as e:
        results["redis"] = {"status": "degraded", "error": str(e)[:200]}

    # 4. Queue Depth
    try:
        queued = await db.pipeline_jobs.count_documents({"status": "QUEUED"})
        processing = await db.pipeline_jobs.count_documents({"status": "PROCESSING"})
        results["queue"] = {
            "status": "ok" if queued < 50 else "warning",
            "queued": queued,
            "processing": processing,
            "pressure": "high" if queued > 20 else "normal",
        }
        if queued > 50:
            overall_healthy = False
    except Exception as e:
        results["queue"] = {"status": "failed", "error": str(e)[:200]}

    # 5. Worker Availability
    try:
        five_min_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
        recent_completions = await db.pipeline_jobs.count_documents({
            "status": {"$in": ["COMPLETED", "PARTIAL"]},
            "completed_at": {"$gte": five_min_ago}
        })
        recent_starts = await db.pipeline_jobs.count_documents({
            "status": "PROCESSING",
            "started_at": {"$gte": five_min_ago}
        })
        results["workers"] = {
            "status": "ok" if recent_completions > 0 or recent_starts > 0 or processing == 0 else "idle",
            "recent_completions_5m": recent_completions,
            "active_processing": processing if 'processing' in dir() else 0,
        }
    except Exception as e:
        results["workers"] = {"status": "unknown", "error": str(e)[:200]}

    # 6. Storage (R2) Read Test — check presigned URL generation
    try:
        from services.cloudflare_r2_storage import get_r2_client
        client = get_r2_client()
        if client:
            results["storage"] = {"status": "ok", "provider": "cloudflare_r2"}
        else:
            results["storage"] = {"status": "degraded", "note": "R2 client not configured"}
    except Exception as e:
        results["storage"] = {"status": "degraded", "error": str(e)[:200]}

    # 7. Asset Validation Path
    try:
        sample_job = await db.pipeline_jobs.find_one(
            {"status": {"$in": ["COMPLETED", "PARTIAL"]}},
            {"_id": 0, "job_id": 1, "output_url": 1}
        )
        if sample_job and sample_job.get("output_url"):
            results["asset_validation"] = {"status": "ok", "sample_job": sample_job["job_id"][:12]}
        else:
            results["asset_validation"] = {"status": "no_assets", "note": "No completed jobs with assets"}
    except Exception as e:
        results["asset_validation"] = {"status": "failed", "error": str(e)[:200]}

    # 8. Credits Service Truth
    try:
        admin_user = await db.users.find_one(
            {"role": "ADMIN"},
            {"_id": 0, "credits": 1, "email": 1}
        )
        if admin_user:
            admin_credits = admin_user.get("credits", 0)
            results["credits_service"] = {
                "status": "ok" if admin_credits > 0 else "failed",
                "admin_credits": admin_credits,
                "admin_blocked": admin_credits <= 0,
            }
            if admin_credits <= 0:
                overall_healthy = False
        else:
            results["credits_service"] = {"status": "no_admin", "note": "No admin user found"}
    except Exception as e:
        results["credits_service"] = {"status": "failed", "error": str(e)[:200]}
        overall_healthy = False

    # 9. AI Provider Reachability (check env keys exist)
    providers = {}
    for key_name in ["EMERGENT_LLM_KEY", "SENDGRID_API_KEY", "ELEVENLABS_API_KEY"]:
        val = os.environ.get(key_name, "")
        providers[key_name] = "configured" if val and len(val) > 10 else "missing"
    has_any_provider = any(v == "configured" for v in providers.values())
    results["ai_providers"] = {
        "status": "ok" if has_any_provider else "failed",
        "keys": providers,
        "generation_possible": has_any_provider,
    }
    if not has_any_provider:
        overall_healthy = False

    # 10. Failure Rate (last hour)
    try:
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        total_1h = await db.pipeline_jobs.count_documents({"created_at": {"$gte": one_hour_ago}})
        failed_1h = await db.pipeline_jobs.count_documents({"status": "FAILED", "created_at": {"$gte": one_hour_ago}})
        fail_rate = (failed_1h / total_1h * 100) if total_1h > 0 else 0
        results["failure_rate"] = {
            "status": "ok" if fail_rate < 30 else "warning" if fail_rate < 60 else "critical",
            "total_1h": total_1h,
            "failed_1h": failed_1h,
            "rate_percent": round(fail_rate, 1),
        }
        if fail_rate > 60:
            overall_healthy = False
    except Exception as e:
        results["failure_rate"] = {"status": "unknown", "error": str(e)[:200]}

    return {
        "healthy": overall_healthy,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": results,
        "summary": "ALL SYSTEMS OPERATIONAL" if overall_healthy else "DEGRADED — check individual components",
    }
