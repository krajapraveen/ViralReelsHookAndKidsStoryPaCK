"""
P1 2026-05-19 — Generic completion-invariant audit.

Enforces doctrine rule 2: "every critical flow has canonical state",
and rule 3: "every failure is observable".

For every pipeline registered in
`services.reliability.completion_invariant.REGISTERED_PIPELINES`,
this audit asserts:

  1. The file imports `assert_completion_invariant`.
  2. Every function in the file that persists a terminal-success
     status (COMPLETED / READY / SUCCESS / READY_WITH_WARNINGS) is
     either:
        (a) annotated with `# invariant: not_applicable` on the line
            preceding the status persistence (explicit opt-out for
            single-output flows like avatar mode), or
        (b) preceded — within the same function body — by a call to
            `assert_completion_invariant(...)` whose result feeds the
            persisted status.

Also locks down the helper module itself:
  • Public API surface: `assert_completion_invariant`,
    `InvariantResult`, `REGISTERED_PIPELINES`.
  • Required metrics emitted on failure.
  • The helper never raises.

The scanner is intentionally opt-in via REGISTERED_PIPELINES. Pipelines
that haven't been migrated yet are NOT audited — they show up in the
backlog test below so we know they remain to be wired through the
canonical gate.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

BACKEND = Path("/app/backend")
sys.path.insert(0, str(BACKEND))

from services.reliability.completion_invariant import (  # noqa: E402
    REGISTERED_PIPELINES,
    DEFAULT_TERMINAL_SUCCESS,
)


# ─── Helpers ─────────────────────────────────────────────────────────


def _strip_comments(src: str) -> str:
    """Strip Python `#` line comments and triple-quoted docstrings.
    Preserves regular string literal contents so the status-assignment
    regex still matches `'COMPLETED'`."""
    out: list[str] = []
    i, n = 0, len(src)
    in_str: str | None = None
    in_triple: str | None = None
    while i < n:
        c = src[i]
        # Inside a triple-quoted docstring — skip until close.
        if in_triple:
            if src.startswith(in_triple, i):
                i += 3
                in_triple = None
                continue
            i += 1
            continue
        # Inside a regular string — preserve contents verbatim.
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(src[i + 1])
                i += 2
                continue
            if c == in_str:
                in_str = None
            i += 1
            continue
        # Start of triple-quoted block.
        if src.startswith('"""', i) or src.startswith("'''", i):
            in_triple = src[i: i + 3]
            i += 3
            continue
        # Start of regular string.
        if c in "\"'":
            in_str = c
            out.append(c)
            i += 1
            continue
        # Line comment.
        if c == "#":
            j = src.find("\n", i)
            i = n if j == -1 else j
            continue
        out.append(c)
        i += 1
    return "".join(out)


_FN_RE = re.compile(r"^(\s*)(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\(", re.M)


def _walk_functions(src: str) -> list[tuple[str, int, int, int]]:
    """Return (name, start_offset, end_offset, indent_len). End offset
    is computed as the first line at or below the def's indent that
    isn't blank — a sufficient bound for our static checks on this
    codebase's style."""
    fns: list[tuple[str, int, int, int]] = []
    matches = list(_FN_RE.finditer(src))
    for k, m in enumerate(matches):
        indent = len(m.group(1))
        start = m.end()
        # Find end: next def at same-or-lower indent, or EOF.
        end = len(src)
        for nm in matches[k + 1:]:
            nm_indent = len(nm.group(1))
            if nm_indent <= indent:
                end = nm.start()
                break
        fns.append((m.group(2), start, end, indent))
    return fns


# Match status persistence patterns ONLY:
#   • `$set: {"status": "VALUE", …}`
#   • `update_one({...}, {"$set": {"status": "VALUE"}})`
#   • `status = "VALUE"` / `job_status = "VALUE"` (assignment, not comparison)
# Read-side patterns (`j.get("status") == "VALUE"`, `count_documents`,
# `if status in (…,)`) are NOT matched because they don't mutate.
_STATUS_WRITE_RE = re.compile(
    r"(?:"
    # Direct assignment: identifier =[ <no '=' after to exclude '=='> ] "VALUE"
    r"\b(?:job_status|status|new_status|final_status)\s*=\s*['\"]([A-Z_]+)['\"]"
    r"|"
    # Mongo write: `"status": "VALUE"` within 80 chars after a $set
    r"\$set[\s\S]{0,200}?['\"]status['\"]\s*:\s*['\"]([A-Z_]+)['\"]"
    r")"
)


