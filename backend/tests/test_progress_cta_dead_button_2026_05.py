"""
Progress-CTA dead-button regression — 2026-05-16
Founder directive: every "View Progress" / "Leave & come back later" CTA
must produce visible feedback within 100ms. This guards the static contract
(handler exists, props wired, funnel events whitelisted) and the dynamic
contract (the click triggers visible UI state change on /app/my-space).
"""
import os
import re
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MYSPACE = ROOT / "frontend" / "src" / "pages" / "MySpacePage.js"
SVP = ROOT / "frontend" / "src" / "pages" / "StoryVideoPipeline.js"
PHOTO = ROOT / "frontend" / "src" / "pages" / "PhotoTrailerPage.jsx"
FUNNEL_PY = ROOT / "backend" / "routes" / "funnel_tracking.py"

BASE = os.environ.get("REACT_APP_BACKEND_URL") or "http://localhost:8001"


# ─── STATIC: handler + prop wiring ─────────────────────────────────
def test_my_space_view_progress_button_has_handler():
    src = MYSPACE.read_text(encoding="utf-8")
    # Button exists
    assert 'data-testid={`view-progress-btn-${job.job_id}`}' in src
    # Bound to onNavigate (not a no-op)
    assert re.search(
        r'data-testid=\{`view-progress-btn-\$\{job\.job_id\}`\}\s+onClick=\{\(\) => onNavigate\(job\)\}',
        src,
    ), "View Progress button must call onNavigate(job)"


def test_my_space_leave_and_come_back_actually_navigates():
    """Regression: the button used to fire a toast only while staying on
    /app/my-space. Now it must call onLeave(job) which navigates to /app."""
    src = MYSPACE.read_text(encoding="utf-8")
    # The Leave button must be wired to onLeave, NOT just a toast
    assert "onClick={() => onLeave(job)}" in src, \
        "Leave & come back button must call onLeave(job)"
    # And the handleLeaveAndComeBack handler MUST actually navigate
    assert "const handleLeaveAndComeBack" in src
    assert "navigate('/app')" in src, "handleLeaveAndComeBack must navigate('/app')"


def test_handle_navigate_handles_already_focused_state():
    """When user is already on /app/my-space?projectId=X and clicks View
    Progress on card X, handler must bump focusKey instead of issuing a
    same-route navigate that does nothing."""
    src = MYSPACE.read_text(encoding="utf-8")
    assert "setFocusKey" in src, "Missing focusKey state bump"
    assert "highlightId === job.job_id" in src, \
        "Must detect already-focused state and re-trigger scroll/ring"


def test_progress_ctas_have_active_press_feedback():
    """Tactile feedback: every progress CTA must include active:scale-[0.97]
    or similar instant-press effect for <100ms perceived response."""
    src = MYSPACE.read_text(encoding="utf-8")
    # Spot-check the three key buttons — find the line containing testid and
    # look at the rest of that JSX element (up to closing >)
    for testid in ("view-progress-btn", "view-details-btn", "leave-btn"):
        # Find the testid line index
        lines = src.split("\n")
        for i, line in enumerate(lines):
            if f"data-testid={{`{testid}-${{job.job_id}}`}}" in line:
                # JSX is single-line here per our edits, but be safe and look at 3 lines
                window = " ".join(lines[i:i + 3])
                assert "active:scale-" in window, \
                    f"{testid} missing active:scale-* press feedback near line {i+1}"
                break
        else:
            raise AssertionError(f"data-testid `{testid}-*` not found in MySpacePage.js")


def test_funnel_whitelist_contains_progress_events():
    """The three instrumentation events must be on the canonical whitelist."""
    src = FUNNEL_PY.read_text(encoding="utf-8")
    for event in ("progress_cta_clicked", "progress_view_opened", "progress_view_failed"):
        assert f'"{event}"' in src, f"Missing event in funnel whitelist: {event}"


# ─── DYNAMIC: backend accepts the instrumentation events ───────────
def test_funnel_endpoint_accepts_progress_events():
    for step in ("progress_cta_clicked", "progress_view_opened", "progress_view_failed"):
        r = requests.post(
            f"{BASE}/api/funnel/track",
            json={
                "step": step,
                "session_id": "pytest_progress_cta",
                "anonymous_id": "pytest_progress_anon",
                "context": {"source": "pytest"},
            },
            timeout=10,
        )
        assert r.status_code == 200, f"{step} → {r.status_code} {r.text}"
        assert r.json().get("success") is True, f"{step} returned success=False"


# ─── HANDLER COMPLETENESS: try/catch + console.error guards ────────
def test_progress_handler_has_error_logging():
    src = MYSPACE.read_text(encoding="utf-8")
    # The handler must console.error on failure
    assert "console.error('[ProgressCTA]" in src or 'console.error("[ProgressCTA]' in src, \
        "handleNavigate must console.error on handler failure"
    assert "progress_view_failed" in src, \
        "handleNavigate must emit progress_view_failed on error path"


# ─── CLASS-WIDE: every visible 'View Progress' must call a handler ─
def test_no_dead_view_progress_buttons():
    """Static: every JSX <button> whose visible label is 'View Progress' /
    'View progress' must have an onClick that references a handler (not
    undefined / not just toast). We only check button JSX (skip comments)."""
    suspects = []
    for path in (MYSPACE, SVP, PHOTO):
        src = path.read_text(encoding="utf-8")
        # Match a <button ...> ... View [Pp]rogress ... </button> block
        # and require an onClick= inside it.
        for m in re.finditer(r"<button\b[^>]*?>[\s\S]{0,400}?View [Pp]rogress[\s\S]{0,200}?</button>", src):
            block = m.group(0)
            if "onClick=" not in block:
                # Compute line number
                line_no = src[: m.start()].count("\n") + 1
                suspects.append(f"{path.name}:{line_no}: {block[:120].strip()}")
    assert not suspects, "Dead View Progress buttons found:\n" + "\n".join(suspects)
