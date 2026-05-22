# Visionary Suite — Architecture Reference

> Production: **https://www.visionary-suite.com**
> Preview: **https://trust-engine-5.preview.emergentagent.com**
> Generated: 2026-05-24 — sourced directly from `/app` codebase.

This document is the **canonical architecture reference** for the platform. Section ordering: top-down (system → feature).

---

## 1. High-Level System Architecture

```
                         ┌─────────────────────────────────────┐
                         │  CDN (Cloudflare) + edge SSL/WAF    │
                         │  visionary-suite.com                │
                         └───────────────┬─────────────────────┘
                                         │
                              ┌──────────┴──────────┐
                              │                     │
                ┌─────────────▼────────────┐ ┌──────▼──────────────────┐
                │  React SPA (port 3000)    │ │  FastAPI API (port 8001) │
                │  /app/frontend            │ │  /app/backend            │
                │  • Lazy-loaded routes     │ │  • 166 route modules     │
                │  • Shadcn UI + Tailwind   │ │  • 78 service modules    │
                │  • react-router v6        │ │  • slowapi rate-limit    │
                │  • Custom contexts        │ │  • CORS + security mw    │
                └─────────────┬─────────────┘ └──────┬──────────────────┘
                              │ REACT_APP_BACKEND_URL│
                              │ (all routes /api/*)  │
                              └──────────┬───────────┘
                                         │
                          ┌──────────────┼──────────────┐
                          │              │              │
                ┌─────────▼───┐  ┌───────▼──────┐  ┌────▼──────────────┐
                │  MongoDB    │  │ Cloudflare R2│  │ Background workers │
                │  ~290 colls │  │ (S3-compat   │  │ • BackgroundTasks  │
                │  Motor      │  │  object store│  │ • Pipeline engine  │
                │  async      │  │  + presigned │  │ • Self-healing     │
                └─────────────┘  └──────────────┘  └────────────────────┘
                                                          │
                                  ┌───────────────────────┼──────────────────┐
                                  │                       │                  │
                          ┌───────▼──────┐      ┌─────────▼─────┐    ┌───────▼──────┐
                          │ Emergent LLM │      │ Cashfree pay  │    │ Google Ads / │
                          │ • OpenAI     │      │ • orders      │    │ GA4 / Meta   │
                          │ • Gemini     │      │ • subs        │    │ Pixel        │
                          │ • Claude     │      │ • webhooks    │    │ • conv tags  │
                          │ • Sora 2     │      └───────────────┘    └──────────────┘
                          │ • Nano Banana│
                          │ • Whisper    │
                          └──────────────┘
```

**Runtime topology**: Kubernetes pod with supervisord managing 2 long-lived processes (`backend`, `frontend`). MongoDB is in-cluster. R2 is external. All third-party APIs are HTTPS.

---

## 2. Tech Stack

| Layer | Tech |
|---|---|
| Frontend framework | React 18, react-router 6 (lazy routes), Vite/CRA build |
| Frontend UI | Tailwind, Shadcn/UI (`/app/frontend/src/components/ui/*`), lucide-react, sonner toasts, framer-motion |
| Frontend state | React Context (CreditContext, NotificationContext, MediaEntitlementContext, FeedbackContext, ProductGuideContext, TourProvider) |
| Frontend auth | JWT in localStorage + Google OAuth (`@react-oauth/google`) |
| Backend framework | FastAPI on uvicorn, slowapi rate-limit |
| Backend DB driver | Motor (async MongoDB) |
| Async jobs | FastAPI `BackgroundTasks` + custom pipeline engine + worker queues |
| Object storage | Cloudflare R2 via `boto3` (S3-compatible) |
| Auth | JWT (HS256) + bcrypt + optional Google OAuth |
| Payments | Cashfree (orders, subscriptions, webhooks) |
| Email | Resend / SendGrid (via `email_service.py`) |
| Push notifications | Web Push via VAPID keys |
| LLM gateway | `emergentintegrations` library (Universal Key) |
| Video processing | ffmpeg (static build, `/usr/local/bin/ffmpeg`) + ffprobe |
| Tracking | gtag (Google Ads + GA4), Meta Pixel |
| Build/test | pytest (boundary audits), ruff (Python), ESLint (JS) |
| CI gate | `make audit-boundaries` runs 35+ static + runtime audit suites |

---

## 3. Source-Code Topology

### 3.1 Backend (`/app/backend`)

```
backend/
├── server.py                       # FastAPI bootstrap; 167 include_router() lines
├── shared.py                       # db handle, auth helpers, credit fns
├── security.py                     # rate limiter, security headers, middleware
├── ml_threat_detection.py          # content moderation classifier
├── routes/                         # 166 modules, ~1,367 endpoints total
├── services/                       # 78 modules — business logic + integrations
├── services/story_engine/          # Modular story-video pipeline state machine
├── services/comic_pipeline/        # Comic storybook v2 pipeline
├── services/viral/                 # Viral workers (audio/image/video/packaging)
├── services/reliability/           # asset_verifier, completion_invariant, render_validator
├── services/rewrite_engine/        # Content-safety rewrite + safe-rewrite
├── scripts/                        # CLI tools (audit_boundaries_coverage, seeds)
└── tests/                          # 100+ test files, including 35 audit suites
```

### 3.2 Frontend (`/app/frontend/src`)

