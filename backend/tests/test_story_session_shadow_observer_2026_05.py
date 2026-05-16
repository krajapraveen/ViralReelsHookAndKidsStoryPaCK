"""
Phase 3a — Shadow Observer Module Contract (read-only, preserved)
==================================================================

After Phase 3b migration the EDITOR no longer imports the shadow hook
directly — it uses the canonical autosave hook (`useStorySessionAutosave`)
which embeds the same divergence-logging logic. The shadow MODULE file
itself stays available for future read-only observers (admin debug, ops
dashboards, etc.) and MUST keep its read-only contract.

This file locks in:
  • The shadow module never calls write APIs
  • The shadow module continues to emit structured divergence logs
  • Founder-spec divergence-tracking fields whitelist is intact
"""
from __future__ import annotations

from pathlib import Path

SHADOW_JS = Path("/app/frontend/src/state/useStorySessionShadow.js")
HOOK_JS = Path("/app/frontend/src/state/useStorySession.js")


# ════════════════════════════════════════════════════════════════════════
# READ-ONLY guarantee — shadow module must not call mutator APIs
# ════════════════════════════════════════════════════════════════════════
def test_shadow_hook_does_not_call_mutators_internally():
    src = SHADOW_JS.read_text(encoding="utf-8")
    for forbidden in ("api.commit", "api.transition", "api.startFresh",
                       "client.patchSession", "client.transitionSession",
                       "client.createSession"):
        assert forbidden not in src, \
            f"Shadow hook leaked mutator usage: {forbidden}"


def test_shadow_hook_uses_canonical_read_only_hook():
    src = SHADOW_JS.read_text(encoding="utf-8")
    assert "from './useStorySession'" in src
    assert "destructure `api`" in src or "do NOT destructure" in src, \
        "Shadow contract comment must remain (anti-regression marker)"


def test_shadow_logs_have_required_structured_fields():
    src = SHADOW_JS.read_text(encoding="utf-8")
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
    for f in ("title", "storyText", "animationStyle", "ageGroup",
              "voicePreset", "lifecycle"):
        assert f"'{f}'" in src, f"Shadow tracked-fields missing {f!r}"


def test_shadow_dedupes_log_lines_per_canonical_version():
    src = SHADOW_JS.read_text(encoding="utf-8")
    assert "loggedRef" in src
    assert "version: state.version" in src or "version === state.version" in src


def test_canonical_hook_remains_pure_react():
    """The useStorySession source must still expose the documented surface."""
    src = HOOK_JS.read_text(encoding="utf-8")
    assert "useStorySession" in src
    assert "commit" in src and "transition" in src and "startFresh" in src


def test_shadow_module_does_not_import_storySessionClient_directly():
    """Read-only hygiene: the shadow goes through useStorySession (which
    fires only the hydration read)."""
    src = SHADOW_JS.read_text(encoding="utf-8")
    assert "from './storySessionClient'" not in src
    assert "from '../state/storySessionClient'" not in src

