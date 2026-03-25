"""
FFmpeg Assembly Adapter — Real implementation.
Stitches scene clips, adds transitions, mixes audio, burns subtitles,
generates preview and thumbnail.

This is the ONLY assembly tool. It does NOT animate. Moving clips come from Wan2.1.
"""
import os
import logging
import asyncio
import json
from typing import List, Optional, Dict

logger = logging.getLogger("story_engine.adapters.ffmpeg")

OUTPUT_DIR = os.environ.get("STORY_ENGINE_OUTPUT_DIR", "/tmp/story_engine_output")


def _ensure_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


async def _run_ffmpeg(cmd: str, timeout: int = 120) -> bool:
    """Run an FFmpeg command asynchronously."""
    logger.info(f"[FFMPEG] Running: {cmd[:200]}...")
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if proc.returncode != 0:
            logger.error(f"[FFMPEG] Failed (exit {proc.returncode}): {stderr.decode()[:500]}")
            return False
        return True
    except asyncio.TimeoutError:
        proc.kill()
        logger.error(f"[FFMPEG] Timed out after {timeout}s")
        return False


async def stitch_clips(
    clip_paths: List[str],
    output_path: str,
    transition_duration: float = 0.5,
    transitions: Optional[List[str]] = None,
) -> bool:
    """
    Stitch scene clips together with crossfade transitions.
    clip_paths: list of local file paths to scene clips
    output_path: where to write the final stitched video
    """
    _ensure_dir()

    if not clip_paths:
        logger.error("[FFMPEG] No clips to stitch")
        return False

    if len(clip_paths) == 1:
        # Single clip — just copy
        cmd = f'ffmpeg -y -i "{clip_paths[0]}" -c:v libx264 -pix_fmt yuv420p -preset medium -crf 20 "{output_path}"'
        return await _run_ffmpeg(cmd)

    # Multiple clips — use xfade transitions
    inputs = " ".join([f'-i "{p}"' for p in clip_paths])
    filter_parts = []
    prev_label = "0:v"

    for i in range(1, len(clip_paths)):
        trans = (transitions[i-1] if transitions and i-1 < len(transitions) else "fade")
        out_label = f"v{i}" if i < len(clip_paths) - 1 else "v"
        # Approximate offset: sum of clip durations minus transition overlap
        offset = i * 4.5  # ~5s clips with 0.5s overlap
        filter_parts.append(
            f"[{prev_label}][{i}:v]xfade=transition={trans}:duration={transition_duration}:offset={offset}[{out_label}]"
        )
        prev_label = out_label

    filter_complex = ";".join(filter_parts)
    cmd = (
        f'ffmpeg -y {inputs} '
        f'-filter_complex "{filter_complex}" '
        f'-map "[v]" -c:v libx264 -pix_fmt yuv420p -crf 20 "{output_path}"'
    )
    return await _run_ffmpeg(cmd, timeout=180)


async def mix_audio(
    video_path: str,
    narration_path: Optional[str],
    music_path: Optional[str],
    output_path: str,
    narration_volume: float = 1.2,
    music_volume: float = 0.18,
) -> bool:
    """Mix narration and background music onto the video."""
    _ensure_dir()

    if not narration_path and not music_path:
        # No audio — just copy video
        cmd = f'ffmpeg -y -i "{video_path}" -c copy "{output_path}"'
        return await _run_ffmpeg(cmd)

    inputs = f'-i "{video_path}"'
    filter_parts = []
    audio_inputs = []

    if narration_path:
        inputs += f' -i "{narration_path}"'
        idx = len(audio_inputs) + 1
        filter_parts.append(f"[{idx}:a]volume={narration_volume}[narr]")
        audio_inputs.append("narr")

    if music_path:
        inputs += f' -i "{music_path}"'
        idx = len(audio_inputs) + 1
        filter_parts.append(f"[{idx}:a]volume={music_volume}[music]")
        audio_inputs.append("music")

    if len(audio_inputs) == 2:
        filter_parts.append(f"[{audio_inputs[0]}][{audio_inputs[1]}]amix=inputs=2:duration=first:dropout_transition=2[a]")
        audio_map = '"[a]"'
    elif len(audio_inputs) == 1:
        audio_map = f'"[{audio_inputs[0]}]"'
    else:
        audio_map = ""

    filter_complex = ";".join(filter_parts)
    cmd = (
        f'ffmpeg -y {inputs} '
        f'-filter_complex "{filter_complex}" '
        f'-map 0:v -map {audio_map} -c:v copy -c:a aac -b:a 192k "{output_path}"'
    )
    return await _run_ffmpeg(cmd)


