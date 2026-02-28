"""
Temporary Download Routes
Handles downloads with 5-minute expiry
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from datetime import datetime, timezone
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user
from services.download_expiry_service import get_download_service, DOWNLOAD_EXPIRY_MINUTES

router = APIRouter(prefix="/downloads", tags=["Downloads"])


@router.get("/my-downloads")
async def get_my_downloads(user: dict = Depends(get_current_user)):
    """Get all active downloads for current user"""
    service = get_download_service(db)
    downloads = await service.get_user_downloads(user["id"])
    
    return {
        "downloads": downloads,
        "expiry_minutes": DOWNLOAD_EXPIRY_MINUTES,
        "message": f"Downloads expire {DOWNLOAD_EXPIRY_MINUTES} minutes after creation"
    }


@router.get("/{download_id}")
async def get_download_info(download_id: str, user: dict = Depends(get_current_user)):
    """Get download info and remaining time"""
    service = get_download_service(db)
    download = await service.get_download(download_id, user["id"])
    
    if not download:
        raise HTTPException(status_code=404, detail="Download not found")
    
    if download.get("expired"):
        raise HTTPException(status_code=410, detail="Download has expired. Please generate again.")
    
    return download


@router.get("/{download_id}/file")
async def download_file(download_id: str, user: dict = Depends(get_current_user)):
    """Download the actual file"""
    service = get_download_service(db)
    download = await service.get_download(download_id, user["id"])
    
    if not download:
        raise HTTPException(status_code=404, detail="Download not found")
    
    if download.get("expired"):
        raise HTTPException(status_code=410, detail="Download has expired. Please generate again.")
    
    file_path = Path(download.get("file_path", ""))
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on server")
    
    return FileResponse(
        path=str(file_path),
        filename=download.get("original_filename", "download"),
        media_type=download.get("file_type", "application/octet-stream"),
        headers={
            "X-Expires-In-Seconds": str(download.get("remaining_seconds", 0)),
            "X-Expires-At": download.get("expires_at", ""),
            "X-Download-Warning": f"This file will be deleted in {download.get('remaining_minutes', 0)} minutes"
        }
    )


@router.post("/{download_id}/extend")
async def extend_download(download_id: str, user: dict = Depends(get_current_user)):
    """Extend download expiry (premium feature)"""
    # Check if user is premium (optional)
    user_data = await db.users.find_one({"id": user["id"]})
    is_premium = user_data.get("plan", "free") in ["pro", "premium", "enterprise"]
    
    if not is_premium:
        raise HTTPException(
            status_code=403, 
            detail="Download extension is a premium feature. Upgrade to extend downloads."
        )
    
    service = get_download_service(db)
    result = await service.extend_download(download_id, user["id"])
    
    if not result:
        raise HTTPException(status_code=404, detail="Download not found")
    
    if result.get("expired"):
        raise HTTPException(status_code=410, detail=result.get("error"))
    
    return result


@router.delete("/{download_id}")
async def delete_download(download_id: str, user: dict = Depends(get_current_user)):
    """Manually delete a download before expiry"""
    download = await db.temporary_downloads.find_one({
        "id": download_id,
        "user_id": user["id"]
    })
    
    if not download:
        raise HTTPException(status_code=404, detail="Download not found")
    
    # Delete file
    file_path = Path(download.get("file_path", ""))
    if file_path.exists():
        file_path.unlink()
    
    # Remove from database
    await db.temporary_downloads.delete_one({"id": download_id})
    
    return {"success": True, "message": "Download deleted"}


@router.get("/admin/stats")
async def get_download_stats(user: dict = Depends(get_current_user)):
    """Get download statistics (admin only)"""
    if user.get("role") not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    service = get_download_service(db)
    stats = await service.get_stats()
    
    return stats
