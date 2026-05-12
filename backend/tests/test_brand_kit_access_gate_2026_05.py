"""
P0/P1 2026-05 — Brand Kit / Brand Story access-gate regression.

Validates:
  1. Admin/unlimited GET /job/:id/result → access.full_access=true and the
     full text of each artifact is returned.
  2. Free user GET /job/:id/result → access.preview_only=true and the
     artifact text is truncated server-side (no full payload leaks).
  3. Free user GET /job/:id/pdf  → HTTP 402 with clean JSON detail.
  4. Free user GET /job/:id/zip  → HTTP 402 with clean JSON detail.
  5. Admin   GET /job/:id/pdf    → 200 application/pdf body.
  6. Admin   GET /job/:id/zip    → 200 application/zip body.
  7. Missing job → JSON 404 (never raw HTML).
"""
import io
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
    email = "brandkit_free_fixture@test.com"
    password = "BrandKit@2026Test#"
    pwd_hash = _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()
    if not db.users.find_one({"email": email}):
        db.users.insert_one({
            "id": str(uuid.uuid4()),
            "email": email,
            "name": "BrandKit Free",
            "password": pwd_hash,
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
            "role": "user", "credits": 0, "password": pwd_hash,
        }})
    return email, password


def _user_id_for(email):
    return _mongo().users.find_one({"email": email}, {"id": 1, "_id": 0})["id"]


_LONG_TEXT = ("In a world where connection often feels superficial, our team "
              "envisioned a platform that fosters genuine professional "
              "relationships. " * 6)


def _seed_ready_job(user_id):
    """Insert a synthetic READY brand_kit_job so we can exercise the
    access gate without round-tripping through the LLM orchestrator."""
    db = _mongo()
    jid = f"bk_test_{uuid.uuid4().hex[:12]}"
    db.brand_kit_jobs.insert_one({
        "id": jid,
        "userId": user_id,
        "status": "READY",
        "mode": "pro",
        "progress": 100,
        "purchased": False,
        "brief": {"business_name": "Test Brand"},
        "artifacts": {
            "short_brand_story": {"status": "READY", "data": {"short_brand_story": _LONG_TEXT}, "latency_ms": 1000},
            "long_brand_story":  {"status": "READY", "data": {"long_brand_story": _LONG_TEXT}, "latency_ms": 1500},
            "taglines": {"status": "READY", "data": {"taglines": [
                {"text": "Tagline one — long enough to truncate quite plainly.", "style": "bold"},
                {"text": "Tagline two", "style": "concise"},
            ]}, "latency_ms": 500},
            "color_palettes": {"status": "READY", "data": {"palettes": [
                {"name": "Primary", "colors": ["#112233", "#445566", "#778899"]},
            ]}, "latency_ms": 300},
        },
        "total_artifacts": 4,
        "completed_artifacts": 4,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    })
    return jid


def _cleanup_job(jid):
    _mongo().brand_kit_jobs.delete_one({"id": jid})


# ─── Tests ────────────────────────────────────────────────────────────


