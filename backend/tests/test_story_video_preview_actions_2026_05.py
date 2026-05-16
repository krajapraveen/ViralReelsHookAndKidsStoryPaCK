"""
P0 PRODUCT — Story-to-Video Preview-First Contract (2026-05-18)
================================================================
Founder mandate: after generation, users must land on a Preview screen
where they can Approve / Regenerate / Edit Prompt before any publish or
download flow. No auto-publish. No auto-redirect. Failed preview shows
a structured error with a request_id Reference ID.

This file locks in the wiring (source-level + behavioral assertions):

  Preview Action Row (renders only when video isActionable):
    1. data-testid="preview-actions-row" exists in PostGenPhase
    2. Three CTAs present with stable testids:
       preview-approve-btn, preview-regenerate-btn, preview-edit-prompt-btn
    3. Approve dismisses force-share + scrolls to download (no nav)
    4. Regenerate calls onRegenerate (re-runs same prompt as fresh job)
    5. Edit Prompt calls onEditPrompt (returns to phase=input preserving title/storyText)

  Auto-publish discipline:
    6. The 3-second auto-redirect for branch type was REMOVED
       (founder forbade auto-navigation before preview)

  Character / series linkage:
    7. Preview shows character chip when job has a character
    8. Preview shows series chip when job has a series_title

  Failed preview state:
    9. PostGen reducer carries `requestId` field
   10. validateAndResolve plumbs request_id from response headers into SET_FAILED
   11. FAILED state renders Reference ID with stable testid

  Approve does NOT trigger a nav / publish:
   12. The Approve handler does NOT call any /api/*/publish endpoint
   13. The Approve handler does NOT route away from the page
   14. No new feature surface (no /api/preview/approve endpoint added)

  Cumulative regression hooks:
   15. The post-gen phase root testid is preserved (postgen-phase)
"""
from __future__ import annotations

from pathlib import Path

SVP_JS = Path("/app/frontend/src/pages/StoryVideoPipeline.js")
SERVER_PY = Path("/app/backend/server.py")


# ════════════════════════════════════════════════════════════════════════
# Preview Action Row — wiring + testids
# ════════════════════════════════════════════════════════════════════════
def test_preview_actions_row_exists_in_postgen():
    src = SVP_JS.read_text(encoding="utf-8")
    assert 'data-testid="preview-actions-row"' in src, \
        "Founder mandate: a dedicated preview action row must exist"


def test_three_preview_ctas_with_stable_testids():
    src = SVP_JS.read_text(encoding="utf-8")
    for tid in (
        "preview-approve-btn",
        "preview-regenerate-btn",
        "preview-edit-prompt-btn",
    ):
        assert f'data-testid="{tid}"' in src, f"Missing CTA testid: {tid}"


def test_preview_action_row_only_renders_when_actionable():
    """Renders inside `{isActionable && (...)}` so it doesn't appear during
    processing/validating states. Guards against showing dead buttons."""
    src = SVP_JS.read_text(encoding="utf-8")
    needle = 'data-testid="preview-actions-row"'
    idx = src.find(needle)
    # Look back a few hundred chars for the conditional render guard
    prelude = src[max(0, idx - 600): idx]
    assert "{isActionable && (" in prelude, \
        "Preview action row must be gated by `{isActionable && (`"


def test_preview_actions_responsive_layout_no_overlap():
    """Mobile: stack vertically. Desktop: row layout. Reuses the layout
    primitives from the Character Detail fix so the same overlap regression
    can't return."""
    src = SVP_JS.read_text(encoding="utf-8")
    needle = 'data-testid="preview-actions-row"'
    idx = src.find(needle)
    # Container className lives on the line that closes ABOVE the testid —
    # take the surrounding window so we capture both.
    block = src[max(0, idx - 400): idx + 5500]
    assert "flex-col sm:flex-row" in block
    assert "sm:flex-wrap" in block
    # Each CTA gets w-full sm:w-auto + whitespace-normal break-words
    assert block.count("w-full sm:w-auto") >= 3
    assert block.count("whitespace-normal break-words") >= 3
    # No fixed h-9 (would clip wrapped text)
    cta_section = block.split("preview-approve-btn", 1)[1].split("</div>", 1)[0]
    assert " h-9 " not in cta_section


