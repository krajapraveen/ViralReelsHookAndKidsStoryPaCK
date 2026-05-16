"""
Canonical Story Session State — 2026-05-16 P0 (Stability Sprint Session 2)
============================================================================

This module defines the SINGLE SOURCE OF TRUTH for a user's story editing
session. It replaces the ad-hoc collection of `useState`/`localStorage`/
`async-callback` ownership that previously caused race conditions, stale
overwrites and phantom UI.

Design pillars (founder-mandated, in order):

  1.  ONE canonical state model            (`StorySessionState`)
  2.  Explicit lifecycle transitions       (`Lifecycle` enum + table)
  3.  Illegal transition guards            (`is_legal_transition`)
  4.  Draft version incrementing           (`version` field, monotonic)
  5.  Stale write rejection                (`StaleWriteError`)
  6.  Deterministic hydration              (one read endpoint, no merging)
  7.  Single source of truth               (every write through the service)
  8.  Immutable updates                    (model is frozen / copy_with patches)
  9.  Strict ownership by draft_id/job_id  (composite key on every op)
 10.  Regression coverage first-class      (every transition + error tested)

Scope discipline
----------------
This file is pure data + state machine + error types. ZERO IO. ZERO routes.
The route layer (`routes/drafts.py`) and service layer
(`services/story_session_service.py`) compose this primitive — they never
mutate fields directly.

Backward compatibility
----------------------
Older draft documents (pre-Session-2) are missing the `version` and
`lifecycle` fields. The service backfills them on first read so existing
sessions don't have to be migrated by a batch job.
"""
from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any, Dict, FrozenSet, Optional, Tuple
from pydantic import BaseModel, Field, ConfigDict


# ════════════════════════════════════════════════════════════════════════════
# Lifecycle — explicit, finite state machine
# ════════════════════════════════════════════════════════════════════════════

class Lifecycle(str, enum.Enum):
    """All legal lifecycle states for a story session.

    The string values are stable wire-format identifiers. NEVER rename them
    without a migration — they are persisted on every draft document and
    cited in error envelopes consumed by the frontend.
    """
    IDLE = "IDLE"                              # fresh blank draft, no edits yet
    EDITING = "EDITING"                        # user is actively typing
    AUTOSAVING = "AUTOSAVING"                  # autosave roundtrip in flight
    READY_TO_GENERATE = "READY_TO_GENERATE"    # has content, passed validation
    GENERATING = "GENERATING"                  # pipeline job attached & running
    READY = "READY"                            # generation completed successfully
    FAILED = "FAILED"                          # generation failed (recoverable)
    ARCHIVED = "ARCHIVED"                      # soft-deleted (Start Fresh)


# All edges in the state graph. Frozen at module load — any change requires
# a documented migration. The shape is `from_state -> {allowed next states}`.
#
# Reading the graph:
#   • IDLE is the only entry state for a fresh draft.
#   • ARCHIVED is the only terminal state — once archived, the draft is
#     immutable from the user's perspective (still admin-recoverable).
#   • READY can flow back to EDITING ONLY by way of a fresh draft created
#     elsewhere — same draft_id cannot be "un-readied" without an explicit
#     architectural decision. Today we forbid READY -> EDITING to keep the
#     contract clean; remix-into-same-draft would be a future migration.
_LEGAL_TRANSITIONS: Dict[Lifecycle, FrozenSet[Lifecycle]] = {
    Lifecycle.IDLE: frozenset({
        Lifecycle.EDITING,
        Lifecycle.ARCHIVED,
    }),
    Lifecycle.EDITING: frozenset({
        Lifecycle.AUTOSAVING,
        Lifecycle.READY_TO_GENERATE,
        Lifecycle.ARCHIVED,
    }),
    Lifecycle.AUTOSAVING: frozenset({
        Lifecycle.EDITING,             # user kept typing while save was in flight
        Lifecycle.READY_TO_GENERATE,   # autosave finished + content is valid
        Lifecycle.ARCHIVED,
    }),
    Lifecycle.READY_TO_GENERATE: frozenset({
        Lifecycle.EDITING,             # user edited more before clicking Generate
        Lifecycle.GENERATING,
        Lifecycle.ARCHIVED,
    }),
    Lifecycle.GENERATING: frozenset({
        Lifecycle.READY,
        Lifecycle.FAILED,
        # NOTE: ARCHIVED from GENERATING is intentionally forbidden — the
        # in-flight pipeline job owns the document until it terminates. The
        # frontend's "Start Fresh" while generating must first wait for the
        # job to finish (or be cancelled via the pipeline's own cancel API,
        # which transitions to FAILED).
    }),
    Lifecycle.READY: frozenset({
        Lifecycle.ARCHIVED,
    }),
    Lifecycle.FAILED: frozenset({
        Lifecycle.EDITING,             # user can edit + retry
        Lifecycle.ARCHIVED,
    }),
    Lifecycle.ARCHIVED: frozenset(),   # terminal
}


