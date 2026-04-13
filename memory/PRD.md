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

## Quick Shot Blank Screen Fix — DONE (Apr 13)

### Root cause: Wrong route. All post-creation redirects used `/app/story-video-pipeline` but the actual route is `/app/story-video-studio`.
- Fixed in 7 files: HottestBattle, CompetitionPulse, StoryViewerPage, StoryBattlePage, StoryChainTimeline, StoryVideoPipeline (self-references)
- Quick Shot now shows: "Queued for rendering" → progress stages → "What's happening now" → explore links
- Added IDLE/GENERATING fallback: "Creating your battle entry..." message with spinner for jobs without preview assets yet

### UX Clarity Fix:
- Every battle row now has instruction text explaining what to do
- "Compete or watch others win. Top entry gets visibility."
- "#1 — Leading" label on top contender
- Quick Shot: "We generate a competitive version for you. No thinking. No typing."
- View Your Battle: "See your ranking, views, and competitors"

---

## All Systems (Apr 12-13)
- Queue System, Data Integrity, Export Pipeline
- Consumption-First Loop, Entry Conversion Engine
- Post-Launch-Branch, Analytics Dashboard
- Funnel Integrity, "Enter Battle" CTA

---

## Backlog

### P0 (Data-driven)
- Attack 86% impression→click drop: auto-play preview
- Monitor Enter Battle CTR vs old 0%

### P1
- Auto-Recovery FAILED_PERSISTENCE, Secondary Action Matrix

### P2
- Resend domain, hover autoplay
