# Visionary Suite - Product Requirements Document

## Original Problem Statement
Build a "Growth Engine" for an AI Creator Suite. Users are not entering, not engaging, and not returning. This is a product experience + growth loop failure, not a feature problem. The platform must be rebuilt as an **addictive story-driven platform**, not a tools dashboard.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI
- **Backend**: FastAPI + MongoDB + Redis
- **AI Services**: OpenAI (GPT-4o-mini, GPT Image 1, Sora 2, TTS), Gemini (via Emergent LLM Key)
- **Payments**: Cashfree
- **Auth**: JWT + Emergent-managed Google Auth
- **Storage**: Cloudflare R2 (Object Storage)

## What's Been Implemented

### Phase 1-4: Core Platform + Growth + Monetization + Trust
- Multi-tool creator suite, authentication, gallery, character system
- Compulsion-driven growth loop with 1-click continue flow
- Cashfree payments, credit system (50 credits for new users)
- Truth-based admin dashboard, authentic live feed

### Phase 5: Growth Engine Enhancements (March 20, 2026)
- A/B Test Hook Text Variations, Auto-Share Prompts, Remix Variants
- Admin WebSocket Live Updates, Style Preset Thumbnails
- Story Chain Leaderboard, A/B Test Results Dashboard

### Phase 6: P0 PRODUCT TRANSFORMATION — Phase 1 (March 25, 2026)
- **Homepage Rebuild**: Story-driven hero, "Continue a Story" + "Create Your Version" big CTAs, trending showcase, clickable story hooks, how-it-works, live feed
- **Zero-Friction Entry**: Studio accessible without login, login only at Generate
- **Continue Story Flow E2E**: Homepage → Continue → Studio with prefilled prompt
- **Credit Gate**: Shows Required/You Have/Shortfall with Buy Credits CTA
- **Gallery Transformation**: Continue This Story primary, Add Twist/Make Funny secondary
- **Style Preset Thumbnails**: Gradient preview cards

### Phase 7: P0 PRODUCT TRANSFORMATION — Phase 2: VIRAL GROWTH ENGINE (March 25, 2026) ← CURRENT

**Results Page (PostGenPhase) Transformation — WATCH → CONTINUE → LOOP → SHARE:**
- Cliffhanger hook above actions: "WHERE THE STORY LEFT OFF..." + "But something unexpected happens next..."
- PRIMARY action: "Continue Story" (biggest button, first position) — prefills Studio with continuation context + higher stakes direction
- SECONDARY actions: "Add Twist" (unexpected reveal), "Make Funny" (comedy override), "Next Episode" (Episode 2 context)
- "Share & Earn Credits" section: +5 credits per share (WhatsApp, X/Twitter, Copy Link)
- Download button demoted to TERTIARY
- Advanced continuation options with custom direction input
- Remix with Different Style grid

**Public Share Page (/v/{slug}) — Full Conversion Page:**
- Character intro (if available): "Meet [Name]"
- Story title + views + continuations social proof
- Scene viewer with thumbnail navigation
- Cliffhanger hook: "WHERE THE STORY LEFT OFF..." + "But something unexpected happens next..."
- PRIMARY CTA: "Continue This Story" — no login needed
- SECONDARY CTAs: "Add Twist" / "Make Funny" / "Next Episode"
- "Create Your Version" CTA
- Momentum section: "X people continued this story" + style/scenes/date/creator
- Share buttons (X, WA, In, Link)
- Remix variants (Comic Book, GIF, Reel, Bedtime)

**Prefilled Prompt Engine:**
- Continue: Original story + "Continue with higher stakes and tension"
- Twist: "Introduce an unexpected betrayal, reveal, or surprise"
- Funny: "Convert into hilariously funny version with comedic timing"
- Next Episode: "Create Episode 2 continuing from the ending"
- All prefills include title, story context, and direction instruction

**Open-Loop Endings Enforcement:**
- Added CRITICAL RULE FOR OPEN-LOOP ENDINGS to pipeline_engine.py story planning prompt
- Every story must end with unresolved conflict, curiosity gap, or cliffhanger
- Example endings provided: "But as the door closed... something moved in the shadows"
- NEVER end with happy resolution or "happily ever after"

**Share Rewards System:**
- POST /api/growth/share-reward: +5 credits per share (once per job per user)
- POST /api/growth/continuation-reward: +10 credits to original creator when someone continues their story
- Deduplication prevents double rewards

**Funnel Tracking:**
- New events: continue_click, add_twist_click, make_funny_click, next_episode_click
- Full funnel: page_view → continue_click → generate_click → signup → completion → share_click
- Viral coefficient (K) calculation at /api/growth/viral-coefficient

## Prioritized Backlog

### P1 (High Priority — Phase 3)
- "Build Your Character Universe" feature visibility
- Story Series Netflix-like episode timeline UI
- "Meet [Character Name]" pages with "Used in X stories"

### P2 (Medium Priority — Phase 4)
- Streak system + episode milestones + credit rewards for engagement
- "Continue your story" reminder/push system
- Content seeding API for batch generation of showcase content
- Social distribution hooks ("Continue this story → visionary-suite.com")

### P3 (Lower Priority)
- General UI polish across all tools
- Multi-language support
- Mobile app wrapper
- Collaborative story creation
