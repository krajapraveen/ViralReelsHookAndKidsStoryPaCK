# AI Creator Suite — Product Requirements Document

## Original Problem Statement
Full-stack AI creator suite with a "compulsion-driven" growth engine. Latest focus: Daily Viral Idea Drop — a queue-driven content pack generator with distribution + monetization proof via Growth Engine.

## Core Architecture
- **Frontend**: React (port 3000)
- **Backend**: FastAPI (port 8001)
- **Database**: MongoDB
- **AI**: GPT-4o-mini (text), GPT Image 1 (thumbnails), OpenAI TTS (voiceover), Gemini (fallback)
- **Video**: moviepy + ffmpeg
- **Payments**: Cashfree | **Auth**: Emergent Google Auth + JWT

## Growth Engine (Latest — April 2026)

### 1. Shareable Output System
- Public teaser page at `/viral/{job_id}` — no auth required
- Shows: big hook, blurred thumbnail, partial script/caption
- CTAs: "Generate Your Own Free Pack" → signup, "Unlock Full Pack" → login
- Social proof floor (500+), speed proof ("30 seconds")
- Share tracking: WhatsApp, Twitter, copy link

### 2. Soft Paywall
- First generation: FREE (no credits deducted)
- Subsequent: deduct 5 credits, or generate locked if no credits
- Locked packs: truncated text, blurred images, no downloads
- "Unlock This Pack" CTA → 5 credits → full access

### 3. Viral Hook Injection
- 4 structured hook types: curiosity, pattern_break, emotional, loop
- 5 variants per idea (up from 3)
- Auto-select strongest hook (curiosity > loop > pattern_break > emotional)

### 4. Basic Metrics
- `viral_growth_metrics` collection tracking:
  - generation, share_event, share_view, share_to_signup, free_to_paid
- Queryable via `GET /api/viral-ideas/metrics/growth`
- Referral tracking via `POST /api/viral-ideas/track-referral`

## Test Results
- Growth Engine: 27/27 tests passed (iteration_425)
- Phase 2 (audio/video/repair/feedback): 21/21 tests passed (iteration_424)
- Phase 1 (core pipeline): 13/13 tests passed

## What Remains Before Phase 3
- Validate real user data: Do users share? Do shares bring new users? Do users pay?
- Monitor metrics via `/api/viral-ideas/metrics/growth`

## Frozen Backlog (DO NOT BUILD)
- Personalization, Admin dashboard, Precomputed packs, Quality modes
- Share This Pack feature, Auto captions, Multi-reaction packs
- Character DNA System, Smart router, Advanced analytics

## Test Credentials
- Test User: `test@visionary-suite.com` / `Test@2026#`
- Admin User: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`
