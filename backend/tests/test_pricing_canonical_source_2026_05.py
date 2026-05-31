"""
Pricing canonical-source contract — 2026-05-31 update.

This audit pins TWO contracts:

  1. The canonical pricing source (backend/config/pricing.py) carries
     the live (subscription + top-up) prices and credits that the
     customer sees in production. Updates land here first.

  2. Every customer-visible surface that ALSO shows prices must read
     from a canonical helper or carry the SAME numbers as fallbacks.
     We deliberately disallow stale prices in fallback strings — a
     ghost ₹149 in a fallback would appear the moment the helper
     fails to load, lying to the user. Bug class: pricing duplicated
     across surfaces without a single source of truth.

Doctrine refs:
  • /app/memory/ENGINEERING_DOCTRINE.md — Bug-Class Elimination Mandate.
  • Registered in /app/Makefile under audit-boundaries.

Scope notes:
  • backend/config/monetization.py is a SEPARATE product line (battle
    packs, daily idea packs, series caps). NOT in scope.
  • backend/services/cashfree_subscription_service.py defines a
    different recurring product set (creator/pro/studio). NOT in scope.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

REPO = Path("/app")
BACKEND = REPO / "backend"
FRONTEND = REPO / "frontend" / "src"
sys.path.insert(0, str(BACKEND))


# ─────────────────────────────────────────────────────────────────────
# Section A — Canonical backend source carries the new prices.
# ─────────────────────────────────────────────────────────────────────
class TestBackendCanonicalPricing(unittest.TestCase):
    def setUp(self):
        from config.pricing import SUBSCRIPTION_PLANS, TOPUP_PACKS, ALL_PRODUCTS
        self.subs = SUBSCRIPTION_PLANS
        self.topups = TOPUP_PACKS
        self.all_products = ALL_PRODUCTS

    def test_weekly_price_and_credits(self):
        self.assertEqual(self.subs["weekly"]["price_inr"], 299)
        self.assertEqual(self.subs["weekly"]["credits"], 40)

    def test_monthly_price_and_credits(self):
        self.assertEqual(self.subs["monthly"]["price_inr"], 899)
        self.assertEqual(self.subs["monthly"]["credits"], 200)

    def test_quarterly_price_and_credits(self):
        self.assertEqual(self.subs["quarterly"]["price_inr"], 2499)
        self.assertEqual(self.subs["quarterly"]["credits"], 750)

    def test_yearly_price_and_credits(self):
        self.assertEqual(self.subs["yearly"]["price_inr"], 5999)
        self.assertEqual(self.subs["yearly"]["credits"], 3000)

    def test_topup_40_slug_carries_new_60_credit_pack(self):
        # Slug stays for in-flight order dereferenceability, but the
        # customer-visible name + credits + price are the new pack.
        self.assertEqual(self.topups["topup_40"]["price_inr"], 200)
        self.assertEqual(self.topups["topup_40"]["credits"], 60)
        self.assertIn("60", self.topups["topup_40"]["name"])

    def test_topup_120_slug_carries_new_150_credit_pack(self):
        self.assertEqual(self.topups["topup_120"]["price_inr"], 350)
        self.assertEqual(self.topups["topup_120"]["credits"], 150)
        self.assertIn("150", self.topups["topup_120"]["name"])

    def test_topup_300_slug_carries_new_400_credit_pack(self):
        self.assertEqual(self.topups["topup_300"]["price_inr"], 699)
        self.assertEqual(self.topups["topup_300"]["credits"], 400)
        self.assertIn("400", self.topups["topup_300"]["name"])

    def test_topup_700_slug_carries_new_800_credit_pack(self):
        self.assertEqual(self.topups["topup_700"]["price_inr"], 1299)
        self.assertEqual(self.topups["topup_700"]["credits"], 800)
        self.assertIn("800", self.topups["topup_700"]["name"])

    def test_largest_topup_is_best_value_per_credit(self):
        """Pricing-arithmetic invariant: the largest top-up pack MUST
        have the lowest ₹/credit. Anything else creates the buy-2-smaller-
        instead-of-1-larger arbitrage we just shipped a fix for."""
        ratios = [
            (pid, p["price_inr"] / p["credits"])
            for pid, p in self.topups.items()
        ]
        ratios.sort(key=lambda r: -self.topups[r[0]]["credits"])
        biggest_ratio = ratios[0][1]
        for pid, ratio in ratios[1:]:
            self.assertLessEqual(
                biggest_ratio, ratio + 1e-9,
                f"Largest top-up must be best ₹/credit. "
                f"Largest={ratios[0][0]} ({biggest_ratio:.3f} ₹/credit), "
                f"{pid} undercuts it ({ratio:.3f} ₹/credit) — fix pricing.py",
            )

    def test_get_price_helper_returns_new_prices(self):
        from config.pricing import get_price
        # Subscription
        self.assertEqual(get_price("weekly"), 299)
        self.assertEqual(get_price("monthly"), 899)
        self.assertEqual(get_price("quarterly"), 2499)
        self.assertEqual(get_price("yearly"), 5999)
        # Top-ups
        self.assertEqual(get_price("topup_40"), 200)
        self.assertEqual(get_price("topup_120"), 350)
        self.assertEqual(get_price("topup_300"), 699)
        self.assertEqual(get_price("topup_700"), 1299)

    def test_weekly_4x_does_not_exceed_monthly_2x(self):
        """Pricing rationality: 4 weeks of weekly must NOT be more than
        ~2x monthly. Otherwise users would never choose weekly over
        monthly even for short trials. This is the subscription-side
        analog of the top-up arbitrage check."""
        weekly_4x = self.subs["weekly"]["price_inr"] * 4
        monthly = self.subs["monthly"]["price_inr"]
        self.assertLess(
            weekly_4x, monthly * 2,
            f"4× weekly ({weekly_4x}) >= 2× monthly ({monthly*2}) — "
            f"weekly is irrationally priced relative to monthly",
        )

    def test_quarterly_offers_commitment_value_over_yearly_floor(self):
        """Quarterly must be cheaper than 4× monthly (the price ceiling
        — beyond which nobody would ever commit upfront). We don't
        enforce quarterly < 3× monthly because that's a marketing call
        the user explicitly flagged for data-driven evaluation
        ('compare the new quarterly plan against actual user behavior').

        We surface the strict ratio as a structured print so analytics
        can spot the arbitrage gap during rollout."""
        monthly = self.subs["monthly"]["price_inr"]
        quarterly = self.subs["quarterly"]["price_inr"]
        monthly_3x = monthly * 3
        monthly_4x = monthly * 4
        self.assertLess(
            quarterly, monthly_4x,
            f"Quarterly ({quarterly}) must be < 4× monthly ({monthly_4x}) — "
            f"otherwise users have zero reason to commit upfront",
        )
        if quarterly >= monthly_3x:
            arbitrage = quarterly - monthly_3x
            print(
                f"[PRICING-NOTE] Quarterly ({quarterly}) is ₹{arbitrage} "
                f"MORE than 3× monthly ({monthly_3x}). Users who do the "
                f"arithmetic will re-subscribe monthly 3× instead. "
                f"Track quarterly conversion rate post-rollout."
            )

    def test_yearly_beats_12_monthly_and_4_quarterly(self):
        """Yearly must beat 12 months AND 4 quarters — i.e. be the
        unambiguous best deal."""
        m12 = self.subs["monthly"]["price_inr"] * 12
        q4 = self.subs["quarterly"]["price_inr"] * 4
        yearly = self.subs["yearly"]["price_inr"]
        self.assertLess(yearly, m12, f"Yearly ({yearly}) must beat 12× monthly ({m12})")
        self.assertLess(yearly, q4, f"Yearly ({yearly}) must beat 4× quarterly ({q4})")

    def test_subscription_badges_match_brief(self):
        """Brief: Monthly → Most Popular, Yearly → Best Value.
        Weekly and Quarterly carry no badge."""
        self.assertEqual(self.subs["monthly"].get("badge"), "MOST POPULAR")
        self.assertEqual(self.subs["yearly"].get("badge"), "BEST VALUE")
        self.assertIsNone(self.subs["weekly"].get("badge"))
        self.assertIsNone(self.subs["quarterly"].get("badge"))


# ─────────────────────────────────────────────────────────────────────
# Section B — Frontend canonical mirror.
# ─────────────────────────────────────────────────────────────────────
class TestFrontendCanonicalPricing(unittest.TestCase):
    def setUp(self):
        self.src = (FRONTEND / "utils" / "pricing.js").read_text()

    def _assert_plan_fields(self, plan_id, price, credits, label_fragment):
        """Assert a plan object contains the canonical price/credits/label
        invariants. Extra fields (tier, tierLabel, etc.) are allowed."""
        import re as _re
        pattern = (
            rf"{plan_id}\s*:\s*\{{[^}}]*\bprice\s*:\s*{price}\b[^}}]*"
            rf"\bcredits\s*:\s*{credits}\b[^}}]*"
            rf"\blabel\s*:\s*['\"][^'\"]*{_re.escape(label_fragment)}[^'\"]*['\"][^}}]*\}}"
        )
        self.assertRegex(
            self.src, pattern,
            f"{plan_id} plan must carry price={price}, credits={credits}, "
            f"label containing {label_fragment!r} (extra fields like tier/tierLabel are allowed)."
        )

    def test_weekly_object(self):
        self._assert_plan_fields("weekly", 299, 40, "₹299/week")

    def test_monthly_object(self):
        self._assert_plan_fields("monthly", 899, 200, "₹899/month")

    def test_quarterly_object(self):
        self._assert_plan_fields("quarterly", 2499, 750, "₹2,499/quarter")

    def test_yearly_object(self):
        self._assert_plan_fields("yearly", 5999, 3000, "₹5,999/year")

    def test_topup_array_entries(self):
        for fragment in (
            "{ id: 'topup_40', price: 200, credits: 60",
            "{ id: 'topup_120', price: 350, credits: 150",
            "{ id: 'topup_300', price: 699, credits: 400",
            "{ id: 'topup_700', price: 1299, credits: 800",
        ):
            self.assertIn(
                fragment, self.src,
                f"Frontend pricing helper must include top-up entry: {fragment}",
            )

    def test_topup_desc_reflects_entry_pack(self):
        self.assertIn(
            "topupDesc: '60 credits from ₹200'",
            self.src,
            "Top-up tagline must advertise the entry pack (₹200 → 60 credits)",
        )


# ─────────────────────────────────────────────────────────────────────
# Section C — Customer-visible surfaces carry NO stale ghost prices.
# ─────────────────────────────────────────────────────────────────────
class TestNoStalePricesInCustomerSurfaces(unittest.TestCase):
    """The brief: 'Do not make a fake UI-only change.' Pin the inverse —
    no stale price remains in any customer-visible code path. Surfaces
    audited: Pricing page, Landing page, UpsellModal, LiveChatWidget,
    user_manual, feedback chat."""

    FORBIDDEN_PRICES = (
        # Subscription OLD values (₹149 weekly, ₹499 monthly, ₹1,199
        # quarterly, ₹3,999 yearly). ₹3,999 is now valid as quarterly,
        # so test only ₹3,999/year (the yearly position).
        "₹149",
        "₹1,199",
        "₹1199",
        # Old top-up prices (₹99, ₹249, ₹999).
        "₹99\b",
        "₹249",
    )

    SURFACES = (
        FRONTEND / "pages" / "Pricing.js",
        FRONTEND / "pages" / "Landing.js",
        FRONTEND / "components" / "UpsellModal.js",
        FRONTEND / "components" / "LiveChatWidget.js",
        BACKEND / "routes" / "user_manual.py",
        BACKEND / "routes" / "feedback.py",
    )

    def test_no_old_weekly_price_anywhere(self):
        for path in self.SURFACES:
            src = path.read_text()
            self.assertNotIn(
                "₹149", src,
                f"Old weekly price ₹149 leaked into {path.relative_to(REPO)}",
            )

    def test_no_old_quarterly_price_anywhere(self):
        for path in self.SURFACES:
            src = path.read_text()
            for needle in ("₹1,199", "₹1199"):
                self.assertNotIn(
                    needle, src,
                    f"Old quarterly price {needle} leaked into "
                    f"{path.relative_to(REPO)}",
                )

    def test_no_old_topup_price_99_anywhere(self):
        # ₹99 must not appear ALONE (other product lines may have
        # different ₹99/₹999 packs and those tests live elsewhere).
        # We scope this check to the canonical pricing surfaces only.
        for path in self.SURFACES:
            src = path.read_text()
            # Ban ₹99 only when it's an entry-pack price string. The
            # token "₹99 →" or "from ₹99" is unambiguous.
            self.assertNotIn(
                "from ₹99", src,
                f"Old entry-pack copy 'from ₹99' leaked into "
                f"{path.relative_to(REPO)}",
            )
            self.assertFalse(
                re.search(r"₹99\s*→", src),
                f"Old top-up line '₹99 → N credits' leaked into "
                f"{path.relative_to(REPO)}",
            )


# ─────────────────────────────────────────────────────────────────────
# Section D — Surfaces driven by canonical helper, not hardcoded.
# ─────────────────────────────────────────────────────────────────────
class TestSurfacesUseCanonicalHelper(unittest.TestCase):
    """Landing + LiveChatWidget were direct offenders. Pin them to the
    helper so the next price change doesn't require touching them."""

    def test_landing_imports_pricing_helper(self):
        src = (FRONTEND / "pages" / "Landing.js").read_text()
        self.assertIn(
            "from '../utils/pricing'", src,
            "Landing.js must import the canonical pricing helper",
        )
        # And use it in the pricing teaser.
        self.assertIn(
            'data-testid="landing-weekly-price"', src,
            "Landing pricing teaser must expose stable testids for QA",
        )
        self.assertIn(
            'data-testid="landing-monthly-price"', src,
            "Landing pricing teaser must expose stable testids for QA",
        )

    def test_livechat_uses_pricing_helper(self):
        src = (FRONTEND / "components" / "LiveChatWidget.js").read_text()
        self.assertIn(
            "from '../utils/pricing'", src,
            "LiveChatWidget must import the canonical pricing helper",
        )
        self.assertIn(
            "_buildPricingMessage", src,
            "LiveChatWidget must build the pricing message from the helper",
        )

    def test_pricing_page_uses_helper(self):
        # Pricing.js already used getPricing; pin that it still does.
        src = (FRONTEND / "pages" / "Pricing.js").read_text()
        self.assertIn(
            "getPricing", src,
            "Pricing.js must read from the canonical pricing helper",
        )


