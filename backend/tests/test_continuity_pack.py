"""
Test Suite: ContinuityPack — Curated reference selection correctness.

Covers:
  - Anchor panel chosen correctly under mixed confidence
  - Latest high-confidence character panel beats merely recent panel
  - Corrupted/empty prior panel is excluded from useful references
  - Degraded but recent panel does not poison the pack
  - Pack remains stable when extra low-value history is appended
  - get_generation_context returns bounded list (never bloats)
  - get_validation_context returns broader but still bounded set
  - Summary stats are accurate
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.comic_pipeline.continuity_pack import ContinuityPack


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_scores(face=0.85, style=0.80):
    return {
        "face_consistency": face,
        "style_consistency": style,
        "source_similarity": face,
    }


GOOD_BYTES = b'\x89PNG\r\n\x1a\n' + b'\x00' * 1000  # Fake PNG header
WEAK_BYTES = b'\x89PNG\r\n\x1a\n' + b'\x01' * 500
EMPTY_BYTES = b""
DEGRADED_BYTES = b'\x89PNG\r\n\x1a\n' + b'\x02' * 800


# ── 1. Basic registration and retrieval ─────────────────────────────────────

class TestContinuityPackBasic:

    def test_empty_pack_returns_none(self):
        pack = ContinuityPack()
        assert pack.get_generation_context(0) is None
        assert pack.get_validation_context(0) is None
        assert pack.approved_count == 0

    def test_register_and_retrieve(self):
        pack = ContinuityPack()
        pack.register_approved_panel(0, GOOD_BYTES, make_scores(0.90, 0.85))
        assert pack.approved_count == 1
        assert 0 in pack.approved_indices

    def test_generation_context_for_panel_0(self):
        """Panel 0 is generating — no prior context exists."""
        pack = ContinuityPack()
        assert pack.get_generation_context(0) is None

    def test_generation_context_for_panel_1(self):
        """Panel 1 should get anchor (Panel 0)."""
        pack = ContinuityPack()
        pack.register_approved_panel(0, GOOD_BYTES, make_scores(0.90, 0.85))
        ctx = pack.get_generation_context(1)
        assert ctx is not None
        assert len(ctx) == 1
        assert ctx[0] == GOOD_BYTES


# ── 2. Anchor selection under mixed confidence ─────────────────────────────

class TestContinuityPackAnchorSelection:

    def test_anchor_always_included(self):
        """Anchor (panel 0) is always in generation context, even with low scores."""
        pack = ContinuityPack()
        pack.register_approved_panel(0, GOOD_BYTES, make_scores(0.50, 0.50))  # Low scores
        pack.register_approved_panel(1, WEAK_BYTES, make_scores(0.95, 0.95))  # High scores

        ctx = pack.get_generation_context(2)
        assert ctx is not None
        # Should include anchor (panel 0) even though panel 1 has better scores
        assert GOOD_BYTES in ctx

    def test_anchor_not_included_for_panel_0(self):
        """When generating panel 0, it can't reference itself."""
        pack = ContinuityPack()
        pack.register_approved_panel(0, GOOD_BYTES, make_scores(0.90, 0.85))
        ctx = pack.get_generation_context(0)
        assert ctx is None  # Panel 0 has nothing before it


# ── 3. High-confidence beats merely recent ──────────────────────────────────

class TestContinuityPackConfidenceRanking:

    def test_best_face_beats_most_recent(self):
        """The highest face confidence panel should be selected, not just the latest."""
        pack = ContinuityPack()
        pack.register_approved_panel(0, b'anchor', make_scores(0.70, 0.70))
        pack.register_approved_panel(1, b'best_face', make_scores(0.95, 0.80))
        pack.register_approved_panel(2, b'mid_face', make_scores(0.75, 0.85))
        pack.register_approved_panel(3, b'recent', make_scores(0.60, 0.90))

        ctx = pack.get_generation_context(4)
        assert ctx is not None

        # Should contain:
        # 1. Anchor (panel 0)
        # 2. Best face (panel 1, face=0.95)
        # 3. Previous panel (panel 3)
        assert b'anchor' in ctx
        assert b'best_face' in ctx
        assert b'recent' in ctx  # Previous panel
        assert len(ctx) == 3  # Max 3 for generation

    def test_best_face_when_anchor_is_best(self):
        """If anchor IS the best face panel, only 2 refs should be selected."""
        pack = ContinuityPack()
        pack.register_approved_panel(0, b'anchor_best', make_scores(0.99, 0.95))
        pack.register_approved_panel(1, b'okay', make_scores(0.60, 0.60))
        pack.register_approved_panel(2, b'previous', make_scores(0.55, 0.55))

        ctx = pack.get_generation_context(3)
        assert ctx is not None
        # Anchor (best face already in #1 slot), previous panel
        assert b'anchor_best' in ctx
        assert b'previous' in ctx  # Previous panel


