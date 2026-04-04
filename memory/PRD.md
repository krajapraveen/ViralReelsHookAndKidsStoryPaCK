# Daily Viral Idea Drop — PRD

## Original Problem Statement
Build a "Growth Engine" / "Daily Viral Idea Drop" — a queue-driven AI content creation platform. The product must never show a dead-end UI and must be optimized strictly for growth and conversion.

## Core Architecture
- React frontend + FastAPI backend + MongoDB
- 7 background workers: text, image, audio, video, packaging, orchestrator, repair
- Queue abstraction, fallback ladder (GPT-4o-mini → Gemini → templates)
- Teaser-first share pages with soft paywalls

## 3rd Party Integrations
- OpenAI & Gemini (Emergent LLM Key)
- Cloudflare R2 (Object Storage)
- Cashfree (Payments)
- Google Auth (Emergent-managed)

## What's Been Implemented

### Phase 1 & 2: Backend Workers (DONE)
### Growth Engine (DONE)
### P0 Fix: Empty Feed Blocker (DONE)
### P0 Fix: Generation Blank Screen (DONE — April 4, 2026)
### P0 Fix: Broken Media Assets (DONE — April 4, 2026)
- Video worker re-encodes with system ffmpeg (baseline h264, faststart)
- VideoAsset, ThumbnailAsset, VoiceoverAsset components with onError fallbacks

### P0 Fix: "Generate Another Pack" Dead Button (DONE — April 4, 2026)
- Root cause: `<Link to="/app/daily-viral-ideas">` navigated to the same route without resetting `view` state
- Fix: Replaced with `<button onClick={onGoToFeed}>` that resets view to 'feed', clears jobId, updates URL
- Verified: Click returns to feed with all ideas visible

### P0 Fix: Credit Reset (DONE — April 4, 2026)
- Hard reset all 30 non-admin users to exactly 50 credits
- 3 admin users excluded (ADMIN/SUPERADMIN roles untouched)
- Signup defaults already at 50 for all paths (email, Google)
- Before: 4 users had incorrect balances (999999999, 998623, 160, 100)

### Admin Dashboard Status (April 4, 2026)
- All backend endpoints return 200 OK (summary, funnel, reliability, revenue, series, credits, conversion, leaderboard, share-rewards, comic-health, production-metrics)
- Dashboard loads correctly in preview with zero errors
- User's production "Failed to load" error is a deployment/environment mismatch, not a code bug

## User Mandate
- Growth and Conversion only. No new features.

## Backlog (Frozen)
- (P1) Migrate media to R2 for cross-deployment persistence
- (P1) A/B test hook variations, auto-share prompts
- (P1) Personalization, Admin Dashboard enhancements, Precomputed Packs
- (P2) Remix Variants, Story Chain leaderboard, UI polish

## Key Files
- `/app/frontend/src/pages/DailyViralIdeas.js` — Feed, Progress, Result + media components
- `/app/backend/services/viral/workers/video_fast_worker.py` — Video worker with ffmpeg re-encode
- `/app/backend/routes/viral_ideas_v2.py` — Feed, generation
- `/app/backend/routes/admin_metrics.py` — Admin metrics
- `/app/backend/routes/production_metrics.py` — Production metrics

## Credentials
- Test: `test@visionary-suite.com` / `Test@2026#`
- Admin: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`
