"""
Reel Engine reward-loop reliability — 2026-05-16 P0

User mandate:
  • After generation completes, user MUST stay on the same page and see the
    Generated Output panel — no auto-redirect.
  • If token expires mid-generation, defer the 401 redirect until the
    result has been displayed.
  • Persist the latest result to sessionStorage so an accidental refresh
    or auth churn cannot destroy the reward moment.
  • Emit reel_generation_started / _completed / _result_viewed funnel
    events for the completion→viewed conversion ratio.
  • Guard against polling/re-render duplicate display side effects via an
    alreadyDisplayedResult ref.

This regression suite is source-level (cheap, deterministic, environment-
independent) — it locks the behaviors in place so future refactors of
ReelGenerator.js / api.js / generationLifecycle.js can't silently regress
the activation moment again.
"""
from pathlib import Path
import re

REEL = Path("/app/frontend/src/pages/ReelGenerator.js")
API = Path("/app/frontend/src/utils/api.js")
LIFECYCLE = Path("/app/frontend/src/utils/generationLifecycle.js")


# ─── 1. NO auto-redirect after generation success ────────────────────────────
def test_handle_submit_does_not_navigate_after_success():
    """`handleSubmit` must NOT call navigate/window.location/history.push
    in its success path. Failure messaging is via toast.error only."""
    src = REEL.read_text(encoding="utf-8")
    m = re.search(
        r"const handleSubmit = async \(e\) =>\s*\{(.*?)\n  \};",
        src,
        re.S,
    )
    assert m, "handleSubmit not found in ReelGenerator.js"
    body = m.group(0)
    # The only window.location/navigate call inside handleSubmit must be
    # the DEFERRED-401 flush (gated by hasPendingLogin()). No raw redirect.
    # Strip the pending-login flush block before scanning.
    body_without_flush = re.sub(
        r"if \(hasPendingLogin\(\)\) \{.*?\n      \}",
        "",
        body,
        flags=re.S,
    )
    for needle in ("navigate(", "history.push", "router.push"):
        assert needle not in body_without_flush, \
            f"handleSubmit must not call {needle} — kills the reward moment"
    # window.location.href assignments are ONLY allowed inside the
    # consumePendingLogin() block we just stripped.
    assert "window.location.href" not in body_without_flush, \
        "handleSubmit must not perform a raw window.location redirect"


# ─── 2. alreadyDisplayedResult guard exists + idempotent ─────────────────────
def test_already_displayed_result_guard_present():
    src = REEL.read_text(encoding="utf-8")
    assert "alreadyDisplayedResult" in src, "Missing alreadyDisplayedResult ref"
    assert "alreadyDisplayedResult = useRef(false)" in src
    # The result-effect early-returns when the flag is already true
    assert "if (alreadyDisplayedResult.current) return;" in src, \
        "result-effect must early-return when flag is already true (idempotent)"
    # Flag is RESET at the start of a fresh generation
    assert "alreadyDisplayedResult.current = false;" in src, \
        "handleSubmit must reset the guard at the start of each generation"


# ─── 3. Auto-scroll to the result panel on success ───────────────────────────
def test_result_panel_auto_scroll_wired():
    src = REEL.read_text(encoding="utf-8")
    assert "resultPanelRef" in src
    assert "ref={resultPanelRef}" in src, "Output panel must carry the ref"
    assert "scrollIntoView" in src, "Must scroll the result panel into view"
    assert "behavior: 'smooth'" in src or 'behavior: "smooth"' in src


# ─── 4. Success-state heading copy ───────────────────────────────────────────
def test_success_state_heading_copy():
    src = REEL.read_text(encoding="utf-8")
    # When result is set the header reads "Your reel is ready"; pre-gen
    # state remains "Generated Output".
    assert "'Your reel is ready'" in src or '"Your reel is ready"' in src
    assert "data-testid=\"reel-output-heading\"" in src
    assert "data-testid=\"reel-output-panel\"" in src


# ─── 5. Three funnel events fire at the right moments ────────────────────────
def test_funnel_events_emitted():
    src = REEL.read_text(encoding="utf-8")
    assert "trackFunnel('reel_generation_started'" in src
    assert "trackFunnel('reel_generation_completed'" in src
    assert "trackFunnel('reel_generation_result_viewed'" in src
    # And the started/completed events live inside handleSubmit while
    # _result_viewed fires from the result useEffect (idempotent).
    m = re.search(
        r"const handleSubmit = async \(e\) =>\s*\{(.*?)\n  \};",
        src,
        re.S,
    )
    submit_body = m.group(0)
    assert "reel_generation_started" in submit_body
    assert "reel_generation_completed" in submit_body
    # _result_viewed must NOT live inside handleSubmit — it belongs to the
    # idempotent result useEffect so polling/hydration triggers it correctly.
    assert "reel_generation_result_viewed" not in submit_body, \
        "result_viewed must fire from the idempotent useEffect, not handleSubmit"


