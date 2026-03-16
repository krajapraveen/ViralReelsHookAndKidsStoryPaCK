# Visionary Suite — PRD

## Pipeline Architecture
```
Prompt → Admission Controller → Credit Reserve → Queue (Priority) → Workers
              ↓                                        ↓
     Check: concurrency,                     Stage 1: Scenes (LLM)
     queue depth, plan                              ↓
              ↓                        Stage 2: Images + Voices (PARALLEL)
     ADMIT / REJECT / QUEUE                    ↓ (direct litellm bypass)
                                        Stage 3: Package + Export
```

### Performance History
| Version | Total Time | Key Change |
|---------|-----------|------------|
| v1 (sequential, wrapper) | ~79s | baseline |
| v2 (parallel, wrapper) | ~69s | images+voices parallel |
| **v3 (parallel, direct bypass, size=1024x1024)** | **~65s** | **litellm direct, explicit size** |

### Per-Image Benchmark
| Config | Time per image | vs baseline |
|--------|---------------|-------------|
| No size param (wrapper) | 16.8s | baseline |
| **size=1024x1024 (direct)** | **13.8s** | **-18%** |
| size=auto | 16.6s | ~same |
| medium quality | 22.4s | +33% slower |

### Admission Controller
| Check | Behavior |
|-------|----------|
| Free concurrency (1) | REJECT with clear message |
| Paid concurrency (3) | REJECT with wait message |
| Premium concurrency (5) | REJECT with wait message |
| Queue depth ≥ 20 (free) | REJECT with retry timer |
| Queue depth ≥ 20 (paid) | QUEUE with ETA |
| Queue depth ≥ 20 (premium) | ADMIT immediately |

### Plan Controls
| Plan | Scenes | Priority | Watermark | Concurrent | Image |
|------|--------|----------|-----------|------------|-------|
| Free | 3 | Low | Yes | 1 | 1024, low quality |
| Paid | 4 | Medium | No | 3 | 1024, low quality |
| Premium | 6 | High | No | 5 | 1024, low quality |

## Distribution Loop (LIVE)
Public pages, explore, creator profiles, OG tags, sitemap, share buttons, remix, watermark. 134+ creations seeded.

## Completed (All Sessions)
1. Design system, homepage, dashboard, Story Video Pipeline
2. Distribution loop (explore, public pages, remix, share, OG tags, sitemap)
3. Content Seeding Phase A (40 videos), Creator Profiles, Growth Dashboard
4. Plan-based scene limits, credit reservation, scene caching
5. Parallel image+voice execution
6. Streaming first asset, estimated time remaining
7. Admission controller + per-user concurrency limits
8. **Direct litellm image bypass** — 18% faster per image, 17% faster total pipeline

## Remaining Backlog
### P0
- [ ] Content Seeding Phase B+C (80 more → 120 total)
- [ ] Graceful degradation under load (fewer scenes/lower quality when stressed)

### P1
- [ ] Direct-to-storage uploads via signed URLs
- [ ] Storage lifecycle (auto-delete temp assets after 72h)

### P2
- [ ] BYO API / BYO Cloud mode
- [ ] Creator Challenges, Cashfree payments
- [ ] Email Notifications (BLOCKED — SendGrid)
