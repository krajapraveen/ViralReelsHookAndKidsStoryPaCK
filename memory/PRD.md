# Story Universe Engine — Product Requirements Document

## Original Problem Statement
Build a "Story Universe Engine" — a full-stack AI creator suite with growth engine, monetization, and viral sharing. The core mandate is a production-grade, mobile-first UI with Netflix-level media delivery, a locked-down visual contract, deterministic homepage personalization, and an addictive hook system that transforms the app from a "content generator" into an "attention engine".

## Core Architecture
- Frontend: React (CRA + Craco) on port 3000
- Backend: FastAPI on port 8001
- Database: MongoDB
- Storage: Cloudflare R2 (all media via same-origin streaming proxy)
- Payments: Cashfree
- AI: OpenAI GPT-4o-mini, Sora 2, TTS + Gemini 3 via Emergent LLM Key

## Deterministic Media Pipeline (IMPLEMENTED)
- FFmpeg extracts frame, Pillow generates thumbnail_small (400x530) + poster_large (1280x720)
- Stored in nested `media` object in DB
- Feed API returns `media.thumbnail_small_url`, `media.poster_large_url`, `media.preview_short_url`, `media.media_version: "v3"`

## Frontend Component Contract (IMPLEMENTED)
- **HeroMedia.jsx** — Hero poster (eager, high priority, blur-up, fallback)
- **StoryCardMedia.jsx** — Card thumbnail (thumbnail_small -> poster_large -> fallback)
- **MediaPreloader.jsx** — Preloads hero poster + first 4 thumbnails only
- **Dashboard.js** — DUMB RENDERER: maps over API-provided rows[] and features[]

## Deterministic Homepage Personalization (IMPLEMENTED)
- Backend owns ALL ordering — frontend is a dumb renderer
- Pure deterministic math — NO ML, NO embeddings, NO LLM recommenders
- Event-driven profile updates with 0.98 decay multiplier
- Cold start threshold: 5 events minimum for personalization

### Updated Story Scoring Formula (with Hook System)
```
story_score = (0.25 × category_affinity) + (0.20 × hook_strength)
            + (0.15 × completion_rate) + (0.15 × momentum)
            + (0.10 × freshness) + (0.10 × share_rate)
            + (0.05 × global_trending)
```
NOTE: hook_strength already encodes continue signal — no double counting.

### Event Weights
```
card_click=1  watch_start=2  continue_click=5  watch_complete=8
share_click=10  generation_start=6  generation_complete=12
```

### Feature Scoring Formula
```
feature_score = (0.50 × feature_affinity) + (0.25 × recent_usage)
              + (0.15 × success_rate) + (0.10 × monetization_priority)
```

### Row Priority Rules
- IF user has active stories → continue_stories = rank 1
- ELSE IF high continue_rate → trending = rank 1
- ELSE → fresh = rank 1

## Hook System (IMPLEMENTED — Mar 30 2026)

### Hook Generation
- 3 LLM-generated hook variants per story (GPT-4o-mini via Emergent Key)
- Category-aware templates: kids, horror, mystery, reels, emotional, default
- Weak hook detection: `is_weak_hook()` checks length (>12 words), generic openers, no curiosity triggers
- Auto-rewrite via LLM: `rewrite_hook()` for weak hooks
- Hook prediction: `predict_hook_score()` rule-based pre-screen (0-5)
- Generated during pipeline Step 3.5 (after planning, before character continuity)

### Hook A/B Testing Engine
- **Serving**: 80% best hook / 20% exploration (when not locked)
- **Lock condition**: ≥300 total impressions + ≥15% winner margin
- **Evolution**: Every 100 impressions, drop worst hook, rewrite from best
- **Confidence weighting**: `adjusted_score = raw_score × log(impressions + 1)`

### Hook Score Formula
```
hook_score = (0.6 × continue_rate) + (0.3 × share_rate) + (0.1 × completion_rate)
```

### Hook DB Schema (in story_engine_jobs)
```json
{
  "hooks": [
    {"id": "A", "text": "...", "impressions": 120, "continues": 50, "shares": 5, "completions": 10},
    {"id": "B", "text": "...", "impressions": 110, "continues": 61, "shares": 12, "completions": 15},
    {"id": "C", "text": "...", "impressions": 100, "continues": 20, "shares": 2, "completions": 5}
  ],
  "hook_text": "The winning hook text",
  "winning_hook": "B",
  "hook_locked": true
}
```

### Hook API Endpoints
- `GET /api/engagement/story-feed` — Returns `hook_text` + `hook_variant_id` per story
- `POST /api/engagement/hook-event` — Tracks hook impressions, continues, shares, completions

## Key Files
- `/app/backend/services/hook_service.py` — Core hook engine (generation, A/B, evolution, scoring)
- `/app/backend/services/personalization_service.py` — Ranking engine
- `/app/backend/routes/engagement.py` — Feed API + hook event tracking
- `/app/backend/services/story_engine/pipeline.py` — Pipeline with hook generation stage
- `/app/frontend/src/pages/Dashboard.js` — Dumb renderer with hook display + A/B tracking
- `/app/frontend/src/components/HeroMedia.jsx`
- `/app/frontend/src/components/StoryCardMedia.jsx`
- `/app/frontend/src/components/MediaPreloader.jsx`
- `/app/frontend/src/utils/growthTracker.js`

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Completed
- [x] Deterministic media pipeline (Pillow + FFmpeg)
- [x] Nested media DB schema + backfill
- [x] Feed API nested media object (media_version: v3)
- [x] HeroMedia, StoryCardMedia, MediaPreloader components
- [x] Dashboard rewrite with contract components
- [x] Visual contract — exact Tailwind/CSS class system
- [x] Deterministic homepage personalization (scoring engine, profile updates, ranked rows/features)
- [x] Event-driven profile ingestion via growth_events hooks
- [x] Cold start fallback logic
- [x] MongoDB indexes for user_homepage_profile
- [x] Frontend updated to dumb renderer (maps over API rows[] and features[])
- [x] Hook generation service (3 variants, LLM + category templates)
- [x] Hook validation (is_weak_hook) + auto-rewrite
- [x] Hook prediction (rule-based pre-screen)
- [x] Hook A/B testing engine (80/20 explore/exploit, lock at 300+15% margin)
- [x] Hook evolution (drop worst, rewrite from best every 100 impressions)
- [x] Hook scoring integrated into ranking formula (0.20 weight)
- [x] Hook event tracking endpoint (impression/continue/share/completion)
- [x] Pipeline integration (_stage_hooks after planning)
- [x] Frontend hook display on hero + cards
- [x] Frontend hook A/B event tracking
- [x] Tested: Backend 19/19 + Frontend 100% (iteration 382)

## Upcoming Tasks
- (P1) A/B rollout flag (10% personalized, 90% default)
- (P1) Blurhash/thumb_blur generation for instant perception
- (P1) Preview_short video generation for Netflix autoplay
- (P1) CDN-first delivery optimization
- (P1) Backfill hooks for all existing stories (batch job)
- (P2) "Remix Variants" on share pages
- (P2) Admin dashboard WebSocket upgrade
- (P2) Story Chain leaderboard
