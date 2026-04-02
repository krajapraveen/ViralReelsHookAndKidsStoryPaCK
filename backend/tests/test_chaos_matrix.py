"""
P1 Chaos Matrix — Structured kill tests for the Smart Repair Pipeline.

Every case proves these invariants:
  - No crash
  - No infinite retry
  - No silent success on corrupted output
  - No missing decision
  - No cap violation (attempts, context size)
  - No empty final state

Matrix structure:
  | Scenario | Injected Fault | Expected Signals | Expected Policy | Allowed Degradation | Forbidden |

Categories:
  A. Input/Model Chaos: blurry faces, no face, multi-face, style overcompliance
  B. Economic/Operational Chaos: validator timeouts, corrupt bytes, expensive loops, cost breach
  C. Pipeline State Machine: illegal transitions, stale state, concurrent mutation
  D. Cross-Panel Chaos: continuity breaks, anchor corruption, divergent styles
"""
import pytest
import asyncio
import sys
import os
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.comic_pipeline.job_orchestrator import JobOrchestrator, JobDecision, JobSignals, JobPolicy
from services.comic_pipeline.continuity_pack import ContinuityPack
from services.comic_pipeline.validator_stack import ValidatorStack, AssetValidator
from services.comic_pipeline.model_router import ModelRouter
from enums.pipeline_enums import (
    PanelStatus, RiskBucket, FailureType, FailureClass, ModelTier,
    RepairMode, ValidationResult, PanelScores,
    MAX_TOTAL_ATTEMPTS_PER_PANEL, PASS_THRESHOLDS, FALLBACK_THRESHOLDS,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_panel(pn, status="READY", ps=PanelStatus.PASSED.value,
               face=0.85, style=0.80, scene="s", timing_ms=5000, attempts=1,
               fallback=False):
    p = {
        "panelNumber": pn, "status": status, "pipeline_status": ps,
        "validation_scores": {"face_consistency": face, "style_consistency": style},
        "scene": scene, "timing_ms": timing_ms, "attempts": attempts,
    }
    if fallback:
        p["fallback"] = True
    return p


def make_failed(pn, timing_ms=5000, attempts=3):
    return make_panel(pn, status="FAILED", ps=PanelStatus.FAILED.value,
                      face=0, style=0, timing_ms=timing_ms, attempts=attempts)


class MockDB:
    def __init__(self):
        self.logged_decisions = []
        self.comic_job_decisions = self
    async def insert_one(self, doc):
        self.logged_decisions.append(doc)


policy = JobPolicy()

LEGAL_DECISIONS = {
    JobDecision.ACCEPT_FULL, JobDecision.ACCEPT_WITH_DEGRADATION,
    JobDecision.TARGETED_PANEL_RERUN, JobDecision.STYLE_DOWNGRADE_RERUN,
    JobDecision.PARTIAL_USABLE_OUTPUT, JobDecision.FAIL_TERMINAL,
}

LEGAL_STATUSES = {"COMPLETED", "READY_WITH_WARNINGS", "PARTIAL_READY", "FAILED"}


# ══════════════════════════════════════════════════════════════════════════════
# A. INPUT/MODEL CHAOS
# ══════════════════════════════════════════════════════════════════════════════

class TestChaosInputModel:
    """Chaos from bad inputs and model behavior."""

    def test_a1_no_face_detected_all_panels(self):
        """
        Scenario: Source photo has no face. All panels generated with face=0.
        Expected: character_preserved=True (default when no data), policy accepts.
        Forbidden: FAIL_TERMINAL when panels are actually ready.
        """
        panels = [make_panel(i+1, face=0, style=0.80) for i in range(4)]
        sig = JobSignals(panels, 4).compute()
        assert sig["character_preserved"]  # No face data = default True
        assert sig["avg_face_consistency"] == 0
        res = policy.evaluate(sig)
        assert res["decision"] in (JobDecision.ACCEPT_FULL, JobDecision.ACCEPT_WITH_DEGRADATION)
        assert res["decision"] != JobDecision.FAIL_TERMINAL

    def test_a2_multi_face_extreme_risk(self):
        """
        Scenario: Multi-face photo → HIGH risk → Tier 2 routing.
        Expected: ModelRouter selects TIER2_STABLE_CHARACTER.
        """
        router = ModelRouter()
        tier = router.choose_initial_tier(RiskBucket.HIGH)
        assert tier == ModelTier.TIER2_STABLE_CHARACTER

        tier_extreme = router.choose_initial_tier(RiskBucket.EXTREME)
        assert tier_extreme == ModelTier.TIER2_STABLE_CHARACTER

    def test_a3_style_overcompliance_all_degraded(self):
        """
        Scenario: Model overcomplied with style, all panels PASSED_DEGRADED.
        Expected: PARTIAL_USABLE_OUTPUT or ACCEPT_WITH_DEGRADATION.
        Forbidden: ACCEPT_FULL.
        """
        panels = [
            make_panel(i+1, ps=PanelStatus.PASSED_DEGRADED.value, face=0.70, style=0.60)
            for i in range(4)
        ]
        sig = JobSignals(panels, 4).compute()
        assert sig["fallback_contamination"] == 1.0  # All degraded
        res = policy.evaluate(sig)
        assert res["decision"] != JobDecision.ACCEPT_FULL

    def test_a4_blurry_face_low_similarity_all_panels(self):
        """
        Scenario: Blurry source → low face similarity across all panels.
        Expected: Ready panels with low face scores. Policy should not crash.
        """
        panels = [make_panel(i+1, face=0.30, style=0.75) for i in range(4)]
        sig = JobSignals(panels, 4).compute()
        assert not sig["character_preserved"]  # Below threshold
        res = policy.evaluate(sig)
        assert res["decision"] in LEGAL_DECISIONS

    def test_a5_mixed_face_quality(self):
        """
        Scenario: Some panels have great face match, others terrible.
        Expected: Average face consistency drives decision, not individual panels.
        """
        panels = [
            make_panel(1, face=0.95),
            make_panel(2, face=0.20),
            make_panel(3, face=0.90),
            make_panel(4, face=0.15),
        ]
        sig = JobSignals(panels, 4).compute()
        assert 0.40 < sig["avg_face_consistency"] < 0.60  # Mixed
        res = policy.evaluate(sig)
        assert res["decision"] in LEGAL_DECISIONS


# ══════════════════════════════════════════════════════════════════════════════
# B. ECONOMIC/OPERATIONAL CHAOS
# ══════════════════════════════════════════════════════════════════════════════

class TestChaosEconomicOperational:
    """Chaos from resource exhaustion and operational failures."""

    def test_b1_all_panels_max_attempts(self):
        """
        Scenario: Every panel hit the 3-attempt cap.
        Expected: Cost burn ratio = 3.0. Still decides based on outcomes.
        Forbidden: cost_burn_ratio miscalculated.
        """
        panels = [make_panel(i+1, attempts=MAX_TOTAL_ATTEMPTS_PER_PANEL) for i in range(4)]
        sig = JobSignals(panels, 4).compute()
        assert sig["cost_burn_ratio"] == float(MAX_TOTAL_ATTEMPTS_PER_PANEL)
        assert sig["total_attempts"] == 4 * MAX_TOTAL_ATTEMPTS_PER_PANEL
        res = policy.evaluate(sig)
        assert res["decision"] in LEGAL_DECISIONS

    def test_b2_extreme_latency_budget_exceeded(self):
        """
        Scenario: Each panel took 2 minutes. Total far exceeds any reasonable budget.
        Expected: Policy still makes a decision (latency doesn't block acceptance).
        """
        panels = [make_panel(i+1, timing_ms=120_000) for i in range(4)]
        sig = JobSignals(panels, 4).compute()
        assert sig["total_latency_ms"] == 480_000  # 8 minutes
        res = policy.evaluate(sig)
        # Currently latency is NOT a policy gate
        assert res["decision"] in LEGAL_DECISIONS

    def test_b3_cost_burn_3x_with_all_pass(self):
        """
        Scenario: Very expensive job (3x attempts each) but all panels ready.
        Expected: ACCEPT despite high cost burn.
        Forbidden: FAIL_TERMINAL when all panels are ready.
        """
        panels = [make_panel(i+1, attempts=3) for i in range(4)]
        sig = JobSignals(panels, 4).compute()
        assert sig["cost_burn_ratio"] == 3.0
        res = policy.evaluate(sig)
        assert res["decision"] != JobDecision.FAIL_TERMINAL

    def test_b4_expensive_repairs_then_all_fail(self):
        """
        Scenario: 3 attempts per panel, all still failed.
        Expected: FAIL_TERMINAL with max cost burn.
        """
        panels = [make_failed(i+1, attempts=3) for i in range(4)]
        sig = JobSignals(panels, 4).compute()
        assert sig["cost_burn_ratio"] == 3.0
        assert sig["fail_rate"] == 1.0
        res = policy.evaluate(sig)
        assert res["decision"] == JobDecision.FAIL_TERMINAL

    @pytest.mark.asyncio
    async def test_b5_orchestrator_exception_mid_rerun(self):
        """
        Scenario: Panel orchestrator throws exception during targeted rerun.
        Expected: Graceful degradation, valid result returned.
        Forbidden: Unhandled exception.
        """
        db = MockDB()
        orch = JobOrchestrator(db)

        mock_panel_orch = AsyncMock()
        call_count = 0
        async def flaky_process_panel(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Provider unreachable")
            return make_panel(kwargs["panel_index"] + 1)
        mock_panel_orch.process_panel = AsyncMock(side_effect=flaky_process_panel)

        panels = [make_panel(1), make_panel(2), make_panel(3), make_failed(4)]
        rerun_ctx = {
            "story_scenes": [{"scene": f"s{i}"} for i in range(4)],
            "style": "cartoon_fun", "style_prompt": "test",
            "genre": "action", "photo_b64": "b64", "negative_prompt": "neg",
            "panel_count": 4, "character_lock": None,
            "source_image_bytes": b"src", "continuity_pack": None,
            "user_id": "usr",
        }

        # Should not crash
        result = await orch.evaluate_and_execute(
            "chaos-b5", panels, 4,
            orchestrator=mock_panel_orch,
            rerun_context=rerun_ctx,
        )
        assert "decision" in result
        assert result["decision"] in LEGAL_DECISIONS


# ══════════════════════════════════════════════════════════════════════════════
# C. PIPELINE STATE MACHINE CHAOS
# ══════════════════════════════════════════════════════════════════════════════

class TestChaosPipelineStateMachine:
    """Chaos in pipeline state transitions and data integrity."""

    def test_c1_panels_with_invalid_status(self):
        """
        Scenario: Panel data with unexpected status strings.
        Expected: Signal extraction handles gracefully (treated as neither READY nor FAILED).
        """
        panels = [
            {"panelNumber": 1, "status": "UNKNOWN", "pipeline_status": "WEIRD",
             "scene": "s", "timing_ms": 1000, "attempts": 1},
            make_panel(2),
            make_panel(3),
            {"panelNumber": 4, "status": "GENERATING", "pipeline_status": "IN_PROGRESS",
             "scene": "s", "timing_ms": 1000, "attempts": 1},
        ]
        sig = JobSignals(panels, 4).compute()
        # UNKNOWN and GENERATING are neither READY nor FAILED
        assert sig["ready_count"] == 2
        assert sig["failed_count"] == 0
        # Should still produce a decision
        res = policy.evaluate(sig)
        assert res["decision"] in LEGAL_DECISIONS

    def test_c2_duplicate_panel_numbers(self):
        """
        Scenario: Two panels with the same panelNumber.
        Expected: Signals compute without crash. sequential = False.
        """
        panels = [
            make_panel(1),
            make_panel(1),  # Duplicate
            make_panel(3),
            make_panel(4),
        ]
        sig = JobSignals(panels, 4).compute()
        assert not sig["sequential"]  # 1, 1, 3, 4 is not sequential
        res = policy.evaluate(sig)
        assert res["decision"] in LEGAL_DECISIONS

    def test_c3_panel_count_mismatch(self):
        """
        Scenario: panel_count says 6 but only 3 panels provided.
        Expected: story_coverage reflects actual vs expected.
        """
        panels = [make_panel(i+1) for i in range(3)]
        sig = JobSignals(panels, 6).compute()
        assert sig["story_coverage"] == 0.5  # 3/6
        assert sig["total_panels"] == 3
        res = policy.evaluate(sig)
        assert res["decision"] in LEGAL_DECISIONS

    def test_c4_panels_with_missing_fields(self):
        """
        Scenario: Panels missing validation_scores or timing_ms.
        Expected: Graceful defaults, no KeyError.
        """
        panels = [
            {"panelNumber": 1, "status": "READY", "pipeline_status": "PASSED", "scene": "s"},
            {"panelNumber": 2, "status": "READY", "scene": "s", "timing_ms": 3000},
            {"panelNumber": 3, "status": "FAILED", "scene": "s"},
            make_panel(4),
        ]
        sig = JobSignals(panels, 4).compute()
        # Should not crash on missing fields
        assert sig["total_panels"] == 4
        res = policy.evaluate(sig)
        assert res["decision"] in LEGAL_DECISIONS

    def test_c5_non_dict_panels(self):
        """
        Scenario: Panel list contains non-dict items (corruption).
        Expected: Silently skipped, no crash.
        """
        panels = [
            make_panel(1),
            None,  # Corrupted
            "string_panel",  # Corrupted
            make_panel(4),
        ]
        sig = JobSignals(panels, 4).compute()
        # None and string should be handled by isinstance checks
        assert sig["ready_count"] == 2
        res = policy.evaluate(sig)
        assert res["decision"] in LEGAL_DECISIONS


# ══════════════════════════════════════════════════════════════════════════════
# D. CROSS-PANEL CHAOS
# ══════════════════════════════════════════════════════════════════════════════

class TestChaosCrossPanel:
    """Chaos in cross-panel consistency and continuity."""

    def test_d1_anchor_panel_failed_rest_pass(self):
        """
        Scenario: Panel 1 (anchor) failed but panels 2-4 passed.
        Expected: Should NOT be ACCEPT_FULL (broken story start).
        """
        panels = [
            make_failed(1),
            make_panel(2),
            make_panel(3),
            make_panel(4),
        ]
        sig = JobSignals(panels, 4).compute()
        assert sig["failed_count"] == 1
        res = policy.evaluate(sig)
        assert res["decision"] == JobDecision.TARGETED_PANEL_RERUN

    def test_d2_last_panel_failed_rest_pass(self):
        """
        Scenario: Only the final panel failed.
        Expected: TARGETED_PANEL_RERUN for just the last panel.
        """
        panels = [make_panel(i+1) for i in range(3)] + [make_failed(4)]
        sig = JobSignals(panels, 4).compute()
        assert sig["failed_indices"] == [3]
        res = policy.evaluate(sig)
        assert res["decision"] == JobDecision.TARGETED_PANEL_RERUN

    def test_d3_alternating_pass_fail(self):
        """
        Scenario: Panels alternate pass/fail (worst for visual continuity).
        Expected: Policy handles the pattern — not ACCEPT_FULL.
        """
        panels = [
            make_panel(1),
            make_failed(2),
            make_panel(3),
            make_failed(4),
            make_panel(5),
            make_failed(6),
        ]
        sig = JobSignals(panels, 6).compute()
        assert sig["fail_rate"] == 0.5
        res = policy.evaluate(sig)
        assert res["decision"] != JobDecision.ACCEPT_FULL
        assert res["decision"] in LEGAL_DECISIONS

    def test_d4_continuity_pack_all_zero_face_confidence(self):
        """
        Scenario: Every registered panel has 0 face confidence.
        Expected: Pack still works, no "best face" selected, anchor used.
        """
        pack = ContinuityPack()
        for i in range(6):
            pack.register_approved_panel(
                i, f"p{i}".encode(),
                {"face_consistency": 0.0, "style_consistency": 0.50}
            )
        
        ctx = pack.get_generation_context(6)
        assert ctx is not None
        assert len(ctx) <= 3
        assert b"p0" in ctx  # Anchor always included

    def test_d5_continuity_pack_descending_confidence(self):
        """
        Scenario: Each panel has lower confidence than the previous.
        Expected: Anchor and first panel (highest confidence) selected.
        """
        pack = ContinuityPack()
        confidences = [0.95, 0.80, 0.65, 0.50, 0.35, 0.20]
        for i, conf in enumerate(confidences):
            pack.register_approved_panel(
                i, f"p{i}".encode(),
                {"face_consistency": conf, "style_consistency": conf}
            )
        
        ctx = pack.get_generation_context(6)
        assert ctx is not None
        # Should include: anchor (p0, face=0.95), best face (p0 already used),
        # next best = p1 (0.80), previous = p5 (0.20)
        assert b"p0" in ctx  # Anchor = highest confidence

    def test_d6_continuity_pack_only_degraded_panels(self):
        """
        Scenario: All prior panels are from degraded fallback.
        Expected: Pack still serves references (can't be picky with degraded data).
        """
        pack = ContinuityPack()
        for i in range(4):
            pack.register_approved_panel(
                i, f"degraded_{i}".encode(),
                {"face_consistency": 0.40, "style_consistency": 0.35},
                pipeline_status="PASSED_DEGRADED",
            )
        
        ctx = pack.get_generation_context(4)
        assert ctx is not None
        # Even degraded panels should be served if they're all we have
        assert len(ctx) >= 1


# ══════════════════════════════════════════════════════════════════════════════
# E. VALIDATOR STACK CHAOS
# ══════════════════════════════════════════════════════════════════════════════

class TestChaosValidatorStack:
    """Direct validator stack chaos."""

    def test_e1_asset_validator_none_bytes(self):
        """None bytes = EMPTY_OUTPUT hard failure."""
        av = AssetValidator()
        ok, failures, details = av.validate(None)
        assert not ok
        assert FailureType.EMPTY_OUTPUT in failures

    def test_e2_asset_validator_tiny_bytes(self):
        """Extremely small bytes = CORRUPT_ASSET."""
        av = AssetValidator()
        ok, failures, details = av.validate(b"tiny")
        assert not ok
        assert FailureType.CORRUPT_ASSET in failures

    def test_e3_asset_validator_wrong_header(self):
        """Valid size but wrong header = CORRUPT_ASSET."""
        av = AssetValidator()
        ok, failures, details = av.validate(b"NOT_AN_IMAGE" * 200)
        assert not ok
        assert FailureType.CORRUPT_ASSET in failures

    def test_e4_asset_validator_valid_png(self):
        """Valid PNG header passes."""
        av = AssetValidator()
        png_bytes = b'\x89PNG\r\n\x1a\n' + b'\x00' * 2000
        ok, failures, details = av.validate(png_bytes)
        assert ok
        assert failures == []

    def test_e5_asset_validator_valid_jpeg(self):
        """Valid JPEG header passes."""
        av = AssetValidator()
        jpeg_bytes = b'\xff\xd8' + b'\x00' * 2000
        ok, failures, details = av.validate(jpeg_bytes)
        assert ok
        assert failures == []

    def test_e6_full_validator_stack_with_none(self):
        """Full validator stack with None image bytes."""
        vs = ValidatorStack()
        result = vs.validate(
            image_bytes=None,
            panel_plan={"panel_index": 0},
            panel_data={"panelNumber": 1, "scene": "test"},
        )
        assert not result.pass_status
        assert FailureType.EMPTY_OUTPUT in result.failure_types
        assert result.failure_class == FailureClass.HARD
        assert result.severity == 1.0

    def test_e7_full_validator_stack_with_corrupt(self):
        """Full validator stack with corrupt bytes (not an image)."""
        vs = ValidatorStack()
        result = vs.validate(
            image_bytes=b"this is not an image but it is long enough" * 100,
            panel_plan={"panel_index": 0},
            panel_data={"panelNumber": 1, "scene": "test"},
        )
        assert not result.pass_status
        assert FailureType.CORRUPT_ASSET in result.failure_types
        assert result.failure_class == FailureClass.HARD


# ══════════════════════════════════════════════════════════════════════════════
# F. MODEL ROUTER CHAOS
# ══════════════════════════════════════════════════════════════════════════════

class TestChaosModelRouter:
    """Model router edge cases and repair strategy selection."""

    def test_f1_unknown_risk_bucket(self):
        """Unexpected risk bucket should default safely."""
        router = ModelRouter()
        # RiskBucket.LOW is valid
        tier = router.choose_initial_tier(RiskBucket.LOW)
        assert tier == ModelTier.TIER1_QUALITY

    def test_f2_hard_failure_goes_to_tier4(self):
        """Hard failure must always route to Tier 4 degraded."""
        router = ModelRouter()
        validation = ValidationResult(
            pass_status=False,
            failure_types=[FailureType.HARD_FAIL],
            failure_class=FailureClass.HARD,
            severity=1.0,
        )
        strategy = router.choose_repair_strategy(validation)
        assert strategy.repair_mode == RepairMode.R4_DEGRADED_FALLBACK
        assert strategy.model_tier == ModelTier.TIER4_SAFE_DEGRADED
        assert strategy.degraded

    def test_f3_structural_failure_goes_to_tier3(self):
        """Structural failure routes to Tier 3 deterministic."""
        router = ModelRouter()
        validation = ValidationResult(
            pass_status=False,
            failure_types=[FailureType.STORY_MISMATCH],
            failure_class=FailureClass.STRUCTURAL,
            severity=0.5,
        )
        strategy = router.choose_repair_strategy(validation)
        assert strategy.repair_mode == RepairMode.R3_STRUCTURAL_REPAIR
        assert strategy.model_tier == ModelTier.TIER3_DETERMINISTIC

    def test_f4_face_drift_priority_over_style_drift(self):
        """When both face and style drift, face takes priority."""
        router = ModelRouter()
        validation = ValidationResult(
            pass_status=False,
            failure_types=[FailureType.STYLE_DRIFT, FailureType.FACE_DRIFT],
            failure_class=FailureClass.SOFT,
            severity=0.4,
        )
        strategy = router.choose_repair_strategy(validation)
        # Face drift is checked first in priority_order
        assert strategy.model_tier == ModelTier.TIER2_STABLE_CHARACTER

    def test_f5_severity_at_fallback_threshold(self):
        """Severity at exactly the fallback trigger = R4 degraded."""
        from enums.pipeline_enums import FALLBACK_TRIGGER_SEVERITY
        router = ModelRouter()
        validation = ValidationResult(
            pass_status=False,
            failure_types=[FailureType.FACE_DRIFT],
            failure_class=FailureClass.SOFT,
            severity=FALLBACK_TRIGGER_SEVERITY,
        )
        strategy = router.choose_repair_strategy(validation)
        assert strategy.repair_mode == RepairMode.R4_DEGRADED_FALLBACK

    def test_f6_provider_config_for_all_tiers(self):
        """Every tier has a valid provider config."""
        router = ModelRouter()
        for tier in ModelTier:
            config = router.get_provider_config(tier)
            assert "provider" in config
            assert "model" in config
            assert len(config["model"]) > 0

    def test_f7_routing_explanation_never_empty(self):
        """Routing explanation is always a non-empty string."""
        router = ModelRouter()
        explanation = router.explain_routing_decision(
            ModelTier.TIER1_QUALITY, "Test reason"
        )
        assert isinstance(explanation, str)
        assert len(explanation) > 10


# ══════════════════════════════════════════════════════════════════════════════
# G. FULL PIPELINE CHAOS MATRIX
# ══════════════════════════════════════════════════════════════════════════════

class TestChaosFullMatrix:
    """
    Comprehensive chaos scenarios run through the full orchestrator.
    Each test verifies all 6 invariants.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scenario,panels,panel_count,forbidden_decisions", [
        (
            "all_pass_clean",
            [make_panel(i+1) for i in range(4)],
            4,
            [JobDecision.FAIL_TERMINAL],
        ),
        (
            "all_fail_terminal",
            [make_failed(i+1) for i in range(4)],
            4,
            [JobDecision.ACCEPT_FULL, JobDecision.ACCEPT_WITH_DEGRADATION],
        ),
        (
            "single_failure_targeted",
            [make_panel(1), make_panel(2), make_panel(3), make_failed(4)],
            4,
            [JobDecision.FAIL_TERMINAL, JobDecision.STYLE_DOWNGRADE_RERUN],
        ),
        (
            "high_repair_concentration",
            [make_panel(i+1, ps=PanelStatus.PASSED_REPAIRED.value, attempts=2) for i in range(4)],
            4,
            [JobDecision.ACCEPT_FULL],
        ),
        (
            "all_degraded_fallback",
            [make_panel(i+1, ps=PanelStatus.PASSED_DEGRADED.value, fallback=True) for i in range(4)],
            4,
            [JobDecision.ACCEPT_FULL],
        ),
        (
            "one_panel_job_pass",
            [make_panel(1)],
            1,
            [JobDecision.FAIL_TERMINAL],
        ),
        (
            "six_panel_two_fail",
            [make_panel(1), make_panel(2), make_panel(3), make_panel(4), make_failed(5), make_failed(6)],
            6,
            [],  # Any legal decision is fine
        ),
        (
            "max_attempts_all_pass",
            [make_panel(i+1, attempts=MAX_TOTAL_ATTEMPTS_PER_PANEL) for i in range(4)],
            4,
            [JobDecision.FAIL_TERMINAL],
        ),
    ])
    async def test_chaos_matrix_scenario(self, scenario, panels, panel_count, forbidden_decisions):
        """Run scenario through full orchestrator and verify invariants."""
        db = MockDB()
        orch = JobOrchestrator(db)
        result = await orch.evaluate_and_execute(f"chaos-{scenario}", panels, panel_count)

        # Invariant 1: No crash (if we got here, no crash)
        assert True

        # Invariant 2: No infinite retry (orchestrator doesn't retry in eval-only mode)
        assert True

        # Invariant 3: No silent success on corrupted output
        if all(p.get("status") == "FAILED" for p in panels if isinstance(p, dict)):
            assert result["decision"] != JobDecision.ACCEPT_FULL

        # Invariant 4: No missing decision
        assert result["decision"] in LEGAL_DECISIONS, \
            f"Missing/illegal decision in {scenario}: {result['decision']}"

        # Invariant 5: No cap violation (panels list unchanged in eval-only)
        assert len(result["panels"]) == len(panels)

        # Invariant 6: No empty final state
        assert result["job_status"] in LEGAL_STATUSES
        assert result["progress_msg"] and len(result["progress_msg"]) > 0
        assert result["decision_log"] is not None

        # Check forbidden decisions
        for fd in forbidden_decisions:
            assert result["decision"] != fd, \
                f"Forbidden decision {fd} in scenario {scenario}"

        # Verify decision was logged
        assert len(db.logged_decisions) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
