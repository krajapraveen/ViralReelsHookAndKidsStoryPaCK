"""
Rewrite Service — Orchestrator for the Safe Rewrite Engine.
detect -> rewrite -> continue. Block only for genuinely dangerous content.

Main entry points:
  - process_safety_check()       — PRE-GENERATION: sanitize all user inputs
  - validate_generation_output() — POST-GENERATION: validate generated outputs
"""
import logging
from typing import Dict, Optional
from dataclasses import dataclass, field

from .rule_rewriter import rewrite_text, has_risky_terms
from .policy_engine import evaluate_policy_batch, Decision
from .safety_logger import log_safety_event, log_output_validation
from .output_validator import validate_output

logger = logging.getLogger("rewrite_engine")


@dataclass
class RewriteResult:
    """Result of a safe rewrite operation."""
    original_text: str
    rewritten_text: str
    was_rewritten: bool
    changes: list = field(default_factory=list)
    user_note: str = ""

    def to_dict(self) -> Dict:
        return {
            "original_text": self.original_text,
            "rewritten_text": self.rewritten_text,
            "was_rewritten": self.was_rewritten,
            "changes_count": len(self.changes),
            "user_note": self.user_note,
        }


@dataclass
class SafetyCheckResult:
    """Result of the full safety pipeline for one generation request."""
    blocked: bool = False
    block_reason: str = ""
    clean: Dict[str, str] = field(default_factory=dict)
    was_rewritten: bool = False
    user_note: str = ""
    rewrite_count: int = 0
    decision: str = "ALLOW"

    def to_dict(self) -> Dict:
        return {
            "blocked": self.blocked,
            "was_rewritten": self.was_rewritten,
            "rewrite_count": self.rewrite_count,
            "decision": self.decision,
            "user_note": self.user_note,
        }


def safe_rewrite(text: str) -> RewriteResult:
    """
    Core entry point: rewrite risky terms in text.
    NEVER raises an exception for trademark/copyright content.
    Always returns usable text.
    """
    if not text or not text.strip():
        return RewriteResult(
            original_text=text or "",
            rewritten_text=text or "",
            was_rewritten=False,
        )

    rewritten, changes = rewrite_text(text)

    was_rewritten = len(changes) > 0
    user_note = ""
    if was_rewritten:
        user_note = "We adjusted a few words to keep your content original and generation-ready."
        logger.info(
            f"[REWRITE] Rewrote {len(changes)} term(s): "
            + ", ".join(f"'{c['original']}' -> '{c['replacement']}'" for c in changes[:5])
        )

    return RewriteResult(
        original_text=text,
        rewritten_text=rewritten,
        was_rewritten=was_rewritten,
        changes=changes,
        user_note=user_note,
    )


def safe_rewrite_fields(**fields: str) -> Dict[str, RewriteResult]:
    """
    Rewrite multiple named text fields at once.
    Returns dict of field_name -> RewriteResult.
    """
    return {name: safe_rewrite(text) for name, text in fields.items()}


