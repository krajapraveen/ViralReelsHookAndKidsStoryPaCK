"""
P0 SECURITY HARDENING — Open-redirect guard via safeRedirectPath (2026-06)
==========================================================================

Bug class
---------
Post-login redirect via `?next=` / `?return=` was unsanitized. A crafted
URL like `/login?next=https://evil.com` could navigate the freshly-
authenticated user to an attacker-controlled origin — a classic
phishing/credential-relay vector.

Contract (founder spec)
-----------------------
Allowed redirect targets MUST:
  • be a non-empty string
  • after URL-decoding, start with `/`
  • NOT start with `//` (scheme-relative)
  • NOT contain protocols like `http://`, `https://`, `javascript:`,
    `data:`, `vbscript:`, `file:` anywhere
  • NOT loop to `/login` or `/signup`

Invalid values MUST return the safe fallback `/app/dashboard`.

Param resolution priority (canonical):
  1. `?next=` (canonical, founder-mandated)
  2. `?return=` (legacy back-compat)

Test plan (all from the security spec)
--------------------------------------
  S1.  `/login?next=/app/billing`            → allowed (returns same)
  S2.  `/login?return=/app/my-space`         → allowed (legacy still works)
  S3.  `/login?next=https://evil.com`        → fallback `/app/dashboard`
  S4.  `/login?next=//evil.com`              → fallback `/app/dashboard`
  S5.  `/login?next=javascript:alert(1)`     → fallback `/app/dashboard`
  S6.  `/login?next=data:text/html,...`      → fallback `/app/dashboard`
  S7.  encoded external URL (%2F%2Fevil.com, double-encoded)
                                             → fallback `/app/dashboard`
  S8.  `/login?next=/login` (self-loop)      → fallback `/app/dashboard`

We exercise the sanitizer two ways:
  (A) static-source assertions — pin the contract in the JS code,
      so it cannot regress silently.
  (B) live-execution via Node — actually invoke `safeRedirectPath` and
      verify the returned string for every attack vector. This is
      where the real teeth are: any tweak to the sanitizer that breaks
      a defense will fail here.
"""
import json
import pathlib
import subprocess
import shutil
import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
SAFE_REDIRECT_JS = REPO / "frontend" / "src" / "utils" / "safeRedirect.js"
LOGIN_JS = REPO / "frontend" / "src" / "pages" / "Login.js"
APP_JS = REPO / "frontend" / "src" / "App.js"


def _read(path):
    assert path.exists(), f"required file missing: {path}"
    return path.read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────
# (A) Static-source assertions — pin the contract.
# ─────────────────────────────────────────────────────────────────────
class TestSanitizerSourceContract:
    """The sanitizer file MUST exist, export the canonical helper, and
    contain the defenses required by the security spec."""

    def test_safe_redirect_file_exists(self):
        assert SAFE_REDIRECT_JS.exists(), (
            "safeRedirect.js must exist at frontend/src/utils/."
        )

    def test_exports_safe_redirect_path(self):
        src = _read(SAFE_REDIRECT_JS)
        assert "export function safeRedirectPath" in src, (
            "safeRedirect.js must export `safeRedirectPath`."
        )

    def test_safe_fallback_is_app_dashboard(self):
        src = _read(SAFE_REDIRECT_JS)
        assert "'/app/dashboard'" in src or '"/app/dashboard"' in src, (
            "Safe fallback must be `/app/dashboard` (founder spec)."
        )

    def test_login_imports_sanitizer(self):
        src = _read(LOGIN_JS)
        assert "from '../utils/safeRedirect'" in src or \
               'from "../utils/safeRedirect"' in src, (
            "Login.js must import the sanitizer."
        )
        # Both auth paths (email + Google) must call it.
        assert src.count("safeRedirectPath(") >= 2, (
            "Login.js must call safeRedirectPath in BOTH the email and "
            "Google login paths. Found "
            f"{src.count('safeRedirectPath(')}."
        )

    def test_app_authenticated_redirect_uses_sanitizer(self):
        src = _read(APP_JS)
        assert "safeRedirectPath" in src, (
            "App.js AuthenticatedRedirect must use the sanitizer "
            "(an authenticated user revisiting /login?next=evil.com "
            "must also be protected)."
        )

    def test_no_raw_navigate_with_search_param(self):
        """No code path in Login.js should pass `searchParams.get('next')`
        DIRECTLY to navigate()/location.href without sanitizing.

        We check for the anti-pattern of `navigate(returnParam,` or
        `navigate(searchParams.get(`.
        """
        src = _read(LOGIN_JS)
        # The legacy unsanitized patterns we explicitly want gone.
        forbidden = [
            "navigate(returnParam,",
            "navigate(searchParams.get(",
            "window.location.href = returnParam",
            "window.location.href = searchParams.get(",
        ]
        for f in forbidden:
            assert f not in src, (
                f"Login.js still contains unsafe pattern `{f}`. "
                f"All post-login navigation must go through safeRedirectPath."
            )


