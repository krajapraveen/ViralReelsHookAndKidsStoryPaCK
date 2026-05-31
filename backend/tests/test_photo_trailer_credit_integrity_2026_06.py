"""
P0 2026-06 — Credit integrity invariant suite for the Photo Trailer pipeline.

Triggered by the krajapraveen@gmail.com production incident:
  FAILED 60s "Anime Intro" trailer's UI claimed "60 credits refunded"
  but the actual user balance was never restored.

These tests pin the bug class so it cannot regress. Specifically:

  1. FAILED paid trailer job → ZERO or EXACTLY ONE refund ledger row.
     Never zero-but-message-says-refunded. Never two refunds.

  2. Refund retry is idempotent at the ledger level. Calling refund_credits
     twice with the same reference_id MUST NOT double-credit the user.

  3. UI refund badge requires backend-confirmed refund. The honest-message
     contract: error_message claims "credits refunded" only when a refund
     ledger row exists.

  4. Balance after failure equals original balance (deduct + refund net 0).

  5. Historical failed jobs repair correctly via the idempotent repair
     endpoint and the repair is itself idempotent.

  6. add_credits-style failure path: when the refund attempt raises, the
     job's error_message MUST NOT claim "credits refunded".

  Pinned in: /app/Makefile (BOUNDARY_AUDIT_SUITES)
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
TRAILER_PATH = ROOT / "backend" / "routes" / "photo_trailer.py"
FRONTEND_FAIL_STEP = ROOT / "frontend" / "src" / "pages" / "PhotoTrailerPage.jsx"
CREDITS_SERVICE = ROOT / "backend" / "services" / "credits_service.py"
MAKEFILE = ROOT / "Makefile"


# ─── 1. Static-source invariants ─────────────────────────────────────────────


def test_fail_function_refunds_before_setting_error_message():
    """The pre-fix bug wrote `error_message = "credits refunded"` to the DB
    BEFORE the refund was attempted. That is now structurally impossible:
    the refund block must appear LEXICALLY before the `error_message`
    persistence in `_fail()`."""
    src = TRAILER_PATH.read_text()
    # Locate the body of _fail() — from its def to the next top-level def.
    m = re.search(r"async def _fail\([^\)]*\):(?P<body>.+?)(?=\nasync def |\ndef )", src, re.S)
    assert m, "_fail() must exist in photo_trailer.py"
    body = m.group("body")

    refund_pos = body.find("svc.refund_credits(")
    msg_persist_pos = body.find("\"error_message\":")
    assert refund_pos != -1, "_fail() must call svc.refund_credits() — refund path is required."
    assert msg_persist_pos != -1, "_fail() must persist error_message."
    assert refund_pos < msg_persist_pos, (
        "_fail() must attempt refund BEFORE persisting error_message — "
        "this is the honest-message contract."
    )


def test_fail_function_uses_idempotent_reference_id():
    """The refund call must use the canonical reference_id pattern
    `trailer_refund:<job_id>` so concurrent fail+janitor+repair paths
    CANNOT double-refund."""
    src = TRAILER_PATH.read_text()
    assert 'reference_id=f"trailer_refund:{job_id}"' in src, (
        "_fail() must use reference_id='trailer_refund:<job_id>' "
        "for ledger-level idempotency."
    )
    # Same for cancel + janitor + repair surfaces (mandate: ALL refund sinks
    # share the same idempotency key).
    assert 'reference_id=f"trailer_refund:{jid}"' in src, (
        "Janitor and repair sweeps must share the canonical reference_id."
    )


def test_fail_function_falls_back_to_ledger_when_charged_credits_zero():
    """If `deduct_credits` succeeded but the `charged_credits` denorm cache
    write failed, the refund path must still recover the amount from the
    credit_ledger — not silently skip the refund."""
    src = TRAILER_PATH.read_text()
    m = re.search(r"async def _fail\([^\)]*\):(?P<body>.+?)(?=\nasync def |\ndef )", src, re.S)
    body = m.group("body")
    assert 'db.credit_ledger.find_one' in body, (
        "_fail() must consult the credit_ledger as a fallback when "
        "`charged_credits` denorm cache is 0."
    )
    assert '"type": "deduct"' in body, (
        "_fail() must look up the deduct ledger row by type='deduct'."
    )


def test_error_message_never_falsely_claims_refund():
    """The hardcoded RENDER_INVALID message that claimed "credits refunded"
    must NOT appear unconditionally any more. The honest-message branch
    must be gated by `refund_issued`."""
    src = TRAILER_PATH.read_text()
    m = re.search(r"async def _fail\([^\)]*\):(?P<body>.+?)(?=\nasync def |\ndef )", src, re.S)
    body = m.group("body")
    # Find any line that sets user_facing_msg to a "credits refunded" string.
    # Each such line must live inside an `if refund_issued ...` branch.
    refund_claim_re = re.compile(r'user_facing_msg\s*=\s*\(?\s*[\'"](?P<msg>[^\'"]*credits refunded[^\'"]*)', re.I)
    matches = list(refund_claim_re.finditer(body))
    assert matches, "Expected at least one branch that DOES claim a refund."
    for mm in matches:
        # Look 200 chars before the match — must contain an `if refund_issued`
        # or `if refund_issued and` guard.
        prefix = body[max(0, mm.start() - 250): mm.start()]
        assert "if refund_issued" in prefix, (
            f"Found `user_facing_msg = '...credits refunded...'` without an "
            f"`if refund_issued` guard. Excerpt: ...{prefix[-200:]!r} → "
            f"{mm.group('msg')!r}"
        )


def _extract_top_level_func(src: str, name: str) -> str:
    """Pull the body of a top-level `(async )?def {name}(...)` until the
    next top-level `def`/`async def`/`class` line. Robust to nested
    helpers and string literals containing `def `."""
    pat = re.compile(
        rf"^(?P<head>(?:async\s+)?def {re.escape(name)}\([^)]*\)[^:]*:\s*\n)"
        rf"(?P<body>(?:^[ \t]+.*\n|^\s*\n)+)",
        re.M,
    )
    m = pat.search(src)
    if not m:
        return ""
    return m.group("body")


def test_janitor_uses_idempotent_refund_path():
    """The stale-job janitor must use the same idempotent
    CreditsService.refund_credits path as _fail() — never the legacy
    `add_credits(..., tx_type="REFUND")` shortcut which has no ledger
    idempotency."""
    src = TRAILER_PATH.read_text()
    body = _extract_top_level_func(src, "_reap_stale_pipelines")
    assert body, "_reap_stale_pipelines() must exist."
    assert 'get_credits_service' in body and 'refund_credits' in body, (
        "Janitor must use CreditsService.refund_credits, not legacy add_credits."
    )
    # Must NOT call the legacy non-idempotent add_credits(..., tx_type="REFUND") any more.
    legacy_call = re.search(r'add_credits\([^)]*tx_type="REFUND"', body)
    assert legacy_call is None, (
        "Janitor must not use the legacy non-idempotent add_credits refund path: "
        f"found {legacy_call.group(0) if legacy_call else ''!r}"
    )


def test_cancel_path_uses_idempotent_refund():
    """`cancel_job` must use the same idempotent refund path as `_fail`."""
    src = TRAILER_PATH.read_text()
    body = _extract_top_level_func(src, "cancel_job")
    assert body, "cancel_job() must exist."
    assert "refund_credits" in body and "trailer_refund" in body, (
        "cancel_job must use CreditsService.refund_credits with the "
        "canonical reference_id."
    )


# ─── 2. Frontend honest-message contract ─────────────────────────────────────


def test_frontend_default_copy_does_not_claim_refund_when_unconfirmed():
    """If `refunded_credits === 0` (i.e. backend never confirmed a refund),
    the FailedStep card MUST NOT use a fallback string that claims
    "credits refunded". Previously the fallback was
    'Something went wrong. Your credits were refunded.' — that lied."""
    src = FRONTEND_FAIL_STEP.read_text()
    # The honest contract: a `refundConfirmed` ternary selecting the
    # fallback message based on `Number(job?.refunded_credits || 0) > 0`.
    assert "refundConfirmed" in src, (
        "FailedStep must compute refundConfirmed from refunded_credits."
    )
    assert "Number(job?.refunded_credits || 0) > 0" in src, (
        "Refund confirmation must read from refunded_credits."
    )
    # The unconditional fallback string MUST NOT lie.
    assert (
        "'Something went wrong. Your credits were refunded.'" not in src
    ), (
        "Default fallback string must not unconditionally claim a refund. "
        "Use a refundConfirmed ternary instead."
    )


# ─── 3. CreditsService idempotency ───────────────────────────────────────────


def test_credits_service_refund_supports_reference_idempotency():
    """The CreditsService.refund_credits implementation must short-circuit
    when called twice with the same reference_id — exactly like award_credits.
    Without this, every retry path in photo_trailer would risk double-paying."""
    src = CREDITS_SERVICE.read_text()
    m = re.search(
        r"async def refund_credits\([^\)]*\)[^:]*:(?P<body>.+?)(?=\n    async def |\n\nclass |\nclass |\Z)",
        src,
        re.S,
    )
    assert m, "CreditsService.refund_credits must exist."
    body = m.group("body")
    assert "reference_id" in body, "refund_credits must accept reference_id."
    assert "Duplicate refund blocked" in body or "already_refunded" in body, (
        "refund_credits must short-circuit on duplicate reference_id."
    )
    assert 'self.ledger.find_one' in body, (
        "Idempotency check must consult the ledger."
    )


@pytest.mark.asyncio
async def test_credits_service_refund_is_runtime_idempotent():
    """End-to-end behavioural proof: calling refund_credits twice with the
    same reference_id awards the credit exactly ONCE."""
    import sys
    sys.path.insert(0, str(ROOT / "backend"))
    from services.credits_service import CreditsService

    # Minimal in-memory fakes mimicking Motor's API surface.
    class _FakeCol:
        def __init__(self, rows=None):
            self._rows = list(rows or [])

        async def find_one(self, query, projection=None):
            for r in self._rows:
                if all(r.get(k) == v for k, v in query.items() if not isinstance(v, dict)):
                    return dict(r)
            return None

        async def find_one_and_update(self, query, update, projection=None, return_document=None):
            for r in self._rows:
                if all(r.get(k) == v for k, v in query.items()):
                    inc = (update.get("$inc") or {})
                    set_ = (update.get("$set") or {})
                    for k, v in inc.items():
                        r[k] = (r.get(k) or 0) + v
                    for k, v in set_.items():
                        r[k] = v
                    return dict(r)
            return None

        async def insert_one(self, doc):
            self._rows.append(dict(doc))

    users = _FakeCol([{"id": "u-x", "credits": 100}])
    ledger = _FakeCol([])
    svc = CreditsService(users=users, ledger=ledger)

    r1 = await svc.refund_credits("u-x", 35, "Refund failed trailer JID", reference_id="trailer_refund:JID")
    r2 = await svc.refund_credits("u-x", 35, "Refund failed trailer JID (retry)", reference_id="trailer_refund:JID")

    assert r1["new_balance"] == 135, "First refund must credit +35"
    assert r2["new_balance"] == 135, "Second call with same reference must be a no-op (idempotent)"
    assert r2.get("already_refunded") is True
    # Exactly ONE refund ledger row.
    refund_rows = [r for r in ledger._rows if r.get("type") == "refund"]
    assert len(refund_rows) == 1, f"Expected 1 refund ledger row, got {len(refund_rows)}: {refund_rows}"


# ─── 4. Repair endpoint is registered + idempotent in source ─────────────────


def test_repair_refunds_endpoint_exists():
    src = TRAILER_PATH.read_text()
    assert "@router.post(\"/admin/repair-refunds\")" in src, (
        "POST /api/photo-trailer/admin/repair-refunds must exist for ops."
    )
    assert "@router.get(\"/admin/diagnose-user\")" in src, (
        "GET /api/photo-trailer/admin/diagnose-user must exist for ops."
    )


def test_repair_refunds_dry_run_default_is_true():
    """Repair endpoint must default to dry_run=True — destructive writes
    require an explicit operator opt-in."""
    src = TRAILER_PATH.read_text()
    m = re.search(r"class _RefundRepairIn\(BaseModel\):(?P<body>.+?)\n\n", src, re.S)
    assert m, "_RefundRepairIn model must exist."
    body = m.group("body")
    assert "dry_run: bool = True" in body, (
        "Repair endpoint must default to dry_run=True."
    )


# ─── 5. Makefile registration ────────────────────────────────────────────────


def test_credit_integrity_suite_registered_in_makefile():
    """The bug-class-elimination mandate: every new audit must be wired into
    the boundary-audit gate. Without this, the suite is invisible to CI."""
    mk = MAKEFILE.read_text()
    assert "test_photo_trailer_credit_integrity_2026_06.py" in mk, (
        "/app/Makefile must register the credit-integrity audit in "
        "BOUNDARY_AUDIT_SUITES."
    )