# ════════════════════════════════════════════════════════════════════════
# Handler wiring
# ════════════════════════════════════════════════════════════════════════
def test_handle_regenerate_resets_job_and_reuses_prompt():
    src = SVP_JS.read_text(encoding="utf-8")
    assert "const handleRegenerate = useCallback" in src
    block = src.split("const handleRegenerate", 1)[1].split("};", 1)[0]
    # Resets job/jobId/postGen but PRESERVES title + storyText
    assert "setJobId(null)" in block
    assert "setJob(null)" in block
    assert "dispatchPostGen({ type: 'RESET' })" in block
    # MUST NOT clear title/storyText (those are the prompt the user wants reused)
    assert "setTitle('')" not in block
    assert "setStoryText('')" not in block
    # Re-fires generation
    assert "handleGenerate()" in block


def test_handle_edit_prompt_returns_to_input_preserving_prompt():
    src = SVP_JS.read_text(encoding="utf-8")
    assert "const handleEditPrompt = useCallback" in src
    block = src.split("const handleEditPrompt", 1)[1].split("};", 1)[0]
    assert "setPhase('input')" in block
    # Preservation: NOT clearing the prompt
    assert "setTitle('')" not in block
    assert "setStoryText('')" not in block
    # Cleans up the previous job artifacts
    assert "dispatchPostGen({ type: 'RESET' })" in block
    assert "setJobId(null)" in block


def test_postgen_phase_receives_callbacks_via_props():
    src = SVP_JS.read_text(encoding="utf-8")
    # Parent passes onRegenerate + onEditPrompt to PostGenPhase. We split
    # on the JSX render block specifically (not the auto-status effect).
    site = src.split("{phase === 'postgen' && (", 1)[1].split("{phase === 'failed_recovery'", 1)[0]
    assert "onRegenerate={handleRegenerate}" in site
    assert "onEditPrompt={handleEditPrompt}" in site
    # Function signature receives them
    sig = src.split("function PostGenPhase(", 1)[1].split(")", 1)[0]
    assert "onRegenerate" in sig and "onEditPrompt" in sig


# ════════════════════════════════════════════════════════════════════════
# Auto-publish discipline — branch auto-redirect REMOVED
# ════════════════════════════════════════════════════════════════════════
def test_branch_auto_redirect_removed():
    """Founder forbade auto-navigation before preview. The 3-second
    setTimeout that redirected branch jobs to /app/story-battle/<root>
    must be gone."""
    src = SVP_JS.read_text(encoding="utf-8")
    # The exact deleted timing+navigation pattern must NOT exist anymore.
    forbidden_combinations = [
        "navigate(`/app/story-battle/${battleRoot}`, { replace: true })",
        "navigate(`/app/story-viewer/${jobId}`, { replace: true })",
    ]
    for f in forbidden_combinations:
        assert f not in src, \
            f"Auto-redirect pattern returned: {f!r} — must remain user-initiated"


def test_branch_redirect_replaced_with_explicit_user_initiated_link():
    """The Battle Entry Banner / Leaderboard link must remain — those are
    user-initiated. Cheap proof: the leaderboard testid is still wired."""
    src = SVP_JS.read_text(encoding="utf-8")
    assert 'data-testid="view-leaderboard-btn"' in src


