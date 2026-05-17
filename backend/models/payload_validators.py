"""
Backend Payload Validators — P1 2026-05-19 reliability sweep
================================================================

Shared types for the target payload keys called out by the founder
spec. Use these in Pydantic request models and Form()/Query() params
instead of raw `str` so the FastAPI/Pydantic boundary itself rejects:

  • objects, arrays, nulls where strings are required
  • overlong / underlong IDs
  • non-canonical labels in slug-only fields
  • non-numeric values for amount/credits
  • out-of-range numerics

Every type is Annotated so it shows up in the OpenAPI schema with a
clear regex/max_length contract.

Usage:

    from typing import Annotated
    from models.payload_validators import (
        IdStr, SlugStr, JobIdStr, OrderIdStr,
        CreditAmountInt, MoneyAmountInt,
    )

    class GenerateRequest(BaseModel):
        story_id: IdStr
        style: SlugStr
        credits: CreditAmountInt
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field, StringConstraints

# ── Opaque IDs (UUID-ish, mongo ObjectIds, short canonical handles) ──
# Accepts `[A-Za-z0-9_-]{6,128}`. Rejects empty strings, objects via
# Pydantic's native type checking, and anything with whitespace or
# special chars.
IdStr = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=6,
        max_length=128,
        pattern=r"^[A-Za-z0-9_\-]{6,128}$",
    ),
]

# ── Canonical slugs (`bold_superhero`, `cartoon_fun`, …) ─────────────
# First char must be alnum, then alnum/underscore/hyphen.
SlugStr = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=2,
        max_length=64,
        pattern=r"^[a-z0-9][a-z0-9_\-]{1,63}$",
    ),
]

# ── Job IDs — UUID-shaped or opaque (allow uppercase for backwards compat) ──
JobIdStr = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=6,
        max_length=128,
        pattern=r"^[A-Za-z0-9_\-]{6,128}$",
    ),
]

# ── Order IDs (Cashfree-style) ───────────────────────────────────────
OrderIdStr = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=6,
        max_length=128,
        pattern=r"^[A-Za-z0-9_\-]{6,128}$",
    ),
]

# ── Credits — non-negative integer, sane upper bound ─────────────────
# Backend never trusts a client-supplied credit grant; this constraint
# is for accounting/forecasting endpoints, NOT for billing.
CreditAmountInt = Annotated[
    int,
    Field(ge=0, le=1_000_000),
]

# Strictly positive credits (for spends/reservations).
PositiveCreditInt = Annotated[
    int,
    Field(gt=0, le=1_000_000),
]

# ── Money — INR paise / USD cents, integer only ──────────────────────
MoneyAmountInt = Annotated[
    int,
    Field(ge=0, le=10_000_000),
]

# ── User-facing free-text — safe upper bound ─────────────────────────
ShortText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=0, max_length=512),
]

LongText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=0, max_length=8000),
]
