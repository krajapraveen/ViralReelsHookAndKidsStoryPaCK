# Visionary Suite - Product Requirements Document

## Architecture
- **Frontend**: React (CRA) + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB + Redis
- **URL**: https://trust-engine-5.preview.emergentagent.com

## Credentials
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

---

## Core Philosophy: WATCH > MAKE YOUR VERSION > CREATE

---

## Conversion Analytics Dashboard — DONE + INTEGRITY FIX (Apr 12)

### Funnel Integrity Fix:
- **Problem**: 27 entries shown from only 3 clicks — data lie
- **Root cause**: Quick Shots bypass card clicks entirely; demo/seed data inflated entry count
- **Fix**: Funnel now shows TWO paths separately:
  1. Card path: impression → click → watch → create_cta_clicked
  2. Quick Shot path: quick_shot_fired (bypasses card click)
- Attribution warnings flag unattributed entries (pre-tracking data)
- Formula transparency: every metric shows exact formula on click

### Social Proof on Cards:
- View count + competition count added to story cards
- Engagement feed now includes total_views and total_children in response

### Key Data Insights:
- 86% drop impression→click = BIGGEST LEAK (card hooks not compelling enough)
- Quick Shot = strongest converter (bypasses click friction entirely)
- 0 Make Your Version clicks = secondary CTA not converting at all
- 19 unattributed entries = pre-tracking demo data (correctly flagged)

---

## All Completed Systems (Apr 12)
- Queue System (hardened, FIFO, drain on success+failure)
- Unfinished Worlds fix, Post-Launch-Branch flow
- Data Integrity, Export Pipeline
- Consumption-First Viral Loop, Entry Conversion Engine
- System Integrity

---

## Backlog

### P0 (Next — based on data)
- Attack click rate: auto-play preview, curiosity hooks, urgency labels
- Validate Quick Shot retention (are they returning?)

### P1
- Auto-Recovery FAILED_PERSISTENCE
- Secondary Action Matrix, Follow Creator

### P2
- Resend domain, personalized headlines, hover autoplay
