/**
 * K6 Large-Scale Stress Test for CreatorStudio AI
 * 
 * This script simulates thousands of concurrent users to test
 * system limits and identify breaking points.
 * 
 * WARNING: Only run this against staging/test environments!
 * 
 * Usage:
 *   k6 run stress_test_large_scale.js
 *   k6 run --out influxdb=http://localhost:8086/k6 stress_test_large_scale.js
 */

import http from 'k6/http';
import { check, sleep, group, fail } from 'k6';
import { Rate, Trend, Counter, Gauge } from 'k6/metrics';
import { SharedArray } from 'k6/data';

// Custom metrics
const errorRate = new Rate('errors');
const responseTime = new Trend('response_time');
const throughput = new Counter('throughput');
const activeUsers = new Gauge('active_users');

// Configuration
const BASE_URL = __ENV.BASE_URL || 'https://worker-scaling.preview.emergentagent.com';

// Test configuration for large-scale testing
export const options = {
  scenarios: {
    // Soak test - Extended duration testing
    soak_test: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '5m', target: 100 },   // Ramp up to 100 users
        { duration: '30m', target: 100 },  // Stay at 100 for 30 minutes
        { duration: '5m', target: 0 },     // Ramp down
      ],
      gracefulStop: '60s',
      tags: { test_type: 'soak' },
    },
    
    // Breakpoint test - Find the breaking point
    breakpoint_test: {
      executor: 'ramping-arrival-rate',
      startRate: 10,
      timeUnit: '1s',
      preAllocatedVUs: 500,
      maxVUs: 2000,
      stages: [
        { duration: '2m', target: 50 },    // 50 requests/sec
        { duration: '2m', target: 100 },   // 100 requests/sec
        { duration: '2m', target: 200 },   // 200 requests/sec
        { duration: '2m', target: 500 },   // 500 requests/sec
        { duration: '2m', target: 1000 },  // 1000 requests/sec
        { duration: '2m', target: 0 },     // Ramp down
      ],
      gracefulStop: '60s',
      startTime: '40m',
      tags: { test_type: 'breakpoint' },
    },
    
    // Concurrent users scaling test
    concurrent_scaling: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m', target: 100 },
        { duration: '2m', target: 100 },
        { duration: '1m', target: 500 },
        { duration: '2m', target: 500 },
        { duration: '1m', target: 1000 },
        { duration: '2m', target: 1000 },
        { duration: '1m', target: 2000 },
        { duration: '2m', target: 2000 },
        { duration: '2m', target: 0 },
      ],
      gracefulStop: '120s',
      startTime: '52m',
      tags: { test_type: 'concurrent_scaling' },
    },
  },
  
  thresholds: {
    http_req_duration: ['p(95)<5000', 'p(99)<10000'],
    http_req_failed: ['rate<0.15'],
    errors: ['rate<0.15'],
  },
  
  // Network settings for high concurrency
  batch: 20,
  batchPerHost: 10,
  httpDebug: 'full',
};

// Test endpoints weighted by typical usage
const ENDPOINTS = [
  { path: '/api/health', weight: 10, method: 'GET', auth: false },
  { path: '/api/auth/me', weight: 20, method: 'GET', auth: true },
  { path: '/api/credits', weight: 15, method: 'GET', auth: true },
  { path: '/api/creator-tools/hashtags/business', weight: 25, method: 'GET', auth: true },
  { path: '/api/creator-tools/trending', weight: 20, method: 'GET', auth: true },
  { path: '/api/creator-tools/carousel', weight: 5, method: 'POST', auth: true, query: '?topic=Test&niche=business&slides=5' },
  { path: '/api/generate/reel', weight: 5, method: 'POST', auth: true, body: { topic: 'Test', niche: 'Business' } },
];

// Weighted random selection
function selectEndpoint() {
  const totalWeight = ENDPOINTS.reduce((sum, e) => sum + e.weight, 0);
  let random = Math.random() * totalWeight;
  
  for (const endpoint of ENDPOINTS) {
    random -= endpoint.weight;
    if (random <= 0) return endpoint;
  }
  
  return ENDPOINTS[0];
}

// Global token cache (per VU)
let cachedToken = null;
let tokenExpiry = 0;

function getToken() {
  const now = Date.now();
  
  if (cachedToken && now < tokenExpiry) {
    return cachedToken;
  }
  
  const loginRes = http.post(
    `${BASE_URL}/api/auth/login`,
    JSON.stringify({ email: 'demo@example.com', password: 'Password123!' }),
    { headers: { 'Content-Type': 'application/json' } }
  );
  
  if (loginRes.status === 200) {
    cachedToken = loginRes.json('token');
    tokenExpiry = now + (55 * 60 * 1000); // 55 minutes (token usually valid for 1 hour)
    return cachedToken;
  }
  
  return null;
}

