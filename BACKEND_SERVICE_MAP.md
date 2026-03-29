# Backend Service / Pipeline Map

> **Canonical reference for the current platform.**
> Do NOT improvise vague service responsibilities.
> Do NOT mix route/controller logic with service logic.
> Do NOT add future architecture ideas or extra phases.
> This is for the CURRENT working platform only.

---

# 1. BACKEND LAYERING RULES

All backend logic must follow this structure:

## Layer 1 — Routes / Controllers

Responsibilities:

* receive request
* validate input
* call service
* return response

Routes must NOT:

* perform pipeline orchestration
* assemble FFmpeg commands directly
* contain business logic for credits/refunds/retries
* contain data-munging that belongs in service layer

---

## Layer 2 — Services

Responsibilities:

* business logic
* orchestration
* composition of adapters/utilities
* state transitions
* retries
* failure handling
* response normalization

---

## Layer 3 — Adapters / Providers

Responsibilities:

* talk to external systems
* OpenAI / Sora / GPT Image / TTS
* FFmpeg execution
* R2 upload/download
* email provider

Adapters must NOT contain product logic.

---

## Layer 4 — Persistence / Storage

Responsibilities:

* MongoDB collections
* R2 media assets
* temporary local files if required for assembly

---

# 2. PRIMARY BACKEND SERVICES

The platform must be understood as these core backend services:

1. Feed / Engagement Service
2. Story Engine Service
3. Credits / Billing Service
4. Share / Referral Service
5. Character Service
6. Story Series Service
7. Content Engine Service
8. Auth / Password Reset Service
9. Admin / Analytics Service
10. Media Proxy / Storage Service

---

# 3. FEED / ENGAGEMENT SERVICE MAP

## Purpose

Drives homepage/dashboard/explore feed.

## Routes

* `GET /api/engagement/story-feed`
* `GET /api/engagement/explore`
* `POST /api/engagement/card-click`
* `GET /api/engagement/card-analytics`

## Service ownership

Service should:

* gather stories from `story_engine_jobs`
* use `pipeline_jobs` only as legacy fallback
* use `content_engine_items` if seeded fallback required
* derive badges / row placement / display priorities
* return normalized card objects for frontend

## MongoDB reads

Primary:

* `story_engine_jobs`

Secondary:

* `pipeline_jobs`

Optional:

* `content_engine_items`
* `growth_events`
* `share_links`
* `character_profiles`

## Output contract

Returns:

* featured_story
* trending_stories[]
* fresh_stories[]
* continue_stories[]
* unfinished_worlds[]
* live_stats

## Rules

* rows always returned
* no dead empty sections when fallback content exists
* normalize media fields before response

---

# 4. STORY ENGINE SERVICE MAP

## Purpose

Owns Story-to-Video pipeline end-to-end.

## Routes

* `GET /api/story-engine/credit-check`
* `POST /api/story-engine/create`
* `GET /api/story-engine/status/{job_id}`
* `GET /api/story-engine/my-jobs`
* `POST /api/story-engine/retry/{job_id}`
* any assembly/admin retry route currently in codebase

## Main service

Suggested canonical service:

* `pipeline.py` as orchestration core

## Input flow

Route receives:

* title
* story_text
* animation_style
* target_age
* narrator_voice
* parent_video_id
* hook_text

Route validates and forwards to Story Engine Service.

---

## Story Engine pipeline stages

Strict stage flow:

1. INIT
2. PLANNING
3. BUILDING_CHARACTER_CONTEXT
4. PLANNING_SCENE_MOTION
5. GENERATING_KEYFRAMES
6. GENERATING_SCENE_CLIPS
7. GENERATING_AUDIO
8. ASSEMBLING_VIDEO
9. VALIDATING
10. READY / PARTIAL_READY / FAILED

---

## Stage-by-stage service ownership

### Stage 1 — Credit gate

Service:

* Credits Service

Does:

* check credits
* reject if insufficient
* deduct atomically before expensive processing

Writes:

* `story_engine_jobs.required_credits`
* `story_engine_jobs.deducted_credits`

---

### Stage 2 — Job creation

Service:

* Story Engine Service

Does:

* create `story_engine_jobs` document
* store initial input
* status = INIT

Writes:

* `story_engine_jobs`

---

### Stage 3 — Planning

Service:

* Planning adapter called by Story Engine Service

Does:

* create `episode_plan`
* derive summary
* derive scene breakdown
* derive cliffhanger

Writes:

* `story_engine_jobs.episode_plan`
* status = PLANNING

External dependency:

* GPT-4o-mini now
* self-hosted planner later if migrated

---

### Stage 4 — Character continuity

Service:

* Character context builder inside Story Engine Service
* may consult Character Service if parent/story/series linked

Does:

* build `character_continuity`
* preserve continuity from prior story if `parent_video_id` exists

Writes:

* `story_engine_jobs.character_continuity`
* status = BUILDING_CHARACTER_CONTEXT

Reads:

* `character_profiles`
* `character_visual_bibles`
* `character_memory_logs`
* prior `story_engine_jobs` if continuing

---

### Stage 5 — Scene motion plan

Service:

* Planning adapter / motion planner inside Story Engine Service

Does:

* build `scene_motion_plan`
* sanitize transitions for FFmpeg compatibility

Writes:

* `story_engine_jobs.scene_motion_plan`
* status = PLANNING_SCENE_MOTION

---

### Stage 6 — Keyframe generation

Service:

* Image generation adapter

Does:

* generate scene images/keyframes
* upload to R2
* store structured scene_images

Writes:

* `story_engine_jobs.scene_images[]`
* status = GENERATING_KEYFRAMES

External dependency:

* GPT Image 1 now
* self-hosted image/video model later if migrated

Storage:

* R2

---

### Stage 7 — Scene clip generation

Service:

* Video generation adapter

Does:

* generate moving scene clips
* if clip generation fails, allow graceful fallback path
* upload clips to R2

Writes:

* `story_engine_jobs.scene_clips[]`
* `story_engine_jobs.fallback.*`
* status = GENERATING_SCENE_CLIPS

External dependency:

* Sora now
* Wan2.1 later if migrated

Fallback:

* Ken Burns / quick render mode if applicable

---

### Stage 8 — Audio generation

Service:

* TTS adapter

Does:

* generate narration
* upload audio to R2

Writes:

* `story_engine_jobs.audio`
* status = GENERATING_AUDIO

External dependency:

* OpenAI TTS now
* Kokoro later if migrated

Fallback:

* video may still succeed without narration if allowed

---

### Stage 9 — Assembly

Service:

* FFmpeg Assembly adapter

Does:

* normalize clips
* stitch clips
* mix narration/audio
* create final output
* generate poster
* generate preview
* generate `thumbnail_small`

Writes:

* `story_engine_jobs.media.*`
* status = ASSEMBLING_VIDEO

External dependency:

* FFmpeg local execution

Storage:

* output uploaded to R2

---

### Stage 10 — Validation

Service:

* Story Engine validation routine

Does:

* check output exists
* check poster/thumbnail/preview exists
* check final state
* check fallback metadata if relevant

Writes:

* final status = READY / PARTIAL_READY / FAILED
* append `errors[]` if failure

---

# 5. STORY ENGINE ADAPTER MAP

## Planning Adapter

Responsibilities:

* LLM episode planning
* continuity-aware story planning
* motion plan generation

Must return structured objects only.
No raw text blobs passed downstream if avoidable.

---

## Image Adapter

Responsibilities:

* generate keyframes
* return URLs/storage keys
* no business logic

---

## Video Adapter

Responsibilities:

* generate scene clips
* return URLs/storage keys
* no business logic

---

## TTS Adapter

Responsibilities:

* generate narration audio
* return URL/storage key
* no product logic

---

## FFmpeg Assembly Adapter

Responsibilities:

* clip normalization
* concatenation / xfade when valid
* audio mix
* poster / preview / thumbnail generation
* resilient subprocess execution

Must not decide business status beyond assembly result.
Story Engine Service decides final job state.

---

## R2 / Storage Adapter

Responsibilities:

* upload media
* provide URLs/keys
* fetch or proxy where needed

Must support:

* images
* previews
* videos
* audio
* posters
* thumbnail_small

---

# 6. CREDITS / BILLING SERVICE MAP

## Purpose

Single source of truth for credit display, deduction, and refund.

## Routes

* `GET /api/credits/me`
* `GET /api/story-engine/credit-check`
* pricing/billing routes currently in codebase

## MongoDB source

* `users`

## Responsibilities

* return current credits
* return `is_unlimited`
* calculate shortfall
* atomically deduct before expensive processing
* refund on failure
* prevent double-deduction

## Rules

No feature route should reimplement custom credit math.
All expensive generation flows should go through Credits Service logic.

---

# 7. SHARE / REFERRAL SERVICE MAP

## Purpose

Own public story links, referral attribution, and share rewards.

## Routes

* public share page route
* `POST /api/share/track`
* signup referral reward route currently in codebase

## MongoDB source

* `share_links`
* `referral_attribution`
* `growth_events`
* `users` (for reward crediting)

## Responsibilities

* create/retrieve public story slug
* record views/clicks/continues/signups
* enforce self-referral prevention
* enforce duplicate reward prevention
* trigger share/signup/continue rewards

---

# 8. CHARACTER SERVICE MAP

## Purpose

Own persistent characters and continuity support.

## Routes

* character routes currently in codebase
* at minimum create/list/detail/update

## MongoDB source

* `character_profiles`
* `character_visual_bibles`
* `character_memory_logs`
* `character_relationships`

## Responsibilities

