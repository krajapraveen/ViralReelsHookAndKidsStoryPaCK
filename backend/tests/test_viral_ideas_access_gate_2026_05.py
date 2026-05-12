"""
P0/P1 2026-05 — Viral Ideas (Daily Viral Idea Drop) subscription gate.

Validates:
  1. Free user POST /generate-bundle → 402 (cannot start generation).
  2. Admin/unlimited POST /generate-bundle → 200 with job_id.
  3. Free user GET /jobs/:id/assets → access.full_access=false,
     access.upgrade_required=true, locked=true (server-side override),
     and the asset text content is truncated.
  4. Admin GET /jobs/:id/assets → access.full_access=true,
     locked=false, full content visible.
  5. Free user POST /jobs/:id/unlock → 402 (credit unlock no longer
     accepted; subscribers/admin unlock for free).
  6. Free user POST /media/download-token for a viral asset → 402.
  7. Admin POST /media/download-token for a viral asset → 200 + url.
"""
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
    r = requests.post(
        f"{API}/api/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    r.raise_for_status()
    d = r.json()
    return d.get("access_token") or d.get("token")


def _ensure_free_user():
    db = _mongo()
    email = "viral_free_fixture@test.com"
    password = "Viral@2026Test#"
    pwd = _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()
    if not db.users.find_one({"email": email}):
        db.users.insert_one({
            "id": str(uuid.uuid4()), "email": email, "name": "Viral Free",
            "password": pwd, "role": "user", "plan": "free", "credits": 0,
            "subscription": None, "is_unlimited": False, "emailVerified": True,
        })
    else:
        db.users.update_one({"email": email}, {"$set": {
            "plan": "free", "subscription": None, "is_unlimited": False,
            "role": "user", "credits": 0, "password": pwd,
        }})
    return email, password


def _user_id_for(email):
    return _mongo().users.find_one({"email": email}, {"id": 1, "_id": 0})["id"]


_LONG_HOOK = ("Hook line one that is quite long\nHook line two\nHook line three\nHook line four")
_LONG_SCRIPT = ("Hook: Stop scrolling…\n\nScene 1: long script paragraph that should be hidden for free users." * 4)


def _seed_ready_viral_job(user_id):
    """Insert a synthetic READY viral_jobs doc + assets so we can exercise
    the access gate without round-tripping through the LLM pipeline."""
    db = _mongo()
    jid = f"viral_test_{uuid.uuid4().hex[:12]}"
    db.viral_jobs.insert_one({
        "job_id": jid, "user_id": user_id,
        "idea": "Test viral idea", "niche": "Tech",
        "status": "completed", "locked": False,
        "progress": {"percent": 100, "message": "Ready"},
        "created_at": datetime.now(timezone.utc),
        "completed_at": datetime.now(timezone.utc),
    })
    base = {"job_id": jid, "created_at": datetime.now(timezone.utc), "mime_type": "text/plain"}
    db.viral_assets.insert_many([
        {**base, "asset_id": f"a_{uuid.uuid4().hex[:10]}", "asset_type": "hooks", "content": _LONG_HOOK},
        {**base, "asset_id": f"a_{uuid.uuid4().hex[:10]}", "asset_type": "script", "content": _LONG_SCRIPT},
        {**base, "asset_id": f"a_{uuid.uuid4().hex[:10]}", "asset_type": "captions", "content": "Cap1\nCap2\nCap3\nCap4"},
    ])
    return jid


def _cleanup(jid):
    db = _mongo()
    db.viral_jobs.delete_one({"job_id": jid})
    db.viral_assets.delete_many({"job_id": jid})


# ─── Tests ────────────────────────────────────────────────────────────


def test_free_user_generate_bundle_blocked_402():
    email, password = _ensure_free_user()
    token = _login(email, password)
    r = requests.post(
        f"{API}/api/viral-ideas/generate-bundle",
        headers={"Authorization": f"Bearer {token}"},
        json={"idea": "Test viral idea", "niche": "Tech"},
        timeout=30,
    )
    assert r.status_code == 402, r.text
    assert r.headers.get("content-type", "").startswith("application/json")
    assert "subscribe" in (r.json().get("detail") or "").lower()


def test_admin_generate_bundle_succeeds():
    token = _login("admin@creatorstudio.ai", "Cr3@t0rStud!o#2026")
    r = requests.post(
        f"{API}/api/viral-ideas/generate-bundle",
        headers={"Authorization": f"Bearer {token}"},
        json={"idea": "Test viral idea — admin path", "niche": "Tech"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload.get("job_id")
    assert payload.get("locked") is False
    # Cleanup so we don't queue real LLM workers.
    _cleanup(payload["job_id"])


def test_free_user_assets_locked_and_truncated():
    email, password = _ensure_free_user()
    token = _login(email, password)
    user_id = _user_id_for(email)
    jid = _seed_ready_viral_job(user_id)
    try:
        r = requests.get(
            f"{API}/api/viral-ideas/jobs/{jid}/assets",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        access = body.get("access") or {}
        assert access.get("full_access") is False
        assert access.get("upgrade_required") is True
        assert body.get("locked") is True
        # Asset text must be truncated for free users.
        script_asset = next(a for a in body["assets"] if a["asset_type"] == "script")
        assert "Unlock to see full content" in (script_asset.get("content") or "")
    finally:
        _cleanup(jid)


def test_admin_assets_unlocked_and_full():
    token = _login("admin@creatorstudio.ai", "Cr3@t0rStud!o#2026")
    admin_id = _user_id_for("admin@creatorstudio.ai")
    jid = _seed_ready_viral_job(admin_id)
    try:
        r = requests.get(
            f"{API}/api/viral-ideas/jobs/{jid}/assets",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        access = body.get("access") or {}
        assert access.get("full_access") is True
        assert body.get("locked") is False
        script_asset = next(a for a in body["assets"] if a["asset_type"] == "script")
        assert script_asset["content"] == _LONG_SCRIPT
    finally:
        _cleanup(jid)


def test_free_user_unlock_returns_402():
    email, password = _ensure_free_user()
    token = _login(email, password)
    user_id = _user_id_for(email)
    jid = _seed_ready_viral_job(user_id)
    # Force the job's own locked flag to simulate a paywalled pack.
    _mongo().viral_jobs.update_one({"job_id": jid}, {"$set": {"locked": True}})
    try:
        r = requests.post(
            f"{API}/api/viral-ideas/jobs/{jid}/unlock",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        assert r.status_code == 402, r.text
        assert r.headers.get("content-type", "").startswith("application/json")
    finally:
        _cleanup(jid)


def test_free_user_download_token_blocked_402():
    email, password = _ensure_free_user()
    token = _login(email, password)
    user_id = _user_id_for(email)
    jid = _seed_ready_viral_job(user_id)
    asset = _mongo().viral_assets.find_one({"job_id": jid, "asset_type": "hooks"})
    try:
        r = requests.post(
            f"{API}/api/media/download-token",
            headers={"Authorization": f"Bearer {token}"},
            json={"asset_id": asset["asset_id"]},
            timeout=30,
        )
        assert r.status_code == 402, r.text
        assert r.headers.get("content-type", "").startswith("application/json")
    finally:
        _cleanup(jid)


def test_admin_download_token_succeeds():
    token = _login("admin@creatorstudio.ai", "Cr3@t0rStud!o#2026")
    admin_id = _user_id_for("admin@creatorstudio.ai")
    jid = _seed_ready_viral_job(admin_id)
    asset = _mongo().viral_assets.find_one({"job_id": jid, "asset_type": "hooks"})
    try:
        r = requests.post(
            f"{API}/api/media/download-token",
            headers={"Authorization": f"Bearer {token}"},
            json={"asset_id": asset["asset_id"]},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("url")
        assert body.get("single_use") is True
    finally:
        _cleanup(jid)
