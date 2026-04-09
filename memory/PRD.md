# Visionary Suite - Product Requirements Document

## Original Problem Statement
Build an AI Creator Suite with a compulsion-driven "Growth Engine" — a full-stack application featuring AI video generation, social sharing loops, and monetization via credits and payments. The platform must create irresistible user journeys with a multi-day retention engine that pulls creators back through notifications, email, challenges, and social proof.

## Architecture
- **Frontend**: React (CRA) + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB + Redis
- **Integrations**: OpenAI (GPT-4o-mini, GPT Image 1, Sora 2, TTS), Gemini, Cloudflare R2, Cashfree, Google Auth, Resend (email)
- **Key URL**: https://trust-engine-5.preview.emergentagent.com

## Credentials
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

---

## What's Been Implemented

### Core Platform — DONE
- P0 Growth Loop, P1 Monetization, MySpace UX, Pipeline Resilience, Remix Gallery, Addiction Layer, Trust Fixes

### P0 Failed Job Recovery — DONE (Apr 9)
- Server-authoritative view_mode routing, FailedRecoveryScreen, deep-link support
- Testing: 17/18 (iteration_470)

### Retention Layer — Release 1 — DONE (Apr 9)
- In-App Notifications (bell, throttled, aggregated), Ownership Messaging, Daily Challenges, Soft Leaderboard, Mock Email
- Testing: 25/25 (iteration_471)

### Retention Layer — Release 2 — DONE (Apr 9)
- Real Resend email, auto-play hover preview, challenge participation tracking, challenge leaderboard, challenge badges
- Testing: 24/24 (iteration_472)

### Creator Digest — DONE (Apr 9)
- **Weekly digest** computing per-user stats: total views, new remixes, top story highlight, momentum signal, percentile comparison, Rising Fast badge
- **Smart skip**: No digest for zero-activity users or guest accounts
- **Personalized CTA**: Dynamic based on user's top metric (remixes → "See who remixed", views → "See why trending")
- **Per-user weekly cap**: Max 1 digest/week
- **Admin controls**: Preview digest for any user, send to specific user, run-all weekly digest
- **Email template**: Clean dark theme, 20-second read, stats + top story + momentum + CTA
- **User lookup fix**: Searches by `id` field (matching users collection schema)
- Testing: 14/14 (iteration_473)

### Prestige + Quality Loop — DONE (Apr 9)
- **Homepage Featured Challenge Winner Hero Slot**: Prestigious design with trophy badge, winner reason badge, large thumbnail, gradient glow. Remix This Winner (primary) + View Winning Story (secondary) CTAs. Analytics: `hero_winner_impression`, `hero_winner_view_clicked`, `hero_winner_remix_clicked`. Graceful fallback when no winner: "Today's challenge winner will appear soon".
- **Improve Consistency CTA**: Premium enhancement button on story_engine completed cards. Shows only on eligible jobs (source=story_engine, consistency_retry_count < 1). Max 1 retry per job enforced. Success: "Your characters now appear more consistent across scenes". Analytics: `improve_consistency_clicked`, `improve_consistency_success`, `improve_consistency_failed`. Auto-hides after use or for ineligible jobs.
- Testing: 14/14 (iteration_474)

### A/B Hero Headline Optimization — DONE (Apr 9)
- **Experiment: hero_headline (Week 1)** — A vs B only, Variant C deferred until first winner emerges
  - **Variant A (Control)**: "Create stories kids will remember forever" (emotional)
  - **Variant B (Challenger)**: "Create award-worthy AI stories in minutes" (prestige)
- **Sticky assignment**: Deterministic MD5 hash of session_id + experiment_id. Same user always sees same variant.
- **Traffic source tracking**: Auto-detected from referrer (instagram, organic, direct, referral, internal)
- **Minimum threshold**: 500 sessions per variant AND 95% statistical confidence (z-test) required before winner declared
- **Analytics events**: `ab_variant_assigned`, `impression`, `experience_click` (primary), `paywall_shown` (secondary)
- **Admin dashboard**: Clean table showing Variant, Impressions, Clicks, CTR%, Paywall%, Confidence%, Winner badge
- **Only headline text changes** — layout, fonts, CTA, colors are identical between variants
- Testing: 17/17 (iteration_475)

### Traffic Source Segmentation + Auto-Share Prompts — DONE (Apr 9)
- **Traffic Source Segmentation Dashboard**: Per-source breakdown of A/B test performance. Shows Source, Variant, Impressions, CTR%, Confidence%, Winner. Sources sorted by traffic volume (highest first). "Insufficient data" label for sources with <100 impressions per variant. Confidence calculated per-source via z-test.
- **Character-Driven Auto-Share Prompts**: Contextual share modal that adapts messaging based on story status:
  - Challenge Winner: "Share your winning challenge story!" (trophy icon)
  - Trending: "Your story is gaining momentum — share it now!" (trending icon)
  - Highly Remixed: "People love this story — invite more viewers!" (heart icon)
  - Standard: "Share your new AI story with friends" (sparkles icon)
