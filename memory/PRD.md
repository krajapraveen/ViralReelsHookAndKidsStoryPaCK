# Visionary Suite - Product Requirements Document

## Original Problem Statement
Full-stack SaaS platform for creative content generation with comprehensive monetization optimization, admin analytics, stability improvements, auto-scaling, self-healing, and CDN optimization.

## Core Features (Implemented)
- **Content Generation**: Reel Generator, Comic AI, GIF Maker, Story Generator, Comic Storybook
- **User Authentication**: JWT-based auth with email verification
- **Payment Integration**: Cashfree payment gateway
- **Credit System**: Wallet-based credit management for generations
- **Admin Dashboard**: Comprehensive analytics, user management, and monitoring

## Recent Changes (2026-02-27)

### Coloring Book Creator - Complete 5-Step Wizard Rebuild ✅ NEW

#### UX Structure (Linear 5-Step Flow)
| Step | Name | Description |
|------|------|-------------|
| 1 | Choose Mode | Story vs Photo with Recommended badge |
| 2 | Provide Content | Form fields based on selected mode |
| 3 | Customize | Paper size, add-ons, live calculator |
| 4 | Preview | 2 sample pages with watermark |
| 5 | Download | PDF, HD PDF, Share Link |

#### Story Mode Pricing
| Pages | Credits | Badge |
|-------|---------|-------|
| 5 pages | 10 | - |
| 10 pages | 18 | Save 10% |
| 20 pages | 32 | MOST POPULAR (default) |
| 30 pages | 45 | BEST VALUE |

#### Photo Mode Pricing
| Images | Credits | Badge |
|--------|---------|-------|
| 1 image | 5 | - |
| 5 images | 20 | POPULAR |
| 10 images | 35 | BEST VALUE |

#### Add-ons (High Profit, Low Cost)
| Add-on | Credits | Notes |
|--------|---------|-------|
| Activity Pages | +3 | Puzzles, mazes |
| Personalized Cover | +4 | PRE-SELECTED by default |
| Dedication Page | +2 | Personal message |
| Premium Templates | +5 | Pro only |
| HD Print Version | +5 | 300 DPI PDF |
| Commercial License | +10 | Commercial use |

#### Revenue Psychology
- Default: 20 pages + Personalized Cover = 36 credits
- Expected AOV: 39 credits (with activity pages)
- "Best Value: 20 pages + Cover saves 15%" tip shown

#### Subscription Discounts
| Plan | Discount | Preview Pages | Watermark |
|------|----------|---------------|-----------|
| Free | 0% | 2 | Yes |
| Creator | 20% | 3 | No |
| Pro | 30% | 5 | No |
| Studio | 40% | Unlimited | No |

#### Admin Analytics Tracking
- Mode selected
- Pages selected
- Add-ons selected
- Drop-off step
- Conversion funnel

#### New API Endpoints
```
GET  /api/coloring-book/pricing          - Complete pricing config
POST /api/coloring-book/calculate        - Live cost calculation
GET  /api/coloring-book/preview-config   - Preview settings by plan
POST /api/coloring-book/session/start    - Start tracking session
POST /api/coloring-book/analytics/track  - Track user actions
POST /api/coloring-book/generate/full    - Generate book (charges credits)
POST /api/coloring-book/upsell/hd-upgrade - HD upgrade (+5 credits)
GET  /api/coloring-book/admin/analytics  - Admin analytics dashboard
GET  /api/coloring-book/admin/funnel     - Conversion funnel data
```

### Monetization Optimization (No New AI/Infra)

#### 1. Multi-Output Pricing ✅
- Single output: Base cost
- 3 Variations: +5 credits (50% savings)
- 5 Variations: +10 credits (60% savings)
- 10 Variations: +20 credits (70% savings)

#### 2. Premium Style Lock System ✅
- 50% of styles locked as "Pro Only"
- Upgrade modal for non-Pro users
- Affects: Comix AI, GIF Maker, Storybook, Reel Generator

