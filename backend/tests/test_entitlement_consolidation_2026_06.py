"""
P0 ENTITLEMENT CONSOLIDATION — Canonical subscription resolver (2026-06)
=========================================================================

Doctrine
--------
After 2026-06, **no route file may call `db.subscriptions.find_one`
directly for the purpose of entitlement gating.** All subscription
state reads MUST go through `services.entitlement`:

  • get_current_subscription(user_id)
  • get_user_subscription_tier(user_id)
  • is_premium_user(user_id)
  • is_active_subscriber(user_id)

This module exists because subscription state used to be split between
`db.subscriptions` (collection) and `users.subscription` (embedded),
with inconsistent status casing and inconsistent plan id sets across
feature gates. A paid Monthly user was silently gated from MyTrailer's
90s duration because the writer wrote to one store and the reader
read from the other.

What this file pins
-------------------
1. The entitlement module exists and exports the canonical helpers.
2. Plan-id classification — every plan id maps to the right tier:
      weekly                                   → STANDARD
      monthly | quarterly | yearly             → PREMIUM
      premium | pro | unlimited (legacy)       → PREMIUM (back-compat)
3. The helpers read BOTH `db.subscriptions` AND `users.subscription`,
   with case-insensitive status matching and endDate honoring.
4. **No route file** has a `db.subscriptions.find_one` for entitlement
   purposes. Allowed call sites are explicitly listed.
5. The 5 known-affected routes have been migrated:
      • routes/photo_trailer.py     (MyTrailer 90s gate)
      • routes/comix_ai.py          (comic download gate)
      • routes/daily_viral_ideas.py (viral-ideas pro gate)
      • routes/subscriptions.py:GET /current (Billing UI status)
      • routes/gif_maker.py         (gif download gate)
"""
import asyncio
import re
import sys
import uuid
import pathlib
from datetime import datetime, timezone, timedelta

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
BACKEND = REPO / "backend"
ENTITLEMENT_PY = BACKEND / "services" / "entitlement.py"

sys.path.insert(0, str(BACKEND))


def _read(p):
    assert p.exists(), f"required file missing: {p}"
    return p.read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────
# (A) Module contract — helpers exist and have the right shapes.
# ─────────────────────────────────────────────────────────────────────
class TestEntitlementModuleContract:
    def test_module_exists(self):
        assert ENTITLEMENT_PY.exists()

    def test_exports_get_user_subscription_tier(self):
        from services.entitlement import get_user_subscription_tier  # noqa: F401

    def test_exports_get_current_subscription(self):
        from services.entitlement import get_current_subscription  # noqa: F401

    def test_exports_is_premium_user(self):
        from services.entitlement import is_premium_user  # noqa: F401

    def test_exports_is_active_subscriber(self):
        from services.entitlement import is_active_subscriber  # noqa: F401

    def test_exports_plan_id_sets(self):
        from services.entitlement import (
            SUB_PREMIUM_PLAN_IDS, SUB_STANDARD_PLAN_IDS
        )
        # Founder canonical mapping.
        assert "monthly" in SUB_PREMIUM_PLAN_IDS
        assert "quarterly" in SUB_PREMIUM_PLAN_IDS
        assert "yearly" in SUB_PREMIUM_PLAN_IDS
        # Legacy back-compat.
        assert "premium" in SUB_PREMIUM_PLAN_IDS
        assert "pro" in SUB_PREMIUM_PLAN_IDS
        assert "unlimited" in SUB_PREMIUM_PLAN_IDS
        # Standard.
        assert SUB_STANDARD_PLAN_IDS == {"weekly"}


# ─────────────────────────────────────────────────────────────────────
# (B) Live classification via monkeypatched db.
# ─────────────────────────────────────────────────────────────────────
try:
    import services.entitlement as ent_module  # noqa: E402
    _live_ok = True
