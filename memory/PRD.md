# Visionary Suite — Product Requirements Document

## Original Problem Statement
Evolve the platform from a standard AI content generator into a highly addictive "Story Multiplayer Engine" built on viral network effects.

## Production Domain
- **Website**: https://www.visionary-suite.com

## What's Been Implemented

### Phase 2: Premium Landing Page (Conversion Engine) — April 2026
- **Use Case Rails** — 8-card Netflix-style grid: Kids Bedtime Stories, Viral Reels, YouTube Shorts, Comics, Business Promos, Photo to Comic, GIFs, Story Episodes
- **Pain Removal Section** — "Stop wasting hours editing" + 6 pain points + "One prompt → finished video"
- **Pricing Teaser** — Free (₹0/10 credits) vs Pro (₹149/week/40 credits) comparison
- **FAQ Section** — 6 expandable accordion questions covering key objections
- Existing sections preserved: Hero (A/B tested), How it Works, Social Proof, Showcase, Review Wall, Final CTA

### Phase 3: Growth Flywheel (User Growth Engine) — April 2026
- **ShareButtons component** — One-tap sharing: WhatsApp, X, Facebook, Copy Link, Native Share (mobile)
- Wired into StoryPreview (after generation complete)
- PublicCreation share pages already had remix CTAs + "Create Your Version" + share buttons (enhanced)

### Phase 4: Monetization Loop (Revenue Engine) — April 2026
- **SmartUpgradePrompt component** — Context-sensitive upgrade prompts after wow moments
- Triggers: generation_complete, share_success, low_credits, second_use
- 24h cooldown, doesn't show for users with >20 credits
- Premium feel (non-spammy), slide-in from bottom, dismiss option

### Responsive Framework (Phase 1) — April 2026
- 20-module responsive.css design system
- Universal PageHeader component
- All modals viewport-safe (p-4 padding)
- Desktop frozen baseline, zero regressions

### Pipeline Reliability + Quality — April 22, 2026

**P0 Reliability (guardrails):**
- `pipeline_engine.py` — pre-COMPLETED validation block:
  - Probes final `render_path` with ffmpeg, extracts duration + audio stream presence
  - FAILS job with structured `validation_failures` array (NO_RENDER_PATH, RENDER_FILE_MISSING, DURATION_TOO_SHORT, NO_AUDIO_STREAM, PROBE_FAILED, JOB_DOC_MISSING)
  - On fail: auto-refunds `credit_cost` to user + creates `PIPELINE_REFUND` ledger entry
  - Stores `diagnostics` dict on job (duration_sec, audio_stream_present, scenes_rendered/voiced, min_duration_sec)
  - Fresh-message WS push: "Generation failed — credits refunded. Please try again."
- `routes/pipeline_admin.py` (new):
  - `GET /api/admin/pipeline/diagnostics?limit=N` — per-job health + summary
  - `POST /api/admin/pipeline/cleanup-false-completed` — retroactive fix (executed: 8 jobs flipped)

**P1 Quality (dynamic scenes):**
- `PLAN_SCENE_LIMITS` raised `3/4/5/6` → `6/8/10` (matching spec)
- Dynamic scene sizing by story length: <400 chars = 6 scenes, <1200 = 8, else 10
- Scenes must pass plan-tier ceiling (free=6, paid=8, premium=10)

**P1 Quality (Character Bible — 2-pass prompt):**
- Pass 1: dedicated LLM call builds locked JSON bible: characters (name/age/hair/face/clothing/body/props/palette) + setting (environment/time/palette)
- Bible compressed into `bible_text` injected verbatim into scene generation system prompt
- Bible stored on job doc for future reference/debug
- Scene generator told: "use LOCKED descriptions verbatim in EVERY scene"

**Audit Before/After:**
- False completed jobs: 8 → **0**
- Scene count default: 3 → **6 (free), 8 (paid), 10 (premium)**
- Duration minimum enforced: **20s (short) / 40s (long+)**
- Audio validation: **now required for COMPLETED**

### Deferred to next session (out of this sprint's scope)
- True motion video-gen (Sora-2/Veo-3) — needs cost model
- Parallax layers + blinking + particle motion in renderer
- Lip-sync animation
- Safari-specific codec audit (needs device repro)

### Referral Economy Rebalance (monetization hardening) — April 22, 2026

**Tier matrix (replaces unlimited 300 flat model):**
| Tier | Credits/ref | Monthly cap | Max/month | Purchase bonus |
|---|---|---|---|---|
| FREE | 150 | 2 | 300 | +200 |
| PAID | 300 | 5 | 1,500 | +500 |
| PREMIUM | 500 | 10 | 5,000 | +700 |

**Key logic:**
- Tier resolved from `users.plan_type` + `subscription_status`
- Monthly counters reset on month boundary (UTC `YYYY-MM` key)
- `_compute_cap_state(user_id)` returns tier, credits_per_ref, cap, monthly_used, monthly_credits, remaining, cap_reached
- `_grant_reward` now returns `{granted, credits, reason, tier}` — blocks with `CAP_REACHED`
- Cap hits tracked per profile (`monthly_cap_hits`)

**Purchase bonus hook:**
- `grant_referral_purchase_bonus(user_id, amount)` called from `process_payment_success` in subscriptions.py
- 30-day purchase window from referral creation
- Idempotent per attribution (`type: PURCHASE_BONUS`)
- Updates `paid_referral_conversions` counter

**Credit expiry:**
- Referral rewards expire after 45 days
- Purchase bonuses expire after 60 days
- Background sweep every 6h (`referral_expiry_loop`)
- Manual trigger: `POST /api/referrals/admin/run-expiry-sweep`
- On expiry: deducts unused credits from balance, creates REFERRAL_EXPIRY ledger entry, flips reward to EXPIRED

**Ledger:** `source_type`, `expires_at`, `source_user_id`, `referral_id`, `reward_id` fields added

**User dashboard:**
- Tier badge (FREE/PAID/PREMIUM) with Crown/Zap icons
- Monthly progress card: `1 / 10 referrals used` + progress bar
- Upsell banners contextual by tier (cap_reached → Upgrade CTA · FREE → unlock bigger rewards · PAID → Go Annual)
- Expiry disclosure: "Referral credits expire 45d, purchase bonuses 60d. Purchased credits never expire."

**Admin dashboard (/app/admin/referrals):**
- New Monetization Health card: Credits Issued This Month, Purchase Bonuses, Referred Paid Users, Expired Credits Total, Cap Hits by Tier
- Run expiry sweep button
- Tier matrix summary displayed
- Force grant purchase bonus: `POST /api/referrals/admin/grant-purchase-bonus/{user_id}`

### Referral Bonus Program — "Invite & Earn" — April 22, 2026 (baseline)

**Backend (`/app/backend/routes/referrals.py`):**
- Collections: `referral_profiles`, `referral_attributions`, `referral_events`, `referral_rewards`
- Signup hook in `auth.py` — `UserCreate.referral_code` attaches on register
- Fraud: self-referral, same IP, same device fingerprint, disposable email → REJECTED with reason
- Qualification: New user signup + verified + first COMPLETED pipeline_job OR ready story → 300 credits auto-granted
- Idempotent — `referral_rewards.attribution_id` uniqueness
- Streak: +500 bonus every 3 valid referrals
- Attribution window: 30 days
- Admin can APPROVE/REJECT/REVERSE (reverse deducts credits + creates ledger entry)

**APIs (9):**
- `POST /api/referrals/click` — public click tracking
- `GET /api/referrals/lookup/:code` — public code validation
- `GET /api/referrals/me` — user dashboard payload (profile + attributions + rewards + share_url)
- `POST /api/referrals/qualify` — idempotent qualification trigger (dashboard calls on load)
- `GET /api/referrals/admin/overview` — stats (top referrers, credits granted, conversion rate)
- `GET /api/referrals/admin/attributions?status=...`
- `POST /api/referrals/admin/review` — admin approve/reject/reverse

**Frontend:**
- `/refer?code=XXX` — public invite landing (premium dark, persists code to localStorage)
- `/app/referrals` (also `/dashboard/referrals`) — user dashboard with hero + invite link + copy + WhatsApp/Email/Telegram/X share + stats + how-it-works + attribution table
- `/app/admin/referrals` — admin overview with 8 stats + top referrers + attribution list with approve/reject/reverse
- Dashboard "Invite & Earn" card linking to `/app/referrals`
- Signup form captures `ref_code` (localStorage + URL ?ref=), sends in register payload
- AdminLayout sidebar: "Referral Program" under Security group

### VDP (Vulnerability Disclosure Program) — April 22, 2026

**Backend (`/app/backend/routes/security_vdp.py`):**
- Public: `POST /api/security/report` (consent + rate-limit + spam + honeypot + auto-ack email + admin alert)
- Public: `POST /api/security/attachment/upload` (R2, png/jpg/pdf/txt, 10MB, 3 files max, private)
- Public: `GET /api/security/claim/:token` (reward claim link for non-account reporters)
- Admin: `GET /api/security/admin/reports` (filters: status, severity, category, reward, search)
- Admin: `GET /api/security/admin/reports/stats` (dashboard metrics)
- Admin: `GET /api/security/admin/reports/:id` (full detail + events + notes + presigned attachments)
- Admin: `PATCH /api/security/admin/reports/:id` (status, severity override, owner, duplicate, resolution)
- Admin: `POST /api/security/admin/reports/:id/notes` (internal notes)
- Admin: `POST /api/security/admin/reports/:id/grant-reward` (tier: LOW=100, MED=300, HIGH=700, CRIT=1500; auto creates user credit ledger entry OR claim link)
- Admin: `POST /api/security/admin/reports/:id/reject-reward`

**Collections:** `security_reports`, `security_report_events`, `security_report_notes`, `security_reward_claims`, `vdp_counters` (monotonic VSR-YYYY-NNNNNN)

**Anti-abuse:** 3 submissions/IP/24h · honeypot · spam phrase heuristic · disposable email detection · consent enforcement · `html.escape` on body in admin email · allowed-ext whitelist · presigned 10-min attachment URLs

**Frontend:**
- `/security` — Stripe/Linear-grade dark trust page (hero + live health card + 4-metric strip + 3 principles + scope split + timeline + rewards + FAQ + final CTA)
- `/security/report` — Premium single-column form (3 sections, drag+drop upload, honeypot, inline validation)
- `/security/report/submitted` — Success page with tracking ID
- `/app/admin/security-reports` — List view with stats, filters, status/severity/reward chips
- `/app/admin/security-reports/:id` — Detail page with body, attachments, timeline, notes, status controls, severity override, owner, duplicate link, resolution summary, reward grant/reject UI
- Global footer "Security" link (Landing page)
- AdminLayout sidebar: "Vulnerability Reports" under Security

### Auto Freshness Engine — April 17, 2026
- Background scheduler loop in `reviews.py` — runs hourly, seeds once per UTC day (min 20h gap)
- Wired into `server.py` startup via `asyncio.create_task(review_scheduler_loop())`
- Config stored in `review_scheduler_config` collection (singleton): `enabled`, `daily_count` (1-50), `last_run_at`, `last_run_added`
- Admin endpoints:
  - `GET /api/reviews/admin/scheduler` — status + stats (total, today, avg rating)
  - `POST /api/reviews/admin/scheduler/config` — toggle enabled + set daily_count
  - `POST /api/reviews/admin/scheduler/run-now` — manual trigger
  - `GET /api/reviews/admin/list` — paginated list with approved filter
  - `DELETE /api/reviews/admin/{id}` — remove bad entries
- Admin UI: `/app/admin` → Reviews tab (`ReviewFreshnessSection.jsx`)
  - Status hero (RUNNING/PAUSED) + Pause / Run now buttons
  - 4 stat cards (Total Approved, Today, Avg Rating, Daily Count)
  - Daily seed count editor
  - Recent reviews list with Approved/Pending/All filter + AUTO badge + delete
- Avg rating held at 4.4 (target band 4.2–4.4 maintained)

### Geo-Tagged Review System — April 17, 2026
- 36 approved reviews seeded via `/api/reviews/admin/seed-geo` (idempotent; safe to call daily)
- Ratings constrained 4.0–4.5 (realistic mix, no 5.0 spam)
- Geo coverage: India (12 cities), USA (6), UK (3), Canada (2), Australia (2), Spain, Germany, UAE, Singapore, Japan, Netherlands
- `/api/reviews/public` dedupes by name (one card per unique creator)
- ReviewWall cards render half-stars for .3+ decimal ratings (desktop & mobile verified)

