#!/usr/bin/env python3
"""
audit_boundaries_coverage.py — P1 2026-05-19 reliability sweep.

Read-only visibility tool. Walks the backend/routes/ and backend/services/
trees, reports:

  • Pipelines currently in REGISTERED_PIPELINES (protected by the
    canonical gate).
  • Functions inside registered pipelines that go through
    `assert_completion_invariant`.
  • Functions inside registered pipelines that opt out via
    `# invariant: not_applicable`.
  • Heuristic candidate list of UNREGISTERED files that persist a
    terminal-success status — these are the next migration targets.
  • Recommended migration order, ranked by:
        (1) explicit per-scene/per-panel/per-segment fan-out shape
            (more outputs = higher bug class risk),
        (2) presence of an existing in-file count check we'd
            replace with the helper,
        (3) file traffic proxy (line count of route handlers).

Usage:
    python3 backend/scripts/audit_boundaries_coverage.py
    make audit-boundaries-coverage

Exit code is always 0 — this is a report, not a gate.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from services.reliability.completion_invariant import (  # noqa: E402
    REGISTERED_PIPELINES,
    DEFAULT_TERMINAL_SUCCESS,
)

# ── reuse the same scanner primitives as the audit test ──
_FN_RE = re.compile(r"^(\s*)(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\(", re.M)
_STATUS_WRITE_RE = re.compile(
    r"(?:"
    r"\b(?:job_status|status|new_status|final_status)\s*=\s*['\"]([A-Z_]+)['\"]"
    r"|"
    r"\$set[\s\S]{0,200}?['\"]status['\"]\s*:\s*['\"]([A-Z_]+)['\"]"
    r")"
)


def _strip_comments(src: str) -> str:
    out: list[str] = []
    i, n = 0, len(src)
    in_str: str | None = None
    in_triple: str | None = None
    while i < n:
        c = src[i]
        if in_triple:
            if src.startswith(in_triple, i):
                i += 3
                in_triple = None
                continue
            i += 1
            continue
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
        if src.startswith('"""', i) or src.startswith("'''", i):
            in_triple = src[i: i + 3]
            i += 3
            continue
        if c in "\"'":
            in_str = c
            out.append(c)
            i += 1
            continue
        if c == "#":
            j = src.find("\n", i)
            i = n if j == -1 else j
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _walk_functions(src: str) -> list[tuple[str, int, int, int]]:
    fns: list[tuple[str, int, int, int]] = []
    matches = list(_FN_RE.finditer(src))
    for k, m in enumerate(matches):
        indent = len(m.group(1))
        start = m.end()
        end = len(src)
        for nm in matches[k + 1:]:
            if len(nm.group(1)) <= indent:
                end = nm.start()
                break
        fns.append((m.group(2), start, end, indent))
    return fns


def _persists_terminal_success(body: str) -> list[str]:
    hits: list[str] = []
    for m in _STATUS_WRITE_RE.finditer(body):
        val = m.group(1) or m.group(2)
        if val and val in DEFAULT_TERMINAL_SUCCESS:
            hits.append(val)
    return hits


def _calls_invariant(body: str) -> bool:
    return "assert_completion_invariant(" in body


def _opted_out(raw_body: str) -> bool:
    return bool(re.search(r"#\s*invariant\s*:\s*not_applicable", raw_body, re.IGNORECASE))


def _candidate_files() -> list[Path]:
    """Walk routes/ and services/, return every .py file that contains
    at least one terminal-success WRITE that isn't already a registered
    pipeline."""
    roots = [BACKEND / "routes", BACKEND / "services"]
    out: list[Path] = []
    registered_set = {str(BACKEND / p) for p in REGISTERED_PIPELINES}
    for root in roots:
        if not root.exists():
            continue
        for f in root.rglob("*.py"):
            if "__pycache__" in f.parts:
                continue
            if str(f) in registered_set:
                continue
            try:
                raw = f.read_text(errors="replace")
            except OSError:
                continue
            src = _strip_comments(raw)
            if _persists_terminal_success(src):
                out.append(f)
    return sorted(out)


# Signal-shape scorer used to rank unregistered candidates.
_FANOUT_TOKENS = (
    "scenes", "panels", "segments", "chapters",
    "scene_count", "panel_count", "segment_count",
    "for i in range(", "asyncio.gather(",
)
_EXISTING_COUNT_CHECK_TOKENS = (
    "expected_count", "actual_count",
    "actual_ready_count", "completed_count",
    "len(ready", "len(completed",
)


