"""
P0 2026-05-19 CASE B — Photo-to-Comic frontend object-state hotfix.
=====================================================================
Production CASE B screenshot:
  Toast: "Selected comic style is not supported. Please try another
         style. Reference ID: not-captured (frontend rejected style=object)"
  Mode:  Comic Avatar
  Tile:  Chibi (selected)

Root cause (frontend):
  The `style` state slot held a non-string value (a tile object) when
  the user clicked Generate. The previous `normalizeComicStyle()` only
  extracted from `input.key` — production tile objects shaped
  `{id, name, color, tier}` had no `key` field → rejected → toast.

Surgical fix (this file pins the contract):
  1. `normalizeComicStyle()` extracts from key / id / value / slug /
     apiValue / style and also retries label coercion against
     name / label. Logs `OBJECT_FALLBACK` on rescue and
     `OBJECT_REJECTED` on true garbage.
  2. `setStyle` in PhotoToComic is wrapped — non-string writes are
     coerced through `normalizeComicStyle()` before touching state.
  3. Pre-submit invariant: if the normalized value is not a non-empty
     string, auto-recover by re-selecting the first available style
     for the current mode (so the user doesn't have to reload).
  4. Bundle version constant exported on every diagnostic log so
     stale-bundle / SW-cache cases are immediately identifiable.

These tests run the JS source directly via `node -e` so we don't have
to stand up Jest. The contracts are sourced from /app/frontend/src
and asserted as-is.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


COMIC_STYLES_JS = Path("/app/frontend/src/constants/comicStyles.js")
PHOTO_TO_COMIC_JS = Path("/app/frontend/src/pages/PhotoToComic.js")


def _run_normalizer(input_repr: str) -> str | None:
    """Invoke normalizeComicStyle() in node against the live source.

    `input_repr` is a JS expression (e.g. `"chibi"`, `{ id: 'chibi' }`,
    `null`). We re-read the source on every call so the test always
    reflects the latest implementation.
    """
    src = COMIC_STYLES_JS.read_text()
    # Strip the `import api from ...` line (we don't need the api
    # client for the pure-JS normalizer) and the `export` keywords so
    # the file can be eval'd in a script sandbox.
    import re
    src = re.sub(r"^import\s+.*?from\s+.*?;\s*$", "", src, flags=re.M)
    src = re.sub(r"^export\s+", "", src, flags=re.M)
    script = (
        # Suppress console.* output so it doesn't pollute stdout (tests
        # read stdout for the JSON result).
        "console.info = console.warn = console.error = console.log = () => {};\n"
        + src
        + "\n;const __raw__ = " + input_repr + ";"
        + "\n;const __out__ = normalizeComicStyle(__raw__);"
        + "\n;process.stdout.write(JSON.stringify(__out__ === undefined ? null : __out__));"
    )
    proc = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"node runner failed: rc={proc.returncode}\n"
            f"stdout={proc.stdout}\nstderr={proc.stderr[:500]}"
        )
    return json.loads(proc.stdout)


# ════════════════════════════════════════════════════════════════════════
# normalizeComicStyle — object input rescue (the CASE B fix)
# ════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("expr,expected", [
    # The most common production-tile shapes — these were ALL rejected
    # before the hotfix because they lack a `key` field.
    ("{ id: 'cute_chibi' }",                 "cute_chibi"),
    ("{ id: 'cartoon_fun' }",                "cartoon_fun"),
    ("{ id: 'bold_superhero' }",             "bold_superhero"),
    ("{ id: 'soft_manga' }",                 "soft_manga"),
    ("{ id: 'retro_action' }",               "retro_action"),
    # Other field-name shapes that legacy bundles might serialize.
    ("{ value: 'cartoon_fun' }",             "cartoon_fun"),
    ("{ slug: 'soft_manga' }",               "soft_manga"),
    ("{ apiValue: 'cute_chibi' }",           "cute_chibi"),
    # The original `key` path still works (no regression).
    ("{ key: 'cartoon_fun' }",               "cartoon_fun"),
    # Tile shape with a LABEL in the id field (worst case).
    ("{ id: 'Chibi' }",                      "cute_chibi"),
    ("{ id: 'Cartoon' }",                    "cartoon_fun"),
    # Tile shape that puts label in name/label only.
    ("{ name: 'Chibi', color: 'pink' }",     "cute_chibi"),
    ("{ label: 'Bold Hero' }",               "bold_superhero"),
])
def test_object_inputs_coerce_to_canonical_keys(expr, expected):
    """The CASE B core contract: tile-object inputs must coerce."""
    assert _run_normalizer(expr) == expected, (
        f"object input {expr!r} must coerce to {expected!r} — without "
        "this rescue, production reproduces 'frontend rejected style=object'"
    )


@pytest.mark.parametrize("expr", [
    "{ color: '#fff', tier: 'free' }",   # no id-like fields at all
    "{ id: 'not_a_real_style' }",         # unknown id, no label match
    "{ id: 42 }",                         # non-string id
    "{ name: 'Garbage Name' }",           # unknown label
    "{}",                                  # empty object
])
def test_object_inputs_without_id_or_label_still_reject_cleanly(expr):
    """Garbage objects must still produce null — the rescue must NOT
    silently coerce things that genuinely have nothing to rescue."""
    assert _run_normalizer(expr) is None, (
        f"object input {expr!r} has no valid id/label → must reject "
        "with null so the pre-submit invariant fires"
    )


# ════════════════════════════════════════════════════════════════════════
# String inputs — no regression
# ════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("expr,expected", [
    ("'cartoon_fun'",       "cartoon_fun"),
    ("'cute_chibi'",        "cute_chibi"),
    ("'Cartoon'",           "cartoon_fun"),    # label fallback
    ("'Chibi'",             "cute_chibi"),
    ("'Bold Hero'",         "bold_superhero"),
    ("'   cartoon_fun  '",  "cartoon_fun"),    # trimmed
    ("''",                  None),
    ("'not_real'",          None),
    ("null",                None),
    ("undefined",           None),
])
def test_string_inputs_unchanged(expr, expected):
    assert _run_normalizer(expr) == expected


# ════════════════════════════════════════════════════════════════════════
# Source-level — frontend wrappers are in place
# ════════════════════════════════════════════════════════════════════════
def test_set_style_is_wrapped_to_reject_non_strings():
    """The setStyle wrapper guarantees the state slot is always a string,
    even if a legacy click handler accidentally passes the whole tile."""
    src = PHOTO_TO_COMIC_JS.read_text()
    assert "const [style, _setStyleRaw] = useState" in src, (
        "useState must expose the raw setter under an underscored name"
    )
    assert "const setStyle = useCallback((value) =>" in src, (
        "setStyle must be wrapped to coerce non-string writes"
    )
    # The wrapper must call normalizeComicStyle on non-string inputs.
    handler = src.split("const setStyle = useCallback", 1)[1].split(
        "}, []);", 1
    )[0]
    assert "normalizeComicStyle(value)" in handler, (
        "Wrapper must funnel non-strings through normalizeComicStyle"
    )
    # And reject what can't be coerced.
    assert "[p2c/setStyle] rejected non-string write" in handler


def test_handle_generate_has_invariant_with_auto_recovery():
    """When the normalized value isn't a non-empty string, the
    pre-submit invariant must fire AND auto-recover (re-select first
    available style) so the user doesn't have to reload."""
    src = PHOTO_TO_COMIC_JS.read_text()
    handler = src.split("const handleGenerate = async", 1)[1].split(
        "// ─── Share", 1
    )[0]
    assert "[p2c/submit-blocked] invalid_style_state" in handler, (
        "Pre-submit invariant must emit the structured submit-blocked log"
    )
    # Required diagnostic fields per founder spec.
    for f in ("raw_type", "raw_value", "selectedStyleId", "mode",
              "available_keys", "bundle_version"):
        assert f in handler, f"submit-blocked log missing field {f!r}"
    # Auto-recovery: must call setStyle with a string id.
    assert "setStyle(recovery.id)" in handler, (
        "Auto-recovery must re-select the first available style for "
        "the current mode"
    )


