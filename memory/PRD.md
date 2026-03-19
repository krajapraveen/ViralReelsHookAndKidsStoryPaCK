# Visionary Suite — PRD

## Product Vision
AI-powered creator suite with Growth Engine, AI Character Memory, and truth-based Admin Control Center.

## Growth Event Tracking (P1 — IMPLEMENTED)

### Core Events (7)
1. `page_view` — Public pages (Gallery, Character, Creation)
2. `remix_click` — CTA clicks on public/share pages
3. `tool_open_prefilled` — Tool opened with remix data
4. `generate_click` — User clicks Generate button
5. `signup_completed` — User finishes signup
6. `creation_completed` — Generation finishes successfully
7. `share_click` — User shares content

### Event Schema (Strict Contract)
- event, session_id, user_id (nullable), anonymous_id
- source_page, source_slug, tool_type, creation_type
- series_id, character_id
- origin (direct|share_page|public_character_page|series_page)
- origin_slug, origin_character_id, origin_series_id
- referrer_slug, ab_variant (nullable), idempotency_key, meta

### Features
- Client-side batching (5s flush, immediate for critical events)
- Idempotency-based deduplication (2s debounce window)
- Anonymous→user session linkage on signup/login via POST /api/growth/link-session
- Admin funnel endpoint returns real conversion data

### Instrumented Pages
- PublicCharacterPage: page_view + remix_click + setOrigin
- PublicCreation: page_view + remix_click + share_click
- StoryVideoStudio: tool_open_prefilled + generate_click + creation_completed
- Signup: signup_completed + linkSessionToUser
- Login: linkSessionToUser
- CharacterDetail: share_click
- SeriesTimeline: share_click
- Gallery: page_view

## Admin Control Center (Truth-Based)
### Sections: Executive, Growth Funnel, Reliability, Story Intelligence, Revenue
### Architecture: REST snapshot + 15s polling auto-refresh
### Endpoints: /api/admin/metrics/* (summary, funnel, reliability, revenue, series, safety)

## Growth Engine (P0 — Complete)
1. Auto-Character Extraction (confidence scoring, deduplication, user confirmation)
2. Character-Based Sharing Loop (public pages, no login wall, remix_data integration)
3. Series Completion Rewards (milestones at 3/5/10)

## In-Product Guidance (Complete)
- 5-step Quick Start Guide, inline tips, empty state guidance, copyright disclaimers

## Core Features
- Story Video Studio, Comic Storybook, Photo to Comic, GIF Maker
- Story Series Engine, AI Character Memory System (3 sprints)
- Pricing & Monetization (4-tier), Public explore/gallery

## Tech Stack
- Frontend: React, Tailwind CSS, Shadcn/UI, lucide-react
- Backend: FastAPI, Python, MongoDB
- Integrations: OpenAI, Gemini, Google Auth, Cloudflare R2, Redis, ffmpeg

## Auth
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Backlog
- (P1) WebSocket live push for admin dashboard (upgrade from polling)
- (P2) Style preset preview thumbnails
- (P2) Full background uniformity cleanup
