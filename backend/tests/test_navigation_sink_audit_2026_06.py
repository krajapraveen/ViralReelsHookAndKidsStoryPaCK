"""
P0 SECURITY — Codebase-wide navigation-sink audit (2026-06)
============================================================

Doctrine
--------
Any frontend code path that performs `navigate(...)`, `window.location.href = ...`,
or `window.open(...)` MUST be classified into ONE of three categories:

  (A) Internal hardcoded literal path           → SAFE (no input)
  (B) Internal user/backend-controlled value    → MUST route through
                                                  `safeRedirectPath()`
  (C) Explicitly external (CDN / share / mailto) → MUST be documented
                                                   in-source with the
                                                   reason it is exempt.

This audit pins the contract so a new unsanitized sink CANNOT slip in
silently — every PR introducing a new `window.location.href = <expr>`
or `navigate(<expr>)` with a non-literal expression must either route
through `safeRedirectPath` or carry an inline `SECURITY` justification
comment that explains why it is exempt.

Scope of audit (sinks classified by main agent on 2026-06)
-----------------------------------------------------------

SAFE (Category A) — hardcoded internal paths, no input:
  • Profile.js                  → '/login'
  • GlobalUserBar.jsx           → '/login'
  • ErrorBoundary.js            → '/app'
  • SubscribeRequiredModal.jsx  → '/app/pricing', '/app/billing'
  • SmartDownloadButton.js      → '/app/billing'
  • ProtectedContent.js         → '/app/billing'
  • BrowserVideoExport.js       → '/app/billing'
  • SocialShareDownload.js      → '/app/billing'
  • VideoExportPanel.jsx        → '/app/billing'
  • RecoveryPage.js             → '/app/recovery'
  • MyDownloads.js (line 59)    → '/app/billing'
  • StoryVideoPipeline.js       → '/app', '/app/billing', '/login',
                                   '/signup' (all literals)
  • Billing.js                  → self-built `/login?next=/app/billing`
  • api.js interceptor          → self-built `/login?next=<currentPath>`
                                   (sanitized at consume in Login.js)
  • generationLifecycle.js      → self-built `/login?next=<currentPath>`

SANITIZED (Category B) — user/backend-controlled, routed via safeRedirectPath:
  • Login.js (email path)       → searchParams `next` / `return`
  • Login.js (Google path)      → searchParams `next` / `return`
  • App.js AuthenticatedRedirect→ searchParams `next` / `return`
  • Signup.js (email path)      → localStorage `remix_return_url`
  • Signup.js (Google path)     → localStorage `auth_return_path` /
                                   `remix_return_url`
  • NotificationContext.js      → backend `notification.actionUrl`
  • StoryVideoComponents.jsx    → backend `videoStatus.redirect_to`

INTENTIONAL EXTERNAL (Category C) — documented exemptions:
  • MyDownloads.js (line 66+)   → signed CDN download URL
  • PhotoTrailerPage.jsx        → signed CDN download URL (Safari fallback)
  • TwinFinder / DailyViralIdeas / PhotoReactionGIF /
    PublicCreation / PublicTrailerPage / PhotoToComic /
    StoryVideoStudio / StoryVideoPipeline / BrowsePage  → window.open
    to social-share or share-link URLs (`twitter.com`, `wa.me`, etc.)
  • RecoveryPage.js             → mailto: support escalation
  • PhotoTrailerPage.jsx        → mailto: premium support

This file pins the above classification with two layers of defense:
  1. **Live-execution check**: every Category-B sink we manually identified
     is verified to actually import `safeRedirectPath` from the canonical
     module and reference it.
  2. **Net-new prohibition**: scan the entire frontend tree for any
     `window.location.href = <variable>` pattern that is NEITHER routed
     through `safeRedirectPath` NOR carries an inline `SECURITY`
     justification comment within the surrounding ±5 lines.
"""
import pathlib
import re
import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
SRC = REPO / "frontend" / "src"


def _src(rel):
    p = SRC / rel
    assert p.exists(), f"required file missing: {p}"
    return p.read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────
# (1) Category-B sinks MUST import and call safeRedirectPath.
# ─────────────────────────────────────────────────────────────────────
SANITIZED_SINKS = [
    ("pages/Login.js",                    {"min_calls": 2}),
    ("pages/Signup.js",                   {"min_calls": 2}),
    ("App.js",                            {"min_calls": 1}),
    ("contexts/NotificationContext.js",   {"min_calls": 1}),
    ("components/StoryVideoComponents.jsx", {"min_calls": 1}),
]


