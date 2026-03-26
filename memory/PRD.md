# Visionary Suite — Product Requirements Document

## Original Problem Statement
Build a viral, addictive "Story Universe Engine" with an optimized frontend growth loop and a Private Story-to-Video Engine backend.

## Architecture
- **Frontend**: React, Shadcn UI, TailwindCSS
- **Backend**: FastAPI, Python 3.11
- **Database**: MongoDB
- **Storage**: Cloudflare R2
- **AI**: GPT-4o-mini, GPT Image 1, Sora 2, OpenAI TTS — via Emergent LLM Key
- **Video Assembly**: FFmpeg 5.1 (system binary)
- **Payments**: Cashfree
- **NOTE**: NOT yet fully independent API — depends on external AI budgets

## Implemented Features

### P0 E2E Story Engine — PROVEN (2026-03-26)
- "The Crystal Cave": Full pipeline INIT→PLANNING→CHARACTER→MOTION→KEYFRAMES→CLIPS→AUDIO→ASSEMBLY→READY
- 3 Sora 2 clips + 1 Ken Burns fallback, 14.5s final video on R2
- FFmpeg clip normalization fix for mixed Sora + Ken Burns clips
- Admin retry-assembly endpoint for FFmpeg-only retries

### P0 Strict Credit Gate (2026-03-26)
- **Frontend**: Pre-flight `/api/story-engine/credit-check` on Generate click
- **Modal**: Shows "Not enough credits" with exact required/current/shortfall
- **Buttons**: Buy Credits → /app/profile?tab=billing, View Plans → /pricing, Cancel
- **Backend**: HTTP 402 enforcement — rejects creation if credits insufficient
- **No generation starts, no credits deducted, no job created** when insufficient
- Both frontend and backend gates tested and proven

### P0 Frontend → Story Engine Migration (2026-03-26)
- ALL frontend calls use `/api/story-engine/*` (single source of truth)
- Transparent fallback queries both collections
- Testing: 100% (iteration_344)

### P1 Public Share Page Rebuild (2026-03-26)
- Auto-play video, character intro, cliffhanger, post-video CTA overlay
- Testing: 100% (iteration_345)

### Earlier Completed Work
- Truth-based hype text, social proof, scroll traps
- Zero-Friction Entry (login only on Generate)
- Share Reward System (+5/+15/+25 credits)
- Click Psychology (cinematic cards, A/B tracking)
- Gallery / Explore Page (infinite scroll, filters)
- Trust & UI Fixes, Monetization (Cashfree)

## Prioritized Backlog

### P1 — Next Up
- Character-driven auto-share prompts after creation
- A/B test hook text variations on public pages
- E2E: degraded/fallback job + continue/chain job (pending LLM budget)

### P2 — Future
- Remix Variants, WebSocket admin, Story Chain leaderboard
- Self-hosted GPU (Wan2.1, Kokoro) for true independence

## Credentials
- Test: `test@visionary-suite.com` / `Test@2026#`
- Admin: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`
