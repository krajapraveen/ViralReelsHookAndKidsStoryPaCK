"""
My Downloads — Permanent Asset Downloads

Reads ONLY from user_assets collection.
Shows only assets with status=ready, is_downloadable=true, valid CDN URL.
No temp-expiry logic. All downloads are permanent.
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user

router = APIRouter(prefix="/downloads", tags=["Downloads"])


@router.get("/my-downloads")
async def get_my_downloads(user: dict = Depends(get_current_user)):
    """Get all permanent downloadable assets for current user."""
    try:
        assets = await db.user_assets.find(
            {
                "user_id": user["id"],
                "is_downloadable": True,
                "status": "ready",
            },
            {"_id": 0}
        ).sort("created_at", -1).limit(100).to_list(100)

        # Presign CDN URLs
        from utils.r2_presign import presign_url
        downloads = []
        for asset in assets:
            cdn_url = asset.get("cdn_url", "")
            presigned = presign_url(cdn_url) if cdn_url and ".r2.dev/" in cdn_url else cdn_url

            downloads.append({
                "id": asset.get("asset_id", ""),
                "filename": asset.get("display_name", "Download"),
                "file_type": asset.get("mime_type", "application/octet-stream"),
                "feature": asset.get("asset_type", "unknown"),
                "created_at": asset.get("created_at"),
                "download_url": presigned,
                "permanent": True,
                "status": "ready",
                "downloaded": asset.get("downloaded", False),
            })

        return {
            "downloads": downloads,
            "total": len(downloads),
            "permanent": True,
        }
    except Exception as e:
        logger.error(f"Error in get_my_downloads: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch downloads")


@router.get("/{download_id}/url")
async def get_download_url(download_id: str, user: dict = Depends(get_current_user)):
    """Get presigned download URL for an asset."""
    asset = await db.user_assets.find_one(
        {"asset_id": download_id, "user_id": user["id"], "status": "ready"},
        {"_id": 0}
    )

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    cdn_url = asset.get("cdn_url", "")
    if not cdn_url:
        raise HTTPException(status_code=404, detail="No download URL available")

    from utils.r2_presign import presign_url
    url = presign_url(cdn_url) if ".r2.dev/" in cdn_url else cdn_url

    return {"url": url, "permanent": True}


@router.post("/{download_id}/mark-downloaded")
async def mark_downloaded(download_id: str, user: dict = Depends(get_current_user)):
    """Mark an asset as downloaded."""
    result = await db.user_assets.update_one(
        {"asset_id": download_id, "user_id": user["id"]},
        {"$set": {"downloaded": True, "downloaded_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"success": True}


@router.delete("/{download_id}")
async def delete_download(download_id: str, user: dict = Depends(get_current_user)):
    """Remove an asset from user's downloads (soft delete)."""
    result = await db.user_assets.update_one(
        {"asset_id": download_id, "user_id": user["id"]},
        {"$set": {"is_downloadable": False, "status": "archived"}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"success": True}
