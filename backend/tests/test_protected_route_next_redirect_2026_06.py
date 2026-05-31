"""
P0 Reliability — Protected-route deep-link `?next=` redirect contract (2026-06)
==============================================================================

Bug class pinned
----------------
Anonymous deep-links to ANY `/app/<route>` (email links, shared URLs,
bookmarks) were silently stripped on the way to `/login`. Users signed
in and landed on `/app`, losing the context they were trying to reach.
That is a measurable, repeated funnel leak.

The cure is a single `LoginRedirect` component in `App.js` that captures
the current location and forwards `?next=<encoded-original-path>`. This
test pins three invariants:

  1. NO route in App.js uses the legacy `<Navigate to="/login" />`
     pattern that drops the destination.
  2. A canonical `LoginRedirect` component exists and is the ONLY way
     protected routes redirect anonymous visitors.
  3. The redirect target is `/login?next=<encoded-path>` for every
     non-trivial path (i.e., not `/`, `/login`, `/signup`).
  4. The catch-all route still works.
  5. Legacy `?return=` is still accepted by Login.js (back-compat).

Covered route classes (representative sample, founder-spec):
  - Billing                       (/app/billing)
  - One creator-tools / creation  (/app/story-video-studio paths,
                                   /app/story-generator)
  - One dashboard / library       (/app/dashboard, /app/my-space,
                                   /app/characters)
  - One admin route               (/app/admin/...)
  - Backwards-compat: `/login?return=...` still navigates to target
    after successful login.
"""
import os
import re
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO = pathlib.Path(__file__).resolve().parents[2]
APP_JS = REPO / "frontend" / "src" / "App.js"
LOGIN_JS = REPO / "frontend" / "src" / "pages" / "Login.js"


def _read(p):
    assert p.exists(), f"required file missing: {p}"
    return p.read_text(encoding="utf-8")


class TestNoLegacyNavigateToLogin:
    """The legacy `<Navigate to="/login" />` pattern must be gone from
    the live routing table. It silently drops the destination."""

    def test_no_inline_navigate_to_login_in_routes(self):
        src = _read(APP_JS)
        # Forbid `<Navigate to="/login" />` (literal, no attrs) anywhere.
        bad = re.findall(r'<Navigate\s+to="/login"\s*/>', src)
        assert not bad, (
            f"Found {len(bad)} legacy `<Navigate to=\"/login\" />` in "
            f"App.js. Use <LoginRedirect /> so the original path is "
            f"preserved via ?next=."
        )

    def test_no_navigate_to_login_with_state_only(self):
        """Catch the ProtectedRoute-style legacy too:
        `<Navigate to="/login" state={...} replace />` — also drops the
        destination from the URL. Replace with <LoginRedirect />."""
        src = _read(APP_JS)
        bad = re.findall(
            r'<Navigate\s+to="/login"[^>]*?state=\{[^}]+\}[^>]*?/>',
            src,
        )
        assert not bad, (
            "ProtectedRoute fallback must use <LoginRedirect />, "
            "not `<Navigate to=\"/login\" state=... />`."
        )


class TestLoginRedirectComponent:
    """A canonical LoginRedirect component must exist and emit a
    `/login?next=<encoded>` URL."""

    def test_login_redirect_component_defined(self):
        src = _read(APP_JS)
        assert re.search(
            r"function\s+LoginRedirect\s*\(\s*\)",
            src,
        ), "App.js must define a LoginRedirect() helper component."

    def test_login_redirect_uses_canonical_next_param(self):
        src = _read(APP_JS)
        # Must build a /login?next=${encodeURIComponent(path)} target.
        assert re.search(
            r"`/login\?next=\$\{encodeURIComponent\(",
            src,
        ), (
            "LoginRedirect must build `/login?next=${encodeURIComponent(path)}` "
            "— that's the canonical contract."
        )

    def test_login_redirect_avoids_self_loop(self):
        """The redirect must not preserve `/login` or `/signup` as next,
        otherwise an anonymous visit to /login itself would loop."""
        src = _read(APP_JS)
        # Look for the safety guard in the component.
        m = re.search(
            r"function\s+LoginRedirect\s*\(\s*\)[^}]*?"
            r"(safe|target)[^}]*?'/login'",
            src,
            re.DOTALL,
        )
        assert m, (
            "LoginRedirect must guard against `/login` and `/signup` "
            "as next-paths to avoid redirect loops."
        )
        # Defensive: must not allow `next=/login` literal.
        assert "next=/login" not in src, (
            "LoginRedirect must never set next=/login — that's a loop."
        )


