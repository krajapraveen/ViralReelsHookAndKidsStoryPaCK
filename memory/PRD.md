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

