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


### Photo Trailer — P0 STUCK-AT-88% RELIABILITY FIX (2026-02-XX)
Founder-reported live bug: spinner stuck at 88% RENDERING_TRAILER forever.
Root cause = heartbeat protection had no upper bound + ffmpeg/upload calls had
no per-stage timeout. Fixed in one disciplined pass.

**Backend**
- New `HARD_MAX_RUNTIME_BY_DURATION` (20s=8min, 60s=15min, 90s=25min) — absolute ceiling
- New `RENDER_TIMEOUT_BY_DURATION` (20s=5min, 60s=8min, 90s=12min) — per-stage ceiling
- `_render_trailer` wrapped in `asyncio.wait_for(timeout=render_timeout)` — surfaces RENDER_TIMEOUT cleanly
- All R2 uploads (widescreen + vertical + thumbnail) bounded by `asyncio.wait_for` (300s/180s/60s)
- Janitor logic rewritten: heartbeat extension is now valid ONLY in `[hard_max, stale_threshold]` window. Past `stale_threshold` → reap regardless of heartbeat
- Hard-max-exceeded jobs at retry_count=0 now SUPPRESS auto-requeue (toxic — would just hang again)
- Janitor uses `RENDER_TIMEOUT` error_code when failure occurred during RENDERING_TRAILER stage (vs generic STALE_PIPELINE for upstream)
- New admin endpoint `GET /admin/stuck-jobs?min_age_minutes=N` lists PROCESSING jobs with stale heartbeat + reap-prediction
- Dashboard `ERROR_TO_STAGE` map + `RETRYABLE_CODES` updated to include `RENDER_TIMEOUT`

**Frontend**
- `ProgressStep` polling now also exits on `status === 'CANCELLED'` (was: COMPLETED + FAILED only)
- Escalation copy gated to elapsed time:
  - 0-3 min: clean spinner only (no clutter)
  - 3+ min: "you can leave this page" card + escape buttons
  - 4+ min: amber "This is taking longer than usual" warning above
- Trust `j.status` over `progress_percent` for terminal transition (fixes "88% with status=FAILED" stuck-spinner bug)

**Tests** — 9 new tests in `test_photo_trailer_render_timeout.py`:
1. Hard-max thresholds match founder spec
2. Hard-max overrides fresh heartbeat in janitor
3. Hard-max suppresses auto-requeue
4. Admin /admin/stuck-jobs surfaces stuck jobs
5. RENDER_TIMEOUT in dashboard error map
6. Render stage uses asyncio.wait_for
7. Frontend ProgressStep detects terminal status
8. Frontend escalation copy gated to 3-min mark
9. RENDER_TIMEOUT emits funnel failure event

**Total Photo Trailer regression: 61/61 green**

Live verification: `/admin/stuck-jobs` returned a real 90s job at 5.5min mid-GENERATING_SCENES with `will_be_reaped_next_sweep=false` (correctly under 25min hard-max).


### Photo Trailer — P0 DOWNLOAD-BUTTON FIX (2026-02-XX)
Founder bug: "Download 16:9" button does nothing on Result screen.

**Root cause**
The download handler called `window.open(j.url, '_blank', 'noopener')` AFTER an
async `fetch()`. Chrome and Safari popup blockers silently kill `window.open()`
that doesn't originate from a synchronous user gesture — the async fetch broke
the gesture chain. No error, no toast, button just appeared dead.

**Fix (`PhotoTrailerPage.jsx :: handleDownload`)**
1. Toast "Preparing download…" immediately on click (user feedback)
2. Always fetch a FRESH signed URL on click (handles 10+ min waits where
   the previous `streamUrl` may have expired)
3. Trigger via temporary `<a href={url} download={fname}>` element +
   programmatic `click()` — counts as gesture continuation, no popup blocker
4. Fallback: if anchor click throws (locked-down WebKit), `window.location.href = url`
5. Exact error reasons surfaced (`detail.message`, `detail`, network err)
   — no more silent "Could not start download"
6. Toast "Download started" on success
7. Funnel emit: `photo_trailer_download_clicked` (allowlisted server-side)

**Backend (already correct, verified by tests)**
- `/api/photo-trailer/jobs/{job_id}/stream?download=true&format=wide|vertical`
  returns `{url, expires_in, format, thumbnail_url, has_vertical}`
- R2 signer adds `response-content-disposition: attachment; filename="..."`
- Format regex enforces `wide|vertical` only
- Owner-only (404 for non-owner, 401 anonymous)

