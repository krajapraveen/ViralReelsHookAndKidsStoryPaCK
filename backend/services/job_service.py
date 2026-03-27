"""
Job Service - Handles retrieval and merging of story and pipeline jobs
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

async def get_user_jobs_combined(db, user_id: str, limit: int = 20):
    """
    Fetches and merges jobs from genstudio_jobs (story_engine) and pipeline_jobs.
    Filters for READY or PARTIAL_READY status to ensure valid media exists.
    """
    try:
        # Query conditions: Status must be usable and media must exist
        query = {
            "status": {"$in": ["READY", "PARTIAL_READY", "COMPLETED"]},
            "$or": [
                {"video_url": {"$exists": True, "$ne": ""}},
                {"videoUrl": {"$exists": True, "$ne": ""}}
            ]
        }

        # Fetch from main jobs collection
        jobs = await db.genstudio_jobs.find(query).sort("createdAt", -1).limit(limit).to_list(length=limit)
        
        # Fetch from pipeline jobs if they are separate
        pipeline_jobs = await db.pipeline_jobs.find(query).sort("createdAt", -1).limit(limit).to_list(length=limit)

        combined = jobs + pipeline_jobs
        
        # Normalize field names and sort by newest
        normalized = []
        for job in combined:
            normalized.append({
                "id": str(job.get("_id") or job.get("id")),
                "title": job.get("title") or job.get("prompt", "Untitled Story")[:30],
                "video_url": job.get("video_url") or job.get("videoUrl"),
                "thumbnail_url": job.get("thumbnail_url") or job.get("thumbnailUrl") or "https://placehold.co/600x400?text=Processing",
                "hook": job.get("hook") or job.get("cliffhanger") or "Continue the adventure...",
                "status": job.get("status"),
                "createdAt": job.get("createdAt")
            })

        return sorted(normalized, key=lambda x: x['createdAt'] if x['createdAt'] else datetime.min, reverse=True)
    except Exception as e:
        logger.error(f"Error fetching combined jobs: {e}")
        return []