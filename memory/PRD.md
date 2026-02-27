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
