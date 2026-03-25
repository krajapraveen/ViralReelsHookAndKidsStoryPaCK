# Visionary Suite - Product Requirements Document

## Original Problem Statement
Rebuild Visionary Suite from an AI tools dashboard into an **addictive story-driven viral platform**. Multi-phase transformation for compulsion-driven loops: enter → engage → return → share → grow.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI
- **Backend**: FastAPI + MongoDB + Redis
- **AI**: OpenAI (GPT-4o-mini, GPT Image 1, Sora 2, TTS), Gemini (Emergent LLM Key)
- **Payments**: Cashfree | **Auth**: JWT + Google Auth | **Storage**: Cloudflare R2

## Implemented Phases

### Phase 1: Homepage + Zero Friction
Story-driven hero, zero-friction entry, credit gating

### Phase 2: Viral Growth Engine
Results page WATCH→CONTINUE→LOOP→SHARE, open-loop endings, prefilled prompts

### Phase 3: Content Flywheel
Character Universe (Follow/Remix), Story Series Timeline, Notifications, Rankings

### Phase 3 + 3.5: UX Audit + Behavioral Momentum
Action-first CTA placement, entry story auto-selection, delayed urgency triggers, auto-scroll, follow feed, auto-next popup, CTA glow animations

### Phase 4 + 4.5: Retention Engine + Behavioral Tightening
- Nudge system (hourly, 6h inactivity, character name + cliffhanger + deep link)
- Return banner + forced decision modal (3 sec delay, Continue Now / Later)
- Content seeding API (hook-based themes: emotional, mystery, kids, viral)
- Streak system (Day 3: +10, Day 7: +25 credits, emotional messaging)
- Episode milestones (every 5 episodes = +5 credits)
- Reward celebration toasts
- Email nudges (queued, pending email service)

### Phase 5: K-Factor Engine (Viral Scaling) ← LATEST
- **Share page rebuilt** as conversion machine: social proof banner ("X people continued"), mid-page "This story has no ending" hook, urgency badge, cliffhanger text
- **Share UX**: WhatsApp, X, Instagram, Copy Link — 4 buttons
- **Upgraded rewards**: +5 share, +15 friend continues, +25 friend signs up
- **Signup referral reward**: POST /api/growth/signup-referral-reward
- **K-factor metrics**: GET /api/growth/k-factor (user + platform 7-day metrics)
- **Remix variants**: Comic Book, GIF, Reel, Bedtime on share page
- **PostGenPhase**: Upgraded share section with all reward tiers

## Self-Hosted Stack
Architecture spec at `/app/memory/SELF_HOSTED_STACK.md`

## Prioritized Backlog

### P0 (Immediate)
- Connect email service (SendGrid/Resend) to activate queued nudges
- Referral tracking in signup flow (detect shared link → attribute signup)

### P1 (Growth)
- A/B test hook text variations on share pages
- Social distribution hooks on every creation
- Compete mechanic (Top Story Today, Most Continued, Fastest Growing)
- Funnel analytics deep dive (share_click_rate, share_to_continue, K-factor dashboard)

### P2 (Platform)
- Admin dashboard WebSocket upgrade
- Style preset thumbnails
- Story Chain leaderboard gamification

### P3 (Scale)
- Mobile app wrapper
- Collaborative story creation
- Character portrait generation
- Multi-language support
