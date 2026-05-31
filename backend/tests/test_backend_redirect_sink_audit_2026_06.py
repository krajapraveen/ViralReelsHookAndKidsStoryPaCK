"""
P0 SECURITY — Backend redirect-sink audit (2026-06)
====================================================

Server-side equivalent of the frontend navigation-sink audit. Pins the
classification of every `RedirectResponse(...)` and every URL that the
backend hands to Cashfree as `return_url` / `notify_url`. Prevents a
future regression from introducing a backend open-redirect that
bypasses the now-locked-down frontend `safeRedirectPath` boundary.

Doctrine (mirrors the frontend audit)
-------------------------------------
Every backend redirect sink falls into one of three categories:

  (A) Hardcoded/server-built internal URL  — SAFE
  (B) User/untrusted input                  — MUST be sanitized
  (C) Intentionally external                — MUST carry an inline
                                              `SECURITY` justification

Inventory (audited 2026-06)
---------------------------
RedirectResponse sinks (only 2):
  • routes/r2_proxy.py:81  → `cached_url` (boto3-presigned R2 URL).
                              Host fixed by R2 endpoint env. Path
                              traversal blocked by `".." in path` guard.
                              Category C — documented.
  • routes/r2_proxy.py:97  → `presigned_url` (boto3-generated). Same.
                              Category C — documented.

Cashfree return_url / notify_url builders (3):
  • routes/cashfree_payments.py:270            (order)
  • routes/subscriptions.py:863                (subscription create)
  • routes/subscriptions.py:1067               (subscription upgrade)
  • services/cashfree_subscription_service.py:391 (cancel-and-recreate)
All are SERVER-BUILT from a hardcoded base path + `FRONTEND_URL` env
var + a server-generated `order_id`. Category A. No user input reaches
these strings.

Defense-in-depth:
  • `services/cashfree_subscription_service.create_subscription` now
    validates its `return_url` parameter through
    `utils.safe_redirect.assert_same_origin_https()` so a future caller
    that wires user input through it fails closed.

OAuth:
  • routes/auth.py:850 → `"redirect_uri": "postmessage"` is a hardcoded
    string literal sentinel for Google's postMessage flow. Category A.

User-controlled redirect inputs:
  • NONE. There is no backend route today that reads `?next=` /
    `?return=` / `redirect_uri` from a request and echoes it back as a
    redirect target.

Audit invariants pinned below
-----------------------------
1. The sanitizer module exists and exports the canonical helpers.
2. The sanitizer logic is correct against every documented attack
   vector (full unit test, 22 cases).
3. Every known RedirectResponse sink in the codebase is on the
   documented-exemption list AND carries an inline `SECURITY` comment.
4. No NEW `RedirectResponse(url=<variable>)` may be added without
   either routing through `safe_redirect_path` OR carrying an inline
   `SECURITY:` justification within ±5 lines.
5. `cashfree_subscription_service.create_subscription` defensively
   validates its `return_url` parameter.
6. Path traversal on `/api/media/r2/{path}` returns 400.
"""
import os
import re
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
BACKEND = REPO / "backend"
SAFE_REDIRECT_PY = BACKEND / "utils" / "safe_redirect.py"

sys.path.insert(0, str(BACKEND))


def _read(p):
    assert p.exists(), f"required file missing: {p}"
    return p.read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────
# (1) Sanitizer module exists and exports the canonical helpers.
# ─────────────────────────────────────────────────────────────────────
class TestSanitizerModuleContract:
    def test_module_exists(self):
        assert SAFE_REDIRECT_PY.exists(), (
            "backend/utils/safe_redirect.py must exist as the canonical "
            "server-side sanitizer module."
        )

    def test_exports_safe_redirect_path(self):
        from utils.safe_redirect import safe_redirect_path  # noqa: F401

    def test_exports_assert_same_origin_https(self):
        from utils.safe_redirect import assert_same_origin_https  # noqa: F401

    def test_safe_fallback_is_app_dashboard(self):
        from utils.safe_redirect import SAFE_FALLBACK
        assert SAFE_FALLBACK == "/app/dashboard", (
            "Server-side safe fallback must match the frontend "
            "canonical `/app/dashboard`."
        )


# ─────────────────────────────────────────────────────────────────────
# (2) Sanitizer logic — full attack-vector matrix.
# ─────────────────────────────────────────────────────────────────────
SAFE_FB = "/app/dashboard"


