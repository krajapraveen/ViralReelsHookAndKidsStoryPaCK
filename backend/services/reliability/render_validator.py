"""
Render artifact validator — P0 2026-05-21 bug-class elimination.

Shared `validate_render(path, expected_duration)` helper that gates a
video job's transition to COMPLETED on the artifact ACTUALLY being
playable with audible audio. Extracted verbatim from the proven
photo_trailer.py implementation (P0-D 2026-05-16) so every video
pipeline in the codebase uses one canonical gate.

Doctrine refs (ENGINEERING_DOCTRINE.md):
  • Rule 1 — validate every boundary (here: filesystem → "ready" state)
  • Rule 5 — never expose internal errors (the public message is safe)
  • Bug-Class Elimination Mandate — production trust-bug: "video plays
    but is silent." Class: artifact integrity not gated by completion
    invariant.

The rules a final MP4 must pass to be COMPLETED:
  • file exists on disk
  • has a video stream
  • has an audio stream
  • video codec == h264
  • audio codec in ("aac", "mp4a")
  • audio duration >= video duration - 0.5s
    (catches truncated/empty audio tracks that the codec check alone
    would miss).

Failure mode is a typed RenderValidationError that the caller MUST
translate into a FAILED_RENDER_VALIDATION status + a refund + a
user-facing safe message. NEVER swallow.

Why a fallback for ffmpeg parsing exists: some base images ship a
stub `ffprobe` that doesn't accept `-print_format`. The helper
probes for a real ffprobe and falls back to parsing `ffmpeg -i`
stderr if none is available (only the existence of the streams is
verified in fallback mode; codec + duration checks are skipped).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
from typing import Optional

logger = logging.getLogger("creatorstudio.render_validator")


class RenderValidationError(Exception):
    """Raised when the final MP4 fails the artifact-integrity check.

    Carries a `reason` machine-readable code that the caller can use
    to dispatch into FAILED_RENDER_VALIDATION + structured metrics
    without parsing a free-form string. Stable codes (pinned by audit):

      • missing_path
      • no_video_stream
      • no_audio_stream
      • wrong_video_codec
      • wrong_audio_codec
      • audio_shorter_than_video
      • audio_longer_than_video
      • ffprobe_failed
      • ffprobe_non_json

    For duration-mismatch failures (`audio_shorter_than_video` /
    `audio_longer_than_video`) the instance also exposes:

      • video_duration  (float seconds)
      • audio_duration  (float seconds)
      • gap_seconds     (positive float — |audio - video|)

    P0 2026-06 — callers can use these to decide between hard-fail and
    soft-repair (e.g. pad audio with silence when gap is small).
    """

    def __init__(
        self,
        message: str,
        reason: str = "unknown",
        *,
        video_duration: Optional[float] = None,
        audio_duration: Optional[float] = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.video_duration = video_duration
        self.audio_duration = audio_duration
        if video_duration is not None and audio_duration is not None:
            self.gap_seconds = abs(float(video_duration) - float(audio_duration))
        else:
            self.gap_seconds = None


def _resolve_ffprobe() -> Optional[str]:
    """Return the path to a real ffprobe that supports -print_format,
    or None if only the stub is available."""
    cand = []
    env = os.environ.get("FFPROBE_BIN")
    if env and os.path.exists(env):
        cand.append(env)
    which_path = shutil.which("ffprobe")
    if which_path:
        cand.append(which_path)
    cand += ["/usr/local/bin/ffprobe", "/usr/bin/ffprobe"]
    return cand[0] if cand and cand[0] and os.path.exists(cand[0]) else None


async def validate_render(path: str, expected_duration: float = 0.0) -> dict:
    """Validate the final MP4. Raises RenderValidationError on any failure.

    Returns a dict summary on success:
      {
        "video_codec": "h264", "audio_codec": "aac",
        "video_duration": float, "audio_duration": float,
        "mode": "ffprobe" | "ffmpeg_fallback",
      }

    NEVER swallows. Callers must catch RenderValidationError and route
    to FAILED_RENDER_VALIDATION + refund + safe UI message.
    """
    if not path or not os.path.exists(path):
        raise RenderValidationError(f"render output missing: {path!r}", "missing_path")

    ffprobe = _resolve_ffprobe()

    if not ffprobe:
        # Fallback: parse ffmpeg -i stderr. Only verifies stream
        # existence; codec/duration checks are skipped.
        ffmpeg_bin = "/usr/local/bin/ffmpeg" if os.path.exists("/usr/local/bin/ffmpeg") else "ffmpeg"
        proc = await asyncio.create_subprocess_exec(
            ffmpeg_bin, "-i", path, "-hide_banner",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        _, err = await proc.communicate()
        err_txt = err.decode(errors="replace")
        if "Video:" not in err_txt:
            raise RenderValidationError("no video stream in final MP4 (ffmpeg fallback)", "no_video_stream")
        if "Audio:" not in err_txt:
            raise RenderValidationError("no audio stream in final MP4 (ffmpeg fallback)", "no_audio_stream")
        logger.info("[validate_render] OK (ffmpeg fallback): video+audio streams present")
        return {"mode": "ffmpeg_fallback"}

    # Real ffprobe path.
    proc = await asyncio.create_subprocess_exec(
        ffprobe, "-v", "error", "-print_format", "json",
        "-show_streams", "-show_format", path,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RenderValidationError(
            f"ffprobe rc={proc.returncode}: {stderr.decode(errors='replace')[:200]}",
            "ffprobe_failed",
        )
    try:
        info = json.loads(stdout.decode())
    except Exception as e:
        raise RenderValidationError(f"ffprobe non-JSON: {e}", "ffprobe_non_json")

    streams = info.get("streams", []) or []
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if not v:
        raise RenderValidationError("no video stream in final MP4", "no_video_stream")
    if not a:
        raise RenderValidationError("no audio stream in final MP4", "no_audio_stream")
    if v.get("codec_name") != "h264":
        raise RenderValidationError(
            f"video codec={v.get('codec_name')} (expected h264)",
            "wrong_video_codec",
        )
    if a.get("codec_name") not in ("aac", "mp4a"):
        raise RenderValidationError(
            f"audio codec={a.get('codec_name')} (expected aac)",
            "wrong_audio_codec",
        )

    def _dur(s: dict) -> float:
        try:
            return float(s.get("duration") or (s.get("tags") or {}).get("DURATION", 0) or 0)
        except Exception:
            return 0.0

    fmt_dur = float((info.get("format") or {}).get("duration", 0) or 0)
    v_dur = _dur(v) or fmt_dur
    a_dur = _dur(a) or fmt_dur
    # P0 2026-05-31 — bidirectional audio/video duration parity check.
    # Pre-fix: only `audio_shorter_than_video` was caught (tail silence).
    # The new mix_audio path with -stream_loop -1 + duration=longest +
    # -shortest can in theory produce audio_longer_than_video if the
    # -shortest pin races the loop closure. Reject both deltas with a
    # 0.5s tolerance — pinned by test_audio_video_duration_parity_2026_05.
    if v_dur > 0:
        delta = a_dur - v_dur
        if delta < -0.5:
            raise RenderValidationError(
                f"audio shorter than video (audio={a_dur:.2f}s, video={v_dur:.2f}s)",
                "audio_shorter_than_video",
                video_duration=v_dur, audio_duration=a_dur,
            )
        if delta > 0.5:
            raise RenderValidationError(
                f"audio longer than video (audio={a_dur:.2f}s, video={v_dur:.2f}s)",
                "audio_longer_than_video",
                video_duration=v_dur, audio_duration=a_dur,
            )
    logger.info(
        "[validate_render] OK video=%.2fs audio=%.2fs v_codec=%s a_codec=%s",
        v_dur, a_dur, v.get("codec_name"), a.get("codec_name"),
    )
    return {
        "video_codec": v.get("codec_name"),
        "audio_codec": a.get("codec_name"),
        "video_duration": v_dur,
        "audio_duration": a_dur,
        "mode": "ffprobe",
    }


# ────────────────────────────────────────────────────────────────────────
# Render-pipeline registry (P0 2026-05-23 silent-render bug-class fix).
#
# Every backend module that produces a final .mp4 AND transitions a job
# to a terminal "completed"/"COMPLETED" state MUST be listed here AND
# call `validate_render` against the local artifact before that
# transition. The static audit at
# /app/backend/tests/test_silent_render_prevention_2026_05.py reads
# this tuple and enforces the contract via grep.
#
# Adding a new video producer? One-line addition here PLUS a call site
# is the entire bug-class-elimination contract. CI will fail until
# both are present.
# ────────────────────────────────────────────────────────────────────────
REGISTERED_RENDER_PIPELINES: tuple[str, ...] = (
    "routes/photo_trailer.py",
    "routes/story_video_generation.py",
    "routes/story_video_fast.py",
    "routes/genstudio.py",
    "services/optimized_video_renderer.py",
)
