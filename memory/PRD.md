# Visionary Suite - Product Requirements Document

## Architecture
- **Frontend**: React (CRA) + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB
- **Payments**: Cashfree (production + sandbox)
- **URL**: https://trust-engine-5.preview.emergentagent.com

## Credentials
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

---

## Core Philosophy: WATCH > ENTER BATTLE > GENERATE > COMPETE > PAY

## Video Preview Pipeline (Apr 13)
- **Media Derivative Pipeline** (`/app/backend/services/media_preview_pipeline.py`)
  - Generates 3 derivatives per video: poster_sm (webp), poster_md (webp), 2s muted preview clip (mp4 h264 faststart)
  - Hook selection: scene-based I-frame analysis, picks best 2s window (not just first 2s)
  - FFmpeg: 540px width, 24fps, CRF 28, no audio, faststart
  - Uploads to R2 under `/previews/{job_id}/`
  - `media_assets` collection tracks all derivatives
  - Auto-triggers on pipeline completion via `asyncio.create_task`
  - Admin backfill: `POST /api/stories/admin/backfill-previews`
- **Feed API** returns `preview_media` contract: `poster_url`, `preview_url`, `autoplay_enabled`, `processing_state`
- **Frontend autoplay**: IntersectionObserver triggers `video.play()` at 60% visibility, falls back to poster on failure, pauses on scroll-out
Dashboard order: PersonalAlertStrip > LiveBattleHero > QuickActions > TrendingPublicFeed > MomentumSection > HeroSection > Story Rows

### New Components:
- `LiveBattleHero.jsx` — Live battle zone with stats, rank, #1 preview, Enter Battle + Quick Shot CTAs. Polls pulse every 15s. Paywall-gated. Listens for `show-battle-paywall` global events.
- `QuickActions.jsx` — "Choose Your Path" section with 3 differentiated entry paths
- `MomentumSection.jsx` — User stats: Current Rank, Battles Entered, Credits, Status

---

## Master Flow (Money Loop)
```
Dashboard > Quick Shot / Story Card > Overlay > Pipeline > Watch Page (Battle)
> User Actions: Share / Enter Again (Paywall) / Track Rank / Leave (Return Trigger)
> Return > Repeat > PAY
```

---

## All Completed Systems
- **Master QA Execution (Apr 14)**: Ran full 4-layer QA suite — 114 tests across Smoke/Regression/Negative/Failure. Found and fixed 1 HIGH-severity XSS vulnerability in draft save endpoint. Final verdict: CONDITIONALLY READY.
- Content Seeding Sprint (Apr 14): 26 real videos with thumbnails, clips, and assembly.
- Emotional Copy + Battle Hero Autoplay (Apr 14)
- Studio Creation Engine V2 (Apr 14): Draft Safety, Post-Generation Loop, Recent Drafts Panel, Guided Start V2.
- Studio Fresh Session Fix (Apr 14)
- P0.5 Performance Hardening (Apr 14): 7 API calls -> 1, load 5s -> 1.8s
- P0 Performance Sprint (Apr 14): Code splitting, TTL caching, image lazy loading
- CTA Route Separation Fix (Apr 13)
- UX Trust Fixes (Apr 13)
- Google Sign-In Hardened (Apr 13)
- P0 Feed Fix (Apr 13)
- CTA Conversion Redesign v2 (Apr 13)
- Entry Conversion Engine
- Consumption-First UI
- Queue System
- Data Integrity
- Export Pipeline
- Conversion Analytics Dashboard
- Psychology Layer v1+v2
- WIN/LOSS Moments + BattlePulse
- Push Notifications on ALL rank drops
- WIN Share Trigger
- Autoplay Hook Quality
- Battle Paywall Modal (Cashfree inline)
- Free Entry Limit Enforcement
- Watch Page (7 components complete)
- Pipeline > Battle auto-redirect
- XSS Sanitization on draft save endpoint (Apr 14)

---

## QA Status (Apr 14, 2026)

| Layer | Tests | Passed | Status |
|-------|-------|--------|--------|
| Smoke Tests | 20 | 20 | ALL PASS |
| Regression Suite | 69 | 69 | ALL PASS |
| Negative/Failure | 25 | 25 | ALL PASS (post-fix) |
| **Total** | **114** | **114** | **CONDITIONALLY READY** |

### Defects Found & Fixed
- DEF-001 (HIGH): XSS in draft save — FIXED, VERIFIED

### Conditions for Production Ready
1. Manual Google OAuth test in real browser
2. Resend email domain verification (user DNS action)
3. Real user traffic validation (20-50 users)

---

## Backlog

### P1
- Push live traffic (20-50 real users) and track funnel signals
- WebP/AVIF image optimization for banners/thumbnails
- Optimize thresholds based on traffic data
- Follow Creator / Network Graph
- Auto-Recovery FAILED_PERSISTENCE

### P2
- Category-specific AI hook selection policies
- Replace asyncio.create_task with Celery
- Personalized headline serving by channel
- Admin WebSocket upgrade
- Resend domain verification (blocked on DNS)
