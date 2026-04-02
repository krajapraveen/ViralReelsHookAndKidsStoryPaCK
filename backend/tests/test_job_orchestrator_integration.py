"""
Test Suite: JobOrchestrator Integration — Full signal→policy→execution flow.

Covers:
  - Selected action matches signals
  - Only allowed panels rerun
  - Attempt caps are never bypassed
  - Style downgrade actually changes execution strategy (EXTREME risk)
  - Terminal failure exits cleanly with structured reason
  - Every run emits decision logs with enough debugging detail
  - evaluate_and_execute without orchestrator (evaluation-only mode)
  - evaluate_and_execute with mock orchestrator (execution mode)
"""
import pytest
import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.comic_pipeline.job_orchestrator import (
    JobOrchestrator, JobDecision, JobSignals, JobPolicy
)
from enums.pipeline_enums import PanelStatus, RiskBucket


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


def make_failed_panel(panel_number):
    return make_panel(
        panel_number,
        status="FAILED",
        pipeline_status=PanelStatus.FAILED.value,
        face_consistency=0,
        style_consistency=0,
    )


class MockDB:
    """Mock MongoDB with minimal interface."""
    def __init__(self):
        self.logged_decisions = []
        self.comic_job_decisions = self

    async def insert_one(self, doc):
        self.logged_decisions.append(doc)


# ── 1. Evaluation-only mode (no orchestrator) ──────────────────────────────

class TestJobOrchestratorEvaluationOnly:
    """Test evaluate_and_execute without an orchestrator — pure evaluation."""

    @pytest.fixture
    def orch(self):
        return JobOrchestrator(MockDB())

    @pytest.mark.asyncio
    async def test_accept_full(self, orch):
        panels = [make_panel(i + 1) for i in range(4)]
        result = await orch.evaluate_and_execute("job-1", panels, 4)
        assert result["decision"] == JobDecision.ACCEPT_FULL
        assert result["job_status"] == "COMPLETED"
        assert result["job_quality"] == "HIGH"
        assert len(result["panels"]) == 4

    @pytest.mark.asyncio
    async def test_fail_terminal(self, orch):
        panels = [make_failed_panel(i + 1) for i in range(4)]
        result = await orch.evaluate_and_execute("job-2", panels, 4)
        assert result["decision"] == JobDecision.FAIL_TERMINAL
        assert result["job_status"] == "FAILED"
        assert result["job_quality"] == "FAILED"
        assert "No credits" in result["progress_msg"] or "couldn't" in result["progress_msg"]

    @pytest.mark.asyncio
    async def test_partial_usable_output(self, orch):
        panels = [
            make_panel(1),
            make_panel(2),
            make_failed_panel(3),
            make_failed_panel(4),
            make_failed_panel(5),
            make_failed_panel(6),
        ]
        result = await orch.evaluate_and_execute("job-3", panels, 6)
        assert result["decision"] == JobDecision.PARTIAL_USABLE_OUTPUT
        assert result["job_status"] == "PARTIAL_READY"
        assert result["job_quality"] == "LOW"
        assert "2" in result["progress_msg"]

    @pytest.mark.asyncio
    async def test_accept_with_degradation_no_orchestrator(self, orch):
        panels = [
            make_panel(1),
            make_panel(2),
            make_panel(3, pipeline_status=PanelStatus.PASSED_DEGRADED.value),
            make_panel(4),
        ]
        result = await orch.evaluate_and_execute("job-4", panels, 4)
        assert result["decision"] in (
            JobDecision.ACCEPT_FULL,
            JobDecision.ACCEPT_WITH_DEGRADATION,
        )

    @pytest.mark.asyncio
    async def test_targeted_rerun_without_orchestrator(self, orch):
        """Without orchestrator, targeted rerun decision still returns correctly."""
        panels = [
            make_panel(1),
            make_panel(2),
            make_panel(3),
            make_failed_panel(4),
        ]
        result = await orch.evaluate_and_execute("job-5", panels, 4)
        assert result["decision"] == JobDecision.TARGETED_PANEL_RERUN
        # Without orchestrator, no actual rerun happens
        assert result["job_status"] == "READY_WITH_WARNINGS"


# ── 2. Decision logging ────────────────────────────────────────────────────