async def generate_preview(
    video_path: str,
    output_path: str,
    duration: float = 8.0,
) -> bool:
    """Generate a short preview clip."""
    _ensure_dir()
    cmd = (
        f'ffmpeg -y -i "{video_path}" -t {duration} '
        f'-c:v libx264 -pix_fmt yuv420p -crf 24 "{output_path}"'
    )
    return await _run_ffmpeg(cmd)


async def generate_thumbnail(
    video_path: str,
    output_path: str,
    timestamp: float = 2.0,
) -> bool:
    """Extract a single frame as thumbnail."""
    _ensure_dir()
    cmd = (
        f'ffmpeg -y -i "{video_path}" -ss {timestamp} '
        f'-vframes 1 -q:v 2 "{output_path}"'
    )
    return await _run_ffmpeg(cmd)


async def burn_subtitles(
    video_path: str,
    srt_path: str,
    output_path: str,
) -> bool:
    """Burn subtitles into video."""
    _ensure_dir()
    cmd = (
        f'ffmpeg -y -i "{video_path}" '
        f'-vf "subtitles={srt_path}" -c:v libx264 -crf 20 -c:a copy "{output_path}"'
    )
    return await _run_ffmpeg(cmd)


async def create_ken_burns_fallback(
    image_path: str,
    output_path: str,
    duration: float = 5.0,
) -> bool:
    """
    FALLBACK ONLY — Creates motion illusion from still keyframe.
    This is NOT real animation. Use only when video generation is unavailable.
    """
    _ensure_dir()
    cmd = (
        f'ffmpeg -y -loop 1 -i "{image_path}" '
        f'-vf "zoompan=z=\'min(zoom+0.0015,1.15)\':'
        f'x=\'iw/2-(iw/zoom/2)\':y=\'ih/2-(ih/zoom/2)\':'
        f'd={int(duration*25)}:s=1280x720,framerate=25" '
        f'-t {duration} -c:v libx264 -pix_fmt yuv420p "{output_path}"'
    )
    return await _run_ffmpeg(cmd)


def build_assembly_plan(
    scene_clips: List[str],
    narration_path: Optional[str] = None,
    music_path: Optional[str] = None,
    subtitle_path: Optional[str] = None,
    transitions: Optional[List[str]] = None,
) -> Dict:
    """
    Build a complete assembly plan (for logging/debugging).
    Does not execute — just documents what FFmpeg will do.
    """
    return {
        "steps": [
            {"step": 1, "action": "stitch_clips", "inputs": scene_clips, "transitions": transitions or ["crossfade"] * max(0, len(scene_clips) - 1)},
            {"step": 2, "action": "mix_audio", "narration": narration_path, "music": music_path},
            {"step": 3, "action": "burn_subtitles", "srt": subtitle_path} if subtitle_path else None,
            {"step": 4, "action": "generate_preview", "duration": 8},
            {"step": 5, "action": "generate_thumbnail", "timestamp": 2},
        ],
        "total_clips": len(scene_clips),
        "has_narration": bool(narration_path),
        "has_music": bool(music_path),
        "has_subtitles": bool(subtitle_path),
    }
