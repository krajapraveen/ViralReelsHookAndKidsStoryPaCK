# Visionary Suite — PRD

## Product Vision
AI Creative Operating System with a **Create → Share → View → Remix** growth loop.
Every output is a permanent CDN-backed asset in the network.

## Pipeline Architecture
```
Prompt → Admission Controller → Credit Reserve → Queue (Priority) → Workers
              ↓                                        ↓
     Check: concurrency,                     Stage 1: Scenes (LLM)
     queue depth, plan,                              ↓
     LOAD LEVEL                        Stage 2: Images + Voices (PARALLEL)
              ↓                        ↓ (direct litellm bypass)
     ADMIT / DEGRADE / REJECT         Stage 3: Package + Export → R2 Upload
```

### Download Architecture (FIXED)
```
Generation → Upload to R2 → Register in user_assets DB → Return CDN URL
```
- All generated assets are **permanent** — no 5-minute expiry
- Download buttons reference CDN URLs only
- Asset validation (HEAD request) before enabling download
- user_assets collection stores all permanent creations

### Performance History
| Version | Total Time | Key Change |
|---------|-----------|------------|
| v1 (sequential, wrapper) | ~79s | baseline |
| v2 (parallel, wrapper) | ~69s | images+voices parallel |
| **v3 (parallel, direct bypass)** | **~65s** | **litellm direct** |

### Graceful Degradation
| Load Level | Queue | Free Users | Paid Users | Premium Users |
|-----------|-------|------------|------------|---------------|
| NORMAL | <10 | Full quality (3 scenes) | Full quality | Full quality |
| STRESSED | 10-19 | Reduced (2 scenes) | Full quality | Full quality |
| SEVERE | 20-34 | PAUSED | Reduced (3 scenes) | Full quality |
| CRITICAL | 35+ | PAUSED | PAUSED | Full quality |

## Distribution Loop (LIVE)
- Public pages, explore, OG tags, sitemap, share buttons, remix, watermark
- **120 seeded creations** across 6 categories in 3 waves
- **Creator Profiles** at `/creator/:username` — avatar, bio, creation grid, views, remixes
- **Trending This Week** algorithmic carousel on homepage (views + remixes*5 + recency boost)

## Content Seeding: 120/120 COMPLETE
| Phase | Count | Status |
|-------|-------|--------|
| Phase A | 40 | COMPLETE |
| Phase B+C | 80 | COMPLETE |
| **Total** | **120** | **COMPLETE** |

## Completed (All Sessions)
1. Design system, homepage, dashboard, Story Video Pipeline
2. Distribution loop (explore, public pages, remix, share, OG tags, sitemap)
3. Content Seeding Phase A+B+C (120 videos total)
4. Plan-based scene limits, credit reservation, scene caching
5. Parallel image+voice execution, direct litellm bypass
6. Admission controller + graceful degradation (4 load levels)
7. **Download architecture fix** — permanent CDN assets, no expiry, R2 upload, user_assets collection
8. **Creator Profile pages** — `/creator/:username` with avatar, bio, grid, views, remixes
9. **Trending This Week** — algorithmic carousel with weighted scoring

## Remaining Backlog
### P0
- [ ] Photo to Comic UX improvements (hero section, upload-first flow, style presets, social proof)

### P1
- [ ] Direct-to-storage uploads via signed URLs (browser → R2, bypass backend)
- [ ] Storage lifecycle (auto-delete temp assets after 72h)

### P2
- [ ] BYO API / BYO Cloud mode
- [ ] Creator Challenges
- [ ] Cashfree payments (live)
- [ ] Email Notifications (BLOCKED — SendGrid)
