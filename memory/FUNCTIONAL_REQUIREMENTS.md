# Visionary Suite — Complete Functional Requirements Document

**Platform**: AI-Powered Story Multiplayer Engine
**Core Loop**: WATCH > ENTER BATTLE > GENERATE > COMPETE > PAY
**Stack**: React + FastAPI + MongoDB + Cloudflare R2 + Cashfree + OpenAI/Gemini/Sora 2

---

## TABLE OF CONTENTS

1. Authentication & User Management
2. Landing Page & Public Entry
3. Dashboard (Battle-First Home)
4. Story Video Studio (Creation Engine)
5. Story Generation Pipeline
6. Battle System (Story Multiplayer)
7. Content Feed & Discovery
8. Credits, Paywall & Monetization
9. Payment Gateway (Cashfree)
10. Post-Generation Loop
11. Share & Viral Distribution
12. Push Notifications
13. Creator Tools Suite
14. Character System
15. Series & Episodes
16. Admin Panel
17. Analytics & Funnel Tracking
18. Media Storage & Delivery
19. Security & Abuse Prevention
20. Performance & Optimization
21. Onboarding & User Guidance
22. Referral & Growth Systems

---

## 1. AUTHENTICATION & USER MANAGEMENT

### 1.1 Email/Password Authentication
| Req ID | Requirement | Route |
|--------|-------------|-------|
| AUTH-01 | User registration with email, password, name | `POST /api/auth/register` |
| AUTH-02 | Email/password login with JWT token | `POST /api/auth/login` |
| AUTH-03 | Password strength validation (min 8 chars, mixed case, special) | Backend validation |
| AUTH-04 | Duplicate email prevention | 400 on existing email |
| AUTH-05 | JWT token-based session (stored in localStorage) | Bearer token auth |
| AUTH-06 | Session persistence across page refresh | Token check on mount |
| AUTH-07 | Logout (client-side token clearing) | Client-side |
| AUTH-08 | Password change for authenticated users | `POST /api/auth/change-password` |
| AUTH-09 | Forgot password flow with email reset | `POST /api/auth/forgot-password` |
| AUTH-10 | Password reset with token | `POST /api/auth/reset-password` |

### 1.2 Google OAuth Sign-In
| Req ID | Requirement | Route |
|--------|-------------|-------|
| AUTH-11 | Google sign-in via popup (`useGoogleLogin` hook) | Client-side popup |
| AUTH-12 | Google access_token exchange on backend | `POST /api/auth/google` |
| AUTH-13 | Account linking (Google + existing email) | Backend merge logic |
| AUTH-14 | Popup cancel — graceful toast + button re-enable | Client UX |
| AUTH-15 | Popup blocked — friendly error with retry | Client UX |
| AUTH-16 | Loading overlay during OAuth exchange | Client UX |

### 1.3 User Roles & Access Control
| Req ID | Requirement |
|--------|-------------|
| AUTH-17 | Roles: `USER`, `ADMIN`, `SUPERADMIN` |
| AUTH-18 | Protected routes require authentication (redirect to `/login`) |
| AUTH-19 | Admin routes require ADMIN role (server-side enforcement) |
| AUTH-20 | Standard users cannot access `/app/admin/*` (redirect) |
| AUTH-21 | Return-to-intent after login (stored in `localStorage.auth_return_path`) |

### 1.4 Account Security
| Req ID | Requirement | Route |
|--------|-------------|-------|
| AUTH-22 | Rate limiting on login (100/min) | `slowapi` limiter |
| AUTH-23 | Account lockout after repeated failures | `account_lockouts` collection |
| AUTH-24 | reCAPTCHA v3 integration (soft-fail mode) | Google reCAPTCHA |
| AUTH-25 | Login activity logging | `login_activity` collection |
| AUTH-26 | Email verification flow | `POST /api/auth/verify-email` |

### 1.5 Profile Management
| Req ID | Requirement | Route |
|--------|-------------|-------|
| AUTH-27 | View/update profile (name, avatar, bio) | `GET/PUT /api/auth/profile` |
| AUTH-28 | Creator profile (public-facing) | `/creator/:username` |
| AUTH-29 | Privacy settings | `/app/privacy` |
| AUTH-30 | User homepage profile | `user_homepage_profile` collection |

---

## 2. LANDING PAGE & PUBLIC ENTRY

### 2.1 Landing Page (`/`)
| Req ID | Requirement |
|--------|-------------|
| LAND-01 | Hero section: "Create stories kids will remember forever" |
| LAND-02 | Primary CTA: "Create Your Story & Take #1 Spot" → `/experience` |
| LAND-03 | Secondary CTA: "Watch Examples" → scroll to showcase |
| LAND-04 | Trust line: "No credit card required · Free to start · Compete for #1" |
| LAND-05 | Alive signals (stories created today, active users, live battles) |
| LAND-06 | A/B test headline variants (`ab_experiments`) |
| LAND-07 | Traffic source detection (utm_source, referrer, Instagram/WhatsApp/etc.) |
| LAND-08 | Cookie consent banner |
| LAND-09 | Mobile responsive — CTA visible without scroll |
| LAND-10 | Creator bio section (Raja Praveen Katta) |

