"""
Completion-prompt modal trust-flow audit — 2026-05-16 P0 (bounded fix)

Locks in the 5 audit fixes:
  1. ESC key support + body scroll-lock + cleanup on unmount
  2. handleCreateAnother CLEARS stale remix_video / remix_data localStorage
     before navigating (kills "blank editor with old story" bug)
  3. RemixGallery.handleRemix uses correct localStorage hydration channel
     (was state-only — silently dropped, same bug class as the 4 action
     cards we fixed previously)
  4. handleShare validates job_id BEFORE constructing share URL (kills
     /share/undefined leaks)
  5. Modal has role="dialog" + aria-modal + aria-labelledby + backdrop
     data-testid for accessibility audits
"""
from pathlib import Path
import re

MS = Path("/app/frontend/src/pages/MySpacePage.js")
RG = Path("/app/frontend/src/components/RemixGallery.js")


# ─── 1. ESC key + scroll-lock + cleanup ──────────────────────────────────────
def test_completion_modal_supports_escape_key():
    src = MS.read_text(encoding="utf-8")
    idx = src.find("function CompletionPromptModal(")
    assert idx > 0
    body = src[idx:idx + 4000]
    # Listener added inside a useEffect
    assert "React.useEffect" in body or "useEffect(" in body
    assert "addEventListener('keydown'" in body
    assert "e.key === 'Escape'" in body
    # And removed on cleanup
    assert "removeEventListener('keydown'" in body


def test_completion_modal_locks_body_scroll():
    src = MS.read_text(encoding="utf-8")
    idx = src.find("function CompletionPromptModal(")
    body = src[idx:idx + 4000]
    assert "document.body.style.overflow = 'hidden'" in body
    # And restores previous overflow on cleanup (no permanent lock)
    assert "document.body.style.overflow = prevOverflow" in body


def test_completion_modal_has_accessibility_attrs():
    src = MS.read_text(encoding="utf-8")
    idx = src.find("function CompletionPromptModal(")
    body = src[idx:idx + 4000]
    assert 'role="dialog"' in body
    assert 'aria-modal="true"' in body
    assert 'aria-labelledby="completion-prompt-heading"' in body
    assert 'id="completion-prompt-heading"' in body
    assert 'aria-label="Close completion prompt"' in body


def test_completion_modal_inner_card_has_max_height():
    """Same fix class as the SharePromptModal positioning fix from earlier:
    inner card must clamp height so it scrolls instead of pushing content
    off-screen on small viewports."""
    src = MS.read_text(encoding="utf-8")
    idx = src.find("function CompletionPromptModal(")
    body = src[idx:idx + 4000]
    assert "max-h-[calc(100vh-2rem)]" in body
    assert "overflow-y-auto" in body


def test_completion_modal_backdrop_has_testid():
    src = MS.read_text(encoding="utf-8")
    idx = src.find("function CompletionPromptModal(")
    body = src[idx:idx + 4000]
    assert 'data-testid="completion-prompt-backdrop"' in body


# ─── 2. Create Another CLEARS stale remix state ──────────────────────────────
def test_create_another_clears_stale_remix_video_and_remix_data():
    """The bug-class regression guard. If we don't strip both keys, the
    studio's mount-time hydration loads the OLD story → "Create Another"
    appears to do nothing."""
    src = MS.read_text(encoding="utf-8")
    idx = src.find("const handleCreateAnother = ()")
    assert idx > 0
    body = src[idx:idx + 800]
    assert "localStorage.removeItem('remix_video')" in body
    assert "localStorage.removeItem('remix_data')" in body
    # Cache-buster query so even same-route mounts re-init clean
    assert "t=${Date.now()}" in body


def test_create_another_navigates_to_canonical_create_route():
    src = MS.read_text(encoding="utf-8")
    idx = src.find("const handleCreateAnother = ()")
    body = src[idx:idx + 800]
    assert "/app/story-video-studio" in body


