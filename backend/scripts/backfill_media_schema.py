"""
Backfill script: Migrate existing story_engine_jobs and pipeline_jobs
to the new nested `media` schema.

Reads existing flat thumbnail_url / thumbnail_small_url fields and
writes them into the structured media.thumbnail_small and media.poster_large
nested documents.

Usage: python -m scripts.backfill_media_schema
"""
import asyncio
import os
import sys
from dotenv import load_dotenv
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "visionary_suite")


async def backfill():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    # ── 1. Backfill story_engine_jobs ──
    se_cursor = db.story_engine_jobs.find(
        {
            "media": {"$exists": False},
            "$or": [
                {"thumbnail_url": {"$exists": True, "$ne": None}},
                {"thumbnail_small_url": {"$exists": True, "$ne": None}},
            ],
        },
        {"_id": 0, "job_id": 1, "thumbnail_url": 1, "thumbnail_small_url": 1},
    )

    se_count = 0
    async for job in se_cursor:
        thumb_small = job.get("thumbnail_small_url")
        poster = job.get("thumbnail_url")

        update = {}
        if thumb_small:
            update["media.thumbnail_small.url"] = thumb_small
            update["media.thumbnail_small.type"] = "image/jpeg"
        if poster:
            update["media.poster_large.url"] = poster
            update["media.poster_large.type"] = "image/jpeg"

        # If only one exists, use it for both
        if thumb_small and not poster:
            update["media.poster_large.url"] = thumb_small
            update["media.poster_large.type"] = "image/jpeg"
        elif poster and not thumb_small:
            update["media.thumbnail_small.url"] = poster
            update["media.thumbnail_small.type"] = "image/jpeg"

        if update:
            await db.story_engine_jobs.update_one(
                {"job_id": job["job_id"]},
                {"$set": update},
            )
            se_count += 1

    print(f"[BACKFILL] story_engine_jobs migrated: {se_count}")

    # ── 2. Backfill pipeline_jobs ──
    pj_cursor = db.pipeline_jobs.find(
        {
            "media": {"$exists": False},
            "status": "COMPLETED",
            "$or": [
                {"thumbnail_url": {"$exists": True, "$ne": None}},
                {"scene_images": {"$exists": True, "$ne": {}}},
            ],
        },
        {"_id": 0, "job_id": 1, "thumbnail_url": 1, "thumbnail_small_url": 1, "scene_images": 1},
    )

    pj_count = 0
    async for job in pj_cursor:
        thumb = job.get("thumbnail_url") or job.get("thumbnail_small_url")

        # Fallback to first scene_image
        if not thumb:
            si = job.get("scene_images") or {}
            if si:
                fk = sorted(si.keys(), key=lambda k: int(k) if k.isdigit() else 999)[0] if si else None
                if fk and isinstance(si[fk], dict):
                    thumb = si[fk].get("url")

        if thumb:
            await db.pipeline_jobs.update_one(
                {"job_id": job["job_id"]},
                {"$set": {
                    "media.thumbnail_small.url": thumb,
                    "media.thumbnail_small.type": "image/jpeg",
                    "media.poster_large.url": thumb,
                    "media.poster_large.type": "image/jpeg",
                }},
            )
            pj_count += 1

    print(f"[BACKFILL] pipeline_jobs migrated: {pj_count}")
    print(f"[BACKFILL] Total migrated: {se_count + pj_count}")

    client.close()


if __name__ == "__main__":
    asyncio.run(backfill())
