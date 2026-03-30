# Story Universe Engine — Product Requirements Document

## Original Problem Statement
Build a "Story Universe Engine" — a full-stack AI creator suite with growth engine, monetization, and viral sharing. Core mandate: production-grade, mobile-first UI with Netflix-level media delivery, locked-down visual contract, deterministic homepage personalization, and addictive hook system.

## Core Architecture
- Frontend: React (CRA + Craco) on port 3000
- Backend: FastAPI on port 8001
- Database: MongoDB
- Storage: Cloudflare R2 (images via CDN, videos via same-origin proxy for CORS safety)
- Payments: Cashfree
- AI: OpenAI GPT-4o-mini, Sora 2, TTS + Gemini 3 via Emergent LLM Key

## Homepage Regression Protection (IMPLEMENTED)

### Backend Guards
- Personalization scoring wrapped in try/except → falls back to DB default ordering
- Row ranking wrapped in try/except → falls back to manual row construction
- Feature ranking wrapped in try/except → falls back to default features
- Hook A/B serving wrapped in try/except → falls back to clean stories without hook variant

### Frontend Guards
- `DEFAULT_FEATURES` (10 static tools) — used when API features empty
- `DEFAULT_ROWS` (3 seed-data rows) — used when API rows empty
- `safeHeroPool` — uses SEED_CARDS when API hero + all rows empty
- No single section failure can collapse the page

## Updated Story Scoring Formula (with Hook System)
```
story_score = (0.25 x category_affinity) + (0.20 x hook_strength)
            + (0.15 x completion_rate) + (0.15 x momentum)
            + (0.10 x freshness) + (0.10 x share_rate)
            + (0.05 x global_trending)
```

## Hook System (IMPLEMENTED)
- 3 LLM-generated hook variants per story
- A/B: 80% best / 20% exploration
- Lock: >=300 impressions + >=15% margin
- Evolution: every 100 impressions, drop worst, rewrite from best
- `hook_score = (0.6 x continue_rate) + (0.3 x share_rate) + (0.1 x completion_rate)`

## Media Delivery Architecture
- **Images**: CDN direct (`https://pub-...r2.dev/KEY`) — Safari-safe Cache-Control
- **Videos**: Same-origin proxy (`/api/media/r2/videos/...`) — CORS-safe streaming
- **resolveMediaUrl()**: Frontend utility that routes images to CDN, videos to proxy
- **Blur Placeholders**: 32x32 base64 JPEG generated per story for zero-blank-UI

## Autoplay Preview System (IMPLEMENTED — Mar 30 2026)
- **Singleton controller**: Max 1 video at a time, max 2 per 5 seconds
- **Desktop**: Hover → 120ms delay → play
- **Mobile**: IntersectionObserver → 150ms debounce → play
- **Hero**: 1000ms delay after poster loads → autoplay
- **Safety**: muted + playsInline + loop (Safari mandatory)
- **Fallback**: preview → blurhash + static poster
- **Analytics**: preview_impression, preview_play, preview_watch_complete, preview_click

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Completed
- [x] Deterministic media pipeline
- [x] Frontend component contract (HeroMedia, StoryCardMedia, MediaPreloader)
- [x] Visual contract (Tailwind/CSS)
- [x] Deterministic homepage personalization
- [x] Hook generation, A/B testing, evolution
- [x] Updated scoring formula (no continue_rate duplication)
- [x] Homepage regression protection (backend + frontend fallback guards)
- [x] P0 CDN Bypass Fix: Removed ${API} prefix from resolveMedia()
- [x] P0 Perceived Speed — Blurhash: Pipeline + backfill + feed integration
- [x] Preload + Priority Loading: Hero fetchPriority=high, first 6 cards eager, CDN preconnected
- [x] Netflix Autoplay Preview System: Singleton controller, hover/visible triggers, analytics, fallback chain

## Key Files
- `/app/backend/services/hook_service.py`
- `/app/backend/services/personalization_service.py`
- `/app/backend/routes/engagement.py`
- `/app/backend/routes/backfill_blur.py`
- `/app/backend/services/story_engine/pipeline.py`
- `/app/backend/services/story_engine/adapters/media_gen.py`
- `/app/frontend/src/pages/Dashboard.js`
- `/app/frontend/src/utils/mediaUrl.js`
- `/app/frontend/src/utils/videoController.js`
- `/app/frontend/src/components/HeroMedia.jsx`
- `/app/frontend/src/components/StoryCardMedia.jsx`

## Upcoming Tasks
- (P1) Backfill hooks for existing stories
- (P1) A/B rollout flag for hooks
- (P2) Character-driven auto-share prompts
- (P2) Remix Variants on share pages
- (P2) Upgrade admin dashboard to WebSockets
- (P2) Story Chain leaderboard