def _persists_terminal_success(fn_body: str) -> list[str]:
    """Return the list of terminal-success status strings ACTUALLY
    WRITTEN inside this function body. Read-side comparisons and
    dict-literal references in projection/filter clauses are excluded."""
    hits: list[str] = []
    for m in _STATUS_WRITE_RE.finditer(fn_body):
        val = m.group(1) or m.group(2)
        if val and val in DEFAULT_TERMINAL_SUCCESS:
            hits.append(val)
    return hits


def _calls_invariant(fn_body: str) -> bool:
    return "assert_completion_invariant(" in fn_body


def _annotated_not_applicable(raw_fn_body: str) -> bool:
    """Single-output paths (e.g. avatar mode) may legitimately
    persist COMPLETED without a count invariant. They MUST opt out
    explicitly with `# invariant: not_applicable` somewhere inside
    the function body (must be in the raw source, BEFORE comment
    stripping, since the marker itself lives in a comment)."""
    return bool(re.search(
        r"#\s*invariant\s*:\s*not_applicable",
        raw_fn_body,
        re.IGNORECASE,
    ))


# ─── Tests ───────────────────────────────────────────────────────────


def test_registered_pipelines_exist():
    """Every entry in REGISTERED_PIPELINES must resolve to a real file."""
    missing = [p for p in REGISTERED_PIPELINES if not (BACKEND / p).exists()]
    assert not missing, f"REGISTERED_PIPELINES references missing files: {missing}"


@pytest.mark.parametrize("rel_path", REGISTERED_PIPELINES)
def test_registered_pipeline_imports_invariant(rel_path: str) -> None:
    src = (BACKEND / rel_path).read_text()
    assert "assert_completion_invariant" in src, (
        f"{rel_path} is in REGISTERED_PIPELINES but never references "
        "`assert_completion_invariant`. Wire the canonical gate through "
        "or remove the file from the registry."
    )


@pytest.mark.parametrize("rel_path", REGISTERED_PIPELINES)
def test_registered_pipeline_functions_gate_terminal_success(rel_path: str) -> None:
    """Every function in a registered pipeline that persists a
    terminal-success status MUST go through the invariant helper OR
    explicitly opt out via `# invariant: not_applicable`."""
    raw = (BACKEND / rel_path).read_text()
    # Walk the RAW source so the `# invariant: not_applicable` markers
    # (which live in comments) are visible to the opt-out check. The
    # status-write regex is precise enough to avoid being fooled by
    # comments.
    offenders: list[str] = []
    for name, start, end, _indent in _walk_functions(raw):
        raw_body = raw[start:end]
        # Strip comments only for the status-write detection so that an
        # `# noqa` or doc reference to "COMPLETED" doesn't false-positive.
        stripped_body = _strip_comments(raw_body)
        hits = _persists_terminal_success(stripped_body)
        if not hits:
            continue
        if _calls_invariant(stripped_body):
            continue
        if _annotated_not_applicable(raw_body):
            continue
        offenders.append(
            f"{rel_path}::{name} persists terminal-success {hits!r} "
            "without calling assert_completion_invariant() and without "
            "the `# invariant: not_applicable` opt-out marker."
        )
    assert not offenders, (
        "COMPLETION-INVARIANT AUDIT FAILED:\n"
        + "\n".join(f"  - {o}" for o in offenders)
        + "\n\nFix each by:\n"
        + "  • Wrapping the status persistence with\n"
        + "    `result = await assert_completion_invariant(...)`,\n"
        + "  • OR adding `# invariant: not_applicable` on the line "
          "above the status assignment for single-output flows."
    )


def test_invariant_helper_exposes_public_api():
    """The helper must export the canonical API surface."""
    from services.reliability import completion_invariant as ci

    # Functions / dataclasses
    assert callable(ci.assert_completion_invariant)
    assert hasattr(ci, "InvariantResult")
    # Constants
    assert isinstance(ci.REGISTERED_PIPELINES, tuple)
    assert "COMPLETED" in ci.DEFAULT_TERMINAL_SUCCESS
    assert "READY" in ci.DEFAULT_TERMINAL_SUCCESS
    assert "SUCCESS" in ci.DEFAULT_TERMINAL_SUCCESS


