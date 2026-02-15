# CreatorStudio AI - Product Requirements Document

## Overview
**Tagline:** "Generate viral reels + kids story videos in minutes."

CreatorStudio AI is a full-stack SaaS application that helps content creators generate:
1. **AI Reel Scripts (Module A)** - Instant Instagram Reel scripts with hooks, captions, hashtags, and posting tips
2. **Kids Story Video Packs (Module B)** - Complete video production packages with scenes, narration, and YouTube metadata

## Tech Stack
- **Frontend:** React (Create React App with Craco) + TailwindCSS
- **Backend:** Spring Boot (Java 17) on port 8001
- **Database:** PostgreSQL
- **Message Queue:** RabbitMQ for async story generation
- **AI Worker:** Python/Flask on port 5000 using emergentintegrations library
- **Authentication:** JWT + Emergent-managed Google OAuth

## Core Features Implemented

### Authentication
- [x] Email/Password registration and login
- [x] JWT token-based session management  
- [x] Google Sign-On via Emergent Auth (redirects to /auth/callback)
- [x] Protected routes with automatic redirect to login

### AI Reel Generator
- [x] Form with niche, tone, duration, goal, topic inputs
- [x] Real-time AI generation using GPT-5.2
- [x] JSON output with hooks, script, captions, hashtags, posting tips
- [x] 1 credit per generation

### Kids Story Generator
- [x] Async generation via RabbitMQ queue
- [x] Age groups from 3-17 years
- [x] 12 story genres (Fantasy, Adventure, Mystery, etc.)
- [x] 8-12 scene options
- [x] Progress bar during generation
- [x] PDF export for story packs
- [x] 6-8 credits per generation

### Credit System
- [x] Credit wallet per user
- [x] Credit ledger for transaction history
- [x] 54 free credits for new users
- [x] Credit balance display in UI

### Billing & Payments (COMPLETE)
- [x] Products table with credit packs and subscriptions
- [x] Pricing page with plan display
- [x] Razorpay checkout integration
- [x] Order creation endpoint
- [x] Payment verification with signature validation
- [x] Webhook endpoint for production
- [x] Credits automatically added after successful payment
- [x] User tier upgrade (removes watermarks after purchase)

### Email Notifications (COMPLETE)
- [x] Gmail SMTP integration
- [x] Welcome email on registration
- [x] Payment success email with receipt details
- [x] Low credits warning email
- [x] HTML email templates with branding

### Admin Dashboard
- [x] User statistics
- [x] Generation counts
- [x] Payment history (when implemented)

## Database Schema
- users: {id, name, email, password_hash, role}
- credit_wallet: {user_id, balance_credits}
- credit_ledger: {id, user_id, type, amount, reason}
- products: {id, name, type, price_inr, credits, razorpay_plan_id}
- payments: {id, user_id, product_id, status, provider_order_id}
- generations: {id, user_id, type, status, input_json, output_json, credits_used}

## API Endpoints
- POST /api/auth/register - User registration (sends welcome email)
- POST /api/auth/login - User login
- GET /api/auth/google - Google OAuth initiation
- GET /api/credits/balance - Get credit balance with isFreeTier status
- GET /api/products - List products
- POST /api/generate/reel - Generate reel script (instant)
- POST /api/generate/demo-reel - Demo reel generation (public, no auth)
- POST /api/generate/story - Generate story pack (async)
- GET /api/generate/generations/{id} - Get generation status/result
- GET /api/generate/generations/{id}/pdf - Download story as PDF
- POST /api/payments/create-order - Create Razorpay order
- POST /api/payments/verify - Verify payment signature
- POST /api/payments/webhook - Razorpay webhook endpoint
- GET /api/payments/products - List payment products
- GET /api/payments/history - User payment history
- GET /api/admin/stats - Admin statistics

## Issues Fixed (Latest Session - Feb 14, 2026)

### Critical Fixes
1. **CORS Configuration** - Fixed Spring Boot CORS to properly allow frontend requests with Origin header
2. **Service Architecture** - Stopped conflicting Python backend, running Spring Boot on 8001
3. **Python Worker** - Fixed supervisor config to use correct Python path (/root/.venv/bin/python3)
4. **Database Setup** - Installed PostgreSQL, created database, seeded admin user with 500 credits

### UI Fixes
1. **Color Scheme** - Removed all yellow/orange colors, standardized to purple/indigo
2. **Button Labels** - Shortened to "PDF" and "JSON" buttons
3. **Secondary Color** - Changed CSS --secondary variable from orange to purple