except Exception as _exc:  # noqa: BLE001
    print(f"[entitlement consolidation tests] import skipped: {_exc}")
    _live_ok = False


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class _FakeSubsCollection:
    def __init__(self, docs):
        self._docs = docs

    async def find_one(self, query, projection=None, **kwargs):  # noqa: ARG002
        user_id = query.get("userId")
        status_q = query.get("status")

        def _matches(doc):
            if doc.get("userId") != user_id:
                return False
            s = (doc.get("status") or "")
            if isinstance(status_q, dict) and "$regex" in status_q:
                return re.match(status_q["$regex"], s, re.IGNORECASE) is not None
            return s == status_q

        actives = [d for d in self._docs if _matches(d)]
        actives.sort(key=lambda d: d.get("createdAt", ""), reverse=True)
        return actives[0] if actives else None


class _FakeUsersCollection:
    def __init__(self, user_doc):
        self._doc = user_doc

    async def find_one(self, query, projection=None, **kwargs):  # noqa: ARG002
        if self._doc and self._doc.get("id") == query.get("id"):
            return dict(self._doc)
        return None


class _FakeDB:
    def __init__(self, subs_docs=None, user_doc=None):
        self.subscriptions = _FakeSubsCollection(subs_docs or [])
        self.users = _FakeUsersCollection(user_doc)


def _patch_db(monkeypatch, subs_docs=None, user_doc=None):
    """Patch the `shared.db` import that entitlement.py uses lazily."""
    import shared as shared_module
    monkeypatch.setattr(
        shared_module, "db", _FakeDB(subs_docs, user_doc), raising=False
    )


def _sub_doc(user_id, plan_id, status="ACTIVE", days_remaining=30):
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


