# Technical Architecture Document
## Story Universe Engine — System Blueprint
**Generated: 2026-03-29 | READ-ONLY — No implementation suggestions**

---

## 1. System Overview

| Layer      | Technology           | Port  | Purpose                          |
|------------|----------------------|-------|----------------------------------|
| Frontend   | React 18 + Tailwind  | 3000  | SPA with Shadcn/UI components    |
| Backend    | FastAPI (Python)     | 8001  | REST API + WebSocket + Background Jobs |
| Database   | MongoDB              | 27017 | Primary data store (162+ collections) |
| Object Storage | Cloudflare R2    | -     | Media files (images, videos, audio) |
| Proxy      | Kubernetes Ingress   | 443   | Routes `/api/*` → 8001, all else → 3000 |

**External Services:** OpenAI (GPT-4o-mini, GPT Image 1, Sora 2, TTS/STT), Gemini 3, Cashfree Payments, SendGrid Email — all LLM calls go through Emergent LLM Key.

---

## 2. User Flow

### 2.1 Entry → Dashboard → Creation
```
User lands on /app (Dashboard)
  ├── Hero carousel: auto-rotating featured stories with poster images
  ├── Trending rows: story cards with thumbnails (IntersectionObserver lazy-loaded)
  ├── "Creator Tools" grid: 10 feature buttons
  └── Create bar: free-text prompt input
  
Story Card Click (or Hero "Watch & Continue"):
  → Navigate to /app/story-video-studio
  → Prefill: { title, prompt (hook_text), animation_style, parent_video_id }
  → Phase stays at 'input' — NO auto-generation
  → User reviews/edits prefilled fields
  → User clicks "Generate Video" → pipeline starts
```

### 2.2 Story-to-Video Pipeline (User-Facing Phases)
```
Input → Planning → Scene Storyboard → Image Generation → Video Generation → Audio → Assembly → Result
```
Each phase updates the frontend via polling (`GET /api/story-engine/status/{job_id}` every 3s).

### 2.3 Authentication Flow
```
Login (/api/auth/login) → JWT token (24h expiry)
Signup (/api/auth/register) → 50 credits granted → JWT token
Google OAuth (/api/auth/google/callback) → JWT token
All protected routes: Authorization: Bearer <token>
```

### 2.4 Credit System
```
New user signup → 50 credits (standard, no exceptions)
Generation cost → Deducted before pipeline starts (varies by tool, typically 5-25 credits)
Purchase → Cashfree payment → credits added on webhook confirmation
Refund → Credits restored, order marked refunded
```

---

## 3. Backend Flow

### 3.1 Route Architecture
All routes mounted under `/api` prefix via `APIRouter(prefix="/api")`.

**Core Feature Routes:**
| Route File | Prefix | Purpose |
|---|---|---|
| `auth.py` | `/auth` | Login, register, Google OAuth, password reset |
| `story_engine_routes.py` | `/story-engine` | Create/status/cancel pipeline jobs |
| `pipeline_routes.py` | `/pipeline` | Pipeline job CRUD, admin management |
| `engagement.py` | `/engagement` | Story feed, trending, card clicks |
| `media_proxy.py` | `/media` | R2 object streaming with CORS + HTTP 206 |
| `cashfree_routes.py` | `/cashfree` | Payment order creation, verification |
| `cashfree_webhook.py` | `/cashfree-webhook` | Payment status callbacks |
| `wallet.py` | `/wallet` | Credit balance, purchase, deduction |

**Creator Tool Routes (10 features):**
| Route File | Feature | Generation Method |
|---|---|---|
| `story_series.py` | Story Series | GPT-4o-mini text + GPT Image 1 |
| `character_routes.py` | Character Memory | GPT-4o-mini + persistent profiles |
| `reel_export_routes.py` | Reel Generator | FFmpeg clip assembly |
| `photo_to_comic.py` | Photo to Comic | GPT Image 1 style transfer |
| `comic_storybook_routes.py` | Comic Storybook | GPT-4o-mini + GPT Image 1 panels |
| `story_tools.py` | Bedtime Stories | GPT-4o-mini + OpenAI TTS |
| `gif_maker_routes.py` | Reaction GIF | GPT Image 1 → FFmpeg GIF |
| `tone_switcher.py` | Caption Rewriter | GPT-4o-mini text transform |
| `creator_tools.py` | Brand Story | GPT-4o-mini structured output |
| `content_engine_routes.py` | Daily Viral Ideas | GPT-4o-mini trending analysis |

