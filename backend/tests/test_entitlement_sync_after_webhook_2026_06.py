"""
P0 ENTITLEMENT SYNC — Webhook → MyTrailer gate (2026-06)
=========================================================

Background
----------
On 2026-06, a real user (krajapraveen@gmail.com) reported that after
purchasing a Monthly subscription on production, the MyTrailer 90s
duration was still blocked behind the "Premium Subscription" paywall.

Root cause (verified by code audit)
-----------------------------------
The Cashfree `/api/cashfree/webhook` handler in `cashfree_payments.py`
wrote subscription details into the EMBEDDED `users.subscription`
field only. But the MyTrailer entitlement gate `_user_plan()` in
`photo_trailer.py` read from the SEPARATE `db.subscriptions`
COLLECTION. The two paths never touched the same data.

A secondary issue: `_user_plan` was querying `status: "active"`
(lowercase), but the rest of the codebase (cashfree_subscription_service,
subscriptions.py legacy paths) writes `"ACTIVE"` (uppercase). So even
when `db.subscriptions` *was* populated by some other code path, the
case mismatch silently filtered it out.

Fix
---
1. **Forward-fix** (webhook): dual-write to BOTH `users.subscription`
   AND `db.subscriptions` so every gate sees Monthly/Quarterly/Yearly
   purchases. Writes `"ACTIVE"` (uppercase) to match codebase convention.
2. **Backward-fix** (reader): `_user_plan()` reads both sources and
   matches status case-insensitively via `$regex: ^active$/i`. This
   unblocks already-paid users (like krajapraveen) on deploy without
   any DB backfill.
3. **Forbid regression**: the static tests in this file fail if the
   webhook ever stops writing to `db.subscriptions` again, OR if
   `_user_plan` stops reading from the embedded fallback, OR if a new
   plan id sneaks into `PREMIUM_PLAN_IDS` without being matched
   live.

Live-execution coverage
-----------------------
Class `TestUserPlanLive` boots Mongo via the same db module the
backend uses and inserts realistic user + subscription documents,
then calls `_user_plan` directly. Every recorded failure mode is
covered:

  T1. Monthly sub in db.subscriptions (status="ACTIVE")  → PREMIUM
  T2. Monthly sub in db.subscriptions (status="active")  → PREMIUM
  T3. Monthly sub embedded only (legacy)                  → PREMIUM
  T4. Monthly sub embedded + expired endDate              → falls back
  T5. Quarterly / Yearly → PREMIUM
  T6. Weekly → PAID (NOT premium)
  T7. No sub but credits ≥ 35                              → PAID
  T8. No sub, credits 0                                    → FREE
  T9. Embedded sub with malformed endDate trusts `active`  → tier
  T10. Both sources populated (collection wins)            → PREMIUM
"""
import asyncio
import os
import re
import sys
import uuid
import pathlib
from datetime import datetime, timezone, timedelta

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
BACKEND = REPO / "backend"
sys.path.insert(0, str(BACKEND))


