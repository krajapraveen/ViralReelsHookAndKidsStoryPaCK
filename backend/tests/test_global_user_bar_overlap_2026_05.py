"""
P0 2026-05-19 — Shared global user bar layout hardening.

Production screenshot showed the `GlobalUserBar` cluster (bell pill +
credits/profile pill, fixed to top-right of every authenticated route)
letting page title text bleed visibly through the pill backgrounds.

Root cause:
  • Bell button used `bg-black/40` and credits pill used `bg-black/60`.
    Both alphas were low enough that the page title underneath ("Preview
    & Generate" → "pe…") was clearly readable through the glass.
  • At narrow viewports the 6 px sibling gap was small enough for the
    two pills' backdrop-blur halos to visually merge.

Structural contract pinned by these tests:
  1. Outer wrapper sits fixed top-right with z-index ≥ 10002 and is
     pointer-events-none so dead inter-pill space never steals clicks.
  2. Inner row is `flex flex-nowrap` so the cluster never wraps onto a
     second row at any viewport.
  3. Both pills use SOLID `bg-slate-950/95` so page content can never
     read through.
  4. Both pills carry `flex-shrink-0` so they never compress to
     overlap at narrow widths.
  5. Bar is capped at `max-w-[calc(100vw-0.5rem)]` so it can never
     trigger horizontal scroll on mobile.
  6. Each pill re-enables pointer events so clicks still register.
"""
from __future__ import annotations

from pathlib import Path

USER_BAR = Path("/app/frontend/src/components/GlobalUserBar.jsx")
BELL = Path("/app/frontend/src/components/NotificationBell.js")


def test_global_user_bar_outer_wrapper_is_pointer_events_none():
    """The outer wrapper must be pointer-events-none so dead pixels
    between pills don't intercept page-level clicks."""
    src = USER_BAR.read_text()
    # The opening fixed-position div should carry pointer-events-none.
    wrapper = src.split('data-testid="global-user-bar"', 1)[0][-500:]
    assert "pointer-events-none" in wrapper, (
        "Outer GlobalUserBar wrapper must be pointer-events-none — "
        "dead inter-pill space was previously stealing clicks"
    )
    assert "z-[10002]" in wrapper, (
        "Outer wrapper must keep its high z-index above all page content"
    )


def test_global_user_bar_inner_row_is_flex_nowrap():
    """`flex-nowrap` is the structural guarantee against the cluster
    wrapping onto a second row at any viewport."""
    src = USER_BAR.read_text()
    assert "flex-nowrap" in src, (
        "Inner cluster row must be flex-nowrap so it never wraps "
        "across viewports"
    )
    assert "items-center" in src
    assert "justify-end" in src, (
        "Inner row must justify-end so the cluster hugs the right edge"
    )


def test_global_user_bar_uses_solid_opaque_pill_backgrounds():
    """The production bleed-through happened because pill backgrounds
    were `bg-black/40` / `bg-black/60` — too transparent. Both pills
    must now use opaque `bg-slate-950/95`."""
    src = USER_BAR.read_text()
    # Strip JS line comments so historical references in docstrings
    # don't trip the legacy-class assertions.
    import re
    code_only = re.sub(r"//.*$", "", src, flags=re.M)
    code_only = re.sub(r"/\*.*?\*/", "", code_only, flags=re.S)
    # The credits/profile pill must be on the new opaque background.
    assert "bg-slate-950/95" in code_only, (
        "Credits/profile pill must use bg-slate-950/95 — anything more "
        "transparent reproduces the production bleed-through"
    )
    # Legacy transparent backgrounds must be GONE from active classNames.
    assert "bg-black/40" not in code_only, (
        "Legacy bg-black/40 must be removed from GlobalUserBar"
    )
    assert "bg-black/60" not in code_only, (
        "Legacy bg-black/60 must be removed from GlobalUserBar"
    )


def test_notification_bell_uses_solid_opaque_background():
    """Bell button was the worse offender — bg-black/40. It now matches
    the credits pill at bg-slate-950/95."""
    src = BELL.read_text()
    btn_block = src.split('data-testid="notification-btn"', 1)[0][-800:]
    assert "bg-slate-950/95" in btn_block, (
        "Notification bell button must use bg-slate-950/95 — was "
        "bg-black/40 which let page text bleed through"
    )
    assert "bg-black/40" not in btn_block, (
        "Legacy bg-black/40 must be removed from the bell button"
    )


def test_both_pills_have_flex_shrink_zero():
    """At narrow viewports a missing flex-shrink-0 lets pills compress
    into each other. Both pills must be marked non-shrinkable."""
    user_bar = USER_BAR.read_text()
    bell = BELL.read_text()
    # The bell button + the credits button + the inner Zap/User icons
    # all need flex-shrink-0. Count occurrences as a coarse guard.
    assert user_bar.count("flex-shrink-0") >= 3, (
        f"Expected ≥3 flex-shrink-0 anchors in GlobalUserBar; found "
        f"{user_bar.count('flex-shrink-0')}"
    )
    btn = bell.split('data-testid="notification-btn"', 1)[0][-800:]
    assert "flex-shrink-0" in btn, (
        "Bell button must carry flex-shrink-0 so it cannot compress "
        "at narrow widths"
    )


def test_global_user_bar_has_max_viewport_width_cap():
    """Mobile widths (320–375px) must not produce horizontal scroll
    from the bar's natural width. A max-width cap on the wrapper is the
    structural guarantee."""
    src = USER_BAR.read_text()
    assert "max-w-[calc(100vw-" in src, (
        "GlobalUserBar wrapper must cap at calc(100vw - gutter) so it "
        "can never push horizontal scroll on mobile"
    )


def test_pills_have_sibling_gap_to_prevent_halo_overlap():
    """At heavy zoom the two pills' backdrop-blur halos can visually
    merge into each other if the sibling gap is too tight. We bumped
    the gap to `gap-2 sm:gap-2.5` (was `gap-1.5 sm:gap-2`)."""
    src = USER_BAR.read_text()
    row = src.split("flex-nowrap", 1)[1].split(">", 1)[0]
    assert "gap-2" in row, "Inner row must use gap-2+ between pills"
    # The legacy tight gap must be gone.
    assert "gap-1.5" not in row, (
        "Legacy gap-1.5 was tight enough for backdrop-blur halos to "
        "visually merge — must be removed"
    )


def test_pills_keep_their_canonical_testids():
    """Smoke: the data-testid contract surface that downstream Playwright
    suites and the GlobalUserBar e2e checks depend on must not regress."""
    src = USER_BAR.read_text()
    for tid in ("global-user-bar", "user-menu-toggle", "user-menu-dropdown",
                "menu-profile", "menu-billing", "menu-settings",
                "menu-logout"):
        assert f'data-testid="{tid}"' in src, f"Missing testid: {tid}"
    assert 'data-testid="notification-btn"' in BELL.read_text()
    assert 'data-testid="notification-bell"' in BELL.read_text()
