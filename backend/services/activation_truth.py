"""
Activation-truth service — P0 2026-05-22 Phase A.

The `first_project_created` activation event is the foundational
funnel metric we cannot recover later. It must be server-authoritative
and emitted exactly once per user — across refreshes, multi-tab
sessions, and pipeline retries.

Hard requirement (founder mandate 2026-05-22):

> first_project_created MUST be server authoritative.
> No frontend heuristics.

Implementation:
  1. Atomic compare-and-set on `users.first_project_completed_at`.
  2. Helper `mark_first_project_if_needed` returns True only when
     the row actually transitioned — callers can fire side effects.
  3. The activation endpoint exposes a `fire_now` flag that flips
     to True on the single request that crosses the boundary.

This module deliberately does NOT instrument each pipeline. The
activation endpoint is polled by the frontend after every successful
generation; the endpoint queries the unified set of "completed
generation" collections to determine if the user has actually created
anything yet. Adding a new generator → add it to GENERATION_COLLECTIONS
and the audit will keep working — the change becomes a one-line edit.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Tuple

from shared import db, logger

# ─── Generation collections checked for "first ever completion" ───
# Order matters: we short-circuit on the first hit, so put the
# highest-traffic collections first for query efficiency.
#
# IMPORTANT: this list is the canonical "what counts as a project"
# definition. Adding a new generator means adding a row here. The
# audit suite pins this list so a forgotten entry fails CI.
GENERATION_COLLECTIONS: Tuple[Tuple[str, str, dict], ...] = (
    # (collection_name, status_field, terminal_status_match)
    ("reaction_gif_jobs",   "status", {"$in": ["COMPLETED", "PARTIAL_READY"]}),
    ("photo_to_comic_jobs", "status", {"$in": ["COMPLETED", "PARTIAL_READY"]}),
    ("storybook_jobs",      "status", {"$in": ["COMPLETED", "PARTIAL_READY"]}),
    ("story_video_jobs",    "status", {"$in": ["COMPLETED", "READY", "PARTIAL_READY"]}),
    ("youstar_jobs",        "status", {"$in": ["COMPLETED", "READY"]}),
    ("ai_studio_jobs",      "status", {"$in": ["COMPLETED", "READY"]}),
    ("generations",         "status", {"$in": ["COMPLETED"]}),
)


async def _user_has_any_completed_generation(user_id: str) -> bool:
    """Cheap existence check across all known generation collections.

    Returns True the moment we find any terminal-success row. We do
    NOT count — only existence matters for the activation gate.
    """
    if not user_id:
        return False
    for coll_name, status_field, status_match in GENERATION_COLLECTIONS:
        coll = getattr(db, coll_name)
        doc = await coll.find_one(
            {"userId": user_id, status_field: status_match},
            projection={"_id": 1},
        )
        if doc is not None:
            return True
    return False


async def mark_first_project_if_needed(user_id: str) -> bool:
    """Atomic compare-and-set on `users.first_project_completed_at`.

    Returns True only when this call was the one that transitioned
    the user from "no project ever" to "has a first project". On
    every subsequent call returns False (idempotent).

    The atomicity guarantee comes from MongoDB's `$exists: False`
    predicate combined with `$currentDate`. If two parallel calls
    race (multi-tab; the user double-clicks), only one succeeds.
    """
    if not user_id:
        return False

    # Step 1: does the user actually have a completed generation?
    # No point setting the timestamp if they don't.
    has_one = await _user_has_any_completed_generation(user_id)
    if not has_one:
        return False

    now_iso = datetime.now(timezone.utc).isoformat()
    result = await db.users.update_one(
        {"id": user_id, "first_project_completed_at": {"$exists": False}},
        {"$set": {"first_project_completed_at": now_iso}},
    )
    transitioned = result.modified_count == 1
    if transitioned:
        logger.info(
            "[ACTIVATION] first_project_completed user=%s at=%s",
            user_id, now_iso,
        )
    return transitioned


async def get_activation_state(user_id: str) -> dict:
    """Return the activation state for a user, performing the
    server-authoritative first-project check on the fly.

    Returns:
      {
        "first_project_completed_at": ISO-8601 string or None,
        "fire_now": True only on the single request that transitioned
                    the user — frontend uses this to fire the Google
                    Ads conversion exactly once.
      }
    """
    if not user_id:
        return {"first_project_completed_at": None, "fire_now": False}

    user = await db.users.find_one({"id": user_id}, {"_id": 0, "first_project_completed_at": 1})
    already = (user or {}).get("first_project_completed_at")
    if already:
        return {"first_project_completed_at": already, "fire_now": False}

    fired = await mark_first_project_if_needed(user_id)
    if fired:
        # Re-read to surface the timestamp we just wrote.
        user = await db.users.find_one({"id": user_id}, {"_id": 0, "first_project_completed_at": 1})
        return {
            "first_project_completed_at": (user or {}).get("first_project_completed_at"),
            "fire_now": True,
        }
    return {"first_project_completed_at": None, "fire_now": False}