@pytest.mark.skipif(not _live_ok, reason="backend imports unavailable")
class TestCanonicalResolver:
    """Comprehensive matrix of every documented scenario."""

    def test_collection_monthly_uppercase_active_premium(self, monkeypatch):
        uid = f"u_{uuid.uuid4().hex[:8]}"
        _patch_db(monkeypatch, subs_docs=[_sub_doc(uid, "monthly", "ACTIVE")])
        assert _run_async(ent_module.get_user_subscription_tier(uid)) == "PREMIUM"
        assert _run_async(ent_module.is_premium_user(uid)) is True

    def test_collection_monthly_lowercase_active_premium(self, monkeypatch):
        uid = f"u_{uuid.uuid4().hex[:8]}"
        _patch_db(monkeypatch, subs_docs=[_sub_doc(uid, "monthly", "active")])
        assert _run_async(ent_module.get_user_subscription_tier(uid)) == "PREMIUM"

    def test_collection_quarterly_premium(self, monkeypatch):
        uid = f"u_{uuid.uuid4().hex[:8]}"
        _patch_db(monkeypatch, subs_docs=[_sub_doc(uid, "quarterly")])
        assert _run_async(ent_module.is_premium_user(uid)) is True

    def test_collection_yearly_premium(self, monkeypatch):
        uid = f"u_{uuid.uuid4().hex[:8]}"
        _patch_db(monkeypatch, subs_docs=[_sub_doc(uid, "yearly")])
        assert _run_async(ent_module.is_premium_user(uid)) is True

    def test_collection_weekly_standard_not_premium(self, monkeypatch):
        uid = f"u_{uuid.uuid4().hex[:8]}"
        _patch_db(monkeypatch, subs_docs=[_sub_doc(uid, "weekly")])
        assert _run_async(ent_module.get_user_subscription_tier(uid)) == "STANDARD"
        assert _run_async(ent_module.is_premium_user(uid)) is False
        # Still an active subscriber.
        assert _run_async(ent_module.is_active_subscriber(uid)) is True

    def test_legacy_premium_plan_id_still_premium(self, monkeypatch):
        """daily_viral_ideas rows pre-2026-06 used `premium`/`pro`/`unlimited`."""
        for plan in ("premium", "pro", "unlimited"):
            uid = f"u_{uuid.uuid4().hex[:8]}"
            _patch_db(monkeypatch, subs_docs=[_sub_doc(uid, plan)])
            assert _run_async(ent_module.is_premium_user(uid)) is True, (
                f"legacy plan id {plan!r} must classify as PREMIUM"
            )

    def test_no_subscription_returns_free(self, monkeypatch):
        uid = f"u_{uuid.uuid4().hex[:8]}"
        _patch_db(monkeypatch, subs_docs=[], user_doc={"id": uid})
        assert _run_async(ent_module.get_user_subscription_tier(uid)) == "FREE"
        assert _run_async(ent_module.is_active_subscriber(uid)) is False

    def test_embedded_monthly_premium_KRAJAPRAVEEN(self, monkeypatch):
        """The CORE krajapraveen case: only embedded sub data exists.
        Must classify as PREMIUM via the embedded fallback."""
        uid = f"u_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        _patch_db(
            monkeypatch,
            subs_docs=[],
            user_doc={
                "id": uid,
                "subscription": {
                    "planId": "monthly",
                    "planName": "Monthly Premium",
                    "status": "active",
                    "endDate": (now + timedelta(days=30)).isoformat(),
                    "orderId": "ord_test_xyz",
                },
            },
        )
        assert _run_async(ent_module.is_premium_user(uid)) is True

    def test_embedded_expired_falls_back(self, monkeypatch):
        uid = f"u_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        _patch_db(
            monkeypatch,
            subs_docs=[],
            user_doc={
                "id": uid,
                "subscription": {
                    "planId": "monthly",
                    "status": "active",
                    "endDate": (now - timedelta(days=1)).isoformat(),
                },
            },
        )
        assert _run_async(ent_module.get_user_subscription_tier(uid)) == "FREE"

    def test_both_sources_collection_wins(self, monkeypatch):
        uid = f"u_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        _patch_db(
            monkeypatch,
            subs_docs=[_sub_doc(uid, "monthly", "ACTIVE")],
            user_doc={
                "id": uid,
                "subscription": {
                    "planId": "weekly",
                    "status": "active",
                    "endDate": (now + timedelta(days=7)).isoformat(),
                },
            },
        )
        # Collection (monthly/premium) wins over embedded (weekly).
        assert _run_async(ent_module.is_premium_user(uid)) is True

    def test_superseded_sub_ignored(self, monkeypatch):
        uid = f"u_{uuid.uuid4().hex[:8]}"
        _patch_db(
            monkeypatch,
            subs_docs=[_sub_doc(uid, "monthly", "SUPERSEDED")],
            user_doc={"id": uid},
        )
        assert _run_async(ent_module.is_premium_user(uid)) is False

    def test_cancelled_sub_ignored(self, monkeypatch):
        uid = f"u_{uuid.uuid4().hex[:8]}"
        _patch_db(
            monkeypatch,
            subs_docs=[_sub_doc(uid, "monthly", "CANCELLED")],
            user_doc={"id": uid},
        )
        assert _run_async(ent_module.is_premium_user(uid)) is False

    def test_get_current_subscription_returns_dict_shape(self, monkeypatch):
        """Callers expect `planId`, `status`, `endDate` keys regardless
        of which source the data came from."""
        uid = f"u_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        _patch_db(
            monkeypatch,
            subs_docs=[],
            user_doc={
                "id": uid,
                "subscription": {
                    "planId": "monthly",
                    "planName": "Monthly Premium",
                    "status": "active",
                    "endDate": (now + timedelta(days=30)).isoformat(),
                },
            },
        )
        sub = _run_async(ent_module.get_current_subscription(uid))
        assert sub is not None
        assert sub["planId"] == "monthly"
        assert sub["status"] == "ACTIVE"  # normalised to uppercase
        assert sub["_source"] == "embedded"  # diagnostic field

    def test_empty_user_id_returns_none(self, monkeypatch):
        _patch_db(monkeypatch, subs_docs=[], user_doc=None)
        assert _run_async(ent_module.get_current_subscription("")) is None
        assert _run_async(ent_module.get_user_subscription_tier("")) == "FREE"


