import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// ─── CUSTOM METRICS ──────────────────────────────────────────
const spikeLatency = new Trend('spike_latency', true);
const spikeErrors = new Rate('spike_error_rate');
const spikeSuccess = new Counter('spike_success_count');
const trackLatency = new Trend('track_latency', true);

const BASE_URL = __ENV.BASE_URL || 'https://trust-engine-5.preview.emergentagent.com';

// ─── PHASE 3: SPIKE TEST (0 → 3K in 10s) ────────────────────
export const options = {
  scenarios: {
    viral_spike: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '10s', target: 3000 },  // Instant spike to 3K
        { duration: '30s', target: 3000 },  // Hold 3K
        { duration: '10s', target: 0 },     // Drop
      ],
    },
  },
  thresholds: {
    'spike_latency': ['p(95)<3000'],     // Spike: p95 < 3s
    'spike_error_rate': ['rate<0.10'],    // Allow up to 10% during spike (graceful degradation)
  },
};

const FULL_JOURNEY_EVENTS = [
  'demo_viewed',
  'story_generation_started',
  'story_generated_success',
  'continue_clicked',
  'story_part_generated',
  'paywall_teaser_shown',
  'paywall_shown',
  'paywall_dismissed',
  'exit_offer_shown',
];

function randomId() {
  return Math.random().toString(36).slice(2, 14);
}

export default function () {
  const sessionId = `lt-spike-${randomId()}`;
  const headers = { 'Content-Type': 'application/json' };

  // ── Generate story ──────────────────────────────────────────
  const genRes = http.post(`${BASE_URL}/api/public/quick-generate`, JSON.stringify({
    mode: 'fresh',
    session_id: sessionId,
  }), { headers, timeout: '10s' });

  spikeLatency.add(genRes.timings.duration);

  const genOk = check(genRes, {
    'spike: status 200': (r) => r.status === 200,
    'spike: valid response': (r) => {
      try { return JSON.parse(r.body).story_id !== undefined; } catch(e) { return false; }
    },
  });

  spikeErrors.add(genOk ? 0 : 1);
  if (genOk) spikeSuccess.add(1);

  // ── Full funnel burst ───────────────────────────────────────
  for (const step of FULL_JOURNEY_EVENTS) {
    const trackRes = http.post(`${BASE_URL}/api/funnel/track`, JSON.stringify({
      step: step,
      session_id: sessionId,
      context: { source_page: 'experience', device: 'desktop', meta: { part_number: 2, story_id: sessionId } },
    }), { headers, timeout: '5s' });

    trackLatency.add(trackRes.timings.duration);
    check(trackRes, { [`track ${step}: ok`]: (r) => r.status === 200 });
  }

  sleep(Math.random() * 0.3);
}
