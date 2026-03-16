# Visionary Suite — PRD (Product Requirements Document)

## Product Vision
Visionary Suite is an **AI Creative Operating System** — a creator network centered around the growth loop: **Create → Share → View → Remix → Create**.

## Pipeline Architecture (Optimized)
```
User Prompt → API Gateway → Job Create (credit reservation) → Queue (priority) → Workers
                                                                    ↓
                                                            Stage 1: Scenes (LLM)
                                                                    ↓
                                                       Stage 2: Images + Voices (PARALLEL)
                                                                    ↓
                                                            Stage 3: Package + Export
```

### Performance Metrics
| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Total pipeline (3 scenes) | 79s | 69s | -13% |
| Parallel stage (images+voices) | 70s (sequential) | 59s (parallel) | -16% |
| Voices tail time | +13s | 0s (overlapped) | -100% |
| Scene cache hit | N/A | saves ~7s | New |

### Plan-Based Controls
| Plan | Max Scenes | Queue Priority | Watermark |
|------|-----------|---------------|-----------|
| Free | 3 | Low (10) | Yes |
| Starter/Monthly | 4 | Medium (1) | No |
| Pro/Premium | 6 | Medium (1) | No |

### Credit System
- Reserve on job start → Finalize on success → Refund on failure
- Small (≤3): 10 credits, Medium (4-6): 15, Large (7+): 20

## Distribution Loop (LIVE)
- Public pages `/v/{slug}` with OG meta tags, social share buttons
- Explore gallery `/explore` with 134+ creations
- Creator profiles `/creator/{username}`
- Sitemap `/api/public/sitemap.xml`
- Admin Growth Dashboard `/app/admin/growth`
- Content seeded: 40 videos (Phase A), system creator "Visionary AI"

## Completed (All Sessions)
1. Global design system, homepage, dashboard
2. Story Video Pipeline (multi-stage, durable)
3. Distribution loop (explore, public pages, remix, share, OG tags)
4. Content Seeding Phase A (40 videos)
5. Plan-based scene limits (free=3, paid=4, premium=6)
6. Credit reservation model
7. Scene caching for prompt reuse
8. **Parallel image+voice execution** (saves ~10s per job)
9. **Streaming first asset to UI** (reduces perceived wait)
10. **Estimated time remaining** display
11. Creator Profiles, Sitemap, Social Share Buttons

## Remaining Backlog
### P0
- [ ] Content Seeding Phase B+C (80 more → 120 total)

### P1
- [ ] Admission controller (queue depth check before job start)
- [ ] Per-user concurrency limits (free=1, paid=3, premium=5)
- [ ] Graceful degradation under load

### P2
- [ ] BYO API / BYO Cloud mode
- [ ] Storage lifecycle (auto-delete temp assets after 72h)
- [ ] Direct-to-storage uploads via signed URLs
- [ ] Creator Challenges, Cashfree payments
- [ ] Email Notifications (BLOCKED — SendGrid)
