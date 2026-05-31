"""
P0 Bug-Class Elimination — Billing page reliability (2026-06)
============================================================

Original symptom
----------------
User reaches /app/billing → page shell renders → "Failed to load billing
data" → entire page unusable. Root cause: a single dependency failure
(401 on /api/credits/balance) was nuking the entire page because the
page used Promise.all and trusted a stale localStorage user object
while the live token was expired/missing.

Bug class
---------
Two distinct, recurring classes are pinned by this file:

  (A) **Dependency-coupling crash** — a non-critical XHR failure must
      never tombstone an entire page whose primary content (products)
      loaded successfully. Promise.all is forbidden when one of the
      branches is decorative (balance chip). Use Promise.allSettled,
      surface a banner, keep the page alive.

  (B) **Stale-session phantom** — pages that read auth state from
      localStorage may render an "authenticated" shell with a token
      that is already missing or expired, leading to mass 401s on
      sub-requests. The cure is a live session probe (/api/auth/me)
      BEFORE the authenticated shell renders, with a clean redirect
      to `/login?next=<current-path>` on 401.

Founder contract
----------------
1. `/api/cashfree/products` is **public** and MUST be reachable
   without a token. (Marketing/discovery surface.)
2. `/api/credits/balance` requires auth and MUST return 401 without
   a valid token.
3. `/api/auth/me` is the canonical session-probe endpoint. It MUST
   return 401 for missing/expired token and MUST NOT be mutating.
4. The Billing page MUST NOT use Promise.all. It MUST use
   Promise.allSettled (or equivalent independent fetch) so that one
   401 cannot kill the products UI.
5. The login redirect from billing MUST use `?next=` (the canonical
   param). Login.js MUST accept both `?next=` and `?return=`.
6. The global axios interceptor MUST NOT auto-redirect on
   /api/auth/me 401 — that endpoint is a self-handled probe.
   (Otherwise two redirects race, with inconsistent param names.)

Test coverage (5 cases the freeze spec requires)
-------------------------------------------------
  T1. products success + balance failure  → page contract is sound
  T2. expired token                       → /auth/me 401 contract
  T3. stale cached user (no token)        → /auth/me 401 contract
  T4. auth redirect uses ?next= and Login accepts both
  T5. degraded balance state               → frontend banner contract
"""
import os
import sys
import re
import pathlib
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "").rstrip("/")
if not BASE_URL:
    BASE_URL = "https://trust-engine-5.preview.emergentagent.com"

REPO = pathlib.Path(__file__).resolve().parents[2]
BILLING_JS = REPO / "frontend" / "src" / "pages" / "Billing.js"
LOGIN_JS = REPO / "frontend" / "src" / "pages" / "Login.js"
API_JS = REPO / "frontend" / "src" / "utils" / "api.js"


# ─────────────────────────────────────────────────────────────────────
# Backend contract tests
# ─────────────────────────────────────────────────────────────────────
class TestBackendBillingContract:
    """Backend MUST honor the public/auth split the Billing page relies on."""

    def test_products_endpoint_is_public_returns_200(self):
        """T1a. /api/cashfree/products MUST return 200 without auth.

        If this regresses, the billing page (which the user opens before
        any auth concerns matter) becomes a dead surface for prospects.
        """
        r = requests.get(f"{BASE_URL}/api/cashfree/products", timeout=15)
        assert r.status_code == 200, (
            f"products endpoint must be public, got {r.status_code}: "
            f"{r.text[:200]}"
        )
        body = r.json()
        assert isinstance(body, dict), "products response must be a JSON object"
        assert "products" in body and isinstance(body["products"], dict), (
            "products contract: {'products': {...}} required for "
            "billing page rendering"
        )
        assert len(body["products"]) > 0, "products dict must not be empty"

    def test_credits_balance_requires_auth(self):
        """T1b. /api/credits/balance MUST 401 without auth.

        This is the failure mode that USED to kill the page. The
        backend contract is correct — the frontend must tolerate it.
        """
        r = requests.get(f"{BASE_URL}/api/credits/balance", timeout=15)
        assert r.status_code in (401, 403), (
            f"balance endpoint must require auth, got {r.status_code}"
        )

    def test_auth_me_is_session_probe_401_on_no_token(self):
        """T2. /api/auth/me MUST 401 without a token (probe contract)."""
        r = requests.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r.status_code == 401, (
            f"/api/auth/me must 401 without auth, got {r.status_code}"
        )

    def test_auth_me_is_session_probe_401_on_garbage_token(self):
        """T3. /api/auth/me MUST 401 on a stale/garbage token. The
        frontend uses this signal to clear localStorage and redirect."""
        r = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": "Bearer stale-token-xyz"},
            timeout=15,
        )
        assert r.status_code == 401, (
            f"/api/auth/me must 401 on garbage token, got {r.status_code}"
        )


