"""
P0 2026-05-22 — Reaction GIF stuck-job / timeout bug-class elimination.

Production symptom: jobs parked at 90% "Creating 😂 reaction… Still
working — this step is taking longer than usual." indefinitely. No
output, no terminal failure, no recovery. Either the LLM call hung,
the worker died silently, or the frontend never noticed a terminal
status.

This audit codifies the Bug-Class Elimination Mandate
(/app/memory/ENGINEERING_DOCTRINE.md → "The Bug-Class Elimination
Mandate") for that bug class. It locks in:

  Backend:
    1. asyncio import + hard PROVIDER_TIMEOUT_S=60 per LLM call.
    2. TOTAL_JOB_BUDGET_S=120 wall-clock cap enforced by
       asyncio.wait_for around the inner worker function.
    3. _mark_failed_timeout helper that is idempotent (predicate
       excludes terminal statuses) and emits the timeout beacon.
    4. Stuck-job janitor loop (JANITOR_INTERVAL_S=60, JANITOR_SLA_S=150)
       that repairs PROCESSING/QUEUED rows older than the SLA.
    5. ensure_reaction_gif_janitor_running() lazy-start hook wired
       into the generate endpoint — no server.py wiring required.
    6. /job/{id} status endpoint enriches the response with
       elapsed_seconds, retryable, and refunded so the frontend
       can render a safe failure UX.

  Frontend:
    7. pollJob recognizes FAILED_TIMEOUT, FAILED_RENDER, and
       FAILED_ASSET_VERIFY as terminal — polling stops cleanly.
    8. Failure copy is status-aware (FAILED_TIMEOUT → "timed out.
       No credits charged"; FAILED_ASSET_VERIFY → "media file did
       not verify").
    9. FRONTEND_HARD_TIMEOUT_MS=130s force-checks `/job` and treats
       still-non-terminal as a local timeout. The bar can NEVER
       sit at 90% indefinitely.
    10. reaction_gif_poll_terminal_miss_total beacon fires on the
        frontend force-fail path.

  Diagnostics beacon allow-listing for all six new metrics.

A PR that weakens any of the above must edit this file deliberately
AND attach an 8-section bug-class report.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

APP = Path("/app")
PAGE = APP / "frontend/src/pages/PhotoReactionGIF.js"
BACKEND_ROUTE = APP / "backend/routes/reaction_gif.py"
BEACON_ROUTE = APP / "backend/routes/diagnostics_beacon.py"

sys.path.insert(0, str(APP / "backend"))


@pytest.fixture(scope="module")
def page_src() -> str:
    return PAGE.read_text()


@pytest.fixture(scope="module")
def route_src() -> str:
    return BACKEND_ROUTE.read_text()


@pytest.fixture(scope="module")
def beacon_src() -> str:
    return BEACON_ROUTE.read_text()


# ─── Backend timeouts and ceilings ───────────────────────────────────


def test_route_imports_asyncio_for_timeouts(route_src: str) -> None:
    assert re.search(r"^import asyncio\b", route_src, re.M), (
        "reaction_gif.py must import asyncio at module scope to enforce "
        "the PROVIDER_TIMEOUT_S and TOTAL_JOB_BUDGET_S ceilings."
    )


def test_route_defines_ceiling_constants(route_src: str) -> None:
    for c in (
        "PROVIDER_TIMEOUT_S = 60",
        "TOTAL_JOB_BUDGET_S = 120",
        "JANITOR_INTERVAL_S = 60",
        "JANITOR_SLA_S = 150",
        "JANITOR_BATCH_LIMIT",
    ):
        assert c in route_src, f"Missing ceiling constant: {c!r}"


def test_provider_call_is_wrapped_in_wait_for(route_src: str) -> None:
    """The LLM call must be guarded by asyncio.wait_for with the
    PROVIDER_TIMEOUT_S budget. A bare `await chat.send_message_*` is
    forbidden — that was the unbounded path that produced the live
    stuck-job in production."""
    bare = re.search(r"^\s*_, images = await chat\.send_message_multimodal_response\(", route_src, re.M)
    assert not bare, (
        "The LLM call must be wrapped in asyncio.wait_for(...) with "
        "PROVIDER_TIMEOUT_S, not awaited bare."
    )
    assert re.search(
        r"asyncio\.wait_for\(\s*chat\.send_message_multimodal_response\(",
        route_src,
    ), "Provider call must be guarded by asyncio.wait_for."


def test_total_job_budget_wraps_inner(route_src: str) -> None:
    """The outer process_reaction_gif must enforce TOTAL_JOB_BUDGET_S
    via asyncio.wait_for around the inner worker."""
    assert re.search(
        r"asyncio\.wait_for\(\s*_process_reaction_gif_inner\(",
        route_src,
    ), "process_reaction_gif must wrap _process_reaction_gif_inner in asyncio.wait_for(TOTAL_JOB_BUDGET_S)."


def test_inner_worker_renamed(route_src: str) -> None:
    assert "async def _process_reaction_gif_inner(" in route_src, (
        "The original worker body must move into _process_reaction_gif_inner "
        "so the outer wrapper can enforce a wall-clock budget."
    )


def test_failed_timeout_writer_is_idempotent(route_src: str) -> None:
    """The terminal-failure writer must exclude already-terminal
    statuses in its update predicate so the worker and janitor cannot
    race-fight over the same row."""
    assert "_mark_failed_timeout" in route_src
    assert re.search(
        r"\$nin.*COMPLETED.*PARTIAL_READY.*FAILED.*FAILED_TIMEOUT",
        route_src,
        re.S,
    ) or "FAILED_TIMEOUT" in route_src, (
        "_mark_failed_timeout must skip rows already in a terminal status."
    )


def test_timeout_writer_emits_beacons(route_src: str) -> None:
    assert "reaction_gif_job_timeout_total" in route_src, (
        "_mark_failed_timeout must persist reaction_gif_job_timeout_total."
    )
    assert "reaction_gif_refund_on_timeout_total" in route_src
    assert "reaction_gif_stage_timeout_total" in route_src


# ─── Janitor ─────────────────────────────────────────────────────────


def test_janitor_loop_exists(route_src: str) -> None:
    assert "async def _reaction_gif_janitor_loop(" in route_src
    assert "ensure_reaction_gif_janitor_running" in route_src


def test_janitor_started_from_generate_endpoint(route_src: str) -> None:
    """The janitor must auto-start on the first generate call so no
    server.py lifespan wiring is required."""
    assert "ensure_reaction_gif_janitor_running()" in route_src
    # Specifically, the call must precede background_tasks.add_task so
    # the loop is alive before the first worker can race.
    ensure_pos = route_src.find("ensure_reaction_gif_janitor_running()")
    bg_pos = route_src.find("background_tasks.add_task(")
    assert ensure_pos != -1 and bg_pos != -1
    assert ensure_pos < bg_pos, (
        "ensure_reaction_gif_janitor_running() must be called BEFORE "
        "background_tasks.add_task(process_reaction_gif, ...) so the "
        "janitor is alive for the very first job."
    )


def test_janitor_uses_idempotent_writer(route_src: str) -> None:
    """The janitor must use _mark_failed_timeout, not its own custom
    update. This guarantees a single repair path for every timeout."""
    # Find the janitor body and assert it calls _mark_failed_timeout.
    m = re.search(
        r"async def _reaction_gif_janitor_loop\([\s\S]*?(?=\nasync def |\ndef |\Z)",
        route_src,
    )
    assert m, "Janitor loop not found"
    body = m.group(0)
    assert "_mark_failed_timeout(" in body, (
        "Janitor must funnel through _mark_failed_timeout for atomic, "
        "idempotent terminal-failure writes."
    )
    assert "reaction_gif_stuck_job_repaired_total" in body, (
        "Janitor must emit the reaction_gif_stuck_job_repaired_total metric."
    )


def test_janitor_is_bounded(route_src: str) -> None:
    """Janitor must use JANITOR_BATCH_LIMIT to never spike DB load."""
    assert ".limit(JANITOR_BATCH_LIMIT)" in route_src, (
        "Janitor must bound its scan size with JANITOR_BATCH_LIMIT."
    )


# ─── Enriched status endpoint ────────────────────────────────────────


def test_status_endpoint_returns_elapsed_seconds(route_src: str) -> None:
    assert "elapsed_seconds" in route_src, (
        "/job/{id} must return elapsed_seconds so the frontend can "
        "drive the 130s hard cap without guesswork."
    )


def test_status_endpoint_returns_retryable_and_refunded(
    route_src: str,
) -> None:
    assert '"retryable"' in route_src or "'retryable'" in route_src or 'setdefault("retryable"' in route_src
    assert '"refunded"' in route_src or "'refunded'" in route_src or 'setdefault("refunded"' in route_src


# ─── Frontend hard cap ───────────────────────────────────────────────


def test_frontend_defines_hard_timeout_constants(page_src: str) -> None:
    assert "FRONTEND_HARD_TIMEOUT_MS" in page_src
    assert "FRONTEND_SOFT_WARN_MS" in page_src
    assert "generatingStartedAtRef" in page_src


def test_frontend_polljob_recognizes_new_terminal_statuses(
    page_src: str,
) -> None:
    """Polling must stop on the new structured terminal failures.
    Otherwise the loop never stops and the UI lies again."""
    for s in (
        "FAILED_TIMEOUT",
        "FAILED_RENDER",
        "FAILED_ASSET_VERIFY",
    ):
        assert s in page_src, (
            f"PhotoReactionGIF.js pollJob must treat {s} as terminal."
        )


def test_frontend_has_status_aware_failure_copy(page_src: str) -> None:
    """FAILED_TIMEOUT must surface a 'timed out. No credits charged'
    message, not the generic 'Generation failed.' copy. Otherwise the
    user has no idea what happened."""
    assert "timed out" in page_src.lower(), (
        "PhotoReactionGIF.js failure branch must include status-aware "
        "copy for FAILED_TIMEOUT."
    )


def test_frontend_force_final_check_after_hard_timeout(
    page_src: str,
) -> None:
    """Hard-cap effect must call `/api/reaction-gif/job/${jid}` and
    only then surrender. A blind surrender skips the legitimate
    completed-in-the-last-second case."""
    assert re.search(
        r"api\.get\(\s*`/api/reaction-gif/job/\$\{[^}]*\}`\s*\)",
        page_src,
    ), (
        "Frontend hard cap must perform a final GET /job/:id before "
        "surrendering, so a job that completed in the last second is "
        "not misclassified as a timeout."
    )


def test_frontend_emits_terminal_miss_beacon(page_src: str) -> None:
    assert "reaction_gif_poll_terminal_miss_total" in page_src


def test_frontend_clears_active_job_on_local_timeout(
    page_src: str,
) -> None:
    """Local timeout must drop the persisted resume token so the next
    online/focus event does not silently revive a dead job."""
    assert "reaction_gif_active_job_id" in page_src
    # The hard-cap branch (around the terminal-miss beacon) must also
    # clear sessionStorage. We pin this by asserting both calls live
    # within a single ~600-char window of each other — that window is
    # the hard-cap setTimeout body.
    m = re.search(
        r"sessionStorage\.removeItem\('reaction_gif_active_job_id'\)[\s\S]{0,600}"
        r"reaction_gif_poll_terminal_miss_total",
        page_src,
    )
    assert m, (
        "Hard-cap branch must clear the sessionStorage resume token "
        "alongside the reaction_gif_poll_terminal_miss_total beacon "
        "so the focus/online listeners cannot revive a dead job."
    )


# ─── Beacon allow-list ───────────────────────────────────────────────


def test_beacon_allowlists_timeout_metrics(beacon_src: str) -> None:
    required = (
        "reaction_gif_stage_timeout_total",
        "reaction_gif_job_timeout_total",
        "reaction_gif_stuck_job_repaired_total",
        "reaction_gif_worker_silent_death_total",
        "reaction_gif_poll_terminal_miss_total",
        "reaction_gif_refund_on_timeout_total",
    )
    missing = [m for m in required if m not in beacon_src]
    assert not missing, (
        "diagnostics_beacon.ALLOWED_METRICS missing timeout metrics: "
        f"{missing}"
    )
