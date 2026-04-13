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

## Audit Fixes Applied (Apr 13)
- Cookie consent: shrunk to small bottom-right toast (no longer blocks CTAs)
- Journey Progress Bar: only shows on Studio/Pipeline pages (removed from Dashboard, Battle, Viewer)
- Dashboard restructured: Battle-first (HottestBattle → TrendingPublicFeed → HeroSection)
- PostValueOverlay: "Continue with limited access" stays on /app (no studio redirect)
- Explore page: only shows stories with thumbnails (no blank cards)
- Login: correctly redirects to /app dashboard

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
