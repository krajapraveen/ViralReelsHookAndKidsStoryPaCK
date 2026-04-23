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

## North-Star Metric — April 23, 2026
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

