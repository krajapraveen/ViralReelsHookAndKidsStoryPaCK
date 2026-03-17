"""
Story Chain — Relational story object model for Photo to Comic.

A Story Chain is a tree of related comic jobs:
  - Original: the first comic created from a photo
  - Continuation: extends the story from a parent
  - Remix: same photo, different style/genre from a parent

Data model fields added to each photo_to_comic_jobs doc:
  story_chain_id  — shared across all jobs in the chain
  root_job_id     — the original job that started the chain
  parent_job_id   — direct parent (null for originals)
  branch_type     — "original" | "continuation" | "remix"
  sequence_number — order within the chain (0 for original)

Endpoints:
  GET  /api/photo-to-comic/chain/{chain_id}  — full chain tree
  GET  /api/photo-to-comic/my-chains         — user's chains (grouped)
  POST /api/photo-to-comic/chain/init        — retroactively assign chain IDs
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Optional
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user


async def ensure_chain_fields(job_id: str, user_id: str, parent_job_id: str = None, branch_type: str = "original"):
    """
    Assign story chain fields to a job. Called during job creation.
    - If original: creates a new chain (chain_id = job_id)
    - If continuation/remix: inherits chain from parent
    """
    if parent_job_id:
        parent = await db.photo_to_comic_jobs.find_one(
            {"id": parent_job_id, "userId": user_id},
            {"_id": 0, "story_chain_id": 1, "root_job_id": 1, "sequence_number": 1}
        )
        if parent:
            chain_id = parent.get("story_chain_id", parent_job_id)
            root_id = parent.get("root_job_id", parent_job_id)
            # Count existing in chain for sequence
            count = await db.photo_to_comic_jobs.count_documents({"story_chain_id": chain_id})
            seq = count  # 0-indexed: original=0, first continuation=1, etc.
        else:
            chain_id = job_id
            root_id = job_id
            seq = 0
    else:
        chain_id = job_id
        root_id = job_id
        seq = 0

    await db.photo_to_comic_jobs.update_one(
        {"id": job_id},
        {"$set": {
            "story_chain_id": chain_id,
            "root_job_id": root_id,
            "parent_job_id": parent_job_id,
            "branch_type": branch_type,
            "sequence_number": seq,
        }}
    )
    return chain_id


async def get_chain_tree(chain_id: str, user_id: str):
    """Build the full chain tree from DB."""
    jobs = await db.photo_to_comic_jobs.find(
        {"story_chain_id": chain_id, "userId": user_id},
        {"_id": 0, "id": 1, "parent_job_id": 1, "branch_type": 1,
         "sequence_number": 1, "status": 1, "mode": 1, "style": 1,
         "genre": 1, "panelCount": 1, "storyPrompt": 1,
         "resultUrl": 1, "resultUrls": 1, "panels": 1,
         "createdAt": 1, "cost": 1, "title": 1}
    ).sort("sequence_number", 1).to_list(50)

    if not jobs:
        return None

    root = jobs[0]
    # Build node map
    node_map = {}
    for j in jobs:
        node_map[j["id"]] = {
            **j,
            "children": [],
        }

    # Link children to parents
    for j in jobs:
        pid = j.get("parent_job_id")
        if pid and pid in node_map:
            node_map[pid]["children"].append(node_map[j["id"]])

    # Chain metadata
    total = len(jobs)
    completed = sum(1 for j in jobs if j.get("status") in ("COMPLETED", "PARTIAL_COMPLETE"))
    styles_used = list({j.get("style", "unknown") for j in jobs})
    continuations = sum(1 for j in jobs if j.get("branch_type") == "continuation")
    remixes = sum(1 for j in jobs if j.get("branch_type") == "remix")

    return {
        "chain_id": chain_id,
        "root_job_id": root["id"],
        "total_episodes": total,
        "completed": completed,
        "continuations": continuations,
        "remixes": remixes,
        "styles_used": styles_used,
        "created_at": root.get("createdAt"),
        "tree": node_map.get(root["id"]),
        "flat": jobs,
    }


async def backfill_chain_ids(user_id: str):
    """
    Retroactively assign chain IDs to jobs that don't have them.
    Originals get chain_id = their own id.
    Continuations/remixes inherit from parent.
    """
    jobs_without_chain = await db.photo_to_comic_jobs.find(
        {"userId": user_id, "story_chain_id": {"$exists": False}},
        {"_id": 0, "id": 1, "parentJobId": 1, "isContinuation": 1}
    ).to_list(200)

    updated = 0
    for job in jobs_without_chain:
        parent_id = job.get("parentJobId")
        if job.get("isContinuation") and parent_id:
            branch_type = "continuation"
        else:
            parent_id = None
            branch_type = "original"

        await ensure_chain_fields(job["id"], user_id, parent_id, branch_type)
        updated += 1

    return updated
