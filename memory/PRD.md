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
        │   ├── StoryVideoPipeline.js  # Main video generation UI with zero-friction entry + login gate
        │   ├── ContentEngine.js       # Admin content generation + rating
        │   ├── AdminDashboard.js      # Truth-based admin metrics
```

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

### Phase 11: Dashboard Transformation — Story-First Experience
- Hero Section, Universal Prompt Bar, Live Social Proof, Trending Stories Grid

### Phase 12: P0.5 "Make It Look Alive" (2026-03-26)
- Rotating Hero Carousel (6s cycle, pause on hover, progress dots)
- Truth-Based Hype Stats (never shows zeros)
- Story Card Social Proof (Just dropped / Early story / Trending)
- First Mover Advantage ("Be first to continue")
- Hover Motion Previews (zoom + brightness)
- Scroll Trap (dynamic story-specific hooks)
- Shimmer CTA Animations

### Phase 13: P1 Zero-Friction Entry (2026-03-26)
- Studio accessible WITHOUT login at /app/story-video-studio
- Unauthenticated users can fill title, story text, animation style, age group, voice
- Login gate triggers ONLY on "Generate Video" click
- Gentle login prompt: "Log in to generate your story" with "50 free credits on signup"
- ALL form state saved to localStorage before login redirect
- State fully restored after login (title, text, style, age, voice, remix data)
- Dashboard "Continue Story" buttons save remix_data to localStorage for seamless handoff
- Shared link flow: PublicCreation → saves remix_data → studio (no login wall)
- Welcome overlay appears after state restoration confirming work is preserved

## Key DB Schema
- `users`: Profile, role, credits (50 standard)
- `pipeline_jobs`: Legacy video generation jobs
- `story_engine_jobs`: Real Sora 2 video jobs with Ken Burns fallback tracking
- `seed_stories`: Content engine generated stories with quality scores
- `video_ratings`: Hook quality ratings per job
- `credit_transactions`: Credit ledger

## 3rd Party Integrations
- OpenAI GPT-4o-mini, GPT Image 1, Sora 2, TTS — Emergent LLM Key
- Resend (Email Nudges) — User API Key
- Cashfree (Payments) — User API Key
- Cloudflare R2 (Object Storage)

## Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Current Blocker
Emergent LLM key budget depleted. User needs to add balance at Profile > Universal Key > Add Balance.

## Prioritized Backlog

### P0 (After Budget Top-Up)
- Generate 10 controlled videos through scoring pipeline
- Rate each video's hook quality

### P1
- Share Rewards: +5 credits per share, +10 if someone continues
- Click Psychology optimization on story cards

### P2
- Gallery/Explore page with categorized outputs
- Rebuild /share/:id pages as conversion pages
- Auto-improve weak hooks via GPT rewriting
- A/B test hook text variations on public pages

### P3
- Self-hosted GPU migration (Wan2.1, Kokoro)
- Mobile App Wrapper
- Collaborative story creation