```
frontend/src/
├── App.js                          # Routes (mostly lazy), context providers
├── pages/                          # 122 page-level components
├── pages/admin/                    # Admin pages
├── components/                     # 100+ reusable components
├── components/ui/                  # Shadcn primitives
├── components/admin/               # Admin panel parts
├── components/guide/               # Onboarding/journey/AppTour
├── components/recovery/            # ErrorBoundary + recovery UI
├── components/support/             # Help & support widgets
├── contexts/                       # 5 React contexts (auth not in context — JWT in localStorage + api util)
├── utils/                          # api.js (axios + JWT), analytics, funnelTracker, etc.
└── styles + App.css                # Custom CSS vars + Tailwind
```

---

## 4. Backend Service Layer (Key Modules)

| Service | Responsibility |
|---|---|
| `credits_service.py` | Atomic credit deduct/award/refund. Source of truth for credit balance. |
| `entitlement.py` | Plan-tier entitlements (downloads, watermark, max scenes, …). |
| `idempotency_service.py` | Webhook / external-call dedup via `idempotency_keys`. |
| `cashfree_subscription_service.py` | Cashfree plan + checkout creation + sub state sync. |
| `payment_recovery_service.py` | Failed-payment retry + dunning. |
| `notification_service.py` | In-app + push + email fanout. |
| `welcome_email_service.py` | First-login email + drip. |
| `email_service.py` | Resend/SendGrid abstraction. |
| `pipeline_engine.py` | Generic job orchestrator (legacy story videos). |
| `pipeline_worker.py` | Worker loop for pipeline jobs. |
| `story_engine/pipeline.py` | New canonical story-video state machine. |
| `story_engine/state_machine.py` | INIT → PLANNING → KEYFRAMES → MOTION → TTS → ASSEMBLE → COMPLETED. |
| `story_engine/adapters/*` | LLM planning, image gen, video gen, TTS, ffmpeg assembly. |
| `comic_pipeline/job_orchestrator.py` | Comic storybook v2 orchestration. |
| `viral/workers/*` | Reaction GIF + viral pack workers (text, image, audio, video, packaging). |
| `optimized_video_renderer.py` | High-throughput ffmpeg video renderer for story video v2. |
| `media_preview_pipeline.py` | Preview MP4 generation (fast cut). |
| `reliability/render_validator.py` | Canonical ffprobe gate before COMPLETED on any video pipeline. |
| `reliability/asset_verifier.py` | Image/asset readability gate (magic bytes + size). |
| `reliability/completion_invariant.py` | Pre-COMPLETED count/state invariant; prevents false success. |
| `self_healing_core.py` + `self_healing_middleware.py` | Auto-recovery for stuck/orphaned jobs. |
| `job_recovery_service.py` | Resume / requeue interrupted jobs after restart. |
| `render_recovery_service.py` | Video-specific recovery (re-encode / fallback). |
| `revenue_protection.py` | Auto-refund + audit + admin alerts on render failures. |
| `auto_refund.py` | Generic refund executor (idempotent). |
| `cdn_optimizer.py` | R2 + Cloudflare cache headers + faststart re-mux. |
| `cloudflare_r2_storage.py` | R2 upload (multipart + presigned URLs). |
| `media_token_service.py` | Signed short-lived tokens for protected downloads. |
| `download_expiry_service.py` | Time-boxed download URL expiry + revocation. |
| `content_protection_service.py` | Watermarking + DRM-lite + abuse flags. |
| `watermark_service.py` | ffmpeg watermark renderer. |
| `personalization_service.py` | Per-user recommendation + onboarding signal. |
| `hook_scoring_engine.py` + `hook_service.py` | Viral hook scoring + storage. |
| `centralized_generation_service.py` | Generic generation entrypoint that picks pipeline by feature. |
| `retention_service.py` | Re-engagement (push, email nudges, viral milestones). |
| `cost_guardrails.py` | Per-user / per-feature daily cost ceilings. |
| `admission_controller.py` | Slot management — blocks new jobs when system saturated. |
| `priority_scaling_service.py` | Promotes priority jobs (paid users) ahead of free queue. |
| `worker_queues.py` + `multi_queue.py` + `enhanced_worker_system.py` | Internal job queue with retry/DLQ. |
| `webhook_retry_queue.py` | Persistent retry queue for outbound webhooks. |
| `database_environment_monitor.py` | Mongo health probes + write-stall detection. |
| `system_health_service.py` | Aggregated health for `/api/health/*`. |
| `database_indexes.py` | Index ensurer (run on boot). |
| `audit_log_service.py` + `audit_log.py` | Append-only admin/security audit. |
| `two_factor_auth_service.py` | TOTP + WebAuthn enrollment. |
| `anti_abuse_service.py` + `ip_security_service.py` | IP rep / OTP gating / device fingerprint. |
| `activation_truth.py` | Backend-authoritative `first_project_completed_at` for ad conversions. |
| `funnel_tracking.py` | Canonical activation-funnel event sink. |

---

## 5. Database Schemas

> MongoDB with ~290 collections. Names are stable; documents are flexible. `_id` is always excluded from API responses (Pydantic models + projections). Below: canonical schemas grouped by domain.

### 5.1 Users / Auth / Billing

