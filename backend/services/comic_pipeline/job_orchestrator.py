"""
Job Orchestrator — Job-level policy engine for comic strip quality.
Split into three concerns:
  1. SIGNALS: panel pass/fail, face consistency, narrative coherence, latency, cost, fallback exhaustion
  2. POLICY: accept / targeted rerun / style downgrade / partial finalize / fail
  3. EXECUTION: call panel orchestrator, rerun selected panels, finalize output

Decision outcomes (no vague states):
  - ACCEPT_FULL: all panels passed, quality is high
  - ACCEPT_WITH_DEGRADATION: some panels degraded but job is coherent
  - TARGETED_PANEL_RERUN: specific panels need re-generation
  - STYLE_DOWNGRADE_RERUN: re-plan with simpler visual ambition
  - PARTIAL_USABLE_OUTPUT: deliver what we have, mark degraded
  - FAIL_TERMINAL: unrecoverable, refund credits
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from enums.pipeline_enums import (
    PanelStatus, RiskBucket, ModelTier,
    PASS_THRESHOLDS, FALLBACK_THRESHOLDS,
)

logger = logging.getLogger("creatorstudio.comic_pipeline.job_orchestrator")


# ══════════════════════════════════════════════════════════════════════════════
# DECISION OUTCOMES
# ══════════════════════════════════════════════════════════════════════════════

class JobDecision:
    ACCEPT_FULL = "ACCEPT_FULL"
    ACCEPT_WITH_DEGRADATION = "ACCEPT_WITH_DEGRADATION"
    TARGETED_PANEL_RERUN = "TARGETED_PANEL_RERUN"
    STYLE_DOWNGRADE_RERUN = "STYLE_DOWNGRADE_RERUN"
    PARTIAL_USABLE_OUTPUT = "PARTIAL_USABLE_OUTPUT"
    FAIL_TERMINAL = "FAIL_TERMINAL"


# ══════════════════════════════════════════════════════════════════════════════
# 1. SIGNALS — Extract structured metrics from panel results
# ══════════════════════════════════════════════════════════════════════════════

class JobSignals:
    """Extracts structured signals from a list of panel results."""

    def __init__(self, panels: List[Dict], panel_count: int):
        self.panels = panels
        self.panel_count = panel_count

    def compute(self) -> Dict:
        """Compute all job-level signals from panel data."""
        ready = [p for p in self.panels if isinstance(p, dict) and p.get("status") == "READY"]
        failed = [p for p in self.panels if isinstance(p, dict) and p.get("status") == "FAILED"]
        degraded = [p for p in self.panels if isinstance(p, dict) and p.get("pipeline_status") == PanelStatus.PASSED_DEGRADED.value]
        repaired = [p for p in self.panels if isinstance(p, dict) and p.get("pipeline_status") == PanelStatus.PASSED_REPAIRED.value]
        primary_pass = [p for p in self.panels if isinstance(p, dict) and p.get("pipeline_status") == PanelStatus.PASSED.value]

        total = len(self.panels)

        # Face consistency across ready panels
        face_scores = []
        style_scores = []
        for p in ready:
            vs = p.get("validation_scores", {})
            if vs.get("face_consistency", 0) > 0:
                face_scores.append(vs["face_consistency"])
            if vs.get("style_consistency", 0) > 0:
                style_scores.append(vs["style_consistency"])

        avg_face = (sum(face_scores) / len(face_scores)) if face_scores else 0
        avg_style = (sum(style_scores) / len(style_scores)) if style_scores else 0

        # Story coverage: did all required beats appear?
        panels_with_scene = sum(1 for p in self.panels if isinstance(p, dict) and p.get("scene"))
        story_coverage = panels_with_scene / self.panel_count if self.panel_count > 0 else 0

        # Narrative coherence: are panels sequential?
        sequential = all(
            isinstance(p, dict) and p.get("panelNumber") == i + 1
            for i, p in enumerate(self.panels)
        )

        # Character preservation: face consistency trend
        char_preserved = avg_face >= PASS_THRESHOLDS["face_consistency"] if face_scores else True

        # Repair concentration: ratio of panels that needed rescue
        repair_concentration = (len(repaired) + len(degraded)) / total if total > 0 else 0

        # Fallback contamination: ratio of panels from degraded path
        fallback_contamination = len(degraded) / total if total > 0 else 0

        # Total attempts across all panels
        total_attempts = sum(p.get("attempts", 1) for p in self.panels if isinstance(p, dict))
        expected_attempts = total  # 1 per panel ideal
        cost_burn_ratio = total_attempts / expected_attempts if expected_attempts > 0 else 1.0

        # Latency
        panel_timings = [p.get("timing_ms", 0) for p in self.panels if isinstance(p, dict) and p.get("timing_ms")]
        total_latency_ms = sum(panel_timings)
        avg_latency_ms = (total_latency_ms / len(panel_timings)) if panel_timings else 0

        # Failed panel indices (for targeted rerun)
        failed_indices = [p.get("panelNumber", 0) - 1 for p in failed if isinstance(p, dict)]

        return {
            "total_panels": total,
            "ready_count": len(ready),
            "failed_count": len(failed),
            "degraded_count": len(degraded),
            "repaired_count": len(repaired),
            "primary_pass_count": len(primary_pass),
            "pass_rate": len(ready) / total if total > 0 else 0,
            "fail_rate": len(failed) / total if total > 0 else 0,
            "avg_face_consistency": round(avg_face, 4),
            "avg_style_consistency": round(avg_style, 4),
            "story_coverage": round(story_coverage, 3),
            "sequential": sequential,
            "character_preserved": char_preserved,
            "repair_concentration": round(repair_concentration, 3),
            "fallback_contamination": round(fallback_contamination, 3),
            "cost_burn_ratio": round(cost_burn_ratio, 2),
            "total_attempts": total_attempts,
            "total_latency_ms": total_latency_ms,
            "avg_latency_ms": round(avg_latency_ms),
            "failed_indices": failed_indices,
        }


# ══════════════════════════════════════════════════════════════════════════════
# 2. POLICY — Decide what to do based on signals
# ══════════════════════════════════════════════════════════════════════════════

class JobPolicy:
    """
    Decides the job-level action based on extracted signals.
    Every decision logs why it was made and why alternatives were rejected.
    """

    # Policy thresholds
    FACE_CONSISTENCY_FLOOR = 0.65
    STYLE_CONSISTENCY_FLOOR = 0.65
    STORY_COVERAGE_FLOOR = 0.75
    REPAIR_CONCENTRATION_CEILING = 0.5
    FALLBACK_CONTAMINATION_CEILING = 0.5
    COST_BURN_CEILING = 2.5
    FAIL_RATE_TERMINAL = 0.75
    FAIL_RATE_TARGETED_RERUN = 0.25
    LATENCY_BUDGET_MS = 300_000  # 5 minutes

    def evaluate(self, signals: Dict) -> Dict:
        """
        Evaluate signals and produce a decision with full audit trail.
        Returns: {decision, reason, rejected_alternatives, signals_used, threshold_crossings}
        """
        crossings = []
        decision = None
        reason = ""
        rejected = []

        fail_rate = signals["fail_rate"]
        ready_count = signals["ready_count"]
        total = signals["total_panels"]

        # ── FAIL_TERMINAL: unrecoverable ──
        if fail_rate >= self.FAIL_RATE_TERMINAL:
            decision = JobDecision.FAIL_TERMINAL
            reason = f"Fail rate {fail_rate:.0%} >= {self.FAIL_RATE_TERMINAL:.0%}. Too many panels failed to recover."
            crossings.append({"threshold": "FAIL_RATE_TERMINAL", "value": fail_rate, "limit": self.FAIL_RATE_TERMINAL})
            rejected.append({"action": "STYLE_DOWNGRADE_RERUN", "reason": "Fail rate too high, style downgrade unlikely to help"})
            return self._build_result(decision, reason, rejected, signals, crossings)

        # ── ACCEPT_FULL: everything passed cleanly ──
        if (signals["failed_count"] == 0 and
            signals["repair_concentration"] < 0.15 and
            signals["fallback_contamination"] == 0 and
            signals["story_coverage"] >= 1.0 and
            signals["character_preserved"]):
            decision = JobDecision.ACCEPT_FULL
            reason = "All panels passed. Low repair concentration. Full story coverage. Character preserved."
            return self._build_result(decision, reason, rejected, signals, crossings)

        # ── TARGETED_PANEL_RERUN: few panels failed ──
        if 0 < fail_rate <= self.FAIL_RATE_TARGETED_RERUN and signals["failed_count"] <= 2:
            decision = JobDecision.TARGETED_PANEL_RERUN
            reason = f"{signals['failed_count']} panel(s) failed. Targeted rerun is efficient."
            rejected.append({"action": "STYLE_DOWNGRADE_RERUN", "reason": "Only minor failures, style downgrade would be overkill"})
            rejected.append({"action": "FAIL_TERMINAL", "reason": f"Fail rate {fail_rate:.0%} is below terminal threshold"})
            return self._build_result(decision, reason, rejected, signals, crossings)

        # ── STYLE_DOWNGRADE_RERUN: moderate failure + quality issues ──
        if (fail_rate > self.FAIL_RATE_TARGETED_RERUN and
            fail_rate < self.FAIL_RATE_TERMINAL and
            signals["repair_concentration"] > self.REPAIR_CONCENTRATION_CEILING):
            decision = JobDecision.STYLE_DOWNGRADE_RERUN
            reason = (f"Fail rate {fail_rate:.0%} with repair concentration {signals['repair_concentration']:.0%}. "
                     f"Style downgrade needed to stabilize output.")
            crossings.append({"threshold": "REPAIR_CONCENTRATION", "value": signals["repair_concentration"],
                            "limit": self.REPAIR_CONCENTRATION_CEILING})
            rejected.append({"action": "TARGETED_PANEL_RERUN", "reason": "Too many panels affected for targeted repair"})
            rejected.append({"action": "ACCEPT_WITH_DEGRADATION", "reason": "Repair concentration too high to accept"})
            return self._build_result(decision, reason, rejected, signals, crossings)

        # ── ACCEPT_WITH_DEGRADATION: usable but not perfect ──
        if (ready_count > total / 2 and
            signals["story_coverage"] >= self.STORY_COVERAGE_FLOOR and
            signals["fallback_contamination"] < self.FALLBACK_CONTAMINATION_CEILING):
            decision = JobDecision.ACCEPT_WITH_DEGRADATION
            reason = (f"{ready_count}/{total} panels ready. Story coverage {signals['story_coverage']:.0%}. "
                     f"Fallback contamination {signals['fallback_contamination']:.0%}.")

            # Check quality floors
            if signals["avg_face_consistency"] > 0 and signals["avg_face_consistency"] < self.FACE_CONSISTENCY_FLOOR:
                crossings.append({"threshold": "FACE_CONSISTENCY", "value": signals["avg_face_consistency"],
                                "limit": self.FACE_CONSISTENCY_FLOOR})
            if signals["avg_style_consistency"] > 0 and signals["avg_style_consistency"] < self.STYLE_CONSISTENCY_FLOOR:
                crossings.append({"threshold": "STYLE_CONSISTENCY", "value": signals["avg_style_consistency"],
                                "limit": self.STYLE_CONSISTENCY_FLOOR})

            rejected.append({"action": "FAIL_TERMINAL", "reason": "More than half the panels are usable"})
            return self._build_result(decision, reason, rejected, signals, crossings)

        # ── PARTIAL_USABLE_OUTPUT: deliver what we have ──
        if ready_count > 0:
            decision = JobDecision.PARTIAL_USABLE_OUTPUT
            reason = f"Only {ready_count}/{total} panels usable. Delivering partial result."
            rejected.append({"action": "ACCEPT_FULL", "reason": "Too many failures for full acceptance"})
            rejected.append({"action": "STYLE_DOWNGRADE_RERUN", "reason": "Would add too much latency for uncertain gain"})
            return self._build_result(decision, reason, rejected, signals, crossings)

        # ── Absolute fallback ──
        decision = JobDecision.FAIL_TERMINAL
        reason = "No usable panels produced. All recovery paths exhausted."
        return self._build_result(decision, reason, rejected, signals, crossings)

    def _build_result(self, decision, reason, rejected, signals, crossings):
        return {
            "decision": decision,
            "reason": reason,
            "rejected_alternatives": rejected,
            "signals_used": signals,
            "threshold_crossings": crossings,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ══════════════════════════════════════════════════════════════════════════════
# 3. EXECUTION — Apply the policy decision
# ══════════════════════════════════════════════════════════════════════════════

class JobOrchestrator:
    """
    Applies job-level policy decisions to the comic pipeline.
    Coordinates with PanelOrchestrator for targeted reruns.
    """

    def __init__(self, db):
        self.db = db
        self.policy = JobPolicy()

    async def evaluate_and_execute(
        self,
        job_id: str,
        panels: List[Dict],
        panel_count: int,
        orchestrator=None,
        rerun_context: Optional[Dict] = None,
    ) -> Dict:
        """
        Evaluate job quality and decide next action.
        Returns: {decision, panels (updated), job_quality, decision_log}
        """
        # Extract signals
        signal_extractor = JobSignals(panels, panel_count)
        signals = signal_extractor.compute()

        # Apply policy
        policy_result = self.policy.evaluate(signals)
        decision = policy_result["decision"]

        logger.info(
            f"[JOB_POLICY] job={job_id} decision={decision} "
            f"ready={signals['ready_count']}/{signals['total_panels']} "
            f"face={signals['avg_face_consistency']:.3f} "
            f"repair_conc={signals['repair_concentration']:.2f}"
        )

        # Log the decision
        await self._log_decision(job_id, policy_result)

        # Execute based on decision
        result = {
            "decision": decision,
            "panels": panels,
            "decision_log": policy_result,
        }

        if decision == JobDecision.ACCEPT_FULL:
            result["job_status"] = "COMPLETED"
            result["job_quality"] = "HIGH"
            result["progress_msg"] = "Your comic is ready!"

        elif decision == JobDecision.ACCEPT_WITH_DEGRADATION:
            result["job_status"] = "READY_WITH_WARNINGS"
            result["job_quality"] = "MEDIUM"
            result["progress_msg"] = "Your comic is ready!"

        elif decision == JobDecision.TARGETED_PANEL_RERUN:
            # Execute targeted rerun if orchestrator provided
            if orchestrator and rerun_context:
                updated_panels = await self._execute_targeted_rerun(
                    job_id, panels, signals["failed_indices"],
                    orchestrator, rerun_context
                )
                result["panels"] = updated_panels
                # Re-evaluate after rerun
                new_signals = JobSignals(updated_panels, panel_count).compute()
                if new_signals["failed_count"] == 0:
                    result["job_status"] = "COMPLETED"
                    result["job_quality"] = "MEDIUM"
                    result["progress_msg"] = "Your comic is ready!"
                else:
                    result["job_status"] = "READY_WITH_WARNINGS"
                    result["job_quality"] = "LOW"
                    result["progress_msg"] = "Your comic is ready!"
            else:
                result["job_status"] = "READY_WITH_WARNINGS"
                result["job_quality"] = "MEDIUM"
                result["progress_msg"] = "Your comic is ready!"

        elif decision == JobDecision.STYLE_DOWNGRADE_RERUN:
            # Execute style downgrade rerun if orchestrator provided
            if orchestrator and rerun_context:
                updated_panels = await self._execute_style_downgrade_rerun(
                    job_id, panels, signals["failed_indices"],
                    orchestrator, rerun_context
                )
                result["panels"] = updated_panels
                new_signals = JobSignals(updated_panels, panel_count).compute()
                if new_signals["ready_count"] > 0:
                    result["job_status"] = "READY_WITH_WARNINGS"
                    result["job_quality"] = "LOW"
                    result["progress_msg"] = "Your comic is ready!"
                else:
                    result["job_status"] = "FAILED"
                    result["job_quality"] = "FAILED"
                    result["progress_msg"] = "We couldn't create your comic this time. No credits were charged."
            else:
                result["job_status"] = "READY_WITH_WARNINGS"
                result["job_quality"] = "LOW"
                result["progress_msg"] = "Your comic is ready!"

        elif decision == JobDecision.PARTIAL_USABLE_OUTPUT:
            ready_count = signals["ready_count"]
            result["job_status"] = "PARTIAL_READY"
            result["job_quality"] = "LOW"
            result["progress_msg"] = f"Your comic is ready with {ready_count} optimized panels."

        elif decision == JobDecision.FAIL_TERMINAL:
            result["job_status"] = "FAILED"
            result["job_quality"] = "FAILED"
            result["progress_msg"] = "We couldn't create your comic this time. No credits were charged."

        return result

    async def _execute_targeted_rerun(
        self, job_id, panels, failed_indices, orchestrator, ctx
    ) -> List[Dict]:
        """Rerun only the specific failed panels."""
        logger.info(f"[JOB_EXEC] Targeted rerun for panels {[i+1 for i in failed_indices]} in job {job_id}")

        for idx in failed_indices[:2]:  # Max 2 targeted reruns
            if idx >= len(ctx.get("story_scenes", [])):
                continue
            try:
                result = await orchestrator.process_panel(
                    job_id=job_id,
                    panel_index=idx,
                    scene=ctx["story_scenes"][idx],
                    style_name=ctx["style"],
                    style_prompt=ctx["style_prompt"],
                    genre=ctx["genre"],
                    photo_b64=ctx["photo_b64"],
                    negative_prompt=ctx["negative_prompt"],
                    panel_count=ctx["panel_count"],
                    risk_bucket=RiskBucket.HIGH,  # Escalate risk for rerun
                    character_lock=ctx.get("character_lock"),
                    source_image_bytes=ctx.get("source_image_bytes"),
                    approved_panel_bytes=ctx.get("continuity_pack"),
                    user_id=ctx.get("user_id", ""),
                )
                if result.get("status") == "READY":
                    panels[idx] = result
                    logger.info(f"[JOB_EXEC] Targeted rerun succeeded for panel {idx+1}")
            except Exception as e:
                logger.warning(f"[JOB_EXEC] Targeted rerun failed for panel {idx+1}: {e}")

        return panels

    async def _execute_style_downgrade_rerun(
        self, job_id, panels, failed_indices, orchestrator, ctx
    ) -> List[Dict]:
        """Rerun failed panels with EXTREME risk bucket (forces Tier 2+ and simplified prompts)."""
        logger.info(f"[JOB_EXEC] Style downgrade rerun for {len(failed_indices)} panels in job {job_id}")

        for idx in failed_indices:
            if idx >= len(ctx.get("story_scenes", [])):
                continue
            try:
                result = await orchestrator.process_panel(
                    job_id=job_id,
                    panel_index=idx,
                    scene=ctx["story_scenes"][idx],
                    style_name=ctx["style"],
                    style_prompt=ctx["style_prompt"],
                    genre=ctx["genre"],
                    photo_b64=ctx["photo_b64"],
                    negative_prompt=ctx["negative_prompt"],
                    panel_count=ctx["panel_count"],
                    risk_bucket=RiskBucket.EXTREME,  # Force degraded path
                    character_lock=ctx.get("character_lock"),
                    source_image_bytes=ctx.get("source_image_bytes"),
                    approved_panel_bytes=ctx.get("continuity_pack"),
                    user_id=ctx.get("user_id", ""),
                )
                if result.get("status") == "READY":
                    panels[idx] = result
                    panels[idx]["style_downgraded"] = True
                    logger.info(f"[JOB_EXEC] Style downgrade succeeded for panel {idx+1}")
            except Exception as e:
                logger.warning(f"[JOB_EXEC] Style downgrade failed for panel {idx+1}: {e}")

        return panels

    async def _log_decision(self, job_id: str, policy_result: Dict):
        """Persist the decision audit trail."""
        try:
            await self.db.comic_job_decisions.insert_one({
                "job_id": job_id,
                "decision": policy_result["decision"],
                "reason": policy_result["reason"],
                "rejected_alternatives": policy_result["rejected_alternatives"],
                "threshold_crossings": policy_result["threshold_crossings"],
                "signals": policy_result["signals_used"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as e:
            logger.warning(f"[JOB_DECISION_LOG] Failed to log decision for {job_id}: {e}")
