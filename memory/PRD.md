# Photo to Comic — AI Creator Suite PRD

## Original Problem Statement
Build a "Smart Repair Pipeline" for an AI creator suite (Photo to Comic). Highest priority: Failure Masking — users must NEVER see raw failures. If generation fails, deterministic fallback (Guaranteed Output) ensures the user always gets a comic.

## Current Status: P0 OUTPUT FLOW FIX — COMPLETED & VERIFIED (Apr 3, 2026)

### What was broken
1. PNG/PDF/Script downloads not working (cross-origin + status gating + R2 presigning)
2. Continue Story / Choose Direction not working (required COMPLETED status, source photo not stored)
3. No Comic Book export
4. "Null" displayed as panel dialogue
5. Inconsistent output states — showing "ready" before deliverables were truly ready

### Root Causes Found & Fixed

#### RC1: Cross-Origin Download (PNG)
- `<a>` tags with external CDN URLs and `download` attribute don't work cross-origin
- **Fix:** Fetch panel images as blob first, create blob URL, then trigger download

#### RC2: Presigned URLs Missing (PDF/Comic Book)
- Backend PDF generator called `requests.get(url)` on raw R2 URLs without presigning
- **Fix:** Presign all R2 URLs before downloading panel images for PDF/book generation

#### RC3: Status Gating Too Strict (Downloads/Continue Story)
- Download, validate-asset, and continue-story endpoints required `status == "COMPLETED"`
- Many valid jobs end as `PARTIAL_READY` or `READY_WITH_WARNINGS`
- **Fix:** Accept all terminal states with valid panels

#### RC4: Source Photo Not Stored (Continue Story)
- Direct file uploads weren't saved to R2, so `source_storage_key` was null
- Continue Story needs the source photo to maintain character consistency
- **Fix:** Upload photo to R2 via `upload_bytes()` during generation and store the key

#### RC5: Null Dialogue Display
- AI returns "Null" (capitalized) as dialogue; frontend check only filtered lowercase 'null'
- **Fix:** Case-insensitive sanitization on both backend (panel_orchestrator) and frontend (sanitizeDialogue helper)

#### RC6: Missing Comic Book Export
- No endpoint existed for comic book generation
- **Fix:** Added GET `/api/photo-to-comic/comic-book/{job_id}` — full PDF with cover, one panel per page with dialogue, script page, back cover

## Previous Fixes (Earlier Sessions)
- Fixed AI Generation SDK crash (broken import path in panel_orchestrator.py)
- Fixed invalid Tier 3/4 model names
- Added worker performance telemetry
- Rewrote guaranteed_output.py with 8 distinct style renderers
- Fixed UnboundLocalError in job_orchestrator
- Fixed DB persistence bug
- Added Error Boundaries and fixed dead-end UI states

## Model Tier Mapping
| Tier | Model | Provider |
|------|-------|----------|
| TIER1_QUALITY | gemini-3-pro-image-preview | gemini |
| TIER2_STABLE_CHARACTER | gemini-3-pro-image-preview | gemini |
| TIER3_DETERMINISTIC | gemini-3.1-flash-image-preview | gemini |
| TIER4_SAFE_DEGRADED | gemini-3.1-flash-image-preview | gemini |

## API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/photo-to-comic/generate | POST | Create comic job |
| /api/photo-to-comic/job/{id} | GET | Poll job status |
| /api/photo-to-comic/download/{id} | POST | Get presigned panel URLs |
| /api/photo-to-comic/pdf/{id} | GET | Download PDF export |
| /api/photo-to-comic/comic-book/{id} | GET | Download full comic book |
| /api/photo-to-comic/script/{id} | GET | Download story script |
| /api/photo-to-comic/continue-story | POST | Continue story from parent job |
| /api/photo-to-comic/validate-asset/{id} | GET | Validate job deliverables |
| /api/photo-to-comic/styles | GET | List available styles |
| /api/photo-to-comic/presets | GET | List story presets |

## Telemetry & Logging
- [WORKER_TELEMETRY] per-panel timing (model_ms, overhead_ms, attempts, fallback)
- [WORKER_STAGE] per-stage details (stage, model, latency_ms, success, error)
- [JOB_TELEMETRY] job-level quality metrics
- [OUTPUT_VALIDATION] comprehensive deliverable audit before final persistence
- [UPLOAD] Photo R2 storage confirmation
- [COMIC_BOOK] Comic book generation metrics
- [DOWNLOAD] Download access log with presigned URL count

## Upcoming Tasks
- (P0) Drive real traffic: 100-200 real jobs, monitor production metrics

## Frozen/Paused Tasks (DO NOT START)
- Admin routing config editor
- Smart Repair self-tuning router
- Dynamic style popularity badges
- Photo to Comic: Instagram export, WhatsApp share card, GIF teasers
- Bedtime Stories (TTS, Image Gen)

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
