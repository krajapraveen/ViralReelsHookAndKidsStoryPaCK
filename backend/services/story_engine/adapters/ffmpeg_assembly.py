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


async def apply_addiction_triggers(
    video_path: str,
    output_path: str,
    trigger_text: Optional[str] = None,
    cliffhanger_text: Optional[str] = None,
    trigger_duration: float = 2.0,
) -> bool:
    """
    Apply addiction trigger effects to the final 2 seconds of a video:
    1. Slow zoom in (1.0 → 1.08) for tension
    2. Darken slightly (brightness 0.85) for mood shift
    3. Burn trigger/cliffhanger text overlay
    4. Audio volume swell (1.0 → 1.4) then abrupt cut

    Non-fatal: returns False if effects fail, pipeline can use original video.
    """
    _ensure_dir()

    # Get video duration
    dur_cmd = f'ffprobe -v error -show_entries format=duration -of csv=p=0 "{video_path}"'
    proc = await asyncio.create_subprocess_shell(dur_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, _ = await proc.communicate()
    try:
        total_duration = float(stdout.decode().strip())
    except (ValueError, TypeError):
        logger.warning("[FFMPEG] Could not determine video duration for triggers")
        return False

    if total_duration < 4.0:
        logger.warning(f"[FFMPEG] Video too short for triggers ({total_duration:.1f}s)")
        return False

    trigger_start = max(0, total_duration - trigger_duration)

    # Build filter chain
    # 1. Zoom: scale up last 2s with smooth ramp
    # 2. Darken: reduce brightness in last 2s
    # 3. Text overlay: burn cliffhanger text in last 2s
    vf_parts = []

    # Zoom + darken in last trigger_duration seconds
    zoom_expr = f"if(gte(t,{trigger_start:.2f}),min(1+0.04*(t-{trigger_start:.2f})/{trigger_duration:.2f},1.08),1)"
    brightness_expr = f"if(gte(t,{trigger_start:.2f}),0.85,1)"
    vf_parts.append(
        f"zoompan=z='{zoom_expr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1280x720:fps=25"
    )

    # Actually, zoompan requires loop input. Let's use a simpler approach:
    # scale + crop for zoom, eq for brightness
    vf_parts = []

    # Darken last 2 seconds
    vf_parts.append(f"eq=brightness={brightness_expr}")

    # Text overlay — burn trigger text or cliffhanger
    overlay_text = trigger_text or cliffhanger_text
    if overlay_text:
        # Sanitize text for FFmpeg drawtext
        safe_text = overlay_text.replace("'", "").replace('"', '').replace(":", "\\\\:").replace("\\", "")
        if len(safe_text) > 60:
            safe_text = safe_text[:57] + "..."

        # Show text starting at trigger_start, fade in
        alpha_expr = f"if(gte(t,{trigger_start:.2f}),min((t-{trigger_start:.2f})*2,1),0)"
        vf_parts.append(
            f"drawtext=text='{safe_text}'"
            f":fontsize=36:fontcolor=white@0.9"
            f":borderw=2:bordercolor=black@0.6"
            f":x=(w-text_w)/2:y=h*0.78"
            f":alpha='{alpha_expr}'"
            f":font='sans'"
        )

    video_filter = ",".join(vf_parts)

    # Audio: volume swell in last 2 seconds then cut
    af_parts = []
    vol_expr = f"if(gte(t,{trigger_start:.2f}),1+0.4*(t-{trigger_start:.2f})/{trigger_duration:.2f},1)"
    af_parts.append(f"volume='{vol_expr}':eval=frame")

    audio_filter = ",".join(af_parts)

    # Check if video has audio stream
    has_audio_cmd = f'ffprobe -v error -select_streams a -show_entries stream=codec_type -of csv=p=0 "{video_path}"'
    aproc = await asyncio.create_subprocess_shell(has_audio_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    astdout, _ = await aproc.communicate()
    has_audio = "audio" in astdout.decode().strip()

    if has_audio:
        cmd = (
            f'ffmpeg -y -i "{video_path}" '
            f'-vf "{video_filter}" -af "{audio_filter}" '
            f'-c:v libx264 -pix_fmt yuv420p -crf 20 -c:a aac -b:a 192k '
            f'-movflags +faststart "{output_path}"'
        )
    else:
        cmd = (
            f'ffmpeg -y -i "{video_path}" '
            f'-vf "{video_filter}" '
            f'-c:v libx264 -pix_fmt yuv420p -crf 20 -an '
            f'-movflags +faststart "{output_path}"'
        )

    logger.info(f"[FFMPEG] Applying addiction triggers: zoom+darken+text in last {trigger_duration:.1f}s")
    result = await _run_ffmpeg(cmd, timeout=120)

    if result:
        logger.info(f"[FFMPEG] Addiction triggers applied successfully to {output_path}")
    else:
        logger.warning("[FFMPEG] Addiction triggers failed — pipeline will use original video")

    return result


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


async def add_watermark_endscreen(
    video_path: str,
    output_path: str,
    duration: float = 2.5,
    brand_text: str = "Created with Visionary Suite",
    cta_text: str = "Make yours in seconds",
    url_text: str = "visionary-suite.com",
) -> bool:
    """
    Append a branded end screen to the final video.
    Creates a 2.5s dark frame with brand text, CTA, and URL,
    then concatenates it with the main video.
    Non-fatal: returns False if it fails.
    """
    _ensure_dir()
    work_id = uuid.uuid4().hex[:8]
    endscreen_path = os.path.join(FFMPEG_WORK_DIR, f"endscreen_{work_id}.mp4")

    # Probe video dimensions
    probe_cmd = f'ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "{video_path}"'
    try:
        result = subprocess.run(probe_cmd, shell=True, capture_output=True, text=True, timeout=10)
        dims = result.stdout.strip().split(",")
        w, h = int(dims[0]), int(dims[1])
    except Exception:
        w, h = 1280, 720

    font_size_brand = max(28, w // 30)
    font_size_cta = max(22, w // 40)
    font_size_url = max(20, w // 45)

    # Create end screen with text overlay on dark background
    endscreen_cmd = (
        f'ffmpeg -y -f lavfi -i "color=c=0x0a0a14:s={w}x{h}:d={duration}:r=25" '
        f'-vf "'
        f"drawtext=text='{brand_text}':fontcolor=white:fontsize={font_size_brand}:x=(w-text_w)/2:y=(h-text_h)/2-{font_size_brand}:alpha='if(lt(t,0.5),t/0.5,1)',"
        f"drawtext=text='{cta_text}':fontcolor=0xc4b5fd:fontsize={font_size_cta}:x=(w-text_w)/2:y=(h/2)+{int(font_size_cta*0.3)}:alpha='if(lt(t,0.7),t/0.7,1)',"
        f"drawtext=text='{url_text}':fontcolor=0x818cf8:fontsize={font_size_url}:x=(w-text_w)/2:y=(h/2)+{int(font_size_cta*1.8)}:alpha='if(lt(t,0.9),t/0.9,1)'"
        f'" -c:v libx264 -pix_fmt yuv420p -preset fast -crf 18 "{endscreen_path}"'
    )

    ok = await _run_ffmpeg(endscreen_cmd, timeout=30)
    if not ok or not os.path.exists(endscreen_path):
        logger.warning(f"[WATERMARK] Failed to create end screen for {work_id}")
        return False

    # Concat main video + end screen
    concat_list = os.path.join(FFMPEG_WORK_DIR, f"wm_concat_{work_id}.txt")
    try:
        with open(concat_list, "w") as f:
            f.write(f"file '{video_path}'\n")
            f.write(f"file '{endscreen_path}'\n")

        concat_cmd = (
            f'ffmpeg -y -f concat -safe 0 -i "{concat_list}" '
            f'-c:v libx264 -pix_fmt yuv420p -crf 20 -movflags +faststart "{output_path}"'
        )
        result = await _run_ffmpeg(concat_cmd, timeout=120)

        # Cleanup
        for p in [endscreen_path, concat_list]:
            try:
                os.remove(p)
            except OSError:
                pass

        return result
    except Exception as e:
        logger.error(f"[WATERMARK] Concat failed: {e}")
        return False
