"""P0 2026-06 — Admin Panel content-area must never be obscured by consumer overlays.

Production incident (Jun 2026):
  Admin reported `/app/admin` was visually rendering the sidebar but the
  main content area was blank / unreachable. Root cause was the global
  `FirstActionOverlay` (and `PostValueOverlay`) mounting unconditionally
  for any authenticated session and rendering a full-viewport modal
  (`fixed inset-0 z-[10500] bg-black/85 backdrop-blur-md`) on top of
  the admin dashboard.

  The pre-existing admin-skip guards relied solely on
  `JSON.parse(localStorage.getItem('user'))`. If that object was
  missing, stale, or had a role value with unexpected casing, the
  guard was bypassed and the overlay covered the admin content.

Bug-class fix (defense in depth):
  1. Hard route guard — both overlays must short-circuit when the
     current pathname starts with `/app/admin`. This is the
     non-bypassable check.
  2. JWT-based admin detection — both overlays must additionally
     decode the JWT token's `role` claim (uppercased) and treat
     `ADMIN` / `SUPERADMIN` as admin. This protects the rest of the
     app shell (eg. `/app`) from the same overlay-obscuration class
     when `localStorage.user` is out of sync with the JWT.

Registered under `make audit-boundaries`. Any future PR that removes
the route guard or the JWT-based admin check will fail this audit.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path("/app")
FIRST_ACTION = REPO / "frontend/src/components/guide/FirstActionOverlay.jsx"
POST_VALUE = REPO / "frontend/src/components/guide/PostValueOverlay.jsx"


@pytest.fixture(scope="module")
def first_action_src() -> str:
    assert FIRST_ACTION.exists(), f"missing {FIRST_ACTION}"
    return FIRST_ACTION.read_text()


@pytest.fixture(scope="module")
def post_value_src() -> str:
    assert POST_VALUE.exists(), f"missing {POST_VALUE}"
    return POST_VALUE.read_text()


# ── 1. Route-level hard guard ────────────────────────────────────────────────


def test_first_action_overlay_short_circuits_on_admin_routes(first_action_src: str) -> None:
    """FirstActionOverlay must early-return when pathname starts with /app/admin."""
    assert "useLocation" in first_action_src, (
        "FirstActionOverlay must import useLocation from react-router-dom to "
        "read the current pathname; the admin-route guard depends on it."
    )
    assert "location.pathname.startsWith('/app/admin')" in first_action_src, (
        "FirstActionOverlay must contain an explicit early-return when the "
        "pathname starts with '/app/admin'. Without this guard a stale "
        "localStorage.user value lets the onboarding modal cover the admin "
        "dashboard."
    )


def test_post_value_overlay_short_circuits_on_admin_routes(post_value_src: str) -> None:
    """PostValueOverlay must early-return when pathname starts with /app/admin."""
    assert "useLocation" in post_value_src, (
        "PostValueOverlay must import useLocation from react-router-dom."
    )
    assert "location.pathname.startsWith('/app/admin')" in post_value_src, (
        "PostValueOverlay must contain an explicit early-return when the "
        "pathname starts with '/app/admin'."
    )


# ── 2. JWT-based admin detection (defense in depth) ──────────────────────────


def test_first_action_overlay_uses_jwt_admin_detection(first_action_src: str) -> None:
    """FirstActionOverlay must decode the JWT and treat ADMIN/SUPERADMIN as admin."""
    assert "isAdminFromToken" in first_action_src, (
        "FirstActionOverlay must define and call isAdminFromToken() — the "
        "JWT-claim-based admin check that does not rely on localStorage.user."
    )
    assert "if (isAdminFromToken()) return;" in first_action_src, (
        "FirstActionOverlay must short-circuit on JWT admin role."
    )
    assert "'SUPERADMIN'" in first_action_src or '"SUPERADMIN"' in first_action_src, (
        "FirstActionOverlay must treat SUPERADMIN as admin (uppercase)."
    )


def test_post_value_overlay_uses_jwt_admin_detection(post_value_src: str) -> None:
    """PostValueOverlay must decode the JWT and treat ADMIN/SUPERADMIN as admin."""
    assert "isAdminFromToken" in post_value_src, (
        "PostValueOverlay must define and call isAdminFromToken()."
    )
    assert "if (isAdminFromToken()) return;" in post_value_src, (
        "PostValueOverlay must short-circuit on JWT admin role."
    )
    assert "'SUPERADMIN'" in post_value_src or '"SUPERADMIN"' in post_value_src, (
        "PostValueOverlay must treat SUPERADMIN as admin (uppercase)."
    )


# ── 3. Path guard must run BEFORE the show-state side effects ────────────────


def test_first_action_admin_guard_runs_before_setShow(first_action_src: str) -> None:
    """The admin route guard must execute before any setShow(true) call."""
    guard_idx = first_action_src.find("location.pathname.startsWith('/app/admin')")
    show_idx = first_action_src.find("setShow(true)")
    assert guard_idx != -1 and show_idx != -1, "expected both guard and setShow"
    assert guard_idx < show_idx, (
        "Admin route guard must appear before setShow(true) so the overlay "
        "never mounts on /app/admin."
    )


def test_post_value_admin_guard_runs_before_setShow(post_value_src: str) -> None:
    """The admin route guard must execute before any setShow(true) call."""
    guard_idx = post_value_src.find("location.pathname.startsWith('/app/admin')")
    show_idx = post_value_src.find("setShow(true)")
    assert guard_idx != -1 and show_idx != -1, "expected both guard and setShow"
    assert guard_idx < show_idx, (
        "Admin route guard must appear before setShow(true) so the overlay "
        "never mounts on /app/admin."
    )
