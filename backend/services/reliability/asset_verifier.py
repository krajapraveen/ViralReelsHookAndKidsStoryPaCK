"""
Asset verification helper — P0 2026-05-22 reliability sweep.

Bug-class elimination (see /app/memory/ENGINEERING_DOCTRINE.md →
"The Bug-Class Elimination Mandate") for the production incident
where a Reaction GIF job was marked COMPLETED with an asset that
the browser rendered as a broken image — while share / download /
copy-link actions were exposed in the success UI.

The completion-invariant helper already gates *count* matches.
This helper gates *asset validity* — does the file actually exist
on disk, is it non-empty, and is it a real image the browser can
render?

A pipeline that produces media output MUST call this helper before
declaring an asset as ready. The contract:

    from services.reliability.asset_verifier import (
        verify_image_asset, AssetVerifyResult,
    )

    result = verify_image_asset(filepath)
    if not result.ok:
        # log + skip — do NOT enqueue the URL into real_results
        ...

Doctrine references:
  • rule 1 (every boundary validates) — disk/file boundary
  • rule 2 (canonical state) — "asset ready" must mean "asset readable"
  • rule 3 (every failure is observable) — verifier emits reason codes

This module is intentionally synchronous-only; verification touches
local disk and is fast. It NEVER raises — verification failure is a
domain event, not a 500.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("creatorstudio.asset_verifier")

# Minimum payload size — anything smaller than this is almost
# certainly metadata-only or empty. PNGs encode at least an 8-byte
# signature, a 13-byte IHDR, and a 12-byte IEND — but a real image
# is always many KB. 256 bytes is a generous floor that catches
# zero-byte files and "data:image/..." placeholder garbage.
MIN_ASSET_BYTES = 256

# Maximum payload size we consider before refusing to verify — at
# 30MB the file is clearly beyond what our pipeline produces and
# something has gone wrong upstream.
MAX_ASSET_BYTES = 30 * 1024 * 1024

# Magic-byte prefixes for image formats we accept as renderable.
_MAGIC_PREFIXES: tuple[tuple[bytes, str, str], ...] = (
    (b"\x89PNG\r\n\x1a\n", "PNG", "image/png"),
    (b"\xff\xd8\xff",       "JPEG", "image/jpeg"),
    (b"GIF87a",             "GIF", "image/gif"),
    (b"GIF89a",             "GIF", "image/gif"),
    (b"RIFF",               "WEBP", "image/webp"),   # WEBP starts with RIFF; we confirm below
    (b"BM",                 "BMP", "image/bmp"),
)


@dataclass(frozen=True)
class AssetVerifyResult:
    ok: bool
    reason: str
    size: int
    fmt: Optional[str]
    content_type: Optional[str]
    filepath: str

    def as_meta(self) -> dict:
        """Compact representation suitable for log lines and the
        completion-invariant metric `meta` field."""
        return {
            "ok": self.ok,
            "reason": self.reason,
            "size": self.size,
            "fmt": self.fmt,
            "content_type": self.content_type,
            # path is logged for ops, but never returned to the client.
            "filepath": os.path.basename(self.filepath) if self.filepath else "",
        }


def _detect_magic(head: bytes) -> tuple[Optional[str], Optional[str]]:
    """Return (format, content_type) if the byte prefix matches a
    known renderable image format, else (None, None)."""
    for prefix, fmt, ctype in _MAGIC_PREFIXES:
        if head.startswith(prefix):
            # WEBP: RIFF...WEBP. Confirm the "WEBP" tag at offset 8.
            if fmt == "WEBP":
                if len(head) >= 12 and head[8:12] == b"WEBP":
                    return fmt, ctype
                continue
            return fmt, ctype
    return None, None


def verify_image_asset(filepath: str) -> AssetVerifyResult:
    """Verify that `filepath` points at a non-empty, readable image
    of an accepted format. Returns an `AssetVerifyResult` with a
    reason code. NEVER raises.

    Reason codes (stable; tests pin against them):
      • ok                       — verification passed
      • missing_path             — empty / None filepath argument
      • not_found                — file does not exist on disk
      • not_a_file               — exists but is a directory or symlink loop
      • empty_file               — file size is zero
      • below_min_size           — file size below MIN_ASSET_BYTES
      • above_max_size           — file size above MAX_ASSET_BYTES (sanity guard)
      • unreadable               — OSError while opening the file
      • unknown_format           — magic bytes do not match any accepted format
    """
    if not filepath:
        return AssetVerifyResult(
            ok=False, reason="missing_path", size=0,
            fmt=None, content_type=None, filepath="",
        )

    if not os.path.exists(filepath):
        return AssetVerifyResult(
            ok=False, reason="not_found", size=0,
            fmt=None, content_type=None, filepath=filepath,
        )

    if not os.path.isfile(filepath):
        return AssetVerifyResult(
            ok=False, reason="not_a_file", size=0,
            fmt=None, content_type=None, filepath=filepath,
        )

    try:
        size = os.path.getsize(filepath)
    except OSError:
        return AssetVerifyResult(
            ok=False, reason="unreadable", size=0,
            fmt=None, content_type=None, filepath=filepath,
        )

    if size == 0:
        return AssetVerifyResult(
            ok=False, reason="empty_file", size=0,
            fmt=None, content_type=None, filepath=filepath,
        )

    if size < MIN_ASSET_BYTES:
        return AssetVerifyResult(
            ok=False, reason="below_min_size", size=size,
            fmt=None, content_type=None, filepath=filepath,
        )

    if size > MAX_ASSET_BYTES:
        return AssetVerifyResult(
            ok=False, reason="above_max_size", size=size,
            fmt=None, content_type=None, filepath=filepath,
        )

    try:
        with open(filepath, "rb") as f:
            head = f.read(32)
    except OSError:
        return AssetVerifyResult(
            ok=False, reason="unreadable", size=size,
            fmt=None, content_type=None, filepath=filepath,
        )

    fmt, ctype = _detect_magic(head)
    if fmt is None:
        return AssetVerifyResult(
            ok=False, reason="unknown_format", size=size,
            fmt=None, content_type=None, filepath=filepath,
        )

    return AssetVerifyResult(
        ok=True, reason="ok", size=size,
        fmt=fmt, content_type=ctype, filepath=filepath,
    )