def test_admin_result_has_full_access_and_full_text():
    token = _login("admin@creatorstudio.ai", "Cr3@t0rStud!o#2026")
    admin_id = _user_id_for("admin@creatorstudio.ai")
    jid = _seed_ready_job(admin_id)
    try:
        r = requests.get(
            f"{API}/api/brand-story-builder/job/{jid}/result",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        payload = r.json()
        access = payload.get("access") or {}
        assert access.get("full_access") is True
        assert access.get("preview_only") is False
        outputs = payload["outputs"]
        # Full text returned for admin (matches the seeded long text exactly).
        assert outputs["short_brand_story"]["data"] == {"short_brand_story": _LONG_TEXT}
        assert outputs["long_brand_story"]["data"] == {"long_brand_story": _LONG_TEXT}
        assert isinstance(outputs["taglines"]["data"], dict)
        assert len(outputs["taglines"]["data"].get("taglines", [])) == 2
    finally:
        _cleanup_job(jid)


def test_free_user_result_is_preview_only_and_truncated():
    email, password = _ensure_free_user()
    token = _login(email, password)
    user_id = _user_id_for(email)
    jid = _seed_ready_job(user_id)
    try:
        r = requests.get(
            f"{API}/api/brand-story-builder/job/{jid}/result",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        payload = r.json()
        access = payload.get("access") or {}
        assert access.get("full_access") is False
        assert access.get("preview_only") is True
        assert access.get("upgrade_required") is True
        outputs = payload["outputs"]
        # Free user must NOT receive the full text. The preview is capped
        # at ~140 chars + ellipsis. The data dict's `short_brand_story`
        # field is the truncated text.
        short_dict = outputs["short_brand_story"]["data"]
        assert isinstance(short_dict, dict)
        short_text = short_dict.get("short_brand_story", "")
        assert isinstance(short_text, str)
        assert len(short_text) <= 150
        assert short_text != _LONG_TEXT
        assert short_text.endswith("…")
        # Lists/dicts are recursively truncated: the taglines list inside
        # the data dict is reduced to its first item.
        tag_data = outputs["taglines"]["data"]
        assert isinstance(tag_data, dict)
        assert len(tag_data.get("taglines", [])) == 1
    finally:
        _cleanup_job(jid)


def test_free_user_pdf_download_blocked_402():
    email, password = _ensure_free_user()
    token = _login(email, password)
    user_id = _user_id_for(email)
    jid = _seed_ready_job(user_id)
    try:
        r = requests.get(
            f"{API}/api/brand-story-builder/job/{jid}/pdf",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        assert r.status_code == 402, r.text
        assert r.headers.get("content-type", "").startswith("application/json")
        assert "subscribe" in (r.json().get("detail") or "").lower()
    finally:
        _cleanup_job(jid)


def test_free_user_zip_download_blocked_402():
    email, password = _ensure_free_user()
    token = _login(email, password)
    user_id = _user_id_for(email)
    jid = _seed_ready_job(user_id)
    try:
        r = requests.get(
            f"{API}/api/brand-story-builder/job/{jid}/zip",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        assert r.status_code == 402, r.text
        assert r.headers.get("content-type", "").startswith("application/json")
    finally:
        _cleanup_job(jid)


def test_admin_pdf_download_succeeds():
    token = _login("admin@creatorstudio.ai", "Cr3@t0rStud!o#2026")
    admin_id = _user_id_for("admin@creatorstudio.ai")
    jid = _seed_ready_job(admin_id)
    try:
        r = requests.get(
            f"{API}/api/brand-story-builder/job/{jid}/pdf",
            headers={"Authorization": f"Bearer {token}"},
            timeout=60,
        )
        assert r.status_code == 200, r.text[:200]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        # Must be a non-empty binary body.
        assert len(r.content) > 200
        assert r.content[:5] == b"%PDF-"
    finally:
        _cleanup_job(jid)


def test_admin_zip_download_succeeds():
    token = _login("admin@creatorstudio.ai", "Cr3@t0rStud!o#2026")
    admin_id = _user_id_for("admin@creatorstudio.ai")
    jid = _seed_ready_job(admin_id)
    try:
        r = requests.get(
            f"{API}/api/brand-story-builder/job/{jid}/zip",
            headers={"Authorization": f"Bearer {token}"},
            timeout=60,
        )
        assert r.status_code == 200, r.text[:200]
        assert r.headers.get("content-type", "").startswith("application/zip")
        # ZIP file magic.
        assert r.content[:2] == b"PK"
    finally:
        _cleanup_job(jid)


def test_missing_job_returns_clean_json_404():
    token = _login("admin@creatorstudio.ai", "Cr3@t0rStud!o#2026")
    r = requests.get(
        f"{API}/api/brand-story-builder/job/does_not_exist_xyz/result",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    assert r.status_code == 404, r.text
    assert r.headers.get("content-type", "").startswith("application/json")
    assert "not found" in (r.json().get("detail") or "").lower()
