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
1. **Truth-Driven Pipelines**: Strict state machine (INIT → GENERATING → VALIDATING → READY/FAILED). Never fake output.
2. **No Fake UI States**: Frontend never shows placehold.co, empty cards, or "saved" without real asset.
3. **Universal Negative Prompt**: All image generation paths include comprehensive quality/safety negative prompt.
4. **PLAN → GENERATE Flow**: Story Series Engine enforces strict 2-step flow. Never generate without planning first.
5. **Atomic Memory Updates**: Story memory updates use retry logic (3 attempts) and safe deduplication.

## Story Series Engine — Complete Architecture

### Backend: 15 API Endpoints
| # | Endpoint | Phase | Auth | Description |
|---|----------|-------|------|-------------|
| 1 | POST /create | 1 | Yes | Creates series with LLM foundation |
| 2 | GET /my-series | 1 | Yes | User's active/paused series |
| 3 | GET /{id} | 1 | Yes | Full details + timeline |
| 4 | POST /{id}/plan-episode | 1 | Yes | LLM plans next episode |
| 5 | POST /{id}/generate-episode | 1 | Yes | Generates via pipeline |
| 6 | POST /{id}/suggestions | 1 | Yes | AI next-episode ideas (enriched) |
| 7 | POST /{id}/update-memory | 1 | Yes | Atomic memory update |
| 8 | GET /{id}/episode/{eid}/status | 1 | Yes | Strict validation |
| 9 | POST /{id}/branch-episode | 2 | Yes | Branch from any episode |
| 10 | GET /public/{id} | 2 | No | Public series view |
| 11 | POST /{id}/share | 2 | Yes | Toggle public + share URL |
| 12 | POST /{id}/enhance-characters | 3 | Yes | Deep backstory/relationships |
| 13 | POST /{id}/enhance-world | 3 | Yes | Lore/locations/secrets |
| 14 | GET /{id}/emotional-arc | 3 | Yes | Emotional progression |
| 15 | POST /{id}/generate-cover | 4 | Yes | Cover image from series data |

### Frontend: 4 Pages + Components
- `/app/story-series` — My Series hub
- `/app/story-series/create` — Create series form
- `/app/story-series/:seriesId` — Timeline (4 zones: episodes, actions, suggestions, info + cover)
- `/series/:seriesId` — Public series page (no auth)
- `/app/pricing` — 4-tier subscription plans

### Data Model
- `story_series` — Series metadata, public state, cover_asset_url
- `story_episodes` — Episodes with plan, status, branch info
- `character_bibles` — Characters with backstory, relationships (enhanced)
- `world_bibles` — World with lore, locations, secrets (enhanced)
- `story_memories` — Canon events, open loops, character states, hooks

## Monetization Engine
- **4-tier pricing**: Free / Creator ($5.99) / Pro ($11.99) / Elite ($23.99)
- **Credit top-ups**: 20/$2.49, 50/$4.99, 100/$8.49
- **Per-tool credit costs**: caption=1, gif=2, photo_to_comic=3, storybook=5, story_video=10
- **Paywall enforcement**: Backend returns 403 on series/episode limits, frontend shows UpgradeModal
- **Behavioral compulsion**: ResumeYourStory card with urgency CTAs, SeriesTimeline auto-focus

## Testing History
- Iteration 311: Story Series Phase 1 — 37/37 backend + all frontend (100%)
- Iteration 312: Phase 2+3 + CTA A/B + UI — 53/53 backend + all frontend (100%)
- Iteration 313: Pricing & Compulsion Engine — 45/45 backend + all frontend (100%)
- Iteration 314: AI Suggestions + Cover Image — 24/25 backend + all frontend (100%)
- Ken Burns Motion: 6/6 FFmpeg zoompan patterns produce detectable motion (pixel-verified)

## Completed Work Summary
1-50. Core platform + Stability + Growth Engine + Analytics + UAT + Truth-Repair + GIF Download Pack
51. Story Series Engine Phase 1 (8 APIs, 3 pages) - DONE
52. Dashboard Resume Your Story → Story Series integration - DONE
53. CTA Placement A/B Test (4th experiment: top/bottom/floating) - DONE
54. Story Series Phase 2 (branching, public series, share/growth) - DONE
55. Story Series Phase 3 (deeper character/world bibles, emotional memory) - DONE
56. UI Consistency pass (min-heights, aspect ratios, card sizing) - DONE
57. Behavioral Compulsion Engine (urgency CTAs, auto-focus, action-driven copy) - DONE
58. Pricing & Monetization Engine (4-tier plans, credits, top-ups, paywalls) - DONE
59. Improved AI Suggestions (enriched with chars, world, episodes, memory) - DONE
60. Series Cover Image Generation (gpt-image-1, R2 upload, sidebar display) - DONE
61. Ken Burns Motion E2E Verification (6/6 FFmpeg patterns pass, pixel-level confirmed) - DONE

## Remaining Backlog
### P0
- [x] End-to-end verify Ken Burns motion in actual generated video — VERIFIED (6/6 patterns pass)

### P1
- [ ] Admin Dashboard UI for observability APIs

### P2
- [ ] Growth loop: series completion rewards
- [ ] Advanced emotional memory with mood tracking per character
- [ ] Style preset preview thumbnails for Photo to Comic

### BLOCKED
- [ ] R2 bucket CORS policy (requires manual user config)
- [ ] SendGrid upgrade (requires user plan upgrade)
