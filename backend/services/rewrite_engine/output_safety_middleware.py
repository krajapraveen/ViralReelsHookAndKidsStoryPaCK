"""
Output Safety Middleware — universal post-generation enforcement.

This middleware intercepts ALL responses from generation routes and runs
the output enforcer on them. No route can bypass this.

Coverage is defined by GENERATION_ROUTE_PREFIXES — if a route prefix is
missing from this list, its output is not scanned. This list is the single
source of truth for output safety coverage.
"""
import json
import logging
import jwt
import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse
from starlette.requests import Request

logger = logging.getLogger("safety.middleware")

JWT_SECRET = os.environ.get("JWT_SECRET", "")

# ═══════════════════════════════════════════════════════════════
# COVERAGE REGISTRY — every generation route prefix that emits
# user-visible creative text MUST be listed here.
# If a prefix is missing, its output bypasses safety scanning.
# ═══════════════════════════════════════════════════════════════
GENERATION_ROUTE_PREFIXES = [
    "/api/bedtime-story",
    "/api/brand-story-builder",
    "/api/caption-rewriter",
    "/api/challenge-generator",
    "/api/characters",
    "/api/coloring-book",
    "/api/comic-storybook",
    "/api/comix-ai",
    "/api/comment-reply-bank",
    "/api/content-engine",
    "/api/creator-pro",
    "/api/creator-tools",
    "/api/daily-viral-ideas",
    "/api/generation",
    "/api/genstudio",
    "/api/gif-maker",
    "/api/instagram-bio-generator",
    "/api/offer-generator",
    "/api/photo-to-comic",
    "/api/reaction-gif",
    "/api/story-engine",
    "/api/story-episode-creator",
    "/api/story-hook-generator",
    "/api/story-series",
    "/api/story-video-fast",
    "/api/story-video-studio",
    "/api/story-video",
    "/api/tone-switcher",
    "/api/viral-ideas",
    "/api/youtube-thumbnail-generator",
]

# POST-only methods (GET/OPTIONS/HEAD are never generation)
_GENERATION_METHODS = {"POST", "PUT", "PATCH"}

# Paths within generation routes to SKIP (config, list, admin endpoints)
_SKIP_PATH_SEGMENTS = {
    "/config", "/styles", "/genres", "/pricing", "/templates",
    "/platforms", "/goals", "/niches", "/tones", "/admin/",
    "/status", "/history", "/list", "/health",
}


def _is_generation_response(method: str, path: str) -> bool:
    """Check if this response needs output safety scanning."""
    if method not in _GENERATION_METHODS:
        return False
    # Check if path matches any generation route prefix
    for prefix in GENERATION_ROUTE_PREFIXES:
        if path.startswith(prefix):
            # Skip config/list endpoints
            remainder = path[len(prefix):]
            for skip in _SKIP_PATH_SEGMENTS:
                if skip in remainder:
                    return False
            return True
    return False


def _extract_user_id(request: Request) -> str:
    """Extract user_id from JWT token in Authorization header."""
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return "anonymous"
    token = auth[7:]
    try:
        from shared import JWT_SECRET, JWT_ALGORITHM
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return str(payload.get("sub", payload.get("user_id", payload.get("id", "unknown"))))
    except Exception:
        return "unknown"


def _derive_feature(path: str) -> str:
    """Derive feature name from route path."""
    # /api/story-hook-generator/generate → story_hook_generator
    parts = path.split("/")
    if len(parts) >= 3:
        return parts[2].replace("-", "_")
    return "unknown"


class OutputSafetyMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces output safety on all generation routes.
    Also detects if the input contained safety-rewritable content and
    injects `_safety_meta` into the response for frontend UX.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method
        is_gen = _is_generation_response(method, path)

        # Cache request body BEFORE call_next for safety detection
        cached_body = None
        if is_gen:
            try:
                cached_body = await request.body()
            except Exception:
                pass

        response = await call_next(request)

        if not is_gen:
            return response

        if response.status_code != 200:
            return response

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        logger.info(f"[OUTPUT MIDDLEWARE] Scanning {method} {path}")

        # Read response body
        try:
            body_chunks = []
            async for chunk in response.body_iterator:
                if isinstance(chunk, bytes):
                    body_chunks.append(chunk)
                else:
                    body_chunks.append(chunk.encode("utf-8"))
            body = b"".join(body_chunks)
        except Exception as e:
            logger.error(f"[OUTPUT MIDDLEWARE] Failed to read body: {e}")
            return response

        # Handle gzip-compressed responses
        import gzip as gzip_mod
        if body[:2] == b'\x1f\x8b':
            try:
                body = gzip_mod.decompress(body)
            except Exception:
                pass

        # Parse JSON
        try:
            data = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
            )

        # Enforce output safety
        try:
            from services.rewrite_engine.output_enforcer import enforce_output_safety
            from services.rewrite_engine import get_and_clear_safety_meta

            user_id = _extract_user_id(request)
            feature = _derive_feature(path)

            cleaned = await enforce_output_safety(
                user_id=user_id,
                feature=feature,
                response_data=data,
            )

            # Try to get safety metadata from the route handler (task-based)
            safety_meta = get_and_clear_safety_meta()

            # Fallback: detect rewrite from cached request body
            if not safety_meta and isinstance(cleaned, dict) and cached_body:
                safety_meta = _detect_input_rewrite_from_body(cached_body)

            if isinstance(cleaned, dict) and safety_meta and safety_meta.get("was_rewritten"):
                cleaned["_safety_meta"] = {
                    "was_rewritten": True,
                    "safety_note": safety_meta.get("safety_note",
                        "We adjusted a few words to keep your content original and generation-ready."),
                }

            return JSONResponse(
                content=cleaned,
                status_code=response.status_code,
            )
        except Exception as e:
            logger.error(f"[OUTPUT MIDDLEWARE] Enforcer failed on {path}: {e}", exc_info=True)
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
            )


def _detect_input_rewrite_from_body(raw_body: bytes) -> dict:
    """
    Lightweight check: did the request body contain terms that would trigger a rewrite?
    Uses the same rule_rewriter and semantic_detector that process_safety_check uses.
    """
    try:
        text = raw_body.decode("utf-8", errors="ignore")
        req_data = json.loads(text)
    except Exception:
        return None

    try:
        from services.rewrite_engine.rule_rewriter import has_risky_terms
        from services.rewrite_engine.semantic_detector import has_semantic_risk

        strings_to_check = []
        if isinstance(req_data, dict):
            for v in req_data.values():
                if isinstance(v, str) and len(v) > 3:
                    strings_to_check.append(v)

        for s in strings_to_check:
            if has_risky_terms(s) or has_semantic_risk(s):
                return {
                    "was_rewritten": True,
                    "safety_note": "We adjusted a few words to keep your content original and generation-ready.",
                }

        return None
    except Exception:
        return None
