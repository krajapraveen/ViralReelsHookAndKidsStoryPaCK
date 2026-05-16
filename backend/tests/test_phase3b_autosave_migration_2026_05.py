"""
Phase 3b — Autosave migration to canonical version-locked writes
=================================================================
Locks in (founder spec, 2026-05-17):

  Hard requirements
  -----------------
   1. Autosave increments `version` (every accepted patch monotonically)
   2. Stale autosave returns `STALE_WRITE`
   3. Frontend recovery is non-destructive (local text NEVER wiped)
   4. Multi-tab overwrite protection (CAS at the service layer)
   5. Autosave failure surfaces request_id (for support correlation)
   6. No generation-worker changes (pipeline writes untouched)
   7. No Comic Storybook changes
   8. No UI redesign
   9. No Relationships card work
  10. No new feature surface (no new endpoints, no new pages)

  Behavior preservation
  ---------------------
  • 3-second debounce preserved inside the hook
  • Resume Draft modal contract intact (archive + create + canonical hydrate)
  • Phase 3a divergence logging still fires from inside the new autosave hook
"""
from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv("/app/backend/.env")


SVP_JS = Path("/app/frontend/src/pages/StoryVideoPipeline.js")
AUTOSAVE_JS = Path("/app/frontend/src/state/useStorySessionAutosave.js")
SHADOW_JS = Path("/app/frontend/src/state/useStorySessionShadow.js")


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


# ════════════════════════════════════════════════════════════════════════
# Frontend source-level: editor uses the canonical autosave hook
# ════════════════════════════════════════════════════════════════════════
def test_editor_wires_canonical_autosave_hook():
    src = SVP_JS.read_text(encoding="utf-8")
    assert "useStorySessionAutosave" in src
    assert "from '../state/useStorySessionAutosave'" in src
    needle = "useStorySessionAutosave({"
    assert src.count(needle) == 1, "Exactly one autosave mount expected"
    body = src.split(needle, 1)[1].split("});", 1)[0]
    # Required parameters
    for f in ("draftId: activeDraftId", "onDraftCreated", "fields", "title", "storyText"):
        assert f in body, f"Autosave mount missing param: {f}"


def test_editor_no_longer_calls_legacy_drafts_save():
    src = SVP_JS.read_text(encoding="utf-8")
    # Migration complete — legacy POST /api/drafts/save is gone from the editor.
    assert "api.post('/api/drafts/save'" not in src, \
        "Phase 3b: editor must no longer use legacy /drafts/save"


def test_editor_keeps_typing_started_instrumentation():
    """Funnel tracker contract preserved across migration."""
    src = SVP_JS.read_text(encoding="utf-8")
    assert "trackFunnel('typing_started'" in src


def test_editor_keeps_resume_draft_modal_contract():
    """The archive + create flow for Resume Draft must remain untouched.
    Phase 3b is autosave only — Start Fresh stays page-owned."""
    src = SVP_JS.read_text(encoding="utf-8")
    assert "api.post('/api/drafts/archive')" in src
    assert "api.post('/api/drafts/create')" in src
    assert 'data-testid="resume-draft-modal"' in src


def test_editor_keeps_status_endpoint_for_pipeline_signals():
    """No generation-worker changes — /drafts/status calls remain."""
    src = SVP_JS.read_text(encoding="utf-8")
    assert "api.post('/api/drafts/status'" in src


def test_editor_does_not_introduce_new_mutator_surface_outside_hook():
    """Editor must NOT call patch/transition/session directly. Those must
    go through the canonical hook."""
    src = SVP_JS.read_text(encoding="utf-8")
    # The hook calls /api/drafts/{id}/patch — but it lives in
    # useStorySessionAutosave.js, not in the editor. Assert the editor
    # itself doesn't reach for these strings.
    for forbidden in (
        "/patch'", "/patch`",
        "/transition'", "/transition`",
        "'/api/drafts/session'", "`/api/drafts/session`",
    ):
        assert forbidden not in src, \
            f"Editor must not call mutator directly: {forbidden}"


# ════════════════════════════════════════════════════════════════════════
# Hook self-contract: debounce, version-lock, recovery copy, shadow log
# ════════════════════════════════════════════════════════════════════════
def test_hook_preserves_3_second_debounce():
    src = AUTOSAVE_JS.read_text(encoding="utf-8")
    assert "AUTOSAVE_DEBOUNCE_MS = 3000" in src or "3000" in src
    assert "setTimeout" in src


def test_hook_uses_version_locked_patch():
    src = AUTOSAVE_JS.read_text(encoding="utf-8")
    assert "client.patchSession" in src
    assert "expectedVersion: versionRef.current" in src