# ─── 3. RemixGallery handleRemix writes correct hydration shape ──────────────
def test_remix_gallery_writes_remix_video_localstorage():
    """ROOT-CAUSE FIX: same as the 4 action-card buttons. RemixGallery used
    to pass payload via location.state which the studio ignores → blank
    editor. Now writes remix_video to localStorage in the correct shape."""
    src = RG.read_text(encoding="utf-8")
    idx = src.find("const handleRemix = async (item)")
    assert idx > 0
    body = src[idx:idx + 2500]
    # Must write remix_video to localStorage
    assert "localStorage.setItem('remix_video'" in body
    # With the canonical shape
    assert "parent_video_id: item.item_id" in body
    assert "story_text: sourceStory" in body
    # And the pre-fix dangerous pattern is gone
    assert "state: {" not in body or "navigate('/app/story-video-studio', {\n      state:" not in body


def test_remix_gallery_navigates_with_query_params_not_state():
    src = RG.read_text(encoding="utf-8")
    idx = src.find("const handleRemix = async (item)")
    body = src[idx:idx + 2500]
    # New navigation uses ?remix=trending&source_item=<id>
    assert "?remix=trending&source_item=" in body
    assert "encodeURIComponent(item.item_id)" in body


def test_remix_gallery_validates_item_id_before_navigation():
    src = RG.read_text(encoding="utf-8")
    idx = src.find("const handleRemix = async (item)")
    body = src[idx:idx + 2500]
    assert "if (!item?.item_id)" in body
    assert "Unable to load trending project" in body
    assert "Reference ID:" in body


def test_remix_gallery_validates_story_text_before_navigation():
    src = RG.read_text(encoding="utf-8")
    idx = src.find("const handleRemix = async (item)")
    body = src[idx:idx + 2500]
    assert "if (!sourceStory.trim())" in body
    assert "missing story content" in body


# ─── 4. handleShare validates job_id BEFORE constructing URL ────────────────
def test_handle_share_validates_job_id():
    src = MS.read_text(encoding="utf-8")
    idx = src.find("const handleShare = async (job)")
    assert idx > 0
    body = src[idx:idx + 2500]
    # Must guard at the top of the function
    assert "if (!job?.job_id && !job?.public_share_slug && !job?.share_slug)" in body
    assert "Unable to share:" in body
    assert "Reference ID:" in body


# ─── 5. No silent failure paths in modal handlers ───────────────────────────
def test_no_dead_onclick_handlers_in_completion_modal():
    src = MS.read_text(encoding="utf-8")
    idx = src.find("function CompletionPromptModal(")
    body = src[idx:idx + 6000]
    # No empty onClicks
    assert "onClick={() => {}}" not in body
    assert "onClick={()=>{}}" not in body
    # Each clickable element has a data-testid so audits can target them
    for need in (
        'data-testid="completion-prompt-close"',
        'data-testid="completion-prompt-backdrop"',
        'data-testid="completion-prompt-title"',
    ):
        assert need in body, f"missing testid: {need}"


# ─── 6. Trending card mounts via RemixCard with key=item.item_id ────────────
def test_trending_cards_keyed_by_item_id():
    """React-key collision audit. Trending cards in the modal map MUST
    be keyed by item.item_id (per-item), never by index."""
    src = RG.read_text(encoding="utf-8")
    assert "key={item.item_id}" in src, "Trending cards must be keyed by item_id"


# ─── 7. Composite: pre-fix dangerous patterns are gone ──────────────────────
def test_pre_fix_state_only_navigation_removed_from_remix_gallery():
    src = RG.read_text(encoding="utf-8")
    # The exact pre-fix navigation pattern must be gone
    assert "navigate('/app/story-video-studio', {\n      state: {" not in src, \
        "Pre-fix state-only navigation pattern still present in RemixGallery"
    assert "source: 'remix_gallery'," not in src, \
        "Pre-fix remixFrom payload still being passed via state"
