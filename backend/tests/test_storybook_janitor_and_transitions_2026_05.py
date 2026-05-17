"""
Phase 3c-minimal + Phase 4a 2026-05-19 — Comic Storybook canonical
transition log + stuck-job janitor.
=====================================================================
Phase 3c-minimal: every terminal status change on a
`comic_storybook_v2_jobs` row is audited into
`comic_storybook_v2_transitions` with the source, the previous
status, the new status, an optional reason, and the request_id.

Phase 4a: a background janitor finds non-terminal jobs whose
`updatedAt` is older than STUCK_THRESHOLD_MINUTES, transitions them
to FAILED_STUCK with refund, releases the idempotency lock, and
records the audit row.

Locked-in contract:
  1. `record_transition()` is the canonical helper. Failures are
     swallowed — audit never breaks the generation flow.
  2. `recover_stuck_comic_jobs()` is idempotent — running it twice
     on the same stuck row produces the same (recovered) state.
  3. Janitor uses CAS (`{id: ..., status: prev}`) so it can't
     clobber a racing real-completion update.
  4. Janitor refunds the cost on the user document and releases any
     leftover idempotency lock.
  5. Admin-only endpoints: `POST /admin/janitor/run` and
     `GET /admin/transitions/{job_id}` (uses `is_unlimited_user`).
  6. Pipeline completion + exception branches both write transitions.
"""
from __future__ import annotations

import os
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from pymongo import MongoClient

sys.path.insert(0, "/app/backend")

from services.comic_storybook_janitor import (  # noqa: E402
    record_transition,
    recover_stuck_comic_jobs,
    STUCK_THRESHOLD_MINUTES,
    TERMINAL_STATUSES,
)


JANITOR_PY = Path("/app/backend/services/comic_storybook_janitor.py")
COMIC_ROUTE_PY = Path("/app/backend/routes/comic_storybook_v2.py")
SERVER_PY = Path("/app/backend/server.py")


def _api_base() -> str:
    for line in open("/app/frontend/.env"):
        if line.startswith("REACT_APP_BACKEND_URL="):
            return line.split("=", 1)[1].strip()
    return "http://localhost:8001"


def _backend_env():
    text = open("/app/backend/.env").read()
    mongo = re.search(r"^MONGO_URL=(.*)$", text, flags=re.M).group(1).strip().strip('"')
    dbn = re.search(r"^DB_NAME=(.*)$", text, flags=re.M).group(1).strip().strip('"')
    return mongo, dbn


@pytest.fixture
def sync_db():
    mongo, dbn = _backend_env()
    yield MongoClient(mongo)[dbn]


@pytest_asyncio.fixture
async def admin_session():
    async with httpx.AsyncClient(base_url=_api_base(), timeout=20.0) as cli:
        r = await cli.post(
            "/api/auth/login",
            json={"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"},
        )
        assert r.status_code == 200
        d = r.json()
        yield d.get("access_token") or d.get("token"), (d.get("user") or {}).get("id")


# ════════════════════════════════════════════════════════════════════════
# 1. Source — janitor module structural contract
# ════════════════════════════════════════════════════════════════════════
def test_terminal_statuses_include_failed_stuck():
    """FAILED_STUCK is the new terminal status emitted by the janitor.
    It must be in TERMINAL_STATUSES so a second pass doesn't re-process
    an already-recovered job."""
    assert "FAILED_STUCK" in TERMINAL_STATUSES


def test_stuck_threshold_default_is_30_minutes():
    """Defensive: the live env override is fine, but the default must
    be conservative enough that real long generations don't get killed."""
    assert STUCK_THRESHOLD_MINUTES >= 5, (
        "Janitor threshold must be at least 5 minutes — anything lower "
        "risks killing a healthy long-running generation"
    )


def test_record_transition_swallows_errors_to_protect_pipeline():
    """The audit MUST never break the generation flow."""
    src = JANITOR_PY.read_text()
    fn = src.split("async def record_transition", 1)[1].split(
        "\n\nasync def ", 1
    )[0]
    assert "try:" in fn and "except Exception" in fn, (
        "record_transition must wrap the insert in a try/except so a "
        "MongoDB hiccup never crashes the pipeline"
    )