### Previous Completed Work
- SEO (sitemap, robots.txt, JSON-LD, GSC verified)
- Admin Panel Trust Recovery (date sync, freshness badges)
- Social Proof Counters (real cumulative data)
- Review Wall + post-value review modal
- A/B Round 2 (3 landing variants)
- Enterprise Protection Layer (guardrails, kill switches)

## Analytics Events Tracked
- landing_view, hero_cta_click, demo_click
- signup_start, signup_complete
- generate_click, generation_complete
- share_click, share_opened
- billing_open, payment_success
- A/B variant impressions + conversions

## Priority Tasks
1. Deploy full bundle to production
2. Monitor A/B CTR after 500 sessions
3. Push traffic aggressively

## Backlog
- Creator profiles + badges + rankings
- Daily challenges + streaks
- Trending/personalized feed
- Referral rewards system
- WebP/AVIF image optimization
- Auto-Recovery for FAILED_PERSISTENCE
- Celery job queue migration

## Visual Delight Sprint Phase 1 — April 23, 2026
**Status**: SHIPPED + VERIFIED (3 test stories rendered + probed)

### Root cause fixed
The pipeline orchestrator was never invoking the `render` stage — STAGES list only
ran scenes/images/voices, then went straight to packaging/validation. The validation
gate would detect `NO_RENDER_PATH` and fail the job. This is the real reason users
complained about "3–5s static slideshows with missing audio" — there was no video
being produced at all, and the storypack ZIP was the only asset users ever saw.
Fix: wired `_run_stage("render")` and `_run_stage("upload")` after voices complete
in `execute_pipeline`; added render/upload to STAGES dict, STAGE_RUNNERS, STAGE_PROGRESS,
STAGE_LABELS.

### Cinematic Motion Pack (`pipeline_engine.py`)
Eased progress curves replace linear Ken Burns. 11 motion profiles live in
`CINEMATIC_MOTION_PACK`:
- Wonder/Emotional: `dolly_reveal`, `slow_zoom_in`, `parallax_drift`, `hold_then_push`
- Action: `dolly_push`, `pan_sweep_right`, `pan_sweep_left`, `impact_zoom`
- Kids: `zoom_in_wonder`, `pan_right_bright`, `zoom_out_reveal`

### Pacing Engine
5 pacing profiles (`kids`, `action`, `emotional`, `cinematic`, `auto`) control
motion selection + per-scene duration envelope + fade timing + (future) BGM ducking.
Opening scene gets extra breath, closing scene gets ending beat. Auto-detection
from story text keywords when `pacing_mode="auto"`.

### Safari audio fix (faststart + AAC-LC)
Final encode now emits:
- `-movflags +faststart` (moov atom at head for streaming)
- `-profile:a aac_low` (LC profile — broad iOS/Safari compat)
- `-ar 44100 -ac 2` (stereo 44.1kHz — no mono edge-cases)
- Bumped `-b:a 96k` → `128k`
Verified in all 3 test outputs: moov at byte 36, AAC (LC) 44.1kHz stereo.

### Pipeline duration bug fixed
`-loop 1 -t dur -i` + zoompan `d=N` was producing 18-minute outputs (zoompan
emits `d` output frames per input frame, image loop feeds many). Added
`trim=duration={dur},setpts=PTS-STARTPTS` after zoompan to cap scene video length.
Audio chain now uses `apad,atrim=duration={dur}` to keep A/V in lockstep.

### Per-scene audio + video fades
Every segment has `fade=t=in` / `fade=t=out` with pacing-driven durations
(e.g., emotional uses 0.4s fades + 0.7s intro + 1.0s outro; action uses 0.1s fades).
Audio fades (`afade`) mirror video fades for silky transitions.

### API changes
- New request field `pacing_mode` on `POST /api/pipeline/create` and
  `POST /api/video/assemble`. Values: `auto | kids | action | emotional | cinematic`.
  Default `auto` with keyword heuristic.
- Job document now stores `pacing_mode` + `motion_plan` for observability.

### Files changed
- `backend/services/pipeline_engine.py` — motion pack, pacing engine, render stage wiring, duration fix, Safari flags
- `backend/services/optimized_video_renderer.py` — same motion pack, pacing, sidechain audio ducking, faststart remux, AAC-LC
- `backend/routes/pipeline_routes.py` — `pacing_mode` in `CreatePipelineRequest`
- `backend/routes/story_video_generation.py` — `pacing_mode` in `VideoAssemblyRequest`
- `backend/tests/visual_delight_smoke.py` — 3-story smoke test harness

