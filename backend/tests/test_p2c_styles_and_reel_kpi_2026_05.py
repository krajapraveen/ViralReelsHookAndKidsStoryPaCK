"""
Three-fix regression bundle — 2026-05-16 P0

1. Photo-to-Comic [object Object] style mapping (frontend registry +
   backend tolerance + structured INVALID_STYLE error).
2. Reel reward-moment success-rate KPI endpoint + tile visibility gating.
3. Generic "Service temporarily unavailable" toast suppression for the
   two pages that own structured error mapping (Create Series + P2C).
"""
import os
import json
import asyncio
import uuid
import pytest
import pytest_asyncio
import httpx
from datetime import datetime, timezone, timedelta
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


# ═════════════════════════════════════════════════════════════════════
# 1. Photo-to-Comic [object Object] fix
# ═════════════════════════════════════════════════════════════════════
COMIC_STYLES_JS = Path("/app/frontend/src/constants/comicStyles.js")
P2C_JS = Path("/app/frontend/src/pages/PhotoToComic.js")
P2C_PY = Path("/app/backend/routes/photo_to_comic.py")


def test_canonical_comic_styles_registry_exists():
    src = COMIC_STYLES_JS.read_text(encoding="utf-8")
    assert "export const COMIC_STYLES" in src
    assert "export function normalizeComicStyle" in src
    # All 12 styles per spec
    for key in (
        "bold_superhero", "cartoon_fun", "retro_action", "soft_manga",
        "cute_chibi", "kids_storybook", "noir_comic", "scifi_neon",
        "cyberpunk_comic", "magical_fantasy", "dreamy_pastel",
        "black_white_ink",
    ):
        assert key in src, f"Missing canonical style key: {key}"


def test_normalize_comic_style_logic_present():
    """The normalizer must handle string + object (id/apiValue/key/value/style)
    + nullish + unknown values."""
    src = COMIC_STYLES_JS.read_text(encoding="utf-8")
    assert "if (typeof input === 'string')" in src
    for k in ("apiValue", "id", "key", "value", "style"):
        assert k in src, f"normalizer must check object key: {k}"
    # Must return null for unknown values (so the caller can surface a
    # clean structured error rather than silently bouncing to backend).
    assert "VALID_KEYS.has(candidate) ? candidate : null" in src


def test_p2c_page_uses_registry_and_normalizer():
    src = P2C_JS.read_text(encoding="utf-8")
    assert "from '../constants/comicStyles'" in src
    assert "normalizeComicStyle" in src
    # The handler MUST call normalizeComicStyle on the active style
    assert "const activeStyle = normalizeComicStyle" in src
    # And refuse to submit when null
    assert "Selected comic style is not supported" in src


def test_p2c_page_maps_structured_invalid_style_error():
    src = P2C_JS.read_text(encoding="utf-8")
    assert "INVALID_STYLE" in src
    assert "Selected comic style is not supported. Please try another style." in src
    # The structured envelope check
    assert "structured?.code" in src or "structured && structured.code" in src or \
           "if (structured?.code)" in src


def test_backend_style_normalizer_present():
    src = P2C_PY.read_text(encoding="utf-8")
    assert "def _normalize_style_input" in src
    # Must explicitly handle the "[object Object]" literal
    assert "[object Object]" in src
    # Must accept JSON-encoded object payloads
    assert 'startswith("{")' in src
    for k in ("apiValue", "id", "key", "value", "style"):
        assert f'"{k}"' in src


def test_backend_returns_structured_invalid_style_error():
    src = P2C_PY.read_text(encoding="utf-8")
    # The /generate handler now raises detail={code, message, ...}
    assert '"code": "INVALID_STYLE"' in src
    assert '"Selected comic style is not supported.' in src


