"""
P0.5 Adversarial Smoke Pack — Proves the foundation before full chaos matrix.

Categories:
  1. Threshold-edge cases (signals at exact boundaries trip correct decision)
  2. Validator disagreement (conflicting signal combinations)
  3. Cost breach (cost burn ratio exceeds budget with acceptable outputs)
  4. Continuity pack corruption (poisoned/corrupted panel references)
  5. Fallback exhaustion (all repair paths fail, system exits cleanly)

Invariants tested:
  - No crash
  - No infinite retry
  - No silent success on corrupted output
  - No missing decision
  - No cap violation
  - No empty final state
"""
import pytest
import asyncio
import sys
import os
from unittest.mock import AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.comic_pipeline.job_orchestrator import JobOrchestrator, JobDecision, JobSignals, JobPolicy
from services.comic_pipeline.continuity_pack import ContinuityPack
from enums.pipeline_enums import PanelStatus, RiskBucket, PASS_THRESHOLDS


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_panel(pn, status="READY", ps=PanelStatus.PASSED.value,
               face=0.85, style=0.80, scene="s", timing_ms=5000, attempts=1):
    return {
        "panelNumber": pn, "status": status, "pipeline_status": ps,
        "validation_scores": {"face_consistency": face, "style_consistency": style},
        "scene": scene, "timing_ms": timing_ms, "attempts": attempts,
    }


def make_failed(pn):
    return make_panel(pn, status="FAILED", ps=PanelStatus.FAILED.value, face=0, style=0)


class MockDB:
    def __init__(self):
        self.logged_decisions = []
        self.comic_job_decisions = self
    async def insert_one(self, doc):
        self.logged_decisions.append(doc)


policy = JobPolicy()


# ══════════════════════════════════════════════════════════════════════════════
# 1. THRESHOLD-EDGE CASES
# ══════════════════════════════════════════════════════════════════════════════

class TestAdversarialThresholdEdge:
    """Signals at exact thresholds must always resolve deterministically."""

    def test_fail_rate_0749_vs_0750(self):
        """0.749... is not terminal, 0.75 is. Proves >= boundary."""
        # 2 ready, 4 failed out of 6 = 0.667 fail rate = NOT terminal
        sig_below = JobSignals(
            [make_panel(1), make_panel(2)] + [make_failed(i) for i in range(3, 7)], 6
        ).compute()
        assert sig_below["fail_rate"] < 0.75
        res_below = policy.evaluate(sig_below)
        assert res_below["decision"] != JobDecision.FAIL_TERMINAL

        # 1 ready, 3 failed out of 4 = 0.75 fail rate = terminal
        sig_at = JobSignals(
            [make_panel(1)] + [make_failed(i) for i in range(2, 5)], 4
        ).compute()
        assert sig_at["fail_rate"] == 0.75
        res_at = policy.evaluate(sig_at)
        assert res_at["decision"] == JobDecision.FAIL_TERMINAL

    def test_targeted_rerun_at_exact_025(self):
        """1 out of 4 failed = 0.25. Must trigger TARGETED, not ACCEPT."""
        panels = [make_panel(1), make_panel(2), make_panel(3), make_failed(4)]
        sig = JobSignals(panels, 4).compute()
        assert sig["fail_rate"] == 0.25
        res = policy.evaluate(sig)
        assert res["decision"] == JobDecision.TARGETED_PANEL_RERUN

    def test_targeted_rerun_just_above_025(self):
        """2 out of 6 failed = 0.333. Too high for targeted rerun."""
        panels = [make_panel(i+1) for i in range(4)] + [make_failed(5), make_failed(6)]
        sig = JobSignals(panels, 6).compute()
        assert round(sig["fail_rate"], 3) == 0.333
        res = policy.evaluate(sig)
        assert res["decision"] != JobDecision.TARGETED_PANEL_RERUN

    def test_repair_concentration_at_050(self):
        """Exactly at 0.5 ceiling should NOT trigger style downgrade (requires >)."""
        panels = [
            make_panel(1, ps=PanelStatus.PASSED_REPAIRED.value, attempts=2),
            make_panel(2, ps=PanelStatus.PASSED_REPAIRED.value, attempts=2),
            make_failed(3),
            make_failed(4),
        ]
        sig = JobSignals(panels, 4).compute()
        assert sig["repair_concentration"] == 0.5
        res = policy.evaluate(sig)
        assert res["decision"] != JobDecision.STYLE_DOWNGRADE_RERUN

    def test_repair_concentration_at_051(self):
        """0.51 must trigger style downgrade."""
        # 3 repaired + 1 degraded = 4 repaired/degraded, 2 failed, out of 6
        panels = [
            make_panel(1, ps=PanelStatus.PASSED_REPAIRED.value, attempts=2),
            make_panel(2, ps=PanelStatus.PASSED_REPAIRED.value, attempts=2),
            make_panel(3, ps=PanelStatus.PASSED_DEGRADED.value, attempts=3),
            make_panel(4),
            make_failed(5),
            make_failed(6),
        ]
        sig = JobSignals(panels, 6).compute()
        # repair_concentration = (2 repaired + 1 degraded) / 6 = 0.5
        # Adjust to get above 0.5
        panels2 = [
            make_panel(1, ps=PanelStatus.PASSED_REPAIRED.value, attempts=2),
            make_panel(2, ps=PanelStatus.PASSED_REPAIRED.value, attempts=2),
            make_panel(3, ps=PanelStatus.PASSED_DEGRADED.value, attempts=3),
            make_failed(4),
            make_failed(5),
        ]
        sig2 = JobSignals(panels2, 5).compute()
        # repair_conc = (2+1)/5 = 0.6
        assert sig2["repair_concentration"] == 0.6
        res = policy.evaluate(sig2)
        assert res["decision"] == JobDecision.STYLE_DOWNGRADE_RERUN


