# Visionary Suite — Product Requirements

## Core Product
AI Creator Suite for content generation (story videos, comics, GIFs, storybooks).

## Architecture
- **Frontend**: React + Tailwind + shadcn/ui (port 3000)
- **Backend**: FastAPI + MongoDB (port 8001)
- **Storage**: Cloudflare R2
- **AI**: OpenAI GPT-4o-mini, GPT Image 1, Sora 2, TTS; Gemini; Google Auth
- **Other**: Redis, Cashfree, SendGrid (BLOCKED), apscheduler, FFmpeg

## AI Character Memory — Full Architecture

### Backend: 12 API Endpoints + 3 Internal Functions
| # | Endpoint | Description |
|---|----------|-------------|
| 1 | POST /api/characters/create | Create with LLM visual bible |
| 2 | GET /api/characters/my-characters | List user's characters |
| 3 | GET /api/characters/{id} | Full detail |
| 4 | PATCH /api/characters/{id} | Update profile |
| 5 | GET /api/characters/{id}/memory | Memory log timeline |
| 6 | POST /api/characters/{id}/generate-portrait | Canonical portrait |
| 7 | POST /api/characters/attach-to-series/{series_id} | Link to series |
| 8 | POST /api/characters/{id}/validate-continuity | Run continuity check |
| 9 | GET /api/characters/{id}/continuity-history | Validation history |
| 10 | POST /api/characters/{id}/voice-profile | Set voice config |
| 11 | GET /api/characters/{id}/voice-profile | Get voice config |
| 12 | POST /api/characters/create-from-reference | Reference-based with consent |
| Internal | build_character_prompt_package() | 5-block generation contract |
| Internal | build_character_generation_context() | Cross-tool shared context |
| Internal | validate_character_continuity() | Post-generation gate |

### Data Collections (6)
- `character_profiles` — identity, personality, portrait_url, status
- `character_visual_bibles` — canonical desc, locked rules, style_lock, negative constraints
- `character_memory_logs` — per-episode events, emotions, open/resolved loops
- `character_safety_profiles` — consent, copyright flags, disallowed transformations
- `character_voice_profiles` — voice_id, tone, pace, accent, energy, do_not_change_rules
- `character_continuity_validations` — score, drift_flags, retry_recommended

### Continuity Validator (6 checks)
1. Canonical description presence in prompt
2. Do-not-change rules ratio (flags if <50%)
3. Style lock maintained
4. Negative constraints present
5. IP resemblance scan (100+ blocked names)
6. Output asset existence

### Cross-Tool Character Persistence
One shared function: `build_character_generation_context(character_id, series_id, tool_type, scene_context)`
Integrated into: Story Video, Comic Storybook, Photo to Comic, GIF Maker

### Safety Layer (3-Tier + Consent)
- **Tier 1**: 100+ blocked IP names
- **Tier 2**: Similarity regex patterns
- **Tier 3**: Celebrity/real-person detection
- **Consent Gate**: create-from-reference requires consent_confirmed for real-person likeness

## Story Series Engine — 15 API Endpoints
(See previous PRD for full list)

## Monetization Engine
- 4-tier pricing: Free / Creator ($5.99) / Pro ($11.99) / Elite ($23.99)
- Paywall enforcement: 403 on limits, UpgradeModal in frontend

## Testing History
- Iteration 311: Story Series Phase 1 — 37/37 (100%)
- Iteration 312: Phase 2+3 + CTA A/B + UI — 53/53 (100%)
- Iteration 313: Pricing & Compulsion Engine — 45/45 (100%)
- Iteration 314: AI Suggestions + Cover Image — 24/25 (100%)
- Iteration 315: AI Character Memory Phase 1 — 23/23 (100%)
- Iteration 316: Phase 2+3 (Continuity Validator + Voice + Cross-Tool + Consent) — 20/20 (100%)
- Ken Burns Motion: 6/6 FFmpeg zoompan patterns (pixel-verified)

## Completed Work
1-61. (Previous features)
62. AI Character Memory Phase 1 MVP - DONE
63. Continuity Validator — 6 rule-based checks, score 0-100, drift_flags, retry_recommended - DONE
64. Voice Profile Entity — voice_id, tone, pace, accent, energy, upsert pattern - DONE
65. Cross-Tool Character Persistence — shared build_character_generation_context(), wired into Comic Storybook, Photo to Comic, GIF Maker - DONE
66. Real-Person Consent Guardrails — create-from-reference with consent gate, negative constraints for no real-person likeness - DONE

## Remaining Backlog

### Sprint C (Deferred per user)
- [ ] Editable visual bibles with live preview
- [ ] Relationship graph entity + visualization
- [ ] Character Library UI enhancements (search/filter/sort)
- [ ] Advanced emotional memory

### Other
- [ ] Admin Dashboard UI for observability APIs
- [ ] Growth loop: series completion rewards
- [ ] Style preset preview thumbnails for Photo to Comic

### BLOCKED
- [ ] R2 bucket CORS policy (requires manual user config)
- [ ] SendGrid upgrade (requires user plan upgrade)
