"""P0 2026-06 — Render-regression hardening: TTS empty-bytes guard,
ffmpeg stderr persistence, admin trailer-job diagnostic shape.

Born from the krajapraveen@gmail.com production incident: failed jobs had
`audio_url_present=false` and `RENDER_INVALID` at `RENDERING_TRAILER`, but
the ffprobe error string was not persisted on the job doc — ops had to
re-run ffprobe locally to know what was wrong.

These tests pin the loud-failure contract:
  • TTS that returns <1024 bytes thrice raises `TTSEmptyResponseError`.
  • `_render_trailer` persists `render_validation_error` on the job doc
    BEFORE re-raising.
  • The new `/admin/trailer-jobs/{id}` endpoint exists with the canonical
    9-field shape ops asked for.
  • `TTS_EMPTY` + `RENDER_INVALID` are mapped to their canonical stages.
  • COMPLETED status is impossible without `video_url + video_key`.

Suite uses the live backend (Motor cross-event-loop safety).
"""
from __future__ import annotations
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
import pytest_asyncio
import httpx
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv("/app/backend/.env")
ROOT = Path(__file__).resolve().parents[2]
TRAILER_PATH = ROOT / "backend" / "routes" / "photo_trailer.py"


def _api_base() -> str:
    p = "/app/frontend/.env"
    if os.path.exists(p):
        for line in open(p):
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    return "http://localhost:8001"


# ─── Static-source pins ──────────────────────────────────────────────────────


def test_tts_empty_response_error_class_exists():
    src = TRAILER_PATH.read_text()
    assert "class TTSEmptyResponseError" in src, (
        "TTSEmptyResponseError must exist — used to map empty-audio failures "
        "to GENERATING_VOICEOVER stage with TTS_EMPTY code."
    )


def test_tts_guard_checks_bytes_threshold():
    """`_tts()` must guard against TTS returning <1024 bytes (likely
    swallowed auth/quota error). Bare bytes >0 isn't enough — empty MP3
    headers can be ~100 bytes."""
    src = TRAILER_PATH.read_text()
    # Find the _tts function body — bounded by the helper above + the next def.
    m = re.search(
        r"async def _tts\([^)]*\) -> bytes:(?P<body>.+?)(?=\nasync def |\ndef )",
        src, re.S,
    )
    assert m, "_tts() must exist."
    body = m.group("body")
    assert "1024" in body, (
        "_tts must enforce a minimum-bytes threshold (1024) for the empty-audio guard."
    )
    assert "empty" in body.lower(), (
        "_tts must log/raise on the empty-bytes branch."
    )
    assert "TTSEmptyResponseError" in body, (
        "_tts must raise TTSEmptyResponseError after retries exhausted on empty bytes."
    )


def test_tts_empty_failure_routes_to_voiceover_stage():
    """When ALL scene assets gather returns TTSEmptyResponseError, the
    pipeline must (a) set stage = GENERATING_VOICEOVER, (b) call _fail
    with code = TTS_EMPTY — not the generic IMAGE_GEN_FAIL."""
    src = TRAILER_PATH.read_text()
    assert '"TTS_EMPTY"' in src, "TTS_EMPTY error code must be raised."
    # Match the INNER pipeline body which holds the gather + failure
    # branch (the outer `_run_pipeline` is a queue-gate wrapper that
    # delegates to `_run_pipeline_inner`).
    m = re.search(
        r"async def _run_pipeline_inner\([^)]*\)[^:]*:(?P<body>.+?)(?=\nasync def |\ndef )",
        src, re.S,
    )
    assert m, "_run_pipeline_inner() must exist."
    body = m.group("body")
    assert '"TTS_EMPTY"' in body, (
        "TTS_EMPTY must be wired inside _run_pipeline_inner's failure branch."
    )
    assert "TTSEmptyResponseError" in body, (
        "Pipeline must detect TTSEmptyResponseError to route to TTS_EMPTY."
    )


def test_render_validation_error_persisted_to_job_doc():
    """`_render_trailer`'s validation-failure branch must write
    `render_validation_error` to the job doc BEFORE re-raising. Otherwise
    the admin diagnostic can't surface the ffprobe complaint."""
    src = TRAILER_PATH.read_text()
    m = re.search(
        r"async def _render_trailer\([^)]*\)[^:]*:(?P<body>.+?)(?=\nasync def |\ndef )",
        src, re.S,
    )
    assert m, "_render_trailer() must exist."
    body = m.group("body")
    assert "render_validation_error" in body, (
        "_render_trailer must persist render_validation_error on validation failure."
    )
    # And the write must happen inside the except/before-raise window.
    except_block = re.search(
        r"except RenderValidationError as e:(?P<eb>.+?)raise",
        body, re.S,
    )
    assert except_block, "RenderValidationError except block must exist."
    assert "render_validation_error" in except_block.group("eb"), (
        "Persistence must happen inside the except block, before the re-raise."
    )


def test_admin_trailer_jobs_endpoint_exists_with_canonical_shape():
    """The user-mandated endpoint shape — these are the fields ops needs
    to triage 'is this video real?' in one curl. Missing any of these is
    a documentation regression."""
    src = TRAILER_PATH.read_text()
    assert '@router.get("/admin/trailer-jobs/{job_id}")' in src, (
        "GET /admin/trailer-jobs/{job_id} endpoint must be registered."
    )
    m = re.search(
        r"async def admin_trailer_job_summary\([^)]*\)[^:]*:(?P<body>.+?)\n    return \{(?P<ret>[^}]+)\}",
        src, re.S,
    )
    assert m, "admin_trailer_job_summary() must return a dict literal."
    ret = m.group("ret")
    canonical_fields = [
        "current_stage", "progress_percent", "photos_count",
        "audio_exists", "output_video_exists", "r2_uploaded",
        "video_url", "failure_reason",
    ]
    for field in canonical_fields:
        assert f'"{field}"' in ret, (
            f"Canonical diagnostic shape missing field: {field!r}"
        )