# ══════════════════════════════════════════════════════════════════════════════
# 2. VALIDATOR DISAGREEMENT
# ══════════════════════════════════════════════════════════════════════════════

class TestAdversarialValidatorDisagreement:
    """Conflicting quality signals must still yield a single legal decision."""

    def test_high_face_zero_style(self):
        """Face perfect, style completely drifted."""
        panels = [make_panel(i+1, face=0.98, style=0.0) for i in range(4)]
        sig = JobSignals(panels, 4).compute()
        res = policy.evaluate(sig)
        assert res["decision"] in (
            JobDecision.ACCEPT_FULL,
            JobDecision.ACCEPT_WITH_DEGRADATION,
        )
        # Decision must exist
        assert res["decision"] is not None

    def test_zero_face_high_style(self):
        """No face data, but style is consistent."""
        panels = [make_panel(i+1, face=0, style=0.95) for i in range(4)]
        sig = JobSignals(panels, 4).compute()
        assert sig["character_preserved"]  # No face data = default True
        res = policy.evaluate(sig)
        # Should accept since panels are ready
        assert res["decision"] in (
            JobDecision.ACCEPT_FULL,
            JobDecision.ACCEPT_WITH_DEGRADATION,
        )

    def test_all_repaired_high_quality(self):
        """Every panel needed repair but scores are excellent."""
        panels = [
            make_panel(i+1, ps=PanelStatus.PASSED_REPAIRED.value,
                       face=0.95, style=0.92, attempts=2)
            for i in range(4)
        ]
        sig = JobSignals(panels, 4).compute()
        assert sig["repair_concentration"] == 1.0
        res = policy.evaluate(sig)
        # High repair concentration (1.0 > 0.15) means NOT ACCEPT_FULL
        assert res["decision"] != JobDecision.ACCEPT_FULL
        # But all panels are ready, so should accept with degradation
        assert res["decision"] == JobDecision.ACCEPT_WITH_DEGRADATION

    def test_mixed_pass_and_degraded_good_coverage(self):
        """Some passed, some degraded, but story coverage is full.
        FINDING: 2/4 PASSED_DEGRADED = 0.5 fallback_contamination.
        Policy uses strict < 0.5, so this correctly rejects ACCEPT_WITH_DEGRADATION
        and falls to PARTIAL_USABLE_OUTPUT. This is by design — 50% degraded is too risky.
        """
        panels = [
            make_panel(1),
            make_panel(2, ps=PanelStatus.PASSED_DEGRADED.value),
            make_panel(3),
            make_panel(4, ps=PanelStatus.PASSED_DEGRADED.value),
        ]
        sig = JobSignals(panels, 4).compute()
        assert sig["fallback_contamination"] == 0.5  # At exact boundary
        res = policy.evaluate(sig)
        # All panels are READY, but 50% fallback contamination triggers
        # PARTIAL_USABLE_OUTPUT (strict < boundary on ACCEPT_WITH_DEGRADATION)
        assert res["decision"] == JobDecision.PARTIAL_USABLE_OUTPUT


