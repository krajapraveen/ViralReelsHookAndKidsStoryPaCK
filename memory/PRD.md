# Visionary Suite - Product Requirements Document

## Original Problem Statement
Rebuild Visionary Suite from an AI tools dashboard into an **addictive story-driven platform** with a Content Flywheel Engine. The mandate: solve the growth problem where users were not entering, engaging, or returning. Multi-phase transformation to establish "compulsion-driven" loops.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI
- **Backend**: FastAPI + MongoDB + Redis
- **AI Services**: OpenAI (GPT-4o-mini, GPT Image 1, Sora 2, TTS), Gemini (via Emergent LLM Key)
- **Payments**: Cashfree
- **Auth**: JWT + Emergent-managed Google Auth
- **Storage**: Cloudflare R2

## What's Been Implemented

### Phase 1: Homepage + Zero Friction (March 25)
- Story-driven hero with autoplaying videos and big CTAs
- Zero-friction entry (no login wall before Studio)
- Credit gate with Required/You Have/Shortfall display
- Gallery: Continue This Story primary + Add Twist/Make Funny secondary

### Phase 2: Viral Growth Engine (March 25)
- Results page WATCH -> CONTINUE -> LOOP -> SHARE
- Public share page conversion funnel
- Open-loop endings enforced in pipeline_engine.py
- Prefilled prompt engine, share rewards, funnel tracking

### Phase 3: Content Flywheel Engine (March 25)
- Character Universe with Follow/Remix, character feed, rankings
- Story Series Netflix Timeline with episode locks
- Notification system with 30s auto-refresh

### Phase 3 UX Audit (March 25)
- Character Page: action-first above-fold CTA, hook quote, social proof, stripped passive info
- Series Timeline: progress bar, cliffhanger preview, urgency CTAs, episode status nodes
- Follow System: wired to notifications, creator alerts on follow

### Phase 3.5 Behavioral Momentum (March 25)
- "Start with this story" entry story auto-selection on Character Page
- Delayed urgency triggers (5s: "Continue before others do")
- Per-episode hook text on Series Timeline
- Auto-scroll to current episode
- Dashboard Follow Feed ("From Characters You Follow")
- Auto-next trigger popup (8s after generation: "What happens next?")
- CTA glow animations + micro-UX

### Phase 4: Retention Engine (March 25)
**A) Nudge System:**
- Background scheduler (hourly) finds users with 6h+ inactive stories
- Creates in-app notifications with character name + cliffhanger + deep link
- Each notification includes: character name, hook text, story link

**B) Return Experience:**
- "Continue your story" banner above the fold on Dashboard
- Shows cliffhanger text, character name, series context
- Deep links to correct story with prefilled context

**C) Content Seeding API:**
- POST /api/retention/admin/seed-content — admin endpoint to batch-queue showcase stories
- GET /api/retention/admin/seed-status — check seed content progress
- Only creates real, valid outputs (no placeholders)

**D) Streak System (Simplified):**
- Daily streak counter tracking consecutive days of engagement
- Milestone rewards: Day 3 = +10 credits, Day 7 = +25 credits
- Displayed on Dashboard sidebar + Profile page
- Pipeline integration: auto-records activity on story completion

**E) Episode Milestone Rewards:**
- Every 5 episodes completed in a series = +5 credits
- Triggered automatically on successful episode generation

**F) Self-Hosted Stack Documentation:**
- Full architecture spec at /app/memory/SELF_HOSTED_STACK.md
- Models: Qwen2.5-14B (planning), Wan2.1-T2V-14B (video), Kokoro-82M (TTS)
- GPU recommendations: L40S or L4 for generation, CPU for app
- FFmpeg commands for stitching, crossfades, audio mixing, subtitles

## Prioritized Backlog

### P1 (High Priority)
- A/B test hook text variations on public pages
- Social distribution hooks on every creation
- Funnel tracking analytics deep dive (K-factor, share rate)
- Character-driven auto-share prompts

### P2 (Medium Priority)
- Remix Variants on share pages
- Admin dashboard WebSocket upgrade
- Style preset preview thumbnails
- Story Chain leaderboard gamification

### P3 (Lower Priority)
- Mobile app wrapper
- Collaborative story creation
- Character portrait generation
- Multi-language support
- Advanced character relationship graph
