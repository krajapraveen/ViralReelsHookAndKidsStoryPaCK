# Visionary Suite — PRD

## Product Vision
AI Creative Operating System: **Create -> Share -> View -> Remix**

### Golden Rules
1. **NO BUTTON SHOULD EXIST IF IT CANNOT GUARANTEE AN OUTPUT.**
2. **A job cannot be READY until the primary preview asset is validated and renderable.**
3. **Frontend must never lie about backend truth.**
4. **One authoritative UI state. No contradictory rendering.**
5. **Credits must NEVER show 0 due to loading or API failure.**

## UI State Machine (IMPLEMENTED — Photo-to-Comic + Story Video)
```
IDLE -> PROCESSING -> VALIDATING -> READY | PARTIAL_READY | FAILED
```

| uiState | Badge | Download | Share | Preview |
|---|---|---|---|---|
| PROCESSING | Progress bar | Hidden | Disabled | Hidden |
| VALIDATING | "Validating Assets" (amber) | "Verifying..." (disabled) | Disabled | Skeleton |
| READY | "Video/Comic Ready" (green) | Enabled | Enabled | Real image/poster |
| PARTIAL_READY | "Video/Comic Saved" (amber) | Enabled if download_ready | Disabled | Gradient fallback + retry |
| FAILED | "Generation Issue" (red) | Disabled (unless partial assets) | Disabled | Retry/Resume button |

## Asset Truth Model (IMPLEMENTED — Both pipelines)
Backend `/validate-asset` returns separate truth:
```json
{
  "preview_ready": bool,
  "download_ready": bool,
  "share_ready": bool,
  "ui_state": "READY | PARTIAL_READY | FAILED",
  "poster_url": "...",
  "download_url": "...",
  "share_url": "...",
  "stage_detail": "Human-readable status"
}
```

## Credits Truth (IMPLEMENTED — ALL Pages)
- State initialized to `null` (loading), NEVER `0`
- Shows `...` while loading, never 0
- Shows `∞` for admin/unlimited users
- 3-tier fetch: cache -> auth/me -> wallet fallback
- Every page that displays credits: Dashboard, GifMaker, ComicStorybookBuilder, BedtimeStoryBuilder, PhotoToComic, CreditStatusBadge

## SafeImage Component (IMPLEMENTED — ALL Surfaces)
Handles: null, empty, data URIs, broken CDN, CORS failures.
Gradient fallback + title overlay. Deployed on:
- Dashboard (trending videos)
- Landing (trending section)
- Gallery (video thumbnails + preview modal)
- ExplorePage (all cards)
- CreatorProfile (avatar + creation cards)
- ComicStorybookBuilder (page previews)
- StoryPreview (scene images)
- ProgressiveGeneration (scene thumbnails)
- StoryVideoPipeline (postgen preview + scene thumbs)
- MyStories, StoryChainView, ResumeYourStory

## Story Video Bulletproof Pipeline (IMPLEMENTED — March 17, 2026)
- Strict useReducer state machine
- Backend `GET /api/pipeline/validate-asset/{job_id}` — granular asset truth
- Separate preview/download/share readiness
- Download/Share gated on validated assets
- Reconnect safety: active jobs resumed on page load
- Duplicate click guard
- Hard 5-minute timeout + 90-second stale detection
- ProgressiveGeneration delegates all transitions to parent

## Full Platform Hardening Audit (COMPLETED — March 17, 2026)
### Tested Modules (ALL PASS):
- Dashboard, Photo to Comic, Story Video Studio, Comic Storybook Builder
- GIF Maker, Reel Generator, Bedtime Story Builder, Brand Story Builder
- Caption Rewriter Pro, Daily Viral Ideas
- My Downloads, Gallery, Explore, Landing, Creator Profile
- Credits system (all pages), CreditStatusBadge, Story Chain

### Results:
- Backend: 25/25 tests PASS (0 errors, 0 failures)
- Frontend: ALL pages load correctly, credits display correct, SafeImage prevents broken icons
- No contradictory UI states found
- No pages show credits as 0
- No broken image icons on any surface

## Completed Work (All Sessions)
1-23. Previous work (resilience, upload, story chains, re-engagement)
24. Credits truth fix + SafeImage component creation
25. STATE MACHINE FIX: Strict uiState for Photo-to-Comic
26. IMAGE FALLBACK SWEEP: onError handlers + gradient fallbacks
27. STORY VIDEO BULLETPROOF PIPELINE: Full state machine, validate-asset, reconnect safety
28. FULL PLATFORM HARDENING: Credits truth across all pages (null init, ∞ display), SafeImage sweep on Landing/Gallery/Explore/CreatorProfile/ComicStorybook/GifMaker, generation truth verified for all tools

## Remaining Backlog
### P0
- [ ] R2 bucket CORS configuration (infra — will move PARTIAL_READY -> READY)

### P1
- [ ] Consistent aspect ratios and card sizing across all surfaces
- [ ] Post-generation parity for Story Video (Continue/Remix/Share/View Chain)

### P2
- [ ] Style preset preview thumbnails
- [ ] Cashfree payments (live)
- [ ] Frontend admin dashboard for observability
- [ ] Email Notifications (BLOCKED — SendGrid)
- [ ] Automated regression + monitoring architecture

### Blocked
- R2 CORS — requires manual infra config
- SendGrid — requires plan upgrade
