# Story Universe Engine — Product Requirements Document

## Original Problem Statement
Build a "Story Universe Engine" — a full-stack AI creator suite with a behavior-driven growth engine, monetization, and viral sharing. Core mandate: Netflix-level media delivery, deterministic personalization, addictive hook system, and a complete dopamine loop (autoplay → hooks → personalization → infinite scroll).

## Core Architecture
- Frontend: React (CRA + Craco) on port 3000
- Backend: FastAPI on port 8001
- Database: MongoDB
- Storage: Cloudflare R2 (images via CDN, videos via same-origin proxy for CORS safety)
- Payments: Cashfree
- AI: OpenAI GPT-4o-mini, Sora 2, TTS + Gemini 3 via Emergent LLM Key

## Behavior Engine (THE ADDICTION LOOP)

### Flow
```
Autoplay grabs attention → Hook creates curiosity → Preview builds emotion
→ User clicks (reward) → Session momentum increases → Personalization adapts
→ Next item improves → Variable reward spikes dopamine → Infinite scroll continues
→ Recovery system prevents boredom → Loop repeats
```

### Session Memory
- `momentum_score`: 0.0-10.0, tracks in-session engagement intensity
- `last_5_clicked_categories`: Recent category preferences
- `last_3_hooks_clicked`: Recent hook patterns
- `consecutive_skips`: Triggers recovery at >=3

### Momentum Deltas
| Event | Delta |
|-------|-------|
| click | +1.0 |
| continue_click | +2.0 |
| preview_play | +0.5 |
| watch_complete | +1.5 |
| hook_seen | +0.3 |
| skip_fast | -1.0 |
| share_click | +2.0 |

### Content Intensity (Based on Momentum)
- HIGH (>=5.0): Show engaging/intense content
- MEDIUM (>=2.0): Balanced mix
- LOW (<2.0): Safe/easy content to re-engage

### Recovery System
- Triggers when `consecutive_skips >= 3`
- De-prioritizes recently-seen categories
- Surfaces fresh/unseen content

### Variable Reward Injection
- High-score items spiked at RANDOM intervals (3-9 positions)
- Creates unpredictability = dopamine

### Soft Breaks
- Every 12 infinite-scroll items, inject "Try something different?" CTA
- Resets dopamine, increases session time

## Story Scoring Formula
```
story_score = (0.25 × category_affinity) + (0.20 × hook_strength)
            + (0.15 × completion_rate) + (0.15 × momentum)
            + (0.10 × freshness) + (0.10 × share_rate)
            + (0.05 × global_trending)
```

## Hook System
- 3 LLM-generated hook variants per story
- A/B: 80% best / 20% exploration
- Lock: >=300 impressions + >=15% margin
- Evolution: every 100 impressions, drop worst, rewrite from best

## Media Delivery
- Images: CDN direct (`https://pub-...r2.dev/KEY`)
- Videos: Same-origin proxy (`/api/media/r2/videos/...`) for CORS safety
- Blur Placeholders: 32x32 base64 JPEG per story (zero blank UI)

## Autoplay Preview System
- Singleton controller: Max 1 video at a time, max 2 per 5 seconds
- Desktop: 120ms hover delay → play
- Mobile: 150ms debounced IntersectionObserver → play
- Hero: 1000ms delay after poster loads
- Fallback: preview → blurhash + static poster

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Key API Endpoints
- `GET /api/engagement/story-feed` — Main feed with personalized ranking
- `GET /api/engagement/story-feed/more?offset=X&limit=Y` — Infinite scroll
- `POST /api/engagement/feed-event` — Real-time session momentum + profile updates
- `POST /api/engagement/preview-event` — Autoplay analytics
- `POST /api/engagement/hook-event` — Hook A/B tracking
- `POST /api/admin/backfill/thumb-blur/sync` — Blurhash backfill

## Key Files
- `/app/backend/services/personalization_service.py` — Session memory, momentum, recovery, variable rewards
- `/app/backend/services/hook_service.py` — Hook A/B logic
- `/app/backend/routes/engagement.py` — Feed, events, infinite scroll
- `/app/backend/routes/backfill_blur.py` — Blurhash backfill
- `/app/backend/services/story_engine/adapters/media_gen.py` — Blur + media generation
- `/app/frontend/src/pages/Dashboard.js` — Infinite scroll, skip tracking, scroll speed
- `/app/frontend/src/utils/mediaUrl.js` — CDN/proxy URL resolution
- `/app/frontend/src/utils/videoController.js` — Singleton autoplay controller
- `/app/frontend/src/utils/feedTracker.js` — Engagement events, scroll speed, dynamic hook delay
- `/app/frontend/src/components/HeroMedia.jsx` — Hero with delayed autoplay
- `/app/frontend/src/components/StoryCardMedia.jsx` — Card with hover/visible autoplay

## Completed
- [x] Deterministic homepage personalization (exact math, no ML)
- [x] Hook system (3 variants, A/B test, lock, evolution)
- [x] Homepage regression protection (backend + frontend fallback guards)
- [x] CDN bypass fix (removed ${API} prefix from resolveMedia)
- [x] Blurhash system (pipeline + backfill 181 stories + feed integration)
- [x] Preload + priority loading (hero eager, first 6 cards eager, CDN preconnect)
- [x] Netflix autoplay preview (singleton, hover/visible, Safari-safe)
- [x] **Behavior Engine** (Mar 30 2026):
  - Session memory (momentum, categories, hooks, skip tracking)
  - Real-time profile updates via feed-event endpoint
  - Variable reward injection (random 3-9 interval spikes)
  - Recovery system (3+ skips → content reset)
  - Infinite scroll with soft breaks every 12 items
  - Dynamic hook timing based on scroll speed
  - Mid-session re-rank signal (should_rerank every 5 actions)

## Upcoming Tasks
- (P1) Backfill hooks for existing stories
- (P1) A/B rollout flag for hooks
- (P1) Hook + autoplay combo optimization (hook text synced with preview start)
- (P2) Character-driven auto-share prompts
- (P2) Remix Variants on share pages
- (P2) Upgrade admin dashboard to WebSockets
- (P2) Story Chain leaderboard
