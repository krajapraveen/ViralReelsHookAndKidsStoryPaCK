"""
P0 UX (2026-05-17) — Character Detail "How to attach this character to a series" help
====================================================================================
Locks in:

  Frontend source-level (CharacterDetail + CreateSeries):
    1. Help section renders on Character Detail with the required title
    2. All 7 user-facing steps present + role tags (Hero/Villain/Sidekick/
       Narrator/Mentor/Trickster)
    3. CTA "Create Series with this Character" routes to
       /app/story-series/create?character_id=<id>
    4. CTA "Open My Series" routes to /app/story-series
    5. CTA "Back to My Characters" routes to /app/characters
    6. Memory Timeline empty-state copy is user-friendly
    7. CreateSeries reads ?character_id query param and validates via
       GET /api/characters/{id}
    8. Invalid character_id surfaces a structured toast with Ref id

  Backend integration:
    9. Attach-to-series endpoint still works (no regression to existing
       POST /api/characters/attach-to-series/{series_id})
   10. Foreign character is rejected with a clear envelope
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv("/app/backend/.env")


CHARACTER_DETAIL = Path("/app/frontend/src/pages/CharacterDetail.js")
CREATE_SERIES = Path("/app/frontend/src/pages/CreateSeries.js")


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


# ════════════════════════════════════════════════════════════════════════
# Frontend source-level: help section + CTAs + empty-state copy
# ════════════════════════════════════════════════════════════════════════
def test_character_detail_help_section_renders():
    src = CHARACTER_DETAIL.read_text(encoding="utf-8")
    # Container with deterministic testid
    assert 'data-testid="character-attach-help"' in src
    # Required title verbatim per founder spec
    assert "How to attach this character to a series" in src


def test_help_section_lists_all_7_steps_with_role_tags():
    src = CHARACTER_DETAIL.read_text(encoding="utf-8")
    # All 7 steps (some keywords) MUST be present in the rendered ordered list
    needles = [
        "Open <span",                                # step 1 — Create Series from menu
        "Start a new series or open an existing",    # step 2
        "Use existing character",                    # step 3
        "Select this character from",                # step 4 — My Characters
        "Hero, Villain, Sidekick, Narrator, Mentor, or Trickster",  # step 5 roles
        "Generate <span",                            # step 6 — Episode 1
        "Memory Timeline will update",               # step 7 — after generation
    ]
    for needle in needles:
        assert needle in src, f"Help section missing required step content: {needle!r}"


def test_three_ctas_with_correct_routes_and_testids():
    src = CHARACTER_DETAIL.read_text(encoding="utf-8")
    # 1. Create Series with this Character
    assert "Create Series with this Character" in src
    assert 'data-testid="cta-create-series-with-character"' in src
    # Route MUST include character_id query param using the route variable.
    assert "/app/story-series/create?character_id=" in src
    assert "encodeURIComponent(characterId)" in src
    # 2. Open My Series
    assert "Open My Series" in src
    assert 'data-testid="cta-open-my-series"' in src
    assert "navigate('/app/story-series')" in src
    # 3. Back to My Characters
    assert "Back to My Characters" in src
    assert 'data-testid="cta-back-to-my-characters"' in src
    assert "navigate('/app/characters')" in src


def test_memory_timeline_empty_state_copy_is_friendly():
    src = CHARACTER_DETAIL.read_text(encoding="utf-8")
    assert 'data-testid="memory-timeline-empty"' in src
    # The new friendly copy
    assert "Memories appear after this character is used in generated series episodes." in src
    # And the abrupt old copy is GONE
    assert "No memories yet. Attach this character to a series and generate episodes to build memory." not in src


def test_help_section_is_mobile_responsive_grid():
    src = CHARACTER_DETAIL.read_text(encoding="utf-8")
    # The CTA grid switches from 1 to 3 columns at sm breakpoint
    assert "grid-cols-1 sm:grid-cols-3" in src


# ════════════════════════════════════════════════════════════════════════
# CreateSeries: reads ?character_id, validates, shows banner, auto-attaches
# ════════════════════════════════════════════════════════════════════════
def test_create_series_reads_character_id_query_param():
    src = CREATE_SERIES.read_text(encoding="utf-8")
    assert "useSearchParams" in src
    assert "searchParams.get('character_id')" in src


def test_create_series_validates_preselected_character():
    src = CREATE_SERIES.read_text(encoding="utf-8")
    # Validation hits the canonical character endpoint
    assert "api.get(`/api/characters/${preselectedCharacterId}`)" in src


def test_create_series_shows_preselected_banner():
    src = CREATE_SERIES.read_text(encoding="utf-8")
    assert 'data-testid="preselected-character-banner"' in src
    assert 'data-testid="preselected-character-name"' in src
    assert 'data-testid="preselected-character-clear"' in src


def test_create_series_auto_attaches_preselected_character_after_create():
    src = CREATE_SERIES.read_text(encoding="utf-8")
    # The auto-attach helper exists + is invoked from the create handler
    assert "attachPreselectedCharacter" in src
    assert "/api/characters/attach-to-series/${seriesId}" in src
    # Must be called inside handleCreate success branch (both duplicate + new)
    assert "await attachPreselectedCharacter(res.data.series_id)" in src


def test_invalid_character_id_renders_structured_toast_with_request_id():
    src = CREATE_SERIES.read_text(encoding="utf-8")
    # Error path surfaces the request_id from the structured envelope
    assert "request_id" in src and "requestId" in src
    # The toast message includes the Ref id token for support correlation
    assert "Ref:" in src


# ════════════════════════════════════════════════════════════════════════
# Backend integration: attach-to-series endpoint unchanged & correct
# ════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_attach_to_series_404_for_foreign_character(admin_token, mongo):
    """A character the admin doesn't own must reject with 404 — protects
    the new preselection flow from cross-tenant pollution."""
    # Seed a foreign-owned character + a foreign-owned series
    foreign_char = f"char-{uuid.uuid4().hex}"
    foreign_series = f"series-{uuid.uuid4().hex}"
    await mongo.character_profiles.insert_one({
        "character_id": foreign_char,
        "owner_user_id": "ghost-user",
        "name": "Ghost Hero",
    })
    # Admin series — owned by admin
    admin = await mongo.users.find_one({"email": "admin@creatorstudio.ai"}, {"_id": 0, "id": 1})
    await mongo.story_series.insert_one({
        "series_id": foreign_series,
        "user_id": admin["id"],
        "title": "Admin series",
        "attached_characters": [],
    })
    try:
        async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
            r = await cli.post(
                f"/api/characters/attach-to-series/{foreign_series}",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"character_id": foreign_char},
            )
            assert r.status_code == 404
            # The endpoint distinguishes character-not-found from series-not-found
            assert "Character not found" in r.text
    finally:
        await mongo.character_profiles.delete_one({"character_id": foreign_char})
        await mongo.story_series.delete_one({"series_id": foreign_series})


@pytest.mark.asyncio
async def test_attach_to_series_happy_path_idempotent(admin_token, mongo):
    """Real attach call — verifies the preselection flow's post-create
    handoff still works (no regression to existing /attach-to-series)."""
    admin = await mongo.users.find_one({"email": "admin@creatorstudio.ai"}, {"_id": 0, "id": 1})
    uid = admin["id"]
    char_id = f"char-{uuid.uuid4().hex}"
    series_id = f"series-{uuid.uuid4().hex}"
    await mongo.character_profiles.insert_one({
        "character_id": char_id, "owner_user_id": uid, "name": "Test Hero",
    })
    await mongo.story_series.insert_one({
        "series_id": series_id, "user_id": uid, "title": "Test", "attached_characters": [],
    })
    try:
        async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
            h = {"Authorization": f"Bearer {admin_token}"}
            r1 = await cli.post(
                f"/api/characters/attach-to-series/{series_id}",
                headers=h, json={"character_id": char_id},
            )
            assert r1.status_code == 200, r1.text
            assert r1.json()["success"] is True
            # Idempotency: second call returns already_attached
            r2 = await cli.post(
                f"/api/characters/attach-to-series/{series_id}",
                headers=h, json={"character_id": char_id},
            )
            assert r2.status_code == 200
            assert r2.json().get("already_attached") is True
            # Series document carries the character
            s = await mongo.story_series.find_one({"series_id": series_id})
            assert char_id in s.get("attached_characters", [])
    finally:
        await mongo.character_profiles.delete_one({"character_id": char_id})
        await mongo.story_series.delete_one({"series_id": series_id})
