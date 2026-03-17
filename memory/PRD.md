# Visionary Suite — PRD

## Product Vision
AI Creative Operating System: **Create -> Share -> View -> Remix**
Every output is a permanent CDN-backed asset.

### Strategic Principle
> 1 flagship feature, 2 supporting features, everything else secondary.
> Stop adding surface area. Deepen what exists.

## Architecture Principles
1. DB must never claim success before storage confirms success
2. Downloads are permanent CDN assets — no temp expiry
3. Stage-based pipelines — not monolithic jobs
4. Per-panel/per-page retries — never rerun entire job
5. Assets validate before exposing download
6. Every job goes through: idempotency -> guardrails -> admission -> degradation -> queue
7. Partial success is better than total failure — deliver what works, heal the rest
8. Upload-first UX — reduce clicks to conversion

## 5-Layer Resilience Architecture (IMPLEMENTED)
- Idempotency (header + body fingerprint)
- Cost Guardrails (per-job, per-user daily, system kill switch)
- Tier-Aware Degradation Matrix (4x3: NORMAL/STRESSED/SEVERE/CRITICAL x free/paid/premium)
- Multi-Queue (premium:5, paid:3, free:1, background:1 concurrency)
- Observability APIs (6 admin endpoints)
- Partial Success Model (thresholds: free=70%, paid=80%, premium=90%)

## Direct-to-Storage Uploads (IMPLEMENTED)
- POST /api/storage/presigned-upload -> signed URL for browser -> R2
- POST /api/storage/confirm-upload -> validate completion
- Graceful fallback: if direct PUT fails (CORS), frontend silently uses FormData through backend
- R2 CORS requires Cloudflare dashboard config (bucket admin access needed)

## Storage Lifecycle (IMPLEMENTED)
- Background hourly cleanup of temp uploads > 72h
- POST /api/storage/cleanup-temp (admin)
- Auto-promotion: on job COMPLETED, source upload promoted from temp to permanent
- On job FAILED/abandoned, temp uploads left for lifecycle cleanup

## Photo to Comic (REBUILT - Conversion-Focused)
- Upload-first hero: full-width drop zone as primary CTA
- Single-screen builder: photo preview + mode + style + cost sidebar
- 12 visual style presets with gradient color cards
- Signed URL upload with CDN-ready badge + silent fallback
- Generate endpoint accepts either photo file OR storage_key

## Post-Generation Experience (IMPLEMENTED)
- Rich action panel: Download, Share (copy/twitter/whatsapp), Continue Story, Remix, Create New
- Continue Story: generates 4 more panels continuing where strip left off (POST /api/photo-to-comic/continue-story)
- Remix: pre-fills builder with same photo + different style (POST /api/photo-to-comic/remix/{id})
- Share-ready: copy link, Twitter share, WhatsApp share with generated URL
- Goal: convert one-time users into repeat creators

## Key API Endpoints
- POST /api/v2/comic-storybook/create (resilience pipeline)
- POST /api/photo-to-comic/generate (accepts photo OR storage_key)
- POST /api/photo-to-comic/continue-story
- POST /api/photo-to-comic/remix/{job_id}
- POST /api/storage/presigned-upload
- POST /api/storage/confirm-upload
- GET /api/observability/queue-status, pipeline-health, cost-summary, guardrail-state
- POST /api/observability/kill-switch, replay-job

## Completed (All Sessions)
1. Design system, homepage, dashboard, Story Video Pipeline
2. Distribution loop (explore, public pages, remix, share, OG tags, sitemap)
3. Content Seeding (120 videos)
4. Plan-based scene limits, credit reservation, scene caching
5. Parallel execution, direct litellm bypass
6. Admission controller + graceful degradation (4 tiers)
7. Creator Profile pages, Trending This Week, Live Creations Feed
8. Download architecture fix — permanent CDN assets
9. Comic Story Book REBUILT — 8-stage pipeline
10. My Downloads REBUILT — permanent assets only
11. 5-Layer Resilience Architecture (Feb 2026)
12. Photo to Comic UX REBUILT — upload-first builder (Feb 2026)
13. Direct-to-storage signed URL uploads (Feb 2026)
14. Storage lifecycle — temp asset cleanup (Feb 2026)
15. Post-generation experience — action panel, continue story, remix, share (Feb 2026)
16. Storage auto-promotion — temp->permanent on job success (Feb 2026)

## Remaining Backlog
### P0
- [ ] Configure R2 bucket CORS via Cloudflare dashboard (needs admin access)

### P1
- [ ] Photo to Comic: style presets with actual preview thumbnails
- [ ] Story Video post-gen experience (continue/remix/share parity)

### P2
- [ ] BYO API mode
- [ ] Creator Challenges
- [ ] Cashfree payments (live)
- [ ] Email Notifications (BLOCKED — SendGrid)
- [ ] Instant Preview Mode, Export Packs
- [ ] Frontend admin dashboard for observability