```jsonc
// users
{
  "_id": ObjectId,
  "id": "uuid-str",                     // app-level id (also used as user_id everywhere)
  "email": "lowercase@x.com",
  "password_hash": "bcrypt$...",        // null for Google-only accounts
  "google_id": "...",
  "name": "...",
  "role": "USER" | "ADMIN" | "SUPER_ADMIN",
  "plan": "free" | "starter" | "pro" | "enterprise",
  "credits": 100,
  "subscription_status": "ACTIVE" | "TRIAL" | "CANCELLED" | null,
  "subscription_id": "cashfree_sub_id",
  "current_period_end": ISODate,
  "first_project_completed_at": ISODate, // P0: backend truth for Google Ads conversions
  "email_verified": true,
  "phone_verified": false,
  "two_factor_enabled": false,
  "created_at": ISODate, "updated_at": ISODate,
  "last_login_at": ISODate,
  "device_fingerprint": "...",
  "attribution": { "utm_source": "...", "utm_campaign": "...", "gclid": "...", "fbclid": "..." }
}

// credit_transactions
{ user_id, amount, type: "DEDUCT"|"AWARD"|"REFUND"|"PURCHASE", reason, reference_id, created_at }

// credit_ledger
{ user_id, balance_before, balance_after, delta, tx_type, created_at }  // idempotent ledger

// cashfree_orders / orders / payments
{ user_id, order_id, amount, currency, status, plan_id, created_at, paid_at }

// subscriptions
{ user_id, plan, status, cashfree_sub_id, current_period_start, current_period_end, cancel_at_period_end }

// subscription_payments / subscription_webhooks
{ webhook_id, event_type, payload, processed_at, idempotency_key }

// referrals / referral_codes / referral_attributions / referral_events / referral_rewards
{ inviter_user_id, invitee_user_id, code, status, reward_credits, attributed_at, paid_out }

// account_lockouts / login_attempts / sessions / user_login_activity
{ user_id, ip, ts, action, success }

// otp_codes / phone_verifications
{ user_id, code, channel, expires_at }
```

### 5.2 Generation Jobs (per feature)

```jsonc
// story_engine_jobs (canonical story-video v2)
{
  "job_id": "uuid", "user_id": "...",
  "title": "...", "story_text": "...",      // story_text stripped from list APIs
  "state": "INIT"|"PLANNING"|"KEYFRAMES"|"MOTION"|"TTS"|"ASSEMBLE"|"COMPLETED"|"FAILED"|"PARTIAL_READY",
  "style_id": "cartoon_2d", "voice_preset": "..", "age_group": "..", "quality_mode": "..",
  "episode_plan": {...}, "scene_motion_plans": [...],
  "stage_results": [{ stage, status, duration_seconds, error }],
  "keyframe_urls": [...], "output_url": "...", "thumbnail_url": "...",
  "credits_charged": 21, "cost_estimate": {...},
  "is_guest": false, "guest_ip": null,
  "character_continuity": {...}, "fallback_in_use": false,
  "created_at": ISODate, "completed_at": ISODate,
  "series_id": null, "episode_number": null, "challenge_id": null,
  "reuse_info": { parent_job_id, stages_reused: [...] },
  "error_message": null, "consistency_retry_count": 0
}

// pipeline_jobs (legacy story videos)
{ job_id, user_id, status, current_stage, progress, output_url, scenes, scene_images, scene_voices, ... }

// render_jobs (OptimizedVideoRenderer)
{ job_id, user_id, project_id, status, progress, output_url, storage_type,
  render_timing_ms, timing_breakdown, error, failed_at }

// reaction_gif_jobs
{ job_id, user_id, status: "QUEUED"|"PROCESSING"|"COMPLETED"|"FAILED",
  elapsed_seconds, retryable, refunded, output_url, error, stage, progress, created_at }

// photo_trailer_jobs, photo_trailer_outputs, photo_trailer_scenes, photo_trailer_assets
{ job_id (=_id), user_id, template_id, duration_target_seconds, status,
  current_stage, progress_percent, result_video_url, result_thumbnail_url,
  result_vertical_video_url, public_share_slug, watermark_applied, error_message }

// comic_storybook_v2_jobs
{ job_id, user_id, stages: { plan, characters, panels, layout, export }, status, panel_results,
  final_pdf_url, elapsed_seconds, retryable, refunded }

// photo_to_comic_jobs, gif_jobs, genstudio_jobs, fast_video_jobs, viral_jobs, conversion_jobs,
// brand_kit_jobs, story_generator_jobs, story_async_jobs, storybook_jobs, comix_jobs,
// reel_generator_jobs, generation_jobs, generated_videos, generated_reels, generated_stories,
// generated_content, coloring_generations, twinfinder_analyses, bio_generations, caption_rewrites,
// tone_rewrites, reply_generations
```

### 5.3 Reliability + Observability

