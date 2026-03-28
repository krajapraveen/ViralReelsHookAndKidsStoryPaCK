# Visionary Suite — Story Universe Engine

## Product Overview
A full-stack AI creator suite (React, FastAPI, MongoDB) — a Netflix-style story platform where users create, watch, and continue AI-generated animated stories.

## Core Architecture
- **Frontend**: React + Shadcn UI, Netflix-style dark theme
- **Backend**: FastAPI + MongoDB
- **Storage**: Cloudflare R2 (served via backend proxy — no presigned URL issues)
- **AI**: OpenAI GPT-4o-mini (planning), GPT Image 1 (keyframes), Sora 2 (video clips), TTS (narration)
- **Video Assembly**: FFmpeg (installed in container)
- **Payments**: Cashfree
- **Auth**: JWT + Emergent Google Auth

## What's Been Implemented

### Netflix-Style Dashboard (March 28, 2026)
- **Hero Section** (55vh): Real thumbnail background via R2 proxy, carousel (5 stories), FEATURED badge, hook text, "Continue Story" + "Create Your Own" CTAs
- **Continue Watching**: Horizontal scroll, 8+ story cards with REAL AI thumbnails, TRENDING/HOT/NEW badges, hook text, "Continue Story >" CTA
- **Trending Now**: Larger horizontal scroll row with See All link
- **Scroll Hook**: "You won't believe what happens next..." gradient text with animated dots
- **Just Dropped**: Third row of story cards
- **Quick Tools**: Minimal tool chips at bottom (Story Video, Reels, Comic Book, Bedtime Story, Caption AI)

### R2 Media Proxy (March 28, 2026) — ROOT CAUSE FIX
- **Problem**: ALL R2 presigned URLs expired (403), R2 API keys couldn't generate new presigned URLs
- **Fix**: Backend proxy at `/api/media/r2/{key}` streams R2 objects directly via `get_object` API
- **Result**: All thumbnails and videos now load reliably through the proxy with 24h cache headers
- **Files**: `/app/backend/routes/media_proxy.py` (new), `/app/backend/routes/engagement.py` (modified)

### Core Pipeline Fix (March 28, 2026)
- Installed FFmpeg, inline runner, concat demuxer fallback
- Full E2E: Planning → Keyframes → Sora 2 → TTS → FFmpeg → R2

### All Generation Tools Working
Reel Generator, Bedtime Story, Caption Rewriter, Brand Story, Story Generator, Comic Storybook, Coloring Book, Photo to Comic, GIF Maker

### Credit Display Fix
- Replaced literal '...' with animated loading skeletons across 7+ files
- Dashboard, ReelGenerator, ComicStorybookBuilder, PhotoToComic, GifMaker, CreditStatusBadge

## Test Credentials
- **Test User**: test@visionary-suite.com / Test@2026#
- **Admin User**: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Known Issues
- FFmpeg xfade transitions fail (concat fallback works)
- SendGrid forgot-password email fails (401 — needs valid API key)

## Upcoming Tasks
- (P1) A/B test hook text variations
- (P1) Character avatars for stories
- (P2) Remix Variants on share pages
- (P2) Self-Hosted GPU Models (Wan2.1, Kokoro)
- (P3) Auto-improve weak hooks from A/B data
