/**
 * K6 Load Testing Script for CreatorStudio AI
 * Tests API performance under load
 * 
 * Run: k6 run --out json=results.json load-test.js
 * Run with cloud: k6 cloud load-test.js
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// Custom metrics for monitoring dashboard
const apiErrors = new Counter('api_errors');
const apiLatency = new Trend('api_latency', true);
const successRate = new Rate('success_rate');

// Test configuration
export const options = {
  // Stages define the load profile
  stages: [
    { duration: '1m', target: 10 },   // Ramp up to 10 users over 1 min
    { duration: '3m', target: 50 },   // Ramp up to 50 users over 3 min
    { duration: '5m', target: 50 },   // Stay at 50 users for 5 min
    { duration: '2m', target: 100 },  // Spike to 100 users
    { duration: '3m', target: 100 },  // Stay at 100 users for 3 min
    { duration: '2m', target: 0 },    // Ramp down to 0 users
  ],
  
  // Thresholds for pass/fail
  thresholds: {
    http_req_duration: ['p(95)<2000'],  // 95% of requests should be under 2s
    http_req_failed: ['rate<0.05'],      // Less than 5% failure rate
    success_rate: ['rate>0.95'],         // 95% success rate
    api_latency: ['p(95)<1500'],         // Custom metric threshold
  },
  
  // Cloud/InfluxDB output for monitoring dashboard
  // Uncomment for cloud execution
  // cloud: {
  //   projectID: 12345,
  //   name: 'CreatorStudio Load Test'
  // }
};

// Base URL from environment or default
const BASE_URL = __ENV.BASE_URL || 'https://legacy-user-fix.preview.emergentagent.com';

// Test user credentials
const TEST_USER = {
  email: 'demo@example.com',
  password: 'Password123!'
};

// Helper function for authenticated requests
function getAuthHeaders(token) {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  };
}

// Helper to record metrics
function recordMetrics(response, endpoint) {
  const success = response.status >= 200 && response.status < 400;
  successRate.add(success);
  apiLatency.add(response.timings.duration);
  
  if (!success) {
    apiErrors.add(1);
    console.log(`ERROR: ${endpoint} - Status: ${response.status}`);
  }
  
  return success;
}

export default function() {
  let authToken = null;

  // ==========================================
  // Authentication Flow
  // ==========================================
  group('Authentication', function() {
    // Health Check
    group('Health Check', function() {
      const healthRes = http.get(`${BASE_URL}/api/health`);
      check(healthRes, {
        'health check status is 200': (r) => r.status === 200,
      });
      recordMetrics(healthRes, '/api/health');
    });

    // Login
    group('Login', function() {
      const loginRes = http.post(
        `${BASE_URL}/api/auth/login`,
        JSON.stringify({
          email: TEST_USER.email,
          password: TEST_USER.password
        }),
        { headers: { 'Content-Type': 'application/json' } }
      );
      
      const loginSuccess = check(loginRes, {
        'login status is 200': (r) => r.status === 200,
        'login returns token': (r) => r.json('token') !== undefined,
      });
      
      recordMetrics(loginRes, '/api/auth/login');
      
      if (loginSuccess) {
        authToken = loginRes.json('token');
      }
    });
    
    sleep(1);
  });

  // Skip remaining tests if auth failed
  if (!authToken) {
    console.log('Authentication failed, skipping authenticated tests');
    return;
  }

  const headers = getAuthHeaders(authToken);

  // ==========================================
  // Dashboard APIs
  // ==========================================
  group('Dashboard APIs', function() {
    // User Profile
    group('Get User Profile', function() {
      const profileRes = http.get(`${BASE_URL}/api/auth/profile`, { headers });
      check(profileRes, {
        'profile status is 200': (r) => r.status === 200,
        'profile has user data': (r) => r.json('name') !== undefined,
      });
      recordMetrics(profileRes, '/api/auth/profile');
    });

    // Credits
    group('Get Credits', function() {
      const creditsRes = http.get(`${BASE_URL}/api/credits`, { headers });
      check(creditsRes, {
        'credits status is 200': (r) => r.status === 200,
        'credits has balance': (r) => r.json('balance') !== undefined,
      });
      recordMetrics(creditsRes, '/api/credits');
    });
    
    sleep(0.5);
  });

  // ==========================================
  // Content Generation APIs
  // ==========================================
  group('Content Generation APIs', function() {
    // Comix AI Styles
    group('Get Comix Styles', function() {
      const stylesRes = http.get(`${BASE_URL}/api/comix/styles`, { headers });
      check(stylesRes, {
        'comix styles status is 200': (r) => r.status === 200,
      });
      recordMetrics(stylesRes, '/api/comix/styles');
    });

    // GIF Maker Styles
    group('Get GIF Styles', function() {
      const gifStylesRes = http.get(`${BASE_URL}/api/gif-maker/styles`, { headers });
      check(gifStylesRes, {
        'gif styles status is 200': (r) => r.status === 200,
      });
      recordMetrics(gifStylesRes, '/api/gif-maker/styles');
    });

    // GenStudio Templates
    group('Get GenStudio Templates', function() {
      const templatesRes = http.get(`${BASE_URL}/api/genstudio/templates`, { headers });
      check(templatesRes, {
        'templates status is 200': (r) => r.status === 200,
        'templates has items': (r) => r.json('templates').length > 0,
      });
      recordMetrics(templatesRes, '/api/genstudio/templates');
    });
    
    sleep(0.5);
  });

  // ==========================================
  // User Manual & Help APIs
  // ==========================================
  group('Help & Documentation', function() {
    // User Manual
    group('Get User Manual', function() {
      const manualRes = http.get(`${BASE_URL}/api/help/manual`, { headers });
      check(manualRes, {
        'manual status is 200': (r) => r.status === 200,
        'manual has features': (r) => r.json('features') !== undefined,
        'manual excludes TwinFinder': (r) => !JSON.stringify(r.json()).includes('twinfinder'),
        'manual includes Comix AI': (r) => r.json('features').comix_ai !== undefined,
      });
      recordMetrics(manualRes, '/api/help/manual');
    });
    
    sleep(0.5);
  });

  // ==========================================
  // Content Vault API
  // ==========================================
  group('Content Vault', function() {
    group('Get Content Vault', function() {
      const vaultRes = http.get(`${BASE_URL}/api/content/vault`, { headers });
      check(vaultRes, {
        'vault status is 200': (r) => r.status === 200,
        'vault has themes': (r) => r.json('themes') !== undefined,
      });
      recordMetrics(vaultRes, '/api/content/vault');
    });
    
    sleep(0.5);
  });

  // ==========================================
  // Analytics API
  // ==========================================
  group('Analytics', function() {
    group('Get User Stats', function() {
      const statsRes = http.get(`${BASE_URL}/api/analytics/user-stats`, { headers });
      check(statsRes, {
        'stats status is 200': (r) => r.status === 200,
      });
      recordMetrics(statsRes, '/api/analytics/user-stats');
    });
    
    sleep(0.5);
  });

  // ==========================================
  // Creator Tools API
  // ==========================================
  group('Creator Tools', function() {
    group('Get Conversion Costs', function() {
      const costsRes = http.get(`${BASE_URL}/api/convert/costs`, { headers });
      if (costsRes.status === 200) {
        check(costsRes, {
          'reel_to_carousel is 10 credits': (r) => r.json('reel_to_carousel') === 10,
          'reel_to_youtube is 10 credits': (r) => r.json('reel_to_youtube') === 10,
          'story_to_reel is 10 credits': (r) => r.json('story_to_reel') === 10,
        });
      }
      recordMetrics(costsRes, '/api/convert/costs');
    });
    
    sleep(0.5);
  });

  // Random think time between iterations
  sleep(Math.random() * 3 + 1);
}

// Teardown function - runs once after all VUs complete
export function teardown(data) {
  console.log('Load test completed');
}

// Handle summary for monitoring integration
export function handleSummary(data) {
  return {
    'results.json': JSON.stringify(data),
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
  };
}

// Text summary helper
function textSummary(data, options) {
  const indent = options.indent || '';
  let summary = '\n';
  summary += `${indent}=== Load Test Summary ===\n\n`;
  
  // Key metrics
  const metrics = data.metrics;
  summary += `${indent}HTTP Requests:\n`;
  summary += `${indent}  Total: ${metrics.http_reqs.values.count}\n`;
  summary += `${indent}  Rate: ${metrics.http_reqs.values.rate.toFixed(2)}/s\n\n`;
  
  summary += `${indent}Response Times:\n`;
  summary += `${indent}  Avg: ${metrics.http_req_duration.values.avg.toFixed(2)}ms\n`;
  summary += `${indent}  P95: ${metrics.http_req_duration.values['p(95)'].toFixed(2)}ms\n`;
  summary += `${indent}  Max: ${metrics.http_req_duration.values.max.toFixed(2)}ms\n\n`;
  
  summary += `${indent}Errors:\n`;
  summary += `${indent}  Failed: ${metrics.http_req_failed.values.passes} (${(metrics.http_req_failed.values.rate * 100).toFixed(2)}%)\n`;
  
  return summary;
}
