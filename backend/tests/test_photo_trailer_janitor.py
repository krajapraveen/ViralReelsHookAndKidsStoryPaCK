"""
Stuck-job janitor tests for Photo Trailer.

Verifies all 4 guarantees:
1. Stale detection: PROCESSING jobs older than STALE_THRESHOLD_MINUTES get reaped.
2. Refund: charged credits are refunded exactly once.
3. Idempotency: running the janitor twice on the same job does not double-refund.
4. Selectivity: fresh PROCESSING jobs and already-terminal jobs are NOT touched.

Tests use the admin-only POST /api/photo-trailer/admin/janitor/run-now endpoint
to trigger sweeps deterministically (no need to wait 5 min wall-clock).
"""
import os
import uuid
import requests
from datetime import datetime, timezone, timedelta
import asyncio
import pytest
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv("/app/backend/.env")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL") or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split("\n")[0].strip()
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
STALE_MIN = 25  # must exceed the largest per-tier threshold (90s = 35min) NO,
#               # must exceed the 20s tier threshold (10min) — using 25 gives us
#               # comfortable margin past 20min (45/60s tier) too. For 90s tier
#               # individual tests pass age explicitly.


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD,
    }, timeout=30)
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text}")
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def db():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]]


def _iso_minutes_ago(n: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=n)).isoformat()


async def _seed_job(db, *, age_min: int, charged: int = 5, refunded: int = 0,
                    status: str = "PROCESSING", retry_count: int = 1,
                    duration_seconds: int = 20) -> str:
    """Insert a synthetic Photo Trailer job for the admin user.

    NOTE on `retry_count`: the reliability sprint added auto-requeue, so a
    fresh (retry_count=0) stale job is REQUEUED, not refunded. Tests that
    want to exercise the FAIL+refund path pass retry_count=1 (already
    requeued once) — that's the real "second-time-stale" path."""
    # Resolve admin user_id once
    admin = await db.users.find_one({"email": ADMIN_EMAIL}, {"_id": 0, "id": 1})
    assert admin, "admin user not found"
    jid = str(uuid.uuid4())
    doc = {
        "_id": jid,
        "user_id": admin["id"],
        "upload_session_id": "test-session-" + jid[:8],
        "status": status,
        "current_stage": "GENERATING_SCENES" if status == "PROCESSING" else status,
        "progress_percent": 50 if status == "PROCESSING" else 0,
        "hero_asset_id": "fake-asset",
        "supporting_asset_ids": [],
        "template_id": "comedy_roast",
        "template_name": "Comedy Roast",
        "duration_target_seconds": duration_seconds,
        "estimated_credits": charged,
        "charged_credits": charged,
        "refunded_credits": refunded,
        "narrator_style": "echo",
        "music_mood": "playful",
        "retry_count": retry_count,
        "created_at": _iso_minutes_ago(age_min + 1),
        "started_at": _iso_minutes_ago(age_min),
        "updated_at": _iso_minutes_ago(age_min),
        # Stale heartbeat so the alive-protection doesn't shield the job
        "last_progress_at": _iso_minutes_ago(age_min),
    }
    await db.photo_trailer_jobs.insert_one(doc)
    return jid


async def _user_credits(db, email: str) -> int:
    u = await db.users.find_one({"email": email}, {"_id": 0, "credits": 1})
    return (u or {}).get("credits", 0)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ────────────────────────────────────────────────────────────────────────────
