"""
TTS Adapter — REAL implementation using OpenAI TTS via Emergent.
Generates narration audio from episode scripts.

NO MOCKS. NO PLACEHOLDERS. REAL AUDIO OUTPUT.
"""
import os
import logging
from typing import Optional, Dict, List
from pathlib import Path

logger = logging.getLogger("story_engine.adapters.tts")

EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
STATIC_DIR = Path("/app/backend/static/generated")
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Voice mapping for narration styles
VOICE_MAP = {
    "dramatic": "onyx",
    "calm": "nova",
    "mysterious": "echo",
    "playful": "shimmer",
    "neutral": "alloy",
}


async def generate_narration(
    episode_plan: Dict,
    scene_motion_plans: List[Dict],
    job_id: str = "",
) -> Dict:
    """
    Generate REAL narration audio using OpenAI TTS.
    Returns: {"status": "ready"|"failed"|"skipped", "url": str|None, "local_path": str|None}
    """
    if not EMERGENT_KEY:
        return {"status": "failed", "url": None, "error": "No EMERGENT_LLM_KEY"}

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
        return {"status": "skipped", "url": None, "segments": [], "note": "No narration text"}

    # Build full narration
    full_text = " ... ".join([s["text"] for s in segments])

    if len(full_text) < 10:
        return {"status": "skipped", "url": None, "segments": segments, "note": "Narration text too short"}

    narration_style = episode_plan.get("narration_style", "dramatic")
    voice = VOICE_MAP.get(narration_style, "alloy")

    try:
        from emergentintegrations.llm.openai import OpenAITextToSpeech

        tts = OpenAITextToSpeech(api_key=EMERGENT_KEY)
        audio_bytes = await tts.generate_speech(
            text=full_text[:4096],
            model="tts-1",
            voice=voice,
            speed=1.0,
            response_format="mp3",
        )

        if not audio_bytes:
            return {"status": "failed", "url": None, "error": "TTS returned no audio"}

        # Save locally
        filename = f"se_{job_id[:8]}_narration.mp3"
        local_path = str(STATIC_DIR / filename)
        with open(local_path, "wb") as f:
            f.write(audio_bytes)

        # Upload to R2
        url = await _upload_audio_to_r2(audio_bytes, filename, job_id)
        if not url:
            url = f"/api/generated/{filename}"

        size_kb = len(audio_bytes) / 1024
        logger.info(f"[TTS] Narration generated ({size_kb:.0f}KB, voice={voice})")

        return {
            "status": "ready",
            "url": url,
            "local_path": local_path,
            "segments": segments,
            "voice": voice,
            "model": "tts-1",
        }

    except Exception as e:
        logger.error(f"[TTS] Narration generation failed: {e}")
        return {"status": "failed", "url": None, "error": str(e)}


async def _upload_audio_to_r2(data: bytes, filename: str, job_id: str) -> Optional[str]:
    """Upload audio to R2."""
    try:
        import tempfile
        from services.cloudflare_r2_storage import get_r2_storage
        r2 = get_r2_storage()
        if not r2.is_configured:
            return None

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        try:
            ok, pub_url, key = await r2.upload_file_multipart(tmp_path, "voice", job_id, filename)
            if ok and pub_url:
                return pub_url
        finally:
            os.unlink(tmp_path)

    except Exception as e:
        logger.warning(f"[TTS] R2 upload failed: {e}")

    return None
