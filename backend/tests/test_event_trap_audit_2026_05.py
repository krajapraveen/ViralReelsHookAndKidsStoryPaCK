"""
P1 2026-05-19 — Codebase-wide event-trap audit.

Scans the entire frontend source tree and asserts that NO React event
handler with a non-event default-arg signature is bare-wired into a
DOM event prop. The bug we're freezing out forever:

    const handleX = async (overrideStyle = null) => { ... };
    ...
    <Button onClick={handleX} />        // ← React passes SyntheticEvent
                                        //   as overrideStyle → poison.

Safe forms (which the audit allows):
    onClick={() => handleX()}           // arrow drops the event
    onClick={() => handleX('twist')}    // explicit string arg
    onClick={handleX}                   // ONLY if handleX takes () or (e)

This test is the long-term insurance policy for the Photo-to-Comic
"frontend rejected style=object" bug class.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

FRONTEND_SRC = Path("/app/frontend/src")

# DOM event props that React will pass a SyntheticEvent into when wired
# with a bare handler reference.
DOM_EVENT_PROPS = (
    "onClick",
    "onMouseDown",
    "onMouseUp",
    "onPointerDown",
    "onPointerUp",
    "onKeyDown",
    "onKeyUp",
    "onKeyPress",
    "onTouchEnd",
    "onTouchStart",
    "onChange",
    "onFocus",
    "onBlur",
    "onInput",
    "onSubmit",
)

# Pattern: `prop={handlerName}` (no arrow, no extra parens). Captures
# the prop name, the handler name, and the surrounding file position.
_BARE_HANDLER_RE = re.compile(
    r"\b(?P<prop>" + "|".join(DOM_EVENT_PROPS) + r")=\{(?P<handler>handle[A-Z][A-Za-z0-9_]*)\}"
)

# Handler signature pattern. Matches:
#   const handleX = (
#   const handleX = async (
#   const handleX = useCallback((
# and captures the first parameter declaration (or empty string).
_HANDLER_DECL_RE = re.compile(
    r"const\s+(?P<name>handle[A-Z][A-Za-z0-9_]*)\s*=\s*"
    r"(?:useCallback\(\s*)?(?:async\s*)?\(\s*(?P<params>[^)]*)\)"
)


def _all_frontend_files() -> list[Path]:
    files: list[Path] = []
    for ext in ("*.js", "*.jsx", "*.ts", "*.tsx"):
        files.extend(FRONTEND_SRC.rglob(ext))
    # Ignore build artifacts and node_modules just in case.
    return [
        f for f in files
        if "node_modules" not in f.parts and "build" not in f.parts
    ]


def _strip_comments(src: str) -> str:
    """Strip both `/* ... */` block comments and `// ...` line comments.
    Naive but adequate for our static-analysis needs."""
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


def _first_param_is_event_or_empty(params: str) -> tuple[bool, str]:
    """Return (is_safe, first_param_name)."""
    params = params.strip()
    if not params:
        return True, ""
    # Split on top-level commas (no destructuring nesting expected here).
    first = params.split(",", 1)[0].strip()
    if not first:
        return True, ""
    # Strip TS type annotation.
    if ":" in first:
        first = first.split(":", 1)[0].strip()
    # Has default? Then it's UNSAFE when bare-wired.
    if "=" in first:
        return False, first
    name_match = re.match(r"\{?\s*([a-zA-Z_$][\w$]*)", first)
    name = name_match.group(1) if name_match else first
    # Conventional event names are safe (handler explicitly expects event).
    if name in ("e", "event", "evt", "ev", "_e", "_event"):
        return True, name
    return False, name


def _scan_file(path: Path) -> tuple[dict[str, list[str]], list[tuple[str, str, int]]]:
    """Return ({handlerName: [params, ...]}, [(prop, handlerName, line_no), ...]).

    A handler can be declared more than once in a single file (a parent
    component and a nested sub-component both naming `handleSave`, etc).
    We keep ALL decls so the audit can correctly classify the wiring
    as safe-if-any-decl-is-safe.
    """
    raw = path.read_text(errors="replace")
    src = _strip_comments(raw)
    handlers: dict[str, list[str]] = {}
    for m in _HANDLER_DECL_RE.finditer(src):
        handlers.setdefault(m.group("name"), []).append(m.group("params"))
    bare: list[tuple[str, str, int]] = []
    for m in _BARE_HANDLER_RE.finditer(src):
        prop = m.group("prop")
        h = m.group("handler")
        line_no = src.count("\n", 0, m.start()) + 1
        bare.append((prop, h, line_no))
    return handlers, bare


def _build_global_handler_index() -> dict[str, list[str]]:
    """Global name → [param-decl, ...] across the whole codebase. Used
    only when a bare wiring cannot resolve the handler locally (cross-file
    prop drilling)."""
    idx: dict[str, list[str]] = {}
    for f in _all_frontend_files():
        try:
            handlers, _ = _scan_file(f)
        except Exception:  # noqa: BLE001
            continue
        for name, params_list in handlers.items():
            idx.setdefault(name, []).extend(params_list)
    return idx


@pytest.fixture(scope="module")
def global_index() -> dict[str, list[str]]:
    return _build_global_handler_index()


def test_no_unsafe_bare_handler_wirings(global_index: dict[str, list[str]]) -> None:
    """The audit: every `<X onClick={handlerName}>` must reference a
    handler whose first parameter is empty or named like an event. A
    handler name with MULTIPLE decls is treated as safe if ANY decl
    matches the safe signature (covers nested sub-components that
    shadow a parent handler name)."""
    offenders: list[str] = []
    for path in _all_frontend_files():
        handlers, bare = _scan_file(path)
        for prop, handler_name, line in bare:
            params_list = handlers.get(handler_name)
            if not params_list:
                # Fall back to the global index for cross-file references.
                params_list = global_index.get(handler_name)
            if not params_list:
                continue
            any_safe = any(
                _first_param_is_event_or_empty(p)[0] for p in params_list
            )
            if any_safe:
                continue
            # Every decl is unsafe — flag.
            offenders.append(
                f"{path.relative_to(FRONTEND_SRC)}:{line}  "
                f"{prop}={{{handler_name}}}  "
                f"unsafe param signatures: {params_list!r}"
            )
    assert not offenders, (
        "EVENT-TRAP AUDIT FAILED. The following bare handler wirings "
        "will leak React SyntheticEvents into handler logic:\n"
        + "\n".join(f"  - {o}" for o in offenders)
        + "\n\nFix each by wrapping the call in an arrow:\n"
        + "  onClick={() => handlerName()}  // drops the event\n"
        + "or rename the handler's first parameter to `e` / `event` if "
        + "it really does want the event."
    )


def test_event_trap_audit_self_finds_known_safe_patterns(global_index: dict[str, str]) -> None:
    """Sanity check: the audit MUST classify the well-known safe
    patterns as safe. If this regresses, the regex is too aggressive."""
    # PhotoToComic's fixed wiring uses `() => handleGenerate()` and is
    # not bare-wired. Confirm the audit doesn't flag the file.
    photo = FRONTEND_SRC / "pages" / "PhotoToComic.js"
    handlers, bare = _scan_file(photo)
    # We expect NO bare wiring of `handleGenerate` (the fix removed it).
    assert not any(h == "handleGenerate" for _, h, _ in bare), (
        "PhotoToComic.js must NOT bare-wire handleGenerate"
    )


def test_event_trap_audit_detects_simulated_regression(tmp_path) -> None:
    """If a future contributor reintroduces the bug, the audit must
    catch it. We synthesize a single file in memory and assert the
    audit machinery flags the unsafe pattern."""
    src = (
        "const handleX = async (overrideStyle = null) => {};\n"
        "function App() { return <button onClick={handleX} />; }\n"
    )
    f = tmp_path / "Bug.jsx"
    f.write_text(src)
    handlers, bare = _scan_file(f)
    assert "handleX" in handlers
    assert ("onClick", "handleX", 2) in bare or any(
        prop == "onClick" and h == "handleX" for prop, h, _ in bare
    )
    is_safe, first = _first_param_is_event_or_empty(handlers["handleX"][0])
    assert not is_safe, "Audit must mark `(overrideStyle = null)` as UNSAFE"
    assert "overrideStyle" in first


# ─── Specific primary CTA coverage ────────────────────────────────────────

PRIMARY_CTA_TESTIDS = (
    ("pages/PhotoToComic.js", "generate-btn"),
    ("pages/ComicStorybookBuilder.js", "generate-btn"),
    ("pages/StoryVideoPipeline.js", "generate-btn"),
    # YouStar trailer build button (the page name maps to PhotoTrailerPage).
    ("pages/PhotoTrailerPage.jsx", "trailer-download-btn"),
    ("pages/BedtimeStoryBuilder.js", "generate-btn"),
)


def test_primary_cta_buttons_are_not_bare_wired() -> None:
    """For every primary CTA testid, the surrounding <Button|button>
    declaration MUST NOT use a bare `onClick={handlerName}` form
    UNLESS that handler is provably safe (zero args or `(e)` first param)."""
    failures = []
    for rel, testid in PRIMARY_CTA_TESTIDS:
        path = FRONTEND_SRC / rel
        if not path.exists():
            continue
        src = _strip_comments(path.read_text())
        pattern = (
            r"<(?:Button|button)\b[^>]*?(?:=>[^>]*?)*?data-testid=\"" +
            re.escape(testid) +
            r"\"[^>]*?>"
        )
        m = re.search(pattern, src, re.DOTALL)
        if not m:
            continue
        tag = m.group(0)
        bad = re.search(r"\bonClick=\{(handle[A-Z][A-Za-z0-9_]*)\}", tag)
        if bad:
            handler_name = bad.group(1)
            handlers, _ = _scan_file(path)
            params_list = handlers.get(handler_name) or []
            any_safe = any(
                _first_param_is_event_or_empty(p)[0] for p in params_list
            )
            if not any_safe:
                failures.append(
                    f"{rel} testid={testid} bare-wired UNSAFE handler "
                    f"{handler_name}: params={params_list!r}"
                )
    assert not failures, (
        "Primary CTAs MUST wrap their handlers in an arrow to drop the "
        "click event:\n" + "\n".join(f"  - {f}" for f in failures)
    )


# ─── Shared reliability utilities exist ───────────────────────────────────

def test_event_trap_guard_util_exists() -> None:
    p = FRONTEND_SRC / "utils" / "eventTrapGuard.js"
    assert p.exists(), "Missing shared dropEventArg utility"
    body = p.read_text()
    assert "export function dropEventArg" in body
    assert "looksLikeReactEvent" in body
    assert "frontend_event_trap_blocked_total" in body


def test_toast_safe_util_exists_and_strips_jargon() -> None:
    p = FRONTEND_SRC / "utils" / "toastSafe.js"
    assert p.exists(), "Missing shared toastErrorSafe utility"
    body = p.read_text()
    assert "export function toastErrorSafe" in body
    for phrase in (
        "frontend rejected",
        "style=object",
        "[object Object]",
        "unsupported enum",
        "validator",
        "stack trace",
    ):
        assert phrase in body, (
            f"toastSafe must scrub {phrase!r} from user-facing messages"
        )
    assert "error_toast_without_request_id_total" in body
    assert "Reference ID" in body


def test_build_info_util_exists() -> None:
    p = FRONTEND_SRC / "utils" / "buildInfo.js"
    assert p.exists()
    body = p.read_text()
    assert "BUILD_HASH" in body


def test_api_client_sends_build_header() -> None:
    p = FRONTEND_SRC / "utils" / "api.js"
    body = p.read_text()
    assert "X-Frontend-Build" in body, (
        "api.js must stamp X-Frontend-Build header on every request "
        "so backend logs can correlate stale-bundle reports."
    )
    assert "BUILD_HASH" in body
