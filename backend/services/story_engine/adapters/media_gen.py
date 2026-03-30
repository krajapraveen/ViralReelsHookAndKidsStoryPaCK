"""
Deterministic Media Asset Generator — Pillow + FFmpeg.

Generates homepage-ready assets during the pipeline assembly stage:
  - thumbnail_small: 400x530 JPEG (~30KB) for feed cards
  - poster_large:   1280x720 JPEG (~100KB) for hero sections

These are the ONLY images the Feed API and Dashboard should ever reference.
NO runtime derivation. NO fallbacks. NO guessing.
"""
import os
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image

logger = logging.getLogger("story_engine.adapters.media_gen")


def extract_frame(video_path: str) -> Optional[str]:
    """Extract a single stable frame from a video using FFmpeg.
    Returns path to the extracted JPEG frame, or None on failure."""
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    output = tmp.name
    tmp.close()

    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-ss", "00:00:01.000",
        "-vframes", "1",
        "-q:v", "2",
        output,
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=30)
        if os.path.exists(output) and os.path.getsize(output) > 0:
            logger.info(f"[MEDIA_GEN] Frame extracted from {Path(video_path).name}")
            return output
        logger.warning("[MEDIA_GEN] FFmpeg produced empty frame output")
        return None
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        logger.error(f"[MEDIA_GEN] Frame extraction failed: {e}")
        try:
            os.unlink(output)
        except OSError:
            pass
        return None


def generate_thumbnail_small(input_image: str, output_path: str) -> bool:
    """Generate a 400x530 JPEG card thumbnail from any source image.
    Uses center-crop + LANCZOS resize for maximum quality at ~30KB."""
    try:
        img = Image.open(input_image).convert("RGB")

        target_w, target_h = 400, 530
        img_ratio = img.width / img.height
        target_ratio = target_w / target_h

        if img_ratio > target_ratio:
            new_width = int(img.height * target_ratio)
            left = (img.width - new_width) // 2
            img = img.crop((left, 0, left + new_width, img.height))
        else:
            new_height = int(img.width / target_ratio)
            top = (img.height - new_height) // 2
            img = img.crop((0, top, img.width, top + new_height))

        img = img.resize((target_w, target_h), Image.LANCZOS)
        img.save(output_path, "JPEG", quality=75, optimize=True)

        size_kb = os.path.getsize(output_path) / 1024
        logger.info(f"[MEDIA_GEN] thumbnail_small generated: {target_w}x{target_h}, {size_kb:.0f}KB")
        return True
    except Exception as e:
        logger.error(f"[MEDIA_GEN] thumbnail_small generation failed: {e}")
        return False


def generate_poster_large(input_image: str, output_path: str) -> bool:
    """Generate a 1280x720 JPEG poster from any source image.
    Uses center-crop + LANCZOS resize at high quality (~100KB)."""
    try:
        img = Image.open(input_image).convert("RGB")

        target_w, target_h = 1280, 720
        img_ratio = img.width / img.height
        target_ratio = target_w / target_h

        if img_ratio > target_ratio:
            new_width = int(img.height * target_ratio)
            left = (img.width - new_width) // 2
            img = img.crop((left, 0, left + new_width, img.height))
        else:
            new_height = int(img.width / target_ratio)
            top = (img.height - new_height) // 2
            img = img.crop((0, top, img.width, top + new_height))

        img = img.resize((target_w, target_h), Image.LANCZOS)
        img.save(output_path, "JPEG", quality=85, optimize=True)

        size_kb = os.path.getsize(output_path) / 1024
        logger.info(f"[MEDIA_GEN] poster_large generated: {target_w}x{target_h}, {size_kb:.0f}KB")
        return True
    except Exception as e:
        logger.error(f"[MEDIA_GEN] poster_large generation failed: {e}")
        return False


async def generate_media_assets(
    video_path: str,
    job_id: str,
    fallback_image_path: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Generate deterministic homepage media assets from a video (or fallback image).

    1. Extract a frame from the video using FFmpeg
    2. Generate thumbnail_small (400x530 JPEG) using Pillow
    3. Generate poster_large (1280x720 JPEG) using Pillow
    4. Upload both to R2 under media/{job_id}/
    5. Return (thumbnail_small_url, poster_large_url)

    Returns (None, None) if generation fails entirely.
    """
    # Step 1: Get source image — prefer video frame, fall back to provided image
    frame_path = None
    if video_path and os.path.exists(video_path):
        frame_path = extract_frame(video_path)

    if not frame_path and fallback_image_path and os.path.exists(fallback_image_path):
        frame_path = fallback_image_path
        logger.info(f"[MEDIA_GEN] Using fallback image for job {job_id[:8]}")

    if not frame_path:
        logger.error(f"[MEDIA_GEN] No source image available for job {job_id[:8]}")
        return None, None

    # Step 2: Generate both assets
    thumb_path = f"/tmp/{job_id}_thumb_small.jpg"
    poster_path = f"/tmp/{job_id}_poster_large.jpg"

    thumb_ok = generate_thumbnail_small(frame_path, thumb_path)
    poster_ok = generate_poster_large(frame_path, poster_path)

    # Clean up extracted frame (only if we extracted it, not if it's the fallback)
    if frame_path != fallback_image_path:
        try:
            os.unlink(frame_path)
        except OSError:
            pass

    # Step 3: Upload to R2
    thumb_url = None
    poster_url = None

    try:
        from services.story_engine.adapters.video_gen import _upload_to_r2

        if thumb_ok and os.path.exists(thumb_path):
            with open(thumb_path, "rb") as f:
                thumb_url = await _upload_to_r2(
                    f.read(),
                    f"media/{job_id}/thumbnail_small.jpg",
                    job_id,
                    "thumbnail",
                )
            if not thumb_url:
                thumb_url = f"/api/generated/{job_id}_thumb_small.jpg"

        if poster_ok and os.path.exists(poster_path):
            with open(poster_path, "rb") as f:
                poster_url = await _upload_to_r2(
                    f.read(),
                    f"media/{job_id}/poster_large.jpg",
                    job_id,
                    "image",
                )
            if not poster_url:
                poster_url = f"/api/generated/{job_id}_poster_large.jpg"

    except Exception as e:
        logger.error(f"[MEDIA_GEN] R2 upload failed for job {job_id[:8]}: {e}")

    # Clean up temp files
    for p in (thumb_path, poster_path):
        try:
            os.unlink(p)
        except OSError:
            pass

    logger.info(f"[MEDIA_GEN] Assets complete for job {job_id[:8]}: thumb={bool(thumb_url)}, poster={bool(poster_url)}")
    return thumb_url, poster_url
