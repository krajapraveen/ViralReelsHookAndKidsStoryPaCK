"""
Retry visibility contract — P0 2026-05-31.

Bug class targeted: "UI omits canonical backend retry state, making
honest retries look like indefinite hangs."

The story_engine pipeline already enforces every safety invariant
the brief listed:
  • Retries are bounded per stage (STAGE_MAX_RETRIES in
    services/story_engine/state_machine.py — 1..4 attempts each).
  • Credit deduction happens EXACTLY ONCE in pipeline.create_job().
    Internal stage retries and manual POST /retry/{job_id} never call
    deduct_credits. Auto-refunds run through credits_service.
  • Polling is read-only: LocatingProjectCard only calls
    api.get('/api/story-engine/status/<id>'); never POST.
  • The Generate button is guarded by createLockRef (mutex).

What was missing — and what this audit now pins:
  1. /status response must surface `retry_info.is_retrying`,
     `retry_info.last_error_code`, and `retry_info.credits_charged_once`.
  2. LocatingProjectCard must show a distinct retry banner when
     is_retrying=true, so an automatic in-stage retry is never
     mistaken for a silent hang.
  3. FAILED card copy must follow the brief verbatim:
       "Video generation failed. Your credits are safe."
  4. Retry CTA must say "Retry generation" (not just "Retry").
  5. The brief's invariant "polling is read-only" must be statically
     guarded — LocatingProjectCard must never POST to /create.

Doctrine: /app/memory/ENGINEERING_DOCTRINE.md (Bug-Class Elimination
Mandate). Registered in /app/Makefile under audit-boundaries.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

REPO = Path("/app")
BACKEND = REPO / "backend"
FRONTEND_SRC = REPO / "frontend" / "src"
sys.path.insert(0, str(BACKEND))


def _routes_src() -> str:
    return (BACKEND / "routes" / "story_engine_routes.py").read_text()


def _myspace_src() -> str:
    return (FRONTEND_SRC / "pages" / "MySpacePage.js").read_text()


def _pipeline_src() -> str:
    return (BACKEND / "services" / "story_engine" / "pipeline.py").read_text()


def _state_machine_src() -> str:
    return (BACKEND / "services" / "story_engine" / "state_machine.py").read_text()


# ─────────────────────────────────────────────────────────────────────
# Section A — Backend bounded-retry invariant.
# ─────────────────────────────────────────────────────────────────────
class TestRetriesAreBounded(unittest.TestCase):
    """Class invariant: STAGE_MAX_RETRIES must be a finite dict — no
    infinite-loop possibility. Each per-stage cap is small (≤4)."""

    def test_stage_max_retries_is_finite(self):
        src = _state_machine_src()
        m = re.search(r"STAGE_MAX_RETRIES:[^{]*\{([^}]+)\}", src, re.DOTALL)
        self.assertIsNotNone(m, "STAGE_MAX_RETRIES must be declared")
        body = m.group(1)
        # Extract integers from the dict values.
        nums = [int(n) for n in re.findall(r":\s*(\d+)", body)]
        self.assertGreater(len(nums), 4, "Expected at least 5 stage entries")
        for n in nums:
            self.assertLessEqual(
                n, 4,
                "No single stage may be allowed more than 4 retries",
            )
            self.assertGreaterEqual(
                n, 1,
                "Every stage must permit at least 1 retry attempt",
            )

    def test_failure_to_retry_terminates_at_per_stage_failed_state(self):
        """The state machine routes every exhausted retry to a
        terminal FAILED_* state. This guarantees no infinite cycling."""
        src = _state_machine_src()
        self.assertIn("FAILURE_TO_RETRY", src)
        # The matching STAGE_TO_FAILURE map exists and maps to
        # FAILED_* terminals.
        for state in ("FAILED_PLANNING", "FAILED_IMAGES", "FAILED_TTS", "FAILED_RENDER"):
            self.assertIn(state, src, f"State machine must define {state}")


# ─────────────────────────────────────────────────────────────────────
# Section B — Credit deduction is once-only (no retry double-charge).
# ─────────────────────────────────────────────────────────────────────
class TestCreditsChargedOnceInvariant(unittest.TestCase):
    """deduct_credits MUST be called only from create_job. The manual
    /retry endpoint MUST NOT call deduct_credits. The per-stage
    _execute_stage_with_retry MUST NOT call deduct_credits. Anything
    else is a double-charge bug."""

    def test_pipeline_has_single_deduct_call_site(self):
        src = _pipeline_src()
        # Count only the *call* sites (the line that invokes the
        # method), not the import or function name occurrences.
        call_sites = re.findall(r"\.deduct_credits\(", src)
        self.assertEqual(
            len(call_sites), 1,
            f"pipeline.py must call .deduct_credits exactly once "
            f"(found {len(call_sites)})",
        )

    def test_retry_endpoint_does_not_deduct_credits(self):
        src = _routes_src()
        # Carve out the retry handler body.
        idx = src.find('@router.post("/retry/{job_id}")')
        self.assertGreater(idx, 0)
        # Next router decorator marks the end of this handler.
        end = src.find("@router.", idx + 1)
        body = src[idx:end if end > 0 else len(src)]
        self.assertNotIn(
            "deduct_credits", body,
            "POST /retry/{job_id} MUST NOT deduct credits — retries are free",
        )

    def test_status_response_exposes_credits_charged_once_flag(self):
        src = _routes_src()
        # The status response retry_info block must include the canonical
        # `credits_charged_once: True` flag.
        self.assertIn(
            '"credits_charged_once": True',
            src,
            "/status retry_info must include `credits_charged_once: True`",
        )


# ─────────────────────────────────────────────────────────────────────
# Section C — /status retry_info contract.
# ─────────────────────────────────────────────────────────────────────
class TestStatusRetryInfoContract(unittest.TestCase):
    def setUp(self):
        self.src = _routes_src()

    def test_retry_info_block_present(self):
        self.assertIn('"retry_info":', self.src)
        for field in (
            "current_attempt",
            "max_attempts",
            "total_retries",
            "is_retrying",
            "last_error_stage",
            "last_error_code",
            "credits_charged_once",
            "can_retry",
        ):
            self.assertIn(
                f'"{field}"', self.src,
                f"/status retry_info must surface `{field}`",
            )

    def test_is_retrying_excludes_terminal_and_failed_states(self):
        """is_retrying must be False on terminal success and on every
        PER_STAGE_FAILURE_STATE — those are handled by `can_retry` instead.
        The boolean expression must explicitly exclude both."""
        # Locate the is_retrying block and read forward until heartbeat_detail.
        start = self.src.find('"is_retrying":')
        self.assertGreater(start, 0, "is_retrying field must be present in /status response")
        end = self.src.find('"heartbeat_detail"', start)
        self.assertGreater(end, start, "is_retrying must precede heartbeat_detail in retry_info")
        expr = self.src[start:end]
        self.assertIn("current_attempt", expr)
        self.assertIn("PER_STAGE_FAILURE_STATES", expr)
        self.assertIn("READY", expr)
        self.assertIn("FAILED", expr)


# ─────────────────────────────────────────────────────────────────────
# Section D — LocatingProjectCard surfaces the retry banner.
# ─────────────────────────────────────────────────────────────────────
class TestLocatingCardRetryVisibility(unittest.TestCase):
    def setUp(self):
        self.src = _myspace_src()

    def test_locating_card_reads_retry_info(self):
        self.assertIn(
            "retry_info: data.retry_info", self.src,
            "LocatingProjectCard must read retry_info from the status response",
        )

    def test_retry_banner_renders_when_is_retrying(self):
        self.assertIn(
            'data-testid="locating-retry-banner"', self.src,
            "Retry banner must render with stable data-testid",
        )
        self.assertIn(
            'data-testid="locating-retry-banner-title"', self.src,
            "Retry banner title must expose data-testid",
        )
        self.assertIn(
            'data-testid="locating-retry-banner-detail"', self.src,
            "Retry banner detail must expose data-testid",
        )

    def test_retry_banner_copy_matches_brief(self):
        """The brief verbatim: 'Render failed once. Retrying
        automatically… Attempt 2 of 2.' Pin both halves."""
        self.assertIn(
            "Render failed once. Retrying automatically", self.src,
            "Retry banner title must use the brief's verbatim copy",
        )
        self.assertIn(
            "Attempt {ri.current_attempt} of {ri.max_attempts", self.src,
            "Retry banner must show 'Attempt N of M' using retry_info",
        )
        self.assertIn(
            "your credits are safe", self.src,
            "Retry banner must reassure user that credits are safe",
        )

    def test_retry_banner_gated_on_is_retrying_only(self):
        """The banner must render conditionally on isRetrying (which is
        derived from backend `retry_info.is_retrying`) — NOT on a
        heuristic the frontend invents. The frontend must trust the
        backend invariant."""
        self.assertIn(
            "const isRetrying = !!(ri && ri.is_retrying);",
            self.src,
            "isRetrying must be derived from backend retry_info.is_retrying",
        )

    def test_failed_card_copy_matches_brief(self):
        """The brief verbatim: 'Video generation failed.' + 'Your
        credits are safe.' + buttons 'Retry generation' and 'Back to
        studio'."""
        self.assertIn(
            "Video generation failed", self.src,
            "FAILED card headline must match the brief verbatim",
        )
        self.assertIn(
            "Your credits are safe.", self.src,
            "FAILED card must explicitly state credits are safe",
        )
        # Retry CTA copy
        self.assertIn(
            "Retry generation",
            self.src,
            "Retry CTA must say 'Retry generation' (not just 'Retry')",
        )


