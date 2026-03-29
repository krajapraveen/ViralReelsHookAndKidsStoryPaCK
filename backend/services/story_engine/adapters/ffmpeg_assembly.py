"""
FFmpeg Assembly Adapter — Real implementation.
Stitches scene clips, adds transitions, mixes audio, burns subtitles,
generates preview and thumbnail.

This is the ONLY assembly tool. It does NOT animate. Moving clips come from Wan2.1.

Resilience: Long-running FFmpeg operations use a detached shell wrapper that survives
backend hot-reloads. A marker file signals completion so the pipeline can resume.
"""
import os
import logging
import asyncio
import uuid
import subprocess
from typing import List, Optional, Dict

logger = logging.getLogger("story_engine.adapters.ffmpeg")

OUTPUT_DIR = os.environ.get("STORY_ENGINE_OUTPUT_DIR", "/tmp/story_engine_output")
FFMPEG_WORK_DIR = os.path.join(OUTPUT_DIR, ".ffmpeg_work")


def _ensure_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(FFMPEG_WORK_DIR, exist_ok=True)


async def _run_ffmpeg(cmd: str, timeout: int = 120) -> bool:
    """Run a short FFmpeg command inline (thumbnails, previews, normalization)."""
    logger.info(f"[FFMPEG] Running: {cmd[:200]}...")
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        preexec_fn=os.setsid,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if proc.returncode != 0:
            logger.error(f"[FFMPEG] Failed (exit {proc.returncode}): {stderr.decode()[-1500:]}")
            return False
        return True
    except asyncio.TimeoutError:
        try:
            os.killpg(os.getpgid(proc.pid), 9)
        except OSError:
            proc.kill()
        logger.error(f"[FFMPEG] Timed out after {timeout}s")
        return False


