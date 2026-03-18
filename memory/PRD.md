# Visionary Suite — PRD

## Product Vision
AI Creative Operating System: **Create -> Share -> Remix -> Loop -> Grow -> Measure -> Optimize**

### Golden Rules
1. No paid/credit-consuming feature should ever pretend to have output when it does not.
2. SUCCESS = REAL OUTPUT RENDERED TO USER.
3. All text must be visually readable on dark backgrounds.
4. Downloads must download, not open blank tabs.
5. Copy to clipboard must have fallback for non-HTTPS contexts.

## Production Test History
- Iteration 303: A/B Testing (26/26 - 100%)
- Iteration 304-305: Gallery/Explore Image Rendering (100%)
- Iteration 306: Comic Storybook Preview (100%)
- Iteration 307: Download Fix + Timer (100%)
- Iteration 308: Photo to Comic Strip Pipeline (100%)

## Completed Work
1-40. Core platform + Stability + Growth Engine + Analytics + UAT
41. Lean A/B Testing System (3 experiments live)
42. Gallery/Explore root cause fixes
43. Comic Story Book Builder fixes
44. Download fix (fetch→blob) + Generation timer
45. Photo to Comic Strip Pipeline fix
46. **Text Visibility + Copy Fix** (Feb 2026):
    - PhotoToComic.js: Continue Story buttons — labels: text-white, descriptions: text-slate-400
    - StoryVideoPipeline.js: Same Continue Story pattern fixed
    - StoryVideoStudio.js: Quick Continue + Remix description text fixed
    - AutomationDashboard.js: text-slate-600 → text-slate-400
    - Contact.js, CopyrightInfo.js: dark text → visible text
    - StorySeries.js: opacity-70 → text-slate-400
    - PhotoToComic.js: Copy fallback (navigator.clipboard + execCommand fallback)

## Active A/B Experiments
1. cta_copy — "Create This in 1 Click" | "Make Your Own Now" | "Generate This in Seconds"
2. hook_text — "Made in 30 seconds." | "Created with AI." | "Anyone can make this."
3. login_timing — Before Generate | After Generate | After Preview

## Remaining Backlog
### P0
- [ ] Remove placehold.co from avatar mode, comix_ai, gif_maker
- [ ] CTA Placement experiment
- [ ] Monitor experiment data

### P1
- [ ] UI Consistency (aspect ratios, card sizing)
- [ ] Character consistency for comic strip panels

### P2
- [ ] Style preset real thumbnails
- [ ] Admin Dashboard
- [ ] Cashfree USD

### Blocked
- R2 CORS — images load without CORS enforcement
- SendGrid — plan upgrade
