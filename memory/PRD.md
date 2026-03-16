# Visionary-Suite — Product Requirements Document

## Vision
Transform Visionary-Suite from "AI tools website" into "The AI Creative Operating System" — competing with Runway, Canva, and Notion.

## Original Problem Statement
AI content generation platform (story videos, comics, GIFs, reels) with full creative pipeline.

## Architecture

### Backend (FastAPI + MongoDB + Redis + Cloudflare R2)
- Asset-first pipeline: scenes -> images -> voices -> manifest + ZIP -> COMPLETED
- Asset proxy endpoint for CORS-free client-side access
- No server-side video rendering in normal user flow

### Frontend (React + TailwindCSS + Shadcn + ffmpeg.wasm)
- Global Design System with CSS custom properties
- AI Command Center homepage with universal prompt routing
- Canvas-style creation workflows with step indicators
- Browser-side MP4 export with WebM fallback

### Design System
- **Fonts**: Sora (headings), Inter (body), JetBrains Mono (numbers)
- **Background**: #0B0F1A (base), #111827 (panels), #1F2937 (cards)
- **Accent**: #7C3AED (CTA), #6D5BFF → #A855F7 (gradient)
- **File**: `/app/frontend/src/design-system.css`

## Implemented Features (Phase 1 — Mar 16, 2026)

### Global Design System
- [x] CSS custom properties for all colors, typography, spacing, shadows
- [x] Card system (vs-card, vs-panel, vs-card-flat) with hover effects
- [x] Button system (vs-btn-primary, vs-btn-secondary)
- [x] Typography classes (vs-h1, vs-h2, vs-h3, vs-body, vs-mono)
- [x] Animation system (vs-fade-up-1/2/3/4, vs-glow-pulse, vs-shimmer)
- [x] Glass morphism (vs-glass), gradient helpers, chip/tag system
- [x] Sora, Inter, JetBrains Mono fonts loaded globally

### AI Command Center (Dashboard)
- [x] Universal prompt box (800px, 70px) with intent-based routing
- [x] 4 suggestion chips that populate prompt on click
- [x] Create / Remix / Publish mode tabs (6/4/4 tools)
- [x] Tool cards grid with gradient accent icons and credit costs
- [x] Right sidebar: Credits, Streak tracker, Daily Challenge, Creator Level, AI Ideas
- [x] Recent Creations list with status badges

### Creation Canvas (StoryVideoPipeline)
- [x] Step indicators in header: Prompt → Scenes → Images → Voice → Preview
- [x] Active step highlighting with progress tracking
- [x] Form inputs styled with design system
- [x] Animation style grid (6 options) with selected state
- [x] Recent Videos sidebar
- [x] Error boundary with design system styling

### Landing Page
- [x] "The AI Creative Operating System" tagline
- [x] "Turn Any Idea Into Cinematic AI Content" hero
- [x] Glass morphism navigation bar
- [x] Purple gradient CTA buttons
- [x] Dark theme (#0B0F1A) applied

### Asset-First Pipeline
- [x] Pipeline: scenes -> images -> voices (3 stages only)
- [x] Auto manifest + Story Pack ZIP on completion
- [x] Job durability with auto-resume from checkpoint
- [x] CORS proxy for R2 assets (/api/pipeline/asset-proxy)

### Browser Video Export (Fixed Mar 16, 2026)
- [x] FFmpeg.wasm MP4 export (UMD core from same-origin)
- [x] WebM MediaRecorder fallback
- [x] Cross-origin isolation (COOP/COEP)
- [x] Backend asset proxy for CORS-free R2 access

## Roadmap

### Phase 2 — Viral Engine (NEXT)
- [ ] /explore page (trending, newest, most remixed, most viewed)
- [ ] Public creation pages with SEO (/reel/slug, /story/slug)
- [ ] Remix button on all creations
- [ ] Creator profiles (/creator/{username})
- [ ] Viral branding/watermark on exports

### Phase 3 — Distribution & SEO
- [ ] SEO creation pages (title, description, preview, tags)
- [ ] Social sharing buttons (Instagram, YouTube, TikTok)
- [ ] Animated watermark option on exports

### Phase 4 — Addiction Mechanics
- [ ] Daily creation rewards & streak system (backend exists, needs frontend gamification)
- [ ] Creator status/level system (backend exists, needs public display)
- [ ] Weekly creator challenges
- [ ] Referral program (invite friend → both get credits)

### Phase 5 — AI & Economy
- [ ] AI Assistant (floating Visionary AI)
- [ ] Advanced discovery algorithms
- [ ] Creator economy (monetization)
- [ ] Cashfree live payment testing

### Blocked
- [ ] Email notifications (SendGrid external issue)

## Key API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | /api/pipeline/create | Create new pipeline job |
| GET | /api/pipeline/status/{id} | Job status + manifest + ZIP URL |
| GET | /api/pipeline/preview/{id} | Public preview data |
| GET | /api/pipeline/asset-proxy?url= | Proxy R2 assets for export |
| GET | /api/pipeline/user-jobs | User's job history |
| GET | /api/engagement/dashboard | Streak, challenge, level, ideas |
| GET | /api/engagement/trending | Trending creations |

## Test Credentials
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
- Test: test@visionary-suite.com / Test@2026#