# ─────────────────────────────────────────────────────────────────────
# (C) Migration audit — no route file calls db.subscriptions.find_one
#                       for entitlement purposes.
# ─────────────────────────────────────────────────────────────────────

# Files explicitly allowed to call `db.subscriptions.find_one` for
# non-entitlement reasons. Each entry MUST justify the exemption
# inline near the call site.
DB_SUBSCRIPTIONS_FIND_ALLOWLIST = {
    # The canonical resolver itself owns the read. Of course.
    "services/entitlement.py",
    # The writer paths read briefly to check for an existing row before
    # upsert / supersede. NOT entitlement reads.
    "services/cashfree_subscription_service.py",
    # The legacy subscriptions.py renewal/cancel handlers still
    # operate on specific subscription docs (by id, by orderId, by
    # gatewaySubscriptionId), not for entitlement gating. They were
    # NOT migrated in this sprint because they require a separate
    # CRUD/lifecycle refactor; left in the allowlist for now.
    "routes/subscriptions.py",
}


class TestNoBypassReadsFromRoutes:
    """No route file may bypass the canonical resolver. If a new file
    starts calling `db.subscriptions.find_one`, it must either go
    through the service OR be explicitly added to the allowlist."""

    def test_no_unauthorised_db_subscriptions_find(self):
        offenders = []
        backend_root = REPO / "backend"
        for path in (backend_root / "routes").rglob("*.py"):
            rel = str(path.relative_to(backend_root))
            if rel in DB_SUBSCRIPTIONS_FIND_ALLOWLIST:
                continue
            src = path.read_text(encoding="utf-8")
            for m in re.finditer(r"db\.subscriptions\.find_one\b", src):
                line_no = src[:m.start()].count("\n") + 1
                offenders.append(f"{rel}:{line_no}")
        assert not offenders, (
            "Route files calling `db.subscriptions.find_one` for "
            "entitlement purposes:\n  - " + "\n  - ".join(offenders) +
            "\nFix: route through `services.entitlement`."
        )


# ─────────────────────────────────────────────────────────────────────
# (D) Per-route migration contract.
# ─────────────────────────────────────────────────────────────────────
MIGRATED_ROUTES = [
    ("routes/photo_trailer.py",      "get_user_subscription_tier"),
    ("routes/comix_ai.py",           "is_active_subscriber"),
    ("routes/daily_viral_ideas.py",  "is_premium_user"),
    ("routes/subscriptions.py",      "get_current_subscription"),
    ("routes/gif_maker.py",          "is_active_subscriber"),
]


class TestMigratedRoutesUseService:
    @pytest.mark.parametrize(
        "rel,helper", MIGRATED_ROUTES, ids=[r[0] for r in MIGRATED_ROUTES]
    )
    def test_route_imports_canonical_helper(self, rel, helper):
        src = _read(REPO / "backend" / rel)
        # Helper must appear in source (either as import or in
        # subsequent `from services.entitlement import` call).
        assert helper in src and "services.entitlement" in src, (
            f"{rel} must import and use `{helper}` from "
            f"`services.entitlement`."
        )


# ─────────────────────────────────────────────────────────────────────
# (E) Direction-of-write contract (sanity).
# ─────────────────────────────────────────────────────────────────────
class TestWriteDirectionUnchanged:
    """The canonical writers are still writing both stores. This is
    paranoia coverage that the migration didn't accidentally break
    the writer side."""

    def test_cashfree_payments_still_dual_writes(self):
        src = _read(REPO / "backend" / "routes" / "cashfree_payments.py")
        assert "_activate_subscription_for_order" in src
        assert "db.subscriptions.update_one" in src
        assert "db.users.update_one" in src
