"""
Data Repair Script: Fix zombie COMPLETED jobs with no real output.

Scans all COMPLETED pipeline_jobs and:
1. If no real output asset exists → marks ORPHANED
2. Filters out placehold.co URLs from any field
3. Removes from gallery/explore surfaces
4. Reports stats

Run: cd /app/backend && python scripts/repair_zombie_jobs.py
"""
import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from shared import db

FAKE_URL_PATTERNS = ["placehold.co", "placeholder", "example.com"]


def is_fake_url(url):
    if not url or not isinstance(url, str):
        return True
    if url.strip() == "":
        return True
    for pattern in FAKE_URL_PATTERNS:
        if pattern in url:
            return True
    return False


def is_real_url(url):
    """A URL is real if it's non-empty, not fake, and looks like a valid path or URL"""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    if not url:
        return False
    for pattern in FAKE_URL_PATTERNS:
        if pattern in url:
            return False
    # Must start with http, /, or data:
    if url.startswith(("http://", "https://", "/", "data:image/")):
        return True
    return False


async def repair():
    print("=" * 60)
    print("DATA REPAIR: Scanning completed pipeline_jobs...")
    print("=" * 60)

    # Count totals
    total_completed = await db.pipeline_jobs.count_documents({"status": "COMPLETED"})
    print(f"\nTotal COMPLETED jobs: {total_completed}")

    # Find zombie jobs: COMPLETED but no real output
    cursor = db.pipeline_jobs.find(
        {"status": "COMPLETED"},
        {"job_id": 1, "title": 1, "output_url": 1, "thumbnail_url": 1,
         "scene_images": 1, "scene_progress": 1, "render_path": 1, "_id": 0}
    )

    zombies = []
    has_output = []
    has_scenes_only = []

    async for job in cursor:
        jid = job.get("job_id", "?")
        out_url = job.get("output_url")
        thumb_url = job.get("thumbnail_url")
        scene_imgs = job.get("scene_images") or {}
        scene_progress = job.get("scene_progress") or []
        render_path = job.get("render_path")

        # Check if this job has ANY real output
        has_real_output = is_real_url(out_url)
        has_real_thumb = is_real_url(thumb_url)
        has_real_render = render_path and os.path.exists(str(render_path))

        # Check scene_images for real URLs
        real_scene_urls = []
        if isinstance(scene_imgs, dict):
            for sn, urls in scene_imgs.items():
                if isinstance(urls, list):
                    real_scene_urls.extend([u for u in urls if is_real_url(u)])
                elif isinstance(urls, str) and is_real_url(urls):
                    real_scene_urls.append(urls)

        # Check scene_progress for real image URLs
        for sp in scene_progress:
            img_url = sp.get("image_url") or sp.get("url")
            if is_real_url(img_url):
                real_scene_urls.append(img_url)

        if has_real_output or has_real_render:
            has_output.append(jid)
        elif real_scene_urls:
            has_scenes_only.append(jid)
        else:
            zombies.append(jid)

    print(f"\nJobs with real video output: {len(has_output)}")
    print(f"Jobs with scene images only (no video): {len(has_scenes_only)}")
    print(f"ZOMBIE jobs (no real output at all): {len(zombies)}")

    if not zombies:
        print("\nNo zombie jobs found. Database is clean.")
        return

    # Mark zombies as ORPHANED
    print(f"\nMarking {len(zombies)} zombie jobs as ORPHANED...")
    result = await db.pipeline_jobs.update_many(
        {"job_id": {"$in": zombies}, "status": "COMPLETED"},
        {"$set": {
            "status": "ORPHANED",
            "orphaned_at": datetime.now(timezone.utc).isoformat(),
            "orphan_reason": "COMPLETED with no real output assets"
        }}
    )
    print(f"Updated: {result.modified_count} jobs marked ORPHANED")

    # Also clean placehold.co from comic jobs
    print("\nCleaning placehold.co from comic/avatar/gif jobs...")
    for collection_name in ["comic_avatar_jobs", "comix_jobs", "gif_jobs", "storybook_jobs"]:
        try:
            coll = db[collection_name]
            fake_count = await coll.count_documents({
                "$or": [
                    {"resultUrl": {"$regex": "placehold\\.co"}},
                    {"primary_url": {"$regex": "placehold\\.co"}},
                    {"thumbnail_url": {"$regex": "placehold\\.co"}},
                ]
            })
            if fake_count > 0:
                result = await coll.update_many(
                    {"$or": [
                        {"resultUrl": {"$regex": "placehold\\.co"}},
                        {"primary_url": {"$regex": "placehold\\.co"}},
                        {"thumbnail_url": {"$regex": "placehold\\.co"}},
                    ]},
                    {"$set": {
                        "status": "FAILED",
                        "error": "Output contained fake placeholder URL",
                        "repaired_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
                print(f"  {collection_name}: {result.modified_count} fake records marked FAILED")
            else:
                print(f"  {collection_name}: clean")
        except Exception as e:
            print(f"  {collection_name}: error - {e}")

    # Clean photo_to_comic chains that have placehold.co preview_url
    print("\nCleaning story chains with fake preview URLs...")
    chains_cleaned = await db.story_chains.update_many(
        {"preview_url": {"$regex": "placehold\\.co"}},
        {"$set": {"preview_url": None}}
    )
    print(f"  Story chains cleaned: {chains_cleaned.modified_count}")

    print("\n" + "=" * 60)
    print("REPAIR COMPLETE")
    print(f"  Zombies marked ORPHANED: {len(zombies)}")
    print(f"  Jobs with scenes only: {len(has_scenes_only)} (kept as COMPLETED)")
    print(f"  Jobs with real output: {len(has_output)} (untouched)")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(repair())
