"""
P0/P1 2026-05-19 — Comic Story Book post-generation action cards.
==================================================================
Production screenshot showed four cards rendered after a completed
comic — `Add Next Chapter`, `Change Art Style`, `Convert to Video`,
`Make Bedtime Story` — none of which behaved correctly. Founder spec:

  > If feature is already implemented, route to the correct page with
  > the correct context. If feature is not implemented, do NOT show it
  > as active. Disable it or show "Coming soon" clearly.

DESTINATION ROUTE AUDIT
-----------------------
- Add Next Chapter      → /app/comic-storybook (same tool, remix-aware ✅)
- Change Art Style      → /app/comic-storybook (same tool, remix-aware ✅)
- Convert to Video      → /app/story-video-studio (remix-aware ✅)
- Make Bedtime Story    → /app/bedtime-story-builder (NOT remix-aware ❌)

FIX
---
- The three remix-aware destinations stay enabled. We now pass
  `source_job_id` in both the route state AND localStorage remix
  payload so destinations can fetch source-comic context when needed.
- "Make Bedtime Story" is marked `comingSoon: true`. The card renders
  disabled with a visible "Coming soon" badge, click is a no-op +
  info toast (NEVER navigates, NEVER calls setShowUpsell).
- Each card now carries its founder-spec canonical `data-testid`:
    storybook-add-next-chapter, storybook-change-art-style,
    storybook-convert-video, storybook-bedtime-story
"""
from __future__ import annotations

from pathlib import Path

NEXT_ACTIONS_JS = Path("/app/frontend/src/components/NextActionHooks.js")


def _comic_block() -> str:
    src = NEXT_ACTIONS_JS.read_text()
    return src.split("'comic-storybook':", 1)[1].split("'bedtime-story-builder':", 1)[0]


# ════════════════════════════════════════════════════════════════════════
# 1. Each card carries its canonical founder-spec data-testid
# ════════════════════════════════════════════════════════════════════════
def test_all_four_cards_have_canonical_testids():
    block = _comic_block()
    for tid in ("storybook-add-next-chapter", "storybook-change-art-style",
                "storybook-convert-video", "storybook-bedtime-story"):
        assert tid in block, (
            f"Comic Story Book hooks card missing canonical testid {tid!r}"
        )


# ════════════════════════════════════════════════════════════════════════
# 2. Bedtime Story card is marked Coming Soon (destination not wired)
# ════════════════════════════════════════════════════════════════════════
def test_bedtime_story_card_is_coming_soon():
    block = _comic_block()
    # Locate the bedtime card line.
    bedtime_line = next(
        l for l in block.splitlines() if "storybook-bedtime-story" in l
    )
    assert "comingSoon: true" in bedtime_line, (
        "Bedtime Story card must be marked comingSoon: true because the "
        "destination route doesn't consume remix_data yet — founder spec "
        "mandates no dead buttons"
    )


def test_other_three_cards_are_not_coming_soon():
    """Confirm we didn't accidentally disable the working cards too."""
    block = _comic_block()
    for tid in ("storybook-add-next-chapter", "storybook-change-art-style",
                "storybook-convert-video"):
        line = next(l for l in block.splitlines() if tid in l)
        assert "comingSoon: true" not in line, (
            f"{tid} must remain active — its destination IS remix-aware"
        )


# ════════════════════════════════════════════════════════════════════════
# 3. Coming-soon handler logic — no navigate, no toast.success
# ════════════════════════════════════════════════════════════════════════
def test_coming_soon_handler_does_not_navigate():
    src = NEXT_ACTIONS_JS.read_text()
    fn = src.split("const handleHook = (hook) => {", 1)[1].split(
        "  return (", 1
    )[0]
    # Must check comingSoon FIRST and early-return.
    assert "if (hook.comingSoon)" in fn, (
        "Click handler must check comingSoon before any navigation"
    )
    coming_soon_branch = fn.split("if (hook.comingSoon)", 1)[1].split(
        "return;", 1
    )[0]
    assert "navigate(" not in coming_soon_branch, (
        "Coming-soon branch must NOT navigate"
    )
    assert "Coming soon" in coming_soon_branch, (
        "Coming-soon branch must give the user a clear info toast"
    )
    assert "toast.info" in coming_soon_branch, (
        "Coming-soon branch must use toast.info, not toast.success "
        "(success implies action completed; info is correct semantics)"
    )


