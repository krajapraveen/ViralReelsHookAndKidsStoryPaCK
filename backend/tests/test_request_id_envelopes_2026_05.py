"""
request_id correlation — 2026-05-16 P0 (foundation pass)

Adds request_id to:
  • Photo-to-Comic INVALID_STYLE envelope + warning log
  • Create Series LLM_TIMEOUT / LLM_BAD_JSON / LLM_*_ERROR envelopes
  • Frontend toasts surface "Reference ID: <request_id>" when present

Also adds Comic-Strip-specific coverage proving that mode=strip with a
malformed style payload returns the structured INVALID_STYLE envelope
(not the legacy "Invalid style '[object Object]'. Allowed: ..." string).
"""
import os
import json
import uuid
import pytest
import pytest_asyncio
import httpx
from pathlib import Path
from dotenv import load_dotenv

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


P2C_PY = Path("/app/backend/routes/photo_to_comic.py")
SERIES_PY = Path("/app/backend/routes/story_series.py")
P2C_JS = Path("/app/frontend/src/pages/PhotoToComic.js")
SERIES_JS = Path("/app/frontend/src/pages/CreateSeries.js")


# ─── P2C INVALID_STYLE envelope carries request_id ───────────────────────────
@pytest.mark.asyncio
async def test_p2c_invalid_style_envelope_includes_request_id(admin_token):
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        files = {"photo": ("x.jpg", b"\xff\xd8\xff", "image/jpeg")}
        data = {"mode": "avatar", "style": "[object Object]"}
        r = await cli.post(
            "/api/photo-to-comic/generate",
            files=files, data=data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 400, r.text
        detail = r.json().get("detail")
        assert isinstance(detail, dict)
        assert detail.get("code") == "INVALID_STYLE"
        # request_id MUST be present and a non-empty string
        rid = detail.get("request_id")
        assert isinstance(rid, str) and len(rid) >= 8, \
            f"request_id missing or too short: {rid!r}"
        # And distinct across two consecutive calls (uuid)
        r2 = await cli.post(
            "/api/photo-to-comic/generate",
            files=files, data=data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        rid2 = r2.json()["detail"]["request_id"]
        assert rid != rid2, "request_id must be unique per request"


# ─── Comic-Strip-mode INVALID_STYLE coverage (closes production gap) ────────
@pytest.mark.asyncio
async def test_p2c_invalid_style_envelope_in_strip_mode(admin_token):
    """The user-visible production screenshot was from `mode=strip`. Confirm
    the structured envelope (NOT the legacy 'Invalid style ...' string) is
    returned for the strip pipeline too."""
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        files = {"photo": ("x.jpg", b"\xff\xd8\xff", "image/jpeg")}
        data = {
            "mode": "strip",
            "style": "[object Object]",
            "panel_count": "4",
            "genre": "action",
        }
        r = await cli.post(
            "/api/photo-to-comic/generate",
            files=files, data=data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 400, r.text
        body_text = r.text
        # NO legacy raw string allowed to leak
        assert "Invalid style '[object Object]'" not in body_text, \
            "Legacy raw error string MUST NOT appear in strip mode response"
        assert "Allowed: [" not in body_text, \
            "Legacy 'Allowed: [...]' tail must not leak in strip mode"
        # Must be the structured envelope
        detail = r.json().get("detail")
        assert isinstance(detail, dict)
        assert detail.get("code") == "INVALID_STYLE"
        assert detail.get("message") == "Selected comic style is not supported. Please try another style."
        assert isinstance(detail.get("request_id"), str)


@pytest.mark.parametrize("style_key", [
    "bold_superhero", "cartoon_fun", "retro_action", "soft_manga",
    "cute_chibi", "kids_storybook", "noir_comic", "scifi_neon",
    "cyberpunk_comic", "magical_fantasy", "dreamy_pastel", "black_white_ink",
])
def test_p2c_strip_mode_accepts_all_12_canonical_styles(style_key):
    """All 12 canonical styles must pass the synchronous validation gate.
    Style validation is purely `if style not in SAFE_STYLES: raise INVALID_STYLE`
    — no network hop needed. Unit-test the registry membership directly so
    the 12 cases don't depend on the live LLM pipeline (which is what made
    the previous httpx variant flaky at >2-min wall clock).
    """
    import sys
    sys.path.insert(0, "/app/backend")
    from routes.photo_to_comic import SAFE_STYLES, _normalize_style_input
    # Canonical key passes membership
    assert style_key in SAFE_STYLES, f"Canonical style '{style_key}' missing from SAFE_STYLES"
    # And the normalizer is idempotent for canonical keys
    assert _normalize_style_input(style_key) == style_key
    # And the normalizer correctly extracts canonical keys from JSON-wrapped objects
    wrapped = json.dumps({"id": style_key, "label": "ignored"})
    assert _normalize_style_input(wrapped) == style_key


# ─── Backend source-level checks for log + envelope ──────────────────────────
def test_p2c_logs_request_id_on_invalid_style():
    src = P2C_PY.read_text(encoding="utf-8")
    # Session 1 refactor: log is now via structured_log() on the
    # "p2c/invalid-style" event. The middleware fills request_id.
    assert '"p2c/invalid-style"' in src
    assert "structured_log(" in src
    # And the envelope must still include the field
    idx = src.find('"code": "INVALID_STYLE"')
    assert idx > 0
    block = src[idx:idx + 800]
    assert '"request_id": request_id' in block
    assert '"retryable": False' in block


def test_create_series_envelopes_include_request_id():
    src = SERIES_PY.read_text(encoding="utf-8")
    # Session 1 refactor: request_id sourced from middleware via get_request_id
    assert "request_id = get_request_id(_http)" in src
    # All three structured envelopes must carry request_id
    # LLM_TIMEOUT
    idx = src.find('"code": "LLM_TIMEOUT"')
    assert idx > 0
    block = src[idx:idx + 500]
    assert '"request_id": request_id' in block
    # LLM_BAD_JSON
    idx = src.find('"code": "LLM_BAD_JSON"')
    assert idx > 0
    block = src[idx:idx + 500]
    assert '"request_id": request_id' in block
    # Catch-all generic-LLM envelope
    idx = src.find('"code": code, "message": msg')
    assert idx > 0
    block = src[idx:idx + 300]
    assert '"request_id": request_id' in block
    # Logs include request_id
    assert "request_id={request_id}" in src


# ─── Frontend renders "Reference ID: ..." when backend provides one ─────────
def test_p2c_frontend_surfaces_reference_id():
    src = P2C_JS.read_text(encoding="utf-8")
    assert "structured.request_id" in src
    assert "Reference ID: ${structured.request_id}" in src


def test_create_series_frontend_surfaces_reference_id():
    src = SERIES_JS.read_text(encoding="utf-8")
    assert "d.detail.request_id" in src
    assert "Reference ID: ${d.detail.request_id}" in src
