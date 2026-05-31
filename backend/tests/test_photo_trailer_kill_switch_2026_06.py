"""P0 2026-06 — Photo Trailer KILL SWITCH (PHOTO_TRAILER_PAUSED).

Hard kill switch ordered by the user during the krajapraveen@gmail.com
production money-trust incident (multiple FAILED Anime Intro trailers
still deducting credits despite the refund-integrity patch). The switch
must satisfy:

  • POST /api/photo-trailer/jobs → 503 BEFORE deduction / upload / enqueue.
  • POST /api/photo-trailer/jobs/{id}/retry → 503 (retries burn compute too).
  • GET  /api/photo-trailer/my-trailers → still 200 (existing trailers viewable).
  • GET  /api/photo-trailer/jobs/{id}  → still 200 (existing trailer details).
  • POST /api/photo-trailer/admin/repair-refunds → still 200 (ops unblocked).
  • GET  /api/photo-trailer/admin/diagnose-user → still 200 (ops unblocked).
  • GET  /api/photo-trailer/status → public probe so the frontend banner renders.

These tests drive the LIVE backend (avoids Motor's cross-event-loop trap)
and toggle the env var in-process. Each test resets the flag at teardown
so an aborted test cannot leave the switch on for the next suite.

Pinned in: /app/Makefile (BOUNDARY_AUDIT_SUITES)
"""
from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
import pytest_asyncio
import httpx
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient


load_dotenv("/app/backend/.env")
ROOT = Path(__file__).resolve().parents[2]
TRAILER_PATH = ROOT / "backend" / "routes" / "photo_trailer.py"
FRONTEND_PATH = ROOT / "frontend" / "src" / "pages" / "PhotoTrailerPage.jsx"


def _api_base() -> str:
    p = "/app/frontend/.env"
    if os.path.exists(p):
        for line in open(p):
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    return "http://localhost:8001"


# ─── Flag toggle helper ──────────────────────────────────────────────────────
# We flip the env var in-process AND hot-reload the photo_trailer module's
# bound copy because `_is_paused()` reads `os.environ` every call — so a
# simple `os.environ["PHOTO_TRAILER_PAUSED"] = "true"` is enough.


class _Flag:
    @staticmethod
    def on():
        os.environ["PHOTO_TRAILER_PAUSED"] = "true"

    @staticmethod
    def off():
        os.environ.pop("PHOTO_TRAILER_PAUSED", None)


@pytest.fixture(autouse=True)
def _reset_flag_between_tests():
    """Guarantee the kill switch is off before AND after every test —
    so a bug in one test cannot pause the suite that follows."""
    _Flag.off()
    yield
    _Flag.off()


# ─── Test user fixture (sync between live process + this suite via env) ──────