```jsonc
// diagnostics_metrics  (daily-bucketed counters)
{ metric: "completion_invariant_failed_total", bucket: "YYYY-MM-DD", count, recent_samples: [...] }

// exception_logs
{ id, functionality, error_type, error_message, user_id, stack_trace, severity, resolved, created_at }

// self_healing_logs / self_healing_issues
{ id, issue_type, target_collection, target_id, action, outcome, created_at }

// audit_logs / admin_audit_log / security_audit_log
{ id, actor_id, action, target, before, after, ts, ip }

// health_alerts / production_alerts / system_alerts / environment_alerts
{ id, severity, kind, message, fired_at, acked_by, resolved_at }

// kill_switches
{ id, "generation_disabled" | "..." , enabled, scope, reason, updated_by, updated_at }

// rate_limits / rate_limit_logs
{ key, window, count, last_seen }

// funnel_events
{ user_id|session_id, event: "landing_view"|"hero_video_play"|"signup_completed"|
  "prompt_submitted"|"story_generation_started"|"first_generation_completed"|...,
  meta, ts, request_id }

// attribution_sessions
{ session_id, user_id, utm_*, gclid, fbclid, referrer, landing_page, first_touch_at }

// conversions
{ user_id, event: "first_project_completed"|"purchase"|..., value, currency, fired_at,
  client_id, gclid, server_authoritative: true }
```

### 5.4 Content / Social

```jsonc
// shares, share_events, video_shares, twinfinder_shares
{ user_id, asset_id, channel, share_id, ts, conversion_attribution }

// remix_lineage, remix_events
{ child_job_id, parent_job_id, depth, root_id, created_at }

// story_series, story_episode_series, story_episodes, story_chain (collection: stories /
// story_memories / story_morals / story_themes / story_templates)
{ series_id, owner_user_id, title, episodes: [{ episode_number, job_id }], ... }

// public_share_slug → photo_trailer_jobs, story_engine_jobs (for /share/<slug>)

// gallery_content / gallery_views
{ user_id, asset_id, tags, public: true, view_count }

// character_profiles, character_bibles, character_visual_bibles, character_voice_profiles,
// character_relationships, character_continuity_validations, character_memory_logs, trained_characters
{ character_id, owner_user_id, name, visual_traits, voice_preset, ... }

// world_bibles, story_morals
{ world_id, owner_user_id, lore, factions, locations }
```

### 5.5 Engagement / Retention / Gamification

```jsonc
// daily_streaks, creation_streaks, user_streaks, streaks
{ user_id, current, longest, last_date }

// daily_rewards, daily_idea_claims, daily_challenges, challenge_completions, challenge_winners
{ user_id, day, claimed, reward_credits }

// daily_wars, battle_rank_cache, battle_rank_snapshot, daily_viral_ideas
{ war_id, day, leaderboard: [...] }

// viral_milestones, viral_nudges, viral_rewards, viral_referrals, viral_assets, viral_growth_metrics
// viral_jobs, viral_job_events, viral_job_tasks, viral_feedback
{ user_id, milestone, achieved_at, ... }

// engagement_events, growth_events, feature_events
{ user_id, event, ts, meta }

// notifications, push_subscriptions, push_log, email_events, email_nudges
{ user_id, channel, kind, payload, sent_at, opened_at, clicked_at }
```

### 5.6 Storage / Media

```jsonc
// media_assets, media_access_log, asset_access_log, file_access_logs, user_files, user_assets
{ asset_id, owner_user_id, r2_key, content_type, size, expires_at }

// media_tokens
{ token, asset_id, user_id, expires_at, scope: "download"|"preview" }

// temporary_downloads
{ token, asset_id, expires_at, downloaded_at, ip }

// media_suspensions, media_abuse_flags
{ asset_id, reason, suspended_by, ts }

// content_protection_service: watermark_logs, watermark_removals, copyright_audits
```

### 5.7 Security / Anti-abuse

```jsonc
// ip_activity, blocked_ips, blocked_signups, ip_signup_tracking, ip_whitelist, ip_geo_cache,
// quarantined_ips, device_fingerprints, anti_abuse_logs, abuse_events,
// security_events, security_alerts, security_reports, security_report_events,
// security_report_notes, security_reward_claims, webhook_security_events
{ ip / fingerprint, score, last_seen, reasons: [...] }
```

### 5.8 Admin / Ops

```jsonc
// admin_actions, admin_alerts, admin_notifications, admin_audit_log
// kill_switches, system_config, scaling_events, worker_metrics, worker_telemetry, worker_jobs
// load_guard_alerts, load_tests, scheduled_tests, test_runs, request_logs
```

---

## 6. Frontend Routing & Page Map

`/app/frontend/src/App.js` defines the route table (all paths are public unless wrapped by an auth guard in the page itself).

**Auth / public**: `/`, `/login`, `/signup`, `/forgot-password`, `/reset-password`, `/verify-email`, `/auth/callback`, `/pricing`, `/contact`, `/about`, `/reviews`, `/privacy-policy`, `/terms-of-service`, `/cookie-policy`, `/copyright`, `/security`, `/security/report`, `/blog`, `/blog/:slug`, `/refer/:code`, `/share/:slug`, `/explore`, `/gallery`, `/creator/:id`, `/character/:id`, `/series/:id`, `/trailer/:slug` (PublicTrailerPage).

**App shell (`/app/*`)**: `/app` dashboard, `/app/my-space`, `/app/create`, `/app/billing`, `/app/profile`, `/app/privacy-settings`, `/app/referrals`, `/app/feature-requests`, `/app/payment-history`, `/app/subscription`, `/app/notifications-center`.

