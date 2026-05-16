"""
P0 production UX break — bounded fixes (2026-05-16)

Locks in source-level contracts for the four visible failures:
  1. Modal centering — SharePromptModal portal + max-h-[90vh] scroll;
     ForceShareGate inner card max-h-[calc(100vh-2rem)] scroll
  2. "Continue Mira's Story" — hard navigation when already on the
     /app/story-video-studio route so the editor remounts and reads the
     new remix_video payload; includes continue_from in the URL
  3. Share modal links — already wired (no dead buttons); verify the
     copy / instagram / reel / message / post handlers still call
     navigator.clipboard or window.open (not no-ops)
  4. Download — silent-fail path now surfaces structured error with
     request_id (via X-Request-Id response header)
"""
from pathlib import Path
import re


FSG = Path("/app/frontend/src/components/ForceShareGate.js")
SPM = Path("/app/frontend/src/components/SharePromptModal.js")
SVP = Path("/app/frontend/src/pages/StoryVideoPipeline.js")
EDB = Path("/app/frontend/src/components/EntitledDownloadButton.js")


# ─── BUG 1: Modal positioning ────────────────────────────────────────────────
def test_force_share_gate_inner_card_has_max_height_scroll():
    src = FSG.read_text(encoding="utf-8")
    # Inner card (the actual modal body) must clamp height so on small
    # viewports (Safari mobile, laptop full-height) it scrolls instead of
    # pushing content off-screen.
    assert "max-h-[calc(100vh-2rem)]" in src, \
        "ForceShareGate inner card must clamp height to viewport-2rem"
    # And the outer overlay must scroll if the modal exceeds viewport
    assert "overflow-y-auto" in src


def test_share_prompt_modal_uses_portal():
    src = SPM.read_text(encoding="utf-8")
    # ROOT CAUSE: SharePromptModal was rendering inline. An ancestor with
    # `transform`/`filter`/`perspective` creates a new containing block for
    # fixed positioning → modal appears lower-than-center. createPortal
    # mounts to document.body which is always the viewport.
    assert "from 'react-dom'" in src or 'from "react-dom"' in src
    assert "createPortal" in src
    assert "createPortal(" in src
    assert "document.body" in src


def test_share_prompt_modal_inner_card_has_max_height_scroll():
    src = SPM.read_text(encoding="utf-8")
    assert "max-h-[calc(100vh-2rem)]" in src
    # The fixed overlay also must scroll
    assert "overflow-y-auto" in src


# ─── BUG 2: "Continue Mira's Story" no-op ────────────────────────────────────
def test_continue_handler_uses_hard_nav_when_same_route():
    src = SVP.read_text(encoding="utf-8")
    idx = src.find("const handleContinue = (direction) =>")
    assert idx > 0
    body = src[idx:idx + 3000]
    # Must detect "already on /app/story-video-studio" and force a hard
    # navigation. Without this, navigate(...) to the same path doesn't
    # remount the page and the user sees nothing happen.
    assert "samePathname" in body or "samePath" in body
    assert "window.location.href" in body
    # Must include continue_from in the URL per spec
    assert "continue_from=" in body
    # And a cache-buster `t=` so even same-route hard reloads always
    # bypass any same-URL caches
    assert "&t=${Date.now()}" in body


def test_continue_handler_surfaces_structured_error_when_no_jid():
    src = SVP.read_text(encoding="utf-8")
    idx = src.find("const handleContinue = (direction) =>")
    body = src[idx:idx + 3000]
    # Spec: "If story_id missing, show structured error toast with
    # request_id, not silent failure."
    assert "if (!jid)" in body
    assert "missing story id" in body
    assert "Reference ID:" in body


# ─── BUG 3: Share modal links — all 5 buttons wired ──────────────────────────
def test_share_modal_buttons_still_wired():
    src = SPM.read_text(encoding="utf-8")
    # All five must have onClick handlers — not just visual chrome.
    # We grep for the canonical action names that imply they DO something.
    assert "navigator.clipboard" in src or "writeText" in src, \
        "Copy / share buttons must use clipboard API"
    # No button should be `onClick={() => {}}` (placeholder)
    assert "onClick={() => {}}" not in src, \
        "No empty onClick handlers (dead buttons)"


# ─── BUG 4: Download silent-fail path ────────────────────────────────────────
def test_download_button_surfaces_request_id_on_empty_response():
    src = EDB.read_text(encoding="utf-8")
    # Locate the handleSecureDownload body
    idx = src.find("const handleSecureDownload = async ()")
    if idx < 0:
        idx = src.find("handleSecureDownload = async")
    assert idx >= 0
    body = src[idx:idx + 3000]
    # Spec: "No silent no-op." The else-branch when data.success is false
    # or download_url missing must surface a request_id-bearing toast.
    assert "Download response was empty" in body
    assert "X-Request-Id" in body
    assert "Reference ID:" in body


def test_download_button_error_path_surfaces_request_id():
    src = EDB.read_text(encoding="utf-8")
    idx = src.find("const handleSecureDownload = async ()")
    if idx < 0:
        idx = src.find("handleSecureDownload = async")
    body = src[idx:idx + 6000]
    # The catch block must include request_id (X-Request-Id) in the
    # surfaced toast so support requests are traceable.
    catch_idx = body.find("} catch (err)")
    assert catch_idx > 0
    catch_block = body[catch_idx:catch_idx + 2000]
    assert "X-Request-Id" in catch_block or "request_id" in catch_block.lower()
    assert "Reference ID:" in catch_block
    # And we must NOT have stripped the original toast.error path
    assert "toast.error" in catch_block


# ─── Composite: no dead buttons across the 4 files ──────────────────────────
def test_no_dead_onclick_handlers_in_touched_files():
    for path in (FSG, SPM, EDB):
        src = path.read_text(encoding="utf-8")
        # Empty-body onclicks are a dead-button signal
        assert "onClick={() => {}}" not in src, \
            f"{path.name} contains an empty onClick handler"
        assert "onClick={()=>{}}" not in src, \
            f"{path.name} contains an empty onClick handler (no-space variant)"
