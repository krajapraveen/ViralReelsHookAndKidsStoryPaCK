"""
Automatic Retry Mechanism for AI Generation Tasks
Handles failures with exponential backoff and smart retry logic
"""
import asyncio
import traceback
from typing import Callable, Any, Optional, Dict, List
from datetime import datetime, timezone, timedelta
from functools import wraps
import uuid
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger

# Retry Configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_DELAY = 2  # seconds
DEFAULT_MAX_DELAY = 60  # seconds
DEFAULT_BACKOFF_MULTIPLIER = 2

# Error categories and their retry strategies
RETRY_STRATEGIES = {
    "network": {
        "max_retries": 5,
        "initial_delay": 1,
        "backoff_multiplier": 2,
        "errors": [
            "ConnectionError", "TimeoutError", "httpx.ConnectError",
            "httpx.ReadTimeout", "httpx.ConnectTimeout", "aiohttp.ClientError"
        ]
    },
    "rate_limit": {
        "max_retries": 3,
        "initial_delay": 30,
        "backoff_multiplier": 2,
        "errors": [
            "RateLimitError", "429", "Too Many Requests", "rate limit"
        ]
    },
    "service_unavailable": {
        "max_retries": 3,
        "initial_delay": 10,
        "backoff_multiplier": 3,
        "errors": [
            "503", "Service Unavailable", "temporarily unavailable", "overloaded"
        ]
    },
    "ai_generation": {
        "max_retries": 3,
        "initial_delay": 5,
        "backoff_multiplier": 2,
        "errors": [
            "generation failed", "image generation", "video generation",
            "model error", "inference error"
        ]
    },
    "content_safety": {
        "max_retries": 0,  # Don't retry content policy violations
        "errors": [
            "content policy", "safety filter", "blocked", "inappropriate"
        ]
    },
    "auth": {
        "max_retries": 1,
        "initial_delay": 1,
        "errors": [
            "401", "403", "Unauthorized", "Forbidden", "invalid token"
        ]
    },
    "default": {
        "max_retries": 2,
        "initial_delay": 3,
        "backoff_multiplier": 2,
        "errors": []
    }
}


def categorize_error(error: Exception) -> str:
    """Categorize an error to determine retry strategy"""
    error_str = str(error).lower()
    error_type = type(error).__name__
    
    for category, config in RETRY_STRATEGIES.items():
        if category == "default":
            continue
        for pattern in config.get("errors", []):
            if pattern.lower() in error_str or pattern.lower() in error_type.lower():
                return category
    
    return "default"


def get_retry_config(error_category: str) -> dict:
    """Get retry configuration for error category"""
    return RETRY_STRATEGIES.get(error_category, RETRY_STRATEGIES["default"])


