"""
MySpace post-gen action cards — 2026-05-16 P0 (bounded fix)

User-visible bug: the four action buttons on completed cards in MySpace
("Make it funnier", "Change style", "Turn into reel", "Turn into storybook")
rendered but appeared to do nothing.

ROOT CAUSE (one bug, four symptoms):
  Previous handleVariation called navigate(path, { state: payload }).
  None of the destination tools read location.state — they hydrate from
  localStorage. So all four buttons navigated correctly but the
  destination editor loaded BLANK with no remix context → user perceived
  it as "button does nothing."

  Additionally:
    • All four routed to /app/story-video-studio — only 2 of 4 should
    • No source_job query param attached for traceability
    • Missing source ids silently no-op'd (no structured error toast)

FIX (bounded):
  • Each VARIATION_BUTTONS entry declares its own route + mode + storageKey
  • handleVariation validates source job_id + story_text BEFORE navigation
  • Writes to the CORRECT localStorage key in the CORRECT shape:
      - remix_video (Story Video Studio hydration shape) for funny/style
      - remix_data  (useRemixData hook hydration shape) for reel/storybook
  • Appends ?source_job=<id> to every destination URL
  • Missing ids surface "Unable to load source project. Reference ID: ..."
"""
from pathlib import Path
import re

MS = Path("/app/frontend/src/pages/MySpacePage.js")


def _handle_variation_source():
    src = MS.read_text(encoding="utf-8")
    idx = src.find("const handleVariation = (variant) =>")
    assert idx > 0, "handleVariation must exist"
    # Take enough chars to cover the multi-branch handler
    return src[idx:idx + 6000]


# ─── 1. Each variant declares its OWN canonical route + storage key ─────────
def test_variation_buttons_declare_route_and_storage_key():
    src = MS.read_text(encoding="utf-8")
    idx = src.find("const VARIATION_BUTTONS = [")
    assert idx > 0
    arr = src[idx:src.find("];", idx) + 2]
    # Required fields per entry
    for need in ("label:", "route:", "mode:", "storageKey:"):
        assert arr.count(need) >= 4, f"Every variant entry must declare {need}"
    # Canonical destinations
    assert arr.count("/app/story-video-studio") == 2, \
        "Make it funnier + Change style must route to story-video-studio"
    assert "/app/reel-generator" in arr, "Turn into reel must use /app/reel-generator"
    assert "/app/comic-storybook" in arr, "Turn into storybook must use /app/comic-storybook"
    # Two localStorage shapes
    assert arr.count("'remix_video'") == 2
    assert arr.count("'remix_data'") == 2
    # Comedy injection flag on "Make it funnier" only
    assert arr.count("injectComedy: true") == 1
    assert arr.count("injectComedy: false") == 3


# ─── 2. Missing job_id → structured error toast (NO silent failure) ─────────
def test_handler_refuses_when_source_job_id_missing():
    body = _handle_variation_source()
    # Must check job_id BEFORE navigating
    assert "if (!job?.job_id)" in body, "Handler must guard on missing job_id"
    assert "Unable to load source project." in body
    assert "Reference ID:" in body
    # And early-return (no navigate call inside the guard)
    guard_idx = body.find("if (!job?.job_id)")
    guard_block_end = body.find("}", guard_idx)
    guard_block = body[guard_idx:guard_block_end + 1]
    assert "navigate(" not in guard_block


def test_handler_refuses_when_source_story_missing():
    body = _handle_variation_source()
    assert "sourceStory" in body
    assert "missing story content" in body


# ─── 3. Studio variants (funny/style) write remix_video correctly ───────────
def test_studio_variants_write_remix_video_correctly():
    body = _handle_variation_source()
    # remix_video branch present
    assert "localStorage.setItem('remix_video'" in body
    # The studio reads parent_video_id + title + story_text + ...
    assert "parent_video_id: sourceJobId" in body
    assert "title: sourceTitle" in body
    assert "story_text:" in body
    # Comedy variant prepends a comedy directive
    assert "[Make this funnier — same plot, comedy twist, exaggerated reactions]" in body
    # `?remix=funny` / `?remix=style` query param with ?source_job
    assert "?remix=${variant.mode}&source_job=${encodeURIComponent(sourceJobId)}" in body


