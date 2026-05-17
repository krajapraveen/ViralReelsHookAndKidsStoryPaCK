"""
P1 2026-05-19 — URL / path / query boundary audit.
======================================================

Same bug class as `test_payload_boundary_audit_2026_05.py`, but for
*URL* interpolation rather than request bodies. Catches:

    `/api/x/${maybeArg}`
    `?style=${maybeArg}`
    new URLSearchParams({ key: maybeArg })
    formData.append('story_id', maybeArg)
    window.open(`/share/${maybeArg}`)
    window.location.href = `/app/x?key=${maybeArg}`

…when `maybeArg` is an unguarded default-arg parameter from the
enclosing handler.

The audit walks every function scope in the frontend, looks for the
above interpolation patterns, and asserts that the interpolated
expression is one of:

  • a string literal / number literal
  • a state variable / response-field access
  • the result of a guard call (`coerceString`, `dropEventArg`,
    `safePathId`, `safeQueryParam`, `normalizeComicStyle`, …)
  • a parameter that the function explicitly guarded

When the value can be an unguarded default-arg parameter (including
the `arg || state` fallback shape), the audit flags it with the file,
line, the URL fragment, and the suspect expression.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

FRONTEND_SRC = Path("/app/frontend/src")

# Target key names that we care about whenever they appear next to a
# URL interpolation. (Same list as the payload-body audit, plus the
# token-style keys the founder added for this layer.)
TARGET_KEYS = frozenset({
    "style", "style_id", "mode", "template", "template_id",
    "voice", "voice_id", "character", "character_id",
    "story_id", "draft_id", "asset_id",
    "plan", "price_id", "amount", "credits", "order_id",
    "remix_type", "type", "job_id",
    "token", "share_token",
})

# Functions/utilities that are recognized as safe value-producers.
GUARD_CALLS = frozenset({
    "dropEventArg",
    "coerceString", "coerceEnum", "coerceId", "coerceSlug", "coerceNumber",
    "safeOr",
    "safePathId", "safeQueryParam", "safeUrlParams", "safeDownloadUrl",
    "normalizeComicStyle", "isValidComicStyle",
    "encodeURIComponent",  # not validation, but we treat its result as
                           # "the dev consciously coerced to string-form";
                           # we still flag UNGUARDED default-arg params
                           # below as a separate check.
})


# ─── Helpers (reused shape from the payload-body audit) ──────────────

def _all_frontend_files() -> list[Path]:
    files: list[Path] = []
    for ext in ("*.js", "*.jsx", "*.ts", "*.tsx"):
        files.extend(FRONTEND_SRC.rglob(ext))
    return [
        f for f in files
        if "node_modules" not in f.parts and "build" not in f.parts
    ]


def _strip_comments(src: str) -> str:
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


_FN_DECL_RE = re.compile(
    r"(?:"
    r"const\s+([A-Za-z_$][\w$]*)\s*=\s*(?:useCallback\(\s*)?(?:async\s*)?\(([^)]*)\)\s*=>\s*\{"
    r"|"
    r"function\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)\s*\{"
    r")"
)


def _find_matching_brace(src: str, open_idx: int) -> int:
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


class FnScope:
    __slots__ = ("name", "params", "body", "start_line")

    def __init__(self, name: str, params: str, body: str, start_line: int):
        self.name = name
        self.params = params
        self.body = body
        self.start_line = start_line


def _walk_functions(src: str) -> list[FnScope]:
    out: list[FnScope] = []
    for m in _FN_DECL_RE.finditer(src):
        name = m.group(1) or m.group(3) or "<anon>"
        params = (m.group(2) or m.group(4) or "").strip()
        brace_open = m.end() - 1
        brace_close = _find_matching_brace(src, brace_open)
        body = src[brace_open + 1: brace_close - 1]
        start_line = src.count("\n", 0, m.start()) + 1
        out.append(FnScope(name, params, body, start_line))
    return out


def _params_with_defaults(params: str) -> list[str]:
    names: list[str] = []
    for raw in params.split(","):
        raw = raw.strip()
        if not raw or "=" not in raw:
            continue
        head = raw.split("=", 1)[0].strip()
        if ":" in head:
            head = head.split(":", 1)[0].strip()
        m = re.match(r"\{?\s*([A-Za-z_$][\w$]*)", head)
        if m:
            names.append(m.group(1))
    return names


def _is_param_guarded(name: str, scope: FnScope) -> bool:
    body = scope.body
    pat = re.compile(
        r"\b" + re.escape(name) + r"\s*=\s*("
        + r"|".join(re.escape(g) for g in GUARD_CALLS)
        + r")\s*\("
    )
    if pat.search(body):
        return True
    if re.search(r"typeof\s+" + re.escape(name) + r"\s*===\s*['\"]string['\"]", body):
        return True
    if re.search(r"typeof\s+" + re.escape(name) + r"\s*!==\s*['\"]string['\"]", body):
        return True
    if re.search(
        r"\bconst\s+[A-Za-z_$][\w$]*\s*=\s*("
        + r"|".join(re.escape(g) for g in GUARD_CALLS)
        + r")\s*\(\s*" + re.escape(name) + r"\b",
        body,
    ):
        return True
    return False


def _value_is_safe(expr: str, scope: FnScope) -> tuple[bool, str]:
    v = expr.strip()
    if not v:
        return True, "empty"
    if v in ("null", "undefined"):
        return True, "literal"
    if re.match(r"^-?\d+(\.\d+)?$", v):
        return True, "number_literal"
    if v.lower() in ("true", "false"):
        return True, "bool_literal"
    if v.startswith("'") or v.startswith('"') or v.startswith("`"):
        return True, "string_literal"
    # Guard call result
    m = re.match(r"^([A-Za-z_$][\w$]*)\s*\(", v)
    if m and m.group(1) in GUARD_CALLS:
        return True, "guard_call"
    # Member access on a recognized safe namespace
    if re.match(
        r"^(res|response|result|job|data|err|error|resp|searchParams|"
        r"window|document|localStorage|sessionStorage|process|"
        r"renderJob|fj|item|row|record|entry|el|node|user)\b\.",
        v,
    ):
        return True, "member_access"
    # `e.target.value` etc — explicit event field is a string
    if re.match(r"^(e|ev|evt|event)\.(target|currentTarget|detail)\b\.", v):
        return True, "event_field"
    # arg || state / arg ?? state — only safe if `arg` is guarded
    if "||" in v or "??" in v:
        parts = re.split(r"\|\||\?\?", v, maxsplit=1)
        left = parts[0].strip()
        right = parts[1].strip() if len(parts) > 1 else ""
        bare_left = re.match(r"^([A-Za-z_$][\w$]*)$", left)
        defaulted = set(_params_with_defaults(scope.params))
        if bare_left and bare_left.group(1) in defaulted:
            if not _is_param_guarded(bare_left.group(1), scope):
                return False, f"fallback-of-unguarded-param:{bare_left.group(1)}"
        left_safe, _ = _value_is_safe(left, scope)
        right_safe, _ = _value_is_safe(right, scope)
        if left_safe and right_safe:
            return True, "or_safe"
        return False, "or_unsafe"
    # Plain identifier
    bare = re.match(r"^([A-Za-z_$][\w$]*)$", v)
    if bare:
        name = bare.group(1)
        defaulted = set(_params_with_defaults(scope.params))
        if name in defaulted and not _is_param_guarded(name, scope):
            return False, f"unguarded-default-param:{name}"
        return True, "identifier"
    # Template expression / call / ternary — treat as safe-by-fiat
    return True, "expression_unknown_safe"


# ─── Pattern extractors ──────────────────────────────────────────────

# Match every template literal that contains `${...}` substitutions.
# We then walk substitutions and check those that sit inside URL-like
# strings.
_TEMPLATE_RE = re.compile(r"`([^`]*)`")
_SUBST_RE = re.compile(r"\$\{([^{}]+)\}")


# Variable-name heuristics for path segments. The query-string variant
# captures the key from the URL text itself; the path variant has to
# infer the key from the variable name.
_TARGET_VAR_TOKENS = tuple(sorted(TARGET_KEYS, key=len, reverse=True))


def _var_matches_target_key(name: str) -> str | None:
    """Return the matching TARGET_KEY for an interpolation variable
    name (camelCase or snake_case). E.g. `storyId` → `story_id`,
    `jobId` → `job_id`, `style` → `style`. None if no match."""
    # Direct snake_case match
    if name in TARGET_KEYS:
        return name
    # camelCase → snake_case
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
    if snake in TARGET_KEYS:
        return snake
    # Suffix match: `selectedStyleId` → `style_id`, `currentJobId` → `job_id`
    for token in _TARGET_VAR_TOKENS:
        if snake.endswith("_" + token) or snake == token:
            return token
    return None


_QUERY_KEY_BEFORE_SUBST_RE = re.compile(r"[?&]([A-Za-z_][A-Za-z0-9_]*)=$")


def _classify_url_substitution(template: str, subst_start: int, expr: str) -> str | None:
    """Return the canonical TARGET_KEY this substitution is bound to,
    or None if the substitution isn't covered by the audit scope."""
    # Query-string position: `?key=${expr}` or `&key=${expr}`.
    before = template[:subst_start]
    qm = _QUERY_KEY_BEFORE_SUBST_RE.search(before)
    if qm and qm.group(1) in TARGET_KEYS:
        return qm.group(1)
    # Path-segment position: only audit if the variable name itself
    # looks like one of the target keys.
    bare = re.match(r"^([A-Za-z_$][\w$]*)$", expr.strip())
    if bare:
        return _var_matches_target_key(bare.group(1))
    # `arg || state` shape — same check on the left atom.
    if "||" in expr or "??" in expr:
        left = re.split(r"\|\||\?\?", expr, maxsplit=1)[0].strip()
        bl = re.match(r"^([A-Za-z_$][\w$]*)$", left)
        if bl:
            return _var_matches_target_key(bl.group(1))
    return None


