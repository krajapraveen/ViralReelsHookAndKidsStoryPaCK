"""
CreatorStudio AI - Job Recovery Service
=======================================
Handles automatic job recovery, retries, and fallbacks for all generation tasks.

Features:
- Idempotent job submission
- Automatic retry with exponential backoff
- Fallback output generation
- Job state persistence
- Queue management per job type
"""
import asyncio
import hashlib
import json
import time
import uuid
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, add_credits, deduct_credits
from services.self_healing_core import (
    Job, JobState, metrics, orchestrator, alert_manager,
    IncidentLogger, CorrelationContext, AlertSeverity,
    generate_correlation_id, generate_idempotency_key
)

# ============================================
# JOB QUEUE CONFIGURATION
# ============================================

# Separate queues for different job types (bulkhead pattern)
JOB_QUEUES = {
    "text": asyncio.Queue(maxsize=500),      # Text generation (scripts, captions)
    "image": asyncio.Queue(maxsize=200),     # Image generation
    "video": asyncio.Queue(maxsize=100),     # Video generation (heaviest)
    "export": asyncio.Queue(maxsize=300),    # PDF/file exports
    "gif": asyncio.Queue(maxsize=200),       # GIF generation
}

# Job type configurations
JOB_CONFIG = {
    "text": {
        "max_attempts": 3,
        "base_timeout": 30,
        "credits_per_attempt": 0,  # Credits deducted upfront
        "fallback_enabled": True
    },
    "image": {
        "max_attempts": 3,
        "base_timeout": 60,
        "credits_per_attempt": 0,
        "fallback_enabled": True
    },
    "video": {
        "max_attempts": 2,
        "base_timeout": 180,
        "credits_per_attempt": 0,
        "fallback_enabled": True
    },
    "export": {
        "max_attempts": 3,
        "base_timeout": 45,
        "credits_per_attempt": 0,
        "fallback_enabled": True
    },
    "gif": {
        "max_attempts": 3,
        "base_timeout": 60,
        "credits_per_attempt": 0,
        "fallback_enabled": True
    },
    "comix": {
        "max_attempts": 3,
        "base_timeout": 90,
        "credits_per_attempt": 0,
        "fallback_enabled": True
    },
    "storybook": {
        "max_attempts": 2,
        "base_timeout": 120,
        "credits_per_attempt": 0,
        "fallback_enabled": True
    }
}


# ============================================
# JOB SUBMISSION SERVICE
# ============================================

