# Visionary Suite — PRD

## Product Vision
AI Creative Operating System: **Create → Share → View → Remix**
Every output is a permanent CDN-backed asset.

### Strategic Principle
> 1 flagship feature, 2 supporting features, everything else secondary.
> Stop adding surface area. Deepen what exists.

## Architecture Principles
1. **DB must never claim success before storage confirms success**
2. **Downloads are permanent CDN assets — no temp expiry**
3. **Stage-based pipelines — not monolithic jobs**
4. **Per-panel/per-page retries — never rerun entire job**
5. **Assets validate before exposing download**
6. **Every job goes through: idempotency → guardrails → admission → degradation → queue**
7. **Partial success is better than total failure — deliver what works, heal the rest**
8. **Upload-first UX — reduce clicks to conversion**

## Pipeline Architecture
```
Comic Story Book (8-stage pipeline):
  Admission: idempotency → cost_guardrails → admission_controller → degradation_matrix → queue_placement
  stage_1: story_outline → story_json persisted to DB
  stage_2: page_plan → page structure persisted
  stage_3: panel_prompts → prompts persisted (resumable)
  stage_4: image_generation → per-page retries (tier-aware max)
  stage_5: page_assembly → assembled pages
  stage_6: export_creation → actual PDF via reportlab
  stage_7: storage_upload → R2 upload + HEAD validation
  stage_8: asset_registration → user_assets DB records (status=ready)
  Post-pipeline: if partial success → queue background regeneration

Story Video Pipeline: admission → credit reserve → scenes(LLM) → images+voices(parallel) → package → R2
```

## 5-Layer Resilience Architecture (IMPLEMENTED)

### Layer 1: Idempotency
- Idempotency-Key header + body fingerprint fallback (SHA256)
- Cached results for duplicates (409 pending, cached result for completed)

### Layer 2: Cost Guardrails
- Per-job/per-user daily/system-wide kill switch
- Admin API to adjust thresholds

### Layer 3: Tier-Aware Degradation Matrix
```
NORMAL:    free=20pg/1retry  paid=20pg/2retry  premium=30pg/3retry
STRESSED:  free=10pg/1retry  paid=20pg/2retry  premium=30pg/3retry
SEVERE:    free=BLOCKED       paid=10pg/1retry  premium=20pg/2retry
CRITICAL:  free=BLOCKED       paid=BLOCKED       premium=10pg/1retry
```

### Layer 4: Multi-Queue Architecture
- 4 queues: premium(5), paid(3), free(1), background(1) concurrency
- DB-backed queue recovery on restart
- Background queue for panel regeneration

### Layer 5: Observability APIs
- queue-status, pipeline-health, cost-summary, guardrail-state, kill-switch, replay-job

### Partial Success Model
- Thresholds: free=70%, paid=80%, premium=90%
- PARTIAL_COMPLETE → deliver what works → background regeneration

## Direct-to-Storage Uploads (IMPLEMENTED)
- `POST /api/storage/presigned-upload` — Signed URL for browser → R2 direct upload
- `POST /api/storage/confirm-upload` — Validate upload completion
- Bypasses backend for large files, 15MB limit

## Storage Lifecycle (IMPLEMENTED)
- `POST /api/storage/cleanup-temp` — Admin trigger
- Background task (hourly) cleans up temp uploads > 72h old
- Tracks pending_uploads collection with is_temp flag

## Photo to Comic UX (REBUILT - Conversion-Focused)
- **Upload-first hero**: Full-width drop zone as primary CTA
- **Single-screen builder**: Photo preview + mode toggle + style grid + cost sidebar
- **12 visual style presets** with gradient color cards (no emojis)
- **Compact strip options**: Genre pills, panel count buttons, story prompt
- **Sticky cost sidebar** with dynamic total, HD toggle, generate CTA
- Reduced from 3-5 steps to 1 screen (upload → configure → generate)
- 1573 lines → 370 lines

## Completed (All Sessions)
1. Design system, homepage, dashboard, Story Video Pipeline
2. Distribution loop (explore, public pages, remix, share, OG tags, sitemap)
3. Content Seeding (120 videos, 3 waves, 6 categories)
4. Plan-based scene limits, credit reservation, scene caching
5. Parallel execution, direct litellm bypass
6. Admission controller + graceful degradation (4 tiers)
7. Creator Profile pages, Trending This Week carousel, Live Creations Feed
8. Download architecture fix — permanent CDN assets, user_assets collection
9. Comic Story Book REBUILT — 8-stage pipeline, per-page retries, R2 upload
10. My Downloads REBUILT — permanent assets only, no expiry
11. 5-Layer Resilience Architecture (Feb 2026)
12. Photo to Comic UX REBUILT — upload-first, single-screen builder (Feb 2026)
13. Direct-to-storage signed URL uploads (Feb 2026)
14. Storage lifecycle — temp asset cleanup (Feb 2026)

## Remaining Backlog
### P0
- [ ] Frontend admin dashboard for observability (minimal — API endpoints exist)

### P1
- [ ] Integrate signed URL upload into Photo to Comic flow (currently still uploads through backend)
- [ ] Storage lifecycle auto-promote: mark confirmed uploads as permanent when linked to completed jobs

### P2
- [ ] BYO API mode
- [ ] Creator Challenges
- [ ] Cashfree payments (live)
- [ ] Email Notifications (BLOCKED — SendGrid)
- [ ] Instant Preview Mode, Remix, Export Packs
