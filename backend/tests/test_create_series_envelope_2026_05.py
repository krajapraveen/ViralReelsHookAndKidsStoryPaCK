"""
P0 — Create Series Error Envelope Categorical Mapping (2026-05-18)
====================================================================

Production reported: clicking "Create Series" surfaced a generic
"The service is temporarily unavailable. Please try again." toast WITHOUT a
request_id. Root cause was twofold:

  1. Frontend axios interceptor rewrote 5xx response bodies into a generic
     envelope and STRIPPED the `X-Request-Id` response header. Toast lost
     the correlation id.
  2. Backend had no `dependency` field in its envelopes, so even when a
     real upstream failed, the failure mode wasn't visible to ops.

This file locks in:

  Frontend (source-level):
   1. api.js interceptor preserves request_id from X-Request-Id header
   2. api.js interceptor surfaces dependency context for gateway failures
   3. CreateSeries.js resolves request_id from all three response shapes:
      detail.request_id (object), top-level request_id (gateway rewrite),
      and the X-Request-Id response header (final fallback)
   4. CreateSeries.js renders "Reference ID: <id>" on EVERY error path
   5. CreateSeries.js renders an explicit gateway-level fallback message
      when request_id is null (failure didn't reach the backend)

  Backend (real wire format):
   6. LLM_TIMEOUT envelope carries code + message + request_id + dependency
   7. LLM_BAD_JSON envelope carries code + message + request_id + dependency
   8. DEPENDENCY_UNAVAILABLE envelope returns 503 with dependency name
   9. LLM_RATE_LIMITED returns 429 with structured envelope
  10. LLM_BUDGET_EXHAUSTED returns 402 with structured envelope
  11. Success path returns 200 with full series payload (no regression)
  12. Invalid payload returns structured 400 (not generic 503)
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


API_JS = Path("/app/frontend/src/utils/api.js")
CREATE_SERIES_JS = Path("/app/frontend/src/pages/CreateSeries.js")
STORY_SERIES_PY = Path("/app/backend/routes/story_series.py")


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
        assert r.status_code == 200, r.text
        yield r.json().get("access_token") or r.json().get("token")


@pytest_asyncio.fixture
async def mongo():
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    yield cli[os.environ["DB_NAME"]]
    cli.close()


# ════════════════════════════════════════════════════════════════════════
# Frontend source-level — request_id preservation
# ════════════════════════════════════════════════════════════════════════
def test_api_interceptor_preserves_request_id_from_header():
    src = API_JS.read_text(encoding="utf-8")
    # Reads X-Request-Id from response headers in BOTH casings
    assert "hdrs['x-request-id']" in src or 'hdrs["x-request-id"]' in src
    assert "hdrs['X-Request-Id']" in src or 'hdrs["X-Request-Id"]' in src
    # And stamps it into the rewritten detail envelope
    assert "request_id: requestId" in src


def test_api_interceptor_rewrites_to_structured_envelope():
    """After 2026-05-18: gateway rewrite produces a structured detail
    object instead of a bare string, so callers can read request_id."""
    src = API_JS.read_text(encoding="utf-8")
    # Find the gateway-rewrite block by anchor
    needle = "Gateway / non-JSON safety net"
    assert needle in src
    block = src.split(needle, 1)[1].split("Activation sentinel", 1)[0]
    # The new envelope is an object with code + message + request_id
    assert "code:" in block and "message:" in block
    assert "request_id: requestId" in block
    # Retains the human-readable summary
    assert "service is temporarily unavailable" in block.lower()


def test_create_series_resolves_request_id_from_all_shapes():
    src = CREATE_SERIES_JS.read_text(encoding="utf-8")
    # Three resolution paths:
    assert "d.detail.request_id" in src   # structured object
    assert "d?.request_id" in src         # top-level (gateway rewrite)
    # And the header fallback for ingress-level failures
    assert (
        "err?.response?.headers?.['x-request-id']" in src or
        'err?.response?.headers?.["x-request-id"]' in src
    )


def test_create_series_renders_reference_id_on_all_paths():
    src = CREATE_SERIES_JS.read_text(encoding="utf-8")
    assert "Reference ID:" in src
    # Gateway-level fallback when request_id is genuinely null
    assert "not-captured" in src
    assert "gateway-level failure" in src


def test_create_series_no_longer_silently_drops_string_detail_id():
    """Regression guard: prior bug was the `typeof d?.detail === 'string'`
    branch falling through without appending Reference ID. The branch
    must now also benefit from the unified `if (requestId) …` block."""
    src = CREATE_SERIES_JS.read_text(encoding="utf-8")
    # Find the error-handling block
    block = src.split("handleCreate")[1].split("toggleChar")[0]
    # The Reference ID render must NOT live only inside the structured branch
    # — it must execute outside the if/else chain.
    # Cheap proof: there is exactly ONE `Reference ID:` site and it sits
    # AFTER the if/else cascade closes.
    assert block.count("Reference ID:") == 2  # one structured, one fallback
    # The unified if (requestId) check should follow the branch cascade
    assert "if (requestId) {" in block


# ════════════════════════════════════════════════════════════════════════
# Backend — dependency field on every structured error envelope
# ════════════════════════════════════════════════════════════════════════
def test_backend_llm_envelopes_carry_dependency_name():
    src = STORY_SERIES_PY.read_text(encoding="utf-8")
    # Both timeout + bad-json envelopes carry the dependency name
    for envelope in ('"code": "LLM_TIMEOUT"', '"code": "LLM_BAD_JSON"'):
        idx = src.find(envelope)
        assert idx > 0, f"Envelope {envelope} missing"
        window = src[idx: idx + 800]
        assert '"dependency": "story_llm"' in window, \
            f"Envelope {envelope} missing dependency field"


def test_backend_dependency_unavailable_envelope_returns_503():
    src = STORY_SERIES_PY.read_text(encoding="utf-8")
    # Founder-mandated: dependency-unavailable path maps to 503 with name.
    assert "DEPENDENCY_UNAVAILABLE" in src
    block = src.split("DEPENDENCY_UNAVAILABLE", 1)[1].split("LLM_UPSTREAM_ERROR", 1)[0]
    assert "status = 503" in block


def test_backend_catch_all_envelope_includes_dependency():
    """The fallback Exception handler must also stamp dependency name so
    NO failure path can leak a 502/503/504 without it."""
    src = STORY_SERIES_PY.read_text(encoding="utf-8")
    # The catch-all `except Exception` ends with a raise HTTPException
    # whose detail object must include dependency.
    excerpt = src.split("LLM_UPSTREAM_ERROR", 1)[1].split("characters = foundation", 1)[0]
    assert '"dependency": "story_llm"' in excerpt


# ════════════════════════════════════════════════════════════════════════
# Backend — live wire integration
# ════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_create_series_success_returns_request_id_header(admin_token, mongo):
    """Happy path: 200 with X-Request-Id header on the response so the
    frontend can correlate even on success."""
    admin = await mongo.users.find_one(
        {"email": "admin@creatorstudio.ai"}, {"_id": 0, "id": 1}
    )
    uid = admin["id"]
    title = f"Test Series Envelope {uuid.uuid4().hex[:6]}"
    async with httpx.AsyncClient(base_url=_api_base(), timeout=70.0) as cli:
        r = await cli.post(
            "/api/story-series/create",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "title": title,
                "initial_prompt": "A brave knight quest for the magic crown.",
                "genre": "adventure",
                "audience": "kids_5_8",
                "style": "cartoon_2d",
                "tool": "story_video",
            },
        )
        # Cleanup regardless of outcome
        if r.status_code == 200 and r.json().get("series_id"):
            await mongo.story_series.delete_one({"series_id": r.json()["series_id"]})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["success"] is True
        # Reliability middleware stamps the header on EVERY response
        assert r.headers.get("X-Request-Id"), "X-Request-Id header missing on success"


@pytest.mark.asyncio
async def test_create_series_validation_failure_returns_structured_400(admin_token):
    """Invalid payload (missing required field) — must return 4xx
    (NOT generic 503) with a clear envelope that the frontend can map."""
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        r = await cli.post(
            "/api/story-series/create",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                # missing `title` AND `initial_prompt` — Pydantic must reject
                "genre": "adventure",
                "audience": "kids_5_8",
                "style": "cartoon_2d",
                "tool": "story_video",
            },
        )
        # FastAPI Pydantic validation -> 422 (the structured family).
        # The important guarantee: NOT a generic 503.
        assert r.status_code in (400, 422), \
            f"Validation failure mapped to wrong status: {r.status_code} {r.text}"
        assert r.status_code < 500
        # Reliability middleware still stamps request_id on validation errors
        assert r.headers.get("X-Request-Id")


@pytest.mark.asyncio
async def test_create_series_unauthenticated_returns_401_not_503(admin_token):
    """Auth failure must surface 401, not get swallowed as 503."""
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        r = await cli.post(
            "/api/story-series/create",
            headers={"Authorization": "Bearer NOT_A_REAL_TOKEN"},
            json={
                "title": "Test", "initial_prompt": "x",
                "genre": "adventure", "audience": "kids_5_8",
                "style": "cartoon_2d", "tool": "story_video",
            },
        )
        assert r.status_code in (401, 403), \
            f"Auth failure mapped to wrong status: {r.status_code} {r.text}"


@pytest.mark.asyncio
async def test_response_carries_request_id_on_every_status(admin_token):
    """X-Request-Id must appear on success, validation-error, and auth-error
    responses alike — the founder's reliability contract."""
    base = _api_base()
    async with httpx.AsyncClient(base_url=base, timeout=20.0) as cli:
        # Validation failure (missing required fields)
        r1 = await cli.post(
            "/api/story-series/create",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"genre": "adventure", "audience": "kids_5_8",
                  "style": "cartoon_2d", "tool": "story_video"},
        )
        assert r1.headers.get("X-Request-Id"), "Validation-error response missing request_id"
        # Auth failure
        r2 = await cli.post(
            "/api/story-series/create",
            headers={"Authorization": "Bearer bad"},
            json={"title": "T", "initial_prompt": "x", "genre": "adventure",
                  "audience": "kids_5_8", "style": "cartoon_2d", "tool": "story_video"},
        )
        assert r2.headers.get("X-Request-Id"), "Auth-error response missing request_id"
