"""Tests for the centralized entitlement helper (services/entitlement.py).

After 6+ surface-level admin/credit bugs in 24 hours, all routes now route
through `require_credits()` and `is_unlimited_user()`. These tests are the
regression guard against the next surface inventing its own broken check.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.entitlement import (
    is_unlimited_user,
    has_paid_access,
    has_premium_access,
    require_credits,
    entitlement_snapshot,
)
from fastapi import HTTPException


# ─── is_unlimited_user ───────────────────────────────────────────────────


def test_is_unlimited_admin_role_uppercase():
    assert is_unlimited_user({"role": "ADMIN", "credits": 0}) is True


def test_is_unlimited_admin_role_lowercase():
    assert is_unlimited_user({"role": "admin", "credits": 0}) is True


def test_is_unlimited_all_unlimited_roles():
    for role in ("admin", "owner", "dev", "qa", "test", "DEV", "QA"):
        assert is_unlimited_user({"role": role}) is True, f"role={role}"


def test_is_unlimited_flag():
    assert is_unlimited_user({"role": "user", "is_unlimited": True}) is True


def test_is_unlimited_normal_user_false():
    assert is_unlimited_user({"role": "user", "is_unlimited": False, "credits": 9999}) is False


def test_is_unlimited_none_user():
    assert is_unlimited_user(None) is False


def test_is_unlimited_empty_dict():
    assert is_unlimited_user({}) is False


# ─── has_paid_access ─────────────────────────────────────────────────────


def test_paid_access_admin_with_zero_credits():
    """Admin must always have paid access even with credits=0."""
    assert has_paid_access({"role": "admin", "credits": 0}) is True


def test_paid_access_topup_user():
    """Top-up user: free plan + credits → has access."""
    assert has_paid_access({"role": "user", "plan": "free", "credits": 209}) is True


def test_paid_access_subscriber():
    """Subscriber: paid plan + zero credits → still has access."""
    assert has_paid_access({"role": "user", "plan": "creator", "credits": 0}) is True


def test_paid_access_true_free_user():
    """Free plan + zero credits → no access."""
    assert has_paid_access({"role": "user", "plan": "free", "credits": 0}) is False


def test_paid_access_handles_plan_type_alias():
    """Some routes set `plan_type` instead of `plan` — must still work."""
    assert has_paid_access({"role": "user", "plan_type": "creator", "credits": 0}) is True


# ─── has_premium_access ──────────────────────────────────────────────────


def test_premium_admin_yes():
    assert has_premium_access({"role": "admin"}) is True


def test_premium_subscriber_yes():
    for plan in ("creator", "pro", "studio", "starter", "premium"):
        assert has_premium_access({"role": "user", "plan": plan}) is True, f"plan={plan}"


def test_premium_topup_user_NO():
    """Credits alone don't grant premium — only paid plans do."""
    assert has_premium_access({"role": "user", "plan": "free", "credits": 1000}) is False


def test_premium_free_user_no():
    assert has_premium_access({"role": "user", "plan": "free", "credits": 0}) is False


# ─── require_credits ─────────────────────────────────────────────────────


def test_require_credits_admin_bypass_with_zero():
    """Admin with credits=0 must pass require_credits for any cost."""
    require_credits({"role": "admin", "credits": 0}, cost=999)  # must not raise


def test_require_credits_unlimited_flag_bypass():
    require_credits({"role": "user", "is_unlimited": True, "credits": 0}, cost=999)


def test_require_credits_sufficient():
    require_credits({"role": "user", "credits": 100}, cost=50)  # must not raise


def test_require_credits_insufficient_raises_402():
    with pytest.raises(HTTPException) as exc_info:
        require_credits({"role": "user", "credits": 2}, cost=10, feature="comic strip")
    err = exc_info.value
    assert err.status_code == 402
    assert "Required: 10" in err.detail
    assert "Available: 2" in err.detail


def test_require_credits_none_user_raises():
    """None user is treated as having 0 credits → must raise for any positive cost."""
    with pytest.raises(HTTPException) as exc_info:
        require_credits(None, cost=5)
    assert exc_info.value.status_code == 402


def test_require_credits_exact_match_succeeds():
    """credits == cost is a valid pass."""
    require_credits({"role": "user", "credits": 50}, cost=50)


# ─── entitlement_snapshot ────────────────────────────────────────────────


def test_snapshot_admin():
    snap = entitlement_snapshot({"role": "admin", "credits": 999999999, "plan": "free"})
    assert snap["is_unlimited"] is True
    assert snap["has_paid_access"] is True
    assert snap["has_premium_access"] is True


def test_snapshot_topup_user():
    snap = entitlement_snapshot({"role": "user", "credits": 209, "plan": "free"})
    assert snap["is_unlimited"] is False
    assert snap["has_paid_access"] is True
    assert snap["has_premium_access"] is False


def test_snapshot_free_user():
    snap = entitlement_snapshot({"role": "user", "credits": 0, "plan": "free"})
    assert snap["is_unlimited"] is False
    assert snap["has_paid_access"] is False
    assert snap["has_premium_access"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
