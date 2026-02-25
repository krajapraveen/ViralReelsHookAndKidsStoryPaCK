"""
CreatorStudio AI - Recovery UI API
==================================
API endpoints for user-facing recovery features.

Features:
- Job status and recovery
- Retry functionality
- Fallback options
- Download recovery
- Payment status
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timezone, timedelta
from typing import Optional
from pydantic import BaseModel
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user
from services.self_healing_core import (
    metrics, CorrelationContext, generate_correlation_id
)
from services.job_recovery_service import (
    JobSubmissionService, RetryTokenService, Job, JobState
)
from services.download_recovery_service import (
    DownloadRecoveryService, SignedUrlService, PreviewRecoveryService
)
from services.payment_recovery_service import Payment, PaymentState

router = APIRouter(prefix="/recovery", tags=["Recovery UI"])


# ============================================
# REQUEST MODELS
# ============================================

class RetryRequest(BaseModel):
    job_id: Optional[str] = None
    retry_token: Optional[str] = None


class DownloadRecoveryRequest(BaseModel):
    url: str
    error_code: int = 403


class PreviewFallbackRequest(BaseModel):
    content_id: str
    content_type: str


# ============================================
# JOB RECOVERY ENDPOINTS
# ============================================

@router.get("/job/{job_id}")
async def get_job_recovery_status(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get job status with recovery options
    """
    user_id = str(current_user["_id"])
    
    status = await JobSubmissionService.get_job_status(job_id, user_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Build recovery options based on status
    recovery_options = []
    
    if status["status"] in ["failed", "fallback"]:
        # Get retry token if available
        retry_token = await db.retry_tokens.find_one({
            "job_id": job_id,
            "user_id": user_id,
            "used": False,
            "expires_at": {"$gt": datetime.now(timezone.utc)}
        })
        
        if retry_token:
            recovery_options.append({
                "type": "retry",
                "label": "Retry Generation",
                "action": "retry",
                "token": retry_token["token"],
                "credits_required": 0  # Already paid
            })
        
        # Fallback option if available
        if status.get("fallback_result"):
            recovery_options.append({
                "type": "use_fallback",
                "label": "Use Alternative Output",
                "action": "accept_fallback",
                "fallback_type": status["fallback_result"].get("type", "fallback")
            })
        
        # Contact support option
        recovery_options.append({
            "type": "support",
            "label": "Contact Support",
            "action": "open_support",
            "reference_id": job_id
        })
    
    elif status["status"] == "processing":
        # Show resume option if stuck
        job_data = await db.jobs.find_one({"job_id": job_id})
        if job_data:
            created_at = job_data.get("created_at")
            if created_at and (datetime.now(timezone.utc) - created_at).total_seconds() > 300:
                recovery_options.append({
                    "type": "check_status",
                    "label": "Check Status",
                    "action": "refresh",
                    "message": "This job is taking longer than expected"
                })
    
    return {
        "job_id": job_id,
        "status": status["status"],
        "progress": status.get("progress", 0),
        "result_url": status.get("result_url"),
        "error": status.get("error"),
        "fallback_available": status.get("fallback_result") is not None,
        "recovery_options": recovery_options,
        "created_at": status.get("created_at"),
        "completed_at": status.get("completed_at")
    }


@router.post("/job/retry")
async def retry_job(
    request: RetryRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Retry a failed job using retry token or job_id
    """
    user_id = str(current_user["_id"])
    
    if request.retry_token:
        # Use retry token
        job_params = await RetryTokenService.use_retry_token(request.retry_token, user_id)
        
        if not job_params:
            raise HTTPException(
                status_code=400, 
                detail="Invalid or expired retry token"
            )
        
        # Re-submit job
        result = await JobSubmissionService.submit_job(
            user_id=user_id,
            job_type=job_params["job_type"],
            params=job_params["params"],
            credits_required=0  # Already paid
        )
        
        return {
            "success": True,
            "new_job_id": result["job_id"],
            "message": "Job resubmitted successfully"
        }
    
    elif request.job_id:
        # Get original job and create retry token
        job = await db.jobs.find_one({"job_id": request.job_id, "user_id": user_id})
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job["state"] not in ["failed", "fallback"]:
            raise HTTPException(
                status_code=400, 
                detail="Job is not in a retryable state"
            )
        
        # Create retry token and return
        retry_token = await RetryTokenService.create_retry_token(request.job_id, user_id)
        
        return {
            "success": True,
            "retry_token": retry_token,
            "message": "Use this token to retry",
            "expires_in_hours": 24
        }
    
    raise HTTPException(status_code=400, detail="Provide job_id or retry_token")


@router.post("/job/{job_id}/accept-fallback")
async def accept_fallback(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Accept fallback output for a failed job
    """
    user_id = str(current_user["_id"])
    
    job = await db.jobs.find_one({"job_id": job_id, "user_id": user_id})
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if not job.get("fallback_result"):
        raise HTTPException(status_code=400, detail="No fallback available")
    
    # Mark fallback as accepted
    await db.jobs.update_one(
        {"job_id": job_id},
        {"$set": {
            "fallback_accepted": True,
            "fallback_accepted_at": datetime.now(timezone.utc)
        }}
    )
    
    await metrics.increment("recovery.fallback_accepted")
    
    return {
        "success": True,
        "fallback_result": job["fallback_result"],
        "message": "Fallback output accepted"
    }


# ============================================
# DOWNLOAD RECOVERY ENDPOINTS
# ============================================

@router.post("/download")
async def recover_download(
    request: DownloadRecoveryRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Recover a failed download
    """
    user_id = str(current_user["_id"])
    correlation_id = generate_correlation_id()
    
    result = await DownloadRecoveryService.handle_download_failure(
        url=request.url,
        user_id=user_id,
        error_code=request.error_code,
        correlation_id=correlation_id
    )
    
    return result


@router.get("/download/regenerate")
async def regenerate_download_url(
    path: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate a new signed URL for download
    """
    user_id = str(current_user["_id"])
    
    new_url = SignedUrlService.generate_signed_url(path, user_id)
    
    return {
        "success": True,
        "url": new_url,
        "expires_in_minutes": 30
    }


@router.post("/preview/fallback")
async def get_preview_fallback(
    request: PreviewFallbackRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Get fallback options when preview fails
    """
    user_id = str(current_user["_id"])
    
    result = await PreviewRecoveryService.get_preview_fallback(
        content_id=request.content_id,
        content_type=request.content_type,
        user_id=user_id
    )
    
    return result


# ============================================
# PAYMENT RECOVERY ENDPOINTS
# ============================================

@router.get("/payment/{order_id}")
async def get_payment_recovery_status(
    order_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get payment status with recovery information
    """
    user_id = str(current_user["_id"])
    
    payment = await db.payment_records.find_one({
        "order_id": order_id,
        "user_id": user_id
    })
    
    if not payment:
        # Check in old payments collection
        payment = await db.payments.find_one({
            "order_id": order_id,
            "user_id": user_id
        })
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    status_message = ""
    recovery_info = {}
    
    state = payment.get("state") or payment.get("status", "unknown")
    
    if state == "success" and not payment.get("delivered", True):
        status_message = "Your payment was successful. Credits are being added to your account."
        recovery_info = {
            "action": "being_processed",
            "expected_resolution": "Within 5 minutes",
            "support_reference": order_id
        }
    elif state == "reconciling":
        status_message = "We're fixing a delivery issue. Your credits will be added shortly."
        recovery_info = {
            "action": "auto_resolving",
            "expected_resolution": "Within 10 minutes",
            "support_reference": order_id
        }
    elif state == "failed":
        status_message = "Payment failed. No charges were made."
        recovery_info = {
            "action": "retry_payment",
            "can_retry": True
        }
    elif state == "refunded":
        status_message = "This payment has been refunded."
        recovery_info = {
            "refund_id": payment.get("refund_id"),
            "refunded_at": payment.get("refunded_at")
        }
    elif state == "success" and payment.get("delivered"):
        status_message = "Payment successful and credits delivered."
    
    return {
        "order_id": order_id,
        "state": state,
        "amount": payment.get("amount"),
        "credits": payment.get("credits"),
        "delivered": payment.get("delivered", False),
        "status_message": status_message,
        "recovery_info": recovery_info,
        "created_at": payment.get("created_at"),
        "support_contact": "support@creatorstudio.ai"
    }


# ============================================
# GENERAL RECOVERY STATUS
# ============================================

@router.get("/status")
async def get_user_recovery_status(
    current_user: dict = Depends(get_current_user)
):
    """
    Get overall recovery status for current user
    """
    user_id = str(current_user.get("id") or current_user.get("_id", ""))
    
    # Check for pending jobs
    pending_jobs = await db.jobs.count_documents({
        "user_id": user_id,
        "state": {"$in": ["pending", "queued", "processing", "retrying"]}
    })
    
    # Check for failed jobs with retry available
    failed_jobs = await db.jobs.find({
        "user_id": user_id,
        "state": {"$in": ["failed", "fallback"]},
        "created_at": {"$gte": datetime.now(timezone.utc) - timedelta(hours=24)}
    }).to_list(length=10)
    
    # Check for stuck payments
    stuck_payments = await db.payment_records.count_documents({
        "user_id": user_id,
        "state": "success",
        "delivered": False
    })
    
    # Build status
    issues = []
    
    if stuck_payments > 0:
        issues.append({
            "type": "payment",
            "message": f"{stuck_payments} payment(s) being processed",
            "action": "wait",
            "auto_resolving": True
        })
    
    for job in failed_jobs:
        if job.get("fallback_result"):
            issues.append({
                "type": "job_fallback",
                "job_id": job["job_id"],
                "job_type": job["job_type"],
                "message": "Alternative output available",
                "action": "review_fallback"
            })
        else:
            issues.append({
                "type": "job_failed",
                "job_id": job["job_id"],
                "job_type": job["job_type"],
                "message": "Generation failed",
                "action": "retry_available"
            })
    
    return {
        "has_issues": len(issues) > 0,
        "pending_jobs": pending_jobs,
        "issues": issues,
        "system_status": "operational"  # Could be dynamic based on system health
    }


# ============================================
# SUPPORT REFERENCE
# ============================================

@router.get("/support-reference/{reference_type}/{reference_id}")
async def get_support_reference(
    reference_type: str,
    reference_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get support reference information for customer support
    """
    user_id = str(current_user["_id"])
    
    if reference_type == "job":
        record = await db.jobs.find_one({"job_id": reference_id, "user_id": user_id})
        record_type = "Job"
    elif reference_type == "payment":
        record = await db.payment_records.find_one({"order_id": reference_id, "user_id": user_id})
        record_type = "Payment"
    else:
        raise HTTPException(status_code=400, detail="Invalid reference type")
    
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    # Build support reference (sanitized for sharing)
    support_info = {
        "reference_id": reference_id,
        "type": record_type,
        "created_at": record.get("created_at"),
        "status": record.get("state") or record.get("status"),
        "correlation_id": record.get("correlation_id"),
        "user_email": current_user.get("email")
    }
    
    # Add type-specific info
    if reference_type == "job":
        support_info["job_type"] = record.get("job_type")
        support_info["attempt"] = record.get("attempt")
        support_info["error"] = record.get("last_error")
    elif reference_type == "payment":
        support_info["amount"] = record.get("amount")
        support_info["delivered"] = record.get("delivered")
    
    return {
        "support_reference": support_info,
        "instructions": "Share this information with support for faster resolution."
    }
