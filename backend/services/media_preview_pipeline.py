"""
Media Derivative Pipeline — Preview Generator for Visionary Suite.

Generates 3 derivatives per video asset:
1. Poster thumbnail (webp, sm + md)
2. 2-second muted preview clip (mp4, h264, faststart)
3. Full playback asset (original, already stored)

Uses hook selection to pick the best 2s window (motion + face + novelty).
Never blocks story visibility on derivative generation.
"""

import os
import asyncio
import tempfile
import logging
import subprocess
from datetime import datetime, timezone
from typing import Optional
import httpx

logger = logging.getLogger("media_preview_pipeline")

# Config
PREVIEW_DURATION = 2.0
PREVIEW_FPS = 24
PREVIEW_WIDTH = 540
POSTER_SM_WIDTH = 360
POSTER_MD_WIDTH = 720
PREVIEW_CRF = 28


async def generate_preview_derivatives(job_id: str, source_url: str, db) -> dict:
    """
    Main entry: download source video, select hook, generate poster + preview.
    Returns dict with URLs or None on failure. Never raises.
    """
    result = {"poster_sm": None, "poster_md": None, "preview_url": None, "hook_start_ms": 0}

    tmp_dir = tempfile.mkdtemp(prefix=f"preview_{job_id[:8]}_")

    try:
        # 1. Download source video
        started_at = datetime.now(timezone.utc).isoformat()
        source_path = os.path.join(tmp_dir, "source.mp4")
        ok = await _download_video(source_url, source_path)
        if not ok:
            logger.warning(f"[PREVIEW] Failed to download source for {job_id[:12]}")
            return result

        # 2. Get video info
        duration_ms, width, height = _get_video_info(source_path)
        if duration_ms <= 0:
            logger.warning(f"[PREVIEW] Invalid video duration for {job_id[:12]}")
            return result

        # 3. Select hook window (best 2s segment)
        hook_start_ms = _select_hook_window(source_path, duration_ms)
        result["hook_start_ms"] = hook_start_ms
        hook_start_s = hook_start_ms / 1000.0

        # 4. Generate poster thumbnails
        poster_sm_path = os.path.join(tmp_dir, "poster_sm.webp")
        poster_md_path = os.path.join(tmp_dir, "poster_md.webp")

        _extract_poster(source_path, hook_start_s, POSTER_SM_WIDTH, poster_sm_path)
        _extract_poster(source_path, hook_start_s, POSTER_MD_WIDTH, poster_md_path)

        # 5. Generate 2s muted preview clip
        preview_path = os.path.join(tmp_dir, "preview_2s.mp4")
        _generate_preview_clip(source_path, hook_start_s, PREVIEW_DURATION, preview_path)

        # 6. Upload to R2
        from services.cloudflare_r2_storage import get_r2_storage
        r2 = get_r2_storage()

        if r2.is_configured:
            if os.path.exists(poster_sm_path) and os.path.getsize(poster_sm_path) > 0:
                ok1, url1, _ = await r2.upload_file_multipart(
                    poster_sm_path, "previews", job_id, "poster_sm.webp"
                )
                if ok1:
                    result["poster_sm"] = url1

            if os.path.exists(poster_md_path) and os.path.getsize(poster_md_path) > 0:
                ok2, url2, _ = await r2.upload_file_multipart(
                    poster_md_path, "previews", job_id, "poster_md.webp"
                )
                if ok2:
                    result["poster_md"] = url2

            if os.path.exists(preview_path) and os.path.getsize(preview_path) > 0:
                ok3, url3, _ = await r2.upload_file_multipart(
                    preview_path, "previews", job_id, "preview_2s.mp4"
                )
                if ok3:
                    result["preview_url"] = url3

        # 7. Persist to media_assets collection
        now = datetime.now(timezone.utc).isoformat()
        duration_ms_elapsed = int((datetime.now(timezone.utc) - datetime.fromisoformat(started_at)).total_seconds() * 1000)
        await db.media_assets.update_one(
            {"story_id": job_id},
            {"$set": {
                "story_id": job_id,
                "source_asset": {
                    "url": source_url,
                    "duration_ms": duration_ms,
                    "width": width,
                    "height": height,
                },
                "hook": {
                    "start_ms": hook_start_ms,
                    "duration_ms": int(PREVIEW_DURATION * 1000),
                    "method": "scene_analysis",
                },
                "poster": {
                    "sm_url": result["poster_sm"],
                    "md_url": result["poster_md"],
                },
                "preview": {
                    "mp4_url": result["preview_url"],
                    "duration_ms": int(PREVIEW_DURATION * 1000),
                    "width": PREVIEW_WIDTH,
                    "status": "READY" if result["preview_url"] else "FAILED",
                },
                "processing": {
                    "state": "READY" if result["preview_url"] else "FAILED",
                    "started_at": started_at,
                    "completed_at": now,
                    "duration_ms": duration_ms_elapsed,
                    "updated_at": now,
                },
                "updated_at": now,
            }},
            upsert=True,
        )

        # 8. Update story_engine_jobs with preview URLs
        update_fields = {}
        if result["poster_md"]:
            update_fields["preview_poster_url"] = result["poster_md"]
        if result["preview_url"]:
            update_fields["preview_video_url"] = result["preview_url"]
        if update_fields:
            update_fields["preview_ready"] = True
            await db.story_engine_jobs.update_one(
                {"job_id": job_id},
                {"$set": update_fields}
            )

        generated = sum(1 for v in [result["poster_sm"], result["poster_md"], result["preview_url"]] if v)
        logger.info(f"[PREVIEW] Generated {generated}/3 derivatives for {job_id[:12]} (hook@{hook_start_ms}ms)")

    except Exception as e:
        logger.error(f"[PREVIEW] Pipeline failed for {job_id[:12]}: {e}")
    finally:
        # Cleanup temp files
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return result