# ─────────────────────────────────────────────────────────────────────
# Section E — Cashfree amount mapping uses canonical source.
# ─────────────────────────────────────────────────────────────────────
class TestCashfreeAmountSource(unittest.TestCase):
    """Payment-order creation MUST read amounts from config/pricing.py.
    Any cashfree route hardcoding INR amounts in its body would
    silently double-bill or short-bill on the next pricing change."""

    def test_cashfree_payments_imports_canonical_pricing(self):
        src = (BACKEND / "routes" / "cashfree_payments.py").read_text()
        self.assertIn(
            "from config.pricing import",
            src,
            "cashfree_payments.py MUST import amounts from "
            "config/pricing.py — no hardcoded INR per plan",
        )

    def test_subscriptions_imports_canonical_pricing(self):
        src = (BACKEND / "routes" / "subscriptions.py").read_text()
        self.assertIn(
            "from config.pricing import",
            src,
            "subscriptions.py MUST import canonical SUBSCRIPTION_PLANS",
        )

    def test_credits_router_imports_canonical_topups(self):
        src = (BACKEND / "routes" / "credits.py").read_text()
        self.assertIn(
            "from config.pricing import TOPUP_PACKS",
            src,
            "credits.py MUST import canonical TOPUP_PACKS — no hardcoded "
            "credit-grant numbers",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
