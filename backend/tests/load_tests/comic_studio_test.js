/**
 * K6 Load Test for Comic Studio API
 * Tests the comic studio endpoints under various load conditions
 * 
 * Run: k6 run comic_studio_test.js
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Counter, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const genresSuccess = new Counter('genres_success');
const assetsSuccess = new Counter('assets_success');
const templatesSuccess = new Counter('templates_success');
const storyGenSuccess = new Counter('story_generation_success');
const genresLatency = new Trend('genres_latency');
const assetsLatency = new Trend('assets_latency');

// Test configuration
export const options = {
  scenarios: {
    // Smoke test - verify basic functionality
    smoke: {
      executor: 'constant-vus',
      vus: 1,
      duration: '30s',
      startTime: '0s',
      gracefulStop: '5s',
    },
    // Load test - normal traffic
    load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 10 },
        { duration: '1m', target: 10 },
        { duration: '30s', target: 0 },
      ],
      startTime: '35s',
      gracefulStop: '10s',
    },
    // Stress test - peak traffic
    stress: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 50 },
        { duration: '1m', target: 50 },
        { duration: '30s', target: 100 },
        { duration: '1m', target: 100 },
        { duration: '30s', target: 0 },
      ],
      startTime: '3m',
      gracefulStop: '15s',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    errors: ['rate<0.1'],
    genres_latency: ['p(95)<300'],
    assets_latency: ['p(95)<400'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'https://image-to-comic.preview.emergentagent.com';

// Test user credentials
const TEST_USER = {
  email: 'demo@example.com',
  password: 'Password123!'
};

// Helper function to login and get token
function login() {
  const loginRes = http.post(`${BASE_URL}/api/auth/login`, JSON.stringify({
    email: TEST_USER.email,
    password: TEST_USER.password
  }), {
    headers: { 'Content-Type': 'application/json' }
  });
  
  if (loginRes.status === 200) {
    const data = JSON.parse(loginRes.body);
    return data.token;
  }
  return null;
}

export default function() {
  const token = login();
  const headers = token ? {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  } : { 'Content-Type': 'application/json' };

  group('Comic Studio API Tests', () => {
    
    // Test 1: Get all genres
    group('GET /api/comic/genres', () => {
      const start = Date.now();
      const res = http.get(`${BASE_URL}/api/comic/genres`);
      const duration = Date.now() - start;
      
      genresLatency.add(duration);
      
      const success = check(res, {
        'genres status is 200': (r) => r.status === 200,
        'genres response has data': (r) => {
          try {
            const data = JSON.parse(r.body);
            return data.genres && data.genres.length >= 8;
          } catch {
            return false;
          }
        }
      });
      
      if (success) {
        genresSuccess.add(1);
      } else {
        errorRate.add(1);
      }
    });

    sleep(0.5);

    // Test 2: Get genre assets for each genre
    group('GET /api/comic/assets/{genre}', () => {
      const genres = ['superhero', 'romance', 'comedy', 'scifi', 'fantasy', 'mystery', 'horror', 'kids'];
      const randomGenre = genres[Math.floor(Math.random() * genres.length)];
      
      const start = Date.now();
      const res = http.get(`${BASE_URL}/api/comic/assets/${randomGenre}`);
      const duration = Date.now() - start;
      
      assetsLatency.add(duration);
      
      const success = check(res, {
        'assets status is 200': (r) => r.status === 200,
        'assets has stickers': (r) => {
          try {
            const data = JSON.parse(r.body);
            return data.stickers && Array.isArray(data.stickers);
          } catch {
            return false;
          }
        },
        'assets has sfx': (r) => {
          try {
            const data = JSON.parse(r.body);
            return data.sfx && Array.isArray(data.sfx);
          } catch {
            return false;
          }
        }
      });
      
      if (success) {
        assetsSuccess.add(1);
      } else {
        errorRate.add(1);
      }
    });

    sleep(0.5);

    // Test 3: Get story templates
    group('GET /api/comic/templates/{genre}', () => {
      const genres = ['superhero', 'romance', 'comedy'];
      const randomGenre = genres[Math.floor(Math.random() * genres.length)];
      
      const res = http.get(`${BASE_URL}/api/comic/templates/${randomGenre}`);
      
      const success = check(res, {
        'templates status is 200': (r) => r.status === 200,
        'templates has data': (r) => {
          try {
            const data = JSON.parse(r.body);
            return data.templates && data.templates.length > 0;
          } catch {
            return false;
          }
        }
      });
      
      if (success) {
        templatesSuccess.add(1);
      } else {
        errorRate.add(1);
      }
    });

    sleep(0.5);

    // Test 4: Get layouts
    group('GET /api/comic/layouts', () => {
      const res = http.get(`${BASE_URL}/api/comic/layouts`);
      
      const success = check(res, {
        'layouts status is 200': (r) => r.status === 200,
        'layouts has 5 options': (r) => {
          try {
            const data = JSON.parse(r.body);
            return data.layouts && data.layouts.length === 5;
          } catch {
            return false;
          }
        }
      });
      
      errorRate.add(!success);
    });

    sleep(0.5);

    // Test 5: Generate story (authenticated)
    if (token) {
      group('POST /api/comic/generate-story', () => {
        const res = http.post(`${BASE_URL}/api/comic/generate-story`, JSON.stringify({
          genre: 'superhero',
          tone: 'normal',
          character_name: 'TestHero',
          panel_count: 4
        }), { headers });
        
        const success = check(res, {
          'story generation status is 200': (r) => r.status === 200,
          'story has title': (r) => {
            try {
              const data = JSON.parse(r.body);
              return data.title && data.title.length > 0;
            } catch {
              return false;
            }
          },
          'story has panels': (r) => {
            try {
              const data = JSON.parse(r.body);
              return data.panels && data.panels.length > 0;
            } catch {
              return false;
            }
          }
        });
        
        if (success) {
          storyGenSuccess.add(1);
        } else {
          errorRate.add(1);
        }
      });
    }

    sleep(0.5);

    // Test 6: Get export cost
    group('GET /api/comic/export-cost', () => {
      const res = http.get(`${BASE_URL}/api/comic/export-cost?panel_count=4&story_mode=true&remove_watermark=false`);
      
      const success = check(res, {
        'export cost status is 200': (r) => r.status === 200,
        'export cost has total': (r) => {
          try {
            const data = JSON.parse(r.body);
            return data.totalCost && typeof data.totalCost === 'number';
          } catch {
            return false;
          }
        }
      });
      
      errorRate.add(!success);
    });

    sleep(1);
  });
}

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: '  ', enableColors: true }),
    '/app/test_reports/k6_comic_studio.json': JSON.stringify(data, null, 2)
  };
}

function textSummary(data, options) {
  const { metrics } = data;
  
  let summary = `
========================================
K6 Comic Studio Load Test Results
========================================

Total Requests: ${metrics.http_reqs?.values?.count || 0}
Failed Requests: ${metrics.http_req_failed?.values?.passes || 0}
Error Rate: ${(metrics.errors?.values?.rate * 100 || 0).toFixed(2)}%

Response Times:
  - Average: ${(metrics.http_req_duration?.values?.avg || 0).toFixed(2)}ms
  - P95: ${(metrics.http_req_duration?.values?.['p(95)'] || 0).toFixed(2)}ms
  - P99: ${(metrics.http_req_duration?.values?.['p(99)'] || 0).toFixed(2)}ms

Custom Metrics:
  - Genres API P95: ${(metrics.genres_latency?.values?.['p(95)'] || 0).toFixed(2)}ms
  - Assets API P95: ${(metrics.assets_latency?.values?.['p(95)'] || 0).toFixed(2)}ms
  - Successful Genre Requests: ${metrics.genres_success?.values?.count || 0}
  - Successful Asset Requests: ${metrics.assets_success?.values?.count || 0}
  - Successful Template Requests: ${metrics.templates_success?.values?.count || 0}
  - Successful Story Generations: ${metrics.story_generation_success?.values?.count || 0}

========================================
`;
  
  return summary;
}
