# Visionary Suite - Product Requirements Document

## Original Problem Statement
Rebuild Visionary Suite from an AI tools dashboard into an **addictive story-driven platform** with a Content Flywheel Engine. Users must enter, engage, and return organically through story continuation loops, character following, and episode progression.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI
- **Backend**: FastAPI + MongoDB + Redis
- **AI Services**: OpenAI (GPT-4o-mini, GPT Image 1, Sora 2, TTS), Gemini (via Emergent LLM Key)
- **Payments**: Cashfree
- **Auth**: JWT + Emergent-managed Google Auth
- **Storage**: Cloudflare R2

## What's Been Implemented

### Phase 1-4: Core Platform + Growth + Monetization + Trust (Pre-transformation)
- Multi-tool creator suite, authentication, gallery, character system
- Compulsion-driven growth loop, 1-click continue, A/B testing
- Cashfree payments, credit system (50 credits), credit transaction ledger
- Truth-based admin dashboard, authentic live feed

### Phase 5: Growth Engine Enhancements (March 20)
- A/B testing wired to public pages, Auto-Share Prompts, Remix Variants
- Admin WebSocket, Style Preset Thumbnails, Story Chain Leaderboard

### Phase 6: P0 TRANSFORMATION — Phase 1: Homepage + Zero Friction (March 25)
- Story-driven hero, big CTAs, trending showcase
- Zero-friction entry (no login wall before Studio)
- Credit gate with Required/You Have/Shortfall display
- Gallery: Continue This Story primary + Add Twist/Make Funny secondary

### Phase 7: P0 TRANSFORMATION — Phase 2: Viral Growth Engine (March 25)
- Results page WATCH -> CONTINUE -> LOOP -> SHARE
- Public share page conversion funnel
- Open-loop endings enforced in pipeline_engine.py
- Prefilled prompt engine, share rewards, full funnel tracking

### Phase 8: P0 TRANSFORMATION — Phase 3: Content Flywheel Engine (March 25)
- Character Universe with Follow/Remix, character feed, rankings
- Story Series Netflix Timeline with episode locks
- Notification system with 30s auto-refresh

### Phase 9: BRUTAL UX AUDIT — Action-First Redesign (March 25)
**Character Page Overhaul:**
- Action-first above-the-fold: avatar, name, hook quote, social proof counter, BIG "Continue Story" CTA
- Removed passive info sections (bio, relationships, sample scenes)
- Action row: Add Twist / Make Funny / Next Episode / Follow (with "Get notified" subtext)
- "Create your own version of [Name]" secondary CTA
- Stories grid with "Continue This Story" on every card
- Bottom CTA with urgency text

**Series Timeline Overhaul:**
- Progress bar showing completed/total episodes
- Cliffhanger preview section with urgency styling
- BIG "Continue Episode X" button in hero section
- Episode nodes: completed (green check), current (flame + CONTINUE NOW badge, glow), locked (lock icon)
- Visual emphasis on current episode (shadow, ring, glow)

**Follow System Wired to Notifications:**
- Follow creates notification for character creator ("X followed your character")
- Story completion notifies all character followers ("Character has a new story")
- NotificationBell shows "Continue story" action link on follow-type notifications
- "Why follow?" messaging via "Get notified" subtext

## Prioritized Backlog

### P0 (Critical — Phase 4: Addiction Mechanics)
- Streak system (consecutive days of engagement)
- Milestone rewards (credits at streak milestones)
- "Continue your story" reminder notifications
- Content seeding API for batch showcase generation

### P1 (High Priority)
- Social distribution hooks on every creation
- Funnel tracking analytics deep dive (K-factor, share rate)

### P2 (Medium Priority)
- Advanced A/B testing with auto-winner selection
- Enhanced analytics for share-to-conversion funnel
- Character portrait generation
- Multi-language support

### P3 (Lower Priority)
- Mobile app wrapper
- Collaborative story creation
- Advanced character relationship graph