# ─────────────────────────────────────────────────────────────────────
# (B) Live-execution via Node — actually run safeRedirectPath.
# ─────────────────────────────────────────────────────────────────────
NODE_HARNESS_TEMPLATE = """
// Tiny harness: read the sanitizer source, strip the ESM `export` syntax
// so we can `eval` it under plain Node (no build step needed in CI),
// then invoke it for each test case and print a JSON result line.
import fs from 'node:fs';

const src = fs.readFileSync(%(path)r, 'utf8');
// Strip ESM exports — keep the function body so we can call it locally.
const code = src
  .replace(/export function /g, 'function ')
  .replace(/export const [^;]+;?/g, '');
const ctx = {};
const wrapped = '(function(){' + code +
  ';this.safeRedirectPath = safeRedirectPath;}).call(ctx);';
// eslint-disable-next-line no-eval
eval(wrapped);
const fn = ctx.safeRedirectPath;
const cases = %(cases)s;
const out = cases.map((c) => ({
  label: c.label,
  input: c.input,
  expectedKind: c.expectedKind,  // 'pass' (same) or 'fallback'
  result: fn(c.input),
}));
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def sanitizer_results():
    """Run every attack-vector through the actual sanitizer via Node."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not available on this host — static checks still cover the contract.")

    cases = [
        # ── ALLOWED (must pass through) ──────────────────────────────
        {"label": "S1_billing",      "input": "/app/billing",        "expectedKind": "pass"},
        {"label": "S2_my_space",     "input": "/app/my-space",       "expectedKind": "pass"},
        {"label": "ok_with_query",   "input": "/app/billing?tab=plans", "expectedKind": "pass"},
        {"label": "ok_deep_route",   "input": "/app/story-series/abc-123", "expectedKind": "pass"},
        # ── BLOCKED (must fallback) ──────────────────────────────────
        {"label": "S3_https_external",       "input": "https://evil.com",          "expectedKind": "fallback"},
        {"label": "S3b_http_external",       "input": "http://evil.com",           "expectedKind": "fallback"},
        {"label": "S4_scheme_relative",      "input": "//evil.com",                "expectedKind": "fallback"},
        {"label": "S4b_scheme_relative_path","input": "//evil.com/billing",        "expectedKind": "fallback"},
        {"label": "S5_javascript",           "input": "javascript:alert(1)",       "expectedKind": "fallback"},
        {"label": "S5b_js_slash_prefix",     "input": "/javascript:alert(1)",      "expectedKind": "fallback"},
        {"label": "S6_data_url",             "input": "data:text/html,<script>",   "expectedKind": "fallback"},
        {"label": "S6b_data_slash_prefix",   "input": "/data:text/html,x",         "expectedKind": "fallback"},
        {"label": "vbscript",                "input": "vbscript:msgbox",           "expectedKind": "fallback"},
        {"label": "file_scheme",             "input": "file:///etc/passwd",        "expectedKind": "fallback"},
        # ── ENCODED EXTERNAL (must fail after decoding) ─────────────
        {"label": "S7_encoded_scheme_rel",   "input": "%2F%2Fevil.com",            "expectedKind": "fallback"},
        {"label": "S7b_double_encoded",      "input": "%252F%252Fevil.com",        "expectedKind": "fallback"},
        {"label": "S7c_encoded_https",       "input": "https%3A%2F%2Fevil.com",    "expectedKind": "fallback"},
        {"label": "S7d_encoded_javascript",  "input": "javascript%3Aalert(1)",     "expectedKind": "fallback"},
        # ── LOOPS ───────────────────────────────────────────────────
        {"label": "S8_login_loop",           "input": "/login",                    "expectedKind": "fallback"},
        {"label": "S8b_login_with_query",    "input": "/login?next=/app",          "expectedKind": "fallback"},
        {"label": "signup_loop",             "input": "/signup",                   "expectedKind": "fallback"},
        # ── EDGE CASES ──────────────────────────────────────────────
        {"label": "empty_string",            "input": "",                          "expectedKind": "fallback"},
        {"label": "whitespace_only",         "input": "   ",                       "expectedKind": "fallback"},
        {"label": "leading_whitespace_scheme","input": "\\t//evil.com",            "expectedKind": "fallback"},
        {"label": "backslash_scheme_rel",    "input": "/\\\\evil.com",             "expectedKind": "fallback"},
        {"label": "no_leading_slash",        "input": "app/billing",               "expectedKind": "fallback"},
        {"label": "embedded_protocol",       "input": "/foo://evil.com",           "expectedKind": "fallback"},
    ]
    harness = NODE_HARNESS_TEMPLATE % {
        "path": str(SAFE_REDIRECT_JS),
        "cases": json.dumps(cases),
    }
    proc = subprocess.run(
        [node, "--input-type=module", "-e", harness],
        capture_output=True, text=True, timeout=15,
    )
    assert proc.returncode == 0, (
        f"node harness failed: stderr={proc.stderr!r} stdout={proc.stdout!r}"
    )
    return json.loads(proc.stdout.strip().splitlines()[-1])


