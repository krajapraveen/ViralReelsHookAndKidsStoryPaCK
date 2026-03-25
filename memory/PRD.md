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
- Story-driven hero ("Stories that come alive with AI"), big CTAs
- Trending showcase with real story cards + Continue Story buttons
- Clickable story hooks, 3-step how-it-works, live feed
- Zero-friction entry (no login wall before Studio)
- Credit gate with Required/You Have/Shortfall display
- Gallery: Continue This Story primary + Add Twist/Make Funny secondary

### Phase 7: P0 TRANSFORMATION — Phase 2: Viral Growth Engine (March 25)
- **Results page → WATCH → CONTINUE → LOOP → SHARE**: Cliffhanger hook, Continue Story primary, Add Twist/Make Funny/Next Episode secondary, Share & Earn Credits (+5), Download tertiary
- **Public share page → Conversion page**: Character intro, story hook, cliffhanger above fold, all 4 CTAs, social proof
- **Open-loop endings enforced** in pipeline_engine.py
- **Prefilled prompt engine**: Continue/Twist/Funny/Episode templates
- **Share rewards**: +5 credits/share, +10 credits when someone continues your story
- **Full funnel tracking**: continue_click, add_twist_click, make_funny_click, next_episode_click

### Phase 8: P0 TRANSFORMATION — Phase 3: Content Flywheel Engine (March 25) ← CURRENT

**Character Universe (Character as Product):**
- Character page rebuilt: avatar, name, role, full description, personality traits
- **Follow Character** button with toggle (follow/unfollow)
- Stats: X stories, Y followers, Z continuations
- **Continue Character's Story** (PRIMARY CTA) with character-aware prefill
- Add Twist / Make Funny / Next Episode (SECONDARY CTAs)
- "Create your own story with [Name]" (Remix Character)
- **Character Feed**: Latest stories featuring the character
- Zero-friction access (no login wall)

**Story Series Netflix Timeline:**
- Episode timeline with visual nodes: completed (green), current (violet, pulsing), locked (gray)
- Lock system: complete previous episode to unlock next
- Cliffhanger previews on completed episodes
- "Continue Now" badge on current episode
- "Create Episode N" CTA for next episode
- Auto-prefilled prompts from series context

**Notifications System:**
- Bell icon with unread count badge
- Notification dropdown: continuation rewards, share rewards, follow updates, trending
- Mark all as read
- Auto-refresh every 30 seconds
- Notifications created when someone continues your story (+10 credits)

**Rankings System:**
- GET /api/universe/rankings — public
- Top Stories (by views, 10 items)
- Top Characters (by story count + followers, scored)
- Top Creators (by total views + stories)

## Prioritized Backlog

### P1 (High Priority — Phase 4)
- Streak system + episode milestones + engagement rewards
- "Continue your story" reminder/push notifications
- Content seeding API for batch showcase generation
- Social distribution hooks on every creation

### P2 (Medium Priority)
- Advanced A/B testing with auto-winner selection
- Enhanced analytics for share-to-conversion funnel
- Character portrait generation
- Multi-language support

### P3 (Lower Priority)
- Mobile app wrapper
- Collaborative story creation
- Advanced character relationship graph