# ─── 4. Reel + Storybook variants write remix_data correctly ────────────────
def test_reel_and_storybook_variants_write_remix_data():
    body = _handle_variation_source()
    assert "localStorage.setItem('remix_data'" in body
    # useRemixData hook contract: timestamp, prompt, remixFrom { title, prompt, tool, parentId }
    assert "timestamp: Date.now()" in body
    assert "prompt: sourceStory" in body
    assert "remixFrom:" in body
    assert "parentId: sourceJobId" in body
    # Distinguishing fields per destination
    assert "topic: sourceTitle" in body, "Reel mode must seed topic"
    assert "genre:" in body, "Storybook mode must seed genre"


# ─── 5. Every navigate() includes ?source_job=<id> for traceability ─────────
def test_every_navigation_includes_source_job_param():
    body = _handle_variation_source()
    # Two navigate calls (studio + non-studio) — both include source_job
    nav_calls = re.findall(r"navigate\(\s*`([^`]+)`", body)
    assert len(nav_calls) >= 2, f"Expected ≥2 navigate calls, found {len(nav_calls)}"
    for url in nav_calls:
        assert "source_job=" in url, f"Navigate URL missing source_job: {url}"


# ─── 6. No silent failure paths — every branch must toast on completion ─────
def test_every_branch_surfaces_a_toast():
    body = _handle_variation_source()
    # Each successful branch must show a success toast so the user gets
    # immediate feedback (no "button does nothing" perception)
    assert body.count("toast.success(`Opening:") == 2
    # And every error branch must toast.error
    assert body.count("toast.error") >= 3, \
        "Every failure path must surface a structured toast"


# ─── 7. Defensive: pre-fix dangerous pattern is gone ────────────────────────
def test_pre_fix_state_only_navigation_pattern_is_gone():
    """The pre-fix handler did navigate(path, { state: payload }) — that
    pattern silently no-op'd because destination tools don't read state."""
    body = _handle_variation_source()
    # The exact dangerous signature must NOT reappear
    assert "navigate(path, { state: statePayload })" not in body
    # And the fallthrough `if (variant.tone) path += ...` is gone
    assert "if (variant.tone) path +=" not in body
    assert "if (variant.style) path +=" not in body


# ─── 8. Storybook variants must NOT route to story-video-studio ─────────────
def test_storybook_and_reel_dont_misroute_to_studio():
    """Bug-class regression guard: no entry whose label contains 'reel' or
    'storybook' may declare /app/story-video-studio as its route."""
    src = MS.read_text(encoding="utf-8")
    # Find each entry by label and verify its route
    funnier = re.search(r"label: 'Make it funnier'[^}]+route: '([^']+)'", src, re.S)
    style = re.search(r"label: 'Change style'[^}]+route: '([^']+)'", src, re.S)
    reel = re.search(r"label: 'Turn into reel'[^}]+route: '([^']+)'", src, re.S)
    storybook = re.search(r"label: 'Turn into storybook'[^}]+route: '([^']+)'", src, re.S)
    assert funnier and funnier.group(1) == "/app/story-video-studio"
    assert style and style.group(1) == "/app/story-video-studio"
    assert reel and reel.group(1) == "/app/reel-generator", \
        f"Turn into reel must route to /app/reel-generator, got: {reel.group(1) if reel else None}"
    assert storybook and storybook.group(1) == "/app/comic-storybook", \
        f"Turn into storybook must route to /app/comic-storybook, got: {storybook.group(1) if storybook else None}"


# ─── 9. Style picker semantics: animation_style preserved for funny,
#       cleared for change-style so the picker prompts user ────────────────
def test_change_style_omits_animation_style_to_force_picker():
    body = _handle_variation_source()
    # The comedy-only spread keeps animation_style; the change-style path
    # deliberately omits it so the studio shows the picker.
    assert "...(variant.injectComedy ? { animation_style: job.animation_style } : {})" in body