async def _run_ffmpeg_resilient(cmd: str, output_path: str, timeout: int = 300) -> bool:
    """
    Run a long FFmpeg command in a detached process that survives hot-reloads.
    Uses a shell wrapper + marker files for completion signaling.
    """
    _ensure_dir()
    task_id = uuid.uuid4().hex[:8]
    marker_done = os.path.join(FFMPEG_WORK_DIR, f"{task_id}.done")
    marker_fail = os.path.join(FFMPEG_WORK_DIR, f"{task_id}.fail")
    log_file = os.path.join(FFMPEG_WORK_DIR, f"{task_id}.log")
    script_path = os.path.join(FFMPEG_WORK_DIR, f"{task_id}.sh")

    # Check if output already exists from a previous interrupted run
    if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
        logger.info(f"[FFMPEG-RESILIENT] Output already exists: {output_path}")
        return True

    # Write wrapper script
    script = f"""#!/bin/bash
{cmd} > "{log_file}" 2>&1
RC=$?
if [ $RC -eq 0 ] && [ -f "{output_path}" ]; then
    echo "OK" > "{marker_done}"
else
    echo "EXIT_CODE=$RC" > "{marker_fail}"
fi
rm -f "{script_path}"
"""
    with open(script_path, "w") as f:
        f.write(script)
    os.chmod(script_path, 0o755)

    logger.info(f"[FFMPEG-RESILIENT] Launching detached task {task_id}: {cmd[:150]}...")

    # Launch fully detached: nohup + setsid + stdin/stdout redirected
    subprocess.Popen(
        ["nohup", "bash", script_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )

    # Poll for completion markers
    poll_interval = 2.0
    elapsed = 0.0
    while elapsed < timeout:
        if os.path.exists(marker_done):
            logger.info(f"[FFMPEG-RESILIENT] Task {task_id} completed successfully")
            _cleanup_markers(task_id)
            return True
        if os.path.exists(marker_fail):
            try:
                with open(marker_fail) as f:
                    reason = f.read().strip()
            except Exception:
                reason = "unknown"
            logger.error(f"[FFMPEG-RESILIENT] Task {task_id} failed: {reason}")
            # Log last 500 chars of FFmpeg output
            if os.path.exists(log_file):
                try:
                    with open(log_file) as f:
                        content = f.read()
                    logger.error(f"[FFMPEG-RESILIENT] Log tail: {content[-500:]}")
                except Exception:
                    pass
            _cleanup_markers(task_id)
            return False
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

    logger.error(f"[FFMPEG-RESILIENT] Task {task_id} timed out after {timeout}s")
    _cleanup_markers(task_id)
    return False


def _cleanup_markers(task_id: str):
    """Remove marker and log files for a completed task."""
    for ext in (".done", ".fail", ".log", ".sh"):
        path = os.path.join(FFMPEG_WORK_DIR, f"{task_id}{ext}")
        try:
            os.remove(path)
        except OSError:
            pass


def _sanitize_transition(raw: str) -> str:
    """Map LLM-generated transition names to valid FFmpeg xfade transitions."""
    VALID_XFADE = {
        "fade", "fadeblack", "fadewhite", "dissolve",
        "wipeleft", "wiperight", "wipeup", "wipedown",
        "slideleft", "slideright", "slideup", "slidedown",
        "smoothleft", "smoothright", "smoothup", "smoothdown",
        "circlecrop", "circleopen", "circleclose",
        "radial", "rectcrop", "distance", "pixelize",
        "diagtl", "diagtr", "diagbl", "diagbr",
        "horzopen", "horzclose", "vertopen", "vertclose",
        "zoomin", "fadefast", "fadeslow",
    }
    LLM_MAP = {
        "cut": "fade",
        "crossfade": "fade",
        "cross_fade": "fade",
        "cross-fade": "fade",
        "wipe": "wipeleft",
        "slide": "slideleft",
        "zoom": "zoomin",
        "dissolve_slow": "dissolve",
        "hard_cut": "fade",
        "none": "fade",
        "": "fade",
    }
    raw_lower = (raw or "").strip().lower()
    if raw_lower in VALID_XFADE:
        return raw_lower
    return LLM_MAP.get(raw_lower, "fade")


async def stitch_clips(
    clip_paths: List[str],
    output_path: str,
    transition_duration: float = 0.5,
    transitions: Optional[List[str]] = None,
) -> bool:
    """
    Stitch scene clips together with crossfade transitions.
    Pre-normalizes all clips to same resolution/fps/timebase to avoid xfade errors.
    """
    _ensure_dir()

    if not clip_paths:
        logger.error("[FFMPEG] No clips to stitch")
        return False

    if len(clip_paths) == 1:
        cmd = f'ffmpeg -y -i "{clip_paths[0]}" -c:v libx264 -pix_fmt yuv420p -preset medium -crf 20 -movflags +faststart "{output_path}"'
        return await _run_ffmpeg(cmd)

    # Step 1: Normalize all clips to 25fps, 1280x720, same pixel format
    normalized_paths = []
    norm_dir = os.path.join(OUTPUT_DIR, "normalized")
    os.makedirs(norm_dir, exist_ok=True)
    for i, path in enumerate(clip_paths):
        basename = os.path.basename(path).replace(".mp4", "")
        norm_path = os.path.join(norm_dir, f"{basename}_norm.mp4")
        norm_cmd = (
            f'ffmpeg -y -i "{path}" '
            f'-vf "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=25,setpts=PTS-STARTPTS" '
            f'-c:v libx264 -pix_fmt yuv420p -preset fast -crf 20 -an "{norm_path}"'
        )
        ok = await _run_ffmpeg(norm_cmd, timeout=60)
        if ok and os.path.exists(norm_path):
            normalized_paths.append(norm_path)
        else:
            logger.warning(f"[FFMPEG] Failed to normalize clip {i+1}, using original")
            normalized_paths.append(path)

    # Step 2: Get actual durations of normalized clips for accurate xfade offsets
    durations = []
    for np_path in normalized_paths:
        dur_cmd = f'ffprobe -v error -show_entries format=duration -of csv=p=0 "{np_path}"'
        proc = await asyncio.create_subprocess_shell(dur_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await proc.communicate()
        try:
            durations.append(float(stdout.decode().strip()))
        except (ValueError, TypeError):
            durations.append(4.0)  # fallback

    # Step 3: Build xfade filter chain with sanitized transitions and correct offsets
    inputs = " ".join([f'-i "{p}"' for p in normalized_paths])
    filter_parts = []
    prev_label = "0:v"
    cumulative_offset = 0

    for i in range(1, len(normalized_paths)):
        raw_trans = transitions[i-1] if transitions and i-1 < len(transitions) else "fade"
        trans = _sanitize_transition(raw_trans)
        out_label = f"v{i}" if i < len(normalized_paths) - 1 else "v"
        cumulative_offset += durations[i-1] - transition_duration
        # Guard against negative or zero offsets
        if cumulative_offset < 0.1:
            cumulative_offset = 0.1
        filter_parts.append(
            f"[{prev_label}][{i}:v]xfade=transition={trans}:duration={transition_duration}:offset={cumulative_offset:.2f}[{out_label}]"
        )
        prev_label = out_label

    filter_complex = ";".join(filter_parts)
    cmd = (
        f'ffmpeg -y {inputs} '
        f"-filter_complex '{filter_complex}' "
        f'-map "[v]" -c:v libx264 -pix_fmt yuv420p -crf 20 -movflags +faststart "{output_path}"'
    )
    logger.info(f"[FFMPEG] Stitching {len(normalized_paths)} clips with transitions: {[_sanitize_transition(t) for t in (transitions or [])]}")
    result = await _run_ffmpeg(cmd, timeout=180)

    # Fallback: if xfade stitch fails, use simple concat (no transitions)
    if not result:
        logger.warning("[FFMPEG] xfade stitch failed, falling back to concat demuxer")
        concat_list = os.path.join(OUTPUT_DIR, "concat_list.txt")
        with open(concat_list, "w") as f:
            for p in normalized_paths:
                f.write(f"file '{p}'\n")
        concat_cmd = (
            f'ffmpeg -y -f concat -safe 0 -i "{concat_list}" '
            f'-c:v libx264 -pix_fmt yuv420p -crf 20 -movflags +faststart "{output_path}"'
        )
        result = await _run_ffmpeg(concat_cmd, timeout=120)
        try:
            os.remove(concat_list)
        except OSError:
            pass

    # Cleanup normalized files
    for np_path in normalized_paths:
        if np_path.endswith("_norm.mp4"):
            try:
                os.remove(np_path)
            except OSError:
                pass

    return result


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
        cmd = f'ffmpeg -y -i "{video_path}" -c copy -movflags +faststart "{output_path}"'
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
        f"-filter_complex '{filter_complex}' "
        f'-map 0:v -map {audio_map} -c:v copy -c:a aac -b:a 192k -movflags +faststart "{output_path}"'
    )
    return await _run_ffmpeg(cmd, timeout=180)


async def generate_preview(
    video_path: str,
    output_path: str,
    duration: float = 8.0,
) -> bool:
    """Generate a short preview clip."""
    _ensure_dir()
    cmd = (
        f'ffmpeg -y -i "{video_path}" -t {duration} '
        f'-c:v libx264 -pix_fmt yuv420p -crf 24 -movflags +faststart "{output_path}"'
    )
    return await _run_ffmpeg(cmd)


async def generate_thumbnail(
    video_path: str,
    output_path: str,
    timestamp: float = 2.0,
) -> bool:
    """Extract a single frame as poster-quality thumbnail (poster_large)."""
    _ensure_dir()
    cmd = (
        f'ffmpeg -y -i "{video_path}" -ss {timestamp} '
        f'-vframes 1 -q:v 2 "{output_path}"'
    )
    return await _run_ffmpeg(cmd)


async def generate_thumbnail_small(
    video_path: str,
    output_path: str,
    timestamp: float = 2.0,
    width: int = 400,
    height: int = 530,
) -> bool:
    """Generate a compressed card-sized thumbnail (thumbnail_small) for feed cards.
    Outputs JPEG at ~30-50KB for fast loading on cards."""
    _ensure_dir()
    cmd = (
        f'ffmpeg -y -i "{video_path}" -ss {timestamp} '
        f'-vframes 1 -vf "scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}" '
        f'-q:v 6 "{output_path}"'
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
        f'-vf "subtitles={srt_path}" -c:v libx264 -crf 20 -c:a copy -movflags +faststart "{output_path}"'
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
        f'-t {duration} -c:v libx264 -pix_fmt yuv420p -movflags +faststart "{output_path}"'
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
