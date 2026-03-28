# Visionary Suite — Story Universe Engine

## Product Overview
A full-stack AI creator suite (React, FastAPI, MongoDB) with a compulsion-driven growth engine for creating animated story videos and other creative content.

## Core Architecture
- **Frontend**: React + Shadcn UI, dark theme
- **Backend**: FastAPI + MongoDB
- **Storage**: Cloudflare R2
- **AI**: OpenAI GPT-4o-mini (planning), GPT Image 1 (keyframes), Sora 2 (video clips), TTS (narration)
- **Payments**: Cashfree
- **Auth**: JWT + Emergent Google Auth

## What's Been Implemented

### P0 — Core Generation Pipeline (FIXED - March 28, 2026)
- **Root Cause**: FFmpeg not installed in container + shell escaping issues in xfade stitch
- **Fix**: Installed FFmpeg, switched stitch to inline runner with single quotes, added concat demuxer fallback
- **Result**: Full end-to-end pipeline works: Planning → Keyframes → Sora 2 Clips → TTS → FFmpeg Assembly → R2 Upload
- **Verified**: Job 261430a2 completed with video, preview, and thumbnail uploaded to R2

### P0 — All Generation Tools Working
- Reel Generator ✅
- Bedtime Story Builder ✅
- Caption Rewriter Pro ✅
- Brand Story Builder ✅
- Story Generator ✅
- Comic Storybook ✅
- Coloring Book Wizard ✅
- Photo to Comic ✅
- GIF Maker ✅

### P1 — UI Dead States Eliminated (March 28, 2026)
- **Credit "dots" bug**: Replaced literal '...' with animated loading skeletons across 6 files (Dashboard, ReelGenerator, ComicStorybookBuilder, PhotoToComic, GifMaker, CreditStatusBadge)
- **Landing page empty showcase**: Added curated story hook fallback cards when no trending stories exist
- **Dashboard empty trending**: Added "Start a Story" cards with prompts when no trending stories

### Previously Completed
- Compulsion-driven growth loop (ForceShareGate, share prompts, open-loop endings)
- 1-click continue flow with guest (unauthenticated) free generation
- Lean A/B Hook Testing (4 variants, frontend tracking, Admin Dashboard)
- SafeImage retry mechanism for R2 presigned URLs
- Cashfree payment integration
- Credit system (50 credits for new users, strict enforcement)
- Truth-based admin dashboard
- Diverse "Live on the Platform" feed

## Test Credentials
- **Test User**: test@visionary-suite.com / Test@2026#
- **Admin User**: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Known Issues
- FFmpeg xfade transitions fail (concat fallback works — no smooth crossfades)
- SendGrid forgot-password email fails (401 — blocked on valid API key from user)
- R2 presigned URLs expire after 4 hours (SafeImage handles retries)

## Upcoming Tasks
- (P1) A/B test hook text variations on public pages
- (P1) Character-driven auto-share prompts
- (P2) Remix Variants on share pages
- (P2) WebSocket admin dashboard
- (P2) Self-Hosted GPU Models (Wan2.1, Kokoro)
- (P3) Auto-improve weak hooks from A/B data
