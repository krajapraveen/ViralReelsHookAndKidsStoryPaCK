"""
Silent-render prevention — P0 2026-05-23 bug-class elimination.

Production trust-bug: generated MP4s were occasionally landing in
my-space / download flows with NO audio stream — users assumed the
videos themselves were broken. Root cause: multiple video pipelines
(OptimizedVideoRenderer + 3 genstudio Sora-2 flows) transitioned to
COMPLETED/`completed` without ever probing the final artifact for an
audible track.

Doctrine (/app/memory/ENGINEERING_DOCTRINE.md, "Bug-Class Elimination
Mandate"): patches are forbidden. The fix:

  1. One canonical gate — services.reliability.render_validator
     .validate_render — verifies file present + h264 video stream +
     aac audio stream + audio_duration >= video_duration - 0.5.
  2. Every video-producing pipeline is registered in
     render_validator.REGISTERED_RENDER_PIPELINES and MUST call
     validate_render against the local artifact before the COMPLETED
     transition.
  3. Auto-refund on RenderValidationError — silent renders must NEVER
     cost the user money.

This audit pins all three contracts statically (registry + call-site
+ refund-site grep) plus the unit-level invariants on the validator
itself. It is registered in /app/Makefile under `audit-boundaries`.
"""
from __future__ import annotations

import asyncio
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

BACKEND_DIR = Path("/app/backend")
sys.path.insert(0, str(BACKEND_DIR))


# ─────────────────────────────────────────────────────────────────────
# Section A — Static audit: every registered pipeline calls validate_render
# ─────────────────────────────────────────────────────────────────────
class TestRegisteredPipelinesCallValidator(unittest.TestCase):
    """Every entry in REGISTERED_RENDER_PIPELINES must reference
    `validate_render` somewhere in its source. This is the canonical
    bug-class gate. Adding a new video producer without this call
    fails CI before it can ship a silent video."""

    def test_registry_is_non_empty(self):
        from services.reliability.render_validator import REGISTERED_RENDER_PIPELINES
        self.assertGreater(
            len(REGISTERED_RENDER_PIPELINES), 0,
            "REGISTERED_RENDER_PIPELINES must list every video producer",
        )

    def test_every_registered_pipeline_imports_validate_render(self):
        from services.reliability.render_validator import REGISTERED_RENDER_PIPELINES
        missing: list[str] = []
        for rel in REGISTERED_RENDER_PIPELINES:
            path = BACKEND_DIR / rel
            self.assertTrue(
                path.exists(),
                f"Registered pipeline {rel} does not exist on disk",
            )
            src = path.read_text()
            if "validate_render" not in src:
                missing.append(rel)
        self.assertEqual(
            missing, [],
            f"Registered pipelines missing validate_render call: {missing}",
        )

    def test_no_unregistered_mp4_producer_marks_completed(self):
        """Scan backend/{routes,services} for files that BOTH write a
        local .mp4 AND mark a job COMPLETED/`completed`. Any such file
        must appear in REGISTERED_RENDER_PIPELINES. If a new module
        slips through, this test fails until the registry is updated
        AND validate_render is wired in."""
        from services.reliability.render_validator import REGISTERED_RENDER_PIPELINES
        registered = set(REGISTERED_RENDER_PIPELINES)
        # Allow-list — modules that legitimately mark COMPLETED for
        # NON-video assets (image strips, audio jobs, etc.).
        allowed_non_video: set[str] = {
            "routes/comic_storybook_v2.py",
            "routes/photo_to_comic.py",
            "routes/coloring_book_v2.py",
            "routes/reaction_gif.py",  # GIF, no audio
            "routes/comic_storybook.py",
            "services/comic_pipeline/job_orchestrator.py",
            "services/comic_storybook_janitor.py",
            "services/story_chain.py",
            "services/job_queue_service.py",
            "services/pipeline_engine.py",
            "services/pipeline_worker.py",
            "services/idempotency_service.py",
            "services/admission_controller.py",
            "services/generated_files_cleanup.py",
            "services/daily_report_service.py",
            "services/periodic_report_service.py",
            "services/cdn_optimizer.py",
            "services/media_preview_pipeline.py",
            "services/revenue_protection.py",
            "services/story_engine/safety.py",
            "services/reliability/completion_invariant.py",
            "services/activation_truth.py",
        }

        offenders: list[str] = []
        for root_dir in ("routes", "services"):
            for path in (BACKEND_DIR / root_dir).rglob("*.py"):
                rel = str(path.relative_to(BACKEND_DIR))
                src = path.read_text(errors="replace")
                # Detect direct .mp4 output writes (loose heuristic but
                # accurate for known producers).
                writes_mp4 = bool(re.search(r'\.mp4["\']', src)) and (
                    "save_video" in src
                    or "ffmpeg" in src.lower()
                    or "_finalize_output" in src
                )
                marks_completed = bool(
                    re.search(r'"status":\s*["\']COMPLETED["\']', src)
                    or re.search(r'"status":\s*["\']completed["\']', src)
                )
                if writes_mp4 and marks_completed:
                    if rel in registered or rel in allowed_non_video:
                        continue
                    offenders.append(rel)

        self.assertEqual(
            offenders, [],
            "Unregistered video-producing pipelines mark COMPLETED without "
            "validate_render. Add to REGISTERED_RENDER_PIPELINES AND wire "
            f"validate_render(): {offenders}",
        )


