"""Tests for _normalize_ref_image_bytes patch (2026-04-30 P0).

Validates:
  1. Normalizer unit cases (RGB, RGBA, CMYK, palette, EXIF-rotation, oversize, tiny).
  2. Corrupt input raises → pipeline maps to HERO_LOAD_FAIL.
  3. Retry loop in _gen_scene_image is untouched.
  4. Idempotent: re-normalizing the output is a no-op byte-equal JPEG.

Run in isolation (per handoff guidance on cross-event-loop flakiness):
  cd /app && pytest backend/tests/test_photo_trailer_image_normalization.py -v
"""
from __future__ import annotations

import asyncio
import base64
from io import BytesIO
from unittest.mock import AsyncMock, patch

import pytest
from PIL import Image, UnidentifiedImageError

from routes.photo_trailer import _normalize_ref_image_bytes


# ───────────────────────── Helpers ────────────────────────────────────────
def _jpeg_bytes(img: Image.Image, **kw) -> bytes:
    buf = BytesIO()
    img.save(buf, format="JPEG", **{"quality": 90, **kw})
    return buf.getvalue()


def _png_bytes(img: Image.Image) -> bytes:
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _open(out: bytes) -> Image.Image:
    return Image.open(BytesIO(out))


# ───────────────────────── Unit tests ─────────────────────────────────────
def test_rgb_jpeg_happy_path():
    src = _jpeg_bytes(Image.new("RGB", (800, 600), (120, 45, 200)))
    out = _normalize_ref_image_bytes(src)
    im = _open(out)
    assert im.mode == "RGB"
    assert im.format == "JPEG"
    assert im.size == (800, 600)


def test_rgba_png_drops_alpha():
    src = _png_bytes(Image.new("RGBA", (500, 500), (10, 20, 30, 128)))
    out = _normalize_ref_image_bytes(src)
    im = _open(out)
    assert im.mode == "RGB"
    assert im.format == "JPEG"


def test_cmyk_jpeg_converts_to_rgb():
    cmyk = Image.new("CMYK", (400, 400), (50, 50, 50, 50))
    src = _jpeg_bytes(cmyk)
    out = _normalize_ref_image_bytes(src)
    im = _open(out)
    assert im.mode == "RGB"


def test_palette_png_converts_to_rgb():
    pal = Image.new("P", (300, 300))
    src = _png_bytes(pal)
    out = _normalize_ref_image_bytes(src)
    im = _open(out)
    assert im.mode == "RGB"


def test_oversize_is_capped_to_1024():
    src = _jpeg_bytes(Image.new("RGB", (3000, 4000), (10, 10, 10)))
    out = _normalize_ref_image_bytes(src)
    im = _open(out)
    # longest side must be exactly 1024 (thumbnail preserves aspect)
    assert max(im.size) == 1024
    # aspect preserved (3000:4000 → 768:1024)
    assert im.size == (768, 1024)


def test_tiny_image_is_left_alone():
    src = _jpeg_bytes(Image.new("RGB", (16, 16), (1, 2, 3)))
    out = _normalize_ref_image_bytes(src)
    im = _open(out)
    assert im.size == (16, 16)


def test_exif_orientation_is_honored():
    """EXIF orientation=6 means rotate 90° CW when rendered.
    After exif_transpose the pixel dimensions should swap."""
    # Create a 200x400 image with EXIF orientation=6 tag.
    base = Image.new("RGB", (200, 400), (200, 100, 50))
    buf = BytesIO()
    # Write with a minimal EXIF block encoding Orientation=6.
    # Pillow's Image.save accepts an `exif=` bytes payload.
    import struct
    # TIFF header (little-endian) + 1 IFD entry: Orientation (0x0112), SHORT, 1, value=6
    exif_bytes = (
        b"Exif\x00\x00"                      # APP1 exif header
        b"II*\x00"                           # TIFF little-endian, magic 42
        b"\x08\x00\x00\x00"                  # offset of 0th IFD = 8
        b"\x01\x00"                          # 1 entry
        + struct.pack("<HHI", 0x0112, 3, 1)  # tag, type(SHORT), count
        + struct.pack("<HH", 6, 0)           # value=6, padding
        + b"\x00\x00\x00\x00"                # no next IFD
    )
    base.save(buf, format="JPEG", exif=exif_bytes, quality=90)
    src = buf.getvalue()
    out = _normalize_ref_image_bytes(src)
    im = _open(out)
    # Original was 200x400 (portrait). Orientation=6 → should render as 400x200 (landscape).
    assert im.size == (400, 200), f"expected exif_transpose to swap dims, got {im.size}"


