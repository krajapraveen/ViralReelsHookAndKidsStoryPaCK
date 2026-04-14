# Visionary Suite - Product Requirements Document

## Architecture
- **Frontend**: React (CRA) + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB
- **Payments**: Cashfree (production + sandbox)
- **URL**: https://trust-engine-5.preview.emergentagent.com

## Credentials
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

---

## Core Philosophy: WATCH > ENTER BATTLE > GENERATE > COMPETE > PAY

## Video Preview Pipeline (Apr 13)
- **Media Derivative Pipeline** (`/app/backend/services/media_preview_pipeline.py`)
  - Generates 3 derivatives per video: poster_sm (webp), poster_md (webp), 2s muted preview clip (mp4 h264 faststart)
  - Hook selection: scene-based I-frame analysis, picks best 2s window (not just first 2s)
  - FFmpeg: 540px width, 24fps, CRF 28, no audio, faststart
  - Uploads to R2 under `/previews/{job_id}/`
  - `media_assets` collection tracks all derivatives
  - Auto-triggers on pipeline completion via `asyncio.create_task`
  - Admin backfill: `POST /api/stories/admin/backfill-previews`
- **Feed API** returns `preview_media` contract: `poster_url`, `preview_url`, `autoplay_enabled`, `processing_state`
- **Frontend autoplay**: IntersectionObserver triggers `video.play()` at 60% visibility, falls back to poster on failure, pauses on scroll-out
Dashboard order: PersonalAlertStrip → LiveBattleHero → QuickActions → TrendingPublicFeed → MomentumSection → HeroSection → Story Rows

