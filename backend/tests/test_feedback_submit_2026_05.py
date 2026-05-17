"""
P0 2026-05-19 — Legacy feedback endpoint trailing-slash redirect trap.
====================================================================
Production symptom: "Submit Feedback" on /reviews → toast "Failed to
submit feedback" with no diagnostic. Every other feedback flow
(`/api/feedback/suggestion`, `/api/feedback/experience`,
`/api/feedback/contact`) was fine.

ROOT CAUSE
----------
`FeedbackForm.js :: handleSubmit` did:
    fetch(`${BACKEND_URL}/api/feedback`, ...)   # NO trailing slash

The backend declared:
    @router.post("/")   # router prefix "/feedback"

FastAPI returned `307 Temporary Redirect` with
`Location: http://...emergentagent.com/api/feedback/`. The proxy chain
(Cloudflare → ingress → uvicorn) stamped the redirect Location with
`http://` (not `https://`). Browsers refused to follow the
HTTPS→HTTP redirect under CSP `upgrade-insecure-requests` + mixed-
content. Net: silent fetch failure → dead toast.

LOCKED-IN CONTRACT
------------------
1. Backend legacy feedback endpoint accepts BOTH `/api/feedback` and
   `/api/feedback/` — no 307 redirect at all.
2. Every error response on /api/feedback* is a structured envelope
   with `code`, `message`, `request_id`, `retryable`.
3. Frontend `FeedbackForm.js`:
   • Uses the shared `api` axios client (not raw fetch) so auth,
     request_id capture, and gateway-error normalization all apply.
   • Hits the canonical `/api/feedback/` (trailing slash).
   • Surfaces `Reference ID:` on every error path (real id or
     `not-captured` sentinel).
   • Logs structured `[feedback-submit] failed` on errors.
"""
from __future__ import annotations

import os
import re
import sys
import uuid
from pathlib import Path

import httpx
import pytest
import pytest_asyncio

sys.path.insert(0, "/app/backend")


FEEDBACK_FORM_JS = Path("/app/frontend/src/components/FeedbackForm.js")
FEEDBACK_PY = Path("/app/backend/routes/feedback.py")


def _api_base() -> str:
    p = "/app/frontend/.env"
    for line in open(p):
        if line.startswith("REACT_APP_BACKEND_URL="):
            return line.split("=", 1)[1].strip()
    return "http://localhost:8001"


# ════════════════════════════════════════════════════════════════════════
# Backend route — no more 307 redirect on /api/feedback
# ════════════════════════════════════════════════════════════════════════
@pytest_asyncio.fixture
async def auth_token():
    async with httpx.AsyncClient(base_url=_api_base(), timeout=20.0) as cli:
        r = await cli.post(
            "/api/auth/login",
            json={"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"},
        )
        assert r.status_code == 200, r.text
        d = r.json()
        yield d.get("access_token") or d.get("token")


@pytest.mark.asyncio
async def test_legacy_feedback_endpoint_accepts_no_trailing_slash(auth_token):
    """The production trap: POST /api/feedback (no slash) used to return
    307 to http://... which browsers blocked under CSP. It must now
    answer 200 directly."""
    async with httpx.AsyncClient(
        base_url=_api_base(), timeout=15.0, follow_redirects=False
    ) as cli:
        r = await cli.post(
            "/api/feedback",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "Regression",
                "email": f"r+{uuid.uuid4().hex[:6]}@example.com",
                "message": "Regression test message",
                "type": "feedback",
                "rating": "5",
            },
        )
        # No 307 — the dual @router.post("") + @router.post("/") makes
        # the redirect impossible.
        assert r.status_code != 307, (
            f"307 redirect resurfaced — feedback endpoint must answer "
            f"directly at /api/feedback (no slash). Got: {dict(r.headers)}"
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["success"] is True
        assert body.get("request_id"), "request_id must be present in success response"
        assert body.get("id"), "feedback id must be returned"


@pytest.mark.asyncio
async def test_legacy_feedback_endpoint_accepts_trailing_slash(auth_token):
    """Backward compatibility: the trailing-slash URL must still work
    so any existing callers don't regress."""
    async with httpx.AsyncClient(
        base_url=_api_base(), timeout=15.0, follow_redirects=False
    ) as cli:
        r = await cli.post(
            "/api/feedback/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "Regression",
                "email": f"r+{uuid.uuid4().hex[:6]}@example.com",
                "message": "Slash variant message",
                "type": "feedback",
                "rating": "5",
            },
        )
        assert r.status_code == 200, r.text
        assert r.json()["success"] is True


@pytest.mark.asyncio
async def test_legacy_feedback_rejects_empty_message_with_structured_envelope(auth_token):
    """Empty body must surface a structured 400 with code + request_id,
    NOT a bare string. Founder mandate."""
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        r = await cli.post(
            "/api/feedback/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"name": "X", "email": "x@x.com", "message": ""},
        )
        assert r.status_code == 400, r.text
        d = r.json()["detail"]
        assert isinstance(d, dict), "detail must be a structured object, not string"
        assert d["code"] == "FEEDBACK_EMPTY"
        assert d["request_id"]
        assert d["retryable"] is False


