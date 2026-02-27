"""
Worker System Admin Routes
Expose worker metrics and controls to admins
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user

router = APIRouter(prefix="/admin/workers", tags=["Admin Workers"])


def require_admin(user: dict):
    """Check if user is admin"""
    role = user.get("role", "").lower()
    if role not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/metrics")
async def get_worker_metrics(user: dict = Depends(get_current_user)):
    """Get all worker pool metrics"""
    require_admin(user)
    
    # Get latest metrics from DB
    metrics = await db.worker_metrics.find({}).sort("timestamp", -1).to_list(20)
    
    # Convert ObjectId and format
    formatted_metrics = []
    for m in metrics:
        m["_id"] = str(m["_id"])
        if "timestamp" in m:
            m["timestamp"] = m["timestamp"].isoformat() if hasattr(m["timestamp"], 'isoformat') else str(m["timestamp"])
        formatted_metrics.append(m)
    
    return {
        "pools": formatted_metrics,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/pools/{feature}")
async def get_pool_metrics(feature: str, user: dict = Depends(get_current_user)):
    """Get metrics for a specific feature pool"""
    require_admin(user)
    
    metrics = await db.worker_metrics.find_one(
        {"feature": feature},
        sort=[("timestamp", -1)]
    )
    
    if not metrics:
        raise HTTPException(status_code=404, detail=f"No metrics found for feature: {feature}")
    
    metrics["_id"] = str(metrics["_id"])
    if "timestamp" in metrics:
        metrics["timestamp"] = metrics["timestamp"].isoformat() if hasattr(metrics["timestamp"], 'isoformat') else str(metrics["timestamp"])
    
    return metrics


@router.get("/jobs/history")
async def get_job_history(
    feature: str = None,
    status: str = None,
    limit: int = 100,
    user: dict = Depends(get_current_user)
):
    """Get recent job history"""
    require_admin(user)
    
    query = {}
    if feature:
        query["feature"] = feature
    if status:
        query["status"] = status
    
    jobs = await db.worker_jobs.find(query).sort("created_at", -1).limit(limit).to_list(limit)
    
    for job in jobs:
        job["_id"] = str(job["_id"])
        for field in ["created_at", "started_at", "completed_at"]:
            if field in job and job[field]:
                job[field] = job[field].isoformat() if hasattr(job[field], 'isoformat') else str(job[field])
    
    return {"jobs": jobs, "count": len(jobs)}


@router.post("/pools/{feature}/scale")
async def scale_pool(
    feature: str,
    target_workers: int,
    user: dict = Depends(get_current_user)
):
    """Manually scale a worker pool"""
    require_admin(user)
    
    if target_workers < 1 or target_workers > 20:
        raise HTTPException(status_code=400, detail="Target workers must be between 1 and 20")
    
    # Log the scaling action
    await db.admin_audit_logs.insert_one({
        "action": "worker_scale",
        "feature": feature,
        "target_workers": target_workers,
        "admin_id": user["id"],
        "admin_email": user["email"],
        "timestamp": datetime.now(timezone.utc)
    })
    
    logger.info(f"Admin {user['email']} requested scale of {feature} to {target_workers} workers")
    
    return {
        "success": True,
        "message": f"Scaling request submitted for {feature}",
        "target_workers": target_workers
    }


@router.get("/load-balancer/status")
async def get_load_balancer_status(user: dict = Depends(get_current_user)):
    """Get load balancer status and configuration"""
    require_admin(user)
    
    # Get all pool metrics
    metrics = await db.worker_metrics.find({}).sort("timestamp", -1).to_list(50)
    
    # Calculate overall load
    total_workers = 0
    busy_workers = 0
    total_queue = 0
    
    pools_status = []
    for m in metrics:
        total_workers += m.get("workers_count", 0)
        total_queue += m.get("queue_size", 0)
        
        # Count busy workers from worker list
        workers = m.get("workers", [])
        busy = sum(1 for w in workers if w.get("status") == "busy")
        busy_workers += busy
        
        pools_status.append({
            "feature": m.get("feature"),
            "workers": m.get("workers_count", 0),
            "busy": busy,
            "queue": m.get("queue_size", 0),
            "utilization": round(busy / max(m.get("workers_count", 1), 1) * 100, 1)
        })
    
    overall_utilization = round(busy_workers / max(total_workers, 1) * 100, 1)
    
    return {
        "status": "healthy" if overall_utilization < 80 else "high_load" if overall_utilization < 95 else "critical",
        "total_workers": total_workers,
        "busy_workers": busy_workers,
        "overall_utilization": overall_utilization,
        "total_queue_size": total_queue,
        "pools": pools_status,
        "auto_scaling": {
            "enabled": True,
            "scale_up_threshold": 80,
            "scale_down_threshold": 30,
            "check_interval_seconds": 10
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/auto-scaling/toggle")
async def toggle_auto_scaling(
    enabled: bool,
    user: dict = Depends(get_current_user)
):
    """Enable or disable auto-scaling"""
    require_admin(user)
    
    # Store in config
    await db.system_config.update_one(
        {"key": "auto_scaling"},
        {"$set": {
            "enabled": enabled,
            "updated_by": user["email"],
            "updated_at": datetime.now(timezone.utc)
        }},
        upsert=True
    )
    
    logger.info(f"Admin {user['email']} {'enabled' if enabled else 'disabled'} auto-scaling")
    
    return {
        "success": True,
        "auto_scaling_enabled": enabled
    }