### Infrastructure
1. **RabbitMQ** - Installed and configured for async story generation
2. **Java JDK** - Installed OpenJDK 17 for Spring Boot
3. **Maven** - Installed for Spring Boot builds

### New Features (Feb 14, 2026 - Session 2)
1. **Landing Page Demo** - "Try Free Demo" button that opens full reel generator form without login
   - Full form with all options (topic, niche, tone, duration, language, goal, audience)
   - Limited to 1 use per browser (tracked via localStorage)
   - Shows watermark banner "Made with CreatorStudio AI - Demo Version"
   - CTA to sign up after generation

2. **Free-Tier Watermarks** - Watermark system for users who haven't purchased
   - Purple banner "⚡ Made with CreatorStudio AI" shown on generated content
   - Watermark added to JSON downloads for free-tier users
   - Removable after purchase/subscription (tracked via localStorage 'has_purchased')

3. **Google Sign-On Verification** - Redirect URL fixed to /auth/callback
   - Correctly redirects to https://auth.emergentagent.com with callback URL

### New Features (Feb 14, 2026 - Session 3)
1. **54 Free Credits** - Increased default credits from 5 to 54 for new users
   - Allows extensive use of both reel generator (1 credit) and story generator (6-8 credits)
   - Updated all landing, pricing, and signup pages

2. **PDF Watermarks** - Watermark on PDF exports for free-tier users
   - Purple banner at top: "⚡ MADE WITH CREATORSTUDIO AI - FREE TIER | Upgrade to remove watermark"
   - Footer watermark with upgrade link
   - Server-side implementation checks user payment history

3. **Upgrade Banners** - Dynamic banners based on credit status
   - "Exhausted" banner when credits = 0 with prominent upgrade CTA
   - "Low" banner when credits <= 10 with warning
   - "Watermark" banner for free-tier users explaining watermarks

4. **Upgrade Modal on Download** - Prompts free users before downloading
   - Modal shows "Remove Watermark?" with premium benefits
   - Options: "Upgrade Now - Remove Watermark" or "Download with Watermark"
   - Works for both JSON and PDF downloads

5. **isFreeTier API Field** - Backend returns user tier in credits balance
   - `/api/credits/balance` now returns `isFreeTier` boolean
   - Determined by checking if user has any PAID payments

### Bug Fix (Feb 15, 2026)
1. **Reel Generator UI Bug** - Fixed critical issue where clicking "Generate Reel Script" caused UI error
   - Error was: `null is not an object (evaluating 'result.hooks')`
   - Root cause: Conditional rendering accessed `result.hooks` without proper null checks
   - Fix: Added `result && result.hooks &&` checks before rendering result sections
   - File: `/app/frontend/src/pages/ReelGenerator.js` (lines 283-295 and 315)
   - Verified: Generation completes successfully, shows 5 hooks, best hook, script scenes, captions, hashtags

2. **CORS Configuration Update** - Updated CORS_ORIGINS to include new preview URL
   - Changed from `reel-creator-42.preview.emergentagent.com` to `viralmakers-1.preview.emergentagent.com`
   - File: `/etc/supervisor/conf.d/springboot.conf`

3. **Environment Setup for Fork** - Installed missing dependencies
   - Java 17 (OpenJDK)
   - PostgreSQL 15 with database `creatorstudio`
   - RabbitMQ server
   - Redis server

## Known Limitations
1. **Razorpay Integration** - Working in TEST MODE with test keys (not production)
2. **Google Sign-On** - Redirect URL verified, requires actual Google account to test full flow

## Test Credentials
- **Demo User:** demo@example.com / password123 (53 credits, free tier)

## Upcoming Tasks (Prioritized)
### P1 - Important  
- Verify "Share Your Creation" feature end-to-end
- Copyright review of app content

### P2 - Nice to Have
- Razorpay production setup (configure live keys + webhook secret)
- Implement subscription webhooks for recurring billing
- Full Google Sign-On flow testing with real account

## File Structure
```
/app/
├── backend-springboot/     # Spring Boot API
│   ├── src/main/java/com/creatorstudio/
│   │   ├── config/         # Security, CORS, RabbitMQ
│   │   ├── controller/     # API endpoints
│   │   ├── entity/         # JPA entities
│   │   ├── service/        # Business logic
│   └── pom.xml
├── frontend/               # React application
│   ├── src/
│   │   ├── pages/          # Route components
│   │   ├── components/     # Reusable UI
│   │   └── utils/          # API helpers
│   └── package.json
├── worker/                 # Python AI worker
│   ├── app.py              # Flask + RabbitMQ consumer
│   └── requirements.txt
└── memory/                 # Documentation
    └── PRD.md
```
