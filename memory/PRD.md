# Visionary Suite - Product Requirements Document

## Architecture
- **Frontend**: React (CRA) + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB + Redis
- **URL**: https://trust-engine-5.preview.emergentagent.com

## Credentials
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

---

## Core Philosophy: WATCH > ENTER BATTLE > CREATE

---

## Push Notifications on Rank Drop (P0) — DONE (Apr 13)

### Backend:
- `check_and_send_rank_notifications()` now tracks ALL users via `battle_rank_snapshot` collection
- Compares current rank map vs stored snapshot — pushes to EVERY user who dropped, not just old #1
- Rate-limited: 1 rank_drop push per user per battle per 2 hours
- Push fires on: increment-metric (views/shares) AND pipeline completion (new branch finishes rendering)
- Web Push via `pywebpush` with VAPID keys
- `trigger_rank_drop_push()` copy: "You dropped to #N / Someone just beat your entry on 'Title'. Come back now and take your spot."

### Frontend:
- `BattlePulse.jsx` shows push notification prompt when user has a rank and permission is 'default'
- Prompt: bell icon + "Get notified if your rank drops / We'll send a push when someone beats you" + Enable/Dismiss buttons
- `usePushNotifications.js` hook manages service worker registration and push subscription
- Auto-subscribes on `StoryViewerPage` when viewing a battle entry with permission already granted

### Service Worker (`sw-push.js`):
- `requireInteraction: true` for rank_drop (notification stays until tapped)
- Aggressive vibration pattern [200, 100, 200, 100, 300] for rank_drop
- Trigger-specific CTA: "Take it back" for rank_drop, "Claim #1" for near_win
- Deep-links to Story Battle screen on click

---

## WIN Share Trigger (P0.5) — DONE (Apr 13)

### BattlePulse WIN Moment:
- **Persistent** — does NOT auto-dismiss (user must click X or share)
- Crown icon (w-12 h-12) + "YOU'RE #1" + "You just beat N others"
- "This is getting pushed to more users"
- **PRIMARY Share CTA**: full-width amber button "Share now to lock your position"
- "Sharing boosts your visibility score"
- Tracks `win_share_triggered` funnel event

### StoryViewerPage Rank-Aware Share:
- `battle_rank` field added to viewer API response
- When rank = 1: Crown icon + "You're #1 — Share to lock it" (amber-500/20 bg, border-2)
- When rank > 1: standard "This could go viral" prompt
- Share increments both shares metric and funnel tracking

---

## Autoplay Hook Quality (P1) — DONE (Apr 13)

### TrendingPublicFeed Cards:
- **Hook text overlay**: context-aware text on card thumbnails
  - 3+ competitors: "N people competing for #1"
  - 2+ competitors: "Battle in progress"  
  - 20+ views: "Trending now"
- **LIVE indicator**: red pulse dot + "LIVE" badge for stories with active competitors
- Hot badge only shows when no hook text overlay present (prevents overlap)
- Competitive signals (views, competitors) visible at glance

### StoryCardMedia:
- New props: `hookText`, `competitorCount`, `viewCount`
- Hook text overlay: blurred bg, bold white text, top-left positioned
- Social proof badges: top-right, views + "competing" count

---

## All Systems (Apr 12-13)
- Queue System, Data Integrity, Export Pipeline
- Consumption-First Loop, Entry Conversion Engine
- Analytics Dashboard + Funnel Integrity
- Auto-play, Social proof, Competitive copy
- Instant dopamine, Continuous tension, Identity/ranking
- WIN/LOSS moments, Real-time battle pulse
- Viral share prompts, Return triggers
- **Push notifications on ALL rank drops**
- **Persistent WIN share trigger**
- **Autoplay hook text overlays + LIVE indicators**

---

## Backlog

### P0 (Data-driven)
- Monitor: 2nd action rate, CTR, session time
- Validate WIN/LOSS → share conversion rate

### P1
- Follow Creator / Network Graph Expansion
- Auto-Recovery FAILED_PERSISTENCE (P0.6)
- Phase C Gamification (Dark launched, gated behind GREENLIGHT)

### P2
- Personalized headline serving by channel
- Admin WebSocket upgrade
- Resend domain verification (blocked on DNS)
