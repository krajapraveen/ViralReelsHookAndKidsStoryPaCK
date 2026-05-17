"""
P1 2026-05-22 — Bug-Class Elimination Mandate pinning suite.

The founder adopted, on 2026-05-22, an extension of the Engineering
Doctrine that elevates every production bug fix from an isolated
patch to a *bug-class elimination task*. The mandate is codified in:

  • /app/memory/ENGINEERING_DOCTRINE.md  — section "The Bug-Class
    Elimination Mandate"
  • /app/memory/BUG_CLASS_ELIMINATION_TEMPLATE.md — the required
    8-section report template

This suite is the merge gate that prevents the mandate from being
silently weakened, partially deleted, or dropped during a refactor.
It fails any change that:

  • removes the mandate section from the doctrine
  • drops or renames any of the 8 mandatory report sections
  • drops or weakens the 8 stability non-negotiables
  • removes the success-definition sentence
  • deletes / weakens the template file
  • deletes the canonical template path reference from the doctrine

Modifying any of the above requires an explicit founder greenlight,
a dated changelog entry in the doctrine, AND a deliberate edit of
THIS test file.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

DOCTRINE = Path("/app/memory/ENGINEERING_DOCTRINE.md")
TEMPLATE = Path("/app/memory/BUG_CLASS_ELIMINATION_TEMPLATE.md")
MAKEFILE = Path("/app/Makefile")


# ─── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def doctrine_text() -> str:
    assert DOCTRINE.exists(), f"Doctrine missing: {DOCTRINE}"
    return DOCTRINE.read_text()


@pytest.fixture(scope="module")
def template_text() -> str:
    assert TEMPLATE.exists(), (
        f"Bug-class elimination template missing: {TEMPLATE}. "
        "This file is mandatory per the 2026-05-22 founder mandate."
    )
    return TEMPLATE.read_text()


@pytest.fixture(scope="module")
def makefile_text() -> str:
    assert MAKEFILE.exists(), f"Makefile missing: {MAKEFILE}"
    return MAKEFILE.read_text()


# ─── Doctrine: the mandate exists and is intact ──────────────────────


def test_doctrine_contains_mandate_section(doctrine_text: str) -> None:
    """The mandate heading must be present verbatim."""
    assert "The Bug-Class Elimination Mandate" in doctrine_text, (
        "Doctrine no longer contains 'The Bug-Class Elimination "
        "Mandate' section. Founder mandate adopted 2026-05-22."
    )


def test_doctrine_contains_success_definition(doctrine_text: str) -> None:
    """The success-definition sentence must remain verbatim. This is
    the entire point of the mandate; weakening it defeats the rule."""
    canonical = (
        'this entire class of bug is now impossible, or is '
        'automatically detected the next time it tries to recur.'
    )
    # Strip blockquote markers and collapse whitespace so the line-wrapped
    # quoted form still matches.
    normalized = re.sub(r"\s+", " ", doctrine_text.replace("> ", ""))
    assert canonical in normalized, (
        "The bug-class elimination success-definition sentence has "
        "been altered or removed. Restore verbatim or obtain a "
        "founder-signed changelog amendment."
    )


def test_doctrine_lists_all_eight_stability_non_negotiables(
    doctrine_text: str,
) -> None:
    """The 8 stability bullets are non-negotiable merge gates."""
    required_bullets = (
        "Validate every boundary",
        "Canonicalize all critical state",
        "Make async jobs idempotent",
        "Never trust client payloads",
        "Never expose internal errors",
        "Every failure carries a `request_id`",
        "Every recurring issue becomes a CI rule",
        "No new feature work during an instability freeze",
    )
    missing = [b for b in required_bullets if b not in doctrine_text]
    assert not missing, (
        f"Stability non-negotiables missing from doctrine: {missing}. "
        "All 8 are required per the 2026-05-22 founder mandate."
    )


def test_doctrine_lists_all_eight_report_sections(
    doctrine_text: str,
) -> None:
    """The 8 mandatory bug-report sections must remain enumerated in
    the doctrine itself (so the procedure is visible at the policy
    layer, not only in the template)."""
    required_sections = (
        "Root cause",
        "Exact broken boundary",
        "Boundary class",
        "Why existing tests missed it",
        "Regression test / scanner",
        "Observability signal added",
        "Similar-pattern sweep",
        "Scope confirmation",
    )
    missing = [s for s in required_sections if s not in doctrine_text]
    assert not missing, (
        f"Doctrine is missing required bug-report sections: {missing}"
    )


def test_doctrine_forbids_one_off_patches(doctrine_text: str) -> None:
    """The mandate must continue to forbid one-off patches outside
    a live P0 outage. Removing this phrase removes the teeth."""
    # We look for both the "one-off patches are forbidden" stance and
    # the P0 exception window, in normalized form.
    normalized = re.sub(r"\s+", " ", doctrine_text)
    assert "One-off patches are forbidden" in normalized, (
        "Doctrine must continue to forbid one-off patches except "
        "during a live P0 outage."
    )
    assert "within 24 hours" in normalized, (
        "Doctrine must continue to bound the P0 exception window "
        "to 24 hours."
    )


def test_doctrine_references_canonical_template_path(
    doctrine_text: str,
) -> None:
    """The doctrine must point at the canonical template path so
    contributors can find it without scavenger-hunting."""
    assert "/app/memory/BUG_CLASS_ELIMINATION_TEMPLATE.md" in doctrine_text


# ─── Template file: exists, structured, and complete ─────────────────


def test_template_has_all_eight_numbered_sections(
    template_text: str,
) -> None:
    """Each of the 8 report sections must be a numbered heading in
    the template. Order matters — contributors read top-to-bottom."""
    required_headings = (
        "## 1. Root cause",
        "## 2. Exact broken boundary",
        "## 3. Boundary class",
        "## 4. Why existing tests missed it",
        "## 5. Regression test / scanner",
        "## 6. Observability signal added",
        "## 7. Similar-pattern sweep",
        "## 8. Scope confirmation",
    )
    missing = [h for h in required_headings if h not in template_text]
    assert not missing, (
        f"Template missing required section headings: {missing}"
    )


def test_template_enumerates_boundary_classes(
    template_text: str,
) -> None:
    """Section 3 must explicitly enumerate the boundary classes,
    otherwise reporters guess and the data is unaggregatable."""
    required_classes = (
        "Frontend payload",
        "Backend request model",
        "URL / path / query",
        "Async job",
        "Payment / wallet / ledger",
        "Cache",
        "Third-party contract",
        "DB invariant",
    )
    missing = [c for c in required_classes if c not in template_text]
    assert not missing, (
        f"Template is missing boundary classes: {missing}"
    )


def test_template_carries_success_definition(template_text: str) -> None:
    """The bottom of the template must restate the success definition
    so reviewers see it at sign-off time."""
    # Strip Markdown blockquote markers and collapse whitespace so the
    # blockquoted, line-wrapped form still matches as a substring.
    normalized = re.sub(r"\s+", " ", template_text.replace("> ", ""))
    assert (
        "this entire class of bug is now impossible, or is "
        "automatically detected the next time it tries to recur."
    ) in normalized, (
        "Template must restate the success-definition sentence at "
        "sign-off time."
    )


def test_doctrine_forbids_one_off_patches_normalized(doctrine_text: str) -> None:
    """Belt-and-suspenders: re-check the P0 exception language with
    blockquote markers stripped, since the mandate paragraph that
    forbids one-off patches lives inside a blockquote."""
    normalized = re.sub(r"\s+", " ", doctrine_text.replace("> ", ""))
    assert "One-off patches are forbidden" in normalized
    assert "within 24 hours" in normalized


def test_template_requires_scope_confirmation_checkboxes(
    template_text: str,
) -> None:
    """Section 8's checkboxes are the explicit anti-Trojan-horse
    guard. Removing them defeats the freeze protection."""
    required_checkboxes = (
        "No unrelated feature work",
        "No unrelated refactors",
        "No incidental UI changes",
        "No incidental dependency bumps",
        "`git diff` reviewed line-by-line for this confirmation",
    )
    missing = [c for c in required_checkboxes if c not in template_text]
    assert not missing, (
        f"Template missing scope-confirmation checkboxes: {missing}"
    )


# ─── CI registration: this scanner must run in audit-boundaries ──────


def test_this_audit_is_registered_in_makefile(makefile_text: str) -> None:
    """The mandate's pinning suite must itself be wired into
    `make audit-boundaries`. A pinning test that never runs is no
    pin at all."""
    assert "test_bug_class_elimination_mandate_2026_05.py" in makefile_text, (
        "The bug-class elimination pinning suite must be listed in "
        "BOUNDARY_AUDIT_SUITES inside /app/Makefile."
    )
