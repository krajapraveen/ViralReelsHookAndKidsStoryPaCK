"""
Resume-Draft contract — 2026-05-16 P0 (Stability Sprint Session 0)

Locks in the user-mandated behaviour:

  "Start Fresh":
    • Soft-archives the old draft (status → archived, archived_at stamped)
    • Old draft + ALL attached assets remain in the DB (recoverable)
    • A new clean draft is created with a fresh draft_id
    • Frontend resets state + cancels in-flight requests + navigates

  "Continue":
    • Fetch canonical state via GET /drafts/{draft_id} ONLY
    • Backend validates ownership + schema version
    • On failure, return structured envelope with request_id so the
      recovery UX has a debuggable reference
    • Frontend navigates with ?restore=true to flag a hydration session
"""
import os
import uuid
import pytest
import pytest_asyncio
import httpx
from pathlib import Path
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
    db = cli[os.environ["DB_NAME"]]
    yield db
    cli.close()


# ═════════════════════════════════════════════════════════════════════
# End-to-end: archive + create + hydrate cycle
# ═════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_start_fresh_cycle_archives_old_and_creates_new(admin_token, mongo):
    """The canonical Start Fresh flow:
       1. user has an active draft (from /save autosave)
       2. POST /archive → status flips to "archived", archived_at stamped
       3. POST /create → new draft_id, status="draft", schema_version=1
       4. Old draft DOC still exists with all fields (assets preserved)
       5. Hydration via GET /{old_draft_id} still works (admin recovery)
    """
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Clean slate — archive any drafts from prior runs
        await cli.post("/api/drafts/archive", headers=headers)

        # 1. Auto-save establishes an active draft (legacy entry point)
        save = await cli.post(
            "/api/drafts/save",
            headers=headers,
            json={"title": "Pre-fresh title", "story_text": "Lorem ipsum dolor sit amet."},
        )
        assert save.status_code == 200
        cur = (await cli.get("/api/drafts/current", headers=headers)).json()
        old_id = cur["draft"]["draft_id"]
        assert old_id, "Saved draft must carry a draft_id"
        assert cur["draft"]["schema_version"] == 1
        # Optional sanity: assets-shaped placeholder field would live on the
        # same doc; we don't add one here because no upload happened, but the
        # contract is "the document is preserved untouched".

        # 2. ARCHIVE — soft transition
        arch = await cli.post("/api/drafts/archive", headers=headers)
        assert arch.status_code == 200
        body = arch.json()
        assert body["success"] is True
        assert body["archived_draft_id"] == old_id
        assert isinstance(body["request_id"], str) and len(body["request_id"]) >= 8

        # 3. Old doc still exists, with status=archived (NOT deleted)
        old_doc = await mongo.story_drafts.find_one({"draft_id": old_id})
        assert old_doc is not None, "Old draft must be preserved, never deleted"
        assert old_doc["status"] == "archived"
        assert "archived_at" in old_doc
        assert old_doc["title"] == "Pre-fresh title"
        assert old_doc["story_text"] == "Lorem ipsum dolor sit amet."

        # 4. CREATE — new blank draft
        crt = await cli.post("/api/drafts/create", headers=headers)
        assert crt.status_code == 200
        new_body = crt.json()
        new_id = new_body["draft_id"]
        assert new_id and new_id != old_id
        assert new_body["schema_version"] == 1
        assert isinstance(new_body["request_id"], str)

        # 5. The new draft is the canonical "current" one (and is blank)
        cur2 = (await cli.get("/api/drafts/current", headers=headers)).json()
        # No content yet, /current returns null when title+story_text empty
        assert cur2["draft"] is None

        # 6. Old draft still hydratable by id (admin / undo-fresh)
        hydrate_old = await cli.get(f"/api/drafts/{old_id}", headers=headers)
        assert hydrate_old.status_code == 200
        hpay = hydrate_old.json()
        assert hpay["success"] is True
        assert hpay["is_archived"] is True
        assert hpay["draft"]["title"] == "Pre-fresh title"

        # Cleanup
        await mongo.story_drafts.delete_many({"draft_id": {"$in": [old_id, new_id]}})


