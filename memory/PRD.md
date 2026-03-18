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
1. **Truth-Driven Pipelines**: Strict state machine (INIT -> GENERATING -> VALIDATING -> READY/FAILED). Never fake output.
2. **Character Memory = Structured Persistence**: Not a prompt shortcut. Identity + Visual Bible + Memory Log + Safety Profile + Prompt Package Builder.
3. **Universal Negative Prompt**: All image generation paths include comprehensive quality/safety negative prompt.
4. **PLAN -> GENERATE Flow**: Story Series Engine enforces strict 2-step flow.
5. **3-Tier Safety**: Keyword screening + similarity flagging + no persistent storage of risky profiles.

## AI Character Memory — Complete Architecture

### Backend: 7 API Endpoints + 2 Internal Functions
| # | Endpoint | Auth | Description |
|---|----------|------|-------------|
| 1 | POST /api/characters/create | Yes | Creates character with LLM-generated visual bible |
| 2 | GET /api/characters/my-characters | Yes | List user's characters |
| 3 | GET /api/characters/{id} | Yes | Full detail: profile + visual bible + safety + memory |
| 4 | PATCH /api/characters/{id} | Yes | Update profile fields (re-checks safety) |
| 5 | GET /api/characters/{id}/memory | Yes | Memory log timeline |
| 6 | POST /api/characters/{id}/generate-portrait | Yes | Canonical portrait via gpt-image-1 |
| 7 | POST /api/characters/attach-to-series/{series_id} | Yes | Link character to series |
| Internal | build_character_prompt_package() | - | Returns 5-block generation contract |
| Internal | write_character_memory() | - | Writes memory after episode generation |

### Data Entities (4 Collections)
- `character_profiles` — name, species, role, age_band, personality, backstory, goals, fears, speech_style, portrait_url, status
- `character_visual_bibles` — canonical_description, face/hair/body/clothing, color_palette, accessories, style_lock, do_not_change_rules, negative_constraints
- `character_memory_logs` — per-episode: event_summary, emotion_state, goal_state, relationship_changes, open_loops, resolved_loops
- `character_safety_profiles` — is_user_uploaded_likeness, consent_status, is_minor_like, disallowed_transformations, copyright_risk_flags

### Safety Layer (3-Tier)
- **Tier 1**: 100+ blocked IP names (Disney, Marvel, DC, Anime, Nintendo, etc.)
- **Tier 2**: Regex patterns for similarity phrases ("like Batman", "similar to Elsa", "Marvel style hero")
- **Tier 3**: Celebrity/real-person detection ("looks like [Name]", "resembles [Name]")

### Prompt Package (5-Block Generation Contract)
```json
{
  "identity_block": { "name", "role", "personality", "goals", "fears", "speech_style" },
  "visual_lock_block": { "canonical_description", "do_not_change_rules", "style_lock" },
  "memory_block": { "recent_events", "current_emotion", "open_loops", "relationship_changes" },
  "scene_block": "scene context",
  "negative_constraints": ["no character redesign", "no copyrighted resemblance", ...]
}
```

### Pipeline Integration
- `plan-episode` loads attached characters and injects prompt packages into LLM context
- `generate-episode` enriches scene visual_prompts with character visual locks
- `_update_memory_internal` writes character memory after episode reaches READY

### Frontend (3 Pages + Integration)
- `/app/characters` — Character Library (grid of cards)
- `/app/characters/create` — 4-step Creator wizard (Identity -> Personality -> Appearance -> Review)
- `/app/characters/:id` — Character Detail (portrait, identity, visual bible, safety, memory timeline)
- SeriesTimeline sidebar — Attached characters zone with chips, Attach button, picker
- Dashboard "More Tools" — Character Memory card

## Story Series Engine — 15 API Endpoints
(Unchanged from previous — see full list in previous PRD version)

## Monetization Engine
- **4-tier pricing**: Free / Creator ($5.99) / Pro ($11.99) / Elite ($23.99)
- **Paywall enforcement**: 403 on limits, UpgradeModal in frontend

## Testing History
- Iteration 311: Story Series Phase 1 — 37/37 (100%)
- Iteration 312: Phase 2+3 + CTA A/B + UI — 53/53 (100%)
- Iteration 313: Pricing & Compulsion Engine — 45/45 (100%)
- Iteration 314: AI Suggestions + Cover Image — 24/25 (100%)
- Iteration 315: AI Character Memory — 23/23 backend + 100% frontend (100%)
- Ken Burns Motion: 6/6 FFmpeg zoompan patterns (pixel-verified)

## Completed Work
1-58. (Previous features — core platform, stability, growth, analytics, story series phases 1-3, pricing engine)
59. Improved AI Suggestions (enriched with chars, world, episodes, memory) - DONE
60. Series Cover Image Generation (gpt-image-1, R2 upload, sidebar display) - DONE
61. Ken Burns Motion E2E Verification (6/6 FFmpeg patterns) - DONE
62. AI Character Memory Phase 1 MVP - DONE
    - character_profiles + character_visual_bibles + character_memory_logs + character_safety_profiles
    - 3-tier safety layer (100+ blocked IPs, similarity regex, celebrity detection)
    - LLM-generated visual bibles with canonical descriptions and locked rules
    - Canonical portrait generation (gpt-image-1)
    - Prompt package builder (5-block generation contract)
    - Story Video pipeline integration (plan-episode + generate-episode + memory write)
    - Character Creator (4-step wizard), Library, Detail pages
    - Series Timeline character attach UI

## Remaining Backlog

### Phase 2 — Character Memory
- [ ] Voice profile entity + TTS integration
- [ ] Relationship graph entity + visualization
- [ ] Continuity validator (post-generation check)
- [ ] Character Library UI enhancements

### Phase 3 — Character Memory
- [ ] Editable visual bibles with live preview
- [ ] Real-person consent workflows
- [ ] Advanced emotional memory
- [ ] Cross-tool character persistence (comic, GIF, storybook pipelines)

### Other
- [ ] Admin Dashboard UI for observability APIs
- [ ] Growth loop: series completion rewards
- [ ] Style preset preview thumbnails for Photo to Comic

### BLOCKED
- [ ] R2 bucket CORS policy (requires manual user config)
- [ ] SendGrid upgrade (requires user plan upgrade)
