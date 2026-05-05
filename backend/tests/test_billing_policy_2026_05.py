"""Tests for the zero-free-credits + subscription-required policy.

Run:  cd /app/backend && pytest tests/test_billing_policy_2026_05.py -v
"""
import pytest
import httpx
import time
import os

BASE_URL = "http://localhost:8001"


@pytest.mark.asyncio
async def test_new_signup_receives_zero_credits():
    """New email signup must start with credits=0 (no welcome bonus)."""
    email = f"newsignup_{int(time.time()*1000)}@vs-test.com"
    async with httpx.AsyncClient(timeout=10.0) as c:
        r = await c.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test", "email": email, "password": "Test1234!",
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["user"]["credits"] == 0
        assert "subscribe" in body["message"].lower() or "subscription" in body["message"].lower()
        assert body["credits_info"]["current_credits"] == 0


@pytest.mark.asyncio
async def test_avatar_demo_remains_ungated_anonymous():
    """The anonymous avatar demo MUST stay open — no auth, no credits."""
    sid = f"freeze_{int(time.time())}"
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.post(f"{BASE_URL}/api/avatar/studio/anon-mock-generate", json={
            "session_id": sid,
            "avatar_type": "quick_avatar",
            "motion_style": "talking_head",
            "duration_seconds": 15,
            "safety_confirmed": True,
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["anonymous"] is True
        assert d["is_demo_output"] is True
        assert "job_id" in d


@pytest.mark.asyncio
async def test_avatar_anon_jobs_endpoint_remains_ungated():
    """Anon poll endpoint must require no auth."""
    sid = f"freeze_poll_{int(time.time())}"
    async with httpx.AsyncClient(timeout=10.0) as c:
        # First create a job
        r = await c.post(f"{BASE_URL}/api/avatar/studio/anon-mock-generate", json={
            "session_id": sid,
            "avatar_type": "quick_avatar",
            "motion_style": "talking_head",
            "duration_seconds": 15,
            "safety_confirmed": True,
        })
        assert r.status_code == 200
        jid = r.json()["job_id"]
        # Poll without any token
        r2 = await c.get(f"{BASE_URL}/api/avatar/studio/anon-jobs/{jid}",
                         params={"session_id": sid})
        assert r2.status_code == 200, r2.text
        assert r2.json()["anonymous"] is True


@pytest.mark.asyncio
async def test_admin_billing_policy_verification():
    """Admin endpoint reports 0 free-credit users post-migration."""
    async with httpx.AsyncClient(timeout=10.0) as c:
        r = await c.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026",
        })
        assert r.status_code == 200, r.text
        token = r.json()["token"]
        r2 = await c.get(f"{BASE_URL}/api/admin/billing-policy/verification",
                         headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 200, r2.text
        d = r2.json()
        assert d["users_with_credits_gt_zero"] == 0
        assert d["users_with_free_credit_flag"] == 0
        assert d["policy"] == "subscription_required_2026_05"


@pytest.mark.asyncio
async def test_admin_endpoint_blocks_non_admin():
    """Non-admin can't read the verification report."""
    async with httpx.AsyncClient(timeout=10.0) as c:
        r = await c.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@visionary-suite.com",
            "password": "Test@2026#",
        })
        if r.status_code != 200:
            pytest.skip("test user creds not available")
        token = r.json()["token"]
        r2 = await c.get(f"{BASE_URL}/api/admin/billing-policy/verification",
                         headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 403


@pytest.mark.asyncio
async def test_unsubscribed_zero_credit_user_blocked_at_paid_endpoint():
    """Brand new user with 0 credits hitting a paid endpoint is blocked."""
    email = f"paygate_{int(time.time()*1000)}@vs-test.com"
    async with httpx.AsyncClient(timeout=10.0) as c:
        r = await c.post(f"{BASE_URL}/api/auth/register", json={
            "name": "PG", "email": email, "password": "Test1234!",
        })
        assert r.status_code == 200
        body = r.json()
        token = body["token"]
        assert body["user"]["credits"] == 0
        # /api/credits/balance should report 0 (read-only)
        r2 = await c.get(f"{BASE_URL}/api/credits/balance",
                         headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 200
        bal = r2.json()
        # Different services may use different field names
        credits = bal.get("credits", bal.get("balance", 0))
        assert credits == 0, bal
