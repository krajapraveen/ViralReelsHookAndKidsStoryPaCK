"""
P0 2026-05 regression — Bedtime Stories subscription access gate.

Validates that:
  1. Free users receive a preview-only payload (1 scene + access flags).
  2. Subscribers (active subscription doc) receive the full payload.
  3. Admin / unlimited users receive the full payload.
  4. The /export endpoint refuses free users with HTTP 402.

These tests guard against future regressions where the full story text is
accidentally exposed to free users via the API.
"""
import os
import re
import time
import requests
import pytest


def _read_env():
    with open("/app/frontend/.env") as f:
        text = f.read()
    m = re.search(r"^REACT_APP_BACKEND_URL=(.*)$", text, flags=re.M)
    return m.group(1).strip() if m else "http://localhost:8001"


API = _read_env()


def _login(email, password):
    r = requests.post(
        f"{API}/api/auth/login",
        json={"email": email, "password": password},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    return data.get("access_token") or data.get("token")


def _generate(token):
    r = requests.post(
        f"{API}/api/bedtime-story-builder/generate",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "age_group": "6-8",
            "theme": "Friendship",
            "moral": "Be kind",
            "length": "3",
            "voice_style": "calm_parent",
            "child_name": "RegressionPip",
            "mood": "calm",
        },
        timeout=60,
    )
    return r


def _provision_free_user_with_credits():
    """Create / reset a fixed free user (DB-direct) with 50 credits.

    We bypass /api/auth/register to avoid the per-IP signup throttle. The
    user is reused across runs and reset to plan=free/credits=50 on entry.
    """
    from pymongo import MongoClient
    import uuid as _uuid
    import bcrypt as _bcrypt

    with open("/app/backend/.env") as f:
        env_text = f.read()
    mongo = re.search(r"^MONGO_URL=(.*)$", env_text, flags=re.M).group(1).strip().strip('"')
    db_name = re.search(r"^DB_NAME=(.*)$", env_text, flags=re.M).group(1).strip().strip('"')

    email = "bedtime_gate_fixture@test.com"
    password = "Bedtime@2026Test#"

    client = MongoClient(mongo)
    db = client[db_name]
    existing = db.users.find_one({"email": email})
    pwd_hash = _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()
    if not existing:
        db.users.insert_one({
            "id": str(_uuid.uuid4()),
            "email": email,
            "name": "Bedtime Gate Fixture",
            "password": pwd_hash,
            "role": "user",
            "plan": "free",
            "credits": 50,
            "subscription": None,
            "is_unlimited": False,
            "emailVerified": True,
            "tourCompleted": True,
        })
    else:
        db.users.update_one(
            {"email": email},
            {"$set": {
                "credits": 50,
                "plan": "free",
                "subscription": None,
                "is_unlimited": False,
                "role": "user",
                "password": pwd_hash,
            }},
        )

    token = _login(email, password)
    return email, password, token


def test_free_user_receives_preview_only_payload():
    _email, _pw, token = _provision_free_user_with_credits()
    r = _generate(token)
    assert r.status_code == 200, r.text
    story = r.json()["story"]
    access = story.get("access") or {}

    assert access.get("full_access") is False
    assert access.get("preview_only") is True
    assert access.get("upgrade_required") is True
    assert access.get("preview_scenes") == 1
    assert access.get("total_scenes", 0) >= 1
    # Critical: the backend MUST NOT leak the full story text to free users.
    assert len(story.get("scenes") or []) == 1


def test_free_user_export_is_blocked():
    _email, _pw, token = _provision_free_user_with_credits()
    r = requests.post(
        f"{API}/api/bedtime-story-builder/export",
        params={"format": "txt"},
        headers={"Authorization": f"Bearer {token}"},
        json={"script": "irrelevant"},
        timeout=10,
    )
    assert r.status_code == 402, r.text
    assert "subscribe" in r.json().get("detail", "").lower()


@pytest.mark.skipif(
    not os.environ.get("ADMIN_PASSWORD") and not os.path.exists("/app/memory/test_credentials.md"),
    reason="admin credentials unavailable in this env",
)
def test_admin_receives_full_payload():
    # Pulled from /app/memory/test_credentials.md / handoff.
    token = _login("admin@creatorstudio.ai", "Cr3@t0rStud!o#2026")
    r = _generate(token)
    assert r.status_code == 200, r.text
    story = r.json()["story"]
    access = story.get("access") or {}
    assert access.get("full_access") is True
    assert access.get("preview_only") is False
    assert len(story.get("scenes") or []) >= 2
    assert access.get("preview_scenes") == access.get("total_scenes")


def test_subscriber_receives_full_payload():
    """The QA test user has an active yearly subscription document."""
    try:
        token = _login("test@visionary-suite.com", "Test@2026#")
    except Exception:
        pytest.skip("test user credentials unavailable")
    r = _generate(token)
    assert r.status_code == 200, r.text
    story = r.json()["story"]
    access = story.get("access") or {}
    assert access.get("full_access") is True
    assert access.get("preview_only") is False
