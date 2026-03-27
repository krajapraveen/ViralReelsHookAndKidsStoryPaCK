# Visionary Suite — Product Requirements Document

## Original Problem Statement
Build a viral, addictive "Story Universe Engine" with an optimized frontend growth loop, a Private Story-to-Video Engine backend, a data-driven content optimization system, and production-grade UX with truthful, compelling content.

## Architecture
- **Frontend**: React, Shadcn UI, TailwindCSS
- **Backend**: FastAPI, Python 3.11
- **Database**: MongoDB (creatorstudio_production)
- **Storage**: Cloudflare R2 (public URLs)
- **AI**: GPT-4o-mini, GPT Image 1, Sora 2, OpenAI TTS — via Emergent LLM Key
- **Video Assembly**: FFmpeg 5.1 with resilient detached execution
- **Payments**: Cashfree
- **A/B Testing**: Custom lean framework
- **Email**: SendGrid (KEY EXPIRED — needs user to provide new key)

## Implemented Features

### P0 E2E Story Engine — PROVEN
- Full pipeline INIT->PLANNING->CHARACTER->MOTION->KEYFRAMES->CLIPS->AUDIO->ASSEMBLY->READY

### P0 Media Display Fix (2026-03-27)
- **SafeImage with retry**: One-time cache-bust retry on image load failure
- **Gallery**: Switched to SafeImage, improved error handling, shows "All (30)"
- **Explore**: Switched to SafeImage for all cards
- **Landing Showcase**: Already using SafeImage, verified working with 10 cards
- Testing: 100% (iteration_349)

### P0 Production Issues Fixed (2026-03-27)
1. **Landing Page Hero**: "Stories that don't end until you continue them"
2. **Misleading Labels Removed**: "No login required", "Free to start", "Ready in 30s"
3. **Footer**: 4 columns with distinct descriptions, contact email
4. **Legal Section**: Distinct descriptions for Privacy, Terms, Cookies
5. **Final CTA**: "Someone already started this story"
6. **"Happening Now" Feed**: Compelling copyright-safe titles, diverse countries
7. **Guest Mode**: First-time users get ONE free generation, IP-tracked
8. **Forgot Password**: Honest error when SendGrid fails
- Testing: 100% (iteration_348)

### P0 Character-Driven Auto-Share Prompt — VERIFIED (2026-03-26)
### P1 FFmpeg Subprocess Resilience — IMPLEMENTED (2026-03-26)
### P1 A/B Hook Testing — VERIFIED (2026-03-26)

## Critical Open Issues
1. **SendGrid API Key EXPIRED** — Password reset emails cannot be sent

## Prioritized Backlog
### P0 — Blocked
- Fix email delivery (requires new SendGrid key from user)

### P1 — Next Up
- User to provide updated pricing/credits for Pricing page
- E2E degraded/fallback job + continue/chain job (pending LLM budget)
- Viral headline rotation, ad copy templates

### P2 — Future
- Auto-improve hooks from A/B data
- Self-hosted GPU models
- WebSocket admin, Story Chain leaderboard

## Credentials
- Test: `test@visionary-suite.com` / `Test@2026#`
- Admin: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`
