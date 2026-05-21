"""
P0 2026-05-21 — My Space false-success Preview CTA bug-class elimination.

Production trust-bug: My Space → Completed → Final Video card showed:
  • "Your video is ready" pill
  • Enabled Preview / Download / Share buttons
  • Clicking Preview did NOTHING (silent no-op)

Root cause: handleWatch was `() => { if (job.output_url) window.open(...) }`.
When output_url was missing on a COMPLETED job (a legit failure mode of
the false-COMPLETED bug class), the click vanished without feedback —
no toast, no console, no console.error. The success UI was rendered
based on `status === 'COMPLETED'` alone, decoupled from the canonical
"is there actually a playable asset?" predicate.

This audit pins the surgical fix:

  1. handleWatch never silently no-ops. When output_url is missing,
     it fires a toastErrorSafe with a stable code + request_id AND
     emits the my_space_preview_clicked_without_url_total beacon.
  2. The canonical hasPlayableVideo predicate is `Boolean(job.output_url)`.
     The UI gates Preview / Download / Share buttons on this — NOT on
     the status string.
  3. When hasPlayableVideo is false on a COMPLETED job, the Preview
     button renders in a non-actionable "Finalizing…" state with the
     `preview-btn-finalizing-${job_id}` testid; the original
     `preview-btn-${job_id}` testid is reserved for the playable case.
  4. Download and Share are disabled with explicit titles when the
     asset is missing.
  5. The diagnostics beacon allow-lists the new metric so we can
     dashboard how often production hits this condition.

Doctrine refs: ENGINEERING_DOCTRINE.md → Rule 5 (no leaked internals,
no silent failures) + Rule 6 (every failure observable) + Bug-Class
Elimination Mandate (this entire class — completed-status lying about
playable asset — is now impossible to merge).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

APP = Path("/app")
PAGE = APP / "frontend/src/pages/MySpacePage.js"
BEACON = APP / "backend/routes/diagnostics_beacon.py"


@pytest.fixture(scope="module")
def page_src() -> str:
    assert PAGE.exists(), f"Missing: {PAGE}"
    return PAGE.read_text()


@pytest.fixture(scope="module")
def beacon_src() -> str:
    return BEACON.read_text()


# ─── handleWatch: never silently no-ops ─────────────────────────────


def test_handle_watch_does_not_silently_no_op(page_src: str) -> None:
    """The legacy single-line handler that vanished a click without
    feedback must be gone. Pin its exact prior form as forbidden."""
    legacy = "const handleWatch = () => { if (job.output_url) window.open(job.output_url, '_blank'); };"
    assert legacy not in page_src, (
        "Legacy silent-no-op handleWatch is back. Restore the "
        "P0 2026-05-21 defensive version that fires a "
        "toastErrorSafe + beacon on missing output_url."
    )


def test_handle_watch_uses_toast_error_safe(page_src: str) -> None:
    """The missing-URL branch must surface a structured toast with
    request_id — never a console.log or a silent return."""
    # Find the handleWatch function body and confirm both branches.
    m = re.search(
        r"const handleWatch\s*=\s*\(\)\s*=>\s*\{([\s\S]+?)\n  \};",
        page_src,
    )
    assert m, "handleWatch function body not found"
    body = m.group(1)
    assert "window.open(job.output_url" in body, "Working-case branch must call window.open with output_url."
    assert "toastErrorSafe(" in body, (
        "Missing-URL branch must call toastErrorSafe so the user "
        "gets a Reference ID + actionable copy."
    )
    assert "MY_SPACE_PREVIEW_NOT_READY" in body, (
        "toastErrorSafe must carry a stable error code "
        "MY_SPACE_PREVIEW_NOT_READY for support correlation."
    )


def test_handle_watch_emits_observability_beacon(page_src: str) -> None:
    """When the missing-URL branch fires, we MUST emit the new
    my_space_preview_clicked_without_url_total beacon so we can see
    production frequency in the diagnostics dashboard."""
    assert "my_space_preview_clicked_without_url_total" in page_src
    assert "/api/diagnostics/beacon" in page_src


def test_toast_safe_import_present(page_src: str) -> None:
    assert "from '../utils/toastSafe'" in page_src, (
        "MySpacePage.js must import toastErrorSafe from "
        "../utils/toastSafe so the missing-URL branch can fire a "
        "request_id-carrying toast."
    )
    assert "toastErrorSafe" in page_src


# ─── Canonical predicate: hasPlayableVideo, NOT status === COMPLETED ─


def test_canonical_predicate_present(page_src: str) -> None:
    """The single source of truth for "is this thing playable" must
    be `Boolean(job.output_url)`. Pin the literal form."""
    assert "const hasPlayableVideo = Boolean(job.output_url);" in page_src, (
        "MySpacePage.js must define `hasPlayableVideo = Boolean(job.output_url)` "
        "as the canonical playable-asset predicate. This replaces the "
        "implicit `status === 'COMPLETED'` gate that produced the "
        "false-success Preview button."
    )


def test_preview_button_uses_hasplayablevideo_gate(page_src: str) -> None:
    """The Preview button must conditionally render the active form
    ONLY when hasPlayableVideo is true. The non-playable case must
    render a disabled `Finalizing…` button with a distinct testid."""
    assert "hasPlayableVideo ? (" in page_src
    assert "preview-btn-finalizing-${job.job_id}" in page_src, (
        "The non-playable Preview render must use a distinct "
        "`preview-btn-finalizing-<job_id>` testid so accessibility "
        "tooling and tests can distinguish the two states."
    )
    assert 'disabled\n                    aria-disabled="true"' in page_src, (
        "Finalizing button must be disabled AND aria-disabled='true' "
        "so assistive tech reports the correct state."
    )


def test_download_and_share_also_gated(page_src: str) -> None:
    """Download and Share share the same trust failure: rendering
    enabled while no asset is attached. They must be disabled
    explicitly when hasPlayableVideo is false."""
    src = page_src
    # Find the Download button block.
    dl = re.search(
        r"data-testid=\{`download-btn-\$\{job\.job_id\}`\}[\s\S]{0,500}",
        src,
    )
    assert dl, "Download button block not found"
    assert "disabled={!hasPlayableVideo}" in dl.group(0)
    assert "aria-disabled={!hasPlayableVideo}" in dl.group(0)

    sh = re.search(
        r"data-testid=\{`share-btn-\$\{job\.job_id\}`\}[\s\S]{0,500}",
        src,
    )
    assert sh, "Share button block not found"
    assert "disabled={!hasPlayableVideo}" in sh.group(0)


def test_no_completed_status_gates_active_actions(page_src: str) -> None:
    """We must never see an active-action button (Preview / Download
    / Share) whose enable condition is `status === 'COMPLETED'` with
    no further check. Pin this anti-pattern as forbidden in the
    actions block.

    We scope the search to the COMPLETED/PARTIAL branch and check
    that none of the action buttons there directly key off the
    statusKey predicate alone."""
    block_match = re.search(
        r"\{\(statusKey === 'COMPLETED' \|\| statusKey === 'PARTIAL'\) && \(\s*<>([\s\S]+?)\n\s*\)\}\s*\n",
        page_src,
    )
    assert block_match, "COMPLETED/PARTIAL actions block not found"
    block = block_match.group(1)
    # The block must contain hasPlayableVideo (positive proof of the gate).
    assert "hasPlayableVideo" in block, (
        "COMPLETED/PARTIAL action block must reference hasPlayableVideo "
        "so the actions are gated on playability, not status alone."
    )


# ─── Beacon allow-list ───────────────────────────────────────────────


def test_beacon_allowlists_my_space_preview_metric(beacon_src: str) -> None:
    assert "my_space_preview_clicked_without_url_total" in beacon_src, (
        "diagnostics_beacon.ALLOWED_METRICS must include "
        "my_space_preview_clicked_without_url_total or the frontend "
        "emit will be rejected."
    )
