"""Health check routes"""
from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/")
async def health_check():
    return {"status": "healthy"}


@router.get("/live")
async def liveness():
    return {"status": "live"}


@router.get("/ready")
async def readiness():
    return {"status": "ready"}
