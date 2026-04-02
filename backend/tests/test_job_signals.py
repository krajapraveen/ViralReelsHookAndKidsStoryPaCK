"""
Test Suite: JobSignals — Structured signal extraction from panel results.

Covers:
  - All-pass, all-fail, mixed, degraded scenarios
  - Borderline thresholds at exact cutoffs
  - Contradictory panel outcomes (high face, low narrative)
  - Many repaired panels that technically passed
  - Latency budget exceeded with okay quality signals
  - Cost burn ratio breach with acceptable outputs
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.comic_pipeline.job_orchestrator import JobSignals
from enums.pipeline_enums import PanelStatus, PASS_THRESHOLDS


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_panel(
    panel_number,
    status="READY",
    pipeline_status=PanelStatus.PASSED.value,
    face_consistency=0.85,
    style_consistency=0.80,
    scene="test scene",
    timing_ms=5000,
    attempts=1,
):
    return {
        "panelNumber": panel_number,
        "status": status,
        "pipeline_status": pipeline_status,
        "validation_scores": {
            "face_consistency": face_consistency,
            "style_consistency": style_consistency,
        },
        "scene": scene,
        "timing_ms": timing_ms,
        "attempts": attempts,
    }


# ── 1. Basic scenarios ──────────────────────────────────────────────────────

class TestJobSignalsBasic:
    """Core extraction correctness."""

    def test_all_panels_passed(self):
        panels = [make_panel(i + 1) for i in range(4)]
        s = JobSignals(panels, 4).compute()
        assert s["ready_count"] == 4
        assert s["failed_count"] == 0
        assert s["pass_rate"] == 1.0
        assert s["fail_rate"] == 0.0
        assert s["primary_pass_count"] == 4
        assert s["repair_concentration"] == 0.0
        assert s["fallback_contamination"] == 0.0
        assert s["sequential"]
        assert s["character_preserved"]
        assert s["story_coverage"] == 1.0

    def test_all_panels_failed(self):
        panels = [
            make_panel(i + 1, status="FAILED", pipeline_status=PanelStatus.FAILED.value,
                       face_consistency=0, style_consistency=0)
            for i in range(4)
        ]
        s = JobSignals(panels, 4).compute()
        assert s["ready_count"] == 0
        assert s["failed_count"] == 4
        assert s["pass_rate"] == 0.0
        assert s["fail_rate"] == 1.0
        assert s["failed_indices"] == [0, 1, 2, 3]

    def test_mixed_pass_fail(self):
        panels = [
            make_panel(1),
            make_panel(2, status="FAILED", pipeline_status=PanelStatus.FAILED.value,
                       face_consistency=0, style_consistency=0),
            make_panel(3),
            make_panel(4),
        ]
        s = JobSignals(panels, 4).compute()
        assert s["ready_count"] == 3
        assert s["failed_count"] == 1
        assert s["pass_rate"] == 0.75
        assert s["fail_rate"] == 0.25
        assert s["failed_indices"] == [1]

    def test_degraded_panels_counted(self):
        panels = [
            make_panel(1),
            make_panel(2, pipeline_status=PanelStatus.PASSED_DEGRADED.value),
            make_panel(3, pipeline_status=PanelStatus.PASSED_REPAIRED.value),
            make_panel(4),
        ]
        s = JobSignals(panels, 4).compute()
        assert s["degraded_count"] == 1
        assert s["repaired_count"] == 1
        assert s["primary_pass_count"] == 2
        assert s["repair_concentration"] == 0.5  # 2/4 needed rescue
        assert s["fallback_contamination"] == 0.25  # 1/4 degraded


# ── 2. Borderline threshold tests ───────────────────────────────────────────

class TestJobSignalsBorderline:
    """Signals at exact threshold boundaries."""

    def test_face_consistency_at_exact_threshold(self):
        """Face at PASS_THRESHOLDS['face_consistency'] should still be preserved."""
        threshold = PASS_THRESHOLDS["face_consistency"]
        panels = [make_panel(i + 1, face_consistency=threshold) for i in range(4)]
        s = JobSignals(panels, 4).compute()
        assert s["avg_face_consistency"] == threshold
        assert s["character_preserved"]  # >= threshold

    def test_face_consistency_below_threshold(self):
        threshold = PASS_THRESHOLDS["face_consistency"]
        panels = [make_panel(i + 1, face_consistency=threshold - 0.01) for i in range(4)]
        s = JobSignals(panels, 4).compute()
        assert not s["character_preserved"]

    def test_face_consistency_zero_scores(self):
        """When no face scores exist, character_preserved defaults to True."""
        panels = [make_panel(i + 1, face_consistency=0) for i in range(4)]
        s = JobSignals(panels, 4).compute()
        # Zero scores are not counted in face_scores list
        assert s["character_preserved"]  # No face data = assume preserved

    def test_story_coverage_partial(self):
        """3 out of 4 panels have scenes."""
        panels = [
            make_panel(1, scene="scene1"),
            make_panel(2, scene="scene2"),
            make_panel(3, scene="scene3"),
            make_panel(4, scene=""),
        ]
        s = JobSignals(panels, 4).compute()
        assert s["story_coverage"] == 0.75

    def test_story_coverage_full(self):
        panels = [make_panel(i + 1, scene=f"scene{i}") for i in range(4)]
        s = JobSignals(panels, 4).compute()
        assert s["story_coverage"] == 1.0


# ── 3. Contradictory signal combinations ────────────────────────────────────

class TestJobSignalsContradictory:
    """Test conflicting signal combinations that expose policy bugs."""

    def test_high_face_low_style(self):
        """Face is great, style drifted — signals must reflect both accurately."""
        panels = [make_panel(i + 1, face_consistency=0.95, style_consistency=0.40) for i in range(4)]
        s = JobSignals(panels, 4).compute()
        assert s["avg_face_consistency"] == 0.95
        assert s["avg_style_consistency"] == 0.40
        assert s["character_preserved"]  # Face is fine

    def test_high_style_no_face(self):
        """Style consistent, but no face detected at all."""
        panels = [make_panel(i + 1, face_consistency=0, style_consistency=0.90) for i in range(4)]
        s = JobSignals(panels, 4).compute()
        assert s["avg_style_consistency"] == 0.90
        assert s["avg_face_consistency"] == 0  # No face data
        assert s["character_preserved"]  # No face data means no penalty

    def test_sequential_but_degraded(self):
        """Panels are sequential but all needed repair."""
        panels = [
            make_panel(i + 1, pipeline_status=PanelStatus.PASSED_REPAIRED.value, attempts=2)
            for i in range(4)
        ]
        s = JobSignals(panels, 4).compute()
        assert s["sequential"]
        assert s["repair_concentration"] == 1.0  # All repaired
        assert s["cost_burn_ratio"] == 2.0  # 8 attempts / 4 expected

    def test_non_sequential_panels(self):
        """Panel numbers don't follow sequence."""
        panels = [
            make_panel(1),
            make_panel(3),  # Skipped panel 2
            make_panel(2),
            make_panel(4),
        ]
        s = JobSignals(panels, 4).compute()
        assert not s["sequential"]