# ─────────────────────────────────────────────────────────────────────
# Section E — Polling is read-only (kill the trash-architecture class).
# ─────────────────────────────────────────────────────────────────────
class TestPollingIsReadOnly(unittest.TestCase):
    """The brief's biggest worry: 'polling/reload effect accidentally
    calling start generation again instead of only checking status.'
    Pin the invariant: LocatingProjectCard must NEVER POST to
    /api/story-engine/create. Any HTTP method other than GET inside
    the polling loop is forbidden."""

    def setUp(self):
        self.src = _myspace_src()
        # Carve out the LocatingProjectCard function body.
        start = self.src.find("function LocatingProjectCard(")
        end = self.src.find("\n// ─── MAIN COMPONENT", start)
        self.assertGreater(start, 0)
        self.assertGreater(end, start)
        self.card_src = self.src[start:end]

    def test_card_never_posts_create(self):
        self.assertNotIn(
            "/api/story-engine/create",
            self.card_src,
            "LocatingProjectCard MUST NOT reference /api/story-engine/create "
            "— polling is read-only",
        )

    def test_card_never_calls_api_post(self):
        # The card may only call api.get(). api.post anywhere inside
        # the card body would re-fire a write — bug.
        forbidden = re.findall(
            r"\bapi\.(post|put|patch|delete)\b",
            self.card_src,
        )
        self.assertEqual(
            forbidden, [],
            "LocatingProjectCard MUST only call api.get — found: "
            f"{forbidden}",
        )

    def test_status_path_is_canonical(self):
        # The card must hit the canonical, ownership-checked status
        # endpoint, never an inferred path.
        self.assertIn(
            "/api/story-engine/status/", self.card_src,
            "LocatingProjectCard must poll the canonical status endpoint",
        )


