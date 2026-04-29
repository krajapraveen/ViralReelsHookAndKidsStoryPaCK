"""Tests for the P0 START-ERROR transparency fix (2026-04-29).

Backend: every error path on POST /api/photo-trailer/jobs returns a structured
{detail: {code, message}} envelope so the frontend can map to a human message.

Frontend: source-level guarantees that the inline error panel + mapper +
funnel event are wired correctly.
"""
import os
import re
import uuid
import pytest
import pytest_asyncio
import httpx
from datetime import datetime, timezone
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


@pytest_asyncio.fixture
async def authed_user():
    """Synthetic user with PREMIUM tier (so plan checks pass) but zero credits."""
    import sys
    sys.path.insert(0, "/app/backend")
    from shared import create_token

    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    user_id = f"errfx-{uuid.uuid4().hex[:8]}"
    sub_id = str(uuid.uuid4())
    sess_id = str(uuid.uuid4())
    asset_id = str(uuid.uuid4())
    try:
        await db.users.insert_one({
            "_id": user_id, "id": user_id,
            "email": f"{user_id}@example.com",
            "credits": 0, "role": "USER",
            "created_at": _now_iso(),
        })
        await db.subscriptions.insert_one({
            "_id": sub_id, "userId": user_id,
            "planId": "monthly", "status": "active",
            "createdAt": _now_iso(),
        })
        await db.photo_trailer_upload_sessions.insert_one({
            "_id": sess_id, "user_id": user_id,
            "status": "COMPLETED",
            "asset_ids": [asset_id], "photo_count": 1,
            "consent_recorded_at": _now_iso(),
            "created_at": _now_iso(),
        })
        await db.photo_trailer_assets.insert_one({
            "_id": asset_id, "user_id": user_id,
            "upload_session_id": sess_id,
            "stored_url": "https://example.invalid/x.jpg",
            "storage_key": "fake/x.jpg",
            "moderation_status": "PASSED",
            "consent_recorded_at": _now_iso(),
            "created_at": _now_iso(),
        })
        token = create_token(user_id, "USER")
        yield {"token": token, "user_id": user_id, "sess_id": sess_id, "asset_id": asset_id}
    finally:
        await db.users.delete_one({"_id": user_id})
        await db.subscriptions.delete_one({"_id": sub_id})
        await db.photo_trailer_upload_sessions.delete_one({"_id": sess_id})
        await db.photo_trailer_assets.delete_one({"_id": asset_id})
        await db.photo_trailer_jobs.delete_many({"user_id": user_id})
        await db.funnel_events.delete_many({"user_id": user_id})
        cli.close()


# ─── BACKEND: every error path returns structured detail ──────────────────────
@pytest.mark.asyncio
async def test_invalid_template_returns_structured_400(authed_user):
    base = _api_base()
    async with httpx.AsyncClient(base_url=base, timeout=15.0) as cli:
        r = await cli.post(
            "/api/photo-trailer/jobs",
            headers={"Authorization": f"Bearer {authed_user['token']}"},
            json={
                "upload_session_id": authed_user["sess_id"],
                "hero_asset_id":     authed_user["asset_id"],
                "supporting_asset_ids": [],
                "template_id": "definitely_not_a_real_template",
                "duration_target_seconds": 20,
                "narrator_style": "alloy",
            },
        )
    assert r.status_code == 400, r.text
    body = r.json()
    assert isinstance(body.get("detail"), dict)
    assert body["detail"]["code"] == "INVALID_TEMPLATE"
    assert body["detail"]["message"]


@pytest.mark.asyncio
async def test_unknown_session_returns_structured_404(authed_user):
    base = _api_base()
    async with httpx.AsyncClient(base_url=base, timeout=15.0) as cli:
        r = await cli.post(
            "/api/photo-trailer/jobs",
            headers={"Authorization": f"Bearer {authed_user['token']}"},
            json={
                "upload_session_id": "nope-no-such-session",
                "hero_asset_id":     authed_user["asset_id"],
                "supporting_asset_ids": [],
                "template_id": "comedy_roast",
                "duration_target_seconds": 20,
                "narrator_style": "alloy",
            },
        )
    assert r.status_code == 404
    body = r.json()
    assert body["detail"]["code"] == "UPLOAD_SESSION_NOT_FOUND"


