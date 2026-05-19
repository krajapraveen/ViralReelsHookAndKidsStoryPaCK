"""
Attribution capture endpoint — P0 2026-05-22 Phase A.

Persists Google Ads / Meta Ads / utm_* click-IDs from the FIRST page
load so they survive every downstream redirect (Cashfree hosted-page,
OAuth, etc.). Without this, every paid signup and every paid payment
loses its attribution at the redirect boundary.

Hard requirements (founder mandate 2026-05-22):
  • Capture on first page load — not waiting for signup.
  • Idempotent for the same anonymous_id (we never overwrite a real
    gclid with a missing one on subsequent navigations).
  • Carries source_platform alongside the click-IDs so downstream
    funnel analysis can slice by paid channel without a join.

Doctrine refs:
  • rule 1 (validate every boundary) — strict Pydantic envelope
  • rule 5 (no leaked internals) — only writes; no read endpoint exposed
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from shared import db, logger, get_optional_user

router = APIRouter(prefix="/attribution", tags=["attribution"])

# ─── Allow-listed source platforms ──────────────────────────────────
# Strict literal-style validation: we don't want free-form strings
# poisoning analytics downstream. New platforms add here deliberately.
ALLOWED_SOURCE_PLATFORMS = frozenset({
    "google_ads", "meta_ads", "twitter_ads", "linkedin_ads",
    "tiktok_ads", "youtube_ads",
    "organic", "direct", "referral", "email", "unknown",
})


class AttributionCapturePayload(BaseModel):
    anonymous_id: str = Field(..., min_length=8, max_length=64)
    gclid: Optional[str] = Field(default=None, max_length=512)
    gbraid: Optional[str] = Field(default=None, max_length=512)
    wbraid: Optional[str] = Field(default=None, max_length=512)
    fbclid: Optional[str] = Field(default=None, max_length=512)
    utm_source: Optional[str] = Field(default=None, max_length=200)
    utm_medium: Optional[str] = Field(default=None, max_length=200)
    utm_campaign: Optional[str] = Field(default=None, max_length=200)
    utm_content: Optional[str] = Field(default=None, max_length=200)
    utm_term: Optional[str] = Field(default=None, max_length=200)
    landing_path: Optional[str] = Field(default=None, max_length=2048)
    referrer: Optional[str] = Field(default=None, max_length=2048)
    source_platform: Optional[str] = Field(default=None, max_length=32)


def _classify_source_platform(p: AttributionCapturePayload) -> str:
    """Derive a canonical source_platform from the strongest signal
    available. Order matters: paid click-IDs win over utm_* over
    referrer over the caller-supplied value over 'direct'."""
    if p.gclid or p.gbraid or p.wbraid:
        return "google_ads"
    if p.fbclid:
        return "meta_ads"
    sp = (p.source_platform or "").lower()
    if sp in ALLOWED_SOURCE_PLATFORMS:
        return sp
    utm = (p.utm_source or "").lower()
    if "google" in utm:
        return "google_ads"
    if utm in ("facebook", "instagram", "meta"):
        return "meta_ads"
    if utm:
        return "referral"
    if p.referrer:
        return "referral"
    return "direct"


@router.post("/capture")
async def capture_attribution(
    payload: AttributionCapturePayload,
    request: Request,
    user: Optional[dict] = Depends(get_optional_user),
):
    """Persist attribution against an anonymous session id.

    Idempotency: we never overwrite an existing real gclid/utm field
    with an empty one. Each call merges only the fields that are
    actually present and non-empty in the payload.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    source_platform = _classify_source_platform(payload)

    set_fields: dict = {
        "anonymous_id": payload.anonymous_id,
        "last_seen_at": now_iso,
        "source_platform": source_platform,
    }
    if user and user.get("id"):
        set_fields["user_id"] = user["id"]

    # Only merge fields that are present and non-empty. This is the
    # idempotency guarantee: subsequent visits without a gclid never
    # clobber the original capture.
    for fld in ("gclid", "gbraid", "wbraid", "fbclid",
                "utm_source", "utm_medium", "utm_campaign",
                "utm_content", "utm_term",
                "landing_path", "referrer"):
        v = getattr(payload, fld, None)
        if v:
            set_fields[fld] = v

    await db.attribution_sessions.update_one(
        {"anonymous_id": payload.anonymous_id},
        {
            "$set": set_fields,
            "$setOnInsert": {
                "first_seen_at": now_iso,
                "first_landing_path": payload.landing_path or "",
                "first_referrer": payload.referrer or "",
            },
        },
        upsert=True,
    )

    request_id = getattr(request.state, "request_id", None)
    logger.info(
        "[ATTRIBUTION] captured anonymous_id=%s source=%s gclid=%s utm_source=%s request_id=%s",
        payload.anonymous_id, source_platform,
        bool(payload.gclid), payload.utm_source or "-", request_id,
    )

    return {
        "ok": True,
        "source_platform": source_platform,
        "request_id": request_id,
    }


async def get_attribution_for_user(user_id: str) -> dict:
    """Look up the most recent attribution session for a given user.

    Used by the cashfree webhook to stamp the order with the paid-click
    context so the conversion fire has the correct source_platform.
    Returns {} when not found (safe-default).
    """
    if not user_id:
        return {}
    doc = await db.attribution_sessions.find_one(
        {"user_id": user_id},
        sort=[("last_seen_at", -1)],
        projection={"_id": 0},
    )
    return doc or {}
