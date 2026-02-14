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
- [x] 5 free credits for new users (default)
- [x] Credit balance display in UI

### Billing (Partially Implemented)
- [x] Products table with credit packs and subscriptions
- [x] Pricing page with plan display
- [ ] Razorpay checkout integration (NOT COMPLETE)
- [ ] Webhook verification

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
- POST /api/auth/register - User registration
- POST /api/auth/login - User login
- GET /api/auth/google - Google OAuth initiation
- GET /api/credits/balance - Get credit balance
- GET /api/products - List products
- POST /api/generate/reel - Generate reel script (instant)
- POST /api/generate/story - Generate story pack (async)
- GET /api/generate/generations/{id} - Get generation status/result
- GET /api/generate/generations/{id}/pdf - Download story as PDF
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

## Known Limitations
1. **Razorpay Integration** - Payment flow not complete (endpoints exist but checkout/webhook not functional)
2. **Google Sign-On** - Redirect URL verified, requires actual Google account to test full flow

## Test Credentials
- **Admin:** admin@creatorstudio.ai / admin123 (498 credits, free tier)

## Upcoming Tasks (Prioritized)
### P0 - Critical
- Complete Razorpay integration for payments (this will enable tier upgrade and watermark removal)

### P1 - Important  
- Full Google Sign-On flow testing with real account
- Admin panel enhancements

### P2 - Nice to Have
- Observability (logging, health checks)
- Rate limiting enhancements
- Email notifications for credit exhaustion

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
