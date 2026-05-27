import asyncio
import shutil
import subprocess
from pathlib import Path

import pytest

from services.story_engine.adapters import ffmpeg_assembly
from services.story_engine.continuity import validate_pipeline_outputs, should_mark_ready


def _ffmpeg_available() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg/ffprobe required")
@pytest.mark.parametrize("target_seconds", [30, 45, 60])
def test_conform_duration_outputs_exact_h264_aac_contract(tmp_path: Path, target_seconds: int):
    source = tmp_path / "source.mp4"
    output = tmp_path / f"output_{target_seconds}.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=160x90:d=2:r=15",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(source),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    result = asyncio.run(ffmpeg_assembly.conform_duration(str(source), str(output), target_seconds, tolerance=0.5))

    assert result["ok"] is True
    assert target_seconds - 0.5 <= result["actual_duration_seconds"] <= target_seconds + 0.5
    assert result["actual_audio_duration_seconds"] >= target_seconds - 0.5
    assert result["has_aac_audio"] is True


def test_ready_requires_duration_and_audio_contract():
    validation = validate_pipeline_outputs({
        "output_url": "https://cdn.example/video.mp4",
        "thumbnail_url": "https://cdn.example/poster.jpg",
        "episode_plan": {"title": "Contract"},
        "duration_seconds": 30,
        "actual_duration_seconds": 28.9,
        "duration_validation": {"actual_audio_duration_seconds": 30.0},
    })

    assert validation.passed is False
    assert should_mark_ready(validation) == "FAILED"


def test_ready_accepts_exact_duration_audio_contract():
    validation = validate_pipeline_outputs({
        "output_url": "https://cdn.example/video.mp4",
        "thumbnail_url": "https://cdn.example/poster.jpg",
        "episode_plan": {"title": "Contract"},
        "duration_seconds": 45,
        "actual_duration_seconds": 45.2,
        "duration_validation": {"actual_audio_duration_seconds": 45.1},
    })

    assert validation.passed is True
    assert should_mark_ready(validation) == "READY"
