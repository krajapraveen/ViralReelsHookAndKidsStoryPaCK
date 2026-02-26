import http from "k6/http";
import { check, sleep, group } from "k6";
import { Counter, Rate, Trend } from "k6/metrics";

// Custom metrics
const errorRate = new Rate("errors");
const apiLatency = new Trend("api_latency");
const loginSuccess = new Counter("login_success");
const loginFailure = new Counter("login_failure");

// Configuration
const BASE = __ENV.BASE_URL || "https://rating-insights.preview.emergentagent.com";

export const options = {
  scenarios: {
    // Browse scenario - Light traffic
    browse: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "30s", target: 50 },
        { duration: "1m", target: 100 },
        { duration: "30s", target: 0 },
      ],
      gracefulRampDown: "10s",
    },
    // Auth scenario - Medium traffic
    auth: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "30s", target: 30 },
        { duration: "1m", target: 50 },
        { duration: "30s", target: 0 },
      ],
      gracefulRampDown: "10s",
    },
    // API scenario - Higher traffic
    api: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "30s", target: 100 },
        { duration: "2m", target: 200 },
        { duration: "30s", target: 0 },
      ],
      gracefulRampDown: "10s",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],        // <1% request failures
    http_req_duration: ["p(95)<1000"],     // p95 < 1s
    "http_req_duration{type:api}": ["p(95)<500"],  // API p95 < 500ms
    errors: ["rate<0.05"],                 // Error rate < 5%
  },
};

// Helper: Get auth token
function getAuthToken() {
  const email = __ENV.USER_EMAIL || "demo@example.com";
  const password = __ENV.USER_PASSWORD || "Password123!";
  
  const payload = JSON.stringify({ email, password });
  const res = http.post(`${BASE}/api/auth/login`, payload, {
    headers: { "Content-Type": "application/json" },
    tags: { type: "auth" },
  });
  
  if (res.status === 200) {
    loginSuccess.add(1);
    const body = res.json();
    return body.token;
  } else {
    loginFailure.add(1);
    return null;
  }
}

// Helper: Authenticated request
function authRequest(method, url, token, body = null) {
  const headers = {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
  
  const start = Date.now();
  let res;
  
  if (method === "GET") {
    res = http.get(url, { headers, tags: { type: "api" } });
  } else if (method === "POST") {
    res = http.post(url, body ? JSON.stringify(body) : null, { headers, tags: { type: "api" } });
  }
  
  apiLatency.add(Date.now() - start);
  return res;
}

// Main test function
export default function () {
  group("Browse Public Pages", function () {
    // Landing page
    let res = http.get(`${BASE}/`, { tags: { type: "page" } });
    check(res, { "landing 200": (r) => r.status === 200 }) || errorRate.add(1);
    sleep(0.5);
    
    // Pricing page
    res = http.get(`${BASE}/pricing`, { tags: { type: "page" } });
    check(res, { "pricing 200": (r) => r.status === 200 }) || errorRate.add(1);
    sleep(0.5);
    
    // User Manual
    res = http.get(`${BASE}/user-manual`, { tags: { type: "page" } });
    check(res, { "manual 200": (r) => r.status === 200 }) || errorRate.add(1);
    sleep(0.5);
  });
  
  group("API Endpoints", function () {
    // Health check
    let res = http.get(`${BASE}/api/health/`, { tags: { type: "api" } });
    check(res, { "health 200": (r) => r.status === 200 }) || errorRate.add(1);
    
    // User Manual API
    res = http.get(`${BASE}/api/help/manual`, { tags: { type: "api" } });
    check(res, { "manual api 200": (r) => r.status === 200 }) || errorRate.add(1);
    
    // Subscription Plans
    res = http.get(`${BASE}/api/subscriptions/plans`, { tags: { type: "api" } });
    check(res, { "plans 200": (r) => r.status === 200 }) || errorRate.add(1);
  });
  
  group("Authenticated Flow", function () {
    const token = getAuthToken();
    if (!token) {
      errorRate.add(1);
      return;
    }
    
    // Dashboard data
    let res = authRequest("GET", `${BASE}/api/credits/balance`, token);
    check(res, { "balance 200": (r) => r.status === 200 }) || errorRate.add(1);
    sleep(0.3);
    
    // User stats
    res = authRequest("GET", `${BASE}/api/analytics/user-stats`, token);
    check(res, { "stats 200": (r) => r.status === 200 }) || errorRate.add(1);
    sleep(0.3);
    
    // Subscription current
    res = authRequest("GET", `${BASE}/api/subscriptions/current`, token);
    check(res, { "subscription 200": (r) => r.status === 200 }) || errorRate.add(1);
  });
  
  sleep(1);
}

// Stress test scenario
export function stressTest() {
  const token = getAuthToken();
  if (!token) return;
  
  // Rapid API calls
  for (let i = 0; i < 10; i++) {
    authRequest("GET", `${BASE}/api/credits/balance`, token);
    authRequest("GET", `${BASE}/api/help/manual`, token);
  }
}

// Soak test scenario (long duration)
export function soakTest() {
  const token = getAuthToken();
  if (!token) return;
  
  // Regular operations over time
  authRequest("GET", `${BASE}/api/credits/balance`, token);
  sleep(5);
  
  authRequest("GET", `${BASE}/api/analytics/user-stats`, token);
  sleep(5);
  
  authRequest("GET", `${BASE}/api/subscriptions/current`, token);
  sleep(5);
}
