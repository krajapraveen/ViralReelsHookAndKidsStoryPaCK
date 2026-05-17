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

from typing import Annotated, Literal

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


# ── Tokens (JWT-shaped, opaque, content-protection, stream) ──────────
# Allows the full JWT alphabet (`[A-Za-z0-9_\-\.]`) plus the `~` and `=`
# we see from a few legacy URL-safe-base64 variants. Length is bounded
# so an attacker cannot mail us a gigabyte of bytes.
TokenStr = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=16,
        max_length=4096,
        pattern=r"^[A-Za-z0-9_\-\.~=]{16,4096}$",
    ),
]

# ── OTP (numeric, exactly N digits — Verify2FA enforces 6) ───────────
# Stripped to a strict 6-digit token. The longer OTP variants (8 digits
# for some recovery flows) should use Otp8DigitStr.
Otp6DigitStr = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
    ),
]

# ── User-supplied API key (BYO-key flow) ─────────────────────────────
# OpenAI/Gemini/Anthropic keys are at minimum ~32 chars and we never
# accept anything beyond a few hundred. The length cap is a DoS guard;
# the actual provider validates the key on first use.
ApiKeyStr = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=10,
        max_length=512,
    ),
]

# ── Password — length cap + min strength threshold ───────────────────
# We bound max_length to 128 so an attacker can't waste bcrypt cycles
# on multi-MB inputs. Min length is set on a per-route basis (auth
# allows 8, schemas.UserCreate allows 6 for legacy reasons).
Password6PlusStr = Annotated[
    str,
    StringConstraints(min_length=6, max_length=128),
]
Password8PlusStr = Annotated[
    str,
    StringConstraints(min_length=8, max_length=128),
]


# ── Wallet ledger Literals (P0 — money) ──────────────────────────────
# These mirror the comments in routes/wallet.py:LedgerEntry.
LedgerEntryType = Literal["HOLD", "CAPTURE", "RELEASE", "TOPUP", "ADJUST"]
LedgerRefType = Literal["JOB", "SUBSCRIPTION", "ADMIN", "REFUND"]
LedgerStatus = Literal["ACTIVE", "REVERSED"]


# ── Payment ledger Literals (P0 — money) ─────────────────────────────
# Mirror models/schemas.py:PaymentLog comments.
PaymentStatus = Literal["SUCCESS", "FAILED", "PENDING", "REFUNDED"]
PaymentCurrency = Literal["INR", "USD"]
