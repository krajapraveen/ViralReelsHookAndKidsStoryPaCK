# Visionary Suite — PRD

## Product Vision
AI Creative Operating System with a **Create → Share → View → Remix** growth loop.
Every output is a permanent CDN-backed asset in the network.

### Strategic Focus (User Directive)
> 1 flagship feature, 2 supporting features, everything else secondary.
> Stop adding surface area. Deepen what exists.

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

### Graceful Degradation
| Load Level | Queue | Free Users | Paid Users | Premium Users |
|-----------|-------|------------|------------|---------------|
| NORMAL | <10 | Full quality | Full quality | Full quality |
| STRESSED | 10-19 | Reduced (2 scenes) | Full quality | Full quality |
| SEVERE | 20-34 | PAUSED | Reduced (3 scenes) | Full quality |
| CRITICAL | 35+ | PAUSED | PAUSED | Full quality |

## Distribution Loop (LIVE)
- Public pages, explore, OG tags, sitemap, share, remix, watermark
- **120 seeded creations** across 6 categories in 3 waves
- **Creator Profiles** at `/creator/:username`
- **Trending This Week** algorithmic carousel (views + remixes*5 + recency)
- **Live Creations Feed** — real-time social proof, 7s auto-refresh, anonymized locations

## Completed (All Sessions)
1. Design system, homepage, dashboard, Story Video Pipeline
2. Distribution loop (explore, public pages, remix, share, OG tags, sitemap)
3. Content Seeding Phase A+B+C (120 videos total)
4. Plan-based scene limits, credit reservation, scene caching
5. Parallel image+voice execution, direct litellm bypass
6. Admission controller + graceful degradation (4 load levels)
7. Download architecture fix — permanent CDN assets, R2 upload, user_assets collection
8. Creator Profile pages — `/creator/:username`
9. Trending This Week — algorithmic carousel with weighted scoring
10. **Live Creations Feed** — real-time activity feed, excludes seeded content, diverse locations

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
