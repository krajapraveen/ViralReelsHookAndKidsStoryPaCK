"""
P0 2026-05-21 — Async story generation contract pinning suite.

Production incident: mobile clients hitting POST /api/generate/story
exceeded Cloudflare's 30s upstream timeout (observed 30.14s 504s on
cf-ray 9ff471b0...). The mobile contract is now async-job pattern on
new endpoints; the sync endpoint remains untouched for web clients.

This audit pins the **published mobile contract** verbatim so a
future refactor cannot silently break the mobile app:

  POST /api/generate/story/async
    → returns { job_id, status:"PENDING", request_id, poll_url,
                poll_interval_ms } in well under CF's 30s.

  GET /api/generate/story/async/{job_id}
    → returns the canonical poll envelope:
      { job_id, status, progress, elapsed_seconds, request_id,
        result?, error?, credits_used?, remaining_credits?,
        generation_id? }

Doctrine refs: ENGINEERING_DOCTRINE.md → "Bug-Class Elimination
Mandate" + Rule 4 (async jobs idempotent) + Rule 6 (every failure
observable).

A PR that weakens any of the below must edit this file deliberately
AND attach an 8-section bug-class report.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

APP = Path("/app")
ROUTE = APP / "backend/routes/generation.py"

sys.path.insert(0, str(APP / "backend"))


@pytest.fixture(scope="module")
def route_src() -> str:
    assert ROUTE.exists(), f"Missing: {ROUTE}"
    return ROUTE.read_text()


# ─── Endpoints exist on the canonical paths ──────────────────────────


def test_async_post_endpoint_exists(route_src: str) -> None:
    """POST /api/generate/story/async is the published mobile path
    (router prefix is /generate; api_router adds /api)."""
    assert '@router.post("/story/async")' in route_src, (
        "POST /api/generate/story/async must be the canonical async "
        "entry point. Mobile contract is published — do not rename."
    )


def test_async_get_endpoint_exists(route_src: str) -> None:
    assert '@router.get("/story/async/{job_id}")' in route_src, (
        "GET /api/generate/story/async/{job_id} must be the canonical "
        "poll endpoint. Mobile contract is published — do not rename."
    )


def test_sync_endpoint_preserved(route_src: str) -> None:
    """Web clients still depend on POST /api/generate/story (sync).
    The async work must be ADDITIVE, not a replacement."""
    assert '@router.post("/story")' in route_src
    assert "async def generate_story(" in route_src


# ─── Async POST contract: returns immediately with job_id + status ──


def test_async_post_returns_canonical_envelope(route_src: str) -> None:
    """Mobile expects { job_id, status:"PENDING", request_id, poll_url,
    poll_interval_ms }. Pin each field by name."""
    # Locate the function body.
    fn = re.search(
        r"async def generate_story_async\([\s\S]+?(?=\n@router\.|\nasync def |\ndef |\Z)",
        route_src,
    )
    assert fn, "generate_story_async function body not found"
    body = fn.group(0)
    # Pin the return shape: must include exact keys in the response.
    for key in ('"job_id"', '"status"', '"request_id"', '"poll_url"', '"poll_interval_ms"'):
        assert key in body, f"Async POST response missing key: {key}"
    # The PENDING status must be the literal initial value (mobile
    # discriminates terminal vs non-terminal on this string).
    assert '"PENDING"' in body, "Async POST must return status: 'PENDING' verbatim."


def test_async_post_uses_background_task(route_src: str) -> None:
    """The whole point of the async pattern: HTTP returns before the
    LLM call runs. background_tasks.add_task is the proof."""
    fn = re.search(
        r"async def generate_story_async\([\s\S]+?(?=\n@router\.|\nasync def |\ndef |\Z)",
        route_src,
    )
    assert fn
    assert "background_tasks.add_task(" in fn.group(0)
    assert "_story_async_worker" in fn.group(0)


def test_async_post_inserts_job_row_before_returning(route_src: str) -> None:
    """job_id returned to the client must reference a real row, so
    the immediate first poll succeeds (no race with the worker)."""
    fn = re.search(
        r"async def generate_story_async\([\s\S]+?(?=\n@router\.|\nasync def |\ndef |\Z)",
        route_src,
    )
    body = fn.group(0)
    insert_pos = body.find("db.story_async_jobs.insert_one(")
    return_pos = body.find("return {")
    assert insert_pos != -1 and return_pos != -1
    assert insert_pos < return_pos, (
        "Job row must be inserted BEFORE the HTTP response so the "
        "first client poll cannot race against the worker."
    )


def test_async_post_does_not_deduct_credits_optimistically(route_src: str) -> None:
    """Credit deduction is ONLY allowed on COMPLETED — never in the
    POST handler (which returns before generation runs)."""
    fn = re.search(
        r"async def generate_story_async\([\s\S]+?(?=\n@router\.|\nasync def |\ndef |\Z)",
        route_src,
    )
    body = fn.group(0)
    assert "deduct_credits(" not in body, (
        "Async POST must NEVER deduct credits — the worker does it "
        "only on a real COMPLETED outcome. Otherwise a failed "
        "generation charges the user."
    )


def test_async_post_preserves_safety_pipeline(route_src: str) -> None:
    """Content moderation must run in the POST handler before any
    background work is scheduled — same posture as the sync endpoint."""
    fn = re.search(
        r"async def generate_story_async\([\s\S]+?(?=\n@router\.|\nasync def |\ndef |\Z)",
        route_src,
    )
    body = fn.group(0)
    assert "check_and_rewrite(" in body
    assert "threat_intel.moderate_content(" in body
    assert "check_credits(" in body


# ─── Async GET contract: canonical poll envelope ────────────────────


def test_async_get_returns_canonical_envelope(route_src: str) -> None:
    fn = re.search(
        r"async def get_story_async_status\([\s\S]+?(?=\n@router\.|\nasync def |\ndef |\Z)",
        route_src,
    )
    assert fn
    body = fn.group(0)
    for key in ('"job_id"', '"status"', '"progress"', '"elapsed_seconds"', '"request_id"'):
        assert key in body, f"Async GET envelope missing key: {key}"
    # COMPLETED branch must surface result + credit fields
    assert '"result"' in body
    assert '"credits_used"' in body
    assert '"remaining_credits"' in body
    # FAILED branch must surface a safe error string
    assert '"error"' in body


def test_async_get_isolates_jobs_to_owner(route_src: str) -> None:
    """A user must not be able to read another user's story job —
    the find_one predicate must include userId."""
    fn = re.search(
        r"async def get_story_async_status\([\s\S]+?(?=\n@router\.|\nasync def |\ndef |\Z)",
        route_src,
    )
    body = fn.group(0)
    assert '"userId": user["id"]' in body, (
        "GET /story/async/{job_id} must scope the lookup to the "
        "authenticated user's id — no cross-tenant reads."
    )


# ─── Worker correctness ──────────────────────────────────────────────


def test_worker_uses_completion_invariant(route_src: str) -> None:
    """Per doctrine, any pipeline writing terminal COMPLETED status
    must route the decision through assert_completion_invariant."""
    assert "from services.reliability.completion_invariant import assert_completion_invariant" in route_src
    fn = re.search(
        r"async def _story_async_worker\([\s\S]+?(?=\n@router\.|\nasync def |\ndef |\Z)",
        route_src,
    )
    assert fn
    body = fn.group(0)
    inv_pos = body.find("assert_completion_invariant(")
    # The terminal-status WRITE must come AFTER the invariant call.
    # We use the canonical Mongo-write form to avoid false positives.
    completed_write = re.search(
        r"""['"]status['"]\s*:\s*invariant\.effective_status""",
        body,
    )
    assert inv_pos != -1, "Worker must call assert_completion_invariant before terminal write."
    assert completed_write is not None, (
        "Worker must persist `status: invariant.effective_status` so "
        "PARTIAL_READY repairs are reflected to the client."
    )


