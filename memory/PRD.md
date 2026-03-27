# Visionary Suite — Product Requirements Document

## Original Problem Statement
Build a viral, addictive "Story Universe Engine" with an optimized frontend growth loop, a Private Story-to-Video Engine backend, a data-driven content optimization system, and production-grade UX with truthful, compelling content.

## Architecture
- **Frontend**: React, Shadcn UI, TailwindCSS
- **Backend**: FastAPI, Python 3.11
- **Database**: MongoDB
- **Storage**: Cloudflare R2
- **AI**: GPT-4o-mini, GPT Image 1, Sora 2, OpenAI TTS — via Emergent LLM Key
- **Video Assembly**: FFmpeg 5.1 (system binary) with resilient detached execution
- **Payments**: Cashfree
- **A/B Testing**: Custom lean framework (deterministic session-based assignment, deduped events)
- **Email**: SendGrid (KEY EXPIRED — needs user to provide new key)

## Implemented Features

### P0 E2E Story Engine — PROVEN
- Full pipeline: INIT->PLANNING->CHARACTER->MOTION->KEYFRAMES->CLIPS->AUDIO->ASSEMBLY->READY

### P0 Character-Driven Auto-Share Prompt — VERIFIED (2026-03-26)
- ForceShareGate modal via React Portal, dynamic character data injection

### P0 Production Issues Fixed (2026-03-27)
1. **Landing Page Hero** — Updated to "Stories that don't end until you continue them"
2. **Misleading Labels Removed** — "No login required", "Free to start", "Ready in 30s" all removed
3. **Footer Navigation** — All 4 columns with distinct, premium descriptions per user's exact copy
4. **Legal Section** — Privacy Policy, Terms, Cookies each have distinct professional descriptions
5. **Final CTA** — "Someone already started this story" / "Will you finish it?"
6. **"Happening Now" Feed** — Compelling copyright-safe story titles with diverse countries, fresh timestamps
7. **Guest Mode (Free Trial)** — First-time users get ONE free video generation without login, IP-tracked
8. **Explore Page** — Working with thumbnails (30 stories, 24 visible cards)
9. **Forgot Password** — Now returns honest error when email delivery fails (SendGrid key expired)
10. **Continue a Story** — Landing page section populated with real story cards

### P1 FFmpeg Subprocess Resilience — IMPLEMENTED (2026-03-26)
- Detached shell wrapper via nohup/setsid, survives hot-reloads

### P1 A/B Hook Testing — VERIFIED (2026-03-26)
- 4 variants (Mystery, Emotional, Shock, Curiosity) on 2 surfaces
- Admin "Hook A/B" tab with per-variant metrics and confidence warnings

### Earlier Completed Work
- Strict Credit Gate, Public Share Page Rebuild, Social Proof, Monetization (Cashfree)

## Critical Open Issues
1. **SendGrid API Key EXPIRED** — Password reset emails cannot be sent. User needs to provide a new valid SendGrid API key or replace with another email provider.

## Prioritized Backlog

### P0 — Blocked
- Fix email delivery (requires new SendGrid key from user)

### P1 — Next Up
- E2E: degraded/fallback job + continue/chain job (pending LLM budget)
- User to provide updated pricing/credits for Pricing page
- Viral landing page headline A/B rotation
- Ad copy for Instagram/YouTube (user provided templates)

### P2 — Future
- Auto-improve weak hooks based on A/B data
- Self-hosted GPU models for AI independence
- WebSocket admin, Story Chain leaderboard

## Key DB Collections
- `story_engine_jobs`, `ab_experiments`, `ab_assignments`, `ab_conversions`
- `free_trial_generations` — IP-based guest generation tracking
- `users`, `orders`, `feedback`, `ratings`, `credit_transactions`

## Credentials
- Test: `test@visionary-suite.com` / `Test@2026#`
- Admin: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`