@pytest.fixture(scope="module")
def sanitizer():
    from utils.safe_redirect import safe_redirect_path
    return safe_redirect_path


class TestSafeRedirectPathLogic:
    """22 attack-vector cases — mirrors the frontend Node harness."""

    @pytest.mark.parametrize("value,expected", [
        # Allowed (pass-through)
        ("/app/billing",                 "/app/billing"),
        ("/app/my-space",                "/app/my-space"),
        ("/app/billing?tab=plans",       "/app/billing?tab=plans"),
        ("/app/story-series/abc-123",    "/app/story-series/abc-123"),
        # External
        ("https://evil.com",             SAFE_FB),
        ("http://evil.com",              SAFE_FB),
        # Scheme-relative
        ("//evil.com",                   SAFE_FB),
        ("//evil.com/billing",           SAFE_FB),
        # javascript: / data: / vbscript: / file:
        ("javascript:alert(1)",          SAFE_FB),
        ("/javascript:alert(1)",         SAFE_FB),
        ("data:text/html,<script>",      SAFE_FB),
        ("/data:text/html,x",            SAFE_FB),
        ("vbscript:msgbox",              SAFE_FB),
        ("file:///etc/passwd",           SAFE_FB),
        # Encoded
        ("%2F%2Fevil.com",               SAFE_FB),
        ("%252F%252Fevil.com",           SAFE_FB),
        ("https%3A%2F%2Fevil.com",       SAFE_FB),
        ("javascript%3Aalert(1)",        SAFE_FB),
        # Loops
        ("/login",                       SAFE_FB),
        ("/login?next=/app",             SAFE_FB),
        ("/signup",                      SAFE_FB),
        # Edge cases
        ("",                             SAFE_FB),
        ("   ",                          SAFE_FB),
        ("\t//evil.com",                 SAFE_FB),
        ("/\\evil.com",                  SAFE_FB),
        ("app/billing",                  SAFE_FB),
        ("/foo://evil.com",              SAFE_FB),
        (None,                           SAFE_FB),
        (123,                            SAFE_FB),
    ])
    def test_attack_vectors(self, sanitizer, value, expected):
        assert sanitizer(value) == expected, (
            f"safe_redirect_path({value!r}) → expected {expected!r}"
        )


# ─────────────────────────────────────────────────────────────────────
# (3) Same-origin HTTPS validator.
# ─────────────────────────────────────────────────────────────────────
class TestAssertSameOriginHttps:
    @pytest.fixture(autouse=True)
    def _env(self, monkeypatch):
        monkeypatch.setenv(
            "ALLOWED_REDIRECT_HOSTS",
            "www.visionary-suite.com,visionary-suite.com",
        )
        monkeypatch.setenv("FRONTEND_URL", "https://www.visionary-suite.com")

    def test_accepts_canonical_frontend_url(self):
        from utils.safe_redirect import assert_same_origin_https
        out = assert_same_origin_https(
            "https://www.visionary-suite.com/app/billing?order_id=x"
        )
        assert out.startswith("https://www.visionary-suite.com/")

    def test_rejects_external_host(self):
        from utils.safe_redirect import assert_same_origin_https
        with pytest.raises(ValueError):
            assert_same_origin_https("https://evil.com/app/billing")

    def test_rejects_http_scheme(self):
        from utils.safe_redirect import assert_same_origin_https
        with pytest.raises(ValueError):
            assert_same_origin_https("http://www.visionary-suite.com/app/billing")

    def test_rejects_javascript_scheme(self):
        from utils.safe_redirect import assert_same_origin_https
        with pytest.raises(ValueError):
            assert_same_origin_https("javascript:alert(1)")

    def test_rejects_empty(self):
        from utils.safe_redirect import assert_same_origin_https
        with pytest.raises(ValueError):
            assert_same_origin_https("")
        with pytest.raises(ValueError):
            assert_same_origin_https(None)  # type: ignore[arg-type]