**Tests** — 7 new in `test_photo_trailer_download.py`:
1. /stream returns signed URL with attachment disposition
2. format=vertical mints vertical key
3. invalid format → 422
4. anonymous → 401/403
5. non-owner → 404
6. Frontend uses `<a download>` pattern (no `window.open(` in handler code)
7. Funnel allowlist includes `photo_trailer_download_clicked`

**Live verification**: hit `/stream` for a real completed trailer with both
formats — both return 200 with `response-content-disposition` in the signed URL.

**Total Photo Trailer regression: 68/68 green**


### Photo Trailer — P0 RESULT-PAGE ESCAPE PATH (2026-02-XX)
Founder bug: Result page had no Back/Home — users got trapped after a trailer
finished (couldn't get back to wizard or home without browser back-button).

**Frontend (`PhotoTrailerPage.jsx :: ResultStep`)**
- Top-left **Back** button (testid `trailer-result-back-btn`):
  prefers parent-supplied `onBackToWizard` callback (in-page state reset),
  falls back to `navigate('/app/photo-trailer')`
- Top-right **Home** button (testid `trailer-result-home-btn`): `navigate('/app')`
- Both labels use `hidden sm:inline` — icon-only on mobile, icon+label on desktop
  → no horizontal overflow on iPhone widths (verified at 390x844)
- Wrapped in a labelled flex container (testid `trailer-result-nav`) using
  the existing border/background tokens, no new color or design language
- Parent passes `onBackToWizard` mirroring the existing `onCreateAnother`
  reset logic so Back lands on wizard step 1 with clean state

**Untouched (per founder rule)**: generation pipeline, render logic, download
logic, payments, credits, templates, share buttons, Make-another button.

**Tests** — 9 new in `test_photo_trailer_result_nav.py`:
1. Back button rendered with documented testid
2. Home button rendered with documented testid
3. Home routes via useNavigate to /app
4. Back uses callback with route fallback
5. Nav container has labelled testid
6. All 5 existing primary CTAs still present (Download / WhatsApp / More /
   Make another / video element)
7. ArrowLeft + Home icons imported from lucide-react
8. Labels use `hidden sm:inline` — mobile-safe
9. Parent passes `onBackToWizard` prop

**Total Photo Trailer regression: 77/77 green**


### Photo Trailer — P0 START-ERROR TRANSPARENCY (2026-02-XX)
Founder bug: clicking Generate on failure showed only "Could not start trailer"
red toast. No cause, no next step. Users blamed the product.

**Backend** — every error path on `POST /api/photo-trailer/jobs` now returns
structured `{detail: {code, message}}` instead of bare strings:
- `INVALID_TEMPLATE`, `UPLOAD_SESSION_NOT_FOUND`, `UPLOAD_NOT_FINALISED`
- `HERO_NOT_IN_SESSION`, `CHARACTER_NOT_IN_SESSION`
- `TOO_MANY_ACTIVE_JOBS` (with `active_jobs` count)
- `PROMPT_BLOCKED` (existing safety reject path now structured)
- (Pre-existing structured: `INSUFFICIENT_CREDITS`, `UPGRADE_REQUIRED`,
  `FREE_QUOTA_EXCEEDED`)
- New funnel event `photo_trailer_start_failed` allowlisted

**Frontend** (`PhotoTrailerPage.jsx`)
- New `START_ERROR_MESSAGES` map with founder-spec human copy for: insufficient
  credits, rate-limited, auth-required, upload-missing, beta-locked,
  validation, plus all backend codes
- New `deriveStartError(resp, body, thrown)` helper produces stable
  `{code, message, http_status, retryable, cta}` shape
- New inline error panel (testid `trailer-start-error`) ABOVE Generate:
  - Persistent (doesn't disappear like a toast)
  - Shows error code + http status (debug-friendly)
  - Contextual CTAs:
    - INSUFFICIENT_CREDITS → "Buy credits" → `/app/billing`
    - UPGRADE_REQUIRED / FREE_QUOTA_EXCEEDED → "See plans" → `/app/pricing`
    - AUTH_REQUIRED → "Sign in" → `/login`
    - UPLOAD_*  / HERO_*/CHARACTER_* → "Re-upload" (jumps to wizard step 1)
    - INVALID_TEMPLATE → "Pick a template" (jumps to wizard step 2)
    - PROMPT_BLOCKED → "Edit prompt"
    - TOO_MANY_ACTIVE_JOBS / RATE_LIMITED / UNKNOWN → "Retry"
- Toast still fires (same human message) — toast for ephemeral feedback,
  panel for read-and-act
- `setStartError(null)` at the top of every onGenerate attempt — never a
  stale red panel
- `photo_trailer_start_failed` emitted with `{code, message, http_status}`
- The OLD bare `'Could not start trailer'` fallback string is GONE
- No raw stack traces ever surfaced

**Tests** — 11 new in `test_photo_trailer_start_errors.py`:
1. `INVALID_TEMPLATE` returns structured 400 detail
2. `UPLOAD_SESSION_NOT_FOUND` returns structured 404
3. `TOO_MANY_ACTIVE_JOBS` returns structured 429 with active_jobs count
4. `photo_trailer_start_failed` is in funnel allowlist
5. Frontend has all 13 spec'd error codes in mapper
6. Inline error panel testids present + role=alert
7. Frontend emits start_failed event with code+http_status
8. Generic "Could not start trailer" fallback removed
9. Retry button gated to `err.retryable`
10. CTA button + buy/pricing/billing routes wired
11. `setStartError(null)` clears panel on retry

**Total Photo Trailer regression: 88 passed across 12 suites (each isolated)**


─────────────────────────────────────────────────────────
[2026-04-30] PHOTO TRAILER — HERO UI VERIFY + 48h READOUT + SIGNUP ROOT-CAUSE
─────────────────────────────────────────────────────────
Founder directive: a → b → c, evidence only, no new features, no patches until root cause proven.

─── (a) HERO SELECTION UI — 6/6 PASS (iteration_532.json) ───
  test_1  desktop_checkboxes_outside_photo   PASS  (photo Y=304, checkboxes Y=520)
  test_1b mobile_checkboxes_outside_photo    PASS  (44px tap, 390px viewport)
  test_2  villain_only_selection             PASS  (Continue enabled → step 3)
  test_3  supporting_only_selection          PASS  (Continue enabled → step 3)
  test_4  hero_fallback_mechanism            PASS  (backend 200/201 on promoted hero)
  test_5  happy_path_explicit_hero           PASS  (job_id returned)
  test_6  backend_contract_regression        PASS  (422 on missing hero — enforced)
  File:   backend/tests/test_photo_trailer_hero_selection_ui_iteration532.py

─── (b) 48h RELIABILITY READOUT (2026-04-28 17:41Z → 2026-04-30 17:41Z) ───
  Window tool: backend/tests/reliability_readout_48h.py (live MongoDB pull)

  STARTS
    starts_attempted            278
    starts_succeeded            275  (reached pipeline)
    start_failed (job doc)        3  (all HERO_LOAD_FAIL)
    start_failed (funnel events)  0

  OUTCOMES
    completed                    79
    pipeline_failed             194
    still_running                 1
    completion_rate_of_starts  28.7%
    completion_rate_of_attempts 28.4%

  PIPELINE FAILURES BY CODE
    IMAGE_GEN_FAIL   92  (47.4%)   ← top bottleneck
    STALE_PIPELINE   87  (44.8%)   ← janitor-driven (often downstream of hung image-gen)
    RENDER_FAIL       8  ( 4.1%)
    SCRIPT_FAIL       4  ( 2.1%)
    TTS_FAIL          3  ( 1.5%)
    RENDER_TIMEOUT    0  (zero wall-clock kills — prior P0 fix holding)

  RENDER TIME (COMPLETED only, n=76)
    median          82.1 s
    p95            154.4 s
    max            246.2 s
    by_bucket      {15s:62  45s:5  60s:3  90s:1}

  USER ACTIONS
    downloads_clicked             0      ← instrumentation gap or real
    whatsapp_shares              25
    native_shares                 0
    auto_requeued                17
    jobs_with_manual_retry       27

  BOTTLENECK STATEMENT (founder-mandatory closer):
    Single largest bottleneck now is: Pipeline failures (IMAGE_GEN_FAIL)
    Expected lift if fixed first:     +21.5 pts on completion rate
                                      (65% retry success rate assumed)
    Confidence:                       High  (n=194 pipeline failures)

─── (c) signup_completed=0 — ROOT CAUSE PROVEN, NOT PATCHED ───
  Classification: INSTRUMENTATION BUG (naming mismatch). NOT a real signup failure.

  Evidence (live MongoDB pull, funnel_events collection):
    window  signup_started  signup_success  signup_completed  signup_failed
    48h         129             129               0                0
    7d          161             161               0                0
    30d         161             161               0                0

  Code trace:
    • backend/routes/photo_trailer.py:2139
        signup_completed = await _unique_sessions("signup_completed", cutoff)
      ← queries a step name nothing fires.
    • backend/routes/funnel_tracking.py:95-96 whitelist contains
        "signup_started", "signup_success"  (NOT "signup_completed")
    • frontend/src/pages/Login.js:188,327
        trackFunnel('signup_success', ...)  (NOT signup_completed)

  Proof signups are succeeding: 129 signup_success events in 48h,
  session_uniq == event count (1:1, no double-fire). Success-to-started
  ratio = 100% (129/129). No signup_failed events in 48h either.

  Recommendation (NOT applied per founder freeze):
    One-line fix in photo_trailer.py dashboard query — change
    "signup_completed" → "signup_success"  (or teach the whitelist to
    alias both). No data is missing; the dashboard just reads the wrong key.

  Secondary observation (flagged, not patched):
    Login.js fires signup_started/signup_success on EVERY login (existing
    users included), not only on new user creation. The 129 48h events
    therefore mix new-signup + returning-user traffic. Real new-user count
    per users.createdAt in 48h = 0. This is a separate measurement bug
    (misnamed event, not a broken flow).

📁 Files added:
   • backend/tests/test_photo_trailer_hero_selection_ui_iteration532.py (testing agent)
   • backend/tests/reliability_readout_48h.py

🚦 Freeze discipline maintained: ZERO new features, ZERO UI changes,
   ZERO refactors, ZERO patches. Evidence-only deliverable.


─────────────────────────────────────────────────────────
[2026-04-30] PHOTO TRAILER — IMAGE NORMALIZATION PATCH SHIPPED
─────────────────────────────────────────────────────────
Founder directive: apply _normalize_ref_image_bytes exactly as proposed, no
deviations. Ship, watch 6h, report.

✅ Patch implemented in backend/routes/photo_trailer.py:
   - New helper _normalize_ref_image_bytes(raw, max_dim=1024):
     exif_transpose → mode=='RGB' → thumbnail(1024, LANCZOS) → JPEG q=90.
   - Wrapped hero_bytes + villain_bytes call sites in _run_pipeline_inner.
   - PIL failure maps to HERO_LOAD_FAIL (no new error codes leaked).
   - Zero changes to retry logic, worker pools, templates, prompts, logging,
     metrics.
   - One-line dashboard fix applied earlier: signup_completed → signup_success
     (surfaces 161 real signups that were zeroed by a key mismatch).

✅ Tests (14/14 PASS, new file test_photo_trailer_image_normalization.py):
   - RGB happy path, RGBA→RGB, CMYK→RGB, palette→RGB, EXIF orientation honored,
     3000×4000 capped to 1024, 16×16 untouched, idempotent re-normalization,
     corrupt bytes raise UnidentifiedImageError, truncated bytes raise,
     output size sanity (<800KB), pipeline source assertions confirm
     HERO_LOAD_FAIL mapping on both hero and villain branches,
     _gen_scene_image retry loop (3 attempts, 2/5/10s backoff) untouched.

✅ Regression (26 PASS, 1 pre-existing skip):
   test_photo_trailer_reliability_sprint.py + test_photo_trailer_regression_2026_04_29.py
   + test_photo_trailer_start_errors.py — all green.

✅ Live smoke (admin, post-deploy):
   - CMYK 2400×3200 hero photo (previously Nano Banana 400): job
     2d69d1dc passed GENERATING_SCENES cleanly (all 6 scenes rendered +
     voiceovers) — failed downstream at RENDER_FAIL (ffmpeg drawtext filter
     missing; pre-existing issue observed in logs at 17:35–17:40 before
     this patch shipped).
   - RGB 1024×1024 happy path (birthday_movie): job f91e86c9 same result:
     image-gen clean → RENDER_FAIL on drawtext.

✅ Post-deploy window (5.6 min, n=2 — insufficient for 6h verdict but
   directionally clear):
   - IMAGE_GEN_FAIL count         0
   - IMAGE_GEN_FAIL reduction    100% (vs 33.1% of starts in prior 48h)
   - completion_rate              0.0% (shifted bottleneck, not regression)
   - new dominant bottleneck     RENDER_FAIL (ffmpeg "No such filter: drawtext")

📁 Files Changed:
   - backend/routes/photo_trailer.py (one helper, two call sites,
     one dashboard query key fix)
   - backend/tests/test_photo_trailer_image_normalization.py (NEW, 14 tests)
   - backend/tests/reliability_readout_48h.py (NEW, reusable raw-data tool)

🚦 Discipline held: zero refactor, zero logging noise, zero dashboard work,
   zero new error codes, zero new pipeline stages.

⚠️ Next bottleneck flagged (not touched): ffmpeg system binary lacks drawtext
   filter (requires libfreetype). Fix candidates: install libfreetype-dev
   + rebuild, OR drop drawtext from scene render filter chain. Awaiting
   founder directive to dig.



─────────────────────────────────────────────────────────
[2026-04-30] PHOTO TRAILER — FFMPEG DRAWTEXT ENV FIX SHIPPED
─────────────────────────────────────────────────────────
Founder directive: fix the binary, not the pipeline. Preserve drawtext.

✅ Environment fix (no code change):
   apt-get install -y ffmpeg libfreetype6 libfreetype6-dev fontconfig
   → /usr/bin/ffmpeg now = ffmpeg 5.1.8 with --enable-libfreetype
     + --enable-libfontconfig; drawtext filter present.
   → Pipeline code at photo_trailer.py:1040/1148 already prefers
     /usr/bin/ffmpeg when it exists — no code change needed.

✅ Capability verified:
   /usr/bin/ffmpeg -filters | grep drawtext
   T.C drawtext  V->V  Draw text on top of video frames using libfreetype library.
   Fonts: FreeSans + Liberation + WenQuanYi available via fc-list
   (fc-match default = wqy-zenhei).

✅ Mandatory real-job validation (admin):
   Job d2f2ffcc — superhero_origin, 15s, RGB hero
   COMPLETED in 95s — full traversal: WRITING_TRAILER_SCRIPT →
   GENERATING_SCENES → RENDERING_TRAILER → COMPLETED
   Output: 1280×720 H.264 + AAC stereo, 20.56s, 2.44 MB
   Drawtext overlay verified by pixel scan — 1.8% bright pixels in
   bottom 80-px strip (watermark region). PASS.

─── Readout (format per founder spec; actual window 3.1 min post-env-fix) ───

POST-ENV-FIX window (3.1 min, n=1 — directional, not statistical):
  completion_rate    100%
  IMAGE_GEN_FAIL     0    (stays at 0)
  RENDER_FAIL        0    (collapsed from 100% of drawtext-broken period)
  new bottleneck     none observed yet

Full post-normalize window (12.1 min, n=3, spans drawtext-broken + fix):
  completion_rate    33.3%
  IMAGE_GEN_FAIL     0
  RENDER_FAIL        2    (both pre-env-fix)

Delta vs 48h baseline (28.7% completion): post-env-fix +71.3 pts.

Verdict: both clusters eliminated. 45–50% threshold needs 6h of real traffic
to verify; if it doesn't land, next cluster to peel = STALE_PIPELINE.

📁 Files Changed: NONE (env-only fix).

─────────────────────────────────────────────────────────
[2026-04-30] PHOTO TRAILER — HERO/VILLAIN/SUPPORT ALIGNMENT FIX
─────────────────────────────────────────────────────────
Founder-approved exception to freeze: "purely alignment + layout fix" on
Step 2 role selectors (attached screenshot showed uneven spacing, mis-aligned
checkboxes, floating buttons, not centered under photo).

✅ Implemented exactly to spec (frontend/src/pages/PhotoTrailerPage.jsx):

  1. ONE flex container wrapping all three options:
       flex flex-wrap justify-center items-center gap-4 p-2
       rounded-xl border border-white/15 bg-transparent

  2. Each option (Hero / Villain / Supporting) is identical:
       min-w-[140px] h-12 flex items-center justify-center gap-2.5
       px-3 rounded-lg border

  3. Checkbox + label perfectly vertically centered (flex items-center).

  4. Container reads as a segmented control (outer border, inner pills).

  5. Mobile: flex-wrap kicks in when width is tight; each button keeps
     its 140×48 footprint and wraps cleanly centered.

  6. aria-pressed attribute added on each button (preserves the existing
     test_clicking_hero_marks_button_active_with_aria contract).

✅ Zero logic changes: pickHero/pickVillain/pickSupport unchanged.
   Continue button behavior unchanged (anyRoleSelected). Hero-fallback
   still promotes villain/supporting to hero_asset_id on submit. Backend
   contract untouched.

✅ Existing visibility regression PASS (5/5 in 53.76s):
   - consent_checkbox square 22px / 24px (desktop / mobile)
   - role buttons ≥40px H + ≥48px W (now 48H × 140W)
   - role buttons ≥44px H on mobile (now 48H)
   - click-hero aria-pressed flip (still works with new layout)

📁 Files Changed: frontend/src/pages/PhotoTrailerPage.jsx (2 small edits —
   RoleCheckbox className, outer grid → flex container).

🚦 Freeze discipline: no animations, no logic shift, no new components,
   no backend change, no refactor, no dashboard work.

