"""
P0 2026-05-19 — Comic Strip completion-invariant regression suite.

Locks down the fix for the production "Your Comic is Ready / All panels
generated and verified" bug where a 3-panel strip request silently
finished with only 2 panels.

Three layers of invariants asserted:

  1. STORY PLAN: pre-flight pads `story_scenes` to `panel_count` and
     emits an observability counter.
  2. GENERATION LOOP: always iterates `panel_count` times, never
     `min(panel_count, len(story_scenes))`.
  3. COMPLETION INVARIANT: COMPLETED (or READY_WITH_WARNINGS) must
     require `len(ready_panels) == panel_count`. A mismatch downgrades
     to PARTIAL_READY and increments
     `p2c_completion_invariant_failed_total`.

Plus frontend pinning (source-level):
  • status badge subtitle never claims "All panels generated and verified"
    when `readyPanels < expectedPanels`.
  • result-page READY state requires the strip-completeness check before
    setting `uiState='READY'`.
  • the empty-panel placeholder no longer says "Being optimized" — it
    explicitly says "Generating…" or "Retrying…" so an incomplete strip
    can never silently look complete.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PHOTO_TO_COMIC_PY = Path("/app/backend/routes/photo_to_comic.py")
PHOTO_TO_COMIC_JS = Path("/app/frontend/src/pages/PhotoToComic.js")


@pytest.fixture(scope="module")
def backend_src() -> str:
    return PHOTO_TO_COMIC_PY.read_text()


@pytest.fixture(scope="module")
def frontend_src() -> str:
    return PHOTO_TO_COMIC_JS.read_text()


# ─── Backend invariants ──────────────────────────────────────────────


def test_story_plan_padder_exists(backend_src: str) -> None:
    """The pre-flight padder must extend `story_scenes` to `panel_count`
    so the generation loop always has enough scenes."""
    assert "STORY-PLAN INVARIANT" in backend_src, (
        "Missing the STORY-PLAN INVARIANT block in photo_to_comic.py. "
        "Without it, an LLM that returns fewer scenes than requested "
        "silently truncates the strip."
    )
    assert re.search(
        r"while\s+len\(story_scenes\)\s*<\s*panel_count\s*:",
        backend_src,
    ), "Padder must keep appending until story_scenes reaches panel_count"
    assert "p2c_story_plan_padded_total" in backend_src, (
        "Padder must emit p2c_story_plan_padded_total observability counter"
    )


def test_generation_loop_iterates_full_panel_count(backend_src: str) -> None:
    """The loop must use `range(panel_count)` — never the buggy
    `range(min(panel_count, len(story_scenes)))` form."""
    assert "for i in range(panel_count):" in backend_src, (
        "Strip generation loop must iterate `panel_count` times so the "
        "story-plan invariant has bite."
    )
    # The legacy bug pattern must be GONE from executable code.
    assert "range(min(panel_count, len(story_scenes)))" not in backend_src, (
        "REGRESSION: Found the legacy truncating loop "
        "`range(min(panel_count, len(story_scenes)))`. This is the exact "
        "shape that caused the 2-of-3 panel bug."
    )


def test_completion_invariant_block_exists(backend_src: str) -> None:
    """The strip path must route through the canonical
    `assert_completion_invariant` helper. Replaces the prior inline
    block (which the helper now subsumes)."""
    assert "assert_completion_invariant" in backend_src, (
        "Missing call to assert_completion_invariant — without the "
        "canonical gate a partial generation could mark COMPLETED."
    )
    assert "pipeline=\"photo_to_comic.strip\"" in backend_src, (
        "Strip path must identify itself when calling the gate so the "
        "metric `recent_samples` ring shows which pipeline tripped it."
    )


def test_completion_invariant_downgrades_status(backend_src: str) -> None:
    """The strip path must pass `actual_ready_count` and `panel_count`
    into the helper. The helper itself owns the downgrade behavior;
    we just pin the call shape so the wiring can't drift."""
    block = re.search(
        r"actual_ready_count\s*=\s*len\(\[p for p in panels if p\.get\(\"status\"\) == \"READY\"\]\)"
        r"[\s\S]{0,500}?"
        r"assert_completion_invariant\([\s\S]*?\)",
        backend_src,
    )
    assert block, (
        "Strip path must compute `actual_ready_count` and pass it "
        "(along with `panel_count`) into `assert_completion_invariant`."
    )
    body = block.group(0)
    assert "expected_count=panel_count" in body, (
        "Helper call must supply `expected_count=panel_count`."
    )
    assert "actual_count=actual_ready_count" in body, (
        "Helper call must supply `actual_count=actual_ready_count`."
    )
    assert "effective_status" in backend_src, (
        "Caller must consume `invariant_result.effective_status`."
    )