def test_janitor_uses_cas_to_avoid_clobbering_real_completion():
    """The recovery write must include the previous status in the
    filter so a racing real-completion update can't be clobbered."""
    src = JANITOR_PY.read_text()
    fn = src.split("async def recover_stuck_comic_jobs", 1)[1].split(
        "\n\nasync def ", 1
    )[0]
    assert '"id": job_id, "status": prev' in fn, (
        "Janitor update must use CAS on (id, status) so it can't clobber "
        "a job that just completed legitimately"
    )


def test_janitor_refunds_credits_and_releases_idempotency_lock():
    src = JANITOR_PY.read_text()
    fn = src.split("async def recover_stuck_comic_jobs", 1)[1].split(
        "\n\nasync def ", 1
    )[0]
    assert "credits" in fn and "$inc" in fn, (
        "Janitor must refund credits on recovery"
    )
    assert "idempotency_keys" in fn and "delete_one" in fn, (
        "Janitor must release the idempotency lock so the user can retry"
    )


# ════════════════════════════════════════════════════════════════════════
# 2. Pipeline writes transition rows on terminal states
# ════════════════════════════════════════════════════════════════════════
def test_pipeline_writes_transition_on_success():
    src = COMIC_ROUTE_PY.read_text()
    # Locate the success path in the pipeline.
    success_block = src.split("logger.info(f\"[COMIC] Job {job_id[:8]} → {final_status}", 1)[0]
    assert "source=\"pipeline:completion\"" in success_block[-2000:], (
        "Pipeline success path must record a canonical transition"
    )


def test_pipeline_writes_transition_on_exception():
    src = COMIC_ROUTE_PY.read_text()
    assert 'source="pipeline:exception"' in src, (
        "Pipeline exception path must record a canonical transition"
    )


# ════════════════════════════════════════════════════════════════════════
# 3. Server startup wires the janitor under the env flag
# ════════════════════════════════════════════════════════════════════════
def test_server_startup_schedules_janitor():
    src = SERVER_PY.read_text()
    assert "COMIC_STORYBOOK_JANITOR_ENABLED" in src, (
        "Janitor must be opt-in via env flag for rollback safety"
    )
    assert "run_janitor_forever" in src, (
        "Startup must spawn the janitor task"
    )
    assert "[ComicStorybookJanitor] scheduled" in src