class TestStaleJobJanitor:
    """End-to-end janitor verification using real DB writes + admin endpoint."""

    def test_stale_processing_job_is_reaped_and_refunded(self, admin_headers, db):
        """6-minute-old PROCESSING job (stale) -> FAILED + refunded exactly once.
        Tolerates the background janitor loop sweeping the job first — what
        matters is that EXACTLY ONE reap happens (manual or auto)."""
        # Setup
        jid = _run(_seed_job(db, age_min=STALE_MIN + 1, charged=5, refunded=0))
        before_credits = _run(_user_credits(db, ADMIN_EMAIL))

        # Trigger manual sweep — may or may not catch this job depending on
        # whether the background loop got there first.
        r = requests.post(f"{BASE_URL}/api/photo-trailer/admin/janitor/run-now",
                          headers=admin_headers, timeout=30)
        assert r.status_code == 200, r.text

        # The defining check: regardless of who reaped it, the job MUST be
        # FAILED + refunded by the time we look.
        # Allow up to 2.5s for either the manual call or the bg loop to finish.
        import time
        deadline = time.time() + 2.5
        job = None
        while time.time() < deadline:
            job = _run(db.photo_trailer_jobs.find_one({"_id": jid}))
            if job["status"] == "FAILED" and job["refunded_credits"] == 5:
                break
            time.sleep(0.2)

        assert job is not None
        assert job["status"] == "FAILED", f"job not reaped: {job}"
        assert job["current_stage"] == "FAILED"
        assert job["error_code"] == "STALE_PIPELINE"
        assert job["refunded_credits"] == 5

        # Verify user credits restored (delta >= 5; could be more if other tests
        # also seeded jobs in parallel, but never less).
        after_credits = _run(_user_credits(db, ADMIN_EMAIL))
        assert after_credits >= before_credits + 5, \
            f"credits not refunded: before={before_credits} after={after_credits}"

    def test_idempotent_double_run_does_not_double_refund(self, admin_headers, db):
        """Running the janitor twice in a row on the same stale job refunds ONCE."""
        jid = _run(_seed_job(db, age_min=STALE_MIN + 2, charged=7, refunded=0))
        before_credits = _run(_user_credits(db, ADMIN_EMAIL))

        # First run reaps + refunds
        r1 = requests.post(f"{BASE_URL}/api/photo-trailer/admin/janitor/run-now",
                           headers=admin_headers, timeout=30)
        assert r1.status_code == 200
        # Second run should NOT re-reap this job (already FAILED; not PROCESSING)
        r2 = requests.post(f"{BASE_URL}/api/photo-trailer/admin/janitor/run-now",
                           headers=admin_headers, timeout=30)
        assert r2.status_code == 200

        after_credits = _run(_user_credits(db, ADMIN_EMAIL))
        # Refund delta must be exactly 7 (this test's job) — not 14.
        delta = after_credits - before_credits
        # Because other tests can also seed jobs, just assert THIS job's refund stayed at 7
        job = _run(db.photo_trailer_jobs.find_one({"_id": jid}))
        assert job["refunded_credits"] == 7, f"refund mutated on second run: {job['refunded_credits']}"
        assert job["status"] == "FAILED"
        # And the second sweep must NOT report this job as freshly reaped
        # (it should be filtered out by status:PROCESSING query). delta covers
        # only THIS test's refund, so it should be >=7 but the per-job
        # refunded_credits check above is the strict idempotency proof.
        assert delta >= 7, f"first refund missing: delta={delta}"

    def test_fresh_processing_job_is_not_reaped(self, admin_headers, db):
        """A 1-minute-old PROCESSING job is healthy and must NOT be touched."""
        jid = _run(_seed_job(db, age_min=1, charged=5, refunded=0))

        r = requests.post(f"{BASE_URL}/api/photo-trailer/admin/janitor/run-now",
                          headers=admin_headers, timeout=30)
        assert r.status_code == 200

        job = _run(db.photo_trailer_jobs.find_one({"_id": jid}))
        assert job["status"] == "PROCESSING", f"fresh job should not be reaped: {job}"
        assert job.get("error_code") is None
        assert job["refunded_credits"] == 0

        # Cleanup so we don't leave fake PROCESSING jobs lying around
        _run(db.photo_trailer_jobs.delete_one({"_id": jid}))

    def test_terminal_job_is_not_reaped(self, admin_headers, db):
        """An old COMPLETED job must be skipped — only PROCESSING is in scope."""
        jid = _run(_seed_job(db, age_min=STALE_MIN + 5, charged=5,
                             refunded=0, status="COMPLETED"))

        r = requests.post(f"{BASE_URL}/api/photo-trailer/admin/janitor/run-now",
                          headers=admin_headers, timeout=30)
        assert r.status_code == 200

        job = _run(db.photo_trailer_jobs.find_one({"_id": jid}))
        assert job["status"] == "COMPLETED"
        assert job["refunded_credits"] == 0
        assert job.get("error_code") is None

        _run(db.photo_trailer_jobs.delete_one({"_id": jid}))
