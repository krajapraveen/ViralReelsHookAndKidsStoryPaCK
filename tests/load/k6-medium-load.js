/**
 * CreatorStudio AI - Load Testing Script (k6)
 * Medium Load Test: 200 Concurrent Users
 * Tests all functionalities EXCEPT payment gateway
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Counter, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const successfulLogins = new Counter('successful_logins');
const apiLatency = new Trend('api_latency');

// Test configuration
export const options = {
  stages: [
    { duration: '30s', target: 50 },   // Ramp up to 50 users
    { duration: '1m', target: 100 },   // Ramp up to 100 users
    { duration: '2m', target: 200 },   // Ramp up to 200 users (peak)
    { duration: '3m', target: 200 },   // Stay at 200 users
    { duration: '1m', target: 100 },   // Ramp down to 100
    { duration: '30s', target: 0 },    // Ramp down to 0
  ],
  thresholds: {
    http_req_duration: ['p(95)<3000'],  // 95% of requests < 3s
    http_req_failed: ['rate<0.1'],      // Error rate < 10%
    errors: ['rate<0.1'],               // Custom error rate < 10%
  },
};

const BASE_URL = __ENV.BASE_URL || 'https://visionary-suite.com';

// Test user credentials (rotating)
const TEST_USERS = [
  { email: 'demo@example.com', password: 'Password123!' },
  { email: 'admin@creatorstudio.ai', password: 'Cr3@t0rStud!o#2026' },
];

// Helper to get random user
function getRandomUser() {
  return TEST_USERS[Math.floor(Math.random() * TEST_USERS.length)];
}

// Helper to make authenticated request
function authRequest(method, endpoint, token, body = null) {
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };
  
  const start = Date.now();
  let response;
  
  if (method === 'GET') {
    response = http.get(`${BASE_URL}${endpoint}`, { headers });
  } else if (method === 'POST') {
    response = http.post(`${BASE_URL}${endpoint}`, JSON.stringify(body), { headers });
  }
  
  apiLatency.add(Date.now() - start);
  return response;
}

export default function() {
  const user = getRandomUser();
  let token = null;
  
  // ========================================
  // GROUP 1: PUBLIC PAGES (No Auth Required)
  // ========================================
  group('Public Pages', function() {
    // Landing page
    let res = http.get(`${BASE_URL}/`);
    check(res, { 'Landing page loads': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
    
    // Pricing page
    res = http.get(`${BASE_URL}/pricing`);
    check(res, { 'Pricing page loads': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
    
    // Contact page
    res = http.get(`${BASE_URL}/contact`);
    check(res, { 'Contact page loads': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
    
    // User Manual
    res = http.get(`${BASE_URL}/user-manual`);
    check(res, { 'User Manual loads': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
    
    // API Health
    res = http.get(`${BASE_URL}/api/health/`);
    check(res, { 'API Health OK': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
  });
  
  sleep(1);
  
  // ========================================
  // GROUP 2: AUTHENTICATION
  // ========================================
  group('Authentication', function() {
    // Login
    const loginRes = http.post(`${BASE_URL}/api/auth/login`, JSON.stringify({
      email: user.email,
      password: user.password,
    }), {
      headers: { 'Content-Type': 'application/json' },
    });
    
    const loginSuccess = check(loginRes, { 
      'Login successful': (r) => r.status === 200 && r.json('token'),
    });
    
    if (loginSuccess) {
      token = loginRes.json('token');
      successfulLogins.add(1);
    }
    errorRate.add(!loginSuccess);
  });
  
  if (!token) {
    console.log('Login failed, skipping authenticated tests');
    return;
  }
  
  sleep(0.5);
  
  // ========================================
  // GROUP 3: DASHBOARD & WALLET
  // ========================================
  group('Dashboard & Wallet', function() {
    // Get user profile
    let res = authRequest('GET', '/api/auth/me', token);
    check(res, { 'Get user profile': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
    
    // Get wallet balance
    res = authRequest('GET', '/api/wallet/me', token);
    check(res, { 'Get wallet balance': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
    
    // Get user analytics
    res = authRequest('GET', '/api/analytics/user-stats', token);
    check(res, { 'Get user analytics': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
  });
  
  sleep(0.5);
  
  // ========================================
  // GROUP 4: GENSTUDIO
  // ========================================
  group('GenStudio', function() {
    // GenStudio Dashboard
    let res = authRequest('GET', '/api/genstudio/dashboard', token);
    check(res, { 'GenStudio dashboard loads': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
    
    // GenStudio Templates
    res = authRequest('GET', '/api/genstudio/templates', token);
    check(res, { 'GenStudio templates load': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
    
    // GenStudio History
    res = authRequest('GET', '/api/genstudio/history', token);
    check(res, { 'GenStudio history loads': (r) => r.status === 200 || r.status === 404 });
  });
  
  sleep(0.5);
  
  // ========================================
  // GROUP 5: STORY SERIES
  // ========================================
  group('Story Series', function() {
    // Get themes
    let res = authRequest('GET', '/api/story-series/themes', token);
    check(res, { 'Story themes load': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
    
    // Get pricing
    res = authRequest('GET', '/api/story-series/pricing', token);
    check(res, { 'Story pricing loads': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
    
    // Get history
    res = authRequest('GET', '/api/story-series/history?limit=5', token);
    check(res, { 'Story history loads': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
  });
  
  sleep(0.5);
  
  // ========================================
  // GROUP 6: CHALLENGE GENERATOR
  // ========================================
  group('Challenge Generator', function() {
    // Get platforms
    let res = authRequest('GET', '/api/challenge-generator/platforms', token);
    check(res, { 'Challenge platforms load': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
    
    // Get pricing
    res = authRequest('GET', '/api/challenge-generator/pricing', token);
    check(res, { 'Challenge pricing loads': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
    
    // Get history
    res = authRequest('GET', '/api/challenge-generator/history?limit=5', token);
    check(res, { 'Challenge history loads': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
  });
  
  sleep(0.5);
  
  // ========================================
  // GROUP 7: TONE SWITCHER
  // ========================================
  group('Tone Switcher', function() {
    // Get tones
    let res = authRequest('GET', '/api/tone-switcher/tones', token);
    check(res, { 'Tones list loads': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
    
    // Get pricing
    res = authRequest('GET', '/api/tone-switcher/pricing', token);
    check(res, { 'Tone pricing loads': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
    
    // Get history
    res = authRequest('GET', '/api/tone-switcher/history?limit=5', token);
    check(res, { 'Tone history loads': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
  });
  
  sleep(0.5);
  
  // ========================================
  // GROUP 8: COLORING BOOK
  // ========================================
  group('Coloring Book', function() {
    // Get pricing
    let res = authRequest('GET', '/api/coloring-book/pricing', token);
    check(res, { 'Coloring pricing loads': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
    
    // Get styles
    res = authRequest('GET', '/api/coloring-book/styles', token);
    check(res, { 'Coloring styles load': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
    
    // Get history
    res = authRequest('GET', '/api/coloring-book/history?limit=5', token);
    check(res, { 'Coloring history loads': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
  });
  
  sleep(0.5);
  
  // ========================================
  // GROUP 9: SUBSCRIPTIONS & BILLING (No Payment)
  // ========================================
  group('Subscriptions & Billing', function() {
    // Get subscription plans
    let res = authRequest('GET', '/api/subscriptions/plans', token);
    check(res, { 'Subscription plans load': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
    
    // Get current subscription
    res = authRequest('GET', '/api/subscriptions/current', token);
    check(res, { 'Current subscription loads': (r) => r.status === 200 || r.status === 404 });
    
    // Get products (Cashfree)
    res = http.get(`${BASE_URL}/api/cashfree/products`);
    check(res, { 'Products load': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
    
    // Get pricing plans with region
    res = http.get(`${BASE_URL}/api/pricing/plans?currency=INR`);
    check(res, { 'Regional pricing loads': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
  });
  
  sleep(0.5);
  
  // ========================================
  // GROUP 10: USER MANUAL & HELP
  // ========================================
  group('User Manual & Help', function() {
    // Get quick start guide
    let res = http.get(`${BASE_URL}/api/help/quick-start`);
    check(res, { 'Quick start loads': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
    
    // Get feature guides
    res = http.get(`${BASE_URL}/api/help/features`);
    check(res, { 'Feature guides load': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
    
    // Search help
    res = http.get(`${BASE_URL}/api/help/search?q=credits`);
    check(res, { 'Help search works': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
  });
  
  sleep(0.5);
  
  // ========================================
  // GROUP 11: PRIVACY & DATA
  // ========================================
  group('Privacy & Data', function() {
    // Get my data
    let res = authRequest('GET', '/api/privacy/my-data', token);
    check(res, { 'My data loads': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
    
    // Get privacy policy
    res = http.get(`${BASE_URL}/api/privacy/policy`);
    check(res, { 'Privacy policy loads': (r) => r.status === 200 || r.status === 404 });
  });
  
  sleep(1);
}

export function handleSummary(data) {
  return {
    '/app/test_reports/load_test_results.json': JSON.stringify(data, null, 2),
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
  };
}

function textSummary(data, options) {
  let summary = '\n========================================\n';
  summary += '   LOAD TEST SUMMARY - 200 USERS\n';
  summary += '========================================\n\n';
  
  summary += `Total Requests: ${data.metrics.http_reqs?.values?.count || 0}\n`;
  summary += `Success Rate: ${((1 - (data.metrics.http_req_failed?.values?.rate || 0)) * 100).toFixed(2)}%\n`;
  summary += `Avg Response Time: ${(data.metrics.http_req_duration?.values?.avg || 0).toFixed(2)}ms\n`;
  summary += `95th Percentile: ${(data.metrics.http_req_duration?.values?.['p(95)'] || 0).toFixed(2)}ms\n`;
  summary += `Successful Logins: ${data.metrics.successful_logins?.values?.count || 0}\n`;
  summary += `Error Rate: ${((data.metrics.errors?.values?.rate || 0) * 100).toFixed(2)}%\n`;
  
  return summary;
}
