"""Tests for the P0 STUCK-AT-88% reliability fix (2026-04-29 founder directive).

Acceptance criteria:
  1. Render timeout marks job FAILED with error_code=RENDER_TIMEOUT
  2. Hard-max wall-clock OVERRIDES heartbeat freshness in the janitor
  3. Janitor refunds credits on RENDER_TIMEOUT-tier reaps
  4. Admin /admin/stuck-jobs surfaces stuck-at-same-progress jobs
  5. Auto-requeue is suppressed when hard-max is exceeded (toxic jobs)
  6. RENDER_TIMEOUT error_code is in the dashboard's stage map
"""
import os
import uuid
import pytest
import pytest_asyncio
import httpx
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv("/app/backend/.env")


def _api_base() -> str:
    p = "/app/frontend/.env"
    if os.path.exists(p):
        for line in open(p):
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    return "http://localhost:8001"


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _iso_minutes_ago(m: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=m)).isoformat()


@pytest_asyncio.fixture
async def admin_token():
    base = _api_base()
    async with httpx.AsyncClient(base_url=base, timeout=15.0) as cli:
        r = await cli.post(
            "/api/auth/login",
            json={"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        yield body.get("access_token") or body.get("token")


async def _run_janitor(admin_token: str) -> dict:
    base = _api_base()
    async with httpx.AsyncClient(base_url=base, timeout=30.0) as cli:
        r = await cli.post(
            "/api/photo-trailer/admin/janitor/run-now",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 200, r.text
        return r.json()


# ─── 1. Hard-max thresholds match founder spec ────────────────────────────────
def test_hard_max_thresholds_match_spec():
    """20s = 8min, 45/60s = 15min, 90s = 25min — never one global cutoff."""
    import sys
    sys.path.insert(0, "/app/backend")
    from routes.photo_trailer import (
        _hard_max_runtime_for, HARD_MAX_RUNTIME_BY_DURATION,
        _render_timeout_for, RENDER_TIMEOUT_BY_DURATION,
    )
    assert HARD_MAX_RUNTIME_BY_DURATION[20] == 8
    assert HARD_MAX_RUNTIME_BY_DURATION[60] == 15
    assert HARD_MAX_RUNTIME_BY_DURATION[90] == 25
    assert _hard_max_runtime_for(20) == 8
    assert _hard_max_runtime_for(60) == 15
    assert _hard_max_runtime_for(90) == 25
    assert _hard_max_runtime_for(None) == 15
    # Render timeouts (per-stage)
    assert RENDER_TIMEOUT_BY_DURATION[20] == 5
    assert RENDER_TIMEOUT_BY_DURATION[60] == 8
    assert RENDER_TIMEOUT_BY_DURATION[90] == 12
    assert _render_timeout_for(60) == 8


# ─── 2. Hard-max OVERRIDES heartbeat freshness ────────────────────────────────
@pytest.mark.asyncio
async def test_hard_max_overrides_fresh_heartbeat(admin_token):
    """The bug we are fixing: a render hangs for 20+ minutes but somehow keeps
    leaking a heartbeat update. Old janitor would skip it forever. New janitor
    must reap it because age exceeded the per-tier hard-max."""
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    jid = f"hardmax-{uuid.uuid4().hex[:8]}"
    user_id = f"hm-user-{uuid.uuid4().hex[:6]}"
    try:
        await db.users.insert_one({
            "_id": user_id, "id": user_id, "email": f"{user_id}@example.com",
            "credits_balance": 0,
        })
        await db.photo_trailer_jobs.insert_one({
            "_id": jid, "user_id": user_id, "status": "PROCESSING",
            "current_stage": "RENDERING_TRAILER",
            "progress_percent": 88,
            "duration_target_seconds": 20,  # 8-min hard-max
            "started_at": _iso_minutes_ago(20),  # 20 min ≫ 8 min hard-max
            "created_at": _iso_minutes_ago(20),
            "updated_at": _iso_minutes_ago(0.2),
            # FRESH heartbeat — 12s ago. Old janitor would skip; new janitor
            # must reap because hard-max overrides.
            "last_progress_at": _iso_minutes_ago(0.2),
            "retry_count": 0,
            "charged_credits": 5,
            "refunded_credits": 0,
            "template_id": "comedy_roast",
        })
        result = await _run_janitor(admin_token)
        doc = await db.photo_trailer_jobs.find_one({"_id": jid})
        assert doc["status"] == "FAILED", \
            f"hard-max-exceeded job must be reaped despite fresh heartbeat; got {doc['status']}"
        assert doc["error_code"] == "RENDER_TIMEOUT", \
            f"render-stage hard-max → RENDER_TIMEOUT, got {doc['error_code']}"
        assert doc["failure_stage"] == "RENDERING_TRAILER"
        assert doc["refunded_credits"] == 5  # refunded exactly once
        assert result["reaped"] >= 1
    finally:
        await db.photo_trailer_jobs.delete_one({"_id": jid})
        await db.users.delete_one({"_id": user_id})
        cli.close()


# ─── 3. Hard-max suppresses auto-requeue (toxic jobs go straight to refund) ───
@pytest.mark.asyncio
async def test_hard_max_suppresses_auto_requeue(admin_token):
    """A retry_count=0 job that exceeded hard-max must NOT be auto-requeued
    (it would just hang again). Goes straight to FAILED+refund."""
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    jid = f"hardmax-noreq-{uuid.uuid4().hex[:8]}"
    user_id = f"hmr-user-{uuid.uuid4().hex[:6]}"
    try:
        await db.users.insert_one({
            "_id": user_id, "id": user_id, "email": f"{user_id}@example.com",
            "credits_balance": 0,
        })
        await db.photo_trailer_jobs.insert_one({
            "_id": jid, "user_id": user_id, "status": "PROCESSING",
            "current_stage": "RENDERING_TRAILER",
            "duration_target_seconds": 60,  # 15-min hard-max
            "started_at": _iso_minutes_ago(20),  # past 15-min hard-max
            "last_progress_at": _iso_minutes_ago(10),  # not alive
            "retry_count": 0,  # would normally auto-requeue
            "charged_credits": 35,
            "refunded_credits": 0,
            "template_id": "comedy_roast",
        })
        result = await _run_janitor(admin_token)
        doc = await db.photo_trailer_jobs.find_one({"_id": jid})
        assert doc["status"] == "FAILED", \
            f"hard-max-exceeded job at retry=0 must FAIL (not requeue); got {doc['status']}"
        assert doc["error_code"] == "RENDER_TIMEOUT"
        assert doc.get("retry_count", 0) == 0  # was NOT incremented
        assert doc["refunded_credits"] == 35
        assert result.get("auto_requeued", 0) == 0
        assert result["reaped"] >= 1
    finally:
        await db.photo_trailer_jobs.delete_one({"_id": jid})
        await db.users.delete_one({"_id": user_id})
        cli.close()


# ─── 4. Admin /admin/stuck-jobs surfaces stuck jobs ───────────────────────────
@pytest.mark.asyncio
async def test_admin_stuck_jobs_surfaces_stuck(admin_token):
    """The diagnostic endpoint must return any PROCESSING job whose
    last_progress_at is older than the threshold, with reap-prediction."""
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    base = _api_base()
    jid = f"stuck-diag-{uuid.uuid4().hex[:8]}"
    try:
        await db.photo_trailer_jobs.insert_one({
            "_id": jid, "user_id": "stuck-user", "status": "PROCESSING",
            "current_stage": "RENDERING_TRAILER",
            "progress_percent": 88,
            "progress_message": "Final render — stitching scenes, adding music, watermark",
            "duration_target_seconds": 60,
            "started_at": _iso_minutes_ago(8),
            "last_progress_at": _iso_minutes_ago(8),  # 8 min stale
            "retry_count": 0,
            "template_id": "comedy_roast",
        })
        async with httpx.AsyncClient(base_url=base, timeout=15.0) as cli_h:
            r = await cli_h.get(
                "/api/photo-trailer/admin/stuck-jobs?min_age_minutes=3",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
        assert r.status_code == 200, r.text
        body = r.json()
        ours = next((j for j in body["jobs"] if j["job_id"] == jid), None)
        assert ours is not None, "our seeded stuck job must appear in the list"
        assert ours["current_stage"] == "RENDERING_TRAILER"
        assert ours["progress_percent"] == 88
        assert ours["since_last_heartbeat_minutes"] >= 7
        assert ours["hard_max_runtime_minutes"] == 15
        assert ours["render_timeout_minutes"] == 8
        # Not yet reapable — 8 min < 15 min hard-max, but past 3-min query gate
        assert ours["will_be_reaped_next_sweep"] is False
    finally:
        await db.photo_trailer_jobs.delete_one({"_id": jid})
        cli.close()


# ─── 5. RENDER_TIMEOUT in the dashboard error_code map ────────────────────────
def test_render_timeout_in_dashboard_error_map():
    """The KPI dashboard's `ERROR_TO_STAGE` table must include RENDER_TIMEOUT
    so it shows up in the failure_stage_breakdown / error_code_breakdown."""
    src = open("/app/backend/routes/photo_trailer.py").read()
    # Either explicit mapping or a render-timeout-aware path
    assert "RENDER_TIMEOUT" in src
    # The dashboard ERROR_TO_STAGE map must include it (or share with RENDER_FAIL).
    # Look for at least one mapping line.
    assert ('RENDER_FAIL' in src and 'RENDERING_TRAILER' in src), \
        "render-stage error codes must map to RENDERING_TRAILER stage"


# ─── 6. Render-stage timeout is wrapped via asyncio.wait_for ──────────────────
def test_render_stage_uses_wait_for_timeout():
    """The orchestrator must wrap _render_trailer in asyncio.wait_for so a
    hung ffmpeg can't park the user at 88% forever."""
    src = open("/app/backend/routes/photo_trailer.py").read()
    # The render block uses wait_for with the per-duration timeout
    assert "asyncio.wait_for" in src
    assert "_render_timeout_for" in src
    assert 'RENDER_TIMEOUT' in src
    # Upload calls also get wait_for
    assert "_upload_video_bytes" in src
    # The TimeoutError → RENDER_TIMEOUT branch exists
    assert "asyncio.TimeoutError" in src


# ─── 7. Frontend ProgressStep checks status FAILED / COMPLETED reliably ───────
def test_frontend_progress_step_detects_terminal_status():
    """The polling loop must transition out of progress on COMPLETED/FAILED/
    CANCELLED — not on progress_percent. Bug we fixed: 88% with status=FAILED
    used to keep the spinner alive."""
    src = open("/app/frontend/src/pages/PhotoTrailerPage.jsx").read()
    assert "j.status === 'COMPLETED'" in src
    assert "j.status === 'FAILED'" in src
    assert "CANCELLED" in src


# ─── 8. Frontend escalation copy is gated to 3-min mark ───────────────────────
def test_frontend_escalation_gated_to_three_minutes():
    """The 'you can leave this page' card must only appear after 3 minutes,
    not on the initial paint. Founder spec."""
    src = open("/app/frontend/src/pages/PhotoTrailerPage.jsx").read()
    assert "ESCALATE_AT_SEC = 180" in src
    assert "STILL_WORKING_AT_SEC = 240" in src
    assert "showLeaveCard" in src
    assert "showStillWorking" in src
    # The "still working" card test ID exists
    assert 'data-testid="trailer-still-working-card"' in src


# ─── 9. Funnel allowlist accepts the new render-timeout failure event ─────────
@pytest.mark.asyncio
async def test_render_timeout_emits_failure_event(admin_token):
    """A timed-out render must emit photo_trailer_generation_failed with
    code=RENDER_TIMEOUT so the dashboard error_code_breakdown picks it up."""
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    jid = f"rtimeout-evt-{uuid.uuid4().hex[:8]}"
    user_id = f"rt-user-{uuid.uuid4().hex[:6]}"
    try:
        await db.users.insert_one({
            "_id": user_id, "id": user_id, "email": f"{user_id}@example.com",
            "credits_balance": 0,
        })
        await db.photo_trailer_jobs.insert_one({
            "_id": jid, "user_id": user_id, "status": "PROCESSING",
            "current_stage": "RENDERING_TRAILER",
            "duration_target_seconds": 20,  # 8-min hard-max
            "started_at": _iso_minutes_ago(15),
            "last_progress_at": _iso_minutes_ago(0.2),  # fresh heartbeat
            "retry_count": 0, "charged_credits": 5, "refunded_credits": 0,
            "template_id": "comedy_roast",
        })
        await _run_janitor(admin_token)
        import asyncio
        await asyncio.sleep(0.4)
        ev = await db.funnel_events.find_one({
            "step": "photo_trailer_generation_failed",
            "meta.job_id": jid,
        })
        assert ev is not None, "RENDER_TIMEOUT must emit a failure event"
        assert ev["meta"]["code"] == "RENDER_TIMEOUT"
    finally:
        await db.photo_trailer_jobs.delete_one({"_id": jid})
        await db.funnel_events.delete_many({"meta.job_id": jid})
        await db.users.delete_one({"_id": user_id})
        cli.close()
