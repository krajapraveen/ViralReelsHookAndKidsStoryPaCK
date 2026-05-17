"""P0 2026-05-19 — Photo-to-Comic event-trap regression suite.

Locks down the production hotfix for the toast:
  "Selected comic style is not supported. Please try another style.
   Reference ID: not-captured (frontend rejected style=object)"

ROOT CAUSE the user reported:
  • The generate button was wired as `<Button onClick={handleGenerate} />`.
  • React passes a SyntheticEvent as the first argument.
  • `handleGenerate(overrideStyle = null)` did `overrideStyle || style`.
  • Because the event is truthy, it became `rawSelected` →
    `normalizeComicStyle(event)` returned null → leaky toast.

The fixes asserted by these tests:
  1. The button MUST NOT pass the click event into the handler. It must
     be wrapped as `() => handleGenerate()` (or `onClick={()=>handleGenerate()}`).
  2. `handleGenerate` MUST only honor `overrideStyle` when it is a
     non-empty string — anything else falls through to the canonical
     `style` state slot.
  3. The user-facing error toast MUST NOT leak internal jargon
     ("style=object", "frontend rejected", "not-captured", "enum",
     "validator", "object Object").
  4. The user-facing toast MUST still surface a stable Reference ID.
  5. The locked-style grid tiles MUST stay non-interactive
     (`disabled={locked}` and a tier-gated `onClick`).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

P2C = Path("/app/frontend/src/pages/PhotoToComic.js")
COMIC_STYLES = Path("/app/frontend/src/constants/comicStyles.js")


@pytest.fixture(scope="module")
def p2c_src() -> str:
    assert P2C.exists(), f"Missing source: {P2C}"
    return P2C.read_text()


def _strip_js_comments(src: str) -> str:
    """Remove // line comments and /* */ block comments so substring
    assertions only look at executable code (comments are documentation
    and may legitimately mention legacy bug patterns)."""
    out: list[str] = []
    i, n = 0, len(src)
    in_str: str | None = None
    escaped = False
    while i < n:
        c = src[i]
        if in_str:
            out.append(c)
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == in_str:
                in_str = None
            i += 1
            continue
        if c in "\"'`":
            in_str = c
            out.append(c)
            i += 1
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            i = n if j == -1 else j
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            i = n if j == -1 else j + 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


@pytest.fixture(scope="module")
def p2c_code(p2c_src: str) -> str:
    """Comment-stripped view of the source, used for regression checks
    that must not match commented-out legacy snippets."""
    return _strip_js_comments(p2c_src)


@pytest.fixture(scope="module")
def comic_styles_src() -> str:
    assert COMIC_STYLES.exists(), f"Missing source: {COMIC_STYLES}"
    return COMIC_STYLES.read_text()


# ─── 1. Event-trap fix ────────────────────────────────────────────────────

def test_generate_button_does_not_pass_event_to_handler(p2c_code: str) -> None:
    """The bare-handler wiring `onClick={handleGenerate}` is the bug.
    Must be wrapped so the SyntheticEvent never reaches the handler."""
    # The exact bug pattern: onClick={handleGenerate} with no arrow.
    bug_pattern = re.compile(r"onClick=\{handleGenerate\}")
    assert not bug_pattern.search(p2c_code), (
        "REGRESSION: The generate button is wired as onClick={handleGenerate}. "
        "React will pass the SyntheticEvent as overrideStyle and the user "
        "will see 'frontend rejected style=object'. Wrap as "
        "onClick={() => handleGenerate()}."
    )

    # And the safe pattern MUST exist next to data-testid='generate-btn'.
    # Match the <Button ...> opening tag, accounting for `=>` arrows
    # which contain a `>` inside JSX attribute values.
    btn_block = re.search(
        r"<Button\b[^>]*?(?:=>[^>]*?)*data-testid=\"generate-btn\"[^>]*?>",
        p2c_code,
        re.DOTALL,
    )
    assert btn_block, "generate-btn Button declaration not found"
    btn_text = btn_block.group(0)
    assert "onClick={() => handleGenerate()" in btn_text or \
           re.search(r"onClick=\{\(\s*\)\s*=>\s*handleGenerate\(", btn_text), (
        f"generate-btn must wrap handleGenerate in an arrow to drop the "
        f"event. Got: {btn_text}"
    )


def test_handle_generate_only_honors_string_override(p2c_code: str) -> None:
    """The defensive guard inside handleGenerate must reject non-string
    overrides so a stray event/object/null falls through to `style`."""
    assert "typeof overrideStyle === 'string'" in p2c_code, (
        "handleGenerate must explicitly check `typeof overrideStyle === "
        "'string'` before honoring the argument."
    )
    assert re.search(
        r"const\s+rawSelected\s*=\s*overrideIsString\s*\?\s*overrideStyle\s*:\s*style",
        p2c_code,
    ), (
        "handleGenerate must select `style` from React state whenever "
        "overrideStyle is not a non-empty string. The legacy "
        "`overrideStyle || style` form is the source of the bug."
    )

    # And the legacy bug pattern must be GONE from executable code.
    assert "overrideStyle || style" not in p2c_code, (
        "REGRESSION: Found the legacy `overrideStyle || style` truthiness "
        "check. Any truthy non-string (e.g., a SyntheticEvent) will poison "
        "the style payload."
    )


# ─── 2. No internal jargon leaks ──────────────────────────────────────────

# Forbidden substrings inside any `toast.error(...)` call. Internal
# diagnostics may continue to use these in `console.*` log lines.
FORBIDDEN_USER_FACING_PHRASES = (
    "frontend rejected style",
    "style=object",
    "[object Object]",
    "unsupported enum",
    "validator",
    "stack trace",
    "not-captured (frontend",
)


def _toast_error_calls(src: str) -> list[str]:
    """Return the raw argument text of every toast.error(...) call.
    Captures template literals, plain strings, and concatenations."""
    calls: list[str] = []
    i = 0
    needle = "toast.error("
    while True:
        j = src.find(needle, i)
        if j == -1:
            return calls
        # Walk balanced parens.
        depth = 0
        k = j + len(needle)
        start = k
        in_str: str | None = None
        escaped = False
        while k < len(src):
            c = src[k]
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif in_str:
                if c == in_str:
                    in_str = None
            elif c in "\"'`":
                in_str = c
            elif c == "(":
                depth += 1
            elif c == ")":
                if depth == 0:
                    calls.append(src[start:k])
                    break
                depth -= 1
            k += 1
        i = k + 1


def test_no_internal_jargon_in_user_facing_toasts(p2c_src: str) -> None:
    calls = _toast_error_calls(p2c_src)
    assert calls, "Expected at least one toast.error(...) call in PhotoToComic.js"
    offenders: list[tuple[str, str]] = []
    for arg_text in calls:
        lowered = arg_text.lower()
        for phrase in FORBIDDEN_USER_FACING_PHRASES:
            if phrase.lower() in lowered:
                offenders.append((phrase, arg_text.strip()))
    assert not offenders, (
        "Internal implementation jargon is leaking into user-facing toasts:\n"
        + "\n".join(f"  - {p!r} in: {t[:200]}" for p, t in offenders)
    )


def test_invalid_style_toast_surfaces_reference_id(p2c_src: str) -> None:
    """When the style state goes sideways, the user still gets a stable
    Reference ID so support can correlate."""
    # Find the submit-blocked recovery branch.
    block = re.search(
        r"// P0 2026-05-19[^\n]*No internal jargon[\s\S]{0,800}?toast\.error\([\s\S]*?\);",
        p2c_src,
    )
    assert block, (
        "Expected the canonical submit-blocked recovery block with a "
        "user-friendly toast and a generated Reference ID."
    )
    body = block.group(0)
    assert "Reference ID:" in body, "User-facing toast must include a Reference ID."
    assert re.search(r"refId\s*=\s*`p2c-", body), (
        "Reference ID should be a stable, prefixed token like `p2c-<...>`."
    )


# ─── 3. Locked-style tiles ────────────────────────────────────────────────

def test_locked_style_tiles_are_disabled_and_gated(p2c_src: str) -> None:
    grid = re.search(
        r"data-testid=\"style-grid\">([\s\S]*?)</div>\s*</div>",
        p2c_src,
    )
    assert grid, "style-grid block not found"
    body = grid.group(1)
    # The tile click must be tier-gated AND the button disabled when locked.
    assert "!locked && setStyle(s.id)" in body, (
        "Locked tiles must short-circuit setStyle so the canonical state "
        "slot never receives a locked id."
    )
    assert "disabled={locked}" in body, (
        "Locked tiles must render the underlying <button> with "
        "`disabled={locked}` so keyboard activation is also blocked."
    )


# ─── 4. Single canonical style registry ───────────────────────────────────

def test_only_one_comic_style_registry(comic_styles_src: str) -> None:
    """There must be exactly one COMIC_STYLES export — no duplicate
    hardcoded arrays drifting in other files."""
    assert "export const COMIC_STYLES" in comic_styles_src, (
        "constants/comicStyles.js must export COMIC_STYLES as the single "
        "source of truth."
    )
    # Sweep the whole frontend tree for stray COMIC_STYLES exports.
    other_decls: list[Path] = []
    for f in Path("/app/frontend/src").rglob("*.js"):
        if f == COMIC_STYLES:
            continue
        try:
            txt = f.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        if re.search(r"^\s*export\s+const\s+COMIC_STYLES\b", txt, re.M):
            other_decls.append(f)
    assert not other_decls, (
        "Found duplicate COMIC_STYLES exports outside the canonical "
        f"registry: {other_decls}"
    )


def test_p2c_imports_canonical_registry(p2c_src: str) -> None:
    assert "from '../constants/comicStyles'" in p2c_src, (
        "PhotoToComic.js must import the canonical style registry from "
        "constants/comicStyles."
    )
    assert "normalizeComicStyle" in p2c_src, (
        "PhotoToComic.js must run every incoming style through "
        "normalizeComicStyle() before submitting."
    )


# ─── 5. Visible build marker bumped ───────────────────────────────────────

def test_bundle_version_advanced_for_this_hotfix(p2c_src: str) -> None:
    """The visible cache-bust marker must change every hotfix so QA can
    confirm production is serving the latest bundle."""
    m = re.search(r"const\s+BUNDLE_VERSION\s*=\s*'([^']+)'", p2c_src)
    assert m, "BUNDLE_VERSION constant not found"
    version = m.group(1)
    assert version != "2026-05-19-case-b-visible-marker", (
        "BUNDLE_VERSION was not bumped for the event-trap hotfix. "
        "Bump it so users on stale bundles are visibly identifiable."
    )
    assert "event-trap" in version or "p2c-event" in version, (
        f"BUNDLE_VERSION should label this hotfix; got {version!r}."
    )
