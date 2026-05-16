"""
P0 2026-05-19 — Comic Story Book "Your comic is already generating" lock-trap.
==============================================================================
Production screenshot showed a user permanently trapped on the Preview &
Generate step with the dead toast "Your comic is already generating.
Please wait a moment and try again."

ROOT CAUSE
----------
The /generate endpoint inserts an idempotency row with status=PENDING
BEFORE the comic_storybook_v2_jobs row. If the request died between
those two writes (asyncio.CancelledError from a client disconnect,
worker OOM, supervisor restart), the PENDING row sat for up to
STALE_PENDING_MINUTES (was 10 min) and the job row never landed.
A retry within that window hit:
  is_dup=True, cached=None, no existing_job → HTTP 409
…and the frontend's history fallback found nothing → dead toast.

LOCKED-IN CONTRACT
------------------
1. Stale PENDING TTL is 2 minutes (was 10).
2. Source-level: /generate has a `except BaseException` catch that
   marks the idempotency key FAILED so client-disconnect /
   CancelledError can never leave a soft-lock behind.
3. Source-level: when is_dup=True + cached=None + no existing_job,
   /generate AUTO-RECOVERS the orphan PENDING row and proceeds as a
   fresh submit instead of returning 409.
4. Every error envelope on /generate carries a structured `code`,
   `message`, `request_id`, `retryable` shape.
5. The legitimate in-flight resumption returns
   `code: EXISTING_ACTIVE_JOB` (200, not 409) so the frontend can
   silently attach to progress without showing an error toast.
6. Frontend `submittingRef` synchronously guards against double-clicks
   (state-batching can't trip the race).
"""
from __future__ import annotations

import re
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, "/app/backend")

from services.idempotency_service import IdempotencyService  # noqa: E402


COMIC_STORYBOOK_BUILDER_JS = Path("/app/frontend/src/pages/ComicStorybookBuilder.js")
COMIC_STORYBOOK_V2_PY = Path("/app/backend/routes/comic_storybook_v2.py")


def _read_backend_env():
    text = Path("/app/backend/.env").read_text()
    mongo = re.search(r"^MONGO_URL=(.*)$", text, flags=re.M).group(1).strip().strip('"')
    dbn = re.search(r"^DB_NAME=(.*)$", text, flags=re.M).group(1).strip().strip('"')
    return mongo, dbn


@pytest_asyncio.fixture
async def db():
    mongo, dbn = _read_backend_env()
    client = AsyncIOMotorClient(mongo)
    yield client[dbn]
    client.close()


@pytest_asyncio.fixture
async def idem(db):
    svc = IdempotencyService(db)
    yield svc


# ════════════════════════════════════════════════════════════════════════
# 1. Stale PENDING TTL is 2 minutes (was 10)
# ════════════════════════════════════════════════════════════════════════
def test_stale_pending_ttl_was_reduced_to_two_minutes():
    """Production trap: 10-minute soft-lock. New ceiling: 2 minutes."""
    assert IdempotencyService.STALE_PENDING_MINUTES == 2, (
        "STALE_PENDING_MINUTES must be 2 — anything higher reproduces the "
        "production lock-trap. Was 10, now 2."
    )


# ════════════════════════════════════════════════════════════════════════
# 2. Idempotency unit contract (these were already correct — pinned)
# ════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_first_submit_is_not_a_duplicate(idem, db):
    key = f"lock-recover-first-{uuid.uuid4().hex[:8]}"
    await db.idempotency_keys.delete_one({"key": key})
    is_dup, cached = await idem.check_and_store(key)
    assert is_dup is False
    assert cached is None
    await db.idempotency_keys.delete_one({"key": key})


@pytest.mark.asyncio
async def test_fresh_pending_blocks_duplicate(idem, db):
    """A fresh PENDING is a real in-flight request — duplicate must wait."""
    key = f"lock-recover-pending-{uuid.uuid4().hex[:8]}"
    await db.idempotency_keys.delete_one({"key": key})
    await idem.check_and_store(key)
    is_dup, cached = await idem.check_and_store(key)
    assert is_dup is True
    assert cached is None
    await db.idempotency_keys.delete_one({"key": key})


@pytest.mark.asyncio
async def test_pending_older_than_two_minutes_auto_recovers(idem, db):
    """A PENDING older than the new 2-minute ceiling MUST auto-recover."""
    key = f"lock-recover-stale-{uuid.uuid4().hex[:8]}"
    await db.idempotency_keys.delete_one({"key": key})
    await idem.check_and_store(key)
    # Backdate beyond the new threshold.
    stale = (datetime.now(timezone.utc) - timedelta(minutes=3)).isoformat()
    await db.idempotency_keys.update_one(
        {"key": key}, {"$set": {"createdAt": stale}}
    )
    is_dup, _ = await idem.check_and_store(key)
    assert is_dup is False, (
        "stale PENDING must auto-recover under the new 2-minute ceiling"
    )
    await db.idempotency_keys.delete_one({"key": key})