# ─── 6. SessionStorage survival cache ────────────────────────────────────────
def test_session_storage_result_cache():
    src = REEL.read_text(encoding="utf-8")
    assert "REEL_RESULT_CACHE_KEY" in src
    # Set on success, read on mount
    assert "sessionStorage.setItem(REEL_RESULT_CACHE_KEY" in src
    assert "sessionStorage.getItem(REEL_RESULT_CACHE_KEY" in src
    # Try/catch wraps both — sessionStorage may be disabled
    assert "try {" in src and "sessionStorage" in src


# ─── 7. generationLifecycle module exists with correct API ───────────────────
def test_generation_lifecycle_module_contract():
    src = LIFECYCLE.read_text(encoding="utf-8")
    for needle in (
        "export function beginGeneration",
        "export function isGenerationInFlight",
        "export function deferLogin",
        "export function hasPendingLogin",
        "export function consumePendingLogin",
        "let activeCount = 0",
    ):
        assert needle in src, f"generationLifecycle.js missing: {needle}"


# ─── 8. api.js 401 interceptor defers redirect when generation in-flight ─────
def test_api_interceptor_defers_401_during_generation():
    src = API.read_text(encoding="utf-8")
    # Must import / require the lifecycle module
    assert "generationLifecycle" in src, \
        "api.js must consult generationLifecycle on 401"
    assert "isGenerationInFlight" in src
    assert "deferLogin" in src
    # The deferral path shows a "Session expired" toast — exact copy per spec
    assert "Session expired. Please log in again to continue." in src
    # And the deferral block early-returns BEFORE the hard window.location.href
    # redirect path. Verify the deferral check appears textually BEFORE the
    # localStorage.removeItem('token') hard-redirect block.
    idx_defer = src.find("deferLogin(")
    idx_remove = src.find("localStorage.removeItem('token')")
    assert idx_defer != -1 and idx_remove != -1
    assert idx_defer < idx_remove, \
        "Deferral guard must run BEFORE the hard 401 redirect path"


# ─── 9. handleSubmit flushes pending login AFTER setLoading(false) ───────────
def test_pending_login_flushed_in_finally_after_loading_false():
    src = REEL.read_text(encoding="utf-8")
    # Isolate handleSubmit specifically (other functions have their own finally
    # blocks — fetchCredits etc.).
    m = re.search(
        r"const handleSubmit = async \(e\) =>\s*\{(.*?)\n  \};",
        src,
        re.S,
    )
    assert m, "Could not locate handleSubmit"
    submit_body = m.group(0)
    m2 = re.search(r"} finally \{(.*?)\n    \}", submit_body, re.S)
    assert m2, "Could not isolate handleSubmit finally block"
    finally_body = m2.group(0)
    assert "setLoading(false)" in finally_body
    assert "endGeneration()" in finally_body
    assert "hasPendingLogin()" in finally_body
    assert "consumePendingLogin()" in finally_body
    # And the actual location change happens AFTER a setTimeout so the
    # result UI mounts before the redirect (user sees their reward, briefly).
    assert "setTimeout" in finally_body
    # And in the right order: setLoading(false) before endGeneration() before pending-login flush
    i_loading = finally_body.find("setLoading(false)")
    i_end = finally_body.find("endGeneration()")
    i_pending = finally_body.find("hasPendingLogin()")
    assert i_loading < i_end < i_pending, \
        "finally order must be: setLoading(false) → endGeneration() → flushPendingLogin()"


# ─── 10. beginGeneration imported AND called in handleSubmit ─────────────────
def test_handle_submit_marks_generation_in_flight():
    src = REEL.read_text(encoding="utf-8")
    assert "from '../utils/generationLifecycle'" in src
    assert "beginGeneration," in src
    # beginGeneration() invoked early in handleSubmit (before await)
    m = re.search(
        r"const handleSubmit = async \(e\) =>\s*\{(.*?)\n  \};",
        src,
        re.S,
    )
    submit_body = m.group(0)
    assert "const endGeneration = beginGeneration();" in submit_body
    # And endGeneration() called in finally
    assert "endGeneration();" in submit_body
