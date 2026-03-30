# Story Universe Engine — Product Requirements Document

## Original Problem Statement
Build a "Story Universe Engine" — a full-stack AI creator suite with growth engine, monetization, and viral sharing.

## Core Architecture
- **Frontend**: React (CRA + Craco) on port 3000
- **Backend**: FastAPI on port 8001
- **Database**: MongoDB
- **Storage**: Cloudflare R2 (images served via **same-origin backend proxy**)
- **Payments**: Cashfree
- **AI**: OpenAI GPT-4o-mini, Sora 2, TTS + Gemini 3 via Emergent LLM Key

## Dashboard Media Architecture (PROXY-FIRST — Mar 30 2026)

### Hard Rule
**ALL homepage images are served via same-origin backend proxy (`/api/media/r2/{key}`). NO direct R2 CDN URLs. This eliminates Safari/Mobile CORS/ORB blocking.**

### 3-Layer Fix Applied
1. **Data Pipeline (Fixed)**: DB backfill populated `thumbnail_small_url` for all stories. Feed API enforces non-null.
2. **Delivery Layer (Fixed)**: ALL image URLs converted to same-origin proxy paths with auto-resize params. Zero direct R2 CDN exposure.
3. **Frontend Consumption (Fixed)**: Dashboard.js prepends `API` base URL to proxy paths. Hero uses `loading="eager"` + `fetchPriority="high"`. Cards use `loading="lazy"` + `decoding="async"`. Preload `<link>` tags injected for hero poster + first 4 thumbnails.

### URL Format
- **Card thumbnails**: `/api/media/r2/{key}?w=480&q=80`
- **Hero posters**: `/api/media/r2/{key}?w=1200&q=85`
- **Videos**: `/api/media/r2/{key}` (Range/206 support)

### What's NOT on Dashboard
- No direct R2 CDN URLs (`https://pub-xxx.r2.dev/...`)
- No static banners / bundled assets
- No `<video>` tags in card rows
- No gradient-only fallbacks as primary state

## What's Been Implemented
- 11 creator tools, Story-to-Video pipeline
- **Same-origin proxy Dashboard** with hero + 4 story rows (all via backend proxy)
- DB backfill script for `thumbnail_small_url`
- Preload hints (hero + first 4 thumbnails)
- `<link rel="preconnect">` + `<link rel="dns-prefetch">` in index.html
- Cashfree payments, Google Auth, Admin dashboard
- Trust-based admin metrics (real data, no mocks)
- 50-credit allocation consistency

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
