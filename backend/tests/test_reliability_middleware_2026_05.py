"""
Reliability middleware foundation — 2026-05-16 P0 (Session 1)

Locks in:
  • RequestIdMiddleware stamps X-Request-Id on every response
  • Inbound X-Request-Id is preserved (when safely-formatted)
  • Malformed inbound X-Request-Id is rejected → server generates a fresh id
  • request.state.request_id is reachable from handlers
  • get_request_id() helper falls back to a fresh uuid when middleware absent
  • structured_log() emits "[event] request_id=... key=value ..." records
  • CORS exposes X-Request-Id (so cross-origin frontends can read it)
  • P2C + Create Series structured envelopes consume the middleware id
    (per-handler uuid.uuid4() plants retired)
"""
import os
import re
import uuid
import logging
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


HEX_RE = re.compile(r"^[A-Za-z0-9._\-]{8,128}$")


# ═════════════════════════════════════════════════════════════════════
# 1. Middleware-level behaviour (end-to-end via live backend)
# ═════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_response_always_carries_x_request_id():
    async with httpx.AsyncClient(base_url=_api_base(), timeout=10.0) as cli:
        # /api/health/ returns 307 redirect — even pre-route responses
        # MUST carry the header. follow_redirects=False keeps this honest.
        r = await cli.get("/api/health/", follow_redirects=False)
        rid = r.headers.get("X-Request-Id") or r.headers.get("x-request-id")
        assert rid is not None and len(rid) >= 8, \
            f"X-Request-Id missing on health response: headers={dict(r.headers)}"
        assert HEX_RE.match(rid), f"X-Request-Id has unsafe format: {rid!r}"


@pytest.mark.asyncio
async def test_inbound_safe_request_id_propagated():
    """Caller-supplied id (within safe character set + length bounds) MUST
    flow through unchanged so distributed tracing works."""
    caller_id = "test-trace-id-" + uuid.uuid4().hex
    async with httpx.AsyncClient(base_url=_api_base(), timeout=10.0) as cli:
        r = await cli.get(
            "/api/health/",
            headers={"X-Request-Id": caller_id},
            follow_redirects=False,
        )
        assert r.headers.get("X-Request-Id") == caller_id


@pytest.mark.asyncio
async def test_inbound_malformed_request_id_replaced():
    """Caller sends a payload-looking value — middleware must reject it and
    generate a fresh server-side id. Prevents log-injection."""
    async with httpx.AsyncClient(base_url=_api_base(), timeout=10.0) as cli:
        r = await cli.get(
            "/api/health/",
            headers={"X-Request-Id": "<script>alert(1)</script>"},
            follow_redirects=False,
        )
        rid = r.headers.get("X-Request-Id")
        assert rid is not None
        assert "<" not in rid and "script" not in rid, \
            f"Malformed inbound id should have been replaced, got: {rid!r}"
        assert HEX_RE.match(rid)


@pytest.mark.asyncio
async def test_inbound_too_short_request_id_replaced():
    async with httpx.AsyncClient(base_url=_api_base(), timeout=10.0) as cli:
        r = await cli.get(
            "/api/health/",
            headers={"X-Request-Id": "abc"},  # < 8 chars
            follow_redirects=False,
        )
        rid = r.headers.get("X-Request-Id")
        assert rid != "abc"
        assert HEX_RE.match(rid)


@pytest.mark.asyncio
async def test_inbound_too_long_request_id_replaced():
    async with httpx.AsyncClient(base_url=_api_base(), timeout=10.0) as cli:
        r = await cli.get(
            "/api/health/",
            headers={"X-Request-Id": "x" * 200},  # > 128 chars
            follow_redirects=False,
        )
        rid = r.headers.get("X-Request-Id")
        assert len(rid) < 200


@pytest.mark.asyncio
async def test_two_consecutive_requests_get_distinct_ids():
    """No global counter / no shared state — each request gets its own id."""
    async with httpx.AsyncClient(base_url=_api_base(), timeout=10.0) as cli:
        r1 = await cli.get("/api/health/", follow_redirects=False)
        r2 = await cli.get("/api/health/", follow_redirects=False)
        assert r1.headers.get("X-Request-Id") != r2.headers.get("X-Request-Id")


# ═════════════════════════════════════════════════════════════════════
# 2. Module-level unit checks for the helper APIs
# ═════════════════════════════════════════════════════════════════════
def test_get_request_id_fallback_when_state_missing():
    """If a handler ever runs without the middleware (test client / direct
    invocation), get_request_id() must still return a non-empty string."""
    import sys
    sys.path.insert(0, "/app/backend")
    from middleware.reliability import get_request_id

    class _NoStateRequest:
        pass

    rid = get_request_id(_NoStateRequest())
    assert isinstance(rid, str) and len(rid) >= 8


def test_get_request_id_returns_state_value():
    import sys
    sys.path.insert(0, "/app/backend")
    from middleware.reliability import get_request_id

    class _State:
        request_id = "abc123def456ghi"

    class _Req:
        state = _State()

    assert get_request_id(_Req()) == "abc123def456ghi"


def test_structured_log_emits_request_id(caplog):
    import sys
    sys.path.insert(0, "/app/backend")
    from middleware.reliability import structured_log

    log = logging.getLogger("test-reliability-log")
    with caplog.at_level(logging.WARNING, logger="test-reliability-log"):
        structured_log(
            log, logging.WARNING, "test-event",
            request=None, request_id="fixed-id-001",
            user="admin", code="DEMO", note="hello world",
        )
    # Find our record
    rec = next((r for r in caplog.records if r.name == "test-reliability-log"), None)
    assert rec is not None
    msg = rec.getMessage()
    assert "[test-event]" in msg
    assert "request_id=fixed-id-001" in msg
    assert "user=" in msg and "'admin'" in msg
    assert "code=" in msg and "'DEMO'" in msg