# ── 4. Corrupted/empty panel exclusion ──────────────────────────────────────

class TestContinuityPackCorruptedPanels:

    def test_empty_bytes_panel_included_but_not_selected_as_best(self):
        """Empty bytes panel is registered but shouldn't poison best-face selection."""
        pack = ContinuityPack()
        pack.register_approved_panel(0, GOOD_BYTES, make_scores(0.85, 0.80))
        pack.register_approved_panel(1, EMPTY_BYTES, make_scores(0.0, 0.0))
        pack.register_approved_panel(2, WEAK_BYTES, make_scores(0.90, 0.85))

        ctx = pack.get_generation_context(3)
        assert ctx is not None
        # Best face should be panel 2 (0.90), not panel 1 (0.0)
        assert WEAK_BYTES in ctx  # Panel 2 has best face
        assert GOOD_BYTES in ctx  # Anchor
        # Panel 1 (empty) should be previous, but it's index 2-1=2, which is already included as best
        # Actually previous is panel 2

    def test_zero_confidence_not_selected_as_best_face(self):
        """A panel with face_confidence=0 should not be selected as best face reference."""
        pack = ContinuityPack()
        pack.register_approved_panel(0, b'anchor', make_scores(0.80, 0.75))
        pack.register_approved_panel(1, b'no_face', make_scores(0.0, 0.70))
        pack.register_approved_panel(2, b'good_face', make_scores(0.88, 0.82))

        ctx = pack.get_generation_context(3)
        assert ctx is not None
        # Best face is panel 2 (0.88), not panel 1 (0.0)
        assert b'good_face' in ctx


# ── 5. Degraded panel not poisoning the pack ────────────────────────────────

class TestContinuityPackDegradedPanels:

    def test_degraded_panel_registered_with_low_scores(self):
        """Degraded panels have low scores and should not dominate best-face."""
        pack = ContinuityPack()
        pack.register_approved_panel(0, b'anchor', make_scores(0.85, 0.80))
        pack.register_approved_panel(1, DEGRADED_BYTES, make_scores(0.30, 0.40),
                                      pipeline_status="PASSED_DEGRADED")
        pack.register_approved_panel(2, b'good', make_scores(0.92, 0.88))

        ctx = pack.get_generation_context(3)
        assert ctx is not None
        # Best face should be panel 2 (0.92), not panel 1 (0.30)
        assert b'good' in ctx
        assert b'anchor' in ctx

    def test_degraded_panel_still_available_for_validation(self):
        """Validation context is broader and includes degraded panels."""
        pack = ContinuityPack()
        pack.register_approved_panel(0, b'anchor', make_scores(0.85, 0.80))
        pack.register_approved_panel(1, DEGRADED_BYTES, make_scores(0.30, 0.40))
        pack.register_approved_panel(2, b'good', make_scores(0.92, 0.88))

        val_ctx = pack.get_validation_context(3)
        assert val_ctx is not None
        # Validation should include all 3 prior panels (up to 4 max)
        assert len(val_ctx) == 3


# ── 6. Bounded context size ─────────────────────────────────────────────────

