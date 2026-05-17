"""
P0 2026-05-19 CASE B — Comic Story Book download entitlement parity.
====================================================================
Production CASE B screenshot:
  User: 159 credits, Comic Story Book COMPLETED, real "Download Comic
        Book" button visible (green).
  Click: routed to upgrade/paywall logic instead of downloading.

ROOT CAUSE — split-brain entitlement
------------------------------------
- RENDER path used `job.entitlement?.can_download` (NEW per-job block
  returned by GET /job/{id}) — correctly showed the green button.
- CLICK path in `handleDownload` (ComicStorybookBuilder.js:968) used
  the LEGACY heuristic: `userPlan === 'free' && !job.purchased &&
  !isUnlimitedUser`. A user whose `userPlan` cache was stale, or
  whose plan-detection sync lagged, would pass the render check but
  fail the click check → upsell modal.

The two gates disagreed. The user's diagnosis is exact: "UI rendering
fix landed, but the ACTUAL download action path is still gated
incorrectly."

LOCKED-IN CONTRACT
------------------
1. Frontend click handler reads `job.entitlement.can_download` first
   and ONLY falls back to the legacy heuristic if the entitlement
   block is missing (very old / pre-deploy cached jobs).
2. Frontend emits `[storybook/download] click` with both the new
   entitlement reading and the legacy signal block so future
   split-brain is visible in 1 console line.
3. Backend `/download/{job_id}` now does its OWN authoritative
   entitlement re-check (mirror of GET /job/{id}'s entitlement block
   logic), returns structured envelopes on every failure path
   (`JOB_NOT_FOUND`, `JOB_NOT_READY`, `ASSETS_NOT_REGISTERED`,
   `DOWNLOAD_FORBIDDEN`, `ASSETS_MISSING`), and echoes the
   authoritative entitlement back in the success response for
   client-side parity checks.
4. Frontend catch path surfaces the REAL backend reason + Reference
   ID — never silently redirects to upsell.
"""
from __future__ import annotations

import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, "/app/backend")


BUILDER_JS = Path("/app/frontend/src/pages/ComicStorybookBuilder.js")
ROUTE_PY = Path("/app/backend/routes/comic_storybook_v2.py")


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


@pytest_asyncio.fixture
async def db():
    mongo, dbn = _backend_env()
    client = AsyncIOMotorClient(mongo)
    yield client[dbn]
    client.close()


@pytest_asyncio.fixture
async def admin_session():
    """Admin login → (token, user_id). Admin user is unlimited."""
    async with httpx.AsyncClient(base_url=_api_base(), timeout=20.0) as cli:
        r = await cli.post(
            "/api/auth/login",
            json={"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"},
        )
        assert r.status_code == 200, r.text
        d = r.json()
        token = d.get("access_token") or d.get("token")
        uid = (d.get("user") or {}).get("id")
        yield token, uid


# ════════════════════════════════════════════════════════════════════════
# Frontend source — click handler now reads the new entitlement block
# ════════════════════════════════════════════════════════════════════════
def test_click_handler_uses_per_job_entitlement_block():
    src = BUILDER_JS.read_text()
    handler = src.split("const handleDownload = async", 1)[1].split(
        "// Navigation", 1
    )[0]
    # Must consult job.entitlement.can_download FIRST.
    assert "job.entitlement" in handler, (
        "Click handler must consult the per-job entitlement block — "
        "this is what fixes the split-brain"
    )
    assert "job.entitlement.can_download === true" in handler, (
        "Strict-equality check on can_download must be present"
    )
    # Legacy heuristic is now ONLY a fallback when the block is missing.
    assert "isUnlimitedUser || userPlan !== 'free'" in handler, (
        "Legacy heuristic must remain as a graceful fallback for old "
        "cached job documents without an entitlement block"
    )


def test_click_handler_emits_structured_forensic_log():
    """The next split-brain must be visible in 1 console line."""
    src = BUILDER_JS.read_text()
    handler = src.split("const handleDownload = async", 1)[1].split(
        "// Navigation", 1
    )[0]
    assert "[storybook/download] click" in handler, (
        "Forensic log must be greppable"
    )
    # Must include both the new entitlement reading and the legacy
    # signal block so split-brain is immediately visible.
    for f in ("render_entitlement", "legacy_signals", "endpoint",
              "can_download", "reason", "plan_type", "is_unlimited"):
        assert f in handler, f"Forensic log missing field {f!r}"