def _score(path: Path) -> tuple[int, int, int, str]:
    """Return (fanout_score, has_existing_count_check, line_count, marker_summary)."""
    try:
        raw = path.read_text(errors="replace")
    except OSError:
        return (0, 0, 0, "")
    fanout = sum(1 for tok in _FANOUT_TOKENS if tok in raw)
    existing = sum(1 for tok in _EXISTING_COUNT_CHECK_TOKENS if tok in raw)
    lc = raw.count("\n") + 1
    marker = ",".join(t for t in _FANOUT_TOKENS if t in raw)[:80]
    return (fanout, existing, lc, marker)


def _registered_breakdown() -> list[dict]:
    breakdown: list[dict] = []
    for rel in REGISTERED_PIPELINES:
        path = BACKEND / rel
        if not path.exists():
            breakdown.append({"path": rel, "missing": True})
            continue
        raw = path.read_text(errors="replace")
        protected: list[str] = []
        opt_out: list[str] = []
        for name, start, end, _i in _walk_functions(raw):
            raw_body = raw[start:end]
            stripped_body = _strip_comments(raw_body)
            hits = _persists_terminal_success(stripped_body)
            if not hits:
                continue
            if _calls_invariant(stripped_body):
                protected.append(f"{name} ← assert_completion_invariant")
            elif _opted_out(raw_body):
                opt_out.append(f"{name} ← # invariant: not_applicable")
        breakdown.append({
            "path": rel,
            "missing": False,
            "protected": protected,
            "opt_out": opt_out,
        })
    return breakdown


def main() -> int:
    print("═══════════════════════════════════════════════════════════════")
    print("  CreatorStudio boundary coverage report")
    print("  Doctrine: 'Never allow unvalidated input, ambiguous state,")
    print("  or silent failure to cross a system boundary.'")
    print("═══════════════════════════════════════════════════════════════")
    print()

    # ─── Registered pipelines ────────────────────────────────────────
    print("REGISTERED PIPELINES (protected by the canonical gate)")
    print("---------------------------------------------------------------")
    breakdown = _registered_breakdown()
    if not breakdown:
        print("  (none)")
    for item in breakdown:
        if item.get("missing"):
            print(f"  ⚠ {item['path']}  — REFERENCED BUT MISSING ON DISK")
            continue
        print(f"  ● {item['path']}")
        for line in item.get("protected", []):
            print(f"      ✓ {line}")
        for line in item.get("opt_out", []):
            print(f"      ○ {line}")
        if not item.get("protected") and not item.get("opt_out"):
            print("      (no terminal-success writes detected — empty pipeline?)")
    print()

    # ─── Candidate (unprotected) pipelines ───────────────────────────
    print("UNPROTECTED CANDIDATES (persist terminal success outside the gate)")
    print("---------------------------------------------------------------")
    candidates = _candidate_files()
    scored = [(p, *_score(p)) for p in candidates]
    # Sort: highest fanout first, then existing count check, then size.
    scored.sort(key=lambda r: (-r[1], -r[2], -r[3]))
    if not scored:
        print("  ✓ All terminal-success writers are registered.")
    else:
        for path, fan, existing, lc, marker in scored[:25]:
            rel = path.relative_to(BACKEND)
            label = []
            if fan > 0:
                label.append(f"fanout={fan}")
            if existing > 0:
                label.append(f"has_count_check={existing}")
            label.append(f"loc={lc}")
            tag = "  ".join(label)
            print(f"  ◦ {rel}    [{tag}]")
            if marker:
                print(f"        signals: {marker}")
        if len(scored) > 25:
            print(f"  … and {len(scored) - 25} more (truncated for brevity)")
    print()

    # ─── Recommended migration order ─────────────────────────────────
    print("RECOMMENDED NEXT MIGRATIONS (top 5, by signal score)")
    print("---------------------------------------------------------------")
    top = scored[:5]
    if not top:
        print("  Nothing left to migrate. ✓")
    else:
        for rank, (path, fan, existing, lc, _marker) in enumerate(top, 1):
            rel = path.relative_to(BACKEND)
            verdict = []
            if existing > 0:
                verdict.append("ALREADY has count-check (low-risk migration)")
            if fan >= 3:
                verdict.append("multi-output fan-out (high bug-class risk)")
            elif fan >= 1:
                verdict.append("fan-out present")
            print(f"  {rank}. {rel}")
            if verdict:
                print(f"     → {' · '.join(verdict)}")
    print()
    print("How to migrate one:")
    print("  1. Add the file path to REGISTERED_PIPELINES in")
    print("     /app/backend/services/reliability/completion_invariant.py.")
    print("  2. Replace its terminal-success persistence with:")
    print("       result = await assert_completion_invariant(")
    print("           expected_count=..., actual_count=...,")
    print("           declared_status=..., pipeline='<canonical name>',")
    print("           db=db,")
    print("       )")
    print("  3. Run `make audit-boundaries` — the new audit will fail")
    print("     until the gate is wired correctly.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
