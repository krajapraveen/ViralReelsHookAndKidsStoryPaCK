# Story Universe Engine — Product Requirements Document

## Original Problem Statement
Build a "Story Universe Engine" — a full-stack AI creator suite with growth engine, monetization, and viral sharing.

## Core Architecture
- **Frontend**: React (CRA + Craco) on port 3000
- **Backend**: FastAPI on port 8001
- **Database**: MongoDB
- **Storage**: Cloudflare R2 (all media served via **same-origin backend proxy**)
- **Payments**: Cashfree
- **AI**: OpenAI GPT-4o-mini, Sora 2, TTS + Gemini 3 via Emergent LLM Key

## Media Delivery Architecture (Safari-Safe — Mar 30 2026)

### Hard Rules
1. **ALL homepage images served via same-origin proxy** (`/api/media/r2/{key}`)
2. **NO direct R2 CDN URLs** ever reach the browser
3. **Every proxy response includes ALL Safari-required headers** via `_safari_safe_response()`
4. **Video supports Range/206 Partial Content** for Safari playback

### 3-Layer Fix
1. **Data Pipeline**: DB backfilled `thumbnail_small_url` for all stories. API enforces non-null.
2. **Delivery**: Same-origin proxy with auto-resize. Cards: `?w=480&q=80`. Hero: `?w=1200&q=85`.
3. **Protocol**: `_safari_safe_response()` guarantees on EVERY response:
   - `Content-Type` (correct MIME)
   - `Content-Length` (exact byte count)
   - `Accept-Ranges: bytes`
   - `Content-Disposition: inline`
   - `ETag` (weak, content-hash-based)
   - `X-Content-Type-Options: nosniff`
   - `Access-Control-Allow-Origin: *`
   - `Vary: Range`

### Video Protocol
- Range requests → HTTP 206 + `Content-Range: bytes start-end/total`
- HEAD requests → `Content-Length` + `Accept-Ranges: bytes`
- OPTIONS preflight → 204 with full CORS headers

### Frontend Preload Strategy
- `<link rel="preconnect">` + `<link rel="dns-prefetch">` in index.html
- Dynamic `<link rel="preload">` for hero poster + first 4 thumbnails
- Hero: `loading="eager"` + `fetchPriority="high"` + `decoding="sync"`
- Cards: `loading="lazy"` + `decoding="async"`

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## What's Been Implemented
- Same-origin proxy with Safari-safe headers for all media
- DB backfill + API contract enforcement (zero null media)
- Dashboard consumes proxy URLs directly (no static banners)
- 11 creator tools, Story-to-Video pipeline
- Cashfree payments, Google Auth, Admin dashboard
- Trust-based admin metrics, 50-credit consistency