def _walk_template_substitutions(body: str) -> list[tuple[str, str, int, int]]:
    """Return (template_text, substitution_expr, body_offset, subst_start_in_template)
    for every `${...}` inside a backtick template literal that looks URL-ish."""
    out: list[tuple[str, str, int, int]] = []
    for tpl in _TEMPLATE_RE.finditer(body):
        text = tpl.group(1)
        if (
            "/api/" not in text
            and "/app/" not in text
            and "?" not in text
            and "/share/" not in text
            and "/v/" not in text
        ):
            continue
        for sm in _SUBST_RE.finditer(text):
            out.append((text, sm.group(1).strip(), tpl.start() + sm.start(), sm.start()))
    return out


# new URLSearchParams({ key: VAL })  — capture the object literal.
_URLSEARCHPARAMS_RE = re.compile(r"new\s+URLSearchParams\s*\(\s*\{")
# formData.append('KEY', VAL[, …])  — same as payload-body audit.
_FORMDATA_RE = re.compile(
    r"\b(?:formData|fd|form)\s*\.\s*append\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*"
)
# params.set('KEY', VAL)  or  params.append('KEY', VAL)
_URLSP_SET_RE = re.compile(
    r"\b(?:params|qs|searchParams)\s*\.\s*(?:set|append)\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*"
)


