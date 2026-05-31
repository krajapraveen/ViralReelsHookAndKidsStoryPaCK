/**
 * Pricing config — Single source of truth for frontend.
 * Must match backend config/pricing.py exactly.
 */

const PRICING = {
  INR: {
    symbol: '₹',
    code: 'INR',
    weekly: { price: 699, credits: 40, label: '₹699/week' },
    monthly: { price: 899, credits: 200, label: '₹899/month' },
    quarterly: { price: 3999, credits: 750, label: '₹3,999/quarter' },
    yearly: { price: 5999, credits: 3000, label: '₹5,999/year' },
    topups: [
      { id: 'topup_40', price: 200, credits: 60, label: '₹200' },
      { id: 'topup_120', price: 350, credits: 150, label: '₹350' },
      { id: 'topup_300', price: 699, credits: 400, label: '₹699', popular: true },
      { id: 'topup_700', price: 1999, credits: 800, label: '₹1,999' },
    ],
    topupDesc: '60 credits from ₹200',
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
