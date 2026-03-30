# Story Universe Engine — Product Requirements Document

## Original Problem Statement
Build a "Story Universe Engine" — a full-stack AI creator suite with growth engine, monetization, and viral sharing.

## Core Architecture
- **Frontend**: React (CRA + Craco) on port 3000
- **Backend**: FastAPI on port 8001
- **Database**: MongoDB
- **Storage**: Cloudflare R2 (story detail/watch/result pages only — NOT homepage)
- **Payments**: Cashfree
- **AI**: OpenAI GPT-4o-mini, Sora 2, TTS + Gemini 3 via Emergent LLM Key

## Route → Component Mapping (CRITICAL)
| Route | Component | Media Source |
|-------|-----------|-------------|
| `/` | `Landing.js` | Webpack-bundled static |
| `/app` | `Dashboard.js` | Webpack-bundled static |
| `/app/story-video-studio` | StoryVideoStudio | Dynamic R2/proxy |
| `/share/*` | PublicCreation | Dynamic R2/proxy |

## Homepage Media Architecture (WEBPACK-BUNDLED — Mar 30 2026)

### Hard Rule
**Both Landing.js AND Dashboard.js use webpack-bundled images. ZERO network dependency.**

### Root Cause History
ALL previous fixes (iterations 367-370) were applied to `Dashboard.js` (route `/app`). But the user's actual public homepage is `Landing.js` (route `/`). Landing.js was still using `SafeImage` + R2 CDN the entire time. Fixed in iteration 371.

### Implementation
- 28 JPEG files in `src/assets/homepage/` imported by webpack
- `staticBanners.js`: exports `getStaticHeroImg()`, `getStaticCardImg()`, `getAllStaticBanners()`
- `Landing.js`: showcase = `getAllStaticBanners()`, cards use `item.card_img` directly
- `Dashboard.js`: uses `getStaticHeroImg(jobId)` / `getStaticCardImg(jobId)`
- Test marker: "VISIONARY TEST BUILD 01" (temporary, remove after user confirms)

### What's NOT on homepage (Landing OR Dashboard)
- No R2 CDN, No `/api/media/r2/` proxy, No SafeImage, No `<video>`, No crossOrigin

## What's Been Implemented
- 11 creator tools, Story-to-Video pipeline
- **Webpack-bundled Landing page** (17 stories, 10 showcase cards)
- **Webpack-bundled Dashboard** (4 story rows + hero)
- Cashfree payments, Google Auth, Admin dashboard
- Addiction Loop Metrics Dashboard, Frontend event tracking
- Media proxy (asyncio.to_thread + LRU cache) for deeper pages
- GitHub Actions workflows (manual-only triggers)

## Prioritized Backlog
### P2 (User-paused)
- Migrate remaining routes to CreditsService, A/B test hooks, Remix Variants

### P3
- Self-hosted GPU models, WebSockets for admin

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