# ── 4. Cost and latency budget tests ────────────────────────────────────────

class TestJobSignalsCostLatency:
    """Latency budget and cost burn ratio correctness."""

    def test_cost_burn_ratio_ideal(self):
        """1 attempt per panel = ratio of 1.0."""
        panels = [make_panel(i + 1, attempts=1) for i in range(4)]
        s = JobSignals(panels, 4).compute()
        assert s["cost_burn_ratio"] == 1.0
        assert s["total_attempts"] == 4

    def test_cost_burn_ratio_high(self):
        """3 attempts per panel = ratio of 3.0."""
        panels = [make_panel(i + 1, attempts=3) for i in range(4)]
        s = JobSignals(panels, 4).compute()
        assert s["cost_burn_ratio"] == 3.0
        assert s["total_attempts"] == 12

    def test_cost_burn_ratio_mixed(self):
        """Some panels took more attempts than others."""
        panels = [
            make_panel(1, attempts=1),
            make_panel(2, attempts=3),
            make_panel(3, attempts=1),
            make_panel(4, attempts=2),
        ]
        s = JobSignals(panels, 4).compute()
        assert s["total_attempts"] == 7
        assert s["cost_burn_ratio"] == 1.75  # 7/4

    def test_latency_total_and_average(self):
        panels = [
            make_panel(1, timing_ms=10000),
            make_panel(2, timing_ms=20000),
            make_panel(3, timing_ms=15000),
            make_panel(4, timing_ms=5000),
        ]
        s = JobSignals(panels, 4).compute()
        assert s["total_latency_ms"] == 50000
        assert s["avg_latency_ms"] == 12500

    def test_latency_with_missing_timings(self):
        """Some panels have no timing data."""
        panels = [
            make_panel(1, timing_ms=10000),
            {"panelNumber": 2, "status": "READY", "pipeline_status": "PASSED", "scene": "x"},
            make_panel(3, timing_ms=20000),
            make_panel(4, timing_ms=5000),
        ]
        s = JobSignals(panels, 4).compute()
        assert s["total_latency_ms"] == 35000
        assert s["avg_latency_ms"] == round(35000 / 3)