class TestLiveSanitizerExecution:
    """These tests actually invoke the sanitizer for every documented
    attack vector. They are the load-bearing security tests."""

    def test_allowed_paths_pass_through(self, sanitizer_results):
        for r in sanitizer_results:
            if r["expectedKind"] != "pass":
                continue
            assert r["result"] == r["input"], (
                f"[{r['label']}] expected {r['input']!r} to pass through, "
                f"got {r['result']!r}"
            )

    def test_external_https_blocked(self, sanitizer_results):
        r = next(x for x in sanitizer_results if x["label"] == "S3_https_external")
        assert r["result"] == "/app/dashboard", (
            f"https://evil.com must fallback to /app/dashboard, got {r['result']!r}"
        )

    def test_external_http_blocked(self, sanitizer_results):
        r = next(x for x in sanitizer_results if x["label"] == "S3b_http_external")
        assert r["result"] == "/app/dashboard"

    def test_scheme_relative_blocked(self, sanitizer_results):
        for label in ("S4_scheme_relative", "S4b_scheme_relative_path"):
            r = next(x for x in sanitizer_results if x["label"] == label)
            assert r["result"] == "/app/dashboard", (
                f"[{label}] //evil.com must fallback, got {r['result']!r}"
            )

    def test_javascript_scheme_blocked(self, sanitizer_results):
        for label in ("S5_javascript", "S5b_js_slash_prefix"):
            r = next(x for x in sanitizer_results if x["label"] == label)
            assert r["result"] == "/app/dashboard", (
                f"[{label}] javascript: must fallback, got {r['result']!r}"
            )

    def test_data_url_blocked(self, sanitizer_results):
        for label in ("S6_data_url", "S6b_data_slash_prefix"):
            r = next(x for x in sanitizer_results if x["label"] == label)
            assert r["result"] == "/app/dashboard", (
                f"[{label}] data: URL must fallback, got {r['result']!r}"
            )

    def test_other_dangerous_schemes_blocked(self, sanitizer_results):
        for label in ("vbscript", "file_scheme"):
            r = next(x for x in sanitizer_results if x["label"] == label)
            assert r["result"] == "/app/dashboard"

    def test_encoded_attacks_blocked(self, sanitizer_results):
        """Critical: encoded external URLs MUST fail after decoding."""
        for label in (
            "S7_encoded_scheme_rel",
            "S7b_double_encoded",
            "S7c_encoded_https",
            "S7d_encoded_javascript",
        ):
            r = next(x for x in sanitizer_results if x["label"] == label)
            assert r["result"] == "/app/dashboard", (
                f"[{label}] encoded attack must fallback after decoding, "
                f"got {r['result']!r}"
            )

    def test_login_signup_loops_blocked(self, sanitizer_results):
        for label in ("S8_login_loop", "S8b_login_with_query", "signup_loop"):
            r = next(x for x in sanitizer_results if x["label"] == label)
            assert r["result"] == "/app/dashboard", (
                f"[{label}] self-loop must fallback, got {r['result']!r}"
            )

    def test_edge_cases_blocked(self, sanitizer_results):
        for label in (
            "empty_string",
            "whitespace_only",
            "leading_whitespace_scheme",
            "backslash_scheme_rel",
            "no_leading_slash",
            "embedded_protocol",
        ):
            r = next(x for x in sanitizer_results if x["label"] == label)
            assert r["result"] == "/app/dashboard", (
                f"[{label}] must fallback, got {r['result']!r}"
            )

    def test_fallback_string_is_canonical(self, sanitizer_results):
        """Every blocked result must be the EXACT canonical fallback,
        never an alternative or empty string."""
        for r in sanitizer_results:
            if r["expectedKind"] == "fallback":
                assert r["result"] == "/app/dashboard", (
                    f"[{r['label']}] fallback must be `/app/dashboard`, "
                    f"got {r['result']!r}"
                )