@pytest.mark.asyncio
async def test_backend_rejects_object_object_with_structured_400(admin_token):
    """End-to-end: posting style='[object Object]' must yield a 400 with
    detail.code == 'INVALID_STYLE'."""
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        files = {"photo": ("x.jpg", b"\xff\xd8\xff", "image/jpeg")}
        data = {"mode": "avatar", "style": "[object Object]"}
        r = await cli.post(
            "/api/photo-to-comic/generate",
            files=files, data=data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 400
        body = r.json()
        detail = body.get("detail")
        assert isinstance(detail, dict)
        assert detail.get("code") == "INVALID_STYLE"
        assert "not supported" in detail.get("message", "").lower()


@pytest.mark.asyncio
async def test_backend_accepts_json_encoded_style_object(admin_token):
    """If a future caller switches to JSON body and accidentally serializes
    the whole style object, the backend should extract the id and proceed
    past the style-validation step."""
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        files = {"photo": ("x.jpg", b"\xff\xd8\xff", "image/jpeg")}
        data = {"mode": "avatar",
                "style": json.dumps({"id": "cartoon_fun", "label": "Cartoon"})}
        r = await cli.post(
            "/api/photo-to-comic/generate",
            files=files, data=data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        # MUST NOT return INVALID_STYLE — the object should have been
        # normalized to "cartoon_fun" before validation.
        if r.status_code == 400:
            body = r.json()
            detail = body.get("detail", {})
            assert (not isinstance(detail, dict)) or detail.get("code") != "INVALID_STYLE", \
                f"Backend should normalize JSON-encoded style, got: {detail}"
        # Other failure modes (credits, photo bytes, etc.) are acceptable —
        # we're only testing the style-normalization extraction here.


@pytest.mark.asyncio
@pytest.mark.parametrize("style_key", [
    "bold_superhero", "cartoon_fun", "retro_action", "soft_manga",
    "cute_chibi", "kids_storybook", "noir_comic", "scifi_neon",
    "cyberpunk_comic", "magical_fantasy", "dreamy_pastel", "black_white_ink",
])
async def test_all_12_styles_pass_validation(admin_token, style_key):
    """Smoke: every canonical style key must pass the style-validation
    gate. We don't actually run the full pipeline (no real photo, would
    require credits) — but we DO require that the request gets past the
    INVALID_STYLE gate."""
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        files = {"photo": ("x.jpg", b"\xff\xd8\xff", "image/jpeg")}
        data = {"mode": "avatar", "style": style_key}
        r = await cli.post(
            "/api/photo-to-comic/generate",
            files=files, data=data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        if r.status_code == 400:
            body = r.json()
            detail = body.get("detail")
            if isinstance(detail, dict):
                assert detail.get("code") != "INVALID_STYLE", \
                    f"Style '{style_key}' rejected as INVALID_STYLE — registry drift"


# ═════════════════════════════════════════════════════════════════════
# 2. Reel reward-moment KPI tile + endpoint
# ═════════════════════════════════════════════════════════════════════
GROWTH_JS = Path("/app/frontend/src/pages/Admin/GrowthDashboard.js")


@pytest.mark.asyncio
async def test_reward_moment_endpoint_admin_gated():
    async with httpx.AsyncClient(base_url=_api_base(), timeout=10.0) as cli:
        r = await cli.get("/api/funnel/reel/reward-moment")
        assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_reward_moment_endpoint_returns_envelope(admin_token):
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        r = await cli.get(
            "/api/funnel/reel/reward-moment?days=7",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        for key in ("started", "completed", "result_viewed",
                    "success_pct", "completion_pct", "window_days", "cutoff_iso"):
            assert key in body, f"missing key: {key}"
        assert body["window_days"] == 7


@pytest.mark.asyncio
async def test_reward_moment_empty_state_returns_null_pct(admin_token):
    """Empty state: when completed == 0, success_pct must be null (not 0.0).
    Use a forced 0-window by hitting the endpoint with a fresh event-free
    period — but since funnel_events may have unrelated data, we instead
    just assert the empty-state CONTRACT by inspecting the source for the
    early-return null branch."""
    src = Path("/app/backend/routes/funnel_tracking.py").read_text(encoding="utf-8")
    # The reward-moment endpoint must early-return None on zero-den
    block = src.split("# ─── Reel Engine reward-moment KPI", 1)
    assert len(block) == 2, "Reward-moment block missing"
    block_body = block[1]
    assert "if not den:" in block_body
    assert "return None" in block_body
    # And the OpenAPI return doc must call out the empty-state behavior
    assert "Empty-state" in block_body or "empty-state" in block_body or \
           "None when" in block_body


def test_reward_moment_tile_present_in_dashboard():
    src = GROWTH_JS.read_text(encoding="utf-8")
    assert "RewardMomentTile" in src
    assert "data-testid=\"reel-reward-moment-tile\"" in src
    assert "data-testid=\"reel-reward-moment-pct\"" in src
    # Tile must be rendered in the dashboard (not just defined)
    assert "<RewardMomentTile" in src
    # Empty state: shows "—" when no completions
    assert "'—'" in src or '"—"' in src
    # Tile fetches the new endpoint
    assert "/api/funnel/reel/reward-moment" in src


def test_reward_moment_tile_color_coded():
    """Tile must color-code: green ≥95%, amber ≥80%, red below."""
    src = GROWTH_JS.read_text(encoding="utf-8")
    # Anchor to the tile component body
    idx = src.find("function RewardMomentTile")
    assert idx > 0
    body = src[idx:idx + 2500]
    assert "successPct >= 95" in body
    assert "successPct >= 80" in body
    assert "emerald" in body
    assert "amber" in body
    assert "red" in body


# ═════════════════════════════════════════════════════════════════════
# 3. Generic "Service temporarily unavailable" toast suppressed for
#    Create Series + Photo-to-Comic flows
# ═════════════════════════════════════════════════════════════════════
API_JS = Path("/app/frontend/src/utils/api.js")


def test_503_global_toast_suppressed_for_self_handled_flows():
    src = API_JS.read_text(encoding="utf-8")
    # The 503 branch must guard with an isSelfHandled check
    assert "SELF_HANDLED_URLS" in src
    assert "SELF_HANDLED_PAGES" in src
    assert "/api/photo-to-comic/" in src
    assert "/api/story-series/" in src
    assert "/app/photo-to-comic" in src
    assert "/app/create-series" in src
    # The toast call must live inside an `if (!isSelfHandled)` block
    idx = src.find("isSelfHandled")
    assert idx > 0
    # The toast.error for service-unavailable lives below this guard
    after_guard = src[idx:idx + 800]
    assert "if (!isSelfHandled)" in after_guard
    assert "id: 'service-unavailable'" in after_guard


def test_503_global_toast_still_fires_for_other_flows():
    """Sanity: non-P2C/non-create-series pages still see the global toast
    so we haven't accidentally silenced ALL 503s."""
    src = API_JS.read_text(encoding="utf-8")
    # The toast call still exists in the file (just gated now)
    assert "This feature is temporarily unavailable. Please try again shortly." in src