### 2.2 Public Pages
| Req ID | Requirement | Route |
|--------|-------------|-------|
| LAND-11 | Pricing page | `/pricing` |
| LAND-12 | About page | `/about` |
| LAND-13 | Gallery (public creations) | `/gallery` |
| LAND-14 | Explore page | `/explore` |
| LAND-15 | Blog with articles | `/blog`, `/blog/:slug` |
| LAND-16 | Reviews page | `/reviews` |
| LAND-17 | Contact page | `/contact` |
| LAND-18 | User manual/help | `/user-manual`, `/help` |
| LAND-19 | Privacy policy, Terms, Cookie policy | `/privacy-policy`, `/terms`, `/cookie-policy` |

### 2.3 Instant Story Experience (`/experience`)
| Req ID | Requirement |
|--------|-------------|
| LAND-20 | Zero-auth story generation (guest mode) |
| LAND-21 | AI generates story instantly from prompt |
| LAND-22 | Shows story text + images |
| LAND-23 | Login prompt after value delivery |
| LAND-24 | Funnel tracking: `demo_viewed`, `story_generation_started`, `login_prompt_shown` |

---

## 3. DASHBOARD (Battle-First Home) (`/app`)

### 3.1 Consolidated Loading
| Req ID | Requirement | Route |
|--------|-------------|-------|
| DASH-01 | Single consolidated API: `/api/dashboard/init` | Returns feed, challenges, top stories, viral status, leaderboard |
| DASH-02 | 20-second TTL cache per user | `cachetools.TTLCache` |
| DASH-03 | Sub-2s load time target | Code splitting + consolidated API |
| DASH-04 | Skeleton UI during loading | React Suspense fallback |

### 3.2 Dashboard Sections (render order)
| Req ID | Section | Component |
|--------|---------|-----------|
| DASH-05 | Personal Alert Strip ("You dropped to #3") | `PersonalAlertStrip` |
| DASH-06 | Live Battle Hero (autoplay, rank, stats) | `LiveBattleHero.jsx` |
| DASH-07 | Quick Actions ("Choose Your Path" — 3 CTAs) | `QuickActions.jsx` |
| DASH-08 | Trending Public Feed (story cards with autoplay) | `TrendingPublicFeed` |
| DASH-09 | Momentum Section (rank, battles, credits, status) | `MomentumSection.jsx` |
| DASH-10 | Hero Section | `HeroSection` |
| DASH-11 | Story Rows | Various |

### 3.3 Live Battle Hero
| Req ID | Requirement |
|--------|-------------|
| DASH-12 | Shows hottest active battle with title, stats, #1 entry |
| DASH-13 | Autoplay muted video loop of #1 entry (with poster/gradient fallback) |
| DASH-14 | Live stats: WATCHING count, FIGHTING count, YOUR RANK |
| DASH-15 | Rank countdown timer (next update in X:XX) |
| DASH-16 | CTAs: "Take #1 Spot" + "Post in 10 Seconds" (Quick Shot) |
| DASH-17 | BattlePulse polling every 15 seconds |
| DASH-18 | Paywall-gated entry (listens for `show-battle-paywall` event) |
| DASH-19 | Credit-aware micro-copy ("Entry requires credits · View the battle first") |

### 3.4 Quick Actions
| Req ID | Requirement |
|--------|-------------|
| DASH-20 | Primary: "Enter Battle Instantly" (AI auto-gen, spans 2 cols, credit indicator) |
| DASH-21 | Secondary: "Write Your Own Story" → fresh studio `/app/story-video-studio` |
| DASH-22 | Tertiary: "Beat the Leader" → battle page with dynamic #1 title |

---

## 4. STORY VIDEO STUDIO (Creation Engine) (`/app/story-video-studio`)

### 4.1 Fresh Session Flow
| Req ID | Requirement |
|--------|-------------|
| STUDIO-01 | "Write Your Own Story" CTA opens with `freshSession: true` state |
| STUDIO-02 | Fresh session: empty title, empty story text, no pre-loaded data |
| STUDIO-03 | Recent Videos sidebar hidden during fresh session |
| STUDIO-04 | Direct URL access loads studio (shows recent drafts if returning user) |
| STUDIO-05 | Deep-link via `?projectId=` loads specific project |

### 4.2 Input Phase
| Req ID | Requirement |
|--------|-------------|
| STUDIO-06 | Title input (required, 3-100 chars) |
| STUDIO-07 | Story text area (required, 50-10,000 chars, live character count) |
| STUDIO-08 | Animation style selector (2D Cartoon, Anime, 3D Animation, Comic Book, Cinematic 3D, Watercolor) |
| STUDIO-09 | Target age group selector |
| STUDIO-10 | Narrator voice preset selector |
| STUDIO-11 | Quality mode selector (balanced / high) |
| STUDIO-12 | Generate button with validation + duplicate-click guard (`createLockRef`) |
| STUDIO-13 | Form validation: inline errors for title length, story length |

### 4.3 Guided Start V2 (Feature Flag: `guidedStartV2`)
| Req ID | Requirement | Route |
|--------|-------------|-------|
| STUDIO-14 | Vibe picker: Bedtime Magic, Emotional Story, Mind-Blowing Twist, 1M Views Hook | UI only |
| STUDIO-15 | "Random Idea" button → `GET /api/drafts/idea` | Returns random story prompt |
| STUDIO-16 | Category-filtered ideas → `GET /api/drafts/idea?vibe={kids\|drama\|thriller\|viral}` | Returns vibe-specific prompt |
| STUDIO-17 | "Use Sample Story" → pre-fills "The Secret Garden on Mars" | Client-side |
| STUDIO-18 | Guided start hides after user begins typing | UI auto-hide |

