import http from "k6/http";
import { check, sleep, group } from "k6";
import { Counter, Rate, Trend } from "k6/metrics";

// Custom metrics
const errorRate = new Rate("errors");
const cashfreeLatency = new Trend("cashfree_latency");
const orderCreated = new Counter("orders_created");
const webhookProcessed = new Counter("webhooks_processed");

const BASE = __ENV.BASE_URL || "https://gallery-showcase-43.preview.emergentagent.com";

export const options = {
  scenarios: {
    // Payment simulation - Lower volume, realistic
    payments: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "30s", target: 10 },
        { duration: "2m", target: 20 },
        { duration: "30s", target: 5 },
        { duration: "30s", target: 0 },
      ],
      gracefulRampDown: "10s",
    },
    // Concurrent order creation stress
    orderStress: {
      executor: "constant-vus",
      vus: 15,
      duration: "1m",
      startTime: "3m",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.02"],          // <2% failures (payment APIs can be flaky)
    "http_req_duration{name:createOrder}": ["p(95)<2000"],  // p95 < 2s for orders
    errors: ["rate<0.05"],
  },
};

// Get auth token
function getAuthToken() {
  const email = __ENV.USER_EMAIL || "demo@example.com";
  const password = __ENV.USER_PASSWORD || "Password123!";
  
  const res = http.post(`${BASE}/api/auth/login`, JSON.stringify({ email, password }), {
    headers: { "Content-Type": "application/json" },
  });
  
  return res.status === 200 ? res.json().token : null;
}

// Main payment flow test
export default function () {
  const token = getAuthToken();
  if (!token) {
    errorRate.add(1);
    return;
  }
  
  const headers = {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
  
  group("Cashfree Integration", function () {
    // Health check
    let res = http.get(`${BASE}/api/cashfree/health`, { headers });
    check(res, {
      "cashfree health 200": (r) => r.status === 200,
      "cashfree configured": (r) => r.json().configured === true,
    }) || errorRate.add(1);
    sleep(0.5);
    
    // Get products
    res = http.get(`${BASE}/api/cashfree/products`, { headers });
    check(res, { "products 200": (r) => r.status === 200 }) || errorRate.add(1);
    sleep(0.3);
  });
  
  group("Order Creation", function () {
    const start = Date.now();
    
    // Create order (sandbox)
    const orderPayload = {
      product_id: "credits_100",
      amount: 299,
      currency: "INR",
    };
    
    const res = http.post(
      `${BASE}/api/cashfree/create-order`,
      JSON.stringify(orderPayload),
      { headers, tags: { name: "createOrder" } }
    );
    
    cashfreeLatency.add(Date.now() - start);
    
    const success = check(res, {
      "order created": (r) => r.status === 200 || r.status === 201,
      "has order_id": (r) => {
        try {
          const body = r.json();
          return body.order_id || body.cf_order_id || body.payment_session_id;
        } catch {
          return false;
        }
      },
    });
    
    if (success) {
      orderCreated.add(1);
    } else {
      errorRate.add(1);
    }
    
    sleep(1);
  });
  
  group("Subscription Flow", function () {
    // Get plans
    let res = http.get(`${BASE}/api/subscriptions/plans?currency=INR`, { headers });
    check(res, {
      "plans 200": (r) => r.status === 200,
      "has plans": (r) => r.json().plans && r.json().plans.length > 0,
    }) || errorRate.add(1);
    sleep(0.3);
    
    // Current subscription
    res = http.get(`${BASE}/api/subscriptions/current`, { headers });
    check(res, { "current 200": (r) => r.status === 200 }) || errorRate.add(1);
    sleep(0.3);
    
    // Subscription history
    res = http.get(`${BASE}/api/subscriptions/history`, { headers });
    check(res, { "history 200": (r) => r.status === 200 }) || errorRate.add(1);
  });
  
  sleep(2);
}

// Concurrent payment simulation
export function concurrentPayments() {
  const token = getAuthToken();
  if (!token) return;
  
  const headers = {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
  
  // Simulate rapid payment attempts (testing idempotency)
  for (let i = 0; i < 3; i++) {
    const uniqueOrderId = `test_${Date.now()}_${__VU}_${i}`;
    
    http.post(
      `${BASE}/api/cashfree/create-order`,
      JSON.stringify({
        product_id: "credits_100",
        amount: 299,
        currency: "INR",
        order_id: uniqueOrderId,
      }),
      { headers }
    );
    
    sleep(0.2);
  }
}

// Currency conversion test
export function currencyTest() {
  const token = getAuthToken();
  if (!token) return;
  
  const headers = {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
  
  // Test INR
  let res = http.get(`${BASE}/api/subscriptions/plans?currency=INR`, { headers });
  check(res, { "INR plans": (r) => r.status === 200 });
  
  // Test USD
  res = http.get(`${BASE}/api/subscriptions/plans?currency=USD`, { headers });
  check(res, { "USD plans": (r) => r.status === 200 });
  
  // Test EUR
  res = http.get(`${BASE}/api/subscriptions/plans?currency=EUR`, { headers });
  check(res, { "EUR plans": (r) => r.status === 200 });
}
