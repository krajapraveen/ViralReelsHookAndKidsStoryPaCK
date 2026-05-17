"""
Structured validation error envelope — P1 2026-05-19 reliability sweep
========================================================================

FastAPI's default 422 response includes raw Pydantic error dicts that
can leak internal model names (e.g. `body -> credits -> int`) and the
exact field shapes our backend uses. The founder mandate is:

  • structured envelope with `code` + user-safe `message`
  • `request_id` present
  • no stack traces
  • no internal model names leaked

This module wires a single global handler on `RequestValidationError`
(invalid POST bodies, query params, path params, etc.) that returns the
canonical reliability envelope.

The handler is intentionally minimal — it does NOT touch HTTPException
(which routes raise themselves with their own structured envelopes) and
it does NOT touch CORS / request-id middleware (already handled).
"""

from __future__ import annotations

import logging
from typing import Any, Iterable

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("creatorstudio.validation_envelope")

# Friendly mapping from Pydantic error `type` codes to a sanitized
# `reason` shown to the client. The frontend uses this to render
# field-level helper text without seeing raw model internals.
_REASON_BY_TYPE: dict[str, str] = {
    "string_type": "Expected text value.",
    "string_pattern_mismatch": "Value format is invalid.",
    "string_too_short": "Value is too short.",
    "string_too_long": "Value is too long.",
    "literal_error": "Value is not one of the allowed options.",
    "enum": "Value is not one of the allowed options.",
    "missing": "This field is required.",
    "int_type": "Expected a whole number.",
    "int_parsing": "Expected a whole number.",
    "float_parsing": "Expected a number.",
    "greater_than": "Value is below the allowed minimum.",
    "less_than": "Value exceeds the allowed maximum.",
    "greater_than_equal": "Value is below the allowed minimum.",
    "less_than_equal": "Value exceeds the allowed maximum.",
    "value_error": "Value is invalid.",
    "type_error": "Value has the wrong type.",
    "list_type": "Expected a list of values.",
    "dict_type": "Expected an object.",
    "model_type": "Expected an object.",
    "json_invalid": "Body is not valid JSON.",
}


def _normalize_field_path(loc: Iterable[Any]) -> str:
    """Convert Pydantic's `('body', 'credits')` tuple into a
    user-facing dotted path. We strip the leading "body" / "query" /
    "path" segment because the client only needs the field name."""
    parts = [str(p) for p in loc if not isinstance(p, int)]
    if parts and parts[0] in ("body", "query", "path", "header", "form"):
        parts = parts[1:]
    return ".".join(parts) if parts else "request"


def _sanitize_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map Pydantic error dicts onto the structured envelope shape.
    Specifically strips:
      • `ctx` (may contain raw regex / Pydantic internal state)
      • `input` (raw user input — could echo PII or sensitive data)
      • `url` (links to pydantic docs internals)
      • the full `msg` text (often references Python type names)
    """
    out: list[dict[str, Any]] = []
    for err in errors[:25]:  # cap so an attacker can't blow up the body
        etype = str(err.get("type", "value_error"))
        out.append({
            "field": _normalize_field_path(err.get("loc", [])),
            "code": etype,
            "reason": _REASON_BY_TYPE.get(etype, "Value is invalid."),
        })
    return out


def _get_request_id(request: Request) -> str | None:
    try:
        from middleware.reliability import get_request_id  # local import to avoid cycles
        return get_request_id(request)
    except Exception:  # noqa: BLE001
        return None


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Single canonical handler for invalid request payloads."""
    request_id = _get_request_id(request)
    errors = _sanitize_errors(list(exc.errors()))

    # Structured log — full error context for ops, never returned to client.
    try:
        logger.warning(
            "validation_error path=%s request_id=%s field_errors=%s",
            request.url.path,
            request_id,
            errors,
        )
    except Exception:  # noqa: BLE001
        pass

    envelope = {
        "detail": {
            "code": "VALIDATION_ERROR",
            "message": "One or more fields are invalid. Please check your input and try again.",
            "request_id": request_id,
            "field_errors": errors,
            "retryable": False,
        },
        # Mirror at top level for legacy frontend code paths.
        "code": "VALIDATION_ERROR",
        "request_id": request_id,
    }

    headers: dict[str, str] = {}
    if request_id:
        headers["X-Request-Id"] = request_id

    return JSONResponse(status_code=422, content=envelope, headers=headers)


def install_validation_envelope(app) -> None:
    """One-line wiring helper called from server.py."""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
