"""Restore users.credits from a /tmp/billing_backup_*.json snapshot.

Only restores the per-user credit balance fields. Does NOT touch
credit_ledger (that's append-only audit history).

Run:
    cd /app/backend && python scripts/restore_credits_from_backup.py /tmp/billing_backup_<TS>.json [--apply]

Default is dry-run. Pass --apply to actually write.
"""
import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()


async def main(path: str, apply: bool):
    from motor.motor_asyncio import AsyncIOMotorClient
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

    with open(path) as f:
        snap = json.load(f)
    print(f"Snapshot taken: {snap['snapshot_taken_at']}")
    print(f"DB at snapshot: {snap['db_name']}")
    print(f"Restoring {len(snap['users'])} users")
    print(f"Mode: {'APPLY' if apply else 'DRY-RUN'}\n")

    diffs = 0
    restored = 0
    for u in snap["users"]:
        uid = u.get("id")
        if not uid:
            continue
        cur = await db.users.find_one({"id": uid}, {"credits": 1})
        if not cur:
            continue
        old = u.get("credits", 0)
        now = cur.get("credits", 0)
        if old != now:
            diffs += 1
            print(f"  {u.get('email','?')[:40]}: {now} → {old} (delta {old - now:+d})")
            if apply:
                await db.users.update_one(
                    {"id": uid},
                    {"$set": {"credits": old,
                              "topup_credits": u.get("topup_credits", 0),
                              "signup_bonus_granted": u.get("signup_bonus_granted", False)},
                     "$unset": {"free_credits_revoked_at": ""}},
                )
                restored += 1

    print(f"\nDifferences detected: {diffs}")
    print(f"Restored: {restored if apply else 0}")
    if not apply:
        print("(re-run with --apply to commit)")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("backup_path")
    p.add_argument("--apply", action="store_true")
    a = p.parse_args()
    asyncio.run(main(a.backup_path, a.apply))