def test_structured_log_truncates_long_strings(caplog):
    """200-char cap keeps log lines reasonable; newlines stripped."""
    import sys
    sys.path.insert(0, "/app/backend")
    from middleware.reliability import structured_log

    log = logging.getLogger("test-reliability-trim")
    with caplog.at_level(logging.WARNING, logger="test-reliability-trim"):
        structured_log(
            log, logging.WARNING, "test-event",
            request=None, request_id="trim-id",
            blob=("X" * 1000),
            multi="line1\nline2\nline3",
        )
    rec = next((r for r in caplog.records if r.name == "test-reliability-trim"), None)
    assert rec is not None
    msg = rec.getMessage()
    # Long blob got truncated to <=200 chars + ellipsis
    assert "X" * 1000 not in msg
    assert "X" * 197 in msg
    assert "..." in msg
    # Multi-line collapsed to single line
    assert "line1 line2 line3" in msg.replace("'", "")


# ═════════════════════════════════════════════════════════════════════
# 3. CORS exposes X-Request-Id (so browser fetch() can read it)
# ═════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_cors_preflight_exposes_x_request_id():
    """The Access-Control-Expose-Headers list on CORS responses MUST
    include X-Request-Id, otherwise cross-origin browser fetch() won't be
    able to read the header even though the server sends it."""
    async with httpx.AsyncClient(base_url=_api_base(), timeout=10.0) as cli:
        r = await cli.get("/api/health/", follow_redirects=False, headers={"Origin": "https://example.test"})
        expose = r.headers.get("Access-Control-Expose-Headers", "")
        assert "X-Request-Id" in expose, \
            f"CORS must expose X-Request-Id; got: {expose!r}"


# ═════════════════════════════════════════════════════════════════════
# 4. P2C INVALID_STYLE envelope consumes middleware request_id
# ═════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_p2c_invalid_style_envelope_matches_response_header(admin_token):
    """The request_id surfaced inside the structured envelope MUST equal
    the X-Request-Id header on the SAME response. This is the actual
    correlation guarantee — without it, the envelope is meaningless."""
    caller_id = "p2c-trace-" + uuid.uuid4().hex
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        files = {"photo": ("x.jpg", b"\xff\xd8\xff", "image/jpeg")}
        data = {"mode": "avatar", "style": "[object Object]"}
        r = await cli.post(
            "/api/photo-to-comic/generate",
            files=files, data=data,
            headers={"Authorization": f"Bearer {admin_token}", "X-Request-Id": caller_id},
        )
        assert r.status_code == 400
        header_rid = r.headers.get("X-Request-Id")
        envelope_rid = r.json()["detail"]["request_id"]
        assert header_rid == caller_id, "Inbound id must propagate to header"
        assert envelope_rid == caller_id, \
            "Envelope request_id MUST equal header — that's the correlation guarantee"


# ═════════════════════════════════════════════════════════════════════
# 5. Server.py wires the middleware LAST (so it runs FIRST in the path)
# ═════════════════════════════════════════════════════════════════════
def test_server_py_wires_request_id_middleware_after_others():
    server = Path("/app/backend/server.py").read_text(encoding="utf-8")
    # RequestIdMiddleware is imported
    assert "from middleware.reliability import RequestIdMiddleware" in server
    # And added via app.add_middleware
    assert "app.add_middleware(RequestIdMiddleware)" in server
    # And added AFTER LatencyTrackingMiddleware so it wraps it (outermost
    # middleware runs first in Starlette).
    idx_latency = server.find("app.add_middleware(LatencyTrackingMiddleware)")
    idx_request = server.find("app.add_middleware(RequestIdMiddleware)")
    assert 0 < idx_latency < idx_request, \
        "RequestIdMiddleware must be added AFTER LatencyTrackingMiddleware so it wraps the entire stack"


# ═════════════════════════════════════════════════════════════════════
# 6. Per-handler uuid plants in P2C + Create Series have been retired
# ═════════════════════════════════════════════════════════════════════
def test_p2c_no_longer_generates_its_own_request_id():
    src = Path("/app/backend/routes/photo_to_comic.py").read_text(encoding="utf-8")
    # Find the INVALID_STYLE block
    idx = src.find('"code": "INVALID_STYLE"')
    assert idx > 0
    # Slice ~500 chars BEFORE that block, where the request_id was set
    before = src[max(0, idx - 800):idx]
    assert "request_id = get_request_id(request)" in before, \
        "P2C must source request_id from middleware via get_request_id(request)"
    # And it must NOT do its own uuid plant for this purpose anymore.
    assert "request_id = str(uuid.uuid4())" not in before, \
        "Per-handler uuid.uuid4() plant for request_id must be retired"


def test_create_series_no_longer_generates_its_own_request_id():
    src = Path("/app/backend/routes/story_series.py").read_text(encoding="utf-8")
    # Find the create_series handler signature
    idx = src.find("async def create_series(")
    assert idx > 0
    func = src[idx:idx + 1200]
    # Must accept the Starlette Request
    assert "_http: StarletteRequest" in func
    # And source request_id from middleware
    assert "request_id = get_request_id(_http)" in func
    # And the old per-handler uuid plant for request_id is gone
    assert "request_id = _uuid()" not in func, \
        "Per-handler _uuid() plant for request_id must be retired"
