"""P0 2026-06-PROD-FOLLOWUP #4 — COEP/COOP playback regression.

Production incident (krajapraveen@gmail.com, fifth strike):

Generation finally reached COMPLETED. The trailer card showed
"COMPLETED" + a valid thumbnail, but the `<video>` player on the
result page showed "Video failed to load. Tap reload or refresh the
page."

DevTools Network tab showed the R2 `.mp4` GET as:

    Status: (failed) net::ERR_BLOCKED_BY_RESPONSE
            (NotSameOriginAfterDefaultedToSameOriginByCoep)
    Size:   0.0 kB

Root cause:
  • `backend/server.py` set `Cross-Origin-Embedder-Policy: credentialless`
    + `Cross-Origin-Opener-Policy: same-origin` GLOBALLY on every
    response. The intent was "enable SharedArrayBuffer for the
    optional BrowserVideoExport ffmpeg.wasm path."
  • Under COEP, every cross-origin subresource the page loads MUST
    either be CORS-validated or carry a `Cross-Origin-Resource-Policy`
    header. R2 presigned URLs send NEITHER.
  • Chrome therefore refused the `<video>` request, and the player
    silently surfaced "Video failed to load."

Bug-class fix:
  • REMOVE the global COEP + COOP headers from `backend/server.py`.
  • Keep `Cross-Origin-Resource-Policy: cross-origin` on API
    responses — harmless without COEP, useful for embedding.
  • `BrowserVideoExport.js` already guards on `typeof SharedArrayBuffer`
    (line 51) and falls back to single-threaded ffmpeg.wasm. Slower
    but functional.

These tests are the bug-class pin. Any future PR that re-adds
`Cross-Origin-Embedder-Policy` on the global response middleware will
fail the audit — UNLESS it ALSO either (a) configures R2 to send CORP
on every object, or (b) scopes COEP to a route subset that excludes
the photo-trailer playback page.

Registered under `make audit-boundaries`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path("/app")
BACKEND = REPO / "backend"
FRONTEND = REPO / "frontend"
sys.path.insert(0, str(BACKEND))

SERVER_PY = BACKEND / "server.py"
SECURITY_MIDDLEWARE_PY = BACKEND / "middleware" / "security.py"
SETUP_PROXY_JS = FRONTEND / "src" / "setupProxy.js"


def _security_headers_block() -> str:
    """Return the security-headers middleware body.

    Strategy: locate the anchor line that sets `Content-Security-Policy`
    (the canonical security-headers middleware) and return a generous
    window around it. This avoids regex/middleware-finder fragility.
    """
    src = SERVER_PY.read_text()
    anchor = src.find('response.headers["Content-Security-Policy"]')
    assert anchor >= 0, "Could not locate the security-headers middleware."
    return src[max(0, anchor - 200):anchor + 1500]


def test_no_global_coep_header():
    """Global response middleware MUST NOT set Cross-Origin-Embedder-Policy.
    Setting it globally breaks R2 video playback under Chrome."""
    body = _security_headers_block()
    # Look only for actual header-setter lines, not comments/prose
    # that document why we removed COEP.
    assert 'response.headers["Cross-Origin-Embedder-Policy"]' not in body, (
        "Setting Cross-Origin-Embedder-Policy globally breaks the production "
        "trailer playback path (Chrome refuses R2-hosted .mp4 with "
        "ERR_BLOCKED_BY_RESPONSE because R2 doesn't send CORP). If you need "
        "COEP for ffmpeg.wasm, scope it to the specific route — never global."
    )


def test_no_global_coop_same_origin():
    """COOP same-origin combined with COEP creates Cross-Origin Isolated
    mode. Without COEP, COOP alone is harmless, but we remove both for
    clarity (the BrowserVideoExport ffmpeg.wasm fallback path doesn't
    need either)."""
    body = _security_headers_block()
    assert 'response.headers["Cross-Origin-Opener-Policy"]' not in body, (
        "Cross-Origin-Opener-Policy was set alongside the now-removed COEP "
        "for SharedArrayBuffer support. Re-adding it without explicit "
        "scoping is a regression risk — keep it out of the global middleware."
    )


def test_setup_proxy_does_not_set_coep_coop():
    """Dev proxy (setupProxy.js) must mirror the production server.py
    state so preview-environment testing reproduces prod behaviour."""
    src = SETUP_PROXY_JS.read_text()
    assert "Cross-Origin-Embedder-Policy" not in src, (
        "setupProxy.js must not set COEP — it desyncs preview from prod "
        "and hides exactly the bug that hit production this iteration."
    )
    assert "Cross-Origin-Opener-Policy" not in src, (
        "setupProxy.js must not set COOP — see COEP comment above."
    )


def test_security_middleware_does_not_set_coep_coop():
    """Bug-class elimination: there was a SECOND middleware in
    `backend/middleware/security.py` that ALSO set COEP+COOP globally.
    Removing it from `server.py` alone was insufficient — production
    `curl -I` still showed the headers. Any future PR that re-adds
    them in EITHER place will fail."""
    src = SECURITY_MIDDLEWARE_PY.read_text()
    assert 'response.headers["Cross-Origin-Embedder-Policy"]' not in src, (
        "backend/middleware/security.py must not set COEP. This was the "
        "second silent setter that survived the first fix."
    )
    assert 'response.headers["Cross-Origin-Opener-Policy"]' not in src, (
        "backend/middleware/security.py must not set COOP."
    )


def test_cross_origin_resource_policy_retained():
    """We KEEP Cross-Origin-Resource-Policy: cross-origin on API
    responses — it's harmless without COEP and protects our own assets
    when embedded elsewhere. Removing it would be over-correction."""
    body = _security_headers_block()
    assert 'Cross-Origin-Resource-Policy' in body, (
        "Cross-Origin-Resource-Policy should remain on API responses — "
        "removing it weakens cross-origin protections without addressing "
        "any known bug."
    )


def test_browser_video_export_has_sab_fallback_guard():
    """The BrowserVideoExport feature MUST guard on SharedArrayBuffer
    availability so it degrades cleanly when COEP is removed."""
    p = FRONTEND / "src" / "components" / "BrowserVideoExport.js"
    src = p.read_text()
    assert "typeof SharedArrayBuffer" in src, (
        "BrowserVideoExport must check `typeof SharedArrayBuffer` before "
        "using it — otherwise removing COEP breaks the export pathway."
    )


def test_csp_media_src_allows_https():
    """The HTTP CSP header should NOT restrict media-src beyond what
    is needed. The current `media-src 'self' blob: https:` is correct
    and must not regress to `'self'` only — that would also block R2."""
    src = SERVER_PY.read_text()
    m = re.search(r'"media-src([^"]+)"', src)
    assert m, "media-src directive must exist in the CSP."
    directive = m.group(1)
    assert "https:" in directive, (
        "CSP media-src must include `https:` to permit R2-hosted "
        "playback. Restricting to 'self' only would re-break this bug."
    )
