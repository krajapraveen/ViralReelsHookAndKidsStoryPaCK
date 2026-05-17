"""
P0 2026-05-19 CASE B (visible-marker iteration) — production cache bust.
========================================================================
Second CASE B in a row indicates the previous CASE B hotfix never
actually reached the user — either the deploy didn't land OR a stale
Service Worker / CDN intermediary served an older bundle. The toast
text shown in the screenshot (`frontend rejected style=object`) is
straight from the previous hotfix, so the page IS loading newer code,
but possibly NOT the very latest. The user explicitly required:

  1. Visible build marker on the page itself so incognito production
     can prove which bundle is loaded.
  2. Service Worker / cache-bust at boot so a legacy SW or CacheStorage
     can never persist across a hard refresh.
  3. No-cache headers on the app shell (index.html).

This file pins those three contracts.
"""
from __future__ import annotations

from pathlib import Path

PHOTO_TO_COMIC_JS = Path("/app/frontend/src/pages/PhotoToComic.js")
INDEX_JS = Path("/app/frontend/src/index.js")
INDEX_HTML = Path("/app/frontend/public/index.html")


# ════════════════════════════════════════════════════════════════════════
# 1. Visible build marker
# ════════════════════════════════════════════════════════════════════════
def test_bundle_version_bumped_for_this_iteration():
    """The bundle version must change EVERY time we ship a CASE B
    hotfix so production can confirm visually which iteration is
    live."""
    src = PHOTO_TO_COMIC_JS.read_text()
    # Pinned to the current iteration. Bump this string in lockstep with
    # the BUNDLE_VERSION constant whenever a new P2C hotfix ships.
    assert "const BUNDLE_VERSION = '2026-05-19-p2c-event-trap-fix'" in src, (
        "BUNDLE_VERSION must be bumped to the event-trap-fix iteration"
    )


def test_visible_build_marker_renders_near_generate_button():
    """The marker must be in the JSX, must reference BUNDLE_VERSION
    (not a hardcoded string that can drift), and must carry the
    canonical testid for Playwright assertions."""
    src = PHOTO_TO_COMIC_JS.read_text()
    assert 'data-testid="p2c-build-marker"' in src, (
        "Visible build marker must carry the canonical testid"
    )
    # The text must reference BUNDLE_VERSION rather than a hardcoded
    # string (avoid future drift).
    marker_block = src.split('data-testid="p2c-build-marker"', 1)[1].split(
        "</div>", 1
    )[0]
    assert "{BUNDLE_VERSION}" in marker_block, (
        "Marker must interpolate BUNDLE_VERSION, not hardcode a string"
    )
    assert "P2C build:" in marker_block, (
        "Marker prefix must match the founder spec text"
    )


def test_marker_is_styled_subtly_so_it_doesnt_dominate_ui():
    """Founder spec calls this a TEMPORARY diagnostic — it must be
    visible enough to read in a screenshot but not dominate the UI."""
    src = PHOTO_TO_COMIC_JS.read_text()
    marker = src.split('data-testid="p2c-build-marker"', 1)[0][-300:]
    # Tiny, muted, monospace.
    assert "text-[9px]" in marker
    assert "text-slate-600" in marker
    assert "font-mono" in marker


# ════════════════════════════════════════════════════════════════════════
# 2. Service Worker / Cache Storage unregister at boot
# ════════════════════════════════════════════════════════════════════════
def test_service_worker_unregister_runs_at_boot():
    src = INDEX_JS.read_text()
    assert "navigator.serviceWorker.getRegistrations()" in src, (
        "Boot must enumerate ALL Service Worker registrations so legacy "
        "SWs from prior deploys can be killed"
    )
    assert "reg.unregister()" in src, (
        "Each enumerated SW must be unregistered"
    )
    assert "[boot] unregistering legacy ServiceWorker" in src, (
        "Forensic log must be greppable so we can see when this fires "
        "on a user's first load"
    )


def test_cache_storage_keys_cleared_at_boot():
    """Without clearing CacheStorage, the next page load still serves
    stale JS bundles even after the SW is unregistered."""
    src = INDEX_JS.read_text()
    assert "caches.keys()" in src
    assert "caches.delete(name)" in src


def test_sw_unregister_is_defensive_against_missing_apis():
    """The SW unregister code must not crash if the browser doesn't
    support Service Workers OR CacheStorage (older browsers, file://
    contexts, etc.)."""
    src = INDEX_JS.read_text()
    assert "'serviceWorker' in navigator" in src
    assert "typeof navigator !== 'undefined'" in src
    assert "typeof caches !== 'undefined'" in src


# ════════════════════════════════════════════════════════════════════════
# 3. No-cache headers on the app shell
# ════════════════════════════════════════════════════════════════════════
def test_index_html_declares_no_cache_for_app_shell():
    """Hashed JS/CSS assets are immutable (webpack hashes them), but
    index.html itself MUST be marked no-cache so the browser/proxy
    always fetches the latest. Without this, the user keeps loading
    the same old index.html that references the same old asset
    hashes."""
    html = INDEX_HTML.read_text()
    assert 'http-equiv="Cache-Control"' in html, (
        "index.html must declare Cache-Control: no-cache for the app shell"
    )
    assert "no-cache, no-store, must-revalidate" in html, (
        "Cache-Control directive must be aggressive enough to stop "
        "intermediary caches"
    )
    assert 'http-equiv="Pragma"' in html
    assert 'http-equiv="Expires"' in html
