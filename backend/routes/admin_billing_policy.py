"""Admin verification endpoint for the zero-free-credits policy migration."""
from fastapi import APIRouter, Depends, HTTPException
from shared import db, get_admin_user

router = APIRouter(prefix="/admin/billing-policy", tags=["admin-billing-policy"])


@router.get("/verification")
async def policy_verification_report(user: dict = Depends(get_admin_user)):
    """Returns the post-migration audit report.

    Expected after migration:
      users_with_credits_gt_zero (excluding admin/unlimited/subscribed) = 0
      users_with_free_credit_flag = 0
      signup_bonus_grants (recent) = 0
    """
    UNLIMITED_ROLES = {"admin", "ADMIN", "dev", "qa", "test"}

    total_users = await db.users.count_documents({})
    users_with_credits = await db.users.count_documents({
        "credits": {"$gt": 0},
        "role": {"$nin": list(UNLIMITED_ROLES)},
        "is_unlimited": {"$ne": True},
        "subscription_status": {"$ne": "active"},
    })
    bonus_flags = await db.users.count_documents({"signup_bonus_granted": True})
    revoked_count = await db.users.count_documents({"free_credits_revoked_at": {"$exists": True}})

    # signup-grant ledger rows in the last 7 days (must be 0 after this patch ships)
    from datetime import datetime, timezone, timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    recent_signup_grants = await db.credit_ledger.count_documents({
        "type": "SIGNUP",
        "amount": {"$gt": 0},
        "createdAt": {"$gte": cutoff},
    })

    # Users who tried to generate but were blocked (read-only count from a
    # dedicated collection — empty if nothing has been instrumented yet).
    blocked_attempts = await db.subscription_blocked_attempts.count_documents({})

    return {
        "total_users": total_users,
        "users_with_credits_gt_zero": users_with_credits,
        "users_with_free_credit_flag": bonus_flags,
        "signup_credit_grants_last_7_days": recent_signup_grants,
        "users_revoked_free_credits": revoked_count,
        "blocked_unsubscribed_generation_attempts": blocked_attempts,
        "policy": "subscription_required_2026_05",
        "expected": {
            "users_with_credits_gt_zero": 0,
            "users_with_free_credit_flag": 0,
            "signup_credit_grants_last_7_days": 0,
        },
    }
