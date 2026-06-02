"""P0 2026-06 — UI must surface failure diagnostics, not hide them.

Born from the production screenshot incident: a failed Anime Intro trailer
showed only "Trailer didn't render / Trailer failed. Please try again." —
hiding error_code, failure_stage, provider_error, render_validation_error
that the backend has been persisting since the earlier credit-integrity
patch. Every failure became a 30-minute support ticket round-trip.

This suite pins:
  1. FailedStep renders the diagnostic block whenever any of the
     structured fields are present on the job doc.
  2. The block surfaces failure_stage, error_code, and a composed
     failure_reason that stacks error_message + validation + provider
     + refund errors.
  3. A "Copy diagnostic info" button exists with a stable test-id so
     users / support can grab a structured payload in one click.

Pure source-static so it can run without a browser. The behavioural
clipboard check is left for a manual smoke test (browser-dependent).
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
TRAILER_PAGE = ROOT / "frontend" / "src" / "pages" / "PhotoTrailerPage.jsx"


def _failed_step_body() -> str:
    """Extract the FailedStep function body for focused assertions."""
    src = TRAILER_PAGE.read_text()
    m = re.search(
        r"function FailedStep\([^)]*\)\s*\{(?P<body>.+?)\n\}\n",
        src, re.S,
    )
    assert m, "FailedStep() component must exist."
    return m.group("body")


def test_failed_step_reads_error_code_from_job():
    """The diagnostic block must read `job.error_code` — the canonical
    machine-readable failure cause the backend persists."""
    body = _failed_step_body()
    assert "job?.error_code" in body, (
        "FailedStep must read job.error_code for the diagnostic surface."
    )


def test_failed_step_reads_failure_stage_from_job():
    """`failure_stage` (or fallback `current_stage`) tells the user which
    pipeline stage broke. Must be surfaced."""
    body = _failed_step_body()
    assert "job?.failure_stage" in body, (
        "FailedStep must read job.failure_stage."
    )
    # Fallback chain: failure_stage || current_stage so it works on jobs
    # that failed before the failure_stage field was written.
    assert "current_stage" in body, (
        "FailedStep must fall back to current_stage when failure_stage is absent."
    )


def test_failed_step_composes_failure_reason_from_multiple_fields():
    """The user-facing `failure_reason` must stack:
        error_message + render_validation_error + provider_error + refund_error
    so a single block tells the user (and support) which subsystem broke."""
    body = _failed_step_body()
    for field in ("error_message", "render_validation_error",
                  "provider_error", "refund_error"):
        assert f"job?.{field}" in body, (
            f"FailedStep must include `{field}` in the composed failure_reason."
        )


def test_failed_step_renders_diagnostic_block_with_stable_test_ids():
    """The block + each diagnostic row must have stable test-ids so we can
    automation-test the surface."""
    body = _failed_step_body()
    required_ids = [
        "trailer-failed-diagnostic",
        "trailer-failed-stage",
        "trailer-failed-code",
        "trailer-failed-details",
        "trailer-copy-diagnostic-btn",
    ]
    for tid in required_ids:
        assert tid in body, f"FailedStep must expose data-testid={tid!r}"


def test_failed_step_copy_diagnostic_button_writes_json_to_clipboard():
    """The copy button must serialize a structured JSON payload (NOT the
    visible text) so support can paste it directly into a ticket and we
    can parse it programmatically."""
    body = _failed_step_body()
    assert "navigator.clipboard.writeText" in body, (
        "Copy diagnostic must use the Clipboard API."
    )
    assert "JSON.stringify(diagnostic" in body, (
        "Copy diagnostic must write a STRUCTURED JSON payload, "
        "not raw text — support tickets need parseable data."
    )


def test_failed_step_diagnostic_only_renders_when_data_exists():
    """Empty diagnostic must not render an empty block — the surface should
    degrade gracefully for jobs that pre-date the new fields."""
    body = _failed_step_body()
    assert "hasDiagnostic" in body, (
        "FailedStep must gate the diagnostic block on a presence check."
    )
    assert re.search(r"hasDiagnostic\s*&&", body), (
        "Diagnostic block must be conditionally rendered (hasDiagnostic && ...)."
    )


def test_copy_icon_imported_from_lucide():
    """The Copy icon must be imported — silent missing-icon JSX bugs in
    React render as nothing, leaving the button blank."""
    src = TRAILER_PAGE.read_text()
    # Find the lucide-react import block.
    m = re.search(r"from 'lucide-react'", src)
    assert m, "lucide-react import must exist."
    # The Copy export must be in the named-imports block.
    imp_block = src[:m.start()]
    assert re.search(r"\bCopy\b", imp_block), (
        "Copy icon must be imported from lucide-react for the diagnostic button."
    )
