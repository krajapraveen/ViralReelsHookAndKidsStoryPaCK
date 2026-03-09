"""
Job Queue API Routes
Provides endpoints for job submission, status tracking, and queue management
"""
import os
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from shared import db, get_current_user, get_admin_user
from services.job_queue_service import get_job_queue, JobPriority

router = APIRouter(prefix="/jobs", tags=["Job Queue"])

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class JobSubmitRequest(BaseModel):
    job_type: str
    payload: dict
    priority: str = "normal"  # high, normal, low

class JobStatusResponse(BaseModel):
    success: bool
    job: Optional[dict] = None
    error: Optional[str] = None

# =============================================================================
# JOB ENDPOINTS
# =============================================================================

@router.post("/submit")
async def submit_job(
    request: JobSubmitRequest,
    current_user: dict = Depends(get_current_user)
):
    """Submit a new job to the queue"""
    queue = get_job_queue()
    
    user_id = current_user.get("id") or str(current_user.get("_id"))
    
    # Map priority string to enum
    priority_map = {
        "high": JobPriority.HIGH,
        "normal": JobPriority.NORMAL,
        "low": JobPriority.LOW
    }
    priority = priority_map.get(request.priority.lower(), JobPriority.NORMAL)
    
    job_id = await queue.submit_job(
        job_type=request.job_type,
        payload=request.payload,
        user_id=user_id,
        priority=priority
    )
    
    return {
        "success": True,
        "job_id": job_id,
        "message": "Job submitted successfully"
    }

@router.get("/status/{job_id}")
async def get_job_status(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get the status of a job"""
    queue = get_job_queue()
    
    status = await queue.get_job_status(job_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Verify user owns this job (unless admin)
    user_id = current_user.get("id") or str(current_user.get("_id"))
    if current_user.get("role") != "ADMIN":
        job = queue.jobs.get(job_id)
        if job and job.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to view this job")
    
    return {
        "success": True,
        "job": status
    }

@router.post("/cancel/{job_id}")
async def cancel_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Cancel a pending or queued job"""
    queue = get_job_queue()
    
    # Verify user owns this job
    user_id = current_user.get("id") or str(current_user.get("_id"))
    job = queue.jobs.get(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if current_user.get("role") != "ADMIN" and job.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this job")
    
    cancelled = await queue.cancel_job(job_id)
    
    if not cancelled:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled (already processing or completed)")
    
    return {
        "success": True,
        "message": "Job cancelled successfully"
    }

@router.get("/my-jobs")
async def get_my_jobs(
    limit: int = Query(default=20, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Get current user's jobs"""
    queue = get_job_queue()
    
    user_id = current_user.get("id") or str(current_user.get("_id"))
    jobs = queue.get_user_jobs(user_id, limit)
    
    return {
        "success": True,
        "jobs": jobs,
        "count": len(jobs)
    }

# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================

@router.get("/admin/stats")
async def get_queue_stats(
    current_user: dict = Depends(get_admin_user)
):
    """Get job queue statistics (admin only)"""
    queue = get_job_queue()
    stats = queue.get_stats()
    
    return {
        "success": True,
        "stats": stats,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.get("/admin/all")
async def get_all_jobs(
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    current_user: dict = Depends(get_admin_user)
):
    """Get all jobs (admin only)"""
    queue = get_job_queue()
    
    jobs = list(queue.jobs.values())
    
    # Filter by status if provided
    if status:
        jobs = [j for j in jobs if j.status.value == status]
    
    # Filter by type if provided
    if job_type:
        jobs = [j for j in jobs if j.job_type == job_type]
    
    # Sort by created_at desc
    jobs.sort(key=lambda j: j.created_at, reverse=True)
    
    return {
        "success": True,
        "jobs": [
            {
                "job_id": j.job_id,
                "job_type": j.job_type,
                "user_id": j.user_id,
                "status": j.status.value,
                "progress": j.progress,
                "created_at": j.created_at.isoformat(),
                "error": j.error
            }
            for j in jobs[:limit]
        ],
        "total": len(jobs)
    }

@router.post("/admin/retry/{job_id}")
async def retry_job(
    job_id: str,
    current_user: dict = Depends(get_admin_user)
):
    """Retry a failed job (admin only)"""
    queue = get_job_queue()
    
    job = queue.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status.value != "failed":
        raise HTTPException(status_code=400, detail="Only failed jobs can be retried")
    
    # Reset job for retry
    job.retries = 0
    job.error = None
    job.status = JobPriority.NORMAL
    await queue.queues[job.priority].put(job_id)
    
    return {
        "success": True,
        "message": "Job queued for retry"
    }