### 3.2 Story Engine Pipeline (Backend Steps)
```
POST /api/story-engine/create
  → Validates credits (>= cost)
  → Deducts credits immediately
  → Creates job in story_engine_jobs (state: INTAKE)
  → Spawns background task: run_pipeline(job_id)
  
run_pipeline(job_id):
  Step 3: PLANNING
    → planning_llm.generate_episode_plan() via GPT-4o-mini
    → Output: episode_plan JSON (title, scenes, characters, cliffhanger)
    → Retry: 1 automatic retry on failure
    
  Step 4: CHARACTER_CONTEXT
    → planning_llm.generate_character_continuity()
    → Output: character_continuity JSON (appearance locks, style locks)
    
  Step 5: SCENE_MOTION
    → planning_llm.generate_scene_motion_plans()
    → Output: per-scene motion plans (camera, transitions, keyframe/video prompts)
    
  Step 6: GENERATING_KEYFRAMES
    → For each scene: generate_image_direct() via GPT Image 1
    → Output: keyframe images saved locally + uploaded to R2
    
  Step 7: GENERATING_CLIPS
    → For each scene: OpenAIVideoGeneration.generate() via Sora 2
    → Fallback: Ken Burns effect on keyframe image if Sora fails
    → Output: video clips saved locally + uploaded to R2
    
  Step 8: GENERATING_AUDIO
    → OpenAI TTS: narration from scene dialogue/summary
    → Non-fatal: pipeline continues without narration if TTS fails
    
  Step 9: ASSEMBLY
    → FFmpeg: normalize clips → xfade stitch with sanitized transitions → merge audio
    → Fallback: concat demuxer if xfade fails
    → Output: final .mp4 saved locally + uploaded to R2
    
  Step 10: VALIDATION
    → Verify output file exists and is playable
    → State → READY or PARTIAL_READY
```

### 3.3 Background Job System
- **JobQueueService**: In-process async worker pool (not Celery)
- Workers: Configurable count (default 3), process jobs from `job_queue` collection
- Dead letter queue: Failed jobs moved after max retries
- No external broker (Redis used only for caching, not as message queue)

---

## 4. Data Flow

### 4.1 Content Generation Data Flow
```
User Input → Backend API → LLM Service (via Emergent Key) → MongoDB (job record) → R2 (media assets)
                                                                        ↓
Frontend Polling ← Backend Status API ← MongoDB (job state + stage_results)
                                                                        ↓
Final Video URL ← Media Proxy ← R2 (stored .mp4)
```

### 4.2 Payment Data Flow
```
User clicks "Buy Credits"
  → Frontend: POST /api/cashfree/create-order { amount, credits }
  → Backend: Cashfree API → order_id + payment_session_id
  → Frontend: Cashfree JS SDK opens payment modal
  → User completes payment
  → Cashfree webhook → POST /api/cashfree-webhook/process
  → Backend: Verify signature → Update order → Add credits → credit_ledger entry
```

### 4.3 Media Serving Data Flow
```
Frontend <img src> → /api/media/r2/{path}
  → media_proxy.py: stream from R2 with CORS headers
  → Supports HTTP 206 Range requests for video seeking
  → Content-Type auto-detected from extension
```

---

## 5. Key Database Schemas