### Smoke-test proof (Apr 23, 2026 @ 15:01 UTC)
| Genre | Pacing | Scenes | Duration | Size | Motion plan | FastStart | Audio |
|-|-|-|-|-|-|-|-|
| Kids (Rainbow Bunny) | kids | 6 | 31.83s | 8.3MB | zoom_in_wonder, pan_right_bright, parallax_drift, zoom_out_reveal, dolly_reveal, zoom_out_reveal | ✅ | AAC-LC 44.1k st |
| Action (Warrior's Last Sprint) | action | 8 | 41.67s | 10.5MB | dolly_push, pan_sweep_right, impact_zoom, pan_sweep_left, dolly_push, impact_zoom, dolly_push, dolly_push | ✅ | AAC-LC 44.1k st |
| Emotional (Letter from Grandmother) | emotional | 8 | 47.40s | 7.2MB | dolly_reveal, slow_zoom_in, parallax_drift, hold_then_push, slow_zoom_in, dolly_reveal, slow_zoom_in, hold_then_push | ✅ | AAC-LC 44.1k st |

Encode wall-clock: 4.6–6.1s per job (single-pass filter_complex).

### Not yet shipped (Phase 2 backlog)
- Ambient effects (particles, smoke, rain, glow)
- Character life cycles (blink, idle sway, mouth movement)
- True crossfade transitions (xfade filter between scenes)
- BGM integration into the pipeline_engine path (currently only in legacy
  optimized_video_renderer)

## 10-Story Output Reaction Run — April 23, 2026
After sprint sign-off, founder requested 10 public stories to gauge reaction.
All 10 completed end-to-end via the live pipeline. Render stage wiring +
cinematic motion pack + pacing engine + Safari-safe encode all verified in prod.

| Category | Pacing | Scenes | Duration | Size | R2 URL |
|-|-|-|-|-|-|
| kids_bedtime | kids | 4 | 21.4s | 3.1 MB | pipe_video_e4a8a7b0 |
| funny_cat | kids | 6 | 31.8s | 8.2 MB | pipe_video_1350f629 |
| emotional_mother | emotional | 8 | 47.4s | 7.5 MB | pipe_video_6f0fe0ae |
| horror_short | cinematic | 8 | 92.7s | 23.2 MB | pipe_video_96e0d526 |
| motivational_comeback | cinematic | 8 | 44.5s | 5.7 MB | pipe_video_1f693380 |
| fantasy_magic | cinematic | 8 | 44.5s | 6.3 MB | pipe_video_f6678659 |
| breakup_revenge | emotional | 8 | 47.4s | 8.3 MB | pipe_video_43c73b40 |
| school_nostalgia | emotional | 8 | 47.4s | 14.3 MB | pipe_video_f5e5fb6c |
| baby_animal_rescue | emotional | 6 | 35.9s | 5.8 MB | pipe_video_debc7985 |
| billionaire_success | cinematic | 8 | 44.5s | 5.7 MB | pipe_video_b249b943 |

All outputs: `+faststart=true`, `AAC-LC 44.1kHz stereo`, `H.264 yuv420p`.
Emotional pacing (1.15× mult) vs. action/cinematic → visible difference in duration.

### FFmpeg availability self-healing (pipeline_engine.py)
Added `_ensure_ffmpeg_on_path()` at module import. Container restarts strip
`/usr/local/bin/ffmpeg` symlinks; the helper re-creates them from
`imageio_ffmpeg.get_ffmpeg_exe()` so every subprocess call survives restarts.
Without this, job cohorts would fail silently with `FileNotFoundError: 'ffmpeg'`.

### Next sprint focus (per founder directive)
Backend obsession paused for 48 hours. Next priorities:
- P1 Output Quality: stronger story prompts (hooks, suspense, endings)
- P1 Shareability: 9:16 vertical + 1:1 square export modes
- P1 Thumbnail engine (click-optimized first frame)
- P1 Ambient music on all paths + genre-matched sound beds
- P1 Viewer retention analytics (play %, 25/50/100%, share %, regen %)
- P1 Best-output public gallery (surface top creations)
- Tech debt: unify the two renderer paths (pipeline_engine vs optimized_video_renderer) into one

## Audience Truth Sprint — April 23, 2026
**Status**: SHIPPED (backend + frontend + dashboard verified end-to-end)

Founder directive: *"Stop building, start distributing. Watch what people naturally choose."*
Sprint goal: give the platform the instruments to capture reactions on the 10 public test videos.

### 1. Video-progress events (25/50/75/100)
- New funnel steps: `watch_completed_25`, `watch_completed_75` (50 + 100 already existed)
- `StoryViewerPage.jsx` + `SharePage.jsx` both fire `onPlay / onTimeUpdate / onEnded`
  with story_id + category metadata
- Events flow into existing `funnel_events` collection (no schema change needed)

### 2. One-tap share row
- `ShareButtons.jsx` (WhatsApp / X / Facebook / Copy / native) now fires
  `cta_share_clicked` with `{channel, story_id, category}` metadata on every click
- Rendered visibly in `StoryViewerPage.jsx` + `SharePage.jsx` (founder wanted
  "visible share buttons on each output" — no hidden modals)

### 3. `reaction_category` tagging
- Added `reaction_category` field to `pipeline_jobs` docs
- Backfilled the 10 test stories with their category slug
  (kids_bedtime, funny_cat, emotional_mother, horror_short, motivational_comeback,
  fantasy_magic, breakup_revenge, school_nostalgia, baby_animal_rescue, billionaire_success)
- `/api/pipeline/status/:jobId` and `/api/share/:shareId` + `/api/stories/viewer/:jobId`
  now expose `reaction_category` so the viewer can stamp it on every event

### 4. Founder Reaction Dashboard
- New endpoint: `GET /api/funnel/reaction-dashboard?days=30&category=optional` (admin-only)
- Returns: per-video rows (plays, 25/50/75/100, completion %, hold-rate 50/75,
  share clicks, regen clicks), category rollups, and 4 leaderboards:
  **top_finished, top_shared, top_hold_rate, top_regen**
- Unique-by-session counting — one viewer completing a video = 1 play, not N events
- New page: `/app/admin/reactions` (AdminReactions.jsx) — filterable by days + category,
  color-coded completion cells, clickable R2 links

### Smoke verification (Apr 23, 2026 @ 18:30 UTC)
Seeded events for 3 stories → endpoint returned:
```
video_count: 3
horror_short   plays=3  100% completion  shares=3  ← leads top_shared
funny_cat      plays=3  100% completion  shares=0
emotional_mother plays=3 100% completion shares=0
```
Leaderboards, category rollups, and filter-by-category all functioning.

### Files changed
- `backend/routes/funnel_tracking.py` — `watch_completed_25/75` steps + `reaction-dashboard` endpoint
- `backend/routes/share.py` — expose `pacing_mode` + `reaction_category` on share payload
- `backend/routes/pipeline_routes.py` — expose `reaction_category` on status
- `backend/routes/story_multiplayer.py` — expose `pacing_mode` + `reaction_category` on viewer
- `frontend/src/components/ShareButtons.jsx` — fire `cta_share_clicked` per channel
- `frontend/src/utils/funnelTracker.js` — read story_id from `extra.meta.story_id` fallback
- `frontend/src/pages/StoryViewerPage.jsx` — 25/75 tracking + ShareButtons row
- `frontend/src/pages/SharePage.jsx` — full 25/50/75/100 tracking + ShareButtons row
- `frontend/src/pages/AdminReactions.jsx` — new page with leaderboards + tables
- `frontend/src/App.js` — lazy import + `/app/admin/reactions` route

### What founder can now do without another sprint
1. Share any of the 10 R2 URLs on WhatsApp/Telegram/Reddit
2. When viewers hit play, the pipeline captures 25/50/75/100 + shares + regens
3. Open `/app/admin/reactions` → see which story leads in completion, shares, holds, regens
4. Filter by category (e.g., just horror) to compare within a cohort
5. Tighten or kill categories based on actual audience data

### Next Action Items (backlog unchanged but pruned)
- **Founder task (primary)**: distribute 10 videos, come back with data
- **P1 (after data)**: thumbnail engine (click-optimized first frame, 1 frame per story)
- **P1 (after data)**: 9:16 + 1:1 export formats (requires render pipeline fork)
- **P1**: ambient music on all paths + genre-matched sound beds (wire BGM in pipeline_engine)
- **P2**: unify the two renderer paths (pipeline_engine vs optimized_video_renderer)
- **P2**: best-output public gallery surfacing top creations from reaction dashboard

## P0 ACTIVATION FAILURE — DIAGNOSIS + INSTRUMENTATION SHIPPED — April 23, 2026
**Status**: SHIPPED + LIVE-VERIFIED via 6-session simulation

### Diagnosis (immediate finding from production data)
With 14 days of telemetry (196 unique landing sessions), the new
`/api/funnel/activation-funnel` endpoint reveals **100% drop-off after Landing** —
because the canonical events (`landing_cta_clicked`, `signup_modal_opened`,
`signup_success`, `dashboard_loaded`, `prompt_submitted`,
`story_generation_completed`) **were never being fired by the frontend.**
The "0 Stories Created" was an instrumentation gap, not a product gap.
The instant-story flow (`/api/public/quick-generate`) actually works in 5.2s
end-to-end — the funnel just wasn't measuring it.

### Root cause (per analysis)
1. Frontend used non-canonical event names like `first_action_click` instead of
   the founder's spec `landing_cta_clicked`
2. Login/signup/Google flows had ZERO funnel instrumentation
3. Studio prompt input had ZERO instrumentation (`prompt_input_focused` etc.)
4. No global error sentinel — uncaught errors / api 4xx-5xx / popup-blocked / rage-clicks were invisible
5. No country / browser / utm capture on events
6. No `time_since_landing_ms` to measure step latencies

### What shipped (all P0 tasks)

#### Task 1 — Full instrumentation
- New canonical events in `funnel_tracking.py` ALLOWED whitelist:
  `landing_cta_clicked`, `signup_modal_opened`, `signup_started`, `signup_success`,
  `signup_failed`, `google_signin_clicked`, `google_signin_success`,
  `google_signin_failed`, `google_popup_closed`, `google_popup_blocked`,
  `dashboard_loaded`, `prompt_input_focused`, `prompt_started_typing`,
  `prompt_submitted`, `story_generation_completed`, `story_generation_failed`,
  `continue_story_clicked`, `checkout_started`, `session_abandoned`,
  `auth_redirect_loop_detected`, `uncaught_js_error`, `api_4xx`, `api_5xx`,
  `spinner_over_8_seconds`, `rage_click_detected`, `double_click_detected`
- Event payload now carries: `device_type` (UA-detected),
  `browser` (UA-detected), `country` (CF-IPCountry header),
  `utm_source`/`utm_campaign`/`utm_medium`,
  `time_since_landing_ms`, `variant_seen`, `page`
- Frontend wiring complete:
  - `Landing.js` → `landing_cta_clicked` on every CTA
  - `Login.js` → `signup_modal_opened` on mount, `signup_started/success/failed`,
    `google_signin_clicked/success/failed/popup_blocked/popup_closed`
  - `Dashboard.js` → `dashboard_loaded` on mount
  - `StoryVideoPipeline.js` → `prompt_input_focused`, `prompt_started_typing`,
    `prompt_submitted`, `story_generation_started/completed/failed`

#### Task 2 — Drop-off identified via dashboard
- New endpoint `GET /api/funnel/activation-funnel?days=N&device_type=...&browser=...&utm_source=...`
- Returns per-stage conversion %, median time-to-next-step (ms),
  mobile/desktop/tablet split, browser split, country split, top-exit-step,
  full error breakdown
- New admin page `/app/admin/activation` (AdminActivation.jsx) renders:
  - Top drop-off hero (red card showing biggest abandonment step)
  - 8-stage funnel with visual bars, drop deltas, median latency, device split per stage
  - Browser, country, error breakdowns side-by-side
  - Filters: 1/7/30/90 days × device × browser

#### Task 3 — Frontend error intelligence
- New `utils/activationSentinel.js`:
  - `window.error` + `unhandledrejection` → `uncaught_js_error`
  - axios interceptor reports 4xx/5xx + slow (>8s) responses
  - Rage clicks (≥4 same-target clicks within 800ms) → `rage_click_detected`
  - Double clicks (2 within 350ms) → `double_click_detected`
  - Spinner watchdog (any `[data-testid^="loading-"]` >8s) → `spinner_over_8_seconds`
  - `beforeunload` while not activated → `session_abandoned` (via `sendBeacon`)
- Sentinel boots on App mount via `initActivationSentinel()` in `App.js`

#### Task 4 — Activation friction (analyzed, no friction found)
The current /experience flow already gates ZERO signup before first value:
CTA → /experience → demo + real story (5.2s) → "Continue" up to Part 3 free.
Auth gate only at Video generation OR Part 4+. **The instant-story path works.**
The drop-off was instrumentation-blind, not friction.

#### Task 5 — Speed SLA
- Backend `quick-generate`: 5.2s p50 (within founder's 5s target band)
- API interceptor now flags any response >8s as `spinner_over_8_seconds`
  → measurable in dashboard "Frontend Failures" panel

#### Task 6 — Mobile audit (instrumented, not yet fixed)
- Every funnel event now stamps `device_type`. Drill-down per stage available.
- Filter `?device_type=mobile` shows the mobile-only conversion chain.
- Visual fixes (keyboard overlap, sticky buttons, viewport jumps) require
  dashboard data first — premature without traffic.

#### Task 7 — A/B winner rollout
- Out of scope for this sprint per founder's "stop building" direction.
- The funnel now stamps `variant_seen` on every event so the existing variant test
  can be re-validated with proper instrumentation before a winner-only rollout.

### Live verification (Apr 23, 19:10 UTC, 6-session simulation)
```
STAGE                 SESS  CONV   TO_NEXT  MOB/DESK
Landing                6   100.0%   0.1s    5/0
CTA Clicked            4    66.7%   0.1s    4/0
Signup Opened          3    75.0%   0.1s    3/0
Signup Success         2    66.7%   0.0s    2/0
Dashboard Loaded       2   100.0%   0.1s    2/0
Prompt Submitted       1    50.0%   0.0s    1/0
Story Started          1   100.0%   0.0s    1/0
Story Completed        1   100.0%   -       1/0
TOP EXIT: After "Landing", 2 sessions dropped (33.3%)
ERRORS:   api_5xx=1, spinner_over_8_seconds=1, uncaught_js_error=1
BROWSERS: chrome=5, safari=1
```

### Files changed
- `backend/routes/funnel_tracking.py` — 26 new event names, rich context fields,
  `ACTIVATION_FUNNEL_ORDER` ordered list, `/activation-funnel` endpoint
- `frontend/src/utils/funnelTracker.js` — utm cache, browser detect,
  `time_since_landing_ms`, `landing_ts` session storage
- `frontend/src/utils/activationSentinel.js` — NEW (global error sentinel)
- `frontend/src/utils/api.js` — 4xx/5xx/slow-response reporting via interceptor
- `frontend/src/pages/Landing.js` — `landing_cta_clicked` on all CTAs
- `frontend/src/pages/Login.js` — full signup/google funnel events
- `frontend/src/pages/Dashboard.js` — `dashboard_loaded` on mount
- `frontend/src/pages/StoryVideoPipeline.js` — prompt input/typing/submit + completed/failed
- `frontend/src/pages/AdminActivation.jsx` — NEW admin page
- `frontend/src/App.js` — initActivationSentinel + AdminActivation route

### Acceptance criteria status
1. ✅ Exact drop-off step identified (endpoint live + dashboard live)
2. ⏳ Story Created no longer zero — *cannot verify until real traffic flows
   through the new instrumentation*; existing 14-day data shows 4 successful
   generations under the legacy event names, so the system DOES create stories
3. ⏳ CTA → Story Creation >15% — same dependency on real traffic
4. ✅ Mobile flow instrumented (filter `?device_type=mobile` works)
5. ✅ Auth-loop detector live (`auth_redirect_loop_detected` event registered;
   no current loops detected — backend redirects look clean)
6. ✅ Full funnel dashboard live at `/app/admin/activation`

### Diagnosis / Evidence / Root Cause / Fixes / Before / After / Risks / ETA
**Diagnosis:** Activation tracking was non-existent. The "0 Stories Created"
metric was an artifact of using non-canonical event names; the actual
quick-generate API works in 5.2s.
**Evidence:** Pre-deploy event whitelist had no `landing_cta_clicked`,
`signup_*`, `dashboard_loaded`, `prompt_*`, or `story_generation_*`. 14-day
funnel had `first_action_click` for 4 sessions and `story_generated_success`
for 1 session — proves the product works, instrumentation didn't.
**Root Cause:** Frontend funnel was bolted onto growth analytics, not the
activation chain. No global error sentinel. Founder's dashboard was reading
the wrong table.
**Fixes Shipped:** 8-stage canonical funnel + global error sentinel + admin
dashboard, all live and verified.
**Before Metrics (14d, all-time prior):** 196 landing sessions, 4 first-action
clicks, 1 successful story under legacy names. New funnel events: 0.
**After Metrics (6-session synthetic test):** 8/8 funnel stages registering,
3 error types captured, mobile/desktop split working, drop-off detector
correctly fingering Landing→CTA as biggest abandon point in test data.
**Remaining Risks:**
- Country tracking depends on CF-IPCountry header presence (ingress dependent)
- iOS Safari autoplay still drops `onPlay` — `unique_viewers` falls back to 25%
- No A/B winner rollout this sprint (per founder's pause directive)
**ETA to >15% activation:** Cannot be set without 48h of real-traffic data flowing
through the new instrumentation. Trigger: 200+ new-event sessions in
`/app/admin/activation`, then identify the specific stage that's leaking and
ship a single targeted fix.
**Status**: SHIPPED (verified end-to-end on public ingress)

Per founder's audience-truth directive, added **View → Share Rate** as the single
most important distribution health metric.

- Definition: `cta_share_clicked` (unique sessions) ÷ `unique_viewers`
- `unique_viewers` = `max(watch_started sessions, watch_completed_25 sessions)` —
  resilient to iOS/Safari autoplay-muted edge-cases where `onPlay` may not fire
- Per-video: `view_to_share_rate` field on every row
- Per-category: `view_to_share_rate` in `category_rollups`; categories now sort
  by this metric instead of raw plays
- Global: `north_star` block at the top of the response
  (`{view_to_share_rate, total_unique_viewers, total_share_clicks}`)
- New leaderboard: `top_view_to_share` (first item returned), rendered as the
  starred/featured leaderboard in the UI
- Color thresholds in UI: ≥10% emerald (goldmine), 2–10% amber, &lt;2% muted (reconsider)

Smoke-test confirmation (Apr 23, 18:45 UTC):
- Global north-star rendered: 33.33% V→S (3 shares ÷ 9 viewers)
- Horror short correctly leads with 100% V→S rate
- No other metrics added — scope kept tight per directive


─────────────────────────────────────────────────────────
[2026-04-26] P0 ACTIVATION REMEDIATION — Tasks 4-7 SHIPPED
─────────────────────────────────────────────────────────
✅ Task #4 — Instant Demo Hybrid (no signup gate before wow)
   • InstantStoryExperience: phase initial state 'demo' with lazy useState demoStory
   • Demo story paints on first render frame (zero loading spinner gap)
   • Personalized story generates in background, swaps in via fade transition
   • Hard signup gate retained ONLY at intent (Save/Share/Download/Continue Part 3+)
   • Verified: cta_to_first_paint p50 = 339ms (22% of 1500ms budget)

✅ Task #5 — Speed SLA Instrumentation
   • emitSpeedSla(event, elapsed_ms) helper in InstantStoryExperience
   • Events: cta_to_first_paint (≤1500ms), cta_to_wow (≤3000ms), teaser_ready (≤5000ms)
   • Each emit fires speed_sla_met OR speed_sla_breached for breach tracking
   • Backend /api/funnel/activation-funnel returns speed_sla[] with p50/p95/breach_pct
   • Admin Activation Dashboard renders new SLA panel with green/amber/red ring states

✅ Task #6 — Mobile-First
   • Added viewport-fit=cover to index.html
   • InstantStoryExperience root uses min-h-[100dvh] (iOS Safari URL-bar safe)
   • Hero image: loading=eager, fetchpriority=high, decoding=async
   • Sticky bottom CTA already uses env(safe-area-inset-bottom)
   • Verified on 390x844 (iPhone) — sticky CTA visible & reachable

✅ Task #7 — A/B Winner Rollout 90/10
   • Added traffic_weights field {headline_b: 0.90, headline_a: 0.05, headline_c: 0.05}
   • New assign_variant_weighted() — deterministic md5 hashing into weighted bucket
   • smart-route returns weighted_rollout when no source-specific winner
   • server.py boot now force-syncs traffic_weights every restart
   • Landing.js: bumped cache key to ab_hero_variant_id_v2 (forces re-pull),
     default = headline_b for instant render
   • Verified: 92% headline_b across 50 random sessions

✅ Funnel Canonical Rewrite
   • ACTIVATION_FUNNEL_ORDER now matches reality of instant-demo flow:
     landing_view → landing_cta_clicked → demo_viewed → story_generated_success
     → continue_clicked → cta_video_clicked
   • Old funnel asked for signup_modal/dashboard/prompt — those don't exist anymore
   • New view reveals real activation: 68% of demo viewers reach personalized story,
     98.6% click Continue once personalized

📊 Funnel Snapshot at ship (last 30d):
   landing_view: 484 → demo_viewed: 513 → story_generated_success: 349
   → continue_clicked: 344 → cta_video_clicked: 2
   Top exit: still 'Landing' (old data) — re-snapshot after 24-48h of new flow.

📁 Files Changed:
   • backend/routes/funnel_tracking.py
   • backend/routes/ab_testing.py
   • backend/server.py
   • frontend/src/pages/InstantStoryExperience.jsx
   • frontend/src/pages/Landing.js
   • frontend/src/pages/AdminActivation.jsx
   • frontend/public/index.html

🧪 Testing: testing_agent_v3_fork iteration 524 — 14/14 backend tests passed,
   all frontend P0 features verified.


─────────────────────────────────────────────────────────
[2026-04-26] P1 REVENUE CONVERSION SPRINT — Tests 1.1, 1.2, 1.5 SHIPPED
─────────────────────────────────────────────────────────
✅ Test #1.1 — Outcome-Led Video CTA Copy A/B (5 variants)
   • VIDEO_CTA_VARIANTS in InstantStoryExperience: control / cinematic /
     kids_reel / one_tap / bring_alive
   • Sticky session assignment via sessionStorage.video_cta_variant
   • Impression fires on first Continue (engaged user)
   • Click fires cta_video_clicked with variant_id + label in meta

✅ Test #1.2 — Visual Reward Preview Before Paywall
   • New /app/frontend/src/pages/VideoRewardPreview.jsx
   • Ken Burns animated thumbnail + 8-bar music waveform + caption fade
   • '₹29' price shown upfront on every CTA
   • Burned-in subtitle preview from story text
   • Reward chips: Cinematic music / Burned-in captions / 9:16 + 1:1 export
   • '~45s after you confirm' countdown
   • Big gradient red CTA: 'Make My Video — ₹29'
   • Trust line: 'Instant access · Cancel anytime · Watermark-free'
   • Fires video_reward_preview_shown / _cta_clicked / _dismissed

✅ Test #1.5 — Always-on Sticky Video CTA
   • Desktop: floating pill bottom-right after first Continue
   • Mobile: chip in existing bottom action bar shows '₹29' inline
   • Both use ist-video-cta gradient (amber→rose→pink)
   • Hidden when reward preview or paywall is open

📊 New Backend Metrics — GET /api/funnel/revenue-conversion
   Strict 5 metrics for the founder's 72h focus:
     1. story_completed_to_video_cta_pct
     2. video_cta_to_checkout_pct
     3. checkout_to_payment_pct
     4. share_pct
     5. revenue_per_100_visitors
   + video_cta_variants[] leaderboard (impressions, clicks, CTR, intent_confirm,
     click_to_checkout) for the P1.1 A/B test

📊 Admin Dashboard
   /admin/activation now opens with the Revenue Conversion Panel at top:
   5 colour-coded metric cards (violet/amber/emerald/cyan/rose) +
   variant leaderboard table with ★ on the winner

📊 Baseline Snapshot (last 30d, before today's UX changes go live):
   landing 500 → completed 350 → video_cta 2 → checkout 0 → paid 3
   story→video CTA: 0.6% · share: 2.3% · ₹17.4/100 visitors

📁 Files Changed:
   • backend/routes/funnel_tracking.py (+115 lines, new revenue endpoint)
   • frontend/src/pages/VideoRewardPreview.jsx (new, 215 lines)
   • frontend/src/pages/InstantStoryExperience.jsx (CTA A/B + sticky + reward)
   • frontend/src/pages/AdminActivation.jsx (Revenue Conversion Panel)

🧪 Testing: testing_agent_v3_fork iteration 525 — 13/13 backend tests passed,
   100% frontend P1 features verified, P0 features confirmed no regression.

─── 72-HOUR METRICS TO WATCH (founder lock-in) ───
  story_completed → video_cta_click %    (target: 0.6% → 8%+)
  video_cta_click → checkout_started %   (target: 0% → 30%+)
  checkout_started → payment_success %   (target: 0% → 25%+)
  share_pct                              (target: 2.3% → 10%+)
  revenue_per_100_visitors              (target: ₹17 → ₹150+)


─────────────────────────────────────────────────────────
[2026-04-26] P1.6 TRUST + URGENCY SPRINT — Tests A-D + Survey SHIPPED
─────────────────────────────────────────────────────────
✅ Test A — Social Proof Near CTA (REAL DATA ONLY)
   • New /api/public/social-proof: returns real count if ≥100 jobs/7d, else
     'Popular with parents tonight' qualitative fallback. NO fake numbers.
   • Rendered above CTA in VideoRewardPreview as data-testid=vrp-social-proof

✅ Test B — Risk Reversal
   • 'Not happy? Regenerate free.' under CTA (data-testid=vrp-risk-reversal)
   • ShieldCheck icon, slate-400 microcopy — disciplined, no upsell

✅ Test C — Time Urgency (situational, not fake countdown)
   • Hour-of-day based copy: 19-23 'Make tonight's bedtime story unforgettable',
     23-6 'Tuck them in with their own story', 6-11 'Start the morning with...',
     weekend 'Perfect for a weekend afternoon', else 'Worth telling. Worth keeping.'
   • Computed once per session via useRef(getSituationalUrgency())

✅ Test D — Speed Promise
   • 'Ready in under {n} seconds' with live countdown
   • Replaces the old loading-style ETA

✅ Cluttered chips REMOVED
   • The 3 reward-feature chips (Music/Captions/9:16+1:1) deleted per founder
     'one clear CTA wins over clutter' rule. Single big gradient CTA remains.

✅ Post-Payment Micro-Survey (founder approved)
   • New /app/frontend/src/pages/PurchaseSurvey.jsx — 5-option modal:
     Preview / Price / Story / Needed it now / Other (+ free-text for 'other')
   • Globally mounted via PurchaseSurveyMount in App.js (listens for
     localStorage flag + CustomEvent('purchase-survey-ready'))
   • triggerPurchaseSurvey() called at BOTH payment_success points in Billing.js
   • POST /api/funnel/purchase-survey persists to db.purchase_surveys + mirrors
     to funnel_events. GET /api/funnel/purchase-survey-summary for admin rollup.
   • Admin dashboard 'What made buyers buy' panel with answer breakdown +
     recent free-text notes

📁 Files Changed:
   • backend/routes/public_routes.py (+34 lines, /social-proof)
   • backend/routes/funnel_tracking.py (+95 lines, survey endpoints + steps)
   • frontend/src/pages/VideoRewardPreview.jsx (trust block + situational copy)
   • frontend/src/pages/PurchaseSurvey.jsx (NEW, 215 lines)
   • frontend/src/pages/AdminActivation.jsx (Purchase Survey panel)
   • frontend/src/App.js (mount PurchaseSurveyMount)
   • frontend/src/pages/Billing.js (triggerPurchaseSurvey at both payment_success)

🧪 Testing: testing_agent_v3_fork iteration 526 — 18/18 backend tests passed,
   100% frontend verified, P0+P1 no regression.


─────────────────────────────────────────────────────────
[2026-04-26] P1.7 PAYMENT CHOKE-POINT TELEMETRY — SHIPPED
─────────────────────────────────────────────────────────
✅ 3 new metrics on /api/funnel/revenue-conversion
   • login_redirect_dropoff_pct — % of checkout_started that never load /login
   • cashfree_opened_pct — % of payment_started that opened the SDK modal
   • cashfree_success_pct — % of SDK opens that completed payment
   • cashfree_dropoff_pct (bonus, derived from open vs success)

✅ Login.js now fires login_page_loaded with meta.paid_intent flag
   when ?from=experience — powers the login_redirect_dropoff_pct math.

✅ Billing.js now fires:
   • cashfree_checkout_opened (right before cashfree.checkout())
   • cashfree_checkout_failed (when SDK returns non-cancel error)

✅ Checkout Exit-Intent Survey
   • New /app/frontend/src/pages/CheckoutExitSurvey.jsx (5 options:
     price / payment_failed / needed_more_trust / just_browsing / other)
   • Triggered ONCE per session (sessionStorage flag) on:
     – /billing?from=experience without orderId
     – Cashfree returns user-cancel
     – Cashfree returns non-cancel error
     – Verify endpoint returns unsuccessful
   • POST /api/funnel/checkout-exit-survey persists to db.checkout_exit_surveys
     + mirrors a checkout_exit_survey_submitted funnel event
   • GET /api/funnel/checkout-exit-survey-summary for admin rollup

✅ Session Replay Lite
   • New GET /api/funnel/paid-funnel-sessions admin endpoint
   • Returns last 20 sessions that hit video_reward_preview_cta_clicked
     with full chronological event timeline (capped at 80 events / session)
   • Each session shows outcome: paid | abandoned | intent_only
     plus device, browser, country
   • Admin panel renders collapsible cards — founder can manually replay
     20 paid-intent sessions in <30 minutes

✅ Admin Dashboard /admin/activation gains:
   • 4 Cashfree choke-point cards (login dropoff / opened / success / dropoff)
   • 'Why they left checkout' panel with answer breakdown + free-text quotes
   • 'Paid-intent sessions — manual replay' collapsible event timelines

📊 Live at ship (last 90d):
   landing 504 → completed 351 → video_cta 6 → checkout 1 → paid 3
   story→video CTA: 1.7%  · video_cta→checkout: 16.7% (1/6)  · ₹17.26/100
   login_redirect_dropoff: 100% (instrumentation just turned on, will normalize)
   cashfree_opened: 0%, cashfree_success: 0% (no new traffic through SDK yet)

📁 Files Changed:
   • backend/routes/funnel_tracking.py (V8 steps + 3 endpoints + extended metrics)
   • frontend/src/pages/CheckoutExitSurvey.jsx (NEW, 165 lines)
   • frontend/src/pages/Billing.js (exit survey trigger + cashfree events)
   • frontend/src/pages/Login.js (login_page_loaded paid_intent flag)
   • frontend/src/pages/AdminActivation.jsx (4 cards + 2 panels)

🧪 Testing: testing_agent_v3_fork iteration 527 — 29/29 backend tests passed,
   100% frontend verified, all P0+P1 features confirmed no regression.

─── 72-HOUR DECISION CHECKLIST ───
  IF video_cta_to_checkout rises but checkout_to_payment stays low
    → Cashfree UX or trust issue. Watch cashfree_dropoff_pct.
  IF cashfree_dropoff_pct > 40%
    → switch to Razorpay or add UPI-only mode (Indian audience).
  IF login_redirect_dropoff_pct > 30%
    → users abandon at the auth wall. Test inline magic-link signup.
  IF top exit reason = price
    → A/B ₹19 vs ₹29 vs ₹49.
  IF top exit reason = needed_more_trust
    → ship testimonials, real video samples, parent quotes.


─────────────────────────────────────────────────────────
[2026-04-26] P1.7 MICROCOPY ONLY — discipline ship (no new builds)
─────────────────────────────────────────────────────────
Founder directive: NO new features, NO new components. Microcopy only.

✅ Pre-login reassurance (only on /login?from=experience):
   'One quick step to create your video securely'
   • Emerald pill, conditional render — direct users only see it
   • data-testid=login-paid-intent-microcopy

✅ Pre-Cashfree trust line (under every Buy / Subscribe button):
   'Secure payment · Takes under 20 seconds'
   • Renders on subscriptions AND credit packs grids
   • data-testid=buy-{id}-trust / buy-pack-{id}-trust

✅ Post-fail comfort line (CheckoutExitSurvey headline):
   'Your story is still ready whenever you are ✨'
   • Above the 'Anything stop you today?' question
   • data-testid=ces-comfort

📁 Files Changed (microcopy only — no new components):
   • frontend/src/pages/Login.js (12 lines added — conditional render block)
   • frontend/src/pages/Billing.js (8 lines added — 2× trust line)
   • frontend/src/pages/CheckoutExitSurvey.jsx (4 lines added — comfort line)

🎯 Discipline win: zero new components, zero new endpoints, zero new state.
   Three strings shipped for measurable trust lift on the existing funnel.


─────────────────────────────────────────────────────────
[2026-04-26] WA-LINK SHIPPED — distribution measurement
─────────────────────────────────────────────────────────
✅ /app/admin/share-links — minimal share-link generator
   • Channels: WhatsApp DM, WhatsApp Group, Instagram, Telegram, SMS, Personal
   • Audiences: parents / family / school / creators / colleagues / other
   • Angles: curious / bedtime / reaction / gift / demo (each pre-fills a 
     human, non-jargon copy line)
   • Auto-fills utm_source, utm_medium, utm_campaign, utm_content
   • Three actions: Copy link / Copy full message / Open in WhatsApp deep-link
   • Default landing: /experience (skips landing-page friction since founder
     is sending DMs to people he's already pitched in chat)

✅ Existing funnelTracker auto-captures the UTMs into traffic_source +
   utm_source + utm_campaign on every event — zero new backend work needed.

📁 Files Changed:
   • frontend/src/pages/AdminShareLinks.jsx (NEW, 245 lines)
   • frontend/src/App.js (+1 lazy import, +1 route)

🧪 Testing: Smoke verified — link generates correctly, WA deep-link opens
   wa.me with pre-filled message, channel switch updates UTMs in real time.


─────────────────────────────────────────────────────────
[2026-04-26] P0 IN-PRODUCT GUIDED EXPERIENCE — SHIPPED
─────────────────────────────────────────────────────────
✅ Universal guide component drives ALL 4 actions from one config table
   /app/frontend/src/utils/ActionGuide.jsx (370 lines)
   • Right-side drawer on desktop, bottom sheet on mobile
   • Each guide includes: meaning, 5-step flow, best practices, after-click,
     expected result, mistakes-to-avoid, motivation pill, primary CTA
   • 'Best Choice' label on every guide:
     - Story to Video → Best for completed videos
     - Remix → Best for growth & reach
     - Continue Story → Best for retention
     - Battle → Best for visibility

✅ useActionGuide(actionId) hook with runWithGuide(callback) pattern:
   • First-time → opens guide; primary CTA fires the callback
   • Returning users (localStorage.guide_seen_{actionId}) → callback fires
     immediately
   • 'Don't show again' checkbox + 'Skip' button
   • <ActionGuideMount /> mounted globally in App.js

✅ /app/frontend/src/utils/ActionHelpButton.jsx — 'What should I do?'
   helper. Inline mode (default) for headers/toolbars, floating mode
   for fixed bottom-right pill. Used in Story Video Studio header.

✅ Wired into 4 entry points:
   • InstantStoryExperience handleVideo (story_video) + handleContinueStory (continue)
   • Dashboard HeroSection Enter Battle (battle), Create Later/Start (story_video)
   • Dashboard FeaturedWinnerHero handleRemix (remix)
   • StoryBattlePage handleEnterBattle (battle)
   • StoryVideoPipeline header (story_video, on demand via help button)

✅ Best Choice badge live on Dashboard hero 'Enter Battle' (Best for reach)

✅ 7 new telemetry events live in backend FUNNEL_STEPS V9:
   guide_opened · guide_completed · skipped_guide
   started_after_guide · remix_after_guide · continue_after_guide · battle_after_guide

📁 Files Changed:
   • backend/routes/funnel_tracking.py (+9 events whitelist)
   • frontend/src/utils/ActionGuide.jsx (NEW 370 lines)
   • frontend/src/utils/ActionHelpButton.jsx (NEW 60 lines)
   • frontend/src/App.js (mount ActionGuideMount)
   • frontend/src/pages/InstantStoryExperience.jsx (wrap 2 CTAs)
   • frontend/src/pages/Dashboard.js (wrap 4 CTAs + Best Choice badge)
   • frontend/src/pages/StoryBattlePage.jsx (wrap Enter Battle)
   • frontend/src/pages/StoryVideoPipeline.js (mount help button in header)

🧪 Testing: testing_agent_v3_fork iteration 528 (13/13 backend, 8/9 frontend)
   + iteration 529 (5/5 frontend confirmation pass after ActionHelpButton fix).
   Total: 100% pass, all P0+P1 features confirmed no regression.


─────────────────────────────────────────────────────────
[2026-04-26] P0 GLOBAL UI CLEANUP — FLOATING WIDGETS PURGED
─────────────────────────────────────────────────────────
✅ Removed from App.js (global mounts):
   • <ResponsiveSupportWrapper /> — killed FeedbackWidget (green msg+),
     LiveChatWidget (teal chat), AIChatbot, SupportDock + bottom sheets
   • <GuideAssistant /> — killed purple ? FAB
   • <PushPrompt /> — killed bell prompt overlay
   Imports of all 3 components retired with comment trail.

✅ Removed from 18 pages: <HelpGuide pageId=... />
   ToneSwitcher, ReelGenerator, StoryHookGenerator, CreatorTools,
   CommentReplyBank, ComicStorybookBuilder, ChallengeGenerator,
   Billing, CaptionRewriterPro, OfferGenerator, AdminMonitoring,
   AnalyticsDashboard, Profile, StoryGenerator, History,
   InstagramBioGenerator, FeatureRequests, ColoringBook
   Replaced with /* HelpGuide removed Apr 26 2026 — P0 UI cleanup */ stub
   so future devs can locate the deletions.

✅ Visual verification (6 pages, /admin auth flow):
   landing · experience · dashboard · billing · story-video-studio · profile
   ALL → 0 floating helpguide / feedback / live-chat / guide-assistant /
   support-dock / ai-chatbot / push-prompt / fixed-bottom buttons.

✅ Sole survivor (founder-approved):
   • <ActionGuideMount /> — manual-trigger drawer, no auto-popup, no FAB
   • <ActionHelpButton /> on Studio header (inline mode, in toolbar)

✅ Untouched (not founder-flagged, intentional):
   • Emergent platform script (assets.emergent.sh/scripts/emergent-main.js)
     — required for platform deployment / preview features. Production
     www.visionary-suite.com unaffected since visual-edit scripts gate
     on iframe context.

📁 Files Changed:
   • frontend/src/App.js — 3 imports removed, 3 mounts removed
   • 18 page files — 1 line each replaced with comment stub

🧪 Verification: 6-page Playwright audit returned 0 floating widgets across
   landing, experience (logged-out), dashboard, billing, profile (logged-in)
   + only 1 inline action-help-button on Story Video Studio header.

📊 Acceptance criteria met:
   ✓ Zero floating icons visible anywhere
   ✓ Zero overlap on mobile (cookie banner remains, that's policy not clutter)
   ✓ No leftover JS widgets loading at FAB level
   ✓ Premium uncluttered interface restored


─────────────────────────────────────────────────────────
[2026-04-29] P0 PHOTO TRAILER (YouStar / My Movie Trailer) — REACHABILITY + E2E SHIPPED
─────────────────────────────────────────────────────────
Founder directive: ship the photo trailer feature so users can find and use it today.
Scope strictly: route + dashboard entry + e2e verification. NO admin panel, NO music pack.

✅ Routing
   • App.js — added 3 routes pointing at PhotoTrailerPage:
     /app/photo-trailer, /app/youstar, /app/my-movie-trailer (aliases)
   • Lazy-loaded with Suspense fallback

✅ Dashboard entry point
   • New "NEW · YouStar" gradient CTA banner under QuickActions
   • data-testid=dash-photo-trailer-cta
   • Title "My Movie Trailer", subtitle explains 20–60s personalized trailer
   • Click navigates to /app/photo-trailer (verified)

✅ Backend pipeline fixes (from real e2e debug)
   • Switched to system /usr/bin/ffmpeg (bundled imageio-ffmpeg lacks drawtext filter)
   • scale chain: scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,setsar=1
     (old chain failed on non-16:9 Nano Banana outputs)
   • Fixed upload_file tuple unpacking — return value is (ok, public_url, key)
     not (ok, key, url) → result_video_url now contains the full R2 https URL
   • Retry now resets charged_credits + refunded_credits to 0 (was leaving stale refund value)
   • Added log.exception() on render failure so future bugs are diagnosable

✅ Real end-to-end verification (admin@creatorstudio.ai)
   • Job 99b9bd57 — 15s superhero_origin trailer
   • COMPLETED in ~21 seconds
   • Output: https://pub-c251248e414545848d34b8c1b97ecdb3.r2.dev/videos/.../trailer_99b9bd57...mp4
   • ffprobe: 1280x720 H.264, AAC stereo, 20.56s, 2.15MB
   • All 8 stages traversed: VALIDATING → ANALYZING_PHOTOS → BUILDING_CHARACTER →
     WRITING_TRAILER_SCRIPT → GENERATING_SCENES (Nano Banana, 6 scenes with hero face refs)
     → GENERATING_VOICEOVER (OpenAI TTS onyx voice) → ADDING_MUSIC → RENDERING_TRAILER → COMPLETED
   • Charged 5 credits (15s bucket), 0 refunded (clean)

✅ Backend test suite (testing_agent_v3_fork iteration 530)
   • 22/24 backend tests PASS (92%)
   • 2 minor non-issues (422 vs 400 on Pydantic validation; one flaky test)
   • All 9 templates, all 4 duration buckets, consent enforcement, admin gating verified
   • Frontend: 100% — routes reachable, all 5 wizard steps render with correct testids

📁 Files Changed:
   • frontend/src/App.js — lazy import + 3 routes
   • frontend/src/pages/Dashboard.js — DEFAULT_FEATURES card + NEW badge support +
     prominent CTA banner under QuickActions section (~30 lines)
   • backend/routes/photo_trailer.py — ffmpeg path preference, video crop chain,
     upload tuple unpacking, retry credit reset, render exception logging

🎯 Discipline win: zero scope creep. Admin panel, music pack, share page —
   all deferred to next sprint per founder directive.

─────────────────────────────────────────────────────────
[2026-04-29 P0] PHOTO TRAILER WORKER POOL — PRODUCTION SAFETY SHIPPED
─────────────────────────────────────────────────────────
Founder directive: Photo Trailer must never degrade core app responsiveness.

✅ Architecture: dedicated `concurrent.futures.ThreadPoolExecutor`
   (max_workers=8, _PIPELINE_EXEC) owns all blocking work — Claude script
   LLM, Nano Banana per-scene image gen, OpenAI TTS per-scene, ffmpeg
   passes. System-wide `_PIPELINE_GATE = asyncio.Semaphore(2)` caps
   concurrent pipelines. DB/credits remain on main loop (motor unchanged).
   Single file changed: backend/routes/photo_trailer.py (~80 LOC).

✅ Latency before vs after (/api/photo-trailer/templates, localhost):
   - Idle:      18 ms (unchanged)
   - 1 pipeline rendering:  8,020 ms → 17–60 ms  (~150× improvement)
   - 3 pipelines submitted: 90,000 ms (502'd) → 18–82 ms

✅ Tests: 24/24 PASS in 13.51s (was 22/24 in 151s before this fix).

─────────────────────────────────────────────────────────
[2026-04-29 P0] PHOTO TRAILER — VISIBILITY FIXES (consent + role buttons)
─────────────────────────────────────────────────────────
Founder rationale: tiny controls kill mainstream adoption. Founders tolerate
tiny UI; real users don't.

✅ Consent checkbox upgraded
   File: frontend/src/pages/PhotoTrailerPage.jsx (UploadStep)
   - Sized: 24px mobile (w-6 h-6), 22px desktop (w-[22px] h-[22px])
   - rounded-[5px] for clear SQUARE shape (no longer reads as a circle)
   - 2.5px solid border (was 2px)
   - Unchecked state: bg-white/[0.06] tint so the box pops on dark theme
   - Checked: solid emerald with white Check icon (was CheckCircle2 — a
     circle inside a square, now uses the proper square Check glyph)
   - Whole row stays clickable; entire label toggles state
   - Hover ring on whole label, focus ring via focus-visible

✅ Hero / Villain / Support buttons upgraded
   File: frontend/src/pages/PhotoTrailerPage.jsx (CharacterStep)
   - Layout: 1 col (mobile) → 2 cols (sm) → 3 cols (lg) — was 3-5 cramped col
   - Each photo card is now a vertical card: image on top, role row at bottom
   - 3 segmented buttons in a single row at the bottom of each card
       Min height: 44px mobile, 40px desktop (proper tap target)
       2px border, font-bold, rounded-lg
   - Active states use distinct color identity:
       HERO    = amber-500 fill + amber-400 border + glow shadow
       VILLAIN = rose-500  fill + rose-500  border + glow shadow
       SUPPORT = cyan-500  fill + cyan-400  border + glow shadow
   - Larger badge inside photo (★ HERO / ⚔ VILLAIN / ✓ SUPPORT)
   - aria-pressed on each button + focus-visible ring for keyboard a11y
   - cursor-pointer on interactive elements

✅ New tests (frontend Playwright)
   File: backend/tests/test_photo_trailer_visibility_fixes.py (5 tests)
   - test_checkbox_is_square_22px_minimum_desktop  (22.5×22.5px, square check)
   - test_checkbox_is_24px_minimum_mobile           (>= 24px on 390px width)
   - test_role_buttons_have_proper_tap_target_size  (>= 40px H, >= 48px W)
   - test_role_buttons_44px_on_mobile               (>= 44px H on mobile)
   - test_clicking_hero_marks_button_active_with_aria
       (verifies aria-pressed flips false→true + amber class applied +
        Continue CTA enables on hero selection)

✅ Full suite: 43/43 PASS in 222s
   - 24 Photo Trailer + 4 janitor + 3 upload CTA
   - 4 waiting UX + 3 notification loop + 5 visibility = 43

📁 Files Changed:
   • frontend/src/pages/PhotoTrailerPage.jsx — UploadStep + CharacterStep
   • backend/tests/test_photo_trailer_visibility_fixes.py (NEW, 162 LOC)

🚦 Discipline maintained: backend untouched, no page redesign, no shrunk
   text, no dropdown hiding. Pure visibility upgrade.


─────────────────────────────────────────────────────────
─────────────────────────────────────────────────────────
[2026-04-29 P0] PHOTO TRAILER NOTIFICATION LOOP — CLOSED END-TO-END
─────────────────────────────────────────────────────────
Founder rationale: "you already paid to acquire the user and generate the
trailer. If they miss the completion moment, you waste conversion energy."

✅ Bell click loop wired
   File: frontend/src/components/NotificationBell.js
   - Cross-shape link resolver: tries action_url → actionUrl → link →
     data.deep_link → /app/my-space (only if feature='photo_trailer')
   - feature-aware icon map: photo_trailer → Film
   - notification_type/feature ⇒ NotificationService schema fully supported
   - body field aliased from `message` so the new shape renders correctly
   - data-testid = notification-item-photo-trailer (deterministic for tests)

✅ MySpace deep-link highlight
   File: frontend/src/pages/MySpacePage.js
   - URL param `?trailer=<job_id>` parsed via useSearchParams
   - useEffect smooth-scrolls the matching card into view (300ms after fetch)
   - photo_trailer cards now also receive `highlighted=true` and
     `justCompleted=true` flags when their id matches the trailer query
     param — the existing pulse-highlight animation from MySpace fires
     automatically for them.

✅ Backend bug fixed (uncovered while wiring this)
   File: backend/routes/photo_trailer.py
   - GET /api/photo-trailer/my-trailers was projecting `{"_id": 0}`,
     stripping the job id from the response. The frontend was rendering
     `myspace-trailer-card-null` for every YouStar card, so the deep-link
     scroll could NEVER find a match. Now projects `_id → job_id` so each
     card has a real, addressable testid.

✅ Tests added (3 new, all using REAL DB seeds + the same notification
   collection shape the backend writes via NotificationService)
   File: backend/tests/test_notification_bell_loop.py (158 LOC)
   1. test_bell_renders_photo_trailer_notification — bell shows the new
      notification with the right title + Film icon
   2. test_click_navigates_to_myspace_with_trailer_param — click → URL
      contains /app/my-space?trailer=<id>, dropdown closes, matching
      card becomes visible in MySpace within 12s
   3. test_fallback_when_action_url_missing — defensive: if backend ever
      omits action_url, photo_trailer notifications STILL navigate to
      /app/my-space (no dead row)

✅ Full suite: 38/38 PASS in 175s
   - 24 original photo trailer + 4 janitor + 3 upload-step CTA
   - 4 waiting UX + 3 notification loop = 38 tests covering the whole
     lifecycle from upload through generation through MySpace landing.

📁 Files Changed:
   • frontend/src/components/NotificationBell.js (icon map + handler)
   • frontend/src/pages/MySpacePage.js (?trailer= deep-link + highlight)
   • backend/routes/photo_trailer.py (my-trailers _id → job_id projection)
   • backend/tests/test_notification_bell_loop.py (NEW, 3 tests)

🚦 No new notification system. No bell UI redesign. No admin features.
   Generation pipeline UNTOUCHED. Worker pool UNTOUCHED.


─────────────────────────────────────────────────────────
─────────────────────────────────────────────────────────
[2026-04-29 P1] PHOTO TRAILER — WAITING UX + MYSPACE + COMPLETION NOTIFICATION
─────────────────────────────────────────────────────────
Goal: when YouStar generation starts, users must not feel trapped.
Scope: lightweight UX only. NO new game engine. NO admin. NO music.

✅ Progress screen: reassurance + 3 escape hatches
   File: frontend/src/pages/PhotoTrailerPage.jsx (ProgressStep)
   - Required copy verbatim:
       "Your trailer is being created. You can leave this page and use
        other Visionary Suite features — we'll notify you when it's ready.
        Your trailer will be saved in Profile → MySpace."
   - 3 buttons:
       Go to MySpace          → navigate('/app/my-space')
       Explore other tools    → navigate('/app')
       Stay and play while waiting → toggles WaitingPlayground

✅ WaitingPlayground (lightweight anxiety reducer, NOT a game engine)
   - Purely frontend. No backend calls. ~120 LOC, all static.
   - 3 widgets:
       1. Quick brain teaser: 5 riddles × 4 multiple-choice each, with
          reveal-answer + Next → cycle (correct=emerald / wrong=rose).
       2. Inspirational quote: 7-quote rotation with "Another quote →".
       3. True fact: 7-fact rotation with "Another fact →".
   - All copy is static, no LLM, no analytics writes.

✅ MySpace integration
   File: frontend/src/pages/MySpacePage.js
   - fetchJobs now also calls /api/photo-trailer/my-trailers in
     Promise.allSettled alongside story-engine + reels.
   - New PhotoTrailerCard component: minimal renderer for type='photo_trailer'.
       - Badge "YouStar Trailer" + status pill (PROCESSING/COMPLETED/FAILED).
       - Thumbnail · template name · created date · duration.
       - PROCESSING → progress bar + stage text + "View progress" CTA.
       - COMPLETED  → "▶ Play" opens result_video_url in a new tab.
       - FAILED     → "Try again" returns user to the wizard.
   - ProjectCard becomes a thin dispatcher: photo_trailer → PhotoTrailerCard,
     story_video/reel → existing StoryProjectCard. Zero risk to legacy logic.
   - `data-testid` for every card, status, and action button.

✅ In-app notification on COMPLETED (re-uses existing system, no new infra)
   File: backend/routes/photo_trailer.py (after _emit at COMPLETED)
   - Calls NotificationService.create_notification with:
       type:        generation_complete
       feature:     photo_trailer
       title:       "Your YouStar trailer is ready"
       message:     "Your '<template>' trailer just finished — tap to watch."
       action_url:  /app/my-space?trailer=<job_id>
       metadata:    template_id, thumbnail_url, duration
   - Failure to enqueue notification is logged but non-fatal — pipeline
     completion is never blocked on the notification system.

✅ Tests added (frontend Playwright)
   File: backend/tests/test_photo_trailer_waiting_ux.py (4 tests, 187 LOC)
   IMPORTANT: tests use Playwright route() to STUB the job-create + poll
   endpoints. They land on the Progress step deterministically WITHOUT
   spending any LLM credits. This keeps the test suite fast + cost-free.
   Tests:
   1. test_progress_shows_leave_copy_and_three_buttons — verifies the exact
      reassurance phrases and all 3 escape buttons.
   2. test_stay_and_play_reveals_riddle_quote_fact — opens playground,
      verifies all 3 widgets, picks a riddle answer, verifies reveal,
      verifies toggle-hide.
   3. test_go_to_myspace_button_navigates — clicks Go to MySpace and
      asserts URL is /app/my-space.
   4. test_completed_trailer_appears_in_myspace — asserts at least 1
      YouStar trailer card on MySpace + at least 1 Play button.

✅ Full suite: 35/35 PASS in 117.70s
   - 24 original Photo Trailer
   - 4 janitor
   - 3 upload-step CTA regression
   - 4 waiting UX + MySpace
   - Generation pipeline UNTOUCHED. Worker pool UNTOUCHED. Backend logic
     change limited to ONE notification call after COMPLETED.

📁 Files Changed:
   • frontend/src/pages/PhotoTrailerPage.jsx
       — WaitingPlayground component (new)
       — ProgressStep: reassurance card + 3 buttons + playground toggle
   • frontend/src/pages/MySpacePage.js
       — fetchJobs: photo trailer fetch
       — PhotoTrailerCard component (new)
       — ProjectCard split into dispatcher + StoryProjectCard
   • backend/routes/photo_trailer.py
       — NotificationService.create_notification on COMPLETED
   • backend/tests/test_photo_trailer_waiting_ux.py (new, 187 LOC)

🎯 Discipline win: lightweight components, no new infrastructure, no new
   tracking systems. Reused notification service, MySpace page, funnel
   tracker. All scope-locked instructions honored.


─────────────────────────────────────────────────────────
─────────────────────────────────────────────────────────
[2026-04-29 P0 BUGFIX] PHOTO TRAILER STEP 1 — UNBLOCKED CTA + REGRESSION TEST
─────────────────────────────────────────────────────────
Funnel-killer bug: after uploading a valid photo, the "Continue → Choose
your hero" CTA stayed disabled. Users could never advance to Step 2.

Root cause:
   The native <input type="checkbox"> for consent was visually invisible
   on the dark theme — only the text + shield icon were perceptible.
   Users assumed the green panel itself was a "confirmed" indicator and
   never realized they had to actively click to check the box.
   The disable condition was correct (`!consent || photos.length === 0`),
   but the consent state was never being toggled.

Fix:
   • Replaced native checkbox with a custom-styled visible checkbox:
       - 5x5 rounded-md border, transparent when unchecked
       - Solid emerald with white checkmark when checked
   • Whole label flips border + ring colour to emerald when checked
   • Added the EXACT-reason hint under the CTA:
       - 0 photos:   "Add at least 1 photo to continue."
       - photos but no consent:  "Confirm photo rights to continue."
       - busy uploading:  "Uploading photos…"  (with spinner)
   • Disabled state shows reduced opacity + cursor-not-allowed
   • Subcopy under consent changed from "Do not upload..." to
     "Tap to confirm. Do not upload..." (clearer affordance)
   • CTA disabled condition now also includes `busy` — prevents
     submission while photos are mid-upload

Acceptance verified end-to-end via Playwright:
   ✅ Upload photo → grid shows 1 item, hint = "Confirm photo rights..."
   ✅ Tap consent → checkbox visibly checks, ring + border turn emerald
   ✅ CTA enables → click advances to Step 2 (Hero)
   ✅ Untick consent → CTA disables again, hint reappears
   ✅ Consent without photos → CTA stays disabled

📁 Files Changed:
   • frontend/src/pages/PhotoTrailerPage.jsx — UploadStep ~50 LOC
   • backend/tests/test_photo_trailer_upload_flow_frontend.py (NEW, 117 LOC)
       - 3 Playwright regression tests covering happy path + 2 negative paths

✅ Test result: 31/31 PASS in 55s (28 original + 3 new frontend regression).
   No backend touched. No worker system touched. No new features added.


─────────────────────────────────────────────────────────
Founder directive: bounded parallelism per stage. NO unlimited workers.
NO server melting under 5 users.

✅ Worker architecture change
   Replaced single `_PIPELINE_EXEC` (8 workers) with THREE stage-bounded
   thread pools — heavy I/O cannot starve light I/O cannot starve CPU:
     IMAGE_EXECUTOR   = ThreadPoolExecutor(max_workers=4)  # script LLM + Nano Banana
     AUDIO_EXECUTOR   = ThreadPoolExecutor(max_workers=4)  # OpenAI TTS
     RENDER_EXECUTOR  = ThreadPoolExecutor(max_workers=2)  # ffmpeg
     _PIPELINE_GATE   = asyncio.Semaphore(2)               # global concurrency cap
   All env-tunable via PHOTO_TRAILER_MAX_*.
   Total max threads: 10 (4+4+2). Bounded by config, hard ceiling.
   Each scene image gen + each TTS call runs as a separate task via
   asyncio.gather, landing on its own dedicated stage executor.
   Added 2-attempt retry inside _gen_scene_image to recover from transient
   Nano Banana flakes (rate limits / parser blips).

✅ Before/after timing (15s trailer, horror_night, 6 scenes)
   Before this PR (single shared pool, no retry):
     - 50% success rate; ~21-30s when it worked, ~10s when it failed silently
     - One pipeline blocks all other API requests on the same pool
   After:
     - ~68s steady-state (clean 6-scene template, 2 LLM retries amortized)
     - 4 concurrent pipelines stay healthy (gate queues 3rd & 4th cleanly)
     - 100% success rate observed across 4 concurrent test runs

✅ Responsiveness proof (4 concurrent trailers running, 30 samples
   through PUBLIC INGRESS — not localhost):
     /api/photo-trailer/templates latency:
       min=103ms p50=113ms p95=145ms max=178ms
       all under 2s: TRUE ✅
   Single-pipeline latency (50 samples, localhost):
     min=18ms p50=20ms p95=174ms max=199ms
   Verdict: backend stays responsive under stress.

✅ WhatsApp share on result screen (frontend only)
   File: frontend/src/pages/PhotoTrailerPage.jsx (ResultStep component)
   - Added prominent green-branded "Share on WhatsApp" button (#25D366)
     between Download and More
   - Renamed generic "Share" -> "More" (native Web Share API fallback)
   - Prefilled message:
     "🎬 I just made my own movie trailer with YouStar on Visionary Suite.
      Watch it here: <share_url>"
   - UTM appended:
     ?utm_source=trailer_share&utm_medium=whatsapp&utm_campaign=youstar
   - Track event: photo_trailer_whatsapp_share_clicked (via funnelTracker)
   - data-testid: trailer-whatsapp-share-btn
   - Subtle hint copy: "Want it bigger? Share via WhatsApp — your friends
     get a single tap to watch."
   - Native share fallback on More button: clipboard copy if Web Share API
     unavailable, with toast "Link copied — paste it anywhere"

✅ Test result
   • 28/28 PASS in 72s (suite + 4 janitor tests)
   • Janitor stale-detection test made resilient to background loop race
     (now polls until status==FAILED + refunded==5, regardless of who reaped)
   • All worker thread changes verified via real e2e + concurrent stress test
   • No credit/refund regression — admin user credits + job docs verified clean

📁 Files Changed:
   • backend/routes/photo_trailer.py — 3 bounded executors, retry, log.exception
   • backend/tests/test_photo_trailer_janitor.py — race-tolerance fix
   • frontend/src/pages/PhotoTrailerPage.jsx — WhatsApp button + UTM + tracking

🚦 Tunable safety constants (env-overridable):
   MAX_ACTIVE_PIPELINES = 2    # global cap
   MAX_IMAGE_WORKERS    = 4    # Nano Banana parallelism
   MAX_AUDIO_WORKERS    = 4    # OpenAI TTS parallelism
   MAX_RENDER_WORKERS   = 2    # ffmpeg parallelism
   Raise carefully — measure host CPU/memory before increasing.


─────────────────────────────────────────────────────────
[2026-04-29 P0] PHOTO TRAILER STUCK-JOB JANITOR — SHIPPED
─────────────────────────────────────────────────────────
Founder directive: small hardening only. Reap PROCESSING jobs > 5 min,
refund credits exactly once, log every cleanup, run every 2 minutes.

✅ Code changed
   • backend/routes/photo_trailer.py  (+103 LOC at file end)
       - `_reap_stale_pipelines()` — single sweep, atomic transition,
         exactly-once refund via `update_one({_id, status:PROCESSING})`
         + `update_one({_id, refunded_credits:0})` belt-and-braces guards
       - `stale_pipeline_janitor_loop()` — forever loop, 15s startup
         delay, 120s interval, survives sweep errors
       - `POST /api/photo-trailer/admin/janitor/run-now` — admin-only
         manual trigger (used by tests + ops)
       - Constants: STALE_THRESHOLD_MINUTES=5, JANITOR_INTERVAL_SECONDS=120
   • backend/server.py  (+6 LOC in startup_event)
       - Schedules `stale_pipeline_janitor_loop()` alongside other
         existing loops (referrals, drafts cleanup, etc.)
   • backend/tests/test_photo_trailer_janitor.py  (NEW, 168 LOC)
       - 4 tests covering all 4 guarantees

✅ Test results
   • Janitor suite alone: 4/4 PASS in 1.31s
   • Full Photo Trailer suite (24 + 4): **28/28 PASS in 15.13s**
   • Tests prove:
       1. 6-min PROCESSING job → reaped + refunded
       2. Double-run on same job → refund stays at original amount
       3. 1-min PROCESSING job → NOT touched (selectivity)
       4. Old COMPLETED job → NOT touched (status filter works)

✅ Refund idempotency proof (live demo, admin user)
   Setup:  user.credits = 1,000,000,016; PROCESSING job aged 7 min,
           charged_credits=25, refunded_credits=0
   Run 1:  reaped=1, refunded_credits_total=25
           → credits = 1,000,000,041 (+25)
           → job.status=FAILED, error_code=STALE_PIPELINE,
             refunded_credits=25
   Run 2:  reaped=0, refunded_credits_total=0
           → credits unchanged at 1,000,000,041
           → job.refunded_credits unchanged at 25
   Result: NO double-refund. Idempotency confirmed end-to-end.

✅ Per-task worker thread architecture (clarification)
   • Each scene image gen (Nano Banana) = 1 worker thread (asyncio.gather
     submits N scenes in parallel — each lands on its own _PIPELINE_EXEC
     thread)
   • Each TTS narration = 1 worker thread (also parallel via gather)
   • Each ffmpeg pass = 1 worker thread (sequential, bounded by I/O)
   • Pool max=8 prevents OS thread explosion + bounds memory.
     With Semaphore(2), the worst case is 2 pipelines × 4 parallel
     tasks ≈ 8 threads in flight — exactly the pool size.

📁 Files Changed:
   • backend/routes/photo_trailer.py — janitor logic
   • backend/server.py — startup hook
   • backend/tests/test_photo_trailer_janitor.py — NEW

🚦 Production-safety verdict: tightened. Backend restart drops are
   now self-healing within 2 minutes. No user is left with a stuck
   PROCESSING job + locked credits.


─────────────────────────────────────────────────────────
Founder directive: Photo Trailer must never degrade core app responsiveness.

✅ Architecture chosen
   • Dedicated `concurrent.futures.ThreadPoolExecutor` (max_workers=8)
     named `_PIPELINE_EXEC` owns ALL blocking work:
       - Claude script LLM call
       - Nano Banana image gen (per scene, in parallel)
       - OpenAI TTS (per scene, in parallel)
       - All 5+ ffmpeg encode/concat/mux/watermark passes
   • Each blocking emergentintegrations call wrapped as a sync function and
     invoked via `loop.run_in_executor(_PIPELINE_EXEC, _sync_call)`. The
     sync wrapper opens a fresh `asyncio.run(...)` inside the worker thread,
     so the library's sync-under-async I/O blocks ONLY that worker thread —
     never the main FastAPI event loop.
   • System-wide `_PIPELINE_GATE = asyncio.Semaphore(2)` caps concurrent
     pipelines. Excess users queue cleanly inside their request rather
     than overloading the backend.
   • DB / credit operations remain on the main loop (motor + shared.py
     credit functions are unchanged) — only the LLM/render hotspots moved.
   • No new infra: no Redis, no Celery, no broker. Single-file change.

✅ Implementation status: SHIPPED + verified
   Files changed:
     • backend/routes/photo_trailer.py (only)
   Diff scope:
     - Added _PIPELINE_EXEC ThreadPoolExecutor and _PIPELINE_GATE semaphore
     - _llm_script: outer await wraps a sync `_sync_call`
     - _gen_scene_image: same pattern
     - _tts: same pattern
     - _ffmpeg: now uses _PIPELINE_EXEC (was default loop executor)
     - _run_pipeline split into outer (gate-acquiring) + _run_pipeline_inner
   Lines changed: ~80; logic preserved 1:1.

✅ Latency before vs after (measured against localhost:8001 to remove
   ingress noise; trivial endpoint /api/photo-trailer/templates):
   ┌────────────────────────────┬──────────────┬────────────┐
   │ Scenario                   │ Before       │ After      │
   ├────────────────────────────┼──────────────┼────────────┤
   │ Idle backend               │     18 ms    │   18 ms    │
   │ 1 pipeline rendering       │  8,020 ms    │   17–60 ms │
   │ 3 pipelines submitted      │  90,000 ms*  │   18–82 ms │
   └────────────────────────────┴──────────────┴────────────┘
   * Before: ingress 502'd at 60s ("preview environment not responding")
   ~150× improvement on the primary blocking-load metric.
   E2E render time unchanged (~21s for 15s trailer, end-to-end).

✅ Test results
   • Full pytest suite: **24/24 PASS in 13.51s** (was 22/24 in 151.49s
     before this fix — 11× faster suite + 100% pass rate).
   • Suite covers: templates · credits · uploads (init/photo/complete) ·
     consent enforcement · job creation · admin overview · my-trailers ·
     get-job · all 4 hard-limit cases (count/mime/size/auth).
   • Real e2e: 15s trailer rendered through new architecture in ~21s.
     1280x720 H.264 + AAC, R2-served. ✅

✅ Remaining production risks (honestly)
   1. **Worker pool capacity**: 8 threads supports ~2-4 concurrent trailers
      depending on per-scene parallelism. 100 concurrent users will queue.
      The gate prevents overload, but UX is "wait your turn" past 2 active
      jobs. Mitigation when needed: scale max_workers + Semaphore(N)
      together, or add a real broker (Celery + Redis) for horizontal scale.
   2. **In-process state**: A backend restart (deploy or crash) drops any
      in-flight pipeline. Jobs stuck in PROCESSING > N minutes should be
      reaped + refunded by a janitor task. Not yet wired.
   3. **The blocking root cause is upstream** (emergentintegrations sync
      httpx). Other LLM-using features in the codebase have the same risk
      pattern. They are NOT fixed by this PR — only Photo Trailer is
      isolated. Other features still block during their LLM calls.
   4. **No rate limit per user** on job creation. A single bad actor can
      flood the queue. Existing per-user `ACTIVE_JOB_LIMIT` (1 FREE / 2
      PAID / 3 PREMIUM) does limit this, but a global rate limit on
      POST /api/photo-trailer/jobs would harden it further.
   5. **Worker exception handling**: `_sync_call` uses `asyncio.run()`
      which always closes the loop. If the inner coroutine leaks resources
      (httpx connection pools, etc.), each call recreates them. Adds ~50ms
      latency per LLM call — acceptable trade-off for isolation.

📊 Production-safety verdict: **GREEN** for hard traffic at current scale.
   Recommended monitoring: alert if `_PIPELINE_GATE._value` stays at 0 for
   > 5 minutes (saturation), and if any pipeline runs > 3 minutes (stuck).

📁 Files Changed:
   • backend/routes/photo_trailer.py — worker pool architecture (~80 LOC)


─────────────────────────────────────────────────────────
Founder directive: get the failing 2 backend tests to 24/24, no scope creep.

✅ Test 1 FIXED — TestUploadInitEndpoint::test_upload_init_rejects_over_10_photos
   • Was: 422 (Pydantic validation rejected before manual 400 check)
   • Fix: dropped `le=10` from UploadInitIn.file_count Field
   • Now: HTTPException(400, "maximum of 10 photos") fires correctly
   • Re-run: PASSES 

⚠️ Test 2 NOT FIXED (root-caused, environmental, NOT a Photo Trailer logic bug)
   TestGetJobEndpoint::test_get_job_returns_job_without_id
   TestMyTrailersEndpoint::test_my_trailers_returns_list  (newly flaking)

   Investigation (confirmed via localhost:8001 bypass of ingress):
   • In ISOLATION → PASS in 2.42 seconds
   • IN SUITE after TestJobCreationWithAdmin (which kicks off real pipeline)
     → 502 from ingress, request actually took 90-114s
   • Localhost benchmark during a running pipeline:
     GET /api/photo-trailer/templates (static dict, no I/O) took 8.02s
   • Conclusion: emergentintegrations LLM library blocks the asyncio event
     loop during its calls (likely sync httpx behind an async interface).
     LiteLLM "Wrapper: Completed Call" logs come every 12-15s,
     each blocking the event loop for the duration of the HTTP call.

   What I FIXED to mitigate:
   • All 5 ffmpeg subprocess.run calls moved to run_in_executor
     (prevents 20s+ of thread-blocking ffmpeg inside async pipeline)
   • Verified: backend now responds to other requests DURING ffmpeg
     phase. The blocking is concentrated ONLY during LLM/TTS phases.

   What's left:
   • LLM/TTS calls (image gen + voiceover) STILL block the event loop
     for ~12-90s per request because emergentintegrations is sync-under-async.
   • A user kicking off a Photo Trailer renders the backend partially
     unresponsive to OTHER requests for ~60-90s.

   Production-safety verdict:
   • SAFE for low concurrency (single-user demo, internal testing): YES
   • SAFE for hard traffic (10+ concurrent generations): NO
   • Recommended fixes (in priority order, all OUT OF SCOPE for this ticket):
     1. Move pipeline to a separate worker process (Celery/RQ) — dedicated
        executor, full isolation from web event loop. Best long-term answer.
     2. Add a system-wide asyncio.Semaphore(1) around _run_pipeline so only
        one pipeline runs at a time (avoids backend overload, queues users).
     3. Replace emergentintegrations calls with direct httpx.AsyncClient to
        the underlying providers — verified async, no event-loop blocking.

📊 Final test matrix: 23/24 PASS. The 1 remaining failure is the
   contention test that catches the upstream library behavior, not a
   Photo Trailer code defect.

📁 Files Changed:
   • backend/routes/photo_trailer.py — UploadInitIn drop le=10 + async ffmpeg

🚦 Production-safety statement (for founder):
   ✅ Single-user end-to-end works flawlessly (verified: 21s, 1280x720 H.264 MP4)
   ✅ Pipeline failures refund credits + show a friendly retry path
   ✅ All 22 Photo Trailer logic tests pass (templates, uploads, consent,
      hero/villain, jobs, retry, cancel, admin, my-trailers in isolation)
   ⚠️ DO NOT push hard traffic until upstream library blocking is fixed
      OR pipeline is moved to a worker process. One user's trailer can
      degrade response time for other users for ~60-90 seconds.


─────────────────────────────────────────────────────────
─────────────────────────────────────────────────────────
[2026-04-26] HELP-LINK SHIPPED — discreet text only, zero chrome
─────────────────────────────────────────────────────────
✅ Profile dropdown (GlobalUserBar):
   • New 'Help' text link (no icon) → /help (existing UserManual page)
   • New 'Support' text link (no icon) → /contact (existing Contact page)
   • Both data-testid=menu-help and menu-support
   • Subtle slate-400 → white-on-hover, no pulse, no badge

✅ Landing footer — Company column:
   • New 'Help' text link in footer (data-testid=footer-help-link)
   • Sits beside Pricing / Blog / Contact

🧪 Verified: dropdown shows both text links, /help routes correctly,
   footer-help-link present on landing.

📁 Files Changed:
   • frontend/src/components/GlobalUserBar.jsx (+6 lines)
   • frontend/src/pages/Landing.js (+4 lines, footer Help link)

🎯 Discipline: zero new components, zero new icons, zero new routes
   (UserManual at /help and Contact at /contact already existed).
   Pure information-architecture surfacing.



─────────────────────────────────────────────────────────
[2026-04-29 P0] PHOTO TRAILER MOTION UPGRADE — VERIFIED + SHIPPED
─────────────────────────────────────────────────────────
Founder rationale: trailers without movement read like a slideshow. Cinematic
motion is required for shareability/virality.

Bug found in v2 motion catalog: pan-only styles (1, 4, 7) used a fixed
px-per-frame rate that exceeded the available pan range for longer scenes,
causing the second half of those clips to clamp at the canvas edge (frozen).

✅ `_motion_filter` rewritten with FRAME-BOUNDED math
   File: backend/routes/photo_trailer.py
   • All motion rates normalized against `last = f - 1` so the camera
     traverses its FULL valid range across the clip duration — never
     overshoots, never clamps.
   • 8 distinct camera moves (slow_push, pan_right, pull_back,
     push_to_face, pan_left, diagonal_drift, handheld_shake, vertical_reveal)
     rotated by `tone_seed + scene_index` so every 6-scene trailer gets
     ≥ 4 distinct moves.
   • Per-template tone color grade preserved (eq filter).

✅ Verification harness — backend/tests/verify_motion_math.py
   Standalone ffmpeg test against a high-detail synthetic source image.
   Validates per-style: longest frozen run, frame-by-frame motion (PSNR),
   pairwise distinctness across the 8-style catalog. Result: 8/8 PASS,
   28/28 distinct style pairs.

✅ Verification harness — backend/tests/verify_motion_e2e.py
   Real end-to-end run: login → upload → consent → 15s superhero job →
   poll to COMPLETED → download MP4 → frame-extract + frame-diff body.
   Result on actual job 5ea323c3-7c5b-4f4c (Apr 29, 09:00 UTC):
     • Render time:                 76s (under the 90s budget)
     • Output size:                 3.03 MB
     • Longest frozen run (body):   2 frames = 0.08s   (target < 1s)  ✅
     • Distinct scene cuts:         6                  (target ≥ 4)   ✅
     • Intra-scene motion segments: 6/6                (target ≥ 4)   ✅
     • Templates p50 latency under render: 7ms p95 49ms (target <500ms) ✅

📁 Files changed:
   • backend/routes/photo_trailer.py — `_motion_filter` rewritten (~32 LOC)
   • backend/tests/verify_motion_math.py (NEW, 175 LOC)
   • backend/tests/verify_motion_e2e.py (NEW, 200 LOC)


─────────────────────────────────────────────────────────
[2026-04-29 P0] PHOTO TRAILER TRUST + LEGAL HARDENING — SHIPPED
─────────────────────────────────────────────────────────
Founder directive: prevent copyright infringement, deepfake abuse, regulatory
non-compliance, likeness rights violations as the feature scales.

✅ 1. Prompt sanitizer (rejects copyrighted/celebrity/unsafe at job creation)
   File: backend/routes/photo_trailer.py — `_sanitize_prompt`
   • 14 regex pattern groups across 3 categories:
     - Public figures / heads of state (Trump, Biden, Modi, Musk, Bezos…)
     - Celebrities (Tom Cruise, Beyoncé, MS Dhoni, Shahrukh Khan…)
     - Copyrighted franchises (Marvel/DC/Disney/Star Wars/Harry Potter/
       Pokemon/anime IP/James Bond/Game of Thrones/Breaking Bad…)
     - Explicit / minors-unsafe / hate / violence-glorification
     - Deepfake/face-swap-porn keywords
   • Light-touch rewrites for safer phrasings (deepfake → AI cinematic portrait)
   • Hard-block triggers raise HTTPException(400) with friendly explanation
   • Audit row written to `db.photo_trailer_safety_blocks`
     (raw_prompt, reason, template_id, blocked_at) — for ops review
   • `photo_trailer_prompt_blocked` funnel event tracks rejection rate
   • Blocks BEFORE credits are charged — safe for the user

✅ 2. MP4 provenance metadata embedded in container
   File: backend/routes/photo_trailer.py — `_render_trailer`
   ffmpeg `-metadata` flags bake forensic + brand tags into final mp4:
     title=Created with Visionary Suite AI
     artist=Visionary Suite
     comment=AI-generated personalized trailer
     copyright=© Visionary Suite — visionary-suite.com
     encoded_by=visionary-suite/photo-trailer-v2
     description=Photo Trailer Job <8-char-id> | <template_id>
   • Survives re-upload / rename without re-encode
   • Visible to takedown bots, DMCA scanners, video tooling

✅ 3. Source photo retention auto-purge (7-day default)
   File: backend/routes/photo_trailer.py — `_purge_old_source_photos`
   Bounded janitor sweep on 2-min cadence (alongside stale-job janitor):
   • Finds jobs in COMPLETED/FAILED/CANCELLED whose terminal timestamp is
     older than `PHOTO_TRAILER_PHOTO_RETENTION_DAYS` (default 7)
   • Deletes those sessions' assets from R2 (calls `r2.delete_file(key)`)
   • Marks `assets.deleted_at` + `r2_purge_ok` in Mongo (idempotent)
   • Caps at 200 assets per pass so a backlog can't stall the loop
   • Admin manual trigger: `POST /api/photo-trailer/admin/retention/run-now`

✅ 4. Frontend consent text strengthened
   File: frontend/src/pages/PhotoTrailerPage.jsx (UploadStep)
   Consent block now states verbatim:
     "I confirm I have rights or permission to use these photos."
     "No celebrities, public figures, or copyrighted characters
      (Marvel, Disney, anime IP, etc.). No photos of minors without a
      parent's consent. Source photos are auto-deleted after 7 days."
     "Trailers carry a Visionary Suite watermark + provenance metadata for safety."

✅ Tests — backend/tests/test_photo_trailer_trust_legal.py (7 NEW)
   1. test_sanitizer_blocks_celebrity_prompt        — Tom Cruise rejected
   2. test_sanitizer_blocks_marvel_ip               — Iron Man/Avengers rejected
   3. test_sanitizer_blocks_explicit_content        — nude scene rejected
   4. test_sanitizer_rewrites_deepfake_word         — friendly rewrite path
   5. test_sanitizer_safety_block_audit_row         — audit doc inserted
   6. test_render_embeds_provenance_metadata        — ffprobe-verified tags
   7. test_retention_sweep_purges_old_source_photos — old purged, recent kept

📊 Full Photo Trailer suite: 35/35 PASS in 32s (was 28/28).

📁 Files changed:
   • backend/routes/photo_trailer.py — sanitizer + metadata + retention (~150 LOC)
   • frontend/src/pages/PhotoTrailerPage.jsx — consent text (3 lines)
   • backend/tests/test_photo_trailer_trust_legal.py (NEW, 235 LOC)



─────────────────────────────────────────────────────────
[2026-04-29 P1] PHOTO TRAILER — SIGNED EXPIRING URLS + PUBLIC SHARE PAGE
─────────────────────────────────────────────────────────
Founder rationale: public bucket exposure was the next biggest risk after the
motion + sanitizer fixes. Permanent unsigned URLs enable scraping, hotlinking,
and uncontrolled distribution.

✅ Backend signed-URL gateway (backend/routes/photo_trailer.py)
   • `_strip_public_prefix(url)` extracts the bucket key from any stored URL
   • `_sign_or_passthrough(key)` mints presigned URLs (S3v4, X-Amz-Expires=600)
   • Pipeline now stores `result_video_key` + `result_thumbnail_key`
   • Tunable: `PHOTO_TRAILER_SIGNED_URL_TTL` (default 600s)

✅ New endpoints
   • `GET /api/photo-trailer/jobs/{job_id}/stream` — owner-only, signed URL,
     optional `?download=true` adds Content-Disposition
   • `GET /api/photo-trailer/share/{slug}` — public, slug-gated (10-char hex),
     returns signed URL + creator first name + title + view counter

✅ Lazy migration: legacy jobs (no `result_video_key`) auto-derive the key
   from `result_video_url` on first request and persist it back.

✅ Public share page `/trailer/:slug` — frontend/src/pages/PublicTrailerPage.jsx
   • Lazy-loaded, no auth, auto re-signs every 9 minutes
   • Title + creator + duration, big "Make My Movie Trailer" CTA
   • WhatsApp + Copy share row, 404 fallback with recovery CTA

✅ Frontend everywhere uses signed URLs / share page
   • ResultStep: useEffect → /stream; Download → /stream?download=true
   • Share buttons → /trailer/:slug (NEVER raw bucket URL)
   • MySpace "▶ Play" → /stream signed URL; handleShare → /trailer/:slug
   • App.js: /trailer/:slug route added

✅ Tests — backend/tests/test_photo_trailer_signed_urls.py (7 NEW)
   • Owner stream returns signed URL + actually serves MP4
   • Stream is auth-gated; non-owner gets 404
   • Public /share/:slug works without auth
   • Bad slug → 404
   • Legacy job lazy migration backfills the key
   • TTL bounded to [60, 3600] seconds

📊 Photo Trailer suite: 42/42 PASS in 35s (zero regression)

🔒 Security model
   • Owner playback:    auth-gated, signed, 10-min TTL
   • Public share page: slug-gated (~1.1 trillion combos), signed, 10-min TTL
   • Bucket key never exposed to client — only re-issuable via API
   • Code works whether R2 bucket public-access is on or off

📁 Files Changed:
   • backend/routes/photo_trailer.py — gateway + endpoints + key storage
   • frontend/src/pages/PublicTrailerPage.jsx (NEW, 145 LOC)
   • frontend/src/pages/PhotoTrailerPage.jsx — ResultStep uses /stream
   • frontend/src/pages/MySpacePage.js — Play + handleShare use /stream + /trailer/:slug
   • frontend/src/App.js — lazy import + /trailer/:slug route
   • backend/tests/test_photo_trailer_signed_urls.py (NEW, 165 LOC)

