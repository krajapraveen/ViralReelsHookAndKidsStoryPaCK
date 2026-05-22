"""
Empty-MySpace-after-Generate-Video bug-class elimination — P0 2026-05-24.

Production trust-bug: user clicks "Generate Video" → app navigates to
My Space → My Space renders "No projects yet". The user took action and
the product pretends nothing happened. Worse than ugly UI.

Doctrine (/app/memory/ENGINEERING_DOCTRINE.md, Bug-Class Elimination
Mandate). Class: "successful action → empty state UI" — three
independent boundaries that all needed gating:

  1. Frontend navigation contract: navigate() must be gated on a
     non-empty job_id. A success=true response with no id was being
     accepted and the URL was being formed as ?projectId=undefined.
  2. MySpace empty-state contract: rendering "No projects yet" when
     ?projectId=<id> is in the URL is a lie. The user JUST created a
     project. Cover the race / user_id-shape mismatch / auth hiccup
     paths by falling back to a status probe.
  3. Backend create endpoint: the response shape MUST include job_id
     on success — pinned so a future refactor can't drop it silently.

This audit pins all three contracts statically and is registered in
/app/Makefile under audit-boundaries.
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


# ─────────────────────────────────────────────────────────────────────
# Section A — Frontend navigation contract (StoryVideoPipeline.js)
# ─────────────────────────────────────────────────────────────────────
class TestGenerateVideoNavigationContract(unittest.TestCase):
    """The Generate Video success path must NEVER navigate to MySpace
    with a missing/empty job_id. A success response without a job_id is
    a backend bug, but the frontend must refuse to silently dump the
    user onto an empty page."""

    def setUp(self):
        self.studio = (FRONTEND_SRC / "pages" / "StoryVideoPipeline.js").read_text()

    def test_create_response_logs_forensics(self):
        """A structured log line MUST be emitted on every create
        response so production forensics can correlate `success` /
        `has_job_id` / `is_guest` without depending on user reports."""
        self.assertIn(
            "'[generate_video] response'", self.studio,
            "Generate Video must emit a structured response log for forensics",
        )
        self.assertIn(
            "has_job_id", self.studio,
            "Forensic log must include has_job_id boolean",
        )

    def test_navigation_gated_on_job_id(self):
        """The success → navigate path MUST refuse to proceed when
        res.data.job_id is falsy."""
        # Pattern: the absence-guard branch appears BEFORE the success-
        # branch that constructs the my-space URL with res.data.job_id.
        guard_idx = self.studio.find("res.data.success && !res.data.job_id")
        nav_idx = self.studio.find("/app/my-space?projectId=${res.data.job_id}")
        self.assertGreater(
            guard_idx, 0,
            "StoryVideoPipeline.js must guard against missing job_id "
            "(`res.data.success && !res.data.job_id`)",
        )
        self.assertGreater(
            nav_idx, 0,
            "The MySpace deep-link is the canonical post-create destination",
        )
        self.assertLess(
            guard_idx, nav_idx,
            "Missing-job_id guard MUST execute BEFORE the navigate call",
        )

    def test_missing_id_blocks_navigation_and_surfaces_error(self):
        """When job_id is missing, the user must see an error toast/
        form-error AND remain on the create page (return without nav)."""
        # The guard block must include a `return;` AND surface a
        # user-visible error (toast or setFormError).
        block_start = self.studio.find("res.data.success && !res.data.job_id")
        block_window = self.studio[block_start:block_start + 1200]
        self.assertIn(
            "return;", block_window,
            "Missing-id branch must early-return so navigate() never fires",
        )
        self.assertTrue(
            ("toast.error" in block_window) or ("setFormError" in block_window),
            "Missing-id branch must surface a user-visible error",
        )


# ─────────────────────────────────────────────────────────────────────
# Section B — MySpace empty-state invariant (MySpacePage.js)
# ─────────────────────────────────────────────────────────────────────
class TestMySpaceNeverEmptyAfterCreate(unittest.TestCase):
    """When MySpace mounts with ?projectId=<id> the user just clicked
    Generate Video. Rendering "No projects yet" in that moment is a
    trust-breaking lie. The component MUST detour to a "locating"
    fallback that probes the canonical status endpoint."""

    def setUp(self):
        self.myspace = (FRONTEND_SRC / "pages" / "MySpacePage.js").read_text()

    def test_locating_card_exists(self):
        self.assertIn(
            "function LocatingProjectCard(", self.myspace,
            "MySpace must define LocatingProjectCard for the post-create fallback",
        )
        self.assertIn(
            "data-testid=\"myspace-locating\"", self.myspace,
            "LocatingProjectCard must expose a stable data-testid for e2e",
        )

    def test_empty_state_short_circuit_when_project_id_present(self):
        """The empty-state branch MUST be guarded by
        `jobs.length === 0 && highlightId` and render LocatingProjectCard,
        executed BEFORE the unconditional "No projects yet" empty state."""
        guard_idx = self.myspace.find("jobs.length === 0 && highlightId")
        empty_idx = self.myspace.find("data-testid=\"myspace-empty\"")
        self.assertGreater(
            guard_idx, 0,
            "MySpace must detect the post-create case (`jobs.length===0 && highlightId`)",
        )
        self.assertGreater(empty_idx, 0, "myspace-empty data-testid expected")
        self.assertLess(
            guard_idx, empty_idx,
            "post-create guard MUST execute BEFORE the No-projects-yet render",
        )
        # And the guard branch must return the LocatingProjectCard.
        guard_window = self.myspace[guard_idx:empty_idx]
        self.assertIn(
            "LocatingProjectCard", guard_window,
            "post-create empty case must render LocatingProjectCard, NOT myspace-empty",
        )

    def test_locating_card_probes_canonical_status_endpoint(self):
        """The fallback card must hit /api/story-engine/status/<id> — the
        canonical ownership-checked status endpoint."""
        card_start = self.myspace.find("function LocatingProjectCard(")
        card_window = self.myspace[card_start:card_start + 6000]
        self.assertIn(
            "/api/story-engine/status/", card_window,
            "LocatingProjectCard must probe /api/story-engine/status/<id>",
        )
        # Must handle 404 escalation (job genuinely never recorded).
        self.assertIn(
            "404", card_window,
            "LocatingProjectCard must handle 404 distinctly from transient errors",
        )

    def test_pending_processing_jobs_are_visible_in_myspace(self):
        """The MySpace normalizer must keep PENDING / PROCESSING / QUEUED
        jobs in the visible set (not filtered out, not bucketed into
        ARCHIVED). A user's brand-new job is always PENDING/PROCESSING."""
        # The allow-list constants pin this contract.
        m = re.search(
            r"__ALLOWED_LIVE\s*=\s*new\s+Set\(\[([^\]]+)\]\)",
            self.myspace,
        )
        self.assertIsNotNone(m, "__ALLOWED_LIVE must be defined as a Set literal")
        live = m.group(1)
        for required in ("'PENDING'", "'PROCESSING'", "'QUEUED'"):
            self.assertIn(
                required, live,
                f"__ALLOWED_LIVE must include {required} so brand-new jobs render",
            )