- **CTA priority**: Copy Share Link (primary) > Share to Instagram (secondary) > Share as Reel (third) > WhatsApp / Twitter
- **Cooldown**: Once per completed project only (sessionStorage). Shows 3s after ForceShareGate dismissal. Never before preview.
- **Analytics**: `share_prompt_shown`, `share_link_copied`, `share_instagram_clicked`, `share_reel_clicked`, `share_completed`, `share_dismissed`
- Testing: 16/16 (iteration_476)

---

## Email System Status
- **Provider**: Resend (wired, API key configured)
- **Status**: Infrastructure complete. Domain verification needed for non-owner delivery.
- **Templates**: story_remixed, story_trending, daily_challenge_live, ownership_milestone, creator_digest
- **Safety**: Per-user caps, cooldowns, weekly digest cap, unsubscribe metadata
- **Admin**: Preview at GET /api/retention/email-events

---

## Prioritized Backlog

### P0 — Immediate
- Verify Resend domain for live email delivery (user action)

### Viral Flywheel Engine v1 — Phase A (Foundation) — DONE (Apr 9)
- **Viral Attribution Tracking**: New `viral_referrals` collection tracks share_source_user → click_session_id → attribution_depth → conversion. Supports multi-level chains.
- **Share Landing Pages Enhanced**: Creator attribution badge, "Inspired by" lineage badge on `/v/{slug}` pages. Viral click tracked on page load. OG meta tags enhanced with remix count.
- **Smart Headline Router**: `GET /api/ab/smart-route` auto-serves winning A/B variant per traffic source. Falls back to control (`headline_a`) when confidence < 95% or data insufficient. Safety-first design.
- **Remix Lineage System**: `POST /api/viral/lineage` records parent→child relationships. `GET /api/viral/lineage/{job_id}` returns "Inspired by" data for visible attribution.
- **Creator Rewards**: +1 credit per 5 remix conversions, max 5 bonus credits/day. `GET /api/viral/rewards/status` for current status.
- **Viral Leaderboard**: Weighted scoring (remixes * 0.5 + chain_depth * 0.3 + signups * 0.2). Dashboard section shows top 5 viral creators.
- **Viral Metrics**: Core metrics endpoint: share→click CTR, click→remix conversion, avg attribution depth, viral coefficient estimate.
- **Personalized Dashboard Hero**: 3 segments (challenge-heavy, remix-heavy, default). Viral attribution badge showing total remix conversions + bonus credits earned.
- **MySpace Viral Badge**: "Your stories generated X viral remixes this week" with bonus credit count.
- **Grouped Creator Notifications**: When someone remixes a shared story, creator gets grouped daily notification (not spammy individual alerts).
- Testing: 23/23 backend + all frontend passed (iteration_477)

### P1 — Next Features
- Viral Flywheel Engine v1 — Phase B: Creator Loop (referral chain visibility, personalized share copy)
- Viral Flywheel Engine v1 — Phase C: Gamification (leaderboard polish, reward loop activation, OG card optimization)
- A/B Week 2: Winner of A vs B → test against Variant C ("Join thousands creating viral AI stories")
- A/B Week 3: Lock winning headline, begin CTA button A/B testing

### P2 — Growth & Polish
- Monthly creator milestone digest
- "Remix Variants" on share pages
- Admin WebSocket upgrade
- Story Chain leaderboard

---

## Key Files
- `/app/backend/services/retention_service.py` — Full retention service (email, notifications, challenges, digest)
- `/app/backend/routes/retention_hooks.py` — Retention API routes (challenges, digest, email preview)
- `/app/backend/routes/story_engine_routes.py` — Job APIs + view_mode + remix triggers
- `/app/frontend/src/components/NotificationBell.js` — Bell with retention types
- `/app/frontend/src/components/RemixGallery.js` — Gallery with auto-play hover preview
- `/app/frontend/src/components/GlobalUserBar.jsx` — Top nav with bell
- `/app/frontend/src/pages/StoryVideoPipeline.js` — Studio + recovery + challenge
- `/app/frontend/src/pages/MySpacePage.js` — Dashboard + ownership + challenge badges + Improve Consistency CTA
- `/app/frontend/src/pages/Dashboard.js` — Challenge banner + Top Stories leaderboard + Featured Winner Hero Slot
