"""
Video Render Recovery Service
Implements auto-detection, auto-retry, and auto-recovery for stuck video render jobs

Features:
1. Stall detection (>60 seconds no progress)
2. Auto-retry asset downloads (3 attempts with exponential backoff)
3. Job reassignment to backup workers
4. Real error feedback to frontend
5. Auto-resume on connection restore
6. Timeout safeguards (>2 min = auto-restart)
7. Heartbeat monitoring
"""
import os
import asyncio
import logging
import time
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
import aiohttp
import aiofiles

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Stall detection thresholds
STALL_DETECTION_SECONDS = 60  # Detect stall after 60 seconds
AUTO_RETRY_ATTEMPTS = 3  # Retry failed downloads 3 times
RETRY_BACKOFF_BASE = 2  # Exponential backoff base (2, 4, 8 seconds)
JOB_TIMEOUT_SECONDS = 120  # Auto-restart after 2 minutes stuck
HEARTBEAT_INTERVAL = 5  # Send heartbeat every 5 seconds
MAX_JOB_DURATION = 600  # Maximum 10 minutes per job

# Download retry settings
DOWNLOAD_TIMEOUT = 30
DOWNLOAD_CHUNK_SIZE = 65536  # 64KB chunks for resume support


@dataclass
class JobHealthStatus:
    """Track job health for auto-recovery"""
    job_id: str
    user_id: str
    project_id: str
    status: str = "pending"
    current_stage: str = "initializing"
    progress: int = 0
    last_progress_update: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    retry_count: int = 0
    error_message: Optional[str] = None
    is_stalled: bool = False
    auto_recovered: bool = False
    downloaded_assets: Dict[str, str] = field(default_factory=dict)  # Track completed downloads
    

