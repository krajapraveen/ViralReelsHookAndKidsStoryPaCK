# Story Universe Engine — Product Requirements Document

## Original Problem Statement
Build a "Story Universe Engine" — a full-stack AI creator suite with a behavior-driven growth engine, monetization, and viral sharing. Core mandate: Netflix-level media delivery, deterministic personalization, addictive hook system, and a complete dopamine loop. Currently in **STABILIZATION PHASE** — no new features, focus on data-driven optimization.

## Core Architecture
- Frontend: React (CRA + Craco) on port 3000
- Backend: FastAPI on port 8001
- Database: MongoDB
- Storage: Cloudflare R2 (images via CDN, videos via same-origin proxy for CORS safety)
- Payments: Cashfree
- AI: OpenAI GPT-4o-mini, Sora 2, TTS + Gemini 3 via Emergent LLM Key

## Behavior Engine (THE ADDICTION LOOP)
```
Autoplay → Hook → Preview → Click → Reward → Personalization → Infinite Scroll → Variable Reward → Repeat
```

### Session Memory
- `momentum_score`: 0.0-10.0
- `last_5_clicked_categories`, `last_3_hooks_clicked`, `consecutive_skips`
- Recovery at 3+ skips, variable reward spikes at random 3-9 intervals

### Story Scoring
```
(0.25 × category_affinity) + (0.20 × hook_strength) + (0.15 × completion_rate)
+ (0.15 × momentum) + (0.10 × freshness) + (0.10 × share_rate) + (0.05 × trending)
```

## Retention Analytics Dashboard (IMPLEMENTED)
**Route**: `/app/admin/retention`
**5 Key Metrics**:
1. Avg Session Time (target: 3min+)
2. Hook CTR (target: 15%+)
3. Continue Rate (target: 10%+)
4. 10s Drop-Off Rate (target: <10%)
5. Scroll Depth Distribution (target: 50%+ reach depth 5+)

**Additional**: Session retention curve (7 buckets), autoplay preview funnel, device segmentation, daily trends, period selector (7d/14d/30d)

**Session Tracking**: `POST /api/admin/retention/session` — start/heartbeat(30s)/end lifecycle via `sessionTracker.js`

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Key Files
- `/app/backend/routes/retention_analytics.py` — Session tracking + retention dashboard API
- `/app/backend/routes/engagement.py` — Feed, events, infinite scroll
- `/app/backend/services/personalization_service.py` — Session memory, momentum, recovery
- `/app/backend/services/hook_service.py` — Hook A/B logic
- `/app/backend/routes/backfill_blur.py` — Blurhash backfill
- `/app/frontend/src/pages/RetentionDashboard.js` — Analytics UI
- `/app/frontend/src/pages/Dashboard.js` — Main feed with infinite scroll + session tracking
- `/app/frontend/src/utils/sessionTracker.js` — Session lifecycle
- `/app/frontend/src/utils/feedTracker.js` — Engagement events
- `/app/frontend/src/utils/videoController.js` — Singleton autoplay
- `/app/frontend/src/utils/mediaUrl.js` — CDN/proxy URL resolution
- `/app/frontend/src/components/HeroMedia.jsx` — Hero with delayed autoplay
- `/app/frontend/src/components/StoryCardMedia.jsx` — Card with hover/visible autoplay

## Completed
- [x] Deterministic homepage personalization (exact math, no ML)
- [x] Hook system (3 variants, A/B, lock, evolution)
- [x] Homepage regression protection (backend + frontend fallbacks)
- [x] CDN bypass fix (removed ${API} prefix from resolveMedia)
- [x] Blurhash system (pipeline + backfill 181 stories)
- [x] Preload + priority loading (hero eager, first 6 cards eager, CDN preconnect)
- [x] Netflix autoplay preview (singleton, hover/visible, Safari-safe)
- [x] Behavior engine (session memory, momentum, recovery, variable rewards, infinite scroll, soft breaks, dynamic hook timing)
- [x] **Retention Analytics Dashboard** (Mar 30 2026): 5 key metrics, retention curve, preview funnel, device segmentation, daily trends, period selector

## Current Phase: STABILIZATION
- No new features
- Observe real user behavior via retention dashboard
- Identify biggest drop-off points
- Fix only high-impact issues based on data

## Upcoming (After Data Validation)
- (P1) Fix issues identified by retention metrics
- (P1) Backfill hooks for existing stories
- (P2) Hook + autoplay combo optimization
- (P2) Character-driven auto-share prompts
- (P2) Upgrade admin dashboard to WebSockets
- (P2) Story Chain leaderboard
