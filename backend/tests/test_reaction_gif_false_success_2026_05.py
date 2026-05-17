"""
P0 2026-05-22 — Reaction GIF false-success bug-class elimination suite.

Production incident: A Reaction GIF job was being marked COMPLETED
with an asset that the browser rendered as a broken image, while
Share / Download / Copy Link / "Try another reaction" actions were
exposed in the success UI.

This audit codifies the Bug-Class Elimination Mandate
(/app/memory/ENGINEERING_DOCTRINE.md → "The Bug-Class Elimination
Mandate") for that bug class. It locks in:

  1. The `verify_image_asset` helper:
     • exists with the canonical public API
     • rejects empty, below-min, missing, and unknown-magic files
     • accepts a real PNG written from PIL
     • never raises
     • returns stable reason codes

  2. The Reaction GIF route:
     • imports `verify_image_asset`
     • calls it BEFORE appending a URL to `real_results`
     • persists `assetVerified` flag on the COMPLETED status update
     • emits the `reaction_gif_asset_verify_failed_total` metric on
       a verification miss

  3. The frontend page:
     • only renders share/download UI when `previewReady === true`
     • runs an in-browser image preload probe before flipping
       `previewReady`
     • has a "Retry preview" CTA when probes exhaust
     • emits the new `reaction_gif_broken_preview_total` and
       `reaction_gif_false_success_prevented_total` beacons

  4. Diagnostics beacon allow-listing for all five new metrics.

A PR that weakens any of the above must edit this file deliberately
AND attach an 8-section bug-class elimination report.
"""

from __future__ import annotations

import io
import os
import re
import struct
import sys
import tempfile
import zlib
from pathlib import Path

import pytest

APP = Path("/app")
PAGE = APP / "frontend/src/pages/PhotoReactionGIF.js"
BACKEND_ROUTE = APP / "backend/routes/reaction_gif.py"
VERIFIER_MODULE = APP / "backend/services/reliability/asset_verifier.py"
BEACON_ROUTE = APP / "backend/routes/diagnostics_beacon.py"

sys.path.insert(0, str(APP / "backend"))

from services.reliability.asset_verifier import (  # noqa: E402
    verify_image_asset,
    AssetVerifyResult,
    MIN_ASSET_BYTES,
)


# ─── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def page_src() -> str:
    return PAGE.read_text()


@pytest.fixture(scope="module")
def route_src() -> str:
    return BACKEND_ROUTE.read_text()


@pytest.fixture(scope="module")
def verifier_src() -> str:
    return VERIFIER_MODULE.read_text()


@pytest.fixture(scope="module")
def beacon_src() -> str:
    return BEACON_ROUTE.read_text()


@pytest.fixture
def tmp_image_dir(tmp_path):
    return tmp_path


