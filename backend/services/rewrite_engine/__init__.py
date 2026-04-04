"""
Safe Rewrite Engine — detect, rewrite, continue. Block only when necessary.

Usage in any route:
    from services.rewrite_engine import process_safety_check, validate_generation_output

    # PRE-GENERATION: sanitize user inputs
    safety = await process_safety_check(
        user_id=user_id,
        feature="bedtime_story",
        inputs={"theme": data.theme, "child_name": data.child_name}
    )
    if safety.blocked:
        raise HTTPException(status_code=400, detail=safety.block_reason)
    data.theme = safety.clean["theme"]
    data.child_name = safety.clean["child_name"]

    # POST-GENERATION: validate outputs
    validated = await validate_generation_output(
        user_id=user_id,
        feature="bedtime_story",
        outputs={"title": result["title"], "narration": result["narration"]},
        job_id=job_id,
    )
    result["title"] = validated["title"]
    result["narration"] = validated["narration"]
"""
from .rewrite_service import (
    safe_rewrite,
    safe_rewrite_fields,
    RewriteResult,
    process_safety_check,
    SafetyCheckResult,
    validate_generation_output,
    check_and_rewrite,
)
from .policy_engine import Decision, evaluate_policy
from .output_validator import validate_output, validate_and_clean
