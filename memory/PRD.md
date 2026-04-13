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

## Psychology Layer — DONE (Apr 13)

### 1. Quick Shot Instant Dopamine (ego boost, not just confirmation):
- Overlay shows parent story thumbnail + "You're competing for #1"
- "Your version of [title] is live" + "vs N others" + "If this wins, it gets pushed to everyone"
- 2.5s display → auto-navigate to pipeline

### 2. Identity + Ranking on Watch Page:
- Battle Status shows: Rank #, Score, Views — live data
- "Share to climb ranks — views and continuations determine the winner"
- Leaderboard button always visible

### 3. Social Proof Density:
- Battle header: "{N} creators competing right now — {X} views"
- Leaderboard: "#1 — Leading" label on top entry
- Story cards: view counts + "X competing" labels
- Section rows: "{N} stories · {X}K views" subtitles

### 4. Competitive Copy (provokes action, not just informs):
- "Beat #1 — Easy Win" / "Only X pts — easy win"
- "Rankings can change anytime. One good entry = you take #1"
- "Track Your Ranking — See if you're winning or losing"
- "Enter Instantly — We generate a version. No thinking. No typing."

### 5. Auto-Play on ALL Cards:
- enablePreviewOnVisible for every card (not just priority)
- Desktop + mobile IntersectionObserver auto-play

---

## All Systems (Apr 12-13)
- Queue System, Data Integrity, Export Pipeline
- Consumption-First Loop, Entry Conversion Engine
- Analytics Dashboard, Funnel Integrity
- Quick Shot blank screen fix, Route fix (7 files)

---

## Backlog

### P0 (Wait 48h for data)
- Measure click rate improvement from auto-play + social proof
- Measure Enter Battle CTR
- Validate Quick Shot retention at scale

### P1
- Auto-Recovery FAILED_PERSISTENCE
- Secondary Action Matrix

### P2
- Resend domain, personalized headlines