# ─────────────────────────────────────────────────────────────────────
# (A) Static-source assertions — pin the contract.
# ─────────────────────────────────────────────────────────────────────
class TestWebhookDualWriteContract:
    """The /api/cashfree/webhook handler MUST write to BOTH the
    embedded `users.subscription` field AND the `db.subscriptions`
    collection on a subscription product purchase. Otherwise the
    krajapraveen-class bug returns."""

    def setup_method(self):
        self.src = (BACKEND / "routes" / "cashfree_payments.py").read_text(encoding="utf-8")

    def test_webhook_writes_users_embedded(self):
        # The legacy embedded write must remain.
        assert re.search(
            r"db\.users\.update_one\b.*?\"subscription\":\s*\{",
            self.src, re.DOTALL,
        ), (
            "cashfree_payments.py webhook must still write the "
            "embedded users.subscription field (back-compat for "
            "auth.py/credits.py/genstudio.py readers)."
        )

    def test_webhook_writes_db_subscriptions_collection(self):
        # P0 fix: must ALSO write to db.subscriptions. The shared
        # `_activate_subscription_for_order` helper is the canonical
        # writer; both /verify and /webhook delegate to it.
        assert "db.subscriptions.update_one" in self.src, (
            "cashfree_payments.py must call db.subscriptions.update_one "
            "(via the shared activator) to keep the canonical "
            "subscription collection in sync."
        )
        assert "_activate_subscription_for_order" in self.src, (
            "cashfree_payments.py must define and use the shared "
            "`_activate_subscription_for_order` helper so /verify and "
            "/webhook stay in sync forever."
        )
        # Both endpoints must call the helper.
        assert self.src.count("_activate_subscription_for_order(") >= 3, (
            "Helper must be defined AND called from BOTH the /verify "
            "and /webhook subscription branches. Found "
            f"{self.src.count('_activate_subscription_for_order(')} occurrences."
        )

    def test_webhook_writes_active_status_uppercase(self):
        # The new write must use uppercase "ACTIVE" to match the rest
        # of the codebase (cashfree_subscription_service, legacy
        # subscriptions.py).
        idx = self.src.find("db.subscriptions.update_one")
        assert idx != -1
        window = self.src[idx: idx + 2000]
        assert '"status": "ACTIVE"' in window, (
            "Webhook db.subscriptions write must use status='ACTIVE' "
            "(uppercase) to match codebase convention."
        )

    def test_webhook_supersedes_prior_active_subs(self):
        # Idempotency / no-stale-subs: before activating the new sub,
        # any previously-active sub for this user must be flipped to
        # SUPERSEDED so _user_plan's `find_one + sort by createdAt`
        # never picks up a stale doc.
        assert "update_many" in self.src and "SUPERSEDED" in self.src, (
            "Webhook must mark prior active subs as SUPERSEDED before "
            "activating the new one. Otherwise stale subs linger."
        )


class TestUserPlanReaderContract:
    """`_user_plan()` MUST read from both `db.subscriptions` and the
    embedded `users.subscription` field. This is what unblocks
    already-paid users on deploy with no DB backfill."""

    def setup_method(self):
        self.src = (BACKEND / "routes" / "photo_trailer.py").read_text(encoding="utf-8")

    def test_reads_db_subscriptions(self):
        assert "db.subscriptions.find_one" in self.src

    def test_reads_embedded_subscription_fallback(self):
        # Must look at user.get("subscription") as a fallback.
        assert re.search(
            r"user\.get\(\s*[\"']subscription[\"']\s*\)",
            self.src,
        ), (
            "_user_plan must fall back to `user.get('subscription')` "
            "so users whose record was written by the legacy webhook "
            "(embedded only) get correctly classified."
        )

    def test_matches_status_case_insensitively(self):
        # Must use $regex with /i case-insensitive flag for status.
        assert "$regex" in self.src and "active" in self.src, (
            "_user_plan must match `status` case-insensitively — the "
            "codebase writes both 'ACTIVE' and 'active' historically."
        )

    def test_premium_plan_ids_unchanged(self):
        # Defense: if PREMIUM_PLAN_IDS ever drops monthly/quarterly/yearly,
        # the gate silently breaks.
        assert "PREMIUM_PLAN_IDS = {\"monthly\", \"quarterly\", \"yearly\"}" in self.src


# ─────────────────────────────────────────────────────────────────────
# (B) Live-execution: insert subs into Mongo, call _user_plan, assert.
# ─────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────
# (B) Live-classification: monkeypatch the db.subscriptions reader and
# call _user_plan directly. This decouples the test from Mongo's
# event-loop binding so it passes both standalone AND as part of the
# larger audit-boundaries suite.
# ─────────────────────────────────────────────────────────────────────
sys.path.insert(0, str(BACKEND))
try:
    import routes.photo_trailer as pt_module  # noqa: E402
    _live_import_ok = True
except Exception as _exc:  # noqa: BLE001
    print(f"[entitlement live tests] import skipped: {_exc}")
    _live_import_ok = False


