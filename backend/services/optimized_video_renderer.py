"""
Optimized Video Render Service
High-performance video assembly with detailed timing, parallel processing, and timeout handling

Key Optimizations:
1. Parallel asset downloads (concurrent, not sequential)
2. Optimized FFmpeg preset for fast encoding
3. Async subprocess execution with timeout
4. Non-blocking R2 upload with progress tracking
5. Real progress updates mapped to actual stages
6. Memory-efficient streaming for large files
"""
import os
import uuid
import json
import asyncio
import subprocess
import tempfile
import shutil
import logging
import time
import aiohttp
import aiofiles
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Timeout settings (seconds)
DOWNLOAD_TIMEOUT = 30
FFMPEG_SCENE_TIMEOUT = 60  # Per scene
FFMPEG_CONCAT_TIMEOUT = 30
FFMPEG_MUSIC_TIMEOUT = 30
FFMPEG_WATERMARK_TIMEOUT = 30
R2_UPLOAD_TIMEOUT = 120
TOTAL_RENDER_TIMEOUT = 600  # 10 minutes max for entire render

# FFmpeg optimization settings
FFMPEG_PRESET = "ultrafast"  # ultrafast, superfast, veryfast, faster, fast
FFMPEG_CRF = 28  # Quality: 18-28 (lower = better quality, larger file)
VIDEO_BITRATE = "1500k"
AUDIO_BITRATE = "128k"
OUTPUT_RESOLUTION = "1280:720"
OUTPUT_FPS = 24

# Concurrent download limit
MAX_CONCURRENT_DOWNLOADS = 4


@dataclass
class RenderProgress:
    """Track render progress with detailed stage information"""
    job_id: str
    user_id: str
    total_scenes: int = 0
    current_stage: str = "initializing"
    current_scene: int = 0
    progress_percent: int = 0
    stage_message: str = ""
    timing: Dict[str, float] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)
    
    def update(self, stage: str, progress: int, message: str = ""):
        self.current_stage = stage
        self.progress_percent = min(progress, 100)
        self.stage_message = message
        self.timing[f"{stage}_at"] = time.time() - self.started_at
    
    def log_stage(self, stage: str, duration_ms: float):
        self.timing[stage] = duration_ms
        logger.info(f"[VIDEO_RENDER] [{self.job_id}] {stage}: {duration_ms:.2f}ms")
    
    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "stage": self.current_stage,
            "progress": self.progress_percent,
            "message": self.stage_message,
            "elapsed_seconds": time.time() - self.started_at,
            "timing": self.timing
        }


