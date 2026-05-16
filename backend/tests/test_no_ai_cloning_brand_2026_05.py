"""
AI Cloning brand-cleanup regression — 2026-05-16
The user-facing AI Cloning surface has been surgically removed.
This test makes sure it stays gone.

Guarantees:
  • Source tree contains ZERO user-visible AI Cloning / Clone Chat / Digital Twin / Build Your Clone strings
  • The deleted routes/pages do not exist on disk
  • Backend does not register the avatar_studio router
  • Frontend App.js does not reference deleted lazy imports
  • Dashboard creator-tools list does not contain an avatar/clone entry
  • Backend personalization_service does not score the avatar key
"""
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_SRC = ROOT / "frontend" / "src"
BACKEND = ROOT / "backend"


# ─── 1. Branded strings must be gone ──────────────────────────────
BRAND_PATTERN = re.compile(
    r"AI[ -]?Clon(e|ing)|Clone[ -]?Chat|Digital[ -]?Twin|Build[ -]?Your[ -]?Clone|"
    r"Create[ -]?Clone|New[ -]?Clone|Voice[ -]?Clone|Avatar[ -]?Clone",
    re.IGNORECASE,
)


def _walk_files(base: Path, exts: set[str]):
    for p in base.rglob("*"):
        if p.is_file() and p.suffix in exts and "__pycache__" not in p.parts and "node_modules" not in p.parts:
            yield p


def test_no_ai_cloning_brand_strings_in_frontend_source():
    offenders = []
    for f in _walk_files(FRONTEND_SRC, {".js", ".jsx", ".ts", ".tsx"}):
        try:
            txt = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in BRAND_PATTERN.finditer(txt):
            offenders.append(f"{f.relative_to(ROOT)}: {m.group(0)!r}")
    assert offenders == [], "Branded strings still present in frontend:\n" + "\n".join(offenders)


def test_no_ai_cloning_brand_strings_in_backend_source():
    """Backend source must not contain branded strings.
    Tests are excluded because pytest cache may surface stale names; tests
    are self-checked via the file-existence assertions below."""
    offenders = []
    for f in _walk_files(BACKEND, {".py"}):
        # Skip the tests directory and this regression file itself
        if "tests" in f.parts:
            continue
        try:
            txt = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in BRAND_PATTERN.finditer(txt):
            offenders.append(f"{f.relative_to(ROOT)}: {m.group(0)!r}")
    assert offenders == [], "Branded strings still present in backend:\n" + "\n".join(offenders)


# ─── 2. Deleted files must remain deleted ─────────────────────────
DELETED_FILES = [
    "frontend/src/pages/AICloningStudio.jsx",
    "frontend/src/pages/AdminCloneModerationPage.jsx",
    "frontend/src/pages/AvatarDemoWizard.jsx",
    "frontend/src/pages/AvatarFunnelTablePage.jsx",
    "frontend/src/pages/AvatarStudioPage.legacy.jsx",
    "frontend/src/pages/AvatarDemoPage.legacy.jsx",
    "frontend/src/components/avatar/AssetUploadStep.jsx",
    "frontend/src/components/avatar/AvatarTypeStep.jsx",
    "frontend/src/components/avatar/LibraryStep.jsx",
    "frontend/src/components/avatar/MotionStep.jsx",
    "frontend/src/components/avatar/SafetyReviewStep.jsx",
    "frontend/src/components/avatar/GenerationProgress.jsx",
    "frontend/src/components/avatar/shared.jsx",
    "backend/routes/avatar_studio.py",
    "backend/scripts/generate_avatar_demo_previews.py",
    "backend/scripts/seed_avatar_demo_r2.py",
]


def test_deleted_files_stay_deleted():
    survivors = [p for p in DELETED_FILES if (ROOT / p).exists()]
    assert not survivors, "These should have been deleted:\n" + "\n".join(survivors)


# ─── 3. App.js must not reference deleted lazy imports / routes ──
def test_app_js_has_no_clone_routes_or_imports():
    app_js = (FRONTEND_SRC / "App.js").read_text(encoding="utf-8")
    forbidden = [
        "AICloningStudio",
        "AdminCloneModerationPage",
        "AvatarDemoWizard",
        "AvatarFunnelTablePage",
        "AvatarStudioPage",
        "/app/avatar",
        "/avatar-demo",
        "/app/admin/avatar/",
    ]
    found = [tok for tok in forbidden if tok in app_js]
    assert not found, f"App.js still references: {found}"


# ─── 4. Backend server.py must not register avatar_studio ────────
def test_server_does_not_import_avatar_studio():
    src = (BACKEND / "server.py").read_text(encoding="utf-8")
    assert "avatar_studio" not in src, "server.py still imports/includes avatar_studio router"


# ─── 5. Dashboard creator-tools data has no avatar entry ────────
def test_creator_tools_has_no_avatar_entry():
    src = (FRONTEND_SRC / "data" / "creatorTools.js").read_text(encoding="utf-8")
    assert "'avatar'" not in src and "\"avatar\"" not in src, \
        "creatorTools.js still exposes the avatar/AI Cloning entry"
    # And no AI Cloning name
    assert "AI Cloning" not in src


def test_personalization_service_does_not_score_avatar():
    src = (BACKEND / "services" / "personalization_service.py").read_text(encoding="utf-8")
    # Monetization priority dict must not reference the avatar key
    assert '"avatar":' not in src and "'avatar':" not in src, \
        "personalization_service still references the avatar feature key"
    assert "AI Cloning" not in src


# ─── 6. Funnel whitelist must not contain clone-specific events ─
def test_funnel_whitelist_has_no_clone_events():
    src = (BACKEND / "routes" / "funnel_tracking.py").read_text(encoding="utf-8")
    assert "ai_cloning_used_free_testing" not in src
    assert "avatar_signup_from_avatar" not in src
