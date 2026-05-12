"""
P0 2026-05 — Idempotency service regression for the Comic Story Book
"Duplicate request in progress" soft-lock bug.

We exercise the IdempotencyService at the unit level (no HTTP, no LLM
workers) because the round-trip through /generate would saturate the
real image-generation pipeline and starve the preview API.

Validates:
  1. First-ever key → (False, None).
  2. Same key submitted again with status=PENDING and fresh timestamp
     → (True, None) — backend correctly tells client to poll.
  3. Same key with status=PENDING but stale (>STALE_PENDING_MINUTES)
     → auto-recovered: (False, None). NO more 24-hour soft-lock.
  4. Same key with status=FAILED → auto-recovered: (False, None).
     This is the exact retry path that was broken (admin retrying after
     a crashed generation).
  5. Same key with status=COMPLETED + a cached result → (True, result).

Plus one HTTP integration smoke test:
  6. /generate end-to-end with admin → 200 + jobId, and any in-flight
     worker is immediately cancelled to keep the test environment clean.
"""
import asyncio
import os
import re
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import requests
from pymongo import MongoClient

from services.idempotency_service import IdempotencyService


# ─── helpers ──────────────────────────────────────────────────────────


def _read_env():
    with open("/app/frontend/.env") as f:
        m = re.search(r"^REACT_APP_BACKEND_URL=(.*)$", f.read(), flags=re.M)
    return m.group(1).strip()


API = _read_env()


def _read_backend_env():
    with open("/app/backend/.env") as f:
        text = f.read()
    mongo = re.search(r"^MONGO_URL=(.*)$", text, flags=re.M).group(1).strip().strip('"')
    dbn = re.search(r"^DB_NAME=(.*)$", text, flags=re.M).group(1).strip().strip('"')
    return mongo, dbn


def _mongo_sync():
    mongo, dbn = _read_backend_env()
    return MongoClient(mongo)[dbn]


def _login(email, password):
    r = requests.post(
        f"{API}/api/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    r.raise_for_status()
    d = r.json()
    return d.get("access_token") or d.get("token")


@pytest.fixture
def fresh_db_for_idem():
    """Sync cleanup of the idempotency collection between tests."""
    db = _mongo_sync()
    db.idempotency_keys.delete_many({})
    yield db
    db.idempotency_keys.delete_many({})


@pytest.fixture
def idem_service(fresh_db_for_idem):
    """Build the IdempotencyService against the same Mongo using motor."""
    from motor.motor_asyncio import AsyncIOMotorClient

    mongo, dbn = _read_backend_env()
    client = AsyncIOMotorClient(mongo)
    return IdempotencyService(client[dbn])


# ─── Unit tests — auto-recovery contract ──────────────────────────────


@pytest.mark.asyncio
async def test_first_submit_is_not_duplicate(idem_service):
    key = f"unit-first-{uuid.uuid4().hex[:8]}"
    is_dup, cached = await idem_service.check_and_store(key)
    assert is_dup is False
    assert cached is None


@pytest.mark.asyncio
async def test_concurrent_pending_returns_dup_with_no_result(
    idem_service, fresh_db_for_idem
):
    """Fresh PENDING (not stale) means a real in-flight request — caller
    should be told to poll, not allowed to start a parallel job."""
    key = f"unit-conc-{uuid.uuid4().hex[:8]}"
    await idem_service.check_and_store(key)
    is_dup, cached = await idem_service.check_and_store(key)
    assert is_dup is True
    assert cached is None  # no result yet — this is the "409 path"


@pytest.mark.asyncio
async def test_stale_pending_is_auto_recovered(idem_service, fresh_db_for_idem):
    """PENDING records older than STALE_PENDING_MINUTES must auto-expire
    so a crashed prior request doesn't soft-lock the user for 24 hours."""
    key = f"unit-stale-{uuid.uuid4().hex[:8]}"
    await idem_service.check_and_store(key)
    # Backdate the record beyond the stale threshold.
    stale = (
        datetime.now(timezone.utc)
        - timedelta(minutes=IdempotencyService.STALE_PENDING_MINUTES + 5)
    ).isoformat()
    fresh_db_for_idem.idempotency_keys.update_one(
        {"key": key}, {"$set": {"createdAt": stale}}
    )
    is_dup, cached = await idem_service.check_and_store(key)
    assert is_dup is False, "stale PENDING must auto-recover, not soft-lock"
    assert cached is None


@pytest.mark.asyncio
async def test_failed_key_is_auto_recovered(idem_service, fresh_db_for_idem):
    """FAILED records must auto-clear so the user can retry. Previously
    this was the exact path that stranded admins."""
    key = f"unit-failed-{uuid.uuid4().hex[:8]}"
    await idem_service.check_and_store(key)
    await idem_service.mark_failed(key, "synthetic test failure")
    is_dup, cached = await idem_service.check_and_store(key)
    assert is_dup is False, "FAILED must allow retry"
    assert cached is None


@pytest.mark.asyncio
async def test_completed_key_returns_cached_result(
    idem_service, fresh_db_for_idem
):
    """COMPLETED records with a real result must be returned as cache hit
    (true idempotency — not a 409 / soft-lock)."""
    key = f"unit-comp-{uuid.uuid4().hex[:8]}"
    await idem_service.check_and_store(key)
    cached_result = {"success": True, "jobId": "abc-123", "status": "QUEUED"}
    await idem_service.update_result(key, cached_result, status="COMPLETED")
    is_dup, cached = await idem_service.check_and_store(key)
    assert is_dup is True
    assert cached == cached_result


# ─── HTTP integration smoke (cleans up worker immediately) ────────────


def _cancel_all_inflight():
    db = _mongo_sync()
    db.comic_storybook_v2_jobs.update_many(
        {"status": {"$nin": ["COMPLETED", "FAILED", "CANCELLED"]}},
        {"$set": {"status": "CANCELLED"}},
    )
    db.idempotency_keys.delete_many({})


@pytest.mark.skipif(
    os.environ.get("SKIP_HTTP_SMOKE") == "1",
    reason="opt-out of HTTP smoke (saturates the LLM worker)",
)
def test_http_single_click_returns_200_jobid():
    """End-to-end smoke. We immediately cancel the spawned job to keep
    the worker from hogging the LLM concurrency budget."""
    _cancel_all_inflight()
    token = _login("admin@creatorstudio.ai", "Cr3@t0rStud!o#2026")
    body = {
        "genre": "kids_adventure",
        "title": f"Idem HTTP Smoke {uuid.uuid4().hex[:6]}",
        "storyIdea": "A short original test story for the HTTP smoke check.",
        "author": "Anonymous",
        "pageCount": 10,
        "addOns": {},
        "dedicationText": None,
        "language": "English",
        "ageGroup": "6-10",
        "readingLevel": "intermediate",
        "bilingual": None,
    }
    r = requests.post(
        f"{API}/api/comic-storybook-v2/generate",
        headers={"Authorization": f"Bearer {token}"},
        json=body,
        timeout=60,
    )
    try:
        assert r.status_code == 200, r.text
        payload = r.json()
        assert payload.get("success") is True
        assert payload.get("jobId")
        assert "Duplicate request in progress" not in (payload.get("detail") or "")
    finally:
        _cancel_all_inflight()
