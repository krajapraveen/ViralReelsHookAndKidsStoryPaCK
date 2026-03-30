# Story Universe Engine — Product Requirements Document

## Original Problem Statement
Build a "Story Universe Engine" — a full-stack AI creator suite with growth engine, monetization, and viral sharing.

## Core Architecture
- **Frontend**: React (CRA + Craco) on port 3000
- **Backend**: FastAPI on port 8001
- **Database**: MongoDB
- **Storage**: Cloudflare R2 (images served via R2 Public CDN)
- **Payments**: Cashfree
- **AI**: OpenAI GPT-4o-mini, Sora 2, TTS + Gemini 3 via Emergent LLM Key

## Route → Component Mapping
| Route | Component | Media Source |
|-------|-----------|-------------|
| `/` | `Landing.js` | Webpack-bundled static (showcase) |
| `/app` | `Dashboard.js` | **API-provided R2 CDN URLs** |
| `/app/story-video-studio` | StoryVideoStudio | Dynamic R2/proxy |
| `/share/*` | PublicCreation | Dynamic R2/proxy |

## Dashboard Media Architecture (API-DRIVEN — Mar 30 2026)

### Hard Rule
**Dashboard.js consumes `thumbnail_small_url` and `poster_url` from the feed API. No static banners, no fake images, no fallback mapping.**

### Root Cause History
1. Safari/Mobile showed gradient fallbacks on Dashboard
2. Previous agents applied static banner hacks (bundled images bypassing API)
3. **Real root cause**: DB had 0/62 `thumbnail_small_url` values populated
4. **Fix**: Backend DB backfill + API contract enforcement + frontend consuming API directly

### Data Pipeline
- `thumbnail_small_url` is populated at story creation time via pipeline
- DB backfill script exists at `/app/backend/scripts/backfill_thumbnails.py`
- Feed API (`GET /api/engagement/story-feed`) guarantees non-null `thumbnail_small_url` and `poster_url`
- Resolution chain: `thumbnail_small_url` → `thumbnail_url` → `scene_images[0]` → `stage_results.image_gen`

### What's on Dashboard
- R2 CDN public URLs (`https://pub-xxx.r2.dev/...`)
- Loaded via `<img>` tags (no crossOrigin, no CORS issues)

### What's NOT on Dashboard
- No static banners, No `getStaticHeroImg`/`getStaticCardImg`, No bundled assets, No `<video>`

## What's Been Implemented
- 11 creator tools, Story-to-Video pipeline
- **API-driven Dashboard** with hero + 4 story rows (all R2 CDN media)
- **Webpack-bundled Landing page** (showcase cards)
- Cashfree payments, Google Auth, Admin dashboard
- Addiction Loop Metrics Dashboard, Frontend event tracking
- Media proxy (asyncio.to_thread + LRU cache) for deeper pages
- DB backfill script for `thumbnail_small_url`
- Trust-based admin metrics (real data, no mocks)
- 50-credit allocation consistency

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Prioritized Backlog
### P1
- Unify Landing.js and Dashboard.js architecture
- A/B test hook text variations
- Character-driven auto-share prompts

### P2
- Remix Variants on share pages
- WebSockets for admin dashboard
- Story Chain leaderboard

### P3
- Self-hosted GPU models (Wan2.1, Kokoro)
- *(PAUSED)* Credit Routes Migration