# ─────────────────────────────────────────────────────────────────────
# Frontend contract tests (source-level invariants)
# ─────────────────────────────────────────────────────────────────────
class TestBillingFrontendContract:
    """Frontend source MUST enforce the bug-class invariants. These are
    not stylistic — they are the contract that keeps the page alive."""

    def _read(self, path):
        assert path.exists(), f"required file missing: {path}"
        return path.read_text(encoding="utf-8")

    def test_billing_does_not_use_promise_all(self):
        """T1. Billing.js MUST NOT use Promise.all for the
        products+balance fan-out. One 401 cannot kill the page."""
        src = self._read(BILLING_JS)
        # Forbid Promise.all( on products+credits fetch.
        # Tolerate Promise.allSettled (which is the cure).
        assert "Promise.all(" not in src or "Promise.allSettled" in src, (
            "Billing.js uses Promise.all — forbidden. Use "
            "Promise.allSettled so products survive a balance failure."
        )
        # Hard-fail if both products and balance get fed into Promise.all
        # in the same expression.
        bad = re.search(
            r"Promise\.all\(\s*\[[^\]]*getProducts[^\]]*getBalance[^\]]*\]",
            src,
            re.DOTALL,
        )
        assert not bad, (
            "Billing.js must not bundle products and balance into "
            "Promise.all — that is the original bug class."
        )

    def test_billing_uses_promise_all_settled(self):
        """T1. Billing.js MUST use Promise.allSettled — positive
        assertion so a future refactor can't silently regress."""
        src = self._read(BILLING_JS)
        assert "Promise.allSettled" in src, (
            "Billing.js MUST use Promise.allSettled for the "
            "products/balance fan-out (decoupled-fetch contract)."
        )

    def test_billing_session_probes_auth_me_before_render(self):
        """T2/T3. Billing.js MUST call /api/auth/me before rendering
        authenticated content to detect stale-session phantom."""
        src = self._read(BILLING_JS)
        assert "/api/auth/me" in src, (
            "Billing.js missing live session probe — stale-session "
            "phantom bug class will recur."
        )

    def test_billing_handles_401_with_canonical_next_redirect(self):
        """T4. Billing.js MUST redirect to /login?next=/app/billing on
        a dead session — not /login alone, not /login?return=...
        The canonical param is `next` (founder-mandated)."""
        src = self._read(BILLING_JS)
        # Look for the canonical redirect string with `next=`.
        assert "/login?next=" in src, (
            "Billing.js must redirect with `?next=` on dead session."
        )
        # AND it must encode the return path to /app/billing.
        assert "/app/billing" in src and re.search(
            r"encodeURIComponent\(\s*['\"]/app/billing['\"]\s*\)",
            src,
        ), (
            "Billing.js must encodeURIComponent('/app/billing') in the "
            "`next` param — anything else breaks the round-trip."
        )

    def test_billing_clears_stale_local_storage_on_401(self):
        """T3. Billing.js MUST wipe stale localStorage user+token on
        401 so the next render doesn't see phantom auth state."""
        src = self._read(BILLING_JS)
        # Both `token` and `user` must be removed in the 401 catch block.
        assert "localStorage.removeItem('token')" in src or \
               'localStorage.removeItem("token")' in src, (
            "Billing.js must clear stale token on 401"
        )
        assert "localStorage.removeItem('user')" in src or \
               'localStorage.removeItem("user")' in src, (
            "Billing.js must clear stale cached user on 401"
        )

    def test_billing_surfaces_degraded_balance_banner(self):
        """T5. When balance fails in isolation, Billing.js must NOT
        nuke the page — it must surface a discoverable inline banner
        the user can act on. The data-testid is part of the contract."""
        src = self._read(BILLING_JS)
        assert 'data-testid="billing-balance-degraded"' in src, (
            "Billing.js must render a `billing-balance-degraded` banner "
            "when balance fetch fails in isolation."
        )
        assert 'data-testid="billing-balance-degraded-relogin"' in src, (
            "Degraded banner must offer a clear sign-in CTA "
            "(billing-balance-degraded-relogin)."
        )

    def test_billing_does_not_set_page_error_on_balance_only_failure(self):
        """T5. Static check: setPageError(true) must NOT be inside the
        balance-failure branch — only the products-failure branch.
        Otherwise a 401 on balance would re-trigger the broken behavior."""
        src = self._read(BILLING_JS)
        # The balance-fail branch is identified by `setBalanceUnavailable(true)`.
        # Within ~30 lines around that call, there must be no
        # `setPageError(true)`.
        idx = src.find("setBalanceUnavailable(true)")
        assert idx != -1, "balance-degraded flag must exist"
        window = src[max(0, idx - 400) : idx + 400]
        assert "setPageError(true)" not in window, (
            "Balance failure must NOT set pageError — that's the "
            "original kill-the-page bug class."
        )