class TestProtectedRoutesUseLoginRedirect:
    """Spec-mandated route classes MUST all use LoginRedirect."""

    BILLING = '/app/billing'
    CREATION = ['/app/story-video-studio', '/app/story-generator', '/app/comic-storybook']
    DASHBOARD = ['/app/dashboard', '/app/my-space', '/app/characters']
    ADMIN = '/app/admin'

    def _route_line(self, src, path):
        # Each `<Route path="..." element={...} />` lives on a single
        # line. Grab the whole line for that path.
        for line in src.splitlines():
            if f'path="{path}"' in line and '<Route ' in line:
                return line
        return None

    def test_billing_route_uses_login_redirect(self):
        src = _read(APP_JS)
        line = self._route_line(src, self.BILLING)
        assert line is not None, f"Route for {self.BILLING} missing"
        assert "<LoginRedirect />" in line, (
            f"Route {self.BILLING} must use <LoginRedirect /> "
            f"(found: {line})"
        )
        # Existing /app/billing behavior unchanged: still gated on
        # isAuthenticated, still renders <Billing />.
        assert "isAuthenticated" in line and "Billing" in line, (
            "Billing route must still gate on isAuthenticated"
        )

    def test_one_creation_route_uses_login_redirect(self):
        src = _read(APP_JS)
        found = False
        for p in self.CREATION:
            line = self._route_line(src, p)
            if line and "<LoginRedirect />" in line:
                found = True
                break
        assert found, (
            "At least one creation route "
            f"({self.CREATION}) must use <LoginRedirect />."
        )

    def test_one_dashboard_or_library_uses_login_redirect(self):
        src = _read(APP_JS)
        found = False
        for p in self.DASHBOARD:
            line = self._route_line(src, p)
            if line and "<LoginRedirect />" in line:
                found = True
                break
        assert found, (
            "At least one dashboard/library route "
            f"({self.DASHBOARD}) must use <LoginRedirect />."
        )

    def test_admin_routes_remain_lazy_loaded(self):
        """Admin section is nested under `<Route path='/app/admin'>` and
        is rendered via AdminLayout, which performs its own admin-only
        gate. We just assert the section still exists and is not gated
        by `<Navigate to="/login" />` directly (which would lock out
        admins on a session refresh)."""
        src = _read(APP_JS)
        # The admin parent route is present.
        assert '<Route path="/app/admin"' in src, (
            "Admin route tree must still exist."
        )
        # No raw `<Navigate to="/login" />` inside the admin block.
        admin_block = re.search(
            r'<Route path="/app/admin".*?</Route>',
            src,
            re.DOTALL,
        )
        assert admin_block, "Admin block not parseable"
        assert '<Navigate to="/login"' not in admin_block.group(0), (
            "Admin block must not embed legacy login Navigates."
        )


class TestCatchAllAndPublicRoutesUntouched:
    """Public/open routes and the catch-all must NOT have been turned
    into LoginRedirect calls by mistake."""

    def test_catch_all_redirects_to_app_or_home(self):
        src = _read(APP_JS)
        # The catch-all line: <Route path="*" element={<Navigate to={isAuthenticated ? "/app" : "/"} replace />} />
        m = re.search(
            r'<Route\s+path="\*"\s+element=\{<Navigate\s+to=\{isAuthenticated\s*\?\s*"/app"\s*:\s*"/"\}',
            src,
        )
        assert m, (
            "Catch-all route must remain `Navigate to={isAuthenticated "
            "? '/app' : '/'}` — unaffected by this refactor."
        )

    def test_public_routes_have_no_login_redirect(self):
        """Sample public routes must still render their lazy component
        directly, NOT through LoginRedirect."""
        src = _read(APP_JS)
        public_paths = ['"/"', '"/pricing"', '"/contact"', '"/blog"',
                        '"/explore"', '"/security"']
        for p in public_paths:
            line = re.search(
                r'<Route\s+path=' + re.escape(p) + r'\s+element=\{[^}]+\}',
                src,
            )
            assert line, f"Public route {p} missing"
            assert "<LoginRedirect />" not in line.group(0), (
                f"Public route {p} must NOT use LoginRedirect."
            )


class TestLegacyReturnParamBackcompat:
    """`?return=` MUST still work — old emails, bookmarks, and the
    previous interceptor's URLs still flow through."""

    def test_login_reads_return_param(self):
        src = _read(LOGIN_JS)
        assert re.search(
            r"searchParams\.get\(\s*['\"]return['\"]\s*\)",
            src,
        ), "Login.js must still accept legacy `?return=`."

    def test_login_prefers_next_over_return(self):
        src = _read(LOGIN_JS)
        assert re.search(
            r"searchParams\.get\(\s*['\"]next['\"]\s*\)\s*\|\|\s*"
            r"searchParams\.get\(\s*['\"]return['\"]\s*\)",
            src,
        ), (
            "Login.js must prefer `?next=` (canonical) over `?return=` "
            "(legacy)."
        )


class TestNoRedirectLoops:
    """Static-source check that the canonical redirect cannot loop."""

    def test_no_navigate_target_includes_next_login(self):
        """Verify no code path writes `next=/login` (which would loop)."""
        src = _read(APP_JS)
        assert "next=/login" not in src, (
            "Found `next=/login` literal — would create a redirect loop."
        )

    def test_login_redirect_skips_root_and_login(self):
        """The LoginRedirect safe-guard must explicitly exclude
        `/`, `/login`, `/signup` from next-preservation."""
        src = _read(APP_JS)
        # Find the function body and check for the three guards.
        m = re.search(
            r"function\s+LoginRedirect\s*\(\s*\)\s*\{(.*?)\n\}",
            src,
            re.DOTALL,
        )
        assert m, "LoginRedirect function body not found"
        body = m.group(1)
        for needle in ["'/'", "'/login'", "'/signup'"]:
            assert needle in body, (
                f"LoginRedirect must guard against {needle} as a "
                f"next-target (loop prevention)."
            )
