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
    """Get all active downloads for current user plus completed generation jobs"""
    downloads = []
    
    # Get from temporary_downloads collection
    service = get_download_service(db)
    temp_downloads = await service.get_user_downloads(user["id"])
    downloads.extend(temp_downloads)
    
    # Also get from completed generation jobs (last 24 hours)
    from datetime import timedelta
    one_day_ago = datetime.now(timezone.utc) - timedelta(hours=24)
    
    # Get completed comic jobs
    comic_jobs = await db.photo_to_comic_jobs.find({
        "userId": user["id"],
        "status": "COMPLETED",
        "createdAt": {"$gte": one_day_ago.isoformat()}
    }, {"_id": 0}).sort("createdAt", -1).limit(20).to_list(20)
    
    for job in comic_jobs:
        # For comic avatar
        if job.get("resultUrl"):
            downloads.append({
                "id": f"job_{job.get('id')}",
                "filename": f"comic_{job.get('mode', 'avatar')}_{job.get('id', '')[:8]}.png",
                "file_type": "image/png",
                "feature": job.get("mode", "comic_avatar"),
                "created_at": job.get("createdAt"),
                "expires_at": None,
                "downloaded": False,
                "preview_url": job.get("resultUrl") if job.get("resultUrl", "").startswith("data:") else None,
                "download_url": job.get("resultUrl")
            })
        
        # For comic strip panels
        if job.get("panels"):
            for i, panel in enumerate(job.get("panels", [])):
                if panel.get("imageUrl"):
                    downloads.append({
                        "id": f"job_{job.get('id')}_panel_{i+1}",
                        "filename": f"comic_strip_panel_{i+1}_{job.get('id', '')[:8]}.png",
                        "file_type": "image/png",
                        "feature": "comic_strip",
                        "created_at": job.get("createdAt"),
                        "expires_at": None,
                        "downloaded": False,
                        "preview_url": panel.get("imageUrl") if panel.get("imageUrl", "").startswith("data:") else None,
                        "download_url": panel.get("imageUrl")
                    })
    
    return {
        "downloads": downloads,
        "total": len(downloads),
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


@router.get("/{download_id}/url")
async def get_download_url(download_id: str, user: dict = Depends(get_current_user)):
    """Get the download URL for a file"""
    service = get_download_service(db)
    download = await service.get_download(download_id, user["id"])
    
    if not download:
        raise HTTPException(status_code=404, detail="Download not found")
    
    if download.get("expired"):
        raise HTTPException(status_code=410, detail="Download has expired. Please generate again.")
    
    # Return the download URL
    file_path = download.get("file_path", "")
    if file_path.startswith("http"):
        return {"url": file_path, "expires_at": download.get("expires_at")}
    
    # Return API URL for local files
    return {
        "url": f"/api/downloads/{download_id}/file",
        "expires_at": download.get("expires_at")
    }


@router.post("/{download_id}/mark-downloaded")
async def mark_as_downloaded(download_id: str, user: dict = Depends(get_current_user)):
    """Mark a download as downloaded"""
    result = await db.temporary_downloads.update_one(
        {"id": download_id, "user_id": user["id"]},
        {"$set": {"downloaded": True, "downloaded_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Download not found")
    
    return {"success": True, "message": "Download marked as downloaded"}


@router.get("/admin/stats")
async def get_download_stats(user: dict = Depends(get_current_user)):
    """Get download statistics (admin only)"""
    user_role = (user.get("role") or "").upper()
    if user_role not in ["ADMIN", "SUPERADMIN"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    service = get_download_service(db)
    stats = await service.get_stats()
    
    return stats