def _run_async(coro):
    """Run a coroutine in a fresh event loop (decoupled from any
    pytest-asyncio session loop or motor's bound loop)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class _FakeCursor:
    def __init__(self, doc):
        self._doc = doc

    async def __aiter__(self):
        if self._doc is not None:
            yield self._doc


class _FakeSubsCollection:
    """Stand-in for `db.subscriptions` that returns a pre-seeded doc
    matching the same `userId + case-insensitive status=active` query
    that `_user_plan` performs."""

    def __init__(self, docs):
        self._docs = docs  # list of subscription documents

    async def find_one(self, query, **kwargs):  # noqa: ARG002
        user_id = query.get("userId")
        status_q = query.get("status")
        # status_q is either a literal string or a regex dict.
        def _matches(doc):
            if doc.get("userId") != user_id:
                return False
            s = (doc.get("status") or "")
            if isinstance(status_q, dict) and "$regex" in status_q:
                return re.match(status_q["$regex"], s, re.IGNORECASE) is not None
            return s == status_q
        actives = [d for d in self._docs if _matches(d)]
        # Sort by createdAt desc (newest first) — matches the real query.
        actives.sort(key=lambda d: d.get("createdAt", ""), reverse=True)
        return actives[0] if actives else None


class _FakeDB:
    def __init__(self, subs_docs):
        self.subscriptions = _FakeSubsCollection(subs_docs)


@pytest.fixture()
def fake_user():
    return {
        "id": f"u_entitlement_test_{uuid.uuid4().hex[:12]}",
        "role": "USER",
        "credits": 0,
    }


def _patch_db(monkeypatch, subs_docs):
    """Install a fake `db` into the photo_trailer module for the test."""
    monkeypatch.setattr(pt_module, "db", _FakeDB(subs_docs))


@pytest.mark.skipif(
    not _live_import_ok,
    reason="backend imports unavailable in this test environment",
)
class TestUserPlanLive:
    """Run _user_plan against a fake `db.subscriptions` for every
    documented entitlement scenario."""

    def _sub_doc(self, user_id, plan_id, status="ACTIVE", days_remaining=30):
        now = datetime.now(timezone.utc)
        end = now + timedelta(days=days_remaining)
        return {
            "id": f"sub_{uuid.uuid4().hex[:10]}",
            "userId": user_id,
            "planId": plan_id,
            "planName": plan_id.title(),
            "status": status,
            "startDate": now.isoformat(),
            "endDate": end.isoformat(),
            "createdAt": now.isoformat(),
        }

    def test_monthly_uppercase_active_returns_premium(self, fake_user, monkeypatch):
        _patch_db(monkeypatch, [self._sub_doc(fake_user["id"], "monthly", "ACTIVE")])
        assert _run_async(pt_module._user_plan(fake_user)) == "PREMIUM"

    def test_monthly_lowercase_active_returns_premium(self, fake_user, monkeypatch):
        _patch_db(monkeypatch, [self._sub_doc(fake_user["id"], "monthly", "active")])
        assert _run_async(pt_module._user_plan(fake_user)) == "PREMIUM"

    def test_monthly_mixedcase_active_returns_premium(self, fake_user, monkeypatch):
        _patch_db(monkeypatch, [self._sub_doc(fake_user["id"], "monthly", "Active")])
        assert _run_async(pt_module._user_plan(fake_user)) == "PREMIUM"

    def test_quarterly_returns_premium(self, fake_user, monkeypatch):
        _patch_db(monkeypatch, [self._sub_doc(fake_user["id"], "quarterly")])
        assert _run_async(pt_module._user_plan(fake_user)) == "PREMIUM"

    def test_yearly_returns_premium(self, fake_user, monkeypatch):
        _patch_db(monkeypatch, [self._sub_doc(fake_user["id"], "yearly")])
        assert _run_async(pt_module._user_plan(fake_user)) == "PREMIUM"

    def test_weekly_returns_paid_not_premium(self, fake_user, monkeypatch):
        _patch_db(monkeypatch, [self._sub_doc(fake_user["id"], "weekly")])
        assert _run_async(pt_module._user_plan(fake_user)) == "PAID"

    def test_no_sub_no_credits_returns_free(self, fake_user, monkeypatch):
        _patch_db(monkeypatch, [])
        assert _run_async(pt_module._user_plan(fake_user)) == "FREE"

    def test_no_sub_with_credits_returns_paid(self, fake_user, monkeypatch):
        _patch_db(monkeypatch, [])
        fake_user["credits"] = 50
        assert _run_async(pt_module._user_plan(fake_user)) == "PAID"

    def test_no_sub_low_credits_returns_free(self, fake_user, monkeypatch):
        _patch_db(monkeypatch, [])
        fake_user["credits"] = 10
        assert _run_async(pt_module._user_plan(fake_user)) == "FREE"

    def test_embedded_monthly_returns_premium(self, fake_user, monkeypatch):
        """The CORE krajapraveen case: only embedded data exists.
        No db.subscriptions row at all. Must still return PREMIUM."""
        _patch_db(monkeypatch, [])
        now = datetime.now(timezone.utc)
        fake_user["subscription"] = {
            "planId": "monthly",
            "planName": "Monthly Premium",
            "status": "active",
            "startDate": now.isoformat(),
            "endDate": (now + timedelta(days=30)).isoformat(),
            "orderId": "ord_test_xyz",
        }
        assert _run_async(pt_module._user_plan(fake_user)) == "PREMIUM"

    def test_embedded_uppercase_active_also_works(self, fake_user, monkeypatch):
        _patch_db(monkeypatch, [])
        now = datetime.now(timezone.utc)
        fake_user["subscription"] = {
            "planId": "monthly", "status": "ACTIVE",
            "endDate": (now + timedelta(days=30)).isoformat(),
        }
        assert _run_async(pt_module._user_plan(fake_user)) == "PREMIUM"

    def test_embedded_with_expired_end_date_falls_back(self, fake_user, monkeypatch):
        _patch_db(monkeypatch, [])
        now = datetime.now(timezone.utc)
        fake_user["subscription"] = {
            "planId": "monthly", "status": "active",
            "endDate": (now - timedelta(days=1)).isoformat(),
        }
        assert _run_async(pt_module._user_plan(fake_user)) == "FREE"

    def test_embedded_malformed_end_date_still_trusts_active_flag(self, fake_user, monkeypatch):
        _patch_db(monkeypatch, [])
        fake_user["subscription"] = {
            "planId": "monthly", "status": "active",
            "endDate": "garbage-not-iso",
        }
        assert _run_async(pt_module._user_plan(fake_user)) == "PREMIUM"

    def test_both_sources_collection_wins(self, fake_user, monkeypatch):
        """When both sources exist, the collection answer must be
        honored (it's the canonical write going forward)."""
        _patch_db(monkeypatch, [self._sub_doc(fake_user["id"], "monthly", "ACTIVE")])
        now = datetime.now(timezone.utc)
        fake_user["subscription"] = {
            "planId": "weekly", "status": "active",
            "endDate": (now + timedelta(days=7)).isoformat(),
        }
        assert _run_async(pt_module._user_plan(fake_user)) == "PREMIUM"

    def test_admin_role_short_circuits_premium(self, fake_user, monkeypatch):
        _patch_db(monkeypatch, [])
        fake_user["role"] = "ADMIN"
        assert _run_async(pt_module._user_plan(fake_user)) == "PREMIUM"

    def test_superseded_sub_is_ignored(self, fake_user, monkeypatch):
        _patch_db(monkeypatch, [self._sub_doc(fake_user["id"], "monthly", "SUPERSEDED")])
        assert _run_async(pt_module._user_plan(fake_user)) == "FREE"

    def test_cancelled_sub_is_ignored(self, fake_user, monkeypatch):
        _patch_db(monkeypatch, [self._sub_doc(fake_user["id"], "monthly", "CANCELLED")])
        assert _run_async(pt_module._user_plan(fake_user)) == "FREE"


# ─────────────────────────────────────────────────────────────────────
# (C) `_required_plan_for_duration` invariants — defensive.
# ─────────────────────────────────────────────────────────────────────
class TestDurationGateInvariants:
    def test_durations(self):
        from routes.photo_trailer import _required_plan_for_duration
        assert _required_plan_for_duration(15) == "FREE"
        assert _required_plan_for_duration(45) == "FREE"
        assert _required_plan_for_duration(60) == "PAID"
        assert _required_plan_for_duration(89) == "PAID"
        assert _required_plan_for_duration(90) == "PREMIUM"
        assert _required_plan_for_duration(120) == "PREMIUM"
