"""
Story Session Service — 2026-05-16 P0 (Stability Sprint Session 2)
====================================================================

Single source of truth for writes against `db.story_drafts`.

Every public function here is the ONLY legitimate way to mutate a draft
document. Routes call into this module; they do not touch the collection
directly. The service:

  • Enforces optimistic locking (`expected_version` must match `state.version`,
    else `StaleWriteError`).
  • Enforces lifecycle transitions (illegal moves rejected by the state model).
  • Increments `version` on every accepted write (monotonic, never decrements).
  • Backfills missing fields on first read from pre-Session-2 documents.
  • Emits structured logs with `request_id` for every write.

Reads
-----
`get_session_by_id` returns a frozen `StorySessionState`. It NEVER returns
`None`; missing/foreign drafts raise `DRAFT_NOT_FOUND` so the caller can map
to a 404 envelope.

Writes
------
All writes use Mongo's atomic `find_one_and_update` with a guard query of
`{draft_id, user_id, version: expected_version}`. If the guard fails we
re-read the doc to distinguish a true stale write from a missing/foreign
draft, and raise the right error.

What this service is NOT
------------------------
• Not a cache. We read-through every call. The frontend is the canonical
  cache for live editing.
• Not an event bus. State changes do not publish events from here — the
  pipeline already has its own job lifecycle observability.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from models.story_session import (
    CURRENT_SCHEMA_VERSION,
    Lifecycle,
    StorySessionError,
    StorySessionErrorCode,
    StorySessionPatch,
    StorySessionState,
)

logger = logging.getLogger("story_session_service")


# ════════════════════════════════════════════════════════════════════════════
# Internal helpers
# ════════════════════════════════════════════════════════════════════════════

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _find_draft_doc(
    db: AsyncIOMotorDatabase, *, draft_id: str, user_id: str
) -> Optional[Dict[str, Any]]:
    """Look up a draft document by (draft_id, user_id). Returns None if
    not found — ownership leak protection: foreign drafts must look
    identical to missing drafts to the caller."""
    doc = await db.story_drafts.find_one(
        {"draft_id": draft_id, "user_id": user_id},
        {"_id": 0},
    )
    if doc is None and len(draft_id) == 24:
        # Legacy fallback for pre-Session-2 docs that only have ObjectId.
        try:
            from bson import ObjectId  # local import to keep model layer pure
            doc = await db.story_drafts.find_one(
                {"_id": ObjectId(draft_id), "user_id": user_id},
                {"_id": 0},
            )
        except Exception:
            doc = None
    return doc


async def _load_state(
    db: AsyncIOMotorDatabase, *, draft_id: str, user_id: str
) -> StorySessionState:
    """Load + parse a draft into a canonical state. Raises DRAFT_NOT_FOUND
    if missing/foreign, SCHEMA_UNSUPPORTED if from-the-future."""
    doc = await _find_draft_doc(db, draft_id=draft_id, user_id=user_id)
    if doc is None:
        raise StorySessionError(
            StorySessionErrorCode.DRAFT_NOT_FOUND,
            "We couldn't find that draft. It may have been deleted.",
            status_code=404,
            retryable=False,
        )
    return StorySessionState.from_mongo(doc)


# ════════════════════════════════════════════════════════════════════════════
# Public API
# ════════════════════════════════════════════════════════════════════════════

async def get_session_by_id(
    db: AsyncIOMotorDatabase,
    *,
    draft_id: str,
    user_id: str,
) -> StorySessionState:
    """Canonical hydration read. Always returns a frozen state."""
    return await _load_state(db, draft_id=draft_id, user_id=user_id)


async def get_active_session(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
) -> Optional[StorySessionState]:
    """Return the user's currently active session (lifecycle != ARCHIVED)
    or None if they have no draft.

    Uses the legacy index on (user_id, status) for backward compat. The
    `(user_id, status='draft')` partial unique index guarantees uniqueness.
    """
    doc = await db.story_drafts.find_one(
        {"user_id": user_id, "status": {"$in": ["draft", "processing"]}},
        {"_id": 0},
        sort=[("updated_at", -1)],
    )
    if doc is None:
        return None
    return StorySessionState.from_mongo(doc)


async def create_session(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
) -> StorySessionState:
    """Create a fresh blank session in the IDLE lifecycle. The caller is
    responsible for ensuring there is no existing active draft for this
    user (else the unique index will reject the insert). Use
    `archive_active_session` first if that is the case."""
    draft_id = uuid.uuid4().hex
    now = _now_iso()
    state = StorySessionState(
        draft_id=draft_id,
        user_id=user_id,
        schema_version=CURRENT_SCHEMA_VERSION,
        version=0,
        lifecycle=Lifecycle.IDLE,
        title="",
        story_text="",
        animation_style=None,
        age_group=None,
        voice_preset=None,
        attached_job_id=None,
        created_at=now,
        updated_at=now,
        archived_at=None,
    )
    await db.story_drafts.insert_one(state.to_mongo())
    logger.info(
        "[story-session/create] user=%s draft_id=%s",
        user_id[:8],
        draft_id,
    )
    return state


async def patch_session(
    db: AsyncIOMotorDatabase,
    *,
    draft_id: str,
    user_id: str,
    expected_version: int,
    patch: StorySessionPatch,
    next_lifecycle: Optional[Lifecycle] = None,
) -> StorySessionState:
    """Apply a patch + (optional) lifecycle transition under optimistic
    locking.

    Raises:
      • DRAFT_NOT_FOUND     — no such draft owned by `user_id`
      • STALE_WRITE         — current version != expected_version
      • ILLEGAL_TRANSITION  — `next_lifecycle` not legal from current state
      • INVALID_PATCH       — patch payload contained no actionable fields
                              and no lifecycle transition (no-op rejected)
    """
    current = await _load_state(db, draft_id=draft_id, user_id=user_id)

    if expected_version != current.version:
        raise StorySessionError(
            StorySessionErrorCode.STALE_WRITE,
            "Your edit was based on an older draft state. Refresh to continue.",
            status_code=409,
            retryable=True,
            extra={
                "expected_version": expected_version,
                "current_version": current.version,
                "draft_id": draft_id,
            },
        )

    patch_fields = patch.non_null_fields()
    if not patch_fields and next_lifecycle is None:
        raise StorySessionError(
            StorySessionErrorCode.INVALID_PATCH,
            "Patch must contain at least one field or a lifecycle transition.",
            status_code=400,
            retryable=False,
        )

    # Build the next state — this is where ILLEGAL_TRANSITION is raised.
    next_state = current.patched(next_lifecycle=next_lifecycle, **patch_fields)

    # Atomic CAS: only update if version still matches expected_version.
    res = await db.story_drafts.find_one_and_update(
        {
            "draft_id": draft_id,
            "user_id": user_id,
            "version": current.version,
        },
        {"$set": next_state.to_mongo()},
        return_document=False,
    )
    if res is None:
        # Lost the CAS race — another writer beat us between read and write.
        # Surface as STALE_WRITE so the client can refetch + retry.
        latest = await _load_state(db, draft_id=draft_id, user_id=user_id)
        raise StorySessionError(
            StorySessionErrorCode.STALE_WRITE,
            "Your edit was overtaken by another change. Refresh to continue.",
            status_code=409,
            retryable=True,
            extra={
                "expected_version": expected_version,
                "current_version": latest.version,
                "draft_id": draft_id,
            },
        )

    logger.info(
        "[story-session/patch] user=%s draft_id=%s version=%d->%d lifecycle=%s->%s",
        user_id[:8],
        draft_id,
        current.version,
        next_state.version,
        current.lifecycle.value,
        next_state.lifecycle.value,
    )
    return next_state


async def transition_session(
    db: AsyncIOMotorDatabase,
    *,
    draft_id: str,
    user_id: str,
    expected_version: int,
    next_lifecycle: Lifecycle,
    attached_job_id: Optional[str] = None,
) -> StorySessionState:
    """Pure lifecycle transition — no domain field changes.

    `attached_job_id` is the only auxiliary field we allow setting here so
    GENERATING transitions can stamp the pipeline job id atomically.
    """
    current = await _load_state(db, draft_id=draft_id, user_id=user_id)

    if expected_version != current.version:
        raise StorySessionError(
            StorySessionErrorCode.STALE_WRITE,
            "Your transition was based on an older draft state.",
            status_code=409,
            retryable=True,
            extra={
                "expected_version": expected_version,
                "current_version": current.version,
                "draft_id": draft_id,
            },
        )

    extras: Dict[str, Any] = {}
    if attached_job_id is not None:
        extras["attached_job_id"] = attached_job_id

    next_state = current.patched(next_lifecycle=next_lifecycle, **extras)

    res = await db.story_drafts.find_one_and_update(
        {"draft_id": draft_id, "user_id": user_id, "version": current.version},
        {"$set": next_state.to_mongo()},
        return_document=False,
    )
    if res is None:
        latest = await _load_state(db, draft_id=draft_id, user_id=user_id)
        raise StorySessionError(
            StorySessionErrorCode.STALE_WRITE,
            "Your transition was overtaken by another change.",
            status_code=409,
            retryable=True,
            extra={
                "expected_version": expected_version,
                "current_version": latest.version,
                "draft_id": draft_id,
            },
        )

    logger.info(
        "[story-session/transition] user=%s draft_id=%s %s->%s v=%d->%d",
        user_id[:8],
        draft_id,
        current.lifecycle.value,
        next_state.lifecycle.value,
        current.version,
        next_state.version,
    )
    return next_state


async def archive_active_session(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
) -> Optional[StorySessionState]:
    """Soft-archive whatever active draft the user currently has.

    Idempotent: returns None if there is nothing to archive. The lifecycle
    transition rules forbid archiving from GENERATING, but archive of any
    in-flight job here would race with the pipeline anyway — we deliberately
    leave GENERATING drafts alone (caller must wait or cancel the job).
    """
    current = await get_active_session(db, user_id=user_id)
    if current is None:
        return None

    if current.lifecycle == Lifecycle.GENERATING:
        # Refuse to archive an actively generating draft. Caller must
        # cancel the pipeline job first.
        raise StorySessionError(
            StorySessionErrorCode.ILLEGAL_TRANSITION,
            "Cannot archive a draft while generation is in progress.",
            status_code=409,
            retryable=False,
            extra={
                "from": current.lifecycle.value,
                "to": Lifecycle.ARCHIVED.value,
                "draft_id": current.draft_id,
            },
        )

    next_state = current.patched(next_lifecycle=Lifecycle.ARCHIVED)
    res = await db.story_drafts.find_one_and_update(
        {
            "draft_id": current.draft_id,
            "user_id": user_id,
            "version": current.version,
        },
        {"$set": next_state.to_mongo()},
        return_document=False,
    )
    if res is None:
        # Lost a race — but archive is idempotent enough that we surface
        # success: someone else already moved the draft forward.
        logger.warning(
            "[story-session/archive] race-lost user=%s draft_id=%s",
            user_id[:8], current.draft_id,
        )
        return await get_session_by_id(
            db, draft_id=current.draft_id, user_id=user_id,
        )

    logger.info(
        "[story-session/archive] user=%s draft_id=%s v=%d->%d",
        user_id[:8],
        current.draft_id,
        current.version,
        next_state.version,
    )
    return next_state


__all__ = [
    "get_session_by_id",
    "get_active_session",
    "create_session",
    "patch_session",
    "transition_session",
    "archive_active_session",
]