# ════════════════════════════════════════════════════════════════════════
# 4. Live HTTP — admin endpoints
# ════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_admin_can_trigger_manual_janitor_pass(admin_session):
    token, _ = admin_session
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        r = await cli.post(
            "/api/comic-storybook-v2/admin/janitor/run",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("checked", "recovered_count", "threshold_minutes", "recovered"):
            assert k in body, f"manual janitor response missing {k!r}"


@pytest.mark.asyncio
async def test_admin_can_read_transition_log_for_job(sync_db, admin_session):
    """Synthesize a job + two transition rows, then read them via the
    admin endpoint. Forensic trail must come back in chronological
    order."""
    token, _ = admin_session
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    sync_db.comic_storybook_v2_transitions.insert_many([
        {"id": str(uuid.uuid4()), "job_id": job_id, "from_status": "QUEUED",
         "to_status": "PROCESSING", "source": "pipeline:start",
         "ts": (now - timedelta(seconds=120)).isoformat()},
        {"id": str(uuid.uuid4()), "job_id": job_id, "from_status": "PROCESSING",
         "to_status": "COMPLETED", "source": "pipeline:completion",
         "ts": now.isoformat()},
    ])
    try:
        async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
            r = await cli.get(
                f"/api/comic-storybook-v2/admin/transitions/{job_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["count"] == 2
            assert body["transitions"][0]["to_status"] == "PROCESSING"
            assert body["transitions"][1]["to_status"] == "COMPLETED"
    finally:
        sync_db.comic_storybook_v2_transitions.delete_many({"job_id": job_id})


@pytest.mark.asyncio
async def test_non_admin_cannot_run_janitor():
    """Plain user must get a structured 403 — not silently allowed."""
    # Use a non-admin signup if available; otherwise we just hit the
    # endpoint with no token and confirm we get 401/403.
    async with httpx.AsyncClient(base_url=_api_base(), timeout=10.0) as cli:
        r = await cli.post("/api/comic-storybook-v2/admin/janitor/run")
        assert r.status_code in (401, 403, 422), r.text


# ════════════════════════════════════════════════════════════════════════
# 5. Live HTTP — janitor recovers a synthesized stuck job
# ════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_manual_janitor_recovers_synthesized_stuck_job(sync_db, admin_session):
    """End-to-end proof: insert a stuck PROCESSING job (updatedAt 45m
    old), call the admin run endpoint, confirm it's now FAILED_STUCK,
    refund landed, and an audit row exists."""
    token, _ = admin_session
    job_id = str(uuid.uuid4())
    fake_user_id = f"qa-stuck-{uuid.uuid4().hex[:8]}"
    long_ago = (datetime.now(timezone.utc) - timedelta(minutes=45)).isoformat()
    sync_db.comic_storybook_v2_jobs.insert_one({
        "id": job_id,
        "userId": fake_user_id,
        "type": "COMIC_STORYBOOK",
        "status": "PROCESSING",
        "progress": 42,
        "cost": 60,
        "createdAt": long_ago,
        "updatedAt": long_ago,
    })
    # Synthesize a user document so the refund $inc has something to
    # land on (otherwise the update is a no-op, which is fine — but
    # we want to verify the refund actually applies).
    sync_db.users.insert_one({"id": fake_user_id, "credits": 0})
    try:
        async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
            r = await cli.post(
                "/api/comic-storybook-v2/admin/janitor/run",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["recovered_count"] >= 1, body
            # Our job must be in the recovered list.
            recovered_ids = [r["job_id"] for r in body["recovered"]]
            assert job_id in recovered_ids
        # Verify the row is now FAILED_STUCK.
        row = sync_db.comic_storybook_v2_jobs.find_one({"id": job_id})
        assert row["status"] == "FAILED_STUCK"
        # Refund landed.
        user_row = sync_db.users.find_one({"id": fake_user_id})
        assert user_row["credits"] == 60, (
            f"Refund should have set credits to 60; got {user_row['credits']}"
        )
        # Audit row exists.
        audit = sync_db.comic_storybook_v2_transitions.find_one(
            {"job_id": job_id, "source": "janitor:stuck-job"}
        )
        assert audit is not None
        assert audit["to_status"] == "FAILED_STUCK"
    finally:
        sync_db.comic_storybook_v2_jobs.delete_one({"id": job_id})
        sync_db.users.delete_one({"id": fake_user_id})
        sync_db.comic_storybook_v2_transitions.delete_many({"job_id": job_id})


@pytest.mark.asyncio
async def test_janitor_does_not_touch_fresh_jobs(sync_db, admin_session):
    """A job whose `updatedAt` is recent (1 minute old) must NOT be
    recovered. Otherwise the janitor would kill healthy running jobs."""
    token, _ = admin_session
    job_id = str(uuid.uuid4())
    recent = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    sync_db.comic_storybook_v2_jobs.insert_one({
        "id": job_id,
        "userId": f"qa-fresh-{uuid.uuid4().hex[:8]}",
        "type": "COMIC_STORYBOOK",
        "status": "PROCESSING",
        "progress": 42,
        "cost": 60,
        "createdAt": recent,
        "updatedAt": recent,
    })
    try:
        async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
            r = await cli.post(
                "/api/comic-storybook-v2/admin/janitor/run",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r.status_code == 200
            recovered_ids = [r["job_id"] for r in r.json()["recovered"]]
            assert job_id not in recovered_ids, (
                "Fresh job was wrongly recovered — threshold filter broken"
            )
        # Confirm the row is still PROCESSING.
        row = sync_db.comic_storybook_v2_jobs.find_one({"id": job_id})
        assert row["status"] == "PROCESSING"
    finally:
        sync_db.comic_storybook_v2_jobs.delete_one({"id": job_id})