def test_planned_scene_count_persisted(backend_src: str) -> None:
    """The job document must persist both `planned_scene_count` and
    `expected_panel_count` so post-hoc audits can reconstruct what
    happened."""
    assert '"planned_scene_count":' in backend_src
    assert '"expected_panel_count":' in backend_src


# ─── Frontend invariants ─────────────────────────────────────────────


def test_frontend_strip_completeness_gate_exists(frontend_src: str) -> None:
    """`resolveAssetState` must compute `stripIsComplete` and require
    it before setting `uiState='READY'`. Without this guard the user
    sees a green success banner with missing panels."""
    assert "STRIP COMPLETENESS INVARIANT" in frontend_src
    assert re.search(
        r"const\s+stripIsComplete\s*=",
        frontend_src,
    ), "stripIsComplete derivation must exist"
    # Must be required for the READY transition.
    m = re.search(
        r"if\s*\(\s*previewOk\s*&&\s*downloadOk\s*&&\s*stripIsComplete\s*\)\s*\{[\s\S]*?setUiState\(\s*'READY'\s*\)",
        frontend_src,
    )
    assert m, (
        "READY transition must also require `stripIsComplete`. Without "
        "it a 2-of-3 strip still reaches uiState='READY'."
    )


def test_partial_ready_badge_no_false_completeness(frontend_src: str) -> None:
    """The PARTIAL_READY status badge subtitle must never claim
    completeness when the strip is short."""
    # The new computed `stripShortfall` switch must be present and the
    # short-strip title MUST be the calm "Finalizing your comic…" form.
    assert "stripShortfall" in frontend_src, (
        "PARTIAL_READY badge must compute `stripShortfall` and react to it"
    )
    assert "Finalizing your comic…" in frontend_src, (
        "Short-strip subtitle must use the 'Finalizing your comic…' copy "
        "instead of fake-success language."
    )
    # Specifically — must NOT have the original misleading subtitle form
    # without a shortfall guard.
    assert re.search(
        r"title:\s*stripShortfall\s*\?\s*'Finalizing your comic…'\s*:\s*'Your Comic is Ready'",
        frontend_src,
    ), "PARTIAL_READY title must be conditional on stripShortfall"


def test_empty_panel_placeholder_no_longer_says_being_optimized(frontend_src: str) -> None:
    """The empty-panel placeholder was the visible smoking gun in the
    user's screenshot. It must not silently say 'Being optimized' on a
    READY screen — it must explicitly say 'Generating…' or 'Retrying…'."""
    # Strip block comments before searching so a documentation reference
    # to the old phrase doesn't false-positive.
    src_no_block = re.sub(r"/\*[\s\S]*?\*/", "", frontend_src)
    # Single-line comments rarely contain the literal "Being optimized";
    # the test below would have caught the live JSX bug regardless.
    src_clean = re.sub(r"//[^\n]*", "", src_no_block)
    assert "Being optimized" not in src_clean, (
        "REGRESSION: The 'Being optimized' placeholder copy is back. "
        "Use 'Generating…' / 'Retrying…' instead so the missing panel "
        "is obvious."
    )
    assert "panel-1-pending" in frontend_src or re.search(
        r"data-testid=\{`panel-\$\{i\+1\}-pending`\}",
        frontend_src,
    ), "Pending-panel placeholder must carry a `panel-N-pending` testid"


def test_status_messages_do_not_lie(frontend_src: str) -> None:
    """The verified-text on the success badge is reserved for genuine
    READY. PARTIAL_READY must never claim "All panels generated and verified"."""
    # Strip line + block comments so documentation references to the
    # phrase don't count.
    src_no_block = re.sub(r"/\*[\s\S]*?\*/", "", frontend_src)
    src_clean = re.sub(r"//[^\n]*", "", src_no_block)
    matches = [m.start() for m in re.finditer(
        r"All panels generated and verified", src_clean
    )]
    assert len(matches) <= 1, (
        f"'All panels generated and verified' appears {len(matches)} "
        "times in executable code; it must be used ONLY by the READY badge."
    )
    if matches:
        window = src_clean[max(0, matches[0] - 200): matches[0]]
        assert "READY:" in window, (
            "'All panels generated and verified' must live inside the "
            "READY badge config, not anywhere else."
        )
