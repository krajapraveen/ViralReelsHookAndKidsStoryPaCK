# Visionary Suite — Product Requirements

## Core Product
AI Creator Suite for content generation (story videos, comics, GIFs, storybooks).

## Architecture
- **Frontend**: React + Tailwind + shadcn/ui (port 3000)
- **Backend**: FastAPI + MongoDB (port 8001)
- **Storage**: Cloudflare R2
- **AI**: OpenAI GPT-4o-mini, GPT Image 1, Sora 2, TTS; Gemini; Google Auth
- **Other**: Redis, Cashfree, SendGrid (BLOCKED), apscheduler

## Key Principles
1. **Truth-Driven Pipelines**: All content generation follows strict state machine (INIT→GENERATING→VALIDATING→READY/PARTIAL_READY/FAILED). Never fake output.
2. **No Fake UI States**: Frontend never shows placehold.co, empty cards, or "saved" without real asset.
3. **Universal Negative Prompt**: All image generation paths include comprehensive quality/safety negative prompt.

## Production Test History
- Iteration 303: A/B Testing (26/26 - 100%)
- Iteration 304-305: Gallery/Explore Image Rendering (100%)
- Iteration 306: Comic Storybook Preview (100%)
- Iteration 307: Download Fix + Timer (100%)
- Iteration 308: Photo to Comic Strip Pipeline (100%)
- Iteration 309: Ken Burns, Form Controls, Resume Panels, More Tools (100%)
- Iteration 310: Truth-vs-Illusion Sprint — Zero placehold.co, data repair, negative prompts (16/16 - 100%)

## Completed Work
1-40. Core platform + Stability + Growth Engine + Analytics + UAT
41. Lean A/B Testing System (3 experiments live)
42. Gallery/Explore root cause fixes
43. Comic Story Book Builder fixes
44. Download fix (fetch→blob) + Generation timer
45. Photo to Comic Strip Pipeline fix
46. Text Visibility + Copy Fix (Feb 2026)
47. P0 Critical Fixes (Mar 2026):
    - Ken Burns motion system (6 patterns: zoom_in, pan_right, zoom_out, pan_left, zoom_in_top, pan_up)
    - Story Video form controls: text-slate-200 + border-slate-600 + ring selection highlight
    - More Tools label: text-white/80 with font-medium
    - FFmpeg installed, 24fps/CRF26/2 threads
48. **Truth-vs-Illusion Sprint** (Mar 2026):
    - ELIMINATED all placehold.co from backend (7 instances in 4 files) and frontend (25+ in StylePreview.jsx)
    - Data Repair Script: 19 zombie COMPLETED pipeline_jobs → ORPHANED, 5 fake comic records → FAILED
    - User-jobs endpoint excludes ORPHANED status
    - Explore endpoint requires real output_url
    - Universal Negative Prompt in ALL 5 image generation paths
    - Story Video PostGen truth: View/Download for real output, failure state for no output, never empty preview
    - StylePreview.jsx: CSS gradient backgrounds replace placehold.co URLs
49. **Resume Your Story Data-Layer Fix** (Mar 2026):
    - ROOT CAUSE: 11 photo_to_comic_jobs had placehold.co resultUrl still in DB → marked FAILED, resultUrl set to null
    - Backend truth gate: active-chains endpoint SKIPS chains without valid renderable preview URL
    - Frontend defense: ResumeYourStory only renders chains with valid https:// preview_url
    - "Preview unavailable" fallback REMOVED entirely — if no valid data, section hides completely
    - RESULT: Zero dead content shown, zero "Preview unavailable" cards

## Remaining Backlog
### P0
- [ ] End-to-end verify Ken Burns motion in actual generated video (needs credits)
- [ ] CTA Placement A/B Test (4th experiment)
- [ ] Monitor experiment data

### P1
- [ ] UI Consistency (aspect ratios, card sizing)
- [ ] Admin Dashboard UI for observability APIs

### P2
- [ ] Style preset preview thumbnails for Photo to Comic (real AI-generated)
- [ ] Fine-tune A/B testing experiments based on data

### BLOCKED
- [ ] R2 bucket CORS policy (requires manual user config)
- [ ] SendGrid upgrade (requires user plan upgrade)