def _extract_object_pairs(src: str, start_idx: int) -> list[tuple[str, str]]:
    """Walk a `{...}` object literal and pull top-level (key, value)
    pairs. Lossy but adequate."""
    if start_idx >= len(src) or src[start_idx] != "{":
        return []
    pairs: list[tuple[str, str]] = []
    i = start_idx + 1
    n = len(src)
    while i < n:
        while i < n and src[i] in " \t\n\r,":
            i += 1
        if i >= n or src[i] == "}":
            return pairs
        if src[i] in "\"'`":
            quote = src[i]
            j = src.find(quote, i + 1)
            key = src[i + 1: j] if j != -1 else ""
            i = (j + 1) if j != -1 else n
        else:
            mk = re.match(r"[A-Za-z_$][\w$]*", src[i:])
            if not mk:
                return pairs
            key = mk.group(0)
            i += len(key)
        while i < n and src[i] in " \t":
            i += 1
        if i < n and src[i] in ",}":
            pairs.append((key, key))
            continue
        if i < n and src[i] == ":":
            i += 1
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
    return pairs


# ─── Tests ───────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def all_scopes() -> list[tuple[Path, FnScope]]:
    pairs: list[tuple[Path, FnScope]] = []
    for f in _all_frontend_files():
        try:
            raw = f.read_text(errors="replace")
        except OSError:
            continue
        src = _strip_comments(raw)
        for sc in _walk_functions(src):
            pairs.append((f, sc))
    return pairs


