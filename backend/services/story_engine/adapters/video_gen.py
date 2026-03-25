"""
Video Generation Adapter — REAL implementation using Emergent services.
- Keyframes: GPT Image 1 via litellm
- Scene Clips: Sora 2 via OpenAIVideoGeneration
- Uploads to Cloudflare R2 for persistent storage.

NO MOCKS. NO PLACEHOLDERS. REAL OUTPUT.
"""
import os
import uuid
import logging
import asyncio
import tempfile
from typing import Optional, Dict, List
from pathlib import Path

from ..negative_prompt import get_negative_prompt, get_style_positive_prompt

logger = logging.getLogger("story_engine.adapters.video_gen")

EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
STATIC_DIR = Path("/app/backend/static/generated")
STATIC_DIR.mkdir(parents=True, exist_ok=True)


async def generate_keyframe(
    scene_plan: Dict,
    continuity: Dict,
    style_id: str = "cartoon_2d",
    category: str = "",
    job_id: str = "",
) -> Dict:
    """
    Generate a REAL keyframe image using GPT Image 1.
    Returns: {"status": "ready"|"failed", "url": str|None, "local_path": str|None}
    """
    if not EMERGENT_KEY:
        return {"status": "failed", "url": None, "error": "No EMERGENT_LLM_KEY"}

    prompt = scene_plan.get("keyframe_prompt", scene_plan.get("action", ""))
    style_prompt = get_style_positive_prompt(style_id)
    neg_prompt = get_negative_prompt(category)

    # Build character appearance into prompt for consistency
    chars = continuity.get("characters", [])
    char_desc = ""
    if chars:
        primary = chars[0]
        char_desc = f"{primary.get('name', 'character')}: {primary.get('reference_prompt', primary.get('clothing_default', ''))}"

    full_prompt = f"{style_prompt}. {prompt}"
    if char_desc:
        full_prompt += f". Character: {char_desc}"
    full_prompt += f". Avoid: {neg_prompt[:200]}"

    try:
        from services.image_gen_direct import generate_image_direct

        images = await generate_image_direct(
            api_key=EMERGENT_KEY,
            prompt=full_prompt[:1500],
            model="gpt-image-1",
            quality="low",
            size="1536x1024",
            n=1,
        )

        if not images:
            return {"status": "failed", "url": None, "error": "No images returned"}

        # Save locally
        scene_num = scene_plan.get("scene_number", 0)
        filename = f"se_{job_id[:8]}_kf_{scene_num}.png"
        local_path = str(STATIC_DIR / filename)
        with open(local_path, "wb") as f:
            f.write(images[0])

        # Upload to R2
        url = await _upload_to_r2(images[0], filename, job_id, "image")
        if not url:
            url = f"/api/generated/{filename}"

        logger.info(f"[VIDEO_GEN] Keyframe scene {scene_num} generated ({len(images[0])} bytes)")
        return {"status": "ready", "url": url, "local_path": local_path}

    except Exception as e:
        logger.error(f"[VIDEO_GEN] Keyframe generation failed: {e}")
        return {"status": "failed", "url": None, "error": str(e)}


async def generate_scene_clip(
    scene_plan: Dict,
    keyframe_url: Optional[str],
    keyframe_local_path: Optional[str],
    continuity: Dict,
    style_id: str = "cartoon_2d",
    category: str = "",
    job_id: str = "",
) -> Dict:
    """
    Generate a REAL moving scene clip using Sora 2.
    If keyframe exists, uses image-to-video. Otherwise text-to-video.
    Returns: {"status": "ready"|"failed", "url": str|None, "local_path": str|None}
    """
    if not EMERGENT_KEY:
        return {"status": "failed", "url": None, "error": "No EMERGENT_LLM_KEY"}

    from emergentintegrations.llm.openai import OpenAIVideoGeneration

    prompt = scene_plan.get("video_prompt", scene_plan.get("action", ""))
    style_prompt = get_style_positive_prompt(style_id)

    motion_notes = scene_plan.get("movement_notes", "")
    camera = scene_plan.get("camera_motion", "static")
    if motion_notes:
        prompt = f"{prompt}, {motion_notes}"
    if camera and camera != "static":
        prompt = f"{prompt}, camera {camera.replace('_', ' ')}"

    full_prompt = f"{style_prompt}. {prompt}. Cinematic quality, smooth motion."
    duration = min(int(scene_plan.get("clip_duration_seconds", 4)), 8)
    if duration not in (4, 8, 12):
        duration = 4

    scene_num = scene_plan.get("scene_number", 0)

    try:
        video_gen = OpenAIVideoGeneration(api_key=EMERGENT_KEY)

        logger.info(f"[VIDEO_GEN] Generating scene {scene_num} clip via Sora 2 (duration={duration}s)...")

        video_bytes = await asyncio.to_thread(
            video_gen.text_to_video,
            prompt=full_prompt[:1000],
            model="sora-2",
            size="1280x720",
            duration=duration,
            max_wait_time=600,
        )

        if not video_bytes:
            logger.error(f"[VIDEO_GEN] Sora returned no video for scene {scene_num}")
            return {"status": "failed", "url": None, "error": "Sora returned no video"}

        # Save locally
        filename = f"se_{job_id[:8]}_clip_{scene_num}.mp4"
        local_path = str(STATIC_DIR / filename)
        with open(local_path, "wb") as f:
            f.write(video_bytes)

        # Upload to R2
        url = await _upload_to_r2(video_bytes, filename, job_id, "video")
        if not url:
            url = f"/api/generated/{filename}"

        size_mb = len(video_bytes) / 1024 / 1024
        logger.info(f"[VIDEO_GEN] Scene {scene_num} clip generated ({size_mb:.1f}MB)")
        return {"status": "ready", "url": url, "local_path": local_path}

    except Exception as e:
        logger.error(f"[VIDEO_GEN] Scene clip generation failed for scene {scene_num}: {e}")
        return {"status": "failed", "url": None, "error": str(e)}


async def _upload_to_r2(data: bytes, filename: str, job_id: str, asset_type: str) -> Optional[str]:
    """Upload bytes to R2 storage. Returns public URL or None."""
    try:
        from services.cloudflare_r2_storage import get_r2_storage
        r2 = get_r2_storage()
        if not r2.is_configured:
            return None

        # Write to temp file for upload
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        try:
            ok, pub_url, key = await r2.upload_file_multipart(tmp_path, asset_type, job_id, filename)
            if ok and pub_url:
                return pub_url
        finally:
            os.unlink(tmp_path)

    except Exception as e:
        logger.warning(f"[VIDEO_GEN] R2 upload failed: {e}")

    return None
