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

## Pipeline Architecture
```
Comic Story Book (8-stage pipeline):
  Admission: idempotency → cost_guardrails → admission_controller → degradation_matrix → queue_placement
  stage_1: story_outline       → story_json persisted to DB
  stage_2: page_plan           → page structure persisted
  stage_3: panel_prompts       → prompts persisted (resumable)
  stage_4: image_generation    → per-page retries (tier-aware max)
  stage_5: page_assembly       → assembled pages
  stage_6: export_creation     → actual PDF via reportlab
  stage_7: storage_upload      → R2 upload + HEAD validation
  stage_8: asset_registration  → user_assets DB records (status=ready)

  Post-pipeline: if partial success → queue background regeneration

Story Video Pipeline (parallel):
  admission → credit reserve → scenes(LLM) → images+voices(parallel) → package → R2
```

## 5-Layer Resilience Architecture (IMPLEMENTED)

### Layer 1: Idempotency
- Idempotency-Key header support
- Body fingerprint fallback (SHA256 of user_id + genre + title + storyIdea + pageCount)
- Cached results returned for duplicate requests (409 for pending, cached result for completed)

### Layer 2: Cost Guardrails
- Per-job limits (max pages/retries per plan)
- Per-user daily limits (max jobs/cost per day per plan)
- System-wide kill switch (daily cost ceiling, severe threshold)
- Admin API to adjust kill switch thresholds

### Layer 3: Tier-Aware Degradation Matrix
```
NORMAL:    free=20pg/1retry  paid=20pg/2retry  premium=30pg/3retry
STRESSED:  free=10pg/1retry  paid=20pg/2retry  premium=30pg/3retry
SEVERE:    free=BLOCKED       paid=10pg/1retry  premium=20pg/2retry
CRITICAL:  free=BLOCKED       paid=BLOCKED       premium=10pg/1retry
```

### Layer 4: Multi-Queue Architecture
- 4 queues: premium(5), paid(3), free(1), background(1) concurrency
- Workers pull from highest-priority non-empty queue first
- DB-backed: queue recovery from DB on restart
- Background queue handles panel regeneration at lowest priority

### Layer 5: Observability APIs
- GET /api/observability/queue-status
- GET /api/observability/pipeline-health
- GET /api/observability/cost-summary
- GET /api/observability/guardrail-state
- POST /api/observability/kill-switch
- POST /api/observability/replay-job (modes: full, failed_stage, failed_panels)

### Partial Success Model
- Configurable thresholds: free=70%, paid=80%, premium=90%
- Jobs exceeding threshold → PARTIAL_COMPLETE → deliver what works
- Failed panels → queued for background regeneration automatically

### Download Architecture (FIXED)
```
Generation → Upload to R2 → HEAD validate → Register in user_assets → Mark downloadable
```

## Data Model
- **comic_storybook_v2_jobs**: id, userId, status, current_stage, pages, pdfUrl, coverUrl, permanent, assets[], queue_name, load_level, max_retries, tier, idempotency_key, failed_panels[], success_ratio
- **job_stage_runs**: job_id, stage_name, status, attempt_count, started_at, finished_at, error_message
- **user_assets**: asset_id, user_id, job_id, asset_type, cdn_url, status, is_downloadable, permanent
- **idempotency_keys**: key, status, result, createdAt, expiresAt
- **pipeline_jobs**: (story videos) with admission control + degradation

## Completed (All Sessions)
1. Design system, homepage, dashboard, Story Video Pipeline
2. Distribution loop (explore, public pages, remix, share, OG tags, sitemap)
3. Content Seeding (120 videos, 3 waves, 6 categories)
4. Plan-based scene limits, credit reservation, scene caching
5. Parallel execution, direct litellm bypass
6. Admission controller + graceful degradation (4 tiers)
7. Creator Profile pages, Trending This Week carousel, Live Creations Feed
8. **Download architecture fix** — permanent CDN assets, user_assets collection
9. **Comic Story Book REBUILT** — 8-stage pipeline, per-page retries, R2 upload, PDF via reportlab
10. **My Downloads REBUILT** — permanent assets only, no expiry, validated CDN URLs
11. **5-Layer Resilience Architecture** — idempotency, cost guardrails, admission+degradation, multi-queue, observability APIs, replay, partial success model, background regeneration (Feb 2026)

## Remaining Backlog
### P0
- [ ] Frontend admin dashboard for observability (UI for the existing APIs)

### P1
- [ ] Photo to Comic UX improvements (hero section, upload-first, style presets)
- [ ] Direct-to-storage uploads via signed URLs
- [ ] Storage lifecycle (auto-delete temp intermediates after 72h)

### P2
- [ ] BYO API mode
- [ ] Creator Challenges
- [ ] Cashfree payments (live)
- [ ] Email Notifications (BLOCKED — SendGrid)
- [ ] Instant Preview Mode, Remix, Export Packs
