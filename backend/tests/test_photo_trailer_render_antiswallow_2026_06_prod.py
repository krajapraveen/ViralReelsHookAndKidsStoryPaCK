"""P0 2026-06-PROD-FOLLOWUP — Render-pipeline anti-swallow.

Production diagnostic regression (krajapraveen@gmail.com, third strike):

    {
      "error_code": "RENDER_FAIL",
      "failure_stage": "RENDERING_TRAILER",
      "failure_reason": "Final render hit a hiccup. Please retry.",
      "retry_count": 0
    }

The previous diagnostic system exposed `ffmpeg_exit_code`,
`ffmpeg_stderr_tail`, `render_validation_reason`, etc. — but the generic
`except Exception:` at the end of the render branch was silently
swallowing the underlying exception and replacing it with the friendly
"hiccup" string. Operator could not triage without re-running the job
locally.

Bug-class fix: the catch-all MUST persist:
  • render_exception_class
  • render_exception_message
  • render_traceback_tail
  • render_failure_kind = "uncaught_exception"
  • provider_error (so legacy admin probes still surface the cause)

…onto the job doc BEFORE calling _fail(). The user-facing error_message
MUST include the exception class so the FailedStep UI shows "Final
render failed (ValueError: bad cmd) — credits refunded — please retry."
instead of the generic hiccup line.

These tests are the bug-class pin. Any future PR that re-introduces a
silent generic catch (or strips the exception class from the message)
will fail the audit.

Registered under `make audit-boundaries`.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

REPO = Path("/app")
BACKEND = REPO / "backend"
FRONTEND = REPO / "frontend"
sys.path.insert(0, str(BACKEND))

PHOTO_TRAILER_PY = BACKEND / "routes" / "photo_trailer.py"
PHOTO_TRAILER_JSX = FRONTEND / "src" / "pages" / "PhotoTrailerPage.jsx"


# ─────────────────────────────────────────────────────────────────────
# Section A — Backend: the generic catch-all MUST persist diagnostics.
# ─────────────────────────────────────────────────────────────────────
class TestRenderPipelineCatchAllPersistsDiagnostics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = PHOTO_TRAILER_PY.read_text()
        m = re.search(
            r"async def _run_pipeline_inner\([^)]*\)[^:]*:(?P<body>.+?)(?=\nasync def |\ndef )",
            cls.src, re.S,
        )
        assert m, "_run_pipeline_inner() must exist"
        cls.body = m.group("body")

    def test_no_generic_swallow_with_hiccup_message(self):
        """The string `Final render hit a hiccup` MUST NOT survive in the
        pipeline body — it was the swallow signature."""
        self.assertNotIn(
            "Final render hit a hiccup",
            self.body,
            "The generic 'hiccup' fallback message swallowed real ffmpeg "
            "errors in production. It MUST be replaced with a message "
            "that includes the underlying exception class.",
        )

    def test_uncaught_exception_branch_captures_class_and_message(self):
        """The catch-all in the render branch MUST capture the exception
        class + message into named locals so they can be persisted."""
        # Find the except Exception block that handles render failures.
        # We expect a `type(exc).__name__` capture and a str(exc) slice.
        # Search inside the pipeline body only (avoid false positives in
        # unrelated helpers).
        render_except = re.search(
            r"except Exception as exc:\s*"
            r"(?P<block>(?:.+?\n){5,80}?)\s*return await _fail\(",
            self.body, re.S,
        )
        self.assertIsNotNone(
            render_except,
            "An `except Exception as exc:` block with a `_fail(...)` call "
            "must exist in the render pipeline.",
        )
        block = render_except.group("block")
        self.assertIn(
            "type(exc).__name__", block,
            "The catch-all must capture the exception CLASS NAME so the "
            "admin endpoint can surface it.",
        )
        self.assertIn(
            "format_exc", block,
            "The catch-all must capture the traceback tail.",
        )

    def test_uncaught_exception_persists_to_job_doc(self):
        """All five diagnostic fields must be written to the job doc
        inside the except block, BEFORE the _fail() call."""
        # Locate the catch-all and the next _fail call.
        idx = self.body.find("except Exception as exc:")
        self.assertGreater(idx, 0)
        # Look forward only until the next `return await _fail`.
        tail = self.body[idx:]
        next_fail = tail.find("return await _fail(")
        self.assertGreater(next_fail, 0)
        block = tail[:next_fail]
        for field in (
            "render_exception_class",
            "render_exception_message",
            "render_traceback_tail",
            "render_failure_kind",
            "provider_error",
        ):
            self.assertIn(
                field, block,
                f"Catch-all must persist `{field}` on the job doc before "
                f"calling _fail.",
            )
        self.assertIn(
            '"uncaught_exception"', block,
            "render_failure_kind must be set to 'uncaught_exception' so "
            "ops can distinguish it from ffmpeg_subprocess / asyncio_wait_for_timeout.",
        )

    def test_user_facing_message_includes_exception_class(self):
        """The _fail() call inside the catch-all must pass a message that
        includes the exception CLASS and a slice of its message — never
        a generic placeholder. Otherwise the FailedStep UI again hides
        the real error."""
        idx = self.body.find("except Exception as exc:")
        tail = self.body[idx:]
        next_fail_end = tail.find(")\n", tail.find("return await _fail("))
        self.assertGreater(next_fail_end, 0)
        call = tail[:next_fail_end + 1]
        # The message string must reference the captured exc_class variable.
        self.assertIn(
            "exc_class", call,
            "Catch-all _fail() message must include {exc_class} so the "
            "user-visible error contains the exception type.",
        )
        # Defensive: make sure the legacy "hiccup" string isn't here either.
        self.assertNotIn("hit a hiccup", call)


# ─────────────────────────────────────────────────────────────────────
# Section B — _fail's user-facing message composition preserves the
# caller's diagnostic msg for the DIAGNOSTIC_CODES set, even when a
# refund is confirmed.
# ─────────────────────────────────────────────────────────────────────
class TestFailMessageDoesNotStripDiagnostics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = PHOTO_TRAILER_PY.read_text()
        m = re.search(
            r"async def _fail\([^)]*\)[^:]*:(?P<body>.+?)(?=\nasync def |\ndef )",
            cls.src, re.S,
        )
        assert m, "_fail() must exist"
        cls.body = m.group("body")

    def test_diagnostic_codes_set_is_declared(self):
        self.assertIn(
            "DIAGNOSTIC_CODES", self.body,
            "_fail must declare a DIAGNOSTIC_CODES set listing the error "
            "codes that carry triage info in their `msg` argument.",
        )
        for code in ("RENDER_FAIL", "RENDER_INVALID", "RENDER_TIMEOUT",
                     "TTS_EMPTY", "IMAGE_GEN_FAIL", "UPLOAD_FAIL"):
            self.assertIn(
                f'"{code}"', self.body,
                f"DIAGNOSTIC_CODES must include {code} so the caller's "
                f"msg is surfaced verbatim.",
            )

    def test_diagnostic_msg_preserved_on_refund_path(self):
        """When refund_issued + code in DIAGNOSTIC_CODES, the user_facing
        message must NOT be replaced with the generic 'credits refunded'
        line — the caller's msg already includes the refund clause."""
        # The branch must reference is_diagnostic and use {msg}.
        self.assertIn("is_diagnostic = code in DIAGNOSTIC_CODES", self.body)
        # Find the refund-issued branch.
        m = re.search(
            r"if refund_issued and refund_amount > 0:\s*"
            r"(?P<branch>(?:.+?\n){2,8}?)\s*elif charged > 0",
            self.body, re.S,
        )
        self.assertIsNotNone(m, "refund_issued branch must exist")
        branch = m.group("branch")
        self.assertIn(
            "is_diagnostic", branch,
            "Refund-issued branch must check is_diagnostic so the "
            "caller's diagnostic msg is preserved.",
        )