def test_hook_creates_session_on_first_type():
    src = AUTOSAVE_JS.read_text(encoding="utf-8")
    assert "client.createSession" in src
    assert "onDraftCreated" in src


def test_hook_handles_stale_write_non_destructively():
    src = AUTOSAVE_JS.read_text(encoding="utf-8")
    # Refetches canonical on stale + KEEPS local text + retries on next tick
    assert "ErrorCode.STALE_WRITE" in src
    assert "client.fetchSessionState" in src
    # User-facing recovery copy must mention non-destructive preservation
    assert "your unsaved text is preserved" in src.lower() or \
           "unsaved text is preserved" in src


def test_hook_emits_request_id_on_failure():
    src = AUTOSAVE_JS.read_text(encoding="utf-8")
    assert "[story-session/autosave-failed]" in src
    assert "request_id=" in src


def test_hook_preserves_phase_3a_divergence_logging():
    """Phase 3a contract must remain active inside the new hook."""
    src = AUTOSAVE_JS.read_text(encoding="utf-8")
    assert "[story-session/divergence]" in src
    for f in ("title", "storyText", "animationStyle", "ageGroup", "voicePreset", "lifecycle"):
        assert f"'{f}'" in src, f"Divergence tracked-fields missing {f!r}"


def test_hook_only_uses_editing_lifecycle():
    """Phase 3b explicitly does NOT progress lifecycle beyond EDITING.
    READY_TO_GENERATE / GENERATING transitions are Phase 3c work."""
    src = AUTOSAVE_JS.read_text(encoding="utf-8")
    assert "Lifecycle.EDITING" in src
    # And NOT the forward-only lifecycles
    for forbidden in (
        "Lifecycle.GENERATING", "Lifecycle.READY", "Lifecycle.READY_TO_GENERATE",
        "Lifecycle.AUTOSAVING", "Lifecycle.FAILED", "Lifecycle.ARCHIVED",
    ):
        assert forbidden not in src, \
            f"Phase 3b must not write lifecycle {forbidden}"


def test_hook_does_not_call_transition_or_startfresh():
    src = AUTOSAVE_JS.read_text(encoding="utf-8")
    for forbidden in ("client.transitionSession", "api.transition", "api.startFresh"):
        assert forbidden not in src, \
            f"Phase 3b autosave must not call {forbidden}"


# ════════════════════════════════════════════════════════════════════════
# Backend integration: real version-locked autosave flow
# ════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_autosave_patch_increments_version_monotonically(admin_token, clean_slate):
    """Three consecutive autosave-like patches advance version 0→1→2→3."""
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        h = {"Authorization": f"Bearer {admin_token}"}
        s0 = (await cli.post("/api/drafts/session", headers=h)).json()["state"]
        did = s0["draft_id"]
        last_version = s0["version"]
        for n, text in enumerate(["one", "two", "three"], start=1):
            r = await cli.post(
                f"/api/drafts/{did}/patch", headers=h,
                json={
                    "expected_version": last_version,
                    "patch": {"story_text": text},
                    "next_lifecycle": "EDITING",
                },
            )
            assert r.status_code == 200, r.text
            st = r.json()["state"]
            assert st["version"] == last_version + 1
            assert st["lifecycle"] == "EDITING"
            last_version = st["version"]
        assert last_version == 3


@pytest.mark.asyncio
async def test_multi_tab_overwrite_protection(admin_token, clean_slate):
    """Tab A and Tab B both have the same draft loaded at version V.
    Tab A patches → version becomes V+1.
    Tab B's autosave fires with expected_version=V → STALE_WRITE.
    Tab B refetches, learns version=V+1, retries with V+1 → success.
    Final document carries Tab B's text (last legitimate writer wins
    AFTER refresh — exactly the non-destructive contract)."""
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        h = {"Authorization": f"Bearer {admin_token}"}
        s0 = (await cli.post("/api/drafts/session", headers=h)).json()["state"]
        did = s0["draft_id"]
        v0 = s0["version"]

        # Tab A writes first
        a = await cli.post(
            f"/api/drafts/{did}/patch", headers=h,
            json={"expected_version": v0, "patch": {"story_text": "from Tab A"},
                  "next_lifecycle": "EDITING"},
        )
        assert a.status_code == 200
        v1 = a.json()["state"]["version"]

        # Tab B is still on v0 — patch must be rejected as STALE_WRITE
        b_stale = await cli.post(
            f"/api/drafts/{did}/patch", headers=h,
            json={"expected_version": v0, "patch": {"story_text": "from Tab B"},
                  "next_lifecycle": "EDITING"},
        )
        assert b_stale.status_code == 409
        detail = b_stale.json()["detail"]
        assert detail["code"] == "STALE_WRITE"
        assert detail["retryable"] is True
        assert detail["current_version"] == v1
        assert detail["request_id"]

        # Tab B refetches (simulating the hook's recovery path)
        fresh = await cli.get(f"/api/drafts/{did}/state", headers=h)
        assert fresh.status_code == 200
        latest_v = fresh.json()["state"]["version"]
        assert latest_v == v1

        # Tab B replays with correct expected_version
        b_replay = await cli.post(
            f"/api/drafts/{did}/patch", headers=h,
            json={"expected_version": latest_v, "patch": {"story_text": "from Tab B"},
                  "next_lifecycle": "EDITING"},
        )
        assert b_replay.status_code == 200
        final = b_replay.json()["state"]
        assert final["story_text"] == "from Tab B"
        assert final["version"] == latest_v + 1


