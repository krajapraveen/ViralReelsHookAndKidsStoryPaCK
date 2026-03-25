"""
Video Generation Adapter — Interface for Wan2.1-T2V-14B / Wan2.1-I2V-14B.
Generates moving scene clips and keyframes.

In production: connects to self-hosted Wan2.1 via inference API.
Currently: provides the interface contract + placeholder that returns structured status.
The actual GPU inference will be handled by the worker when deployed.
"""
import os
import logging
from typing import Optional, Dict, List
from ..negative_prompt import get_negative_prompt, get_style_positive_prompt

logger = logging.getLogger("story_engine.adapters.video_gen")

# Configuration — set these when deploying to point at your GPU workers
WAN_T2V_ENDPOINT = os.environ.get("WAN_T2V_ENDPOINT", "")  # e.g. http://gpu-worker:8080/t2v
WAN_I2V_ENDPOINT = os.environ.get("WAN_I2V_ENDPOINT", "")  # e.g. http://gpu-worker:8080/i2v
KEYFRAME_ENDPOINT = os.environ.get("KEYFRAME_GEN_ENDPOINT", "")  # e.g. http://gpu-worker:8080/keyframe


class VideoGenRequest:
    """Standardized request for video/image generation."""
    def __init__(
        self,
        prompt: str,
        negative_prompt: str,
        style_id: str = "cartoon_2d",
        duration_seconds: float = 5.0,
        width: int = 1280,
        height: int = 720,
        fps: int = 24,
        seed: Optional[int] = None,
        reference_image_url: Optional[str] = None,
    ):
        self.prompt = prompt
        self.negative_prompt = negative_prompt
        self.style_prompt = get_style_positive_prompt(style_id)
        self.full_prompt = f"{self.style_prompt}, {prompt}"
        self.duration_seconds = duration_seconds
        self.width = width
        self.height = height
        self.fps = fps
        self.seed = seed
        self.reference_image_url = reference_image_url

    def to_dict(self) -> dict:
        return {
            "prompt": self.full_prompt,
            "negative_prompt": self.negative_prompt,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "duration_seconds": self.duration_seconds,
            "seed": self.seed,
            "reference_image_url": self.reference_image_url,
        }


async def generate_keyframe(
    scene_plan: Dict,
    continuity: Dict,
    style_id: str = "cartoon_2d",
    category: str = "",
) -> Dict:
    """
    Generate a single keyframe image for a scene.
    Returns: {"status": "queued"|"ready"|"failed", "url": str|None, "request": dict}
    """
    prompt = scene_plan.get("keyframe_prompt", scene_plan.get("action", ""))
    neg_prompt = get_negative_prompt(category)

    request = VideoGenRequest(
        prompt=prompt,
        negative_prompt=neg_prompt,
        style_id=style_id,
        reference_image_url=continuity.get("characters", [{}])[0].get("reference_image_url") if continuity.get("characters") else None,
    )

    if KEYFRAME_ENDPOINT:
        # Production: send to GPU worker
        return await _send_to_worker(KEYFRAME_ENDPOINT, request.to_dict(), "keyframe")
    else:
        # Development: queue for worker processing
        return {
            "status": "queued",
            "url": None,
            "request": request.to_dict(),
            "model": "wan2.1-keyframe",
            "note": "Queued for GPU worker. Set KEYFRAME_GEN_ENDPOINT to connect to self-hosted inference.",
        }


async def generate_scene_clip(
    scene_plan: Dict,
    keyframe_url: Optional[str],
    continuity: Dict,
    style_id: str = "cartoon_2d",
    category: str = "",
) -> Dict:
    """
    Generate a moving scene clip using Wan2.1-T2V or I2V.
    If keyframe_url exists, uses Image-to-Video (I2V). Otherwise Text-to-Video (T2V).
    Returns: {"status": "queued"|"ready"|"failed", "url": str|None, "request": dict}
    """
    prompt = scene_plan.get("video_prompt", scene_plan.get("action", ""))
    neg_prompt = get_negative_prompt(category)
    duration = scene_plan.get("clip_duration_seconds", 5.0)

    # Add motion notes to prompt
    motion_notes = scene_plan.get("movement_notes", "")
    camera = scene_plan.get("camera_motion", "static")
    if motion_notes:
        prompt = f"{prompt}, {motion_notes}"
    if camera != "static":
        prompt = f"{prompt}, camera {camera.replace('_', ' ')}"

    request = VideoGenRequest(
        prompt=prompt,
        negative_prompt=neg_prompt,
        style_id=style_id,
        duration_seconds=duration,
        reference_image_url=keyframe_url,
    )

    # Choose T2V or I2V based on keyframe availability
    if keyframe_url and WAN_I2V_ENDPOINT:
        return await _send_to_worker(WAN_I2V_ENDPOINT, request.to_dict(), "i2v_clip")
    elif WAN_T2V_ENDPOINT:
        return await _send_to_worker(WAN_T2V_ENDPOINT, request.to_dict(), "t2v_clip")
    else:
        model = "wan2.1-i2v-14b" if keyframe_url else "wan2.1-t2v-14b"
        return {
            "status": "queued",
            "url": None,
            "request": request.to_dict(),
            "model": model,
            "note": f"Queued for GPU worker. Set {'WAN_I2V_ENDPOINT' if keyframe_url else 'WAN_T2V_ENDPOINT'} to connect.",
        }


async def _send_to_worker(endpoint: str, payload: dict, job_type: str) -> Dict:
    """Send generation request to GPU worker API."""
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                endpoint,
                json={**payload, "job_type": job_type},
                timeout=aiohttp.ClientTimeout(total=300),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "status": data.get("status", "queued"),
                        "url": data.get("url"),
                        "request": payload,
                        "model": data.get("model", "wan2.1"),
                    }
                else:
                    error_text = await resp.text()
                    logger.error(f"[VIDEO_GEN] Worker returned {resp.status}: {error_text}")
                    return {"status": "failed", "url": None, "error": error_text}
    except Exception as e:
        logger.error(f"[VIDEO_GEN] Worker request failed: {e}")
        return {"status": "failed", "url": None, "error": str(e)}