@pytest.mark.asyncio
async def test_legacy_feedback_works_for_guest_too(auth_token):
    """Reviews page allows guests to submit feedback — preserve that.
    No Authorization header → must still 200."""
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        r = await cli.post(
            "/api/feedback/",
            json={
                "name": "Guest",
                "email": f"g+{uuid.uuid4().hex[:6]}@example.com",
                "message": "Guest feedback message",
                "type": "feedback",
                "rating": "4",
            },
        )
        assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_suggestion_endpoint_still_works(auth_token):
    """Other feedback subpaths (suggestion, experience) were not the
    source of the bug — but make sure my hardening edits didn't break
    them."""
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        r = await cli.post(
            "/api/feedback/suggestion",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "rating": 5,
                "category": "praise",
                "suggestion": "Looks great",
                "email": "",
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["success"] is True
        assert body.get("request_id"), (
            "suggestion endpoint must also carry request_id in success "
            "envelope (consistency contract)"
        )


# ════════════════════════════════════════════════════════════════════════
# Backend source — structural assertions
# ════════════════════════════════════════════════════════════════════════
def test_legacy_endpoint_registered_at_both_paths():
    """The double-decorator is the structural guarantee against the
    307 redirect trap."""
    src = FEEDBACK_PY.read_text()
    # @router.post("") AND @router.post("/") must both be present,
    # stacked above the legacy handler.
    decorators = re.findall(r'@router\.post\("(?:|/)"\)', src)
    # We expect at least two: one empty-string, one slash. The order
    # matters less than presence.
    assert '@router.post("")' in src, (
        "Legacy feedback endpoint must be registered at '' to avoid the "
        "307→http://... redirect trap"
    )
    assert '@router.post("/")' in src, (
        "Legacy feedback endpoint must also keep '/' registration for "
        "backward compatibility with existing callers"
    )


def test_every_feedback_error_envelope_is_structured_with_request_id():
    """Every HTTPException in routes/feedback.py must use a dict detail
    with a request_id key."""
    src = FEEDBACK_PY.read_text()
    # Count occurrences of structured error envelopes.
    structured_count = src.count('"request_id": rid')
    assert structured_count >= 3, (
        f"Expected ≥3 structured error envelopes in routes/feedback.py "
        f"with request_id; found {structured_count}"
    )
    # The legacy bare-string detail must be GONE.
    assert 'detail="Failed to submit feedback"' not in src, (
        "Legacy bare-string `detail=` must be replaced with structured "
        "envelope"
    )


# ════════════════════════════════════════════════════════════════════════
# Frontend source — request_id contract + shared api client
# ════════════════════════════════════════════════════════════════════════
def test_feedback_form_uses_shared_api_client():
    src = FEEDBACK_FORM_JS.read_text()
    assert "import api from '../utils/api'" in src, (
        "FeedbackForm must use the shared `api` axios client so auth, "
        "request_id capture, and gateway normalization all apply"
    )
    # Raw fetch to /api/feedback must be GONE.
    assert "fetch(`${process.env.REACT_APP_BACKEND_URL}/api/feedback`" not in src, (
        "Raw fetch to /api/feedback (no slash) was the source of the "
        "307→http:// redirect trap. Must use the shared api client."
    )


def test_feedback_form_hits_canonical_trailing_slash_path():
    src = FEEDBACK_FORM_JS.read_text()
    assert "api.post('/api/feedback/'" in src, (
        "FeedbackForm must hit the canonical trailing-slash URL"
    )


def test_feedback_form_surfaces_reference_id_on_every_error_path():
    """Founder mandate (carried over from Photo-to-Comic + Storybook):
    every error toast must render Reference ID."""
    src = FEEDBACK_FORM_JS.read_text()
    handler = src.split("const handleSubmit", 1)[1].split(
        "return (", 1
    )[0]
    # Resolve request_id from envelope, header, or both.
    assert "detail?.request_id" in handler
    assert "x-request-id" in handler.lower()
    # Reference ID must appear in the error path (real id + not-captured).
    rid_renders = handler.count("Reference ID:")
    assert rid_renders >= 2, (
        f"Expected ≥2 Reference ID render sites in FeedbackForm "
        f"catch path; found {rid_renders}"
    )
    # Structured frontend log.
    assert "[feedback-submit] failed" in handler, (
        "FeedbackForm must emit a structured `[feedback-submit] failed` "
        "console log on errors for ops correlation"
    )


def test_feedback_form_keeps_loading_state_for_disabled_submit():
    """Smoke: the submit button is still disabled while loading so we
    don't regress to multiple submits on rapid clicks."""
    src = FEEDBACK_FORM_JS.read_text()
    assert "disabled={loading}" in src, (
        "Submit button must remain disabled while loading"
    )
