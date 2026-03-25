# Visionary Suite - Product Requirements Document

## Original Problem Statement
Rebuild Visionary Suite into an **addictive story-driven viral platform** with compulsion loops: enter → engage → return → share → grow.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI
- **Backend**: FastAPI + MongoDB + Redis
- **AI**: OpenAI (GPT-4o-mini, GPT Image 1, Sora 2, TTS), Gemini (Emergent LLM Key)
- **Payments**: Cashfree | **Auth**: JWT + Google Auth | **Storage**: Cloudflare R2 | **Email**: Resend (pending key)

## Implemented Phases

### Phase 1-2: Entry + Viral Loop
Homepage, zero-friction entry, credit gating, results page WATCH→CONTINUE→SHARE, open-loop endings

### Phase 3-3.5: Flywheel + Behavioral Momentum
Character Universe, Story Series, Notifications, Rankings, action-first UX, entry story auto-selection, delayed urgency, auto-scroll, follow feed, auto-next popup

### Phase 4-4.5: Retention Engine
Nudge system (hourly, 6h inactivity), return banner + forced decision modal (3s), streaks (Day 3:+10, Day 7:+25), episode milestones (5 eps:+5), reward celebration, emotional messaging, email nudges (queued)

### Phase 5: K-Factor Engine
Share page rebuilt as conversion machine, WhatsApp/X/IG/Copy share UX, upgraded rewards (+5/+15/+25), K-factor tracking API

### Phase 5.5: Attribution + Distribution (LATEST)
- **Referral Tracking**: Share page stores `referral_source` in localStorage → Signup/Google Auth attributes referral → +25 credits to referrer
- **Email Service**: Resend integration with HTML template (character name, cliffhanger, Continue Now CTA). Ready to send — needs RESEND_API_KEY
- **Direct Entry Flow**: Share → Continue → Studio with prefilled prompt, no detours
- **Guard Rails**: Self-referral prevention, duplicate prevention, 24-hour attribution window

## Self-Hosted Stack
Architecture spec at `/app/memory/SELF_HOSTED_STACK.md`

## Prioritized Backlog

### P0 (Activate)
- Add RESEND_API_KEY to backend/.env to activate email nudges

### P1 (Growth Optimization)
- Compete mechanic (Top Story Today, Most Continued, Fastest Growing Character)
- Animated social proof counters ("X people viewing now")
- K-factor dashboard for admin
- A/B test hook text variations

### P2 (Platform)
- Admin dashboard WebSocket upgrade
- Story Chain leaderboard gamification

### P3 (Scale)
- Mobile app wrapper, collaborative stories, multi-language
