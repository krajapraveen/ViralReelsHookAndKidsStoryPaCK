# Visionary Suite - Product Requirements Document

## Original Problem Statement
Rebuild Visionary Suite from an AI tools dashboard into an **addictive story-driven platform** with a Content Flywheel Engine. Multi-phase transformation to establish compulsion-driven loops that make users enter, engage, and return.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI
- **Backend**: FastAPI + MongoDB + Redis
- **AI Services**: OpenAI (GPT-4o-mini, GPT Image 1, Sora 2, TTS), Gemini (via Emergent LLM Key)
- **Payments**: Cashfree
- **Auth**: JWT + Emergent-managed Google Auth
- **Storage**: Cloudflare R2

## What's Been Implemented

### Phase 1: Homepage + Zero Friction
- Story-driven hero, zero-friction entry, credit gating, gallery with Continue primary CTA

### Phase 2: Viral Growth Engine
- Results page WATCH→CONTINUE→LOOP→SHARE, public share conversion funnel, open-loop endings, prefilled prompts, share rewards

### Phase 3: Content Flywheel Engine
- Character Universe (Follow/Remix), Story Series Netflix Timeline, Notifications, Rankings

### Phase 3 UX Audit: Action-First Redesign
- Character Page: above-fold CTA, hook quote, social proof, stripped passive info
- Series Timeline: progress bar, cliffhanger preview, urgency CTAs, episode status nodes
- Follow System: wired to notifications, creator alerts

### Phase 3.5: Behavioral Momentum
- Entry story auto-selection, delayed urgency triggers, per-episode hooks, auto-scroll to current episode
- Dashboard Follow Feed, auto-next trigger popup (8s), CTA glow animations

### Phase 4: Retention Engine
- **Nudge System**: Hourly scheduler, 6h inactivity trigger, character name + cliffhanger + deep link notifications
- **Return Experience**: Above-fold "Continue your story" banner on Dashboard with deep link
- **Content Seeding API**: Admin batch-queue showcase stories
- **Streak System**: Day 3 = +10, Day 7 = +25 credits. Pipeline-integrated auto-recording
- **Episode Milestones**: Every 5 episodes = +5 credits

### Phase 4.5: Behavioral Tightening (Latest)
- **Forced Decision Modal**: 3-sec delay popup "Your story is waiting" with Continue Now / Later (sessionStorage de-dupe)
- **Post-Gen Loop Trigger**: "That was just the beginning..." + Continue Next Episode + Share buttons
- **Reward Celebration**: Toast with streak/episode milestone info when video completes
- **Emotional Streak Messaging**: Context-aware messages ("Don't break it", "You're on fire", "Continue today")
- **Hook-Based Content Seeding**: Emotional, mystery, kids, viral themes with hooks + cliffhangers
- **Email Nudges**: Queued with character name + cliffhanger + deep link (pending email service integration)

## Self-Hosted Stack
Full architecture spec at `/app/memory/SELF_HOSTED_STACK.md`:
- Qwen2.5-14B (planning), Wan2.1-T2V-14B (video), Kokoro-82M (TTS), FFmpeg (assembly)
- GPU recs: L40S/L4 for generation, CPU for app

## Prioritized Backlog

### P0 (Email Integration)
- Connect SendGrid/Resend to activate queued email nudges

### P1 (Growth Optimization)
- A/B test hook text variations on public pages
- Social distribution hooks on every creation
- Funnel analytics deep dive (K-factor, share rate, continuation_rate)
- K-factor optimization (viral scaling phase)

### P2 (Platform Enhancement)
- Remix Variants on share pages
- Admin dashboard WebSocket upgrade
- Style preset thumbnails
- Story Chain leaderboard

### P3 (Scale)
- Mobile app wrapper
- Collaborative story creation
- Character portrait generation
- Multi-language support
