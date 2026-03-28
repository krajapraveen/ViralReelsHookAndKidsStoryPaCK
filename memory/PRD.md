# Visionary Suite — Story Universe Engine

## Product Overview
A full-stack AI creator suite (React, FastAPI, MongoDB) with a compulsion-driven growth engine for creating animated story videos and other creative content. The platform is designed to feel like Netflix for AI stories — visual, alive, and addictive.

## Core Architecture
- **Frontend**: React + Shadcn UI, dark Netflix-style theme
- **Backend**: FastAPI + MongoDB
- **Storage**: Cloudflare R2
- **AI**: OpenAI GPT-4o-mini (planning), GPT Image 1 (keyframes), Sora 2 (video clips), TTS (narration)
- **Video Assembly**: FFmpeg (installed in container)
- **Payments**: Cashfree
- **Auth**: JWT + Emergent Google Auth

## What's Been Implemented

### Netflix-Style Dashboard (March 28, 2026)
- **Hero Section** (65vh): Full-width with gradient fallback, autoplay video support, carousel dots (5 stories), FEATURED badge, hook text, "Continue Story" + "Create Your Own" CTAs
- **Trending Now Row**: Horizontal scroll with 4:5 story cards, thumbnails, gradient overlays, TRENDING/HOT/NEW badges, hook text, "Continue Story" CTA, hover scale (1.05)
- **Just Dropped Row**: Second horizontal scroll row for newer stories
- **Scroll Hook**: "You won't believe what happens next..." gradient text between sections
- **Create Prompt**: Compact search bar with chip suggestions
- **Quick Tools**: Minimal tool chips at bottom (Story Video, Reels, Comic Book, Bedtime Story, Caption AI)
- **Removed**: "Popular Characters" (useless without avatars), "30 seconds" claim, tool grid layout
- **Fixed**: Credits display shows loading skeleton (not "..." dots) across 7+ files

### Core Pipeline Fix (March 28, 2026)
- **Root Cause**: FFmpeg not installed + shell escaping bug in xfade stitch
- **Fix**: Installed FFmpeg, inline runner, concat demuxer fallback
- **Result**: Full E2E pipeline: Planning → Keyframes → Sora 2 → TTS → FFmpeg → R2

### All Generation Tools Working
Reel Generator, Bedtime Story, Caption Rewriter, Brand Story, Story Generator, Comic Storybook, Coloring Book, Photo to Comic, GIF Maker

### Previous Work
- Compulsion-driven growth loop (ForceShareGate, share prompts, open-loop endings)
- 1-click continue flow with guest free generation
- Lean A/B Hook Testing (4 variants)
- SafeImage retry mechanism for R2 URLs
- Cashfree payments, credit system (50 credits for new users)
- Truth-based admin dashboard
- Diverse "Live on the Platform" feed

## Test Credentials
- **Test User**: test@visionary-suite.com / Test@2026#
- **Admin User**: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Known Issues
- R2 presigned URLs expire after ~4 hours (SafeImage shows gradient fallbacks)
- FFmpeg xfade transitions fail (concat fallback works — no smooth crossfades)
- SendGrid forgot-password email fails (401 — blocked on valid API key)

## Upcoming Tasks
- (P1) Fix R2 presigned URL re-signing on backend (fresh URLs per request)
- (P1) A/B test hook text variations on public pages
- (P2) Character avatars for "Popular Characters" section
- (P2) Remix Variants on share pages
- (P2) Self-Hosted GPU Models (Wan2.1, Kokoro)
- (P3) Auto-improve weak hooks from A/B data
- (P3) WebSocket admin dashboard
