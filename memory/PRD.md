# Visionary Suite — PRD

## Product Vision
AI Creative Operating System: **Create -> Share -> View -> Remix**
Every output is a permanent CDN-backed asset. Every creation is a living object, not a one-time result.

### Strategic Principle
> 1 flagship feature, 2 supporting features, everything else secondary.
> Build continuity, not surface area.

## Architecture Principles
1. DB must never claim success before storage confirms success
2. Downloads are permanent CDN assets — no temp expiry
3. Stage-based pipelines — not monolithic jobs
4. Per-panel/per-page retries — never rerun entire job
5. Assets validate before exposing download
6. Every job goes through: idempotency -> guardrails -> admission -> degradation -> queue
7. Partial success is better than total failure — deliver what works, heal the rest
8. Upload-first UX — reduce clicks to conversion
9. Every output is a living object with continue/remix/share — not a dead-end result

## 5-Layer Resilience Architecture (IMPLEMENTED)
- Idempotency (header + body fingerprint)
- Cost Guardrails (per-job, per-user daily, system kill switch)
- Tier-Aware Degradation Matrix (4x3: NORMAL/STRESSED/SEVERE/CRITICAL x free/paid/premium)
- Multi-Queue (premium:5, paid:3, free:1, background:1 concurrency)
- Observability APIs (6 admin endpoints)
- Partial Success Model (thresholds: free=70%, paid=80%, premium=90%)

## Upload Architecture (IMPLEMENTED)
- POST /api/storage/upload — Server-side proxy: browser -> backend -> R2 (no CORS)
- POST /api/storage/presigned-upload — Signed URL for direct browser -> R2 (needs R2 CORS config)
- POST /api/storage/confirm-upload — Validate direct uploads
- Server-side proxy is the primary path (eliminates CORS dependency)
- Generate endpoint accepts storage_key OR photo file

## Storage Lifecycle (IMPLEMENTED)
- Background hourly cleanup of temp uploads > 72h
- Auto-promotion: on job COMPLETED, source upload promoted temp -> permanent
- On FAILED/abandoned, left as temp for lifecycle cleanup

## Story Chain Model (IMPLEMENTED + ENHANCED)
A real relational object, not a stitched scroll:
```
story_chain_id  — shared across all jobs in the chain
root_job_id     — the original job that started the chain
parent_job_id   — direct parent (null for originals)
branch_type     — "original" | "continuation" | "remix"
sequence_number — order within the chain (0 for original)
```
### Progression System (NEW - March 2026)
- GET /api/photo-to-comic/chain/{chain_id} — enhanced with progress_pct, total_panels, latest_continuable_job_id
- GET /api/photo-to-comic/active-chains — top 3 active chains for "Resume Your Story" dashboard entry point
- POST /api/photo-to-comic/chain/suggestions — AI-generated context-aware "Next Episode" suggestions
- GET /api/photo-to-comic/my-chains — enhanced with progress_pct
- Frontend: "Resume Your Story" component on Dashboard (primary chain card + secondary compact cards)
- Frontend: StoryChainView with progression header, progress bar, episode/panel counts, AI suggestions panel
- Frontend: MyStories with progress bars on chain cards
- Frontend: PhotoToComic post-gen panel with direction options (Continue/Twist/Escalate/Custom)

## Photo to Comic (REBUILT - Conversion + Retention)
- Upload-first hero: full-width drop zone as primary CTA
- Single-screen builder: photo preview + mode + style + cost sidebar
- 12 visual style presets with gradient color cards
- Server-side upload with progress indicator + CDN ready badge
- Post-generation action panel:
  - Download, Share (copy/twitter/whatsapp)
  - Continue Story with multiple directions (Next/Twist/Escalate/Custom prompt)
  - Remix (same photo, different style)
  - View Story Chain (navigate to chain timeline)
  - Create New
- POST /api/photo-to-comic/continue-story (inherits chain)
- POST /api/photo-to-comic/remix/{job_id} (returns config for pre-fill)

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
11. 5-Layer Resilience Architecture
12. Photo to Comic UX REBUILT — upload-first builder
13. Direct-to-storage signed URL uploads
14. Storage lifecycle — temp asset cleanup
15. Post-generation experience — action panel, continue story, remix, share
16. Storage auto-promotion — temp->permanent on job success
17. Server-side upload proxy (eliminates CORS dependency)
18. Story Chain model — relational story objects with tree structure
19. Story Chain Progression System — resume entry points, progress indicators, AI suggestions, direction-based continuation

## Remaining Backlog
### P0
- [ ] Configure R2 bucket CORS via Cloudflare dashboard (enables direct PUT uploads)

### P1
- [ ] Story Video post-gen experience (continue/remix/share parity with Photo to Comic)
- [ ] Story Video chain model (reuse same pattern)

### P2
- [ ] Style preset preview thumbnails
- [ ] BYO API mode
- [ ] Creator Challenges
- [ ] Cashfree payments (live)
- [ ] Email Notifications (BLOCKED — SendGrid)
- [ ] Instant Preview Mode, Export Packs
- [ ] Frontend admin dashboard for observability
