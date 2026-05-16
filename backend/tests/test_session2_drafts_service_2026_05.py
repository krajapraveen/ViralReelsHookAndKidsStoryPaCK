"""
Session 2 — Service + Route integration tests
==============================================
Verifies the new canonical endpoints:
  GET    /api/drafts/{draft_id}/state
  POST   /api/drafts/{draft_id}/patch
  POST   /api/drafts/{draft_id}/transition
  POST   /api/drafts/session

Locks in:
  • optimistic locking (STALE_WRITE on version mismatch)
  • illegal-transition envelope shape (code/message/request_id/retryable/allowed_next)
  • ownership leak protection (foreign drafts → 404 DRAFT_NOT_FOUND)
  • deterministic hydration (state read returns version + lifecycle + allowed_next)
  • request_id present on EVERY response (success + error)
  • Legacy /save → /current keeps working alongside new endpoints
"""
from __future__ import annotations

import os
import uuid

import httpx
import pytest
import pytest_asyncio
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


@pytest_asyncio.fixture
async def admin_token():
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        r = await cli.post(
            "/api/auth/login",
            json={"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"},
        )
        assert r.status_code == 200, r.text
        yield r.json().get("access_token") or r.json().get("token")


@pytest_asyncio.fixture
async def mongo():
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    yield cli[os.environ["DB_NAME"]]
    cli.close()


@pytest_asyncio.fixture
async def clean_slate(admin_token, mongo):
    """Hard-clean: delete any non-archived drafts for the admin user before
    AND after each test. Tests in this suite intentionally drive drafts into
    GENERATING (which legacy /archive cannot reach), so we need direct DB
    cleanup for full isolation."""
    user = await mongo.users.find_one(
        {"email": "admin@creatorstudio.ai"}, {"_id": 0, "id": 1}
    )
    uid = user["id"]
    await mongo.story_drafts.delete_many(
        {"user_id": uid, "status": {"$in": ["draft", "processing"]}}
    )
    yield
    await mongo.story_drafts.delete_many(
        {"user_id": uid, "status": {"$in": ["draft", "processing"]}}
    )


