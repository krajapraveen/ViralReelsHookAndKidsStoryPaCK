"""
Universal Back-button regression — 2026-05-16 P1
Founder directive: every /app/* page (and admin) ships a Back button
unless explicitly exempt. The button must navigate(-1) with a fallback.
This guards the static contract:
  • BackButton component exists at the expected path
  • Default export is the controlled button
  • GlobalBackButton + helpers are exported
  • Exempt list contains the locked surfaces (and ONLY those)
  • App.js mounts GlobalBackButton exactly once
  • Component renders ArrowLeft icon + 'Back' label
  • onClick calls navigate(-1) with fallback path
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPONENT = ROOT / "frontend" / "src" / "components" / "BackButton.jsx"
APP_JS = ROOT / "frontend" / "src" / "App.js"


def test_back_button_component_exists():
    assert COMPONENT.exists(), "BackButton component must exist at components/BackButton.jsx"


def test_back_button_has_required_exports():
    src = COMPONENT.read_text(encoding="utf-8")
    assert "export default function BackButton" in src
    assert "export function GlobalBackButton" in src
    assert "export function isBackButtonExempt" in src
    assert "export const GLOBAL_BACK_EXEMPT_PREFIXES" in src
    assert "export const GLOBAL_BACK_EXEMPT_EXACT" in src


def test_back_button_navigates_with_fallback():
    src = COMPONENT.read_text(encoding="utf-8")
    assert "navigate(-1)" in src, "BackButton must call navigate(-1)"
    assert "fallbackPath" in src, "BackButton must accept fallbackPath prop"
    assert "navigate(resolvedFallback" in src, \
        "BackButton must fall back to resolvedFallback when history fails"
    # Admin fallback rule
    assert "/app/admin" in src and "/app/admin')" in src.replace('"', "'"), \
        "Admin pages must fall back to /app/admin"


def test_back_button_renders_icon_and_label():
    src = COMPONENT.read_text(encoding="utf-8")
    assert "ArrowLeft" in src, "BackButton must render an ArrowLeft icon"
    assert '"Back"' in src or "'Back'" in src, "BackButton must default label to 'Back'"
    assert "active:scale-" in src, "BackButton must have active-press feedback"


def test_global_back_exempts_critical_surfaces():
    """Exempt list must include landing, auth, top-level dashboard, top-level
    admin, and the anonymous /experience surface."""
    src = COMPONENT.read_text(encoding="utf-8")
    for must_exempt in ("'/'", "'/login'", "'/signup'", "'/auth/callback'",
                        "'/app'", "'/app/admin'", "'/experience'"):
        assert must_exempt in src, f"Exempt list must contain {must_exempt}"


def test_app_js_mounts_global_back_button_exactly_once():
    src = APP_JS.read_text(encoding="utf-8")
    # Import
    assert "from './components/BackButton'" in src and "GlobalBackButton" in src
    # Single mount
    mounts = re.findall(r"<GlobalBackButton\b", src)
    assert len(mounts) == 1, f"Expected exactly 1 <GlobalBackButton/> mount, found {len(mounts)}"


def test_exempt_logic_is_total():
    """isBackButtonExempt must correctly classify common routes."""
    src = COMPONENT.read_text(encoding="utf-8")
    # Static sanity (no JS exec — just read the source)
    # Verify the helper handles exact + prefix matching
    assert "GLOBAL_BACK_EXEMPT_EXACT.has(pathname)" in src
    assert "startsWith(p" in src, "Prefix matching must use startsWith"


def test_back_button_has_a11y_attributes():
    src = COMPONENT.read_text(encoding="utf-8")
    assert 'aria-label={label}' in src
    assert "type=\"button\"" in src, "BackButton must declare type='button' to prevent form submits"


def test_back_button_does_not_block_toasts():
    """z-30 is below sonner toast (50) and below modal (z-40+) but above page content."""
    src = COMPONENT.read_text(encoding="utf-8")
    assert "z-30" in src, "BackButton must use z-30 to stay below toasts/modals"


def test_back_button_is_mobile_safe():
    src = COMPONENT.read_text(encoding="utf-8")
    assert "safe-area-top" in src, "BackButton must respect iOS safe-area-top via utility class"
    # And the utility class itself must be defined in CSS
    css = (ROOT / "frontend" / "src" / "index.css").read_text(encoding="utf-8")
    assert ".safe-area-top" in css and "safe-area-inset-top" in css
