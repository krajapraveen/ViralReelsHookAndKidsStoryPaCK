"""
Health Check Routes
CreatorStudio AI
"""
from fastapi import APIRouter
from datetime import datetime, timezone
import os
import sys

# Ensure backend directory is in path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, FILE_EXPIRY_MINUTES

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/")
async def health_check():
    """Main health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "file_expiry_minutes": FILE_EXPIRY_MINUTES,
        "security": "enabled"
    }


@router.get("/live")
async def liveness():
    """Kubernetes liveness probe"""
    return {"status": "alive"}


@router.get("/ready")
async def readiness():
    """Kubernetes readiness probe"""
    try:
        # Check database connection
        await db.command("ping")
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        return {"status": "not_ready", "error": str(e)}


@router.get("/metrics")
async def metrics():
    """Basic metrics endpoint"""
    try:
        user_count = await db.users.count_documents({})
        generation_count = await db.generations.count_documents({})
        genstudio_count = await db.genstudio_jobs.count_documents({})
        
        return {
            "users": user_count,
            "generations": generation_count,
            "genstudioJobs": genstudio_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {"error": str(e)}
