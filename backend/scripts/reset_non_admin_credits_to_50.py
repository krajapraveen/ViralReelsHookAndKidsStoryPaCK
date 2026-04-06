"""
One-Time Migration: Reset all non-admin user credits to exactly 50.
Usage:
  python scripts/reset_non_admin_credits_to_50.py          # Execute migration
  python scripts/reset_non_admin_credits_to_50.py --dry-run # Preview only
"""
import asyncio
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MIGRATION_KEY = "reset_non_admin_credits_to_50_v1"

ADMIN_EMAILS = [
    "admin@creatorstudio.ai",
    "demo@example.com",
]

ADMIN_ROLES = ["admin", "ADMIN", "superadmin", "SUPERADMIN"]


def is_admin_user(user):
    email = (user.get("email") or "").lower().strip()
    role = user.get("role", "")
    return role in ADMIN_ROLES or email in [e.lower() for e in ADMIN_EMAILS]


async def run_migration(dry_run=False):
    from shared import db

    existing = await db.system_migrations.find_one({
        "migration_key": MIGRATION_KEY,
        "status": "completed"
    })
    if existing:
        print(f"Migration '{MIGRATION_KEY}' already completed on {existing.get('completed_at')}. Exiting safely.")
        return

    started_at = datetime.now(timezone.utc)
    stats = {"scanned": 0, "updated": 0, "skipped_admin": 0, "skipped_other": 0}

    if not dry_run:
        await db.system_migrations.insert_one({
            "migration_key": MIGRATION_KEY,
            "status": "running",
            "started_at": started_at.isoformat(),
            "meta": {}
        })

    mode = "DRY RUN" if dry_run else "LIVE"
    print(f"\n{'='*60}")
    print(f"  CREDIT RESET MIGRATION [{mode}]")
    print(f"  Target: Set all non-admin users to exactly 50 credits")
    print(f"{'='*60}\n")

    cursor = db.users.find({}, {"_id": 1, "id": 1, "email": 1, "role": 1, "credits": 1})
    async for user in cursor:
        stats["scanned"] += 1
        if is_admin_user(user):
            stats["skipped_admin"] += 1
            print(f"  SKIP (admin): {user.get('email', 'N/A')} — credits unchanged at {user.get('credits', 'N/A')}")
            continue

        current = user.get("credits", 0)
        if not dry_run:
            await db.users.update_one(
                {"_id": user["_id"]},
                {"$set": {
                    "credits": 50,
                    "updatedAt": datetime.now(timezone.utc).isoformat()
                }}
            )
        stats["updated"] += 1
        print(f"  {'WOULD UPDATE' if dry_run else 'UPDATED'}: {user.get('email', 'N/A')} — {current} -> 50")

    if not dry_run:
        await db.system_migrations.update_one(
            {"migration_key": MIGRATION_KEY},
            {"$set": {
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "meta": stats
            }}
        )

    print(f"\n{'='*60}")
    print(f"  RESULTS [{mode}]")
    print(f"  Scanned:       {stats['scanned']}")
    print(f"  Updated:       {stats['updated']}")
    print(f"  Skipped Admin: {stats['skipped_admin']}")
    print(f"  Skipped Other: {stats['skipped_other']}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    asyncio.run(run_migration(dry_run=dry))