# ════════════════════════════════════════════════════════════════════════
# 4. source_job_id propagation — destinations can fetch source context
# ════════════════════════════════════════════════════════════════════════
def test_source_job_id_propagated_to_destination():
    """Founder spec: 'Must carry source_job_id ...'. We pass it both
    as a top-level field AND inside remixFrom for backward compat."""
    src = NEXT_ACTIONS_JS.read_text()
    fn = src.split("const handleHook = (hook) => {", 1)[1].split(
        "  return (", 1
    )[0]
    # Top-level field for new consumers.
    assert "source_job_id: generationId" in fn, (
        "Click handler must pass source_job_id at the top level of "
        "the state payload"
    )
    # Inside remixFrom for legacy consumers.
    assert "remixFrom: {" in fn
    remix_block = fn.split("remixFrom: {", 1)[1].split("},", 1)[0]
    assert "source_job_id: generationId" in remix_block, (
        "source_job_id must also live inside remixFrom for backward compat"
    )


# ════════════════════════════════════════════════════════════════════════
# 5. Same-tool remix scrolls to top
# ════════════════════════════════════════════════════════════════════════
def test_same_tool_remix_scrolls_to_top():
    """Add Next Chapter / Change Art Style stay on /app/comic-storybook —
    must scroll to top so the user lands on Step 1, not mid-page where
    they were."""
    src = NEXT_ACTIONS_JS.read_text()
    fn = src.split("const handleHook = (hook) => {", 1)[1].split(
        "  return (", 1
    )[0]
    assert "hook.target === toolType" in fn, (
        "Click handler must detect same-tool remix"
    )
    assert "window.scrollTo" in fn, (
        "Same-tool remix must scroll to top"
    )


# ════════════════════════════════════════════════════════════════════════
# 6. UI rendering — disabled state + Coming Soon badge
# ════════════════════════════════════════════════════════════════════════
def test_button_disabled_attribute_honors_coming_soon():
    src = NEXT_ACTIONS_JS.read_text()
    btn_block = src.split("config.hooks.map((hook) =>", 1)[1].split(
        "</button>", 1
    )[0]
    assert "disabled={hook.comingSoon === true}" in btn_block, (
        "Coming-soon hooks must render the native disabled attribute"
    )
    assert "aria-disabled={hook.comingSoon === true}" in btn_block, (
        "Coming-soon hooks must also set aria-disabled for a11y"
    )
    assert "cursor-not-allowed" in btn_block, (
        "Coming-soon hooks must show the not-allowed cursor"
    )


def test_coming_soon_badge_renders_with_testid():
    src = NEXT_ACTIONS_JS.read_text()
    btn_block = src.split("config.hooks.map((hook) =>", 1)[1].split(
        "</button>", 1
    )[0]
    assert "Coming soon" in btn_block
    assert "-coming-soon" in btn_block, (
        "Coming-soon badge must have a deterministic testid suffix for "
        "Playwright assertions"
    )


# ════════════════════════════════════════════════════════════════════════
# 7. Smoke — config still has 4 hooks for comic-storybook
# ════════════════════════════════════════════════════════════════════════
def test_comic_storybook_still_has_all_four_hooks():
    block = _comic_block()
    for label in ("Add Next Chapter", "Change Art Style",
                  "Convert to Video", "Make Bedtime Story"):
        assert label in block, f"Missing hook label: {label}"