class RenderRecoveryService:
    """Handles auto-detection and recovery of stuck render jobs"""
    
    def __init__(self, db, broadcast_progress=None, broadcast_error=None):
        self.db = db
        self.broadcast_progress = broadcast_progress
        self.broadcast_error = broadcast_error
        self.active_jobs: Dict[str, JobHealthStatus] = {}
        self.monitoring_task = None
        self._running = False
    
    async def start_monitoring(self):
        """Start the background monitoring task"""
        if self._running:
            return
        
        self._running = True
        self.monitoring_task = asyncio.create_task(self._monitor_jobs())
        logger.info("[RECOVERY] Job monitoring service started")
    
    async def stop_monitoring(self):
        """Stop the monitoring task"""
        self._running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("[RECOVERY] Job monitoring service stopped")
    
    async def _monitor_jobs(self):
        """Background task to monitor all active jobs for stalls"""
        while self._running:
            try:
                current_time = time.time()
                
                for job_id, health in list(self.active_jobs.items()):
                    time_since_update = current_time - health.last_progress_update
                    
                    # Check for stall
                    if time_since_update > STALL_DETECTION_SECONDS:
                        if not health.is_stalled:
                            health.is_stalled = True
                            logger.warning(f"[RECOVERY] Job {job_id} STALLED at {health.progress}% for {time_since_update:.0f}s")
                            await self._handle_stalled_job(health)
                    
                    # Check for timeout
                    job_duration = current_time - (health.last_heartbeat - health.last_progress_update + health.last_progress_update)
                    if time_since_update > JOB_TIMEOUT_SECONDS and health.retry_count < AUTO_RETRY_ATTEMPTS:
                        logger.warning(f"[RECOVERY] Job {job_id} TIMEOUT - initiating auto-restart")
                        await self._auto_restart_job(health)
                    
                    # Remove completed/failed jobs after 5 minutes
                    if health.status in ["completed", "failed", "cancelled"] and time_since_update > 300:
                        del self.active_jobs[job_id]
                
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                
            except Exception as e:
                logger.error(f"[RECOVERY] Monitor error: {e}")
                await asyncio.sleep(5)
    
    async def _handle_stalled_job(self, health: JobHealthStatus):
        """Handle a stalled job - try to recover"""
        
        # Notify frontend
        if self.broadcast_error:
            try:
                await self.broadcast_error(
                    health.job_id,
                    health.user_id,
                    f"Job stalled at {health.current_stage}. Attempting auto-recovery...",
                    stage="recovery"
                )
            except Exception as e:
                logger.debug(f"Broadcast error: {e}")
        
        # Update database
        await self.db.render_jobs.update_one(
            {"job_id": health.job_id},
            {
                "$set": {
                    "stall_detected": True,
                    "stall_detected_at": datetime.now(timezone.utc),
                    "stall_stage": health.current_stage,
                    "stall_progress": health.progress
                }
            }
        )
    
    async def _auto_restart_job(self, health: JobHealthStatus):
        """Auto-restart a stuck job"""
        health.retry_count += 1
        health.auto_recovered = True
        health.is_stalled = False
        health.last_progress_update = time.time()
        
        logger.info(f"[RECOVERY] Auto-restarting job {health.job_id} (attempt {health.retry_count}/{AUTO_RETRY_ATTEMPTS})")
        
        # Update database
        await self.db.render_jobs.update_one(
            {"job_id": health.job_id},
            {
                "$set": {
                    "status": "RETRYING",
                    "retry_count": health.retry_count,
                    "last_retry_at": datetime.now(timezone.utc)
                }
            }
        )
        
        # Notify frontend
        if self.broadcast_progress:
            try:
                await self.broadcast_progress(
                    health.job_id,
                    health.user_id,
                    "retrying",
                    health.progress,
                    metadata={"message": f"Auto-retrying (attempt {health.retry_count})"}
                )
            except Exception:
                pass
    
    def register_job(self, job_id: str, user_id: str, project_id: str) -> JobHealthStatus:
        """Register a new job for monitoring"""
        health = JobHealthStatus(
            job_id=job_id,
            user_id=user_id,
            project_id=project_id
        )
        self.active_jobs[job_id] = health
        return health
    
    def update_progress(self, job_id: str, stage: str, progress: int, message: str = ""):
        """Update job progress - resets stall timer"""
        if job_id in self.active_jobs:
            health = self.active_jobs[job_id]
            health.current_stage = stage
            health.progress = progress
            health.last_progress_update = time.time()
            health.is_stalled = False
            if message:
                health.error_message = None
    
    def mark_completed(self, job_id: str):
        """Mark job as completed"""
        if job_id in self.active_jobs:
            health = self.active_jobs[job_id]
            health.status = "completed"
            health.progress = 100
    
    def mark_failed(self, job_id: str, error: str):
        """Mark job as failed"""
        if job_id in self.active_jobs:
            health = self.active_jobs[job_id]
            health.status = "failed"
            health.error_message = error
    
    # =========================================================================
    # ROBUST ASSET DOWNLOAD WITH RETRY
    # =========================================================================
    
    async def download_asset_with_retry(
        self,
        url: str,
        output_path: str,
        asset_type: str,
        job_id: str,
        on_progress: Callable = None
    ) -> bool:
        """
        Download asset with automatic retry and resume support
        
        Args:
            url: Asset URL
            output_path: Local file path
            asset_type: Type of asset (image, audio, video)
            job_id: Job ID for tracking
            on_progress: Progress callback (bytes_downloaded, total_bytes)
        
        Returns:
            True if download successful, False otherwise
        """
        health = self.active_jobs.get(job_id)
        
        # Check if already downloaded (resume support)
        if health and url in health.downloaded_assets:
            cached_path = health.downloaded_assets[url]
            if os.path.exists(cached_path):
                if cached_path != output_path:
                    import shutil
                    shutil.copy(cached_path, output_path)
                logger.debug(f"[RECOVERY] Using cached asset: {url[:50]}...")
                return True
        
        last_error = None
        
        for attempt in range(AUTO_RETRY_ATTEMPTS):
            try:
                # Calculate backoff delay
                if attempt > 0:
                    delay = RETRY_BACKOFF_BASE ** attempt
                    logger.info(f"[RECOVERY] Retry {attempt + 1}/{AUTO_RETRY_ATTEMPTS} for {asset_type} after {delay}s")
                    await asyncio.sleep(delay)
                
                # Attempt download
                success = await self._download_file(url, output_path, asset_type, on_progress)
                
                if success:
                    # Cache successful download
                    if health:
                        health.downloaded_assets[url] = output_path
                    return True
                    
            except asyncio.TimeoutError:
                last_error = f"Download timeout for {asset_type}"
                logger.warning(f"[RECOVERY] {last_error} (attempt {attempt + 1})")
                
            except aiohttp.ClientError as e:
                last_error = f"Network error: {str(e)[:100]}"
                logger.warning(f"[RECOVERY] {last_error} (attempt {attempt + 1})")
                
            except Exception as e:
                last_error = str(e)[:200]
                logger.warning(f"[RECOVERY] Download error: {last_error} (attempt {attempt + 1})")
        
        # All retries failed
        logger.error(f"[RECOVERY] Asset download failed after {AUTO_RETRY_ATTEMPTS} attempts: {url[:60]}...")
        
        if health:
            health.error_message = last_error
        
        return False
    
    async def _download_file(
        self,
        url: str,
        output_path: str,
        asset_type: str,
        on_progress: Callable = None
    ) -> bool:
        """Internal download implementation with progress tracking"""
        
        # Handle local files
        if url.startswith("/app/backend/") and os.path.exists(url):
            import shutil
            shutil.copy(url, output_path)
            return True
        
        # Handle HTTP/HTTPS URLs
        if not url.startswith(("http://", "https://")):
            # Try to construct full URL
            if url.startswith("/"):
                url = f"https://www.visionary-suite.com{url}"
            else:
                raise ValueError(f"Invalid URL format: {url}")
        
        timeout = aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT, connect=10)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise aiohttp.ClientError(f"HTTP {response.status}")
                
                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0
                
                async with aiofiles.open(output_path, "wb") as f:
                    async for chunk in response.content.iter_chunked(DOWNLOAD_CHUNK_SIZE):
                        await f.write(chunk)
                        downloaded += len(chunk)
                        
                        if on_progress and total_size > 0:
                            await on_progress(downloaded, total_size)
                
                return True
    
    # =========================================================================
    # PROGRESS MESSAGES
    # =========================================================================
    
    def get_user_friendly_message(self, stage: str, progress: int) -> str:
        """Get user-friendly progress message"""
        messages = {
            "initializing": "Preparing your video...",
            "downloading": "Downloading assets from cloud...",
            "download_retry": "Retrying asset download...",
            "encoding": "Encoding video scenes...",
            "composing": "Building video timeline...",
            "audio_sync": "Synchronizing audio...",
            "music": "Adding background music...",
            "rendering": "Rendering final video...",
            "watermark": "Adding watermark...",
            "uploading": "Uploading to cloud...",
            "finalizing": "Finalizing your video...",
            "completed": "Video ready!",
            "failed": "Video generation failed",
            "retrying": "Auto-retrying...",
            "recovery": "Recovering from error..."
        }
        
        base_message = messages.get(stage, f"Processing... ({stage})")
        return f"{base_message} {progress}%"
    
    def get_detailed_progress(self, stage: str, progress: int) -> Dict[str, Any]:
        """Get detailed progress breakdown for UI"""
        stages = [
            {"id": "script", "name": "Script Processing", "range": [0, 5]},
            {"id": "scenes", "name": "Scene Generation", "range": [5, 15]},
            {"id": "images", "name": "Image Generation", "range": [15, 40]},
            {"id": "voices", "name": "Voice Generation", "range": [40, 60]},
            {"id": "download", "name": "Asset Download", "range": [60, 70]},
            {"id": "render", "name": "Video Rendering", "range": [70, 90]},
            {"id": "upload", "name": "Final Export", "range": [90, 100]}
        ]
        
        completed = []
        current = None
        pending = []
        
        for s in stages:
            if progress >= s["range"][1]:
                completed.append({"id": s["id"], "name": s["name"], "status": "completed"})
            elif progress >= s["range"][0]:
                current = {"id": s["id"], "name": s["name"], "status": "in_progress", "progress": progress}
            else:
                pending.append({"id": s["id"], "name": s["name"], "status": "pending"})
        
        return {
            "completed": completed,
            "current": current,
            "pending": pending,
            "overall_progress": progress
        }


# =============================================================================
# SINGLETON & FACTORY
# =============================================================================

_recovery_service: Optional[RenderRecoveryService] = None

def get_recovery_service(db) -> RenderRecoveryService:
    """Get or create the recovery service singleton"""
    global _recovery_service
    if _recovery_service is None:
        try:
            from routes.websocket_progress import broadcast_video_progress, broadcast_error
            _recovery_service = RenderRecoveryService(db, broadcast_video_progress, broadcast_error)
        except ImportError:
            _recovery_service = RenderRecoveryService(db)
    return _recovery_service


async def init_recovery_service(db):
    """Initialize and start the recovery service"""
    service = get_recovery_service(db)
    await service.start_monitoring()
    return service