def is_legal_transition(prev: Lifecycle, nxt: Lifecycle) -> bool:
    """Return True iff `prev -> nxt` is allowed by the canonical state graph."""
    if prev == nxt:
        # Re-asserting the same state is always legal (idempotent retries).
        return True
    return nxt in _LEGAL_TRANSITIONS.get(prev, frozenset())


def legal_next_states(prev: Lifecycle) -> FrozenSet[Lifecycle]:
    """Return the frozen set of legal next states from `prev`."""
    return _LEGAL_TRANSITIONS.get(prev, frozenset())


# Legacy `status` field is still persisted alongside `lifecycle` so older
# endpoints (`/current`, `/recent`) keep working without a schema migration.
# This mapping is the SINGLE PLACE that knows how the two fields relate.
_LIFECYCLE_TO_LEGACY_STATUS: Dict[Lifecycle, str] = {
    Lifecycle.IDLE: "draft",
    Lifecycle.EDITING: "draft",
    Lifecycle.AUTOSAVING: "draft",
    Lifecycle.READY_TO_GENERATE: "draft",
    Lifecycle.GENERATING: "processing",
    Lifecycle.READY: "completed",
    Lifecycle.FAILED: "draft",
    Lifecycle.ARCHIVED: "archived",
}


def lifecycle_to_legacy_status(lc: Lifecycle) -> str:
    return _LIFECYCLE_TO_LEGACY_STATUS[lc]


# ════════════════════════════════════════════════════════════════════════════
# Error codes — what the service raises, what the route returns
# ════════════════════════════════════════════════════════════════════════════

class StorySessionErrorCode(str, enum.Enum):
    DRAFT_NOT_FOUND = "DRAFT_NOT_FOUND"
    NOT_OWNED = "NOT_OWNED"
    STALE_WRITE = "STALE_WRITE"                       # version mismatch
    ILLEGAL_TRANSITION = "ILLEGAL_TRANSITION"
    SCHEMA_UNSUPPORTED = "DRAFT_SCHEMA_UNSUPPORTED"
    INVALID_PATCH = "INVALID_PATCH"


