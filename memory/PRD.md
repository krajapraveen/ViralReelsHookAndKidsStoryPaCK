# Story Universe Engine — Product Requirements Document

## Original Problem Statement
Build a "Story Universe Engine" — a full-stack AI creator suite that lets users create animated story videos through a multi-step pipeline (planning → scenes → images → video → audio → assembly). The platform includes 10 creator tools, a growth/engagement engine, monetization via Cashfree payments, and a viral sharing loop.

## Core Architecture
- **Frontend**: React 18 + Tailwind + Shadcn/UI (port 3000)
- **Backend**: FastAPI + Motor (MongoDB) (port 8001)
- **Database**: MongoDB (creatorstudio_production, 162+ collections)
- **Object Storage**: Cloudflare R2
- **AI**: OpenAI GPT-4o-mini, GPT Image 1, Sora 2, TTS via Emergent LLM Key
- **Payments**: Cashfree

## What's Been Implemented

### Completed (Current Session — 2026-03-29)
- **P0 Fix: Story Card → Studio Prefill Flow** — Clicking a story card/hero now passes full prefill object (title, prompt, animation_style, parent_video_id) to StoryVideoStudio. Studio stays in INPUT phase — no auto-generation. Files: Dashboard.js, StoryVideoPipeline.js
- **P0 Fix: Homepage Media Performance** — Removed eager 16-image preload worker. Implemented IntersectionObserver-based lazy loading in SafeImage. Only hero poster image is eagerly preloaded. Files: SafeImage.jsx, Dashboard.js
- **P0 Fix: FFmpeg Pipeline Assembly** — Root cause: LLM-generated transition names (cut, crossfade) are not valid FFmpeg xfade transitions. Added `_sanitize_transition()` mapping function. Also added planning retry logic (1 auto-retry on LLM failure). Files: ffmpeg_assembly.py, pipeline.py
- **P0: Technical Architecture Document** — Comprehensive read-only doc at /app/ARCHITECTURE.md covering User Flow, Backend Flow, Data Flow, DB Schemas, External Dependencies, Failure Points, Performance Bottlenecks.

### Completed (Previous Sessions)
- Admin Sidebar Navigation (AdminLayout.js)
- Homepage Copy & CTAs ("Watch & Continue")
- 10-feature Creator Tools grid
- Story-to-Video full pipeline (planning → scenes → images → video → audio → assembly)
- Cashfree payment integration
- Credit system (50 credits standard)
- Trust-based admin dashboard (real metrics only)
- Public share pages with momentum-based social proof
- 1-click continue flow
- Google OAuth + JWT auth

## Prioritized Backlog

### P0 (Current)
- [x] Story card → Studio prefill flow
- [x] Homepage media performance (lazy loading)
- [x] FFmpeg pipeline assembly fix
- [x] Technical Architecture Document
- [ ] **E2E Testing** — Test all 10 features end-to-end with copyright-free inputs

### P1 (Next)
- [ ] A/B test hook text variations on story cards
- [ ] Character-driven auto-share prompts after creation

### P2 (Future)
- [ ] Remix Variants on share pages
- [ ] Self-hosted GPU models (Wan2.1, Kokoro)
- [ ] WebSockets for live admin job tracking
- [ ] Style preset preview thumbnails
- [ ] SendGrid email fix (blocked on valid API key)

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Key Documents
- /app/ARCHITECTURE.md — Full technical architecture
- /app/test_reports/iteration_360.json — Latest test results (100% pass)
