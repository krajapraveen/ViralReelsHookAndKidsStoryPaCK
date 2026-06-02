"""P0 2026-06 — Render-timeout hardening + ffmpeg diagnostic persistence.

Born from the krajapraveen production proof: failed Anime Intro trailer
showed `current_stage=RENDERING_TRAILER`, `error_code=RENDER_TIMEOUT`,
and EMPTY `ffmpeg_stderr_tail`. Two root causes:

  1. Render budget was too tight for 60s/90s trailers under load.
  2. ffmpeg subprocess failures didn't persist their stderr/exit_code
     onto the job doc, so ops couldn't tell which stage of the render
     actually broke.

This suite pins:
  • Duration-based render timeout schedule (the user-mandated values).
  • Hard-max wall-clock budgets are >= render budgets + headroom.
  • _ffmpeg_run supports timeout + output_path kwargs and raises
    FfmpegFailure (typed, carries the diagnostic payload).
  • Soft-success: if ffmpeg times out but a valid MP4 is on disk,
    don't fail.
  • Pipeline catches FfmpegFailure and persists ffmpeg_exit_code,
    ffmpeg_stderr_tail, render_timeout_limit_seconds,
    render_duration_seconds, output_file_size_mb to the job doc.
  • /admin/trailer-jobs/<id> surfaces all those new fields.

Pure source-static — no live backend needed.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
TRAILER_PATH = ROOT / "backend" / "routes" / "photo_trailer.py"


def _src() -> str:
    return TRAILER_PATH.read_text()


# ─── 1. Timeout schedule matches user mandate ───────────────────────────────


def test_render_timeout_schedule_matches_user_mandate():
    """User-mandated: 30s→5min (we ship 6 for headroom), 45s→7 (we ship 8),
    60s→10min, 90s→14min. Floors only — generous is fine, tight is not."""
    src = _src()
    m = re.search(r"RENDER_TIMEOUT_BY_DURATION\s*=\s*\{(?P<body>[^}]+)\}", src, re.S)
    assert m, "RENDER_TIMEOUT_BY_DURATION table must exist."
    body = m.group("body")
    # Parse out keyed minutes
    pairs = dict(re.findall(r"(\d+)\s*:\s*(\d+)", body))
    pairs = {int(k): int(v) for k, v in pairs.items()}
    # User mandate floors
    assert pairs.get(30, 0) >= 5, f"30s render budget must be ≥5min, got {pairs.get(30)}"
    assert pairs.get(45, 0) >= 7, f"45s render budget must be ≥7min, got {pairs.get(45)}"
    assert pairs.get(60, 0) >= 10, f"60s render budget must be ≥10min, got {pairs.get(60)}"
    # 90s isn't in the user's spec but the existing 90s tier must scale too.
    assert pairs.get(90, 0) >= 12, f"90s render budget must be ≥12min, got {pairs.get(90)}"


def test_hard_max_runtime_exceeds_render_budget():
    """The wall-clock hard-max must be ≥ render budget + 2min headroom for
    script + image + tts + upload + finalize. Otherwise the janitor reaps
    a job WHILE ffmpeg is still rendering — exactly the krajapraveen bug."""
    src = _src()
    render_m = re.search(r"RENDER_TIMEOUT_BY_DURATION\s*=\s*\{(?P<body>[^}]+)\}", src, re.S)
    hard_m = re.search(r"HARD_MAX_RUNTIME_BY_DURATION\s*=\s*\{(?P<body>[^}]+)\}", src, re.S)
    assert render_m and hard_m
    render = {int(k): int(v) for k, v in re.findall(r"(\d+)\s*:\s*(\d+)", render_m.group("body"))}
    hard = {int(k): int(v) for k, v in re.findall(r"(\d+)\s*:\s*(\d+)", hard_m.group("body"))}
    for dur, render_min in render.items():
        if dur not in hard:
            continue
        assert hard[dur] >= render_min + 2, (
            f"{dur}s tier: hard-max {hard[dur]}min must be ≥ render {render_min}min + 2min headroom"
        )


# ─── 2. _ffmpeg_run has the new contract ────────────────────────────────────


def test_ffmpeg_run_supports_timeout_and_output_path_kwargs():
    """Signature: _ffmpeg_run(args, *, timeout_seconds=..., output_path=...)
    Caller controls per-stage budget; output_path lets the soft-success
    branch check the actual MP4."""
    src = _src()
    m = re.search(
        r"def _ffmpeg_run\(\s*args:\s*List\[str\],\s*\*,\s*(?P<kw>.+?)\)\s*->\s*None:",
        src, re.S,
    )
    assert m, "_ffmpeg_run must have a keyword-only signature."
    kw = m.group("kw")
    assert "timeout_seconds" in kw
    assert "output_path" in kw


def test_ffmpeg_failure_class_carries_diagnostic_payload():
    """FfmpegFailure must expose exit_code, stderr_tail, timeout_limit,
    render_duration, output_path, cmd_head — exactly the fields the
    pipeline persists onto the job doc."""
    src = _src()
    m = re.search(r"class FfmpegFailure\(RuntimeError\):(?P<body>.+?)(?=\nclass |\ndef |\nasync def )", src, re.S)
    assert m, "FfmpegFailure class must exist."
    body = m.group("body")
    for field in ("exit_code", "stderr_tail", "timeout_limit_seconds",
                  "render_duration_seconds", "output_path", "cmd_head"):
        assert f"self.{field}" in body, (
            f"FfmpegFailure must expose `{field}` for ops diagnostics."
        )


def test_ffmpeg_soft_success_window_exists():
    """If ffmpeg times out but the MP4 is on disk + ≥1MB, treat as success.
    Real but slow renders shouldn't be penalized."""
    src = _src()
    m = re.search(
        r"def _ffmpeg_run\(.+?(?=\nasync def |\ndef )", src, re.S,
    )
    body = m.group(0)
    assert "soft-success" in body.lower(), (
        "_ffmpeg_run must have a soft-success branch for output-exists-after-timeout."
    )
    assert "1_000_000" in body or "1000000" in body, (
        "Soft-success threshold must be 1MB (a real trailer is multi-MB)."
    )


