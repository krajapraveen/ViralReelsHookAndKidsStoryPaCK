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
        user_id: str = None,
        animation_style: str = "auto",
        pacing_mode: str = "auto",
        story_text: str = ""
    ) -> Tuple[bool, str, dict]:
        """
        Main render entry point with full optimization + Visual Delight pipeline.
        
        pacing_mode: "auto" | "kids" | "action" | "emotional" | "cinematic"
            - Controls motion selection, scene duration envelope, fade timing,
              and BGM ducking aggressiveness.
        story_text: used to auto-detect pacing when pacing_mode == "auto".
        
        Returns:
            Tuple of (success, video_url, timing_data)
        """
        # Resolve pacing profile (delight sprint v1)
        resolved_pacing = self._resolve_pacing(pacing_mode, story_text, animation_style)
        self._active_pacing = resolved_pacing  # read by encode stages
        logger.info(f"[VIDEO_RENDER] [{job_id}] Pacing profile: {resolved_pacing['name']} (requested={pacing_mode})")
        
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
            
            segments = await self._encode_all_segments(scene_data, temp_dir, progress, animation_style)
            
            encode_duration = (time.time() - encode_start) * 1000
            progress.log_stage("encode_all_segments", encode_duration)
            
            # =================================================================
            # STAGE 3: Concatenate segments (60-70%)
            # =================================================================
            concat_start = time.time()
            progress.update("concatenating", 65, "Concatenating video segments")
            await self._broadcast_progress(progress, "audio_sync", 65, "Merging video segments")
            
            concat_video = await self._concatenate_segments(segments, temp_dir, include_watermark)
            
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
            # STAGE 5: Finalize output (80-90%) — watermark already baked in concat
            # =================================================================
            finalize_start = time.time()
            progress.update("finalizing", 82, "Finalizing video")
            await self._broadcast_progress(progress, "rendering", 82, "Finalizing video")
            
            output_filename = f"{project_id}_final.mp4"
            output_path = await self._finalize_output(final_video, output_filename)
            
            finalize_duration = (time.time() - finalize_start) * 1000
            progress.log_stage("finalize", finalize_duration)
            
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
    
    # =========================================================================
    # KEN BURNS MOTION SYSTEM — Makes videos feel dynamic, not slideshows
    # =========================================================================
    
    # Motion types cycled per scene for visual variety (legacy fallback)
    MOTION_PATTERNS = [
        "zoom_in",       # Slow zoom into center
        "pan_right",     # Pan from left to right
        "zoom_out",      # Start zoomed in, pull out
        "pan_left",      # Pan from right to left
        "zoom_in_top",   # Zoom toward top-right
        "pan_up",        # Slow pan upward
    ]
    
    # =========================================================================
    # VISUAL DELIGHT — CINEMATIC MOTION PACK (Phase 1 Growth Sprint)
    # =========================================================================
    # Each motion uses eased progress curves so motion feels *authored*, not linear.
    # Formula conventions:
    #   t = on / total_frames  (normalized 0..1)
    #   ease-out: 1-(1-t)^2  → fast start, slow finish (pro-cinema default)
    #   ease-in:  t^2        → builds momentum (good for impact zooms)
    #   ease-in-out: 0.5-0.5*cos(PI*t) (calm, breathing)
    # ffmpeg zoompan supports arithmetic on `on` so we embed the curves inline.
    
    CINEMATIC_MOTION_PACK = {
        # ─── WONDER / EMOTIONAL ───
        "dolly_reveal": {
            # Slow eased push from 1.0 → 1.22 with tiny upward drift — opens a story
            "z": "1 + 0.22*(1-pow(1-on/{F},2))",
            "x": "iw/2 - (iw/zoom/2)",
            "y": "ih*0.55 - (ih/zoom/2) - (ih*0.04)*(on/{F})",
        },
        "slow_zoom_in": {
            "z": "1 + 0.18*(1-pow(1-on/{F},3))",
            "x": "iw/2 - (iw/zoom/2)",
            "y": "ih/2 - (ih/zoom/2)",
        },
        "parallax_drift": {
            # Combines eased horizontal drift with mild zoom → layered-depth feel
            "z": "1.12 + 0.06*(on/{F})",
            "x": "iw*0.5 - (iw/zoom/2) + (iw*0.06)*(1-pow(1-on/{F},2)) - (iw*0.03)",
            "y": "ih*0.5 - (ih/zoom/2) - (ih*0.025)*(on/{F})",
        },
        "hold_then_push": {
            # Scene sits still for ~40% then dollies in — dramatic beat
            "z": "if(lt(on,0.4*{F}), 1.05, 1.05 + 0.18*((on-0.4*{F})/(0.6*{F})))",
            "x": "iw/2 - (iw/zoom/2)",
            "y": "ih/2 - (ih/zoom/2)",
        },
        # ─── ACTION / ADVENTURE ───
        "dolly_push": {
            # Aggressive ease-in push — impact
            "z": "1.02 + 0.28*pow(on/{F},2)",
            "x": "iw/2 - (iw/zoom/2)",
            "y": "ih/2 - (ih/zoom/2)",
        },
        "pan_sweep_right": {
            # Fast wide pan with slight zoom — chase energy
            "z": "1.18",
            "x": "(iw*0.22)*(1-pow(1-on/{F},2))",
            "y": "ih/2 - (ih/zoom/2)",
        },
        "pan_sweep_left": {
            "z": "1.18",
            "x": "(iw*0.22)*(1 - (1-pow(1-on/{F},2)))",
            "y": "ih/2 - (ih/zoom/2)",
        },
        "impact_zoom": {
            # Short snap zoom — for reveals / climaxes
            "z": "1.08 + 0.22*pow(on/{F},3)",
            "x": "iw*0.55 - (iw/zoom/2)",
            "y": "ih*0.45 - (ih/zoom/2)",
        },
        # ─── KIDS / WHIMSICAL ───
        "zoom_in_wonder": {
            # Gentle ease-out zoom toward upper-third (storybook sweet spot)
            "z": "1 + 0.20*(1-pow(1-on/{F},2))",
            "x": "iw*0.55 - (iw/zoom/2)",
            "y": "ih*0.40 - (ih/zoom/2)",
        },
        "pan_right_bright": {
            "z": "1.15 + 0.05*sin(on/{F}*PI)",  # subtle breathing
            "x": "(iw*0.16)*(on/{F})",
            "y": "ih/2 - (ih/zoom/2)",
        },
        "zoom_out_reveal": {
            # Pull-back — reveals the world around the character
            "z": "1.28 - 0.22*(1-pow(1-on/{F},2))",
            "x": "iw/2 - (iw/zoom/2)",
            "y": "ih/2 - (ih/zoom/2)",
        },
    }
    
    # Pacing profiles drive motion selection, duration envelope, fade length, BGM ducking.
    PACING_PROFILES = {
        "kids": {
            "name": "kids",
            "motion_set": ["zoom_in_wonder", "pan_right_bright", "parallax_drift", "zoom_out_reveal", "dolly_reveal", "zoom_in_wonder"],
            "duration_mult": 1.0,
            "first_scene_bonus": 0.4,   # extra hold time on opening
            "last_scene_bonus": 0.6,    # clean ending beat
            "fade_in_sec": 0.25,
            "fade_out_sec": 0.35,
            "intro_fade_sec": 0.45,     # black fade-in on scene 0
            "outro_fade_sec": 0.65,     # fade-to-black on final scene
            "bgm_threshold": 0.040,
            "bgm_ratio": 8,
            "bgm_attack_ms": 10,
            "bgm_release_ms": 300,
            "bgm_base_volume": 0.28,    # kids: slightly audible music
        },
        "action": {
            "name": "action",
            "motion_set": ["dolly_push", "pan_sweep_right", "impact_zoom", "pan_sweep_left", "dolly_push", "impact_zoom"],
            "duration_mult": 0.88,      # tighter cuts for action
            "first_scene_bonus": 0.15,  # punchy opening, less breath
            "last_scene_bonus": 0.5,
            "fade_in_sec": 0.10,        # snappy transitions
            "fade_out_sec": 0.12,
            "intro_fade_sec": 0.20,
            "outro_fade_sec": 0.55,
            "bgm_threshold": 0.050,
            "bgm_ratio": 6,             # less aggressive duck — lets music breathe during beats
            "bgm_attack_ms": 5,
            "bgm_release_ms": 200,
            "bgm_base_volume": 0.34,
        },
        "emotional": {
            "name": "emotional",
            "motion_set": ["dolly_reveal", "slow_zoom_in", "parallax_drift", "hold_then_push", "slow_zoom_in", "dolly_reveal"],
            "duration_mult": 1.15,      # slower holds for emotional weight
            "first_scene_bonus": 0.55,  # strong establishing beat
            "last_scene_bonus": 0.85,
            "fade_in_sec": 0.40,        # longer fades for drama
            "fade_out_sec": 0.55,
            "intro_fade_sec": 0.70,
            "outro_fade_sec": 1.00,
            "bgm_threshold": 0.030,
            "bgm_ratio": 10,            # aggressive duck — narration priority
            "bgm_attack_ms": 12,
            "bgm_release_ms": 350,
            "bgm_base_volume": 0.22,    # low, cinematic
        },
        "cinematic": {
            "name": "cinematic",
            "motion_set": ["dolly_reveal", "hold_then_push", "parallax_drift", "slow_zoom_in", "pan_sweep_right", "dolly_reveal"],
            "duration_mult": 1.08,
            "first_scene_bonus": 0.45,
            "last_scene_bonus": 0.75,
            "fade_in_sec": 0.30,
            "fade_out_sec": 0.45,
            "intro_fade_sec": 0.55,
            "outro_fade_sec": 0.90,
            "bgm_threshold": 0.035,
            "bgm_ratio": 9,
            "bgm_attack_ms": 10,
            "bgm_release_ms": 300,
            "bgm_base_volume": 0.25,
        },
        "auto": {
            # Balanced — used when genre can't be detected
            "name": "auto",
            "motion_set": ["dolly_reveal", "slow_zoom_in", "parallax_drift", "pan_sweep_right", "zoom_in_wonder", "hold_then_push"],
            "duration_mult": 1.0,
            "first_scene_bonus": 0.30,
            "last_scene_bonus": 0.55,
            "fade_in_sec": 0.22,
            "fade_out_sec": 0.30,
            "intro_fade_sec": 0.40,
            "outro_fade_sec": 0.70,
            "bgm_threshold": 0.038,
            "bgm_ratio": 8,
            "bgm_attack_ms": 10,
            "bgm_release_ms": 280,
            "bgm_base_volume": 0.28,
        },
    }
    
    # Keyword → pacing heuristic (used when pacing_mode="auto")
    _PACING_KEYWORDS = {
        "kids":      ["bunny", "puppy", "kitten", "giggle", "tickle", "magical", "fairy", "unicorn", "silly", "playground", "mommy", "daddy", "rainbow", "wiggle", "bedtime"],
        "action":    ["chase", "explode", "battle", "fight", "race", "escape", "crash", "ambush", "storm", "warrior", "sword", "pursuit", "danger", "hunted", "sprint"],
        "emotional": ["tear", "goodbye", "love", "remember", "lost", "heart", "grandmother", "grandfather", "mourn", "hope", "forgive", "reunion", "whisper", "promise", "embrace"],
    }
    
    def _resolve_pacing(self, pacing_mode: str, story_text: str, animation_style: str) -> dict:
        """Pick the best pacing profile given explicit mode + story text + style hints."""
        mode = (pacing_mode or "auto").lower().strip()
        if mode in self.PACING_PROFILES and mode != "auto":
            return self.PACING_PROFILES[mode]
        
        # Animation style hint (cinematic templates exist on backend)
        style_l = (animation_style or "").lower()
        if "cinematic" in style_l or "cinema" in style_l or "noir" in style_l:
            return self.PACING_PROFILES["cinematic"]
        
        # Heuristic from story text
        text_l = (story_text or "").lower()
        if text_l:
            scores = {}
            for genre, kws in self._PACING_KEYWORDS.items():
                scores[genre] = sum(1 for kw in kws if kw in text_l)
            best_genre = max(scores, key=scores.get) if scores else None
            if best_genre and scores[best_genre] >= 2:
                return self.PACING_PROFILES[best_genre]
        
        return self.PACING_PROFILES["auto"]
    
    def _pick_motion_for_scene(self, scene_index: int, total_scenes: int, pacing: dict) -> str:
        """Pick a cinematic motion for a scene based on pacing + position in sequence."""
        motion_set = pacing["motion_set"]
        # Emphasize opening with the profile's first motion (usually a "reveal" type)
        if scene_index == 0:
            return motion_set[0]
        # Emphasize closing with a reveal/push for payoff
        if scene_index == total_scenes - 1 and total_scenes > 1:
            # Pick the strongest: hold_then_push, dolly_push, zoom_out_reveal, or dolly_reveal
            for preferred in ("hold_then_push", "zoom_out_reveal", "dolly_push", "dolly_reveal"):
                if preferred in motion_set:
                    return preferred
        # Middle scenes cycle through the set
        return motion_set[scene_index % len(motion_set)]
    
    def _apply_scene_pacing(self, scene_index: int, total_scenes: int, base_duration: float, pacing: dict) -> float:
        """Apply pacing-driven duration envelope: opening breath, holds, ending beat."""
        dur = base_duration * pacing["duration_mult"]
        if scene_index == 0:
            dur += pacing["first_scene_bonus"]
        if scene_index == total_scenes - 1 and total_scenes > 1:
            dur += pacing["last_scene_bonus"]
        # Clamp: no scene under 2.0s, no scene over 14s
        return max(2.0, min(14.0, dur))
    
    def _get_motion_filter(self, scene_index: int, duration: float, animation_style: str = "auto", motion_name: Optional[str] = None) -> str:
        """
        Build the FFmpeg zoompan filter for a scene using the Cinematic Motion Pack.
        Eased progress curves make motion feel authored, not robotic.
        
        If motion_name is supplied, uses that motion from CINEMATIC_MOTION_PACK.
        Otherwise falls back to legacy MOTION_PATTERNS (linear) for back-compat.
        """
        total_frames = int(duration * OUTPUT_FPS)
        total_frames = max(total_frames, OUTPUT_FPS * 2)  # min 2s of frames
        F = total_frames
        
        # ─── Primary path: cinematic motion pack ───
        if motion_name and motion_name in self.CINEMATIC_MOTION_PACK:
            spec = self.CINEMATIC_MOTION_PACK[motion_name]
            z_expr = spec["z"].replace("{F}", str(F))
            x_expr = spec["x"].replace("{F}", str(F))
            y_expr = spec["y"].replace("{F}", str(F))
            return (
                f"zoompan=z='{z_expr}'"
                f":x='{x_expr}':y='{y_expr}'"
                f":d={F}:s={OUTPUT_RESOLUTION}:fps={OUTPUT_FPS}"
            )
        
        # ─── Legacy fallback (linear motion) ───
        if animation_style and animation_style != "auto":
            motion = animation_style
        else:
            motion = self.MOTION_PATTERNS[scene_index % len(self.MOTION_PATTERNS)]
        
        if motion == "zoom_in":
            zp = (
                f"zoompan=z='min(1+0.25*on/{F},1.25)'"
                f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                f":d={F}:s={OUTPUT_RESOLUTION}:fps={OUTPUT_FPS}"
            )
        elif motion == "zoom_out":
            zp = (
                f"zoompan=z='if(eq(on,1),1.25,max(1.0,zoom-0.25/{F}))'"
                f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                f":d={F}:s={OUTPUT_RESOLUTION}:fps={OUTPUT_FPS}"
            )
        elif motion == "pan_right":
            zp = (
                f"zoompan=z='1.15'"
                f":x='(iw*0.15)*on/{F}':y='ih/2-(ih/zoom/2)'"
                f":d={F}:s={OUTPUT_RESOLUTION}:fps={OUTPUT_FPS}"
            )
        elif motion == "pan_left":
            zp = (
                f"zoompan=z='1.15'"
                f":x='(iw*0.15)*(1-on/{F})':y='ih/2-(ih/zoom/2)'"
                f":d={F}:s={OUTPUT_RESOLUTION}:fps={OUTPUT_FPS}"
            )
        elif motion == "zoom_in_top":
            zp = (
                f"zoompan=z='min(1+0.25*on/{F},1.25)'"
                f":x='iw*0.6-(iw/zoom/2)':y='ih*0.35-(ih/zoom/2)'"
                f":d={F}:s={OUTPUT_RESOLUTION}:fps={OUTPUT_FPS}"
            )
        elif motion == "pan_up":
            zp = (
                f"zoompan=z='1.15'"
                f":x='iw/2-(iw/zoom/2)':y='(ih*0.15)*(1-on/{F})'"
                f":d={F}:s={OUTPUT_RESOLUTION}:fps={OUTPUT_FPS}"
            )
        else:
            zp = (
                f"zoompan=z='min(1+0.15*on/{F},1.15)'"
                f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                f":d={F}:s={OUTPUT_RESOLUTION}:fps={OUTPUT_FPS}"
            )
        
        return zp

    async def _encode_all_segments(
        self,
        scene_data: List[dict],
        temp_dir: str,
        progress: RenderProgress,
        animation_style: str = "auto"
    ) -> List[str]:
        """Encode all scene segments with Cinematic Motion Pack + pacing-driven fades"""
        total = len(scene_data)
        pacing = getattr(self, "_active_pacing", None) or self.PACING_PROFILES["auto"]
        
        # Apply pacing-driven duration envelope (opening breath, ending beat)
        for idx, scene in enumerate(scene_data):
            base = scene.get("duration", 5.0)
            scene["_original_duration"] = base
            scene["duration"] = self._apply_scene_pacing(idx, total, base, pacing)
        
        # Limit concurrent ffmpeg processes to avoid CPU overload
        encode_semaphore = asyncio.Semaphore(min(2, total))
        completed_count = 0
        
        async def encode_single_scene(scene, scene_index):
            nonlocal completed_count
            async with encode_semaphore:
                scene_num = scene["scene_number"]
                segment_path = os.path.join(temp_dir, f"segment_{scene_num}.mp4")
                scene_duration = scene["duration"]
                
                # Pick cinematic motion per scene (opening/closing emphasis)
                motion_name = self._pick_motion_for_scene(scene_index, total, pacing)
                motion_filter = self._get_motion_filter(
                    scene_index, scene_duration, animation_style, motion_name=motion_name
                )
                
                # Per-scene fade timing: dramatic intro on scene 0, fade-to-black on final
                is_first = scene_index == 0
                is_last = scene_index == total - 1 and total > 1
                fade_in = pacing["intro_fade_sec"] if is_first else pacing["fade_in_sec"]
                fade_out = pacing["outro_fade_sec"] if is_last else pacing["fade_out_sec"]
                # Safety: fades must not overlap in very short scenes
                if fade_in + fade_out > scene_duration * 0.8:
                    fade_in = scene_duration * 0.2
                    fade_out = scene_duration * 0.2
                fade_out_start = max(0.0, scene_duration - fade_out)
                
                # Step 1: Upscale the source image so zoompan has headroom (1920x1080 → pans 1280x720)
                scaled_img_path = os.path.join(temp_dir, f"scene_{scene_num}_scaled.png")
                scale_cmd = [
                    "ffmpeg", "-y",
                    "-i", scene["image_path"],
                    "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
                    "-frames:v", "1",
                    scaled_img_path
                ]
                scale_proc = await asyncio.create_subprocess_exec(
                    *scale_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await asyncio.wait_for(scale_proc.communicate(), timeout=15)
                src_image = scaled_img_path if os.path.exists(scaled_img_path) else scene["image_path"]
                
                # Step 2: Generate the motion video with cinematic ease + fades
                motion_video_path = os.path.join(temp_dir, f"motion_{scene_num}.mp4")
                motion_chain = (
                    f"{motion_filter},"
                    f"fade=t=in:st=0:d={fade_in:.3f},"
                    f"fade=t=out:st={fade_out_start:.3f}:d={fade_out:.3f}"
                )
                motion_cmd = [
                    "ffmpeg", "-y",
                    "-loop", "1",
                    "-i", src_image,
                    "-vf", motion_chain,
                    "-c:v", "libx264",
                    "-preset", FFMPEG_PRESET,
                    "-crf", str(FFMPEG_CRF),
                    "-pix_fmt", "yuv420p",
                    "-t", str(scene_duration + 0.3),
                    "-threads", "2",
                    motion_video_path
                ]
                
                start_time = time.time()
                try:
                    process = await asyncio.create_subprocess_exec(
                        *motion_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    try:
                        stdout, stderr = await asyncio.wait_for(
                            process.communicate(),
                            timeout=FFMPEG_SCENE_TIMEOUT * 2
                        )
                    except asyncio.TimeoutError:
                        process.kill()
                        raise subprocess.TimeoutExpired(motion_cmd, FFMPEG_SCENE_TIMEOUT * 2)
                    
                    if process.returncode != 0:
                        error_output = stderr.decode()[:500] if stderr else "Unknown error"
                        logger.warning(
                            f"[VIDEO_RENDER] Cinematic motion '{motion_name}' failed for scene {scene_num}, "
                            f"falling back to static: {error_output}"
                        )
                        motion_video_path = await self._encode_static_fallback(
                            scene, temp_dir, scene_num
                        )
                    
                    # Step 3: Merge motion video with audio
                    # Audio fade matches video fades for silky transitions
                    merge_cmd = [
                        "ffmpeg", "-y",
                        "-i", motion_video_path,
                        "-i", scene["audio_path"],
                        "-c:v", "copy",
                        "-af", f"afade=t=in:st=0:d={min(fade_in, 0.3):.3f},afade=t=out:st={fade_out_start:.3f}:d={min(fade_out, 0.4):.3f}",
                        "-c:a", "aac",
                        "-profile:a", "aac_low",  # Safari-safe LC profile
                        "-ar", "44100",
                        "-ac", "2",
                        "-b:a", AUDIO_BITRATE,
                        "-shortest",
                        "-t", str(scene_duration + 0.3),
                        segment_path
                    ]
                    merge_proc = await asyncio.create_subprocess_exec(
                        *merge_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    try:
                        await asyncio.wait_for(merge_proc.communicate(), timeout=FFMPEG_SCENE_TIMEOUT)
                    except asyncio.TimeoutError:
                        merge_proc.kill()
                        raise subprocess.TimeoutExpired(merge_cmd, FFMPEG_SCENE_TIMEOUT)
                    if merge_proc.returncode != 0:
                        raise Exception(f"Audio merge failed for scene {scene_num}")
                finally:
                    duration = (time.time() - start_time) * 1000
                    progress.log_stage(f"encode_scene_{scene_num}_{motion_name}", duration)
                
                completed_count += 1
                pct = 25 + int((completed_count / total) * 35)
                progress.update("encoding", pct, f"Encoded scene {completed_count}/{total} [{motion_name}]")
                await self._broadcast_progress(
                    progress, "composing", pct,
                    f"Encoded scene {completed_count}/{total} [{motion_name}]"
                )
                
                return scene_num, segment_path
        
        async def _fallback_static(scene, scene_num):
            """Encode a plain static segment as a last resort"""
            return await self._encode_static_fallback(scene, temp_dir, scene_num)
        
        # Run all scene encodings in parallel
        results = await asyncio.gather(
            *[encode_single_scene(scene, idx) for idx, scene in enumerate(scene_data)],
            return_exceptions=True
        )
        
        # Sort by scene number and collect paths
        segments = []
        for result in results:
            if isinstance(result, Exception):
                raise result
            scene_num, path = result
            segments.append((scene_num, path))
        
        segments.sort(key=lambda x: x[0])
        return [path for _, path in segments]
    
    async def _encode_static_fallback(self, scene: dict, temp_dir: str, scene_num: int) -> str:
        """Fallback: encode a static segment (no motion) if Ken Burns fails"""
        fallback_path = os.path.join(temp_dir, f"static_{scene_num}.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", scene["image_path"],
            "-c:v", "libx264",
            "-preset", FFMPEG_PRESET,
            "-tune", "stillimage",
            "-crf", str(FFMPEG_CRF),
            "-pix_fmt", "yuv420p",
            "-vf", f"scale={OUTPUT_RESOLUTION}:force_original_aspect_ratio=decrease,pad={OUTPUT_RESOLUTION}:(ow-iw)/2:(oh-ih)/2",
            "-r", str(OUTPUT_FPS),
            "-t", str(scene["duration"] + 0.5),
            fallback_path
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await asyncio.wait_for(proc.communicate(), timeout=FFMPEG_SCENE_TIMEOUT)
        return fallback_path
    
    async def _concatenate_segments(self, segments: List[str], temp_dir: str, include_watermark: bool = False) -> str:
        """Concatenate video segments. Since each segment already has cinematic
        fade-in/fade-out baked in, plain concat produces smooth dissolves."""
        
        # If only one segment, skip concat
        if len(segments) == 1:
            if include_watermark:
                output_path = os.path.join(temp_dir, "concat_video.mp4")
                cmd = [
                    "ffmpeg", "-y",
                    "-i", segments[0],
                    "-vf", "drawtext=text='visionary-suite.com':fontcolor=white@0.5:fontsize=18:x=w-tw-10:y=h-th-10",
                    "-c:v", "libx264", "-preset", FFMPEG_PRESET, "-crf", str(FFMPEG_CRF),
                    "-c:a", "copy",
                    output_path
                ]
                process = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                await asyncio.wait_for(process.communicate(), timeout=FFMPEG_CONCAT_TIMEOUT)
                return output_path
            return segments[0]
        
        concat_file = os.path.join(temp_dir, "concat.txt")
        with open(concat_file, "w") as f:
            for seg in segments:
                f.write(f"file '{seg}'\n")
        
        output_path = os.path.join(temp_dir, "concat_video.mp4")
        
        if include_watermark:
            # Concat + watermark in ONE pass
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", concat_file,
                "-vf", "drawtext=text='visionary-suite.com':fontcolor=white@0.5:fontsize=18:x=w-tw-10:y=h-th-10",
                "-c:v", "libx264", "-preset", FFMPEG_PRESET, "-crf", str(FFMPEG_CRF),
                "-c:a", "copy",
                output_path
            ]
        else:
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", concat_file,
                "-c", "copy",
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
        """Add background music with INTELLIGENT SIDECHAIN DUCKING.
        
        When narration is loud, music auto-dimmers down (threshold+ratio compressor
        keyed off the narration track). When narration pauses, music returns to
        full volume. This is the core of 'cinematic audio immersion'.
        """
        from routes.story_video_generation import PIXABAY_MUSIC_SAMPLES
        
        music_track = next((m for m in PIXABAY_MUSIC_SAMPLES if m["id"] == music_id), None)
        if not music_track:
            return video_path
        
        # Download music
        music_path = os.path.join(temp_dir, "music.mp3")
        await self._download_file_with_timeout(music_track["url"], music_path, "music")
        
        output_path = os.path.join(temp_dir, "video_with_music.mp4")
        
        pacing = getattr(self, "_active_pacing", None) or self.PACING_PROFILES["auto"]
        # Caller volume is a user/ui hint; pacing can override if explicit mode was picked
        eff_volume = volume if pacing["name"] == "auto" else pacing["bgm_base_volume"]
        threshold = pacing["bgm_threshold"]
        ratio = pacing["bgm_ratio"]
        attack = pacing["bgm_attack_ms"]
        release = pacing["bgm_release_ms"]
        
        # Sidechain compression: music (input 1) ducks when narration (input 0) is present
        # The sidechain input is split so we can use it as both key and final mix source
        filter_complex = (
            f"[1:a]aloop=loop=-1:size=2e9,volume={eff_volume}[music];"
            f"[0:a]asplit=2[narr1][narr2];"
            f"[music][narr2]sidechaincompress="
            f"threshold={threshold}:ratio={ratio}:attack={attack}:release={release}:"
            f"makeup=1:knee=2.5[duck];"
            f"[narr1][duck]amix=inputs=2:duration=first:dropout_transition=3:normalize=0[a]"
        )
        
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", music_path,
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[a]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-profile:a", "aac_low",
            "-ar", "44100",
            "-ac", "2",
            "-b:a", AUDIO_BITRATE,
            "-shortest",
            output_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=FFMPEG_MUSIC_TIMEOUT)
        except asyncio.TimeoutError:
            process.kill()
            raise subprocess.TimeoutExpired(cmd, FFMPEG_MUSIC_TIMEOUT)
        
        if process.returncode != 0:
            # Fallback: plain amix without ducking — never block render on ducking failure
            logger.warning(f"[VIDEO_RENDER] Sidechain ducking failed, falling back to plain amix: {(stderr or b'')[:300]!r}")
            fallback_cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-i", music_path,
                "-filter_complex", f"[1:a]volume={eff_volume}[bg];[0:a][bg]amix=inputs=2:duration=first[a]",
                "-map", "0:v",
                "-map", "[a]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-profile:a", "aac_low",
                "-ar", "44100",
                "-ac", "2",
                "-shortest",
                output_path
            ]
            fp = await asyncio.create_subprocess_exec(
                *fallback_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(fp.communicate(), timeout=FFMPEG_MUSIC_TIMEOUT)
            if fp.returncode != 0:
                return video_path  # hard fallback to no-music
        
        return output_path
    
    async def _finalize_output(self, video_path: str, output_filename: str) -> str:
        """Finalize video: remux with +faststart for iOS/Safari streaming compatibility.
        
        Safari requires moov atom at the start of the MP4 container to stream
        audio+video reliably (without +faststart, Safari may play video silently
        until moov is read at file-end). This is a lightweight container-only
        operation — no re-encoding.
        """
        static_dir = Path("/app/backend/static/generated")
        static_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(static_dir / output_filename)
        
        # Remux with +faststart. Codecs are already AAC-LC stereo 44.1kHz from merge step.
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-c", "copy",
            "-movflags", "+faststart",
            output_path
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        except asyncio.TimeoutError:
            proc.kill()
            # Fallback to plain copy — worst case Safari sees old moov-at-end
            shutil.copy(video_path, output_path)
            return output_path
        
        if proc.returncode != 0:
            logger.warning(f"[VIDEO_RENDER] faststart remux failed, using raw copy: {(stderr or b'')[:300]!r}")
            shutil.copy(video_path, output_path)
        
        return output_path
    
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