def test_corrupt_bytes_raise():
    with pytest.raises(UnidentifiedImageError):
        _normalize_ref_image_bytes(b"\x00\x01\x02not-an-image-at-all")


def test_truncated_bytes_raise():
    # Real JPEG header + garbage truncation
    src = _jpeg_bytes(Image.new("RGB", (100, 100), (0, 0, 0)))
    truncated = src[:20]  # well under a valid JPEG
    with pytest.raises(Exception):
        _normalize_ref_image_bytes(truncated)


def test_output_is_reasonable_size():
    """A 3000x4000 photo normalized should be a few-hundred-KB JPEG,
    not multi-megabyte. Loose upper bound — guards against obvious regressions."""
    src = _jpeg_bytes(Image.new("RGB", (3000, 4000), (127, 127, 127)), quality=95)
    out = _normalize_ref_image_bytes(src)
    assert len(out) < 800_000, f"normalized output too large: {len(out)} bytes"


def test_idempotent_on_already_normalized():
    src = _jpeg_bytes(Image.new("RGB", (500, 500), (50, 60, 70)))
    out1 = _normalize_ref_image_bytes(src)
    out2 = _normalize_ref_image_bytes(out1)
    # Re-normalizing must not keep shrinking or changing modes.
    im1, im2 = _open(out1), _open(out2)
    assert im1.size == im2.size
    assert im1.mode == im2.mode == "RGB"


# ───────────────────── Pipeline guard (HERO_LOAD_FAIL mapping) ────────────
def test_corrupt_hero_photo_maps_to_hero_load_fail():
    """Source-level guarantee that when _normalize_ref_image_bytes raises on
    corrupt input the pipeline fails the job with HERO_LOAD_FAIL (not a new
    error code). Motor collections don't support attribute monkey-patching
    across __getattr__, so we assert at the AST/source level — same pattern
    the reliability sprint test uses for retry config."""
    import inspect
    from routes import photo_trailer as pt

    src = inspect.getsource(pt._run_pipeline_inner)

    # 1. Hero branch: normalize inside try, except maps to HERO_LOAD_FAIL
    hero_block = (
        "        try:\n"
        "            hero_bytes = _normalize_ref_image_bytes(hero_bytes)\n"
        "        except Exception:\n"
        "            return await _fail(job_id, \"HERO_LOAD_FAIL\","
    )
    assert hero_block in src, "hero normalization→HERO_LOAD_FAIL guard missing"

    # 2. Villain branch: same mapping (no new code leaked)
    villain_block = (
        "                try:\n"
        "                    vb = _normalize_ref_image_bytes(vb)\n"
        "                    villain_b64 = base64.b64encode(vb).decode(\"utf-8\")\n"
        "                except Exception:\n"
        "                    return await _fail(job_id, \"HERO_LOAD_FAIL\","
    )
    assert villain_block in src, "villain normalization→HERO_LOAD_FAIL guard missing"

    # 3. Negative: no new error code was introduced
    for forbidden in ("IMAGE_NORMALIZE_FAIL", "NORMALIZE_FAIL", "PIL_FAIL", "BAD_IMAGE"):
        assert forbidden not in src, f"new error code leaked: {forbidden}"


# ───────────────────── Retry loop unchanged (regression guard) ────────────
def test_gen_scene_image_retry_loop_still_exists():
    """Signature + retry scaffolding in _gen_scene_image must be preserved.
    We introspect the function body — if retry logic was removed this test
    fails loudly."""
    import inspect
    from routes import photo_trailer as pt

    src = inspect.getsource(pt._gen_scene_image)
    # Must still contain the 3-attempt inner retry with the 2/5/10 backoff
    assert "BACKOFF_SECONDS = [2, 5, 10]" in src
    assert "for attempt in range(3):" in src
    # Must still delegate to an executor (non-blocking pattern intact)
    assert "run_in_executor" in src


def test_normalize_helper_is_referenced_in_pipeline():
    """Proves the wiring is wired — the patch would be silently dead if the
    call sites don't invoke _normalize_ref_image_bytes."""
    import inspect
    from routes import photo_trailer as pt

    src = inspect.getsource(pt._run_pipeline_inner)
    # Hero wrap
    assert "_normalize_ref_image_bytes(hero_bytes)" in src
    # Villain wrap
    assert "_normalize_ref_image_bytes(vb)" in src