### 4.4 Draft Persistence V2 (Feature Flag: `draftPersistenceV2`)
| Req ID | Requirement | Route |
|--------|-------------|-------|
| STUDIO-19 | Auto-save draft 3s after user stops typing | `POST /api/drafts/save` |
| STUDIO-20 | Save only fires on content change (deduped) | `lastSavedRef` comparison |
| STUDIO-21 | XSS sanitization on save (title + story_text) | `sanitize_input()` applied |
| STUDIO-22 | One active draft per user (upsert model) | MongoDB upsert |
| STUDIO-23 | Resume modal on return: "Continue" vs "Start Fresh" | `GET /api/drafts/current` |
| STUDIO-24 | "Continue" restores title, story, style, age, voice | Full draft restoration |
| STUDIO-25 | "Start Fresh" discards draft | `DELETE /api/drafts/discard` |
| STUDIO-26 | Draft status lifecycle: `draft` → `processing` → `completed` | `POST /api/drafts/status` |
| STUDIO-27 | On generation failure: processing reverts to draft (recovery) | Status revert |
| STUDIO-28 | Navigation guard: warn on unsaved changes | `beforeunload` + React |

### 4.5 Recent Drafts Panel (Feature Flag: `recentDraftsPanel`)
| Req ID | Requirement | Route |
|--------|-------------|-------|
| STUDIO-29 | Shows max 3 recent items (drafts + projects) | `GET /api/drafts/recent` |
| STUDIO-30 | Each item: title, last edited, status badge | Structured response |
| STUDIO-31 | Clicking item opens correct project | Navigate with projectId |

---

## 5. STORY GENERATION PIPELINE

### 5.1 Pipeline Initiation
| Req ID | Requirement | Route |
|--------|-------------|-------|
| PIPE-01 | Create story video job | `POST /api/story-engine/create` |
| PIPE-02 | Credit gate: pre-flight check before generation | `GET /api/story-engine/credit-check` |
| PIPE-03 | Credits charged on creation (10 per video) | `credit_ledger` deduction |
| PIPE-04 | Admin exemption from rate limits and queue caps | `skip_credits=True` |
| PIPE-05 | Idempotency: prevent duplicate jobs on double-click | `createLockRef` + backend guard |

### 5.2 Pipeline Stages
| Req ID | Stage | Description |
|--------|-------|-------------|
| PIPE-06 | Story Planning | AI generates episode plan, scenes, characters |
| PIPE-07 | Scene Generation | Scene descriptions and compositions |
| PIPE-08 | Image Generation | AI generates scene images (OpenAI/Gemini) |
| PIPE-09 | Voice Generation | Text-to-speech narration (ElevenLabs) |
| PIPE-10 | Video Compilation | FFmpeg assembly: images + voice + music → MP4 |
| PIPE-11 | Upload to R2 | Final video + thumbnail uploaded to Cloudflare R2 |

### 5.3 Pipeline Status & Progress
| Req ID | Requirement | Route |
|--------|-------------|-------|
| PIPE-12 | Real-time status polling | `GET /api/story-engine/status/{job_id}` |
| PIPE-13 | Progress percentage updates | Frontend polling every 3-5s |
| PIPE-14 | Stage indicators (prompt → scenes → images → voices → result) | UI progress bar |
| PIPE-15 | Stale detection (no progress for 90s → warning toast) | Client-side timer |
| PIPE-16 | Hard timeout (extended generation notification) | Client-side 10min cap |
| PIPE-17 | WebSocket progress (optional) | `useJobWebSocket` hook |

### 5.4 Pipeline States
| Req ID | State | Description |
|--------|-------|-------------|
| PIPE-18 | `CREATED` | Job initialized |
| PIPE-19 | `QUEUED` | Waiting for processing slot |
| PIPE-20 | `PROCESSING` | Active generation |
| PIPE-21 | `COMPLETED` | All stages done, assets ready |
| PIPE-22 | `PARTIAL` | Partial success (some assets) |
| PIPE-23 | `FAILED` | Generation failed (retry available) |

### 5.5 Failure Handling
| Req ID | Requirement |
|--------|-------------|
| PIPE-24 | Failed jobs never delete draft content |
| PIPE-25 | Retry available (max 2 attempts) |
| PIPE-26 | Failed_recovery view mode for partial results |
| PIPE-27 | Stage-level reuse on retry (skip successful stages) |

### 5.6 Media Derivative Pipeline
| Req ID | Requirement |
|--------|-------------|
| PIPE-28 | Auto-generates 3 derivatives per video: poster_sm (webp), poster_md (webp), 2s preview clip (mp4) |
| PIPE-29 | Hook selection: I-frame analysis for best 2s window |
| PIPE-30 | FFmpeg: 540px width, 24fps, CRF 28, no audio, faststart |
| PIPE-31 | Upload to R2 under `/previews/{job_id}/` |
| PIPE-32 | `media_assets` collection tracks derivatives |

---

## 6. BATTLE SYSTEM (Story Multiplayer)

### 6.1 Battle Structure
| Req ID | Requirement | Route |
|--------|-------------|-------|
| BATTLE-01 | Battle page: `/app/story-battle/:storyId` | Shows leaderboard, #1 entry, rank |
| BATTLE-02 | Battle pulse (live updates) | `GET /api/story-multiplayer/battle-pulse/{root_story_id}` |
| BATTLE-03 | Hottest active battle | `GET /api/stories/hottest-battle` |
| BATTLE-04 | Leaderboard with rankings, scores, creator names | Sorted by `battle_score` |
| BATTLE-05 | #1 entry auto-play video | Video player on battle page |