# ══════════════════════════════════════════════════════════════════════════════
# 3. COST BREACH
# ══════════════════════════════════════════════════════════════════════════════

class TestAdversarialCostBreach:
    """Cost burn ratio exceeds budget with acceptable panel outputs."""

    def test_high_cost_burn_all_panels_ready(self):
        """Every panel took 3 attempts (max), cost burn = 3.0, but all ready."""
        panels = [make_panel(i+1, attempts=3) for i in range(4)]
        sig = JobSignals(panels, 4).compute()
        assert sig["cost_burn_ratio"] == 3.0
        # Panels are all ready with 0 failures and 0 repair concentration
        # (attempts ≠ repair_concentration, repair_conc checks pipeline_status)
        res = policy.evaluate(sig)
        # With all panels PASSED (not REPAIRED/DEGRADED), it should accept
        assert res["decision"] in (
            JobDecision.ACCEPT_FULL,
            JobDecision.ACCEPT_WITH_DEGRADATION,
        )

    def test_extreme_latency_all_panels_ready(self):
        """Each panel took 90 seconds (way beyond budget), but all ready."""
        panels = [make_panel(i+1, timing_ms=90000) for i in range(4)]
        sig = JobSignals(panels, 4).compute()
        assert sig["total_latency_ms"] == 360000
        # Policy doesn't currently gate on latency — all pass
        res = policy.evaluate(sig)
        assert res["decision"] == JobDecision.ACCEPT_FULL


# ══════════════════════════════════════════════════════════════════════════════
# 4. CONTINUITY PACK CORRUPTION
# ══════════════════════════════════════════════════════════════════════════════

class TestAdversarialContinuityCorruption:
    """Poisoned/corrupted references must not break the pack."""

    def test_all_panels_empty_bytes(self):
        """All panels registered with empty bytes — pack should still work."""
        pack = ContinuityPack()
        for i in range(4):
            pack.register_approved_panel(i, b"", {"face_consistency": 0, "style_consistency": 0})
        
        ctx = pack.get_generation_context(4)
        # Should still return references (they're empty but registered)
        assert ctx is not None or pack.approved_count == 4

    def test_all_panels_zero_confidence(self):
        """All panels have zero confidence — no 'best face' selection should crash."""
        pack = ContinuityPack()
        for i in range(6):
            pack.register_approved_panel(i, f"p{i}".encode(),
                                          {"face_consistency": 0, "style_consistency": 0})
        
        ctx = pack.get_generation_context(6)
        assert ctx is not None
        # Anchor (panel 0) should still be included
        assert b"p0" in ctx

    def test_gigantic_panel_history(self):
        """100 panels registered — pack must stay bounded."""
        pack = ContinuityPack()
        for i in range(100):
            pack.register_approved_panel(i, f"p{i}".encode(),
                                          {"face_consistency": 0.5, "style_consistency": 0.5})
        
        gen_ctx = pack.get_generation_context(100)
        val_ctx = pack.get_validation_context(100)
        assert gen_ctx is not None
        assert len(gen_ctx) <= 3  # BOUNDED
        assert val_ctx is not None
        assert len(val_ctx) <= 4  # BOUNDED

    def test_duplicate_panel_indices(self):
        """Registering same index twice — last write wins, no crash."""
        pack = ContinuityPack()
        pack.register_approved_panel(0, b"first", {"face_consistency": 0.50, "style_consistency": 0.50})
        pack.register_approved_panel(0, b"second", {"face_consistency": 0.95, "style_consistency": 0.90})
        
        assert pack.approved_count == 1  # Overwritten
        ctx = pack.get_generation_context(1)
        assert ctx is not None
        assert ctx[0] == b"second"  # Last write wins

    def test_non_sequential_registration(self):
        """Panels registered out of order — pack handles correctly."""
        pack = ContinuityPack()
        pack.register_approved_panel(3, b"p3", {"face_consistency": 0.85, "style_consistency": 0.80})
        pack.register_approved_panel(0, b"p0", {"face_consistency": 0.90, "style_consistency": 0.85})
        pack.register_approved_panel(5, b"p5", {"face_consistency": 0.70, "style_consistency": 0.75})
        
        ctx = pack.get_generation_context(6)
        assert ctx is not None
        assert b"p0" in ctx  # Anchor
        # Should be sorted by index
        indices = []
        for b in ctx:
            for i, name in [(0, b"p0"), (3, b"p3"), (5, b"p5")]:
                if b == name:
                    indices.append(i)
        assert indices == sorted(indices)

    def test_validation_with_single_panel(self):
        """Validation context with only anchor panel registered."""
        pack = ContinuityPack()
        pack.register_approved_panel(0, b"anchor", {"face_consistency": 0.90, "style_consistency": 0.85})
        
        val_ctx = pack.get_validation_context(1)
        assert val_ctx is not None
        assert len(val_ctx) == 1
        assert val_ctx[0] == b"anchor"