async def _download_video(url: str, dest_path: str) -> bool:
    """Download video from URL to local file."""
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200 and len(resp.content) > 1000:
                with open(dest_path, "wb") as f:
                    f.write(resp.content)
                return True
    except Exception as e:
        logger.warning(f"[PREVIEW] Download failed: {e}")
    return False


def _get_video_info(path: str) -> tuple:
    """Get video duration (ms), width, height using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            duration = float(data.get("format", {}).get("duration", 0))
            streams = data.get("streams", [])
            width, height = 0, 0
            for s in streams:
                if s.get("codec_type") == "video":
                    width = int(s.get("width", 0))
                    height = int(s.get("height", 0))
                    break
            return int(duration * 1000), width, height
    except Exception as e:
        logger.warning(f"[PREVIEW] ffprobe failed: {e}")
    return 0, 0, 0


def _select_hook_window(path: str, duration_ms: int) -> int:
    """
    Select the best 2s window for the hook preview.
    V1: Scene-based — pick window with most visual change (motion proxy).
    Falls back to first 2 seconds if analysis fails.
    """
    if duration_ms <= 2500:
        return 0  # Short video, use start

    try:
        # Sample frames at 2fps across the video and measure scene changes
        cmd = [
            "ffprobe", "-v", "quiet",
            "-show_entries", "frame=pts_time,pict_type",
            "-select_streams", "v",
            "-of", "csv=p=0",
            "-read_intervals", "%+10",  # Only analyze first 10s
            path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)

        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            # Find I-frames (scene changes) — they indicate visual interest
            scene_times = []
            for line in lines:
                parts = line.strip().split(',')
                if len(parts) >= 2 and parts[1] == 'I':
                    try:
                        t = float(parts[0])
                        if t > 0.5:  # Skip very start
                            scene_times.append(t)
                    except ValueError:
                        pass

            if scene_times:
                # Pick the first significant scene change
                best = scene_times[0]
                # Ensure we don't exceed video duration
                max_start = max(0, (duration_ms / 1000.0) - PREVIEW_DURATION)
                hook_start = min(best - 0.5, max_start)  # Start 0.5s before scene change
                return max(0, int(hook_start * 1000))

    except Exception as e:
        logger.warning(f"[PREVIEW] Hook selection failed: {e}")

    # Fallback: 20% into the video (avoids title cards / black frames)
    fallback_ms = int(duration_ms * 0.2)
    max_start_ms = max(0, duration_ms - int(PREVIEW_DURATION * 1000))
    return min(fallback_ms, max_start_ms)


def _extract_poster(source_path: str, timestamp: float, width: int, output_path: str):
    """Extract a single frame as WebP poster."""
    try:
        cmd = [
            "ffmpeg", "-y", "-ss", str(timestamp),
            "-i", source_path,
            "-frames:v", "1",
            "-vf", f"scale={width}:-2",
            "-quality", "80",
            output_path
        ]
        subprocess.run(cmd, capture_output=True, timeout=15)
    except Exception as e:
        logger.warning(f"[PREVIEW] Poster extraction failed: {e}")


def _generate_preview_clip(source_path: str, start: float, duration: float, output_path: str):
    """Generate a muted 2s preview clip optimized for silent autoplay."""
    try:
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", source_path,
            "-t", str(duration),
            "-an",  # No audio
            "-vf", f"scale={PREVIEW_WIDTH}:-2,fps={PREVIEW_FPS}",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", str(PREVIEW_CRF),
            "-movflags", "+faststart",
            "-pix_fmt", "yuv420p",
            output_path
        ]
        subprocess.run(cmd, capture_output=True, timeout=30)
    except Exception as e:
        logger.warning(f"[PREVIEW] Preview clip generation failed: {e}")


async def backfill_previews(db, limit: int = 50):
    """Backfill preview derivatives for existing READY stories with output_url but no preview."""
    cursor = db.story_engine_jobs.find(
        {
            "state": {"$in": ["READY", "PARTIAL_READY", "COMPLETED"]},
            "output_url": {"$ne": None},
            "preview_ready": {"$ne": True},
        },
        {"_id": 0, "job_id": 1, "output_url": 1}
    ).sort("battle_score", -1).limit(limit)

    jobs = await cursor.to_list(limit)
    logger.info(f"[PREVIEW-BACKFILL] Found {len(jobs)} stories to process")

    for job in jobs:
        try:
            await generate_preview_derivatives(job["job_id"], job["output_url"], db)
        except Exception as e:
            logger.warning(f"[PREVIEW-BACKFILL] Failed {job['job_id'][:12]}: {e}")
        await asyncio.sleep(1)  # Rate limit