# ─────────────────────────────────────────────────────────────────────
# (4) cashfree_subscription_service guard.
# ─────────────────────────────────────────────────────────────────────
class TestCashfreeSubscriptionServiceValidatesReturnUrl:
    """Defense-in-depth: even though no current caller passes user
    input, the service MUST validate `return_url` so a future call
    that wires user input through it fails closed."""

    def test_service_imports_validator(self):
        path = BACKEND / "services" / "cashfree_subscription_service.py"
        src = _read(path)
        assert "from utils.safe_redirect import assert_same_origin_https" in src, (
            "cashfree_subscription_service.py must import "
            "assert_same_origin_https from the canonical sanitizer."
        )

    def test_create_subscription_calls_validator(self):
        path = BACKEND / "services" / "cashfree_subscription_service.py"
        src = _read(path)
        # Look for the validator call inside `create_subscription`.
        m = re.search(
            r"async def create_subscription\b.*?return await self",
            src, re.DOTALL,
        )
        assert m, "create_subscription function body not found"
        body = m.group(0)
        assert "assert_same_origin_https(return_url)" in body, (
            "create_subscription must call "
            "`assert_same_origin_https(return_url)` before handing the "
            "URL to Cashfree."
        )


# ─────────────────────────────────────────────────────────────────────
# (5) RedirectResponse sink classification — no new unsafe ones.
# ─────────────────────────────────────────────────────────────────────

# Files allowed to contain `RedirectResponse(url=<variable>)` if they
# carry an inline `SECURITY` justification within ±5 lines.
REDIRECT_RESPONSE_EXEMPTIONS = {
    "routes/r2_proxy.py",
}


class TestRedirectResponseSinkAudit:
    """Static scan of the entire backend for `RedirectResponse(url=...)`.
    Anything whose URL is a non-literal expression must live in
    REDIRECT_RESPONSE_EXEMPTIONS AND carry a SECURITY comment."""

    def test_no_unsafe_redirect_response(self):
        violations = []
        for path in BACKEND.rglob("*.py"):
            rel = str(path.relative_to(BACKEND))
            if rel.startswith("tests/") or "__pycache__" in rel:
                continue
            # The sanitizer module itself documents the bug-class in
            # its docstring with example attack strings — exclude it.
            if rel == "utils/safe_redirect.py":
                continue
            try:
                src = path.read_text(encoding="utf-8")
            except Exception:
                continue
            for m in re.finditer(
                r"RedirectResponse\s*\(\s*url\s*=\s*([^,)\n]+)", src
            ):
                rhs = m.group(1).strip()
                # Literal? (string, b-string, f-string with no var)
                if (rhs.startswith(("'", '"'))
                        and not any(c in rhs for c in "{$")):
                    continue
                # Routed through sanitizer?
                if "safe_redirect_path(" in rhs:
                    continue
                if rel in REDIRECT_RESPONSE_EXEMPTIONS:
                    line_no = src[:m.start()].count("\n")
                    lines = src.split("\n")
                    window = "\n".join(
                        lines[max(0, line_no - 5): line_no + 5]
                    )
                    if "SECURITY" in window:
                        continue
                    violations.append(
                        f"{rel}:{line_no + 1}  RHS={rhs[:80]!r}  "
                        f"(exempted but missing SECURITY comment)"
                    )
                    continue
                violations.append(
                    f"{rel}:{src[:m.start()].count(chr(10)) + 1}  "
                    f"RHS={rhs[:80]!r}"
                )
        assert not violations, (
            "Unsafe `RedirectResponse(url=<variable>)` found:\n  - " +
            "\n  - ".join(violations) +
            "\nFix: route through safe_redirect_path() OR add the file "
            "to REDIRECT_RESPONSE_EXEMPTIONS with an inline SECURITY "
            "comment."
        )

    @pytest.mark.parametrize(
        "rel", sorted(REDIRECT_RESPONSE_EXEMPTIONS)
    )
    def test_exemption_carries_security_comment(self, rel):
        src = _read(BACKEND / rel)
        assert "SECURITY" in src, (
            f"{rel} is on the RedirectResponse exemption list but no "
            f"longer contains a `SECURITY` justification. Re-document "
            f"the exemption or move the redirect through "
            f"safe_redirect_path()."
        )


# ─────────────────────────────────────────────────────────────────────
# (6) Cashfree return_url builders — all SERVER-BUILT, no user input.
# ─────────────────────────────────────────────────────────────────────
CASHFREE_BUILDER_FILES = {
    "routes/cashfree_payments.py",
    "routes/subscriptions.py",
    "services/cashfree_subscription_service.py",
}


