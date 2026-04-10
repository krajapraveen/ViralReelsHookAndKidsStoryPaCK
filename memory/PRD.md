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

### Viral Flywheel Engine v1 — Phase B (Creator Emotional Loop) — DONE (Apr 9)
- **Viral Chain Timeline UI**: Shows user's top viral story with momentum signals ("+X new remixes today" pulsing badge, "X this week"). Displays chain stats: remixes inspired, new creators, creator levels. Celebratory language, not technical. Only shows top story to avoid clutter.
- **Emotional Creator Notifications**: Momentum-driven copy adapts by volume ("Your story inspired 3 creators this week — you're gaining momentum", "you're on fire!"). Grouped by day to avoid spam. Includes link to MySpace.
- **Personalized Share Prompt Copy**: Uses real viral stats when available ("Your stories generated 12 remixes — share this one to grow faster"), falls back to "Stories shared early generate more remixes" for new users.
- **"Share Again" CTA**: Appears on stories with existing viral traction to encourage repeat sharing for amplification.
- **Viral Milestone Badges**: First Viral Remix, Inspired 5/10 Creators, Spread Across 3/5 Levels, 25 Viral Remixes. Auto-earned from live stats. Upcoming milestone shown with remaining count.
- **End-to-end chain verified**: Simulated lineage chain → chain stats → milestones → all rendering correctly.
- Testing: Backend 6/6 endpoints verified via curl, Frontend verified via Playwright screenshots

### Viral Readiness Dashboard — DONE (Apr 9)
- **Phase C Go/No-Go Report**: Data-driven readiness check measuring 5 behavioral thresholds: Repeat Share Rate (20%), Chain Depth >=2 (15%), Creator Return-to-Inspect (30%), Click-to-Remix Conversion (8%), Milestone Badge Engagement (20%).
- **Verdict**: GREENLIGHT requires 4/5 thresholds passing. Current verdict: NOT_READY (1/4 passing — only milestone engagement passes).
- **Admin Dashboard**: "Viral Readiness" tab with verdic header, Go/No-Go metrics table (Metric, Current, Threshold, Status), sample sizes.
- **Recommendation**: Phase C deferred until data matures. Focus on optimizing viral loop (share prompts, landing page, notification strength).
- Testing: Backend verified via curl, Frontend verified via Playwright screenshot

### Viral Flywheel Engine v1 — Phase C: Dark Launch Infrastructure — DONE (Apr 9)
- **Leaderboard Engine**: Computes competitive rankings using weighted viral score (remixes * 0.5 + depth * 0.3 + signups * 0.2 + streak_bonus * 0.1). Assigns rank tiers (Bronze → Silver → Gold → Diamond). Daily rank snapshots stored for "You climbed X places this week" momentum.
- **Reward Calculation Engine**: Silently accumulates pending rewards (rank-tier credits + streak-tier credits). All rewards include `earned_at` and `expires_at` (7 days post-activation). Pre-builds competition notification drafts.
- **Streak Tracking Engine**: Enhanced 60-day streak lookback with tiers (3/7/14/30 day), freeze tokens (1 per 7 streak days), auto-freeze on missed days, best streak tracking.
- **Achievement Framework**: 11 achievement badges across 3 categories (rank, streak, reward). All stored as `status: "hidden"` until Phase C activation.
- **Feature Flag**: `GET /api/phase-c/status` — requires BOTH 4/5 readiness thresholds AND 1000+ viral referral events for activation. Currently: NOT_READY.
- **Admin Dark Launch Monitor**: Aggregate-first dashboard (total ranked, pending rewards, active streaks, achievements, freeze tokens). Phase C Simulated Engagement Score. Optional drill-down per category.
- **Security**: All admin/engine endpoints protected by `get_admin_user`. No Phase C data leaks to public endpoints.
- **Hidden Analytics**: Events tracked: `hidden_rank_progress`, `hidden_reward_pending`, `hidden_streak_days`, `phase_c_activation_ready`.
- Testing: 22/22 backend + all frontend passed (iteration_478)

### P0 Dashboard Hero Story-Context Bug Fix — DONE (Apr 10)
**Root cause:** Dashboard.js HeroSection "Continue Story" navigated to `/experience` (a fresh story generation page with hardcoded DEMO_STORIES), not the actual project. "Remix" sent zero story context.
**Fix:** Continue Story → `/app/story-video-studio?projectId={job_id}`. Remix → studio with `remixFrom: {title, job_id}`. Seed cards → fresh session.
**Verification:** 3-story integrity test (Painter of Stars, Crystal Cave, Whispering Woods) — all buttons use correct story context. Deep-link refresh persistence confirmed. Full 30-button audit passed. Testing: iteration_481 100%.

### Viral Optimization Sprint — DONE (Apr 9)
**Goal:** Push readiness metrics toward GREENLIGHT through behavioral tuning, not feature expansion.

1. **Raise Repeat Share Rate:**
   - Momentum Meter badge on stories (Rising Fast / Trending / Spreading Widely)
   - "Share Again" button on viral chain timeline with contextual copy
   - Reshare nudge below chain when story has weekly remixes
   - Improved SharePromptModal copy: momentum + pride + urgency tone
   - Reshare notification system with 24h caps per story
2. **Improve Chain Depth ≥2:**
   - Changed remix CTA from "Remix as..." to "Create Your Version of This Story"
   - Added helper text: "Inspired stories spread faster — make this one yours"
3. **Improve Return-to-Inspect:**
   - 24h viral progress nudge notifications (curiosity-driven copy)
   - Max 1 progress nudge per 24h per user
4. **Improve Badge Engagement:**
   - Animated milestone celebration card with bounceIn animation
   - "Share Milestone" micro-CTA on new badge reveals
   - Hover effects on existing milestone badges

All copy variants tagged with `copy_variant_id` for A/B attribution tracking.
Testing: 15/15 backend + all frontend passed (iteration_479)

### P1 — Next Features
- Optimize viral loop: improve share prompt conversion, share link CTR, notification emotional strength, share landing remix conversion
- A/B Week 2: Winner of A vs B → test against Variant C (when threshold reached)

### P2 — Growth & Polish
- Monthly creator milestone digest
- "Remix Variants" on share pages
- Admin WebSocket upgrade
- Story Chain leaderboard

---

## Key Files
- `/app/backend/routes/phase_c_dark_launch.py` — Phase C Dark Launch: engines, feature flag, admin monitor, drill-down
- `/app/backend/services/retention_service.py` — Full retention service (email, notifications, challenges, digest)
- `/app/backend/routes/retention_hooks.py` — Retention API routes (challenges, digest, email preview)
- `/app/backend/routes/story_engine_routes.py` — Job APIs + view_mode + remix triggers
- `/app/backend/routes/viral_flywheel.py` — Viral attribution, lineage, rewards, readiness report
- `/app/frontend/src/components/NotificationBell.js` — Bell with retention types
- `/app/frontend/src/components/RemixGallery.js` — Gallery with auto-play hover preview
- `/app/frontend/src/components/GlobalUserBar.jsx` — Top nav with bell
- `/app/frontend/src/pages/StoryVideoPipeline.js` — Studio + recovery + challenge
- `/app/frontend/src/pages/MySpacePage.js` — Dashboard + ownership + challenge badges + Improve Consistency CTA
- `/app/frontend/src/pages/Dashboard.js` — Challenge banner + Top Stories leaderboard + Featured Winner Hero Slot
- `/app/frontend/src/pages/AdminDashboard.js` — Admin dashboard with Dark Launch Monitor tab