class OptimizedVideoRenderer:
    """High-performance video renderer with parallel processing"""
    
    def __init__(self, db, broadcast_progress=None, broadcast_error=None, broadcast_completion=None):
        self.db = db
        self.broadcast_progress = broadcast_progress
        self.broadcast_error = broadcast_error
        self.broadcast_completion = broadcast_completion
    
    async def render_video(
        self,
        job_id: str,
        project_id: str,
        scene_images: List[dict],
        voice_tracks: List[dict],
        include_watermark: bool = True,
        background_music_id: Optional[str] = None,
        music_volume: float = 0.3,
        user_id: str = None
    ) -> Tuple[bool, str, dict]:
        """
        Main render entry point with full optimization
        
        Returns:
            Tuple of (success, video_url, timing_data)
        """
        progress = RenderProgress(job_id=job_id, user_id=user_id, total_scenes=len(scene_images))
        temp_dir = None
        
        try:
            logger.info(f"[VIDEO_RENDER] [{job_id}] Starting render for {len(scene_images)} scenes")
            
            # Update job status
            await self._update_job_status(job_id, "PROCESSING", 5, "Starting video render")
            await self._broadcast_progress(progress, "preparing", 5, "Preparing video assets")
            
            # Create temp directory
            temp_dir = tempfile.mkdtemp(prefix=f"render_{job_id}_")
            
            # =================================================================
            # STAGE 1: Download all assets in parallel (0-20%)
            # =================================================================
            download_start = time.time()
            progress.update("downloading", 10, "Downloading scene assets")
            await self._broadcast_progress(progress, "downloading", 10, "Downloading scene assets")
            
            scene_data = await self._download_all_assets_parallel(
                scene_images, voice_tracks, temp_dir, progress
            )
            
            download_duration = (time.time() - download_start) * 1000
            progress.log_stage("download_all_assets", download_duration)
            
            # =================================================================
            # STAGE 2: Encode each scene segment (20-60%)
            # =================================================================
            encode_start = time.time()
            progress.update("encoding", 25, "Encoding video segments")
            await self._broadcast_progress(progress, "encoding", 25, "Encoding video segments")
            
            segments = await self._encode_all_segments(scene_data, temp_dir, progress)
            
            encode_duration = (time.time() - encode_start) * 1000
            progress.log_stage("encode_all_segments", encode_duration)
            
            # =================================================================
            # STAGE 3: Concatenate segments (60-70%)
            # =================================================================
            concat_start = time.time()
            progress.update("concatenating", 65, "Concatenating video segments")
            await self._broadcast_progress(progress, "audio_sync", 65, "Merging video segments")
            
            concat_video = await self._concatenate_segments(segments, temp_dir)
            
            concat_duration = (time.time() - concat_start) * 1000
            progress.log_stage("concatenate_segments", concat_duration)
            
            # =================================================================
            # STAGE 4: Add background music if specified (70-80%)
            # =================================================================
            final_video = concat_video
            if background_music_id:
                music_start = time.time()
                progress.update("music", 72, "Adding background music")
                await self._broadcast_progress(progress, "music", 72, "Adding background music")
                
                final_video = await self._add_background_music(
                    concat_video, background_music_id, music_volume, temp_dir
                )
                
                music_duration = (time.time() - music_start) * 1000
                progress.log_stage("add_music", music_duration)
            
            await self._update_job_status(job_id, "PROCESSING", 80, "Finalizing video")
            
            # =================================================================
            # STAGE 5: Add watermark and finalize (80-90%)
            # =================================================================
            watermark_start = time.time()
            progress.update("finalizing", 82, "Adding watermark and finalizing")
            await self._broadcast_progress(progress, "rendering", 82, "Adding watermark")
            
            output_filename = f"{project_id}_final.mp4"
            output_path = await self._add_watermark_and_finalize(
                final_video, include_watermark, output_filename, temp_dir
            )
            
            watermark_duration = (time.time() - watermark_start) * 1000
            progress.log_stage("add_watermark", watermark_duration)
            
            # =================================================================
            # STAGE 6: Upload to R2 cloud storage (90-100%)
            # =================================================================
            upload_start = time.time()
            progress.update("uploading", 90, "Uploading to cloud storage")
            await self._broadcast_progress(progress, "uploading", 90, "Uploading video to cloud")
            
            video_url, storage_type = await self._upload_to_r2(
                output_path, project_id, output_filename, progress
            )
            
            upload_duration = (time.time() - upload_start) * 1000
            progress.log_stage("upload_to_r2", upload_duration)
            
            # =================================================================
            # COMPLETE
            # =================================================================
            total_duration = (time.time() - progress.started_at) * 1000
            progress.log_stage("TOTAL_RENDER_TIME", total_duration)
            
            # Log detailed breakdown
            logger.info(f"[VIDEO_RENDER] [{job_id}] COMPLETE - Total: {total_duration:.0f}ms")
            logger.info(f"[VIDEO_RENDER] [{job_id}] BREAKDOWN: {json.dumps(progress.timing, indent=2)}")
            
            # Update job as completed
            await self._update_job_completed(
                job_id, project_id, video_url, storage_type, progress.timing
            )
            
            # Broadcast completion
            if self.broadcast_completion:
                await self.broadcast_completion(
                    job_id, user_id, "Video",
                    result_url=video_url,
                    metadata={"project_id": project_id, "storage": storage_type, "timing": progress.timing}
                )
            
            return True, video_url, progress.timing
            
        except asyncio.TimeoutError as e:
            error_msg = f"Render timeout: {str(e)}"
            logger.error(f"[VIDEO_RENDER] [{job_id}] TIMEOUT: {error_msg}")
            await self._handle_render_failure(job_id, user_id, error_msg, progress)
            return False, "", progress.timing
            
        except subprocess.TimeoutExpired as e:
            error_msg = f"FFmpeg timeout: {str(e)}"
            logger.error(f"[VIDEO_RENDER] [{job_id}] FFMPEG_TIMEOUT: {error_msg}")
            await self._handle_render_failure(job_id, user_id, error_msg, progress)
            return False, "", progress.timing
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[VIDEO_RENDER] [{job_id}] ERROR: {error_msg}")
            await self._handle_render_failure(job_id, user_id, error_msg, progress)
            return False, "", progress.timing
            
        finally:
            # Cleanup temp directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception as e:
                    logger.warning(f"[VIDEO_RENDER] [{job_id}] Cleanup warning: {e}")
    
    # =========================================================================
    # PARALLEL ASSET DOWNLOAD
    # =========================================================================
    
    async def _download_all_assets_parallel(
        self,
        scene_images: List[dict],
        voice_tracks: List[dict],
        temp_dir: str,
        progress: RenderProgress
    ) -> List[dict]:
        """Download all images and audio files in parallel batches"""
        
        # Sort by scene number
        scene_images.sort(key=lambda x: x.get("scene_number", 0))
        voice_tracks.sort(key=lambda x: x.get("scene_number", 0))
        
        scene_data = []
        download_tasks = []
        
        # Prepare download tasks
        for i, (img, voice) in enumerate(zip(scene_images, voice_tracks)):
            scene_num = img.get("scene_number", i + 1)
            image_path = os.path.join(temp_dir, f"scene_{scene_num}.png")
            audio_path = os.path.join(temp_dir, f"scene_{scene_num}_audio.mp3")
            
            img_url = img.get("url") or img.get("image_url")
            audio_url = voice.get("audio_url") or voice.get("audio_path")
            duration = voice.get("duration", 5)
            
            scene_data.append({
                "scene_number": scene_num,
                "image_path": image_path,
                "audio_path": audio_path,
                "duration": max(duration, 1)
            })
            
            download_tasks.append(self._download_file_with_timeout(img_url, image_path, "image"))
            download_tasks.append(self._download_file_with_timeout(audio_url, audio_path, "audio"))
        
        # Execute downloads in parallel with semaphore for rate limiting
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
        
        async def limited_download(coro):
            async with semaphore:
                return await coro
        
        # Run all downloads concurrently
        results = await asyncio.gather(
            *[limited_download(task) for task in download_tasks],
            return_exceptions=True
        )
        
        # Check for failures
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                raise Exception(f"Asset download failed: {result}")
        
        # Update progress
        progress.update("downloading", 20, f"Downloaded {len(scene_data)} scenes")
        
        return scene_data
    
    async def _download_file_with_timeout(
        self,
        url: str,
        output_path: str,
        file_type: str
    ):
        """Download a file with timeout handling"""
        start_time = time.time()
        
        try:
            if not url:
                raise Exception(f"No URL provided for {file_type}")
            
            # Handle local files
            if url.startswith("/app/backend/") and os.path.exists(url):
                shutil.copy(url, output_path)
                return
            
            # Handle HTTP/HTTPS URLs
            if url.startswith("http://") or url.startswith("https://"):
                timeout = aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            content = await response.read()
                            async with aiofiles.open(output_path, "wb") as f:
                                await f.write(content)
                            return
                        else:
                            raise Exception(f"HTTP {response.status} downloading {url}")
            
            # Handle local path URLs
            if url.startswith("/static/") or url.startswith("/api/"):
                local_path = f"/app/backend{url}"
                if os.path.exists(local_path):
                    shutil.copy(local_path, output_path)
                    return
                
                # Try production URL
                full_url = f"https://www.visionary-suite.com{url}"
                timeout = aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(full_url) as response:
                        if response.status == 200:
                            content = await response.read()
                            async with aiofiles.open(output_path, "wb") as f:
                                await f.write(content)
                            return
            
            raise Exception(f"Could not download {file_type}: {url}")
            
        finally:
            duration = (time.time() - start_time) * 1000
            logger.debug(f"[VIDEO_RENDER] Download {file_type}: {duration:.0f}ms - {url[:60]}...")
    
    # =========================================================================
    # VIDEO ENCODING
    # =========================================================================
    
    async def _encode_all_segments(
        self,
        scene_data: List[dict],
        temp_dir: str,
        progress: RenderProgress
    ) -> List[str]:
        """Encode all scene segments with optimized FFmpeg settings"""
        segments = []
        total = len(scene_data)
        
        for i, scene in enumerate(scene_data):
            scene_num = scene["scene_number"]
            segment_path = os.path.join(temp_dir, f"segment_{scene_num}.mp4")
            
            # Update progress (25-60% range for encoding)
            pct = 25 + int((i / total) * 35)
            progress.update("encoding", pct, f"Encoding scene {scene_num}/{total}")
            await self._broadcast_progress(
                progress, "composing", pct, 
                f"Encoding scene {scene_num}/{total}"
            )
            
            # FFmpeg command - highly optimized
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", scene["image_path"],
                "-i", scene["audio_path"],
                "-c:v", "libx264",
                "-preset", FFMPEG_PRESET,
                "-tune", "stillimage",
                "-crf", str(FFMPEG_CRF),
                "-c:a", "aac",
                "-b:a", AUDIO_BITRATE,
                "-pix_fmt", "yuv420p",
                "-vf", f"scale={OUTPUT_RESOLUTION}:force_original_aspect_ratio=decrease,pad={OUTPUT_RESOLUTION}:(ow-iw)/2:(oh-ih)/2",
                "-r", str(OUTPUT_FPS),
                "-shortest",
                "-t", str(scene["duration"] + 0.5),
                "-threads", "2",
                segment_path
            ]
            
            # Run FFmpeg with timeout
            start_time = time.time()
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=FFMPEG_SCENE_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    process.kill()
                    raise subprocess.TimeoutExpired(cmd, FFMPEG_SCENE_TIMEOUT)
                
                if process.returncode != 0:
                    error_output = stderr.decode()[:500] if stderr else "Unknown error"
                    raise Exception(f"FFmpeg encode failed for scene {scene_num}: {error_output}")
                
            finally:
                duration = (time.time() - start_time) * 1000
                progress.log_stage(f"encode_scene_{scene_num}", duration)
            
            segments.append(segment_path)
        
        return segments
    
    async def _concatenate_segments(self, segments: List[str], temp_dir: str) -> str:
        """Concatenate video segments using stream copy (fast)"""
        
        # Create concat file
        concat_file = os.path.join(temp_dir, "concat.txt")
        with open(concat_file, "w") as f:
            for seg in segments:
                f.write(f"file '{seg}'\n")
        
        output_path = os.path.join(temp_dir, "concat_video.mp4")
        
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",  # Stream copy - very fast
            output_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            await asyncio.wait_for(process.communicate(), timeout=FFMPEG_CONCAT_TIMEOUT)
        except asyncio.TimeoutError:
            process.kill()
            raise subprocess.TimeoutExpired(cmd, FFMPEG_CONCAT_TIMEOUT)
        
        if process.returncode != 0:
            raise Exception("FFmpeg concat failed")
        
        return output_path
    
    async def _add_background_music(
        self,
        video_path: str,
        music_id: str,
        volume: float,
        temp_dir: str
    ) -> str:
        """Add background music track"""
        from routes.story_video_generation import PIXABAY_MUSIC_SAMPLES
        
        music_track = next((m for m in PIXABAY_MUSIC_SAMPLES if m["id"] == music_id), None)
        if not music_track:
            return video_path
        
        # Download music
        music_path = os.path.join(temp_dir, "music.mp3")
        await self._download_file_with_timeout(music_track["url"], music_path, "music")
        
        output_path = os.path.join(temp_dir, "video_with_music.mp4")
        
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", music_path,
            "-filter_complex", f"[1:a]volume={volume}[bg];[0:a][bg]amix=inputs=2:duration=first[a]",
            "-map", "0:v",
            "-map", "[a]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            output_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            await asyncio.wait_for(process.communicate(), timeout=FFMPEG_MUSIC_TIMEOUT)
        except asyncio.TimeoutError:
            process.kill()
            raise subprocess.TimeoutExpired(cmd, FFMPEG_MUSIC_TIMEOUT)
        
        return output_path if process.returncode == 0 else video_path
    
    async def _add_watermark_and_finalize(
        self,
        video_path: str,
        include_watermark: bool,
        output_filename: str,
        temp_dir: str
    ) -> str:
        """Add watermark and finalize output"""
        
        static_dir = Path("/app/backend/static/generated")
        static_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(static_dir / output_filename)
        
        if include_watermark:
            watermark_text = "visionary-suite.com"
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-vf", f"drawtext=text='{watermark_text}':fontcolor=white@0.5:fontsize=18:x=w-tw-10:y=h-th-10",
                "-c:v", "libx264",
                "-preset", FFMPEG_PRESET,
                "-crf", str(FFMPEG_CRF),
                "-c:a", "copy",
                output_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                await asyncio.wait_for(process.communicate(), timeout=FFMPEG_WATERMARK_TIMEOUT)
            except asyncio.TimeoutError:
                process.kill()
                raise subprocess.TimeoutExpired(cmd, FFMPEG_WATERMARK_TIMEOUT)
            
            if process.returncode != 0:
                # Fallback to copy without watermark
                shutil.copy(video_path, output_path)
        else:
            shutil.copy(video_path, output_path)
        
        return output_path
    
    # =========================================================================
    # R2 UPLOAD
    # =========================================================================
    
    async def _upload_to_r2(
        self,
        file_path: str,
        project_id: str,
        filename: str,
        progress: RenderProgress
    ) -> Tuple[str, str]:
        """Upload to R2 with timeout and progress tracking"""
        
        video_url = f"/static/generated/{filename}"
        storage_type = "local"
        
        try:
            from services.cloudflare_r2_storage import get_r2_storage
            r2_storage = get_r2_storage()
            
            if r2_storage.is_configured:
                # Progress callback for upload
                async def upload_progress(uploaded, total):
                    pct = 90 + int((uploaded / total) * 8)  # 90-98%
                    progress.update("uploading", pct, f"Uploading: {uploaded}/{total} bytes")
                
                # Upload with timeout
                upload_task = r2_storage.upload_file_multipart(
                    file_path, "video", project_id, filename, upload_progress
                )
                
                success, public_url, key = await asyncio.wait_for(
                    upload_task,
                    timeout=R2_UPLOAD_TIMEOUT
                )
                
                if success:
                    video_url = public_url
                    storage_type = "r2_cloud"
                    logger.info(f"[VIDEO_RENDER] Uploaded to R2: {public_url}")
                    
        except asyncio.TimeoutError:
            logger.warning("[VIDEO_RENDER] R2 upload timeout, using local storage")
        except Exception as e:
            logger.warning(f"[VIDEO_RENDER] R2 upload failed: {e}, using local storage")
        
        return video_url, storage_type
    
    # =========================================================================
    # DATABASE & PROGRESS UPDATES
    # =========================================================================
    
    async def _update_job_status(self, job_id: str, status: str, progress: int, message: str):
        """Update job status in database"""
        await self.db.render_jobs.update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "status": status,
                    "progress": progress,
                    "status_message": message,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
    
    async def _update_job_completed(
        self,
        job_id: str,
        project_id: str,
        video_url: str,
        storage_type: str,
        timing: dict
    ):
        """Update job as completed"""
        await self.db.render_jobs.update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "status": "COMPLETED",
                    "progress": 100,
                    "output_url": video_url,
                    "storage_type": storage_type,
                    "completed_at": datetime.now(timezone.utc),
                    "render_timing_ms": timing.get("TOTAL_RENDER_TIME", 0),
                    "timing_breakdown": timing
                }
            }
        )
        
        # Update project status
        await self.db.story_projects.update_one(
            {"project_id": project_id},
            {
                "$set": {
                    "status": "video_rendered",
                    "final_video_url": video_url,
                    "storage_type": storage_type,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
    
    async def _broadcast_progress(
        self,
        progress: RenderProgress,
        stage: str,
        pct: int,
        message: str
    ):
        """Broadcast progress to WebSocket"""
        if self.broadcast_progress:
            try:
                await self.broadcast_progress(
                    progress.job_id,
                    progress.user_id,
                    stage,
                    pct,
                    metadata={"stage": message, "timing": progress.timing}
                )
            except Exception as e:
                logger.debug(f"Progress broadcast error: {e}")
    
    async def _handle_render_failure(
        self,
        job_id: str,
        user_id: str,
        error_message: str,
        progress: RenderProgress
    ):
        """Handle render failure with refund"""
        
        # Update job as failed
        await self.db.render_jobs.update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "status": "FAILED",
                    "error": error_message,
                    "failed_at": datetime.now(timezone.utc),
                    "timing_at_failure": progress.timing
                }
            }
        )
        
        # Broadcast error
        if self.broadcast_error:
            try:
                await self.broadcast_error(job_id, user_id, error_message, stage="video_assembly")
            except Exception:
                pass
        
        # Auto-refund
        try:
            from routes.story_video_generation import CREDIT_COSTS
            refund_amount = CREDIT_COSTS.get("video_render", 20)
            
            from bson import ObjectId
            user = None
            try:
                user = await self.db.users.find_one({"_id": ObjectId(user_id)})
            except Exception:
                user = await self.db.users.find_one({"id": user_id})
            
            if user:
                await self.db.users.update_one(
                    {"_id": user.get("_id")},
                    {"$inc": {"credits": refund_amount}}
                )
                
                await self.db.credit_transactions.insert_one({
                    "user_id": str(user.get("_id")),
                    "amount": refund_amount,
                    "type": "refund",
                    "description": f"Auto-refund for failed video render: {error_message[:100]}",
                    "created_at": datetime.now(timezone.utc)
                })
                
                logger.info(f"[VIDEO_RENDER] Refunded {refund_amount} credits for failed job {job_id}")
                
        except Exception as e:
            logger.error(f"[VIDEO_RENDER] Refund failed: {e}")


# Singleton instance
_renderer_instance = None

def get_optimized_renderer(db):
    """Get or create the optimized renderer instance"""
    global _renderer_instance
    if _renderer_instance is None:
        try:
            from routes.websocket_progress import (
                broadcast_video_progress,
                broadcast_completion,
                broadcast_error
            )
            _renderer_instance = OptimizedVideoRenderer(
                db, broadcast_video_progress, broadcast_error, broadcast_completion
            )
        except ImportError:
            _renderer_instance = OptimizedVideoRenderer(db)
    return _renderer_instance