#### 3. Revenue Upsell Layer ✅
- HD Download: +5 credits
- Remove Watermark: +3 credits
- Commercial License: +10 credits
- Batch Download ZIP: +5 credits
- Watermark-free for paid plans

#### 4. Subscription Model ✅
| Plan | Price | Credits | Features |
|------|-------|---------|----------|
| Free | ₹0 | 10 trial | Basic styles, watermarked |
| Creator | ₹499/mo | 200/mo | Watermark-free, HD |
| Pro | ₹1,499/mo | 800/mo | Premium styles, commercial |
| Studio | ₹3,999/mo | 3,000/mo | Priority queue, all features |

#### 5. Credit Psychology UI ✅
- Color-coded credit badge (green/yellow/red)
- "Only X credits left" alerts
- Daily Login Reward: +3 credits
- Trending 🔥 badge on high-value tools

#### 6. Bundle Pricing ✅
- Comix: 1 panel (10) → 3 panels (25) → 6 panels (45)
- Storybook: 4 pages (30) → 8 pages (55) → 20 pages (120)
- GIF: 1 GIF (8) → 3 GIFs (20) → 5 GIFs (30)

#### 7. Dashboard Reordering ✅
**Priority Order:**
1. Comix AI (🔥 TRENDING)
2. Comic Storybook (🔥 TRENDING)
3. Reel Generator
4. Story Pack

**Creator Boost Pack (bundled tools):**
- GIF Maker, Coloring Book, Tone Switcher, Challenge Gen

## New API Endpoints (Monetization)

```
GET  /api/monetization/plans           - Subscription plans
GET  /api/monetization/variations      - Multi-output pricing
GET  /api/monetization/bundles/{f}     - Bundle pricing
GET  /api/monetization/upsells         - Upsell options
GET  /api/monetization/styles/{f}      - Feature styles with lock status
POST /api/monetization/styles/check    - Check style access
POST /api/monetization/upsell/purchase - Purchase upsell
GET  /api/monetization/daily-reward/status  - Daily reward status
POST /api/monetization/daily-reward/claim   - Claim daily reward
GET  /api/monetization/credit-status   - Credit psychology alerts
GET  /api/monetization/dashboard-config - Dashboard priority config
GET  /api/monetization/watermark-status - Watermark logic
```

## New Frontend Components

```
/app/frontend/src/components/
├── UpsellModal.jsx        - Post-generation upsells
├── StyleSelector.jsx      - Premium style lock UI
├── CreditStatusBadge.jsx  - Credit psychology badge
└── VariationSelector.jsx  - Multi-output selector
```

## Architecture

```
/app/
├── backend/
│   ├── config/
│   │   └── monetization.py    # NEW: Centralized pricing config
│   ├── routes/
│   │   └── monetization.py    # NEW: Monetization APIs
│   └── services/
│       ├── auto_scaling_service.py
│       ├── cdn_optimizer.py
│       └── ...
└── frontend/
    └── src/
        ├── components/
        │   ├── UpsellModal.jsx
        │   ├── StyleSelector.jsx
        │   ├── CreditStatusBadge.jsx
        │   └── VariationSelector.jsx
        └── pages/
            └── Dashboard.js   # Reordered for monetization
```

## Monetization Goals
- **ARPU Increase**: Higher basket size via bundles
- **Subscription Conversions**: Premium style locks + upgrade prompts
- **Credit Consumption**: Multi-output pricing + trending badges
- **No API Cost Increase**: Pricing logic only, no new AI models

## Test Credentials
- Admin: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`
- Demo: `demo@example.com` / `Password123!`

## Backlog
- ✅ Monetization optimization complete
- ✅ GenStudio AI removed
- ✅ Full A→Z QA audit complete
- ✅ Auto-scaling & self-healing implemented
- ✅ CDN caching configured

## Future Enhancements
- P3: Referral program
- P3: Affiliate system
- P3: Gift cards
