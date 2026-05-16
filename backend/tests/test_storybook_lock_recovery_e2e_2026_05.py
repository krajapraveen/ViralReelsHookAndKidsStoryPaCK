"""
P0 2026-05-19 — Live HTTP regression for the storybook lock-recovery fix.

Verifies the actual server-on-the-wire behavior:
  • Synthesise an ORPHANED PENDING idempotency row (worker died before
    inserting the comic_storybook_v2_jobs row).
  • Hit /generate with the SAME body → backend must auto-recover the
    orphan and return 200 with a fresh jobId.
  • Job is immediately cancelled to avoid spending LLM budget.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone

import pytest
import requests
from pymongo import MongoClient


def _read_env():
    return re.search(
        r"^REACT_APP_BACKEND_URL=(.*)$",
        open("/app/frontend/.env").read(),
        flags=re.M,
    ).group(1).strip()


def _read_backend_env():
    text = open("/app/backend/.env").read()
    mongo = re.search(r"^MONGO_URL=(.*)$", text, flags=re.M).group(1).strip().strip('"')
    dbn = re.search(r"^DB_NAME=(.*)$", text, flags=re.M).group(1).strip().strip('"')
    return mongo, dbn


API = _read_env()


def _mongo():
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
    return d.get("access_token") or d.get("token"), (d.get("user") or {}).get("id")


def _cancel_all_inflight():
    db = _mongo()
    db.comic_storybook_v2_jobs.update_many(
        {"status": {"$nin": ["COMPLETED", "FAILED", "CANCELLED"]}},
        {"$set": {"status": "CANCELLED"}},
    )
    db.idempotency_keys.delete_many({})


def _body_hash(user_id, genre, title, story_idea, page_count):
    return hashlib.sha256(json.dumps({
        "user_id": user_id, "genre": genre, "title": title,
        "storyIdea": story_idea[:200], "pageCount": page_count,
    }, sort_keys=True).encode()).hexdigest()[:32]


@pytest.mark.skipif(
    os.environ.get("SKIP_HTTP_SMOKE") == "1",
    reason="opt-out (saturates LLM worker)",
)
def test_orphan_pending_idempotency_is_auto_recovered_e2e():
    """
    Setup:
      1. Cancel any prior in-flight jobs.
      2. Pre-insert an ORPHANED PENDING idempotency row (status=PENDING,
         result=None) for the body fingerprint we're about to submit —
         AND deliberately do NOT insert a matching comic_storybook_v2_jobs
         row. This is exactly the production trap state.
      3. Hit /generate with the same body.

    Assert:
      • Response is 200 (NOT 409).
      • Response carries jobId.
      • The orphan PENDING was recovered (not soft-locking the user).
    """
    _cancel_all_inflight()

    token, user_id = _login("admin@creatorstudio.ai", "Cr3@t0rStud!o#2026")
    assert user_id, "admin login must return a user id"

    body = {
        "genre": "kids_adventure",
        "title": f"Lock Recovery {uuid.uuid4().hex[:6]}",
        "storyIdea": "A short original test story for the lock-recovery e2e.",
        "author": "Anonymous",
        "pageCount": 10,
        "addOns": {},
        "dedicationText": None,
        "language": "English",
        "ageGroup": "6-10",
        "readingLevel": "intermediate",
        "bilingual": None,
    }

    # Synthesise the orphan PENDING for this exact body.
    db = _mongo()
    fp = _body_hash(
        user_id, body["genre"], body["title"], body["storyIdea"], body["pageCount"]
    )
    db.idempotency_keys.delete_one({"key": fp})
    db.idempotency_keys.insert_one({
        "key": fp,
        "status": "PENDING",
        "createdAt": datetime.now(timezone.utc).isoformat(),  # FRESH, not stale
        "result": None,
    })
    # Confirm no matching job row exists (simulates worker death pre-insert).
    db.comic_storybook_v2_jobs.delete_many({"idempotency_key": fp})

    try:
        r = requests.post(
            f"{API}/api/comic-storybook-v2/generate",
            headers={"Authorization": f"Bearer {token}"},
            json=body,
            timeout=60,
        )
        # The orphan-recovery branch must let this through as a 200 with
        # a fresh jobId — NOT the legacy 409.
        assert r.status_code == 200, (
            f"Expected 200 (orphan recovery), got {r.status_code}. "
            f"Body: {r.text[:500]}"
        )
        payload = r.json()
        assert payload.get("success") is True, payload
        assert payload.get("jobId"), payload
        assert "Duplicate request in progress" not in (payload.get("message") or ""), (
            "The dead 'Duplicate request in progress' toast must be gone"
        )
    finally:
        _cancel_all_inflight()


@pytest.mark.skipif(
    os.environ.get("SKIP_HTTP_SMOKE") == "1",
    reason="opt-out (saturates LLM worker)",
)
def test_existing_active_job_returns_structured_resume_envelope_e2e():
    """
    When a job genuinely IS active for the same idempotency key, the
    backend now returns a STRUCTURED EXISTING_ACTIVE_JOB envelope with
    jobId + request_id (not 409).
    """
    _cancel_all_inflight()
    token, user_id = _login("admin@creatorstudio.ai", "Cr3@t0rStud!o#2026")

    body = {
        "genre": "kids_adventure",
        "title": f"Active Resume {uuid.uuid4().hex[:6]}",
        "storyIdea": "Another short original test story for the resume e2e.",
        "author": "Anonymous",
        "pageCount": 10,
        "addOns": {},
        "dedicationText": None,
        "language": "English",
        "ageGroup": "6-10",
        "readingLevel": "intermediate",
        "bilingual": None,
    }

    db = _mongo()
    fp = _body_hash(
        user_id, body["genre"], body["title"], body["storyIdea"], body["pageCount"]
    )
    db.idempotency_keys.delete_one({"key": fp})
    # Synthesise PENDING + a matching active job row → the legitimate
    # in-flight resumption case (NOT the orphan).
    db.idempotency_keys.insert_one({
        "key": fp,
        "status": "PENDING",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "result": None,
    })
    fake_job_id = str(uuid.uuid4())
    db.comic_storybook_v2_jobs.insert_one({
        "id": fake_job_id,
        "userId": user_id,
        "type": "COMIC_STORYBOOK",
        "status": "PROCESSING",
        "progress": 42,
        "idempotency_key": fp,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    })

    try:
        r = requests.post(
            f"{API}/api/comic-storybook-v2/generate",
            headers={"Authorization": f"Bearer {token}"},
            json=body,
            timeout=30,
        )
        assert r.status_code == 200, r.text
        payload = r.json()
        assert payload.get("code") == "EXISTING_ACTIVE_JOB", payload
        assert payload.get("jobId") == fake_job_id, payload
        assert payload.get("status") == "PROCESSING", payload
        assert payload.get("resumed") is True, payload
        assert payload.get("request_id"), "request_id must be plumbed"
    finally:
        db.comic_storybook_v2_jobs.delete_one({"id": fake_job_id})
        _cancel_all_inflight()