class TestCashfreeReturnUrlBuilders:
    """All Cashfree return_url/notify_url constructions must be
    server-built. The source must contain a SECURITY justification
    near each construction site so the classification cannot regress
    silently."""

    @pytest.mark.parametrize("rel", sorted(CASHFREE_BUILDER_FILES))
    def test_file_documents_return_url_classification(self, rel):
        src = _read(BACKEND / rel)
        # Each file should contain at least one `return_url=` site AND
        # a SECURITY comment near it (within ±10 lines).
        for m in re.finditer(r"return_url\s*=\s*f?[\"']", src):
            line_no = src[:m.start()].count("\n")
            lines = src.split("\n")
            window = "\n".join(lines[max(0, line_no - 10): line_no + 10])
            assert "SECURITY" in window, (
                f"{rel}:{line_no + 1} — return_url construction site "
                f"missing SECURITY justification within ±10 lines. "
                f"Document why this URL is server-built and safe."
            )


# ─────────────────────────────────────────────────────────────────────
# (7) Live attack — path traversal on the only public redirect endpoint.
# ─────────────────────────────────────────────────────────────────────
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "").rstrip("/")
if not BASE_URL:
    BASE_URL = "https://trust-engine-5.preview.emergentagent.com"


class TestR2ProxyPathTraversalGuard:
    """The `/api/media/r2/{path}` endpoint is the only public 302
    redirect in the backend. The critical security invariant is that
    the `Location` header is ALWAYS on our R2 host — never
    attacker-controlled. Path traversal in the cache key is a
    secondary concern handled by the `".." in path` guard.
    """

    R2_HOST_SUFFIX = ".r2.cloudflarestorage.com"

    def _location_safe(self, response):
        """If the response is a 3xx, its Location must be on R2."""
        if response.status_code in (301, 302, 303, 307, 308):
            loc = response.headers.get("Location", "")
            from urllib.parse import urlparse
            host = (urlparse(loc).hostname or "").lower()
            return host.endswith(self.R2_HOST_SUFFIX), loc
        # 4xx/5xx response is also acceptable (no redirect at all).
        return True, None

    def test_dot_dot_rejected_with_400(self):
        """The explicit `.. in path` guard in `r2_proxy` MUST raise
        HTTPException(400). We test at the function level because
        HTTP clients normalize `foo/../bar` to `bar` before the
        request reaches the backend.
        """
        import asyncio
        from unittest.mock import MagicMock
        from fastapi import HTTPException
        from routes.r2_proxy import r2_proxy

        # Path containing literal ".." must trip the guard.
        request = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(r2_proxy(path="../etc/passwd", request=request))
        assert exc_info.value.status_code == 400, (
            f"r2_proxy must reject `..` with 400, got "
            f"{exc_info.value.status_code}"
        )

    def test_empty_path_rejected_with_400(self):
        """Empty path must also trip the guard."""
        import asyncio
        from unittest.mock import MagicMock
        from fastapi import HTTPException
        from routes.r2_proxy import r2_proxy

        request = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(r2_proxy(path="", request=request))
        assert exc_info.value.status_code == 400

    def test_double_encoded_path_redirect_stays_on_r2_host(self):
        """Even when the guard doesn't fire (e.g., `%252E%252E` which
        decodes only once at FastAPI's path parser to `%2E%2E`, not to
        `..`), the redirect Location MUST be on our R2 host. The
        attacker cannot point the redirect anywhere off-domain."""
        r = requests.get(
            f"{BASE_URL}/api/media/r2/%252E%252E/etc/passwd",
            timeout=10, allow_redirects=False,
        )
        safe, loc = self._location_safe(r)
        assert safe, (
            f"R2 redirect target is NOT on our R2 host: Location={loc!r} "
            f"status={r.status_code}. This is the actual open-redirect "
            f"failure mode."
        )

    def test_empty_path_does_not_redirect_offsite(self):
        """Empty path via HTTP — must not produce off-site redirect.
        FastAPI may return 404 or 405; either is fine."""
        r = requests.get(
            f"{BASE_URL}/api/media/r2/",
            timeout=10, allow_redirects=False,
        )
        safe, loc = self._location_safe(r)
        assert safe, f"Empty path produced off-site redirect: {loc!r}"


# Note: the live HTTP `test_empty_path_does_not_redirect_offsite` above
# overlaps semantically with the unit-level `test_empty_path_rejected_with_400`
# but stays in the suite as a smoke test against the real preview
# environment.
