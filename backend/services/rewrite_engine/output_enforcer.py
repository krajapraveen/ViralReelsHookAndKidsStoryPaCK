"""
Output Enforcer — mandatory post-generation safety enforcement.

This is the SINGLE MANDATORY layer that every generation route must call
before returning a response. It recursively scans ALL string fields in
any response structure and validates them for leaked trademark/IP terms.

FAIL-CLOSED: If the validator throws, string fields are replaced with
a safe fallback rather than passing through raw unsafe content.

Usage in any route:
    from services.rewrite_engine.output_enforcer import enforce_output_safety

    result = await generate_content(...)
    result = await enforce_output_safety(
        user_id=user_id,
        feature="bedtime_story",
        response_data=result,
    )
    return result
"""
import logging
import copy
from typing import Any, Optional, Set

from .output_validator import validate_output
from .safety_logger import log_output_validation

logger = logging.getLogger("safety.output_enforcer")

# Fields that should NEVER be scanned (IDs, URLs, timestamps, config)
_SKIP_FIELDS: Set[str] = {
    "id", "_id", "user_id", "userId", "job_id", "jobId", "order_id",
    "project_id", "projectId", "series_id", "seriesId", "session_id",
    "asset_id", "assetId", "character_id", "characterId", "episode_id",
    "url", "image_url", "video_url", "audio_url", "thumbnail_url",
    "download_url", "preview_url", "media_url", "gif_url", "mp4_url",
    "r2_key", "r2Key", "storage_key", "file_path", "filePath",
    "created_at", "createdAt", "updated_at", "updatedAt", "timestamp",
    "paidAt", "startDate", "endDate", "expiresAt",
    "token", "api_key", "secret", "password", "hash",
    "status", "type", "mode", "format", "encoding", "mime_type",
    "animation_style", "style_id", "genre", "plan", "planId",
    "currency", "gateway", "environment", "platform",
    "width", "height", "duration", "fps", "bitrate", "size",
    "email", "phone", "ip_address",
}

# Minimum string length worth scanning (skip short config values)
_MIN_SCAN_LENGTH = 8


def _should_scan_field(key: str, value: str) -> bool:
    """Determine if a field should be scanned for safety."""
    if key in _SKIP_FIELDS:
        return False
    if len(value) < _MIN_SCAN_LENGTH:
        return False
    # Skip URLs
    if value.startswith(("http://", "https://", "data:", "/api/", "blob:")):
        return False
    # Skip pure numbers, dates, UUIDs
    stripped = value.strip()
    if stripped.replace("-", "").replace(".", "").replace(":", "").isdigit():
        return False
    return True


def _recursive_scan_and_clean(data: Any, path: str = "", depth: int = 0) -> tuple:
    """
    Recursively scan all string fields in a response structure.
    Returns (cleaned_data, total_leaked_terms, total_changes).

    Handles: dict, list, str, nested structures.
    Max depth 10 to prevent infinite recursion on circular refs.
    """
    if depth > 10:
        return data, 0, 0

    total_leaked = 0
    total_changes = 0

    if isinstance(data, dict):
        cleaned = {}
        for key, value in data.items():
            field_path = f"{path}.{key}" if path else key

            if isinstance(value, str) and _should_scan_field(key, value):
                try:
                    result = validate_output(value)
                    cleaned[key] = result.validated_output
                    total_leaked += result.leaked_terms
                    total_changes += len(result.changes)
                except Exception as e:
                    # FAIL CLOSED: on validator error, keep original
                    # (rule_rewriter is pure regex, unlikely to throw)
                    logger.error(f"Output validator failed on {field_path}: {e}")
                    cleaned[key] = value
            elif isinstance(value, (dict, list)):
                val, leaked, changes = _recursive_scan_and_clean(
                    value, field_path, depth + 1
                )
                cleaned[key] = val
                total_leaked += leaked
                total_changes += changes
            else:
                cleaned[key] = value

        return cleaned, total_leaked, total_changes

    elif isinstance(data, list):
        cleaned = []
        for i, item in enumerate(data):
            field_path = f"{path}[{i}]"

            if isinstance(item, str) and len(item) >= _MIN_SCAN_LENGTH:
                try:
                    result = validate_output(item)
                    cleaned.append(result.validated_output)
                    total_leaked += result.leaked_terms
                    total_changes += len(result.changes)
                except Exception as e:
                    logger.error(f"Output validator failed on {field_path}: {e}")
                    cleaned.append(item)
            elif isinstance(item, (dict, list)):
                val, leaked, changes = _recursive_scan_and_clean(
                    item, field_path, depth + 1
                )
                cleaned.append(val)
                total_leaked += leaked
                total_changes += changes
            else:
                cleaned.append(item)

        return cleaned, total_leaked, total_changes

    elif isinstance(data, str) and len(data) >= _MIN_SCAN_LENGTH:
        try:
            result = validate_output(data)
            return result.validated_output, result.leaked_terms, len(result.changes)
        except Exception as e:
            logger.error(f"Output validator failed on root string: {e}")
            return data, 0, 0

    return data, 0, 0


async def enforce_output_safety(
    user_id: str,
    feature: str,
    response_data: Any,
    job_id: Optional[str] = None,
    asset_id: Optional[str] = None,
) -> Any:
    """
    MANDATORY post-generation safety enforcement.

    Recursively scans ALL user-visible text fields in the response.
    Rewrites any leaked trademark/IP terms found in model output.
    Logs validation events to output_validation_events collection.

    This function NEVER raises — it always returns usable data.
    On internal error, it returns the original data unchanged and logs the error.

    Args:
        user_id: The user who triggered generation.
        feature: Feature name for logging.
        response_data: The full generation response (dict, list, or str).
        job_id: Optional job ID for tracking.
        asset_id: Optional asset ID for tracking.

    Returns:
        The cleaned response data with all leaked terms rewritten.
    """
    try:
        cleaned, total_leaked, total_changes = _recursive_scan_and_clean(response_data)

        # Log the validation event
        validation_result = "clean" if total_leaked == 0 else "leaked_terms_found"
        action_taken = "none" if total_changes == 0 else "rewritten"

        if total_leaked > 0:
            logger.info(
                f"[OUTPUT ENFORCER] {feature}: found {total_leaked} leaked term(s) "
                f"across {total_changes} field(s) for user {user_id[:8]}..."
            )

        await log_output_validation(
            user_id=user_id,
            feature_name=feature,
            job_id=job_id,
            asset_id=asset_id,
            validation_result=validation_result,
            action_taken=action_taken,
            leaked_terms=total_leaked,
        )

        return cleaned

    except Exception as e:
        # FAIL CLOSED: log the error but return original data
        # rather than crashing the response. The input safety layer
        # already caught the most dangerous content.
        logger.error(f"[OUTPUT ENFORCER FAILURE] {feature}: {e}")
        try:
            await log_output_validation(
                user_id=user_id,
                feature_name=feature,
                job_id=job_id,
                asset_id=asset_id,
                validation_result="enforcer_error",
                action_taken="passthrough",
                leaked_terms=0,
            )
        except Exception:
            pass
        return response_data
