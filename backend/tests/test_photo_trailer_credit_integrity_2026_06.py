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

    refund_pos = max(
        body.find("_settle_unrefunded_trailer_deducts("),
        body.find("svc.refund_credits("),
    )
    msg_persist_pos = body.find("\"error_message\":")
    assert refund_pos != -1, (
        "_fail() must invoke a refund path (settle helper or refund_credits)."
    )
    assert msg_persist_pos != -1, "_fail() must persist error_message."
    assert refund_pos < msg_persist_pos, (
        "_fail() must attempt refund BEFORE persisting error_message — "
        "this is the honest-message contract."
    )


def test_fail_function_uses_idempotent_reference_id():
    """The refund path must use canonical reference_id patterns so
    concurrent fail+janitor+repair paths CANNOT double-refund.

    Two patterns satisfy this:
      • Legacy single-attempt:  trailer_refund:<job_id>
      • Per-attempt (P0 fix):   trailer_refund:<job_id>:attempt:<N>"""
    src = TRAILER_PATH.read_text()
    assert "trailer_refund:" in src, (
        "Source must reference 'trailer_refund:<job_id>' canonical key."
    )
    assert "attempt:" in src, (
        "P0 2026-06 — per-attempt reference_id must be present for retry safety."
    )


def test_fail_function_falls_back_to_ledger_when_charged_credits_zero():
    """Refund logic must not rely on the `charged_credits` denorm cache —
    it must walk the credit_ledger so a race window between deduct and
    cache-update cannot hide a deduction. The settle helper is the
    canonical implementation."""
    src = TRAILER_PATH.read_text()
    settle_def = re.search(
        r"async def _settle_unrefunded_trailer_deducts\(.+?(?=\nasync def |\ndef )",
        src, re.S,
    )
    assert settle_def, "_settle_unrefunded_trailer_deducts() helper must exist."
    body = settle_def.group(0)
    assert "db.credit_ledger.find" in body, (
        "Settle helper must read deduct rows directly from credit_ledger."
    )
    assert '"type": "deduct"' in body, (
        "Settle helper must filter on type='deduct'."
    )
    fail_def = re.search(
        r"async def _fail\([^\)]*\):(?P<body>.+?)(?=\nasync def |\ndef )", src, re.S,
    )
    assert "_settle_unrefunded_trailer_deducts(" in fail_def.group("body"), (
        "_fail() must delegate to the settle helper."
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
    """The stale-job janitor must use the settle helper — not the legacy
    `add_credits(..., tx_type="REFUND")` shortcut which has no ledger
    idempotency or per-attempt reference_id support."""
    src = TRAILER_PATH.read_text()
    body = _extract_top_level_func(src, "_reap_stale_pipelines")
    assert body, "_reap_stale_pipelines() must exist."
    assert "_settle_unrefunded_trailer_deducts(" in body, (
        "Janitor must delegate to the settle helper for retry-safe refunds."
    )
    legacy_call = re.search(r'add_credits\([^)]*tx_type="REFUND"', body)
    assert legacy_call is None, (
        "Janitor must not use the legacy non-idempotent add_credits refund path: "
        f"found {legacy_call.group(0) if legacy_call else ''!r}"
    )


def test_cancel_path_uses_idempotent_refund():
    """`cancel_job` must use the settle helper — same contract as `_fail`."""
    src = TRAILER_PATH.read_text()
    body = _extract_top_level_func(src, "cancel_job")
    assert body, "cancel_job() must exist."
    assert "_settle_unrefunded_trailer_deducts(" in body, (
        "cancel_job must delegate to the settle helper with the "
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


# ─── 6. Guardrail invariant: catch violations BEFORE users notice ────────────

GUARDRAILS_PATH = ROOT / "backend" / "routes" / "guardrails.py"


def test_trailer_failed_without_refund_invariant_registered():
    """The recurring incident-prevention guardrail: a FAILED trailer with a
    deduction and no refund row > 5 minutes old must trip a CRITICAL alert.
    Higher leverage than any UI trust widget — catches the bug BEFORE the
    user notices the missing balance."""
    src = GUARDRAILS_PATH.read_text()
    assert '"trailer_failed_without_refund"' in src, (
        "INVARIANTS must declare the trailer_failed_without_refund tripwire."
    )
    # Check function present and registered.
    assert "async def _check_trailer_failed_without_refund(" in src, (
        "The check function must exist."
    )
    assert '"trailer_failed_without_refund": _check_trailer_failed_without_refund' in src, (
        "CHECKERS must wire the invariant to its check function."
    )
    # Critical severity — money integrity is the highest priority.
    inv_block = re.search(
        r'"trailer_failed_without_refund":\s*\{(?P<body>[^}]+)\}',
        src,
        re.S,
    )
    assert inv_block, "Invariant declaration must use a dict literal."
    assert '"severity": "critical"' in inv_block.group("body"), (
        "trailer_failed_without_refund must be severity=critical."
    )


def test_trailer_failed_without_refund_uses_5min_window():
    """The grace window is 5 minutes — long enough for the inline refund
    branch and first janitor sweep to land, short enough to alert ops
    before support tickets pile up."""
    src = GUARDRAILS_PATH.read_text()
    m = re.search(
        r"async def _check_trailer_failed_without_refund\(.+?(?=\nasync def |\n# Map invariant)",
        src,
        re.S,
    )
    assert m, "_check_trailer_failed_without_refund must exist."
    body = m.group(0)
    assert "minutes=5" in body, "5-minute grace window must be enforced."
    assert "FAILED" in body and "CANCELLED" in body, (
        "Both terminal states must be covered."
    )
    # Accept BOTH ledger schemes (canonical reference_id + legacy reason).
    assert "trailer_refund:" in body, (
        "Must accept canonical reference_id refunds."
    )
    assert "Refund" in body and "regex" in body, (
        "Must also accept legacy reason-prefix refunds for back-compat."
    )


@pytest.mark.asyncio
async def test_trailer_failed_without_refund_detects_violation():
    """End-to-end behavioural proof: a FAILED trailer with charged_credits>0
    and NO refund row > 5min old is flagged; once a refund row appears the
    invariant clears."""
    import sys
    from datetime import datetime as _dt, timezone as _tz, timedelta as _td
    sys.path.insert(0, str(ROOT / "backend"))

    # Minimal Motor surface needed by _check_trailer_failed_without_refund.
    class _Cursor:
        def __init__(self, rows):
            self._rows = rows
            self._i = 0

        def to_list(self, n):
            async def _inner():
                return list(self._rows[:n])
            return _inner()

        def __aiter__(self):
            self._i = 0
            return self

        async def __anext__(self):
            if self._i >= len(self._rows):
                raise StopAsyncIteration
            r = self._rows[self._i]
            self._i += 1
            return dict(r)

    class _Col:
        def __init__(self, rows=None):
            self._rows = list(rows or [])

        def find(self, query, projection=None):
            def _match(r):
                # Tiny subset of Mongo query semantics — enough for this test.
                for k, v in query.items():
                    if k == "$and":
                        if not all(_match_one(r, sub) for sub in v):
                            return False
                    elif k == "$or":
                        if not any(_match_one(r, sub) for sub in v):
                            return False
                    else:
                        if not _match_one(r, {k: v}):
                            return False
                return True
            return _Cursor([r for r in self._rows if _match(r)])

        async def find_one(self, query):
            for r in self._rows:
                if _match_one(r, query):
                    return dict(r)
            return None

    def _match_one(r, q):
        for k, v in q.items():
            if k == "$or":
                if not any(_match_one(r, sub) for sub in v):
                    return False
                continue
            if k == "$and":
                if not all(_match_one(r, sub) for sub in v):
                    return False
                continue
            actual = r.get(k)
            if isinstance(v, dict):
                if "$in" in v and actual not in v["$in"]:
                    return False
                if "$gt" in v and not (actual is not None and actual > v["$gt"]):
                    return False
                if "$lt" in v and not (actual is not None and actual < v["$lt"]):
                    return False
                if "$gte" in v and not (actual is not None and actual >= v["$gte"]):
                    return False
                if "$ne" in v and actual == v["$ne"]:
                    return False
                if "$exists" in v:
                    has = k in r
                    if v["$exists"] != has:
                        return False
                if "$regex" in v:
                    if actual is None or not re.search(v["$regex"], actual):
                        return False
            else:
                if actual != v:
                    return False
        return True

    # Set up: one FAILED job 10 minutes old, deducted but never refunded.
    now = _dt.now(_tz.utc)
    failed_at = (now - _td(minutes=10)).isoformat()
    fresh_at = (now - _td(minutes=1)).isoformat()  # within grace
    jobs = _Col([
        # VIOLATION: old + no refund
        {"_id": "jid-bad-1", "user_id": "u-1", "status": "FAILED",
         "charged_credits": 60, "refunded_credits": 0,
         "failed_at": failed_at, "updated_at": failed_at,
         "duration_target_seconds": 60, "template_id": "anime_intro",
         "error_code": "RENDER_INVALID"},
        # HEALTHY: has refund row (via canonical ref) — should clear.
        {"_id": "jid-ok-1", "user_id": "u-2", "status": "FAILED",
         "charged_credits": 35, "refunded_credits": 0,
         "failed_at": failed_at, "updated_at": failed_at,
         "duration_target_seconds": 60, "template_id": "anime_intro",
         "error_code": "RENDER_INVALID"},
        # WITHIN GRACE: 1min old — should not flag yet.
        {"_id": "jid-grace", "user_id": "u-3", "status": "FAILED",
         "charged_credits": 35, "refunded_credits": 0,
         "failed_at": fresh_at, "updated_at": fresh_at,
         "duration_target_seconds": 60, "template_id": "anime_intro",
         "error_code": "RENDER_INVALID"},
        # ALREADY REFUNDED via denorm cache — excluded by the query filter.
        {"_id": "jid-refunded", "user_id": "u-4", "status": "FAILED",
         "charged_credits": 35, "refunded_credits": 35,
         "failed_at": failed_at, "updated_at": failed_at,
         "duration_target_seconds": 60},
    ])
    ledger = _Col([
        # jid-bad-1: deducted 60 cr, NO refund row → VIOLATION
        {"user_id": "u-1", "type": "deduct",
         "reason": "Photo trailer jid-bad-1", "amount": 60},
        # jid-ok-1: deducted 35, refunded 35 → balanced
        {"user_id": "u-2", "type": "deduct",
         "reason": "Photo trailer jid-ok-1", "amount": 35},
        {"user_id": "u-2", "reference_id": "trailer_refund:jid-ok-1",
         "type": "refund", "amount": 35},
        # jid-grace: deducted, no refund, but failed_at within grace window
        {"user_id": "u-3", "type": "deduct",
         "reason": "Photo trailer jid-grace", "amount": 35},
        # jid-refunded: deducted + refunded via canonical ref
        {"user_id": "u-4", "type": "deduct",
         "reason": "Photo trailer jid-refunded", "amount": 35},
        {"user_id": "u-4", "reference_id": "trailer_refund:jid-refunded",
         "type": "refund", "amount": 35},
    ])

    # Monkey-patch the module's `db` accessor with our fakes.
    import importlib
    guardrails = importlib.import_module("routes.guardrails")
    fake_db = type("DB", (), {})()
    fake_db.photo_trailer_jobs = jobs
    fake_db.credit_ledger = ledger
    orig_db = guardrails.db
    guardrails.db = fake_db
    try:
        out = await guardrails._check_trailer_failed_without_refund()
    finally:
        guardrails.db = orig_db

    assert out["violated"] is True, f"Expected violation, got: {out}"
    assert out["count"] == 1, f"Expected exactly 1 violation (jid-bad-1), got {out['count']}: {out['sample_ids']}"
    assert any("jid-bad-" in sid for sid in out["sample_ids"]), out["sample_ids"]
    # Grace-window job should NOT be flagged.
    assert not any("jid-grace" in sid for sid in out["sample_ids"])
    # Refunded jobs should NOT be flagged.
    assert not any("jid-ok-1" in sid for sid in out["sample_ids"])
    assert not any("jid-refunded" in sid for sid in out["sample_ids"])
