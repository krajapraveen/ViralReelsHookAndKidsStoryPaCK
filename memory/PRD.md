# Visionary Suite - Product Requirements Document

## Original Problem Statement
Rebuild Visionary Suite into an **addictive story-driven viral platform** with compulsion loops: enter → engage → return → share → grow. Achieve K-factor > 0.5 through referral tracking, share incentivization, and session chaining.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI
- **Backend**: FastAPI + MongoDB + Redis
- **AI**: OpenAI (GPT-4o-mini, GPT Image 1, Sora 2, TTS), Gemini (Emergent LLM Key)
- **Payments**: Cashfree | **Auth**: JWT + Google Auth | **Storage**: Cloudflare R2 | **Email**: Resend (ACTIVE)

## Implemented Phases

### Phase 1-2: Entry + Viral Loop
Homepage, zero-friction entry, credit gating, results page WATCH→CONTINUE→SHARE, open-loop endings

### Phase 3-3.5: Flywheel + Behavioral Momentum
Character Universe, Story Series, Notifications, Rankings, action-first UX, entry story auto-selection, delayed urgency, auto-scroll, follow feed, auto-next popup

### Phase 4-4.5: Retention Engine
Nudge system (hourly, 6h inactivity), return banner + forced decision modal (3s), streaks (Day 3:+10, Day 7:+25), episode milestones (5 eps:+5), reward celebration, emotional messaging, email nudges (queued)

### Phase 5: K-Factor Engine
Share page rebuilt as conversion machine, WhatsApp/X/IG/Copy share UX, upgraded rewards (+5/+15/+25), K-factor tracking API

### Phase 5.5: Attribution + Distribution
- Referral Tracking: Share page stores referral_source in localStorage → Signup/Google Auth attributes referral → +25 credits to referrer
- Email Service: Resend integration with HTML template (character name, cliffhanger, Continue Now CTA)
- Direct Entry Flow: Share → Continue → Studio with prefilled prompt, no detours
- Guard Rails: Self-referral prevention, duplicate prevention, 24-hour attribution window

### Phase 6: Compete + Social Proof + K-Factor Dashboard (2026-03-25)
- Email Nudges ACTIVATED: Resend API key injected, test endpoint verified, scheduler active
- Compete Mechanics: GET /api/compete/trending — Top Story Today, Most Continued Story, Fastest Growing Character, Rising Stories (all truth-based)
- Animated Social Proof: Real-time viewer counts with pulse animation on Dashboard and PublicCreation pages
- Force Share Gate: After video generation, users see Share OR Continue modal to maximize K-factor
- K-Factor Admin Dashboard: New tab showing viral coefficient, funnel, top performing content, email nudge status
- Live Viewers API: GET /api/compete/live-viewers — real session-based counts, no synthetic data

### Phase 7: Content Seeding Engine (2026-03-25 — LATEST)
- AI-powered story hook generation using GPT-4o-mini with strict HOOK → BUILD → CLIFFHANGER format
- Quality filtering: Heuristic scoring (hooks, cliffhangers, word count), auto-reject below threshold
- 5 categories: Emotional, Mystery, Kids, Horror, Viral — each with themed prompts and style pairing
- Social media script generation: Reel scripts, Instagram/TikTok captions, hashtags for every story
- Auto-publish pipeline: Drafts → publish to pipeline_jobs for video generation
- Admin Control Panel: Generate batch (10/25/50), filter by category/status/tag, feature, tag quality, delete weak content, copy scripts
- Admin-accessible at /app/admin/content-engine

## Self-Hosted Stack
Architecture spec at `/app/memory/SELF_HOSTED_STACK.md`

## Prioritized Backlog

### P1 (Growth Optimization)
- A/B test hook text variations on public pages
- Character-driven auto-share prompts after creation

### P2 (Platform)
- Remix Variants on share pages
- Admin dashboard WebSocket upgrade
- Story Chain leaderboard gamification
- UI polish and style preset thumbnails

### P3 (Scale)
- Mobile app wrapper
- Collaborative stories
- Multi-language support

## Key Files
- `/app/backend/routes/content_engine.py` — Content Engine backend (AI generation, quality filter, publish)
- `/app/frontend/src/pages/ContentEngine.js` — Admin control panel
- `/app/backend/routes/compete_routes.py` — Trending + Live Viewers endpoints
- `/app/backend/routes/retention_routes.py` — Email nudges + test endpoint
- `/app/backend/services/email_service.py` — Resend integration
- `/app/frontend/src/components/TrendingCompete.js` — Compete UI
- `/app/frontend/src/components/AnimatedSocialProof.js` — Animated viewer counts
- `/app/frontend/src/components/ForceShareGate.js` — Forced share modal
- `/app/frontend/src/pages/AdminDashboard.js` — K-Factor section + Content Engine nav link