**Generators**: 
- `/app/story-video-studio` (StoryVideoPipeline.js — Story-to-Video)
- `/app/reel-generator`, `/app/bedtime-story-builder`, `/app/brand-story-builder`, `/app/comic-storybook`, `/app/comic-storybook-builder`, `/app/comix-ai`, `/app/coloring-book`, `/app/coloring-book-wizard`, `/app/instant-story`, `/app/photo-to-comic`, `/app/photo-trailer` (YouStar), `/app/photo-reaction-gif`, `/app/gif-maker`, `/app/genstudio`, `/app/youtube-thumbnail-generator`, `/app/caption-rewriter-pro`, `/app/comment-reply-bank`, `/app/instagram-bio-generator`, `/app/offer-generator`, `/app/challenge-generator`, `/app/story-hook-generator`, `/app/tone-switcher`, `/app/twin-finder`, `/app/content-engine`, `/app/content-blueprint-library`, `/app/content-challenge-planner`, `/app/story-episode-creator`, `/app/character-creator`, `/app/character-library`, `/app/character/:id`, `/app/character-consistency-studio`, `/app/create-series`, `/app/promo-videos`, `/app/daily-viral-ideas`, `/app/daily-war`.

**Viewers / Battle / Social**: `/app/story-viewer/:id`, `/app/story-battle/:id`, `/app/story-chain/:id`, `/app/story-chain-timeline/:id`, `/app/story-preview/:id`, `/app/video-reward-preview`, `/app/creator-profile`, `/app/public-creation/:id`, `/app/public-series/:id`.

**Analytics dashboards (per user)**: `/app/analytics`, `/app/story-video-analytics`, `/app/realtime-analytics`, `/app/retention`, `/app/growth`, `/app/conversion`, `/app/automation`.

**Admin (`/admin/*`)**: `/admin`, `/admin/users`, `/admin/dashboard`, `/admin/monitoring`, `/admin/security`, `/admin/security-reports`, `/admin/security-reports/:id`, `/admin/login-activity`, `/admin/referrals`, `/admin/reactions`, `/admin/activation`, `/admin/share-links`. (Components in `pages/Admin/*` + `pages/admin/*`.)

---

## 7. Critical Flows

### 7.1 Story-to-Video — Canonical Flow (state machine)

```
[Frontend] StoryVideoPipeline.js
   │  POST /api/story-engine/create  (title, story_text, animation_style, voice_preset, age_group, quality_mode)
   ▼
[Backend] routes/story_engine_routes.py::create_engine_job
   ├─ kill-switch check (KS1 generation_disabled)
   ├─ get_optional_user → user_id ('guest_<ip>' or auth uuid)
   ├─ rate_limit + admission_controller
   ├─ rewrite_engine.process_safety_check → safe story/title
   ├─ create_job → atomically inserts story_engine_jobs + deducts credits (credits_service)
   ├─ background_tasks.add_task(run_pipeline, job_id)
   └─ returns { success, job_id, credits_charged, is_guest, reuse_mode, ... }
                              │
                              ▼
[Background] services/story_engine/pipeline.py::run_pipeline
   INIT ─► PLANNING (LLM episode_plan)
         ─► KEYFRAMES (Nano Banana image gen per scene; consistency_validator + retry)
         ─► MOTION (Sora 2 video segments)
         ─► TTS (OpenAI/ElevenLabs voices)
         ─► ASSEMBLE (ffmpeg_assembly: concat + music duck + watermark + faststart)
         ─► VALIDATE (reliability/render_validator.validate_render → ffprobe gate)
         ─► COMPLETED  ← only after invariant passes; else FAILED + auto-refund
                              │
                              ▼
[Frontend] MySpacePage.js polls /api/story-engine/user-jobs (every 4s while in-progress).
   When ?projectId=<id> is in URL but the job hasn't surfaced yet, LocatingProjectCard polls
   /api/story-engine/status/<id> directly until it appears.
```

**Files:**
- Frontend: `pages/StoryVideoPipeline.js`, `pages/MySpacePage.js`, `components/ProgressiveGeneration.js`
- Backend routes: `routes/story_engine_routes.py`
- Backend pipeline: `services/story_engine/pipeline.py`, `state_machine.py`, `adapters/{planning_llm,media_gen,video_gen,tts,ffmpeg_assembly}.py`
- Reliability: `services/reliability/{render_validator,asset_verifier,completion_invariant}.py`
- DB: `story_engine_jobs`, `pipeline_jobs` (legacy), `render_jobs`, `credit_transactions`, `funnel_events`, `analytics_events`.

### 7.2 Mobile Async Generation (Cloudflare-30s bypass)

```
POST /api/generate/story/async       → { job_id, status: PENDING, request_id, poll_url, poll_interval_ms }
GET  /api/generate/story/async/<id>  → { status, progress, elapsed_seconds, result?, error? }
```
Source: `routes/generation.py`. Bypasses CF's 30s upstream timeout for mobile apps.

### 7.3 Reaction GIF (with all P0 hardening)

```
[Frontend] PhotoReactionGIF.js → POST /api/reaction-gif/start
[Backend] routes/reaction_gif.py
   ├─ uploads image → asset_verifier (magic bytes + size)
   ├─ creates reaction_gif_jobs (status QUEUED)
   └─ background worker (viral/workers/* or inline)
        ├─ honest progress updates (no fake 50%)
        ├─ HARD per-stage timeouts + janitor sweep stuck jobs
        ├─ ffmpeg/encode → asset_verifier on output
        └─ completion_invariant gate before COMPLETED
Polling: GET /api/reaction-gif/job/<id> returns enriched diagnostic payload.
On failure: auto-refund (credits_service.refund) + push notification.
```

