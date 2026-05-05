"""One-shot migration: zero out all free-credit balances on existing users
under the new subscription-only policy.

Rules:
  * Sets credits = 0 on all users EXCEPT:
      - admins / role in UNLIMITED_ROLES
      - users with paid_credit_lifetime > 0 (i.e. they purchased)
        (we still preserve their balance up to their purchased amount)
      - users with active subscription_status == 'active'
  * Marks signup_bonus_granted = false
  * Records an audit row in credit_ledger per affected user
  * Never touches subscriptions.* / payments.* / orders.* collections

Run preview-only first:
  cd /app/backend && python scripts/migrate_zero_free_credits.py --dry-run
  cd /app/backend && python scripts/migrate_zero_free_credits.py --apply

Production roll-out is gated by founder approval after preview verification.
"""
import argparse
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

UNLIMITED_ROLES = {"admin", "ADMIN", "dev", "qa", "test"}


async def main(dry_run: bool):
    from motor.motor_asyncio import AsyncIOMotorClient
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    total = await db.users.count_documents({})
    print(f"Total users in DB: {total}")
    print(f"Mode: {'DRY-RUN' if dry_run else 'APPLY'}")

    # Compute lifetime purchased credits per user from ledger
    pipeline = [
        {"$match": {"$or": [
            {"type": {"$in": ["TOPUP", "PURCHASE", "SUBSCRIPTION_GRANT"]}},
            {"type": "ADD", "amount": {"$gt": 0}},
        ]}},
        {"$group": {"_id": "$userId", "purchased": {"$sum": "$amount"}}},
    ]
    purchased_by_user = {}
    async for row in db.credit_ledger.aggregate(pipeline):
        purchased_by_user[row["_id"]] = int(row.get("purchased") or 0)

    affected = 0
    skipped = 0
    rows_to_log = []

    async for u in db.users.find({}, {"id": 1, "email": 1, "role": 1, "credits": 1,
                                       "is_unlimited": 1, "subscription_status": 1}):
        uid = u.get("id")
        if not uid:
            continue
        role = u.get("role", "user")
        is_unlimited = bool(u.get("is_unlimited")) or role in UNLIMITED_ROLES
        sub_active = (u.get("subscription_status") == "active")
        old_credits = int(u.get("credits", 0))
        purchased = purchased_by_user.get(uid, 0)

        if is_unlimited:
            skipped += 1
            continue
        if sub_active:
            skipped += 1
            continue

        # Cap balance to whatever they actually paid for. Free grants → 0.
        new_credits = min(old_credits, purchased) if purchased > 0 else 0
        if new_credits == old_credits:
            skipped += 1
            continue

        delta = old_credits - new_credits
        rows_to_log.append({
            "id": str(uuid.uuid4()),
            "userId": uid,
            "amount": -delta,
            "type": "FREE_CREDITS_REVOKED_2026_05",
            "description": (f"Free-credit policy removed. old={old_credits} "
                            f"purchased_lifetime={purchased} new={new_credits}"),
            "createdAt": datetime.now(timezone.utc).isoformat(),
        })
        if not dry_run:
            await db.users.update_one(
                {"id": uid},
                {"$set": {"credits": new_credits,
                          "signup_bonus_granted": False,
                          "free_credits_revoked_at": datetime.now(timezone.utc).isoformat()}},
            )
        affected += 1

    if rows_to_log and not dry_run:
        await db.credit_ledger.insert_many(rows_to_log)

    print(f"\n=== Summary ===")
    print(f"Affected: {affected}")
    print(f"Skipped (admin/unlimited/subscribed/already-zero/purchased-only): {skipped}")
    print(f"Ledger rows {'WOULD BE' if dry_run else ''} written: {len(rows_to_log)}")
    if dry_run:
        print("\n(no writes performed — re-run with --apply to commit)")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true", help="Commit changes (default is dry-run)")
    p.add_argument("--dry-run", action="store_true", help="Preview only (default)")
    args = p.parse_args()
    dry = not args.apply  # default to dry-run unless --apply
    asyncio.run(main(dry))
