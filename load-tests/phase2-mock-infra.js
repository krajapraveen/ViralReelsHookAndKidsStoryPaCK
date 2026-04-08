import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// ─── CUSTOM METRICS ──────────────────────────────────────────
const generateLatency = new Trend('generate_latency', true);
const generateErrors = new Rate('generate_error_rate');
const generateSuccess = new Counter('generate_success_count');
const generateThroughput = new Counter('generate_throughput');
const trackLatency = new Trend('track_latency', true);
const trackErrors = new Rate('track_error_rate');
const dbWriteCount = new Counter('db_write_count');

const BASE_URL = __ENV.BASE_URL || 'https://trust-engine-5.preview.emergentagent.com';

// ─── PHASE 2: MOCK LLM (1K → 3K → 5K → 10K) ───────────────
export const options = {
  scenarios: {
    ramp_infra: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '20s', target: 1000 },  // Ramp to 1K
        { duration: '40s', target: 1000 },  // Hold 1K
        { duration: '20s', target: 3000 },  // Ramp to 3K
        { duration: '40s', target: 3000 },  // Hold 3K
        { duration: '20s', target: 5000 },  // Ramp to 5K
        { duration: '40s', target: 5000 },  // Hold 5K
        { duration: '30s', target: 10000 }, // Ramp to 10K
        { duration: '40s', target: 10000 }, // Hold 10K
        { duration: '20s', target: 0 },     // Cool down
      ],
    },
  },
  thresholds: {
    'generate_latency': ['p(95)<2000'],    // Mock should be fast: p95 < 2s
    'generate_error_rate': ['rate<0.05'],   // <5% errors
    'track_latency': ['p(95)<1000'],        // Tracking under stress: p95 < 1s
    'track_error_rate': ['rate<0.02'],      // <2% tracking errors
  },
};

const FUNNEL_EVENTS = [
  'demo_viewed',
  'story_generation_started',
  'story_generated_success',
  'continue_clicked',
  'story_part_generated',
  'paywall_shown',
  'paywall_converted',
];

function randomId() {
  return Math.random().toString(36).slice(2, 14);
}

export default function () {
  const sessionId = `lt-mock-${randomId()}`;
  const headers = { 'Content-Type': 'application/json' };

  // ── Story generation (mock) ─────────────────────────────────
  const genStart = Date.now();
  const genRes = http.post(`${BASE_URL}/api/public/quick-generate`, JSON.stringify({
    mode: 'fresh',
    session_id: sessionId,
  }), { headers, timeout: '10s' });

  const genDuration = Date.now() - genStart;
  generateLatency.add(genDuration);
  generateThroughput.add(1);

  const genOk = check(genRes, {
    'generate: status 200': (r) => r.status === 200,
    'generate: has body': (r) => r.body && r.body.length > 10,
  });

  generateErrors.add(genOk ? 0 : 1);
  if (genOk) generateSuccess.add(1);

  // ── Funnel tracking burst ───────────────────────────────────
  for (const step of FUNNEL_EVENTS) {
    const trackRes = http.post(`${BASE_URL}/api/funnel/track`, JSON.stringify({
      step: step,
      session_id: sessionId,
      context: { source_page: 'experience', device: 'mobile', meta: { part_number: 1 } },
    }), { headers, timeout: '5s' });

    const trackDur = Date.now() - Date.now(); // measured in k6 internally
    trackLatency.add(trackRes.timings.duration);

    const ok = check(trackRes, { [`track ${step}: 200`]: (r) => r.status === 200 });
    trackErrors.add(ok ? 0 : 1);
    if (ok) dbWriteCount.add(1);
  }

  sleep(Math.random() * 0.5);
}
