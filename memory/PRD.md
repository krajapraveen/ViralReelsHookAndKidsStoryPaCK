# Story Universe Engine — Product Requirements Document

## Original Problem Statement
Build a "Story Universe Engine" — a full-stack AI creator suite that lets users create animated story videos through a multi-step pipeline (planning → scenes → images → video → audio → assembly). The platform includes 11 creator tools, a growth/engagement engine, monetization via Cashfree payments, and a viral sharing loop.

## Core Architecture
- **Frontend**: React 18 + Tailwind + Shadcn/UI (port 3000)
- **Backend**: FastAPI + Motor (MongoDB) (port 8001)
- **Database**: MongoDB (creatorstudio_production, 162+ collections)
- **Object Storage**: Cloudflare R2
- **AI**: OpenAI GPT-4o-mini, GPT Image 1, Sora 2, TTS via Emergent LLM Key
- **Payments**: Cashfree

## Homepage Architecture (Sections 0-18)

### Section Order (enforced)
1. Hero Story Section
2. Story Feed Rows (Trending / Fresh / Continue / Unfinished)
3. Secondary Feature Cards (11 creator tools)
4. Create Bar + Footer

### Rules
- Story sections remain primary, tool cards secondary
- Never show empty/dead sections — inject seed cards when real data insufficient
- All 4 rows ALWAYS render
- No hidden sections from conditional rendering bugs

## What's Been Implemented

### Completed (2026-03-29)
- **Homepage Architecture (Sections 0-18)**:
  - Hero Section with auto-rotate carousel, video/poster/gradient fallback, FEATURED/style/LIVE badges, "Continue Story" + "Create Your Version" CTAs
  - 4 story feed rows: Trending Now, Fresh Stories, Continue Your Story, Unfinished Worlds — all always render with seed card fallback
  - 11 large secondary feature cards: Story Video, Story Series, Character Memory, Reel Generator, Photo to Comic, Comic Storybook, Bedtime Stories, Reaction GIF, Caption Rewriter, Brand Story, Daily Viral Ideas
  - Create bar with prompt prefill
  - Credits display: exact count / Unlimited / skeleton / login CTA
  - Footer with live stats

- **Backend Feed API Enhancement**: `/api/engagement/story-feed` returns separate arrays: `featured_story`, `trending_stories[]`, `fresh_stories[]`, `continue_stories[]`, `unfinished_worlds[]`. Each item has: job_id, title, hook_text, story_prompt, thumbnail_url, poster_url, preview_url, output_url, animation_style, parent_video_id, badge, character_summary

- **Story Card → Studio Prefill Flow**: Full prefill object (title, prompt, animation_style, parent_video_id) passed from hero, cards, and create bar. Studio stays in INPUT phase — no auto-generation.

- **Homepage Performance**: IntersectionObserver lazy loading in SafeImage. Only hero poster preloaded eagerly. All other images deferred.

- **FFmpeg Pipeline Fix**: Transition name sanitization (`cut→fade`, `crossfade→fade`). Planning retry on LLM failure.

- **Pipeline Thumbnail Compression**: Assembly now generates `thumbnail_small` (400x530 compressed JPEG) for feed cards + `poster_large` for hero.

- **Technical Architecture Document**: `/app/ARCHITECTURE.md`

### Previously Completed
- Admin Sidebar Navigation (AdminLayout.js)
- Story-to-Video full pipeline
- Cashfree payment integration
- Credit system (50 credits standard)
- Trust-based admin dashboard
- Public share pages with momentum-based social proof
- Google OAuth + JWT auth

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Key Documents
- /app/ARCHITECTURE.md — Full technical architecture
- /app/test_reports/iteration_361.json — Homepage architecture test (all pass)
- /app/test_reports/iteration_360.json — P0 fixes test (all pass)
