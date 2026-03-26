# Visionary Suite — Growth Engine PRD

## Original Problem Statement
Build a viral, addictive story-driven platform ("Growth Engine") with real Story-to-Video generation (Sora 2, GPT Image 1, TTS), K-factor optimization, and content-driven growth loops.

## Core Architecture
```
/app/
├── backend/routes/
│   ├── engagement.py          # Dashboard feeds, explore, card-click A/B tracking
│   ├── growth_analytics.py    # Share rewards (+5/+15/+25), K-factor
│   ├── admin_metrics.py       # Truth-based admin dashboard + share metrics
│   ├── content_engine.py      # Batch generation, scoring
│   ├── auth.py                # Auth with 50 credits
├── backend/services/
│   ├── story_engine/          # Sora 2 pipeline with Ken Burns fallback
│   ├── hook_scoring_engine.py # Hybrid Rule + GPT evaluator
├── frontend/src/pages/
│   ├── Dashboard.js           # Story-first feed with click-psychology cards
│   ├── ExplorePage.js         # Gallery with categories, infinite scroll, stickiness
│   ├── StoryVideoPipeline.js  # Zero-friction studio with login gate
│   ├── AdminDashboard.js      # Truth-based metrics + share rewards
├── frontend/src/components/
│   ├── ForceShareGate.js      # "Your story is live!" modal + ShareRewardBar
```

## What's Been Implemented (Current Session — 2026-03-26)

### Phase 12: P0.5 "Make It Look Alive"
- Rotating Hero Carousel (6s, pause on hover, progress dots)
- Truth-Based Hype Stats (never shows zeros)
- Story Card Social Proof (Just dropped / Early story / Trending)
- First Mover Advantage, Hover Motion, Scroll Trap, Shimmer CTAs

### Phase 13: P1 Zero-Friction Entry
- Studio accessible WITHOUT login, login gate on "Generate" only
- ALL form state saved/restored across login redirect

### Phase 14: P1 Share Reward System
- ForceShareGate: "Your story is live!" with +5/+15/+25 rewards
- 4 share buttons (WhatsApp, X, Instagram, Copy Link)
- ShareRewardBar in post-gen result, admin share metrics

### Phase 15: P1 Click Psychology Optimization
- Cinematic 4:5 cards with hook overlay, CTA variants, urgency text
- A/B click tracking with variant analytics

### Phase 16: P1 Gallery / Explore Page
- **Route**: /app/explore (also /explore for public access)
- **Category filters**: All (30), Emotional (8), Mystery (2), Kids (30), Viral Hooks (15)
- **Sort options**: Trending, New, Most Continued
- **Infinite scroll**: IntersectionObserver loads 12 per batch, cursor-based pagination
- **Stickiness triggers**: "This story has no ending yet..." between rows with pulsing dots
- **Card design**: Same click-psychology cards as Dashboard (cinematic 4:5, hook overlay, CTA variants, urgency)
- **Empty state**: "Be the first to create a story in this category" with CTA
- **End-of-list**: "You've explored all stories" with create CTA
- **Lazy loading**: All images use loading="lazy"
- **Backend**: GET /api/engagement/explore with category, sort, cursor params
- **Dashboard link**: "View All" in Trending Stories navigates to /app/explore

## 3rd Party Integrations
- OpenAI GPT-4o-mini, GPT Image 1, Sora 2, TTS — Emergent LLM Key
- Resend, Cashfree, Cloudflare R2

## Credentials
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Blocker
Emergent LLM key budget depleted. Add balance at Profile > Universal Key.

## Prioritized Backlog

### P1
- Rebuild /share/:id as conversion pages (auto-play, hook text, CTA)
- Generate 10 videos after budget top-up

### P2
- Auto-improve weak hooks via GPT rewriting
- A/B test hook text variations on public pages

### P3
- Self-hosted GPU migration (Wan2.1, Kokoro)
- Mobile App Wrapper