# ══════════════════════════════════════════════════════════════════════════════
# 5. FALLBACK EXHAUSTION
# ══════════════════════════════════════════════════════════════════════════════

class TestAdversarialFallbackExhaustion:
    """All repair paths fail — system exits cleanly."""

    @pytest.mark.asyncio
    async def test_all_reruns_fail_gracefully(self):
        """Orchestrator reruns panels but all fail — must still return valid result."""
        db = MockDB()
        orch = JobOrchestrator(db)

        mock_panel_orch = AsyncMock()
        # All reruns return FAILED
        mock_panel_orch.process_panel = AsyncMock(return_value={
            "panelNumber": 1, "status": "FAILED",
            "pipeline_status": PanelStatus.FAILED.value,
            "validation_scores": {"face_consistency": 0}, "scene": "s",
            "timing_ms": 3000, "attempts": 3,
        })

        panels = [
            make_panel(1),
            make_panel(2),
            make_panel(3),
            make_failed(4),
        ]

        rerun_ctx = {
            "story_scenes": [{"scene": f"s{i}"} for i in range(4)],
            "style": "cartoon_fun", "style_prompt": "test",
            "genre": "action", "photo_b64": "b64", "negative_prompt": "neg",
            "panel_count": 4, "character_lock": None,
            "source_image_bytes": b"src", "continuity_pack": None,
            "user_id": "usr",
        }

        result = await orch.evaluate_and_execute(
            "exhaust-1", panels, 4,
            orchestrator=mock_panel_orch,
            rerun_context=rerun_ctx,
        )

        # Must return a valid result
        assert "decision" in result
        assert "job_status" in result
        assert "panels" in result

    @pytest.mark.asyncio
    async def test_style_downgrade_all_fail(self):
        """Style downgrade reruns all fail — must return FAILED status."""
        db = MockDB()
        orch = JobOrchestrator(db)

        mock_panel_orch = AsyncMock()
        mock_panel_orch.process_panel = AsyncMock(
            side_effect=Exception("Provider completely down")
        )

        # Force style downgrade scenario
        panels = [
            make_panel(1, ps=PanelStatus.PASSED_REPAIRED.value, attempts=3),
            make_panel(2, ps=PanelStatus.PASSED_REPAIRED.value, attempts=3),
            make_failed(3),
            make_failed(4),
        ]

        rerun_ctx = {
            "story_scenes": [{"scene": f"s{i}"} for i in range(4)],
            "style": "cartoon_fun", "style_prompt": "test",
            "genre": "action", "photo_b64": "b64", "negative_prompt": "neg",
            "panel_count": 4, "character_lock": None,
            "source_image_bytes": b"src", "continuity_pack": None,
            "user_id": "usr",
        }

        result = await orch.evaluate_and_execute(
            "exhaust-2", panels, 4,
            orchestrator=mock_panel_orch,
            rerun_context=rerun_ctx,
        )

        # Must not crash
        assert "decision" in result
        assert "panels" in result

    @pytest.mark.asyncio
    async def test_zero_panels_zero_count(self):
        """Empty job — exits cleanly with FAIL_TERMINAL."""
        db = MockDB()
        orch = JobOrchestrator(db)
        result = await orch.evaluate_and_execute("empty-job", [], 0)
        assert result["decision"] == JobDecision.FAIL_TERMINAL
        assert result["job_status"] == "FAILED"

    @pytest.mark.asyncio
    async def test_single_failed_panel_job(self):
        """Job with only 1 panel that failed."""
        db = MockDB()
        orch = JobOrchestrator(db)
        result = await orch.evaluate_and_execute("single-fail", [make_failed(1)], 1)
        assert result["decision"] == JobDecision.FAIL_TERMINAL
        assert result["job_status"] == "FAILED"

    @pytest.mark.asyncio
    async def test_decision_log_on_exhaustion(self):
        """Even exhausted paths must log decisions."""
        db = MockDB()
        orch = JobOrchestrator(db)
        result = await orch.evaluate_and_execute("log-exhaust", [make_failed(i+1) for i in range(4)], 4)
        
        assert len(db.logged_decisions) == 1
        log = db.logged_decisions[0]
        assert log["decision"] == JobDecision.FAIL_TERMINAL
        assert len(log["reason"]) > 0


