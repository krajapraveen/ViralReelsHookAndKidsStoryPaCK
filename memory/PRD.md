# Visionary Suite — PRD

## Product Vision
AI Creative Operating System: **Create -> Share -> Remix -> Loop -> Grow -> Measure -> Optimize**

### Golden Rules
1. Every tool output must answer: "What should I do next?"
2. Zero-friction transitions: Click -> Prefill -> Generate.
3. Every shared creation is a user acquisition channel.
4. Growth must be measured, not assumed.
5. Speed of learning > quality of code. Ship experiments fast.
6. **No fake success states. If generation fails, say it failed.**
7. **Downloads must download, not open blank tabs.**

## Production Test History
- Iteration 303: A/B Testing System (26/26 - 100%)
- Iteration 304-305: Gallery/Explore Image Rendering (100%)
- Iteration 306: Comic Preview Fix (100%)
- Iteration 307: Download Fix + Timer (100%)

## Completed Work
1-40. Core platform + Stability + Growth Engine + Analytics + UAT
41. Lean A/B Testing System (3 experiments live)
42. Gallery/Explore root cause fixes (crossOrigin, scene_images fallback, query expansion)
43. Comic Story Book Builder fixes (honest preview states, no placehold.co)
44. **Download Fix + Generation Timer** (Feb 2026):
    - DownloadWithExpiry: fetch→blob→createObjectURL download pattern (fixes ALL tools)
    - Removed target='_blank' and window.open from all download handlers
    - Comic Builder: estimatedTime changed to "4-7 minutes"
    - Comic Builder: generationStartTime tracks actual elapsed time
    - Comic Builder: "Generated in Xm Ys" shown after completion

## Active A/B Experiments
1. **cta_copy** — "Create This in 1 Click" | "Make Your Own Now" | "Generate This in Seconds"
2. **hook_text** — "Made in 30 seconds." | "Created with AI." | "Anyone can make this."
3. **login_timing** — Before Generate | After Generate | After Preview

## Remaining Backlog
### P0
- [ ] Remove placehold.co fallbacks from remaining tools (photo_to_comic, comix_ai, gif_maker)
- [ ] CTA Placement experiment (after first 3 running with traffic)
- [ ] Monitor experiment data, declare winners at 200+ sessions

### P1
- [ ] UI Consistency (aspect ratios, card sizing, grid alignment)

### P2
- [ ] Style preset real preview thumbnails
- [ ] Admin Observability Dashboard
- [ ] Cashfree USD support

### Blocked
- R2 CORS — infra config (images now load without CORS enforcement)
- SendGrid — plan upgrade
