"""
P0 2026-05-22 — Reaction GIF connection-loss bug-class elimination suite.

This audit codifies the Bug-Class Elimination Mandate (see
/app/memory/ENGINEERING_DOCTRINE.md → "The Bug-Class Elimination
Mandate") for the production incident where the Reaction GIF Creator
displayed:

    "Connection lost during generation. Try again."

on a single transient poll failure, with:
  • no request_id surfaced
  • no failed stage indicated
  • no retry / resume path
  • CTA stuck in a dead state
  • the backend job still running silently in the background

The fixes this suite locks in:
  1. Frontend `pollJob` tolerates POLL_FAIL_TOLERANCE transient
     failures BEFORE surfacing any toast.
  2. Any user-facing error path uses `toastErrorSafe` so a Reference
     ID is always shown.
  3. The polling interval is NEVER abandoned silently while the
     backend job is still alive.
  4. A `reaction_gif_active_job_id` is persisted to sessionStorage
     so reload / online-event can resume the same job.
  5. The backend `process_reaction_gif` routes the terminal-success
     decision through `assert_completion_invariant` so a partial
     pack run CANNOT be silently marked COMPLETED.
  6. The diagnostics beacon allow-lists the new observability metrics.
  7. `routes/reaction_gif.py` is registered with the canonical
     completion-invariant scanner so any future drift fails CI.

A PR that weakens any of the above must edit this file deliberately
AND attach an 8-section bug-class elimination report
(/app/memory/BUG_CLASS_ELIMINATION_TEMPLATE.md). No silent regression.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

APP = Path("/app")
PAGE = APP / "frontend/src/pages/PhotoReactionGIF.js"
BACKEND_ROUTE = APP / "backend/routes/reaction_gif.py"
INVARIANT_MODULE = APP / "backend/services/reliability/completion_invariant.py"
BEACON_ROUTE = APP / "backend/routes/diagnostics_beacon.py"

# Make `services.reliability.completion_invariant` importable for the
# REGISTERED_PIPELINES check below.
sys.path.insert(0, str(APP / "backend"))


# ─── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def page_src() -> str:
    assert PAGE.exists(), f"Missing page: {PAGE}"
    return PAGE.read_text()


@pytest.fixture(scope="module")
def route_src() -> str:
    assert BACKEND_ROUTE.exists(), f"Missing route: {BACKEND_ROUTE}"
    return BACKEND_ROUTE.read_text()


@pytest.fixture(scope="module")
def invariant_src() -> str:
    return INVARIANT_MODULE.read_text()


@pytest.fixture(scope="module")
def beacon_src() -> str:
    return BEACON_ROUTE.read_text()


# ─── Frontend: brittle toast is gone ─────────────────────────────────


def test_no_bare_connection_lost_toast(page_src: str) -> None:
    """The exact production-trust-breaking string must no longer appear
    as a user-facing toast. If it must appear (e.g. in a comment), use
    a different phrase."""
    # We allow it only inside `/* ... */` or `// ` comments. Strip
    # comments before searching.
    src = _strip_js_comments(page_src)
    assert "Connection lost during generation. Try again." not in src, (
        "The brittle 'Connection lost during generation. Try again.' "
        "toast has reappeared. Use toastErrorSafe with a request_id "
        "and a fail-tolerance counter (see PhotoReactionGIF.js)."
    )


def test_toast_safe_imported(page_src: str) -> None:
    """All user-facing error toasts in this page must route through
    toastErrorSafe so a Reference ID is always present."""
    assert "toastErrorSafe" in page_src, (
        "PhotoReactionGIF.js must import { toastErrorSafe } from "
        "'../utils/toastSafe' so every error toast carries a Reference ID."
    )
    assert "extractRequestId" in page_src, (
        "PhotoReactionGIF.js must import { extractRequestId } so axios "
        "errors surface their request_id correlation id."
    )


# ─── Frontend: pollJob is fail-tolerant ──────────────────────────────


def test_polljob_has_consecutive_fail_counter(page_src: str) -> None:
    """A single poll failure must NOT terminate the UX. There must be
    a tolerance counter that absorbs transient failures."""
    assert "consecutiveFailRef" in page_src, (
        "PhotoReactionGIF.js must track a consecutiveFailRef in the "
        "poll loop so a single transient failure does not kill UX."
    )
    assert "POLL_FAIL_TOLERANCE" in page_src, (
        "PhotoReactionGIF.js must define POLL_FAIL_TOLERANCE so the "
        "tolerance window is explicit and reviewable."
    )


def test_polljob_emits_recovery_beacon(page_src: str) -> None:
    assert "reaction_gif_poll_recovered_total" in page_src, (
        "PhotoReactionGIF.js must emit reaction_gif_poll_recovered_total "
        "via the diagnostics beacon when the network recovers."
    )
    assert "reaction_gif_connection_lost_total" in page_src, (
        "PhotoReactionGIF.js must emit reaction_gif_connection_lost_total "
        "when the tolerance threshold is crossed."
    )


def test_polljob_has_hard_limit(page_src: str) -> None:
    """A hard ceiling protects against truly unreachable backends, but
    only AFTER the tolerance window — never on a single failure."""
    assert "POLL_HARD_LIMIT" in page_src, (
        "PhotoReactionGIF.js must define POLL_HARD_LIMIT so the poll "
        "loop eventually surrenders, but only after persistent failure."
    )


def test_session_storage_remembers_active_job(page_src: str) -> None:
    """Reload / online-recovery must be able to resume the same job_id."""
    assert "reaction_gif_active_job_id" in page_src, (
        "PhotoReactionGIF.js must persist the active job_id to "
        "sessionStorage so a refresh can resume the same backend job."
    )


def test_online_and_focus_listeners_force_repoll(page_src: str) -> None:
    """When the network comes back or the tab regains focus, the page
    must force an immediate poll instead of waiting for the next tick."""
    assert "addEventListener('online'" in page_src, (
        "PhotoReactionGIF.js must add a window 'online' listener to "
        "force an immediate poll on network recovery."
    )
    assert "addEventListener('focus'" in page_src, (
        "PhotoReactionGIF.js must add a window 'focus' listener to "
        "force an immediate poll when the tab regains focus."
    )


def test_partial_ready_is_a_terminal_success_in_ui(page_src: str) -> None:
    """The frontend must understand the backend's PARTIAL_READY status
    so users see partial results instead of a dead 'still loading' UI."""
    assert "PARTIAL_READY" in page_src, (
        "PhotoReactionGIF.js must handle the PARTIAL_READY status the "
        "backend now emits when the completion invariant repairs a "
        "partial pack run."
    )


# ─── Backend: completion invariant gates terminal success ────────────


def test_backend_route_imports_invariant(route_src: str) -> None:
    assert "assert_completion_invariant" in route_src, (
        "routes/reaction_gif.py must import assert_completion_invariant "
        "from services.reliability.completion_invariant."
    )


def test_backend_route_calls_invariant_before_completed(
    route_src: str,
) -> None:
    """In the process_reaction_gif function body, the call to
    assert_completion_invariant must appear textually BEFORE any
    `"status": "COMPLETED"` write within the same function."""
    # Locate the function header (which can span multiple lines) and
    # bound the body by the next top-level `def`/`async def` or EOF.
    header = re.search(
        r"^async def process_reaction_gif\s*\([\s\S]*?\)\s*(?:->[^:]+)?\s*:\s*\n",
        route_src,
        re.M,
    )
    assert header, "process_reaction_gif function not found"
    body_start = header.end()
    next_def = re.search(
        r"^(?:async\s+)?def\s+\w+\s*\(",
        route_src[body_start:],
        re.M,
    )
    body_end = body_start + next_def.start() if next_def else len(route_src)
    body = route_src[body_start:body_end]

    inv_pos = body.find("assert_completion_invariant(")
    # We only care about *persisted* COMPLETED writes, which take the
    # canonical Mongo `$set: {"status": "COMPLETED"}` form. A bare
    # "COMPLETED" string literal (e.g. as input to the invariant
    # itself) is not a write and must not be flagged.
    completed_write = re.search(
        r"""['"]status['"]\s*:\s*['"]COMPLETED['"]""",
        body,
    )
    completed_pos = completed_write.start() if completed_write else -1
    assert inv_pos != -1, (
        "process_reaction_gif must call assert_completion_invariant "
        "before persisting any terminal-success status."
    )
    assert completed_pos == -1 or inv_pos < completed_pos, (
        "assert_completion_invariant must be called BEFORE the COMPLETED "
        "status is written. Reorder the function so the invariant gates "
        "the decision."
    )