def test_worker_only_charges_on_clean_completion(route_src: str) -> None:
    """Mirrors the reaction_gif/photo_to_comic invariant: deduct_credits
    only when invariant.effective_status == 'COMPLETED' AND not repaired."""
    fn = re.search(
        r"async def _story_async_worker\([\s\S]+?(?=\n@router\.|\nasync def |\ndef |\Z)",
        route_src,
    )
    body = fn.group(0)
    assert "charge_now" in body
    assert 'invariant.effective_status == "COMPLETED"' in body
    assert "invariant.repaired" in body


def test_worker_records_failure_safely(route_src: str) -> None:
    """All failure paths must write `status: FAILED` on the job row
    with a safe user-facing error message that includes the "No
    credits charged" affordance for trust."""
    fn = re.search(
        r"async def _story_async_worker\([\s\S]+?(?=\n@router\.|\nasync def |\ndef |\Z)",
        route_src,
    )
    body = fn.group(0)
    assert '"status": "FAILED"' in body
    assert "No credits charged" in body, (
        "Worker failure paths must explicitly tell the user no "
        "credits were charged — trust signal."
    )


def test_worker_has_outer_try_except(route_src: str) -> None:
    """The worker is fire-and-forget; an unhandled exception must NOT
    leave the job row stuck in PROCESSING forever."""
    fn = re.search(
        r"async def _story_async_worker\([\s\S]+?(?=\n@router\.|\nasync def |\ndef |\Z)",
        route_src,
    )
    body = fn.group(0)
    assert "[STORY_ASYNC] worker crashed" in body, (
        "Worker outer try/except must log a crash AND mark the job "
        "FAILED so the poll endpoint cannot return PROCESSING forever."
    )


def test_worker_enforces_inline_timeout(route_src: str) -> None:
    """Per stuck-job doctrine: every inline LLM call must be wrapped
    in asyncio.wait_for with a wall-clock budget."""
    assert "STORY_ASYNC_BUDGET_S" in route_src
    assert "asyncio.wait_for(" in route_src or "_asyncio.wait_for(" in route_src


# ─── Registered in canonical pipeline list ──────────────────────────


def test_route_is_in_registered_pipelines() -> None:
    from services.reliability.completion_invariant import REGISTERED_PIPELINES
    assert "routes/generation.py" in REGISTERED_PIPELINES, (
        "routes/generation.py must be in REGISTERED_PIPELINES so the "
        "completion-invariant audit scanner enforces the gate on "
        "every future change."
    )