# ─────────────────────────────────────────────────────────────────────
# Global interceptor and login redirect contract
# ─────────────────────────────────────────────────────────────────────
class TestRedirectContract:
    """The auth/me probe must be self-handled. Login.js must accept
    both `?next=` (canonical) and `?return=` (legacy)."""

    def _read(self, path):
        assert path.exists(), f"required file missing: {path}"
        return path.read_text(encoding="utf-8")

    def test_api_interceptor_skips_auth_me_redirect(self):
        """The global axios response interceptor MUST NOT auto-redirect
        on /api/auth/me 401 — pages own that flow. Otherwise the
        interceptor's `?return=` and Billing's `?next=` race."""
        src = self._read(API_JS)
        # The interceptor exempt list must mention auth/me.
        assert "/auth/me" in src, (
            "api.js interceptor must exempt /api/auth/me from the "
            "auto-redirect path (it is a self-handled session probe)."
        )
        # Loose structural check: the isAuthEndpoint / isSessionProbe
        # combinator must guard the location.href write.
        assert re.search(
            r"isSessionProbe\s*=.*auth/me",
            src,
        ) or "isSessionProbe" in src, (
            "api.js must define an isSessionProbe flag covering "
            "/api/auth/me."
        )

    def test_api_interceptor_uses_canonical_next_param(self):
        """T4. The global interceptor MUST redirect with `?next=` —
        the canonical, founder-mandated param. Inconsistency here
        (e.g. some redirects with `?return=` and others with `?next=`)
        creates a confusing UX and breaks the contract Billing.js
        documents in its 401 handler.

        Login.js still accepts `?return=` for backwards compat, but
        new writes from the global interceptor MUST use `?next=`.
        """
        src = self._read(API_JS)
        assert re.search(
            r"`/login\?next=\$\{encodeURIComponent",
            src,
        ), (
            "api.js interceptor must redirect with /login?next=... "
            "(canonical param). Found `?return=` instead — that's the "
            "param-mismatch race bug."
        )
        # And the legacy ?return= write must be gone from the live path.
        # We allow the comment string to mention `?return=` for context.
        bad_writes = re.findall(
            r"`/login\?return=\$\{encodeURIComponent",
            src,
        )
        assert not bad_writes, (
            "api.js still writes /login?return=... — replace with "
            "/login?next=... to satisfy the canonical contract."
        )

    def test_login_accepts_next_param(self):
        """T4. Login.js MUST read `?next=` (canonical, founder-mandated)."""
        src = self._read(LOGIN_JS)
        # Must call searchParams.get('next') somewhere.
        assert re.search(
            r"searchParams\.get\(\s*['\"]next['\"]\s*\)",
            src,
        ), (
            "Login.js must accept `?next=` — that is the canonical "
            "return-path contract from the Billing page redirect."
        )

    def test_login_still_accepts_return_param_for_backcompat(self):
        """Login.js MUST also accept `?return=` so existing global
        interceptor redirects continue to work."""
        src = self._read(LOGIN_JS)
        assert re.search(
            r"searchParams\.get\(\s*['\"]return['\"]\s*\)",
            src,
        ), (
            "Login.js must still accept `?return=` for backwards "
            "compat with the global interceptor's legacy param."
        )

    def test_login_uses_next_first_then_return(self):
        """Resolution priority: `?next=` (new contract) wins over
        `?return=` (legacy). Otherwise a stale interceptor URL could
        override the Billing-page intent."""
        src = self._read(LOGIN_JS)
        # We expect a chained `get('next') || get('return')` expression.
        assert re.search(
            r"searchParams\.get\(\s*['\"]next['\"]\s*\)\s*\|\|\s*"
            r"searchParams\.get\(\s*['\"]return['\"]\s*\)",
            src,
        ), (
            "Login.js must prefer `?next=` over `?return=` "
            "(searchParams.get('next') || searchParams.get('return'))."
        )

    def test_app_route_guard_preserves_next_for_billing(self):
        """T4. App.js route-level guard MUST preserve `/app/billing` in
        the redirect when the user is unauthenticated. Otherwise the
        prospect arrives at bare `/login` and is dumped to `/app` after
        sign-in (broken funnel).

        The contract is satisfied EITHER by:
          (a) an inline `Navigate to={`/login?next=${encodeURIComponent(
              '/app/billing')}`}` (per-route fix), OR
          (b) a centralized `<LoginRedirect />` component used by ALL
              protected routes (the canonical refactor — pinned by
              test_protected_route_next_redirect_2026_06.py).
        """
        app_js = REPO / "frontend" / "src" / "App.js"
        assert app_js.exists(), "App.js missing"
        src = app_js.read_text(encoding="utf-8")
        # Find the /app/billing route line.
        billing_line = None
        for line in src.splitlines():
            if 'path="/app/billing"' in line and '<Route ' in line:
                billing_line = line
                break
        assert billing_line, "Route for /app/billing missing"
        # Form (a): inline encodeURIComponent('/app/billing') in next=
        form_a = re.search(
            r'next=\$\{[^}]*encodeURIComponent\([^)]*[\'"]/app/billing[\'"]',
            billing_line,
        )
        # Form (b): centralized <LoginRedirect /> component.
        form_b = '<LoginRedirect />' in billing_line
        assert form_a or form_b, (
            "App.js /app/billing route must redirect with a next param "
            "that encodes /app/billing — either inline or via "
            "<LoginRedirect />. Current line:\n  " + billing_line.strip()
        )