# ─────────────────────────────────────────────────────────────────────
# Section B — Unit tests on the canonical validator.
# ─────────────────────────────────────────────────────────────────────
class TestValidateRenderInvariants(unittest.TestCase):
    """Pin the stable failure reason codes the rest of the system
    branches on (refund classification, telemetry buckets)."""

    @classmethod
    def setUpClass(cls):
        cls.ffmpeg = shutil.which("ffmpeg")
        cls.ffprobe = shutil.which("ffprobe")
        cls.tmp = Path(tempfile.mkdtemp(prefix="silent_render_"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _run(self, coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def test_missing_path_reason(self):
        from services.reliability.render_validator import (
            validate_render, RenderValidationError,
        )
        with self.assertRaises(RenderValidationError) as ctx:
            self._run(validate_render(str(self.tmp / "does_not_exist.mp4")))
        self.assertEqual(ctx.exception.reason, "missing_path")

    def test_silent_video_fails_no_audio_stream(self):
        """A real MP4 with video but no audio must raise
        no_audio_stream (or no_audio_stream via ffmpeg fallback)."""
        if not self.ffmpeg:
            self.skipTest("ffmpeg not installed in test env")
        silent = self.tmp / "silent.mp4"
        subprocess.run(
            [self.ffmpeg, "-y", "-f", "lavfi", "-i", "color=c=black:s=320x240:d=1",
             "-c:v", "libx264", "-t", "1", str(silent)],
            check=True, capture_output=True, timeout=30,
        )
        from services.reliability import render_validator
        from services.reliability.render_validator import (
            validate_render, RenderValidationError,
        )
        # The base image ships a stub ffprobe → force fallback path so
        # the validator parses ffmpeg -i stderr (this is the same code
        # path live containers without a real ffprobe also take).
        with patch.object(render_validator, "_resolve_ffprobe", return_value=None):
            with self.assertRaises(RenderValidationError) as ctx:
                self._run(validate_render(str(silent)))
        self.assertEqual(ctx.exception.reason, "no_audio_stream")

    def test_ok_render_passes(self):
        """A real MP4 with both h264 video and AAC audio passes."""
        if not self.ffmpeg:
            self.skipTest("ffmpeg not installed in test env")
        ok = self.tmp / "ok.mp4"
        subprocess.run(
            [self.ffmpeg, "-y",
             "-f", "lavfi", "-i", "color=c=black:s=320x240:d=2",
             "-f", "lavfi", "-i", "anullsrc=cl=stereo:r=44100",
             "-c:v", "libx264", "-c:a", "aac", "-shortest",
             "-t", "2", str(ok)],
            check=True, capture_output=True, timeout=30,
        )
        from services.reliability import render_validator
        from services.reliability.render_validator import validate_render
        with patch.object(render_validator, "_resolve_ffprobe", return_value=None):
            result = self._run(validate_render(str(ok)))
        self.assertTrue(
            result.get("mode") in ("ffprobe", "ffmpeg_fallback"),
            f"validator returned unexpected mode: {result}",
        )


# ─────────────────────────────────────────────────────────────────────
# Section C — Genstudio refund contract.
# ─────────────────────────────────────────────────────────────────────
class TestGenstudioRefundsOnSilentRender(unittest.TestCase):
    """The 3 genstudio video flows must auto-refund credits when all
    retries exhaust on a RenderValidationError. The refund site is
    the `_refund_genstudio_video_credits` helper — verify it is
    invoked from each failure path."""

    def test_genstudio_imports_refund_helper(self):
        src = (BACKEND_DIR / "routes" / "genstudio.py").read_text()
        self.assertIn(
            "_refund_genstudio_video_credits", src,
            "genstudio.py must define the refund helper",
        )
        # Three video flows must each call the refund site.
        refund_call_count = src.count("await _refund_genstudio_video_credits(")
        self.assertGreaterEqual(
            refund_call_count, 3,
            "Each of the 3 genstudio video flows (text_to_video, "
            "image_to_video, video_remix) must auto-refund on failure; "
            f"found {refund_call_count} call sites",
        )

    def test_refund_helper_is_idempotent(self):
        """The refund flag (refundedCredits) must short-circuit a
        second call. Without idempotency a retried janitor would
        double-credit the user."""
        src = (BACKEND_DIR / "routes" / "genstudio.py").read_text()
        # Look for the idempotency guard inside the helper.
        helper_block = src.split("async def _refund_genstudio_video_credits")[1]
        self.assertIn(
            "refundedCredits", helper_block,
            "Refund helper must read refundedCredits flag for idempotency",
        )
        self.assertIn(
            "already refunded", helper_block.lower(),
            "Refund helper must log a no-op when already refunded",
        )


# ─────────────────────────────────────────────────────────────────────
# Section D — OptimizedVideoRenderer dispatches to failure on validation error.
# ─────────────────────────────────────────────────────────────────────
class TestOptimizedRendererDispatchesFailureOnSilentRender(unittest.TestCase):
    """OptimizedVideoRenderer.render_video must call validate_render
    against the local artifact BEFORE _update_job_completed and route
    to _handle_render_failure (which refunds credits) on
    RenderValidationError."""

    def test_render_video_calls_validator_before_completion(self):
        src = (BACKEND_DIR / "services" / "optimized_video_renderer.py").read_text()
        validate_idx = src.find("await validate_render(")
        complete_idx = src.find("await self._update_job_completed(")
        self.assertGreater(
            validate_idx, 0,
            "optimized_video_renderer must call validate_render()",
        )
        self.assertGreater(
            complete_idx, 0,
            "optimized_video_renderer must call _update_job_completed",
        )
        self.assertLess(
            validate_idx, complete_idx,
            "validate_render MUST execute BEFORE _update_job_completed; "
            "otherwise a silent video can be marked COMPLETED",
        )

    def test_validation_error_routes_to_handle_render_failure(self):
        src = (BACKEND_DIR / "services" / "optimized_video_renderer.py").read_text()
        # The validation-error block must call _handle_render_failure
        # (which already performs the auto-refund + status=FAILED).
        chunk = src.split("await validate_render(")[1]
        # Search the next 1500 chars only to ensure proximity.
        nearby = chunk[:1500]
        self.assertIn(
            "_handle_render_failure", nearby,
            "RenderValidationError must dispatch to _handle_render_failure "
            "(auto-refund + FAILED status)",
        )
        self.assertIn(
            "RenderValidationError", nearby,
            "The except block must catch RenderValidationError explicitly",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
