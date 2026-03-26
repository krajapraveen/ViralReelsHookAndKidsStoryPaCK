# Visionary Suite — Product Requirements Document

## Original Problem Statement
Build a viral, addictive "Story Universe Engine" with an optimized frontend growth loop, a Private Story-to-Video Engine backend, and a data-driven content optimization system.

## Architecture
- **Frontend**: React, Shadcn UI, TailwindCSS
- **Backend**: FastAPI, Python 3.11
- **Database**: MongoDB
- **Storage**: Cloudflare R2
- **AI**: GPT-4o-mini, GPT Image 1, Sora 2, OpenAI TTS — via Emergent LLM Key
- **Video Assembly**: FFmpeg 5.1 (system binary) with resilient detached execution
- **Payments**: Cashfree
- **A/B Testing**: Custom lean framework (deterministic session-based assignment, deduped events)

## Implemented Features

### P0 E2E Story Engine — PROVEN
- Full pipeline: INIT->PLANNING->CHARACTER->MOTION->KEYFRAMES->CLIPS->AUDIO->ASSEMBLY->READY
- 3 Sora 2 clips + 1 Ken Burns fallback, 14.5s final video on R2
- FFmpeg clip normalization fix for mixed Sora + Ken Burns clips

### P0 Strict Credit Gate
- Pre-flight `/api/story-engine/credit-check` on Generate click
- Modal with exact required/current/shortfall
- Backend HTTP 402 enforcement

### P0 Character-Driven Auto-Share Prompt — VERIFIED (2026-03-26)
- ForceShareGate modal via React Portal (createPortal) at document.body
- Dynamic character_name and cliffhanger from story engine status API
- ViewJob fetches full /status endpoint for character data
- Verified: character avatar, title, hook, urgency, rewards (+5/+15/+25), Continue + Skip

### P1 FFmpeg Subprocess Resilience — IMPLEMENTED (2026-03-26)
- `_run_ffmpeg_resilient()`: detached shell wrapper via nohup/setsid
- Polls marker files for completion — survives hot-reloads/supervisor restarts
- Applied to stitch_clips and mix_audio (long operations)

### P1 A/B Hook Testing — VERIFIED (2026-03-26)
- **4 variants**: Mystery, Emotional, Shock, Curiosity
- **2 surfaces**: Public share pages (`/v/{slug}`) + Dashboard trending cards
- **4 tracked events**: impression, click, continue_click, share_click
- **Backend**: `/api/ab/hook-analytics` with per-variant metrics (impressions, clicks, CTR, continues, continue_rate, shares, share_rate, sufficient_data, data_warning)
- **Frontend**: Variant-specific section_label, hook_suffix, cta_text, urgency, accent color
- **Admin**: Dedicated "Hook A/B" tab with metrics grid, progress bars, confidence warnings, summary cards
- **Assignment**: Deterministic session-based (hashed session_id + experiment_id)
- **No auto-promotion** in v1 — manual review only
- Testing: 100% (iteration_347, 21/21 backend + 13/13 frontend)

### P1 Public Share Page Rebuild
- Auto-play video, character intro, cliffhanger, post-video CTA overlay

### Earlier Completed Work
- Truth-based hype text, social proof, scroll traps
- Zero-Friction Entry (login only on Generate)
- Share Reward System (+5/+15/+25 credits)
- Click Psychology (cinematic cards, A/B tracking)
- Gallery / Explore Page (infinite scroll, filters)
- Trust & UI Fixes, Monetization (Cashfree)
- Credit system consistency (50 credits for all normal users)

## Prioritized Backlog

### P1 — Next Up
- E2E: degraded/fallback job + continue/chain job (pending LLM budget)
- Auto-improve weak hooks based on A/B data (after sufficient data collected)

### P2 — Future
- Remix Variants, WebSocket admin, Story Chain leaderboard
- Self-hosted GPU (Wan2.1, Kokoro) for true independence

## Key DB Collections
- `story_engine_jobs`: Complex nested state machine execution
- `ab_experiments`: Experiment definitions with variants
- `ab_assignments`: Session -> variant mapping (deduped)
- `ab_conversions`: Event tracking (impression, click, continue_click, share_click)
- `users`, `orders`, `feedback`, `ratings`, `credit_transactions`

## Credentials
- Test: `test@visionary-suite.com` / `Test@2026#`
- Admin: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`
