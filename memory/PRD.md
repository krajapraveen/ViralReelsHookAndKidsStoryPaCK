# Visionary Suite — Growth Engine PRD

## Original Problem Statement
Build a viral, addictive story-driven platform ("Growth Engine") with:
- Real Story-to-Video generation pipeline (Sora 2, GPT Image 1, OpenAI TTS)
- K-factor optimization, forced share gates, email nudges
- Content Seeding Engine for hooks and cliffhangers
- Graceful degradation when API budget is exceeded

## User Personas
- **Admin/Creator**: Manages content, monitors growth metrics, rates video quality
- **End User**: Creates stories, watches videos, continues/shares with friends

## Core Architecture
```
/app/
├── backend/
│   ├── routes/
│   │   ├── content_engine.py     # Content generation, controlled batch, video rating, metrics
│   │   ├── story_engine_routes.py # Real video generation endpoints
│   │   ├── pipeline_routes.py     # Legacy pipeline (images+voices)
│   │   ├── share.py               # Share creation and retrieval
│   │   ├── admin_metrics.py       # Truth-based admin dashboard
│   │   ├── auth.py                # Auth with standardized 50 credits
│   │   ├── engagement.py          # Feeds for dashboard (trending, hero, story-feed)
│   ├── services/
│   │   ├── story_engine/          # Real Sora 2 video pipeline
│   │   │   ├── pipeline.py        # Orchestrator with Ken Burns fallback
│   │   │   ├── state_machine.py   # Job state management
│   │   │   ├── continuity.py      # Asset validation
│   │   │   └── adapters/          # Sora 2, GPT Image 1, TTS, FFmpeg
│   │   ├── hook_scoring_engine.py # Hybrid Rule + GPT hook evaluator
│   │   ├── pipeline_engine.py     # Legacy pipeline
│   │   ├── email_service.py       # Resend email nudges
└── frontend/
    └── src/
        ├── pages/
        │   ├── Dashboard.js           # Story-first feed with rotating hero, hype UI, scroll trap
        │   ├── StoryVideoPipeline.js  # Main video generation UI
        │   ├── ContentEngine.js       # Admin content generation + rating
        │   ├── AdminDashboard.js      # Truth-based admin metrics
```

## Key Technical Concepts
- **Graceful Degradation**: When Sora 2 fails (budget), pipeline falls back to Ken Burns (FFmpeg zoom-pan on keyframes), marking job PARTIAL_READY
- **Quick Render Mode**: User-facing message when fallback is used
- **Controlled Batch**: Exact category distribution (4 emotional, 3 mystery, 2 kids, 1 viral)
- **Hook Quality Rating**: Admin rates videos HIGH/MEDIUM/LOW with continuation + share signals
- **Hybrid Hook Scoring**: Rule-based filter + GPT evaluation. Only score >= 70 goes to video gen
- **Truth-Based Hype**: Never show zero metrics. Reframe with positive, honest text

## What's Been Implemented

### Phase 1-7: Core Platform (Previous Forks)
- Full auth, credit system (50 credits standard), Cashfree payments
- Story series, character creation, GIF maker
- Admin dashboard with truth-based metrics
- Resend email nudges, compete mechanics, K-Factor dashboard

### Phase 8: Story Engine — Real Video Output
- Real Sora 2 video generation pipeline
- GPT Image 1 keyframe generation, OpenAI TTS narration
- Ken Burns fallback (FFmpeg) when budget exceeded
- FFmpeg assembly (stitch clips + audio + preview + thumbnail)

### Phase 9: Content Validation Infrastructure
- E2E Validation of Pipeline (all test cases passed)
- FFmpeg installed, Quick Render Mode banner, Fallback metadata
- Controlled Batch Generation, Story Engine Publishing, Hook Quality Rating, Micro Metrics

### Phase 10: Hybrid Hook Scoring Engine
- Rule-Based Filter (Stage 1) + GPT Scoring (Stage 2) + Final Decision (Stage 3)
- Admin UI with score badges, Score All button, rejection reasons

### Phase 11: Dashboard Transformation — Story-First Experience
- Hero Section, Universal Prompt Bar, Live Social Proof, Trending Stories Grid
- Character Universe, Engagement Cards, Tools Demoted

### Phase 12: P0.5 "Make It Look Alive" (Current Session — 2026-03-26)
- **Rotating Hero Carousel**: Cycles through 5 stories every 6 seconds, smooth fade, pause on hover, progress dots
- **Truth-Based Hype Stats**: "59 stories created" | "Fresh stories waiting" | "Be the first to continue" — never shows zeros
- **Story Card Social Proof**: Dynamic badges — "Just dropped" (emerald, 0 conts), "Early story" (violet, 1-9), "Trending" (amber, 10+)
- **First Mover Advantage**: "Be first to continue" green CTA for 0-continuation stories
- **Hover Motion Previews**: Zoom (scale 1.1) + brightness increase on story card hover
- **Scroll Trap**: Dynamic story-specific hooks between trending and characters ("The next chapter is waiting...")
- **Shimmer CTA Animations**: Pulsing glow on all primary action buttons

## Key DB Schema
- `users`: Profile, role, credits (50 standard)
- `pipeline_jobs`: Legacy video generation jobs
- `story_engine_jobs`: Real Sora 2 video jobs with Ken Burns fallback tracking
- `seed_stories`: Content engine generated stories with quality scores
- `video_ratings`: Hook quality ratings per job
- `credit_transactions`: Credit ledger
- `character_profiles`, `story_characters`: Character data for dashboard feed

## 3rd Party Integrations
- OpenAI GPT-4o-mini (Planning/Content Engine) — Emergent LLM Key
- OpenAI GPT Image 1 (Keyframes) — Emergent LLM Key
- Sora 2 (Video Clips) — Emergent LLM Key
- OpenAI TTS (Narration) — Emergent LLM Key
- Resend (Email Nudges) — User API Key
- Cashfree (Payments) — User API Key
- Cloudflare R2 (Object Storage)

## Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Current Blocker
**Emergent LLM key budget depleted**. User needs to add balance at Profile > Universal Key > Add Balance before generating new content.

## Prioritized Backlog

### P0 — Ready to Execute (After Budget Top-Up)
- Generate 10 controlled videos through scoring pipeline
- Rate each video's hook quality → Pick top 3

### P1 — Continue Story Everywhere + Share Rewards
- Zero-Friction Entry: Remove login wall for first "Continue Story" experience
- Share rewards: +5 credits per share, +10 if someone continues
- Streak rewards: +5 credits for daily creation streak

### P2 — Gallery/Explore + Share Page Rebuild
- Gallery/Explore page with 50-100 real outputs, categorized
- Rebuild /share/:id pages as conversion pages with hook text + Continue Story CTA
- A/B test hook text variations on public pages

### P3 — Scale & Optimize
- Auto-improve weak hooks (rewrite LOW → HIGH)
- Migrate to self-hosted GPU stack (Wan2.1, Kokoro)
- Mobile App Wrapper
- Collaborative story creation
