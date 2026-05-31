"""P0 2026-06 — Long-running message copy pin.

User-mandated exact wording for the MyTrailer "this is taking a while" copy.
Both surfaces (the amber "still working" card AND the violet "leave card")
must reference BOTH My Space and My Jobs so users know where to find their
work-in-progress regardless of which surface they prefer.

Pinned in: /app/Makefile (BOUNDARY_AUDIT_SUITES)
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRAILER_PAGE = ROOT / "frontend" / "src" / "pages" / "PhotoTrailerPage.jsx"

# Exact user-supplied wording — the source of truth for both surfaces.
REQUIRED_PATH_WORDING = "Profile → My Space or Profile → My Jobs"


def test_still_working_card_uses_canonical_path_wording():
    """The amber 'this is taking longer than usual' card must point users
    to both My Space and My Jobs (user mandate Feb 2026)."""
    src = TRAILER_PAGE.read_text()
    assert REQUIRED_PATH_WORDING in src, (
        f"Long-running surfaces must use '{REQUIRED_PATH_WORDING}' verbatim."
    )
    # The legacy "MySpace either way" wording must be gone — it tested poorly
    # and forced users to guess which surface their trailer landed on.
    assert "MySpace either way" not in src, (
        "Legacy 'MySpace either way' wording must be removed."
    )


def test_leave_card_uses_canonical_path_wording():
    """The violet 'you can leave this page' card must use the same wording.
    Two surfaces, one message — no user should see conflicting paths."""
    src = TRAILER_PAGE.read_text()
    # The leave card lives in a separate JSX block; this assertion is the
    # same string but proves both sites were updated together.
    occurrences = src.count(REQUIRED_PATH_WORDING)
    assert occurrences >= 2, (
        f"Both long-running surfaces (still-working card + leave card) "
        f"must use '{REQUIRED_PATH_WORDING}' — found {occurrences} occurrence(s)."
    )
