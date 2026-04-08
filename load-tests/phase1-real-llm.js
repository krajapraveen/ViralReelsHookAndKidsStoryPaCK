import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// ─── CUSTOM METRICS ──────────────────────────────────────────
const generateLatency = new Trend('generate_latency', true);
const generateErrors = new Rate('generate_error_rate');
const generateSuccess = new Counter('generate_success_count');
const trackLatency = new Trend('track_latency', true);
const trackErrors = new Rate('track_error_rate');
const trackSuccess = new Counter('track_success_count');

const BASE_URL = __ENV.BASE_URL || 'https://trust-engine-5.preview.emergentagent.com';

// ─── PHASE 1: REAL LLM (100 → 250 → 500) ───────────────────
export const options = {
  scenarios: {
    ramp_real: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '15s', target: 10 },    // Ramp to 10
        { duration: '30s', target: 10 },    // Hold 10
        { duration: '15s', target: 25 },    // Ramp to 25
        { duration: '30s', target: 25 },    // Hold 25
        { duration: '15s', target: 50 },    // Ramp to 50
        { duration: '45s', target: 50 },    // Hold 50
        { duration: '15s', target: 0 },     // Cool down
      ],
    },
  },
  thresholds: {
    'generate_latency': ['p(95)<4000'],    // p95 < 4s
    'generate_error_rate': ['rate<0.05'],   // <5% errors
    'track_latency': ['p(95)<500'],         // Tracking p95 < 500ms
    'track_error_rate': ['rate<0.01'],      // <1% tracking errors
  },
};

const FUNNEL_EVENTS = [
  'demo_viewed',
  'story_generation_started',
  'story_generated_success',
  'continue_clicked',
  'story_part_generated',
  'paywall_teaser_shown',
  'paywall_shown',
  'paywall_converted',
];

function randomId() {
  return Math.random().toString(36).slice(2, 14);
}

export default function () {
  const sessionId = `loadtest-${randomId()}`;
  const headers = { 'Content-Type': 'application/json' };

  // ── Step 1: Generate story ──────────────────────────────────
  const genStart = Date.now();
  const genRes = http.post(`${BASE_URL}/api/public/quick-generate`, JSON.stringify({
    mode: 'fresh',
    session_id: sessionId,
  }), { headers, timeout: '20s' });

  const genDuration = Date.now() - genStart;
  generateLatency.add(genDuration);

  const genOk = check(genRes, {
    'generate: status 200': (r) => r.status === 200,
    'generate: has story_id': (r) => {
      try { return JSON.parse(r.body).story_id !== undefined; } catch(e) { return false; }
    },
    'generate: latency < 4s': () => genDuration < 4000,
  });

  if (genOk) {
    generateSuccess.add(1);
    generateErrors.add(0);
  } else {
    generateErrors.add(1);
  }

  // ── Step 2: Fire funnel events (simulates full user journey) ─
  for (const step of FUNNEL_EVENTS) {
    const trackStart = Date.now();
    const trackRes = http.post(`${BASE_URL}/api/funnel/track`, JSON.stringify({
      step: step,
      session_id: sessionId,
      context: {
        source_page: 'experience',
        device: 'desktop',
        meta: { part_number: 1, story_id: sessionId, entry_source: 'load_test' },
      },
    }), { headers, timeout: '5s' });

    const trackDur = Date.now() - trackStart;
    trackLatency.add(trackDur);

    const trackOk = check(trackRes, {
      [`track ${step}: status 200`]: (r) => r.status === 200,
    });

    if (trackOk) {
      trackSuccess.add(1);
      trackErrors.add(0);
    } else {
      trackErrors.add(1);
    }
  }

  // Brief pause between iterations
  sleep(Math.random() * 2 + 1);
}
