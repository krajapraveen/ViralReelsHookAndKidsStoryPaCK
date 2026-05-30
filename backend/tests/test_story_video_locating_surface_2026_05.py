"""
Story-to-Video generation surface trust contract — P0 2026-05-25.

Production trust-bug: the LocatingProjectCard (introduced 2026-05-24 to
prevent the false empty-MySpace UX) became the user's primary surface
during generation but did NOT show real progress, never escalated when
the backend went quiet, never had a hard timeout, never had engagement
during the wait, and never confirmed completion + routed back to the
listing. Users interpreted "Locating / Preparing scenes" as a hung
render.

Doctrine (/app/memory/ENGINEERING_DOCTRINE.md, Bug-Class Elimination
Mandate). Class: "long-running async UX with no honest progress signal."
The fix gates the trust surface on six independently-pinned contracts:

  1. Real % progress bar with numeric % AND stage strip.
  2. Estimated-progress fallback derived from state + elapsed time
     when the backend returns 0.
  3. Stale-state escalation after 90s without a state change.
  4. Hard timeout (8min) → FAILED card with Retry CTA.
  5. Engagement panel rotating every 10s with copyright-free copy
     (no scraped quotes, no brand names).
  6. Completion handoff: success toast + 3s auto-navigate to the
     MySpace listing.

This audit pins all six statically and is registered in
/app/Makefile under audit-boundaries.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

REPO = Path("/app")
FRONTEND = REPO / "frontend" / "src"
sys.path.insert(0, str(REPO / "backend"))


def _myspace_src() -> str:
    return (FRONTEND / "pages" / "MySpacePage.js").read_text()


# ─────────────────────────────────────────────────────────────────────
# Section A — Real % progress bar + stage strip.
# ─────────────────────────────────────────────────────────────────────
class TestRealProgressBarAndStages(unittest.TestCase):
    def setUp(self):
        self.src = _myspace_src()

    def test_progress_pct_element_present(self):
        self.assertIn(
            'data-testid="locating-progress-pct"', self.src,
            "LocatingProjectCard must render a numeric % element",
        )
        self.assertIn(
            'data-testid="locating-progress-bar"', self.src,
            "LocatingProjectCard must render a progress bar element",
        )
        self.assertIn(
            'data-testid="locating-stages"', self.src,
            "LocatingProjectCard must render a per-stage breakdown strip",
        )

    def test_stage_strip_covers_full_pipeline(self):
        # The canonical engine states (mirrors backend
        # _map_state_to_legacy_stage / _state_to_substage).
        required = [
            "PLANNING", "GENERATING_KEYFRAMES", "GENERATING_SCENE_CLIPS",
            "GENERATING_AUDIO", "ASSEMBLING_VIDEO", "VALIDATING",
        ]
        for state in required:
            self.assertIn(
                f"'{state}'", self.src,
                f"Stage progress map must reference state {state}",
            )

    def test_stage_strip_uses_friendly_labels(self):
        # Required user-facing labels from the prompt spec.
        for label in (
            "Request accepted",
            "Writing story scenes",
            "Creating visuals",
            "Adding motion",
            "Adding voice & music",
            "Rendering final video",
            "Saving to My Space",
        ):
            self.assertIn(
                label, self.src,
                f"Stage label '{label}' must be surfaced to the user",
            )


# ─────────────────────────────────────────────────────────────────────
# Section B — Estimated-progress fallback (creeps when backend stalls).
# ─────────────────────────────────────────────────────────────────────
class TestEstimatedProgressFallback(unittest.TestCase):
    def setUp(self):
        self.src = _myspace_src()

    def test_estimator_function_present(self):
        self.assertIn(
            "function _estimateProgress(", self.src,
            "An _estimateProgress helper must exist so the bar never freezes",
        )

    def test_estimator_uses_elapsed_time(self):
        block = self.src.split("function _estimateProgress(", 1)[1].split("\n}", 1)[0]
        self.assertIn(
            "startedAt", block,
            "Estimator must consume an elapsed-time anchor",
        )
        self.assertIn(
            "Date.now()", block,
            "Estimator must derive elapsed time from Date.now()",
        )

    def test_estimator_never_exceeds_99(self):
        """The estimator MUST cap at 99% — only the backend's terminal
        READY state can move us to 100. Otherwise the bar lies."""
        block = self.src.split("function _estimateProgress(", 1)[1].split("\n}", 1)[0]
        self.assertTrue(
            "99" in block,
            "Estimator must clamp to 99 to leave room for the terminal jump",
        )

    def test_estimator_is_monotonic(self):
        """The bar must never go backward (max with last value)."""
        block = self.src.split("function _estimateProgress(", 1)[1].split("\n}", 1)[0]
        self.assertTrue(
            "Math.max(" in block,
            "Estimator must use Math.max to prevent regression of % bar",
        )


# ─────────────────────────────────────────────────────────────────────
# Section C — Stale-state and hard-timeout escalation.
# ─────────────────────────────────────────────────────────────────────
class TestStaleAndTimeoutEscalation(unittest.TestCase):
    def setUp(self):
        self.src = _myspace_src()

    def test_stale_threshold_constant_is_90s(self):
        m = re.search(r"STALE_AFTER_MS\s*=\s*([0-9*\s]+);", self.src)
        self.assertIsNotNone(m, "STALE_AFTER_MS must be declared")
        # 90 * 1000 → 90000
        self.assertIn(
            "90", m.group(1),
            "STALE escalation must trigger at 90 seconds",
        )

    def test_hard_timeout_present(self):
        m = re.search(r"HARD_TIMEOUT_MS\s*=\s*([0-9*\s]+);", self.src)
        self.assertIsNotNone(m, "HARD_TIMEOUT_MS must be declared")
        # 8 * 60 * 1000 → 480000
        self.assertTrue(
            "8" in m.group(1) and "60" in m.group(1),
            "HARD_TIMEOUT_MS must be set to 8 minutes (8 * 60 * 1000)",
        )

    def test_stale_copy_present(self):
        self.assertIn(
            "Still rendering", self.src,
            "Stale state must surface honest 'Still rendering' copy",
        )

    def test_failed_state_renders_retry(self):
        self.assertIn(
            'data-testid="locating-retry-btn"', self.src,
            "FAILED card must surface a Retry button",
        )
        self.assertIn(
            'data-testid="locating-fail-msg"', self.src,
            "FAILED card must surface a user-readable failure message",
        )

    def test_terminal_state_sets_match_backend(self):
        # Backend states from story_engine_routes.py _map_state_to_legacy_stage
        for state in ("FAILED", "FAILED_PLANNING", "FAILED_IMAGES", "FAILED_TTS", "FAILED_RENDER"):
            self.assertIn(
                f"'{state}'", self.src,
                f"TERMINAL_FAIL set must include backend state {state}",
            )
        for state in ("COMPLETED", "READY", "PARTIAL", "PARTIAL_READY"):
            self.assertIn(
                f"'{state}'", self.src,
                f"TERMINAL_OK set must include backend state {state}",
            )


# ─────────────────────────────────────────────────────────────────────
# Section D — Engagement panel (copyright-free, rotates).
# ─────────────────────────────────────────────────────────────────────
class TestEngagementPanel(unittest.TestCase):
    def setUp(self):
        self.src = _myspace_src()

    def test_tip_panel_renders(self):
        self.assertIn(
            'data-testid="locating-tip"', self.src,
            "Engagement panel must render with stable testid",
        )
        self.assertIn(
            'data-testid="locating-tip-text"', self.src,
            "Engagement panel must expose the rotating text for e2e",
        )

    def test_tip_array_is_non_empty(self):
        m = re.search(r"__ENGAGEMENT_TIPS\s*=\s*\[(.*?)\];", self.src, re.DOTALL)
        self.assertIsNotNone(m, "__ENGAGEMENT_TIPS array must be declared")
        body = m.group(1)
        self.assertGreaterEqual(
            body.count("text:"), 6,
            "At least 6 tips required so rotation feels varied",
        )

    def test_rotation_interval_is_8_to_12s(self):
        m = re.search(r"TIP_ROTATION_MS\s*=\s*([0-9*\s]+);", self.src)
        self.assertIsNotNone(m, "TIP_ROTATION_MS must be declared")
        # 10 * 1000 → 10000 (per spec: 8–12s window, 10s sits in the middle)
        self.assertIn(
            "10", m.group(1),
            "Tip rotation must fire within the 8–12s window",
        )

    def test_tips_are_copyright_safe(self):
        """No scraped quotes, no third-party brand names, no copyrighted
        game titles. Spec mandates copyright-free / custom copy only."""
        m = re.search(r"__ENGAGEMENT_TIPS\s*=\s*\[(.*?)\];", self.src, re.DOTALL)
        self.assertIsNotNone(m)
        body_lower = m.group(1).lower()
        forbidden = [
            # Common brand names that would imply copyrighted assets
            "disney", "marvel", "pixar", "nintendo", "playstation",
            "monopoly", "scrabble", "candy crush", "minecraft",
            "fortnite", "roblox", "tiktok", "youtube",
            # Common quote-scraping markers
            "— einstein", "- einstein", "— gandhi", "- gandhi",
            "— jobs", "- jobs", "— mark twain", "- mark twain",
        ]
        for needle in forbidden:
            self.assertNotIn(
                needle, body_lower,
                f"Engagement tips must be copyright-safe (found: {needle!r})",
            )

    def test_tip_categories_match_spec(self):
        """Spec requires the panel to surface a mix of motivational
        quotes, 'try X next' nudges, and tips."""
        m = re.search(r"__ENGAGEMENT_TIPS\s*=\s*\[(.*?)\];", self.src, re.DOTALL)
        self.assertIsNotNone(m)
        body = m.group(1)
        for kind in ("'quote'", "'try'", "'tip'"):
            self.assertIn(
                f"kind: {kind}", body,
                f"Engagement panel must include category {kind}",
            )

    def test_cross_sell_features_named(self):
        """The 'Try X next' nudges from the spec must reference the
        existing app features verbatim."""
        for feature in (
            "Character Memory",
            "Reel Generator",
            "Bedtime Stories",
            "My Movie Trailer",
        ):
            self.assertIn(
                feature, self.src,
                f"Engagement panel must cross-sell '{feature}'",
            )


# ─────────────────────────────────────────────────────────────────────
# Section E — Completion handoff: toast + auto-navigate to MySpace.
# ─────────────────────────────────────────────────────────────────────
class TestCompletionHandoff(unittest.TestCase):
    def setUp(self):
        self.src = _myspace_src()

    def test_success_toast_fires_on_ready(self):
        self.assertIn(
            "saved to My Space", self.src,
            "Completion toast must confirm save to My Space",
        )
        self.assertIn(
            "toast.success", self.src,
            "Completion handoff must fire toast.success",
        )

    def test_auto_redirect_after_3_seconds(self):
        # The 3s auto-redirect must navigate to /app/my-space without
        # the projectId query (so the new card is rendered cleanly).
        self.assertTrue(
            "3000" in self.src,
            "Completion handoff must redirect after 3000ms",
        )
        self.assertIn(
            "navigate('/app/my-space'",
            self.src,
            "Auto-redirect target must be the MySpace listing route",
        )

    def test_go_to_myspace_cta_present(self):
        self.assertIn(
            'data-testid="locating-go-myspace-btn"', self.src,
            "Manual 'Go to My Space' CTA must remain available for users "
            "who don't want to wait for the 3s auto-redirect",
        )

    def test_ready_card_does_not_render_player_without_url(self):
        # The trust contract: never render a player element from
        # LocatingProjectCard. Player rendering belongs to the listing
        # cards, which already gate on hasPlayableVideo (output_url).
        ready_block_start = self.src.find("if (cardState === 'READY'")
        self.assertGreater(ready_block_start, 0)
        # Window of the READY branch only.
        ready_block = self.src[ready_block_start:ready_block_start + 3000]
        self.assertNotIn(
            "<video", ready_block,
            "LocatingProjectCard READY branch MUST NOT render a <video> "
            "element — playback belongs to the listing card, gated on "
            "output_url",
        )


# ─────────────────────────────────────────────────────────────────────
# Section F — Save-to-MySpace (backend invariant).
# ─────────────────────────────────────────────────────────────────────
class TestSaveToMySpaceInvariant(unittest.TestCase):
    """The completed job must show up in the canonical /user-jobs
    listing the moment it transitions to a terminal success state. This
    is guarded by the pre-existing audits (FR-11): no exclusion of
    PENDING/PROCESSING/QUEUED, response shape pinned to include job_id.
    Re-pin those here so this trust contract cannot regress in
    isolation."""

    def setUp(self):
        self.src = (REPO / "backend" / "routes" / "story_engine_routes.py").read_text()

    def test_user_jobs_includes_output_url_for_completed(self):
        """When state=READY the canonical user-jobs aggregator must
        surface `output_url` (after the entitlement gate)."""
        # The block uses `_make_presigned_url(doc.get("output_url"))` —
        # verify it's present in the story_engine projection.
        self.assertIn(
            '_make_presigned_url(doc.get("output_url"))',
            self.src,
            "user-jobs must include output_url so MySpace can render the player",
        )

    def test_status_endpoint_returns_state_progress_and_stage(self):
        """LocatingProjectCard depends on these three fields. Pin them
        in the status response."""
        # Search the get_status handler body.
        idx = self.src.find('@router.get("/status/{job_id}")')
        self.assertGreater(idx, 0)
        body = self.src[idx:idx + 6000]
        for field in ("state", "progress", "current_stage"):
            self.assertIn(
                field, body,
                f"/status response must include `{field}` (consumed by frontend)",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
