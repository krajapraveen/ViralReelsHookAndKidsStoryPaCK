# Visionary Suite — PRD

## Product Vision
AI Creative Operating System: **Create -> Share -> View -> Remix**

### Golden Rules
1. NO BUTTON SHOULD EXIST IF IT CANNOT GUARANTEE AN OUTPUT.
2. A job cannot be READY until the primary preview asset is validated.
3. Frontend must never lie about backend truth.
4. One authoritative UI state. No contradictory rendering.
5. Credits must NEVER show 0 due to loading or API failure.
6. Tests catch regressions. Health checks catch failures. Watchdog heals. Alerts notify.

## Self-Defending Infrastructure

### Regression Suite (35 tests)
- Run: `pytest tests/regression/test_trust_regression.py -v`
- Credits truth (6), Photo to Comic (3), Story Video (5), Comic Storybook (3), Downloads (2), Smoke (10), Tools (6)

### Deep Health: `GET /api/health/deep`
- API, DB, Redis, Queue, Workers, Storage, Asset validation, Credits, AI providers, Failure rate

### Self-Healing Watchdog (Auto: every 5 min)
- `POST /api/watchdog/run` | `GET /api/watchdog/status` | `GET /api/watchdog/logs` | `GET /api/watchdog/confidence`
- Detects: stuck jobs, completed-no-assets, starved queue, credit corruption, broken chains
- SLA: 10min processing, 5min queue, 2min validation, 3 retries max
- Actions: requeue, fail honestly, restore credits — all logged
- Confidence score 0-100 based on failure rate, queue, corrections, alerts

### Production Alerts: `GET /api/alerts/check`
- Failure spikes, queue spikes, timeouts, broken downloads, credit mismatches, provider outages
- Alert → Watchdog coupling: critical alerts auto-trigger watchdog

## UI State Machine (Photo-to-Comic + Story Video)
IDLE -> PROCESSING -> VALIDATING -> READY | PARTIAL_READY | FAILED

## Asset Truth: `/validate-asset` returns separate preview_ready, download_ready, share_ready

## Credits Truth: All pages init to null, show "..." loading, "∞" unlimited

## SafeImage: All surfaces — Dashboard, Landing, Gallery, Explore, CreatorProfile, ComicStorybook, StoryPreview, ProgressiveGeneration, StoryVideoPipeline, MyStories, StoryChainView

## Completed Work
1-23. Core platform build
24-26. Credits truth + SafeImage + PhotoToComic state machine
27. Story Video Bulletproof Pipeline
28. Full Platform Hardening (all-module UAT, SafeImage sweep, credits null-init)
29. Self-Defending Infrastructure (regression suite, deep health, watchdog, alerts)
30. Continuous Self-Healing (scheduled watchdog, structured logs, alert-action coupling, SLA guardrails, confidence score, retry limits)

## Remaining Backlog
### P0
- [ ] R2 bucket CORS configuration (infra)

### P1
- [ ] Consistent aspect ratios and card sizing
- [ ] Post-generation parity for Story Video

### P2
- [ ] Style preset thumbnails
- [ ] Cashfree payments (live)
- [ ] Admin dashboard for observability
- [ ] Email Notifications (BLOCKED — SendGrid)

### Blocked
- R2 CORS — infra config
- SendGrid — plan upgrade
