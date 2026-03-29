# Story Universe Engine — Product Requirements Document

## Original Problem Statement
Build a "Story Universe Engine" — a full-stack AI creator suite with 11 creator tools, growth/engagement engine, monetization via Cashfree payments, and a viral sharing loop.

## Core Architecture
- **Frontend**: React 18 + Tailwind + Shadcn/UI (port 3000)
- **Backend**: FastAPI + Motor (MongoDB) (port 8001)
- **Database**: MongoDB (creatorstudio_production)
- **Object Storage**: Cloudflare R2 (CDN: pub-c251248e414545848d34b8c1b97ecdb3.r2.dev)
- **AI**: OpenAI GPT-4o-mini, GPT Image 1, Sora 2, TTS via Emergent LLM Key
- **Payments**: Cashfree

## Schema Approach
- Compatibility mapping at API response layer
- DB stores existing field names (`state`, flat `thumbnail_url` etc.)
- API responses normalize to consistent contract (`status`, structured media URLs)
- No full DB migration unless blocking functionality

## What's Been Implemented

### Completed (2026-03-29 — Current Session)
- **Image CDN Direct Delivery**: Images now served via R2 CDN direct (0.39s) instead of Python proxy (0.72-1.76s). Videos still use proxy for Range/206 support. 77% speed improvement for large assets.
- **Homepage Architecture (Sections 0-18)**: Hero section, 4 story feed rows (always render with seed fallback), 11 large feature cards, create bar, footer
- **Backend Feed API**: Returns separate arrays with CDN image URLs and proxy video URLs
- **Story Card Prefill Flow**: Full prefill object from cards/hero/create bar → Studio input phase
- **IntersectionObserver Lazy Loading**: SafeImage with viewport-based loading
- **FFmpeg Pipeline Fix**: Transition name sanitization, planning retry
- **Pipeline Thumbnail Compression**: `thumbnail_small` generation during assembly
- **Technical Architecture Document**: /app/ARCHITECTURE.md

### Previously Completed
- Admin sidebar, story-to-video pipeline, Cashfree payments, credit system, trust-based admin dashboard, public share pages, Google OAuth + JWT auth

## Media Delivery Architecture
- **Images** (thumbnails, posters): R2 CDN direct (`https://pub-xxx.r2.dev/...`)
- **Videos** (output, preview): Backend proxy (`/api/media/r2/...`) for Range/206 support
- **Feed API**: `_cdn_url()` for images, `_proxy_url()` for videos

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Key Documents
- /app/ARCHITECTURE.md — Full technical architecture
- /app/test_reports/iteration_361.json — Homepage architecture test (all pass)
- /app/test_reports/iteration_360.json — P0 fixes test (all pass)