def test_click_handler_surfaces_real_backend_reason_on_failure():
    """Frontend must NEVER silently swallow a backend failure into the
    upsell modal — it must show the real reason + Reference ID."""
    src = BUILDER_JS.read_text()
    handler = src.split("const handleDownload = async", 1)[1].split(
        "// Navigation", 1
    )[0]
    # Structured error envelope handling.
    assert "DOWNLOAD_FORBIDDEN" in handler, (
        "Click handler must recognise the DOWNLOAD_FORBIDDEN structured "
        "envelope so it surfaces the real reason"
    )
    assert "ENTITLEMENT_MISMATCH" in handler, (
        "Click handler must recognise the ENTITLEMENT_MISMATCH code"
    )
    # Reference ID rendering on every catch branch.
    assert "Reference ID:" in handler
    # No more silent setShowUpsell on catch.
    catch_block = handler.split("} catch (e) {", 1)[1]
    assert "setShowUpsell" not in catch_block, (
        "Catch path must NOT silently redirect to upsell — that's the "
        "exact production trap we're fixing"
    )


def test_legacy_silent_upsell_redirect_in_catch_is_gone():
    """The legacy 1-line `toast.error(e.response?.data?.detail || ...)`
    must be replaced by structured handling that distinguishes
    entitlement failures from generic failures."""
    src = BUILDER_JS.read_text()
    handler = src.split("const handleDownload = async", 1)[1].split(
        "// Navigation", 1
    )[0]
    assert "toast.error(e.response?.data?.detail || 'Download failed')" not in handler, (
        "Legacy 1-line generic error handler must be removed — replaced "
        "with structured envelope handling that surfaces the real reason"
    )


# ════════════════════════════════════════════════════════════════════════
# Backend source — authoritative re-check is in place
# ════════════════════════════════════════════════════════════════════════
def test_download_route_has_authoritative_entitlement_check():
    src = ROUTE_PY.read_text()
    route = src.split('@router.post("/download/{job_id}")', 1)[1].split(
        "\n@router.", 1
    )[0]
    # Must take Request for request_id plumbing.
    assert "http_request: Request" in route, (
        "Download route must accept Request so request_id can be plumbed"
    )
    # Authoritative re-check.
    assert "is_unlimited_user" in route, (
        "Download route must use the canonical is_unlimited_user helper"
    )
    assert "can_download = owns_job and" in route, (
        "Download route must compute can_download from authoritative "
        "signals, mirroring the per-job entitlement block in /job/{id}"
    )


def test_download_route_uses_structured_envelopes_for_every_error():
    src = ROUTE_PY.read_text()
    route = src.split('@router.post("/download/{job_id}")', 1)[1].split(
        "\n@router.", 1
    )[0]
    # Every error code in the founder spec must be emittable from this route.
    for code in ("JOB_NOT_FOUND", "JOB_NOT_READY", "ASSETS_NOT_REGISTERED",
                 "DOWNLOAD_FORBIDDEN", "ASSETS_MISSING"):
        assert f'"{code}"' in route, f"Missing structured envelope code: {code}"
    # All envelopes must carry request_id.
    rid_count = route.count('"request_id": rid')
    assert rid_count >= 5, (
        f"Expected ≥5 request_id placements in download route envelopes; "
        f"found {rid_count}"
    )
    # Legacy bare-string details must be GONE.
    assert 'detail="Job not found"' not in route
    assert 'detail="Book not ready yet"' not in route


def test_download_route_emits_structured_forensic_log():
    src = ROUTE_PY.read_text()
    route = src.split('@router.post("/download/{job_id}")', 1)[1].split(
        "\n@router.", 1
    )[0]
    assert "[storybook/download] check" in route, (
        "Backend forensic log must be greppable"
    )


def test_download_success_response_echoes_entitlement_for_parity():
    src = ROUTE_PY.read_text()
    route = src.split('@router.post("/download/{job_id}")', 1)[1].split(
        "\n@router.", 1
    )[0]
    # Success response must echo the authoritative entitlement so the
    # client can detect any future split-brain by comparing the
    # echoed value with what it rendered.
    success_block = route.split("return {", 1)[1].split("}", 1)[0]
    assert "entitlement" in success_block, (
        "Download success response must echo the authoritative "
        "entitlement for client-side parity checks"
    )


# ════════════════════════════════════════════════════════════════════════
# Live HTTP — admin/unlimited user can download a completed job
# ════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_admin_unlimited_user_can_download_completed_paid_job(db, admin_session):
    """The exact production scenario inverted: admin user (unlimited) +
    completed job + cost paid via credits → download endpoint must
    return success with downloadUrls + entitlement echo."""
    token, user_id = admin_session
    job_id = str(uuid.uuid4())
    await db.comic_storybook_v2_jobs.insert_one({
        "id": job_id,
        "userId": user_id,
        "type": "COMIC_STORYBOOK",
        "status": "COMPLETED",
        "progress": 100,
        "permanent": True,
        "pdfUrl": "https://example.com/comic.pdf",
        "coverUrl": "https://example.com/cover.png",
        "cost": 60,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    })
    try:
        async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
            r = await cli.post(
                f"/api/comic-storybook-v2/download/{job_id}",
                headers={"Authorization": f"Bearer {token}"},
                json={"type": "pdf"},
            )
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["success"] is True
            assert body.get("downloadUrls"), "downloadUrls must be present"
            assert body.get("request_id"), "request_id must be present"
            # Authoritative entitlement echo for parity checks.
            ent = body.get("entitlement")
            assert ent and ent.get("can_download") is True, (
                "Success response must echo authoritative entitlement"
            )
            # Admin is unlimited so reason should reflect that.
            assert ent["reason"] == "unlimited"
    finally:
        await db.comic_storybook_v2_jobs.delete_one({"id": job_id})