### 6.2 Battle Entry
| Req ID | Requirement | Route |
|--------|-------------|-------|
| BATTLE-06 | Quick Shot: 1-tap AI auto-generation | `POST /api/stories/quick-shot` |
| BATTLE-07 | Submit own story as battle entry | Create + link to root |
| BATTLE-08 | Remix flow: remix #1 entry in studio | Studio with remix context |
| BATTLE-09 | Free entry limit: 3 free entries | `GET /api/stories/battle-entry-status` |
| BATTLE-10 | After 3 free: `needs_payment = true` → paywall | Credit check |

### 6.3 Battle Psychology
| Req ID | Requirement |
|--------|-------------|
| BATTLE-11 | WIN moment: persistent unmissable Share CTA |
| BATTLE-12 | LOSS moment: "Act now" + push notification |
| BATTLE-13 | Rank drop notification: "Someone just beat you" alert strip |
| BATTLE-14 | Near-win auto-paywall: rank #2/#3 within 5pts of #1 → paywall |
| BATTLE-15 | Competitive signals: "X people trying to beat #1" |
| BATTLE-16 | Return triggers: "Your rank might change — come back in 10 minutes" |

### 6.4 Daily War
| Req ID | Requirement | Route |
|--------|-------------|-------|
| BATTLE-17 | Daily themed war/challenge | `/app/war` |
| BATTLE-18 | Challenge winners tracked | `daily_challenges`, `challenge_winners` collections |

---

## 7. CONTENT FEED & DISCOVERY

### 7.1 Story Feed
| Req ID | Requirement | Route |
|--------|-------------|-------|
| FEED-01 | Trending stories feed (sorted by battle_score + views) | `GET /api/engagement/story-feed` |
| FEED-02 | Feed cards: title, animation style, thumbnail, view count, battle info | Structured JSON |
| FEED-03 | IntersectionObserver autoplay: video plays at 60% visibility, pauses on scroll-out | Frontend |
| FEED-04 | Fallback: gradient + title + style when no thumbnail | `SafeImage` component |
| FEED-05 | Click → story viewer or battle page | Navigate on click |
| FEED-06 | LIVE badge indicators | UI badge |
| FEED-07 | Hook text overlays on cards | Story hook generator |

### 7.2 Explore & Browse
| Req ID | Requirement | Route |
|--------|-------------|-------|
| FEED-08 | Public explore page | `/explore`, `/app/explore` |
| FEED-09 | Browse page with categories | `/app/browse` |
| FEED-10 | Search functionality | Search within feed |

