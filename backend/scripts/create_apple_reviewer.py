"""One-off: create the Apple App Store reviewer account with 300 credits.

Usage:
    cd /app/backend && python -m scripts.create_apple_reviewer

Idempotent — if the user exists, updates the password and tops up credits to
the target floor. Writes a credit_ledger entry for full auditability.
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Make `backend/` importable when invoked as `python -m scripts.create_apple_reviewer`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

from shared import hash_password  # noqa: E402

EMAIL = "apple-reviewer@visionary-suite.com"
PASSWORD = "Reviewer@VS2026"
NAME = "Apple Reviewer"
TARGET_CREDITS = 300


async def main() -> int:
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    now_iso = datetime.now(timezone.utc).isoformat()
    existing = await db.users.find_one({"email": EMAIL})

    if existing:
        user_id = existing["id"]
        current_credits = int(existing.get("credits") or 0)
        topup = max(0, TARGET_CREDITS - current_credits)
        await db.users.update_one(
            {"id": user_id},
            {
                "$set": {
                    "password": hash_password(PASSWORD),
                    "name": NAME,
                    "emailVerified": True,
                    "credits_locked": False,
                    "has_delayed_credits": False,
                    "lastLogin": now_iso,
                    "credits": max(current_credits, TARGET_CREDITS),
                }
            },
        )
        if topup > 0:
            await db.credit_ledger.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "userId": user_id,
                    "amount": topup,
                    "type": "ADMIN_GRANT",
                    "description": f"Apple App Store reviewer top-up to {TARGET_CREDITS}",
                    "createdAt": now_iso,
                }
            )
        print(
            f"[UPDATE] {EMAIL} | id={user_id} | credits {current_credits} -> "
            f"{max(current_credits, TARGET_CREDITS)} (top-up={topup})"
        )
    else:
        user_id = str(uuid.uuid4())
        user = {
            "id": user_id,
            "email": EMAIL,
            "name": NAME,
            "password": hash_password(PASSWORD),
            "role": "user",
            "credits": TARGET_CREDITS,
            "emailVerified": True,
            "createdAt": now_iso,
            "lastLogin": now_iso,
            "has_delayed_credits": False,
            "credits_locked": False,
            "verification_disabled_signup": True,
            "plan_type": "free",
            "subscription_status": "inactive",
            "subscription_expires_at": None,
            "topup_credits": 0,
            "signup_bonus_granted": True,
            "is_reviewer_account": True,
        }
        await db.users.insert_one(user)
        await db.credit_ledger.insert_one(
            {
                "id": str(uuid.uuid4()),
                "userId": user_id,
                "amount": TARGET_CREDITS,
                "type": "ADMIN_GRANT",
                "description": "Apple App Store reviewer initial allocation",
                "createdAt": now_iso,
            }
        )
        print(f"[CREATE] {EMAIL} | id={user_id} | credits={TARGET_CREDITS}")

    # Verify
    final = await db.users.find_one({"email": EMAIL}, {"_id": 0, "password": 0})
    print("[FINAL]", {k: final[k] for k in ("id", "email", "name", "role", "credits", "emailVerified")})
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
