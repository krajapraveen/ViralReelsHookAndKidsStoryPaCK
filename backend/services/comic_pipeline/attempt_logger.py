"""
Attempt Logger — Structured per-attempt logging for the comic pipeline.
Every generation, repair, and fallback attempt is persisted to `comic_panel_attempts`.
This is the observability backbone — without it, failures are invisible.
"""
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Dict
import logging

logger = logging.getLogger("creatorstudio.comic_pipeline.attempt_logger")


class AttemptLogger:
    """Persists every pipeline attempt to MongoDB for full auditability."""

    def __init__(self, db):
        self.db = db
        self.collection = db.comic_panel_attempts

    @staticmethod
    def hash_prompt(prompt: str) -> str:
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]

    async def log_attempt(
        self,
        job_id: str,
        panel_index: int,
        attempt_number: int,
        stage: str,
        attempt_type: str,
        model_tier: str,
        provider_model: str,
        prompt_text: str,
        latency_ms: int,
        accepted: bool,
        trigger_reason: Optional[List[str]] = None,
        repair_mode: Optional[str] = None,
        scores: Optional[Dict] = None,
        failure_types_in: Optional[List[str]] = None,
        failure_types_out: Optional[List[str]] = None,
        severity_in: float = 0.0,
        severity_out: float = 0.0,
        asset_url: Optional[str] = None,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        validator_summary: Optional[Dict] = None,
    ) -> str:
        """
        Log a single attempt. Returns the attempt document ID.
        Every field is explicit — no silent branches.
        """
        doc = {
            "job_id": job_id,
            "panel_index": panel_index,
            "attempt_number": attempt_number,
            "stage": stage,
            "attempt_type": attempt_type,
            "trigger_reason": trigger_reason or [],
            "input_context": {
                "model_tier": model_tier,
                "provider_model": provider_model,
                "prompt_hash": self.hash_prompt(prompt_text),
                "repair_mode": repair_mode,
            },
            "result": {
                "accepted": accepted,
                "asset_url": asset_url,
                "latency_ms": latency_ms,
                "error_type": error_type,
                "error_message": error_message,
            },
            "scores": scores or {},
            "diagnostics": {
                "failure_types_in": failure_types_in or [],
                "failure_types_out": failure_types_out or [],
                "severity_in": severity_in,
                "severity_out": severity_out,
                "validator_summary": validator_summary or {},
            },
            "accepted": accepted,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            await self.collection.insert_one(doc)
            logger.info(
                f"[ATTEMPT] job={job_id} panel={panel_index} attempt={attempt_number} "
                f"stage={stage} tier={model_tier} accepted={accepted} "
                f"latency={latency_ms}ms failures_in={failure_types_in or []}"
            )
        except Exception as e:
            logger.error(f"[ATTEMPT_LOG_FAIL] job={job_id} panel={panel_index}: {e}")

        return f"{job_id}_p{panel_index}_a{attempt_number}"

    async def get_panel_attempts(self, job_id: str, panel_index: int) -> list:
        """Get all attempts for a specific panel."""
        cursor = self.collection.find(
            {"job_id": job_id, "panel_index": panel_index},
            {"_id": 0}
        ).sort("attempt_number", 1)
        return await cursor.to_list(20)

    async def get_job_attempts(self, job_id: str) -> list:
        """Get all attempts for a job."""
        cursor = self.collection.find(
            {"job_id": job_id},
            {"_id": 0}
        ).sort([("panel_index", 1), ("attempt_number", 1)])
        return await cursor.to_list(100)

    async def get_attempt_stats(self, job_id: str) -> dict:
        """Compute aggregate stats for a job's attempts."""
        attempts = await self.get_job_attempts(job_id)
        if not attempts:
            return {"total_attempts": 0}

        total = len(attempts)
        accepted = sum(1 for a in attempts if a.get("accepted"))
        primary = [a for a in attempts if a.get("stage") == "PRIMARY"]
        repairs = [a for a in attempts if "REPAIR" in (a.get("stage") or "")]
        fallbacks = [a for a in attempts if a.get("stage") == "FALLBACK"]

        # Failure type frequency
        failure_freq = {}
        for a in attempts:
            for ft in a.get("diagnostics", {}).get("failure_types_in", []):
                failure_freq[ft] = failure_freq.get(ft, 0) + 1

        return {
            "total_attempts": total,
            "accepted": accepted,
            "rejected": total - accepted,
            "primary_attempts": len(primary),
            "primary_accepted": sum(1 for a in primary if a.get("accepted")),
            "repair_attempts": len(repairs),
            "repair_accepted": sum(1 for a in repairs if a.get("accepted")),
            "fallback_attempts": len(fallbacks),
            "fallback_accepted": sum(1 for a in fallbacks if a.get("accepted")),
            "failure_type_frequency": failure_freq,
            "avg_latency_ms": round(
                sum(a.get("result", {}).get("latency_ms", 0) for a in attempts) / total
            ) if total > 0 else 0,
        }