async def process_safety_check(
    user_id: str,
    feature: str,
    inputs: Dict[str, str],
    session_id: Optional[str] = None,
) -> SafetyCheckResult:
    """
    MAIN PRE-GENERATION ENTRY POINT.

    Call this at the top of every generation endpoint with all user-supplied text fields.
    Returns SafetyCheckResult with:
      - .blocked: True if content must be rejected
      - .block_reason: User-friendly message if blocked
      - .clean: Dict of field_name -> sanitized text (use these for generation)
      - .was_rewritten: True if any field was rewritten
      - .user_note: Soft notification for frontend

    Example:
        safety = await process_safety_check(
            user_id=user_id,
            feature="bedtime_story",
            inputs={"theme": data.theme, "child_name": data.child_name}
        )
        if safety.blocked:
            raise HTTPException(status_code=400, detail=safety.block_reason)
        data.theme = safety.clean["theme"]
    """
    # Step 1: Rewrite each field
    clean = {}
    all_changes = []
    trademark_flags = {}

    for field_name, text in inputs.items():
        if not text:
            clean[field_name] = text or ""
            trademark_flags[field_name] = False
            continue
        result = safe_rewrite(text)
        clean[field_name] = result.rewritten_text
        trademark_flags[field_name] = result.was_rewritten
        all_changes.extend(result.changes)

    # Step 2: Policy check (BLOCK only for genuinely dangerous content)
    policy = evaluate_policy_batch(inputs, trademark_flags)

    if policy.decision == Decision.BLOCK:
        # Log the block
        await log_safety_event(
            user_id=user_id,
            feature_name=feature,
            input_type="user_prompt",
            original_texts=inputs,
            decision="BLOCK",
            reason_codes=policy.reason_codes,
            triggered_rules=policy.triggered_rules,
            session_id=session_id,
        )
        return SafetyCheckResult(
            blocked=True,
            block_reason=policy.block_reason,
            clean=clean,
            decision="BLOCK",
        )

    # Step 3: Log the event (REWRITE or ALLOW)
    was_rewritten = len(all_changes) > 0
    user_note = ""
    if was_rewritten:
        user_note = "We adjusted a few words to keep your content original and generation-ready."

    await log_safety_event(
        user_id=user_id,
        feature_name=feature,
        input_type="user_prompt",
        original_texts=inputs,
        decision=policy.decision.value,
        reason_codes=policy.reason_codes,
        triggered_rules=policy.triggered_rules,
        rewrite_summary={
            "total_changes": len(all_changes),
            "changed_terms": [c["original"] for c in all_changes[:10]],
        },
        session_id=session_id,
    )

    return SafetyCheckResult(
        blocked=False,
        clean=clean,
        was_rewritten=was_rewritten,
        user_note=user_note,
        rewrite_count=len(all_changes),
        decision=policy.decision.value,
    )


async def validate_generation_output(
    user_id: str,
    feature: str,
    outputs: Dict[str, str],
    job_id: Optional[str] = None,
    asset_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, str]:
    """
    MAIN POST-GENERATION ENTRY POINT.

    Validates generated outputs for leaked trademark/IP terms.
    Returns dict of field_name -> validated (clean) text.

    Example:
        validated = await validate_generation_output(
            user_id=user_id,
            feature="bedtime_story",
            outputs={"title": result["title"], "narration": result["narration"]},
            job_id=job_id,
        )
        result["title"] = validated["title"]
    """
    clean_outputs = {}
    total_leaked = 0

    for field_name, text in outputs.items():
        if not text:
            clean_outputs[field_name] = text or ""
            continue
        result = validate_output(text)
        clean_outputs[field_name] = result.validated_output
        total_leaked += result.leaked_terms

    # Log validation event
    validation_result = "clean" if total_leaked == 0 else "leaked_terms_found"
    action_taken = "none" if total_leaked == 0 else "rewritten"

    await log_output_validation(
        user_id=user_id,
        feature_name=feature,
        job_id=job_id,
        asset_id=asset_id,
        validation_result=validation_result,
        action_taken=action_taken,
        leaked_terms=total_leaked,
        session_id=session_id,
    )

    return clean_outputs



async def check_and_rewrite(user_id: str, feature: str, data_obj, fields: list, session_id: Optional[str] = None) -> SafetyCheckResult:
    """
    ONE-LINER WIRING HELPER for route handlers.

    Extracts text from data_obj fields, runs full safety pipeline,
    mutates the data_obj fields in-place with cleaned text.

    Usage in any route handler:
        safety = await check_and_rewrite(user_id, "bedtime_story", data, ["theme", "child_name", "moral"])
        if safety.blocked:
            raise HTTPException(status_code=400, detail=safety.block_reason)
        # data.theme, data.child_name, data.moral are now cleaned.
    """
    inputs = {}
    for f in fields:
        val = getattr(data_obj, f, None)
        if val and isinstance(val, str) and val.strip():
            inputs[f] = val

    if not inputs:
        return SafetyCheckResult(clean={f: getattr(data_obj, f, "") or "" for f in fields})

    safety = await process_safety_check(
        user_id=user_id, feature=feature, inputs=inputs, session_id=session_id
    )

    if not safety.blocked:
        for f, clean_val in safety.clean.items():
            try:
                setattr(data_obj, f, clean_val)
            except (AttributeError, ValueError):
                pass

    return safety
