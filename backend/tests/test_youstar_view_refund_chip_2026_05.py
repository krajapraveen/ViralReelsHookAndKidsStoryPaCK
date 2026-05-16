"""
YouStar "View refund" chip — 2026-05-16 P0 (trust loop)

User mandate:
  "Only show when refund is CONFIRMED.
   Link directly to /app/billing.
   Small secondary CTA only — do not overpower primary actions.
   No new backend endpoint. No modal/pop-up."

Coverage:
  • Chip element exists with data-testid=trailer-view-refund-chip
  • Visibility is gated on `job.refunded_credits > 0`
  • Chip is an <a> linking to /app/billing (no modal, no new endpoint)
  • Chip shows the refunded amount + "View" affordance
  • Primary CTAs (Retry / Edit & retry / Delete) are still rendered as
    buttons — chip is purely additive
"""
from pathlib import Path
import re

FRONTEND = Path("/app/frontend/src/pages/PhotoTrailerPage.jsx")


def _failed_step_source() -> str:
    """Return the source of the FailedStep component only — keeps our
    assertions scoped so unrelated parts of the file can't accidentally
    satisfy them."""
    src = FRONTEND.read_text(encoding="utf-8")
    m = re.search(
        r"function FailedStep\([^)]*\)\s*\{(.*?)^\}\s*$",
        src,
        re.S | re.M,
    )
    assert m, "FailedStep component not found in PhotoTrailerPage.jsx"
    return m.group(0)


def test_view_refund_chip_data_testid_present():
    body = _failed_step_source()
    assert 'data-testid="trailer-view-refund-chip"' in body, \
        "Chip must carry the regression-stable data-testid"


def test_view_refund_chip_gated_on_confirmed_refund():
    """Chip MUST be wrapped in a refund-confirmed conditional. The user
    rule is strict: 'Only show when refund is CONFIRMED.'"""
    body = _failed_step_source()
    # The chip exists AND there's a conditional gate involving refunded_credits.
    assert "refundConfirmed" in body
    assert "refunded_credits" in body
    # The conditional renders the chip block
    assert "{refundConfirmed && (" in body, \
        "Chip render must be gated by refundConfirmed flag"
    # And the flag itself must derive from refunded_credits > 0
    assert re.search(r"Number\(job\??\.?refunded_credits[^)]*\)\s*>\s*0", body), \
        "refundConfirmed must be computed from job.refunded_credits > 0"


def test_view_refund_chip_links_to_billing_no_modal():
    body = _failed_step_source()
    # Must be an <a> href, not a button with onClick → modal
    assert 'href="/app/billing"' in body, \
        "Chip must link directly to /app/billing (no modal, no new endpoint)"
    # And the chip block must NOT introduce a modal — no Dialog/Modal usage
    assert "Modal" not in body and "Dialog" not in body, \
        "Chip section must not introduce a modal/dialog"


def test_view_refund_chip_shows_credits_and_view_affordance():
    body = _failed_step_source()
    # The visible label must surface BOTH the refunded amount AND a "View"
    # affordance so the user knows it's clickable and what they'll see.
    assert "{job.refunded_credits}" in body
    assert "View" in body
    assert "refunded" in body.lower()


def test_view_refund_chip_does_not_replace_primary_ctas():
    """The chip is additive only — Retry / Edit & retry / Delete buttons
    must still be present."""
    body = _failed_step_source()
    assert 'data-testid="trailer-retry-btn"' in body
    assert 'data-testid="trailer-edit-btn"' in body
    assert 'data-testid="trailer-delete-btn"' in body


def test_view_refund_chip_uses_secondary_styling():
    """User mandate: 'Small secondary CTA only — do not overpower primary
    actions.' Sanity-check that the chip uses muted/secondary classes and
    NOT the primary violet-600 button class reserved for Retry."""
    body = _failed_step_source()
    # Find the entire <a ...>...</a> chip element (from opening <a to </a>)
    m = re.search(
        r'<a[^>]*?trailer-view-refund-chip[^>]*?>.*?</a>',
        body,
        re.S,
    )
    if not m:
        # Fall back: regex captures from <a back through the className
        m = re.search(
            r'<a\b[^<]*?(?:[^<]|<[^/])*?</a>',
            body,
            re.S,
        )
    assert m, "Could not locate the chip element"
    chip = m.group(0)
    # Must NOT use the primary CTA color (violet-600 background)
    assert "bg-violet-600" not in chip, \
        "Chip must not use the primary CTA background — keep it secondary"
    # Should use a small text size (text-[11px] or text-xs)
    assert ("text-[11px]" in chip) or ("text-xs" in chip), \
        "Chip must use a small text size to stay secondary"