def _make_real_png(path: Path, width: int = 8, height: int = 8) -> None:
    """Write a real, decoder-clean PNG using only stdlib (zlib +
    struct). We deliberately avoid pulling Pillow into the test
    surface so the verifier under test is exercised against bytes
    no different from what production writes.

    Pixels are pseudo-random so the IDAT chunk does not compress
    down past MIN_ASSET_BYTES at small sizes."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    # Noisy pixel pattern derived from coordinates so the image is
    # decoder-clean but resists zlib compression.
    raw = b""
    for y in range(height):
        row = b"\x00"  # filter byte = None
        for x in range(width):
            row += bytes(((x * 31) & 0xFF, (y * 53) & 0xFF, ((x * y * 17) & 0xFF)))
        raw += row
    idat = chunk(b"IDAT", zlib.compress(raw))
    iend = chunk(b"IEND", b"")
    path.write_bytes(sig + ihdr + idat + iend)


# ─── Verifier helper ─────────────────────────────────────────────────


def test_verifier_public_api_intact(verifier_src: str) -> None:
    assert "def verify_image_asset(" in verifier_src
    assert "class AssetVerifyResult" in verifier_src
    assert "MIN_ASSET_BYTES" in verifier_src


def test_verifier_rejects_missing_path():
    result = verify_image_asset("")
    assert result.ok is False
    assert result.reason == "missing_path"


def test_verifier_rejects_nonexistent_file(tmp_image_dir):
    result = verify_image_asset(str(tmp_image_dir / "does_not_exist.png"))
    assert result.ok is False
    assert result.reason == "not_found"


def test_verifier_rejects_directory(tmp_image_dir):
    result = verify_image_asset(str(tmp_image_dir))
    assert result.ok is False
    assert result.reason == "not_a_file"


def test_verifier_rejects_empty_file(tmp_image_dir):
    p = tmp_image_dir / "zero.png"
    p.write_bytes(b"")
    result = verify_image_asset(str(p))
    assert result.ok is False
    assert result.reason == "empty_file"


def test_verifier_rejects_below_min_size(tmp_image_dir):
    p = tmp_image_dir / "tiny.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 10)  # 18 bytes, valid magic but too small
    result = verify_image_asset(str(p))
    assert result.ok is False
    assert result.reason == "below_min_size"
    assert result.size < MIN_ASSET_BYTES


def test_verifier_rejects_unknown_format(tmp_image_dir):
    p = tmp_image_dir / "garbage.png"
    # Write 1KB of random-looking bytes that don't match any magic.
    p.write_bytes(b"junkjunkjunk" * 200)
    result = verify_image_asset(str(p))
    assert result.ok is False
    assert result.reason == "unknown_format"


def test_verifier_accepts_real_png(tmp_image_dir):
    p = tmp_image_dir / "real.png"
    _make_real_png(p, width=128, height=128)
    # Verify the image is large enough (noisy 128x128 compresses to >256 bytes).
    assert p.stat().st_size >= MIN_ASSET_BYTES, (
        f"Test fixture too small: {p.stat().st_size} bytes < MIN_ASSET_BYTES={MIN_ASSET_BYTES}"
    )
    result = verify_image_asset(str(p))
    assert result.ok is True
    assert result.reason == "ok"
    assert result.fmt == "PNG"
    assert result.content_type == "image/png"


def test_verifier_accepts_gif(tmp_image_dir):
    p = tmp_image_dir / "real.gif"
    # GIF89a header + LSD + minimal content (just enough bytes).
    body = b"GIF89a" + b"\x10\x00\x10\x00" + b"\x00" * 512
    p.write_bytes(body)
    result = verify_image_asset(str(p))
    assert result.ok is True
    assert result.fmt == "GIF"


def test_verifier_never_raises_on_bad_input():
    # The static type system doesn't catch None at runtime, so a caller
    # may legitimately pass None. The helper must absorb it.
    result = verify_image_asset(None)  # type: ignore[arg-type]
    assert result.ok is False


# ─── Backend route wiring ────────────────────────────────────────────


def test_route_imports_verify_image_asset(route_src: str) -> None:
    assert "from services.reliability.asset_verifier import verify_image_asset" in route_src


def test_route_calls_verifier_before_appending_result(route_src: str) -> None:
    """In process_reaction_gif, verify_image_asset(...) must be called
    BEFORE the URL is appended to real_results. We pin this with a
    textual ordering check on the function body."""
    header = re.search(
        r"^async def _process_reaction_gif_inner\s*\([\s\S]*?\)\s*(?:->[^:]+)?\s*:\s*\n",
        route_src,
        re.M,
    )
    assert header, "_process_reaction_gif_inner not found"
    body_start = header.end()
    next_def = re.search(
        r"^(?:async\s+)?def\s+\w+\s*\(",
        route_src[body_start:],
        re.M,
    )
    body_end = body_start + next_def.start() if next_def else len(route_src)
    body = route_src[body_start:body_end]

    verify_pos = body.find("verify_image_asset(")
    append_pos = body.find("real_results.append(")
    assert verify_pos != -1, "verify_image_asset must be called in process_reaction_gif"
    assert append_pos != -1, "real_results.append must be present"
    assert verify_pos < append_pos, (
        "verify_image_asset must be called BEFORE the URL is appended "
        "to real_results, so an unverified file cannot reach the "
        "success path."
    )


def test_route_persists_asset_verified_flag(route_src: str) -> None:
    """The COMPLETED status update must set `assetVerified=True` so the
    frontend can gate share/download behind it."""
    assert re.search(
        r"""['"]assetVerified['"]\s*:\s*True""",
        route_src,
    ), "Route must persist assetVerified=True on the COMPLETED branch."


