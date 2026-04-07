/**
 * k6 Production Load Test Suite — Visionary Suite
 * Mixed-workload model for 10,000 concurrent users.
 *
 * Traffic distribution:
 *   40% Landing/browse/explore (unauthenticated)
 *   15% Auth flows
 *   15% Dashboard/gallery/history
 *   10% Generation flows (story/image/video)
 *    5% Pricing/paywall/billing
 *    5% Asset preview/protected download
 *    5% Share/public pages
 *    5% Admin metrics (low %)
 *
 * Usage:
 *   k6 run --env BASE_URL=https://your-domain.com load-tests/mixed-workload.js
 */
import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('error_rate');
const pageLatency = new Trend('page_latency', true);
const apiLatency = new Trend('api_latency', true);
const genLatency = new Trend('generation_latency', true);
const queueAcceptLatency = new Trend('queue_accept_latency', true);
const httpFailures = new Counter('http_failures');
const timeouts = new Counter('timeouts');

// Thresholds
export const options = {
  thresholds: {
    'http_req_duration': ['p(95)<2500'],       // p95 under 2.5s
    'page_latency': ['p(95)<1500'],            // p95 page loads under 1.5s
    'api_latency': ['p(95)<2500'],             // p95 API calls under 2.5s
    'queue_accept_latency': ['p(95)<2000'],    // p95 queue acceptance under 2s
    'error_rate': ['rate<0.005'],              // Error rate under 0.5%
    'http_req_failed': ['rate<0.01'],          // HTTP failures under 1%
  },
  // Default: smoke test. Override with scenarios below.
  scenarios: {
    smoke: {
      executor: 'constant-vus',
      vus: 10,
      duration: '1m',
    },
  },
};

const BASE_URL = __ENV.BASE_URL || 'https://trust-engine-5.preview.emergentagent.com';
const TEST_EMAIL = __ENV.TEST_EMAIL || 'test@visionary-suite.com';
const TEST_PASS = __ENV.TEST_PASS || 'Test@2026#';
const ADMIN_EMAIL = __ENV.ADMIN_EMAIL || 'admin@creatorstudio.ai';
const ADMIN_PASS = __ENV.ADMIN_PASS || 'Cr3@t0rStud!o#2026';

function getToken(email, password) {
  const res = http.post(`${BASE_URL}/api/auth/login`, JSON.stringify({
    email: email,
    password: password,
  }), { headers: { 'Content-Type': 'application/json' }, timeout: '10s' });
  if (res.status === 200) {
    try { return JSON.parse(res.body).token; } catch { return null; }
  }
  return null;
}

function authHeaders(token) {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };
}

// ========== TRAFFIC FLOWS ==========

function landingBrowseFlow() {
  group('Landing & Browse', () => {
    // Landing page
    let r = http.get(`${BASE_URL}/`, { timeout: '10s' });
    pageLatency.add(r.timings.duration);
    check(r, { 'landing 200': (r) => r.status === 200 });
    errorRate.add(r.status >= 500);

    // Public API — social proof / trending
    r = http.get(`${BASE_URL}/api/streaks/social-proof`, { timeout: '5s' });
    apiLatency.add(r.timings.duration);
    check(r, { 'social-proof ok': (r) => r.status === 200 });
    errorRate.add(r.status >= 500);

    // Pricing plans
    r = http.get(`${BASE_URL}/api/pricing-catalog/plans`, { timeout: '5s' });
    apiLatency.add(r.timings.duration);
    check(r, { 'pricing ok': (r) => r.status === 200 });
    errorRate.add(r.status >= 500);

    // Funnel tracking
    r = http.post(`${BASE_URL}/api/funnel/track`, JSON.stringify({
      step: 'landing_view',
      session_id: `load-${__VU}-${__ITER}`,
      context: { source_page: 'landing', device: 'desktop' },
    }), { headers: { 'Content-Type': 'application/json' }, timeout: '5s' });
    apiLatency.add(r.timings.duration);
    errorRate.add(r.status >= 500);
  });
}

function authFlow() {
  group('Authentication', () => {
    // Login
    let r = http.post(`${BASE_URL}/api/auth/login`, JSON.stringify({
      email: TEST_EMAIL, password: TEST_PASS,
    }), { headers: { 'Content-Type': 'application/json' }, timeout: '10s' });
    apiLatency.add(r.timings.duration);
    check(r, { 'login 200': (r) => r.status === 200 });
    errorRate.add(r.status >= 500);

    // Profile
    if (r.status === 200) {
      const token = JSON.parse(r.body).token;
      r = http.get(`${BASE_URL}/api/auth/profile`, { headers: authHeaders(token), timeout: '5s' });
      apiLatency.add(r.timings.duration);
      check(r, { 'profile ok': (r) => r.status === 200 });
      errorRate.add(r.status >= 500);
    }
  });
}