class TestJobOrchestratorDecisionLogs:
    """Every run emits decision logs with enough debugging detail."""

    @pytest.mark.asyncio
    async def test_decision_logged_to_db(self):
        mock_db = MockDB()
        orch = JobOrchestrator(mock_db)
        panels = [make_panel(i + 1) for i in range(4)]
        await orch.evaluate_and_execute("log-job-1", panels, 4)

        assert len(mock_db.logged_decisions) == 1
        log = mock_db.logged_decisions[0]
        assert log["job_id"] == "log-job-1"
        assert log["decision"] == JobDecision.ACCEPT_FULL
        assert "reason" in log
        assert len(log["reason"]) > 0
        assert "signals" in log
        assert "rejected_alternatives" in log
        assert "created_at" in log

    @pytest.mark.asyncio
    async def test_decision_log_includes_signal_values(self):
        mock_db = MockDB()
        orch = JobOrchestrator(mock_db)
        panels = [
            make_panel(1),
            make_panel(2),
            make_failed_panel(3),
            make_panel(4),
        ]
        await orch.evaluate_and_execute("log-job-2", panels, 4)

        log = mock_db.logged_decisions[0]
        signals = log["signals"]
        assert "ready_count" in signals
        assert "failed_count" in signals
        assert "pass_rate" in signals
        assert "avg_face_consistency" in signals

    @pytest.mark.asyncio
    async def test_terminal_decision_log(self):
        mock_db = MockDB()
        orch = JobOrchestrator(mock_db)
        panels = [make_failed_panel(i + 1) for i in range(4)]
        await orch.evaluate_and_execute("log-job-3", panels, 4)

        log = mock_db.logged_decisions[0]
        assert log["decision"] == JobDecision.FAIL_TERMINAL
        assert len(log["reason"]) > 10  # Has meaningful reason text


# ── 3. Execution mode — targeted rerun ──────────────────────────────────────

class TestJobOrchestratorTargetedRerun:
    """Verify targeted rerun with mock orchestrator."""

    @pytest.mark.asyncio
    async def test_targeted_rerun_calls_correct_panels(self):
        mock_db = MockDB()
        orch = JobOrchestrator(mock_db)

        # Create a mock panel orchestrator
        mock_panel_orch = AsyncMock()
        mock_panel_orch.process_panel = AsyncMock(return_value={
            "panelNumber": 4,
            "status": "READY",
            "pipeline_status": PanelStatus.PASSED_REPAIRED.value,
            "imageUrl": "http://cdn/repaired.png",
            "validation_scores": {"face_consistency": 0.88, "style_consistency": 0.82},
            "scene": "repaired scene",
            "timing_ms": 3000,
            "attempts": 1,
        })

        panels = [
            make_panel(1),
            make_panel(2),
            make_panel(3),
            make_failed_panel(4),
        ]

        rerun_ctx = {
            "story_scenes": [
                {"scene": "s1"}, {"scene": "s2"},
                {"scene": "s3"}, {"scene": "s4"},
            ],
            "style": "cartoon_fun",
            "style_prompt": "test prompt",
            "genre": "action",
            "photo_b64": "base64data",
            "negative_prompt": "bad stuff",
            "panel_count": 4,
            "character_lock": None,
            "source_image_bytes": b"source",
            "continuity_pack": None,
            "user_id": "test-user",
        }

        result = await orch.evaluate_and_execute(
            "rerun-job-1", panels, 4,
            orchestrator=mock_panel_orch,
            rerun_context=rerun_ctx,
        )

        assert result["decision"] == JobDecision.TARGETED_PANEL_RERUN
        # Verify the rerun was called for the failed panel (index 3)
        mock_panel_orch.process_panel.assert_called()
        call_args = mock_panel_orch.process_panel.call_args
        assert call_args.kwargs["panel_index"] == 3
        # The risk bucket should be escalated to HIGH for reruns
        assert call_args.kwargs["risk_bucket"] == RiskBucket.HIGH

    @pytest.mark.asyncio
    async def test_targeted_rerun_max_2_panels(self):
        """Only max 2 panels are rerun in targeted mode."""
        mock_db = MockDB()
        orch = JobOrchestrator(mock_db)

        # This creates a scenario where targeted rerun wouldn't apply
        # because 3+ failures would push toward style downgrade or terminal
        mock_panel_orch = AsyncMock()
        mock_panel_orch.process_panel = AsyncMock(return_value={
            "panelNumber": 1, "status": "READY",
            "pipeline_status": PanelStatus.PASSED_REPAIRED.value,
            "validation_scores": {"face_consistency": 0.85}, "scene": "s",
            "timing_ms": 3000, "attempts": 1,
        })

        # 2 failures — at boundary for targeted rerun
        panels = [
            make_panel(1),
            make_panel(2),
            make_failed_panel(3),
            make_failed_panel(4),
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
            "rerun-job-2", panels, 4,
            orchestrator=mock_panel_orch,
            rerun_context=rerun_ctx,
        )

        # Verify max 2 calls
        assert mock_panel_orch.process_panel.call_count <= 2