@pytest.mark.asyncio
async def test_pending_younger_than_two_minutes_still_blocks(idem, db):
    """Defense: a 1-minute-old PENDING must NOT be considered stale."""
    key = f"lock-recover-fresh-{uuid.uuid4().hex[:8]}"
    await db.idempotency_keys.delete_one({"key": key})
    await idem.check_and_store(key)
    near = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    await db.idempotency_keys.update_one(
        {"key": key}, {"$set": {"createdAt": near}}
    )
    is_dup, _ = await idem.check_and_store(key)
    assert is_dup is True, (
        "a 1-minute-old PENDING is still in-flight; do not auto-recover"
    )
    await db.idempotency_keys.delete_one({"key": key})


@pytest.mark.asyncio
async def test_failed_pending_auto_recovers(idem, db):
    """FAILED status must allow retries — this is the simple admin-retry path."""
    key = f"lock-recover-failed-{uuid.uuid4().hex[:8]}"
    await db.idempotency_keys.delete_one({"key": key})
    await idem.check_and_store(key)
    await idem.mark_failed(key, "synthetic")
    is_dup, _ = await idem.check_and_store(key)
    assert is_dup is False
    await db.idempotency_keys.delete_one({"key": key})


# ════════════════════════════════════════════════════════════════════════
# 3. Source-level — backend route hardening
# ════════════════════════════════════════════════════════════════════════
def test_generate_route_imports_request_for_request_id():
    """The route MUST take the FastAPI Request so it can pull the
    correlation id stamped by the reliability middleware."""
    src = COMIC_STORYBOOK_V2_PY.read_text()
    assert "http_request: Request" in src, (
        "Storybook /generate must accept a Request object so request_id "
        "can be plumbed into every error envelope"
    )
    assert "from middleware.reliability import get_request_id" in src, (
        "request_id resolution must use the canonical middleware accessor"
    )


def test_generate_route_catches_base_exception_for_cancellation():
    """asyncio.CancelledError inherits from BaseException, not Exception.
    The ONLY way to release the PENDING idempotency row on a client
    disconnect / worker restart is a BaseException catch."""
    src = COMIC_STORYBOOK_V2_PY.read_text()
    assert "except BaseException" in src, (
        "Without `except BaseException`, asyncio.CancelledError can leave "
        "an orphan PENDING idempotency row → reproduces the production trap"
    )
    # The catch must call mark_failed before re-raising so the lock is
    # immediately released.
    bx_block = src.split("except BaseException", 1)[1].split("\n\n", 1)[0]
    assert "mark_failed" in bx_block, (
        "BaseException catch must release the idempotency lock before re-raise"
    )
    assert "raise" in bx_block, (
        "BaseException catch must re-raise so cancellation isn't swallowed"
    )


def test_generate_route_recovers_orphan_pending_instead_of_409():
    """Founder spec: when is_dup + no cached + no existing_job, the prior
    request is presumed dead. Auto-recover and proceed; never 409 here."""
    src = COMIC_STORYBOOK_V2_PY.read_text()
    assert "orphan PENDING idempotency recovered" in src, (
        "Orphan-PENDING auto-recovery branch is the canonical fix for the "
        "production lock-trap. Must be present and logged."
    )
    # The legacy 409 line must NOT exist in the recovery path.
    assert "Duplicate request in progress" not in src, (
        "Legacy 409 'Duplicate request in progress' should be removed — it "
        "was the production dead-toast source"
    )


def test_generate_route_returns_existing_active_job_envelope():
    """Legitimate in-flight resumption = 200 with code:EXISTING_ACTIVE_JOB,
    NOT a 409 error. Frontend silently attaches to progress."""
    src = COMIC_STORYBOOK_V2_PY.read_text()
    assert '"code": "EXISTING_ACTIVE_JOB"' in src, (
        "In-flight resumption must use the structured EXISTING_ACTIVE_JOB "
        "envelope so the frontend can attach to progress without an error"
    )


def test_every_generate_error_envelope_carries_request_id():
    """Founder mandate: request_id on every error path."""
    src = COMIC_STORYBOOK_V2_PY.read_text()
    # Pluck just the /generate route body.
    route = src.split('@router.post("/generate")', 1)[1].split("\n\n@router.", 1)[0]
    # Every HTTPException with a dict detail must include request_id.
    # Sanity floor: at least 6 distinct request_id placements (BLOCKED_CONTENT
    # idea, BLOCKED_CONTENT title, SAFETY_BLOCKED, GUARDRAIL_BLOCKED,
    # ADMISSION_REJECTED, DEGRADATION_BLOCKED, GENERATE_FAILED, INSUFFICIENT_CREDITS).
    rid_count = route.count('"request_id": rid') + route.count('"request_id"')
    assert rid_count >= 6, (
        f"Expected ≥6 request_id placements in /generate envelopes; found {rid_count}"
    )


