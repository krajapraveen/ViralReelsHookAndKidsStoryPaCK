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
7. **No fake success states. If generation fails, say it failed. Never return placehold.co or gradient fallbacks as if they're real content.**

## Architecture

### Content Truth Pipeline
```
Generation -> R2 Upload -> URL stored -> presigned for browser -> rendered in UI
Fallback chain: thumbnail_url -> scene_images[first].url -> honest "unavailable" state
NEVER: placehold.co URLs, gradient-as-content, fake preview states
```

### A/B Testing System
```
Session -> deterministic hash -> variant assignment (cached in sessionStorage)
Experiments: cta_copy, hook_text, login_timing
Winner heuristic: 20%+ uplift after 200 sessions per variant
```

### Discovery Pipeline
```
pipeline_jobs (COMPLETED) -> Gallery/Explore
Query: COMPLETED + (output_url | thumbnail_url | scene_images | is_showcase)
Debug: GET /api/pipeline/gallery/debug
```

## Production Test History
- Iteration 303: A/B Testing System (Backend 26/26 - 100%)
- Iteration 304: Gallery/Explore Image Fix (Backend 13/13 - 100%)
- Iteration 305: Deep Root Cause Fix (Backend + Frontend - 100%)
- Iteration 306: Comic Story Book Preview Fix (Backend 9/9 - 100%, Frontend verified)

## Completed Work
1-40. Core platform + Stability + Growth Engine + Analytics + UAT
41. Lean A/B Testing System (3 experiments live)
42. **Critical Root Cause Fixes — Gallery/Explore** (Feb 2026):
    - SafeImage crossOrigin='anonymous' removed → R2 images now render
    - Gallery query expanded (output_url | thumbnail_url | scene_images | is_showcase)
    - Thumbnail fallback: auto-populate from scene_images when thumbnail_url missing
    - Profile broken link fixed (/app/story-video → /app/story-video-studio)
    - Added /api/pipeline/gallery/debug diagnostic endpoint
43. **Critical Root Cause Fix — Comic Story Book Builder** (Feb 2026):
    - Backend: Removed placehold.co fake URL fallback from preview endpoint
    - Backend: Returns honest {success: false, message: '...'} on preview failure
    - Backend: Job status now presigns page_urls for completed jobs
    - Frontend: Removed ALL placehold.co fallbacks from ComicStorybookBuilder.js
    - Frontend: Added honest "Preview not available" state with clear messaging
    - Frontend: Added post-generation page gallery (cover + pages with real R2 images)
    - SafeImage: Already filters placehold.co as safety net

## Active A/B Experiments
1. **cta_copy** — "Create This in 1 Click" | "Make Your Own Now" | "Generate This in Seconds"
2. **hook_text** — "Made in 30 seconds." | "Created with AI." | "Anyone can make this."
3. **login_timing** — Before Generate | After Generate | After Preview

## Known placehold.co References (Other Tools)
- photo_to_comic.py (3 refs) — fallback URLs on image generation failure
- comix_ai.py (3 refs) — fallback URLs on panel generation failure
- gif_maker.py (2 refs) — fallback URLs on emotion GIF failure
- comic_storybook.py (1 ref) — legacy, superseded by v2
- StylePreview.jsx (24 refs) — static style catalog thumbnails (P3: replace with real images)
- SafeImage.jsx filters ALL placehold.co URLs as safety net

## Remaining Backlog
### P0
- [ ] CTA Placement experiment (after first 3 running with traffic)
- [ ] Monitor experiment data, declare winners at 200+ sessions
- [ ] Remove placehold.co fallbacks from remaining backend tools (photo_to_comic, comix_ai, gif_maker)

### P1
- [ ] UI Consistency (aspect ratios, card sizing, grid alignment)

### P2
- [ ] Style preset real preview thumbnails (replace placehold.co in StylePreview.jsx)
- [ ] Admin Observability Dashboard
- [ ] Cashfree USD support

### Blocked
- R2 CORS — infra config (images now load without CORS enforcement)
- SendGrid — plan upgrade
