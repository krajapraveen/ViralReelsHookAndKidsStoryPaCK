# Visionary Suite - Product Requirements Document

## Original Problem Statement
Build a full-stack AI Creator Suite ("Visionary Suite") with a compulsion-driven growth engine, monetization system, and complete legal/copyright compliance.

## Core Product
A React + FastAPI + MongoDB AI-powered creator platform offering:
- Story video generation (with AI narration, scenes, music)
- Reel/short-form video script generation
- Social bio generation  
- Comic/coloring book creation
- Photo-to-comic transformation
- Content repurposing tools
- Admin dashboard with truth-based metrics

## User Personas
1. **Content Creators**: Generate viral content for social platforms
2. **Parents/Educators**: Create kids story videos
3. **Small Business Owners**: Brand story building, promo videos
4. **Admin**: Monitor platform health, users, revenue

## Architecture
```
/app/
├── backend/ (FastAPI + MongoDB)
│   ├── routes/ (API endpoints)
│   ├── services/ (Business logic, AI integrations, pipeline)
│   └── server.py (Entry point)
└── frontend/ (React + Tailwind + Shadcn)
    ├── src/pages/ (Feature pages)
    ├── src/components/ (Reusable components)
    └── src/utils/ (API, analytics, helpers)
```

## What's Implemented (as of 2026-04-06)
- Full AI creation suite (Story Video, Reel Generator, Bio Generator, Comic tools, etc.)
- Growth Engine (Share pages, First Video Free, 1-Tap Remix, Watermark, Referrals)
- Cashfree payment integration
- Google OAuth + JWT auth
- Admin dashboard with truth-based metrics
- Credit system (50 credits for new users)
- Momentum-based social proof
- Legal/Copyright compliance audit (COMPLETED)

## Completed Tasks (Current Session)
- [x] P0 Legal/Copyright cleanup across 30+ frontend files and 2 backend files
- [x] Replaced all trademarked brand names with generic equivalents
- [x] Blog content and categories genericized
- [x] Backend style prompts cleaned (Pixar→studio-quality, Studio Ghibli→Japanese animation)
- [x] Fixed 3 compile errors introduced during cleanup (duplicate imports, misplaced const)
- [x] QA/Production Readiness Report delivered

## Backlog
### P1
- Pipeline Parallelization (Script → Voice + Images in parallel → Composition)
- A/B test hook text variations on public pages
- Character-driven auto-share prompts after creation

### P2
- Upgrade admin dashboard from polling to WebSockets
- "Story Chain" leaderboard to gamify continuations
- "Remix Variants" on share pages
- General UI polish and style preset preview thumbnails

## 3rd Party Integrations
- OpenAI & Gemini (Emergent LLM Key)
- Cloudflare R2 (Object Storage)
- Cashfree (Payments)
- Google Identity Services (OAuth 2.0)

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
