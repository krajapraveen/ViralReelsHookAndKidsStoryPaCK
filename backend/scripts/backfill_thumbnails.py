"""
Backfill thumbnail_small_url for ALL stories in the database.

Resolution chain (per story):
  1. thumbnail_url (if already set)
  2. scene_images → first entry → r2_key or url
  3. stage_results → image_gen outputs → r2_key or url
  4. Mark as UNFIXABLE if nothing found

This runs idempotently — safe to re-run at any time.
"""
import asyncio
import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

logger = logging.getLogger("backfill_thumbnails")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "creatorstudio_production")
R2_PUBLIC = os.environ.get("CLOUDFLARE_R2_PUBLIC_URL", "").rstrip("/")


def resolve_thumbnail_from_doc(doc: dict) -> str | None:
    """Resolve the best available thumbnail URL from a raw DB document."""
    # 1. Existing thumbnail_url
    thumb = doc.get("thumbnail_url")
    if thumb and isinstance(thumb, str) and thumb.strip():
        return _to_cdn(thumb)

    # 2. scene_images dict (pipeline_jobs format)
    si = doc.get("scene_images")
    if si and isinstance(si, dict):
        first_key = sorted(si.keys(), key=lambda k: int(k) if k.isdigit() else 999)
        for fk in first_key:
            entry = si[fk]
            if isinstance(entry, dict):
                r2k = entry.get("r2_key")
                if r2k:
                    return f"{R2_PUBLIC}/{r2k}" if R2_PUBLIC else f"/api/media/r2/{r2k}"
                url = entry.get("url")
                if url:
                    return _to_cdn(url)

    # 3. stage_results image_gen outputs (story_engine_jobs format)
    for stage in doc.get("stage_results", []):
        if stage.get("stage") == "image_gen":
            for out in stage.get("outputs", []):
                if isinstance(out, dict):
                    r2k = out.get("r2_key") or out.get("image_r2_key")
                    if r2k:
                        return f"{R2_PUBLIC}/{r2k}" if R2_PUBLIC else f"/api/media/r2/{r2k}"
                    url = out.get("url") or out.get("image_url")
                    if url:
                        return _to_cdn(url)

    return None


def _to_cdn(url: str) -> str | None:
    """Normalize any R2 URL to CDN format."""
    if not url:
        return None
    base = url.split("?")[0]
    if ".r2.dev/" in base:
        key = base.split(".r2.dev/", 1)[1]
        return f"{R2_PUBLIC}/{key}" if R2_PUBLIC else f"/api/media/r2/{key}"
    if ".r2.cloudflarestorage.com/" in base:
        parts = base.split(".r2.cloudflarestorage.com/", 1)
        if len(parts) > 1:
            bk = parts[1].split("/", 1)
            if len(bk) > 1:
                return f"{R2_PUBLIC}/{bk[1]}" if R2_PUBLIC else f"/api/media/r2/{bk[1]}"
    if url.startswith("/api/media/"):
        key = url.replace("/api/media/r2/", "")
        return f"{R2_PUBLIC}/{key}" if R2_PUBLIC else url
    return url


async def backfill_collection(db, collection_name: str, status_filter: dict):
    """Backfill thumbnail_small_url for all documents in a collection."""
    coll = db[collection_name]
    # Find docs missing thumbnail_small_url
    query = {
        **status_filter,
        "$or": [
            {"thumbnail_small_url": {"$exists": False}},
            {"thumbnail_small_url": None},
            {"thumbnail_small_url": ""},
        ],
    }
    cursor = coll.find(query, {"_id": 1, "job_id": 1, "title": 1, "thumbnail_url": 1, "scene_images": 1, "stage_results": 1})
    docs = await cursor.to_list(length=500)

    fixed = 0
    unfixable = 0
    for doc in docs:
        resolved = resolve_thumbnail_from_doc(doc)
        if resolved:
            await coll.update_one(
                {"_id": doc["_id"]},
                {"$set": {"thumbnail_small_url": resolved}},
            )
            fixed += 1
            logger.info(f"  Fixed: {doc.get('title', doc.get('job_id', 'unknown'))} → {resolved[:80]}...")
        else:
            unfixable += 1
            logger.warning(f"  UNFIXABLE: {doc.get('title', doc.get('job_id', 'unknown'))} — no image source found")

    return fixed, unfixable, len(docs)


async def run_backfill():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    logger.info("=== Starting thumbnail_small_url backfill ===")

    # story_engine_jobs
    fixed_se, unfixable_se, total_se = await backfill_collection(
        db, "story_engine_jobs", {"state": "READY"}
    )
    logger.info(f"story_engine_jobs: {total_se} missing → {fixed_se} fixed, {unfixable_se} unfixable")

    # pipeline_jobs
    fixed_pj, unfixable_pj, total_pj = await backfill_collection(
        db, "pipeline_jobs", {"status": "COMPLETED"}
    )
    logger.info(f"pipeline_jobs: {total_pj} missing → {fixed_pj} fixed, {unfixable_pj} unfixable")

    # Also backfill thumbnail_url for pipeline_jobs that have scene_images but no thumbnail_url
    query_no_thumb = {
        "status": "COMPLETED",
        "$or": [
            {"thumbnail_url": {"$exists": False}},
            {"thumbnail_url": None},
            {"thumbnail_url": ""},
        ],
    }
    docs = await db.pipeline_jobs.find(
        query_no_thumb,
        {"_id": 1, "job_id": 1, "title": 1, "scene_images": 1, "stage_results": 1},
    ).to_list(length=500)
    thumb_fixed = 0
    for doc in docs:
        resolved = resolve_thumbnail_from_doc(doc)
        if resolved:
            await db.pipeline_jobs.update_one(
                {"_id": doc["_id"]},
                {"$set": {"thumbnail_url": resolved}},
            )
            thumb_fixed += 1

    logger.info(f"pipeline_jobs thumbnail_url backfill: {thumb_fixed} fixed from {len(docs)} missing")
    logger.info("=== Backfill complete ===")

    total_fixed = fixed_se + fixed_pj + thumb_fixed
    total_unfixable = unfixable_se + unfixable_pj
    return {
        "total_fixed": total_fixed,
        "total_unfixable": total_unfixable,
        "details": {
            "story_engine_jobs": {"missing": total_se, "fixed": fixed_se, "unfixable": unfixable_se},
            "pipeline_jobs_small": {"missing": total_pj, "fixed": fixed_pj, "unfixable": unfixable_pj},
            "pipeline_jobs_thumb": {"missing": len(docs), "fixed": thumb_fixed},
        },
    }


if __name__ == "__main__":
    result = asyncio.run(run_backfill())
    print(f"\nResult: {result}")
