"""
Safety Logger — persists safety events and output validation events to MongoDB.

Collections:
  - safety_events:            input-side (pre-generation) safety decisions
  - output_validation_events: output-side (post-generation) validation results
"""
import logging
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict

logger = logging.getLogger("safety.logger")

# Lazy DB reference — set once on first use
_db = None


def _get_db():
    global _db
    if _db is None:
        from shared import db as app_db
        _db = app_db
    return _db


async def log_safety_event(
    user_id: str,
    feature_name: str,
    input_type: str,
    original_texts: Dict[str, str],
    decision: str,
    reason_codes: list,
    triggered_rules: list,
    rewrite_summary: Optional[Dict] = None,
    session_id: Optional[str] = None,
):
    """
    Log a pre-generation safety event.
    """
    db = _get_db()
    try:
        # Hash original text for privacy — don't store raw user input
        text_hashes = {
            k: hashlib.sha256(v.encode()).hexdigest()[:16]
            for k, v in original_texts.items() if v
        }
        event = {
            "user_id": user_id,
            "session_id": session_id or "",
            "feature_name": feature_name,
            "input_type": input_type,
            "original_text_hashes": text_hashes,
            "decision": decision,
            "reason_codes": reason_codes,
            "triggered_rules": triggered_rules,
            "rewrite_summary": rewrite_summary or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await db.safety_events.insert_one(event)
        logger.debug(f"[SAFETY LOG] {feature_name} | {decision} | user={user_id[:8]}...")
    except Exception as e:
        # Logging must never break generation
        logger.error(f"Failed to log safety event: {e}")


async def log_output_validation(
    user_id: str,
    feature_name: str,
    job_id: Optional[str],
    asset_id: Optional[str],
    validation_result: str,
    action_taken: str,
    leaked_terms: int = 0,
    session_id: Optional[str] = None,
):
    """
    Log a post-generation output validation event.
    """
    db = _get_db()
    try:
        event = {
            "user_id": user_id,
            "session_id": session_id or "",
            "feature_name": feature_name,
            "job_id": job_id or "",
            "asset_id": asset_id or "",
            "validation_result": validation_result,
            "action_taken": action_taken,
            "leaked_terms": leaked_terms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await db.output_validation_events.insert_one(event)
        logger.debug(f"[OUTPUT LOG] {feature_name} | {validation_result} | {action_taken}")
    except Exception as e:
        logger.error(f"Failed to log output validation: {e}")