def test_bundle_version_constant_is_present_and_logged():
    """The bundle version is the only reliable way to tell production
    apart from a stale Service Worker / CDN cache. Every diagnostic
    log on the generate path must include it."""
    src = PHOTO_TO_COMIC_JS.read_text()
    assert "const BUNDLE_VERSION = '2026-05-19-case-b-" in src, (
        "BUNDLE_VERSION must be bumped to a case-b identifier so "
        "production logs can tell the new bundle from the old"
    )
    # And the diagnostic log on every Generate click must include it.
    handler = src.split("const handleGenerate = async", 1)[1].split(
        "// ─── Share", 1
    )[0]
    assert "bundle_version: BUNDLE_VERSION" in handler


def test_normalizer_logs_object_fallback_for_ops_visibility():
    """When the normalizer rescues an object input, it must log
    OBJECT_FALLBACK so ops can spot stale-bundle prevalence over time."""
    src = COMIC_STYLES_JS.read_text()
    fn = src.split("export function normalizeComicStyle", 1)[1].split(
        "\nexport function ", 1
    )[0]
    assert "OBJECT_FALLBACK" in fn, (
        "Normalizer must log OBJECT_FALLBACK on successful object rescue"
    )
    assert "OBJECT_REJECTED" in fn, (
        "Normalizer must log OBJECT_REJECTED on hopeless object input"
    )
    # Must check the full canonical id field-name set.
    for field in ("key", "id", "value", "slug", "apiValue", "style"):
        assert f"'{field}'" in fn, (
            f"Normalizer must check object field {field!r}"
        )
