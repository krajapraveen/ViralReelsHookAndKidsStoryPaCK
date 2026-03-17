# Visionary Suite — PRD

## Product Vision
AI Creative Operating System: **Create -> Share -> Remix -> Loop -> Grow -> Measure -> Optimize**

### Golden Rules
1. Every tool output must answer: "What should I do next?"
2. Zero-friction transitions: Click -> Prefill -> Generate.
3. Every shared creation is a user acquisition channel.
4. Growth must be measured, not assumed.
5. Speed of learning > quality of code. Ship experiments fast.
6. **A content platform with no visible content = dead product. Validate content rendering FIRST.**

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

### Content Discovery Pipeline
```
pipeline_jobs (COMPLETED) -> Gallery/Explore -> thumbnail rendering
Thumbnail priority: thumbnail_url -> scene_images[first].url
Query: COMPLETED + (output_url | thumbnail_url | scene_images | is_showcase)
Debug: GET /api/pipeline/gallery/debug for raw data state
```

## Production Test History
- Iteration 303: A/B Testing System (Backend 26/26 - 100%)
- Iteration 304: Initial Bug Fixes (Backend 13/13, Frontend 100%)
- Iteration 305: Deep Root Cause Fix (Backend 94%, Frontend 100%) - Gallery/Explore verified

## Completed Work
1-40. Core platform + Stability + Growth Engine + Analytics + UAT
41. Lean A/B Testing System (3 experiments live)
42. **Critical Root Cause Fixes** (Feb 2026):
    - ROOT CAUSE 1: SafeImage crossOrigin='anonymous' blocked ALL R2 image rendering → removed
    - ROOT CAUSE 2: Gallery query too strict (only output_url) → expanded to include thumbnail_url + scene_images
    - ROOT CAUSE 3: Missing thumbnail fallback → scene_images[first].url auto-populates empty thumbnails
    - ROOT CAUSE 4: Profile broken link /app/story-video → /app/story-video-studio
    - Added /api/pipeline/gallery/debug diagnostic endpoint
    - Result: Gallery 0 → 74 items, Explore gradient placeholders → real images

## Active A/B Experiments
1. **cta_copy** — "Create This in 1 Click" | "Make Your Own Now" | "Generate This in Seconds"
2. **hook_text** — "Made in 30 seconds." | "Created with AI." | "Anyone can make this."
3. **login_timing** — Before Generate | After Generate | After Preview

## Remaining Backlog
### P0
- [ ] CTA Placement experiment (after first 3 running with traffic)
- [ ] Monitor experiment data, declare winners at 200+ sessions

### P1
- [ ] UI Consistency (aspect ratios, card sizing, grid alignment)

### P2
- [ ] Style preset thumbnails for Photo-to-Comic
- [ ] Admin Observability Dashboard
- [ ] Cashfree USD support

### Blocked
- R2 CORS — infra config (graceful fallback in place, images now load without CORS)
- SendGrid — plan upgrade