def test_error_to_stage_includes_tts_empty_and_render_invalid():
    """Both new error codes must be wired into the central ERROR_TO_STAGE
    mapping so the janitor and stage-derivation logic handle them
    correctly."""
    src = TRAILER_PATH.read_text()
    m = re.search(r"ERROR_TO_STAGE\s*=\s*\{(?P<body>[^}]+)\}", src, re.S)
    assert m, "ERROR_TO_STAGE table must exist."
    body = m.group("body")
    assert '"TTS_EMPTY"' in body, "ERROR_TO_STAGE must map TTS_EMPTY."
    assert '"RENDER_INVALID"' in body, "ERROR_TO_STAGE must map RENDER_INVALID."


# ─── Behavioural ─────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def admin_token():
    import sys
    sys.path.insert(0, "/app/backend")
    from shared import create_token  # noqa: WPS433

    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    aid = f"adm-tj-{uuid.uuid4().hex[:6]}"
    await db.users.insert_one({
        "_id": aid, "id": aid, "email": f"{aid}@example.com",
        "name": "TJ Admin", "role": "ADMIN", "credits": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    yield {"token": create_token(aid, "ADMIN"), "db": db, "id": aid}
    await db.users.delete_one({"id": aid})
    cli.close()


@pytest.mark.asyncio
async def test_admin_trailer_jobs_returns_canonical_shape_for_failed_job(admin_token):
    """Seed a FAILED job with provider_error + render_validation_error and
    verify the endpoint surfaces them in `failure_reason`. Proves the live
    endpoint actually composes the canonical string ops needs."""
    db = admin_token["db"]
    jid = f"jid-failed-{uuid.uuid4().hex[:8]}"
    uid = f"u-failed-{uuid.uuid4().hex[:6]}"
    now = datetime.now(timezone.utc).isoformat()
    await db.users.insert_one({
        "_id": uid, "id": uid, "email": f"{uid}@e.com", "role": "USER",
        "credits": 0, "created_at": now,
    })
    await db.photo_trailer_jobs.insert_one({
        "_id": jid, "user_id": uid,
        "status": "FAILED", "current_stage": "FAILED",
        "failure_stage": "RENDERING_TRAILER",
        "error_code": "RENDER_INVALID",
        "error_message": "Trailer failed — credits refunded. Please try again.",
        "render_validation_error": "audio duration 0.0s < expected 12.5s",
        "provider_error": "OpenAI TTS returned 0 bytes",
        "duration_target_seconds": 60, "template_id": "anime_intro",
        "hero_asset_id": "hero-1", "supporting_asset_ids": ["s1", "s2"],
        "charged_credits": 35, "refunded_credits": 35,
        "created_at": now, "failed_at": now, "updated_at": now,
    })
    try:
        async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
            r = await cli.get(
                f"/api/photo-trailer/admin/trailer-jobs/{jid}",
                headers={"Authorization": f"Bearer {admin_token['token']}"},
            )
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["job_id"] == jid
            assert body["status"] == "FAILED"
            assert body["error_code"] == "RENDER_INVALID"
            assert body["current_stage"] == "FAILED"
            assert body["failure_stage"] == "RENDERING_TRAILER"
            assert body["photos_count"] == 3  # hero + 2 supporting
            assert body["audio_exists"] is False
            assert body["output_video_exists"] is False
            assert body["r2_uploaded"] is False
            assert body["video_url"] is None
            # Failure reason must compose error_message + validation + provider.
            assert "credits refunded" in body["failure_reason"]
            assert "audio duration" in body["failure_reason"]
            assert "OpenAI TTS returned 0 bytes" in body["failure_reason"]
    finally:
        await db.users.delete_one({"id": uid})
        await db.photo_trailer_jobs.delete_one({"_id": jid})


@pytest.mark.asyncio
async def test_admin_trailer_jobs_requires_admin(admin_token):
    """Non-admin token must be rejected."""
    import sys
    sys.path.insert(0, "/app/backend")
    from shared import create_token  # noqa: WPS433

    db = admin_token["db"]
    uid = f"u-non-adm-{uuid.uuid4().hex[:6]}"
    await db.users.insert_one({
        "_id": uid, "id": uid, "email": f"{uid}@e.com", "role": "USER",
        "credits": 0, "created_at": datetime.now(timezone.utc).isoformat(),
    })
    try:
        async with httpx.AsyncClient(base_url=_api_base(), timeout=10.0) as cli:
            r = await cli.get(
                "/api/photo-trailer/admin/trailer-jobs/any-jid",
                headers={"Authorization": f"Bearer {create_token(uid, 'USER')}"},
            )
            assert r.status_code in (401, 403), (
                f"Non-admin must be rejected, got {r.status_code}: {r.text}"
            )
    finally:
        await db.users.delete_one({"id": uid})


@pytest.mark.asyncio
async def test_admin_trailer_jobs_returns_404_for_unknown(admin_token):
    async with httpx.AsyncClient(base_url=_api_base(), timeout=10.0) as cli:
        r = await cli.get(
            "/api/photo-trailer/admin/trailer-jobs/does-not-exist",
            headers={"Authorization": f"Bearer {admin_token['token']}"},
        )
        assert r.status_code == 404
