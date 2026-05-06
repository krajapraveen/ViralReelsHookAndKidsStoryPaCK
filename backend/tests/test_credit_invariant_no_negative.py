"""Regression test for the no-negative-credits invariant.

Founder spec:
    plan=free + credits=1 + required_episode_cost > 1 => episode generation
    blocked, balance remains 1.

This is the line the entire credit economy relies on. A single off-by-one
here means the series count-cap relaxation could be exploited to create
content for free. The atomic compare-and-deduct in credits_service.py
(line 86-94) is the guard.
"""
import os
import sys
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_deduct_with_insufficient_balance_raises_and_does_not_mutate():
    """Atomic guard: deduct_credits with amount > balance must:
       1. Raise InsufficientCreditsError
       2. NOT mutate the user document (find_one_and_update returns None)
       3. Surface the actual current balance in the error
    """
    from services.credits_service import CreditsService, InsufficientCreditsError

    fake_users = MagicMock()
    # Atomic match fails — find_one_and_update returns None
    fake_users.find_one_and_update = AsyncMock(return_value=None)
    # Subsequent fresh-balance fetch
    fake_users.find_one = AsyncMock(return_value={"id": "u1", "credits": 1, "is_unlimited": False})
    fake_ledger = MagicMock()
    fake_ledger.insert_one = AsyncMock()

    svc = CreditsService(users=fake_users, ledger=fake_ledger)

    with pytest.raises(InsufficientCreditsError) as exc_info:
        asyncio.run(svc.deduct_credits("u1", amount=5, reason="episode_generation"))

    # Confirm error carries truthful balance
    err = exc_info.value
    assert "1" in str(err) or getattr(err, "current", None) == 1 or getattr(err, "available", None) == 1

    # Confirm exact MongoDB filter included $gte guard (atomic invariant)
    call_args = fake_users.find_one_and_update.await_args
    filter_arg = call_args.args[0] if call_args.args else call_args.kwargs.get("filter")
    assert filter_arg["id"] == "u1"
    assert filter_arg["credits"] == {"$gte": 5}, (
        "deduct_credits must use $gte:amount in the filter — this is the "
        "no-negative-balance guard. Removing it allows races and underflow."
    )


def test_deduct_with_exactly_enough_balance_succeeds():
    """credits=5, amount=5 → succeeds, new_balance=0."""
    from services.credits_service import CreditsService

    fake_users = MagicMock()
    fake_users.find_one_and_update = AsyncMock(return_value={"credits": 0})
    fake_users.find_one = AsyncMock(return_value={"id": "u1", "credits": 5, "is_unlimited": False})
    fake_ledger = MagicMock()
    fake_ledger.insert_one = AsyncMock()

    svc = CreditsService(users=fake_users, ledger=fake_ledger)
    res = asyncio.run(svc.deduct_credits("u1", amount=5, reason="episode_generation"))

    assert res["success"] is True
    assert res["new_balance"] == 0


def test_unlimited_user_bypass_does_not_deduct():
    """is_unlimited users skip deduction entirely (admin/dev/qa/test/owner)."""
    from services.credits_service import CreditsService

    fake_users = MagicMock()
    fake_users.find_one = AsyncMock(return_value={
        "id": "admin1", "credits": 999999999, "is_unlimited": True
    })
    fake_users.find_one_and_update = AsyncMock()
    fake_ledger = MagicMock()
    fake_ledger.insert_one = AsyncMock()

    svc = CreditsService(users=fake_users, ledger=fake_ledger)
    res = asyncio.run(svc.deduct_credits("admin1", amount=50, reason="episode_generation"))

    assert res["success"] is True
    assert res["amount"] == 0  # bypass — nothing actually deducted
    fake_users.find_one_and_update.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