def test_route_emits_asset_verify_failed_metric(route_src: str) -> None:
    assert "reaction_gif_asset_verify_failed_total" in route_src, (
        "Route must emit reaction_gif_asset_verify_failed_total when "
        "the asset verifier rejects a frame."
    )


# ─── Frontend gate ───────────────────────────────────────────────────


def test_frontend_has_preview_readiness_state(page_src: str) -> None:
    assert "previewReady" in page_src
    assert "previewProbing" in page_src
    assert "previewFailed" in page_src
    assert "runPreviewProbe" in page_src
    assert "PREVIEW_PROBE_MAX_ATTEMPTS" in page_src


def test_frontend_gates_share_and_download_behind_preview_ready(
    page_src: str,
) -> None:
    """Share / Download / Copy Link must be wrapped behind a
    `showActions`/`previewReady` guard. We pin the source so the gate
    cannot be silently removed during a refactor."""
    assert "const showActions = previewReady" in page_src, (
        "PhotoReactionGIF.js must derive `showActions` from "
        "`previewReady` and gate the share/download cluster behind it."
    )
    # The share cluster and download block must be inside the guard.
    assert "{showActions && (" in page_src, (
        "PhotoReactionGIF.js must wrap the share/download UI inside "
        "`{showActions && (...)}` so they NEVER render before the "
        "in-browser preload probe succeeds."
    )


def test_frontend_renders_finalizing_overlay(page_src: str) -> None:
    assert "result-finalizing-overlay" in page_src
    assert "result-preview-retry" in page_src
    assert "result-preview-retry-btn" in page_src
    assert "result-actions-gated" in page_src


def test_frontend_gate_checks_backend_asset_verified(page_src: str) -> None:
    """The COMPLETED-status branch must check backend's `assetVerified`
    flag — not just the status code — before exposing the result UI."""
    assert "res.data.assetVerified === true" in page_src, (
        "PhotoReactionGIF.js must require backend assetVerified=true "
        "before entering the result phase. Without this check, a "
        "stale or legacy COMPLETED row could still expose share/download."
    )


def test_frontend_emits_false_success_metrics(page_src: str) -> None:
    assert "reaction_gif_broken_preview_total" in page_src
    assert "reaction_gif_false_success_prevented_total" in page_src
    assert "reaction_gif_download_url_missing_total" in page_src
    assert "reaction_gif_asset_verify_started_total" in page_src


def test_frontend_probe_uses_cache_buster_on_retry(page_src: str) -> None:
    """A CDN cached 404 must not lock retries out. Pin the cache-bust."""
    assert re.search(r"_p=\$\{att\}_\$\{Date\.now\(\)\}", page_src), (
        "PhotoReactionGIF.js retry probe must include a cache-buster "
        "query param so CDN/browser caches cannot pin a 404 forever."
    )


# ─── Beacon allow-list ───────────────────────────────────────────────


def test_beacon_allowlists_false_success_metrics(beacon_src: str) -> None:
    required = (
        "reaction_gif_asset_verify_started_total",
        "reaction_gif_asset_verify_failed_total",
        "reaction_gif_broken_preview_total",
        "reaction_gif_false_success_prevented_total",
        "reaction_gif_download_url_missing_total",
    )
    missing = [m for m in required if m not in beacon_src]
    assert not missing, (
        "diagnostics_beacon.ALLOWED_METRICS is missing the "
        f"false-success bug-class metrics: {missing}"
    )