class JobSubmissionService:
    """
    Handles idempotent job submission with automatic deduplication
    """
    
    @staticmethod
    def _hash_params(params: Dict) -> str:
        """Create a hash of job parameters for idempotency"""
        serialized = json.dumps(params, sort_keys=True, default=str)
        return hashlib.md5(serialized.encode()).hexdigest()[:16]
    
    @classmethod
    async def submit_job(
        cls,
        user_id: str,
        job_type: str,
        params: Dict,
        credits_required: int = 0,
        correlation_id: str = None,
        client_request_id: str = None
    ) -> Dict[str, Any]:
        """
        Submit a job with idempotency protection
        
        Returns:
            dict: {job_id, status, is_duplicate, message}
        """
        correlation_id = correlation_id or generate_correlation_id()
        CorrelationContext.set(correlation_id, user_id, job_type)
        
        # Generate idempotency key
        params_hash = cls._hash_params(params)
        idem_key = client_request_id or generate_idempotency_key(user_id, job_type, params_hash)
        
        # Check for duplicate submission
        existing_job = await db.jobs.find_one({
            "idempotency_key": idem_key,
            "created_at": {"$gte": datetime.now(timezone.utc) - timedelta(hours=24)}
        })
        
        if existing_job:
            logger.info(f"Duplicate job detected: {idem_key}")
            await metrics.increment("jobs.duplicate_prevented")
            return {
                "job_id": existing_job["job_id"],
                "status": existing_job["state"],
                "is_duplicate": True,
                "message": "Job already submitted",
                "result_url": existing_job.get("result_url")
            }
        
        # Verify user has enough credits
        if credits_required > 0:
            user = await db.users.find_one({"_id": user_id})
            if not user or user.get("credits", 0) < credits_required:
                return {
                    "job_id": None,
                    "status": "rejected",
                    "is_duplicate": False,
                    "message": "Insufficient credits"
                }
            
            # Reserve credits (deduct immediately)
            await deduct_credits(user_id, credits_required, f"Reserved for job {job_type}")
        
        # Create job
        job = Job(
            job_id=f"job_{uuid.uuid4().hex[:16]}",
            user_id=user_id,
            job_type=job_type,
            correlation_id=correlation_id,
            idempotency_key=idem_key,
            credits_reserved=credits_required,
            params=params,
            metadata={
                "client_request_id": client_request_id,
                "params_hash": params_hash
            }
        )
        
        config = JOB_CONFIG.get(job_type, JOB_CONFIG["text"])
        job.max_attempts = config["max_attempts"]
        
        # Save job
        await db.jobs.insert_one(job.to_dict())
        
        # Queue job
        queue = JOB_QUEUES.get(job_type, JOB_QUEUES["text"])
        try:
            queue.put_nowait(job)
            job.state = JobState.QUEUED
            await cls._update_job_state(job)
            await metrics.increment("jobs.queued", tags={"type": job_type})
        except asyncio.QueueFull:
            # Queue is full - return error
            job.state = JobState.FAILED
            job.last_error = "System busy, please try again"
            await cls._update_job_state(job)
            
            # Refund credits
            if credits_required > 0:
                await add_credits(user_id, credits_required, f"Refund - queue full")
            
            await metrics.increment("jobs.queue_full", tags={"type": job_type})
            return {
                "job_id": job.job_id,
                "status": "queue_full",
                "is_duplicate": False,
                "message": "System is busy, please try again in a few minutes"
            }
        
        CorrelationContext.add_trace("job_submitted", "success", {"job_id": job.job_id})
        
        return {
            "job_id": job.job_id,
            "status": "queued",
            "is_duplicate": False,
            "message": "Job submitted successfully",
            "correlation_id": correlation_id
        }
    
    @staticmethod
    async def _update_job_state(job: Job):
        """Update job state in database"""
        await db.jobs.update_one(
            {"job_id": job.job_id},
            {"$set": {
                "state": job.state.value,
                "last_error": job.last_error,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
    
    @classmethod
    async def get_job_status(cls, job_id: str, user_id: str = None) -> Optional[Dict]:
        """Get job status"""
        query = {"job_id": job_id}
        if user_id:
            query["user_id"] = user_id
        
        job_data = await db.jobs.find_one(query)
        if not job_data:
            return None
        
        return {
            "job_id": job_data["job_id"],
            "status": job_data["state"],
            "progress": job_data.get("progress", 0),
            "result_url": job_data.get("result_url"),
            "fallback_result": job_data.get("fallback_result"),
            "error": job_data.get("last_error") if job_data["state"] in ["failed", "fallback"] else None,
            "created_at": job_data.get("created_at"),
            "completed_at": job_data.get("completed_at")
        }


# ============================================
# JOB EXECUTION SERVICE
# ============================================

class JobExecutionService:
    """
    Executes jobs with retry logic and fallback handling
    """
    
    # Registry of job executors
    _executors: Dict[str, Callable] = {}
    _fallback_handlers: Dict[str, Callable] = {}
    
    @classmethod
    def register_executor(cls, job_type: str, executor: Callable):
        """Register a job executor function"""
        cls._executors[job_type] = executor
    
    @classmethod
    def register_fallback(cls, job_type: str, handler: Callable):
        """Register a fallback handler for a job type"""
        cls._fallback_handlers[job_type] = handler
    
    @classmethod
    async def execute_job(cls, job: Job) -> Dict[str, Any]:
        """
        Execute a job with retry and fallback logic
        """
        job.state = JobState.PROCESSING
        job.started_at = datetime.now(timezone.utc)
        await cls._update_job(job)
        
        config = JOB_CONFIG.get(job.job_type, JOB_CONFIG["text"])
        executor = cls._executors.get(job.job_type)
        
        if not executor:
            job.state = JobState.FAILED
            job.last_error = f"No executor registered for job type: {job.job_type}"
            await cls._update_job(job)
            return {"success": False, "error": job.last_error}
        
        last_error = None
        
        # Retry loop
        while job.attempt < job.max_attempts:
            job.attempt += 1
            
            try:
                logger.info(f"Executing job {job.job_id} attempt {job.attempt}/{job.max_attempts}")
                
                # Execute with timeout
                result = await asyncio.wait_for(
                    executor(job.params, job.user_id, job.correlation_id),
                    timeout=config["base_timeout"] * job.attempt  # Increase timeout on retries
                )
                
                # Success
                job.state = JobState.COMPLETED
                job.result_url = result.get("url") or result.get("result_url")
                job.completed_at = datetime.now(timezone.utc)
                job.credits_charged = job.credits_reserved
                
                await cls._update_job(job)
                await metrics.record_job(job.job_type, "completed", 
                                        (job.completed_at - job.started_at).total_seconds() * 1000)
                
                CorrelationContext.add_trace("job_completed", "success")
                return {"success": True, "result": result}
                
            except asyncio.TimeoutError:
                last_error = "Job timed out"
                logger.warning(f"Job {job.job_id} timed out on attempt {job.attempt}")
                
            except Exception as e:
                last_error = str(e)
                logger.error(f"Job {job.job_id} failed on attempt {job.attempt}: {e}")
            
            # Record retry
            if job.attempt < job.max_attempts:
                job.state = JobState.RETRYING
                await cls._update_job(job)
                
                # Exponential backoff
                wait_time = 2 ** (job.attempt - 1)
                await asyncio.sleep(wait_time)
                await metrics.increment("jobs.retried", tags={"type": job.job_type})
        
        # All retries exhausted - try fallback
        job.last_error = last_error
        
        if config["fallback_enabled"] and job.job_type in cls._fallback_handlers:
            return await cls._execute_fallback(job)
        
        # No fallback - mark as failed
        job.state = JobState.FAILED
        job.completed_at = datetime.now(timezone.utc)
        await cls._update_job(job)
        
        # Refund credits
        if job.credits_reserved > 0:
            await add_credits(job.user_id, job.credits_reserved, 
                            f"Refund - job {job.job_id} failed")
        
        await metrics.record_job(job.job_type, "failed")
        await IncidentLogger.log_incident(
            incident_type="job_failed",
            severity="error",
            description=f"Job {job.job_id} failed after {job.max_attempts} attempts",
            user_id=job.user_id,
            correlation_id=job.correlation_id,
            context={"job_type": job.job_type, "error": last_error}
        )
        
        return {"success": False, "error": last_error}
    
    @classmethod
    async def _execute_fallback(cls, job: Job) -> Dict[str, Any]:
        """Execute fallback for a failed job"""
        logger.info(f"Executing fallback for job {job.job_id}")
        
        handler = cls._fallback_handlers[job.job_type]
        
        try:
            fallback_result = await handler(job.params, job.user_id, job.correlation_id)
            
            job.state = JobState.FALLBACK
            job.fallback_result = fallback_result
            job.completed_at = datetime.now(timezone.utc)
            # Charge partial credits for fallback output
            job.credits_charged = max(1, job.credits_reserved // 2)
            
            # Refund partial credits
            refund = job.credits_reserved - job.credits_charged
            if refund > 0:
                await add_credits(job.user_id, refund, 
                                f"Partial refund - job {job.job_id} fallback")
            
            await cls._update_job(job)
            await metrics.record_job(job.job_type, "fallback")
            
            CorrelationContext.add_trace("fallback_executed", "success")
            return {"success": True, "fallback": True, "result": fallback_result}
            
        except Exception as e:
            logger.error(f"Fallback failed for job {job.job_id}: {e}")
            
            job.state = JobState.FAILED
            job.last_error = f"Fallback failed: {e}"
            job.completed_at = datetime.now(timezone.utc)
            await cls._update_job(job)
            
            # Full refund on complete failure
            if job.credits_reserved > 0:
                await add_credits(job.user_id, job.credits_reserved,
                                f"Refund - job {job.job_id} complete failure")
            
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def _update_job(job: Job):
        """Update job in database"""
        job_dict = job.to_dict()
        job_dict["updated_at"] = datetime.now(timezone.utc)
        await db.jobs.update_one({"job_id": job.job_id}, {"$set": job_dict})


# ============================================
# FALLBACK HANDLERS
# ============================================

async def video_fallback_handler(params: Dict, user_id: str, correlation_id: str) -> Dict:
    """
    Fallback for video generation: returns script + storyboard
    """
    logger.info(f"Generating video fallback for user {user_id}")
    
    return {
        "type": "fallback",
        "message": "Video generation encountered issues. Here's your content in alternative format:",
        "outputs": {
            "script": params.get("script") or "Script would be generated here",
            "storyboard_description": params.get("description") or "Storyboard description here",
            "prompt_used": params.get("prompt"),
        },
        "retry_available": True,
        "retry_token": f"retry_{uuid.uuid4().hex[:8]}"
    }


async def image_fallback_handler(params: Dict, user_id: str, correlation_id: str) -> Dict:
    """
    Fallback for image generation: returns prompt pack + placeholder
    """
    logger.info(f"Generating image fallback for user {user_id}")
    
    return {
        "type": "fallback",
        "message": "Image generation is temporarily unavailable. Here's your prompt pack:",
        "outputs": {
            "original_prompt": params.get("prompt"),
            "enhanced_prompt": f"High quality, detailed, {params.get('prompt', '')}",
            "negative_prompt": params.get("negative_prompt", "blurry, low quality"),
            "style": params.get("style", "default"),
            "placeholder_url": "/static/placeholder-image.png"
        },
        "retry_available": True,
        "retry_token": f"retry_{uuid.uuid4().hex[:8]}"
    }


async def export_fallback_handler(params: Dict, user_id: str, correlation_id: str) -> Dict:
    """
    Fallback for export: regenerate from stored data
    """
    logger.info(f"Generating export fallback for user {user_id}")
    
    # Try to find stored generation data
    generation_id = params.get("generation_id")
    if generation_id:
        generation = await db.generations.find_one({"generation_id": generation_id})
        if generation:
            return {
                "type": "fallback",
                "message": "Export is being regenerated from your saved content",
                "data": {
                    "content": generation.get("content"),
                    "format": params.get("format", "pdf")
                },
                "retry_available": True
            }
    
    return {
        "type": "fallback",
        "message": "Export failed. Please try again or contact support.",
        "retry_available": True,
        "retry_token": f"retry_{uuid.uuid4().hex[:8]}"
    }


async def gif_fallback_handler(params: Dict, user_id: str, correlation_id: str) -> Dict:
    """
    Fallback for GIF generation: return static image + animation description
    """
    logger.info(f"Generating GIF fallback for user {user_id}")
    
    return {
        "type": "fallback",
        "message": "GIF generation encountered issues. Here's your content:",
        "outputs": {
            "static_frame": params.get("source_image"),
            "animation_description": f"Animated with {params.get('emotion', 'default')} emotion",
            "style": params.get("style", "default")
        },
        "retry_available": True,
        "retry_token": f"retry_{uuid.uuid4().hex[:8]}"
    }


async def comix_fallback_handler(params: Dict, user_id: str, correlation_id: str) -> Dict:
    """
    Fallback for Comix AI: return character description + panel layout
    """
    logger.info(f"Generating Comix fallback for user {user_id}")
    
    return {
        "type": "fallback",
        "message": "Comic generation encountered issues. Here's your content pack:",
        "outputs": {
            "character_description": params.get("character_description"),
            "style": params.get("style"),
            "panel_layout": params.get("panel_count", 4),
            "story_prompt": params.get("story_prompt")
        },
        "retry_available": True,
        "retry_token": f"retry_{uuid.uuid4().hex[:8]}"
    }


async def storybook_fallback_handler(params: Dict, user_id: str, correlation_id: str) -> Dict:
    """
    Fallback for Comic Storybook: return text + panel descriptions
    """
    logger.info(f"Generating Storybook fallback for user {user_id}")
    
    return {
        "type": "fallback",
        "message": "Storybook generation encountered issues. Here's your story content:",
        "outputs": {
            "story_text": params.get("story_text"),
            "style": params.get("style"),
            "page_count": params.get("page_count", 10),
            "panel_descriptions": "Panel descriptions would be generated here"
        },
        "retry_available": True,
        "retry_token": f"retry_{uuid.uuid4().hex[:8]}"
    }


# Register fallback handlers
JobExecutionService.register_fallback("video", video_fallback_handler)
JobExecutionService.register_fallback("image", image_fallback_handler)
JobExecutionService.register_fallback("export", export_fallback_handler)
JobExecutionService.register_fallback("gif", gif_fallback_handler)
JobExecutionService.register_fallback("comix", comix_fallback_handler)
JobExecutionService.register_fallback("storybook", storybook_fallback_handler)


# ============================================
# JOB WORKER
# ============================================

class JobWorker:
    """
    Background worker that processes jobs from queues
    """
    
    def __init__(self, job_type: str, concurrency: int = 2):
        self.job_type = job_type
        self.concurrency = concurrency
        self.running = False
        self._tasks: List[asyncio.Task] = []
    
    async def start(self):
        """Start the worker"""
        if self.running:
            return
        
        self.running = True
        logger.info(f"Starting {self.job_type} worker with concurrency {self.concurrency}")
        
        for i in range(self.concurrency):
            task = asyncio.create_task(self._worker_loop(i))
            self._tasks.append(task)
    
    async def stop(self):
        """Stop the worker gracefully"""
        self.running = False
        for task in self._tasks:
            task.cancel()
        self._tasks = []
        logger.info(f"Stopped {self.job_type} worker")
    
    async def _worker_loop(self, worker_id: int):
        """Main worker loop"""
        queue = JOB_QUEUES.get(self.job_type, JOB_QUEUES["text"])
        
        while self.running:
            try:
                # Get job from queue with timeout
                try:
                    job = await asyncio.wait_for(queue.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    continue
                
                logger.info(f"Worker {self.job_type}:{worker_id} processing job {job.job_id}")
                
                # Execute job
                result = await JobExecutionService.execute_job(job)
                
                if result.get("success"):
                    logger.info(f"Job {job.job_id} completed successfully")
                else:
                    logger.warning(f"Job {job.job_id} failed: {result.get('error')}")
                
                queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {self.job_type}:{worker_id} error: {e}")
                await asyncio.sleep(1)


# ============================================
# RETRY TOKEN SERVICE
# ============================================

class RetryTokenService:
    """
    Manages retry tokens for failed jobs
    """
    
    @staticmethod
    async def create_retry_token(job_id: str, user_id: str) -> str:
        """Create a retry token for a failed job"""
        token = f"retry_{uuid.uuid4().hex[:12]}"
        
        await db.retry_tokens.insert_one({
            "token": token,
            "job_id": job_id,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
            "used": False
        })
        
        return token
    
    @staticmethod
    async def use_retry_token(token: str, user_id: str) -> Optional[Dict]:
        """
        Use a retry token to re-submit a job
        Returns the original job parameters if valid
        """
        retry_record = await db.retry_tokens.find_one({
            "token": token,
            "user_id": user_id,
            "used": False,
            "expires_at": {"$gt": datetime.now(timezone.utc)}
        })
        
        if not retry_record:
            return None
        
        # Mark token as used
        await db.retry_tokens.update_one(
            {"token": token},
            {"$set": {"used": True, "used_at": datetime.now(timezone.utc)}}
        )
        
        # Get original job
        job = await db.jobs.find_one({"job_id": retry_record["job_id"]})
        if not job:
            return None
        
        return {
            "job_type": job["job_type"],
            "params": job["params"],
            "credits_required": job.get("credits_reserved", 0)
        }