# ═══════════════════════════════════════════════════════════════════
# Hydration
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_get_state_returns_404_with_request_id_for_unknown(admin_token, clean_slate):
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        r = await cli.get(
            f"/api/drafts/{uuid.uuid4().hex}/state",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 404
        detail = r.json()["detail"]
        assert detail["code"] == "DRAFT_NOT_FOUND"
        assert detail["request_id"]
        # And the response itself carries X-Request-Id
        assert r.headers.get("X-Request-Id")


@pytest.mark.asyncio
async def test_create_session_returns_canonical_state_shape(admin_token, clean_slate):
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        r = await cli.post(
            "/api/drafts/session",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        state = body["state"]
        # Canonical shape
        for f in ("draft_id", "version", "lifecycle", "legacy_status", "allowed_next",
                  "title", "story_text", "created_at", "updated_at"):
            assert f in state, f"missing canonical field {f}"
        assert state["version"] == 0
        assert state["lifecycle"] == "IDLE"
        assert state["legacy_status"] == "draft"
        assert isinstance(state["allowed_next"], list)
        assert "EDITING" in state["allowed_next"]
        assert body["request_id"]


@pytest.mark.asyncio
async def test_create_session_rejects_when_active_draft_exists(admin_token, clean_slate):
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        h = {"Authorization": f"Bearer {admin_token}"}
        # Seed an active draft via legacy /save
        await cli.post(
            "/api/drafts/save", headers=h,
            json={"title": "Existing", "story_text": "x"},
        )
        r = await cli.post("/api/drafts/session", headers=h)
        assert r.status_code == 409
        detail = r.json()["detail"]
        assert detail["code"] == "DRAFT_ALREADY_ACTIVE"
        assert detail["active_draft_id"]
        assert detail["request_id"]


# ═══════════════════════════════════════════════════════════════════
# Patch — optimistic locking + stale write rejection
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_patch_happy_path_bumps_version(admin_token, clean_slate):
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        h = {"Authorization": f"Bearer {admin_token}"}
        s0 = (await cli.post("/api/drafts/session", headers=h)).json()["state"]
        draft_id = s0["draft_id"]

        r = await cli.post(
            f"/api/drafts/{draft_id}/patch",
            headers=h,
            json={
                "expected_version": 0,
                "patch": {"title": "Hello"},
                "next_lifecycle": "EDITING",
            },
        )
        assert r.status_code == 200, r.text
        s1 = r.json()["state"]
        assert s1["version"] == 1
        assert s1["lifecycle"] == "EDITING"
        assert s1["title"] == "Hello"


@pytest.mark.asyncio
async def test_patch_rejects_stale_write_with_current_version(admin_token, clean_slate):
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        h = {"Authorization": f"Bearer {admin_token}"}
        s0 = (await cli.post("/api/drafts/session", headers=h)).json()["state"]
        draft_id = s0["draft_id"]

        # First writer advances version to 1
        await cli.post(
            f"/api/drafts/{draft_id}/patch", headers=h,
            json={"expected_version": 0, "patch": {"title": "A"},
                  "next_lifecycle": "EDITING"},
        )

        # Second writer uses STALE expected_version 0 → must be rejected
        r = await cli.post(
            f"/api/drafts/{draft_id}/patch", headers=h,
            json={"expected_version": 0, "patch": {"title": "B"}},
        )
        assert r.status_code == 409
        detail = r.json()["detail"]
        assert detail["code"] == "STALE_WRITE"
        assert detail["retryable"] is True
        assert detail["current_version"] == 1
        assert detail["request_id"]


@pytest.mark.asyncio
async def test_patch_rejects_illegal_transition(admin_token, clean_slate):
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        h = {"Authorization": f"Bearer {admin_token}"}
        s0 = (await cli.post("/api/drafts/session", headers=h)).json()["state"]
        draft_id = s0["draft_id"]

        # IDLE → GENERATING is forbidden
        r = await cli.post(
            f"/api/drafts/{draft_id}/patch", headers=h,
            json={"expected_version": 0, "patch": {},
                  "next_lifecycle": "GENERATING"},
        )
        assert r.status_code == 409
        detail = r.json()["detail"]
        assert detail["code"] == "ILLEGAL_TRANSITION"
        assert detail["retryable"] is False
        assert detail["from"] == "IDLE"
        assert detail["to"] == "GENERATING"
        assert "allowed_next" in detail
        assert detail["request_id"]


@pytest.mark.asyncio
async def test_patch_rejects_empty_payload(admin_token, clean_slate):
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        h = {"Authorization": f"Bearer {admin_token}"}
        s0 = (await cli.post("/api/drafts/session", headers=h)).json()["state"]
        r = await cli.post(
            f"/api/drafts/{s0['draft_id']}/patch", headers=h,
            json={"expected_version": 0, "patch": {}},
        )
        assert r.status_code == 400
        detail = r.json()["detail"]
        assert detail["code"] == "INVALID_PATCH"


# ═══════════════════════════════════════════════════════════════════
# Transition — pure lifecycle moves
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_transition_to_generating_attaches_job_id(admin_token, clean_slate):
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        h = {"Authorization": f"Bearer {admin_token}"}
        s0 = (await cli.post("/api/drafts/session", headers=h)).json()["state"]
        draft_id = s0["draft_id"]

        # IDLE → EDITING → READY_TO_GENERATE → GENERATING
        s1 = (await cli.post(
            f"/api/drafts/{draft_id}/patch", headers=h,
            json={"expected_version": 0, "patch": {"title": "T"},
                  "next_lifecycle": "EDITING"},
        )).json()["state"]
        s2 = (await cli.post(
            f"/api/drafts/{draft_id}/transition", headers=h,
            json={"expected_version": s1["version"], "next_lifecycle": "READY_TO_GENERATE"},
        )).json()["state"]
        s3 = (await cli.post(
            f"/api/drafts/{draft_id}/transition", headers=h,
            json={"expected_version": s2["version"], "next_lifecycle": "GENERATING",
                  "attached_job_id": "job-xyz"},
        )).json()["state"]
        assert s3["lifecycle"] == "GENERATING"
        assert s3["attached_job_id"] == "job-xyz"
        assert s3["version"] == s2["version"] + 1


@pytest.mark.asyncio
async def test_transition_rejects_stale_write(admin_token, clean_slate):
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        h = {"Authorization": f"Bearer {admin_token}"}
        s0 = (await cli.post("/api/drafts/session", headers=h)).json()["state"]
        r = await cli.post(
            f"/api/drafts/{s0['draft_id']}/transition", headers=h,
            json={"expected_version": 99, "next_lifecycle": "EDITING"},
        )
        assert r.status_code == 409
        detail = r.json()["detail"]
        assert detail["code"] == "STALE_WRITE"


@pytest.mark.asyncio
async def test_transition_unknown_lifecycle_rejected(admin_token, clean_slate):
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        h = {"Authorization": f"Bearer {admin_token}"}
        s0 = (await cli.post("/api/drafts/session", headers=h)).json()["state"]
        r = await cli.post(
            f"/api/drafts/{s0['draft_id']}/transition", headers=h,
            json={"expected_version": 0, "next_lifecycle": "NOT_A_STATE"},
        )
        assert r.status_code == 400
        detail = r.json()["detail"]
        assert detail["code"] == "ILLEGAL_TRANSITION"
        assert "allowed" in detail


# ═══════════════════════════════════════════════════════════════════
# Ownership — foreign drafts must look like 404 (no existence leak)
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_ownership_isolation_foreign_draft_404(admin_token, mongo, clean_slate):
    foreign_id = f"foreign-session2-{uuid.uuid4().hex}"
    await mongo.story_drafts.insert_one({
        "user_id": "ghost-user",
        "draft_id": foreign_id,
        "status": "draft",
        "schema_version": 1,
        "version": 7,
        "lifecycle": "EDITING",
        "title": "secret",
        "story_text": "",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    })
    try:
        async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
            h = {"Authorization": f"Bearer {admin_token}"}
            r = await cli.get(f"/api/drafts/{foreign_id}/state", headers=h)
            assert r.status_code == 404
            # Same envelope shape as missing draft — never leak existence
            assert r.json()["detail"]["code"] == "DRAFT_NOT_FOUND"
            # Patch must also 404 (not 403, not 409)
            r2 = await cli.post(
                f"/api/drafts/{foreign_id}/patch", headers=h,
                json={"expected_version": 7, "patch": {"title": "boom"}},
            )
            assert r2.status_code == 404
            assert r2.json()["detail"]["code"] == "DRAFT_NOT_FOUND"
    finally:
        await mongo.story_drafts.delete_one({"draft_id": foreign_id})


# ═══════════════════════════════════════════════════════════════════
# Backward compat: legacy /save + /current still work
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_legacy_save_and_current_still_work_alongside_v2(admin_token, clean_slate):
    """Confirms Session 2 endpoints didn't regress the legacy contract."""
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        h = {"Authorization": f"Bearer {admin_token}"}
        await cli.post(
            "/api/drafts/save", headers=h,
            json={"title": "Compat", "story_text": "Legacy save."},
        )
        cur = (await cli.get("/api/drafts/current", headers=h)).json()
        assert cur["draft"]["title"] == "Compat"
        assert cur["draft"]["draft_id"]


# ═══════════════════════════════════════════════════════════════════
# Request-id correlation present on EVERY new endpoint
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_request_id_header_propagated(admin_token, clean_slate):
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        h = {"Authorization": f"Bearer {admin_token}", "X-Request-Id": "test-corr-id-12345"}
        s0 = (await cli.post("/api/drafts/session", headers=h)).json()
        assert s0["request_id"] == "test-corr-id-12345"


@pytest.mark.asyncio
async def test_request_id_generated_when_missing(admin_token, clean_slate):
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        h = {"Authorization": f"Bearer {admin_token}"}
        r = await cli.post("/api/drafts/session", headers=h)
        body = r.json()
        assert body["request_id"]
        assert r.headers.get("X-Request-Id") == body["request_id"]
