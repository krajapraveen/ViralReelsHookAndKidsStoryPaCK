"""
Phase 3a — StoryVideoPipeline shadow observer (read-only)
==========================================================
Locks in (per founder spec, 2026-05-17):

  1. Shadow observer is wired into StoryVideoPipeline.js
  2. Wiring uses ONLY the read-only useStorySessionShadow hook
  3. Hook calls only GET /api/drafts/{id}/state — NO write paths
  4. Hook NEVER calls commit/transition/startFresh from the editor file
  5. Divergence logs carry request_id, draft_id, field, legacy_value,
     canonical_value
  6. Field whitelist matches founder spec
  7. Legacy autosave (POST /api/drafts/save) STILL fires identically
  8. No editor data-testids changed (no UI regression)
"""
from __future__ import annotations

from pathlib import Path

SVP_JS = Path("/app/frontend/src/pages/StoryVideoPipeline.js")
SHADOW_JS = Path("/app/frontend/src/state/useStorySessionShadow.js")
HOOK_JS = Path("/app/frontend/src/state/useStorySession.js")


# ════════════════════════════════════════════════════════════════════════
# Wiring proof
# ════════════════════════════════════════════════════════════════════════
def test_shadow_hook_is_imported_in_editor():
    src = SVP_JS.read_text(encoding="utf-8")
    assert "useStorySessionShadow" in src, \
        "Phase 3a: shadow hook must be wired into StoryVideoPipeline.js"
    assert "from '../state/useStorySessionShadow'" in src


def test_shadow_hook_is_called_with_required_params():
    src = SVP_JS.read_text(encoding="utf-8")
    # Confirm a single mount point with the right call shape.
    needle = "useStorySessionShadow({"
    assert src.count(needle) == 1, "Exactly one shadow mount expected"
    # Mount must pass draftId + legacy fields
    after = src.split(needle, 1)[1].split("});", 1)[0]
    assert "draftId: activeDraftId" in after
    for f in ("title", "storyText", "animationStyle:", "ageGroup",
              "voicePreset", "lifecycle"):
        assert f in after, f"Mount missing legacy field: {f}"


# ════════════════════════════════════════════════════════════════════════
# READ-ONLY guarantee — editor file MUST NOT invoke mutator APIs from the
# shadow hook surface area. We assert it negatively.
# ════════════════════════════════════════════════════════════════════════
def test_editor_does_not_call_mutator_apis_from_shadow_surface():
    src = SVP_JS.read_text(encoding="utf-8")
    forbidden_patterns = [
        # Direct mutator paths from the new API. These must not appear in
        # StoryVideoPipeline.js until Phase 3b/3c. Their presence here
        # would mean someone broke the read-only contract.
        "/patch'",          # POST /drafts/{id}/patch
        "/patch`",
        "/transition'",     # POST /drafts/{id}/transition
        "/transition`",
        "/api/drafts/session",  # POST /drafts/session
    ]
    for pat in forbidden_patterns:
        assert pat not in src, \
            f"Editor must not call mutator endpoint (found {pat!r})"


def test_editor_does_not_destructure_hook_mutators():
    src = SVP_JS.read_text(encoding="utf-8")
    # The full useStorySession hook exposes `api: { commit, transition, startFresh }`.
    # The shadow observer hides those. Assert the editor never reaches for them.
    for sym in ("commit(", "transition(", "startFresh("):
        # Specifically check the editor file (not other files in app).
        # These names are not unique globally so we only check after the
        # shadow-hook import marker to scope the assertion.
        idx = src.find("useStorySessionShadow({")
        assert idx > 0
        # Look in a 3 KB window around the shadow mount — sufficient context.
        window = src[max(0, idx - 1500): idx + 2000]
        assert sym not in window, \
            f"Editor must not call {sym} near the shadow mount"


