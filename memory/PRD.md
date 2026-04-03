# Photo to Comic — AI Creator Suite PRD

## Original Problem Statement
Build a "Smart Repair Pipeline" for an AI creator suite (Photo to Comic). Highest priority: Failure Masking — users must NEVER see raw failures. If generation fails, deterministic fallback (Guaranteed Output) ensures the user always gets a comic.

## Current Status: P0 FIX v3 — PENDING USER VERIFICATION
- Fixed dead-end screen: Guaranteed output panels now persisted IMMEDIATELY to DB
- Fixed fake success: FAILED status now shows truthful "Generation Issue" text
- Fixed style distinctness: 8 dedicated style renderers (not 3 shared filters)
- Fixed one-click remix, null dialogue, download state
- Hard [STYLE_TRACE] logging at 5 pipeline points
- Debug audit endpoint at POST /api/photo-to-comic/debug/style-audit

## Root Causes Found & Fixed (Apr 2026)

### RC1: Panel Persistence Bug (Dead-End Screen)
- Guaranteed output panels generated+uploaded to R2 but DB save was at END of function
- Any downstream exception (quality scoring etc) triggered outer exception handler
- Outer handler set status=FAILED without saving panels → panels lost
- **Fix:** Panels saved to DB IMMEDIATELY after generation, before quality scoring
- **Fix:** Outer handler checks for existing guaranteed_output before overwriting

### RC2: Frontend Lying About Failures
- STATUS_CONFIG.FAILED said "Your Comic is Ready" — fake success
- Dead-end screen said "We're improving your comic" — misleading
- **Fix:** FAILED shows "Generation Issue" with actionable retry
- **Fix:** Dead-end shows truthful messaging + retry/change photo buttons

### RC3: Style Filters Not Distinct (Previous Fix)
- 3 shared generic filters rotated by panel index
- Multiple styles shared same filter → identical output
- **Fix:** 8 dedicated renderers: bold_hero, cartoon, retro_pop, manga, noir, sketch, neon, pastel

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

## Logging Points
- [STYLE_TRACE] JOB_START: requested_style, resolved_style, photo_hash
- [STYLE_TRACE] PANEL_DONE: style, status, model_tier, imageUrl
- [STYLE_TRACE] GUARANTEED_OUTPUT_ACTIVATED: style, reason, panel counts
- [STYLE_TRACE] GUARANTEED_OUTPUT_DONE: style, panel URLs
- [STYLE_TRACE] GUARANTEED_PANELS_PERSISTED: panels saved to DB

## Frozen/Paused Tasks (DO NOT START)
- Admin routing config editor
- Smart Repair self-tuning router
- Dynamic style popularity badges
- Photo to Comic: Instagram export, WhatsApp share card, GIF teasers
- Bedtime Stories (TTS, Image Gen)

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
