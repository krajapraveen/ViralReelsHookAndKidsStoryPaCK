# Visionary Suite — Growth Engine PRD

## Original Problem Statement
Build a viral, addictive story-driven platform ("Growth Engine") with:
- Real Story-to-Video generation pipeline (Sora 2, GPT Image 1, OpenAI TTS)
- K-factor optimization, forced share gates, email nudges
- Content Seeding Engine for hooks and cliffhangers
- Graceful degradation when API budget is exceeded

## Core Architecture
```
/app/
├── backend/
│   ├── routes/
│   │   ├── growth_analytics.py    # Share rewards (+5/+15/+25), K-factor
│   │   ├── engagement.py          # Dashboard feeds, card-click A/B tracking
│   │   ├── admin_metrics.py       # Truth-based admin dashboard + share reward metrics
│   │   ├── content_engine.py      # Batch generation, scoring
│   │   ├── auth.py                # Auth with 50 credits
│   ├── services/
│   │   ├── story_engine/          # Sora 2 pipeline with Ken Burns fallback
│   │   ├── hook_scoring_engine.py # Hybrid Rule + GPT evaluator
└── frontend/
    └── src/
        ├── components/
        │   ├── ForceShareGate.js   # "Your story is live!" modal + ShareRewardBar
        ├── pages/
        │   ├── Dashboard.js        # Story-first feed with click-psychology cards
        │   ├── StoryVideoPipeline.js # Zero-friction studio with login gate
        │   ├── AdminDashboard.js   # Truth-based metrics + share rewards
```

## What's Been Implemented

### Phase 12: P0.5 "Make It Look Alive" (2026-03-26)
- Rotating Hero Carousel, Truth-Based Hype Stats, Story Card Social Proof
- First Mover Advantage, Hover Motion, Scroll Trap, Shimmer CTAs

### Phase 13: P1 Zero-Friction Entry (2026-03-26)
- Studio accessible WITHOUT login, login gate on "Generate" only
- ALL form state saved/restored, Dashboard → Studio handoff via localStorage

### Phase 14: P1 Share Reward System (2026-03-26)
- ForceShareGate modal: "Your story is live!" with +5/+15/+25 rewards
- ShareRewardBar in post-gen result, admin share metrics dashboard

### Phase 15: P1 Click Psychology Optimization (2026-03-26)
- **Cinematic 4:5 aspect ratio cards** — taller, more immersive than old 16:9
- **Hook text overlaid on darkened thumbnail** — biggest element, bold white, 1-line
- **Hook formatting** — Truncated to 65 chars with ellipsis for incomplete thought effect
- **CTA variant rotation** — A/B testing 3 variants: "See What Happens Next", "Continue This Story", "What Happens Next?"
- **Truth-based urgency layer** — "Someone just continued this", "Your turn to continue", "This story isn't finished"
- **Micro-animations** — Card lift (-4px) on hover, CTA transforms to amber, thumbnail scale+brightness
- **A/B click tracking** — Every card click tracked with variant to /api/engagement/card-click
- **Card analytics** — GET /api/engagement/card-analytics returns variant breakdown with percentages
- **No clutter** — Only hook, urgency, CTA. No extra metadata or secondary buttons

## 3rd Party Integrations
- OpenAI GPT-4o-mini, GPT Image 1, Sora 2, TTS — Emergent LLM Key
- Resend (Email Nudges) — User API Key
- Cashfree (Payments) — User API Key
- Cloudflare R2 (Object Storage)

## Credentials
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Blocker
Emergent LLM key budget depleted. Add balance at Profile > Universal Key > Add Balance.

## Prioritized Backlog

### P0 (After Budget)
- Generate 10 controlled videos, rate hook quality

### P1
- Gallery/Explore page with categorized outputs
- Rebuild /share/:id as conversion pages

### P2
- Auto-improve weak hooks via GPT rewriting
- A/B test hook text variations on public pages

### P3
- Self-hosted GPU migration (Wan2.1, Kokoro)
- Mobile App Wrapper
