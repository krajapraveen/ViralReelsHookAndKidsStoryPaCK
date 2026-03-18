# Visionary Suite — Product Requirements

## Core Product
AI Creator Suite for content generation (story videos, comics, GIFs, storybooks).

## Architecture
- **Frontend**: React + Tailwind + shadcn/ui (port 3000)
- **Backend**: FastAPI + MongoDB (port 8001)
- **Storage**: Cloudflare R2
- **AI**: OpenAI GPT-4o-mini, GPT Image 1, Sora 2, TTS; Gemini; Google Auth
- **Other**: Redis, Cashfree, SendGrid (BLOCKED), apscheduler, FFmpeg

## Key Principles
1. **Truth-Driven Pipelines**: All content generation follows strict state machine (INIT→GENERATING→VALIDATING→READY/FAILED). Never fake output.
2. **No Fake UI States**: Frontend never shows placehold.co, empty cards, or "saved" without real asset.
3. **Universal Negative Prompt**: All image generation paths include comprehensive quality/safety negative prompt.
4. **PLAN → GENERATE Flow**: Story Series Engine enforces strict 2-step flow. Never generate without planning first.

## Production Test History
- Iteration 303: A/B Testing (26/26 - 100%)
- Iteration 304-305: Gallery/Explore Image Rendering (100%)
- Iteration 306: Comic Storybook Preview (100%)
- Iteration 307: Download Fix + Timer (100%)
- Iteration 308: Photo to Comic Strip Pipeline (100%)
- Iteration 309: Ken Burns, Form Controls, Resume Panels, More Tools (100%)
- Iteration 310: Truth-vs-Illusion Sprint — Zero placehold.co, data repair, negative prompts (16/16 - 100%)
- Iteration 311: Story Series Engine Phase 1 — All 8 APIs + 3 frontend pages (37/37 backend + all frontend - 100%)

## Completed Work
1-50. Core platform + Stability + Growth Engine + Analytics + UAT + Truth-Repair + GIF Download Pack
51. **Story Series Engine — Phase 1** (Mar 2026):
    - **Backend (8 APIs)**: create-series, my-series, get-series, plan-episode, generate-episode, suggestions, update-memory, episode-status
    - **Auth**: All endpoints use Depends(get_current_user) — proper FastAPI auth pattern
    - **State Machine**: planned → generating → ready / failed. No READY without real output_url
    - **Pipeline Integration**: Reuses existing create_pipeline_job + enqueue_job (credit deduction, job queuing)
    - **LLM Integration**: emergentintegrations with gpt-4o-mini for foundation generation, episode planning, suggestions, memory extraction
    - **Atomic Memory**: _update_memory_internal with 3-retry logic, safe dedup for dict items
    - **Frontend (3 pages)**:
      - `/app/story-series` — My Series hub with series cards, episode count, next hook
      - `/app/story-series/create` — Create form (title, prompt, genre, audience, style)
      - `/app/story-series/:seriesId` — Timeline page with 4 zones:
        1. Episode Timeline (status badges, expand/collapse, generate/retry/view actions)
        2. Action Zone ("What happens next?" — Continue, Plot Twist, Raise Stakes)
        3. AI Suggestions (refresh to get LLM-powered story ideas)
        4. Series Info (characters, world, story hooks)

## Remaining Backlog
### P0
- [ ] End-to-end verify Ken Burns motion in actual generated video (needs credits)
- [ ] CTA Placement A/B Test (4th experiment)

### P1
- [ ] Dashboard "Resume Your Story" → link into Story Series
- [ ] Story Series suggestions improvement
- [ ] UI Consistency (aspect ratios, card sizing)
- [ ] Admin Dashboard UI for observability APIs

### P2 — Story Series Phase 2
- [ ] Branching (remix-branch)
- [ ] Public series pages
- [ ] Growth hooks

### P3 — Story Series Phase 3
- [ ] Deeper character/world bible
- [ ] Emotional memory
- [ ] Style preset preview thumbnails for Photo to Comic

### BLOCKED
- [ ] R2 bucket CORS policy (requires manual user config)
- [ ] SendGrid upgrade (requires user plan upgrade)
