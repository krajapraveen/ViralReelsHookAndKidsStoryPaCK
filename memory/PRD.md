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

### Phase 1: Core Platform
- Multi-tool creator suite (Story Video Studio, Comic, GIF, Reels, Bedtime Stories, Coloring Book)
- User authentication (JWT + Google OAuth)
- Gallery and Explore pages
- Character system with memory

### Phase 2: Growth Engine (Compulsion Loop)
- Redesigned public pages with momentum-based social proof
- 1-click continue flow (generate before login)
- Enforced open-loop story endings
- A/B testing infrastructure (4 experiments: cta_copy, hook_text, login_timing, cta_placement)

### Phase 3: Monetization
- Cashfree payment integration
- Credit system (50 credits for new users)
- Strict credit checks on all generation tools
- Credit transaction ledger

### Phase 4: Trust & Integrity Fixes
- Fixed broken Security tab in Profile
- Truth-based admin satisfaction metric
- Authentic "Live on the Platform" feed with diverse locations
- Credit system consistency

### Phase 5: Growth Engine Enhancements (March 20, 2026)
- A/B Test Hook Text Variations on public pages
- Character-Driven Auto-Share Prompts (SharePromptModal)
- Remix Variants on share pages (Comic, GIF, Reel, Bedtime Story)
- Admin Dashboard WebSocket Live Updates
- Style Preset Preview Thumbnails
- Story Chain Leaderboard (admin dashboard)
- Admin A/B Test Results Dashboard

### Phase 6: P0 PRODUCT TRANSFORMATION (March 25, 2026) ← CURRENT
**Homepage Rebuild:**
- Story-driven hero: "Stories that come alive with AI"
- Two BIG CTAs: "Continue a Story" + "Create Your Version"
- "Trending Now" showcase with 10 real story cards + Continue Story buttons
- "Pick a story. Make it yours" with 6 clickable story hooks that prefill studio
- "Story to video in 3 clicks" how-it-works section
- "Happening now" live feed
- "Your story is waiting" final CTA
- NO "AI tools dashboard" language

**Zero-Friction Entry:**
- Studio accessible without login — no login wall before experience
- Login only required when clicking Generate
- Smart "Log in to generate" messaging with prompt preservation
- Redirect back to studio after login

**Continue Story Flow (End-to-End):**
- Homepage → Click Continue Story → Studio with prefilled prompt + title + context
- Gallery → Click Continue This Story → Studio with prefilled prompt
- Hook cards → Click → Studio with hook text prefilled
- localStorage-based data passing (remix_data + onboarding_prompt)

**Credit Gate:**
- Pre-generate credit check showing Required / You Have / Shortfall
- Clear "Buy X More Credits" CTA when insufficient
- 402 error parsing with exact shortfall display

**Gallery Transformation:**
- "Continue This Story" as PRIMARY action on every card
- "Add Twist" and "Make Funny" secondary actions
- Story hook text shown as quotes beneath titles
- Backend filters to ONLY show items with real thumbnails (no empty states)
- Bottom CTA: "Continue any story above — or create your own"

**Style Preset Preview Thumbnails:**
- Gradient-based visual previews for each animation style in Studio

## Prioritized Backlog

### P0 (Critical — Immediate)
- [DONE] Homepage WOW rebuild
- [DONE] Zero-friction entry
- [DONE] Continue Story flow end-to-end
- [DONE] Credit gate with shortfall messaging
- [DONE] Gallery with real content + Continue Story

### P1 (High Priority — Phase 2 of Transformation)
- Continue Story buttons on results page (PostGenPhase)
- Public share page rebuild (/v/{slug}) — character intro + cliffhanger + conversion CTAs
- Open-loop endings enforcement in story planning prompts
- Prefilled prompt templates for faster creation

### P2 (Medium Priority — Phase 3)
- "Build Your Character Universe" feature visibility
- Story Series Netflix-like episode timeline UI
- "Meet [Character Name]" pages with "Used in X stories"

### P3 (Lower Priority — Phase 4)
- Streak system + episode milestones
- Credit rewards for engagement
- "Continue your story" reminder system
- Full viral loop funnel tracking (page_view → continue_click → generate_click → signup → completion → share)
- Content seeding API for batch generation
- Social distribution hooks ("Continue this story → visionary-suite.com")

### P4 (Backlog)
- General UI polish
- Multi-language support
- Mobile app wrapper
- Collaborative story creation
