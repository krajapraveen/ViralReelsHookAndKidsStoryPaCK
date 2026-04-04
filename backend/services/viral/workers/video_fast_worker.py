"""
Video Fast Worker — creates quick social-ready MP4 from thumbnail + hook text.
Uses moviepy + ffmpeg for speed-first composition.
NOT Sora 2 — optimized for fast delivery, not cinematic quality.
Fallback: If video composition fails, pack still completes without video.
"""
import os
import logging
import tempfile
from shared import db
from services.viral import viral_job_service as jobs
from services.viral.task_dispatch import dispatch_task, Q_PACKAGING

logger = logging.getLogger("viral.worker.video_fast")

VIDEO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "static", "generated", "viral_videos")


async def handle_video_task(payload: dict):
    task_id = payload["task_id"]
    job_id = payload["job_id"]
    idea = payload.get("idea", "")
    niche = payload.get("niche", "")

    logger.info(f"[VIDEO_WORKER] Processing video task={task_id} job={job_id}")
    await jobs.update_job_phase(db, job_id, "generating_video")

    try:
        # Get thumbnail and hook from completed assets
        thumb_asset = await db.viral_assets.find_one(
            {"job_id": job_id, "asset_type": "thumbnail"}, {"file_path": 1, "file_url": 1}
        )
        hook_asset = await db.viral_assets.find_one(
            {"job_id": job_id, "asset_type": "hooks"}, {"content": 1}
        )

        if not thumb_asset or not thumb_asset.get("file_path"):
            logger.warning("[VIDEO_WORKER] No thumbnail for video composition, skipping")
            await jobs.update_task(db, task_id, "completed", fallback_used=True)
            await _check_and_dispatch_packaging(job_id)
            return

        thumb_path = thumb_asset["file_path"]
        if not os.path.exists(thumb_path):
            logger.warning(f"[VIDEO_WORKER] Thumbnail file missing: {thumb_path}")
            await jobs.update_task(db, task_id, "completed", fallback_used=True)
            await _check_and_dispatch_packaging(job_id)
            return

        hook_text = ""
        if hook_asset and hook_asset.get("content"):
            lines = hook_asset["content"].strip().split("\n")
            hook_text = lines[0] if lines else idea[:60]
        else:
            hook_text = idea[:60]

        # Compose video
        video_bytes = await _compose_video(thumb_path, hook_text, niche, job_id)

        if video_bytes:
            os.makedirs(VIDEO_DIR, exist_ok=True)
            filename = f"video_{job_id[:8]}_{task_id[:8]}.mp4"
            filepath = os.path.join(VIDEO_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(video_bytes)

            file_url = f"/api/static/generated/viral_videos/{filename}"
            await jobs.save_asset(db, job_id, task_id, "video",
                                  file_url=file_url, file_path=filepath, mime_type="video/mp4")
            await jobs.update_task(db, task_id, "completed", fallback_used=False)
            logger.info(f"[VIDEO_WORKER] Video saved: {filepath} ({len(video_bytes)} bytes)")
        else:
            logger.warning("[VIDEO_WORKER] Video composition returned empty, skipping")
            await jobs.update_task(db, task_id, "completed", fallback_used=True)

    except Exception as e:
        logger.error(f"[VIDEO_WORKER] Video failed: {e}", exc_info=True)
        await jobs.update_task(db, task_id, "completed", fallback_used=True)

    await _check_and_dispatch_packaging(job_id)


async def _compose_video(thumb_path: str, hook_text: str, niche: str, job_id: str) -> bytes | None:
    """
    Create a 6-second social-ready MP4 from thumbnail + text overlay + Ken Burns zoom.
    Uses moviepy for composition.
    """
    import asyncio
    return await asyncio.to_thread(_compose_video_sync, thumb_path, hook_text, niche, job_id)


def _compose_video_sync(thumb_path: str, hook_text: str, niche: str, job_id: str) -> bytes | None:
    try:
        from moviepy import ImageClip, TextClip, CompositeVideoClip
        import numpy as np

        duration = 6

        # Base image clip with slow zoom (Ken Burns)
        img_clip = ImageClip(thumb_path).with_duration(duration)
        w, h = img_clip.size

        # Target size for social (1080x1080 or clip size)
        target_w, target_h = min(w, 1080), min(h, 1080)

        def zoom_effect(t):
            """Slow zoom from 100% to 110% over duration."""
            scale = 1 + 0.1 * (t / duration)
            new_w = int(target_w * scale)
            new_h = int(target_h * scale)
            return (new_w, new_h)

        img_clip = img_clip.resized(lambda t: zoom_effect(t))

        # Text overlay — hook text at bottom
        try:
            txt_clip = TextClip(
                text=hook_text[:80],
                font_size=36,
                color='white',
                font='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                stroke_color='black',
                stroke_width=2,
                method='caption',
                size=(target_w - 80, None),
            ).with_duration(duration).with_position(('center', target_h - 120))

            # Niche tag at top
            tag_clip = TextClip(
                text=niche.upper(),
                font_size=20,
                color='#f97316',
                font='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                stroke_color='black',
                stroke_width=1,
            ).with_duration(duration).with_position(('center', 30))

            final = CompositeVideoClip([img_clip, txt_clip, tag_clip], size=(target_w, target_h))
        except Exception as text_err:
            logger.warning(f"[VIDEO] Text overlay failed, using image only: {text_err}")
            final = img_clip.resized((target_w, target_h))

        # Write to temp file via moviepy
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name

        final.write_videofile(
            tmp_path,
            fps=24,
            codec="libx264",
            audio=False,
            preset="ultrafast",
            logger=None,
        )
        final.close()

        # Re-encode with system ffmpeg for maximum browser compatibility
        # (moviepy's bundled ffmpeg can produce files some browsers reject)
        import subprocess
        web_path = tmp_path + "_web.mp4"
        reencode = subprocess.run([
            "/usr/bin/ffmpeg", "-y", "-i", tmp_path,
            "-c:v", "libx264",
            "-profile:v", "baseline", "-level", "3.0",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-preset", "ultrafast",
            "-an",
            web_path,
        ], capture_output=True, text=True, timeout=60)

        if reencode.returncode == 0 and os.path.exists(web_path):
            logger.info("[VIDEO] Re-encoded with system ffmpeg for web compat")
            with open(web_path, "rb") as f:
                video_bytes = f.read()
            os.unlink(web_path)
        else:
            logger.warning(f"[VIDEO] System ffmpeg re-encode failed, using moviepy output: {reencode.stderr[:200]}")
            with open(tmp_path, "rb") as f:
                video_bytes = f.read()

        os.unlink(tmp_path)
        return video_bytes

    except Exception as e:
        logger.error(f"[VIDEO] Composition failed: {e}", exc_info=True)
        return None


async def _check_and_dispatch_packaging(job_id: str):
    if await jobs.all_pretasks_done(db, job_id):
        pkg_task = await db.viral_job_tasks.find_one_and_update(
            {"job_id": job_id, "task_type": "packaging", "status": "pending"},
            {"$set": {"status": "processing"}},
            projection={"task_id": 1, "_id": 0},
        )
        if pkg_task:
            logger.info(f"[VIDEO_WORKER] Claimed packaging for job {job_id}")
            await dispatch_task(Q_PACKAGING, {
                "task_id": pkg_task["task_id"],
                "job_id": job_id,
            })
