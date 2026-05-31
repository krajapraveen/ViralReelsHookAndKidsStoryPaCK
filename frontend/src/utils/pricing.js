/**
 * Pricing config — Single source of truth for frontend.
 * Must match backend config/pricing.py exactly.
 */

const PRICING = {
  INR: {
    symbol: '₹',
    code: 'INR',
    weekly:    { price: 299,  credits: 40,   label: '₹299/week',     tier: 'Standard', tierLabel: 'Standard Plan' },
    monthly:   { price: 899,  credits: 200,  label: '₹899/month',    tier: 'Premium',  tierLabel: 'Premium Subscription' },
    quarterly: { price: 2499, credits: 750,  label: '₹2,499/quarter',tier: 'Premium',  tierLabel: 'Premium Subscription' },
    yearly:    { price: 5999, credits: 3000, label: '₹5,999/year',   tier: 'Premium',  tierLabel: 'Premium Subscription' },
    topups: [
      { id: 'topup_40', price: 200, credits: 60, label: '₹200' },
      { id: 'topup_120', price: 350, credits: 150, label: '₹350' },
      { id: 'topup_300', price: 699, credits: 400, label: '₹699', popular: true },
      { id: 'topup_700', price: 1299, credits: 800, label: '₹1,299', bestDeal: true },
    ],
    topupDesc: '60 credits from ₹200',
    subscribeDesc: '200 credits/mo + priority generation + HD downloads',
  },
};

// ─── Plan tier canonical helpers (P0 2026-06 entitlement clarity) ───
// Founder spec (visionary-suite, 2026-06):
//   Weekly    → Standard Plan
//   Monthly   → Premium Subscription
//   Quarterly → Premium Subscription
//   Yearly    → Premium Subscription
// 90-second trailers require Premium. 60-second trailers unlock via
// any active sub OR ≥35 credit balance. Used everywhere the UI talks
// about plan tiers so the answer to "which subscription is Premium?"
// is always consistent.
const PLAN_TIERS = {
  weekly:    { tier: 'Standard', tierLabel: 'Standard Plan' },
  monthly:   { tier: 'Premium',  tierLabel: 'Premium Subscription' },
  quarterly: { tier: 'Premium',  tierLabel: 'Premium Subscription' },
  yearly:    { tier: 'Premium',  tierLabel: 'Premium Subscription' },
};

/** Eligible plan ids for a tier (used by paywall copy). */
export const PREMIUM_PLAN_IDS = ['monthly', 'quarterly', 'yearly'];

/** Human-readable list of Premium-eligible plans for the paywall. */
export const PREMIUM_PLAN_NAMES = 'Monthly, Quarterly, or Yearly';

/** Get the tier label for a plan id. Defaults to `Standard Plan`. */
export function getPlanTier(planId) {
  return PLAN_TIERS[(planId || '').toLowerCase()] || { tier: 'Standard', tierLabel: 'Standard Plan' };
}

/** Is the given plan id a Premium subscription? */
export function isPremiumPlan(planId) {
  return getPlanTier(planId).tier === 'Premium';
}

export function getCurrency() {
  return 'INR';
}

export function getPricing() {
  return PRICING.INR;
}

export function formatPrice(amount) {
  return `₹${amount.toLocaleString('en-IN')}`;
}

export default PRICING;
