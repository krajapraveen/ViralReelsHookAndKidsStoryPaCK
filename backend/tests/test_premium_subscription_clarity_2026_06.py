"""
P0 UX/Entitlement Clarity — Premium Subscription naming audit (2026-06)
=======================================================================

Background
----------
Users seeing "90-second trailers need PREMIUM" had no way to map the
abstract tier word "PREMIUM" to a specific subscription on the pricing
page. The founder-canonical mapping is:

  Weekly    → Standard Plan
  Monthly   → Premium Subscription
  Quarterly → Premium Subscription
  Yearly    → Premium Subscription

This file pins the mapping in three layers:

  1. Canonical source — `frontend/src/utils/pricing.js` exports
     `getPlanTier()`, `PREMIUM_PLAN_IDS`, and `PREMIUM_PLAN_NAMES`.
  2. UI surfaces that render plan tier labels MUST consume the helper
     (Pricing page, Billing page, UpgradeModal, MyTrailer PaywallModal).
  3. Paywall copy MUST name the eligible subscription tier explicitly
     (no vague "need PREMIUM" headlines remain) AND name the
     eligible plans (Monthly, Quarterly, or Yearly) in the subtext.

Verified by node-harness execution + static-source audit.
"""
import json
import os
import pathlib
import re
import shutil
import subprocess

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
SRC = REPO / "frontend" / "src"
PRICING_JS = SRC / "utils" / "pricing.js"
PRICING_PAGE = SRC / "pages" / "Pricing.js"
BILLING_PAGE = SRC / "pages" / "Billing.js"
UPGRADE_MODAL = SRC / "components" / "UpgradeModal.js"
TRAILER_PAGE = SRC / "pages" / "PhotoTrailerPage.jsx"


def _read(p):
    assert p.exists(), f"required file missing: {p}"
    return p.read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────
# (1) Canonical helper exists and exports the spec mapping.
# ─────────────────────────────────────────────────────────────────────
class TestPricingHelperContract:
    def test_pricing_js_exports_getPlanTier(self):
        src = _read(PRICING_JS)
        assert "export function getPlanTier" in src, (
            "frontend/src/utils/pricing.js must export getPlanTier."
        )

    def test_pricing_js_exports_premium_plan_ids(self):
        src = _read(PRICING_JS)
        assert "export const PREMIUM_PLAN_IDS" in src, (
            "pricing.js must export PREMIUM_PLAN_IDS."
        )

    def test_pricing_js_exports_premium_plan_names(self):
        src = _read(PRICING_JS)
        assert "export const PREMIUM_PLAN_NAMES" in src, (
            "pricing.js must export PREMIUM_PLAN_NAMES."
        )
        # Founder-spec value.
        assert "'Monthly, Quarterly, or Yearly'" in src or \
               '"Monthly, Quarterly, or Yearly"' in src, (
            "PREMIUM_PLAN_NAMES must be exactly "
            "'Monthly, Quarterly, or Yearly'."
        )

    def test_canonical_mapping_lives_in_source(self):
        """Eyeball check — every plan id appears with its founder-spec
        tier label so a casual code review can verify the mapping."""
        src = _read(PRICING_JS)
        # The PLAN_TIERS object must contain all four plan ids.
        for plan_id in ("weekly", "monthly", "quarterly", "yearly"):
            assert plan_id in src, f"pricing.js missing plan id '{plan_id}'"
        # Founder labels must appear verbatim.
        assert "'Standard Plan'" in src or '"Standard Plan"' in src
        assert "'Premium Subscription'" in src or '"Premium Subscription"' in src


