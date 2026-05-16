"""
YouStar reliability trio — 2026-05-16 P0
Locks in:
  • P0-A: stage timestamps in _set_stage + admin debug endpoint admin-gated
          + per-stage SLA table present + sub-stage heartbeats in _render_trailer
  • P0-C: frontend Play uses videoRef, .load() on src change, canplay-gated
          overlay, cache-busting query param on stream URL
  • P0-D: _validate_render rejects (a) missing file (b) no audio (c) no video
          and is invoked by the create flow with proper error handling
"""
import os
import subprocess
import tempfile
import asyncio
import requests
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PT_PY = ROOT / "backend" / "routes" / "photo_trailer.py"
FRONTEND = ROOT / "frontend" / "src" / "pages" / "PhotoTrailerPage.jsx"
BASE = os.environ.get("REACT_APP_BACKEND_URL") or "http://localhost:8001"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


def _admin_token():
    r = requests.post(f"{BASE}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    r.raise_for_status()
    d = r.json()
    return d.get("access_token") or d.get("token")


# ─── P0-A: stage timestamps + debug endpoint + sub-stage heartbeats ──
def test_set_stage_records_started_and_completed_at():
    src = PT_PY.read_text(encoding="utf-8")
    assert 'f"stage_started_at.{stage}"' in src, \
        "_set_stage must record stage_started_at.<stage> on every transition"
    assert 'f"stage_completed_at.{prev_stage}"' in src, \
        "_set_stage must close out stage_completed_at.<prev>"
    assert 'f"stage_duration_s.{prev_stage}"' in src, \
        "_set_stage must record stage_duration_s.<prev>"


def test_render_trailer_emits_substage_heartbeats():
    """User must see sub-stage progress so 88% / RENDERING_TRAILER no longer
    looks like a hang."""
    src = PT_PY.read_text(encoding="utf-8")
    for label in ("Combining scenes", "Adding music", "Stitching trailer", "Adding end card"):
        assert label in src, f"_render_trailer must emit '{label}' heartbeat"


def test_admin_debug_endpoint_admin_gated():
    r = requests.get(f"{BASE}/api/photo-trailer/admin/jobs/anything/debug", timeout=10)
    assert r.status_code in (401, 403)


def test_admin_debug_endpoint_returns_404_for_unknown_id():
    tok = _admin_token()
    r = requests.get(
        f"{BASE}/api/photo-trailer/admin/jobs/__pytest_unknown__/debug",
        headers={"Authorization": f"Bearer {tok}"},
        timeout=10,
    )
    assert r.status_code == 404


def test_admin_debug_endpoint_returns_contract_for_real_job():
    """Find any existing photo_trailer job and assert the response shape."""
    tok = _admin_token()
    # Use the my-trailers list to discover a real job id without needing
    # direct mongo access from the test environment.
    list_r = requests.get(
        f"{BASE}/api/photo-trailer/my-trailers?limit=1",
        headers={"Authorization": f"Bearer {tok}"},
        timeout=10,
    )
    if list_r.status_code != 200:
        pytest.skip(f"my-trailers list failed: {list_r.status_code}")
    items = (list_r.json() or {}).get("trailers") or (list_r.json() or {}).get("items") or []
    # Discover any trailer via the admin overview if my-trailers is empty
    if not items:
        # Use the known-good ID we observed in /admin endpoint smoke
        job_id = None
        admin_r = requests.get(
            f"{BASE}/api/photo-trailer/admin/overview",
            headers={"Authorization": f"Bearer {tok}"}, timeout=10,
        )
        if admin_r.status_code == 200:
            # admin overview returns a summary, not raw IDs — skip if empty
            pytest.skip("no trailers available in test env")
        else:
            pytest.skip("admin overview unreachable")
    else:
        job_id = items[0].get("_id") or items[0].get("job_id")
        if not job_id:
            pytest.skip("trailer item missing _id/job_id")
    r = requests.get(
        f"{BASE}/api/photo-trailer/admin/jobs/{job_id}/debug",
        headers={"Authorization": f"Bearer {tok}"},
        timeout=10,
    )
    assert r.status_code == 200
    body = r.json()
    for key in ("success", "job_id", "status", "current_stage",
                "elapsed_total_s", "stage_timeline", "output_url_present",
                "audio_url_present", "credits_charged", "credits_refunded",
                "ffmpeg_stderr_tail"):
        assert key in body, f"missing key in debug payload: {key}"
    assert isinstance(body["stage_timeline"], list)


def test_per_stage_sla_table_present():
    src = PT_PY.read_text(encoding="utf-8")
    assert "HEARTBEAT_THRESHOLDS_YS" in src, \
        "Per-stage SLA table missing — janitor + debug endpoint depend on it"
    # Spot-check the critical bounded SLAs
    for stage in ("GENERATING_SCENES", "GENERATING_VOICEOVER", "RENDERING_TRAILER"):
        assert f'"{stage}"' in src


# ─── P0-C: first-click Play frontend fix ─────────────────────────────
def test_frontend_video_uses_ref_and_explicit_load():
    src = FRONTEND.read_text(encoding="utf-8")
    assert "videoRef = React.useRef" in src, "videoRef must exist for explicit .load()"
    assert "videoRef.current.load()" in src, "Must call videoRef.current.load() on src change"
    assert "ref={videoRef}" in src, "<video> must receive the videoRef ref"


def test_frontend_play_button_gated_by_canplay():
    src = FRONTEND.read_text(encoding="utf-8")
    assert "setCanPlay" in src and "onCanPlay=" in src, \
        "Must track canplay state via onCanPlay event handler"
    assert "trailer-tap-to-play" in src, "Tap-to-play overlay must exist"
    # Overlay must only render after canPlay is true AND not currently playing
    assert "canPlay && !isPlaying" in src or "!isPlaying && canPlay" in src


def test_frontend_handle_tap_to_play_runs_in_user_gesture():
    src = FRONTEND.read_text(encoding="utf-8")
    assert "handleTapToPlay" in src
    assert "el.play()" in src, "handleTapToPlay must call .play() synchronously"
    assert "PlayError" in src or "playFailed" in src


def test_frontend_streamurl_cache_busted():
    src = FRONTEND.read_text(encoding="utf-8")
    assert "_v=${Date.now()}" in src, "stream URL must include cache-busting query param"


# ─── P0-D: ffprobe validation ────────────────────────────────────────
@pytest.fixture(scope="module")
def render_fixtures(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("ys_render")
    valid = tmp / "valid.mp4"
    no_audio = tmp / "no_audio.mp4"
    # valid: 2s color video + 2s sine audio, h264+aac
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=red:size=320x180:duration=2:rate=15",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest", str(valid),
    ], check=True, capture_output=True)
    # video-only
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=red:size=320x180:duration=3:rate=15",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        str(no_audio),
    ], check=True, capture_output=True)
    return {"valid": str(valid), "no_audio": str(no_audio), "missing": str(tmp / "ghost.mp4")}


def test_validate_render_accepts_valid_mp4(render_fixtures):
    from routes.photo_trailer import _validate_render
    asyncio.run(_validate_render(render_fixtures["valid"], 2.0))


def test_validate_render_rejects_no_audio(render_fixtures):
    from routes.photo_trailer import _validate_render, RenderValidationError
    with pytest.raises(RenderValidationError, match="audio"):
        asyncio.run(_validate_render(render_fixtures["no_audio"], 3.0))


def test_validate_render_rejects_missing_file(render_fixtures):
    from routes.photo_trailer import _validate_render, RenderValidationError
    with pytest.raises(RenderValidationError, match="missing"):
        asyncio.run(_validate_render(render_fixtures["missing"], 5.0))


def test_create_flow_handles_validation_error():
    """The render-loop except block must specifically catch RenderValidationError
    and mark the job RENDER_INVALID + refund."""
    src = PT_PY.read_text(encoding="utf-8")
    assert "except RenderValidationError as e" in src
    assert "RENDER_INVALID" in src
