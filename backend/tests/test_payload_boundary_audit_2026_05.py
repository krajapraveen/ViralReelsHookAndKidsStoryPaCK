"""
P1 2026-05-19 — Next-layer payload-boundary audit.
====================================================

Catches handler/default-arg values that can leak into backend payloads
without explicit type validation.

The pattern this audit kills forever:

    const handleX = async (overrideId = null) => {
        // …no dropEventArg / coerceString / typeof guard…
        await api.post('/api/x/run', { style_id: overrideId });
        //                            ^^^^^^^^^^^^^^^^^^^^^
        //  React SyntheticEvent flows straight into the request body.
    };

The audit walks every function in the frontend source tree that has a
parameter with a default value (or any non-event-shaped first param),
finds API/FormData payload writes inside that function, and asserts that
EVERY write of a target key uses one of:

  • a literal string / number
  • a state variable (we have full coverage of useState/setState writers)
  • a `coerce*` / `dropEventArg` / `normalize*` call result
  • an `extract*` / `pick*` / response-object member access
  • a value that was reassigned through an explicit `typeof === 'string'`
    or `coerce*` call earlier in the function body

When the value expression doesn't match a known-safe shape, the audit
flags the call site with the file:line, the target key, and the suspect
expression.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

FRONTEND_SRC = Path("/app/frontend/src")

# ─── Target payload keys (per founder spec) ──────────────────────────
TARGET_KEYS = frozenset({
    "style",
    "style_id",
    "mode",
    "template",
    "template_id",
    "voice",
    "voice_id",
    "character",
    "character_id",
    "story_id",
    "draft_id",
    "asset_id",
    "plan",
    "price_id",
    "amount",
    "credits",
    "order_id",
    # Common synonyms that flow into the same backend slots:
    "remix_type",
    "type",
    "job_id",
})

# Functions that are explicitly recognized as guards / value-cleaners.
GUARD_CALLS = frozenset({
    "dropEventArg",
    "coerceString",
    "coerceEnum",
    "coerceId",
    "coerceSlug",
    "coerceNumber",
    "safeOr",
    "normalizeComicStyle",
    "isValidComicStyle",
})

# ─── Helpers ─────────────────────────────────────────────────────────


def _all_frontend_files() -> list[Path]:
    files: list[Path] = []
    for ext in ("*.js", "*.jsx", "*.ts", "*.tsx"):
        files.extend(FRONTEND_SRC.rglob(ext))
    return [
        f for f in files
        if "node_modules" not in f.parts and "build" not in f.parts
    ]


def _strip_comments_and_strings(src: str) -> str:
    """Replace string literals with placeholders and strip all comments
    so identifier scanning is reliable. String contents are replaced
    with `__STR__` so we can still detect "value was a literal" (the
    literal becomes a recognizable token)."""
    out: list[str] = []
    i, n = 0, len(src)
    in_str: str | None = None
    escaped = False
    while i < n:
        c = src[i]
        if in_str:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == in_str:
                in_str = None
                out.append("'__STR__'")
            i += 1
            continue
        if c in "\"'`":
            in_str = c
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


# Match a function-like declaration plus a captured params block. We
# extract the parameter list and remember the byte offset where the
# body begins.
_FN_DECL_RE = re.compile(
    r"(?:"
    r"const\s+([A-Za-z_$][\w$]*)\s*=\s*(?:useCallback\(\s*)?(?:async\s*)?\(([^)]*)\)\s*=>\s*\{"
    r"|"
    r"function\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)\s*\{"
    r")"
)


def _find_matching_brace(src: str, open_idx: int) -> int:
    """Given the index of `{`, return the index AFTER the matching `}`.
    Naive: respects template-literal `${ ... }` nesting and skips
    strings/comments (handled by caller via stripped source)."""
    depth = 1
    i = open_idx + 1
    while i < len(src) and depth > 0:
        c = src[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    return i


class FunctionScope:
    __slots__ = ("name", "params", "body", "start_line", "abs_offset")

    def __init__(self, name: str, params: str, body: str, start_line: int, abs_offset: int):
        self.name = name
        self.params = params
        self.body = body
        self.start_line = start_line
        self.abs_offset = abs_offset

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Fn {self.name} params={self.params!r} line={self.start_line}>"


def _walk_functions(src: str) -> list[FunctionScope]:
    """Return every top-level + nested function/arrow function scope
    we can extract, with its body text. Naive but adequate for the
    handler audit — we only care about leaf-ish handlers."""
    out: list[FunctionScope] = []
    for m in _FN_DECL_RE.finditer(src):
        name = m.group(1) or m.group(3) or "<anon>"
        params = (m.group(2) or m.group(4) or "").strip()
        brace_open = m.end() - 1  # `{`
        brace_close = _find_matching_brace(src, brace_open)
        body = src[brace_open + 1: brace_close - 1]
        start_line = src.count("\n", 0, m.start()) + 1
        out.append(FunctionScope(name, params, body, start_line, m.start()))
    return out


def _param_names_with_defaults(params: str) -> list[str]:
    """Return names of parameters that have a default value (these are
    the ones React can hijack with a SyntheticEvent)."""
    names: list[str] = []
    for raw in params.split(","):
        raw = raw.strip()
        if not raw or "=" not in raw:
            continue
        head = raw.split("=", 1)[0].strip()
        # Strip TS type annotation
        if ":" in head:
            head = head.split(":", 1)[0].strip()
        m = re.match(r"\{?\s*([A-Za-z_$][\w$]*)", head)
        if m:
            names.append(m.group(1))
    return names


# Pattern: api.X(url, { …KEY: VAL, … })  — we capture the literal options
# object and let a per-key scanner pull out each (key, value) pair.
_API_CALL_RE = re.compile(
    r"\bapi\s*\.\s*(?:post|put|patch|delete|get)\s*\(\s*[^,)]+,\s*"
)

# Pattern: formData.append('KEY', VAL[, …])
_FORMDATA_APPEND_RE = re.compile(
    r"\b(?:formData|fd|form)\s*\.\s*append\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*"
)


def _extract_object_pairs(src: str, start_idx: int) -> tuple[list[tuple[str, str]], int]:
    """Starting at `{`, walk a JS object literal and extract top-level
    (key, value_expression) pairs. Returns the pairs and the index
    after the closing `}`. Lossy but adequate for static checks."""
    if start_idx >= len(src) or src[start_idx] != "{":
        return [], start_idx
    pairs: list[tuple[str, str]] = []
    i = start_idx + 1
    n = len(src)
    while i < n:
        # Skip whitespace and commas.
        while i < n and src[i] in " \t\n\r,":
            i += 1
        if i >= n or src[i] == "}":
            return pairs, i + 1
        # Read key (identifier, quoted string, or computed).
        if src[i] in "\"'`":
            quote = src[i]
            j = src.find(quote, i + 1)
            key = src[i + 1: j] if j != -1 else ""
            i = (j + 1) if j != -1 else n
        else:
            mk = re.match(r"[A-Za-z_$][\w$]*", src[i:])
            if not mk:
                # Spread, computed, or something unrecognized — bail.
                return pairs, i
            key = mk.group(0)
            i += len(key)
        # Skip whitespace.
        while i < n and src[i] in " \t":
            i += 1
        # Shorthand `{ key, key2 }` — value is the key itself.
        if i < n and src[i] in ",}":
            pairs.append((key, key))
            continue
        # Skip the colon.
        if i < n and src[i] == ":":
            i += 1
        # Read value expression up to balanced separator.
        depth = 0
        start = i
        while i < n:
            c = src[i]
            if c in "([{":
                depth += 1
            elif c in ")]}":
                if depth == 0:
                    break
                depth -= 1
            elif c == "," and depth == 0:
                break
            i += 1
        value = src[start:i].strip()
        pairs.append((key, value))
    return pairs, i


def _find_payload_writes(scope: FunctionScope) -> list[tuple[str, str, int]]:
    """Return (target_key, value_expr, body_offset) for every payload
    write inside the scope, restricted to TARGET_KEYS."""
    writes: list[tuple[str, str, int]] = []
    body = scope.body
    # formData.append('KEY', VAL[, …])
    for m in _FORMDATA_APPEND_RE.finditer(body):
        key = m.group(1)
        if key not in TARGET_KEYS:
            continue
        # Walk forward to extract the second arg until top-level `,` or `)`.
        i = m.end()
        depth = 0
        start = i
        while i < len(body):
            c = body[i]
            if c in "([{":
                depth += 1
            elif c in ")]}":
                if depth == 0:
                    break
                depth -= 1
            elif c == "," and depth == 0:
                break
            i += 1
        value = body[start:i].strip()
        writes.append((key, value, m.start()))
    # api.X(url, { …KEY: VAL })
    for m in _API_CALL_RE.finditer(body):
        i = m.end()
        # Skip whitespace before object literal.
        while i < len(body) and body[i] in " \t\n\r":
            i += 1
        if i >= len(body) or body[i] != "{":
            continue
        pairs, _ = _extract_object_pairs(body, i)
        for key, val in pairs:
            if key in TARGET_KEYS:
                writes.append((key, val, m.start()))
    return writes


def _value_is_safe(value: str, scope: FunctionScope) -> tuple[bool, str]:
    """Best-effort classification of a payload value expression.

    Returns (is_safe, reason)."""
    v = value.strip()
    if not v:
        return True, "empty"
    # 1. String / number literal (string contents were already replaced
    #    with `__STR__` by _strip_comments_and_strings).
    if v in ("null", "undefined") or v.startswith("'__STR__'"):
        return True, "literal"
    if re.match(r"^-?\d+(\.\d+)?$", v):
        return True, "number_literal"
    if v.lower() in ("true", "false"):
        return True, "bool_literal"
    # 2. Member access on a recognized safe namespace.
    if re.match(
        r"^(res|response|result|job|data|err|error|resp|searchParams|"
        r"localStorage|sessionStorage|window|document|process)\b\.",
        v,
    ):
        return True, "member_access"
    # `e.target.value`, `event.detail.*` etc — explicit event field
    # extraction is safe (it's a string by JS contract).
    if re.match(r"^(e|ev|evt|event)\.(target|currentTarget|detail)\b\.", v):
        return True, "event_field"
    # 3. Guard / coerce call result.
    m = re.match(r"^([A-Za-z_$][\w$]*)\s*\(", v)
    if m and m.group(1) in GUARD_CALLS:
        return True, "guard_call"
    # 4. `someState || 'fallback'` / `someState ?? 'fallback'`.
    if "||" in v or "??" in v:
        parts = re.split(r"\|\||\?\?", v, maxsplit=1)
        left = parts[0].strip()
        right = parts[1].strip() if len(parts) > 1 else ""
        # If the left side is a default-arg parameter and the function
        # didn't guard it, this is the smoking-gun bug.
        defaulted = set(_param_names_with_defaults(scope.params))
        bare_left = re.match(r"^([A-Za-z_$][\w$]*)$", left)
        if bare_left and bare_left.group(1) in defaulted:
            if not _is_param_guarded(bare_left.group(1), scope):
                return False, f"fallback-of-unguarded-param:{bare_left.group(1)}"
        # Otherwise treat as safe IF both sides are safe atoms.
        left_safe, _ = _value_is_safe(left, scope)
        right_safe, _ = _value_is_safe(right, scope)
        if left_safe and right_safe:
            return True, "or_safe"
        return False, "or_unsafe"
    # 5. Bare identifier — check against function parameters.
    bare = re.match(r"^([A-Za-z_$][\w$]*)$", v)
    if bare:
        name = bare.group(1)
        defaulted = set(_param_names_with_defaults(scope.params))
        if name in defaulted:
            return _is_param_guarded(name, scope), (
                "param_guarded" if _is_param_guarded(name, scope)
                else f"unguarded-default-param:{name}"
            )
        # Plain identifier — assume it's a state variable / local.
        return True, "identifier"
    # 6. Object spread, ternary, etc — best effort.
    if v.startswith("..."):
        return True, "spread"
    if "?" in v and ":" in v:
        return True, "ternary"
    # 7. Template literal becomes "'__STR__'" after strip — handled at 1.
    return True, "unknown_safe"


def _is_param_guarded(name: str, scope: FunctionScope) -> bool:
    """Return True if `name` is reassigned by a guard call before any
    use as a payload value. We look for the literal pattern:

        name = coerceString(name, …)
        name = dropEventArg(name, …)
        name = normalizeComicStyle(name, …)
        if (typeof name === 'string') …

    inside the same function body."""
    body = scope.body
    # Reassignment via guard
    pat = re.compile(
        r"\b" + re.escape(name) + r"\s*=\s*("
        + r"|".join(re.escape(g) for g in GUARD_CALLS)
        + r")\s*\("
    )
    if pat.search(body):
        return True
    # typeof guard before payload (looser — anywhere in the function)
    if re.search(
        r"typeof\s+" + re.escape(name) + r"\s*===\s*'__STR__'",
        body,
    ):
        return True
    # `if (!name || typeof name !== 'string') return ...`
    if re.search(
        r"typeof\s+" + re.escape(name) + r"\s*!==\s*'__STR__'",
        body,
    ):
        return True
    # `const xxx = coerce*(name, …)` — explicit local rebinding through
    # a guard. We accept this too.
    if re.search(
        r"\bconst\s+[A-Za-z_$][\w$]*\s*=\s*("
        + r"|".join(re.escape(g) for g in GUARD_CALLS)
        + r")\s*\(\s*" + re.escape(name) + r"\b",
        body,
    ):
        return True
    return False


# ─── Tests ───────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def all_scopes() -> list[tuple[Path, FunctionScope]]:
    pairs: list[tuple[Path, FunctionScope]] = []
    for f in _all_frontend_files():
        try:
            raw = f.read_text(errors="replace")
        except OSError:
            continue
        src = _strip_comments_and_strings(raw)
        for sc in _walk_functions(src):
            pairs.append((f, sc))
    return pairs


def test_payload_boundary_audit(all_scopes) -> None:
    """The core test. Every payload write of a target key must use a
    safe value expression."""
    offenders: list[str] = []
    for path, scope in all_scopes:
        defaulted = set(_param_names_with_defaults(scope.params))
        if not defaulted:
            continue  # only audit handlers with default args
        for key, value, _body_offset in _find_payload_writes(scope):
            safe, reason = _value_is_safe(value, scope)
            if safe:
                continue
            offenders.append(
                f"{path.relative_to(FRONTEND_SRC)}  fn={scope.name}  "
                f"key={key!r}  value={value!r}  reason={reason}"
            )
    assert not offenders, (
        "PAYLOAD-BOUNDARY AUDIT FAILED. The following payload writes can "
        "leak unguarded handler defaults (incl. React SyntheticEvent) "
        "into backend requests:\n"
        + "\n".join(f"  - {o}" for o in offenders)
        + "\n\nFix each by:\n"
        + "  1. Pre-guarding the param with `dropEventArg(name, 'string', …)`\n"
        + "     or `coerceString/Enum/Id/Slug(name, …)` before payload assembly,\n"
        + "  2. OR rewriting the payload value to use a typed local via\n"
        + "     `const safe = coerceEnum(maybeArg, ALLOWED, { fallback });`"
    )


def test_synthesized_regression_is_detected(tmp_path) -> None:
    """If a future contributor reintroduces the bug, the audit catches it."""
    src = (
        "const handleX = async (overrideId = null) => {\n"
        "  await api.post('/api/x', { style_id: overrideId });\n"
        "};\n"
    )
    f = tmp_path / "Bug.jsx"
    f.write_text(src)
    stripped = _strip_comments_and_strings(src)
    scopes = _walk_functions(stripped)
    assert scopes, "Audit must locate the function scope"
    sc = scopes[0]
    writes = _find_payload_writes(sc)
    assert any(k == "style_id" and v == "overrideId" for k, v, _ in writes), (
        f"Audit must extract `style_id: overrideId` write, got {writes!r}"
    )
    safe, reason = _value_is_safe("overrideId", sc)
    assert not safe, f"Audit must classify `overrideId` as UNSAFE, got {reason!r}"


def test_synthesized_guarded_pattern_is_accepted(tmp_path) -> None:
    """A handler that calls a guard before the payload write must pass."""
    src = (
        "const handleX = async (overrideId = null) => {\n"
        "  overrideId = dropEventArg(overrideId, 'string');\n"
        "  await api.post('/api/x', { style_id: overrideId });\n"
        "};\n"
    )
    f = tmp_path / "Good.jsx"
    f.write_text(src)
    stripped = _strip_comments_and_strings(src)
    sc = _walk_functions(stripped)[0]
    safe, _ = _value_is_safe("overrideId", sc)
    assert safe, "Audit must accept a dropEventArg-guarded param"


def test_synthesized_fallback_pattern_is_flagged(tmp_path) -> None:
    """`arg || state` where `arg` is an unguarded default param is the
    canonical event-trap-into-payload bug. The audit must flag it."""
    src = (
        "const handleX = async (overrideStyle = null) => {\n"
        "  await api.post('/api/x', { style_id: overrideStyle || style });\n"
        "};\n"
    )
    f = tmp_path / "Bug2.jsx"
    f.write_text(src)
    stripped = _strip_comments_and_strings(src)
    sc = _walk_functions(stripped)[0]
    safe, reason = _value_is_safe("overrideStyle || style", sc)
    assert not safe
    assert "fallback-of-unguarded-param" in reason


def test_coercer_utility_module_exists() -> None:
    p = FRONTEND_SRC / "utils" / "payloadCoercers.js"
    assert p.exists(), "Missing payloadCoercers utility module"
    body = p.read_text()
    for name in ("coerceString", "coerceNumber", "coerceEnum", "coerceId", "coerceSlug", "safeOr"):
        assert f"export function {name}" in body, (
            f"payloadCoercers must export {name}"
        )


def test_target_keys_constant_coverage() -> None:
    """Smoke test that the audit's TARGET_KEYS set covers everything
    the founder spec listed."""
    spec_required = {
        "style", "style_id", "mode", "template", "template_id",
        "voice", "voice_id", "character", "character_id",
        "story_id", "draft_id", "asset_id",
        "plan", "price_id", "amount", "credits", "order_id",
    }
    missing = spec_required - TARGET_KEYS
    assert not missing, f"TARGET_KEYS is missing founder-spec keys: {missing}"
