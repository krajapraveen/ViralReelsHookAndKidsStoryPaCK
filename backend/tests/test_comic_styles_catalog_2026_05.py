"""
P0 — Comic Style Catalog Single-Source-of-Truth (2026-05-18)
==============================================================
Production reported: "Selected comic style is not supported. Please try
another style." surfacing for visible UI styles. Root cause was contract
drift between two duplicated catalogs (frontend `COMIC_STYLES` vs backend
`SAFE_STYLES`).

This file locks in the new contract:

  1. Backend `SAFE_STYLES` is the single source of truth
  2. Every entry has: name, label, prompt, modes, tier, preview_color, enabled
  3. `GET /api/photo-to-comic/styles-catalog?mode=...` returns enabled
     entries for that mode
  4. `is_style_valid_for_mode()` is the authoritative validator
  5. Create endpoint rejects unknown style → 400 INVALID_STYLE w/ request_id
  6. Create endpoint rejects mode-mismatch → 422 STYLE_MODE_MISMATCH w/ request_id
  7. Frontend hardcoded mirror = subset of backend `enabled: True` entries
  8. Every frontend mirror entry passes `is_style_valid_for_mode` for its modes
  9. PhotoToComic page fetches the catalog on mount + on mode-switch
 10. Mode-switch resets selected style if invalid for new mode
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
sys.path.insert(0, "/app/backend")

from routes.photo_to_comic import (  # noqa: E402
    SAFE_STYLES, _styles_catalog_for_mode, is_style_valid_for_mode,
)


PHOTO_TO_COMIC_JS = Path("/app/frontend/src/pages/PhotoToComic.js")
COMIC_STYLES_JS = Path("/app/frontend/src/constants/comicStyles.js")


def _api_base() -> str:
    p = "/app/frontend/.env"
    if os.path.exists(p):
        for line in open(p):
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    return "http://localhost:8001"


@pytest_asyncio.fixture
async def admin_token():
    async with httpx.AsyncClient(base_url=_api_base(), timeout=20.0) as cli:
        r = await cli.post(
            "/api/auth/login",
            json={"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"},
        )
        assert r.status_code == 200
        yield r.json().get("access_token") or r.json().get("token")


# ════════════════════════════════════════════════════════════════════════
# Backend catalog shape
# ════════════════════════════════════════════════════════════════════════
def test_every_safe_style_has_required_metadata():
    required = ("name", "label", "prompt", "modes", "tier", "preview_color", "enabled")
    for key, meta in SAFE_STYLES.items():
        for f in required:
            assert f in meta, f"SAFE_STYLES[{key!r}] missing required field {f!r}"
        assert isinstance(meta["modes"], list)
        assert meta["modes"], f"{key} has empty modes list"
        for m in meta["modes"]:
            assert m in ("avatar", "strip"), f"{key} has invalid mode {m!r}"
        assert meta["tier"] in ("free", "paid")
        assert isinstance(meta["enabled"], bool)


def test_catalog_filter_returns_only_enabled_for_mode():
    avatar = _styles_catalog_for_mode("avatar")
    strip = _styles_catalog_for_mode("strip")
    for s in avatar:
        assert s["enabled"] is True
        assert "avatar" in s["modes"]
    for s in strip:
        assert s["enabled"] is True
        assert "strip" in s["modes"]


def test_catalog_filter_excludes_disabled_styles():
    """Founder-spec: disabled styles must NEVER reach the frontend grid."""
    for mode in ("avatar", "strip"):
        catalog = _styles_catalog_for_mode(mode)
        catalog_keys = {s["key"] for s in catalog}
        disabled_keys = {k for k, m in SAFE_STYLES.items() if not m.get("enabled", True)}
        assert catalog_keys.isdisjoint(disabled_keys), \
            f"Disabled styles leaked into {mode} catalog: " \
            f"{catalog_keys & disabled_keys}"


def test_is_style_valid_for_mode_consistent_with_catalog():
    for mode in ("avatar", "strip"):
        catalog = _styles_catalog_for_mode(mode)
        for s in catalog:
            assert is_style_valid_for_mode(s["key"], mode), \
                f"Catalog includes {s['key']} for {mode} but validator rejects it"
        # Non-catalog keys must be rejected
        assert not is_style_valid_for_mode("does_not_exist", mode)
        # Other-mode-only keys must be rejected for this mode
        for other_key, meta in SAFE_STYLES.items():
            if not meta.get("enabled", True): continue
            if mode in meta["modes"]: continue
            assert not is_style_valid_for_mode(other_key, mode), \
                f"{other_key} is not legal for {mode} but validator accepts it"


# ════════════════════════════════════════════════════════════════════════
# Backend live API
# ════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_styles_catalog_endpoint_returns_avatar_mode_subset(admin_token):
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        r = await cli.get(
            "/api/photo-to-comic/styles-catalog?mode=avatar",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["mode"] == "avatar"
        assert isinstance(body["styles"], list)
        assert len(body["styles"]) > 0
        for s in body["styles"]:
            for f in ("key", "label", "modes", "tier", "preview_color",
                      "provider_style", "enabled"):
                assert f in s, f"Catalog entry {s.get('key')} missing {f}"
            assert "avatar" in s["modes"]
            assert s["enabled"] is True


@pytest.mark.asyncio
async def test_styles_catalog_endpoint_returns_strip_mode_subset(admin_token):
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        r = await cli.get(
            "/api/photo-to-comic/styles-catalog?mode=strip",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["mode"] == "strip"
        for s in body["styles"]:
            assert "strip" in s["modes"]


@pytest.mark.asyncio
async def test_styles_catalog_rejects_invalid_mode(admin_token):
    async with httpx.AsyncClient(base_url=_api_base(), timeout=10.0) as cli:
        r = await cli.get(
            "/api/photo-to-comic/styles-catalog?mode=hologram",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 400
        assert r.json()["detail"]["code"] == "INVALID_MODE"


# ════════════════════════════════════════════════════════════════════════
# Backend create-endpoint validation envelopes
# ════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_create_endpoint_rejects_invalid_style_with_structured_envelope(admin_token):
    """An unknown style must surface 400 INVALID_STYLE with request_id +
    NOT a generic 503."""
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        r = await cli.post(
            "/api/photo-to-comic/generate",
            headers={"Authorization": f"Bearer {admin_token}"},
            data={
                "style": "this_style_does_not_exist",
                "mode": "avatar",
                "story_preset": "epic_origin_story",
            },
            files={"photo": ("p.png", b"GIF89a\x00", "image/png")},
        )
        # The endpoint validates style BEFORE reading the file, so any
        # 4xx other than 503 is acceptable as long as it carries the code.
        assert r.status_code == 400, r.text
        d = r.json()["detail"]
        assert d["code"] == "INVALID_STYLE"
        assert d["request_id"]
        assert d["retryable"] is False
        assert "allowed_sample" in d


@pytest.mark.asyncio
async def test_create_endpoint_rejects_mode_mismatch_with_422(admin_token):
    """Pick a style whose `modes` does NOT include the active mode →
    must surface 422 STYLE_MODE_MISMATCH (NOT 400, NOT 503)."""
    # Find a style that exists+enabled in only ONE mode (or fabricate one
    # by directly checking SAFE_STYLES). All currently-enabled styles are
    # both-modes, so we exercise a DISABLED style that exists in catalog.
    # Pick `meme_expression` (avatar-only, enabled=False).
    target = None
    for k, m in SAFE_STYLES.items():
        if m.get("enabled", True): continue
        modes = m.get("modes", [])
        if "avatar" in modes and "strip" not in modes:
            target = k; break
    assert target, "Expected at least one avatar-only entry (any tier) for the test"

    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        # Try the avatar-only style in STRIP mode → mode mismatch.
        r = await cli.post(
            "/api/photo-to-comic/generate",
            headers={"Authorization": f"Bearer {admin_token}"},
            data={
                "style": target,
                "mode": "strip",
                "story_preset": "epic_origin_story",
            },
            files={"photo": ("p.png", b"GIF89a\x00", "image/png")},
        )
        assert r.status_code == 422, r.text
        d = r.json()["detail"]
        assert d["code"] == "STYLE_MODE_MISMATCH"
        assert d["request_id"]
        assert d["mode"] == "strip"
        assert "allowed_modes" in d


# ════════════════════════════════════════════════════════════════════════
# Frontend ↔ Backend parity (the contract drift killer)
# ════════════════════════════════════════════════════════════════════════
def _frontend_mirror_keys() -> set[str]:
    src = COMIC_STYLES_JS.read_text(encoding="utf-8")
    # Match { key: 'foo', ... } in COMIC_STYLES array
    return set(re.findall(r"\{\s*key:\s*'([a-z_]+)'", src))


def test_frontend_mirror_is_strict_subset_of_backend_enabled_entries():
    """Every key in the frontend hardcoded mirror MUST be present and
    enabled in the backend SAFE_STYLES. This eliminates the historical
    bug where the frontend offered a style the backend then rejected."""
    fe_keys = _frontend_mirror_keys()
    assert fe_keys, "Could not parse COMIC_STYLES from frontend (test regex)"
    backend_enabled = {k for k, m in SAFE_STYLES.items() if m.get("enabled", True)}
    drift = fe_keys - backend_enabled
    assert not drift, \
        f"Frontend mirror contains keys not in backend enabled set: {drift}"


def test_every_frontend_mirror_style_passes_validator_for_its_modes():
    src = COMIC_STYLES_JS.read_text(encoding="utf-8")
    # For each frontend entry parse its modes list, then assert validator
    # accepts the (key, mode) pair.
    pattern = re.compile(
        r"\{\s*key:\s*'([a-z_]+)',[^}]*modes:\s*\[([^\]]+)\]",
        re.S,
    )
    matches = pattern.findall(src)
    assert matches, "Could not parse modes from frontend mirror"
    for key, modes_raw in matches:
        modes = [m.strip().strip("'\"") for m in modes_raw.split(",")]
        for mode in modes:
            assert is_style_valid_for_mode(key, mode), \
                f"Frontend mirror advertises {key} for {mode} but backend rejects"


# ════════════════════════════════════════════════════════════════════════
# Frontend page wiring (mode-aware grid + reset on mode switch)
# ════════════════════════════════════════════════════════════════════════
def test_page_fetches_catalog_via_canonical_endpoint():
    src = PHOTO_TO_COMIC_JS.read_text(encoding="utf-8")
    assert "fetchComicStylesCatalog" in src
    # Effect runs on mode change so the grid is re-fetched
    assert "useEffect" in src and "[mode]" in src


def test_page_resets_invalid_selection_on_mode_switch():
    src = PHOTO_TO_COMIC_JS.read_text(encoding="utf-8")
    block = src.split("Re-fetch the catalog when the user toggles", 1)[1].split("}, [mode]", 1)[0]
    # The effect builds a legal-keys Set and resets selection if invalid.
    assert "legalKeys" in block
    assert "if (!legalKeys.has(style))" in block
    assert "setStyle(next.id)" in block


def test_page_renders_grid_from_availableStyles_state():
    src = PHOTO_TO_COMIC_JS.read_text(encoding="utf-8")
    # The render maps over availableStyles (NOT the legacy module-scope STYLES)
    assert "availableStyles.map((s)" in src
    # The legacy module-scope const STYLES = ... is gone
    assert "const STYLES = COMIC_STYLES.map" not in src


def test_page_error_handler_surfaces_request_id_on_all_paths():
    src = PHOTO_TO_COMIC_JS.read_text(encoding="utf-8")
    # Locate the catch block that ends with `setGenerating(false);`
    # following the "isGatewayError" branching. We assert the new
    # request_id resolution + Reference ID render landed in the right
    # place.
    assert "isGatewayError" in src
    block = src.split("isGatewayError", 1)[1].split("};", 1)[0]
    # request_id resolution
    assert "data?.request_id" in block
    assert "x-request-id" in block.lower()
    # Reference ID render in this block (gateway/fallback path)
    assert "Reference ID:" in block
    # Globally the structured branch ALSO renders Reference ID — at least
    # 2 sites total in the file
    assert src.count("Reference ID:") >= 2
    # Founder mandate: EVERY non-structured error path must surface a
    # Reference ID line — real or "not-captured" sentinel. Lock in the
    # four exhaustive branches: real rid, gateway, network (code===0),
    # and unexpected-shape catch-all (else).
    assert "if (rid)" in block, "Real-rid branch missing"
    assert "else if (isGatewayError)" in block, "Gateway not-captured branch missing"
    assert "else if (code === 0)" in block, "Network-failure not-captured branch missing"
    # The trailing else ensures any HTTP shape we don't recognise still
    # gets a Reference ID line. We split after the network branch and
    # take everything up to `toast.error(` — that's the catch-all else.
    after_network = block.split("else if (code === 0)", 1)[1]
    catchall_else = after_network.split("toast.error(", 1)[0]
    assert "else {" in catchall_else, "Catch-all else branch missing"
    assert "Reference ID:" in catchall_else, \
        "Catch-all else branch missing Reference ID render for unexpected error shapes"
    assert "HTTP" in catchall_else, \
        "Catch-all else branch should reference the HTTP status code"
    # Sanity: there should now be at least 4 distinct Reference ID
    # render sites in the catch block (real, gateway, network,
    # catch-all) plus the structured branch up top → ≥5 globally.
    assert src.count("Reference ID:") >= 5, \
        f"Expected ≥5 Reference ID render sites; found {src.count('Reference ID:')}"


def test_page_handles_style_mode_mismatch_envelope():
    src = PHOTO_TO_COMIC_JS.read_text(encoding="utf-8")
    assert "STYLE_MODE_MISMATCH" in src
    # And maps it to a code-aware human message
    block = src.split("STYLE_MODE_MISMATCH", 1)[1].split(",", 1)[0]
    # Expect a friendly user-facing string immediately following the key.
    assert "available" in block.lower() or "mode" in block.lower()