@pytest.mark.asyncio
async def test_stale_write_error_includes_request_id(admin_token, clean_slate):
    """Founder requirement #5 — every autosave failure carries a
    correlatable request_id."""
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        h = {"Authorization": f"Bearer {admin_token}"}
        s = (await cli.post("/api/drafts/session", headers=h)).json()["state"]
        did = s["draft_id"]
        # Force stale: expected_version=99 (we're at 0)
        r = await cli.post(
            f"/api/drafts/{did}/patch", headers=h,
            json={"expected_version": 99, "patch": {"title": "x"},
                  "next_lifecycle": "EDITING"},
        )
        assert r.status_code == 409
        detail = r.json()["detail"]
        assert detail["code"] == "STALE_WRITE"
        assert detail["request_id"], "Founder spec: autosave failure must carry request_id"
        # And the HTTP response header carries the same id (reliability middleware)
        assert r.headers.get("X-Request-Id") == detail["request_id"]


@pytest.mark.asyncio
async def test_concurrent_writes_only_one_wins(admin_token, clean_slate):
    """Two simultaneous patches at the same version: exactly one wins,
    the other gets STALE_WRITE. Validates the CAS at the service layer."""
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        h = {"Authorization": f"Bearer {admin_token}"}
        s = (await cli.post("/api/drafts/session", headers=h)).json()["state"]
        did = s["draft_id"]

        async def attempt(text):
            return await cli.post(
                f"/api/drafts/{did}/patch", headers=h,
                json={"expected_version": 0, "patch": {"story_text": text},
                      "next_lifecycle": "EDITING"},
            )

        r1, r2 = await asyncio.gather(attempt("A"), attempt("B"))
        status_codes = sorted([r1.status_code, r2.status_code])
        # Exactly one 200, one 409
        assert status_codes == [200, 409], f"Got {status_codes}"
        winner = r1 if r1.status_code == 200 else r2
        loser = r1 if r1.status_code == 409 else r2
        assert winner.json()["state"]["version"] == 1
        assert loser.json()["detail"]["code"] == "STALE_WRITE"
        assert loser.json()["detail"]["current_version"] == 1


# ════════════════════════════════════════════════════════════════════════
# Phase 3a contract preserved (shadow module still read-only)
# ════════════════════════════════════════════════════════════════════════
def test_phase_3a_shadow_module_still_read_only_for_future_consumers():
    """Even though the editor migrated off the shadow hook, the SHADOW
    module file itself must remain a read-only contract for any future
    observer (e.g., admin debug consoles)."""
    src = SHADOW_JS.read_text(encoding="utf-8")
    for forbidden in ("api.commit", "api.transition", "api.startFresh",
                       "client.patchSession", "client.transitionSession",
                       "client.createSession"):
        assert forbidden not in src, \
            f"Shadow module regressed: {forbidden}"


def test_no_new_endpoints_introduced_in_phase_3b():
    """Founder requirement #10 — no new feature surface. Backend routes/drafts.py
    must remain on the Session 2 API surface (no new POST/PUT/DELETE)."""
    src = Path("/app/backend/routes/drafts.py").read_text(encoding="utf-8")
    # The exhaustive list of endpoints expected on drafts.py as of Session 2.
    expected = {
        "/save", "/status", "/current", "/recent",
        "/archive", "/create", "/discard", "/idea",
        # Session 2 canonical
        "/{draft_id}/state", "/{draft_id}/patch", "/{draft_id}/transition",
        "/session", "/{draft_id}",
    }
    for path in expected:
        assert path in src, f"Expected endpoint missing: {path}"
    # No accidentally introduced new prefixes — count router decorators
    # to confirm we didn't sneak in extras.
    import re as _re
    decorators = _re.findall(r'@router\.(get|post|delete|patch|put)\(', src)
    # Session 2 baseline = 13 decorators (8 legacy + 5 new)
    assert len(decorators) == 13, \
        f"Phase 3b introduced new endpoints: {len(decorators)} decorators (expected 13)"
