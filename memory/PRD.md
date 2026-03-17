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

## Pipeline Architecture
```
Comic Story Book (8-stage pipeline):
  stage_1: story_outline       → story_json persisted to DB
  stage_2: page_plan           → page structure persisted
  stage_3: panel_prompts       → prompts persisted (resumable)
  stage_4: image_generation    → per-page retries (up to 3x each)
  stage_5: page_assembly       → assembled pages
  stage_6: export_creation     → actual PDF via reportlab
  stage_7: storage_upload      → R2 upload + HEAD validation
  stage_8: asset_registration  → user_assets DB records (status=ready)

Story Video Pipeline (parallel):
  admission → credit reserve → scenes(LLM) → images+voices(parallel) → package → R2
```

### Download Architecture (FIXED)
```
Generation → Upload to R2 → HEAD validate → Register in user_assets → Mark downloadable
```
- **user_assets** collection: asset_id, user_id, job_id, cdn_url, status=ready, is_downloadable=true, permanent=true
- My Downloads reads ONLY from user_assets with status=ready
- No 5-minute/30-minute expiry. No countdown. No temp files.
- DownloadWithExpiry → PermanentDownload (backwards compatible)

### Graceful Degradation
| Load Level | Free | Paid | Premium |
|-----------|------|------|---------|
| NORMAL | Full | Full | Full |
| STRESSED | 2 scenes | Full | Full |
| SEVERE | PAUSED | 3 scenes | Full |
| CRITICAL | PAUSED | PAUSED | Full |

## Data Model
- **comic_storybook_v2_jobs**: id, userId, status, current_stage, pages, pdfUrl, coverUrl, permanent, assets[]
- **job_stage_runs**: job_id, stage_name, status, attempt_count, started_at, finished_at, error_message
- **user_assets**: asset_id, user_id, job_id, asset_type, cdn_url, status, is_downloadable, permanent
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

## Remaining Backlog
### P0
- [ ] Photo to Comic UX improvements (hero section, upload-first, style presets)

### P1
- [ ] Direct-to-storage uploads via signed URLs
- [ ] Storage lifecycle (auto-delete temp intermediates after 72h)

### P2
- [ ] BYO API mode
- [ ] Creator Challenges
- [ ] Cashfree payments (live)
- [ ] Email Notifications (BLOCKED — SendGrid)
