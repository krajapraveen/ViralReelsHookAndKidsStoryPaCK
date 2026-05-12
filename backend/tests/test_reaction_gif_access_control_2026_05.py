"""
P0/P1 2026-05 — Reaction GIF download/share access-control regression.

Validates:
  1. /api/reaction-gif/job/:id returns an `access` block with
     `full_access`, `can_download`, `can_copy_link`, `can_share_story`.
  2. Admin/unlimited → `access.full_access=true`.
  3. Free user → `access.full_access=false` and direct download is denied
     by /api/reaction-gif/download/:id with HTTP 402.
  4. 404 for missing job (clean JSON, not raw HTML).
"""
import os
import re
import uuid
from datetime import datetime, timezone

import pytest
import requests
from pymongo import MongoClient
import bcrypt as _bcrypt


def _env():
    with open("/app/frontend/.env") as f:
        m = re.search(r"^REACT_APP_BACKEND_URL=(.*)$", f.read(), flags=re.M)
    return m.group(1).strip()


API = _env()


def _mongo():
    with open("/app/backend/.env") as f:
        text = f.read()
    mongo = re.search(r"^MONGO_URL=(.*)$", text, flags=re.M).group(1).strip().strip('"')
    dbn = re.search(r"^DB_NAME=(.*)$", text, flags=re.M).group(1).strip().strip('"')
    return MongoClient(mongo)[dbn]


def _login(email, password):
    r = requests.post(f"{API}/api/auth/login",
                      json={"email": email, "password": password},
                      timeout=30)
    r.raise_for_status()
    d = r.json()
    return d.get("access_token") or d.get("token")


def _ensure_free_user():
    db = _mongo()
    email = "reactiongif_free_fixture@test.com"
    password = "Reaction@2026Test#"
    if not db.users.find_one({"email": email}):
        db.users.insert_one({
            "id": str(uuid.uuid4()),
            "email": email,
            "name": "RG Free",
            "password": _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode(),
            "role": "user",
            "plan": "free",
            "credits": 0,
            "subscription": None,
            "is_unlimited": False,
            "emailVerified": True,
        })
    else:
        db.users.update_one({"email": email}, {"$set": {
            "plan": "free", "subscription": None, "is_unlimited": False,
            "role": "user", "credits": 0,
            "password": _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode(),
        }})
    return email, password


def _seed_completed_job(user_id: str) -> str:
    """Insert a synthetic COMPLETED reaction_gif_job so we can exercise
    the access gate without round-tripping through the LLM worker."""
    db = _mongo()
    job_id = f"rg_test_{uuid.uuid4().hex[:12]}"
    db.reaction_gif_jobs.insert_one({
        "id": job_id,
        "userId": user_id,
        "status": "COMPLETED",
        "progress": 100,
        "resultUrl": "https://example.com/fake.png",
        "results": [{"url": "https://example.com/fake.png", "reaction": "joy"}],
        "purchased": False,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    })
    return job_id


def _user_id_for(email: str) -> str:
    return _mongo().users.find_one({"email": email}, {"id": 1, "_id": 0})["id"]


def test_admin_job_response_has_full_access():
    token = _login("admin@creatorstudio.ai", "Cr3@t0rStud!o#2026")
    admin_id = _user_id_for("admin@creatorstudio.ai")
    jid = _seed_completed_job(admin_id)
    try:
        r = requests.get(
            f"{API}/api/reaction-gif/job/{jid}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        access = r.json().get("access") or {}
        assert access.get("full_access") is True
        assert access.get("can_download") is True
        assert access.get("can_share_story") is True
        assert access.get("upgrade_required") is False
    finally:
        _mongo().reaction_gif_jobs.delete_one({"id": jid})


def test_admin_download_returns_urls():
    token = _login("admin@creatorstudio.ai", "Cr3@t0rStud!o#2026")
    admin_id = _user_id_for("admin@creatorstudio.ai")
    jid = _seed_completed_job(admin_id)
    try:
        r = requests.post(
            f"{API}/api/reaction-gif/download/{jid}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        payload = r.json()
        assert payload.get("success") is True
        assert payload.get("downloadUrls")
    finally:
        _mongo().reaction_gif_jobs.delete_one({"id": jid})


def test_free_user_job_response_has_no_full_access():
    email, password = _ensure_free_user()
    token = _login(email, password)
    user_id = _user_id_for(email)
    jid = _seed_completed_job(user_id)
    try:
        r = requests.get(
            f"{API}/api/reaction-gif/job/{jid}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        access = r.json().get("access") or {}
        assert access.get("full_access") is False
        assert access.get("can_download") is False
        assert access.get("upgrade_required") is True
    finally:
        _mongo().reaction_gif_jobs.delete_one({"id": jid})


def test_free_user_download_is_blocked_with_402():
    email, password = _ensure_free_user()
    token = _login(email, password)
    user_id = _user_id_for(email)
    jid = _seed_completed_job(user_id)
    try:
        r = requests.post(
            f"{API}/api/reaction-gif/download/{jid}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        assert r.status_code == 402, r.text
        assert r.headers.get("content-type", "").startswith("application/json")
        assert "subscribe" in (r.json().get("detail") or "").lower()
    finally:
        _mongo().reaction_gif_jobs.delete_one({"id": jid})


def test_missing_job_returns_clean_json_404():
    token = _login("admin@creatorstudio.ai", "Cr3@t0rStud!o#2026")
    r = requests.post(
        f"{API}/api/reaction-gif/download/nonexistent_job_xyz",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    assert r.status_code == 404, r.text
    assert r.headers.get("content-type", "").startswith("application/json")
    assert "not found" in (r.json().get("detail") or "").lower()