### 7.4 Photo Trailer (YouStar) — fortified pipeline

`routes/photo_trailer.py` (2700+ lines) — stages:
```
INIT → UPLOAD_VERIFY → CONSENT → SCENE_PLAN → IMAGE_GEN → VOICE_GEN → MUSIC →
RENDER_TRAILER → validate_render → UPLOAD_R2 → VERTICAL_CUT (best-effort) →
THUMBNAIL (best-effort) → COMPLETED
```
With per-stage timeouts, `RenderValidationError` → `RENDER_INVALID` + refund. Public share slugs in `photo_trailer_jobs.public_share_slug`.

### 7.5 Payments (Cashfree)

```
[Frontend] Billing.js / Pricing.js
   POST /api/cashfree/create-order  (returns payment_session_id)
   → Cashfree Checkout (hosted)
   → user pays → Cashfree calls our webhook
[Backend] routes/cashfree_webhook_handler.py
   ├─ HMAC signature verify
   ├─ idempotency_service dedup (idempotency_keys)
   ├─ on SUCCESS: services/credits_service.award_credits or subscription upgrade
   ├─ writes payments / cashfree_orders / subscription_webhooks
   ├─ activation_truth.maybe_mark_first_project_completed (if applicable)
   └─ enqueues /api/cashfree/conversion-acknowledged for frontend to fire Google Ads tag
```
Server-authoritative: frontend cannot fake a conversion event.

### 7.6 Auth + Session

```
POST /api/auth/signup           → bcrypt hash + email verify token (Resend)
POST /api/auth/login            → JWT (HS256, 30-day exp) + login_attempts log
POST /api/auth/google           → Google OAuth ID token → upsert users → JWT
POST /api/auth/reset-password   → token-gated bcrypt rehash
GET  /api/auth/me               → returns sanitized user (no _id, no password_hash)
```
Source: `routes/auth.py`. Brute-force / device-fingerprint gating: `anti_abuse_service.py`.

### 7.7 Activation Funnel + Google Ads (Phase A complete)

```
[Frontend] utils/funnelTracker.js → POST /api/funnel-tracking/event
[Backend] routes/funnel_tracking.py → writes funnel_events
Allowed events: landing_view, hero_video_play, signup_completed, prompt_submitted,
story_generation_started, first_generation_completed, generate_clicked, return_to_inspect, ...

[Backend] activation_truth.py
   On story_engine_jobs.state → COMPLETED, atomic SET users.first_project_completed_at
   (only-set-once via $exists:false guard).
   → emits a `first_project_completed` row in conversions
   → triggers frontend acknowledgement → gtag('event','conversion').
```

### 7.8 My Space + LocatingProjectCard (P0 2026-05-24 fix)

```
[Frontend] MySpacePage.js
   GET /api/story-engine/user-jobs  (+ /api/convert/user-reels + /api/photo-trailer/my-trailers)
   normalizes statuses via __ALLOWED_LIVE / __ALLOWED_TERMINAL
   if jobs.length === 0 && URL ?projectId=<id> present:
       render LocatingProjectCard
       → polls /api/story-engine/status/<id> with 404 escalation
   else if jobs.length === 0: render "No projects yet" empty state.
```

### 7.9 Reliability/CI gate (single command)

```
$ make audit-boundaries
   pytest 35+ audit suites → 354 tests, no skipped fails
Suites cover: payload boundaries, URL trust, completion invariants, doctrine compliance,
diagnostics beacon, bug-class-elimination mandate, reaction GIF connection-loss / false-success /
honest-progress / stuck-jobs, Google Ads conversion shape, async story contract, MySpace preview
CTA, P2C event traps + style validation + object state hotfix + cache bust, strip completion
invariant, storybook next-action hooks, silent-render prevention, empty-MySpace-after-create.
```

---

## 8. Endpoint Catalog (Major Domains)

> ~1,367 endpoints in 166 routers. Domain heads + canonical paths only.