@pytest.mark.asyncio
async def test_too_many_active_jobs_returns_structured_429(authed_user):
    """Seed an active PROCESSING job so the next POST hits the active-job cap."""
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    base = _api_base()
    seeded = []
    try:
        # USER cap is 1 — seed one PROCESSING job
        seed_id = f"errfx-block-{uuid.uuid4().hex[:8]}"
        await db.photo_trailer_jobs.insert_one({
            "_id": seed_id, "user_id": authed_user["user_id"],
            "status": "PROCESSING",
            "current_stage": "GENERATING_SCENES",
            "duration_target_seconds": 60,
            "started_at": _now_iso(), "created_at": _now_iso(),
        })
        seeded.append(seed_id)
        async with httpx.AsyncClient(base_url=base, timeout=15.0) as h:
            r = await h.post(
                "/api/photo-trailer/jobs",
                headers={"Authorization": f"Bearer {authed_user['token']}"},
                json={
                    "upload_session_id": authed_user["sess_id"],
                    "hero_asset_id":     authed_user["asset_id"],
                    "supporting_asset_ids": [],
                    "template_id": "comedy_roast",
                    "duration_target_seconds": 20,
                    "narrator_style": "alloy",
                },
            )
        assert r.status_code == 429
        body = r.json()
        assert body["detail"]["code"] == "TOO_MANY_ACTIVE_JOBS"
        assert body["detail"]["active_jobs"] >= 1
    finally:
        for jid in seeded:
            await db.photo_trailer_jobs.delete_one({"_id": jid})
        cli.close()


@pytest.mark.asyncio
async def test_funnel_allowlist_includes_start_failed():
    """The new event must be allowlisted or the public /api/funnel/track will
    silently drop the frontend's analytics payload."""
    src = open("/app/backend/routes/funnel_tracking.py").read()
    assert '"photo_trailer_start_failed"' in src


# ─── FRONTEND: source-level proofs ────────────────────────────────────────────
SRC_PATH = "/app/frontend/src/pages/PhotoTrailerPage.jsx"


def _src() -> str:
    return open(SRC_PATH).read()


def test_frontend_has_error_message_map():
    """The mapper must cover every code the founder spec'd."""
    src = _src()
    for code in (
        "INSUFFICIENT_CREDITS",
        "RATE_LIMITED",
        "AUTH_REQUIRED",
        "BETA_LOCKED",
        "VALIDATION_ERROR",
        "UNKNOWN",
        "UPGRADE_REQUIRED",
        "FREE_QUOTA_EXCEEDED",
        "TOO_MANY_ACTIVE_JOBS",
        "INVALID_TEMPLATE",
        "UPLOAD_SESSION_NOT_FOUND",
        "UPLOAD_NOT_FINALISED",
        "PROMPT_BLOCKED",
    ):
        assert f'{code}:' in src, f"START_ERROR_MESSAGES missing code: {code}"


def test_frontend_inline_error_panel_present():
    """The panel above Generate must have stable testids and an Alert role."""
    src = _src()
    for tid in (
        "trailer-start-error",
        "trailer-start-error-message",
        "trailer-start-error-code",
        "trailer-start-error-dismiss",
    ):
        assert f'data-testid="{tid}"' in src, f"missing testid: {tid}"
    assert 'role="alert"' in src, "inline error panel must have role=alert for a11y"


def test_frontend_emits_start_failed_event():
    """photo_trailer_start_failed must fire with {code, message, http_status}."""
    src = _src()
    assert "photo_trailer_start_failed" in src
    # Args we want present (matches the spec's structured event)
    assert re.search(r"code:\s*err\.code", src), "must emit err.code"
    assert re.search(r"http_status:\s*err\.http_status", src), "must emit http_status"


def test_frontend_no_more_generic_could_not_start_string():
    """The OLD bare 'Could not start trailer' fallback toast is gone — every
    failure now goes through the mapper."""
    src = _src()
    # The string still appears in a comment/docstring referencing the old
    # behaviour, so we strip JS line comments before searching.
    code_only = "\n".join(
        line for line in src.splitlines() if not line.strip().startswith("//")
    )
    # Block comment removal (simple — we don't need a perfect parser)
    code_only = re.sub(r"/\*.*?\*/", "", code_only, flags=re.S)
    assert "'Could not start trailer'" not in code_only, \
        "generic 'Could not start trailer' fallback must be removed"


def test_frontend_retry_button_in_error_panel():
    src = _src()
    assert 'data-testid="trailer-start-error-retry"' in src
    # And it's gated to err.retryable
    assert "startError.retryable" in src


def test_frontend_cta_button_in_error_panel():
    src = _src()
    assert 'data-testid="trailer-start-error-cta"' in src
    # Buy credits + See plans + Sign in routes are wired
    assert "/app/billing" in src
    assert "/app/pricing" in src


def test_frontend_clears_error_on_retry():
    """When the user clicks Generate (or Retry) the panel must clear so they
    don't stare at a stale red box during the next attempt."""
    src = _src()
    assert "setStartError(null)" in src, \
        "onGenerate must clear startError at the top of each attempt"
