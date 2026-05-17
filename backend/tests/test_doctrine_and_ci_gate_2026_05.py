"""
P1 2026-05-19 — Engineering doctrine pinning regression suite.

Locks in the founder-adopted engineering doctrine and the
`make audit-boundaries` CI gate. These tests fail any merge that:

  • removes or weakens the doctrine document
  • removes or renames the Makefile audit gate
  • drops an existing audit suite from the registry
  • adds a new audit file without registering it

The doctrine itself is at /app/memory/ENGINEERING_DOCTRINE.md.
The CI gate is at /app/Makefile :: audit-boundaries.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

DOCTRINE = Path("/app/memory/ENGINEERING_DOCTRINE.md")
MAKEFILE = Path("/app/Makefile")
TESTS_DIR = Path("/app/backend/tests")


@pytest.fixture(scope="module")
def doctrine_text() -> str:
    assert DOCTRINE.exists(), f"Doctrine document missing: {DOCTRINE}"
    return DOCTRINE.read_text()


@pytest.fixture(scope="module")
def makefile_text() -> str:
    assert MAKEFILE.exists(), f"Makefile missing: {MAKEFILE}"
    return MAKEFILE.read_text()


# ─── Doctrine pinning ────────────────────────────────────────────────


def test_doctrine_sentence_is_intact(doctrine_text: str) -> None:
    """The one-sentence doctrine must appear verbatim. Removing or
    weakening it requires an explicit founder greenlight + dated
    changelog entry — and a deliberate edit of THIS test."""
    canonical = (
        "Never allow unvalidated input, ambiguous state, or silent "
        "failure to cross a system boundary."
    )
    # Normalize: collapse whitespace AND strip Markdown blockquote markers
    # so the line-wrapped `> ` prefix in the quoted form still matches.
    normalized = re.sub(r"\s+", " ", doctrine_text.replace("> ", ""))
    assert canonical in normalized, (
        "The platform doctrine sentence has been altered or removed. "
        "Reverting unless the founder explicitly authorized the change."
    )


def test_doctrine_contains_all_ten_rules(doctrine_text: str) -> None:
    """The numbered ten rules must remain present. Each rule has a
    distinctive heading we pin against."""
    required_headings = (
        "1. Every boundary validates",
        "2. Every critical flow has canonical state",
        "3. Every failure is observable",
        "4. Every async action is idempotent",
        "5. Every user-facing error is sanitized",
        "6. Every new feature must pass boundary audits",
        "7. Freeze before expansion",
        "8. Complexity is a liability",
        "9. CI enforces stability automatically",
        "10. Stability > velocity theater",
    )
    missing = [h for h in required_headings if h not in doctrine_text]
    assert not missing, (
        f"Doctrine is missing rule headings: {missing}. The 10 rules "
        "are non-negotiable per founder mandate."
    )


def test_doctrine_lists_make_audit_boundaries(doctrine_text: str) -> None:
    """Rule 9 must continue to name the canonical CI command."""
    assert "make audit-boundaries" in doctrine_text, (
        "Doctrine rule 9 must continue to reference the "
        "`make audit-boundaries` command."
    )


# ─── Makefile pinning ────────────────────────────────────────────────


def test_makefile_audit_target_exists(makefile_text: str) -> None:
    assert re.search(r"^audit-boundaries\s*:", makefile_text, re.M), (
        "Makefile must declare the `audit-boundaries` target."
    )
    assert ".PHONY: audit-boundaries" in makefile_text, (
        "`audit-boundaries` must be declared .PHONY so stale files "
        "never short-circuit it."
    )


def test_makefile_registers_every_audit_suite(makefile_text: str) -> None:
    """Every NEW boundary-audit file (the dated 2026-05+ scanners and
    the explicitly-named *_boundary_audit / *_event_trap_audit /
    *_payload_boundary_audit / *_url_boundary_audit / *_payment_auth_batch
    families) must be in the Makefile registry. Legacy `*_audit_*` QA
    suites that predate the doctrine are NOT covered — they have their
    own pipelines."""
    # Only require registration of files whose names match the new
    # canonical scanner naming. This is an opt-in marker, not a global
    # filename glob.
    canonical_patterns = (
        "event_trap_audit",
        "payload_boundary_audit",
        "url_boundary_audit",
        "backend_payload_acceptance",
        "payment_auth_batch_a",
        "diagnostics_beacon",
        "doctrine_and_ci_gate",
    )
    audit_files = sorted(
        f.name for f in TESTS_DIR.glob("test_*.py")
        if any(pat in f.name for pat in canonical_patterns)
    )
    # The doctrine test itself doesn't need to be in the audit registry —
    # it's the regulator of the registry, not a participant. Exclude it.
    audit_files = [n for n in audit_files if "doctrine_and_ci_gate" not in n]
    missing = [name for name in audit_files if name not in makefile_text]
    assert not missing, (
        "The Makefile's BOUNDARY_AUDIT_SUITES list is missing the "
        f"following canonical boundary-audit suites: {missing}\n"
        "Add them to /app/Makefile before merging."
    )


def test_makefile_registry_paths_exist(makefile_text: str) -> None:
    """Every path listed in BOUNDARY_AUDIT_SUITES must actually exist
    on disk — a typo silently drops coverage."""
    # Extract the block between the variable assignment and the next blank
    # / non-indented line.
    m = re.search(
        r"BOUNDARY_AUDIT_SUITES\s*:=\s*\\\n((?:\t.*\\\n)*\t.*)",
        makefile_text,
    )
    assert m, "Could not locate BOUNDARY_AUDIT_SUITES block in Makefile"
    block = m.group(1)
    listed = [
        line.strip().rstrip("\\").strip()
        for line in block.splitlines()
        if line.strip()
    ]
    missing_on_disk = [p for p in listed if not (Path("/app") / p).exists()]
    assert not missing_on_disk, (
        f"BOUNDARY_AUDIT_SUITES references non-existent files: "
        f"{missing_on_disk}"
    )


def test_makefile_default_goal_is_help(makefile_text: str) -> None:
    """`make` with no args must print help, not silently run nothing
    or run the slow audit. Predictability matters."""
    assert ".DEFAULT_GOAL := help" in makefile_text


# ─── Doctrine ↔ Makefile cross-check ─────────────────────────────────


def test_doctrine_audit_list_matches_makefile(
    doctrine_text: str,
    makefile_text: str,
) -> None:
    """The doctrine's example audit composition must remain in sync
    with the Makefile registry — at least the well-known audit suites
    that the doctrine names by file must still be registered."""
    pinned_in_doctrine = (
        "test_event_trap_audit_2026_05.py",
        "test_payload_boundary_audit_2026_05.py",
        "test_url_boundary_audit_2026_05.py",
        "test_backend_payload_acceptance_2026_05.py",
        "test_payment_auth_batch_a_2026_05.py",
        "test_diagnostics_beacon_2026_05.py",
    )
    drift = [
        name for name in pinned_in_doctrine
        if name in doctrine_text and name not in makefile_text
    ]
    assert not drift, (
        "Doctrine names the following audits but the Makefile registry "
        f"does not include them (drift): {drift}"
    )