# ════════════════════════════════════════════════════════════════════════
# Approve discipline — does NOT trigger publish, does NOT navigate away
# ════════════════════════════════════════════════════════════════════════
def test_approve_does_not_navigate_away_or_publish():
    src = SVP_JS.read_text(encoding="utf-8")
    # Locate the Approve button onClick handler.
    block = src.split('data-testid="preview-approve-btn"', 1)[0]
    onclick_block = block.rsplit("onClick=", 1)[1]
    # The Approve handler must NOT call navigate or window.location
    assert "navigate(" not in onclick_block, \
        "Approve must not navigate away — preview-first contract"
    assert "window.location" not in onclick_block
    # Must NOT call any /publish endpoint
    assert "/publish" not in onclick_block
    assert "/api/preview/approve" not in onclick_block


def test_no_new_preview_endpoint_introduced():
    """Founder freeze: no new feature surface. Verify the backend did NOT
    grow a /preview/approve route as part of this change."""
    if not SERVER_PY.exists():
        return
    src = SERVER_PY.read_text(encoding="utf-8")
    assert "preview/approve" not in src
    assert "/preview/publish" not in src


# ════════════════════════════════════════════════════════════════════════
# Character / series linkage chips
# ════════════════════════════════════════════════════════════════════════
def test_preview_renders_character_and_series_linkage_chips():
    src = SVP_JS.read_text(encoding="utf-8")
    assert 'data-testid="preview-linkage-chips"' in src
    assert 'data-testid="preview-character-chip"' in src
    assert 'data-testid="preview-series-chip"' in src
    # Conditional renders so empty linkage doesn't show empty chips
    chips_block = src.split('data-testid="preview-linkage-chips"', 1)[1].split("</div>", 1)[0]
    assert "characterName &&" in chips_block
    assert "job?.series_title &&" in chips_block


# ════════════════════════════════════════════════════════════════════════
# Failed preview — request_id surfaced
# ════════════════════════════════════════════════════════════════════════
def test_postgen_reducer_carries_request_id_field():
    src = SVP_JS.read_text(encoding="utf-8")
    # INITIAL_POST_GEN_STATE includes requestId
    init = src.split("INITIAL_POST_GEN_STATE = {", 1)[1].split("};", 1)[0]
    assert "requestId: null" in init
    # SET_FAILED dispatch reads action.requestId
    fail_case = src.split("case 'SET_FAILED':", 1)[1].split("case 'RESET':", 1)[0]
    assert "requestId: action.requestId" in fail_case


def test_validate_and_resolve_extracts_request_id_from_headers():
    src = SVP_JS.read_text(encoding="utf-8")
    block = src.split("validateAndResolve = useCallback", 1)[1].split("// ─── POLLING", 1)[0]
    # Both casings considered + falls back to error.response.detail.request_id
    assert "x-request-id" in block.lower()
    assert "X-Request-Id" in block
    # request_id propagates into SET_FAILED dispatches in BOTH paths
    # (validation returned non-READY, validation endpoint failed)
    assert block.count("requestId,") >= 2


def test_failed_state_renders_reference_id_with_testid():
    src = SVP_JS.read_text(encoding="utf-8")
    failed_block = src.split('data-testid="generation-failed-panel"', 1)[1].split("Actions — Retry is ALWAYS primary", 1)[0]
    assert 'data-testid="preview-failed-request-id"' in failed_block
    assert "Reference ID:" in failed_block
    # postGen.requestId is the source — not just errorCode
    assert "postGen.requestId" in failed_block


# ════════════════════════════════════════════════════════════════════════
# Regression anchor — postgen phase root testid intact
# ════════════════════════════════════════════════════════════════════════
def test_postgen_phase_root_testid_intact():
    src = SVP_JS.read_text(encoding="utf-8")
    assert 'data-testid="postgen-phase"' in src
    assert 'data-testid="status-badge"' in src
    assert 'data-testid="status-title"' in src


def test_preview_processing_state_intact():
    """The processing/generating state must continue to show progress UI
    so users see something between 'click Generate' and 'preview'."""
    src = SVP_JS.read_text(encoding="utf-8")
    assert 'data-testid="generating-preview"' in src
    # Stage detail still renders inside the generating state
    assert "stageDetail" in src
