/**
 * K6 Load Testing Suite for CreatorStudio AI
 * 
 * Installation: 
 *   brew install k6  (macOS)
 *   sudo apt install k6  (Linux)
 *   choco install k6  (Windows)
 * 
 * Usage:
 *   k6 run load_test.js
 *   k6 run --vus 100 --duration 30s load_test.js
 *   k6 run --out json=results.json load_test.js
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const loginTime = new Trend('login_time');
const reelGenTime = new Trend('reel_generation_time');
const storyGenTime = new Trend('story_generation_time');
const hashtagTime = new Trend('hashtag_fetch_time');
const carouselTime = new Trend('carousel_generation_time');
const apiCalls = new Counter('api_calls');

// Configuration
const BASE_URL = __ENV.BASE_URL || 'https://dashboard-stability.preview.emergentagent.com';

// Test scenarios configuration
export const options = {
  scenarios: {
    // Smoke test - Light load to verify system works
    smoke_test: {
      executor: 'constant-vus',
      vus: 1,
      duration: '30s',
      gracefulStop: '5s',
      startTime: '0s',
      tags: { test_type: 'smoke' },
    },
    
    // Load test - Normal expected load
    load_test: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m', target: 10 },   // Ramp up to 10 users
        { duration: '3m', target: 10 },   // Stay at 10 users
        { duration: '1m', target: 0 },    // Ramp down to 0
      ],
      gracefulStop: '10s',
      startTime: '30s',
      tags: { test_type: 'load' },
    },
    
    // Stress test - Beyond normal load
    stress_test: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 50 },   // Ramp up to 50 users
        { duration: '5m', target: 50 },   // Stay at 50 users
        { duration: '2m', target: 100 },  // Ramp up to 100 users
        { duration: '5m', target: 100 },  // Stay at 100 users
        { duration: '2m', target: 0 },    // Ramp down to 0
      ],
      gracefulStop: '30s',
      startTime: '5m30s',
      tags: { test_type: 'stress' },
    },
    
    // Spike test - Sudden traffic spikes
    spike_test: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 5 },    // Normal load
        { duration: '10s', target: 200 },  // Spike to 200 users
        { duration: '1m', target: 200 },   // Stay at spike
        { duration: '10s', target: 5 },    // Back to normal
        { duration: '30s', target: 5 },    // Normal load
        { duration: '10s', target: 0 },    // Ramp down
      ],
      gracefulStop: '30s',
      startTime: '21m30s',
      tags: { test_type: 'spike' },
    },
  },
  
  thresholds: {
    http_req_duration: ['p(95)<2000'],  // 95% of requests should be under 2s
    http_req_failed: ['rate<0.1'],      // Less than 10% failure rate
    errors: ['rate<0.1'],                // Custom error rate under 10%
    login_time: ['p(95)<1000'],          // Login should be under 1s
    reel_generation_time: ['p(95)<10000'], // Reel gen under 10s
  },
};

// Test user credentials
const TEST_USERS = [
  { email: 'demo@example.com', password: 'Password123!' },
  { email: 'loadtest1@example.com', password: 'LoadTest123!' },
  { email: 'loadtest2@example.com', password: 'LoadTest123!' },
];

// Helper function to get random user
function getRandomUser() {
  return TEST_USERS[Math.floor(Math.random() * TEST_USERS.length)];
}

// Helper function to make authenticated request
function authenticatedRequest(method, url, body, token) {
  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
  };
  
  apiCalls.add(1);
  
  if (method === 'GET') {
    return http.get(url, params);
  } else if (method === 'POST') {
    return http.post(url, JSON.stringify(body), params);
  } else if (method === 'PUT') {
    return http.put(url, JSON.stringify(body), params);
  }
}

// Main test function
export default function () {
  const user = getRandomUser();
  let token = null;
  
  // Group 1: Authentication
  group('Authentication Flow', function () {
    const loginPayload = {
      email: user.email,
      password: user.password,
    };
    
    const loginStart = new Date();
    const loginRes = http.post(
      `${BASE_URL}/api/auth/login`,
      JSON.stringify(loginPayload),
      { headers: { 'Content-Type': 'application/json' } }
    );
    loginTime.add(new Date() - loginStart);
    apiCalls.add(1);
    
    const loginSuccess = check(loginRes, {
      'login successful': (r) => r.status === 200,
      'has token': (r) => r.json('token') !== undefined,
    });
    
    errorRate.add(!loginSuccess);
    
    if (loginRes.status === 200) {
      token = loginRes.json('token');
    }
    
    sleep(1);
  });
  
  if (!token) {
    console.log('Login failed, skipping authenticated tests');
    return;
  }
  
  // Group 2: Dashboard & User Profile
  group('Dashboard Operations', function () {
    // Get user info
    const meRes = authenticatedRequest('GET', `${BASE_URL}/api/auth/me`, null, token);
    check(meRes, {
      'get user info': (r) => r.status === 200,
      'has credits': (r) => r.json('credits') !== undefined,
    });
    
    // Get credits
    const creditsRes = authenticatedRequest('GET', `${BASE_URL}/api/credits`, null, token);
    check(creditsRes, {
      'get credits': (r) => r.status === 200,
    });
    
    sleep(0.5);
  });
  
  // Group 3: Reel Generation (Heavy operation)
  group('Reel Generation', function () {
    const reelPayload = {
      topic: 'Morning routines for entrepreneurs',
      niche: 'Business',
      tone: 'Bold',
      duration: '30s',
      language: 'English',
    };
    
    const reelStart = new Date();
    const reelRes = authenticatedRequest('POST', `${BASE_URL}/api/generate/reel`, reelPayload, token);
    reelGenTime.add(new Date() - reelStart);
    
    const reelSuccess = check(reelRes, {
      'reel generation status': (r) => r.status === 200 || r.status === 402, // 402 = insufficient credits
    });
    
    errorRate.add(!reelSuccess);
    
    sleep(2);
  });
  
  // Group 4: Creator Tools (Lighter operations)
  group('Creator Tools - Hashtags', function () {
    const hashtagStart = new Date();
    const hashtagRes = authenticatedRequest('GET', `${BASE_URL}/api/creator-tools/hashtags/business`, null, token);
    hashtagTime.add(new Date() - hashtagStart);
    
    check(hashtagRes, {
      'hashtag fetch successful': (r) => r.status === 200,
      'has hashtags array': (r) => r.json('hashtags') !== undefined,
    });
    
    sleep(0.5);
  });
  
  // Group 5: Carousel Generation
  group('Creator Tools - Carousel', function () {
    const carouselStart = new Date();
    const carouselRes = authenticatedRequest(
      'POST',
      `${BASE_URL}/api/creator-tools/carousel?topic=5%20Tips%20for%20Success&niche=business&slides=5`,
      null,
      token
    );
    carouselTime.add(new Date() - carouselStart);
    
    check(carouselRes, {
      'carousel generation': (r) => r.status === 200 || r.status === 402,
    });
    
    sleep(1);
  });
  
  // Group 6: Trending Topics (Free, high-traffic)
  group('Trending Topics', function () {
    const trendingRes = authenticatedRequest('GET', `${BASE_URL}/api/creator-tools/trending`, null, token);
    check(trendingRes, {
      'trending fetch successful': (r) => r.status === 200,
    });
    
    sleep(0.5);
  });
  
  // Random sleep between iterations to simulate real user behavior
  sleep(Math.random() * 3 + 1);
}

// Setup function - runs once before test
export function setup() {
  console.log(`Starting load test against: ${BASE_URL}`);
  
  // Verify the API is accessible
  const healthRes = http.get(`${BASE_URL}/api/health`);
  if (healthRes.status !== 200) {
    throw new Error(`API health check failed: ${healthRes.status}`);
  }
  
  console.log('API health check passed');
  return { startTime: new Date().toISOString() };
}

// Teardown function - runs once after test
export function teardown(data) {
  console.log(`Load test completed. Started at: ${data.startTime}`);
  console.log(`Finished at: ${new Date().toISOString()}`);
}

// Summary handler
export function handleSummary(data) {
  const summary = {
    timestamp: new Date().toISOString(),
    totalRequests: data.metrics.http_reqs.values.count,
    failedRequests: data.metrics.http_req_failed.values.passes,
    avgResponseTime: data.metrics.http_req_duration.values.avg,
    p95ResponseTime: data.metrics.http_req_duration.values['p(95)'],
    maxResponseTime: data.metrics.http_req_duration.values.max,
    errorRate: data.metrics.errors?.values?.rate || 0,
  };
  
  return {
    'load_test_summary.json': JSON.stringify(summary, null, 2),
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
  };
}

// Import text summary for console output
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.1/index.js';
