# Visionary Suite - Changelog

## 2026-02-28: Admin Credentials Update & CI/CD Integration (Iteration 109)

### Admin Credentials Changed
- **Old Email**: admin@creatorstudio.ai
- **New Email**: krajapraveen.katta@creatorstudio.ai
- **Password**: Updated to new secure password
- **Verified**: Login tested and working on preview environment

### CI/CD Pipeline Integration
- Updated `/app/.github/workflows/playwright.yml` with:
  - Manual workflow dispatch option
  - Environment selection (preview/production)
  - Chromium and Firefox browser support
  - Test artifacts upload
  - GitHub Step Summary generation
  - Failure notifications

### Package.json Scripts Added
```json
{
  "test": "npx playwright test --project=chromium",
  "test:all": "npx playwright test",
  "test:smoke": "npx playwright test --project=chromium --grep 'should login|should load|health' --workers=1",
  "test:report": "npx playwright show-report"
}
```

### Downloads Endpoint Error Handling
- Enhanced `/api/downloads/my-downloads` with try-catch blocks
- Added logging for debugging production issues
- Production 502 error identified as Cloudflare/nginx issue (not code)

---

## 2026-02-28: Production Stabilization Verified (Iteration 107-108)

### Regression Testing Results:
- Production Tests: 95% PASS
- Preview Tests: 100% PASS
- Playwright Automated Tests: 28/31 PASS (90%)

### Comic Generation Verified:
- Job ID: 6a87fee1-2dcc-4818-bfa8-38c6a34c6913
- Result: BASE64 DATA URL (1,056,382 chars)
- Status: COMPLETED on production

---

## Previous Changes

### Notification System (2026-02-27)
- Bell icon in header
- Notification dropdown panel
- Real-time polling

### 5-Minute Download Expiry (2026-02-27)
- Countdown timer
- Auto-cleanup service
- Premium extension feature

### Worker System (2026-02-26)
- Per-feature worker pools
- Auto-scaling at 80% utilization
- Admin dashboard at /app/admin/workers

### Photo Trailer — Share Funnel + Premium Queue Priority (2026-02-XX)
- Share funnel analytics: 12 events tracked (share_page_view, video_play_clicked, signup_completed, etc.) via /api/funnel/track
- Premium queue priority: separate asyncio Semaphores (_PRIORITY_GATE, _STANDARD_GATE) so premium 90s jobs skip the line
- Admin queue-stats endpoint: GET /api/photo-trailer/admin/queue-stats (auth-gated)
- MP4 provenance metadata baked into rendered trailers (title, copyright, description = job_id)
- Fixed 2 failing tests: provenance metadata test now resolves ffmpeg/ffprobe via fallback (system → bundled); queue-stats test passes
- Full photo_trailer regression suite green: 39/39 tests across share_funnel, trust_legal, premium_tier, signed_urls, vertical_cut, janitor



### Photo Trailer — Founder KPI Dashboard (2026-02-XX)
- New endpoint `GET /api/photo-trailer/admin/dashboard?range=24h|7d|30d` returns 27 KPIs across 6 sections:
  Acquisition (3) · Engagement (4-7) · Conversion (8-13) · Revenue (14-19) · Ops (20-24) · Virality (25-27)
- Powered by `funnel_events` (share_page_view, video_play_clicked, watch_25/50/75, completed_watch, share clicks, make_your_own_clicked, signup_started/completed, first_trailer_created, paywall_shown/upgrade_clicked) joined with `photo_trailer_jobs` (plan_tier, duration, queue_lane, queue_wait_seconds, render time, fail rate)
- New admin page `/app/admin/photo-trailers` (`PhotoTrailerKpiDashboard.jsx`): truth-first stat cards + pure-CSS bar charts, 24h/7d/30d toggle, refresh button
- Fixed `priority_slots` config exposure in queue-stats (was reading semaphore-runtime value, now exposes static configured slot count)
- Test suite: `test_photo_trailer_kpi_dashboard.py` (4 tests — auth gate, range validation, all-three-ranges, and seeded-math correctness across all 6 sections)
- Full Photo Trailer regression: 36/36 green

### Photo Trailer — Failure Diagnostics (2026-02-XX)
- Backend: `/admin/dashboard` ops block now includes 7 new diagnostic fields:
  `failure_stage_breakdown`, `error_code_breakdown`, `top_failure_stage`, `top_error_code`,
  `recovery_opportunity`, `recent_failures`, `fail_trend`