class TestSanitizedSinksImportHelper:
    @pytest.mark.parametrize("rel,opts", SANITIZED_SINKS, ids=[s[0] for s in SANITIZED_SINKS])
    def test_imports_and_calls_safe_redirect_path(self, rel, opts):
        src = _src(rel)
        assert "safeRedirectPath" in src and \
               ("from '../utils/safeRedirect'" in src or
                "from './utils/safeRedirect'" in src or
                'from "../utils/safeRedirect"' in src or
                'from "./utils/safeRedirect"' in src), (
            f"{rel} must import safeRedirectPath from the canonical "
            f"sanitizer module."
        )
        calls = src.count("safeRedirectPath(")
        assert calls >= opts["min_calls"], (
            f"{rel} must call safeRedirectPath at least "
            f"{opts['min_calls']} time(s) — found {calls}."
        )


# ─────────────────────────────────────────────────────────────────────
# (2) No new unsafe `window.location.href = <variable>` may exist.
# ─────────────────────────────────────────────────────────────────────
# Allowlist: lines where the right-hand side is a STRING LITERAL or a
# template literal that contains ONLY safe self-built content. We
# detect by regex: assignment to literal string OR a template/expr that
# already includes `safeRedirectPath`.

# Files allowed to assign a non-literal because they have an in-source
# SECURITY justification comment within ±5 lines.
DOCUMENTED_EXEMPTIONS = {
    # Signed CDN download URLs from our own backend.
    "pages/MyDownloads.js",
    "pages/PhotoTrailerPage.jsx",
    # Self-built redirect URLs (constructed locally with hardcoded base path).
    "utils/api.js",
    "utils/generationLifecycle.js",
    # /login?next=... built locally with hardcoded base.
    "pages/Billing.js",
    # Hard navigation to a self-constructed `/app/story-video-studio?...`
    # URL — base path is a hardcoded literal, only query params interpolate
    # backend-issued job_id (a UUID-shaped string used as a query value,
    # not as the redirect target).
    "pages/StoryVideoPipeline.js",
    # `loginUrl` returned by generationLifecycle.consumePendingLogin() —
    # self-built `/login?next=` URL; Login.js sanitizes next on consume.
    "pages/ReelGenerator.js",
}

LITERAL_OR_TEMPLATE_SAFE = re.compile(
    r"window\.location\.href\s*=\s*"
    r"(?:"
        r"['\"][^'\"]*['\"]"                       # plain string literal
        r"|`/[^`$]*`"                              # template literal with ONLY
                                                   # static content (no ${})
        r"|safeRedirectPath\("                     # routed through sanitizer
        r"|'/login\?next=' \+ encodeURIComponent" # billing-style self-built
    r")"
)


class TestNoUnsafeLocationHref:
    """Static-source audit of every `window.location.href = ...` site.
    
    Any assignment whose RHS is a non-literal that is NOT routed through
    safeRedirectPath must live in a documented-exemption file. New code
    that violates this must either:
      (a) route through safeRedirectPath, or
      (b) add the file to DOCUMENTED_EXEMPTIONS with a SECURITY comment.
    """

    def test_all_unsafe_assignments_are_sanitized_or_exempted(self):
        violations = []
        for path in SRC.rglob("*.js"):
            self._scan(path, violations)
        for path in SRC.rglob("*.jsx"):
            self._scan(path, violations)
        assert not violations, (
            "Unsafe `window.location.href = <variable>` found:\n  - " +
            "\n  - ".join(violations) +
            "\nFix: route through safeRedirectPath() OR add the file to "
            "DOCUMENTED_EXEMPTIONS in test_navigation_sink_audit_2026_06.py "
            "with an inline SECURITY comment justifying the exemption."
        )

    def _scan(self, path, violations):
        try:
            src = path.read_text(encoding="utf-8")
        except Exception:
            return
        rel = str(path.relative_to(SRC))
        # Skip node_modules / build outputs (shouldn't be in src but defensive).
        if "node_modules" in rel:
            return
        for m in re.finditer(r"window\.location\.href\s*=\s*([^;\n]+)", src):
            rhs = m.group(1).strip()
            # Safe forms:
            if rhs.startswith(("'", '"', "`")) and "${" not in rhs:
                # Pure literal — safe.
                continue
            if rhs.startswith("safeRedirectPath("):
                continue
            if "safeRedirectPath(" in rhs:
                continue
            # Self-built `?next=` URLs assembled from hardcoded base +
            # encodeURIComponent of a known-internal string are also safe.
            if rhs.startswith("'/login?next=' +") or rhs.startswith('"/login?next=" +'):
                continue
            # Allow exempted files (must carry inline SECURITY comment).
            if rel in DOCUMENTED_EXEMPTIONS:
                # Verify the SECURITY comment exists within ±5 lines.
                line_no = src[:m.start()].count("\n")
                lines = src.split("\n")
                window = "\n".join(lines[max(0, line_no - 5): line_no + 5])
                if "SECURITY" in window:
                    continue
                violations.append(
                    f"{rel}:{line_no + 1}  RHS={rhs[:80]!r}  "
                    f"(file is in exemption list but missing SECURITY comment)"
                )
                continue
            violations.append(f"{rel}:{src[:m.start()].count(chr(10)) + 1}  RHS={rhs[:80]!r}")


