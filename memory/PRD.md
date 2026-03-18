# Visionary Suite — Product Requirements

## Core Product
AI Creator Suite for content generation (story videos, comics, GIFs, storybooks).

## Architecture
- **Frontend**: React + Tailwind + shadcn/ui (port 3000)
- **Backend**: FastAPI + MongoDB (port 8001)
- **Storage**: Cloudflare R2
- **AI**: OpenAI GPT-4o-mini, GPT Image 1, Sora 2, TTS; Gemini; Google Auth
- **Other**: Redis, Cashfree, SendGrid (BLOCKED), apscheduler, FFmpeg

## AI Character Memory — Complete System

### Backend: 16 API Endpoints + 3 Internal Functions
| # | Endpoint | Description |
|---|----------|-------------|
| 1 | POST /api/characters/create | Create with LLM visual bible |
| 2 | GET /api/characters/my-characters | List user's characters |
| 3 | GET /api/characters/{id} | Full detail |
| 4 | PATCH /api/characters/{id} | Update profile |
| 5 | GET /api/characters/{id}/memory | Memory log timeline |
| 6 | POST /api/characters/{id}/generate-portrait | Canonical portrait |
| 7 | POST /api/characters/attach-to-series/{series_id} | Link to series |
| 8 | POST /api/characters/{id}/validate-continuity | Continuity check |
| 9 | GET /api/characters/{id}/continuity-history | Validation history |
| 10 | POST /api/characters/{id}/voice-profile | Set voice config |
| 11 | GET /api/characters/{id}/voice-profile | Get voice config |
| 12 | POST /api/characters/create-from-reference | Reference-based + consent |
| 13 | PATCH /api/characters/{id}/visual-bible | Edit VB (versioned) |
| 14 | GET /api/characters/{id}/visual-bible-history | VB version history |
| 15 | POST /api/characters/{id}/relationships | Add/update relationship |
| 16 | GET /api/characters/{id}/relationships | Get relationship graph |
| 17 | GET /api/characters/{id}/emotional-arc | Emotional progression |
| 18 | GET /api/characters/search/query | Search/filter/sort |
| Int | build_character_prompt_package() | 5-block generation contract |
| Int | build_character_generation_context() | Cross-tool shared context |
| Int | validate_character_continuity() | Post-generation gate |

### Data Collections (7)
- `character_profiles`, `character_visual_bibles`, `character_memory_logs`
- `character_safety_profiles`, `character_voice_profiles`
- `character_continuity_validations`, `character_visual_bible_history`
- `character_relationships`

### Key Features
- **Editable VBs**: Versioned edits with archive, auto-validation, style_lock protection
- **3-Tier Safety**: 100+ blocked IPs, similarity regex, celebrity detection, consent gate
- **Cross-Tool Persistence**: Story Video + Comic Storybook + Photo to Comic + GIF Maker
- **Continuity Validator**: 6 rule-based checks, score 0-100, drift flags
- **Relationship Graph**: Bidirectional, friend/enemy/mentor/family/rival/ally
- **Emotional Memory**: Categorical (happy/sad/tense/scared/confident), intensity 1-5, trend

## Story Series Engine — 15 API Endpoints
(Unchanged)

## Monetization Engine
- 4-tier pricing: Free / Creator / Pro / Elite
- Paywall enforcement + UpgradeModal

## Testing History
- Iteration 311-314: Story Series + Pricing + AI Suggestions + Cover Image
- Iteration 315: Character Memory Phase 1 — 23/23 (100%)
- Iteration 316: Phase 2 (Validator + Voice + Cross-Tool + Consent) — 20/20 (100%)
- Iteration 317: Sprint C (Editable VB + Relationships + Emotions + Search) — 29/29 (100%)

## Completed Work
1-61. Previous features
62. AI Character Memory Phase 1 MVP - DONE
63. Continuity Validator - DONE
64. Voice Profile Entity - DONE
65. Cross-Tool Character Persistence (4 tools) - DONE
66. Real-Person Consent Guardrails - DONE
67. Editable Visual Bibles (versioned + validated + style_lock protected) - DONE
68. Relationship Graph (bidirectional, enriched) - DONE
69. Emotional Memory (categorical, trend derivation) - DONE
70. Library Search/Filter (name search, role filter, sort) - DONE

## Remaining Backlog
- [ ] Admin Dashboard UI for observability APIs
- [ ] Growth loop: series completion rewards
- [ ] Style preset preview thumbnails for Photo to Comic
- [ ] Auto-character extraction from Episode 1

### BLOCKED
- [ ] R2 bucket CORS (manual config)
- [ ] SendGrid upgrade (user plan)
