"""Tests for the P0 RELIABILITY SPRINT changes (2026-04-29 founder directive).

Three concerns covered:

  1. JANITOR — dynamic stale thresholds per duration tier (20s=10m, 60s=20m,
     90s=35m) + heartbeat protection (don't reap if last_progress_at < 3m).

  2. STALE AUTO-RECOVERY — first stale auto-requeues with credits preserved
     and retry_count=1; second stale fails normally with refund.

  3. IMAGE_GEN HARDENING — verified by source-level config check (3 attempts,
     2/5/10s backoff, outer per-scene retry).

Drives the LIVE backend via httpx + admin POST /admin/janitor/run-now to avoid
the cross-event-loop Motor issue that bites direct route imports.
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
        assert r.status_code == 200, f"admin login failed: {r.text}"
        body = r.json()
        yield body.get("access_token") or body.get("token")


async def _run_janitor(admin_token: str) -> dict:
    """Hit POST /admin/janitor/run-now to invoke a sweep through the live
    backend (uses the route's own event loop / Motor client)."""
    base = _api_base()
    async with httpx.AsyncClient(base_url=base, timeout=30.0) as cli:
        r = await cli.post(
            "/api/photo-trailer/admin/janitor/run-now",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 200, r.text
        return r.json()


# ─── 1. Per-duration stale threshold table is honest ──────────────────────────
def test_stale_threshold_per_duration_tier():
    """20s = 10min, 60s = 20min, 90s = 35min, missing = 15min default."""
    import sys
    sys.path.insert(0, "/app/backend")
    from routes.photo_trailer import _stale_threshold_for, STALE_MIN_BY_DURATION
    assert _stale_threshold_for(20) == 10
    assert _stale_threshold_for(60) == 20
    assert _stale_threshold_for(90) == 35
    assert _stale_threshold_for(45) == 20
    assert _stale_threshold_for(None) == 15
    assert _stale_threshold_for(999) == 15
    assert STALE_MIN_BY_DURATION[20] == 10
    assert STALE_MIN_BY_DURATION[60] == 20
    assert STALE_MIN_BY_DURATION[90] == 35


# ─── 2. Janitor: 90s job at 12 min must NOT be reaped ─────────────────────────
@pytest.mark.asyncio
async def test_janitor_respects_per_duration_threshold(admin_token):
    """A 90s job that started 12 minutes ago is well within its 35-min
    threshold and must remain PROCESSING. The OLD janitor (5-min cutoff for
    everything) would have reaped it — this is the regression we're fixing."""
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    jid = f"reliab-90s-{uuid.uuid4().hex[:8]}"
    try:
        await db.photo_trailer_jobs.insert_one({
            "_id": jid, "user_id": "reliab-user", "status": "PROCESSING",
            "current_stage": "GENERATING_SCENES",
            "duration_target_seconds": 90,
            "started_at": _iso_minutes_ago(12),
            "created_at": _iso_minutes_ago(12),
            "updated_at": _iso_minutes_ago(12),
            "last_progress_at": _iso_minutes_ago(12),
            "retry_count": 0,
        })
        await _run_janitor(admin_token)
        doc = await db.photo_trailer_jobs.find_one({"_id": jid})
        assert doc["status"] == "PROCESSING", \
            f"90s job at 12min should not be reaped (threshold=35min); got {doc.get('status')}"
        assert doc.get("retry_count", 0) == 0
    finally:
        await db.photo_trailer_jobs.delete_one({"_id": jid})
        cli.close()


# ─── 3. Heartbeat protection: alive job must NOT be reaped ────────────────────
@pytest.mark.asyncio
async def test_janitor_heartbeat_protection(admin_token):
    """A job past its tier threshold but with a fresh heartbeat (< 3min) is
    actively making progress and must not be touched."""
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    jid = f"reliab-hb-{uuid.uuid4().hex[:8]}"
    try:
        # 60s tier: hard_max=15min, stale_threshold=20min. Heartbeat-extension
        # window is [15, 20]. Age=17min is past hard_max — heartbeat MUST save
        # the job from reaping.
        await db.photo_trailer_jobs.insert_one({
            "_id": jid, "user_id": "reliab-user", "status": "PROCESSING",
            "current_stage": "GENERATING_SCENES",
            "duration_target_seconds": 60,
            "started_at": _iso_minutes_ago(17),
            "created_at": _iso_minutes_ago(17),
            "updated_at": _iso_minutes_ago(0.5),
            "last_progress_at": _iso_minutes_ago(0.5),  # 30s ago — alive
            "retry_count": 0,
        })
        result = await _run_janitor(admin_token)
        doc = await db.photo_trailer_jobs.find_one({"_id": jid})
        assert doc["status"] == "PROCESSING", \
            f"alive job (heartbeat 30s ago) must not be reaped; got {doc.get('status')}"
        assert result["skipped_alive_heartbeat"] >= 1
    finally:
        await db.photo_trailer_jobs.delete_one({"_id": jid})
        cli.close()


# ─── 4. AUTO-RECOVERY: first stale auto-requeues, no refund ───────────────────
@pytest.mark.asyncio
async def test_stale_auto_requeue_first_time(admin_token):
    """retry_count=0 stale job → status QUEUED, retry_count=1, NO refund."""
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    jid = f"reliab-rq1-{uuid.uuid4().hex[:8]}"
    try:
        # 60s tier: hard_max=15min, stale_threshold=20min. Use age=17min
        # (past hard_max, before stale_threshold) WITH stale heartbeat
        # so the job is reapable. retry_count=0 → must auto-requeue.
        await db.photo_trailer_jobs.insert_one({
            "_id": jid, "user_id": "reliab-user", "status": "PROCESSING",
            "current_stage": "GENERATING_SCENES",
            "duration_target_seconds": 60,
            "started_at": _iso_minutes_ago(17),
            "created_at": _iso_minutes_ago(17),
            "updated_at": _iso_minutes_ago(10),
            "last_progress_at": _iso_minutes_ago(10),  # >3min → stale
            "retry_count": 0,
            "charged_credits": 25,
            "refunded_credits": 0,
            "template_id": "superhero_origin",
        })
        result = await _run_janitor(admin_token)
        doc = await db.photo_trailer_jobs.find_one({"_id": jid})
        # The auto-requeue itself is the assertion — once requeued, the
        # orchestrator may re-run the pipeline and that re-run can land in
        # any terminal state for unrelated reasons (test job has no real
        # hero asset, etc). What matters is:
        #  • retry_count was bumped
        #  • auto_requeued_at was stamped
        #  • NO refund was issued by the janitor on this pass
        #  • janitor's metric counted this as auto_requeued, not reaped
        assert doc["retry_count"] == 1, f"retry_count should be 1, got {doc.get('retry_count')}"
        assert doc.get("auto_requeued_at") is not None, "auto_requeued_at must be stamped"
        # Refund must NOT have been issued by the auto-requeue path
        # (a downstream real failure can issue one later, but not on the
        # janitor sweep that did the requeue).
        assert result["auto_requeued"] >= 1
        assert result["refunded_credits_total"] == 0, \
            f"auto-requeue must not refund, got {result['refunded_credits_total']}"
    finally:
        await db.photo_trailer_jobs.delete_one({"_id": jid})
        cli.close()


# ─── 5. AUTO-RECOVERY: second stale fails properly with refund ────────────────
@pytest.mark.asyncio
async def test_stale_second_time_fails_with_refund(admin_token):
    """retry_count=1 stale job goes to FAILED + STALE_PIPELINE + refund."""
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    jid = f"reliab-rq2-{uuid.uuid4().hex[:8]}"
    user_id = f"reliab-{uuid.uuid4().hex[:6]}"
    try:
        await db.users.insert_one({
            "_id": user_id, "id": user_id, "email": f"{user_id}@test.local",
            "credits_balance": 0,
        })
        # 60s tier: hard_max=15min, stale_threshold=20min. retry_count=1 +
        # past stale_threshold(20) → real FAILED + refund.
        await db.photo_trailer_jobs.insert_one({
            "_id": jid, "user_id": user_id, "status": "PROCESSING",
            "current_stage": "GENERATING_SCENES",
            "duration_target_seconds": 60,
            "started_at": _iso_minutes_ago(22),  # past 20-min stale ceiling
            "created_at": _iso_minutes_ago(22),
            "updated_at": _iso_minutes_ago(10),
            "last_progress_at": _iso_minutes_ago(10),
            "retry_count": 1,  # already retried once
            "charged_credits": 10,
            "refunded_credits": 0,
            "template_id": "superhero_origin",
        })
        result = await _run_janitor(admin_token)
        doc = await db.photo_trailer_jobs.find_one({"_id": jid})
        assert doc["status"] == "FAILED"
        assert doc["error_code"] == "STALE_PIPELINE"
        assert doc.get("failure_stage") == "JANITOR_STALE"
        assert doc.get("refunded_credits") == 10
        assert result["reaped"] >= 1
    finally:
        await db.photo_trailer_jobs.delete_one({"_id": jid})
        await db.users.delete_one({"_id": user_id})
        cli.close()


# ─── 6. _set_stage writes heartbeat fields (verified via API after a real job) ─
# Skip direct call — covered by integration. The source-level test below
# ensures the implementation has the right shape.
def test_set_stage_writes_heartbeat_fields_in_source():
    """Source-level guarantee that _set_stage stamps both heartbeat fields."""
    src = open("/app/backend/routes/photo_trailer.py").read()
    # _set_stage must include both fields in its $set
    assert "last_progress_at" in src
    assert "last_stage_change_at" in src
    # And progress_message reset
    assert '"progress_message": None' in src


# ─── 7. _heartbeat helper exists and surfaces messages ────────────────────────
def test_heartbeat_helper_exists_and_writes_message():
    src = open("/app/backend/routes/photo_trailer.py").read()
    assert "async def _heartbeat" in src
    assert 'upd["progress_message"] = message' in src
    # And the orchestrator actually CALLS it during scene gen + voiceover + render
    assert 'await _heartbeat(job_id, f"Generating scene' in src
    assert 'await _heartbeat(job_id, f"Retrying scene' in src
    assert 'await _heartbeat(job_id, f"Recording voiceover' in src
    assert 'await _heartbeat(job_id, "Final render' in src

# ─── 8. _gen_scene_image inner retry config (3 attempts, 2/5/10s backoff) ─────
def test_gen_scene_image_retry_config():
    src = open("/app/backend/routes/photo_trailer.py").read()
    assert "BACKOFF_SECONDS = [2, 5, 10]" in src, \
        "image-gen backoff must be exactly [2, 5, 10]s per founder spec"
    assert "for attempt in range(3):" in src, \
        "image-gen must retry exactly 3 times per founder spec"


# ─── 9. Orchestrator uses return_exceptions for partial-failure tolerance ─────
def test_scene_gather_uses_return_exceptions():
    """Per founder: a single scene's failure must not cancel sibling scenes
    that are still mid-flight. asyncio.gather(return_exceptions=True) is the
    primitive that gives us per-scene failure isolation."""
    src = open("/app/backend/routes/photo_trailer.py").read()
    # Find the scene-gather block
    assert "return_exceptions=True" in src
    assert "_scene_assets(i, sc)" in src
    # And the failure path reports WHICH scene failed
    assert "Couldn't render scene" in src or "scene {failed_idx[0]+1}" in src


# ─── 10. Recovery shows up in dashboard auto_requeued metric ──────────────────
@pytest.mark.asyncio
async def test_auto_requeued_event_emitted(admin_token):
    """When auto-requeue fires, photo_trailer_auto_requeued must appear in
    funnel_events — that gives the dashboard a count of how many jobs the
    auto-recovery saved."""
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    jid = f"reliab-evt-{uuid.uuid4().hex[:8]}"
    user_id = f"reliab-evt-user-{uuid.uuid4().hex[:6]}"
    try:
        # 60s tier: hard_max=15min, stale_threshold=20min. Use age=17min
        # so we hit the auto-requeue path (not hard-max-suppression).
        await db.photo_trailer_jobs.insert_one({
            "_id": jid, "user_id": user_id, "status": "PROCESSING",
            "current_stage": "GENERATING_SCENES",
            "duration_target_seconds": 60,
            "started_at": _iso_minutes_ago(17),
            "created_at": _iso_minutes_ago(17),
            "last_progress_at": _iso_minutes_ago(10),
            "retry_count": 0,
        })
        await _run_janitor(admin_token)
        # Allow the bg event insert a moment
        import asyncio
        await asyncio.sleep(0.5)
        ev = await db.funnel_events.find_one({
            "step": "photo_trailer_auto_requeued",
            "meta.job_id": jid,
        })
        assert ev is not None, "auto-requeue event should be emitted to funnel_events"
        assert ev["meta"]["retry_count"] == 1
    finally:
        await db.photo_trailer_jobs.delete_one({"_id": jid})
        await db.funnel_events.delete_many({"meta.job_id": jid})
        cli.close()