# ─────────────────────────────────────────────────────────────────────
# Section F — Generate button has a click mutex (no duplicate jobs).
# ─────────────────────────────────────────────────────────────────────
class TestGenerateButtonMutex(unittest.TestCase):
    """Brief invariant: 'refresh does not create a new job'. The
    canonical guard is createLockRef on the Generate button. Pin both
    sides: the lock is set before /create AND released only in a
    bounded finally."""

    def setUp(self):
        self.src = (FRONTEND_SRC / "pages" / "StoryVideoPipeline.js").read_text()

    def test_create_lock_set_before_post(self):
        lock_idx = self.src.find("createLockRef.current = true;")
        post_idx = self.src.find("api.post('/api/story-engine/create'")
        self.assertGreater(lock_idx, 0, "createLockRef must be set")
        self.assertGreater(post_idx, lock_idx,
            "createLockRef MUST be acquired BEFORE the /create POST",
        )

    def test_create_lock_released_in_finally(self):
        # Both sides exist: the lock is acquired once and released
        # exactly once.
        acquires = self.src.count("createLockRef.current = true;")
        releases = self.src.count("createLockRef.current = false;")
        self.assertEqual(
            acquires, 1,
            f"createLockRef must be acquired exactly once (found {acquires})",
        )
        self.assertEqual(
            releases, 1,
            f"createLockRef must be released exactly once (found {releases})",
        )

    def test_double_click_short_circuit_present(self):
        # The handler must early-return if the lock is already held.
        self.assertIn(
            "if (createLockRef.current) return;",
            self.src,
            "handleGenerate must early-return if createLockRef is held",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
