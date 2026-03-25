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
│   │   ├── public_routes.py       # Social proof, live activity feed
│   ├── services/
│   │   ├── story_engine/          # Real Sora 2 video pipeline
│   │   │   ├── pipeline.py        # Orchestrator with Ken Burns fallback
│   │   │   ├── state_machine.py   # Job state management
│   │   │   ├── continuity.py      # Asset validation
│   │   │   └── adapters/          # Sora 2, GPT Image 1, TTS, FFmpeg
│   │   ├── pipeline_engine.py     # Legacy pipeline
│   │   ├── email_service.py       # Resend email nudges
└── frontend/
    └── src/
        ├── pages/
        │   ├── StoryVideoPipeline.js  # Main video generation UI
        │   ├── ContentEngine.js       # Admin content generation + rating
        │   ├── AdminDashboard.js      # Truth-based admin metrics
```

## Key Technical Concepts
- **Graceful Degradation**: When Sora 2 fails (budget), pipeline falls back to Ken Burns (FFmpeg zoom-pan on keyframes), marking job PARTIAL_READY
- **Quick Render Mode**: User-facing message when fallback is used
- **Controlled Batch**: Exact category distribution (4 emotional, 3 mystery, 2 kids, 1 viral) for quality validation
- **Hook Quality Rating**: Admin rates videos HIGH/MEDIUM/LOW with continuation + share signals
- **Micro Metrics**: Tracks continuation_rate, share_rate per video and per rating level

## What's Been Implemented
### Phase 1-7: Core Platform (Previous Forks)
- Full auth, credit system (50 credits standard), Cashfree payments
- Story series, character creation, GIF maker
- Admin dashboard with truth-based metrics
- Resend email nudges, compete mechanics, K-Factor dashboard

### Phase 8: Story Engine — Real Video Output
- Real Sora 2 video generation pipeline
- GPT Image 1 keyframe generation
- OpenAI TTS narration
- Ken Burns fallback (FFmpeg) when budget exceeded
- FFmpeg assembly (stitch clips + audio + preview + thumbnail)

### Phase 9: Content Validation Infrastructure (Current Session)
- **P0 E2E Validation**: All 10 test cases passed (Generate → Watch → Continue → Share → Ken Burns fallback)
- **FFmpeg installed** — was missing, breaking all video assembly
- **Quick Render Mode banner** — Shows only when Ken Burns fallback was actually used
- **Fallback metadata** — Backend tracks used_ken_burns_fallback, sora_clips_count, fallback_clips_count
- **Controlled Batch Generation** — POST /api/content-engine/generate-controlled with exact category distribution
- **Story Engine Publishing** — POST /api/content-engine/publish-to-story-engine/{story_id}
- **Hook Quality Rating** — POST /api/content-engine/rate-video (HIGH/MEDIUM/LOW)
- **Micro Metrics Dashboard** — GET /api/content-engine/batch-metrics

## Key DB Schema
- `users`: Profile, role, credits (50 standard)
- `pipeline_jobs`: Legacy video generation jobs
- `story_engine_jobs`: Real Sora 2 video jobs with Ken Burns fallback tracking
- `seed_stories`: Content engine generated stories with quality scores
- `video_ratings`: Hook quality ratings per job
- `credit_transactions`: Credit ledger

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
**Emergent LLM key budget depleted** ($202.62/$202.44). User needs to add balance at Profile → Universal Key → Add Balance before generating new content.

## Prioritized Backlog
### P0 — Ready to Execute (After Budget Top-Up)
- Generate 10 controlled videos (4 emotional, 3 mystery, 2 kids, 1 viral)
- Rate each video's hook quality
- Identify top 3 hooks
- Validate continuation + share behavior

### P1 — Scale What Works
- Generate 30-50 videos from validated hooks
- Run social media ads with top hooks
- A/B test hook text variations on public pages

### P2 — Platform Optimization
- Migrate to self-hosted GPU stack (Wan2.1, Kokoro) — spec in SELF_HOSTED_STACK.md
- Upgrade admin dashboard to WebSockets
- Implement "Remix Variants" on share pages
- Story Chain leaderboard

### P3 — Future
- Mobile App Wrapper
- Collaborative story creation
- Scale to 100+ videos