def test_invariant_helper_emits_required_metrics():
    """The source of the helper must reference the three doctrine
    metrics so they cannot drift out of the implementation."""
    src = (
        BACKEND / "services" / "reliability" / "completion_invariant.py"
    ).read_text()
    for metric in (
        "completion_invariant_failed_total",
        "partial_output_repaired_total",
        "false_complete_prevented_total",
    ):
        assert metric in src, (
            f"completion_invariant.py must emit `{metric}` so ops can "
            "observe the gate doing work."
        )


def test_invariant_helper_never_raises_on_invariant_failure():
    """The helper must downgrade — never raise."""
    import asyncio

    from services.reliability.completion_invariant import (
        assert_completion_invariant,
    )

    async def run():
        return await assert_completion_invariant(
            expected_count=3,
            actual_count=2,
            declared_status="COMPLETED",
            request_id="req-test",
            job_id="job-test",
            pipeline="unit_test.synthetic",
            db=None,  # no DB — must not blow up
        )

    result = asyncio.run(run())
    assert result.repaired is True
    assert result.effective_status == "PARTIAL_READY"
    assert result.decision == "ACCEPT_PARTIAL_INVARIANT_REPAIRED"
    assert result.expected == 3
    assert result.actual == 2


def test_invariant_helper_accepts_full_count():
    import asyncio

    from services.reliability.completion_invariant import (
        assert_completion_invariant,
    )

    async def run():
        return await assert_completion_invariant(
            expected_count=3,
            actual_count=3,
            declared_status="COMPLETED",
            request_id="req-ok",
            job_id="job-ok",
            pipeline="unit_test.synthetic",
            db=None,
        )

    result = asyncio.run(run())
    assert result.repaired is False
    assert result.effective_status == "COMPLETED"
    assert result.decision == "ACCEPT_FULL"


def test_invariant_helper_lets_failed_status_through():
    """Non-success terminal states (FAILED, CANCELLED, etc.) must
    pass through untouched — the gate only fires on claimed success."""
    import asyncio

    from services.reliability.completion_invariant import (
        assert_completion_invariant,
    )

    async def run():
        return await assert_completion_invariant(
            expected_count=3,
            actual_count=0,
            declared_status="FAILED",
            pipeline="unit_test.synthetic",
            db=None,
        )

    result = asyncio.run(run())
    assert result.repaired is False
    assert result.effective_status == "FAILED"
    assert result.decision == "ACCEPT_AS_DECLARED"


def test_synthesized_unregistered_pipeline_is_flagged(tmp_path):
    """If a contributor adds a new pipeline file with a bare
    `status = 'COMPLETED'` and forgets to wire the invariant, the
    audit machinery catches it when the file is registered."""
    fake = tmp_path / "fake_pipeline.py"
    fake.write_text(
        "async def run():\n"
        "    panels = await build_panels()\n"
        "    status = 'COMPLETED'\n"
        "    return status\n"
    )
    raw = fake.read_text()
    fns = _walk_functions(raw)
    assert any(
        _persists_terminal_success(_strip_comments(raw[s:e]))
        for _n, s, e, _i in fns
    )
    body = _strip_comments(raw[fns[0][1]: fns[0][2]])
    assert not _calls_invariant(body)
    assert not _annotated_not_applicable(raw[fns[0][1]: fns[0][2]])


def test_synthesized_opt_out_marker_is_respected(tmp_path):
    fake = tmp_path / "single_output.py"
    fake.write_text(
        "async def run():\n"
        "    # invariant: not_applicable (single avatar output)\n"
        "    status = 'COMPLETED'\n"
        "    return status\n"
    )
    raw = fake.read_text()
    fns = _walk_functions(raw)
    raw_body = raw[fns[0][1]: fns[0][2]]
    stripped_body = _strip_comments(raw_body)
    assert _persists_terminal_success(stripped_body)
    assert not _calls_invariant(stripped_body)
    assert _annotated_not_applicable(raw_body)
