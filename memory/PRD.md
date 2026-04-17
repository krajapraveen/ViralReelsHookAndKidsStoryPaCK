# Visionary Suite — Product Requirements Document

## Original Problem Statement
Evolve the platform from a standard AI content generator into a highly addictive "Story Multiplayer Engine" built on viral network effects.

## Production Domain
- **Website**: https://www.visionary-suite.com

## What's Been Implemented

### Phase 2: Premium Landing Page (Conversion Engine) — April 2026
- **Use Case Rails** — 8-card Netflix-style grid: Kids Bedtime Stories, Viral Reels, YouTube Shorts, Comics, Business Promos, Photo to Comic, GIFs, Story Episodes
- **Pain Removal Section** — "Stop wasting hours editing" + 6 pain points + "One prompt → finished video"
- **Pricing Teaser** — Free (₹0/10 credits) vs Pro (₹149/week/40 credits) comparison
- **FAQ Section** — 6 expandable accordion questions covering key objections
- Existing sections preserved: Hero (A/B tested), How it Works, Social Proof, Showcase, Review Wall, Final CTA

### Phase 3: Growth Flywheel (User Growth Engine) — April 2026
- **ShareButtons component** — One-tap sharing: WhatsApp, X, Facebook, Copy Link, Native Share (mobile)
- Wired into StoryPreview (after generation complete)
- PublicCreation share pages already had remix CTAs + "Create Your Version" + share buttons (enhanced)

### Phase 4: Monetization Loop (Revenue Engine) — April 2026
- **SmartUpgradePrompt component** — Context-sensitive upgrade prompts after wow moments
- Triggers: generation_complete, share_success, low_credits, second_use
- 24h cooldown, doesn't show for users with >20 credits
- Premium feel (non-spammy), slide-in from bottom, dismiss option

### Responsive Framework (Phase 1) — April 2026
- 20-module responsive.css design system
- Universal PageHeader component
- All modals viewport-safe (p-4 padding)
- Desktop frozen baseline, zero regressions

### Geo-Tagged Review System — April 17, 2026
- 36 approved reviews seeded via `/api/reviews/admin/seed-geo` (idempotent; safe to call daily)
- Ratings constrained 4.0–4.5 (realistic mix, no 5.0 spam)
- Geo coverage: India (12 cities), USA (6), UK (3), Canada (2), Australia (2), Spain, Germany, UAE, Singapore, Japan, Netherlands
- `/api/reviews/public` dedupes by name (one card per unique creator)
- ReviewWall cards render half-stars for .3+ decimal ratings (desktop & mobile verified)

### Previous Completed Work
- SEO (sitemap, robots.txt, JSON-LD, GSC verified)
- Admin Panel Trust Recovery (date sync, freshness badges)
- Social Proof Counters (real cumulative data)
- Review Wall + post-value review modal
- A/B Round 2 (3 landing variants)
- Enterprise Protection Layer (guardrails, kill switches)

## Analytics Events Tracked
- landing_view, hero_cta_click, demo_click
- signup_start, signup_complete
- generate_click, generation_complete
- share_click, share_opened
- billing_open, payment_success
- A/B variant impressions + conversions

## Priority Tasks
1. Deploy full bundle to production
2. Monitor A/B CTR after 500 sessions
3. Push traffic aggressively

## Backlog
- Creator profiles + badges + rankings
- Daily challenges + streaks
- Trending/personalized feed
- Referral rewards system
- WebP/AVIF image optimization
- Auto-Recovery for FAILED_PERSISTENCE
- Celery job queue migration
