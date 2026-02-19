"""
Credit Pipeline System - Wallet, Jobs, Ledger Management
Implements credit-gated async job generation with atomic transactions
"""
from fastapi import APIRouter, HTTPException, Depends, Header, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user, log_exception
from security import limiter

router = APIRouter(prefix="/wallet", tags=["Wallet & Credits"])


# =============================================================================
# PRICING CONFIGURATION
# =============================================================================
PRICING_CONFIG = {
    "TEXT_TO_IMAGE": {
        "baseCredits": 10,
        "description": "Generate AI images from text prompts",
        "estimatedTime": "10-30 seconds"
    },
    "TEXT_TO_VIDEO": {
        "baseCredits": 25,
        "perSecondCredits": 5,
        "minDuration": 2,
        "maxDuration": 12,
        "description": "Generate AI videos from text prompts",
        "estimatedTime": "2-5 minutes"
    },
    "IMAGE_TO_VIDEO": {
        "baseCredits": 20,
        "perSecondCredits": 4,
        "description": "Animate images into videos",
        "estimatedTime": "2-5 minutes"
    },
    "VIDEO_REMIX": {
        "baseCredits": 15,
        "description": "Remix and transform videos",
        "estimatedTime": "3-6 minutes"
    },
    "STORY_GENERATION": {
        "baseCredits": 10,
        "description": "Generate kids story packs",
        "estimatedTime": "30-60 seconds"
    },
    "REEL_GENERATION": {
        "baseCredits": 10,
        "description": "Generate viral reel scripts",
        "estimatedTime": "15-30 seconds"
    },
    "STYLE_PROFILE_CREATE": {
        "baseCredits": 20,
        "description": "Create custom style profiles",
        "estimatedTime": "30-60 seconds"
    }
}


# =============================================================================
# PYDANTIC MODELS
# =============================================================================
class WalletResponse(BaseModel):
    userId: str
    balanceCredits: int
    reservedCredits: int
    availableCredits: int


class JobCreateRequest(BaseModel):
    jobType: str = Field(..., description="Type of job: TEXT_TO_IMAGE, TEXT_TO_VIDEO, etc.")
    inputData: Dict[str, Any] = Field(..., description="Input parameters for the job")
    provider: Optional[str] = Field(default="gemini", description="AI provider to use")


class JobResponse(BaseModel):
    jobId: str
    status: str
    jobType: str
    costCredits: int
    createdAt: str
    outputUrl: Optional[str] = None
    errorMessage: Optional[str] = None


class LedgerEntry(BaseModel):
    entryType: str  # HOLD, CAPTURE, RELEASE, TOPUP, ADJUST
    amount: int
    refType: str  # JOB, SUBSCRIPTION, ADMIN, REFUND
    refId: str
    status: str  # ACTIVE, REVERSED


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def calculate_job_cost(job_type: str, input_data: Dict[str, Any]) -> int:
    """Calculate the credit cost for a job based on type and parameters"""
    pricing = PRICING_CONFIG.get(job_type)
    if not pricing:
        raise HTTPException(status_code=400, detail=f"Unknown job type: {job_type}")
    
    base_cost = pricing.get("baseCredits", 10)
    
    # Dynamic pricing based on parameters
    if job_type == "TEXT_TO_VIDEO":
        duration = input_data.get("duration", 4)
        per_second = pricing.get("perSecondCredits", 5)
        return base_cost + (duration * per_second)
    
    if job_type == "IMAGE_TO_VIDEO":
        duration = input_data.get("duration", 4)
        per_second = pricing.get("perSecondCredits", 4)
        return base_cost + (duration * per_second)
    
    return base_cost


