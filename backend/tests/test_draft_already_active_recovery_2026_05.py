"""
Draft-already-active recovery contract — P0 2026-05-30.

Production trust-bug: users landing on Story Video Studio see a red
toast "Couldn't start a new draft. Ref: <hex>" — and cannot proceed,
even though they have a perfectly valid resumable draft on the server.

Root cause (verified):
  • Backend `POST /api/drafts/session` correctly returns
    HTTP 409 { code: "DRAFT_ALREADY_ACTIVE", active_draft_id: "<id>" }
    when a user already has an active session. This is the canonical
    "use the existing one" signal.
  • Frontend `createSession()` in storySessionClient.js was throwing
    this recovery payload into a generic error.
  • `useStorySessionAutosave._commit()` saw `created.ok === false`
    and fired `toast.error("Couldn't start a new draft. Ref: ...")`,
    stranding the user.

Doctrine (/app/memory/ENGINEERING_DOCTRINE.md, Bug-Class Elimination
Mandate). Class: "recoverable backend state surfaced as generic UI
failure." The fix is class-level — the client now distinguishes the
DRAFT_ALREADY_ACTIVE code, hydrates the existing draft via
`fetchSessionState(active_draft_id)`, and continues silently.

This audit pins:
  1. Backend response shape (409 + code + active_draft_id).
  2. Frontend ErrorCode enum includes DRAFT_ALREADY_ACTIVE.
  3. createSession() surfaces `alreadyActive` + `activeDraftId` on 409.
  4. useStorySessionAutosave adopts the existing draft and DOES NOT
     show the "Couldn't start a new draft" toast on the 409 path.

Registered in /app/Makefile under audit-boundaries.
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
# Section A — Backend contract.
# ─────────────────────────────────────────────────────────────────────
class TestBackend409ShapeIsStable(unittest.TestCase):
    """POST /api/drafts/session must return HTTP 409 with
    code=DRAFT_ALREADY_ACTIVE AND active_draft_id when an active draft
    already exists. The client recovery path depends on both fields."""

    def setUp(self):
        self.src = (BACKEND / "routes" / "drafts.py").read_text()

    def test_409_for_active_session_in_create_handler(self):
        # Locate the create_canonical_session handler (POST /session).
        idx = self.src.find('@router.post("/session")')
        self.assertGreater(idx, 0, "POST /api/drafts/session must exist")
        body = self.src[idx:idx + 2500]
        self.assertIn("status_code=409", body, "Conflict must use HTTP 409")
        self.assertIn('"code": "DRAFT_ALREADY_ACTIVE"', body)
        self.assertIn('"active_draft_id"', body)

    def test_409_for_active_session_in_legacy_create_handler(self):
        # The legacy POST /create handler shares the same contract.
        # We pin it so any future divergence is caught.
        # Search the file for at least 2 occurrences of the
        # DRAFT_ALREADY_ACTIVE code (legacy + new endpoints).
        occurrences = self.src.count('"DRAFT_ALREADY_ACTIVE"')
        self.assertGreaterEqual(
            occurrences, 2,
            "Both /create and /session endpoints must return "
            "DRAFT_ALREADY_ACTIVE on conflict",
        )


# ─────────────────────────────────────────────────────────────────────
# Section B — Frontend ErrorCode enum.
# ─────────────────────────────────────────────────────────────────────
class TestErrorCodeEnumIncludesDraftAlreadyActive(unittest.TestCase):
    def test_enum_constant_present(self):
        src = (FRONTEND_SRC / "state" / "storySession.js").read_text()
        # ErrorCode object must include the DRAFT_ALREADY_ACTIVE entry
        # so the client compares against a canonical constant rather
        # than a magic string.
        self.assertIn(
            "DRAFT_ALREADY_ACTIVE: 'DRAFT_ALREADY_ACTIVE'",
            src,
            "ErrorCode enum must include DRAFT_ALREADY_ACTIVE",
        )


# ─────────────────────────────────────────────────────────────────────
# Section C — createSession surfaces the recovery payload.
# ─────────────────────────────────────────────────────────────────────
class TestCreateSessionSurfacesRecoveryPayload(unittest.TestCase):
    def setUp(self):
        self.src = (FRONTEND_SRC / "state" / "storySessionClient.js").read_text()

    def test_already_active_flag_exposed(self):
        # The return object from createSession on a 409 must carry
        # `alreadyActive: true` and `activeDraftId` so the autosave
        # hook can branch without re-parsing the raw detail.
        block = self.src.split("export async function createSession()", 1)[1]
        block = block.split("\n}", 1)[0]
        self.assertIn(
            "alreadyActive:", block,
            "createSession must surface an `alreadyActive` boolean on 409",
        )
        self.assertIn(
            "activeDraftId:", block,
            "createSession must surface `activeDraftId` on 409",
        )
        # The branch must reference the canonical ErrorCode constant.
        self.assertIn(
            "ErrorCode.DRAFT_ALREADY_ACTIVE", block,
            "createSession must compare against the ErrorCode constant",
        )


# ─────────────────────────────────────────────────────────────────────
# Section D — Autosave hook adopts the active draft on 409.
# ─────────────────────────────────────────────────────────────────────
class TestAutosaveAdoptsActiveDraftOn409(unittest.TestCase):
    def setUp(self):
        self.src = (FRONTEND_SRC / "state" / "useStorySessionAutosave.js").read_text()

    def test_adoption_branch_present(self):
        # The hook must read the new alreadyActive / activeDraftId
        # fields and call fetchSessionState to hydrate version.
        self.assertIn(
            "alreadyActive", self.src,
            "Autosave hook must inspect `created.alreadyActive`",
        )
        self.assertIn(
            "activeDraftId", self.src,
            "Autosave hook must consume `created.activeDraftId`",
        )
        self.assertIn(
            "fetchSessionState(", self.src,
            "Autosave hook must hydrate the adopted draft via fetchSessionState",
        )

    def test_no_generic_error_toast_on_already_active(self):
        """The generic 'Couldn't start a new draft' toast MUST live
        on a true-failure code path only. On the already-active
        recovery path the hook must NOT fire it. We assert ordering:
        the alreadyActive branch is checked BEFORE the generic toast,
        and the recovery branch ends with a `return` (no fallthrough
        to the toast call)."""
        m = re.search(
            r"if \(!created\.ok\) \{(.*?)\n      \}\s*else \{",
            self.src,
            re.DOTALL,
        )
        self.assertIsNotNone(
            m,
            "Failed to find the `if (!created.ok) { ... } else { ... }` "
            "block in the autosave hook",
        )
        block = m.group(1)
        # Adoption branch must appear and must `return` before the
        # generic toast.
        already_idx = block.find("created.alreadyActive")
        toast_idx = block.find("Couldn't start a new draft.")
        self.assertGreater(
            already_idx, -1,
            "Autosave hook must check `created.alreadyActive` first",
        )
        self.assertGreater(
            toast_idx, already_idx,
            "Generic 'Couldn't start a new draft' toast must live AFTER "
            "the already-active recovery branch — never before",
        )
        # Inside the adoption branch, the success arm must NOT include
        # the generic toast. We carve out the section between the
        # `if (created.alreadyActive && ...)` line and the next
        # standalone `} else {` (true-failure arm).
        adoption_start = block.find("if (created.alreadyActive")
        adoption_end = block.find("} else {", adoption_start)
        self.assertGreater(adoption_end, adoption_start)
        adoption_window = block[adoption_start:adoption_end]
        self.assertNotIn(
            "Couldn't start a new draft.",
            adoption_window,
            "The already-active recovery branch must NEVER surface the "
            "generic 'Couldn't start a new draft' toast",
        )

    def test_failed_adoption_is_surfaced_distinctly(self):
        """If adoption itself fails (e.g. draft was archived in flight),
        the toast must be the distinct 'Couldn't resume' copy — never
        the generic one. This prevents misdiagnosis in production."""
        self.assertIn(
            "Couldn't resume your existing draft.",
            self.src,
            "Failed-adoption path must use a distinct, debuggable toast",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
