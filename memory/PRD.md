# Photo to Comic — AI Creator Suite PRD

## Original Problem Statement
Build a "Smart Repair Pipeline" for an AI creator suite (Photo to Comic). Highest priority: Failure Masking — users must NEVER see raw failures. If generation fails completely, deterministic fallback filter (Guaranteed Output) ensures the user always gets a comic.

## Current Status: P0 FIX — PENDING USER VERIFICATION
- P0 style-distinctness bug: FIXED with complete guaranteed_output rewrite
- 8 dedicated style renderers replacing 3 shared generic filters
- Hard logging added for full style traceability
- Debug audit endpoint created for ongoing verification
- Development remains FROZEN after this fix is verified

## What's Been Implemented
- Phase 1 & 2 Pipelines fully tested (190+ pytest tests)
- Real cross-panel continuity wired (approved panels fed to LLM as context)
- Multi-tier fallback system ending in deterministic guaranteed_output.py (Pillow-based)
- Frontend scrubbed of all failure dead-end UI states
- **P0 Style-Distinctness Fix v2 (Apr 2026):**
  - 8 unique renderers: bold_hero, cartoon, retro_pop, manga, noir, sketch, neon, pastel
  - Each produces radically different visual output
  - Color profiles verified: brightness ranges from 15 (neon) to 200 (pastel)
  - 26/26 tests passing, debug endpoint returns PASS
  - Hard [STYLE_TRACE] logging at 4 pipeline points
  - One-click remix (auto-generates without going back to builder)
  - Null dialogue filter (no more literal "null" text in panels)
  - Stronger AI style prompts with anti-photorealism instructions

## Style Renderer Map
| Style | Renderer | Visual Treatment |
|-------|----------|-----------------|
| bold_superhero | _render_bold_hero | Saturated, posterized, black outlines |
| cartoon_fun | _render_cartoon | Smooth, bright, flat colors |
| soft_manga | _render_manga | Grayscale, screen tones, ink lines |
| noir_comic | _render_noir | Hard B&W threshold, dramatic shadows |
| retro_action | _render_retro_pop | Wild color shift, pixelated halftone |
| scifi_neon | _render_neon | Dark base, glowing neon edges |
| dreamy_pastel | _render_pastel | Soft, desaturated, color wash |
| sketch_outline | _render_sketch | Pencil sketch, tinted lines |

## Production Observation Metrics (To Monitor When Traffic Arrives)
1. Guaranteed output rate (should decrease as AI improves)
2. Style-specific failure rates
3. Fallback tier usage by style
4. Dead-end screen rate (must be 0%)
5. Comic completion success rate
6. Latency by tier and style
7. User retry rate after output
8. Download/share/open rates
9. Credits charged vs credits waived
10. Low-quality output frequency

## Frozen/Paused Tasks (DO NOT START)
- Admin routing config editor
- Smart Repair self-tuning router
- Dynamic style popularity badges
- Photo to Comic: Instagram export, WhatsApp share card, GIF teasers
- Bedtime Stories (TTS, Image Gen)

## Architecture
- Backend: FastAPI + MongoDB
- Frontend: React
- Pipeline: /app/backend/services/comic_pipeline/
- Key files: guaranteed_output.py (8 renderers), panel_orchestrator.py, job_orchestrator.py
- Routes: /app/backend/routes/photo_to_comic.py
- Frontend: /app/frontend/src/pages/PhotoToComic.js

## 3rd Party Integrations
- OpenAI & Gemini (Emergent LLM Key)
- Cloudflare R2 (Object Storage)
- Cashfree (Payments)

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