function dashboardFlow() {
  group('Dashboard & Gallery', () => {
    const token = getToken(TEST_EMAIL, TEST_PASS);
    if (!token) { httpFailures.add(1); return; }
    const hdrs = authHeaders(token);

    // Credits
    let r = http.get(`${BASE_URL}/api/credits/balance`, { headers: hdrs, timeout: '5s' });
    apiLatency.add(r.timings.duration);
    check(r, { 'credits ok': (r) => r.status === 200 });
    errorRate.add(r.status >= 500);

    // My gallery
    r = http.get(`${BASE_URL}/api/gallery/my?limit=20`, { headers: hdrs, timeout: '10s' });
    apiLatency.add(r.timings.duration);
    errorRate.add(r.status >= 500);

    // Streak
    r = http.get(`${BASE_URL}/api/streaks/my`, { headers: hdrs, timeout: '5s' });
    apiLatency.add(r.timings.duration);
    errorRate.add(r.status >= 500);

    // Progress
    r = http.get(`${BASE_URL}/api/user-progress/my`, { headers: hdrs, timeout: '5s' });
    apiLatency.add(r.timings.duration);
    errorRate.add(r.status >= 500);
  });
}

function generationFlow() {
  group('Story Generation', () => {
    const token = getToken(TEST_EMAIL, TEST_PASS);
    if (!token) { httpFailures.add(1); return; }
    const hdrs = authHeaders(token);

    // Submit generation job
    let r = http.post(`${BASE_URL}/api/genstudio/generate`, JSON.stringify({
      tool: 'reel',
      theme: 'A brave cat on an adventure',
      style: 'pixar_3d',
      tone: 'comedy',
      duration: '15s',
    }), { headers: hdrs, timeout: '15s' });

    queueAcceptLatency.add(r.timings.duration);
    check(r, { 'gen accepted': (r) => r.status === 200 || r.status === 201 || r.status === 402 });
    errorRate.add(r.status >= 500);
    if (r.status >= 500) httpFailures.add(1);

    // Track funnel
    http.post(`${BASE_URL}/api/funnel/track`, JSON.stringify({
      step: 'generation_started',
      session_id: `load-${__VU}-${__ITER}`,
      context: { source_page: 'studio', device: 'desktop' },
    }), { headers: { 'Content-Type': 'application/json' }, timeout: '5s' });
  });
}

function pricingPaywallFlow() {
  group('Pricing & Paywall', () => {
    // Pricing plans (public)
    let r = http.get(`${BASE_URL}/api/pricing-catalog/plans`, { timeout: '5s' });
    apiLatency.add(r.timings.duration);
    check(r, { 'plans ok': (r) => r.status === 200 });
    errorRate.add(r.status >= 500);

    // Regional pricing
    r = http.get(`${BASE_URL}/api/pricing/plans`, { timeout: '5s' });
    apiLatency.add(r.timings.duration);
    errorRate.add(r.status >= 500);

    // Cashfree products
    const token = getToken(TEST_EMAIL, TEST_PASS);
    if (token) {
      r = http.get(`${BASE_URL}/api/cashfree/products`, {
        headers: authHeaders(token), timeout: '5s',
      });
      apiLatency.add(r.timings.duration);
      errorRate.add(r.status >= 500);
    }

    // Track paywall view
    http.post(`${BASE_URL}/api/funnel/track`, JSON.stringify({
      step: 'paywall_viewed',
      session_id: `load-${__VU}-${__ITER}`,
      context: { source_page: 'pricing', device: 'desktop' },
    }), { headers: { 'Content-Type': 'application/json' }, timeout: '5s' });
  });
}

function sharePublicFlow() {
  group('Share & Public Pages', () => {
    // Browse public content
    let r = http.get(`${BASE_URL}/api/public/featured?limit=10`, { timeout: '10s' });
    apiLatency.add(r.timings.duration);
    errorRate.add(r.status >= 500);

    // Public character page
    r = http.get(`${BASE_URL}/api/public/trending?limit=10`, { timeout: '10s' });
    apiLatency.add(r.timings.duration);
    errorRate.add(r.status >= 500);
  });
}

function adminFlow() {
  group('Admin Metrics', () => {
    const token = getToken(ADMIN_EMAIL, ADMIN_PASS);
    if (!token) return;
    const hdrs = authHeaders(token);

    // System health
    let r = http.get(`${BASE_URL}/api/admin/system-health/overview`, { headers: hdrs, timeout: '10s' });
    apiLatency.add(r.timings.duration);
    check(r, { 'health ok': (r) => r.status === 200 });
    errorRate.add(r.status >= 500);

    // Queue detail
    r = http.get(`${BASE_URL}/api/admin/system-health/queues`, { headers: hdrs, timeout: '10s' });
    apiLatency.add(r.timings.duration);
    errorRate.add(r.status >= 500);

    // Funnel metrics
    r = http.get(`${BASE_URL}/api/funnel/metrics?days=7`, { headers: hdrs, timeout: '10s' });
    apiLatency.add(r.timings.duration);
    errorRate.add(r.status >= 500);
  });
}

// ========== MAIN ==========

export default function () {
  // Distribute traffic according to model
  const roll = Math.random();

  if (roll < 0.40) {
    landingBrowseFlow();
  } else if (roll < 0.55) {
    authFlow();
  } else if (roll < 0.70) {
    dashboardFlow();
  } else if (roll < 0.80) {
    generationFlow();
  } else if (roll < 0.85) {
    pricingPaywallFlow();
  } else if (roll < 0.90) {
    sharePublicFlow();
  } else if (roll < 0.95) {
    landingBrowseFlow(); // asset preview substitute
  } else {
    adminFlow();
  }

  // Think time between iterations
  sleep(Math.random() * 2 + 1);
}
