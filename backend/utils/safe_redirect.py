"""
P0 SECURITY — Backend redirect sanitizer (2026-06)
====================================================

Server-side equivalent of `frontend/src/utils/safeRedirect.js`. Used by
backend handlers that might ever echo a user-supplied or untrusted
string into a `RedirectResponse(url=...)`, a Cashfree `return_url`, or
any other 3xx Location header.

Current backend audit (2026-06) finds NO active sinks that take
user-controlled redirect input — every existing redirect target is a
server-built string with a hardcoded base path. This module exists
to:

  1. Defensively wrap the `create_subscription(..., return_url=...)`
     parameter so a future regression that passes user input cannot
     turn into an open redirect via Cashfree.
  2. Provide a canonical sanitizer for any future handler that needs
     to accept a `?next=` style param.
  3. Be the bug-class boundary pinned by
     `tests/test_backend_redirect_sink_audit_2026_06.py`.

Contract (mirrors the frontend doctrine)
----------------------------------------
A "safe" redirect target MUST:
  • be a non-empty string
  • after exhaustive URL-decoding, start with `/`
  • NOT start with `//` (scheme-relative)
  • NOT start with `/\\` or `\\\\` (backslash variants)
  • NOT contain `://` anywhere
  • NOT begin with a dangerous scheme after the leading `/`
    (`javascript:`, `data:`, `vbscript:`, `file:`, `about:`, `blob:`)
  • NOT loop to `/login` or `/signup`

Anything failing → canonical fallback `/app/dashboard`.

For Cashfree return URLs (which MUST be absolute https URLs of our
own frontend), there is a separate helper `assert_same_origin_https`
that validates the URL host against an allowlist drawn from the
`FRONTEND_URL`/`ALLOWED_REDIRECT_HOSTS` env vars.
"""
from __future__ import annotations

import os
import re
from urllib.parse import unquote, urlparse


SAFE_FALLBACK = "/app/dashboard"
_DANGEROUS_SCHEMES = re.compile(
    r"^/(javascript|data|vbscript|file|about|blob):",
    re.IGNORECASE,
)
_CONTROL_OR_WS = re.compile(r"^[\s\x00-\x1f]+|[\s\x00-\x1f]+$")


def _exhaustive_decode(s: str, max_passes: int = 5) -> str:
    cur = s
    for _ in range(max_passes):
        try:
            nxt = unquote(cur)
        except Exception:
            return cur
        if nxt == cur:
            return cur
        cur = nxt
    return cur


def safe_redirect_path(value, fallback: str = SAFE_FALLBACK) -> str:
    """Return a safe same-origin path or the canonical fallback.

    Args:
        value: candidate path (decoded or not). Must be str-like.
        fallback: returned for any tampered/unsafe value.
    """
    if not value or not isinstance(value, str):
        return fallback

    stripped = _CONTROL_OR_WS.sub("", value)
    if not stripped:
        return fallback

    decoded_raw = _exhaustive_decode(stripped)
    decoded = decoded_raw.lower()

    # Must be a relative same-site path.
    if not decoded.startswith("/"):
        return fallback
    if decoded.startswith("//"):
        return fallback
    if decoded.startswith("/\\") or decoded.startswith("\\\\"):
        return fallback

    # Any embedded `://` is rejected (defense in depth).
    if "://" in decoded:
        return fallback

    # Dangerous schemes immediately after the leading slash.
    if _DANGEROUS_SCHEMES.match(decoded):
        return fallback

    # Prevent loops back to auth pages.
    for loop_path in ("/login", "/signup"):
        if (
            decoded == loop_path
            or decoded.startswith(loop_path + "?")
            or decoded.startswith(loop_path + "#")
            or decoded.startswith(loop_path + "/")
        ):
            return fallback

    return decoded_raw


# ─────────────────────────────────────────────────────────────────────
# Same-origin HTTPS validation for absolute URLs we hand off to Cashfree.
# ─────────────────────────────────────────────────────────────────────
def _allowed_hosts() -> set:
    """Hosts we will allow as the host of an outbound redirect URL.

    Drawn from env vars so production/staging/preview each lock down to
    their own canonical hosts without code changes.
    """
    hosts = set()
    raw = os.environ.get("ALLOWED_REDIRECT_HOSTS", "")
    for h in raw.split(","):
        h = h.strip().lower()
        if h:
            hosts.add(h)
    # Always allow whatever FRONTEND_URL points at.
    fu = os.environ.get("FRONTEND_URL", "")
    if fu:
        try:
            p = urlparse(fu)
            if p.hostname:
                hosts.add(p.hostname.lower())
        except Exception:
            pass
    # Sensible defaults for the visionary-suite.com prod surface.
    hosts.update({"www.visionary-suite.com", "visionary-suite.com"})
    return hosts


def assert_same_origin_https(url: str) -> str:
    """Validate that `url` is an https URL on an allowed host.

    Used for Cashfree `return_url` / `notify_url` payloads. Raises
    ValueError on violation so the caller fails closed.
    """
    if not isinstance(url, str) or not url:
        raise ValueError("redirect URL is empty")

    decoded = _exhaustive_decode(url.strip())
    parsed = urlparse(decoded)

    if parsed.scheme != "https":
        raise ValueError(
            f"redirect URL must be https, got scheme={parsed.scheme!r}"
        )
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValueError("redirect URL has no host")
    if host not in _allowed_hosts():
        raise ValueError(
            f"redirect URL host {host!r} not in ALLOWED_REDIRECT_HOSTS"
        )
    if parsed.path and (parsed.path.startswith("//") or "://" in parsed.path):
        raise ValueError("redirect URL path looks tampered")
    return decoded


__all__ = [
    "safe_redirect_path",
    "assert_same_origin_https",
    "SAFE_FALLBACK",
]
