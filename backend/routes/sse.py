"""
Server-Sent Events (SSE) Router
Real-time job status updates to replace polling mechanism
"""
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
import asyncio
import json
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user

router = APIRouter(prefix="/sse", tags=["Real-time Updates"])

# Store active SSE connections by user_id
active_connections: dict = {}


async def job_status_generator(user_id: str, request: Request):
    """
    Generator that yields job status updates for a specific user.
    Sends updates when jobs change status (QUEUED -> RUNNING -> SUCCEEDED/FAILED)
    """
    last_known_jobs = {}
    
    while True:
        # Check if client disconnected
        if await request.is_disconnected():
            logger.info(f"SSE client disconnected for user {user_id}")
            break
        
        try:
            # Fetch active/recent jobs for this user
            jobs = await db.genstudio_jobs.find(
                {
                    "userId": user_id,
                    "status": {"$in": ["QUEUED", "RUNNING", "SUCCEEDED", "FAILED"]}
                },
                {"_id": 0}
            ).sort("updatedAt", -1).limit(10).to_list(10)
            
            for job in jobs:
                job_id = job["id"]
                current_state = {
                    "status": job["status"],
                    "progress": job.get("progress", 0),
                    "progressMessage": job.get("progressMessage", ""),
                    "updatedAt": job.get("updatedAt", "")
                }
                
                # Check if job state changed
                if job_id not in last_known_jobs or last_known_jobs[job_id] != current_state:
                    last_known_jobs[job_id] = current_state
                    
                    # Yield the update event
                    event_data = {
                        "type": "job_update",
                        "jobId": job_id,
                        "jobType": job["jobType"],
                        "status": job["status"],
                        "progress": job.get("progress", 0),
                        "progressMessage": job.get("progressMessage", ""),
                        "outputUrl": job.get("outputUrl"),
                        "outputUrls": job.get("outputUrls", []),
                        "errorMessage": job.get("errorMessage"),
                        "costCredits": job.get("costCredits", 0),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    yield {
                        "event": "job_update",
                        "data": json.dumps(event_data)
                    }
            
            # Clean up completed jobs from tracking after 30 seconds
            current_time = datetime.now(timezone.utc)
            jobs_to_remove = []
            for job_id in list(last_known_jobs.keys()):
                job_in_list = next((j for j in jobs if j["id"] == job_id), None)
                if job_in_list and job_in_list["status"] in ["SUCCEEDED", "FAILED"]:
                    # Keep tracking completed jobs for a bit before removing
                    pass
            
            # Send heartbeat every 15 seconds
            yield {
                "event": "heartbeat",
                "data": json.dumps({"timestamp": datetime.now(timezone.utc).isoformat()})
            }
            
        except Exception as e:
            logger.error(f"SSE generator error for user {user_id}: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"message": "Connection error", "timestamp": datetime.now(timezone.utc).isoformat()})
            }
        
        # Poll interval
        await asyncio.sleep(2)


@router.get("/jobs")
async def stream_job_updates(request: Request, user: dict = Depends(get_current_user)):
    """
    SSE endpoint for streaming job status updates.
    Client connects and receives real-time updates for their jobs.
    
    Usage:
    ```javascript
    const eventSource = new EventSource('/api/sse/jobs', {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    
    eventSource.addEventListener('job_update', (event) => {
        const data = JSON.parse(event.data);
        console.log('Job update:', data);
    });
    
    eventSource.addEventListener('heartbeat', (event) => {
        console.log('Connection alive');
    });
    ```
    """
    user_id = user["id"]
    logger.info(f"SSE connection established for user {user_id}")
    
    return EventSourceResponse(
        job_status_generator(user_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.get("/wallet")
async def stream_wallet_updates(request: Request, user: dict = Depends(get_current_user)):
    """
    SSE endpoint for streaming wallet balance updates.
    Useful for real-time credit balance display.
    """
    user_id = user["id"]
    
    async def wallet_generator():
        last_balance = None
        last_reserved = None
        
        while True:
            if await request.is_disconnected():
                break
            
            try:
                # Get current balance
                user_doc = await db.users.find_one({"id": user_id}, {"_id": 0, "credits": 1})
                current_balance = user_doc.get("credits", 0) if user_doc else 0
                
                # Get reserved credits
                active_holds = await db.credit_ledger.aggregate([
                    {"$match": {"userId": user_id, "entryType": "HOLD", "status": "ACTIVE"}},
                    {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
                ]).to_list(1)
                reserved = active_holds[0]["total"] if active_holds else 0
                
                # Only emit if changed
                if current_balance != last_balance or reserved != last_reserved:
                    last_balance = current_balance
                    last_reserved = reserved
                    
                    yield {
                        "event": "wallet_update",
                        "data": json.dumps({
                            "balanceCredits": current_balance,
                            "reservedCredits": reserved,
                            "availableCredits": current_balance - reserved,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                    }
                
                # Heartbeat
                yield {
                    "event": "heartbeat",
                    "data": json.dumps({"timestamp": datetime.now(timezone.utc).isoformat()})
                }
                
            except Exception as e:
                logger.error(f"Wallet SSE error for user {user_id}: {e}")
            
            await asyncio.sleep(5)
    
    return EventSourceResponse(
        wallet_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
