# Visionary Suite — PRD

## Pipeline Architecture
```
Prompt → Admission Controller → Credit Reserve → Queue (Priority) → Workers
              ↓                                        ↓
     Check: concurrency,                     Stage 1: Scenes (LLM)
     queue depth, plan,                              ↓
     LOAD LEVEL                        Stage 2: Images + Voices (PARALLEL)
              ↓                        ↓ (direct litellm bypass)
     ADMIT / DEGRADE / REJECT         Stage 3: Package + Export
```

### Performance History
| Version | Total Time | Key Change |
|---------|-----------|------------|
| v1 (sequential, wrapper) | ~79s | baseline |
| v2 (parallel, wrapper) | ~69s | images+voices parallel |
| **v3 (parallel, direct bypass, size=1024x1024)** | **~65s** | **litellm direct, explicit size** |

### Admission Controller + Graceful Degradation
| Load Level | Queue | Free Users | Paid Users | Premium Users |
|-----------|-------|------------|------------|---------------|
| NORMAL | <10 | Full quality (3 scenes) | Full quality | Full quality |
| STRESSED | 10-19 | Reduced (2 scenes) | Full quality | Full quality |
| SEVERE | 20-34 | PAUSED | Reduced (3 scenes) | Full quality |
| CRITICAL | 35+ | PAUSED | PAUSED | Full quality |

### Plan Controls
| Plan | Scenes | Priority | Watermark | Concurrent | Image |
|------|--------|----------|-----------|------------|-------|
| Free | 3 (2 under stress) | Low | Yes | 1 | 1024, low quality |
| Paid | 4 | Medium | No | 3 | 1024, low quality |
| Premium | 6 | High | No | 5 | 1024, low quality |

## Distribution Loop (LIVE)
Public pages, explore, creator profiles, OG tags, sitemap, share buttons, remix, watermark. **120 seeded creations** across 6 categories in 3 waves.

## Content Seeding Status
| Phase | Count | Status |
|-------|-------|--------|
| Phase A | 40 | COMPLETE |
| Phase B+C (Wave 1, 7-21 days ago) | 27 | COMPLETE |
| Phase B+C (Wave 2, 2-7 days ago) | 27 | COMPLETE |
| Phase B+C (Wave 3, 0-2 days ago) | 26 | COMPLETE |
| **Total** | **120** | **COMPLETE** |

Categories: Fantasy(21), Motivational(21), Emotional(21), Sci-Fi(20), Kids(19), Luxury(18)

## Completed (All Sessions)
1. Design system, homepage, dashboard, Story Video Pipeline
2. Distribution loop (explore, public pages, remix, share, OG tags, sitemap)
3. Content Seeding Phase A (40 videos), Creator Profiles, Growth Dashboard
4. Plan-based scene limits, credit reservation, scene caching
5. Parallel image+voice execution
6. Streaming first asset, estimated time remaining
7. Admission controller + per-user concurrency limits
8. Direct litellm image bypass — 18% faster per image
9. **Content Seeding Phase B+C** — 80 more videos (120 total) in 3 waves
10. **Graceful degradation under load** — 4 load levels (normal/stressed/severe/critical), auto scene reduction, free-tier pausing

## Remaining Backlog
### P0
- [x] Content Seeding Phase B+C (80 more → 120 total) ✅
- [x] Graceful degradation under load ✅

### P1
- [ ] Direct-to-storage uploads via signed URLs
- [ ] Storage lifecycle (auto-delete temp assets after 72h)
- [ ] Creator Profile pages (`/creator/:username`)

### P2
- [ ] BYO API / BYO Cloud mode
- [ ] Creator Challenges
- [ ] Cashfree payments (live)
- [ ] Email Notifications (BLOCKED — SendGrid)
