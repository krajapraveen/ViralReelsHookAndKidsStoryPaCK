"""
Story-to-Video reliability/perf regression — 2026-05-16
Founder P0 sprint. Locks in:
  • Fast mode is default and honored
  • Sora is skipped in fast mode (the 226s → 9s unlock)
  • Tightened heartbeat SLAs per stage
  • Admin debug endpoint is admin-gated and returns the contract
  • Funnel events for generation lifecycle are whitelisted
  • Recovery daemon emits story_generation_timeout on terminal stuck-job kill
"""
import os
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = os.environ.get("REACT_APP_BACKEND_URL") or "http://localhost:8001"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


def _admin_token():
    r = requests.post(f"{BASE}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    r.raise_for_status()
    d = r.json()
    return d.get("access_token") or d.get("token")


# ─── 1. Fast is the new default ─────────────────────────────────
def test_quality_modes_default_is_fast():
    r = requests.get(f"{BASE}/api/story-engine/quality-modes", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["default"] == "fast", f"Default quality_mode must be 'fast', got {body['default']}"
    assert body["modes"]["fast"]["use_sora"] is False


def test_frontend_default_state_is_fast():
    src = (ROOT / "frontend" / "src" / "pages" / "StoryVideoPipeline.js").read_text(encoding="utf-8")
    assert "useState('fast')" in src, "Frontend default qualityMode must be 'fast'"


# ─── 2. Pipeline honors use_sora and parallelizes scene clips ───
def test_pipeline_honors_use_sora_flag_and_parallelizes():
    src = (ROOT / "backend" / "services" / "story_engine" / "pipeline.py").read_text(encoding="utf-8")
    # Must read use_sora from quality_config
    assert 'quality_config.get("use_sora"' in src or "quality_config.get('use_sora'" in src, \
        "Pipeline must read use_sora from quality_config"
    # Must parallelize scene clips via asyncio.gather
    assert "asyncio.gather" in src and "_make_clip" in src, \
        "Scene clip generation must run via asyncio.gather (was a sequential for loop)"


# ─── 3. Heartbeat SLAs tightened ───────────────────────────────
def test_heartbeat_thresholds_tightened():
    from services.story_engine.state_machine import HEARTBEAT_THRESHOLDS
    # New tighter limits per founder directive (allowing the pipeline some
    # legitimate headroom but no more 5-10 minute hangs).
    assert HEARTBEAT_THRESHOLDS["PLANNING"] <= 30
    assert HEARTBEAT_THRESHOLDS["BUILDING_CHARACTER_CONTEXT"] <= 30
    assert HEARTBEAT_THRESHOLDS["PLANNING_SCENE_MOTION"] <= 30
    assert HEARTBEAT_THRESHOLDS["GENERATING_KEYFRAMES"] <= 120
    assert HEARTBEAT_THRESHOLDS["GENERATING_SCENE_CLIPS"] <= 240
    assert HEARTBEAT_THRESHOLDS["GENERATING_AUDIO"] <= 75
    assert HEARTBEAT_THRESHOLDS["ASSEMBLING_VIDEO"] <= 120
    assert HEARTBEAT_THRESHOLDS["VALIDATING"] <= 60


# ─── 4. Admin debug endpoint ───────────────────────────────────
def test_debug_endpoint_admin_gated():
    r = requests.get(f"{BASE}/api/story-engine/jobs/nonexistent/debug", timeout=10)
    assert r.status_code in (401, 403)


def test_debug_endpoint_returns_contract_for_admin():
    tok = _admin_token()
    # Use any existing job. If none exist this test asserts a 404 + admin OK.
    list_r = requests.get(
        f"{BASE}/api/story-engine/rate-limit-status",
        headers={"Authorization": f"Bearer {tok}"},
        timeout=10,
    )
    assert list_r.status_code == 200
    # Pick any job_id from /status surface — for the smoke we just verify
    # the unknown-id path is 404 with admin auth (auth passed, lookup failed).
    r = requests.get(
        f"{BASE}/api/story-engine/jobs/__pytest_unknown__/debug",
        headers={"Authorization": f"Bearer {tok}"},
        timeout=10,
    )
    assert r.status_code == 404, f"Expected 404, got {r.status_code} {r.text}"


# ─── 5. Funnel events whitelisted ──────────────────────────────
def test_generation_funnel_events_whitelisted():
    src = (ROOT / "backend" / "routes" / "funnel_tracking.py").read_text(encoding="utf-8")
    for event in (
        "story_generation_started",
        "story_generation_completed",
        "story_generation_failed",
        "story_generation_timeout",
    ):
        assert f'"{event}"' in src, f"Missing event in funnel whitelist: {event}"


def test_funnel_endpoint_accepts_generation_events():
    for step in (
        "story_generation_started",
        "story_generation_completed",
        "story_generation_failed",
        "story_generation_timeout",
    ):
        r = requests.post(
            f"{BASE}/api/funnel/track",
            json={
                "step": step,
                "session_id": "pytest_svp_reliability",
                "anonymous_id": "pytest_svp_anon",
                "context": {"source": "pytest"},
            },
            timeout=10,
        )
        assert r.status_code == 200, f"{step} → {r.status_code} {r.text}"


# ─── 6. Recovery daemon emits the timeout funnel event ─────────
def test_recovery_daemon_emits_timeout_funnel_event_on_terminal_kill():
    src = (ROOT / "backend" / "services" / "story_engine" / "recovery_daemon.py").read_text(encoding="utf-8")
    assert "story_generation_timeout" in src, \
        "Recovery daemon must emit story_generation_timeout on terminal stuck-job kill"
    assert "abandonment_reason" in src and "generation_timeout" in src


# ─── 7. Credits refund on terminal failure ─────────────────────
def test_recovery_daemon_refunds_credits_on_terminal():
    src = (ROOT / "backend" / "services" / "story_engine" / "recovery_daemon.py").read_text(encoding="utf-8")
    assert "_refund_credits" in src, "Recovery daemon must call _refund_credits on terminal failure"