| Domain | Router file | Key endpoints |
|---|---|---|
| Auth | `auth.py` | POST `/api/auth/{signup,login,google,logout,reset-password,verify-email}` GET `/api/auth/me` |
| Anti-abuse | `anti_abuse_routes.py`, `account_lock_routes.py`, `login_activity.py` | OTP, account lock, login activity |
| Credits + wallet | `credits.py`, `wallet.py` | balance, history |
| Payments | `cashfree_payments.py`, `cashfree_webhook_handler.py`, `conversions.py` | order, verify, webhook, conversion-acknowledged |
| Subscriptions | `subscriptions.py`, `admin_billing_policy.py` | create/cancel/manage |
| Story-video v2 | `story_engine_routes.py` | create/status/user-jobs/retry/cancel/preview/resume/share-link |
| Story-video legacy | `story_video_generation.py`, `story_video_fast.py`, `story_video_studio.py`, `story_video_templates.py`, `story_video_preview.py`, `story_video_analytics.py` | full legacy pipeline |
| Mobile async | `generation.py` | POST `/api/generate/story/async`, GET poll |
| Reaction GIF | `reaction_gif.py` | start/job/cancel |
| Photo Trailer | `photo_trailer.py` | start/status/share/templates |
| Photo to Comic | `photo_to_comic.py` | start/status/export |
| Comic Storybook | `comic_storybook.py`, `comic_storybook_v2.py` | both versions |
| Coloring Book | `coloring_book.py`, `coloring_book_v2.py` | wizard, generate |
| Other generators | `comix_ai.py`, `gif_maker.py`, `genstudio.py`, `creator_tools.py`, `creator_pro.py`, `story_tools.py`, `instant_story.py`, `bedtime_story_builder.py`, `brand_story_builder.py`, `caption_rewriter_pro.py`, `tone_switcher.py`, `comment_reply_bank.py`, `instagram_bio_generator.py`, `youtube_thumbnail_generator.py`, `offer_generator.py`, `challenge_generator.py`, `story_hook_generator.py`, `twin_finder.py`, `content_engine.py`, `content_blueprint_library.py`, `content_challenge_planner.py`, `daily_viral_ideas.py`, `story_episode_creator.py`, `daily_war.py`, `viral_ideas_v2.py`, `viral_flywheel.py`, `reel_export.py`, `convert.py`, `convert_tools.py` | all share status + retry contract |
| Characters | `characters.py`, `character_routes.py` | create/library/profile/visual-bible |
| Series | `story_series.py`, `story_multiplayer.py`, `universe_routes.py` | multi-episode arcs |
| My Space + drafts | `drafts.py`, `gallery_routes.py`, `media_routes.py`, `r2_proxy.py`, `media_proxy.py`, `media_admin.py`, `protected_download.py`, `download_expiry_routes.py`, `asset_access.py`, `watermark.py`, `content_protection_routes.py` | asset CRUD + protected download |
| Retention/share | `retention_routes.py`, `retention_hooks.py`, `retention_analytics.py`, `share.py`, `remix_routes.py`, `engagement.py`, `engagement_analytics.py`, `daily_rewards_routes.py`, `streaks.py`, `user_progress.py` | every retention surface |
| Push/Email | `push_notifications.py`, `notification_routes.py`, `daily_report_routes.py` | sub/unsub/test/send |
| Analytics | `analytics.py`, `analytics_dashboard.py`, `user_analytics.py`, `realtime_analytics.py`, `growth_analytics.py`, `template_analytics.py`, `template_leaderboard.py`, `revenue_analytics.py`, `audit_dashboard.py`, `production_metrics.py`, `metrics_routes.py`, `ttfd_analytics.py`, `funnel_tracking.py` | aggregated dashboards |
| Health/SRE | `health.py`, `health_routes.py`, `deep_health.py`, `system_health_api.py`, `system_health_routes.py`, `sre_monitoring.py`, `monitoring.py`, `environment_monitor_routes.py`, `self_healing_monitoring.py`, `production_alerts.py`, `watchdog.py`, `diagnostics_beacon.py`, `observability_routes.py`, `live_stats_routes.py`, `kill_switches.py` | infra control plane |
| Admin | `admin.py`, `admin_audit_logs.py`, `admin_billing_policy.py`, `admin_metrics.py`, `admin_payments.py`, `admin_system_routes.py`, `admin_websocket.py`, `admin_worker_routes.py`, `security_management.py`, `security_monitoring.py`, `security_vdp.py` | super-admin panel |
| Style/templates | `style_profiles.py`, `template_versioning.py` | LoRA-like style refs |
| Blog/CMS | `blog.py`, `blog_content.py`, `public_routes.py`, `user_manual.py` | static content + i18n |
| Privacy/legal | `privacy.py`, `reviews.py`, `feedback.py`, `feature_requests.py`, `experience_feedback.py` | DSAR, reviews, feature requests |
| Misc | `sse.py`, `websocket_progress.py`, `pipeline_admin.py`, `pipeline_routes.py`, `priority_scaling.py`, `attribution.py`, `phase_c_dark_launch.py`, `recovery_ui.py`, `regional_pricing.py`, `referral.py`, `referrals.py`, `pricing_api.py`, `ab_testing.py`, `monetization.py`, `share.py`, `telemetry.py`, `user_routes.py`, `user_signals.py`, `user_analytics.py`, `job_queue_routes.py`, `job_worker.py`, `optimized_workers.py`, `backfill_blur.py`, `dashboard_init.py`, `content_trending.py`, `content_vault.py`, `creator_profile.py` |  |

---

## 9. Reliability / Doctrine Layer

| File | Contract |
|---|---|
| `/app/memory/ENGINEERING_DOCTRINE.md` | Bug-Class Elimination Mandate, 5 rules. |
| `/app/memory/BUG_CLASS_ELIMINATION_TEMPLATE.md` | Mandatory template for fixes. |
| `/app/Makefile` | `audit-boundaries` registry — every audit suite. |
| `services/reliability/render_validator.py` | ffprobe gate for all video producers. `REGISTERED_RENDER_PIPELINES` tuple. |
| `services/reliability/asset_verifier.py` | Magic-byte + size gate for image assets. |
| `services/reliability/completion_invariant.py` | Pre-COMPLETED count/state invariant; emits daily-bucketed metrics. |
| `backend/scripts/audit_boundaries_coverage.py` | Migration backlog printer. |
| Static + runtime audits | 35+ test files under `backend/tests/*_2026_05.py` covering every P0 fix to date. |

---

## 10. Third-Party Integrations

