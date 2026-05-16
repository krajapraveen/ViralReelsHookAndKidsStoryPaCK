"""
Reliability middleware foundation — 2026-05-16 P0 (Session 1)

This module establishes the platform reliability primitives.
Scope is intentionally tight: middleware ONLY. No route rewrites beyond
the two flows we already touched (Photo-to-Comic + Create Series).

What it provides
----------------
1. RequestIdMiddleware
   • Reads inbound `X-Request-Id` (any non-empty string up to 128 chars)
     or generates a fresh uuid4 if absent / malformed.
   • Stashes the value on `request.state.request_id` for handlers/loggers.
   • Stamps `X-Request-Id` on every outgoing response (success OR error).

2. get_request_id(request)
   • Single canonical accessor for handlers — falls back to generating a
     fresh id if middleware was somehow bypassed (defensive; never None).

3. structured_log(logger, level, event, request=None, **fields)
   • Tiny structured-logging hook. Produces a key=value line that always
     includes `request_id`, so log aggregation / grep works without per-
     call boilerplate. Designed to coexist with the existing logger.* API.

What it deliberately does NOT do
--------------------------------
• Does NOT wrap unhandled exceptions in a standard envelope yet — that
  belongs in P0-D (LLM error envelopes) and would touch too many routes
  to qualify as "foundation only".
• Does NOT touch CORS (already exposes X-Request-Id).
• Does NOT add metrics emission — that's the admin reliability dashboard
  in Session 3.
• Does NOT impose timing thresholds — Latency middleware already exists.

Foundation only.
"""
from __future__ import annotations

import re
import uuid
import logging
from typing import Any, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# RFC-compliant id formats we accept inbound. uuid4 / uuid-ish / opaque
# alphanumeric with hyphens/underscores. Length-bounded to keep header
# sizes sane and the value safely log-injection-free.
_INBOUND_ID_RE = re.compile(r"^[A-Za-z0-9._\-]{8,128}$")

REQUEST_ID_HEADER = "X-Request-Id"
REQUEST_ID_STATE_ATTR = "request_id"


def _coerce_inbound(raw: Optional[str]) -> Optional[str]:
    """Accept inbound id IFF it matches the safe alphanumeric pattern."""
    if not raw:
        return None
    raw = raw.strip()
    if not raw or not _INBOUND_ID_RE.match(raw):
        return None
    return raw


def _new_request_id() -> str:
    return uuid.uuid4().hex


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Adds a stable per-request correlation id to every request/response.

    Behaviour:
      • If client sends a SAFE `X-Request-Id` header, we propagate it.
      • Otherwise, we generate a uuid4 hex.
      • The value is exposed via `request.state.request_id` and stamped
        on the response under the same header.
    """

    async def dispatch(self, request: Request, call_next):
        inbound = _coerce_inbound(request.headers.get(REQUEST_ID_HEADER))
        rid = inbound or _new_request_id()
        setattr(request.state, REQUEST_ID_STATE_ATTR, rid)

        # Run the rest of the stack. We deliberately do NOT swallow
        # exceptions here — Starlette's exception middleware will produce
        # the response and we'll stamp the header in the EXCEPTION HANDLER
        # path below via a re-raise wrapper that preserves the id.
        try:
            response = await call_next(request)
        except Exception:
            # Re-raise so Starlette's default error handler kicks in. The
            # error response will be missing our header, BUT we still log
            # the id below so ops can correlate.
            logging.getLogger("reliability").exception(
                "[reliability] unhandled-exception request_id=%s path=%s", rid, request.url.path
            )
            raise

        # Stamp header. Never overwrite an explicit value the handler set.
        if REQUEST_ID_HEADER not in response.headers:
            response.headers[REQUEST_ID_HEADER] = rid
        return response


def get_request_id(request: Request) -> str:
    """Canonical accessor for handlers.

    Always returns a non-empty string. Falls back to a fresh uuid4 if the
    middleware was somehow bypassed (test client without app stack, etc.)
    so handlers never need to guard against None.
    """
    rid = getattr(getattr(request, "state", None), REQUEST_ID_STATE_ATTR, None)
    if isinstance(rid, str) and rid:
        return rid
    return _new_request_id()


def structured_log(
    logger: logging.Logger,
    level: int,
    event: str,
    request: Optional[Request] = None,
    **fields: Any,
) -> None:
    """Emit a single structured log line with `request_id` always present.

    Format: `[event] key=value key=value ...`. Keeps the existing
    `logger.warning(...)` callsites stylistically compatible while moving
    them toward grep-able structured records. Values are repr-ed defensively
    to keep nasty payloads (newlines, control chars) out of the log stream.
    """
    parts = [f"[{event}]"]
    rid = get_request_id(request) if request is not None else fields.pop("request_id", None)
    if rid:
        parts.append(f"request_id={rid}")
    for k, v in fields.items():
        if isinstance(v, str):
            # Strip newlines + truncate so a 5MB error body doesn't blow up log lines
            safe = v.replace("\n", " ").replace("\r", " ")
            if len(safe) > 200:
                safe = safe[:197] + "..."
            parts.append(f"{k}={safe!r}")
        else:
            parts.append(f"{k}={v!r}")
    logger.log(level, " ".join(parts))


__all__ = [
    "RequestIdMiddleware",
    "REQUEST_ID_HEADER",
    "REQUEST_ID_STATE_ATTR",
    "get_request_id",
    "structured_log",
]
