"""Backup users.credits + credit_ledger BEFORE running migrate_zero_free_credits.

Snapshots written to /tmp/billing_backup_<ISO>.json. Both files are JSON arrays
that the restore script can replay.

Run BEFORE migration:
    cd /app/backend && python scripts/backup_users_credits.py

Run AFTER migration if rollback needed:
    cd /app/backend && python scripts/restore_credits_from_backup.py /tmp/billing_backup_<TS>.json
"""
import asyncio
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()


async def main():
    from motor.motor_asyncio import AsyncIOMotorClient
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = f"/tmp/billing_backup_{ts}.json"

    users = []
    async for u in db.users.find({}, {"_id": 0, "id": 1, "email": 1, "credits": 1,
                                       "topup_credits": 1, "is_unlimited": 1,
                                       "role": 1, "subscription_status": 1,
                                       "signup_bonus_granted": 1,
                                       "free_credits_revoked_at": 1}):
        users.append(u)

    ledger = []
    async for r in db.credit_ledger.find({}, {"_id": 0}):
        ledger.append(r)

    payload = {
        "snapshot_taken_at": datetime.now(timezone.utc).isoformat(),
        "db_name": os.environ["DB_NAME"],
        "user_count": len(users),
        "ledger_count": len(ledger),
        "users": users,
        "ledger": ledger,
    }
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2, default=str)

    print(f"✔ Backup written: {out_path}")
    print(f"  users={len(users)}  ledger_rows={len(ledger)}")
    print(f"\nKeep this file. Restore command:")
    print(f"  python scripts/restore_credits_from_backup.py {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