class RetryContext:
    """Context manager for tracking retry state"""
    
    def __init__(
        self,
        job_id: str,
        job_type: str,
        user_id: str,
        max_retries: int = DEFAULT_MAX_RETRIES,
        initial_delay: float = DEFAULT_INITIAL_DELAY,
        max_delay: float = DEFAULT_MAX_DELAY,
        backoff_multiplier: float = DEFAULT_BACKOFF_MULTIPLIER
    ):
        self.job_id = job_id
        self.job_type = job_type
        self.user_id = user_id
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
        self.attempt = 0
        self.errors: List[dict] = []
        self.start_time = datetime.now(timezone.utc)
    
    def should_retry(self, error: Exception) -> bool:
        """Determine if we should retry based on error type"""
        category = categorize_error(error)
        config = get_retry_config(category)
        
        # Check if this error category allows retries
        if config["max_retries"] == 0:
            return False
        
        # Check if we've exceeded max retries
        return self.attempt < min(self.max_retries, config["max_retries"])
    
    def get_delay(self) -> float:
        """Calculate delay for next retry with exponential backoff"""
        delay = self.initial_delay * (self.backoff_multiplier ** self.attempt)
        return min(delay, self.max_delay)
    
    def record_error(self, error: Exception):
        """Record an error attempt"""
        self.errors.append({
            "attempt": self.attempt + 1,
            "error_type": type(error).__name__,
            "error_message": str(error)[:500],
            "error_category": categorize_error(error),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    def increment_attempt(self):
        """Increment attempt counter"""
        self.attempt += 1
    
    async def log_to_db(self, status: str, result: Any = None):
        """Log retry context to database"""
        await db.retry_logs.insert_one({
            "id": str(uuid.uuid4()),
            "jobId": self.job_id,
            "jobType": self.job_type,
            "userId": self.user_id,
            "attempts": self.attempt,
            "maxRetries": self.max_retries,
            "errors": self.errors,
            "status": status,
            "duration": (datetime.now(timezone.utc) - self.start_time).total_seconds(),
            "createdAt": self.start_time.isoformat(),
            "completedAt": datetime.now(timezone.utc).isoformat()
        })


async def with_retry(
    func: Callable,
    job_id: str,
    job_type: str,
    user_id: str,
    *args,
    max_retries: int = DEFAULT_MAX_RETRIES,
    on_retry: Callable = None,
    on_failure: Callable = None,
    **kwargs
) -> Any:
    """
    Execute an async function with automatic retry logic
    
    Args:
        func: Async function to execute
        job_id: Job identifier for logging
        job_type: Type of job (text_to_image, text_to_video, etc.)
        user_id: User identifier
        max_retries: Maximum number of retry attempts
        on_retry: Optional callback called before each retry
        on_failure: Optional callback called on final failure
        *args, **kwargs: Arguments to pass to func
    
    Returns:
        Result from func on success
    
    Raises:
        Last exception on failure after all retries
    """
    ctx = RetryContext(
        job_id=job_id,
        job_type=job_type,
        user_id=user_id,
        max_retries=max_retries
    )
    
    last_error = None
    
    while True:
        try:
            # Update job status to show retry attempt
            if ctx.attempt > 0:
                await db.genstudio_jobs.update_one(
                    {"id": job_id},
                    {"$set": {
                        "retryAttempt": ctx.attempt,
                        "status": f"retrying (attempt {ctx.attempt + 1})",
                        "lastError": str(last_error)[:200] if last_error else None
                    }}
                )
                
                if on_retry:
                    await on_retry(ctx.attempt, last_error)
            
            # Execute the function
            result = await func(*args, **kwargs)
            
            # Success - log and return
            await ctx.log_to_db("success", result)
            
            # Update job status
            await db.genstudio_jobs.update_one(
                {"id": job_id},
                {"$set": {
                    "retryAttempt": ctx.attempt,
                    "totalAttempts": ctx.attempt + 1,
                    "retrySuccess": ctx.attempt > 0
                }}
            )
            
            if ctx.attempt > 0:
                logger.info(f"Job {job_id} succeeded after {ctx.attempt + 1} attempts")
            
            return result
            
        except Exception as e:
            last_error = e
            ctx.record_error(e)
            
            logger.warning(
                f"Job {job_id} attempt {ctx.attempt + 1} failed: {type(e).__name__}: {str(e)[:100]}"
            )
            
            # Check if we should retry
            if not ctx.should_retry(e):
                await ctx.log_to_db("failed")
                
                if on_failure:
                    await on_failure(e, ctx.errors)
                
                # Update job with final failure
                await db.genstudio_jobs.update_one(
                    {"id": job_id},
                    {"$set": {
                        "status": "failed",
                        "error": str(e)[:500],
                        "errorCategory": categorize_error(e),
                        "totalAttempts": ctx.attempt + 1,
                        "retryErrors": ctx.errors
                    }}
                )
                
                raise
            
            # Calculate delay and wait
            delay = ctx.get_delay()
            logger.info(f"Job {job_id} retrying in {delay:.1f}s (attempt {ctx.attempt + 2})")
            await asyncio.sleep(delay)
            
            ctx.increment_attempt()


def retry_decorator(
    max_retries: int = DEFAULT_MAX_RETRIES,
    job_type: str = "unknown"
):
    """
    Decorator for adding retry logic to generation functions
    
    Usage:
        @retry_decorator(max_retries=3, job_type="text_to_image")
        async def generate_image(prompt: str, job_id: str, user_id: str) -> dict:
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, job_id: str = None, user_id: str = None, **kwargs):
            if not job_id:
                job_id = str(uuid.uuid4())
            if not user_id:
                user_id = "unknown"
            
            return await with_retry(
                func,
                job_id=job_id,
                job_type=job_type,
                user_id=user_id,
                *args,
                max_retries=max_retries,
                **kwargs
            )
        return wrapper
    return decorator


# ============================================================================
# GENERATION-SPECIFIC RETRY WRAPPERS
# ============================================================================

async def retry_text_to_image(
    generate_func: Callable,
    job_id: str,
    user_id: str,
    prompt: str,
    **kwargs
) -> dict:
    """Retry wrapper for text-to-image generation"""
    
    async def on_retry(attempt: int, error: Exception):
        # Notify user about retry
        await db.genstudio_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "statusMessage": f"Generation attempt {attempt + 1} in progress... Previous attempt encountered an issue, retrying automatically."
            }}
        )
    
    async def on_failure(error: Exception, errors: List[dict]):
        # Import here to avoid circular dependency
        from routes.push_notifications import notify_generation_failure
        await notify_generation_failure(job_id, "text_to_image", str(error), user_id)
    
    return await with_retry(
        generate_func,
        job_id=job_id,
        job_type="text_to_image",
        user_id=user_id,
        prompt=prompt,
        max_retries=3,
        on_retry=on_retry,
        on_failure=on_failure,
        **kwargs
    )


async def retry_text_to_video(
    generate_func: Callable,
    job_id: str,
    user_id: str,
    prompt: str,
    duration: int = 4,
    **kwargs
) -> dict:
    """Retry wrapper for text-to-video generation"""
    
    async def on_retry(attempt: int, error: Exception):
        await db.genstudio_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "statusMessage": f"Video generation attempt {attempt + 1}... Retrying automatically."
            }}
        )
    
    async def on_failure(error: Exception, errors: List[dict]):
        from routes.push_notifications import notify_generation_failure
        await notify_generation_failure(job_id, "text_to_video", str(error), user_id)
    
    return await with_retry(
        generate_func,
        job_id=job_id,
        job_type="text_to_video",
        user_id=user_id,
        prompt=prompt,
        duration=duration,
        max_retries=3,
        on_retry=on_retry,
        on_failure=on_failure,
        **kwargs
    )


async def retry_image_to_video(
    generate_func: Callable,
    job_id: str,
    user_id: str,
    image_data: str,
    prompt: str = "",
    **kwargs
) -> dict:
    """Retry wrapper for image-to-video generation"""
    
    async def on_retry(attempt: int, error: Exception):
        await db.genstudio_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "statusMessage": f"Image-to-video attempt {attempt + 1}... Retrying automatically."
            }}
        )
    
    async def on_failure(error: Exception, errors: List[dict]):
        from routes.push_notifications import notify_generation_failure
        await notify_generation_failure(job_id, "image_to_video", str(error), user_id)
    
    return await with_retry(
        generate_func,
        job_id=job_id,
        job_type="image_to_video",
        user_id=user_id,
        image_data=image_data,
        prompt=prompt,
        max_retries=3,
        on_retry=on_retry,
        on_failure=on_failure,
        **kwargs
    )


async def retry_story_generation(
    generate_func: Callable,
    job_id: str,
    user_id: str,
    story_params: dict,
    **kwargs
) -> dict:
    """Retry wrapper for story generation (text + images)"""
    
    async def on_retry(attempt: int, error: Exception):
        await db.generations.update_one(
            {"id": job_id},
            {"$set": {
                "status": f"retrying",
                "statusMessage": f"Story generation attempt {attempt + 1}... Retrying automatically."
            }}
        )
    
    return await with_retry(
        generate_func,
        job_id=job_id,
        job_type="story",
        user_id=user_id,
        story_params=story_params,
        max_retries=3,
        on_retry=on_retry,
        **kwargs
    )


async def retry_reel_generation(
    generate_func: Callable,
    job_id: str,
    user_id: str,
    reel_params: dict,
    **kwargs
) -> dict:
    """Retry wrapper for reel script generation"""
    
    async def on_retry(attempt: int, error: Exception):
        await db.generations.update_one(
            {"id": job_id},
            {"$set": {
                "status": f"retrying",
                "statusMessage": f"Reel generation attempt {attempt + 1}... Retrying automatically."
            }}
        )
    
    return await with_retry(
        generate_func,
        job_id=job_id,
        job_type="reel",
        user_id=user_id,
        reel_params=reel_params,
        max_retries=3,
        on_retry=on_retry,
        **kwargs
    )


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

async def get_retry_stats(user_id: str = None, days: int = 7) -> dict:
    """Get retry statistics"""
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    query = {"createdAt": {"$gte": start_date}}
    if user_id:
        query["userId"] = user_id
    
    # Aggregate stats
    pipeline = [
        {"$match": query},
        {"$group": {
            "_id": {
                "jobType": "$jobType",
                "status": "$status"
            },
            "count": {"$sum": 1},
            "avgAttempts": {"$avg": "$attempts"},
            "avgDuration": {"$avg": "$duration"}
        }}
    ]
    
    results = await db.retry_logs.aggregate(pipeline).to_list(100)
    
    # Process results
    stats = {
        "total_jobs": 0,
        "successful_retries": 0,
        "failed_after_retry": 0,
        "by_job_type": {},
        "avg_attempts_before_success": 0,
        "period_days": days
    }
    
    success_attempts = []
    
    for r in results:
        job_type = r["_id"]["jobType"]
        status = r["_id"]["status"]
        count = r["count"]
        
        stats["total_jobs"] += count
        
        if job_type not in stats["by_job_type"]:
            stats["by_job_type"][job_type] = {"success": 0, "failed": 0}
        
        if status == "success":
            stats["by_job_type"][job_type]["success"] += count
            stats["successful_retries"] += count
            if r["avgAttempts"]:
                success_attempts.append(r["avgAttempts"])
        else:
            stats["by_job_type"][job_type]["failed"] += count
            stats["failed_after_retry"] += count
    
    if success_attempts:
        stats["avg_attempts_before_success"] = round(sum(success_attempts) / len(success_attempts), 2)
    
    return stats


async def clear_old_retry_logs(days: int = 30):
    """Clean up old retry logs"""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    result = await db.retry_logs.delete_many({"createdAt": {"$lt": cutoff}})
    
    logger.info(f"Cleaned up {result.deleted_count} old retry logs")
    return result.deleted_count


# Export functions
__all__ = [
    'with_retry',
    'retry_decorator',
    'retry_text_to_image',
    'retry_text_to_video',
    'retry_image_to_video',
    'retry_story_generation',
    'retry_reel_generation',
    'RetryContext',
    'categorize_error',
    'get_retry_stats'
]
