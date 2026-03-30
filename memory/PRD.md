# Story Universe Engine — Product Requirements Document

## Original Problem Statement
Build a "Story Universe Engine" — a full-stack AI creator suite with growth engine, monetization, and viral sharing. Core mandate: production-grade, mobile-first UI with Netflix-level media delivery, locked-down visual contract, deterministic homepage personalization, and addictive hook system.

## Core Architecture
- Frontend: React (CRA + Craco) on port 3000
- Backend: FastAPI on port 8001
- Database: MongoDB
- Storage: Cloudflare R2 (all media via same-origin streaming proxy)
- Payments: Cashfree
- AI: OpenAI GPT-4o-mini, Sora 2, TTS + Gemini 3 via Emergent LLM Key

## Homepage Regression Protection (IMPLEMENTED — Mar 30 2026)

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
story_score = (0.25 × category_affinity) + (0.20 × hook_strength)
            + (0.15 × completion_rate) + (0.15 × momentum)
            + (0.10 × freshness) + (0.10 × share_rate)
            + (0.05 × global_trending)
```

## Hook System (IMPLEMENTED — Mar 30 2026)
- 3 LLM-generated hook variants per story
- A/B: 80% best / 20% exploration
- Lock: ≥300 impressions + ≥15% margin
- Evolution: every 100 impressions, drop worst, rewrite from best
- `hook_score = (0.6 × continue_rate) + (0.3 × share_rate) + (0.1 × completion_rate)`

## Key Files
- `/app/backend/services/hook_service.py`
- `/app/backend/services/personalization_service.py`
- `/app/backend/routes/engagement.py`
- `/app/backend/services/story_engine/pipeline.py`
- `/app/frontend/src/pages/Dashboard.js`

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
- [x] **Homepage regression protection** (backend + frontend fallback guards)
- [x] Validated: Hero ✅, 4/4 rows ✅, 10/10 features ✅, Credits ✅

## Upcoming Tasks
- (P1) Backfill hooks for existing stories
- (P1) A/B rollout flag
- (P1) Blurhash generation
- (P1) Preview video for hover autoplay