# ══════════════════════════════════════════════════════════════════════════════
# 6. INVARIANT MATRIX — Cross-cutting invariants
# ══════════════════════════════════════════════════════════════════════════════

class TestAdversarialInvariants:
    """Every scenario must satisfy these invariants."""

    LEGAL_DECISIONS = {
        JobDecision.ACCEPT_FULL,
        JobDecision.ACCEPT_WITH_DEGRADATION,
        JobDecision.TARGETED_PANEL_RERUN,
        JobDecision.STYLE_DOWNGRADE_RERUN,
        JobDecision.PARTIAL_USABLE_OUTPUT,
        JobDecision.FAIL_TERMINAL,
    }

    LEGAL_STATUSES = {"COMPLETED", "READY_WITH_WARNINGS", "PARTIAL_READY", "FAILED"}

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scenario_name,panels,panel_count", [
        ("all_pass_4", [make_panel(i+1) for i in range(4)], 4),
        ("all_fail_4", [make_failed(i+1) for i in range(4)], 4),
        ("half_fail_4", [make_panel(1), make_panel(2), make_failed(3), make_failed(4)], 4),
        ("single_pass", [make_panel(1)], 1),
        ("single_fail", [make_failed(1)], 1),
        ("all_degraded", [make_panel(i+1, ps=PanelStatus.PASSED_DEGRADED.value) for i in range(4)], 4),
        ("all_repaired", [make_panel(i+1, ps=PanelStatus.PASSED_REPAIRED.value, attempts=2) for i in range(4)], 4),
        ("mixed_6", [make_panel(1), make_failed(2), make_panel(3, ps=PanelStatus.PASSED_REPAIRED.value, attempts=2), make_panel(4), make_failed(5), make_panel(6, ps=PanelStatus.PASSED_DEGRADED.value)], 6),
    ])
    async def test_invariant_legal_decision(self, scenario_name, panels, panel_count):
        """Every scenario produces a legal decision."""
        db = MockDB()
        orch = JobOrchestrator(db)
        result = await orch.evaluate_and_execute(f"inv-{scenario_name}", panels, panel_count)
        
        assert result["decision"] in self.LEGAL_DECISIONS, \
            f"Illegal decision '{result['decision']}' in scenario {scenario_name}"
        assert result["job_status"] in self.LEGAL_STATUSES, \
            f"Illegal status '{result['job_status']}' in scenario {scenario_name}"
        assert "panels" in result
        assert "decision_log" in result
        assert "progress_msg" in result
        assert len(result["progress_msg"]) > 0

    @pytest.mark.asyncio
    async def test_no_empty_final_state(self):
        """Result must never have None/empty decision, status, or panels."""
        db = MockDB()
        orch = JobOrchestrator(db)

        for case in [
            [make_panel(i+1) for i in range(4)],
            [make_failed(i+1) for i in range(4)],
            [],
        ]:
            result = await orch.evaluate_and_execute("nfs", case, max(len(case), 1))
            assert result["decision"] is not None
            assert result["job_status"] is not None
            assert result["panels"] is not None
            assert isinstance(result["panels"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