# ── 5. Heavy repair concentration tests ─────────────────────────────────────

class TestJobSignalsRepairConcentration:
    """Many repaired panels that technically passed."""

    def test_all_repaired_high_quality(self):
        """Every panel needed repair but emerged with high scores."""
        panels = [
            make_panel(i + 1, pipeline_status=PanelStatus.PASSED_REPAIRED.value,
                       face_consistency=0.90, style_consistency=0.88, attempts=2)
            for i in range(6)
        ]
        s = JobSignals(panels, 6).compute()
        assert s["ready_count"] == 6
        assert s["failed_count"] == 0
        assert s["repair_concentration"] == 1.0  # All repaired
        assert s["character_preserved"]  # High face scores

    def test_mix_of_repaired_and_degraded(self):
        panels = [
            make_panel(1, pipeline_status=PanelStatus.PASSED.value),
            make_panel(2, pipeline_status=PanelStatus.PASSED_REPAIRED.value, attempts=2),
            make_panel(3, pipeline_status=PanelStatus.PASSED_DEGRADED.value, attempts=3),
            make_panel(4, pipeline_status=PanelStatus.PASSED.value),
            make_panel(5, pipeline_status=PanelStatus.PASSED_REPAIRED.value, attempts=2),
            make_panel(6, pipeline_status=PanelStatus.PASSED_DEGRADED.value, attempts=3),
        ]
        s = JobSignals(panels, 6).compute()
        assert s["repaired_count"] == 2
        assert s["degraded_count"] == 2
        assert s["repair_concentration"] == round(4 / 6, 3)  # 4/6 needed rescue
        assert s["fallback_contamination"] == round(2 / 6, 3)  # 2/6 degraded

    def test_empty_panel_list(self):
        """Edge case: zero panels."""
        s = JobSignals([], 0).compute()
        assert s["total_panels"] == 0
        assert s["pass_rate"] == 0
        assert s["fail_rate"] == 0
        assert s["cost_burn_ratio"] == 1.0  # 0/0 defaults to 1.0

    def test_single_panel(self):
        panels = [make_panel(1, face_consistency=0.90)]
        s = JobSignals(panels, 1).compute()
        assert s["ready_count"] == 1
        assert s["pass_rate"] == 1.0
        assert s["story_coverage"] == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