class StorySessionError(Exception):
    """Domain-specific error. The route layer maps these to HTTP envelopes
    with `code`, `message`, `request_id`, `retryable`. Never construct an
    HTTPException directly inside the service — keep transport concerns out
    of the domain core."""

    def __init__(
        self,
        code: StorySessionErrorCode,
        message: str,
        *,
        status_code: int = 409,
        retryable: bool = False,
        extra: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retryable = retryable
        self.extra = extra or {}


# ════════════════════════════════════════════════════════════════════════════
# StorySessionState — the canonical data model
# ════════════════════════════════════════════════════════════════════════════

CURRENT_SCHEMA_VERSION: int = 1


class StorySessionState(BaseModel):
    """The canonical session document, in memory.

    Immutability
    ------------
    The model is configured `frozen=True`. To produce a derived state you
    MUST go through `patched(**fields)` — it returns a new instance with
    the version pre-incremented. This is what the service does on every
    accepted write.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    # ── identity (immutable across the lifetime of the draft) ──
    draft_id: str = Field(..., description="canonical draft uuid hex; never reused")
    user_id: str = Field(..., description="owning user id (stringified)")
    schema_version: int = Field(default=CURRENT_SCHEMA_VERSION)

    # ── version for optimistic locking ──
    version: int = Field(default=0, ge=0)

    # ── lifecycle ──
    lifecycle: Lifecycle = Field(default=Lifecycle.IDLE)

    # ── domain fields ──
    title: str = Field(default="")
    story_text: str = Field(default="")
    animation_style: Optional[str] = None
    age_group: Optional[str] = None
    voice_preset: Optional[str] = None

    # ── attached pipeline job (only set during GENERATING/READY/FAILED) ──
    attached_job_id: Optional[str] = None

    # ── timestamps ──
    created_at: str
    updated_at: str
    archived_at: Optional[str] = None

    # ─────────────────────────── derived ────────────────────────────
    @property
    def legacy_status(self) -> str:
        return lifecycle_to_legacy_status(self.lifecycle)

    @property
    def is_terminal(self) -> bool:
        return self.lifecycle == Lifecycle.ARCHIVED

    # ─────────────────────────── builders ───────────────────────────
    def patched(
        self,
        *,
        next_lifecycle: Optional[Lifecycle] = None,
        **fields: Any,
    ) -> "StorySessionState":
        """Return a NEW state with `fields` applied and `version` bumped by 1.

        If `next_lifecycle` is provided, it is validated against the legal
        transition table and stored. Re-asserting the same lifecycle is a
        no-op (idempotent retry support).

        Raises `StorySessionError(ILLEGAL_TRANSITION)` for forbidden moves.
        """
        if next_lifecycle is not None and not is_legal_transition(self.lifecycle, next_lifecycle):
            raise StorySessionError(
                StorySessionErrorCode.ILLEGAL_TRANSITION,
                f"Cannot transition from {self.lifecycle.value} to {next_lifecycle.value}",
                status_code=409,
                retryable=False,
                extra={
                    "from": self.lifecycle.value,
                    "to": next_lifecycle.value,
                    "allowed_next": sorted(s.value for s in legal_next_states(self.lifecycle)),
                },
            )

        # Compute new lifecycle + archived_at side effect cleanly.
        new_lifecycle = next_lifecycle if next_lifecycle is not None else self.lifecycle
        now_iso = datetime.now(timezone.utc).isoformat()
        archived_at = self.archived_at
        if new_lifecycle == Lifecycle.ARCHIVED and archived_at is None:
            archived_at = now_iso

        # Build the new field dict. We deliberately use model_dump + override
        # so unknown future fields (added by `extra='ignore'` rejection)
        # don't leak through.
        data = self.model_dump()
        data.update(fields)
        data["lifecycle"] = new_lifecycle
        data["version"] = self.version + 1
        data["updated_at"] = now_iso
        data["archived_at"] = archived_at
        return StorySessionState(**data)

    # ─────────────────────────── serialization ───────────────────────────
    def to_mongo(self) -> Dict[str, Any]:
        """Return a plain dict suitable for `$set` in MongoDB.

        Always emits both the new `lifecycle` field AND the legacy `status`
        field so older endpoints (and admin tools) keep working. Never emits
        `_id` — Mongo ObjectId remains untouched.
        """
        return {
            "draft_id": self.draft_id,
            "user_id": self.user_id,
            "schema_version": self.schema_version,
            "version": self.version,
            "lifecycle": self.lifecycle.value,
            "status": lifecycle_to_legacy_status(self.lifecycle),  # legacy
            "title": self.title,
            "story_text": self.story_text,
            "animation_style": self.animation_style,
            "age_group": self.age_group,
            "voice_preset": self.voice_preset,
            "attached_job_id": self.attached_job_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "archived_at": self.archived_at,
        }

    @classmethod
    def from_mongo(cls, doc: Dict[str, Any]) -> "StorySessionState":
        """Build a canonical state from a Mongo document. Backfills missing
        fields with safe defaults so pre-Session-2 docs hydrate without
        requiring a batch migration.

        Raises `StorySessionError(SCHEMA_UNSUPPORTED)` if `schema_version`
        is from the future.
        """
        schema = int(doc.get("schema_version", CURRENT_SCHEMA_VERSION))
        if schema > CURRENT_SCHEMA_VERSION:
            raise StorySessionError(
                StorySessionErrorCode.SCHEMA_UNSUPPORTED,
                "We found an issue restoring this draft. Recover safe content or start fresh.",
                status_code=409,
                retryable=False,
                extra={
                    "schema_version": schema,
                    "supported_version": CURRENT_SCHEMA_VERSION,
                },
            )

        # Lifecycle backfill from legacy `status` if missing.
        lc_raw = doc.get("lifecycle")
        if lc_raw is None:
            legacy = doc.get("status", "draft")
            lc = _LEGACY_STATUS_TO_LIFECYCLE.get(legacy, Lifecycle.IDLE)
            # If the doc has content, upgrade IDLE → EDITING for accuracy.
            if lc == Lifecycle.IDLE and (
                doc.get("title") or doc.get("story_text")
            ):
                lc = Lifecycle.EDITING
        else:
            try:
                lc = Lifecycle(lc_raw)
            except ValueError:
                lc = Lifecycle.EDITING  # safe fallback for corrupt rows

        now_iso = datetime.now(timezone.utc).isoformat()
        return cls(
            draft_id=str(doc.get("draft_id") or doc.get("_id") or ""),
            user_id=str(doc.get("user_id", "")),
            schema_version=schema,
            version=int(doc.get("version", 0)),
            lifecycle=lc,
            title=doc.get("title", "") or "",
            story_text=doc.get("story_text", "") or "",
            animation_style=doc.get("animation_style"),
            age_group=doc.get("age_group"),
            voice_preset=doc.get("voice_preset"),
            attached_job_id=doc.get("attached_job_id"),
            created_at=doc.get("created_at") or now_iso,
            updated_at=doc.get("updated_at") or now_iso,
            archived_at=doc.get("archived_at"),
        )


_LEGACY_STATUS_TO_LIFECYCLE: Dict[str, Lifecycle] = {
    "draft": Lifecycle.IDLE,
    "processing": Lifecycle.GENERATING,
    "completed": Lifecycle.READY,
    "archived": Lifecycle.ARCHIVED,
}


# ════════════════════════════════════════════════════════════════════════════
# Patch DTO — what the service accepts on a write
# ════════════════════════════════════════════════════════════════════════════

class StorySessionPatch(BaseModel):
    """Domain fields a client may patch on EDITING/AUTOSAVING transitions.

    Only the whitelisted fields below are accepted. Anything else is dropped
    silently. The service uses this to enforce least-privilege writes.
    """
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = None
    story_text: Optional[str] = None
    animation_style: Optional[str] = None
    age_group: Optional[str] = None
    voice_preset: Optional[str] = None

    def non_null_fields(self) -> Dict[str, Any]:
        return {k: v for k, v in self.model_dump().items() if v is not None}


__all__ = [
    "Lifecycle",
    "is_legal_transition",
    "legal_next_states",
    "lifecycle_to_legacy_status",
    "StorySessionState",
    "StorySessionPatch",
    "StorySessionError",
    "StorySessionErrorCode",
    "CURRENT_SCHEMA_VERSION",
]
