# Visionary Suite — PRD

## Product Vision
AI-powered creator suite that turns ideas into cinematic videos, comics, GIFs, and more. Features AI Character Memory, Growth Engine for viral acquisition/retention, and a truth-based Admin Control Center.

## Core Features (Implemented)
- Story Video Studio, Comic Storybook, Photo to Comic, GIF Maker
- Story Series Engine (stateful multi-episode narratives)
- AI Character Memory System (3 sprints: MVP, Cross-Tool, Visual Bibles)
- Pricing & Monetization (4-tier system)
- Public explore/gallery/sharing pages
- Growth Engine (Auto-Extraction, Character Sharing, Series Rewards)

## Admin Control Center (IMPLEMENTED — Truth-Based)

### Architecture
- Backend: 6 real-time metrics endpoints at `/api/admin/metrics/*`
- Frontend: 5-section tabbed dashboard with auto-refresh (15s polling)
- Widget states: LOADING | READY | EMPTY | ERROR | STALE
- No hardcoded values — every metric from real DB collections

### Sections
1. **Executive Snapshot**: Total Users, Active Users (24h), Active Sessions, Generations, Revenue, Avg Rating, System Health, Queue Depth, Stuck Jobs, Avg/Max Render, Active Series, Episodes, Characters, Continuation Rate
2. **Growth Funnel**: Page Views → Remix Clicks → Tool Opens → Generate Clicks → Signups → Completions → Shares. Viral K coefficient, Avg Shares/Creator
3. **Reliability**: System Health (Database, Queue, Stuck Jobs), Queue Depth, Active Jobs, Stuck Jobs, Avg/Max Render Time per Tool
4. **Story Intelligence**: Active Series, Total Episodes, Avg Episodes/Series, Continuation Rate, Total Characters, Auto-Extracted, Character Reuse Rate, Continuity Pass Rate, Most Reused Character, Rewards Claimed
5. **Revenue**: Total Revenue, Revenue Today, Transactions, Paying Users, ARPU, Conversion Rate, Active Subscriptions, Recent Transactions

### Backend Endpoints
- `GET /api/admin/metrics/summary` — Executive snapshot
- `GET /api/admin/metrics/funnel` — Growth funnel
- `GET /api/admin/metrics/reliability` — Queue, workers, health
- `GET /api/admin/metrics/revenue` — Payments, ARPU, subscriptions
- `GET /api/admin/metrics/series` — Story/character intelligence
- `GET /api/admin/metrics/safety` — Moderation, abuse metrics

## Growth Engine (P0 — Complete)
1. Auto-Character Extraction (confidence scoring, deduplication, user confirmation)
2. Character-Based Sharing Loop (public pages, no login wall, remix_data integration)
3. Series Completion Rewards (milestones at 3/5/10, emotional + functional rewards)

## In-Product Guidance (Complete)
- 5-step Quick Start Guide overlay for new users
- Inline tips on empty prompts (StoryVideoStudio, CreateSeries, CharacterCreator)
- Improved empty states (StorySeries, CharacterLibrary)
- Copyright/consent disclaimers on creation tools

## Tech Stack
- Frontend: React, Tailwind CSS, Shadcn/UI, lucide-react
- Backend: FastAPI, Python
- Database: MongoDB
- Integrations: OpenAI (GPT-4o-mini, GPT Image 1, Sora 2, TTS), Gemini, Google Auth, Cloudflare R2
- Other: Redis, apscheduler, ffmpeg, JSZip

## Authentication
- JWT + Google Auth (Emergent-managed)
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Backlog
- (P1) WebSocket live updates for admin dashboard (currently polling)
- (P1) Growth event tracking integration (emit events on user actions)
- (P2) Style preset preview thumbnails for Photo to Comic
- (P2) Full background uniformity cleanup for remaining pages