# ─────────────────────────────────────────────────────────────────────
# Section C — Admin endpoint surfaces the new exception fields.
# ─────────────────────────────────────────────────────────────────────
class TestAdminEndpointSurfacesExceptionFields(unittest.TestCase):
    def test_admin_endpoint_returns_exception_fields(self):
        src = PHOTO_TRAILER_PY.read_text()
        m = re.search(
            r"async def admin_trailer_job_summary\([^)]*\)[^:]*:(?P<body>.+?)\n    return \{(?P<ret>[^}]+)\}",
            src, re.S,
        )
        self.assertIsNotNone(m)
        ret = m.group("ret")
        for field in (
            "render_exception_class",
            "render_exception_message",
            "render_traceback_tail",
        ):
            self.assertIn(
                f'"{field}"', ret,
                f"/admin/trailer-jobs/<id> must surface `{field}` so the "
                f"swallowed exception class is recoverable from one curl.",
            )

    def test_admin_failure_reason_includes_exception_class(self):
        """The composed failure_reason string must include the exception
        class when present, so a single field gives ops the full triage."""
        src = PHOTO_TRAILER_PY.read_text()
        m = re.search(
            r"async def admin_trailer_job_summary\([^)]*\)[^:]*:(?P<body>.+?)\n    return \{",
            src, re.S,
        )
        self.assertIsNotNone(m)
        body = m.group("body")
        self.assertIn("render_exception_class", body)
        # Must be appended to `parts` so it lands in failure_reason.
        self.assertIn('"exception="', body)
        # ffmpeg_exit may be composed via f-string — check for the prefix.
        self.assertIn('ffmpeg_exit=', body)