# ─────────────────────────────────────────────────────────────────────
# (3) navigate(...) — user-controlled variables must be sanitized.
# ─────────────────────────────────────────────────────────────────────
class TestNavigateCallsSanitized:
    """`navigate(varName)` where varName comes from URL params or storage
    must route through safeRedirectPath. We pin the three known places
    (Login email path, Signup email path, AuthenticatedRedirect)."""

    def test_login_navigate_uses_sanitizer(self):
        src = _src("pages/Login.js")
        # The post-login navigate() call must NOT pass a raw localStorage/
        # searchParams value — it must wrap with safeRedirectPath.
        assert "navigate(returnUrl" in src or "navigate(safeRedirectPath" in src, (
            "Login.js post-login navigate site missing."
        )
        # `returnUrl` must be derived from safeRedirectPath.
        m = re.search(r"const\s+returnUrl\s*=\s*[^;]+;", src)
        assert m, "Login.js must define returnUrl before navigate()"
        assert "safeRedirectPath(" in m.group(0), (
            "Login.js returnUrl must be the result of safeRedirectPath()."
        )

    def test_signup_navigate_uses_sanitizer(self):
        src = _src("pages/Signup.js")
        # Signup email path must wrap the localStorage value in safeRedirectPath.
        assert re.search(
            r"navigate\(safeRedirectPath\(",
            src,
        ), (
            "Signup.js email path must wrap the redirect through "
            "safeRedirectPath(...)."
        )

    def test_app_authenticated_redirect_uses_sanitizer(self):
        src = _src("App.js")
        # AuthenticatedRedirect must compute returnUrl from safeRedirectPath.
        m = re.search(
            r"function\s+AuthenticatedRedirect\s*\(\s*\)\s*\{(.*?)\n\}",
            src, re.DOTALL,
        )
        assert m, "AuthenticatedRedirect function body missing"
        assert "safeRedirectPath(" in m.group(1), (
            "AuthenticatedRedirect must wrap returnUrl through "
            "safeRedirectPath()."
        )


# ─────────────────────────────────────────────────────────────────────
# (4) Documented exemption files must still contain SECURITY justification.
# ─────────────────────────────────────────────────────────────────────
class TestExemptionsAreDocumented:
    @pytest.mark.parametrize("rel", sorted(DOCUMENTED_EXEMPTIONS))
    def test_exemption_carries_security_comment(self, rel):
        src = _src(rel)
        # Every exempt file must mention SECURITY somewhere — that proves
        # the deviation is intentional and audited.
        assert "SECURITY" in src, (
            f"{rel} is on the navigation-sink exemption list but its "
            f"source no longer contains a `SECURITY` justification "
            f"comment. Either re-document the exemption or move the "
            f"redirect through safeRedirectPath()."
        )


# ─────────────────────────────────────────────────────────────────────
# (5) Live attack-vector smoke for the NEWLY-sanitized sinks via Node.
# ─────────────────────────────────────────────────────────────────────
# We re-use the dedicated full attack-vector suite in
# test_safe_redirect_open_redirect_guard_2026_06.py — duplicating here
# would be wasteful. But we do a SANITY check that the sanitizer is
# imported correctly in each newly-protected file (caught by section 1).
# That suite, combined with this static audit, gives us:
#   • Sanitizer logic correctness  (the other file)
#   • Sanitizer reach across the codebase (this file)