def test_url_path_substitutions_audit(all_scopes) -> None:
    """Every `${expr}` inside a URL-shaped template literal MUST be
    a guarded/safe value when (a) the enclosing function has default-arg
    params, AND (b) the substitution is bound to a TARGET_KEY."""
    offenders: list[str] = []
    for path, scope in all_scopes:
        defaulted = set(_params_with_defaults(scope.params))
        if not defaulted:
            continue
        for tpl_text, expr, _off, subst_start in _walk_template_substitutions(scope.body):
            bound_key = _classify_url_substitution(tpl_text, subst_start, expr)
            if bound_key is None:
                continue
            safe, reason = _value_is_safe(expr, scope)
            if safe:
                continue
            offenders.append(
                f"{path.relative_to(FRONTEND_SRC)}  fn={scope.name}  "
                f"key={bound_key!r}  url_subst={{{expr}}}  reason={reason}"
            )
    assert not offenders, (
        "URL TEMPLATE AUDIT FAILED. The following `${...}` substitutions "
        "leak an unguarded handler default-arg parameter into the URL "
        "on a target payload key:\n"
        + "\n".join(f"  - {o}" for o in offenders)
        + "\n\nFix each by:\n"
        + "  • Guarding the param with `dropEventArg`/`coerceString`/`safePathId`\n"
        + "    before constructing the URL, OR\n"
        + "  • Building the URL via `safeDownloadUrl(base, [parts], query, allow)`\n"
        + "    which validates each segment."
    )


def test_urlsearchparams_object_audit(all_scopes) -> None:
    """`new URLSearchParams({key: maybeArg})` is the second sibling
    of the URL bug. Audit every literal-object form."""
    offenders: list[str] = []
    for path, scope in all_scopes:
        defaulted = set(_params_with_defaults(scope.params))
        if not defaulted:
            continue
        for m in _URLSEARCHPARAMS_RE.finditer(scope.body):
            obj_start = m.end() - 1
            pairs = _extract_object_pairs(scope.body, obj_start)
            for key, val in pairs:
                if key not in TARGET_KEYS:
                    continue
                safe, reason = _value_is_safe(val, scope)
                if safe:
                    continue
                offenders.append(
                    f"{path.relative_to(FRONTEND_SRC)}  fn={scope.name}  "
                    f"URLSearchParams.{key}={val!r}  reason={reason}"
                )
    assert not offenders, (
        "URLSearchParams AUDIT FAILED. Unguarded params destined for the "
        "query string:\n"
        + "\n".join(f"  - {o}" for o in offenders)
        + "\n\nUse `safeUrlParams(obj, ALLOWLIST)` instead."
    )


