# Story Universe Engine — Product Requirements Document

## Original Problem Statement
Build a "Story Universe Engine" — a full-stack AI creator suite with growth engine, monetization, and viral sharing.

## Core Architecture
- **Frontend**: React (CRA + Craco) on port 3000
- **Backend**: FastAPI on port 8001
- **Database**: MongoDB
- **Storage**: Cloudflare R2 (all media via same-origin streaming proxy)
- **Payments**: Cashfree
- **AI**: OpenAI GPT-4o-mini, Sora 2, TTS + Gemini 3 via Emergent LLM Key

## Media Delivery Architecture (Production-Grade — Mar 30 2026)

### 5-Layer Fix (ALL COMPLETE)

**Layer 1 — Data Pipeline**: DB backfilled `thumbnail_small_url` for all stories. API enforces non-null.

**Layer 2 — Delivery Routing**: ALL media via same-origin proxy `/api/media/r2/{key}`. Zero direct R2 CDN URLs.

**Layer 3 — Protocol Compliance**: `_safari_safe_headers()` on EVERY response: Content-Type, Content-Disposition: inline, ETag, Accept-Ranges, X-Content-Type-Options: nosniff, CORS.

**Layer 4 — Streaming + Cache**: Videos streamed via StreamingResponse (64KB chunks, never buffered). Images buffered + LRU cached. Surrogate-Control bypasses K8s ingress Cache-Control override.

**Layer 5 — Frontend Render Priority**: 
- Hero poster: `loading="eager"`, `fetchPriority="high"`, starts at opacity 0.6 (always visible, no JS gate)
- First 2 rows (Trending Now, Continue): `eager` prop bypasses IntersectionObserver — renders immediately
- First 6 trending cards: `loading="eager"`
- Below-fold rows: lazy loaded via IntersectionObserver (shimmer until scrolled)
- No 12s death timeout on poster
- Preload `<link>` tags for hero + first 4 thumbnails

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
