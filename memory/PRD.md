# AI Creator Suite — PRD

## Core Products
1. **Photo to Comic** — AI comic strip generator with smart repair pipeline
2. **AI Brand Kit Generator** — Multi-format brand identity builder (upgraded from Brand Story Builder)

---

## AI Brand Kit Generator (Phase 1) — COMPLETED Apr 3, 2026

### What was built
Transformed basic template-based Brand Story Builder into a full AI-powered Brand Kit Generator with parallel generation, progressive results, and downloadable deliverables.

### Architecture
- **Backend:** `/app/backend/routes/brand_story_builder.py` + `/app/backend/services/brand_kit/`
- **Frontend:** `/app/frontend/src/pages/BrandStoryBuilder.js`
- **LLM:** GPT-4o-mini via emergentintegrations SDK
- **DB:** MongoDB `brand_kit_jobs` collection

### Modes & Pricing
| Mode | Credits | Artifacts |
|------|---------|-----------|
| Fast | 10 | Short story, Mission/Vision/Values, Taglines, Elevator pitch |
| Pro | 25 | All Fast + Long story, Website hero, Social ad copy, Color palettes, Typography, Logo concepts |
| Premium | 50 | Reserved for Phase 2/3 |

### Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/brand-story-builder/config | GET | Industries, tones, modes |
| /api/brand-story-builder/generate | POST | Create brand kit job |
| /api/brand-story-builder/job/{id} | GET | Poll job status |
| /api/brand-story-builder/job/{id}/result | GET | Full artifact data |
| /api/brand-story-builder/job/{id}/pdf | GET | PDF brand kit download |
| /api/brand-story-builder/job/{id}/zip | GET | ZIP bundle (PDF+TXT+JSON) |

### Features
- Parallel AI generation (all artifacts simultaneously)
- Progressive polling (frontend shows results as they complete)
- Animated generation stages UI
- Tabbed results dashboard (Story, Marketing, Visual Identity)
- Color palette swatches with hex codes
- Taglines grid with style labels
- Website hero copy preview
- Social ad copy (Instagram, Facebook, Google, CTA)
- Logo concept directions
- Typography pairings
- Deterministic fallback for every artifact type
- Copyright protection (blocks trademarked terms)
- PDF + ZIP + TXT download

---

## Photo to Comic — Status
All P0 fixes complete (SDK crash, downloads, continue story, comic book export, null dialogue). See previous PRD entries.

---

## Phase 2 — Brand Kit (UPCOMING)
- AI logo image generation (Gemini visual pipeline)
- Social media creative templates
- Hero banner concepts
- Moodboard images
- Reel script generation

## Phase 3 — Brand Kit (FUTURE)
- Brand intro video (15 sec)
- Multi-language support
- AI brand voice/avatar
- Instagram reel auto-generator

## Frozen Tasks
- Admin routing config editor
- Smart Repair self-tuning router
- Dynamic style popularity badges
- Photo to Comic: Instagram export, WhatsApp share, GIF teasers
- Bedtime Stories (TTS, Image Gen)

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