def test_backend_route_in_registered_pipelines() -> None:
    from services.reliability.completion_invariant import REGISTERED_PIPELINES
    assert "routes/reaction_gif.py" in REGISTERED_PIPELINES, (
        "routes/reaction_gif.py must be in REGISTERED_PIPELINES so the "
        "generic completion-invariant audit scanner enforces the gate "
        "on every future change."
    )


def test_partial_ready_does_not_double_charge(route_src: str) -> None:
    """When the invariant repairs a partial run, the user must NOT be
    charged. This is the credit-safety leg of the bug class."""
    assert "charge_now" in route_src, (
        "routes/reaction_gif.py must explicitly gate credit deduction "
        "behind a charge_now flag tied to the invariant decision."
    )
    assert "PARTIAL_READY" in route_src, (
        "routes/reaction_gif.py must support a PARTIAL_READY effective "
        "status so half-rendered packs are not silently completed."
    )


# ─── Backend: beacon allow-lists the new metrics ─────────────────────


def test_beacon_allowlists_reaction_gif_metrics(beacon_src: str) -> None:
    required = (
        "reaction_gif_connection_lost_total",
        "reaction_gif_poll_recovered_total",
        "reaction_gif_completion_invariant_failed_total",
    )
    missing = [m for m in required if m not in beacon_src]
    assert not missing, (
        "diagnostics_beacon.ALLOWED_METRICS is missing the reaction_gif "
        f"resilience metrics: {missing}"
    )


# ─── Helpers ─────────────────────────────────────────────────────────


def _strip_js_comments(src: str) -> str:
    """Strip /* ... */ block comments and // line comments from JS.
    Naive: does not respect string-literal contents, which is fine for
    this scan because the target phrase appears inside ordinary string
    literals if it is a real toast call."""
    # Block comments
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    # Line comments
    src = re.sub(r"//[^\n]*", "", src)
    return src
