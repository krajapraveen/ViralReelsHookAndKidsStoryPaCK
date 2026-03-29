"""
Credits Service — Single source of truth for all credit operations.
All credit checks, deductions, refunds, and awards MUST go through this service.
No route should use db.users.update_one({"$inc": {"credits": ...}}) directly.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Tuple

logger = logging.getLogger("credits_service")


class CreditResult:
    """Standard result from any credit operation."""
    __slots__ = ("success", "new_balance", "amount", "error")

    def __init__(self, success: bool, new_balance: int = 0, amount: int = 0, error: str = ""):
        self.success = success
        self.new_balance = new_balance
        self.amount = amount
        self.error = error

    def to_dict(self) -> dict:
        return {"success": self.success, "new_balance": self.new_balance, "amount": self.amount, "error": self.error}


# Exempt emails and roles that get unlimited credits
EXEMPT_EMAILS = {"admin@creatorstudio.ai", "test@visionary-suite.com", "demo@visionary-suite.com"}
EXEMPT_ROLES = {"admin", "ADMIN"}


def is_exempt(user: dict) -> bool:
    """Check if user is credit-exempt (admin/test accounts)."""
    return (
        user.get("email", "") in EXEMPT_EMAILS
        or user.get("role", "") in EXEMPT_ROLES
    )


async def get_balance(db, user_id: str) -> Dict:
    """Get current credit balance for a user."""
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "credits": 1, "email": 1, "role": 1, "plan": 1})
    if not user:
        return {"credits": 0, "is_unlimited": False, "plan": "free"}
    exempt = is_exempt(user)
    return {
        "credits": 999999 if exempt else user.get("credits", 0),
        "is_unlimited": exempt,
        "plan": "pro" if exempt else user.get("plan", "free"),
    }


async def check_sufficient(db, user_id: str, required: int) -> Tuple[bool, int, int]:
    """
    Check if user has enough credits. Returns (sufficient, current_balance, shortfall).
    Exempt users always pass.
    """
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "credits": 1, "email": 1, "role": 1})
    if not user:
        return False, 0, required
    if is_exempt(user):
        return True, 999999, 0
    current = user.get("credits", 0)
    shortfall = max(0, required - current)
    return current >= required, current, shortfall


async def deduct(db, user_id: str, amount: int, reason: str, job_id: str = "") -> CreditResult:
    """
    Atomically deduct credits. Fails if insufficient.
    Logs to credit_ledger.
    """
    if amount <= 0:
        return CreditResult(success=True, new_balance=0, amount=0)

    # Check exemption first
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "email": 1, "role": 1, "credits": 1})
    if not user:
        return CreditResult(success=False, error="User not found")
    if is_exempt(user):
        logger.info(f"[CREDITS] Exempt user {user_id[:8]}, skip deduction of {amount} for: {reason}")
        return CreditResult(success=True, new_balance=999999, amount=0)

    # Atomic deduction — only succeeds if credits >= amount
    result = await db.users.update_one(
        {"id": user_id, "credits": {"$gte": amount}},
        {"$inc": {"credits": -amount}},
    )
    if result.modified_count == 0:
        current = user.get("credits", 0)
        return CreditResult(success=False, new_balance=current, amount=0,
                            error=f"Insufficient credits. Required: {amount}, Available: {current}")

    # Log to ledger
    now = datetime.now(timezone.utc).isoformat()
    await db.credit_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "amount": -amount,
        "type": "USAGE",
        "description": reason,
        "job_id": job_id,
        "createdAt": now,
    })

    # Get updated balance
    updated = await db.users.find_one({"id": user_id}, {"_id": 0, "credits": 1})
    new_balance = updated.get("credits", 0) if updated else 0

    logger.info(f"[CREDITS] Deducted {amount} from {user_id[:8]} for: {reason}. New balance: {new_balance}")
    return CreditResult(success=True, new_balance=new_balance, amount=amount)


async def refund(db, user_id: str, amount: int, reason: str, job_id: str = "") -> CreditResult:
    """
    Refund credits to a user. Always succeeds (additive).
    Logs to credit_ledger.
    """
    if amount <= 0:
        return CreditResult(success=True, new_balance=0, amount=0)

    # Check exemption
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "email": 1, "role": 1})
    if not user:
        return CreditResult(success=False, error="User not found")
    if is_exempt(user):
        logger.info(f"[CREDITS] Exempt user {user_id[:8]}, skip refund of {amount}")
        return CreditResult(success=True, new_balance=999999, amount=0)

    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"credits": amount}},
    )

    now = datetime.now(timezone.utc).isoformat()
    await db.credit_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "amount": amount,
        "type": "REFUND",
        "description": reason,
        "job_id": job_id,
        "createdAt": now,
    })

    updated = await db.users.find_one({"id": user_id}, {"_id": 0, "credits": 1})
    new_balance = updated.get("credits", 0) if updated else 0

    logger.info(f"[CREDITS] Refunded {amount} to {user_id[:8]} for: {reason}. New balance: {new_balance}")
    return CreditResult(success=True, new_balance=new_balance, amount=amount)


async def award(db, user_id: str, amount: int, reason: str, award_type: str = "REWARD") -> CreditResult:
    """
    Award credits (challenge completion, streak milestone, signup bonus, etc.).
    Logs to credit_ledger.
    """
    if amount <= 0:
        return CreditResult(success=True, new_balance=0, amount=0)

    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"credits": amount}},
    )

    now = datetime.now(timezone.utc).isoformat()
    await db.credit_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "amount": amount,
        "type": award_type,
        "description": reason,
        "createdAt": now,
    })

    updated = await db.users.find_one({"id": user_id}, {"_id": 0, "credits": 1})
    new_balance = updated.get("credits", 0) if updated else 0

    logger.info(f"[CREDITS] Awarded {amount} to {user_id[:8]} for: {reason}. New balance: {new_balance}")
    return CreditResult(success=True, new_balance=new_balance, amount=amount)
