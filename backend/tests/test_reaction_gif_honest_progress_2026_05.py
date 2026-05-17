"""
P1 2026-05-22 — Reaction GIF honest-progress bug-class elimination.

Production symptom: `/app/gif-maker` parks at "Adding style effects…
90% complete" for the entire LLM call, creating a stuck-job
perception even when the job eventually completes. Root cause:
  • Backend jumped progress directly from 10 → 90 for single-mode.
  • Frontend ignored `job.progressMessage` and synthesized labels
    from `Math.floor(progress / 25)` — so 90% ALWAYS read "Adding
    style effects…", regardless of what the backend reported.
  • No stall detector: when a stage genuinely took longer than the
    "usually 15-30s" promise, the UI kept lying about progress.

Fixes locked in by this suite:

  Backend:
    1. process_reaction_gif emits honest stages: validate (5%),
       prepare (15%), generate (30–75%), encode (75%), verify (90%),
       ready (100%).
    2. Each stage writes a real `progressMessage` AND a `stage`
       string AND appends to a `stages` ring buffer with timestamps.
    3. Source images larger than 1024 px on the longest side are
       downscaled before the LLM call — a real latency win, not
       fake progress.
    4. `totalDurationMs` is persisted on the COMPLETED branch so
       ops can dashboard p50/p90/p99.

  Frontend:
    5. `renderGenerating` renders `job.progressMessage` directly —
       no more synthetic msgs[] array keyed off `progress/25`.
    6. A stall detector (`lastProgressAtRef`, `stallHelperText`,
       `STALL_HELPER_THRESHOLD_MS`) flips the helper line from
       "Usually takes 15–30 seconds" to a stage-aware "Still
       working — <stage> is taking longer than usual." after
       20 seconds without progress movement.
    7. Existing P0 invariants (assetVerified, preload probe gate)
       remain — speed cannot bypass correctness.

A PR that re-introduces the synthetic msgs[] array, removes the
stall detector, or removes the honest stage labels must edit this
file deliberately and attach an 8-section bug-class report.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

APP = Path("/app")
PAGE = APP / "frontend/src/pages/PhotoReactionGIF.js"
BACKEND_ROUTE = APP / "backend/routes/reaction_gif.py"

sys.path.insert(0, str(APP / "backend"))


@pytest.fixture(scope="module")
def page_src() -> str:
    return PAGE.read_text()


@pytest.fixture(scope="module")
def route_src() -> str:
    return BACKEND_ROUTE.read_text()


# ─── Backend: honest stage progress ──────────────────────────────────


def test_route_defines_local_stage_helper(route_src: str) -> None:
    """process_reaction_gif must define a `_stage(...)` helper that
    writes progress + progressMessage + stage + stages[]."""
    assert re.search(r"async def _stage\(", route_src), (
        "process_reaction_gif must define an inner _stage helper that "
        "emits progress, progressMessage, stage, and a stages ring."
    )


def test_route_emits_all_six_canonical_stages(route_src: str) -> None:
    required_stages = ("validate", "prepare", "generate", "encode", "verify", "ready")
    missing = [s for s in required_stages if f'"{s}"' not in route_src]
    assert not missing, (
        f"process_reaction_gif must emit all canonical stages; missing: {missing}"
    )


def test_route_no_longer_jumps_to_90_without_intermediate_stages(
    route_src: str,
) -> None:
    """Sanity: the old single-mode formula `10 + int(((i + 1) / total_reactions) * 80)`
    must be gone — it was the source of the 10→90 jump."""
    assert "10 + int(((i + 1) / total_reactions) * 80)" not in route_src, (
        "The legacy single-mode 10→90 jump formula is gone for good. "
        "Use the _stage helper with explicit progress bands instead."
    )


def test_route_downscales_oversized_source(route_src: str) -> None:
    """Source images bigger than 1024 px on the longest side must be
    downscaled before the LLM call. Pin both the constant and the
    downscale operation."""
    assert "DOWNSCALE_TARGET = 1024" in route_src
    assert "Image.Resampling.LANCZOS" in route_src or "Resampling.LANCZOS" in route_src
    assert "downscaled source" in route_src, (
        "Downscale path must emit a structured ops log so we can "
        "measure how often it fires in production."
    )


def test_route_records_total_duration_ms(route_src: str) -> None:
    assert "totalDurationMs" in route_src, (
        "process_reaction_gif must persist totalDurationMs on the "
        "terminal status update so ops can dashboard p50/p90/p99."
    )


def test_route_persists_stages_log(route_src: str) -> None:
    assert "stages" in route_src
    assert "stage_log" in route_src, (
        "process_reaction_gif must maintain a stage_log list and "
        "persist it on each stage transition so the contract carries "
        "timing info without an extra round-trip."
    )


# ─── Frontend: honest progress, no synthetic msgs, stall detector ────


def test_frontend_renders_backend_progress_message(page_src: str) -> None:
    """The generating phase must render job.progressMessage directly
    instead of fabricating one from `progress / 25`."""
    assert "job?.progressMessage" in page_src, (
        "renderGenerating must read job.progressMessage from the "
        "backend so the UI tells the truth."
    )
    assert "generating-progress-message" in page_src, (
        "renderGenerating must expose a data-testid on the progress "
        "message line so the suite can pin it."
    )


def test_frontend_drops_synthetic_msgs_array(page_src: str) -> None:
    """The old synthetic `const msgs = [...]` array keyed off
    progress/25 was the literal cause of "Adding style effects…"
    appearing at 90% regardless of backend truth. It must stay gone."""
    assert '"Adding style effects..."' not in page_src, (
        "The synthetic 'Adding style effects...' string is the visible "
        "stuck-at-90 signal. It must not be hardcoded in the page — "
        "the backend's progressMessage is the source of truth."
    )
    assert "Math.floor((job?.progress || 0) / 25)" not in page_src, (
        "The synthetic `Math.floor(progress / 25)` msgs-array selector "
        "is gone. Render backend progressMessage directly."
    )


def test_frontend_has_stall_detector(page_src: str) -> None:
    assert "stallHelperText" in page_src
    assert "lastProgressAtRef" in page_src
    assert "STALL_HELPER_THRESHOLD_MS" in page_src
    assert "Still working" in page_src, (
        "renderGenerating must surface a 'Still working — <stage> is "
        "taking longer than usual.' line when a stage stalls. This "
        "replaces the 'Usually takes 15-30 seconds' lie."
    )


def test_frontend_helper_text_has_testid(page_src: str) -> None:
    """A stable testid lets us assert helper-text transitions in
    browser tests post-deploy without scraping by class name."""
    assert "generating-helper-text" in page_src


def test_frontend_uses_endash_in_default_helper_copy(page_src: str) -> None:
    """Copy fix: the brittle '15-30 seconds' string is replaced
    with a typographically correct '15–30 seconds' that lives in
    state, not as a stuck literal."""
    assert "15–30 seconds" in page_src, (
        "Default helper copy must use the en-dash form '15–30 seconds' "
        "in the stall-detector state. It is the only literal we expect."
    )


# ─── Speed-cannot-bypass-correctness invariant remains intact ────────


def test_asset_readiness_gate_still_present(page_src: str) -> None:
    """The Reaction GIF false-success gate (P0 from earlier in the
    day) must remain wired even though we changed the progress UX."""
    assert "const showActions = previewReady" in page_src
    assert "runPreviewProbe" in page_src


def test_completion_invariant_still_called(route_src: str) -> None:
    assert "assert_completion_invariant(" in route_src
    assert "verify_image_asset(" in route_src
