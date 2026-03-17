# Visionary Suite — PRD

## Product Vision
AI Creative Operating System: **Create -> Share -> View -> Remix**

### Golden Rules
1. NO BUTTON SHOULD EXIST IF IT CANNOT GUARANTEE AN OUTPUT.
2. A job cannot be READY until the primary preview asset is validated and renderable.
3. Frontend must never lie about backend truth.
4. One authoritative UI state. No contradictory rendering.
5. Credits must NEVER show 0 due to loading or API failure.
6. Tests catch regressions. Health checks catch runtime failures. Watchdogs catch stuck jobs. Alerts tell you before users do.

## UI State Machine (Photo-to-Comic + Story Video)
```
IDLE -> PROCESSING -> VALIDATING -> READY | PARTIAL_READY | FAILED
```

## Asset Truth Model
Backend `/validate-asset` returns: `preview_ready`, `download_ready`, `share_ready`, `ui_state`, `poster_url`, `download_url`, `share_url`, `stage_detail`

## Credits Truth (ALL Pages)
- State initialized to `null` (loading), NEVER `0`
- Shows `...` while loading, `∞` for unlimited
- Pages fixed: Dashboard, GifMaker, ComicStorybookBuilder, BedtimeStoryBuilder, CreditStatusBadge

## SafeImage Component (ALL Surfaces)
Gradient fallback + title overlay. Deployed on: Dashboard, Landing, Gallery, ExplorePage, CreatorProfile, ComicStorybookBuilder, StoryPreview, ProgressiveGeneration, StoryVideoPipeline, MyStories, StoryChainView, ResumeYourStory

## Self-Defending Infrastructure (IMPLEMENTED — March 17, 2026)

### Phase 1: Automated Regression Suite
- **File**: `/app/backend/tests/regression/test_trust_regression.py`
- **Run**: `pytest tests/regression/test_trust_regression.py -v`
- **35 tests covering**: Credits truth (6), Photo to Comic (3), Story Video (5), Comic Storybook (3), My Downloads (2), Smoke endpoints (10), Reel/GIF/Bedtime/Brand/Caption/Daily (6)
- **Rule**: Run before AND after every deployment

### Phase 2: Deep Health Checks
- **Endpoint**: `GET /api/health/deep` (public, no auth)
- **Checks**: API, Database, Redis, Queue depth, Workers, Storage, Asset validation, Credits service, AI providers, Failure rate
- **Returns**: `{ healthy: bool, checks: {...}, summary: str }`

### Phase 3: Self-Healing Watchdog
- **Endpoint**: `POST /api/watchdog/run` (admin only)
- **Status**: `GET /api/watchdog/status`
- **Detects & fixes**: Stuck PROCESSING jobs (requeue or fail), Completed-no-assets (mark FAILED), Starved queue, Broken chains, Admin 0-credits (auto-restore)
- **Actions**: retry safe stages, move to FAILED honestly, requeue when valid, log root cause

### Phase 4: Production Alerts
- **Endpoint**: `GET /api/alerts/check` (admin)
- **Active alerts**: `GET /api/alerts/active`
- **Acknowledge**: `POST /api/alerts/acknowledge/{alert_id}`
- **Monitors**: Failure rate spikes, Queue depth spikes, Timeout spikes, Broken downloads, Credit truth mismatch, Provider outages, Stuck jobs

## Completed Work Summary
1-23. Previous work (resilience, upload, story chains)
24-26. Credits truth + SafeImage + State machine for Photo-to-Comic
27. Story Video Bulletproof Pipeline
28. Full Platform Hardening (Credits null-init, SafeImage sweep, all-module UAT)
29. Self-Defending Infrastructure (Regression suite, Deep health, Watchdog, Alerts)

## Remaining Backlog
### P0
- [ ] R2 bucket CORS configuration (infra)

### P1
- [ ] Consistent aspect ratios and card sizing
- [ ] Post-generation parity for Story Video (Continue/Remix/Share)

### P2
- [ ] Style preset thumbnails
- [ ] Cashfree payments (live)
- [ ] Admin dashboard for observability
- [ ] Email Notifications (BLOCKED — SendGrid)
- [ ] Scheduled watchdog (cron-style auto-run every 5 min)
- [ ] Alert notification delivery (email/webhook when alerts fire)

### Blocked
- R2 CORS — requires manual infra config
- SendGrid — requires plan upgrade