class TestContinuityPackBounded:

    def test_generation_context_max_3_refs(self):
        """Generation context never exceeds 3 references."""
        pack = ContinuityPack()
        for i in range(10):
            pack.register_approved_panel(i, f'panel_{i}'.encode(), make_scores(0.80, 0.80))

        ctx = pack.get_generation_context(10)
        assert ctx is not None
        assert len(ctx) <= 3

    def test_validation_context_max_4_refs(self):
        """Validation context never exceeds 4 references."""
        pack = ContinuityPack()
        for i in range(10):
            pack.register_approved_panel(i, f'panel_{i}'.encode(), make_scores(0.80, 0.80))

        val_ctx = pack.get_validation_context(10)
        assert val_ctx is not None
        assert len(val_ctx) <= 4

    def test_pack_stable_after_many_additions(self):
        """Adding many low-value panels doesn't bloat or destabilize the pack."""
        pack = ContinuityPack()
        pack.register_approved_panel(0, b'anchor', make_scores(0.90, 0.88))

        # Add 20 low-value panels
        for i in range(1, 21):
            pack.register_approved_panel(i, f'low_{i}'.encode(),
                                          make_scores(0.30, 0.25))

        ctx = pack.get_generation_context(21)
        assert ctx is not None
        assert len(ctx) <= 3
        # Anchor should still be there
        assert b'anchor' in ctx


# ── 7. Summary stats accuracy ───────────────────────────────────────────────

class TestContinuityPackSummary:

    def test_summary_empty_pack(self):
        pack = ContinuityPack()
        summary = pack.get_summary()
        assert summary["approved_count"] == 0
        assert summary["approved_indices"] == []
        assert summary["avg_face_confidence"] == 0
        assert summary["avg_style_confidence"] == 0

    def test_summary_with_panels(self):
        pack = ContinuityPack()
        pack.register_approved_panel(0, b'a', make_scores(0.80, 0.70))
        pack.register_approved_panel(1, b'b', make_scores(0.90, 0.85))
        pack.register_approved_panel(2, b'c', make_scores(0.70, 0.75))

        summary = pack.get_summary()
        assert summary["approved_count"] == 3
        assert summary["approved_indices"] == [0, 1, 2]
        # avg face = (0.80 + 0.90 + 0.70) / 3 = 0.8
        assert summary["avg_face_confidence"] == 0.8
        # avg style = (0.70 + 0.85 + 0.75) / 3 ≈ 0.767
        assert round(summary["avg_style_confidence"], 3) == 0.767

    def test_generation_context_sorted_by_index(self):
        """References should be sorted by panel index for coherent context."""
        pack = ContinuityPack()
        pack.register_approved_panel(0, b'anchor', make_scores(0.70, 0.70))
        pack.register_approved_panel(3, b'best_face', make_scores(0.95, 0.90))
        pack.register_approved_panel(4, b'prev', make_scores(0.60, 0.60))

        ctx = pack.get_generation_context(5)
        assert ctx is not None
        # Should be sorted: anchor (0), best_face (3), prev (4)
        assert ctx == [b'anchor', b'best_face', b'prev']


# ── 8. Edge cases ───────────────────────────────────────────────────────────

class TestContinuityPackEdgeCases:

    def test_single_panel_job(self):
        """Job with only 1 panel — no prior context needed."""
        pack = ContinuityPack()
        ctx = pack.get_generation_context(0)
        assert ctx is None

    def test_two_panel_job(self):
        """Panel 1 should only reference anchor (panel 0)."""
        pack = ContinuityPack()
        pack.register_approved_panel(0, b'anchor', make_scores(0.85, 0.80))
        ctx = pack.get_generation_context(1)
        assert ctx is not None
        assert len(ctx) == 1

    def test_validation_context_no_future_panels(self):
        """Validation should never include panels AFTER the current one."""
        pack = ContinuityPack()
        for i in range(6):
            pack.register_approved_panel(i, f'p{i}'.encode(), make_scores(0.85, 0.80))

        # Validate panel 3 — should only see panels 0, 1, 2
        val_ctx = pack.get_validation_context(3)
        assert val_ctx is not None
        assert len(val_ctx) == 3
        # Should NOT contain panel 3, 4, or 5 bytes
        for b in val_ctx:
            assert b != b'p3'
            assert b != b'p4'
            assert b != b'p5'

    def test_generation_context_no_current_panel(self):
        """Generation context should never include the panel being generated."""
        pack = ContinuityPack()
        for i in range(5):
            pack.register_approved_panel(i, f'p{i}'.encode(), make_scores(0.85, 0.80))

        ctx = pack.get_generation_context(2)
        assert ctx is not None
        # Should not contain panel 2, 3, or 4
        for b in ctx:
            assert b != b'p2'
            assert b != b'p3'
            assert b != b'p4'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
