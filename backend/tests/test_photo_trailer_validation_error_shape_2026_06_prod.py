"""P0 2026-06-PROD-FOLLOWUP #3 — RenderValidationError attribute surface.

Production crash (krajapraveen@gmail.com, fourth strike):

    AttributeError: 'RenderValidationError' object has no attribute 'reason'

Root cause (line-level):
  • The LOCAL `RenderValidationError` class in `routes/photo_trailer.py`
    was a bare `class RenderValidationError(Exception): ...` alias with
    NO `__init__`. It carried no `reason`, no `video_duration`, no
    `audio_duration`, no `gap_seconds`.
  • The `_validate_render` wrapper translated the shared error to the
    local one via `raise RenderValidationError(str(e)) from e`,
    stripping every named attribute.
  • The duration-repair branch (P0 2026-06-PROD-FOLLOWUP #1) then
    accessed `e.reason in ("audio_shorter_than_video", ...)`, which
    AttributeError'd inside a `try` block — caught by the generic
    catch-all and surfaced as RENDER_FAIL.

Bug-class fix:
  • The local RenderValidationError now has the same __init__ surface
    as the shared one (services.reliability.render_validator).
  • `_validate_render` translates ALL named attributes (`reason`,
    `video_duration`, `audio_duration`) end-to-end so callers can
    dispatch on them.

These tests pin the contract — any future PR that drops the attribute
surface will fail the audit.

Registered under `make audit-boundaries`.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

REPO = Path("/app")
BACKEND = REPO / "backend"
sys.path.insert(0, str(BACKEND))


# ─────────────────────────────────────────────────────────────────────
# Section A — Local RenderValidationError carries the canonical attrs.
# ─────────────────────────────────────────────────────────────────────


def test_local_render_validation_error_has_reason_attribute():
    """A bare construction with just a message must still expose
    `.reason` (defaulting to 'unknown') so legacy callers cannot
    AttributeError."""
    from routes.photo_trailer import RenderValidationError
    e = RenderValidationError("audio shorter than video")
    assert hasattr(e, "reason"), "RenderValidationError must always expose .reason"
    assert e.reason == "unknown", (
        "Default reason must be 'unknown' so dispatch code can match it."
    )


def test_local_render_validation_error_carries_named_reason():
    from routes.photo_trailer import RenderValidationError
    e = RenderValidationError(
        "audio shorter than video (audio=60.07s, video=62.52s)",
        "audio_shorter_than_video",
        video_duration=62.52, audio_duration=60.07,
    )
    assert e.reason == "audio_shorter_than_video"
    assert e.video_duration == 62.52
    assert e.audio_duration == 60.07
    assert e.gap_seconds is not None
    assert abs(e.gap_seconds - 2.45) < 0.01


def test_local_render_validation_error_supports_repair_branch_access():
    """The exact attribute-access pattern the repair branch uses must
    not AttributeError on a freshly-raised local error."""
    from routes.photo_trailer import RenderValidationError
    try:
        raise RenderValidationError(
            "audio shorter than video", "audio_shorter_than_video",
            video_duration=62.52, audio_duration=60.07,
        )
    except RenderValidationError as e:
        # Mirrors the repair branch logic verbatim.
        gap = getattr(e, "gap_seconds", None) or 0.0
        repairable = (
            e.reason in ("audio_shorter_than_video", "audio_longer_than_video")
            and 0 < gap <= 10.0
            and getattr(e, "video_duration", None)
        )
        assert repairable, "Repair predicate must hold for the production case."


# ─────────────────────────────────────────────────────────────────────
# Section B — Wrapper preserves attributes across the translation.
# ─────────────────────────────────────────────────────────────────────


def test_wrapper_preserves_reason_and_durations():
    """`_validate_render` raises the LOCAL error type but must copy
    every attribute from the SHARED error first. This was the silent
    stripping site that caused the prod AttributeError."""
    from routes.photo_trailer import _validate_render, RenderValidationError
    from services.reliability.render_validator import (
        RenderValidationError as SharedErr,
    )

    async def _fail_shared(*_, **__):
        raise SharedErr(
            "audio shorter than video", "audio_shorter_than_video",
            video_duration=62.52, audio_duration=60.07,
        )

    # Monkeypatch the shared validator so we don't need a real MP4.
    import services.reliability.render_validator as rv_mod
    orig = rv_mod.validate_render
    rv_mod.validate_render = _fail_shared
    try:
        loop = asyncio.new_event_loop()
        try:
            with pytest.raises(RenderValidationError) as ctx:
                loop.run_until_complete(_validate_render("/tmp/does-not-matter"))
        finally:
            loop.close()
    finally:
        rv_mod.validate_render = orig

    e = ctx.value
    # All four canonical attributes must survive the translation.
    assert e.reason == "audio_shorter_than_video", (
        "Wrapper must copy .reason from the shared error."
    )
    assert e.video_duration == 62.52, "Wrapper must copy .video_duration."
    assert e.audio_duration == 60.07, "Wrapper must copy .audio_duration."
    assert e.gap_seconds is not None and abs(e.gap_seconds - 2.45) < 0.01


# ─────────────────────────────────────────────────────────────────────
# Section C — Static contract: no .reason access path can fail with the
# new __init__ surface. The dispatch sites must continue to work.
# ─────────────────────────────────────────────────────────────────────


def test_local_error_class_has_explicit_init_with_reason_kwarg():
    """Pin the local class signature so future PRs can't drop the
    attribute surface back to a bare Exception subclass."""
    import inspect
    from routes.photo_trailer import RenderValidationError
    sig = inspect.signature(RenderValidationError.__init__)
    params = sig.parameters
    for required in ("message", "reason", "video_duration", "audio_duration"):
        assert required in params, (
            f"RenderValidationError.__init__ must accept `{required}` — "
            f"removing it re-introduces the prod AttributeError bug class."
        )