# ─────────────────────────────────────────────────────────────────────
# (2) Live execution of getPlanTier — confirms the mapping is correct.
# ─────────────────────────────────────────────────────────────────────
NODE_HARNESS = """
import fs from 'node:fs';
const src = fs.readFileSync(%(path)r, 'utf8');
const code = src
  .replace(/export function /g, 'function ')
  .replace(/export const /g, 'const ')
  .replace(/export default[^;]+;?/g, '');
const ctx = {};
const wrapped = '(function(){' + code +
  '; this.getPlanTier = getPlanTier;' +
  '  this.PREMIUM_PLAN_IDS = PREMIUM_PLAN_IDS;' +
  '  this.PREMIUM_PLAN_NAMES = PREMIUM_PLAN_NAMES;' +
  '  this.isPremiumPlan = isPremiumPlan;' +
  '}).call(ctx);';
// eslint-disable-next-line no-eval
eval(wrapped);
const out = {
  tiers: {
    weekly:    ctx.getPlanTier('weekly'),
    monthly:   ctx.getPlanTier('monthly'),
    quarterly: ctx.getPlanTier('quarterly'),
    yearly:    ctx.getPlanTier('yearly'),
    unknown:   ctx.getPlanTier('not-a-plan'),
    nullish:   ctx.getPlanTier(null),
  },
  premiumIds: ctx.PREMIUM_PLAN_IDS,
  premiumNames: ctx.PREMIUM_PLAN_NAMES,
  isPremium: {
    weekly: ctx.isPremiumPlan('weekly'),
    monthly: ctx.isPremiumPlan('monthly'),
    quarterly: ctx.isPremiumPlan('quarterly'),
    yearly: ctx.isPremiumPlan('yearly'),
  }
};
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def helper_runtime():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not available — static checks still cover the contract.")
    proc = subprocess.run(
        [node, "--input-type=module", "-e", NODE_HARNESS % {"path": str(PRICING_JS)}],
        capture_output=True, text=True, timeout=10,
    )
    assert proc.returncode == 0, f"node harness failed: {proc.stderr}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


class TestGetPlanTierLive:
    def test_weekly_is_standard(self, helper_runtime):
        assert helper_runtime["tiers"]["weekly"] == {
            "tier": "Standard", "tierLabel": "Standard Plan"
        }

    def test_monthly_is_premium(self, helper_runtime):
        assert helper_runtime["tiers"]["monthly"] == {
            "tier": "Premium", "tierLabel": "Premium Subscription"
        }

    def test_quarterly_is_premium(self, helper_runtime):
        assert helper_runtime["tiers"]["quarterly"] == {
            "tier": "Premium", "tierLabel": "Premium Subscription"
        }

    def test_yearly_is_premium(self, helper_runtime):
        assert helper_runtime["tiers"]["yearly"] == {
            "tier": "Premium", "tierLabel": "Premium Subscription"
        }

    def test_unknown_defaults_to_standard(self, helper_runtime):
        # Default safe fallback so unknown ids never accidentally
        # render as "Premium" in the UI.
        assert helper_runtime["tiers"]["unknown"]["tier"] == "Standard"
        assert helper_runtime["tiers"]["nullish"]["tier"] == "Standard"

    def test_premium_ids_match_spec(self, helper_runtime):
        assert sorted(helper_runtime["premiumIds"]) == [
            "monthly", "quarterly", "yearly"
        ]

    def test_premium_names_match_spec(self, helper_runtime):
        assert helper_runtime["premiumNames"] == "Monthly, Quarterly, or Yearly"

    def test_is_premium_plan(self, helper_runtime):
        ip = helper_runtime["isPremium"]
        assert ip["weekly"] is False
        assert ip["monthly"] is True
        assert ip["quarterly"] is True
        assert ip["yearly"] is True


# ─────────────────────────────────────────────────────────────────────
# (3) Every plan-card UI consumes the canonical helper.
# ─────────────────────────────────────────────────────────────────────
SURFACES_THAT_RENDER_PLAN_CARDS = [
    ("pages/Pricing.js",          "plan-{id}-tier-label"),
    ("pages/Billing.js",          "buy-{id}-tier-label"),
    ("components/UpgradeModal.js","paywall-plan-{id}-tier-label"),
]


class TestSurfacesUseCanonicalHelper:
    @pytest.mark.parametrize(
        "rel,testid_template",
        SURFACES_THAT_RENDER_PLAN_CARDS,
        ids=[s[0] for s in SURFACES_THAT_RENDER_PLAN_CARDS],
    )
    def test_imports_helper(self, rel, testid_template):
        src = _read(SRC / rel)
        assert "getPlanTier" in src, (
            f"{rel} must import and use `getPlanTier` from "
            f"`../utils/pricing` (or appropriate relative path)."
        )

    @pytest.mark.parametrize(
        "rel,testid_template",
        SURFACES_THAT_RENDER_PLAN_CARDS,
        ids=[s[0] for s in SURFACES_THAT_RENDER_PLAN_CARDS],
    )
    def test_renders_tier_label_testid(self, rel, testid_template):
        src = _read(SRC / rel)
        # The tier-label test-id pattern must appear in source. We
        # accept the test-id template literal form too (covers ${plan.id}).
        # The simplest check: the suffix `-tier-label` must appear.
        assert "-tier-label" in src, (
            f"{rel} must render a tier-label element with a "
            f"`data-testid` containing `-tier-label`. Template was: "
            f"{testid_template!r}"
        )


# ─────────────────────────────────────────────────────────────────────
# (4) MyTrailer paywall copy contract.
# ─────────────────────────────────────────────────────────────────────
class TestTrailerPaywallCopy:
    """The 90-second trailer paywall MUST:
    
      (a) name the eligible subscription tier explicitly
          ("require a Premium Subscription") — not the vague
          "need PREMIUM" copy that started this whole task.
      (b) name the eligible subscription plans in the subtext
          ("Monthly, Quarterly, or Yearly").
      (c) explain the credit/subscription distinction
          ("Credits are still used when you generate.").
    """

    def test_no_legacy_vague_premium_copy(self):
        src = _read(TRAILER_PAGE)
        # The literal headline `${dur}-second trailers need ${tier}`
        # must be gone.
        assert "-second trailers need ${tier}" not in src, (
            "PhotoTrailerPage.jsx still uses the legacy "
            "`${dur}-second trailers need ${tier}` headline."
        )
        assert "trailers need PREMIUM" not in src, (
            "PhotoTrailerPage.jsx still contains the vague "
            "'trailers need PREMIUM' copy."
        )

    def test_headline_uses_subscription_word(self):
        src = _read(TRAILER_PAGE)
        # The new headline format includes "require a ${subscriptionWord}".
        assert re.search(
            r"require a \$\{subscriptionWord\}",
            src,
        ), (
            "PhotoTrailerPage.jsx PaywallModal headline must say "
            "`require a ${subscriptionWord}` so the subscription tier "
            "is named explicitly."
        )

    def test_subscription_word_resolves_to_premium_subscription(self):
        src = _read(TRAILER_PAGE)
        # subscriptionWord ternary must include 'Premium Subscription'.
        assert "'Premium Subscription'" in src, (
            "PhotoTrailerPage.jsx must use the canonical "
            "'Premium Subscription' label."
        )

    def test_subtext_names_eligible_plans(self):
        src = _read(TRAILER_PAGE)
        # Subtext must reference PREMIUM_PLAN_NAMES.
        assert "PREMIUM_PLAN_NAMES" in src, (
            "PhotoTrailerPage.jsx PaywallModal must use "
            "PREMIUM_PLAN_NAMES from utils/pricing in the subtext."
        )

    def test_subtext_explains_credit_distinction(self):
        src = _read(TRAILER_PAGE)
        # Either of these two phrasings is accepted.
        ok = (
            "Credits are still used when you generate" in src
            or "Credits alone do not unlock" in src
        )
        assert ok, (
            "PhotoTrailerPage.jsx PaywallModal must explain the "
            "credit/subscription distinction in the subtext."
        )

    def test_trailer_paywall_subtext_testid_exists(self):
        src = _read(TRAILER_PAGE)
        assert 'data-testid="trailer-paywall-subtext"' in src, (
            "PaywallModal must expose a `trailer-paywall-subtext` "
            "data-testid so the regression suite can hook into it."
        )


# ─────────────────────────────────────────────────────────────────────
# (5) Backend 402 message also names the eligible plans.
# ─────────────────────────────────────────────────────────────────────
class TestBackend402Copy:
    """The server-side `UPGRADE_REQUIRED` 402 response is what a
    direct-curl user (or an attacker bypassing the JS) sees. It MUST
    carry the same canonical copy."""

    def test_backend_message_uses_premium_subscription_phrase(self):
        path = REPO / "backend" / "routes" / "photo_trailer.py"
        src = path.read_text(encoding="utf-8")
        # The UPGRADE_REQUIRED detail must mention "Premium Subscription".
        assert "Premium Subscription" in src, (
            "backend/routes/photo_trailer.py 402 response must use "
            "the canonical phrase 'Premium Subscription'."
        )

    def test_backend_message_names_eligible_plans(self):
        path = REPO / "backend" / "routes" / "photo_trailer.py"
        src = path.read_text(encoding="utf-8")
        assert "Monthly, Quarterly, or Yearly" in src, (
            "backend/routes/photo_trailer.py 402 response must name "
            "the eligible subscription plans for clarity."
        )

    def test_backend_message_explains_credit_distinction(self):
        path = REPO / "backend" / "routes" / "photo_trailer.py"
        src = path.read_text(encoding="utf-8")
        assert "Credits are still used when you generate" in src, (
            "backend/routes/photo_trailer.py 402 response must spell "
            "out the credit/subscription distinction."
        )


# ─────────────────────────────────────────────────────────────────────
# (6) Anti-regression: no vague "need PREMIUM" copy anywhere.
# ─────────────────────────────────────────────────────────────────────
class TestNoVaguePremiumCopyRemains:
    """Catch-all scan of the entire frontend tree for any
    user-facing string of the form 'need PREMIUM' (which was the
    original confusing copy that started this task)."""

    def test_no_user_facing_need_premium_string(self):
        offenders = []
        for path in SRC.rglob("*.js"):
            self._scan(path, offenders)
        for path in SRC.rglob("*.jsx"):
            self._scan(path, offenders)
        assert not offenders, (
            "Found legacy 'need PREMIUM' copy in user-facing source:\n"
            "  - " + "\n  - ".join(offenders) +
            "\nFix: use the canonical 'require a Premium Subscription' "
            "phrasing."
        )

    def _scan(self, path, offenders):
        try:
            src = path.read_text(encoding="utf-8")
        except Exception:
            return
        rel = str(path.relative_to(SRC))
        for m in re.finditer(r"\bneed\s+PREMIUM\b", src):
            line_no = src[:m.start()].count("\n") + 1
            # Exclude comments to allow code-history references.
            line = src.split("\n")[line_no - 1]
            stripped = line.strip()
            if stripped.startswith(("//", "*", "/*")):
                continue
            offenders.append(f"{rel}:{line_no}  {line.strip()[:100]}")
