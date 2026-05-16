"""
StorySessionState — pure model + state-machine regression tests
================================================================
Session 2 (2026-05-17) — locks in:
  • Lifecycle transition table is the canonical state graph
  • Illegal transitions raise StorySessionError(ILLEGAL_TRANSITION)
  • Immutable updates (model is frozen, `patched` returns NEW instance)
  • Version monotonically increments on every accepted patch
  • Mongo round-trip (`to_mongo`/`from_mongo`) is loss-free
  • Schema-version guard rejects from-the-future docs
  • Legacy-status backfill is correct for pre-Session-2 documents

This file is pure unit-test — no DB, no HTTP. The service-level integration
tests live in test_session2_drafts_service_2026_05.py.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from models.story_session import (
    CURRENT_SCHEMA_VERSION,
    Lifecycle,
    StorySessionError,
    StorySessionErrorCode,
    StorySessionPatch,
    StorySessionState,
    is_legal_transition,
    legal_next_states,
    lifecycle_to_legacy_status,
)


def _fresh(lc: Lifecycle = Lifecycle.IDLE, version: int = 0) -> StorySessionState:
    now = datetime.now(timezone.utc).isoformat()
    return StorySessionState(
        draft_id="d-abc",
        user_id="u-1",
        schema_version=CURRENT_SCHEMA_VERSION,
        version=version,
        lifecycle=lc,
        title="t",
        story_text="s",
        created_at=now,
        updated_at=now,
    )


# ────────────────────────────────────────────────────────────────────
# Lifecycle table
# ────────────────────────────────────────────────────────────────────
def test_legal_transitions_match_spec():
    """Canonical list — any change requires a documented migration."""
    expected = {
        Lifecycle.IDLE: {Lifecycle.EDITING, Lifecycle.ARCHIVED},
        Lifecycle.EDITING: {Lifecycle.AUTOSAVING, Lifecycle.READY_TO_GENERATE, Lifecycle.ARCHIVED},
        Lifecycle.AUTOSAVING: {Lifecycle.EDITING, Lifecycle.READY_TO_GENERATE, Lifecycle.ARCHIVED},
        Lifecycle.READY_TO_GENERATE: {Lifecycle.EDITING, Lifecycle.GENERATING, Lifecycle.ARCHIVED},
        Lifecycle.GENERATING: {Lifecycle.READY, Lifecycle.FAILED},
        Lifecycle.READY: {Lifecycle.ARCHIVED},
        Lifecycle.FAILED: {Lifecycle.EDITING, Lifecycle.ARCHIVED},
        Lifecycle.ARCHIVED: set(),
    }
    for prev, allowed in expected.items():
        assert set(legal_next_states(prev)) == allowed, f"transition table drift at {prev.value}"


def test_idempotent_same_state_transition_is_legal():
    assert is_legal_transition(Lifecycle.EDITING, Lifecycle.EDITING)
    assert is_legal_transition(Lifecycle.GENERATING, Lifecycle.GENERATING)
    assert is_legal_transition(Lifecycle.ARCHIVED, Lifecycle.ARCHIVED)


def test_archived_is_terminal():
    """Archive must not allow ANY outbound edge (terminal state)."""
    assert legal_next_states(Lifecycle.ARCHIVED) == frozenset()
    for nxt in Lifecycle:
        if nxt == Lifecycle.ARCHIVED:
            continue
        assert not is_legal_transition(Lifecycle.ARCHIVED, nxt)


def test_generating_cannot_archive_directly():
    """In-flight pipeline owns the draft — direct archive forbidden."""
    assert not is_legal_transition(Lifecycle.GENERATING, Lifecycle.ARCHIVED)


def test_ready_cannot_revert_to_editing():
    """Once a draft is READY, re-editing requires a new draft."""
    assert not is_legal_transition(Lifecycle.READY, Lifecycle.EDITING)


def test_failed_can_recover_to_editing():
    assert is_legal_transition(Lifecycle.FAILED, Lifecycle.EDITING)


# ────────────────────────────────────────────────────────────────────
# Immutable updates & version bump
# ────────────────────────────────────────────────────────────────────
def test_state_is_frozen():
    s = _fresh()
    with pytest.raises(Exception):
        s.version = 99  # frozen — must reject


def test_patched_returns_new_instance_with_version_bumped():
    s0 = _fresh()
    s1 = s0.patched(title="new title")
    assert s1 is not s0
    assert s1.version == 1
    assert s1.title == "new title"
    # Original untouched
    assert s0.version == 0
    assert s0.title == "t"


def test_patched_increments_version_monotonically():
    s = _fresh()
    for i in range(1, 6):
        s = s.patched(title=f"v{i}")
    assert s.version == 5


def test_patched_with_legal_transition_updates_lifecycle():
    s0 = _fresh(Lifecycle.IDLE)
    s1 = s0.patched(next_lifecycle=Lifecycle.EDITING, title="x")
    assert s1.lifecycle == Lifecycle.EDITING
    assert s1.title == "x"
    assert s1.version == 1


def test_patched_with_illegal_transition_raises():
    s = _fresh(Lifecycle.IDLE)
    with pytest.raises(StorySessionError) as exc:
        s.patched(next_lifecycle=Lifecycle.GENERATING)
    assert exc.value.code == StorySessionErrorCode.ILLEGAL_TRANSITION
    assert exc.value.retryable is False
    assert exc.value.extra["from"] == "IDLE"
    assert exc.value.extra["to"] == "GENERATING"
    assert "ARCHIVED" in exc.value.extra["allowed_next"] or \
           "EDITING" in exc.value.extra["allowed_next"]


def test_archived_state_stamps_archived_at():
    s0 = _fresh(Lifecycle.EDITING)
    s1 = s0.patched(next_lifecycle=Lifecycle.ARCHIVED)
    assert s1.archived_at is not None
    assert s1.lifecycle == Lifecycle.ARCHIVED


def test_re_archiving_does_not_clobber_archived_at():
    s0 = _fresh(Lifecycle.EDITING).patched(next_lifecycle=Lifecycle.ARCHIVED)
    first_stamp = s0.archived_at
    s1 = s0.patched(next_lifecycle=Lifecycle.ARCHIVED)  # idempotent
    assert s1.archived_at == first_stamp


# ────────────────────────────────────────────────────────────────────
# Patch DTO
# ────────────────────────────────────────────────────────────────────
def test_patch_dto_drops_extra_fields():
    """`extra='forbid'` keeps least-privilege guarantee."""
    with pytest.raises(Exception):
        StorySessionPatch(version=999)  # not a patchable field


def test_patch_dto_non_null_helper():
    p = StorySessionPatch(title="x", story_text=None)
    assert p.non_null_fields() == {"title": "x"}


# ────────────────────────────────────────────────────────────────────
# Mongo serialization round-trip
# ────────────────────────────────────────────────────────────────────
def test_to_mongo_and_from_mongo_round_trip():
    s0 = _fresh(Lifecycle.EDITING, version=3).patched(title="hello", story_text="world")
    doc = s0.to_mongo()
    # Legacy status field must be present
    assert doc["status"] == "draft"
    assert doc["lifecycle"] == "EDITING"
    assert doc["version"] == s0.version
    s1 = StorySessionState.from_mongo(doc)
    assert s1.draft_id == s0.draft_id
    assert s1.version == s0.version
    assert s1.lifecycle == s0.lifecycle
    assert s1.title == s0.title
    assert s1.story_text == s0.story_text


def test_legacy_status_to_lifecycle_backfill_for_pre_session_2_docs():
    """A pre-Session-2 document has `status` but no `lifecycle`. Backfill."""
    doc = {
        "draft_id": "legacy-1",
        "user_id": "u-1",
        "status": "draft",
        "title": "Hello",
        "story_text": "Some content",
        # NO lifecycle, NO version — pre-Session-2 shape
    }
    s = StorySessionState.from_mongo(doc)
    # Has content → upgraded from IDLE to EDITING for accuracy
    assert s.lifecycle == Lifecycle.EDITING
    assert s.version == 0  # backfilled


def test_legacy_processing_maps_to_generating():
    doc = {"draft_id": "x", "user_id": "u", "status": "processing", "title": "t"}
    assert StorySessionState.from_mongo(doc).lifecycle == Lifecycle.GENERATING


def test_legacy_completed_maps_to_ready():
    doc = {"draft_id": "x", "user_id": "u", "status": "completed", "title": "t"}
    assert StorySessionState.from_mongo(doc).lifecycle == Lifecycle.READY


def test_legacy_archived_maps_to_archived():
    doc = {"draft_id": "x", "user_id": "u", "status": "archived"}
    assert StorySessionState.from_mongo(doc).lifecycle == Lifecycle.ARCHIVED


def test_blank_idle_legacy_doc_stays_idle():
    """Empty draft → still IDLE."""
    doc = {"draft_id": "x", "user_id": "u", "status": "draft", "title": "", "story_text": ""}
    assert StorySessionState.from_mongo(doc).lifecycle == Lifecycle.IDLE


def test_from_mongo_rejects_future_schema_version():
    doc = {
        "draft_id": "x", "user_id": "u",
        "status": "draft", "schema_version": 99,
    }
    with pytest.raises(StorySessionError) as exc:
        StorySessionState.from_mongo(doc)
    assert exc.value.code == StorySessionErrorCode.SCHEMA_UNSUPPORTED
    assert exc.value.extra["schema_version"] == 99
    assert exc.value.extra["supported_version"] == CURRENT_SCHEMA_VERSION


def test_lifecycle_to_legacy_status_covers_all_states():
    """Every lifecycle has a legacy status mapping — no KeyError surprises."""
    for lc in Lifecycle:
        assert isinstance(lifecycle_to_legacy_status(lc), str)


# ────────────────────────────────────────────────────────────────────
# Strict ownership
# ────────────────────────────────────────────────────────────────────
def test_state_carries_user_id_as_ownership_anchor():
    s = _fresh()
    assert s.user_id == "u-1"
    # Patched state preserves owner
    s1 = s.patched(title="z")
    assert s1.user_id == "u-1"