# ─────────────────────────────────────────────────────────────────────
# Section D — Frontend FailedStep surfaces the new fields and always
# renders the Details row when ANY diagnostic field is populated.
# ─────────────────────────────────────────────────────────────────────
class TestFailedStepUIPropagatesUncaughtException(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = PHOTO_TRAILER_JSX.read_text()

    def test_failed_step_reads_render_exception_class(self):
        self.assertIn(
            "render_exception_class", self.src,
            "FailedStep must read `render_exception_class` from the job "
            "doc so the underlying error type is visible.",
        )
        self.assertIn(
            "render_exception_message", self.src,
            "FailedStep must read `render_exception_message`.",
        )

    def test_failed_step_includes_exception_in_details(self):
        """The Details row composition must include the exception class."""
        # Look for the detailParts array.
        m = re.search(r"const detailParts = \[(?P<arr>.+?)\];", self.src, re.S)
        self.assertIsNotNone(m, "detailParts composition must exist")
        arr = m.group("arr")
        self.assertIn(
            "render_exception_class", arr,
            "detailParts must include the exception class so the UI "
            "never displays just a generic message.",
        )
        self.assertIn(
            "ffmpeg_exit_code", arr,
            "detailParts must include ffmpeg_exit_code when present.",
        )

    def test_failed_step_no_hide_when_matches_error_message(self):
        """The legacy `failure_reason !== job.error_message` short-circuit
        used to HIDE the Details row when the composed reason equalled the
        error_message — exactly the production case where both were the
        generic "hit a hiccup" string. Must not return."""
        self.assertNotIn(
            "!== job.error_message",
            self.src,
            "FailedStep MUST NOT short-circuit Details when reason equals "
            "error_message — that was the diagnostic-hiding bug.",
        )

    def test_diagnostic_clipboard_payload_carries_traceback(self):
        """The Copy-diagnostic clipboard payload must carry the full
        traceback tail so the user can paste it into a support ticket."""
        self.assertIn(
            "render_traceback_tail", self.src,
            "Clipboard payload must include render_traceback_tail.",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
