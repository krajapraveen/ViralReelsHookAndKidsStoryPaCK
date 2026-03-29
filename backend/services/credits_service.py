"""
Credits Service — Single source of truth for all credit operations.
All credit checks, deductions, refunds, and awards MUST go through this service.
No route should use db.users.update_one({"$inc": {"credits": ...}}) directly.
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from pymongo import ReturnDocument

logger = logging.getLogger("credits_service")


class InsufficientCreditsError(Exception):
    def __init__(self, required: int, available: int):
        self.required = required
        self.available = available
        self.shortfall = max(required - available, 0)
        super().__init__(
            f"Insufficient credits. Required: {required}, Available: {available}"
        )


UNLIMITED_ROLES = {"admin", "ADMIN", "dev", "qa", "test"}


class CreditsService:
    def __init__(self, users, ledger=None):
        self.users = users
        self.ledger = ledger

    async def get_user_credit_state(self, user_id: str) -> dict:
        user = await self.users.find_one(
            {"id": user_id},
            {"_id": 0, "credits": 1, "is_unlimited": 1, "role": 1}
        )
        if not user:
            raise ValueError("User not found")

        is_unlimited = bool(user.get("is_unlimited", False)) or user.get("role", "") in UNLIMITED_ROLES
        return {
            "user_id": user_id,
            "credits": int(user.get("credits", 0)),
            "is_unlimited": is_unlimited,
            "role": user.get("role", "user"),
        }

    async def check_credits(self, user_id: str, required_credits: int) -> dict:
        state = await self.get_user_credit_state(user_id)

        if state["is_unlimited"]:
            return {
                "has_enough": True,
                "required": required_credits,
                "available": state["credits"],
                "shortfall": 0,
                "is_unlimited": True,
            }

        available = state["credits"]
        shortfall = max(required_credits - available, 0)

        return {
            "has_enough": available >= required_credits,
            "required": required_credits,
            "available": available,
            "shortfall": shortfall,
            "is_unlimited": False,
        }

    async def deduct_credits(
        self, user_id: str, amount: int, reason: str, reference_id: Optional[str] = None
    ) -> dict:
        state = await self.get_user_credit_state(user_id)

        if state["is_unlimited"]:
            await self._log(user_id, "deduct", 0, reason, reference_id)
            return {
                "success": True,
                "new_balance": state["credits"],
                "amount": 0,
                "reason": reason,
                "reference_id": reference_id,
            }

        result = await self.users.find_one_and_update(
            {"id": user_id, "credits": {"$gte": amount}},
            {
                "$inc": {"credits": -amount},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
            },
            projection={"_id": 0, "credits": 1},
            return_document=ReturnDocument.AFTER,
        )

        if not result:
            fresh = await self.get_user_credit_state(user_id)
            raise InsufficientCreditsError(amount, fresh["credits"])

        await self._log(user_id, "deduct", amount, reason, reference_id)

        new_balance = int(result.get("credits", 0))
        logger.info(f"[CREDITS] Deducted {amount} from {user_id[:8]} for: {reason}. Balance: {new_balance}")
        return {
            "success": True,
            "new_balance": new_balance,
            "amount": amount,
            "reason": reason,
            "reference_id": reference_id,
        }

    async def refund_credits(
        self, user_id: str, amount: int, reason: str, reference_id: Optional[str] = None
    ) -> dict:
        result = await self.users.find_one_and_update(
            {"id": user_id},
            {
                "$inc": {"credits": amount},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
            },
            projection={"_id": 0, "credits": 1},
            return_document=ReturnDocument.AFTER,
        )

        if not result:
            raise ValueError("User not found")

        await self._log(user_id, "refund", amount, reason, reference_id)

        new_balance = int(result.get("credits", 0))
        logger.info(f"[CREDITS] Refunded {amount} to {user_id[:8]} for: {reason}. Balance: {new_balance}")
        return {
            "success": True,
            "new_balance": new_balance,
            "amount": amount,
            "reason": reason,
            "reference_id": reference_id,
        }

    async def award_credits(
        self, user_id: str, amount: int, reason: str, reference_id: Optional[str] = None
    ) -> dict:
        result = await self.users.find_one_and_update(
            {"id": user_id},
            {
                "$inc": {"credits": amount},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
            },
            projection={"_id": 0, "credits": 1},
            return_document=ReturnDocument.AFTER,
        )

        if not result:
            raise ValueError("User not found")

        await self._log(user_id, "award", amount, reason, reference_id)

        new_balance = int(result.get("credits", 0))
        logger.info(f"[CREDITS] Awarded {amount} to {user_id[:8]} for: {reason}. Balance: {new_balance}")
        return {
            "success": True,
            "new_balance": new_balance,
            "amount": amount,
            "reason": reason,
            "reference_id": reference_id,
        }

    async def _log(self, user_id: str, tx_type: str, amount: int, reason: str, reference_id: Optional[str]):
        if self.ledger is None:
            return
        await self.ledger.insert_one({
            "user_id": user_id,
            "type": tx_type,
            "amount": amount,
            "reason": reason,
            "reference_id": reference_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })


# ── Singleton accessor ──
_instance: Optional[CreditsService] = None


def get_credits_service(db) -> CreditsService:
    """Get or create the singleton CreditsService instance."""
    global _instance
    if _instance is None:
        _instance = CreditsService(users=db.users, ledger=db.credit_ledger)
    return _instance