// Main test function
export default function () {
  activeUsers.add(1);
  
  const endpoint = selectEndpoint();
  let url = `${BASE_URL}${endpoint.path}${endpoint.query || ''}`;
  let params = { headers: { 'Content-Type': 'application/json' } };
  
  if (endpoint.auth) {
    const token = getToken();
    if (!token) {
      errorRate.add(1);
      activeUsers.add(-1);
      return;
    }
    params.headers['Authorization'] = `Bearer ${token}`;
  }
  
  const startTime = new Date();
  let res;
  
  if (endpoint.method === 'GET') {
    res = http.get(url, params);
  } else if (endpoint.method === 'POST') {
    res = http.post(url, endpoint.body ? JSON.stringify(endpoint.body) : null, params);
  }
  
  const duration = new Date() - startTime;
  responseTime.add(duration);
  throughput.add(1);
  
  const success = check(res, {
    'status is ok': (r) => r.status >= 200 && r.status < 500,
    'response time OK': () => duration < 5000,
  });
  
  errorRate.add(!success);
  activeUsers.add(-1);
  
  // Variable sleep to simulate real user think time
  sleep(Math.random() * 2 + 0.5);
}

// Setup
export function setup() {
  console.log('='.repeat(60));
  console.log('LARGE-SCALE STRESS TEST');
  console.log('='.repeat(60));
  console.log(`Target: ${BASE_URL}`);
  console.log(`Started: ${new Date().toISOString()}`);
  console.log('='.repeat(60));
  
  // Verify API is up
  const health = http.get(`${BASE_URL}/api/health`);
  if (health.status !== 200) {
    fail('API health check failed');
  }
  
  return { startTime: new Date().toISOString() };
}

// Teardown
export function teardown(data) {
  console.log('='.repeat(60));
  console.log('TEST COMPLETED');
  console.log(`Started: ${data.startTime}`);
  console.log(`Ended: ${new Date().toISOString()}`);
  console.log('='.repeat(60));
}

// Custom summary
export function handleSummary(data) {
  const results = {
    timestamp: new Date().toISOString(),
    testType: 'large_scale_stress',
    metrics: {
      totalRequests: data.metrics.http_reqs?.values?.count || 0,
      failedRequests: data.metrics.http_req_failed?.values?.passes || 0,
      errorRate: data.metrics.errors?.values?.rate || 0,
      responseTime: {
        avg: data.metrics.http_req_duration?.values?.avg || 0,
        min: data.metrics.http_req_duration?.values?.min || 0,
        max: data.metrics.http_req_duration?.values?.max || 0,
        p50: data.metrics.http_req_duration?.values?.['p(50)'] || 0,
        p90: data.metrics.http_req_duration?.values?.['p(90)'] || 0,
        p95: data.metrics.http_req_duration?.values?.['p(95)'] || 0,
        p99: data.metrics.http_req_duration?.values?.['p(99)'] || 0,
      },
      throughput: {
        total: data.metrics.throughput?.values?.count || 0,
        rate: data.metrics.throughput?.values?.rate || 0,
      },
    },
    thresholds: data.root_group?.checks || {},
  };
  
  return {
    'stress_test_results.json': JSON.stringify(results, null, 2),
    stdout: generateTextSummary(data),
  };
}

function generateTextSummary(data) {
  const metrics = data.metrics;
  let output = '\n';
  output += '╔════════════════════════════════════════════════════════════╗\n';
  output += '║           LARGE-SCALE STRESS TEST RESULTS                  ║\n';
  output += '╠════════════════════════════════════════════════════════════╣\n';
  output += `║ Total Requests:     ${(metrics.http_reqs?.values?.count || 0).toString().padStart(10)}                       ║\n`;
  output += `║ Failed Requests:    ${(metrics.http_req_failed?.values?.passes || 0).toString().padStart(10)}                       ║\n`;
  output += `║ Error Rate:         ${((metrics.errors?.values?.rate || 0) * 100).toFixed(2).padStart(9)}%                       ║\n`;
  output += '╠════════════════════════════════════════════════════════════╣\n';
  output += '║ Response Time (ms)                                         ║\n';
  output += `║   Average:          ${(metrics.http_req_duration?.values?.avg || 0).toFixed(2).padStart(10)}                       ║\n`;
  output += `║   p95:              ${(metrics.http_req_duration?.values?.['p(95)'] || 0).toFixed(2).padStart(10)}                       ║\n`;
  output += `║   p99:              ${(metrics.http_req_duration?.values?.['p(99)'] || 0).toFixed(2).padStart(10)}                       ║\n`;
  output += `║   Max:              ${(metrics.http_req_duration?.values?.max || 0).toFixed(2).padStart(10)}                       ║\n`;
  output += '╠════════════════════════════════════════════════════════════╣\n';
  output += `║ Throughput:         ${(metrics.throughput?.values?.rate || 0).toFixed(2).padStart(10)} req/s                 ║\n`;
  output += '╚════════════════════════════════════════════════════════════╝\n';
  
  return output;
}
