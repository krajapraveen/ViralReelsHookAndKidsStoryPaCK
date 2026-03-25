"""
TTS Adapter — Interface for Kokoro-82M self-hosted TTS.
Generates narration audio from episode scripts.

In production: connects to self-hosted Kokoro via API.
Currently: provides the interface contract + queue for worker processing.
"""
import os
import logging
from typing import Optional, Dict, List

logger = logging.getLogger("story_engine.adapters.tts")

KOKORO_ENDPOINT = os.environ.get("KOKORO_TTS_ENDPOINT", "")  # e.g. http://tts-worker:8080/synthesize


class TTSRequest:
    """Standardized TTS request."""
    def __init__(
        self,
        text: str,
        voice_style: str = "dramatic",
        speed: float = 1.0,
        language: str = "en",
    ):
        self.text = text
        self.voice_style = voice_style
        self.speed = speed
        self.language = language

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "voice_style": self.voice_style,
            "speed": self.speed,
            "language": self.language,
        }


async def generate_narration(
    episode_plan: Dict,
    scene_motion_plans: List[Dict],
) -> Dict:
    """
    Generate narration audio for the episode.
    Combines scene dialogues and narration into a single audio track.
    Returns: {"status": "queued"|"ready"|"failed", "url": str|None, "segments": list}
    """
    # Build narration script from scenes
    segments = []
    for scene in episode_plan.get("scene_breakdown", []):
        text = ""
        if scene.get("dialogue"):
            text = scene["dialogue"]
        elif scene.get("action_summary"):
            text = scene["action_summary"]

        if text:
            segments.append({
                "scene_number": scene["scene_number"],
                "text": text,
                "emotion": scene.get("emotional_beat", "neutral"),
            })

    if not segments:
        return {"status": "skipped", "url": None, "segments": [], "note": "No narration text found"}

    # Build full narration text
    full_text = " ... ".join([s["text"] for s in segments])

    narration_style = episode_plan.get("narration_style", "dramatic")
    request = TTSRequest(text=full_text, voice_style=narration_style)

    if KOKORO_ENDPOINT:
        return await _send_to_tts_worker(request.to_dict(), segments)
    else:
        return {
            "status": "queued",
            "url": None,
            "request": request.to_dict(),
            "segments": segments,
            "model": "kokoro-82m",
            "note": "Queued for TTS worker. Set KOKORO_TTS_ENDPOINT to connect to self-hosted Kokoro.",
        }


async def _send_to_tts_worker(payload: dict, segments: list) -> Dict:
    """Send TTS request to Kokoro worker."""
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                KOKORO_ENDPOINT,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "status": data.get("status", "queued"),
                        "url": data.get("url"),
                        "segments": segments,
                        "model": "kokoro-82m",
                    }
                else:
                    error = await resp.text()
                    logger.error(f"[TTS] Worker returned {resp.status}: {error}")
                    return {"status": "failed", "url": None, "error": error}
    except Exception as e:
        logger.error(f"[TTS] Worker request failed: {e}")
        return {"status": "failed", "url": None, "error": str(e)}
