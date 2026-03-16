# Visionary Suite — PRD (Product Requirements Document)

## Product Vision
Visionary Suite is an **AI Creative Operating System** — a creator network centered around the growth loop: **Create → Share → View → Remix → Create**.

## Core Architecture
- **Frontend**: React (CRA) + Tailwind CSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB (Motor async)
- **Storage**: Cloudflare R2
- **AI**: OpenAI (GPT-4o-mini, GPT Image 1, Sora 2, TTS), Gemini, ElevenLabs
- **Auth**: JWT + Google Auth (Emergent-managed)
- **Payments**: Cashfree (geo-IP based)

## Flagship Feature
**Story → Video Pipeline**: User writes a prompt → AI generates script, scenes, images, voiceover → Complete video in ~90 seconds.

## Distribution Loop (LIVE)
| Component | Status | Route |
|-----------|--------|-------|
| Public Creation Pages | LIVE | `/v/{slug}` |
| Explore Gallery | LIVE | `/explore` |
| Remix Button | LIVE | On every public page |
| Share Buttons (X, LinkedIn, Reddit, Copy) | LIVE | On every public page |
| Prompt Display for Remix | LIVE | On every public page |
| OG Meta Tags (share page) | LIVE | `/api/public/s/{slug}` |
| Dynamic OG Image | LIVE | `/api/public/og-image/{slug}` |
| Canonical URLs | LIVE | On every public page |
| Sitemap | LIVE | `/api/public/sitemap.xml` |
| Creator Profiles | LIVE | `/creator/{username}` |
| Content Seeding (40 Phase A) | DONE | 40 videos seeded |
| Admin Growth Dashboard | LIVE | `/app/admin/growth` |
| Watermark on exports | LIVE | Client-side |

## User Personas
1. **Creator**: Writes prompts, generates videos, shares on social media
2. **Viewer**: Discovers content on Explore, watches, gets inspired to remix
3. **Admin**: Monitors growth metrics, content moderation

## Key Metrics (Growth Dashboard)
- Daily Creations (content velocity)
- Remix Rate (viral indicator)
- Public Page Views (discovery)
- Creator Activation Rate (signup → first creation)
- Share Rate (future tracking)

## Content Seeding Status
- Phase A: 40 videos (DONE) — Fantasy, Kids, Luxury, Motivational, Sci-Fi, Emotional
- Phase B: 40 more videos (PENDING)
- Phase C: 40 final videos (PENDING)
- System creator: "Visionary AI" (`/creator/visionary-ai`)

## Completed Features
- Global design system
- High-conversion homepage (AI Command Center)
- Simplified dashboard
- Story Video Pipeline (multi-stage, durable)
- Distribution loop (explore, public pages, remix, share)
- OG Meta Tags + Share Pages
- Dynamic OG Image Generation
- Sitemap (XML)
- Social Share Buttons (X, LinkedIn, Reddit, Copy Link)
- Remix Prompt Display
- Creator Profiles
- Admin Growth Dashboard (5 core metrics)
- Content Seeding Phase A (40 videos)
- Watermark branding on exports

## Remaining Backlog
### P0
- [ ] Content Seeding Phase B (40 more videos)
- [ ] Content Seeding Phase C (40 final videos)

### P1
- [ ] UX: Reduce friction to first creation (prompt before login)
- [ ] Time to First Creation metric tracking

### P2
- [ ] Creator Challenges (weekly engagement)
- [ ] Live Cashfree Payment Integration
- [ ] Email Notifications (BLOCKED — SendGrid)

## Technical Debt
- SendGrid integration blocked (external issue)
