"""
Generated Files Cleanup Service
Automatically deletes all generated files (images, videos, PDFs) after 5 minutes
"""
import asyncio
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
import logging
import shutil

logger = logging.getLogger(__name__)

# Configuration
FILE_EXPIRY_MINUTES = 30  # Increased from 5 to 30 minutes
CLEANUP_INTERVAL_SECONDS = 60  # Run cleanup every minute
GENERATED_DIR = Path("/app/backend/static/generated")

# File types to clean up
CLEANUP_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.webp', '.gif',  # Images
    '.mp4', '.webm', '.mov', '.avi',            # Videos
    '.mp3', '.wav', '.ogg', '.m4a',             # Audio
    '.pdf', '.doc', '.docx',                    # Documents
}


class GeneratedFilesCleanupService:
    """Automatically cleans up generated files after expiry"""
    
    def __init__(self, db):
        self.db = db
        self._running = False
        self._cleanup_task = None
        
        # Ensure generated directory exists
        GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    
    async def start(self):
        """Start the cleanup service"""
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info(f"Generated files cleanup service started (expiry: {FILE_EXPIRY_MINUTES} minutes)")
    
    async def stop(self):
        """Stop the cleanup service"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
        logger.info("Generated files cleanup service stopped")
    
    async def _cleanup_loop(self):
        """Background loop to clean up expired files"""
        while self._running:
            try:
                await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
                await self._cleanup_expired_files()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Generated files cleanup error: {e}")
    
    async def _cleanup_expired_files(self):
        """Remove expired generated files from disk and database"""
        now = time.time()
        expiry_threshold = now - (FILE_EXPIRY_MINUTES * 60)
        
        deleted_count = 0
        errors = []
        
        try:
            # Clean up files from the generated directory
            if GENERATED_DIR.exists():
                for file_path in GENERATED_DIR.iterdir():
                    if file_path.is_file():
                        # Check if file extension is in cleanup list
                        if file_path.suffix.lower() in CLEANUP_EXTENSIONS:
                            # Check file modification time
                            try:
                                mtime = file_path.stat().st_mtime
                                if mtime < expiry_threshold:
                                    file_path.unlink()
                                    deleted_count += 1
                                    logger.debug(f"Deleted expired file: {file_path.name}")
                            except Exception as e:
                                errors.append(f"{file_path.name}: {e}")
            
            # Clean up database records for scene_assets older than 5 minutes
            expiry_time = datetime.now(timezone.utc) - timedelta(minutes=FILE_EXPIRY_MINUTES)
            
            # Delete old scene assets
            result = await self.db.scene_assets.delete_many({
                "created_at": {"$lt": expiry_time}
            })
            if result.deleted_count > 0:
                logger.info(f"Deleted {result.deleted_count} expired scene assets from database")
            
            # Delete old voice tracks
            result = await self.db.voice_tracks.delete_many({
                "created_at": {"$lt": expiry_time}
            })
            if result.deleted_count > 0:
                logger.info(f"Deleted {result.deleted_count} expired voice tracks from database")
            
            # Delete old render jobs (but keep completed ones for history)
            result = await self.db.render_jobs.delete_many({
                "created_at": {"$lt": expiry_time},
                "status": {"$in": ["PENDING", "PROCESSING", "FAILED"]}
            })
            if result.deleted_count > 0:
                logger.info(f"Deleted {result.deleted_count} expired render jobs from database")
            
            # Update completed render jobs to mark files as expired
            await self.db.render_jobs.update_many(
                {
                    "created_at": {"$lt": expiry_time},
                    "status": "COMPLETED",
                    "files_expired": {"$ne": True}
                },
                {
                    "$set": {
                        "files_expired": True,
                        "files_expired_at": datetime.now(timezone.utc)
                    }
                }
            )
            
            if deleted_count > 0:
                logger.info(f"Cleanup complete: {deleted_count} expired files deleted")
            
            if errors:
                logger.warning(f"Cleanup errors: {len(errors)} files could not be deleted")
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    async def get_file_expiry_info(self, file_path: str) -> dict:
        """Get expiry information for a file"""
        try:
            full_path = GENERATED_DIR / Path(file_path).name
            if full_path.exists():
                mtime = full_path.stat().st_mtime
                created_at = datetime.fromtimestamp(mtime, tz=timezone.utc)
                expires_at = created_at + timedelta(minutes=FILE_EXPIRY_MINUTES)
                remaining_seconds = (expires_at - datetime.now(timezone.utc)).total_seconds()
                
                return {
                    "created_at": created_at.isoformat(),
                    "expires_at": expires_at.isoformat(),
                    "remaining_seconds": max(0, int(remaining_seconds)),
                    "remaining_minutes": max(0, int(remaining_seconds / 60)),
                    "is_expired": remaining_seconds <= 0
                }
        except Exception as e:
            logger.error(f"Error getting file expiry info: {e}")
        
        return {
            "created_at": None,
            "expires_at": None,
            "remaining_seconds": 0,
            "remaining_minutes": 0,
            "is_expired": True
        }
    
    async def get_stats(self) -> dict:
        """Get cleanup service statistics"""
        try:
            total_files = 0
            total_size = 0
            expiring_soon = 0
            
            now = time.time()
            soon_threshold = now - ((FILE_EXPIRY_MINUTES - 1) * 60)  # Files expiring in next minute
            
            if GENERATED_DIR.exists():
                for file_path in GENERATED_DIR.iterdir():
                    if file_path.is_file() and file_path.suffix.lower() in CLEANUP_EXTENSIONS:
                        total_files += 1
                        total_size += file_path.stat().st_size
                        mtime = file_path.stat().st_mtime
                        if mtime < soon_threshold:
                            expiring_soon += 1
            
            return {
                "total_files": total_files,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "expiring_soon": expiring_soon,
                "expiry_minutes": FILE_EXPIRY_MINUTES,
                "cleanup_interval_seconds": CLEANUP_INTERVAL_SECONDS
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}


# Singleton instance
_cleanup_service = None

def get_cleanup_service(db=None):
    """Get or create the cleanup service singleton"""
    global _cleanup_service
    if _cleanup_service is None and db is not None:
        _cleanup_service = GeneratedFilesCleanupService(db)
    return _cleanup_service

async def start_cleanup_service(db):
    """Start the cleanup service"""
    service = get_cleanup_service(db)
    if service:
        await service.start()
    return service

async def stop_cleanup_service():
    """Stop the cleanup service"""
    global _cleanup_service
    if _cleanup_service:
        await _cleanup_service.stop()
        _cleanup_service = None