@pytest.mark.asyncio
async def test_download_route_returns_structured_404_envelope(db, admin_session):
    token, _ = admin_session
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        r = await cli.post(
            "/api/comic-storybook-v2/download/__no_such_job__",
            headers={"Authorization": f"Bearer {token}"},
            json={"type": "pdf"},
        )
        assert r.status_code == 404
        d = r.json()["detail"]
        assert isinstance(d, dict)
        assert d["code"] == "JOB_NOT_FOUND"
        assert d["request_id"]


@pytest.mark.asyncio
async def test_download_route_returns_structured_not_ready_envelope(db, admin_session):
    token, user_id = admin_session
    job_id = str(uuid.uuid4())
    await db.comic_storybook_v2_jobs.insert_one({
        "id": job_id,
        "userId": user_id,
        "type": "COMIC_STORYBOOK",
        "status": "PROCESSING",  # not yet COMPLETED
        "progress": 50,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    })
    try:
        async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
            r = await cli.post(
                f"/api/comic-storybook-v2/download/{job_id}",
                headers={"Authorization": f"Bearer {token}"},
                json={"type": "pdf"},
            )
            assert r.status_code == 400
            d = r.json()["detail"]
            assert d["code"] == "JOB_NOT_READY"
            assert d["current_status"] == "PROCESSING"
            assert d["request_id"]
            assert d["retryable"] is True
    finally:
        await db.comic_storybook_v2_jobs.delete_one({"id": job_id})


@pytest.mark.asyncio
async def test_download_route_returns_assets_not_registered_envelope(db, admin_session):
    token, user_id = admin_session
    job_id = str(uuid.uuid4())
    await db.comic_storybook_v2_jobs.insert_one({
        "id": job_id,
        "userId": user_id,
        "type": "COMIC_STORYBOOK",
        "status": "COMPLETED",
        "progress": 100,
        # Missing `permanent: True` — the asset registration step never ran.
        "pdfUrl": "https://example.com/comic.pdf",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    })
    try:
        async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
            r = await cli.post(
                f"/api/comic-storybook-v2/download/{job_id}",
                headers={"Authorization": f"Bearer {token}"},
                json={"type": "pdf"},
            )
            assert r.status_code == 400
            d = r.json()["detail"]
            assert d["code"] == "ASSETS_NOT_REGISTERED"
            assert d["request_id"]
            assert d["retryable"] is True
    finally:
        await db.comic_storybook_v2_jobs.delete_one({"id": job_id})


@pytest.mark.asyncio
async def test_render_and_click_entitlement_block_match(db, admin_session):
    """Parity invariant: the entitlement block on GET /job/{id} (render
    path) must produce the SAME can_download as the entitlement check
    on POST /download/{id} (click path). Drift between these two is
    EXACTLY the bug we're fixing."""
    token, user_id = admin_session
    job_id = str(uuid.uuid4())
    await db.comic_storybook_v2_jobs.insert_one({
        "id": job_id,
        "userId": user_id,
        "type": "COMIC_STORYBOOK",
        "status": "COMPLETED",
        "progress": 100,
        "permanent": True,
        "pdfUrl": "https://example.com/comic.pdf",
        "coverUrl": "https://example.com/cover.png",
        "cost": 60,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    })
    try:
        async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
            # RENDER path — the entitlement block the UI uses for the button.
            r1 = await cli.get(
                f"/api/comic-storybook-v2/job/{job_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r1.status_code == 200
            render_ent = r1.json()["entitlement"]

            # CLICK path — the authoritative entitlement re-check.
            r2 = await cli.post(
                f"/api/comic-storybook-v2/download/{job_id}",
                headers={"Authorization": f"Bearer {token}"},
                json={"type": "pdf"},
            )
            assert r2.status_code == 200
            click_ent = r2.json()["entitlement"]

            # PARITY INVARIANT.
            assert render_ent["can_download"] == click_ent["can_download"], (
                f"Split-brain detected — render says can_download="
                f"{render_ent['can_download']} but click says can_download="
                f"{click_ent['can_download']}. This is EXACTLY the production "
                "bug."
            )
            assert render_ent["reason"] == click_ent["reason"], (
                f"Reason mismatch — render={render_ent['reason']!r} "
                f"click={click_ent['reason']!r}"
            )
    finally:
        await db.comic_storybook_v2_jobs.delete_one({"id": job_id})
