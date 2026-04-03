# AI Creator Suite — Product Requirements Document

## Original Problem Statement
Full-stack AI creator suite with tools for story/comic/GIF/video generation, character creation, brand kits, and social content. The platform uses a credit-based monetization model with Cashfree payments.

## Core Architecture
- **Frontend**: React (port 3000)
- **Backend**: FastAPI (port 8001)
- **Database**: MongoDB
- **AI**: OpenAI GPT-4o-mini, GPT Image 1, Sora 2, Gemini (via Emergent LLM Key)
- **Storage**: Cloudflare R2
- **Payments**: Cashfree
- **Auth**: Emergent-managed Google Auth + JWT

## Completed Features

### P0 — Safe Rewrite Engine (April 2026)
- **Centralized rewrite engine** at `backend/services/rewrite_engine/`
  - `rule_rewriter.py`: 200+ term mappings (brands, franchises, characters, celebrities, platforms)
  - `rewrite_service.py`: Orchestrator — detect, rewrite, continue. Never blocks.
- **Replaced hard-blocking in 20+ files**: All `BLOCKED_KEYWORDS`, `check_copyright`, `check_copyright_violation`, `screen_safety` functions updated to use safe_rewrite()
- **Preserved harmful content blocking**: nsfw, violence, gore, explicit still blocked
- **Preserved negative prompts**: Image generation still includes copyright safety in negative prompts
- **Files modified**: safety.py, pipeline.py, caption_rewriter_pro.py, brand_story_builder.py, story_video_studio.py, characters.py, comic_storybook_v2.py, photo_to_comic.py, story_episode_creator.py, comment_reply_bank.py, instagram_bio_generator.py, youtube_thumbnail_generator.py, content_challenge_planner.py, offer_generator.py, reaction_gif.py, bedtime_story_builder.py, story_hook_generator.py, story_video_fast.py, genstudio.py, generation.py, revenue_protection.py
- **Test result**: 26/26 tests passed (iteration_423)

### Previous Completions
- Production Metrics Dashboard
- Brand Kit Generator (stabilized)
- Photo-to-Reaction GIF (zero-friction single-screen UI, viral packs)
- Character Studio (backward-compatible, actionable CTAs)
- Growth Engine (compulsion loops, social proof)
- Cashfree Payment Integration
- Credit System (50 credits standard)
- Truth-based Admin Dashboard

## Prioritized Backlog

### P0 (Current)
- Drive real traffic to reach 100-200 real jobs (user action)

### P1 (Upcoming — FROZEN until traffic data)
- Auto captions (viral text) for Reaction GIFs
- Multi-reaction pack generation (6 GIFs at once)
- Character DNA System (zero-drift guaranteed characters)

### P2 (Future)
- Smart router, repair pipeline, GPU optimization
- Advanced analytics
- A/B test hook text variations
- Character-driven auto-share prompts
- Remix Variants on share pages
- WebSocket admin dashboard
- Story Chain leaderboard

## Test Credentials
- Test User: `test@visionary-suite.com` / `Test@2026#`
- Admin User: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`
