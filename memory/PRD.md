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

## Story Chain Model (IMPLEMENTED + ENHANCED)
A real relational object:
```
story_chain_id, root_job_id, parent_job_id, branch_type (original|continuation|remix), sequence_number
```

### Progression System (March 2026)
- Enhanced chain/{id} with progress_pct, total_panels, latest_continuable_job_id
- GET /active-chains — top 3 with momentum_msg, milestones
- POST /chain/suggestions — AI context-aware suggestions with character refs, scene refs, tone detection, validation, 1h caching

### Re-Engagement System (March 2026 — NEW)
- **Login Interstitial**: Modal on first session visit showing active chain with progress, momentum msg, and direct Continue CTA
- **Action Banner**: Persistent banner with deep-link Continue CTA, 4h resurface after dismiss
- **Active Chains Nav Chip**: "Stories" badge in header nav, opens Resume Drawer with top 3 chains
- **Resume Drawer**: Dropdown showing chains with progress bars, momentum messages, View/Continue CTAs
- **Momentum Messaging**: Milestone targets (5/10/25 episodes), episodes remaining, completion percentage
- **Metrics Instrumentation**: continue_rate, 24h_return_rate, avg_chain_length, suggestion_ctr, resume_from_banner_rate, login_interstitial_rate
- **POST /api/metrics/track**: Lightweight event ingestion
- **GET /api/metrics/reengagement**: Admin-only aggregated metrics dashboard

### Story Video Chain Model (March 2026 — NEW)
- story_projects collection extended with: story_chain_id, root_project_id, parent_project_id, branch_type, sequence_number
- POST /api/story-video-studio/continue-video: Quick Continue — inherits characters, style, chain
- GET /api/story-video-studio/active-video-chains: Resume data for video chains
- GET /api/story-video-studio/video-chain/{chain_id}: Full chain view
- Post-gen panel in StoryVideoPipeline: Quick Continue + Remix buttons

## Photo to Comic (REBUILT)
- Upload-first hero, 12 style presets
- Post-gen action panel: Direction-based continuation (Next/Twist/Escalate/Custom), Remix, Share, View Chain
- POST /api/photo-to-comic/continue-story, POST /api/photo-to-comic/remix/{job_id}

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
20. Re-Engagement System — login interstitial, action banner, nav chip + resume drawer, momentum messaging
21. Metrics Instrumentation — 6 key retention metrics tracked and dashboarded
22. Story Video Chain Model — continuation, chains, post-gen panel with Quick Continue + Remix
23. Context-Aware AI Suggestions — character references, scene continuity, tone detection, validation, caching

## Remaining Backlog
### P0
- [ ] Configure R2 bucket CORS via Cloudflare dashboard (enables direct PUT uploads)

### P1
- [ ] Story Video chain view page (like StoryChainView for comics)
- [ ] Include video chains in "Resume Your Story" / Action Banner

### P2
- [ ] Style preset preview thumbnails
- [ ] BYO API mode
- [ ] Creator Challenges
- [ ] Cashfree payments (live)
- [ ] Email Notifications (BLOCKED — SendGrid)
- [ ] Instant Preview Mode, Export Packs
- [ ] Frontend admin dashboard for observability + metrics