- `_fail()` helper now preserves the active `current_stage` into `failure_stage` BEFORE overwriting current_stage to "FAILED" — without this fix, stage breakdown reports "FAILED" for everything
- Historical jobs without `failure_stage` are mapped via `error_code → stage` table
- Recovery opportunity calc: assumes 65% retry success rate for transient codes, projects fail-rate after retry strategy
- Frontend: 4 cards under fail-rate (#1/#2/#3 stages + top error), recovery banner with strikethrough → projected rate, dual stage/code breakdown tables with retryable/fatal badges, stacked-bar daily fail trend with stage legend, collapsible recent-failures drawer (last 10)
- 6 KPI dashboard tests passing


### Photo Trailer — P0 RELIABILITY SPRINT (2026-02-XX)
Founder directive: 59.2% fail rate → under 20%. Three changes shipped together.

**1. JANITOR — Dynamic stale thresholds + heartbeat protection**
- Replaced single `STALE_THRESHOLD_MINUTES = 5` with per-duration table:
  20s = 10min, 45/60s = 20min, 90s = 35min, default = 15min
- Added `last_progress_at` + `last_stage_change_at` fields, written by `_set_stage`
  and a new `_heartbeat(job_id, message)` helper called inline during long stages
- Janitor skips any job whose `last_progress_at` < 180s (alive)
- DB-side prefilter (smallest tier threshold) + per-sweep cap of 50 jobs prevents
  thundering-herd on backlogs

**2. STALE AUTO-RECOVERY — First stale gets a free retry**
- New `retry_count` field. retry_count == 0 + stale → status flips back to QUEUED,
  `_run_pipeline(jid)` re-scheduled, `auto_requeued_at` stamped, `retry_count = 1`,
  `progress_message = "Recovering stalled job — auto-retrying"`. NO refund.
- retry_count >= 1 + stale → normal FAIL + STALE_PIPELINE + refund (existing path)
- Funnel event `photo_trailer_auto_requeued` emitted for dashboard observability

**3. IMAGE_GEN HARDENING — Per-scene retry, partial-failure tolerance**
- `_gen_scene_image` inner retry bumped 2→3 attempts with explicit 2/5/10s backoff
- Outer per-scene retry in orchestrator (one extra shot with fresh session_id)
- `asyncio.gather(return_exceptions=True)` — one failed scene no longer cancels
  in-flight siblings; failure message tells user which scene index died
- Heartbeat ping per scene start ("Generating scene 4/6") + on retry ("Retrying scene 4/6")

**UX**
- New `progress_message` field rendered under the stage copy in the wizard
- Amber styling on retry/recovery messages, violet on normal progress

**Tests**
- 10/10 new reliability_sprint tests green
- 4/4 existing janitor regression tests updated for new behavior
- Full Photo Trailer regression: 47/47 green

**Expected impact** (per dashboard recovery-opportunity card):
- 67 STALE_PIPELINE jobs in 30d × ~65% recovery → ~44 jobs saved
- Projected fail-rate drop: 59.1% → ~40% on STALE alone
- Plus IMAGE_GEN retries should cut the 41% IMAGE_GEN_FAIL share further
- Combined target post-fix: under 20%


### Photo Trailer — P0 LOW-CREDITS REVENUE UX (2026-02-XX)
Founder directive: replace generic "Could not start trailer" toast with structured
revenue-conversion paywall.

**Backend**
- `POST /api/photo-trailer/jobs` returns structured 402 `INSUFFICIENT_CREDITS`:
  `{code, message, required_credits, current_credits, missing_credits, duration_seconds, current_plan, suggested_durations, upgrade_url, topup_url}`
- `suggested_durations` calculated server-side: lists shorter durations the user
  CAN afford right now (1-tap downgrade UX)
- Emits `photo_trailer_low_credit_seen` funnel event with full context
- Added 5 events to funnel allowlist: `photo_trailer_low_credit_seen`,
  `photo_trailer_buy_credit_clicked`, `photo_trailer_subscribe_clicked`,
  `photo_trailer_duration_downgraded`, `photo_trailer_credit_fail_recovered`,
  plus `photo_trailer_auto_requeued` from reliability sprint

**Frontend**
- New `LowCreditsModal` component replaces the toast for 402 INSUFFICIENT_CREDITS
- Smart primary CTA per plan:
  - FREE → Subscribe Now (revenue conversion)
  - PAID → Buy Credits (top-up)
  - PREMIUM → Contact Support (safety net)
- Variant copy:
  - missing ≤ 5 → "Subscribe now and get instant access"
  - missing > 20 → "Best value: Monthly plan"
  - default → "Add credits or subscribe to continue"
- Inline 1-tap downgrade buttons for cheaper durations
- Pre-click "Need X credits · you have Y" / "You are short by Z" subtext under cost line

**SPEED — Image+TTS pipelined per scene**
- Per-scene voiceover now kicks off inline AS SOON AS that scene's image lands
  (was: serial gather phase 1 = all images, phase 2 = all audio)
- Wall-clock saving estimate: ~25-40% on 6-scene trailers
- One-failure-blocks-all-others isolation preserved via `return_exceptions=True`
- TTS_FAIL vs IMAGE_GEN_FAIL distinguished in error tagging for diagnostics

**Tests**
- 5/5 new low-credits tests green (structured 402 shape, suggested durations,
  funnel event emission, free-tier exemption, pipeline source-level proof)
- 47/47 reliability + KPI + funnel + premium + vertical + janitor regression green
- **Total: 52/52 photo_trailer suite green**

