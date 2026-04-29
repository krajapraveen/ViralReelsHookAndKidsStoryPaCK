"""Tests for the P0 result-page escape-path UX fix (2026-04-29).

Source-level guarantees that the Back + Home navigation controls are wired
into ResultStep, properly routed, and don't disturb the existing primary
CTAs (Download / WhatsApp / More / Make another).
"""
import os
import re


SRC_PATH = "/app/frontend/src/pages/PhotoTrailerPage.jsx"


def _src() -> str:
    return open(SRC_PATH).read()


def _result_step_block() -> str:
    """Slice out just the ResultStep function body so we don't get false
    positives from other components on the page."""
    s = _src()
    start = s.index("function ResultStep(")
    # Walk to the next top-level `function ` after this one
    next_fn = s.index("\nfunction ", start + 1)
    return s[start:next_fn]


def test_result_step_renders_back_button():
    block = _result_step_block()
    assert 'data-testid="trailer-result-back-btn"' in block, \
        "ResultStep must render a Back button with the documented testid"


def test_result_step_renders_home_button():
    block = _result_step_block()
    assert 'data-testid="trailer-result-home-btn"' in block, \
        "ResultStep must render a Home button with the documented testid"


def test_result_step_uses_navigate_for_home():
    """Home button must route to /app via react-router useNavigate, not a
    full-page reload (which would dump state and feel jarring)."""
    block = _result_step_block()
    assert "useNavigate" in block, "ResultStep must import/use useNavigate"
    assert "navigate('/app')" in block, "Home button must navigate to /app"


def test_result_step_back_button_uses_callback_or_route_fallback():
    """Back must prefer the parent-supplied onBackToWizard callback (so it
    can reset wizard state in-page) and fall back to /app/photo-trailer if
    no callback was passed."""
    block = _result_step_block()
    assert "onBackToWizard" in block, "Back button must accept onBackToWizard prop"
    assert "navigate('/app/photo-trailer')" in block, \
        "Back must route to /app/photo-trailer when no callback is provided"


def test_result_step_nav_container_has_testid():
    block = _result_step_block()
    assert 'data-testid="trailer-result-nav"' in block, \
        "ResultStep must wrap the Back/Home controls in a labelled nav container"


def test_result_step_preserves_existing_primary_ctas():
    """The fix must not delete or disturb the existing action buttons."""
    block = _result_step_block()
    for tid in (
        "trailer-download-btn",
        "trailer-whatsapp-share-btn",
        "trailer-share-btn",          # "More"
        "trailer-create-another-btn", # "Make another"
        "trailer-result-video",
    ):
        assert f'data-testid="{tid}"' in block, \
            f"Existing CTA {tid} must remain untouched"


def test_result_step_uses_arrow_left_and_home_icons():
    """Visual: the Back button should be an ArrowLeft (not a generic chevron)
    and the Home button should be a Home icon. These are imported from
    lucide-react at the top of the file."""
    src = _src()
    assert "ArrowLeft" in src and "Home," in src, \
        "ArrowLeft + Home icons must be imported from lucide-react"
    block = _result_step_block()
    assert "<ArrowLeft" in block
    assert "<Home" in block


def test_back_button_label_is_responsive():
    """Founder spec: must work on mobile and desktop. The text label is
    hidden on tiny screens (icon only) and shown >= sm. No horizontal overflow."""
    block = _result_step_block()
    # Both buttons hide their text on the smallest screens via 'hidden sm:inline'
    occurrences = re.findall(r'hidden sm:inline', block)
    # Two — one per button (Back + Home)
    assert len(occurrences) >= 2, \
        f"Back+Home labels must use 'hidden sm:inline' for mobile-safe layout; got {len(occurrences)}"


def test_parent_passes_onBackToWizard_callback():
    """The page that mounts ResultStep must pass the onBackToWizard
    callback. Without it, Back falls through to the route-based fallback,
    which is correct but less smooth than the in-page reset."""
    src = _src()
    # Find the <ResultStep /> usage and verify both props are present
    assert re.search(
        r"<ResultStep\b[^/]*?\bonBackToWizard\s*=", src, re.S
    ), "Parent must pass onBackToWizard prop to <ResultStep />"