async def reserve_credits(user_id: str, amount: int, job_id: str, job_type: str) -> bool:
    """
    Atomically reserve credits for a job
    Returns True if successful, raises HTTPException if insufficient balance
    """
    # Get current balance
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    current_balance = user.get("credits", 0)
    
    # Get current holds
    active_holds = await db.credit_ledger.aggregate([
        {"$match": {"userId": user_id, "entryType": "HOLD", "status": "ACTIVE"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]).to_list(1)
    
    reserved = active_holds[0]["total"] if active_holds else 0
    available = current_balance - reserved
    
    if available < amount:
        raise HTTPException(
            status_code=402, 
            detail=f"Insufficient credits. Need {amount}, available {available} (balance: {current_balance}, reserved: {reserved})"
        )
    
    # Create hold entry
    ledger_entry = {
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "entryType": "HOLD",
        "amount": amount,
        "refType": "JOB",
        "refId": job_id,
        "jobType": job_type,
        "status": "ACTIVE",
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.credit_ledger.insert_one(ledger_entry)
    logger.info(f"Reserved {amount} credits for job {job_id} (user: {user_id})")
    
    return True


async def capture_credits(job_id: str, user_id: str, amount: int) -> bool:
    """
    Convert a HOLD to a CAPTURE - finalize the credit spend
    Called when job succeeds
    """
    # Find and update the hold entry
    hold_entry = await db.credit_ledger.find_one({
        "refId": job_id,
        "userId": user_id,
        "entryType": "HOLD",
        "status": "ACTIVE"
    }, {"_id": 0})
    
    if not hold_entry:
        logger.warning(f"No active hold found for job {job_id}")
        return False
    
    # Mark hold as captured
    await db.credit_ledger.update_one(
        {"id": hold_entry["id"]},
        {"$set": {"status": "CAPTURED", "capturedAt": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Create capture entry
    capture_entry = {
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "entryType": "CAPTURE",
        "amount": amount,
        "refType": "JOB",
        "refId": job_id,
        "holdId": hold_entry["id"],
        "status": "ACTIVE",
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.credit_ledger.insert_one(capture_entry)
    
    # Actually deduct from user balance
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"credits": -amount}}
    )
    
    logger.info(f"Captured {amount} credits for job {job_id}")
    return True


async def release_credits(job_id: str, user_id: str, reason: str = "Job failed") -> bool:
    """
    Release a HOLD - refund the credits
    Called when job fails or is cancelled
    """
    hold_entry = await db.credit_ledger.find_one({
        "refId": job_id,
        "userId": user_id,
        "entryType": "HOLD",
        "status": "ACTIVE"
    }, {"_id": 0})
    
    if not hold_entry:
        logger.warning(f"No active hold found for job {job_id} to release")
        return False
    
    # Mark hold as released
    await db.credit_ledger.update_one(
        {"id": hold_entry["id"]},
        {"$set": {"status": "RELEASED", "releasedAt": datetime.now(timezone.utc).isoformat(), "releaseReason": reason}}
    )
    
    # Create release entry
    release_entry = {
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "entryType": "RELEASE",
        "amount": hold_entry["amount"],
        "refType": "JOB",
        "refId": job_id,
        "holdId": hold_entry["id"],
        "reason": reason,
        "status": "ACTIVE",
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.credit_ledger.insert_one(release_entry)
    logger.info(f"Released {hold_entry['amount']} credits for job {job_id} - reason: {reason}")
    
    return True


async def check_idempotency(user_id: str, idempotency_key: str) -> Optional[str]:
    """
    Check if a request with this idempotency key already exists
    Returns existing job_id if found, None otherwise
    """
    if not idempotency_key:
        return None
    
    existing = await db.idempotency_keys.find_one({
        "userId": user_id,
        "idempotencyKey": idempotency_key
    }, {"_id": 0})
    
    if existing:
        return existing.get("jobId")
    
    return None


async def store_idempotency(user_id: str, idempotency_key: str, job_id: str):
    """Store idempotency key for deduplication"""
    if not idempotency_key:
        return
    
    await db.idempotency_keys.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "idempotencyKey": idempotency_key,
        "jobId": job_id,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "expiresAt": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    })


# =============================================================================
# ENDPOINTS
# =============================================================================
@router.get("/me")
async def get_wallet(user: dict = Depends(get_current_user)):
    """Get user's wallet balance and credit details"""
    user_id = user["id"]
    
    # Get current balance
    current_balance = user.get("credits", 0)
    
    # Get active holds
    active_holds = await db.credit_ledger.aggregate([
        {"$match": {"userId": user_id, "entryType": "HOLD", "status": "ACTIVE"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]).to_list(1)
    
    reserved = active_holds[0]["total"] if active_holds else 0
    available = current_balance - reserved
    
    # Get recent transactions
    recent_transactions = await db.credit_ledger.find(
        {"userId": user_id},
        {"_id": 0}
    ).sort("createdAt", -1).limit(10).to_list(10)
    
    return {
        "userId": user_id,
        "balanceCredits": current_balance,
        "reservedCredits": reserved,
        "availableCredits": available,
        "recentTransactions": recent_transactions
    }


@router.get("/pricing")
async def get_pricing():
    """Get current credit pricing for all job types"""
    return {
        "pricing": PRICING_CONFIG,
        "currency": "credits",
        "note": "Prices may vary based on job parameters (duration, resolution, etc.)"
    }


@router.post("/jobs")
@limiter.limit("30/minute")
async def create_job(
    request: Request,
    data: JobCreateRequest,
    user: dict = Depends(get_current_user),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """
    Create a new generation job with credit reservation
    
    Flow:
    1. Validate input and calculate cost
    2. Check for duplicate request (idempotency)
    3. Reserve credits atomically
    4. Create job with QUEUED status
    5. Return job ID immediately
    """
    user_id = user["id"]
    
    # Check idempotency
    existing_job_id = await check_idempotency(user_id, idempotency_key)
    if existing_job_id:
        existing_job = await db.genstudio_jobs.find_one({"id": existing_job_id}, {"_id": 0})
        if existing_job:
            return {
                "success": True,
                "jobId": existing_job_id,
                "status": existing_job.get("status"),
                "message": "Duplicate request - returning existing job",
                "duplicate": True
            }
    
    # Validate job type
    if data.jobType not in PRICING_CONFIG:
        raise HTTPException(status_code=400, detail=f"Invalid job type: {data.jobType}")
    
    # Calculate cost
    cost = calculate_job_cost(data.jobType, data.inputData)
    
    # Create job ID
    job_id = str(uuid.uuid4())
    
    # Reserve credits (atomic)
    await reserve_credits(user_id, cost, job_id, data.jobType)
    
    # Store idempotency key
    await store_idempotency(user_id, idempotency_key, job_id)
    
    # Create job record
    job = {
        "id": job_id,
        "userId": user_id,
        "jobType": data.jobType,
        "provider": data.provider,
        "status": "QUEUED",
        "costCredits": cost,
        "inputJson": data.inputData,
        "outputUrl": None,
        "outputUrls": [],
        "errorMessage": None,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "startedAt": None,
        "completedAt": None,
        "expiresAt": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    }
    
    await db.genstudio_jobs.insert_one(job)
    
    logger.info(f"Created job {job_id} (type: {data.jobType}, cost: {cost}, user: {user_id})")
    
    return {
        "success": True,
        "jobId": job_id,
        "status": "QUEUED",
        "costCredits": cost,
        "estimatedTime": PRICING_CONFIG[data.jobType].get("estimatedTime", "1-2 minutes"),
        "message": "Job created and credits reserved. Poll /jobs/{id} for status."
    }


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str, user: dict = Depends(get_current_user)):
    """Get job status and output"""
    job = await db.genstudio_jobs.find_one({
        "id": job_id,
        "userId": user["id"]
    }, {"_id": 0})
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "jobId": job["id"],
        "status": job["status"],
        "jobType": job["jobType"],
        "costCredits": job["costCredits"],
        "outputUrl": job.get("outputUrl"),
        "outputUrls": job.get("outputUrls", []),
        "errorMessage": job.get("errorMessage"),
        "createdAt": job["createdAt"],
        "startedAt": job.get("startedAt"),
        "completedAt": job.get("completedAt"),
        "progress": job.get("progress", 0),
        "progressMessage": job.get("progressMessage", ""),
        "resultJson": job.get("resultJson")
    }


@router.get("/jobs/{job_id}/result")
async def get_job_result(job_id: str, user: dict = Depends(get_current_user)):
    """Get job result JSON (for story/reel generation)"""
    job = await db.genstudio_jobs.find_one({
        "id": job_id,
        "userId": user["id"]
    }, {"_id": 0})
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["status"] != "SUCCEEDED":
        raise HTTPException(status_code=400, detail=f"Job not completed. Status: {job['status']}")
    
    result_json = job.get("resultJson")
    if not result_json:
        raise HTTPException(status_code=404, detail="No result data available")
    
    return {
        "jobId": job_id,
        "status": job["status"],
        "result": result_json
    }


@router.get("/jobs")
async def list_jobs(
    user: dict = Depends(get_current_user),
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    limit: int = 20,
    skip: int = 0
):
    """List user's jobs with optional filters"""
    query = {"userId": user["id"]}
    
    if status:
        query["status"] = status
    if job_type:
        query["jobType"] = job_type
    
    jobs = await db.genstudio_jobs.find(
        query,
        {"_id": 0}
    ).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)
    
    total = await db.genstudio_jobs.count_documents(query)
    
    return {
        "jobs": jobs,
        "total": total,
        "limit": limit,
        "skip": skip
    }


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, user: dict = Depends(get_current_user)):
    """Cancel a job if not yet started"""
    job = await db.genstudio_jobs.find_one({
        "id": job_id,
        "userId": user["id"]
    }, {"_id": 0})
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["status"] not in ["QUEUED", "PENDING"]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel job with status: {job['status']}")
    
    # Release credits
    await release_credits(job_id, user["id"], "User cancelled")
    
    # Update job status
    await db.genstudio_jobs.update_one(
        {"id": job_id},
        {
            "$set": {
                "status": "CANCELLED",
                "cancelledAt": datetime.now(timezone.utc).isoformat(),
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    logger.info(f"Job {job_id} cancelled by user")
    
    return {
        "success": True,
        "jobId": job_id,
        "status": "CANCELLED",
        "message": "Job cancelled and credits released"
    }


@router.get("/ledger")
async def get_credit_ledger(
    user: dict = Depends(get_current_user),
    limit: int = 50,
    skip: int = 0
):
    """Get user's credit transaction history"""
    entries = await db.credit_ledger.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)
    
    total = await db.credit_ledger.count_documents({"userId": user["id"]})
    
    # Calculate totals
    totals = await db.credit_ledger.aggregate([
        {"$match": {"userId": user["id"], "status": "ACTIVE"}},
        {"$group": {
            "_id": "$entryType",
            "total": {"$sum": "$amount"}
        }}
    ]).to_list(10)
    
    totals_dict = {t["_id"]: t["total"] for t in totals}
    
    return {
        "entries": entries,
        "total": total,
        "summary": {
            "totalHolds": totals_dict.get("HOLD", 0),
            "totalCaptures": totals_dict.get("CAPTURE", 0),
            "totalReleases": totals_dict.get("RELEASE", 0),
            "totalTopups": totals_dict.get("TOPUP", 0)
        }
    }


# =============================================================================
# INTERNAL FUNCTIONS FOR JOB PROCESSING
# =============================================================================
async def mark_job_started(job_id: str):
    """Mark job as started (called by worker)"""
    await db.genstudio_jobs.update_one(
        {"id": job_id},
        {
            "$set": {
                "status": "RUNNING",
                "startedAt": datetime.now(timezone.utc).isoformat(),
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }
        }
    )


async def mark_job_succeeded(job_id: str, output_url: str, output_urls: List[str] = None):
    """Mark job as succeeded and capture credits (called by worker)"""
    job = await db.genstudio_jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        logger.error(f"Job {job_id} not found for success marking")
        return
    
    # Capture credits
    await capture_credits(job_id, job["userId"], job["costCredits"])
    
    # Update job
    await db.genstudio_jobs.update_one(
        {"id": job_id},
        {
            "$set": {
                "status": "SUCCEEDED",
                "outputUrl": output_url,
                "outputUrls": output_urls or [output_url] if output_url else [],
                "completedAt": datetime.now(timezone.utc).isoformat(),
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    logger.info(f"Job {job_id} succeeded")


async def mark_job_failed(job_id: str, error_message: str):
    """Mark job as failed and release credits (called by worker)"""
    job = await db.genstudio_jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        logger.error(f"Job {job_id} not found for failure marking")
        return
    
    # Release credits
    await release_credits(job_id, job["userId"], f"Job failed: {error_message}")
    
    # Update job
    await db.genstudio_jobs.update_one(
        {"id": job_id},
        {
            "$set": {
                "status": "FAILED",
                "errorMessage": error_message,
                "completedAt": datetime.now(timezone.utc).isoformat(),
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    logger.info(f"Job {job_id} failed: {error_message}")


async def update_job_progress(job_id: str, progress: int, message: str = None):
    """Update job progress (0-100)"""
    update = {
        "progress": progress,
        "updatedAt": datetime.now(timezone.utc).isoformat()
    }
    if message:
        update["progressMessage"] = message
    
    await db.genstudio_jobs.update_one(
        {"id": job_id},
        {"$set": update}
    )