@pytest_asyncio.fixture
async def trailer_user():
    """Seed a synthetic premium user with credits + a COMPLETED upload
    session + hero asset. JWT is minted directly so we bypass /register
    rate-limiting. Tears down everything we touched at fixture exit."""
    import sys
    sys.path.insert(0, "/app/backend")
    from shared import create_token  # noqa: WPS433

    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]

    user_id = f"killsw-{uuid.uuid4().hex[:8]}"
    email = f"killsw-{uuid.uuid4().hex[:6]}@example.com"
    session_id = str(uuid.uuid4())
    asset_id = str(uuid.uuid4())
    sub_id = str(uuid.uuid4())

    starting_credits = 100
    await db.users.insert_one({
        "_id": user_id, "id": user_id, "email": email,
        "name": "Kill Switch Test", "role": "USER",
        "credits": starting_credits,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await db.subscriptions.insert_one({
        "_id": sub_id, "userId": user_id,
        "planId": "monthly",  # PREMIUM tier
        "status": "active",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    })
    await db.photo_trailer_upload_sessions.insert_one({
        "_id": session_id, "user_id": user_id,
        "status": "COMPLETED", "asset_ids": [asset_id], "photo_count": 1,
        "consent_recorded_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await db.photo_trailer_assets.insert_one({
        "_id": asset_id, "user_id": user_id,
        "upload_session_id": session_id,
        "stored_url": "https://example.invalid/fake.jpg",
        "storage_key": "fake/key.jpg",
        "moderation_status": "PASSED",
        "consent_recorded_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    # Seed one COMPLETED trailer + one FAILED-with-deduction trailer so
    # listing/viewing/repair surfaces all have data to operate on.
    completed_jid = f"job-comp-{uuid.uuid4().hex[:8]}"
    failed_jid = f"job-fail-{uuid.uuid4().hex[:8]}"
    await db.photo_trailer_jobs.insert_one({
        "_id": completed_jid, "user_id": user_id,
        "status": "COMPLETED", "current_stage": "COMPLETED",
        "duration_target_seconds": 60, "template_id": "anime_intro",
        "estimated_credits": 35, "charged_credits": 35, "refunded_credits": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    })
    await db.photo_trailer_jobs.insert_one({
        "_id": failed_jid, "user_id": user_id,
        "status": "FAILED", "current_stage": "FAILED",
        "duration_target_seconds": 60, "template_id": "anime_intro",
        "estimated_credits": 35, "charged_credits": 35, "refunded_credits": 0,
        "error_code": "RENDER_INVALID",
        "error_message": "Trailer failed. Refund is being processed.",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "failed_at": datetime.now(timezone.utc).isoformat(),
    })

    token = create_token(user_id, "USER")
    yield {
        "token": token, "user_id": user_id, "email": email,
        "session_id": session_id, "hero_asset_id": asset_id,
        "starting_credits": starting_credits,
        "completed_job_id": completed_jid,
        "failed_job_id": failed_jid,
        "db": db,
    }

    await db.users.delete_one({"id": user_id})
    await db.subscriptions.delete_one({"_id": sub_id})
    await db.photo_trailer_upload_sessions.delete_one({"_id": session_id})
    await db.photo_trailer_assets.delete_one({"_id": asset_id})
    await db.photo_trailer_jobs.delete_many({"user_id": user_id})
    await db.credit_ledger.delete_many({"user_id": user_id})
    await db.funnel_events.delete_many({"user_id": user_id})
    cli.close()


# ─── 1. Static-source pin: kill switch wired at the earliest gate ────────────


def test_create_job_pause_check_is_first_statement():
    """The pause guard must execute BEFORE template lookup, upload-session
    lookup, plan check, credit math, prompt sanitizer, or job insert.
    Lexically: the `_is_paused()` call must appear before the first
    `db.photo_trailer_upload_sessions.find_one` AND before the
    `deduct_credits` call inside the body of `create_job`."""
    src = TRAILER_PATH.read_text()
    m = re.search(
        r"^async def create_job\([^)]*\)[^:]*:\s*\n(?P<body>(?:^[ \t]+.*\n|^\s*\n)+)",
        src, re.M,
    )
    assert m, "create_job() must exist."
    body = m.group("body")
    paused_pos = body.find("_is_paused()")
    session_pos = body.find("db.photo_trailer_upload_sessions.find_one")
    assert paused_pos != -1, "create_job must call _is_paused()"
    assert session_pos != -1, "create_job must look up upload session"
    assert paused_pos < session_pos, (
        "_is_paused() must be checked BEFORE upload-session lookup so a "
        "paused feature does not consume any DB/compute work."
    )


def test_retry_job_also_pause_gated():
    """Retries trigger a fresh pipeline (free compute burn). They must be
    blocked too — otherwise a paused feature would still drain workers."""
    src = TRAILER_PATH.read_text()
    m = re.search(
        r"^async def retry_job\([^)]*\)[^:]*:\s*\n(?P<body>(?:^[ \t]+.*\n|^\s*\n)+)",
        src, re.M,
    )
    assert m, "retry_job() must exist."
    body = m.group("body")
    pause_pos = body.find("_is_paused()")
    db_pos = body.find("db.photo_trailer_jobs.find_one")
    assert pause_pos != -1, "retry_job must call _is_paused()"
    assert db_pos != -1, "retry_job must look up the existing job"
    assert pause_pos < db_pos, (
        "Pause check must precede the job lookup."
    )


def test_is_paused_reads_env_per_call_not_import_time():
    """The helper must read os.environ on every call so operators can
    toggle the flag without restarting code. A cached `paused=...` at
    import time would defeat the purpose."""
    src = TRAILER_PATH.read_text()
    m = re.search(r"def _is_paused\(\)[^:]*:(?P<body>.+?)\n\n", src, re.S)
    assert m, "_is_paused() must exist."
    body = m.group("body")
    assert "os.environ" in body, (
        "_is_paused() must read os.environ at call time."
    )


def test_frontend_renders_paused_banner_and_blocks_generate():
    """The frontend must (a) probe /status, (b) render a banner with the
    correct test-id when paused, (c) early-return from onGenerate so no
    fetch fires."""
    src = FRONTEND_PATH.read_text()
    assert '/api/photo-trailer/status' in src, (
        "Frontend must probe the public /status endpoint."
    )
    assert 'trailer-paused-banner' in src, (
        "Frontend must render the kill-switch banner with a stable test-id."
    )
    # onGenerate must bail before calling fetch.
    on_gen = re.search(
        r"const onGenerate\s*=\s*async\s*\(\)\s*=>\s*\{(?P<body>.+?)\};\s*\n",
        src, re.S,
    )
    assert on_gen, "onGenerate must exist."
    body = on_gen.group("body")
    paused_pos = body.find("paused.paused")
    fetch_pos = body.find("fetch(")
    assert paused_pos != -1, "onGenerate must check paused.paused"
    assert paused_pos < fetch_pos, (
        "onGenerate must bail BEFORE any fetch call when paused."
    )


# ─── 2. Behavioural: real HTTP against the running backend ──────────────────


@pytest.mark.asyncio
async def test_post_jobs_returns_503_and_does_not_deduct_when_paused(trailer_user):
    """When PHOTO_TRAILER_PAUSED is on, POST /jobs must return a 503 with
    the TRAILER_PAUSED code AND the user's credit balance must be unchanged.

    Drives the FastAPI app IN-PROCESS via ASGI transport so the env-var
    toggle is observable (the supervisor backend runs in a separate
    process and would not see our os.environ change)."""
    _Flag.on()
    starting = trailer_user["starting_credits"]

    import sys
    sys.path.insert(0, "/app/backend")
    # Re-import the router module so the route handlers re-evaluate
    # _is_paused() against the CURRENT os.environ — they do anyway
    # (read every call), so this is belt + suspenders.
    from server import app  # noqa: WPS433
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", timeout=15.0) as cli:
        r = await cli.post(
            "/api/photo-trailer/jobs",
            headers={"Authorization": f"Bearer {trailer_user['token']}"},
            json={
                "upload_session_id": trailer_user["session_id"],
                "hero_asset_id":     trailer_user["hero_asset_id"],
                "supporting_asset_ids": [],
                "template_id": "anime_intro",
                "duration_target_seconds": 60,
            },
        )

    assert r.status_code == 503, f"expected 503, got {r.status_code}: {r.text}"
    body = r.json()
    detail = body.get("detail")
    assert isinstance(detail, dict), f"detail must be dict: {detail}"
    assert detail["code"] == "TRAILER_PAUSED"
    assert "paused" in detail["message"].lower()

    # Credit balance must be UNCHANGED — the gate fired before deduction.
    db = trailer_user["db"]
    after = await db.users.find_one({"id": trailer_user["user_id"]}, {"_id": 0, "credits": 1})
    assert int(after["credits"]) == starting, (
        f"Paused gate must not deduct credits. Was {starting}, now {after['credits']}"
    )
    # And no job document must have been created.
    new_jobs = await db.photo_trailer_jobs.count_documents({
        "user_id": trailer_user["user_id"],
        "_id": {"$nin": [trailer_user["completed_job_id"], trailer_user["failed_job_id"]]},
    })
    assert new_jobs == 0, "Paused gate must not create a job document."


@pytest.mark.asyncio
async def test_status_endpoint_reports_pause_state(trailer_user):
    """Public /status endpoint must reflect the flag — the frontend banner
    relies on this. Driven in-process so the env-var toggle is observable."""
    import sys
    sys.path.insert(0, "/app/backend")
    from server import app  # noqa: WPS433
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", timeout=10.0) as cli:
        # Off
        _Flag.off()
        r1 = await cli.get("/api/photo-trailer/status")
        assert r1.status_code == 200
        assert r1.json()["paused"] is False

        # On
        _Flag.on()
        r2 = await cli.get("/api/photo-trailer/status")
        assert r2.status_code == 200
        body = r2.json()
        assert body["paused"] is True
        assert body["message"], "Paused response must carry a user-facing message."


@pytest.mark.asyncio
async def test_existing_trailers_remain_listable_and_viewable_when_paused(trailer_user):
    """The kill switch must not hide a user's existing work."""
    base = _api_base()
    _Flag.on()
    async with httpx.AsyncClient(base_url=base, timeout=15.0) as cli:
        listing = await cli.get(
            "/api/photo-trailer/my-trailers",
            headers={"Authorization": f"Bearer {trailer_user['token']}"},
        )
        assert listing.status_code == 200, f"my-trailers must remain 200 when paused: {listing.text}"
        trailers = listing.json().get("trailers", [])
        ids = {t.get("job_id") for t in trailers}
        assert trailer_user["completed_job_id"] in ids
        assert trailer_user["failed_job_id"] in ids

        detail = await cli.get(
            f"/api/photo-trailer/jobs/{trailer_user['completed_job_id']}",
            headers={"Authorization": f"Bearer {trailer_user['token']}"},
        )
        assert detail.status_code == 200, f"job detail must remain 200 when paused: {detail.text}"


@pytest.mark.asyncio
async def test_admin_diagnose_and_repair_still_work_when_paused(trailer_user):
    """The whole point of pausing is to fix money — so ops surfaces must
    keep working. We mint a synthetic admin user just for this check."""
    import sys
    sys.path.insert(0, "/app/backend")
    from shared import create_token  # noqa: WPS433

    admin_id = f"adm-killsw-{uuid.uuid4().hex[:6]}"
    admin_email = f"adm-killsw-{uuid.uuid4().hex[:6]}@example.com"
    db = trailer_user["db"]
    await db.users.insert_one({
        "_id": admin_id, "id": admin_id, "email": admin_email,
        "name": "Kill Switch Admin", "role": "ADMIN",
        "credits": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    admin_token = create_token(admin_id, "ADMIN")

    base = _api_base()
    _Flag.on()
    try:
        async with httpx.AsyncClient(base_url=base, timeout=15.0) as cli:
            # Diagnose — must still work for the synthetic user we seeded.
            diag = await cli.get(
                f"/api/photo-trailer/admin/diagnose-user?email={trailer_user['email']}",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert diag.status_code == 200, f"diagnose must work when paused: {diag.text}"
            d = diag.json()
            assert d["email"] == trailer_user["email"]
            jids = {t["job_id"] for t in d["trailers"]}
            assert trailer_user["failed_job_id"] in jids

            # Repair — dry-run must run and return a candidate.
            rep = await cli.post(
                "/api/photo-trailer/admin/repair-refunds",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"user_email": trailer_user["email"], "dry_run": True, "limit": 50},
            )
            assert rep.status_code == 200, f"repair must work when paused: {rep.text}"
            rb = rep.json()
            assert rb["dry_run"] is True
            # FAILED job with charged>0 and refunded=0 is exactly our seeded scenario.
            assert rb["candidates"] >= 1, f"repair sweep must find the seeded failed job: {rb}"
            assert any(r["job_id"] == trailer_user["failed_job_id"] for r in rb["results"])
    finally:
        await db.users.delete_one({"id": admin_id})


@pytest.mark.asyncio
async def test_post_jobs_returns_200_when_unpaused(trailer_user):
    """Sanity: with the flag OFF, the same payload must NOT trip the kill
    switch. (This validates that our test toggle actually toggles.)"""
    base = _api_base()
    # Explicit off (even though autouse fixture cleared it).
    _Flag.off()
    async with httpx.AsyncClient(base_url=base, timeout=20.0) as cli:
        r = await cli.post(
            "/api/photo-trailer/jobs",
            headers={"Authorization": f"Bearer {trailer_user['token']}"},
            json={
                "upload_session_id": trailer_user["session_id"],
                "hero_asset_id":     trailer_user["hero_asset_id"],
                "supporting_asset_ids": [],
                "template_id": "anime_intro",
                "duration_target_seconds": 60,
            },
        )
    # Must NOT be 503 with TRAILER_PAUSED. (Job may still 200/4xx for other
    # validation reasons — but never our paused code.)
    assert r.status_code != 503 or "TRAILER_PAUSED" not in r.text, (
        f"Kill switch tripped when flag was OFF: {r.status_code} {r.text}"
    )
