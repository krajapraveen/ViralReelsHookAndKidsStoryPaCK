/**
 * Geo-based currency detection and pricing config.
 * India users see INR, everyone else sees USD.
 */

const PRICING = {
  INR: {
    symbol: '₹',
    code: 'INR',
    creator: { price: 699, credits: 300, label: '₹699/month' },
    pro: { price: 1299, credits: 1000, label: '₹1,299/month' },
    topup: { price: 299, credits: 150, label: '₹299' },
    topupDesc: '150 credits from ₹299',
    subscribeDesc: '300 credits/mo + priority rendering',
  },
  USD: {
    symbol: '$',
    code: 'USD',
    creator: { price: 9, credits: 100, label: '$9/month' },
    pro: { price: 19, credits: 250, label: '$19/month' },
    topup: { price: 5, credits: 50, label: '$5' },
    topupDesc: '50 credits from $5',
    subscribeDesc: '100 credits/mo + priority rendering',
  },
};

function detectCountry() {
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || '';
    if (tz === 'Asia/Kolkata' || tz === 'Asia/Calcutta') return 'IN';
    const lang = navigator.language || '';
    if (lang.endsWith('-IN') || lang === 'hi') return 'IN';
  } catch {}
  return 'OTHER';
}

export function getCurrency() {
  const cached = sessionStorage.getItem('vs_currency');
  if (cached && PRICING[cached]) return cached;
  const country = detectCountry();
  const currency = country === 'IN' ? 'INR' : 'USD';
  sessionStorage.setItem('vs_currency', currency);
  return currency;
}

export function getPricing() {
  return PRICING[getCurrency()];
}

export function formatPrice(amount, currencyCode) {
  const code = currencyCode || getCurrency();
  const p = PRICING[code];
  return `${p.symbol}${amount.toLocaleString()}`;
}

export default PRICING;