# ─────────────────────────────────────────────────────────────────────
# Section C — Backend create endpoint contract
# ─────────────────────────────────────────────────────────────────────
class TestStoryEngineCreateResponseShape(unittest.TestCase):
    """Pin the create-endpoint response shape. job_id MUST be in the
    response on every success path; a future refactor that drops it
    would silently re-introduce the empty-MySpace bug for every user."""

    def setUp(self):
        self.src = (BACKEND / "routes" / "story_engine_routes.py").read_text()

    def test_create_response_includes_job_id(self):
        # The response dict in create_engine_job MUST include job_id.
        # Look for the response literal.
        m = re.search(
            r"response\s*=\s*\{[^}]*\"job_id\"\s*:\s*job_id",
            self.src,
            re.DOTALL,
        )
        self.assertIsNotNone(
            m,
            "POST /api/story-engine/create response must include `job_id`",
        )

    def test_user_jobs_does_not_filter_out_pending_processing(self):
        """The /user-jobs aggregator MUST NOT apply a status filter that
        excludes PENDING / PROCESSING / QUEUED. Newly created jobs must
        be visible to the very next MySpace fetch."""
        # Find the legacy cursor block which uses {"user_id":..., "status": {"$nin":[...]}}
        m = re.search(
            r'db\.pipeline_jobs\.find\(\s*\{\s*"user_id"\s*:\s*user_id\s*,\s*"status"\s*:\s*\{\s*"\$nin"\s*:\s*\[([^\]]*)\]',
            self.src,
        )
        self.assertIsNotNone(m, "user-jobs legacy aggregator pattern not found")
        nin = m.group(1).upper()
        for forbidden in ("PENDING", "PROCESSING", "QUEUED"):
            self.assertNotIn(
                forbidden, nin,
                f"user-jobs MUST NOT exclude {forbidden} — brand-new jobs would vanish",
            )

    def test_credits_deducted_only_on_successful_creation(self):
        """The create endpoint must NOT deduct credits when job creation
        fails. The flow is: create_job() returns {success: bool}; if
        success=False the helper raises HTTPException — no
        deduct_credits side-effect on the failure branch."""
        # We assert that the failure branch (`if not result.get("success")`)
        # appears BEFORE any post-creation credit/state mutation and
        # raises rather than continuing.
        idx = self.src.find('if not result.get("success"):')
        self.assertGreater(
            idx, 0,
            "create_engine_job must check result['success'] explicitly",
        )
        failure_window = self.src[idx:idx + 800]
        self.assertIn(
            "raise HTTPException", failure_window,
            "Failed create MUST raise — never fall through to job_id/credit code",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