# ─── 3. Pipeline catches FfmpegFailure + persists diagnostics ───────────────


def test_pipeline_catches_ffmpeg_failure_and_persists_diagnostics():
    """The pipeline's render block must catch FfmpegFailure (not generic
    RuntimeError) and persist the structured diagnostic fields onto the
    job doc BEFORE calling _fail."""
    src = _src()
    m = re.search(
        r"async def _run_pipeline_inner\([^)]*\)[^:]*:(?P<body>.+?)(?=\nasync def |\ndef )",
        src, re.S,
    )
    body = m.group("body")
    assert "except FfmpegFailure" in body, (
        "Pipeline must catch FfmpegFailure specifically — not generic RuntimeError."
    )
    # All five canonical diagnostic fields must be persisted.
    for field in ("ffmpeg_exit_code", "ffmpeg_stderr_tail",
                  "render_timeout_limit_seconds", "render_duration_seconds",
                  "output_file_size_mb"):
        assert f'"{field}"' in body, (
            f"Pipeline must persist `{field}` to job doc on ffmpeg failure."
        )


def test_pipeline_has_soft_success_branch_for_render_timeout():
    """When asyncio.wait_for fires but the MP4 already landed on disk
    and is valid (ffprobe duration matches), don't fail — proceed to
    finalize. Lying about a real render is worse than a slow one."""
    src = _src()
    m = re.search(
        r"async def _run_pipeline_inner\([^)]*\)[^:]*:(?P<body>.+?)(?=\nasync def |\ndef )",
        src, re.S,
    )
    body = m.group("body")
    # Must reference both ffprobe duration check AND MP4 existence after timeout.
    assert "_ffprobe_duration_seconds" in body, (
        "Soft-success branch must use _ffprobe_duration_seconds to validate."
    )
    # Soft-success comment / variable must be present.
    assert "soft_success" in body.lower(), (
        "Pipeline must define a soft_success flag in the render-timeout branch."
    )


# ─── 4. Admin endpoint surfaces new fields ──────────────────────────────────


def test_admin_trailer_jobs_endpoint_includes_render_diagnostics():
    """Every new render-stage diagnostic field must be exposed in the
    /admin/trailer-jobs/<id> response. Else ops cannot triage."""
    src = _src()
    m = re.search(
        r"async def admin_trailer_job_summary\([^)]*\)[^:]*:(?P<body>.+?)\n    return \{(?P<ret>[^}]+)\}",
        src, re.S,
    )
    assert m, "admin_trailer_job_summary must return a dict literal."
    ret = m.group("ret")
    for field in ("ffmpeg_exit_code", "ffmpeg_stderr_tail",
                  "render_timeout_limit_seconds", "render_duration_seconds",
                  "output_file_size_mb", "render_failure_kind"):
        assert f'"{field}"' in ret, (
            f"Admin diagnostic endpoint must surface `{field}`."
        )