def test_insufficient_credits_envelope_is_normalized_with_request_id():
    """The legacy `require_credits` raises a HTTPException with a STRING
    detail. The route now wraps it into the structured shape so the user
    gets a Reference ID on the credit-block toast."""
    src = COMIC_STORYBOOK_V2_PY.read_text()
    block = src.split('require_credits(user, cost=cost', 1)[1].split("# ── 6.", 1)[0]
    assert "INSUFFICIENT_CREDITS" in block
    assert "request_id" in block


# ════════════════════════════════════════════════════════════════════════
# 4. Frontend wiring — synchronous double-submit guard + recovery surface
# ════════════════════════════════════════════════════════════════════════
def test_frontend_uses_submitting_ref_for_synchronous_double_click_guard():
    src = COMIC_STORYBOOK_BUILDER_JS.read_text()
    assert "submittingRef" in src, (
        "submittingRef is required — React state batching can let two "
        "rapid clicks slip past `loading` before the first re-render"
    )
    # The ref must be checked AND set BEFORE any await.
    handler = src.split("const generateComicBook = async () => {", 1)[1].split(
        "// Download handler", 1
    )[0]
    assert "submittingRef.current" in handler.split("await", 1)[0], (
        "submittingRef must be flipped synchronously, before any await"
    )
    assert "submittingRef.current = false" in handler, (
        "submittingRef must be released — every early-return AND finally"
    )


def test_frontend_distinguishes_existing_active_job_from_dead_toast():
    src = COMIC_STORYBOOK_BUILDER_JS.read_text()
    assert "EXISTING_ACTIVE_JOB" in src, (
        "Frontend must recognise the structured in-flight resumption code"
    )
    # The legacy dead toast string must be GONE — the only remaining
    # place "already generating" appears is the success/info toast for
    # legitimate resumption.
    error_toasts = [
        m for m in re.findall(r"toast\.error\([^)]*\)", src) if "already generating" in m
    ]
    assert not error_toasts, (
        f"Dead 'already generating' error toast still present: {error_toasts}. "
        "Replace with structured EXISTING_ACTIVE_JOB silent attach."
    )


def test_frontend_surfaces_reference_id_on_every_error_path():
    """Founder mandate (carried over from Photo-to-Comic): every error
    toast in generateComicBook must render `Reference ID:` (real or
    not-captured sentinel)."""
    src = COMIC_STORYBOOK_BUILDER_JS.read_text()
    handler = src.split("const generateComicBook = async () => {", 1)[1].split(
        "// Download handler", 1
    )[0]
    # Resolve a request_id from the envelope, header, or both.
    assert "x-request-id" in handler.lower()
    assert "data?.request_id" in handler or "detail?.request_id" in handler
    # Reference ID must appear on the 409 path, the structured path,
    # the network path, and the catch-all path → ≥4.
    rid_renders = handler.count("Reference ID:")
    assert rid_renders >= 4, (
        f"Expected ≥4 Reference ID render sites in generateComicBook; "
        f"found {rid_renders}"
    )


def test_frontend_releases_loading_on_every_error_path():
    """The button is disabled by `loading`. If we forget to setLoading(false)
    on any error path the user is permanently trapped client-side."""
    src = COMIC_STORYBOOK_BUILDER_JS.read_text()
    handler = src.split("const generateComicBook = async () => {", 1)[1].split(
        "// Download handler", 1
    )[0]
    catch_block = handler.split("} catch (e) {", 1)[1].split("} finally {", 1)[0]
    # Every `return;` in the catch block (early exits) must be preceded
    # by a setLoading(false) within a few lines.
    # Simple heuristic: count the `setLoading(false)` calls in the catch
    # — must be at least one per non-success branch (409 attach, structured
    # error, network, fallback).
    assert catch_block.count("setLoading(false)") >= 4, (
        "Each error early-return in the catch block must release `loading` "
        "first"
    )


def test_frontend_finally_releases_submitting_ref():
    """The submittingRef MUST be cleared in a finally block so a transient
    error never permanently locks the button."""
    src = COMIC_STORYBOOK_BUILDER_JS.read_text()
    handler = src.split("const generateComicBook = async () => {", 1)[1].split(
        "// Download handler", 1
    )[0]
    assert "} finally {" in handler, "Missing finally block"
    finally_block = handler.split("} finally {", 1)[1].split("};", 1)[0]
    assert "submittingRef.current = false" in finally_block, (
        "submittingRef must be released in finally — protects against any "
        "uncaught path leaving the button locked"
    )


def test_generate_button_is_disabled_by_loading_state():
    """The visible Generate button must consult the `loading` state so
    React's first re-render after click drops the button."""
    src = COMIC_STORYBOOK_BUILDER_JS.read_text()
    # Locate the Generate Full Comic Book button.
    btn_block = src.split("Generate Full Comic Book", 1)[0]
    # Walk back from the marker to find the most recent `disabled=` and
    # `data-testid` attributes.
    near = btn_block[-800:]
    assert 'data-testid="generate-btn"' in near, (
        "Generate button must keep the canonical generate-btn testid"
    )
    assert "disabled={loading" in near, (
        "Generate button must be disabled while loading=true"
    )
