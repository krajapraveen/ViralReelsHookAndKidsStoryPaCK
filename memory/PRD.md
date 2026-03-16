# Visionary Suite — PRD (Product Requirements Document)

## Product Vision
Visionary Suite is an **AI Creative Operating System** — a creator network: **Create → Share → View → Remix → Create**.

## Pipeline Architecture
```
User Prompt → Admission Controller → Credit Reserve → Queue (Priority) → Workers
                    ↓                                         ↓
            Check: concurrency,                     Stage 1: Scenes (LLM)
            queue depth, plan                              ↓
                    ↓                          Stage 2: Images + Voices (PARALLEL)
            ADMIT / REJECT / QUEUE                         ↓
                                                Stage 3: Package + Export
```

### Admission Controller (LIVE)
| Check | Behavior |
|-------|----------|
| User concurrency | Free=1, Paid=3, Premium=5, Admin=10 |
| Queue depth ≥ 20 | Free: REJECT with retry message. Paid: queue with ETA. Premium: admit. |
| Active workers ≥ 10 | Same as above |

### Performance Metrics
| Metric | Value |
|--------|-------|
| Total pipeline (3 scenes, parallel) | ~69s |
| Scenes | ~8s |
| Images + Voices (parallel) | ~59s |
| Image generation | 57s (82% of total — **bottleneck**) |

### Image Latency Investigation Results
- `quality="low"` already used (fastest option)
- `size` parameter exists in litellm but NOT exposed by emergentintegrations wrapper
- GPT-Image-1 supports: 1024x1024, 1024x1536, 1536x1024, auto
- **Path forward**: Either fork wrapper to add size param, or call litellm directly

### Plan-Based Controls
| Plan | Scenes | Queue Priority | Watermark | Concurrent Jobs |
|------|--------|---------------|-----------|----------------|
| Free | 3 | Low (10) | Yes | 1 |
| Starter/Monthly | 4 | Medium (1) | No | 3 |
| Pro/Premium | 6 | Medium (1) | No | 5 |
| Admin | 6 | High (0) | No | 10 |

### Credit System
- Reserve on job start → Finalize on success → Refund on failure

## Distribution Loop (LIVE)
- Public pages `/v/{slug}` with OG meta tags, social share buttons, prompt display
- Explore gallery `/explore` with 134+ creations
- Creator profiles `/creator/{username}`
- Sitemap, Growth Dashboard, Watermark

## Completed (All Sessions)
1. Global design system, homepage, dashboard
2. Story Video Pipeline (multi-stage, durable)
3. Distribution loop (explore, public pages, remix, share, OG tags)
4. Content Seeding Phase A (40 videos)
5. Plan-based scene limits + credit reservation + scene caching
6. Parallel image+voice execution (saves ~10s per job)
7. Streaming first asset to UI + estimated time remaining
8. **Admission controller** — pre-job gate with concurrency checks
9. **Per-user concurrency limits** — Free=1, Paid=3, Premium=5, Admin=10
10. **System status endpoint** — queue depth, active workers, user slots

## Remaining Backlog
### P0
- [ ] Image latency optimization (bypass wrapper for size control OR faster model)
- [ ] Content Seeding Phase B+C (80 more → 120 total)

### P1
- [ ] Graceful degradation under load (fewer scenes/lower quality for free users)
- [ ] Direct-to-storage uploads via signed URLs
- [ ] Storage lifecycle (auto-delete temp assets after 72h)

### P2
- [ ] BYO API / BYO Cloud mode
- [ ] Creator Challenges, Cashfree payments
- [ ] Email Notifications (BLOCKED — SendGrid)