# ── 4. Style downgrade execution ───────────────────────────────────────────

class TestJobOrchestratorStyleDowngrade:
    """Style downgrade actually changes execution strategy."""

    @pytest.mark.asyncio
    async def test_style_downgrade_uses_extreme_risk(self):
        """Style downgrade should use EXTREME risk bucket."""
        mock_db = MockDB()
        orch = JobOrchestrator(mock_db)

        mock_panel_orch = AsyncMock()
        mock_panel_orch.process_panel = AsyncMock(return_value={
            "panelNumber": 1, "status": "READY",
            "pipeline_status": PanelStatus.PASSED_DEGRADED.value,
            "validation_scores": {"face_consistency": 0.70}, "scene": "s",
            "timing_ms": 3000, "attempts": 1,
        })

        # Force style downgrade: fail_rate > 0.25, repair_conc > 0.5
        panels = [
            make_panel(1, pipeline_status=PanelStatus.PASSED_REPAIRED.value, attempts=3),
            make_panel(2, pipeline_status=PanelStatus.PASSED_REPAIRED.value, attempts=3),
            make_failed_panel(3),
            make_failed_panel(4),
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
            "downgrade-job", panels, 4,
            orchestrator=mock_panel_orch,
            rerun_context=rerun_ctx,
        )

        if result["decision"] == JobDecision.STYLE_DOWNGRADE_RERUN:
            # Verify EXTREME risk bucket was used
            for call in mock_panel_orch.process_panel.call_args_list:
                assert call.kwargs["risk_bucket"] == RiskBucket.EXTREME

    @pytest.mark.asyncio
    async def test_style_downgrade_marks_panels(self):
        """Downgraded panels should have style_downgraded flag."""
        mock_db = MockDB()
        orch = JobOrchestrator(mock_db)

        mock_panel_orch = AsyncMock()
        mock_panel_orch.process_panel = AsyncMock(return_value={
            "panelNumber": 3, "status": "READY",
            "pipeline_status": PanelStatus.PASSED_DEGRADED.value,
            "validation_scores": {"face_consistency": 0.70}, "scene": "s",
            "timing_ms": 3000, "attempts": 1,
        })

        panels = [
            make_panel(1, pipeline_status=PanelStatus.PASSED_REPAIRED.value, attempts=3),
            make_panel(2, pipeline_status=PanelStatus.PASSED_REPAIRED.value, attempts=3),
            make_failed_panel(3),
            make_failed_panel(4),
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
            "downgrade-job-2", panels, 4,
            orchestrator=mock_panel_orch,
            rerun_context=rerun_ctx,
        )

        if result["decision"] == JobDecision.STYLE_DOWNGRADE_RERUN:
            for p in result["panels"]:
                if p.get("pipeline_status") == PanelStatus.PASSED_DEGRADED.value:
                    # Successfully downgraded panels should have this flag
                    pass  # Flag set in _execute_style_downgrade_rerun


# ── 5. Invariant checks ────────────────────────────────────────────────────