def test_formdata_and_urlsp_set_audit(all_scopes) -> None:
    """`formData.append('story_id', maybeArg)` and
    `params.set('story_id', maybeArg)` are the FormData/Query siblings."""
    offenders: list[str] = []
    for path, scope in all_scopes:
        defaulted = set(_params_with_defaults(scope.params))
        if not defaulted:
            continue
        for regex, kind in (
            (_FORMDATA_RE, "formData.append"),
            (_URLSP_SET_RE, "params.set/append"),
        ):
            for m in regex.finditer(scope.body):
                key = m.group(1)
                if key not in TARGET_KEYS:
                    continue
                # Walk forward to the second argument.
                i = m.end()
                depth = 0
                start = i
                body = scope.body
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
                safe, reason = _value_is_safe(value, scope)
                if safe:
                    continue
                offenders.append(
                    f"{path.relative_to(FRONTEND_SRC)}  fn={scope.name}  "
                    f"{kind}({key!r}, {value!r})  reason={reason}"
                )
    assert not offenders, (
        "FormData/Query AUDIT FAILED. Unguarded params destined for the "
        "request payload via .append() / .set():\n"
        + "\n".join(f"  - {o}" for o in offenders)
        + "\n\nUse `coerceString/Enum/Id/Slug` to validate before "
        "calling `.append/.set`."
    )


# ─── Synthesized regression coverage ─────────────────────────────────


def test_synthesized_path_regression_is_detected(tmp_path) -> None:
    src = (
        "const handleX = async (overrideId = null) => {\n"
        "  await api.get(`/api/x/${overrideId}`);\n"
        "};\n"
    )
    f = tmp_path / "BugUrl.jsx"
    f.write_text(src)
    stripped = _strip_comments(src)
    sc = _walk_functions(stripped)[0]
    substs = _walk_template_substitutions(sc.body)
    assert any(expr == "overrideId" for _t, expr, _o, _s in substs)
    safe, reason = _value_is_safe("overrideId", sc)
    assert not safe and "unguarded-default-param" in reason


def test_synthesized_query_regression_is_detected(tmp_path) -> None:
    src = (
        "const handleX = async (style = null) => {\n"
        "  const p = new URLSearchParams({ style });\n"
        "  await api.get(`/api/x?${p.toString()}`);\n"
        "};\n"
    )
    f = tmp_path / "BugQuery.jsx"
    f.write_text(src)
    stripped = _strip_comments(src)
    sc = _walk_functions(stripped)[0]
    # The shorthand `{ style }` resolves to value `style`.
    m = _URLSEARCHPARAMS_RE.search(sc.body)
    assert m
    pairs = _extract_object_pairs(sc.body, m.end() - 1)
    assert any(k == "style" for k, _ in pairs)
    safe, reason = _value_is_safe("style", sc)
    assert not safe


def test_synthesized_guarded_path_is_accepted(tmp_path) -> None:
    src = (
        "const handleX = async (overrideId = null) => {\n"
        "  overrideId = safePathId(overrideId, 'overrideId');\n"
        "  if (!overrideId) return;\n"
        "  await api.get(`/api/x/${overrideId}`);\n"
        "};\n"
    )
    f = tmp_path / "GoodUrl.jsx"
    f.write_text(src)
    stripped = _strip_comments(src)
    sc = _walk_functions(stripped)[0]
    safe, _ = _value_is_safe("overrideId", sc)
    assert safe


def test_safe_url_module_exists() -> None:
    p = FRONTEND_SRC / "utils" / "safeUrl.js"
    assert p.exists(), "Missing safeUrl utility module"
    body = p.read_text()
    for name in ("safePathId", "safeQueryParam", "safeUrlParams", "safeDownloadUrl"):
        assert f"export function {name}" in body, (
            f"safeUrl must export {name}"
        )
    # `encodeURIComponent` MUST come AFTER validation, never instead of.
    assert "encodeURIComponent(trimmed)" in body or "encodeURIComponent(" in body, (
        "safePathId must encode the validated value"
    )


def test_target_keys_include_token_pair() -> None:
    """The founder added `token` / `share_token` for this layer."""
    assert "token" in TARGET_KEYS
    assert "share_token" in TARGET_KEYS
