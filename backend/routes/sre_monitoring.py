"""
SRE Monitoring Routes - Exposes performance metrics, index status, and system health
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from datetime import datetime, timezone
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, get_admin_user, logger
from services.database_indexes import get_index_status, create_all_indexes
from performance import metrics, cache, get_performance_report, run_health_checks

router = APIRouter(prefix="/sre", tags=["SRE Monitoring"])


@router.get("/status")
async def get_sre_status(admin: dict = Depends(get_admin_user)):
    """Get comprehensive SRE status including all subsystems"""
    try:
        # Get performance metrics
        perf_summary = metrics.get_summary()
        
        # Get cache stats
        cache_stats = cache.get_stats()
        
        # Get database index status
        index_status = await get_index_status(db)
        
        # Get job queue stats
        queue_stats = await _get_queue_stats()
        
        # Get dead letter queue count
        dlq_count = await db.dead_letter_queue.count_documents({"status": "pending_review"})
        
        return {
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "performance": {
                "uptime_seconds": perf_summary.get("uptime_seconds", 0),
                "total_requests": perf_summary.get("total_requests", 0),
                "error_rate_percent": perf_summary.get("error_rate_percent", 0),
                "avg_latency_ms": perf_summary.get("avg_latency_ms", 0),
                "requests_per_second": perf_summary.get("requests_per_second", 0)
            },
            "latency_distribution": perf_summary.get("latency_distribution", {}),
            "job_stats": perf_summary.get("job_stats", {}),
            "provider_stats": perf_summary.get("provider_stats", {}),
            "cache": cache_stats,
            "database": {
                "index_status": index_status,
                "collections_indexed": len(index_status)
            },
            "queues": queue_stats,
            "dead_letter_queue": {
                "pending_count": dlq_count,
                "status": "healthy" if dlq_count < 10 else "warning" if dlq_count < 50 else "critical"
            }
        }
    except Exception as e:
        logger.error(f"SRE status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def get_health_status():
    """Get system health status (public endpoint for monitoring)"""
    try:
        health = await run_health_checks()
        return health
    except Exception as e:
        return {
            "overall": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.get("/indexes")
async def get_database_indexes(admin: dict = Depends(get_admin_user)):
    """Get detailed database index information"""
    try:
        index_status = await get_index_status(db)
        return {
            "success": True,
            "indexes": index_status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/indexes/create")
async def create_database_indexes(admin: dict = Depends(get_admin_user)):
    """Manually trigger index creation"""
    try:
        report = await create_all_indexes(db)
        return {
            "success": True,
            "report": report,
            "message": f"Created {len(report.get('created', []))} indexes, {len(report.get('existing', []))} already exist"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance")
async def get_performance_metrics(admin: dict = Depends(get_admin_user)):
    """Get detailed performance report"""
    try:
        report = await get_performance_report()
        return {
            "success": True,
            "report": report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dlq")
async def get_dead_letter_queue(
    admin: dict = Depends(get_admin_user),
    limit: int = 50
):
    """Get items from dead letter queue"""
    try:
        items = await db.dead_letter_queue.find(
            {},
            {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        
        return {
            "success": True,
            "count": len(items),
            "items": items
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dlq/{item_id}/retry")
async def retry_dead_letter_item(
    item_id: str,
    admin: dict = Depends(get_admin_user)
):
    """Retry a dead letter queue item"""
    try:
        item = await db.dead_letter_queue.find_one({"id": item_id}, {"_id": 0})
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        
        # Re-queue the job
        job_data = item.get("job_data", {})
        job_id = item.get("job_id")
        
        # Update the original job to retry
        collection = _get_job_collection(item.get("job_type", ""))
        if collection:
            await db[collection].update_one(
                {"id": job_id},
                {
                    "$set": {
                        "status": "QUEUED",
                        "retryCount": 0,
                        "error": None,
                        "retriedFromDLQ": True,
                        "updatedAt": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
        
        # Mark DLQ item as retried
        await db.dead_letter_queue.update_one(
            {"id": item_id},
            {"$set": {
                "status": "retried",
                "retriedAt": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        return {
            "success": True,
            "message": f"Job {job_id} re-queued for processing"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fallbacks")
async def get_fallback_outputs(
    admin: dict = Depends(get_admin_user),
    limit: int = 50
):
    """Get recent fallback outputs generated for failed jobs"""
    try:
        fallbacks = await db.fallback_outputs.find(
            {},
            {"_id": 0}
        ).sort("createdAt", -1).limit(limit).to_list(limit)
        
        return {
            "success": True,
            "count": len(fallbacks),
            "fallbacks": fallbacks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _get_queue_stats() -> Dict[str, Any]:
    """Get statistics for all job queues"""
    stats = {}
    
    collections = ["genstudio_jobs", "storybook_jobs", "comix_jobs", "gif_jobs"]
    
    for collection in collections:
        try:
            queued = await db[collection].count_documents({"status": "QUEUED"})
            processing = await db[collection].count_documents({"status": "PROCESSING"})
            completed = await db[collection].count_documents({"status": "COMPLETED"})
            failed = await db[collection].count_documents({"status": "FAILED"})
            
            stats[collection] = {
                "queued": queued,
                "processing": processing,
                "completed": completed,
                "failed": failed,
                "total": queued + processing + completed + failed
            }
        except Exception as e:
            stats[collection] = {"error": str(e)}
    
    return stats


def _get_job_collection(job_type: str) -> str:
    """Map job type to collection name"""
    mapping = {
        "TEXT_TO_IMAGE": "genstudio_jobs",
        "TEXT_TO_VIDEO": "genstudio_jobs",
        "IMAGE_TO_VIDEO": "genstudio_jobs",
        "STORY_GENERATION": "genstudio_jobs",
        "REEL_GENERATION": "genstudio_jobs",
        "storybook": "storybook_jobs",
        "comix": "comix_jobs",
        "gif": "gif_jobs"
    }
    return mapping.get(job_type, "genstudio_jobs")
