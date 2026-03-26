# Visionary Suite — Growth Engine PRD

## Original Problem Statement
Build a viral, addictive story-driven platform ("Growth Engine") with:
- Real Story-to-Video generation pipeline (Sora 2, GPT Image 1, OpenAI TTS)
- K-factor optimization, forced share gates, email nudges
- Content Seeding Engine for hooks and cliffhangers
- Graceful degradation when API budget is exceeded

## User Personas
- **Admin/Creator**: Manages content, monitors growth metrics, rates video quality
- **End User**: Creates stories, watches videos, continues/shares with friends

## Core Architecture
```
/app/
├── backend/
│   ├── routes/
│   │   ├── growth_analytics.py    # Share rewards (+5/+15/+25), continuation tracking, K-factor
│   │   ├── admin_metrics.py       # Truth-based admin dashboard + share reward metrics
│   │   ├── content_engine.py      # Content generation, batch, rating
│   │   ├── engagement.py          # Dashboard feeds (trending, hero, story-feed)
│   │   ├── auth.py                # Auth with standardized 50 credits
│   │   ├── share.py               # Share creation and retrieval
│   ├── services/
│   │   ├── story_engine/          # Real Sora 2 video pipeline
│   │   ├── hook_scoring_engine.py # Hybrid Rule + GPT hook evaluator
└── frontend/
    └── src/
        ├── components/
        │   ├── ForceShareGate.js   # Post-gen "Your story is live!" modal + ShareRewardBar
        ├── pages/
        │   ├── Dashboard.js        # Story-first feed with rotating hero, hype UI, scroll trap
        │   ├── StoryVideoPipeline.js # Zero-friction studio with login gate + share rewards
        │   ├── AdminDashboard.js   # Truth-based admin metrics + share reward section
```

## What's Been Implemented

### Phase 1-11: Previous Forks
- Full auth, credit system, Cashfree payments, story series, character creation
- Real Sora 2 video pipeline with Ken Burns fallback
- Hook scoring engine, content engine, dashboard transformation

### Phase 12: P0.5 "Make It Look Alive" (2026-03-26)
- Rotating Hero Carousel (6s, pause on hover, progress dots)
- Truth-Based Hype Stats (never shows zeros)
- Story Card Social Proof (Just dropped / Early story / Trending)
- First Mover Advantage, Hover Motion, Scroll Trap, Shimmer CTAs

### Phase 13: P1 Zero-Friction Entry (2026-03-26)
- Studio accessible WITHOUT login
- Login gate triggers ONLY on "Generate Video"
- ALL form state saved/restored across login redirect
- Dashboard → Studio handoff via localStorage remix_data

### Phase 14: P1 Share Reward System (2026-03-26)
- **ForceShareGate modal**: "Your story is live!" with +5/+15/+25 reward breakdown
- **4 share buttons**: WhatsApp, X (Twitter), Instagram, Copy Link
- **ShareRewardBar**: Inline share section in post-gen result page above download
- **Backend rewards**: POST /api/growth/share-reward (+5), /continuation-reward (+15), /signup-referral-reward (+25)
- **Anti-abuse**: Duplicate prevention per job per user, self-referral check
- **Admin metrics**: GET /api/admin/metrics/share-rewards with real data (shares, continuations, signups, credits given)
- **Admin dashboard**: Color-coded Share Reward Metrics section in K-Factor tab

## 3rd Party Integrations
- OpenAI GPT-4o-mini, GPT Image 1, Sora 2, TTS — Emergent LLM Key
- Resend (Email Nudges) — User API Key
- Cashfree (Payments) — User API Key
- Cloudflare R2 (Object Storage)

## Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Current Blocker
Emergent LLM key budget depleted. User needs to add balance at Profile > Universal Key > Add Balance.

## Prioritized Backlog

### P0 (After Budget Top-Up)
- Generate 10 controlled videos through scoring pipeline

### P1
- Click Psychology optimization on story cards
- Gallery/Explore page with categorized outputs

### P2
- Rebuild /share/:id pages as conversion pages with auto-play + CTA
- Auto-improve weak hooks via GPT rewriting
- A/B test hook text variations

### P3
- Self-hosted GPU migration (Wan2.1, Kokoro)
- Mobile App Wrapper
- Collaborative story creation
