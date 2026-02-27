"""
Load Testing with k6 - Comprehensive Smoke and Stress Tests
Run with: k6 run k6-comprehensive.js
"""

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Counter, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const apiLatency = new Trend('api_latency');
const loginSuccess = new Counter('login_success');
const generationSuccess = new Counter('generation_success');

// Configuration
const BASE_URL = __ENV.BASE_URL || 'https://reaction-pack.preview.emergentagent.com';

export const options = {
  scenarios: {
    // Smoke test - light load
    smoke: {
      executor: 'constant-vus',
      vus: 5,
      duration: '1m',
      gracefulStop: '10s',
      tags: { test_type: 'smoke' },
      exec: 'smokeTest',
    },
    // Load test - normal load
    load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 50 },   // Ramp up
        { duration: '5m', target: 50 },   // Stay at 50
        { duration: '2m', target: 100 },  // Ramp up more
        { duration: '5m', target: 100 },  // Stay at 100
        { duration: '2m', target: 0 },    // Ramp down
      ],
      gracefulStop: '30s',
      tags: { test_type: 'load' },
      exec: 'loadTest',
      startTime: '2m', // Start after smoke test
    },
    // Stress test - find breaking point
    stress: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 100 },
        { duration: '3m', target: 200 },
        { duration: '3m', target: 300 },
        { duration: '3m', target: 400 },
        { duration: '5m', target: 500 },
        { duration: '2m', target: 0 },
      ],
      gracefulStop: '30s',
      tags: { test_type: 'stress' },
      exec: 'stressTest',
      startTime: '20m', // Start after load test
    },
    // Spike test - sudden traffic burst
    spike: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 10 },
        { duration: '30s', target: 500 },  // Spike!
        { duration: '1m', target: 500 },
        { duration: '30s', target: 10 },
        { duration: '30s', target: 0 },
      ],
      gracefulStop: '30s',
      tags: { test_type: 'spike' },
      exec: 'spikeTest',
      startTime: '40m', // Start after stress test
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<3000'], // 95% of requests under 3s
    http_req_failed: ['rate<0.1'],      // Less than 10% failures
    errors: ['rate<0.1'],
    api_latency: ['p(95)<2000'],
  },
};

// Test data
const testUsers = [
  { email: 'demo@example.com', password: 'Password123!' },
  { email: 'admin@creatorstudio.ai', password: 'Cr3@t0rStud!o#2026' },
];

// Helper functions
function getRandomUser() {
  return testUsers[Math.floor(Math.random() * testUsers.length)];
}

function login(email, password) {
  const payload = JSON.stringify({ email, password });
  const params = { headers: { 'Content-Type': 'application/json' } };
  
  const res = http.post(`${BASE_URL}/api/auth/login`, payload, params);
  
  if (res.status === 200) {
    const body = JSON.parse(res.body);
    loginSuccess.add(1);
    return body.token;
  }
  return null;
}

function authHeaders(token) {
  return {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  };
}

// Smoke Test - Basic functionality
export function smokeTest() {
  group('Health Check', () => {
    const res = http.get(`${BASE_URL}/api/health/`);
    check(res, {
      'health check status is 200': (r) => r.status === 200,
      'health check is healthy': (r) => r.json('status') === 'healthy',
    });
    apiLatency.add(res.timings.duration);
    errorRate.add(res.status !== 200);
  });

  group('Public Endpoints', () => {
    const endpoints = [
      '/api/pricing/plans',
      '/api/pricing/topups',
    ];
    
    endpoints.forEach(endpoint => {
      const res = http.get(`${BASE_URL}${endpoint}`);
      check(res, {
        [`${endpoint} responds`]: (r) => r.status === 200,
      });
      apiLatency.add(res.timings.duration);
    });
  });

  sleep(1);
}

// Load Test - Normal usage patterns
export function loadTest() {
  const user = getRandomUser();
  
  group('Authentication Flow', () => {
    // Login
    const token = login(user.email, user.password);
    
    if (token) {
      // Get wallet balance
      const walletRes = http.get(`${BASE_URL}/api/wallet/me`, authHeaders(token));
      check(walletRes, {
        'wallet balance retrieved': (r) => r.status === 200,
      });
      apiLatency.add(walletRes.timings.duration);
      
      // Get user stats
      const statsRes = http.get(`${BASE_URL}/api/analytics/user-stats`, authHeaders(token));
      check(statsRes, {
        'user stats retrieved': (r) => r.status === 200,
      });
      apiLatency.add(statsRes.timings.duration);
      
      // Browse features
      const features = [
        '/api/creator-tools/trending?niche=general&limit=5',
        '/api/coloring-book/templates',
        '/api/wallet/pricing',
      ];
      
      features.forEach(endpoint => {
        const res = http.get(`${BASE_URL}${endpoint}`, authHeaders(token));
        check(res, {
          [`${endpoint} works`]: (r) => r.status === 200,
        });
        apiLatency.add(res.timings.duration);
      });
    } else {
      errorRate.add(1);
    }
  });

  sleep(Math.random() * 3 + 1); // 1-4 seconds between iterations
}

// Stress Test - High load
export function stressTest() {
  const user = getRandomUser();
  
  group('High Load Operations', () => {
    const token = login(user.email, user.password);
    
    if (token) {
      // Simulate multiple API calls
      const endpoints = [
        '/api/wallet/me',
        '/api/credits/balance',
        '/api/analytics/user-stats',
        '/api/creator-tools/trending?niche=general&limit=5',
        '/api/wallet/pricing',
      ];
      
      endpoints.forEach(endpoint => {
        const res = http.get(`${BASE_URL}${endpoint}`, authHeaders(token));
        apiLatency.add(res.timings.duration);
        errorRate.add(res.status !== 200);
      });
    } else {
      errorRate.add(1);
    }
  });

  sleep(Math.random() * 2);
}

// Spike Test - Sudden traffic burst
export function spikeTest() {
  group('Spike Resilience', () => {
    // Just hit health and public endpoints rapidly
    const endpoints = [
      '/api/health/',
      '/api/pricing/plans',
    ];
    
    endpoints.forEach(endpoint => {
      const res = http.get(`${BASE_URL}${endpoint}`);
      apiLatency.add(res.timings.duration);
      errorRate.add(res.status !== 200);
    });
  });

  sleep(0.5);
}

// Summary report
export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'k6-summary.json': JSON.stringify(data),
  };
}

function textSummary(data, options) {
  let summary = '\n========== K6 LOAD TEST SUMMARY ==========\n\n';
  
  // Request metrics
  if (data.metrics.http_req_duration) {
    summary += `HTTP Request Duration:\n`;
    summary += `  - Average: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms\n`;
    summary += `  - P95: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms\n`;
    summary += `  - Max: ${data.metrics.http_req_duration.values.max.toFixed(2)}ms\n\n`;
  }
  
  // Error rate
  if (data.metrics.errors) {
    summary += `Error Rate: ${(data.metrics.errors.values.rate * 100).toFixed(2)}%\n`;
  }
  
  // Throughput
  if (data.metrics.http_reqs) {
    summary += `Total Requests: ${data.metrics.http_reqs.values.count}\n`;
    summary += `Requests/sec: ${data.metrics.http_reqs.values.rate.toFixed(2)}\n\n`;
  }
  
  // Custom metrics
  if (data.metrics.login_success) {
    summary += `Successful Logins: ${data.metrics.login_success.values.count}\n`;
  }
  
  summary += '\n==========================================\n';
  
  return summary;
}