### 7.3 Story Viewer
| Req ID | Requirement | Route |
|--------|-------------|-------|
| FEED-11 | Full story viewer | `/app/story-viewer/:jobId` |
| FEED-12 | Video player with autoplay | Consumption-first UI |
| FEED-13 | Battle status banner (rank/score/views) | BattlePulse integration |
| FEED-14 | Rank-aware viral share prompt (Crown when #1) | Dynamic UI |
| FEED-15 | Enter Battle CTA (gated through free-limit check) | Credit-aware |

---

## 8. CREDITS, PAYWALL & MONETIZATION

### 8.1 Credit System
| Req ID | Requirement | Route |
|--------|-------------|-------|
| CREDIT-01 | Credit balance check | `GET /api/credits/balance` |
| CREDIT-02 | 10 credits per story video generation | Deducted on create |
| CREDIT-03 | Admin/unlimited: `is_unlimited=true`, credits=999999 | Special display |
| CREDIT-04 | Credit ledger (all transactions) | `credit_ledger` collection |
| CREDIT-05 | Credits never go negative | Backend guard |

### 8.2 Free Tier
| Req ID | Requirement |
|--------|-------------|
| CREDIT-06 | FREE_BATTLE_ENTRIES = 3 |
| CREDIT-07 | After 3 entries + 0 credits → `needs_payment = true` |
| CREDIT-08 | Guest/free story experience at `/experience` |

### 8.3 Paywall
| Req ID | Requirement |
|--------|-------------|
| CREDIT-09 | BattlePaywallModal (MODAL ONLY — never navigates away) |
| CREDIT-10 | Paywall triggers: `free_limit`, `loss_moment`, `near_win`, `enter_battle` |
| CREDIT-11 | Packs: ₹49/5 entries, ₹149/20 entries, ₹299/50 entries |
| CREDIT-12 | Returns to SAME blocked action after payment success |
| CREDIT-13 | Copy sells WINNING not credits ("Win the battle", "Take the top spot") |

### 8.4 Plans & Subscriptions
| Req ID | Requirement | Route |
|--------|-------------|-------|
| CREDIT-14 | Weekly/monthly/quarterly/yearly plans | `GET /api/subscriptions/plans` |
| CREDIT-15 | Top-up purchases | `/app/pricing` |
| CREDIT-16 | Subscription management | `/app/subscription` |
| CREDIT-17 | Regional pricing | `/api/pricing-catalog` |

---

## 9. PAYMENT GATEWAY (Cashfree)

### 9.1 Checkout Flow
| Req ID | Requirement | Route |
|--------|-------------|-------|
| PAY-01 | Create payment order | `POST /api/cashfree/create-order` |
| PAY-02 | Cashfree inline checkout (redirectTarget: '_modal') | Frontend SDK |
| PAY-03 | Verify payment status | `GET /api/cashfree/verify/{order_id}` |
| PAY-04 | Poll pending status until resolved | Client-side polling |
| PAY-05 | Production keys configured | `CASHFREE_APP_ID` env |
| PAY-06 | Sandbox keys for testing | `CASHFREE_SANDBOX_APP_ID` env |

### 9.2 Webhook Processing
| Req ID | Requirement | Route |
|--------|-------------|-------|
| PAY-07 | Cashfree webhook handler | `POST /api/cashfree-webhook/` |
| PAY-08 | Signature verification | HMAC validation |
| PAY-09 | Idempotent processing (one payment = one credit grant) | `idempotency_keys` collection |
| PAY-10 | Duplicate webhook handling | Dedup by order_id |
| PAY-11 | Payment reconciliation | `payment_reconciliation_runs` |
| PAY-12 | Auto-refund for failed credits | `auto_refund` service |

---

## 10. POST-GENERATION LOOP (Feature Flag: `postGenerationLoop`)

### 10.1 Result Page
| Req ID | Requirement |
|--------|-------------|
| POSTGEN-01 | Completed video player with autoplay |
| POSTGEN-02 | Title, metadata, thumbnail display |
| POSTGEN-03 | Share controls (copy link, social share) |
| POSTGEN-04 | Download button (entitled) |
| POSTGEN-05 | Refresh preserves correct content |
| POSTGEN-06 | Direct URL with projectId loads correct result |

### 10.2 Retention CTAs
| Req ID | Requirement |
|--------|-------------|
| POSTGEN-07 | "Make it 10x better?" → Rewrite with twist (reopens studio with context) |
| POSTGEN-08 | "Not the vibe you wanted?" → Change style (same story, different style) |
| POSTGEN-09 | "You're Rank #3 right now" → Enter battle (routes to battle page) |
| POSTGEN-10 | "Create Entirely New Story" → Fresh studio session |
| POSTGEN-11 | Cross-tool conversions via CreationActionsBar |

### 10.3 Continuation System
| Req ID | Requirement |
|--------|-------------|
| POSTGEN-12 | Episode continuation (same story, next part) |
| POSTGEN-13 | Branch continuation (same world, different story) |
| POSTGEN-14 | Custom direction continuation |
| POSTGEN-15 | Style remix grid (quick style change) |

---

## 11. SHARE & VIRAL DISTRIBUTION

### 11.1 Share System
| Req ID | Requirement | Route |
|--------|-------------|-------|
| SHARE-01 | Share page for public stories | `/share/:shareId` |
| SHARE-02 | Public creation page | `/v/:slug` |
| SHARE-03 | Viral pack share | `/viral/:jobId` |
| SHARE-04 | Share event tracking | `share_events` collection |
| SHARE-05 | Creator revisit tracking | `share_rewards` collection |
| SHARE-06 | Copy link to clipboard | Client-side |
| SHARE-07 | Social share (WhatsApp, Instagram, Twitter) | Deep links |

### 11.2 Viral Flywheel
| Req ID | Requirement | Route |
|--------|-------------|-------|
| SHARE-08 | Viral rewards for shares | `viral_rewards` collection |
| SHARE-09 | Share-to-credits conversion | Credit rewards |
| SHARE-10 | Viral momentum badge | `ViralMomentumBadge` component |
| SHARE-11 | Remix lineage tracking | `remix_lineage` collection |
| SHARE-12 | Force share gate (after N generations) | `ForceShareGate` component |

---

## 12. PUSH NOTIFICATIONS

| Req ID | Requirement | Route |
|--------|-------------|-------|
| PUSH-01 | Push subscription management | `POST /api/push/subscribe` |
| PUSH-02 | VAPID key configuration | `.env` VAPID keys |
| PUSH-03 | Rank drop push to ALL affected users | `battle_rank_snapshot` collection |
| PUSH-04 | Trigger-specific push actions | Service worker |
| PUSH-05 | Frontend push prompt in BattlePulse | `PushPrompt` component |

---

## 13. CREATOR TOOLS SUITE

### 13.1 Video & Visual Tools
| Req ID | Tool | Route |
|--------|------|-------|
| TOOL-01 | Story Video Studio (core pipeline) | `/app/story-video-studio` |
| TOOL-02 | Reel Generator | `/app/reel-generator` |
| TOOL-03 | Photo to Comic | `/app/photo-to-comic` |
| TOOL-04 | Reaction GIF Maker | `/app/reaction-gif` |
| TOOL-05 | GIF Maker (legacy) | `/app/gif-maker-old` |
| TOOL-06 | Coloring Book Wizard | `/app/coloring-book` |
| TOOL-07 | Comic Storybook Builder | `/app/comic-storybook` |
| TOOL-08 | Promo Videos | `/app/promo-videos` |

### 13.2 Text & Content Tools
| Req ID | Tool | Route |
|--------|------|-------|
| TOOL-09 | Story Generator | `/app/story-generator` |
| TOOL-10 | Bedtime Story Builder | `/app/bedtime-story-builder` |
| TOOL-11 | Story Episode Creator | `/app/story-episode-creator` |
| TOOL-12 | Story Hook Generator | `/app/story-hook-generator` |
| TOOL-13 | Caption Rewriter Pro | `/app/caption-rewriter` |
| TOOL-14 | Brand Story Builder | `/app/brand-story-builder` |
| TOOL-15 | Instagram Bio Generator | `/app/instagram-bio-generator` |
| TOOL-16 | Comment Reply Bank | `/app/comment-reply-bank` |
| TOOL-17 | YouTube Thumbnail Generator | `/app/thumbnail-generator` |
| TOOL-18 | Offer Generator | `/app/offer-generator` |
| TOOL-19 | Daily Viral Ideas | `/app/daily-viral-ideas` |
| TOOL-20 | Tone Switcher | `/app/tone-switcher` |
| TOOL-21 | Challenge Generator | `/app/challenge-generator` |
| TOOL-22 | Content Challenge Planner | `/app/content-challenge-planner` |
| TOOL-23 | Content Blueprint Library | `/app/blueprint-library` |
| TOOL-24 | Content Engine | Admin: `/app/admin/content-engine` |

### 13.3 Discovery & Matching
| Req ID | Tool | Route |
|--------|------|-------|
| TOOL-25 | Twin Finder | `/app/twinfinder` |
| TOOL-26 | Creator Pro Tools | `/app/creator-pro` |

---

## 14. CHARACTER SYSTEM

| Req ID | Requirement | Route |
|--------|-------------|-------|
| CHAR-01 | Character creator | `/app/characters/create` |
| CHAR-02 | Character library | `/app/characters` |
| CHAR-03 | Character detail page | `/app/characters/:characterId` |
| CHAR-04 | Character consistency studio | `/app/character-studio` |
| CHAR-05 | Public character page | `/character/:characterId` |
| CHAR-06 | Character profiles (visual bibles, voice, relationships) | Multiple collections |
| CHAR-07 | Character continuity validation | `character_continuity_validations` |
| CHAR-08 | Character follows | `character_follows` collection |

---

## 15. SERIES & EPISODES

| Req ID | Requirement | Route |
|--------|-------------|-------|
| SERIES-01 | Create story series | `/app/story-series/create` |
| SERIES-02 | Series listing | `/app/story-series` |
| SERIES-03 | Series timeline | `/app/story-series/:seriesId` |
| SERIES-04 | Public series page | `/series/:seriesId` |
| SERIES-05 | Episode linking to series | `series_id` + `episode_number` in job |
| SERIES-06 | Story chain view | `/app/story-chain/:chainId` |
| SERIES-07 | Story chain timeline | `/app/story-chain-timeline/:storyId` |

---

## 16. ADMIN PANEL (`/app/admin/*`)

### 16.1 Core Admin
| Req ID | Module | Route |
|--------|--------|-------|
| ADMIN-01 | Admin Dashboard (overview) | `/app/admin` |
| ADMIN-02 | User Management | `/app/admin/users` |
| ADMIN-03 | Audit Logs | `/app/admin/audit-logs` |
| ADMIN-04 | Account Lock Management | `/app/admin/account-locks` |
| ADMIN-05 | Feedback Management | `/app/admin/feedback` |

### 16.2 Analytics & Monitoring
| Req ID | Module | Route |
|--------|--------|-------|
| ADMIN-06 | Realtime Analytics | `/app/admin/realtime-analytics` |
| ADMIN-07 | User Analytics | `/app/admin/user-analytics` |
| ADMIN-08 | Story Video Analytics | `/app/admin/story-video-analytics` |
| ADMIN-09 | Growth Dashboard | `/app/admin/growth` |
| ADMIN-10 | Retention Dashboard | `/app/admin/retention` |
| ADMIN-11 | Revenue Analytics | `/app/admin/revenue` |
| ADMIN-12 | Conversion Dashboard | `/app/admin/conversion` |
| ADMIN-13 | Template Analytics | `/app/admin/template-analytics` |
| ADMIN-14 | GA4 Event Tester | `/app/admin/ga4-tester` |

### 16.3 Infrastructure
| Req ID | Module | Route |
|--------|--------|-------|
| ADMIN-15 | Performance Monitoring | `/app/admin/performance` |
| ADMIN-16 | System Health | `/app/admin/system-health` |
| ADMIN-17 | Environment Monitor | `/app/admin/environment-monitor` |
| ADMIN-18 | Worker Dashboard | `/app/admin/workers` |
| ADMIN-19 | TTFD Analytics | `/app/admin/ttfd-analytics` |
| ADMIN-20 | Self-Healing Dashboard | `/app/admin/self-healing` |
| ADMIN-21 | Production Metrics | `/app/admin/production-metrics` |
| ADMIN-22 | Monitoring Dashboard | `/app/admin/monitoring` |
| ADMIN-23 | SRE Monitoring | `/api/sre/*` |

### 16.4 Security & Abuse
| Req ID | Module | Route |
|--------|--------|-------|
| ADMIN-24 | Security Dashboard | `/app/admin/security` |
| ADMIN-25 | Media Security | `/app/admin/media-security` |
| ADMIN-26 | Anti-Abuse Dashboard | `/app/admin/anti-abuse` |
| ADMIN-27 | Login Activity | `/app/admin/login-activity` |

### 16.5 Operations
| Req ID | Module | Route |
|--------|--------|-------|
| ADMIN-28 | Payments Dashboard | `/app/admin/payments` |
| ADMIN-29 | Template Leaderboard | `/app/admin/leaderboard` |
| ADMIN-30 | Daily Report | `/app/admin/daily-report` |
| ADMIN-31 | User Activity | `/app/admin/user-activity` |
| ADMIN-32 | Bio Templates Admin | `/app/admin/bio-templates` |
| ADMIN-33 | Automation Dashboard | `/app/admin/automation` |
| ADMIN-34 | Content Engine | `/app/admin/content-engine` |

---

## 17. ANALYTICS & FUNNEL TRACKING

### 17.1 Backend Funnel Tracking
| Req ID | Requirement | Route |
|--------|-------------|-------|
| ANAL-01 | Track funnel event | `POST /api/funnel/track` |
| ANAL-02 | Admin funnel metrics | `GET /api/funnel/metrics?days=N` |
| ANAL-03 | Events stored in `funnel_events` collection | MongoDB |
| ANAL-04 | Rich context: user_id, session_id, device_type, traffic_source, story_id, battle_id | Per event |

### 17.2 Critical 7 Events (V3)
| Req ID | Event | Dedup Guard |
|--------|-------|-------------|
| ANAL-05 | `session_started` | useRef (once per mount) |
| ANAL-06 | `session_ended` | sendBeacon on beforeunload/visibilitychange |
| ANAL-07 | `typing_started` | typingStartedRef (once per session) |
| ANAL-08 | `generate_clicked` | createLockRef |
| ANAL-09 | `generation_completed` | poll-based (on COMPLETED status) |
| ANAL-10 | `postgen_cta_clicked` (with type) | click-based |
| ANAL-11 | `battle_enter_clicked` | click-based |

### 17.3 Full Event Catalog (50+ events)
| Category | Events |
|----------|--------|
| Landing | `landing_view`, `first_action_click` |
| Demo | `demo_viewed`, `story_generation_started/success/failed/timeout` |
| Engagement | `story_viewed`, `story_card_clicked`, `watch_started/completed_50/100`, `scroll_depth_50` |
| Spectator | `spectator_impression`, `spectator_pressure_shown`, `spectator_quick_shot`, `spectator_to_player_conversion` |
| Feed | `feed_card_impression`, `preview_started/completed/failed` |
| Battle | `entered_battle`, `creation_started/abandoned` |
| Paywall | `battle_paywall_viewed`, `battle_pack_selected`, `battle_payment_success/abandoned` |
| Viral | `win_share_triggered`, `return_trigger_sent/clicked` |
| Continue | `continue_clicked`, `story_part_generated`, `paywall_teaser_shown` |
| Core | `generation_started/completed`, `result_viewed`, `paywall_viewed`, `plan_selected`, `payment_started/success/abandoned` |

### 17.4 Google Analytics 4
| Req ID | Requirement |
|--------|-------------|
| ANAL-12 | GA4 event tracking via `window.gtag` |
| ANAL-13 | E-commerce tracking (view_item, add_to_cart, begin_checkout, purchase) |
| ANAL-14 | A/B testing system with variant assignment |
| ANAL-15 | Session tracking with `initSession()` |

---

## 18. MEDIA STORAGE & DELIVERY

### 18.1 Cloudflare R2 Storage
| Req ID | Requirement |
|--------|-------------|
| MEDIA-01 | All generated assets stored in Cloudflare R2 bucket |
| MEDIA-02 | Asset paths: `images/`, `videos/`, `audio/`, `thumbnails/`, `previews/` |
| MEDIA-03 | Presigned URL upload for large files |
| MEDIA-04 | Multipart upload for files > 5MB |

### 18.2 R2 Media Proxy
| Req ID | Requirement | Route |
|--------|-------------|-------|
| MEDIA-05 | R2 proxy for non-public bucket | `GET /api/media/r2/{path}` |
| MEDIA-06 | Presigned URL generation (1hr TTL, cached) | 302 redirect |
| MEDIA-07 | `safeMediaUrl()` converts R2 CDN URLs to proxy paths | Frontend utility |
| MEDIA-08 | `SafeImage` component with IntersectionObserver lazy loading | Priority + lazy |
| MEDIA-09 | Gradient fallback on image load failure | Visual fallback |

### 18.3 Media Protection
| Req ID | Requirement | Route |
|--------|-------------|-------|
| MEDIA-10 | Tokenized media streaming | `GET /api/media/stream/{token}` |
| MEDIA-11 | Download entitlement check | `GET /api/media/entitlement` |
| MEDIA-12 | Download token issuance | `POST /api/media/download-token` |
| MEDIA-13 | Media session tracking | `user_media_sessions` collection |
| MEDIA-14 | Watermark service | `watermark_service.py` |

---

## 19. SECURITY & ABUSE PREVENTION

### 19.1 Input Security
| Req ID | Requirement |
|--------|-------------|
| SEC-01 | XSS sanitization on all user text input (bleach + html.escape) |
| SEC-02 | NoSQL injection prevention |
| SEC-03 | Oversized payload handling (max_length enforcement) |
| SEC-04 | CORS configured (all origins for preview) |
| SEC-05 | Security headers middleware (CSP, HSTS, X-Frame-Options) |

### 19.2 Rate Limiting & Abuse Detection
| Req ID | Requirement |
|--------|-------------|
| SEC-06 | `slowapi` rate limiter on sensitive endpoints |
| SEC-07 | Account lockout after repeated login failures |
| SEC-08 | Abuse detection for generation (exempt admin) |
| SEC-09 | IP-based security service |
| SEC-10 | Anti-abuse logging and dashboard |

### 19.3 Content Safety
| Req ID | Requirement |
|--------|-------------|
| SEC-11 | Rewrite engine: keyword-based content sanitization |
| SEC-12 | Semantic pattern detection |
| SEC-13 | Trademark/IP detection and rewrite |
| SEC-14 | Safety event logging |
| SEC-15 | Output validation (post-generation) |

---

## 20. PERFORMANCE & OPTIMIZATION

### 20.1 Frontend Performance
| Req ID | Requirement |
|--------|-------------|
| PERF-01 | Route-level React.lazy code splitting (5 eager + 136 lazy imports) |
| PERF-02 | Suspense fallback with PageLoader spinner |
| PERF-03 | Image lazy loading via IntersectionObserver |
| PERF-04 | Dashboard loads in < 2s (measured: 0.48s repeat, 1.8s first) |

### 20.2 Backend Performance
| Req ID | Requirement |
|--------|-------------|
| PERF-05 | Consolidated dashboard API (7 calls → 1) |
| PERF-06 | TTL caching on dashboard init (20s), feed endpoints |
| PERF-07 | Parallel query execution with `asyncio.gather` |
| PERF-08 | R2 presigned URL caching (1hr TTL) |

### 20.3 Queue & Scalability
| Req ID | Requirement |
|--------|-------------|
| PERF-09 | Job queue with semaphore (prevent meltdown) |
| PERF-10 | QUEUED state with graceful wait |
| PERF-11 | Degradation matrix (busy system → reduced scenes) |
| PERF-12 | Load guard alerts |

---

## 21. ONBOARDING & USER GUIDANCE

| Req ID | Requirement |
|--------|-------------|
| ONBOARD-01 | First-time onboarding overlay (closeable/skippable via localStorage) |
| ONBOARD-02 | Journey progress bar (studio/character flows) |
| ONBOARD-03 | First action overlay |
| ONBOARD-04 | Post-value overlay (after first navigation, not on first visit) |
| ONBOARD-05 | Guide assistant |
| ONBOARD-06 | App tour (TourProvider) |
| ONBOARD-07 | Upgrade modal (paywall) |
| ONBOARD-08 | Responsive support wrapper |

---

## 22. REFERRAL & GROWTH SYSTEMS

| Req ID | Requirement | Route |
|--------|-------------|-------|
| REF-01 | Referral program | `/app/referral` |
| REF-02 | Referral code generation | `referral_codes` collection |
| REF-03 | Gift cards | `/app/gift-cards` |
| REF-04 | Streaks (creation streaks) | `creation_streaks`, `streaks` collections |
| REF-05 | Daily rewards | `/api/daily-rewards` |
| REF-06 | Viral growth metrics | `viral_growth_metrics` collection |
| REF-07 | Retention hooks | `retention_hooks` routes |
| REF-08 | Re-engagement events | `reengagement_events` collection |

---

## DATABASE SCHEMA (Key Collections — 222 Total)

| Collection | Purpose | Key Fields |
|------------|---------|------------|
| `users` | User accounts | email, password_hash, role, credits, name |
| `story_engine_jobs` | Core pipeline jobs | job_id, user_id, state, title, story_text, output_url, thumbnail_url, battle_score |
| `story_drafts` | Draft persistence | user_id, status (draft/processing/completed), title, story_text |
| `funnel_events` | Funnel tracking | step, session_id, user_id, timestamp, device_type, traffic_source |
| `orders` | Payment orders | order_id, user_id, amount, status, credits |
| `credit_ledger` | Credit transactions | user_id, amount, type, reason, timestamp |
| `media_assets` | Media derivatives | job_id, type, url, status |
| `battle_rank_snapshot` | Rank tracking for push | user_id, rank, battle_id |
| `sessions` | User sessions | session_id, user_id, start, end |
| `login_activity` | Login audit trail | user_id, ip, timestamp, success |
| `push_subscriptions` | Push notification subs | user_id, endpoint, keys |
| `shares` | Share records | share_id, job_id, creator_id |
| `daily_challenges` | Daily war challenges | date, theme, active |
| `ab_experiments` | A/B test configs | experiment_id, variants |
| `pipeline_jobs` | Legacy pipeline jobs | job_id, status, stages |

---

## FEATURE FLAGS

| Flag | Default | Controls |
|------|---------|----------|
| `draftPersistenceV2` | `true` | State-based draft lifecycle |
| `postGenerationLoop` | `true` | Rewrite/style/battle CTAs after result |
| `recentDraftsPanel` | `true` | Recent drafts panel in studio |
| `guidedStartV2` | `true` | Category-based idea generation with vibe picker |

---

## API ENDPOINT SUMMARY (Key Routes)

| Category | Prefix | Key Endpoints |
|----------|--------|---------------|
| Auth | `/api/auth` | register, login, google, profile, forgot-password, reset-password |
| Dashboard | `/api/dashboard` | init |
| Drafts | `/api/drafts` | save, current, recent, discard, status, idea |
| Story Engine | `/api/story-engine` | create, status/{id}, credit-check |
| Battle | `/api/story-multiplayer` | battle-pulse/{id} |
| Stories | `/api/stories` | hottest-battle, battle-entry-status, quick-shot |
| Credits | `/api/credits` | balance |
| Payments | `/api/cashfree` | create-order, verify/{id} |
| Webhook | `/api/cashfree-webhook` | / |
| Funnel | `/api/funnel` | track, metrics |
| Media | `/api/media` | r2/{path}, stream/{token}, entitlement |
| Engagement | `/api/engagement` | story-feed |
| Share | `/api/share` | create, /{id} |
| Push | `/api/push` | subscribe |
| Admin | `/api/admin` | users, metrics, etc. |
| Health | `/api/health` | / |

---

*Document generated: April 14, 2026*
*Total: 153 backend routes, 100+ frontend pages, 222 database collections*