@pytest.mark.asyncio
async def test_create_refuses_when_active_draft_exists(admin_token, mongo):
    """The /create endpoint must refuse with a structured DRAFT_ALREADY_ACTIVE
    envelope when the user has an unarchived draft. Caller must archive first."""
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        headers = {"Authorization": f"Bearer {admin_token}"}
        await cli.post("/api/drafts/archive", headers=headers)
        # Seed an active draft via /save
        await cli.post(
            "/api/drafts/save",
            headers=headers,
            json={"title": "Active", "story_text": "Already-active draft."},
        )
        r = await cli.post("/api/drafts/create", headers=headers)
        assert r.status_code == 409
        detail = r.json()["detail"]
        assert detail["code"] == "DRAFT_ALREADY_ACTIVE"
        assert detail["active_draft_id"]
        assert detail["request_id"]
        # Cleanup
        await cli.post("/api/drafts/archive", headers=headers)


@pytest.mark.asyncio
async def test_archive_is_idempotent_with_no_active_draft(admin_token):
    """Calling /archive when no active draft exists must succeed (idempotent)."""
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        headers = {"Authorization": f"Bearer {admin_token}"}
        await cli.post("/api/drafts/archive", headers=headers)
        # Second call — already no active draft
        r = await cli.post("/api/drafts/archive", headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert body["archived_draft_id"] is None


# ═════════════════════════════════════════════════════════════════════
# GET /drafts/{draft_id} — canonical hydration
# ═════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_hydrate_returns_404_for_unknown_id(admin_token):
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        headers = {"Authorization": f"Bearer {admin_token}"}
        bogus = uuid.uuid4().hex
        r = await cli.get(f"/api/drafts/{bogus}", headers=headers)
        assert r.status_code == 404
        detail = r.json()["detail"]
        assert detail["code"] == "DRAFT_NOT_FOUND"
        assert detail["request_id"]


@pytest.mark.asyncio
async def test_hydrate_respects_ownership(admin_token, mongo):
    """Another user's draft MUST appear as 404 (never leak existence)."""
    other_user_draft_id = f"foreign-{uuid.uuid4().hex}"
    await mongo.story_drafts.insert_one({
        "user_id": "some-other-user",
        "draft_id": other_user_draft_id,
        "status": "draft",
        "schema_version": 1,
        "title": "Foreign draft",
        "story_text": "Should be invisible to admin",
    })
    try:
        async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
            r = await cli.get(
                f"/api/drafts/{other_user_draft_id}",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert r.status_code == 404
    finally:
        await mongo.story_drafts.delete_one({"draft_id": other_user_draft_id})


@pytest.mark.asyncio
async def test_hydrate_rejects_unsupported_schema_version(admin_token, mongo):
    """Future schema_version → structured envelope with recovery copy."""
    admin_id = (await mongo.users.find_one({"email": "admin@creatorstudio.ai"}, {"_id": 0, "id": 1}))["id"]
    future_draft_id = f"future-{uuid.uuid4().hex}"
    await mongo.story_drafts.insert_one({
        "user_id": admin_id,
        "draft_id": future_draft_id,
        "status": "archived",     # archived so it doesn't conflict with unique index
        "schema_version": 99,     # from the future
        "title": "v99",
        "story_text": "x",
    })
    try:
        async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
            r = await cli.get(
                f"/api/drafts/{future_draft_id}",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert r.status_code == 409
            detail = r.json()["detail"]
            assert detail["code"] == "DRAFT_SCHEMA_UNSUPPORTED"
            assert detail["schema_version"] == 99
            assert detail["supported_version"] == 1
            # Recovery copy exactly per spec
            assert detail["message"] == \
                "We found an issue restoring this draft. Recover safe content or start fresh."
            assert detail["request_id"]
    finally:
        await mongo.story_drafts.delete_one({"draft_id": future_draft_id})


# ═════════════════════════════════════════════════════════════════════
# Legacy /discard now archives (assets preserved)
# ═════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_legacy_discard_now_archives_not_deletes(admin_token, mongo):
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        headers = {"Authorization": f"Bearer {admin_token}"}
        await cli.post("/api/drafts/archive", headers=headers)
        await cli.post(
            "/api/drafts/save",
            headers=headers,
            json={"title": "DiscardTest", "story_text": "Test discard preservation"},
        )
        cur = (await cli.get("/api/drafts/current", headers=headers)).json()
        draft_id = cur["draft"]["draft_id"]

        # LEGACY discard
        r = await cli.delete("/api/drafts/discard", headers=headers)
        assert r.status_code == 200
        assert r.json()["archived"] >= 1

        # Document must STILL exist (status=archived, not deleted)
        doc = await mongo.story_drafts.find_one({"draft_id": draft_id})
        assert doc is not None, "Legacy /discard must not hard-delete under the new contract"
        assert doc["status"] == "archived"
        await mongo.story_drafts.delete_one({"draft_id": draft_id})


# ═════════════════════════════════════════════════════════════════════
# Source-level: frontend Start Fresh + Continue contracts
# ═════════════════════════════════════════════════════════════════════
SVP_JS = Path("/app/frontend/src/pages/StoryVideoPipeline.js")


def test_frontend_start_fresh_calls_archive_then_create():
    src = SVP_JS.read_text(encoding="utf-8")
    # Locate the new handleDiscardDraft (Start Fresh) function
    idx = src.find("const handleDiscardDraft = async ()")
    assert idx > 0, "handleDiscardDraft must be async under the new contract"
    body = src[idx:idx + 2200]
    # Must call BOTH endpoints in order: archive → create
    pos_archive = body.find("/api/drafts/archive")
    pos_create = body.find("/api/drafts/create")
    assert pos_archive > 0 and pos_create > 0
    assert pos_archive < pos_create, \
        "Start Fresh must archive BEFORE create (unique-index constraint)"
    # Must cancel autosave timer
    assert "clearTimeout(draftSaveTimer.current)" in body
    assert "draftSaveTimer.current = null" in body
    # Must hard-reset editor state
    for setter in ("setTitle('')", "setStoryText('')", "setAnimStyle('cartoon_2d')",
                   "setAgeGroup('kids_5_8')", "setVoicePreset('narrator_warm')",
                   "setPendingDraft(null)"):
        assert setter in body, f"Start Fresh missing reset: {setter}"
    # lastSavedRef cleared so the next autosave compare resets cleanly
    assert "lastSavedRef.current = { title: '', storyText: '' };" in body
    # activeDraftId updated from the new draft
    assert "setActiveDraftId(newDraftId)" in body
    # Navigate (replace history) with the new draft_id
    assert "navigate(newDraftId ? `${base}?draft_id=${newDraftId}` : base" in body


def test_frontend_continue_hydrates_from_canonical_backend_only():
    src = SVP_JS.read_text(encoding="utf-8")
    idx = src.find("const handleResumeDraft = async ()")
    assert idx > 0, "handleResumeDraft must be async under the new contract"
    body = src[idx:idx + 2500]
    # Must fetch by id (canonical) — NOT use the mount-time pendingDraft snapshot directly
    assert "api.get(`/api/drafts/${draftId}`)" in body, \
        "Continue must refetch from the canonical /drafts/{id} endpoint"
    # Legacy fallback for drafts without draft_id is via /current (acceptable)
    assert "/api/drafts/current" in body
    # MUST NOT touch localStorage / cache in the hydration path
    assert "localStorage" not in body, \
        "Continue must NOT merge localStorage under the canonical-hydration rule"
    # Sets ?restore=true on the URL after successful hydration
    assert "params.set('restore', 'true')" in body
    # Recovery UX on failure surfaces request_id
    assert "Reference ID: ${requestId}" in body or "Reference ID: ${detail" in body or \
           "request_id" in body, "Recovery UX must surface request_id"


def test_frontend_does_not_hard_delete_on_start_fresh():
    """Belt-and-braces: the new contract is archive, NOT delete."""
    src = SVP_JS.read_text(encoding="utf-8")
    idx = src.find("const handleDiscardDraft = async ()")
    body = src[idx:idx + 2200]
    # No DELETE call inside Start Fresh anymore
    assert "api.delete('/api/drafts/discard')" not in body
    assert ".delete(" not in body, "Start Fresh must not issue DELETE under the new contract"


def test_frontend_continue_sets_active_draft_id_on_success():
    src = SVP_JS.read_text(encoding="utf-8")
    idx = src.find("const handleResumeDraft = async ()")
    body = src[idx:idx + 2500]
    assert "setActiveDraftId(fresh.draft_id)" in body