| Service | Where wired | Keys |
|---|---|---|
| Emergent Universal Key | `EMERGENT_LLM_KEY` env → `emergentintegrations` SDK in story_engine adapters, genstudio, etc. | Universal key |
| Cashfree Payments | `cashfree_payments.py`, `cashfree_webhook_handler.py` | App ID + Secret in `.env` |
| Cloudflare R2 | `services/cloudflare_r2_storage.py` | Access/Secret/Endpoint + bucket |
| Google OAuth | `routes/auth.py` (POST /api/auth/google) + `frontend GoogleOAuthProvider` | Client ID |
| Google Ads / GA4 | `frontend/src/utils/googleAdsConversions.js` + `routes/conversions.py` | gtag IDs |
| Meta Pixel | `frontend/src/utils/*` | Pixel ID |
| Web Push (VAPID) | `routes/push_notifications.py` | VAPID public/private |
| Email | `services/email_service.py` (Resend/SendGrid abstraction) | API key |
| Sora 2 video | `emergentintegrations.llm.openai.video_generation.OpenAIVideoGeneration` (in genstudio + story_engine) | Universal key |
| Nano Banana image | `emergentintegrations.llm.chat.LlmChat` with `gemini-3-pro-image-preview` | Universal key |
| ffmpeg / ffprobe | static binary `/usr/local/bin/ffmpeg` (from `imageio_ffmpeg` site-pkg) | n/a |

---

## 11. Frontend Components — Cross-Cutting

| Component | Role |
|---|---|
| `App.js` | Route table + provider tree |
| `contexts/CreditContext` | Cached credit balance + refresh |
| `contexts/MediaEntitlementContext` | Plan-based download/watermark gates |
| `contexts/NotificationContext` | Toaster + bell |
| `contexts/FeedbackContext` | Modal feedback pipeline |
| `contexts/ProductGuideContext` | App tour + onboarding journey |
| `utils/api.js` | axios instance + JWT injection + 401 redirect |
| `utils/funnelTracker.js` | trackFunnel(event, props) |
| `utils/analytics.js` | trackEvent generic |
| `utils/activationSentinel.js` | beforeunload `session_abandoned` |
| `utils/googleAdsConversions.js` | gtag dispatch (server-acknowledged only) |
| `components/recovery/ErrorBoundary` | Crash boundary |
| `components/guide/*` | First-action overlay, journey progress, post-value upsell |
| `components/ContentProtectionWrapper` | DRM-lite for previews |
| `components/AppTour` | Driver.js-style intros |
| `components/CookieConsent` | GDPR banner |
| `components/ProgressiveGeneration` | Live SSE/WS progress UI |
| `components/RealTimeProgressPanel.jsx` | Per-stage % bar (story-video) |
| `components/MySpacePage::LocatingProjectCard` | NEW: post-create fallback (never empty state) |

---

## 12. Recent P0 Fixes (last 30 days)

| Date | Bug-class | Fix |
|---|---|---|
| 2026-05-24 | Empty MySpace after Generate Video | Frontend nav gated on job_id; MySpace LocatingProjectCard fallback; `/user-jobs` no PENDING/PROCESSING exclusion; pinned by 10 audit tests. |
| 2026-05-23 | Silent-render (no audio in MP4s) | Canonical `validate_render` gate + `REGISTERED_RENDER_PIPELINES` registry + auto-refund on RenderValidationError. 10 audit tests. |
| 2026-05-22 | MySpace Preview CTA false-success | CTA gated on `hasPlayableVideo` instead of `status === 'COMPLETED'`. |
| 2026-05-21 | Mobile 30s timeout | New `/api/generate/story/async` poll pattern. |
| 2026-05-21 | Reaction GIF stuck / no audio / connection loss / false success | Hard timeouts + janitor + honest progress + asset_verifier on output. |
| 2026-05-20 | Google Ads 0-conversion attribution loss | Server-authoritative `first_project_completed_at` + Cashfree webhook handshake. |
| 2026-05-19 | Photo-to-Comic 2-of-3 panel false success | Strict `assert_completion_invariant` gate. |

---

## 13. How to Read This Repo

**Trace a feature end-to-end** in 5 steps:
1. Find the page in `frontend/src/pages/` (e.g. `StoryVideoPipeline.js`).
2. Search for `/api/` strings in that file → list of endpoints used.
3. For each endpoint, `grep -rn "@router\.\(get\|post\)(\"/<path>\"" backend/routes/` → handler.
4. From handler, follow imports to `services/*` for business logic and `db.<collection>` writes.
5. Pipeline jobs run in background; resume them via `services/{story_engine,comic_pipeline,viral}/*`.

**Verify reliability** for any pipeline:
- Confirm it's in `REGISTERED_RENDER_PIPELINES` if it outputs video.
- Confirm `assert_completion_invariant` is called before any COMPLETED write.
- Confirm there's a test in `backend/tests/test_*_2026_05.py` and that it's in the Makefile audit list.

---

## 14. Notes & Caveats

- **Feature freeze is active.** Document is reference-only; no new features may be built without explicit unfreeze.
- **Two environments.** Preview pod = dev; visionary-suite.com = production. Code fixes live in preview; user must redeploy.
- **Auth credentials.** Test accounts in `/app/memory/test_credentials.md` (read by testing agent).
- **PRD changelog.** See `/app/memory/PRD.md` for date-stamped feature history.
- **Doctrine.** All fixes follow `/app/memory/ENGINEERING_DOCTRINE.md` Bug-Class Elimination Mandate.

— End of document.