### story_engine_jobs
```json
{
  "job_id": "uuid",
  "user_id": "uuid",
  "state": "INTAKE|PLANNING|BUILDING_CHARACTER_CONTEXT|GENERATING_KEYFRAMES|GENERATING_CLIPS|GENERATING_AUDIO|ASSEMBLY|VALIDATION|READY|PARTIAL_READY|FAILED|CANCELLED",
  "title": "string",
  "story_text": "string",
  "animation_style": "cartoon_2d|watercolor|anime|...",
  "episode_plan": { /* LLM-generated plan */ },
  "character_continuity": { /* appearance/style locks */ },
  "scene_motion_plans": [ /* per-scene camera/transition */ ],
  "keyframe_urls": ["r2://..."],
  "keyframe_local_paths": ["/tmp/..."],
  "scene_clip_urls": ["r2://..."],
  "scene_clip_local_paths": ["/tmp/..."],
  "narration_url": "r2://...",
  "output_url": "r2://...",
  "thumbnail_url": "r2://...",
  "stage_results": [ { "stage": "string", "status": "success|failed", "duration_seconds": 0, "error": "string|null" } ],
  "cost": 15,
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### users
```json
{
  "user_id": "uuid",
  "email": "string",
  "password_hash": "bcrypt",
  "name": "string",
  "role": "user|admin|moderator",
  "credits": 50,
  "plan": "free|pro|enterprise",
  "created_at": "datetime",
  "last_login": "datetime"
}
```

### orders (Cashfree payments)
```json
{
  "order_id": "string",
  "user_id": "uuid",
  "amount": 299,
  "currency": "INR",
  "credits": 100,
  "status": "CREATED|PAID|FAILED|REFUNDED",
  "cashfree_order_id": "string",
  "payment_session_id": "string",
  "webhook_data": { /* raw Cashfree payload */ },
  "created_at": "datetime"
}
```

---

## 6. External Dependencies

| Service | Purpose | Failure Impact | Auth Method |
|---|---|---|---|
| **OpenAI GPT-4o-mini** | Story planning, character context, scene motion | Pipeline fails at Step 3/4/5 | Emergent LLM Key |
| **OpenAI GPT Image 1** | Keyframe generation | Pipeline fails at Step 6, no fallback | Emergent LLM Key |
| **OpenAI Sora 2** | Video clip generation | Falls back to Ken Burns effect | Emergent LLM Key |
| **OpenAI TTS** | Narration audio | Non-fatal, pipeline continues silently | Emergent LLM Key |
| **Cloudflare R2** | Media storage | Assets unreachable; served via media proxy | R2 API Keys |
| **Cashfree** | Payment processing | Users cannot purchase credits | Cashfree App ID + Secret |
| **SendGrid** | Transactional email | Signup confirmation fails | SendGrid API Key (currently INVALID) |
| **MongoDB** | Primary database | Application non-functional | Local connection |
| **FFmpeg** | Video assembly | Pipeline fails at Step 9 | Local binary |

---

## 7. Failure Points

### 7.1 Pipeline Failure Matrix
| Stage | Root Cause | Frequency | Impact | Mitigation |
|---|---|---|---|---|
| Planning (Step 3) | LLM timeout/invalid JSON | ~20% of failures | Job fails entirely | Auto-retry (1x), robust JSON parsing |
| Keyframe (Step 6) | GPT Image 1 rate limit | Rare | Job fails | Per-scene retry with backoff |
| Clips (Step 7) | Sora 2 timeout/rejection | ~30% of clips | Partial video | Ken Burns fallback from keyframe |
| Assembly (Step 9) | Invalid FFmpeg xfade transitions | **Was 40% of failures** | No final video | **FIXED: transition name sanitization** |
| Assembly (Step 9) | Local clip files missing after restart | Intermittent | Assembly skipped | R2 URLs stored for re-download |

### 7.2 Frontend Failure Points
| Component | Issue | Mitigation |
|---|---|---|
| SafeImage | Large images blocking render | IntersectionObserver lazy loading |
| Story Cards | Broken thumbnails | Gradient fallback + retry on error |
| Video Playback | Large MP4 initial load | `preload="none"`, play on hover |
| Pipeline Status | Polling gap (3s interval) | Acceptable for async generation |

### 7.3 Payment Failure Points
| Scenario | Handling |
|---|---|
| Cashfree webhook fails | Order stays CREATED; user can retry verification |
| Double webhook delivery | Idempotency key prevents duplicate credit addition |
| Credits deducted but pipeline fails | Credits NOT auto-refunded (by design — generation was attempted) |

---

## 8. Performance Bottlenecks

### 8.1 Backend
| Bottleneck | Details | Severity |
|---|---|---|
| **Sora 2 generation time** | 30-120s per clip × 3-6 scenes = 2-12 min total | HIGH — inherent to service |
| **Sequential scene processing** | Keyframes/clips processed one-by-one, not parallel | MEDIUM — could parallelize |
| **FFmpeg normalization** | Each clip normalized before stitch (5-15s each) | LOW — necessary for quality |
| **No job queue broker** | In-process workers; no Celery/Redis broker | LOW — works for current scale |

### 8.2 Frontend
| Bottleneck | Details | Severity |
|---|---|---|
| **R2 media through proxy** | All media routes through `/api/media/r2/*` backend proxy | MEDIUM — adds latency vs direct CDN |
| **No image compression pipeline** | Full-size images served (some 2MB+ PNGs) | MEDIUM — needs thumbnail generation |
| **Polling-based status updates** | 3s interval polling for pipeline progress | LOW — WebSocket upgrade would improve UX |
| **Large bundle** | 10 feature pages loaded in main bundle | LOW — code splitting would help |

### 8.3 Database
| Bottleneck | Details | Severity |
|---|---|---|
| **162+ collections** | Many feature-specific collections with low document counts | LOW — no query performance issue yet |
| **No indexes on hot queries** | `story_engine_jobs` queried by user_id + state without compound index | MEDIUM — will matter at scale |
| **Large documents** | `story_engine_jobs` stores full plans + URLs inline | LOW — acceptable for current volume |

---

## 9. Frontend Route Map

| Route | Component | Auth Required | Purpose |
|---|---|---|---|
| `/app` | Dashboard | Yes | Main feed + creator tools |
| `/app/story-video-studio` | StoryVideoPipeline | Yes | Story-to-Video creation |
| `/app/story-series` | StorySeries | Yes | Multi-episode series |
| `/app/characters` | CharacterConsistencyStudio | Yes | Character profiles |
| `/app/reels` | ReelGenerator | Yes | Short reel export |
| `/app/photo-to-comic` | PhotoToComic | Yes | Photo style transfer |
| `/app/comic-storybook` | ComicStorybook | Yes | Panel-by-panel comics |
| `/app/bedtime-stories` | BedtimeStories | Yes | Narrated stories |
| `/app/reaction-gif` | ReactionGif | Yes | GIF creation |
| `/app/caption-rewriter` | CaptionRewriter | Yes | AI caption rewrite |
| `/app/brand-story` | BrandStory | Yes | Business storytelling |
| `/app/daily-viral` | DailyViral | Yes | Trending content ideas |
| `/app/admin/*` | AdminLayout children | Admin | Admin dashboard, analytics |
| `/app/profile` | Profile | Yes | User settings, security |
| `/app/credits` | CreditsPage | Yes | Credit purchase |
| `/share/*` | PublicCreation | No | Public shared content |
| `/character/*` | PublicCharacterPage | No | Public character profiles |

---

## 10. Configuration & Environment

**Frontend (.env):**
- `REACT_APP_BACKEND_URL` — External API URL (Kubernetes ingress)

**Backend (.env):**
- `MONGO_URL` — MongoDB connection string
- `DB_NAME` — Database name (`creatorstudio_production`)
- `EMERGENT_LLM_KEY` — Universal key for all LLM services
- `CLOUDFLARE_R2_*` — R2 storage credentials (account, keys, bucket, public URL)
- `CASHFREE_*` — Payment gateway credentials (app ID, secret, webhook secret)
- `SENDGRID_API_KEY` — Email service (currently invalid)
- `JWT_SECRET` — Token signing key

**Process Management:** Supervisor manages both frontend (port 3000) and backend (port 8001). Hot reload enabled for both.

---

*End of Technical Architecture Document*
