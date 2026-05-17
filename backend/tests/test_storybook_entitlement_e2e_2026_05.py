"""
P0 2026-05-19 — Live HTTP for Comic Story Book per-job entitlement block.
========================================================================
Verifies that GET /api/comic-storybook-v2/job/{job_id} returns the
structured `entitlement` block with all founder-mandated fields.
"""
from __future__ import annotations

import os
import re
import sys
import uuid
from datetime import datetime, timezone

import httpx
import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, "/app/backend")


def _api_base() -> str:
    for line in open("/app/frontend/.env"):
        if line.startswith("REACT_APP_BACKEND_URL="):
            return line.split("=", 1)[1].strip()
    return "http://localhost:8001"


def _backend_env():
    text = open("/app/backend/.env").read()
    mongo = re.search(r"^MONGO_URL=(.*)$", text, flags=re.M).group(1).strip().strip('"')
    dbn = re.search(r"^DB_NAME=(.*)$", text, flags=re.M).group(1).strip().strip('"')
    return mongo, dbn


@pytest_asyncio.fixture
async def db():
    mongo, dbn = _backend_env()
    client = AsyncIOMotorClient(mongo)
    yield client[dbn]
    client.close()


@pytest_asyncio.fixture
async def auth_token_and_id():
    async with httpx.AsyncClient(base_url=_api_base(), timeout=20.0) as cli:
        r = await cli.post(
            "/api/auth/login",
            json={"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"},
        )
        assert r.status_code == 200, r.text
        d = r.json()
        token = d.get("access_token") or d.get("token")
        uid = (d.get("user") or {}).get("id")
        assert token and uid
        yield token, uid


@pytest.mark.asyncio
async def test_per_job_entitlement_block_for_admin_completed_job(db, auth_token_and_id):
    """Synthesize a completed comic job owned by admin and confirm the
    per-job entitlement block grants download with reason='unlimited'."""
    token, user_id = auth_token_and_id
    job_id = str(uuid.uuid4())
    await db.comic_storybook_v2_jobs.insert_one({
        "id": job_id,
        "userId": user_id,
        "type": "COMIC_STORYBOOK",
        "status": "COMPLETED",
        "progress": 100,
        "pdfUrl": "https://example.com/test.pdf",
        "coverUrl": "https://example.com/cover.png",
        "cost": 60,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    })
    try:
        async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
            r = await cli.get(
                f"/api/comic-storybook-v2/job/{job_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r.status_code == 200, r.text
            body = r.json()
            ent = body.get("entitlement")
            assert ent, "entitlement block must be present"
            assert ent["can_download"] is True
            # Founder-mandated keys.
            for key in (
                "can_download",
                "upgrade_required",
                "reason",
                "subscription_status",
                "plan_type",
                "credits_available",
                "required_credits",
                "is_unlimited",
                "request_id",
            ):
                assert key in ent, f"entitlement missing key: {key}"
            assert ent["request_id"], "request_id must be plumbed"
            # Admin is unlimited.
            assert ent["is_unlimited"] is True
            assert ent["reason"] == "unlimited"
            assert ent["required_credits"] == 60
    finally:
        await db.comic_storybook_v2_jobs.delete_one({"id": job_id})


@pytest.mark.asyncio
async def test_per_job_entitlement_returns_404_with_structured_envelope(db, auth_token_and_id):
    token, _ = auth_token_and_id
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        r = await cli.get(
            "/api/comic-storybook-v2/job/__non_existent__",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 404, r.text
        d = r.json()["detail"]
        assert isinstance(d, dict)
        assert d["code"] == "JOB_NOT_FOUND"
        assert d["request_id"]
