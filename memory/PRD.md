# Visionary-Suite — Product Requirements Document

## Vision
**The AI Content Creation Network** — where creators generate, remix, and publish viral AI content.

**One-sentence positioning:** Create viral AI videos in minutes.

## Architecture

### Backend (FastAPI + MongoDB + Redis + Cloudflare R2)
- Asset-first pipeline: scenes -> images -> voices -> manifest + ZIP -> COMPLETED
- Public APIs for distribution loop (no auth): /api/public/stats, /api/public/explore, /api/public/creation/{slug}
- Asset proxy for CORS-free client-side access

### Frontend (React + TailwindCSS + Shadcn + ffmpeg.wasm)
- Global Design System (design-system.css) — CSS custom properties
- AI Command Center homepage with universal prompt routing
- Canvas-style creation workflows with step indicators
- Distribution loop: Explore page, Public creation pages, Remix flow
- Browser-side MP4/WebM export with watermark branding

### Design System
- **Fonts**: Sora (headings), Inter (body), JetBrains Mono (numbers)
- **Background**: #0B0F1A (base), #111827 (panels), #1F2937 (cards)
- **Accent**: #7C3AED (CTA), #6D5BFF→#A855F7 (gradient)

## Three Pillars
1. **CREATE** — Generate cinematic AI videos from prompts (Story Video is the flagship)
2. **REMIX** — Take any creation, change style/voice/story, make it yours
3. **PUBLISH** — Every creation gets a public page with views, remixes, sharing

## Implemented Features

### Phase 1 — Design System & Identity (Mar 16, 2026)
- [x] Global CSS design system (colors, typography, cards, buttons, animations)
- [x] AI Command Center Dashboard — Story Video as hero, 8 tools in "More Tools"
- [x] Universal prompt box with intent-based routing (16+ tool mappings)
- [x] Creation Canvas with step indicators (Prompt→Scenes→Images→Voice→Preview)
- [x] Landing page following high-conversion wireframe

### Phase 2 — Distribution Loop (Mar 16, 2026)
- [x] `/explore` page — Trending / Newest / Most Remixed tabs with grid
- [x] `/v/{slug}` public creation pages — Title, views, remixes, creator, scenes
- [x] Remix button on every creation page (header + sidebar + CTA)
- [x] Share button with clipboard copy / Web Share API
- [x] View tracking (increments on each page visit)
- [x] Landing page social proof with REAL data from database
- [x] Landing page trending creations section from explore API
- [x] Watermark branding on video exports ("Created with Visionary Suite AI")
- [x] Auto-slug generation for new pipeline jobs

### Core Platform
- [x] Auth (JWT + Google OAuth), Credit system, Gallery
- [x] Story Video, Comic, GIF/Reel, Coloring Book generators
- [x] Asset-first pipeline with auto-resume from checkpoint
- [x] Browser MP4 export (ffmpeg.wasm) + WebM fallback
- [x] R2 asset proxy for CORS-free export
- [x] Admin panel, Analytics, Crash Diagnostics

## Growth Loop
```
Creator generates AI video
↓
Video gets public page (/v/slug)
↓
Creator shares link on social media
↓
Viewer sees creation + "Created with Visionary Suite AI"
↓
Viewer clicks "Remix This"
↓
Viewer becomes creator
↓
Loop repeats
```

## Key API Endpoints
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /api/public/stats | No | Real platform stats for social proof |
| GET | /api/public/explore | No | Trending/newest/most_remixed feed |
| GET | /api/public/creation/{slug} | No | Public creation page data + view tracking |
| POST | /api/pipeline/create | Yes | Create new pipeline job |
| GET | /api/pipeline/status/{id} | Yes | Job status + manifest |
| GET | /api/pipeline/asset-proxy?url= | No | Proxy R2 assets for export |

## Roadmap

### Phase 3 — SEO & Distribution (NEXT)
- [ ] SEO meta tags on public creation pages (og:title, og:image, og:description)
- [ ] Social sharing buttons (Instagram, YouTube, TikTok)
- [ ] Animated watermark option
- [ ] Sitemap generation for /v/* pages

### Phase 4 — Addiction Mechanics
- [ ] Daily creation rewards & streak gamification
- [ ] Creator status/level system with public display
- [ ] Weekly creator challenges
- [ ] Referral program (invite friend → both get credits)

### Phase 5 — Creator Economy
- [ ] Creator profiles (/creator/{username})
- [ ] AI Creation Templates Marketplace
- [ ] AI Assistant (floating Visionary AI)
- [ ] Cashfree live payment testing

### Blocked
- [ ] Email notifications (SendGrid external issue)

## Test Credentials
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
- Test: test@visionary-suite.com / Test@2026#
