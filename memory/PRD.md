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

## Retention Analytics Dashboard
**Route**: `/app/admin/retention`
**5 Key Metrics**: Avg Session Time, Hook CTR, Continue Rate, 10s Drop-Off Rate, Scroll Depth
**Additional**: Session retention curve, autoplay preview funnel, device segmentation, daily trends

## Rate Limit UX (Fixed)
- Concurrency cap: KEPT (protects cost/infra)
- "Rate limit" → "All rendering slots are busy" (friendly messaging)
- Shows active jobs list with "View" buttons
- Button: "Slots Busy — Wait or Cancel" (not "Generation Unavailable")
- Status bar: "X videos rendering" (not raw technical limits)

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Key Files
- `/app/backend/routes/retention_analytics.py` — Session tracking + retention dashboard API
- `/app/backend/routes/engagement.py` — Feed, events, infinite scroll
- `/app/backend/routes/story_engine_routes.py` — Rate limit status with active_jobs list
- `/app/backend/services/personalization_service.py` — Session memory, momentum, recovery
- `/app/frontend/src/pages/RetentionDashboard.js` — Analytics UI
- `/app/frontend/src/pages/Dashboard.js` — Main feed with infinite scroll + session tracking
- `/app/frontend/src/pages/StoryVideoPipeline.js` — Rate limit UX (fixed)
- `/app/frontend/src/utils/sessionTracker.js` — Session lifecycle
- `/app/frontend/src/utils/feedTracker.js` — Engagement events
- `/app/frontend/src/utils/videoController.js` — Singleton autoplay
- `/app/frontend/src/components/HeroMedia.jsx` — Hero with delayed autoplay
- `/app/frontend/src/components/StoryCardMedia.jsx` — Card with hover/visible autoplay

## Completed
- [x] CDN bypass fix + Blurhash system
- [x] Netflix autoplay preview (singleton, Safari-safe)
- [x] Behavior engine (session memory, momentum, recovery, variable rewards, infinite scroll)
- [x] Retention Analytics Dashboard (5 key metrics, trends, device segmentation)
- [x] **Rate Limit UX Fix** (Mar 30 2026): Root cause was a TRIPLE rate-limit message source: `story_engine_routes.py` (fixed by prev agent), `pipeline_routes.py` (old harsh messages), and `services/story_engine/safety.py` (returned `success: False` with "Rate limit:" prefix, causing a 400 instead of 429). Fixed all 3 backend files + frontend. Messages now say "All rendering slots are busy" with active jobs list, "View Progress" buttons, and contextual help tips.

## Current Phase: STABILIZATION
- No new features
- Observe real user behavior via retention dashboard
- Fix only high-impact issues based on data

## Upcoming (After Data Validation)
- (P1) Fix issues identified by retention metrics
- (P1) Backfill hooks for existing stories
- (P2) Hook + autoplay combo optimization
- (P2) Character-driven auto-share prompts
- (P2) Story Chain leaderboard
