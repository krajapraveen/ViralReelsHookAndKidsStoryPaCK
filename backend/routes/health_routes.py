"""
Production Health Check and Monitoring System
Implements health checks, alerts, and self-healing for production stability
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone, timedelta
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger

router = APIRouter(prefix="/health", tags=["Health"])

# Build info
BUILD_VERSION = os.environ.get("BUILD_VERSION", "preview-dev")
BUILD_COMMIT = os.environ.get("BUILD_COMMIT", "unknown")
BUILD_DATE = os.environ.get("BUILD_DATE", datetime.now(timezone.utc).isoformat())


@router.get("")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": BUILD_VERSION,
        "commit": BUILD_COMMIT
    }


@router.get("/detailed")
async def detailed_health_check():
    """Detailed health check with component status"""
    health = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": BUILD_VERSION,
        "commit": BUILD_COMMIT,
        "build_date": BUILD_DATE,
        "components": {}
    }
    
    # Check MongoDB
    try:
        await db.command("ping")
        health["components"]["database"] = {"status": "healthy", "type": "mongodb"}
    except Exception as e:
        health["components"]["database"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"
    
    # Check LLM availability
    try:
        from shared import LLM_AVAILABLE, EMERGENT_LLM_KEY
        health["components"]["llm"] = {
            "status": "healthy" if LLM_AVAILABLE and EMERGENT_LLM_KEY else "unavailable",
            "available": LLM_AVAILABLE,
            "key_configured": bool(EMERGENT_LLM_KEY)
        }
    except Exception as e:
        health["components"]["llm"] = {"status": "error", "error": str(e)}
    
    # Check worker pools
    try:
        from services.enhanced_worker_system import get_worker_manager
        worker_mgr = get_worker_manager()
        if worker_mgr:
            pools = await worker_mgr.get_all_pool_stats()
            health["components"]["workers"] = {
                "status": "healthy",
                "pools": len(pools),
                "total_workers": sum(p.get("current_workers", 0) for p in pools.values())
            }
        else:
            health["components"]["workers"] = {"status": "not_initialized"}
    except Exception as e:
        health["components"]["workers"] = {"status": "error", "error": str(e)}
    
    # Check recent error rate
    try:
        fifteen_min_ago = datetime.now(timezone.utc) - timedelta(minutes=15)
        error_count = await db.api_logs.count_documents({
            "timestamp": {"$gte": fifteen_min_ago.isoformat()},
            "status_code": {"$gte": 500}
        })
        total_requests = await db.api_logs.count_documents({
            "timestamp": {"$gte": fifteen_min_ago.isoformat()}
        })
        error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0
        
        health["components"]["error_rate"] = {
            "status": "healthy" if error_rate < 5 else "warning" if error_rate < 10 else "critical",
            "rate_15m": f"{error_rate:.2f}%",
            "errors": error_count,
            "total": total_requests
        }
    except Exception as e:
        health["components"]["error_rate"] = {"status": "unknown", "error": str(e)}
    
    # Check stuck jobs
    try:
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        stuck_jobs = await db.photo_to_comic_jobs.count_documents({
            "status": {"$in": ["QUEUED", "PROCESSING"]},
            "createdAt": {"$lt": one_hour_ago.isoformat()}
        })
        health["components"]["job_queue"] = {
            "status": "healthy" if stuck_jobs == 0 else "warning",
            "stuck_jobs": stuck_jobs
        }
    except Exception as e:
        health["components"]["job_queue"] = {"status": "unknown", "error": str(e)}
    
    return health


@router.get("/readiness")
async def readiness_check():
    """Kubernetes readiness probe - returns 200 if ready to serve traffic"""
    try:
        # Check MongoDB connection
        await db.command("ping")
        
        # Check LLM availability
        from shared import LLM_AVAILABLE
        
        return {
            "ready": True,
            "database": "connected",
            "llm": "available" if LLM_AVAILABLE else "unavailable"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Not ready: {str(e)}")


@router.get("/liveness")
async def liveness_check():
    """Kubernetes liveness probe - returns 200 if process is alive"""
    return {"alive": True, "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/version")
async def get_version():
    """Get current build version and deployment info"""
    return {
        "version": BUILD_VERSION,
        "commit": BUILD_COMMIT,
        "build_date": BUILD_DATE,
        "environment": os.environ.get("ENVIRONMENT", "preview"),
        "frontend_url": os.environ.get("FRONTEND_URL", "unknown")
    }


@router.post("/self-heal")
async def trigger_self_healing():
    """Manually trigger self-healing checks"""
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actions": []
    }
    
    # Requeue stuck jobs
    try:
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        stuck_jobs = await db.photo_to_comic_jobs.find({
            "status": {"$in": ["QUEUED", "PROCESSING"]},
            "createdAt": {"$lt": one_hour_ago.isoformat()}
        }).to_list(100)
        
        for job in stuck_jobs:
            await db.photo_to_comic_jobs.update_one(
                {"id": job["id"]},
                {"$set": {"status": "FAILED", "error": "Job timed out after 1 hour"}}
            )
            results["actions"].append(f"Marked stuck job {job['id']} as FAILED")
    except Exception as e:
        results["actions"].append(f"Error requeuing stuck jobs: {str(e)}")
    
    # Clean up expired downloads
    try:
        from services.download_expiry_service import get_download_service
        download_service = get_download_service(db)
        cleaned = await download_service.cleanup_expired()
        results["actions"].append(f"Cleaned {cleaned} expired downloads")
    except Exception as e:
        results["actions"].append(f"Error cleaning downloads: {str(e)}")
    
    return results