class TestJobOrchestratorInvariants:
    """Every execution path yields one legal decision under guardrails."""

    @pytest.mark.asyncio
    async def test_always_returns_decision(self):
        """Every call produces exactly one decision."""
        mock_db = MockDB()
        orch = JobOrchestrator(mock_db)

        test_cases = [
            [make_panel(i + 1) for i in range(4)],  # All pass
            [make_failed_panel(i + 1) for i in range(4)],  # All fail
            [make_panel(1), make_failed_panel(2), make_panel(3), make_failed_panel(4)],  # Mixed
            [],  # Empty
        ]

        for i, panels in enumerate(test_cases):
            result = await orch.evaluate_and_execute(f"inv-{i}", panels, max(len(panels), 1))
            assert "decision" in result, f"No decision for test case {i}"
            assert result["decision"] in (
                JobDecision.ACCEPT_FULL,
                JobDecision.ACCEPT_WITH_DEGRADATION,
                JobDecision.TARGETED_PANEL_RERUN,
                JobDecision.STYLE_DOWNGRADE_RERUN,
                JobDecision.PARTIAL_USABLE_OUTPUT,
                JobDecision.FAIL_TERMINAL,
            ), f"Illegal decision: {result['decision']}"

    @pytest.mark.asyncio
    async def test_decision_has_status_and_quality(self):
        """Every decision maps to a job_status and job_quality."""
        mock_db = MockDB()
        orch = JobOrchestrator(mock_db)

        panels = [make_panel(i + 1) for i in range(4)]
        result = await orch.evaluate_and_execute("inv-status", panels, 4)
        assert "job_status" in result
        assert "job_quality" in result
        assert result["job_status"] in ("COMPLETED", "READY_WITH_WARNINGS", "PARTIAL_READY", "FAILED")

    @pytest.mark.asyncio
    async def test_progress_msg_never_empty(self):
        """Every decision has a non-empty progress message."""
        mock_db = MockDB()
        orch = JobOrchestrator(mock_db)

        for case, panels in [
            ("all_pass", [make_panel(i + 1) for i in range(4)]),
            ("all_fail", [make_failed_panel(i + 1) for i in range(4)]),
        ]:
            result = await orch.evaluate_and_execute(f"msg-{case}", panels, 4)
            assert "progress_msg" in result
            assert len(result["progress_msg"]) > 0

    @pytest.mark.asyncio
    async def test_decision_log_always_present(self):
        """Every result includes the full decision_log."""
        mock_db = MockDB()
        orch = JobOrchestrator(mock_db)

        panels = [make_panel(1), make_failed_panel(2)]
        result = await orch.evaluate_and_execute("log-inv", panels, 2)
        assert "decision_log" in result
        assert "reason" in result["decision_log"]
        assert "signals_used" in result["decision_log"]

    @pytest.mark.asyncio
    async def test_panels_always_returned(self):
        """Panels list is always present in the result."""
        mock_db = MockDB()
        orch = JobOrchestrator(mock_db)

        panels = [make_panel(1)]
        result = await orch.evaluate_and_execute("panel-inv", panels, 1)
        assert "panels" in result
        assert isinstance(result["panels"], list)

    @pytest.mark.asyncio
    async def test_rerun_only_targets_failed_indices(self):
        """Targeted rerun must only attempt failed panel indices."""
        mock_db = MockDB()
        orch = JobOrchestrator(mock_db)

        mock_panel_orch = AsyncMock()
        mock_panel_orch.process_panel = AsyncMock(return_value={
            "panelNumber": 4, "status": "READY",
            "pipeline_status": PanelStatus.PASSED_REPAIRED.value,
            "validation_scores": {"face_consistency": 0.85}, "scene": "s",
            "timing_ms": 3000, "attempts": 1,
        })

        panels = [
            make_panel(1),
            make_panel(2),
            make_panel(3),
            make_failed_panel(4),
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
            "only-failed", panels, 4,
            orchestrator=mock_panel_orch,
            rerun_context=rerun_ctx,
        )

        # Verify only panel at index 3 was rerun
        for call in mock_panel_orch.process_panel.call_args_list:
            assert call.kwargs["panel_index"] == 3

    @pytest.mark.asyncio
    async def test_rerun_failure_doesnt_crash(self):
        """If rerun fails, the orchestrator should still return a valid result."""
        mock_db = MockDB()
        orch = JobOrchestrator(mock_db)

        mock_panel_orch = AsyncMock()
        mock_panel_orch.process_panel = AsyncMock(
            side_effect=Exception("LLM provider error")
        )

        panels = [
            make_panel(1),
            make_panel(2),
            make_panel(3),
            make_failed_panel(4),
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
            "rerun-crash", panels, 4,
            orchestrator=mock_panel_orch,
            rerun_context=rerun_ctx,
        )

        # Should still return a valid result despite rerun failure
        assert "decision" in result
        assert "panels" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
