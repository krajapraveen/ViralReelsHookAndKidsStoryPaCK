# Visionary Suite — PRD

## Product Vision
AI Creative Operating System: **Create -> Share -> Remix -> Loop -> Grow -> Measure -> Optimize**

### Golden Rules
1. Every tool output must answer: "What should I do next?"
2. Zero-friction transitions: Click -> Prefill -> Generate.
3. Every shared creation is a user acquisition channel.
4. Growth must be measured, not assumed.
5. The dashboard tells you what to fix, not just what happened.
6. Speed of learning > quality of code. Ship experiments fast.

## Architecture

### Viral Growth Engine
```
User creates -> shares /v/{slug} -> viewer sees A/B-tested conversion page -> clicks CTA
-> auto-prefilled tool -> login (timed by experiment) -> generates -> shares -> loop
```

### A/B Testing System
```
Session -> deterministic hash -> variant assignment (cached in sessionStorage)
Experiments: cta_copy, hook_text, login_timing
Events tracked: remix_click, generate_click, signup_completed, share_click
Winner heuristic: 20%+ uplift after 200 sessions per variant
Dashboard: /app/admin/growth -> A/B Experiments section
```

### Growth Intelligence System
```
Events: page_view -> remix_click -> tool_open_prefilled -> generate_click -> signup -> creation -> share
Metrics: Conversion rates at each stage, K factor, drop-off detection, auto-diagnosis
Alerts: Threshold-based (remix <5%, signup <10%, etc.)
Dashboard: /app/admin/growth
```

### Self-Defending Infrastructure
- Regression Suite: 35 tests | Watchdog: Auto every 5 min | Health: /api/health/deep

### Payment System (Cashfree)
- Status: Production, fully wired | Products: 5 | Currency: INR

## Production Test History
- Iteration 301: PRODUCTION GO (Backend 94%, Frontend 100%)
- Iteration 302: Growth Intelligence (Backend 36/36, Frontend 17/17)
- Iteration 303: A/B Testing System (Backend 26/26 - 100%)
- Iteration 304: Critical Bug Fixes (Backend 13/13, Frontend 100%)

## Completed Work
1-40. Core platform + Stability + Growth Engine + Analytics + UAT
41. **Lean A/B Testing System** (Feb 2026):
    - Backend: POST /api/ab/assign, /assign-all, /convert, GET /results
    - 3 experiments: CTA Copy, Hook Text, Login Gate Timing
    - Deterministic session-based assignment, deduped conversion tracking
    - Winner heuristic: 20%+ uplift after 200 sessions
    - Frontend: PublicCreation.js renders A/B variants, Growth Dashboard shows results

42. **Critical Bug Fixes — Root Cause Analysis** (Feb 2026):
    - **FIX 1**: SafeImage crossOrigin='anonymous' removed → R2 presigned images now render on Explore/Gallery/all pages
    - **FIX 2**: Gallery query filter expanded ($or: output_url | thumbnail_url | is_showcase) → Gallery no longer shows 0 items for image-only creations
    - **FIX 3**: Profile.js broken link /app/story-video → fixed to /app/story-video-studio

## Active A/B Experiments
1. **cta_copy** — Primary: remix_click
   - "Create This in 1 Click" | "Make Your Own Now" | "Generate This in Seconds"
2. **hook_text** — Primary: remix_click
   - "Made in 30 seconds. No skills needed." | "Created with AI - try it yourself." | "Anyone can make this."
3. **login_timing** — Primary: signup_completed
   - Before Generate | After Generate | After Preview

## Remaining Backlog
### P0
- [ ] CTA Placement experiment (after first 3 experiments are running with traffic)
- [ ] Monitor experiment data, declare winners when 200+ sessions reached

### P1
- [ ] UI Consistency (aspect ratios, card sizing, grid alignment)

### P2
- [ ] Style preset preview thumbnails for Photo-to-Comic
- [ ] Admin Observability Dashboard
- [ ] Cashfree: Enable USD

### Blocked
- R2 CORS — infra config (graceful fallback in place)
- SendGrid — plan upgrade
