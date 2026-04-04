/**
 * Pricing config — Single source of truth for frontend.
 * Must match backend config/pricing.py exactly.
 */

const PRICING = {
  INR: {
    symbol: '₹',
    code: 'INR',
    weekly: { price: 149, credits: 40, label: '₹149/week' },
    monthly: { price: 499, credits: 200, label: '₹499/month' },
    quarterly: { price: 1199, credits: 750, label: '₹1,199/quarter' },
    yearly: { price: 3999, credits: 3000, label: '₹3,999/year' },
    topups: [
      { id: 'topup_40', price: 99, credits: 40, label: '₹99' },
      { id: 'topup_120', price: 249, credits: 120, label: '₹249' },
      { id: 'topup_300', price: 499, credits: 300, label: '₹499', popular: true },
      { id: 'topup_700', price: 999, credits: 700, label: '₹999' },
    ],
    topupDesc: '40 credits from ₹99',
    subscribeDesc: '200 credits/mo + priority generation + HD downloads',
  },
};

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