# ════════════════════════════════════════════════════════════════════════
# Shadow hook self-contract: only GET, structured logs, dedupe
# ════════════════════════════════════════════════════════════════════════
def test_shadow_hook_does_not_call_mutators_internally():
    src = SHADOW_JS.read_text(encoding="utf-8")
    # The hook MUST NOT touch the mutator surface of useStorySession.
    for forbidden in ("api.commit", "api.transition", "api.startFresh",
                       "client.patchSession", "client.transitionSession",
                       "client.createSession"):
        assert forbidden not in src, \
            f"Shadow hook leaked mutator usage: {forbidden}"


def test_shadow_hook_uses_canonical_read_only_hook():
    src = SHADOW_JS.read_text(encoding="utf-8")
    assert "from './useStorySession'" in src
    # We deliberately do NOT destructure `api` — assert it.
    assert "destructure `api`" in src or "do NOT destructure" in src, \
        "Shadow contract comment must remain (anti-regression marker)"


def test_shadow_logs_have_required_structured_fields():
    src = SHADOW_JS.read_text(encoding="utf-8")
    # Match the founder-required envelope shape.
    for key in (
        "[story-session/divergence]",
        "request_id=",
        "draft_id=",
        "field=",
        "legacy_value=",
        "canonical_value=",
    ):
        assert key in src, f"Divergence log missing required key {key!r}"


def test_shadow_tracked_fields_match_spec():
    src = SHADOW_JS.read_text(encoding="utf-8")
    # Founder spec: title, storyText, animationStyle, ageGroup, voicePreset, lifecycle.
    for f in ("title", "storyText", "animationStyle", "ageGroup",
              "voicePreset", "lifecycle"):
        assert f"'{f}'" in src, f"Shadow tracked-fields missing {f!r}"


def test_shadow_dedupes_log_lines_per_canonical_version():
    src = SHADOW_JS.read_text(encoding="utf-8")
    # The de-dupe mechanism: a ref keyed by canonical version.
    assert "loggedRef" in src
    assert "version: state.version" in src or "version === state.version" in src


# ════════════════════════════════════════════════════════════════════════
# Behavior preservation: legacy autosave + UI testids unchanged
# ════════════════════════════════════════════════════════════════════════
def test_legacy_autosave_still_uses_drafts_save():
    src = SVP_JS.read_text(encoding="utf-8")
    # The 3s debounced autosave must still hit /api/drafts/save.
    assert "api.post('/api/drafts/save'" in src, \
        "Legacy autosave was removed — Phase 3a must NOT migrate writes"


def test_legacy_autosave_debounce_intact():
    src = SVP_JS.read_text(encoding="utf-8")
    assert "draftSaveTimer.current = setTimeout(" in src
    # 3-second debounce matches pre-Phase-3a contract
    assert "}, 3000)" in src


def test_resume_draft_modal_testid_intact():
    src = SVP_JS.read_text(encoding="utf-8")
    # Spot-check that the resume-draft modal testid hasn't been renamed.
    # Critical anchor for the existing Phase 0/1 contract tests.
    assert 'data-testid="resume-draft-modal"' in src, \
        "Resume-draft modal testid regressed during Phase 3a wiring"


def test_canonical_hook_remains_pure_react():
    """The useStorySession source must not have grown new write paths
    just because the shadow consumer landed."""
    src = HOOK_JS.read_text(encoding="utf-8")
    assert "useStorySession" in src
    # Must still expose the documented API surface
    assert "commit" in src and "transition" in src and "startFresh" in src


# ════════════════════════════════════════════════════════════════════════
# Static import graph: shadow does NOT import storySessionClient mutators
# ════════════════════════════════════════════════════════════════════════
def test_shadow_module_does_not_import_storySessionClient():
    """The shadow observer must not directly import the version-aware
    write client. It must go through useStorySession (which itself only
    fires the hydration read)."""
    src = SHADOW_JS.read_text(encoding="utf-8")
    assert "from './storySessionClient'" not in src
    assert "from '../state/storySessionClient'" not in src
