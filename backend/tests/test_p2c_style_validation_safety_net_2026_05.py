"""
P0 2026-05-19 — Photo-to-Comic style validation drift safety net.
==================================================================
Production screenshot showed "Selected comic style is not supported.
Please try another style." on Comic Avatar + Cartoon, with the
Cartoon tile clearly selected and 159 credits in balance.

ROOT CAUSE (most likely)
------------------------
Preview/frontend code on /app correctly sends canonical keys
(`cartoon_fun` etc.). But on production, a stale browser bundle or
Service Worker cache shipped an OLDER PhotoToComic.js that submitted
the human-readable LABEL (`Cartoon`) instead of the canonical key.
The backend validator strictly checked the canonical key and threw
`INVALID_STYLE`. Founder spec also requires that visible/selectable
styles ALWAYS generate successfully — so a stale frontend must not be
able to break the user.

LOCKED-IN CONTRACT
------------------
1. Backend `_normalize_style_input` is a defense-in-depth funnel that
   accepts BOTH canonical keys AND human labels (case-insensitive).
   Each label-fallback is logged as `LABEL_FALLBACK` for ops
   visibility so we can spot stale frontends.
2. ALL 5 founder-required visible-selectable styles
   (cartoon, bold_hero, retro_pop, manga, chibi) must coerce to
   canonical keys via the label fallback, in BOTH avatar and strip
   modes.
3. Object-style serialization ("[object Object]") still rejects
   cleanly with INVALID_STYLE — the safety net only rescues genuine
   labels, not garbage.
4. Frontend `handleGenerate` emits a structured
   `[p2c/handleGenerate] style_state=` console log on every click so
   any future production failure has paste-able diagnostic.
5. Frontend INVALID_STYLE early-return toast now embeds the actual
   rejected style/type for support traceability.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "/app/backend")

from routes.photo_to_comic import (  # noqa: E402
    _normalize_style_input,
    SAFE_STYLES,
    is_style_valid_for_mode,
)


PHOTO_TO_COMIC_PY = Path("/app/backend/routes/photo_to_comic.py")
PHOTO_TO_COMIC_JS = Path("/app/frontend/src/pages/PhotoToComic.js")
COMIC_STYLES_JS = Path("/app/frontend/src/constants/comicStyles.js")


# ════════════════════════════════════════════════════════════════════════
# Backend — _normalize_style_input must accept canonical keys + labels
# ════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("canonical", [
    "cartoon_fun", "bold_superhero", "retro_action", "soft_manga", "cute_chibi",
])
def test_canonical_keys_pass_through_unchanged(canonical):
    """Canonical keys must always be returned unchanged."""
    assert _normalize_style_input(canonical) == canonical
    assert canonical in SAFE_STYLES


@pytest.mark.parametrize("label,expected_key", [
    ("Cartoon", "cartoon_fun"),
    ("Bold Hero", "bold_superhero"),
    ("Retro Pop", "retro_action"),
    ("Manga", "soft_manga"),
    ("Chibi", "cute_chibi"),
])
def test_founder_required_labels_coerce_to_canonical_keys(label, expected_key):
    """The 5 founder-required visible-selectable styles must coerce
    from their human label to the canonical key. This is the
    production safety net against stale frontend bundles."""
    assert _normalize_style_input(label) == expected_key, (
        f"Label {label!r} must coerce to {expected_key!r} — without this "
        "fallback, a stale browser bundle that ships the label trips "
        "INVALID_STYLE and produces the production toast"
    )


@pytest.mark.parametrize("label", [
    "cartoon", "CARTOON", "Cartoon", "cArToOn",  # case variants of "cartoon"
    "BOLD HERO", "bold hero", "Bold Hero",
])
def test_label_fallback_is_case_insensitive(label):
    """Labels must match regardless of casing — users / stale bundles
    can shape-shift the casing in many ways."""
    result = _normalize_style_input(label)
    # Must coerce to SOME canonical key (cartoon* labels → cartoon_fun;
    # bold hero labels → bold_superhero).
    assert result in SAFE_STYLES, (
        f"Case-variant {label!r} must coerce to a canonical key; got {result!r}"
    )


def test_unknown_label_is_NOT_coerced_returns_as_is_for_rejection():
    """Garbage that isn't a known label or key must NOT silently coerce —
    it must fall through to the SAFE_STYLES check and produce a clean
    INVALID_STYLE."""
    assert _normalize_style_input("not_a_real_style_xyz") == "not_a_real_style_xyz"
    assert "not_a_real_style_xyz" not in SAFE_STYLES


def test_object_object_literal_still_rejects_cleanly():
    """The previous serialization-bug rejection path must remain intact —
    label fallback must NOT swallow this signal."""
    assert _normalize_style_input("[object Object]") == "[object Object]"
    assert "[object Object]" not in SAFE_STYLES


def test_empty_and_none_inputs_return_empty_strings():
    assert _normalize_style_input("") == ""
    assert _normalize_style_input(None) == ""
    assert _normalize_style_input("   ") == ""


def test_json_encoded_object_still_extracted():
    """The JSON-object extraction path remains — same coverage."""
    assert _normalize_style_input('{"id":"manga"}') == "manga"
    # `manga` is NOT a canonical key on its own — extraction returns
    # what was inside the JSON; downstream SAFE_STYLES check decides.
    # If the inner value IS canonical we keep it; if not, falls through.
    assert _normalize_style_input('{"id":"cartoon_fun"}') == "cartoon_fun"


@pytest.mark.parametrize("style_key", [
    "cartoon_fun", "bold_superhero", "retro_action", "soft_manga", "cute_chibi",
])
@pytest.mark.parametrize("mode", ["avatar", "strip"])
def test_founder_required_styles_legal_in_both_modes(style_key, mode):
    """All 5 founder-required styles must be legal for BOTH modes."""
    assert is_style_valid_for_mode(style_key, mode), (
        f"Style {style_key!r} must be legal for mode={mode!r} per "
        "founder spec"
    )


# ════════════════════════════════════════════════════════════════════════
# Backend source — defensive normalizer is in place
# ════════════════════════════════════════════════════════════════════════
def test_normalizer_has_label_fallback_block():
    src = PHOTO_TO_COMIC_PY.read_text()
    fn = src.split("def _normalize_style_input", 1)[1].split("\n\ndef ", 1)[0]
    assert "LABEL_FALLBACK" in fn, (
        "Label fallback block missing — without this, a stale frontend "
        "bundle shipping labels reproduces the production INVALID_STYLE "
        "trap"
    )
    # Must log as INFO (not WARNING — this is a routine rescue, not an
    # error) so ops can track stale-bundle prevalence without noise.
    assert "logger.info" in fn


# ════════════════════════════════════════════════════════════════════════
# Frontend — diagnostic console log on every handleGenerate
# ════════════════════════════════════════════════════════════════════════
def test_handle_generate_emits_structured_diagnostic_log():
    """Every click must emit a paste-able diagnostic so the next
    production failure carries forensic info."""
    src = PHOTO_TO_COMIC_JS.read_text()
    handler = src.split("const handleGenerate = async", 1)[1].split(
        "// ─── Share", 1
    )[0]
    assert "[p2c/handleGenerate] style_state=" in handler, (
        "handleGenerate must emit a structured `style_state=` console "
        "log on every click for production forensics"
    )
    # Must include the actually-shipped fields the founder asked for.
    for field in ("raw", "normalized", "mode", "available_keys"):
        assert field in handler, (
            f"diagnostic log must include {field!r} field"
        )


def test_frontend_invalid_style_toast_embeds_rejection_context():
    """When the frontend itself rejects (normalize returns null), the
    toast must include the actual rejected style/type for support."""
    src = PHOTO_TO_COMIC_JS.read_text()
    handler = src.split("const handleGenerate = async", 1)[1].split(
        "// ─── Share", 1
    )[0]
    # The pre-await early-return toast carries forensic context.
    assert "frontend rejected style=" in handler, (
        "Frontend INVALID_STYLE early-return toast must include the "
        "rejected style value so support can triage stale-bundle cases"
    )
    assert "FRONTEND_INVALID_STYLE" in handler, (
        "Frontend console.error key must be greppable"
    )


def test_canonical_keys_match_mirror_match_backend():
    """The hardcoded frontend mirror (used as fallback when the catalog
    fetch fails) must be a strict subset of the backend SAFE_STYLES
    `enabled: True` entries — otherwise the fallback ships keys the
    backend rejects."""
    src = COMIC_STYLES_JS.read_text()
    # Extract the keys from the COMIC_STYLES mirror via regex.
    matches = re.findall(r"key:\s*'([^']+)'", src)
    assert matches, "Could not extract any keys from mirror"
    enabled_keys = {k for k, m in SAFE_STYLES.items() if m.get("enabled", True)}
    for key in matches:
        assert key in enabled_keys, (
            f"Mirror key {key!r} is NOT in backend SAFE_STYLES enabled set "
            "→ frontend fallback would ship a key the backend rejects"
        )


# ════════════════════════════════════════════════════════════════════════
# Acceptance — the 5 founder-required styles work in BOTH modes via
# canonical key OR label
# ════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("input_value,expected_key", [
    # Canonical keys
    ("cartoon_fun", "cartoon_fun"),
    ("bold_superhero", "bold_superhero"),
    ("retro_action", "retro_action"),
    ("soft_manga", "soft_manga"),
    ("cute_chibi", "cute_chibi"),
    # UI labels (stale bundle safety net)
    ("Cartoon", "cartoon_fun"),
    ("Bold Hero", "bold_superhero"),
    ("Retro Pop", "retro_action"),
    ("Manga", "soft_manga"),
    ("Chibi", "cute_chibi"),
])
@pytest.mark.parametrize("mode", ["avatar", "strip"])
def test_acceptance_matrix_styles_x_modes(input_value, expected_key, mode):
    """The full founder acceptance matrix: 5 styles × 2 input forms
    (key + label) × 2 modes (avatar + strip) = 20 combinations. ALL
    must produce a valid canonical key that is legal for the mode."""
    coerced = _normalize_style_input(input_value)
    assert coerced == expected_key, (
        f"input={input_value!r} must coerce to {expected_key!r}; got {coerced!r}"
    )
    assert is_style_valid_for_mode(coerced, mode), (
        f"key={coerced!r} must be legal for mode={mode!r}"
    )
