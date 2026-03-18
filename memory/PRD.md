# Visionary Suite — PRD

## Product Vision
AI Creative Operating System: **Create -> Share -> Remix -> Loop -> Grow -> Measure -> Optimize**

### Golden Rules
1. No paid/credit-consuming feature should ever pretend to have output when it does not.
2. SUCCESS = REAL OUTPUT RENDERED TO USER, not "API returned success".
3. Failed panels show honest failure state, not gradient placeholders.
4. Credits only charged for real generated output.

## Production Test History
- Iteration 303: A/B Testing (26/26 - 100%)
- Iteration 304-305: Gallery/Explore Image Rendering (100%)
- Iteration 306: Comic Storybook Preview Fix (100%)
- Iteration 307: Download Fix + Timer (100%)
- Iteration 308: Photo to Comic Strip Pipeline Fix (Backend 78%, Frontend 100%)

## Completed Work
1-40. Core platform + Stability + Growth Engine + Analytics + UAT
41. Lean A/B Testing System (3 experiments live)
42. Gallery/Explore root cause fixes (crossOrigin, scene_images fallback)
43. Comic Story Book Builder fixes (honest preview, no placehold.co)
44. Download fix (fetch→blob) + Generation timer (4-7 min)
45. **Photo to Comic Strip Pipeline Fix** (Feb 2026):
    - Removed ALL placehold.co from strip generation pipeline
    - Per-panel status tracking: READY (real image) / FAILED (imageUrl: null)
    - Honest job status: COMPLETED / PARTIAL_READY / FAILED
    - Smart credit handling: pro-rated per successful panel, zero charge on total failure
    - Frontend: real images for READY panels, red X + "Panel N Failed" for failures
    - Partial-ready banner: "X of Y panels generated. Z failed."
    - FAILED state: "Generation Failed. No credits were charged."

## Active A/B Experiments
1. cta_copy — "Create This in 1 Click" | "Make Your Own Now" | "Generate This in Seconds"
2. hook_text — "Made in 30 seconds." | "Created with AI." | "Anyone can make this."
3. login_timing — Before Generate | After Generate | After Preview

## Known placehold.co References Remaining
- photo_to_comic.py line 670: Avatar mode fallback (P0 backlog)
- comix_ai.py: 3 references (P0 backlog)
- gif_maker.py: 2 references (P0 backlog)
- comic_storybook.py: 1 reference (legacy, superseded by v2)
- StylePreview.jsx: 24 references (style catalog, P2)

## Remaining Backlog
### P0
- [ ] Remove placehold.co from avatar mode, comix_ai, gif_maker
- [ ] CTA Placement experiment (after first 3 running)
- [ ] Monitor experiment data

### P1
- [ ] UI Consistency
- [ ] Character consistency layer for comic strip panels

### P2
- [ ] Style preset real thumbnails
- [ ] Admin Dashboard
- [ ] Cashfree USD

### Blocked
- R2 CORS — images load without CORS enforcement now
- SendGrid — plan upgrade
