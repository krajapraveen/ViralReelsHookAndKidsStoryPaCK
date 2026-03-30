# Story Universe Engine — Product Requirements Document

## Original Problem Statement
Build a "Story Universe Engine" — a full-stack AI creator suite with growth engine, monetization, and viral sharing.

## Core Architecture
- **Frontend**: React (CRA + Craco) on port 3000
- **Backend**: FastAPI on port 8001
- **Database**: MongoDB
- **Storage**: Cloudflare R2 (all media via same-origin proxy)
- **Payments**: Cashfree
- **AI**: OpenAI GPT-4o-mini, Sora 2, TTS + Gemini 3 via Emergent LLM Key

## Media Delivery Architecture (Production-Grade — Mar 30 2026)

### 4-Layer Fix Applied

**Layer 1 — Data Pipeline (Fixed)**
- DB backfilled `thumbnail_small_url` for all stories
- Feed API enforces non-null media fields

**Layer 2 — Delivery Routing (Fixed)**
- ALL images/videos served via same-origin proxy `/api/media/r2/{key}`
- Zero direct R2 CDN URLs reach the browser
- Eliminates CORS/ORB blocking on Safari/Mobile

**Layer 3 — Protocol Compliance (Fixed)**
- `_safari_safe_headers()` guarantees on EVERY response:
  Content-Type, Content-Disposition: inline, ETag, Accept-Ranges: bytes,
  X-Content-Type-Options: nosniff, Vary, CORS
- Video Range → HTTP 206 + Content-Range
- HEAD → Content-Length + Accept-Ranges

**Layer 4 — Streaming + Cache (Fixed)**
- **Videos**: `StreamingResponse` with async 64KB chunks — never buffered in memory
- **Images**: Buffered + LRU cached (small files after resize)
- **Cache bypass**: `Surrogate-Control: public, max-age=31536000, immutable` survives K8s ingress override
- Ingress overrides `Cache-Control` to `no-store` (platform limitation, mitigated by Surrogate-Control)

### URL Format
- Card thumbnails: `/api/media/r2/{key}?w=480&q=80`
- Hero posters: `/api/media/r2/{key}?w=1200&q=85`
- Videos: `/api/media/r2/{key}` (streamed, Range/206 supported)

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## What's Been Implemented
- Same-origin streaming proxy with Safari-safe headers
- DB backfill + API contract enforcement
- Dashboard consumes proxy URLs directly
- 11 creator tools, Story-to-Video pipeline
- Cashfree payments, Google Auth, Admin dashboard
- Trust-based admin metrics, 50-credit consistency
