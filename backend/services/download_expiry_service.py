"""
Download Expiry Service
Manages temporary downloads with 5-minute expiry
Auto-deletes expired files to save storage
"""
import asyncio
import os
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Configuration
DOWNLOAD_EXPIRY_MINUTES = 30  # Increased from 5 to 30 minutes
CLEANUP_INTERVAL_SECONDS = 60  # Check for expired files every minute
DOWNLOADS_DIR = Path("/app/backend/static/downloads")


class DownloadExpiryService:
    """Manages temporary downloads with automatic expiry"""
    
    def __init__(self, db):
        self.db = db
        self._running = False
        self._cleanup_task = None
        
        # Ensure downloads directory exists
        DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    
    async def start(self):
        """Start the expiry cleanup service"""
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Download expiry service started")
    
    async def stop(self):
        """Stop the expiry cleanup service"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
        logger.info("Download expiry service stopped")
    
    async def _cleanup_loop(self):
        """Background loop to clean up expired downloads"""
        while self._running:
            try:
                await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
                await self._cleanup_expired_downloads()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Download cleanup error: {e}")
    
    async def _cleanup_expired_downloads(self):
        """Remove expired downloads from disk and database"""
        now = datetime.now(timezone.utc)
        
        # Find expired downloads
        expired = await self.db.temporary_downloads.find({
            "expires_at": {"$lt": now}
        }).to_list(100)
        
        deleted_count = 0
        for download in expired:
            try:
                file_path_str = download.get("file_path", "")
                
                # Skip if file_path is a base64 data URL (not an actual file)
                if not file_path_str or file_path_str.startswith("data:"):
                    # Just remove from database, no file to delete
                    await self.db.temporary_downloads.delete_one({"_id": download["_id"]})
                    deleted_count += 1
                    continue
                
                # Delete file from disk if it's a valid path
                file_path = Path(file_path_str)
                if file_path.exists():
                    file_path.unlink()
                    deleted_count += 1
                
                # Remove from database
                await self.db.temporary_downloads.delete_one({"_id": download["_id"]})
                
            except Exception as e:
                logger.error(f"Failed to delete expired download {download.get('id')}: {e}")
                # Still try to remove from database to prevent repeated errors
                try:
                    await self.db.temporary_downloads.delete_one({"_id": download["_id"]})
                except Exception:
                    pass
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} expired downloads")
    
    async def register_download(
        self,
        user_id: str,
        file_path: str,
        original_filename: str,
        file_type: str,
        feature: str
    ) -> Dict:
        """Register a new temporary download"""
        download_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=DOWNLOAD_EXPIRY_MINUTES)
        
        download_record = {
            "id": download_id,
            "user_id": user_id,
            "file_path": file_path,
            "original_filename": original_filename,
            "file_type": file_type,
            "feature": feature,
            "created_at": now,
            "expires_at": expires_at,
            "downloaded": False,
            "download_count": 0
        }
        
        await self.db.temporary_downloads.insert_one(download_record)
        
        return {
            "id": download_id,
            "download_id": download_id,
            "expires_at": expires_at.isoformat(),
            "expires_in_seconds": DOWNLOAD_EXPIRY_MINUTES * 60,
            "expires_in_minutes": DOWNLOAD_EXPIRY_MINUTES,
            "message": f"Your download will be available for {DOWNLOAD_EXPIRY_MINUTES} minutes. Please download before it expires."
        }
    
    async def get_download(self, download_id: str, user_id: str) -> Optional[Dict]:
        """Get download info and validate access"""
        download = await self.db.temporary_downloads.find_one({
            "id": download_id,
            "user_id": user_id
        })
        
        if not download:
            return None
        
        now = datetime.now(timezone.utc)
        expires_at = download.get("expires_at")
        
        # Check if expired
        if expires_at and now > expires_at:
            # Clean up expired download
            file_path = Path(download.get("file_path", ""))
            if file_path.exists():
                file_path.unlink()
            await self.db.temporary_downloads.delete_one({"id": download_id})
            return {"error": "Download has expired", "expired": True}
        
        # Calculate remaining time
        remaining_seconds = int((expires_at - now).total_seconds()) if expires_at else 0
        
        # Update download count
        await self.db.temporary_downloads.update_one(
            {"id": download_id},
            {
                "$set": {"downloaded": True, "last_downloaded_at": now},
                "$inc": {"download_count": 1}
            }
        )
        
        return {
            "file_path": download.get("file_path"),
            "original_filename": download.get("original_filename"),
            "file_type": download.get("file_type"),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "remaining_seconds": remaining_seconds,
            "remaining_minutes": remaining_seconds // 60,
            "expired": False
        }
    
    async def get_user_downloads(self, user_id: str) -> list:
        """Get all active downloads for a user"""
        now = datetime.now(timezone.utc)
        
        downloads = await self.db.temporary_downloads.find({
            "user_id": user_id,
            "expires_at": {"$gt": now}
        }).sort("created_at", -1).to_list(20)
        
        result = []
        for d in downloads:
            expires_at = d.get("expires_at")
            remaining = int((expires_at - now).total_seconds()) if expires_at else 0
            
            result.append({
                "download_id": d.get("id"),
                "filename": d.get("original_filename"),
                "feature": d.get("feature"),
                "created_at": d.get("created_at").isoformat() if d.get("created_at") else None,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "remaining_seconds": remaining,
                "remaining_minutes": remaining // 60,
                "downloaded": d.get("downloaded", False)
            })
        
        return result
    
    async def extend_download(self, download_id: str, user_id: str, minutes: int = 5) -> Optional[Dict]:
        """Extend download expiry (for premium users)"""
        download = await self.db.temporary_downloads.find_one({
            "id": download_id,
            "user_id": user_id
        })
        
        if not download:
            return None
        
        now = datetime.now(timezone.utc)
        current_expiry = download.get("expires_at")
        
        # Can't extend if already expired
        if current_expiry and now > current_expiry:
            return {"error": "Download has already expired", "expired": True}
        
        new_expiry = (current_expiry or now) + timedelta(minutes=minutes)
        
        await self.db.temporary_downloads.update_one(
            {"id": download_id},
            {"$set": {"expires_at": new_expiry}}
        )
        
        remaining = int((new_expiry - now).total_seconds())
        
        return {
            "download_id": download_id,
            "new_expires_at": new_expiry.isoformat(),
            "remaining_seconds": remaining,
            "remaining_minutes": remaining // 60,
            "message": f"Download extended by {minutes} minutes"
        }
    
    async def get_stats(self) -> Dict:
        """Get download statistics"""
        now = datetime.now(timezone.utc)
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        total_active = await self.db.temporary_downloads.count_documents({
            "expires_at": {"$gt": now}
        })
        
        created_last_hour = await self.db.temporary_downloads.count_documents({
            "created_at": {"$gte": hour_ago}
        })
        
        created_last_day = await self.db.temporary_downloads.count_documents({
            "created_at": {"$gte": day_ago}
        })
        
        total_downloaded = await self.db.temporary_downloads.count_documents({
            "downloaded": True
        })
        
        return {
            "active_downloads": total_active,
            "created_last_hour": created_last_hour,
            "created_last_day": created_last_day,
            "total_downloaded": total_downloaded,
            "expiry_minutes": DOWNLOAD_EXPIRY_MINUTES
        }


# Singleton instance
_download_service: Optional[DownloadExpiryService] = None


def get_download_service(db) -> DownloadExpiryService:
    """Get or create download service singleton"""
    global _download_service
    if _download_service is None:
        _download_service = DownloadExpiryService(db)
    return _download_service