### New Components:
- `LiveBattleHero.jsx` — Live battle zone with stats, rank, #1 preview, Enter Battle + Quick Shot CTAs. Polls pulse every 15s. Paywall-gated. Listens for `show-battle-paywall` global events.
- `QuickActions.jsx` — "Choose Your Path" section with 3 differentiated entry paths:
  - Primary: "Enter Battle Instantly" (AI auto-gen, spans 2 cols, credit-aware indicator, "Fastest path to the leaderboard" badge)
  - Secondary: "Write Your Own Entry" (studio with full creative control)
  - Tertiary: "Beat the Leader" (remix flow — shows dynamic #1 entry title, navigates to studio with remix context)
- `MomentumSection.jsx` — User stats: Current Rank, Battles Entered, Credits, Status

---

## Master Flow (Money Loop)
```
Dashboard → Quick Shot / Story Card → Overlay → Pipeline → Watch Page (Battle)
↓
User Actions: Share / Enter Again (Paywall) / Track Rank / Leave (Return Trigger)
↓
Return → Repeat → PAY
```

---

## Pages & Flows

### Dashboard (/app)
- Battle Cards with autoplay + hook text overlays
- Quick Shot CTA (1-tap, zero-input)
- View Battle CTA
- Trending Feed with LIVE indicators

### Quick Shot (NOT a page)
- API call + instant dopamine overlay + redirect to pipeline
- On 402 → Battle Paywall Modal (no navigation)
- On success → overlay with preview + ego boost → auto-redirect

### Pipeline (/app/story-video-studio)
- GENERATING: progress + competition context + activity pulse
- READY: auto-play video + rank + share/enter again CTAs
- Branch entries auto-redirect to Battle page after 3s
- FAILED: retry UI
- 402 credit gate modal (inline)

### Watch Page (/app/story-battle/:id) — CORE PAGE
7 Required Components:
1. Rank + Score card (gold #1 with Share, rose #2+ with "Take it back")
2. Live Activity (BattlePulse polling every 12s)
3. WIN/LOSS moments (persistent WIN, auto-dismiss LOSS)
4. Video autoplay (#1 contender)
5. Share CTA ("Share this battle")
6. Enter Battle CTA (paywall-gated, gradient button)
7. Return Trigger ("Come back in 10 minutes")

### Story Viewer (/app/story-viewer/:jobId)
- Consumption-first with video player
- Battle status banner with rank/score/views
- BattlePulse + push notification prompt
- Enter Battle gated through free-limit check
- Rank-aware viral share prompt (Crown when #1)

### Paywall (MODAL ONLY — BattlePaywallModal)
- Triggers: free_limit, loss_moment, near_win, enter_battle
- Packs: ₹49/5 entries, ₹149/20 entries, ₹299/50 entries
- Cashfree payment inline (redirectTarget: '_modal')
- Returns to SAME blocked action after payment success
- Never navigates away from context

### Payment Flow
```
Paywall Modal → Cashfree SDK → Verify → Credits Added → Resume Action
```

---

## Backend State Machine
- CREATED → GENERATING → READY → display
- FAILED → retry (max 2)
- QUEUED → wait for slot → GENERATING

## Free Entry Limit
- FREE_BATTLE_ENTRIES = 3
- After 3 entries + 0 credits → needs_payment = true → paywall
- GET /api/stories/battle-entry-status checks limit

## Push Notifications
- Rank drop push to ALL users who dropped (battle_rank_snapshot collection)
- Service worker with trigger-specific actions + persistent rank_drop
- Frontend prompt in BattlePulse when user has rank

## Psychology Layer
- WIN moment: persistent, unmissable Share CTA
- LOSS moment: "Act now" + push notification
- Competitive signals: "X people trying to beat #1"
- Return triggers: "Your rank might change"
- Hook text overlays on story cards

---

## Monetization
- 3 free battle entries
- ₹29 / ₹49 / ₹149 entry packs (micro-tier for impulse buy)
- Paywall triggers: free limit, loss moment, near win (AUTO)
- Near-win auto-paywall: rank #2/#3 within 5pts of #1 → forces paywall
- Credits: 10 per story_video generation
- Copy sells WINNING not credits ("Win the battle", "Take the top spot")

---

## Analytics (Tracked Events)
- spectator_impression, spectator_quick_shot, spectator_to_player_conversion
- battle_paywall_viewed, battle_pack_selected, battle_payment_success
- win_share_triggered, story_viewed, watch_started, watch_completed_50/100
- cta_clicked (type: enter_battle, share, next_episode, etc.)

---

## All Completed Systems
- Studio Fresh Session Fix (Apr 14): "Write Your Own Story" now opens a clean blank studio with no "Recent Videos" sidebar. The sidebar only shows when user navigates to studio directly (not from fresh creation intent). Prevents creation-vs-browsing intent collision.
- P0.5 Performance Hardening (Apr 14): Consolidated 7 dashboard API calls into single `/api/dashboard/init` endpoint. Dashboard load: 5.07s → 2.47s (first), 1.89s (repeat).
- P0 Performance Sprint (Apr 14): Route-level code splitting (141 eager → 5 eager + 136 lazy). Backend TTL caching for feed/battle endpoints. Image lazy loading on feed cards.
- CTA Route Separation Fix (Apr 13): "Write Your Own Story" → fresh studio. "Beat the Leader" → battle leaderboard. Updated labels and copy.
- UX Trust Fixes (Apr 13): (1) PostValueOverlay suppressed on first visit — only triggers after user has navigated away once. (2) Hero "Claim Your Rank" CTA now navigates to battle page first, paywall only on action attempt. Credit-aware micro-copy: "Entry requires credits · View the battle first, then decide". (3) Seeded 4 diverse battle themes (Midnight in Tokyo/anime, The Last Laugh/cartoon, Echoes of Mars/sci-fi, Recipe for Disaster/watercolor) to eliminate content repetition perception.
- Google Sign-In Hardened (Apr 13): Popup cancel → toast + re-enable. Rapid clicks → disabled guard. Backend error → clear toast. Loading overlay during exchange.
- P0 Google Sign-In Fix (Apr 13): Replaced broken `GoogleLogin` iframe component with `useGoogleLogin` popup hook. Custom styled button opens Google's OAuth popup directly. Backend verifies via access_token flow. No more iframe blocking.
- P0 Feed Fix (Apr 13): Dashboard "Trending Now" cards with no thumbnails now show rich fallback (gradient + title + animation style) instead of blank dark rectangles.
- CTA Conversion Redesign v2 (Apr 13): Killed hero/QuickActions duplication, renamed CTAs for action-impulse clarity, visual hierarchy with dominant primary card, credit-aware pre-click indicator, remix flow fix (studio with context instead of bare leaderboard), event bridge for paywall modal.
- Entry Conversion Engine (Quick Shot, personalized CTAs)
- Consumption-First UI (Watch > Make)
- Queue System (QUEUED state, graceful handling)
- Data Integrity (COMPLETED = asset exists)
- Export Pipeline (download validation, 410 handling)
- Conversion Analytics Dashboard
- Psychology Layer v1+v2 (tension, ego, urgency, fear)
- WIN/LOSS Moments + BattlePulse
- Push Notifications on ALL rank drops
- WIN Share Trigger (persistent, unmissable)
- Autoplay Hook Quality (text overlays, LIVE badges)
- Battle Paywall Modal (Cashfree inline)
- Free Entry Limit Enforcement
- Watch Page (7 components complete)
- Pipeline → Battle auto-redirect

---

## Backlog

### P1
- Follow Creator / Network Graph
- Auto-Recovery FAILED_PERSISTENCE
- Phase C Gamification (gated behind GREENLIGHT)

### P2
- Personalized headline serving by channel
- Admin WebSocket upgrade
- Resend domain verification (blocked on DNS)