* CRUD for characters
* visual lock retrieval
* memory retrieval
* support Story Engine continuity building

---

# 9. STORY SERIES SERVICE MAP

## Purpose

Own episodic / multi-part story system.

## Routes

* `POST /api/story-series/create`
* `GET /api/story-series/my-series`
* `GET /api/story-series/{series_id}`
* `POST /api/story-series/{series_id}/next-episode`

## MongoDB source

* `story_series`
* `story_episodes`
* linked `story_engine_jobs`

## Responsibilities

* create series
* list user series
* retrieve timeline
* create next episode prompt/context
* maintain episode sequence

---

# 10. CONTENT ENGINE SERVICE MAP

## Purpose

Own seeded content generation/scoring/publishing.

## Routes

* content engine/admin routes currently in codebase

## MongoDB source

* `content_engine_items`

## Responsibilities

* generate hooks/scripts/captions
* run rule score + GPT score
* mark LOW/MEDIUM/HIGH
* publish selected items into Story Engine flow or homepage feed

## Rule

Content Engine is a staging/scoring layer, not the final story output truth.
Final output truth belongs to `story_engine_jobs`.

---

# 11. AUTH / PASSWORD RESET SERVICE MAP

## Purpose

Authentication, signup, reset flow.

## Routes

* login
* signup
* forgot password
* reset password

## MongoDB source

* `users`
* reset token collection/store if present

## Responsibilities

* authenticate user
* create user
* send reset mail
* validate reset token
* reset password

## Rule

Do not claim reset success if provider delivery is broken.

---

# 12. ADMIN / ANALYTICS SERVICE MAP

## Purpose

Admin visibility into users, jobs, credits, growth, health.

## Routes

* `/admin/*` backend routes currently in codebase

## MongoDB source

* `users`
* `story_engine_jobs`
* `pipeline_jobs`
* `growth_events`
* `share_links`
* `system_health_snapshots`
* `admin_audit_logs`

## Responsibilities

* dashboard metrics
* user counts
* job health
* retry controls
* growth analytics
* K-factor visibility
* content visibility

---

# 13. MEDIA PROXY / STORAGE SERVICE MAP

## Purpose

Serve/stream media fast and safely.

## Routes

* media proxy routes currently in codebase

## Responsibilities

* serve posters/thumbnails/previews/videos
* support HEAD and Range for videos
* ensure browser progressive playback
* protect/normalize URL access where required

## Storage truth

* actual asset files in R2
* metadata in MongoDB job/media fields

---

# 14. FAILURE / FALLBACK MAP

## Planning failure

Owner:

* Story Engine Service + Planning Adapter

Behavior:

* retry if allowed
* append error
* fail gracefully
* refund if job fails fully

---

## Clip generation failure

Owner:

* Story Engine Service + Video Adapter

Behavior:

* use Ken Burns/quick render fallback if allowed
* mark fallback metadata
* continue assembly if possible
* READY or PARTIAL_READY depending on completeness

---

## Audio failure

Owner:

* Story Engine Service + TTS Adapter

Behavior:

* if allowed, continue with silent/no narration output
* do not crash whole job unnecessarily

---

## FFmpeg assembly failure

Owner:

* FFmpeg Assembly Adapter + Story Engine Service

Behavior:

* retry once if safe
* mark error
* allow admin retry assembly endpoint where implemented
* fail or partial-ready truthfully

---

## R2 upload failure

Owner:

* Storage Adapter

Behavior:

* fail clearly
* do not pretend output exists
* no false READY state

---

# 15. HOMEPAGE MEDIA PERFORMANCE MAP

## Service ownership

Feed Service + Storage/Media layer + Pipeline thumbnail generation

## Required media outputs per story

* `thumbnail_small_url` → cards
* `poster_url` → hero/fallback
* `preview_url` → autoplay preview
* `output_url` → full playback page

## Rules

* cards should never use raw heavy scene PNGs if thumbnail_small exists
* hero poster should load first
* preview videos should be short and progressive-playback-friendly

---

# 16. BACKWARD COMPATIBILITY RULE

Do NOT do broad schema migration unless mandatory.

Use compatibility mapping in service/response layer for:

* `state` → `status`
* flat media fields → normalized response fields
* legacy job output → normalized feed/job response

Current stability matters more than ideal schema purity.

---

# 17. REQUIRED VALIDATION MAP

For every backend service fix, validate:

1. route receives valid request
2. service executes correct logic
3. adapter called correctly
4. MongoDB updated correctly
5. R2/media written correctly if applicable
6. response matches normalized contract
7. frontend consumes it correctly

---

# 18. REQUIRED RESPONSE FORMAT

When confirming service/pipeline work, return only:

1. Issue fixed
2. Root cause
3. Files changed
4. Validation done
5. Proof

Do NOT include:

* Next Tasks
* Future Tasks
* optional enhancements
* backlog items
* miscellaneous ideas
