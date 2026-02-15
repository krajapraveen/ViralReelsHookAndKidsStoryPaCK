# CreatorStudio AI - Product Requirements Document

## Overview
**Tagline:** "Generate viral reels + kids story videos in minutes."

CreatorStudio AI is a full-stack SaaS application that helps content creators generate:
1. **AI Reel Scripts (Module A)** - Instant Instagram Reel scripts with hooks, captions, hashtags, and posting tips
2. **Kids Story Video Packs (Module B)** - Complete video production packages with scenes, narration, and YouTube metadata

## Tech Stack
- **Frontend:** React (Create React App with Craco) + TailwindCSS + Shadcn/UI
- **Backend:** Spring Boot (Java 17) on port 8001
- **Database:** PostgreSQL
- **Message Queue:** RabbitMQ for async story generation
- **AI Worker:** Python/Flask on port 5000 using emergentintegrations library
- **Cache:** Redis
- **Authentication:** JWT + Emergent-managed Google OAuth

## Core Features Implemented

### Authentication ✅
- [x] Email/Password registration and login
- [x] JWT token-based session management  
- [x] Google Sign-On via Emergent Auth
- [x] Protected routes with automatic redirect
- [x] Role-based access (USER, ADMIN)

### AI Reel Generator ✅
- [x] Form with niche, tone, duration, goal, topic inputs
- [x] Real-time AI generation using GPT-5.2
- [x] JSON output with hooks, script, captions, hashtags, posting tips
- [x] 1 credit per generation
- [x] **Content Filtering** - Blocks inappropriate/vulgar content (frontend + backend)

### Kids Story Generator ✅
- [x] Async generation via RabbitMQ queue
- [x] Age groups from 3-17 years
- [x] 12 story genres + Custom genre option
- [x] 8-12 scene options
- [x] Progress bar during generation
- [x] PDF export for story packs
- [x] 6-8 credits per generation
- [x] **Content Filtering** - Stricter filter for kids content

### Credit System ✅
- [x] Credit wallet per user
- [x] Credit ledger for transaction history
- [x] 54 free credits for new users
- [x] Credit balance display in UI

### Billing & Payments ✅
- [x] Products table with credit packs and subscriptions
- [x] Pricing page with plan display
- [x] Razorpay checkout integration (TEST MODE)
- [x] **International Payments** - USD, EUR, GBP currency support
- [x] Currency selector on pricing page
- [x] Order creation endpoint with currency support
- [x] Payment verification with signature validation
- [x] Webhook endpoint for production
- [x] Credits automatically added after successful payment

### Admin Dashboard ✅
- [x] User statistics and growth trends
- [x] Visitor tracking with daily trends
- [x] Feature usage analytics
- [x] Payment/transaction summary
- [x] Failed transaction reasons
- [x] User satisfaction metrics (NPS score)
- [x] Feature request management
- [x] Date range filter (7/30/90/365 days)

### Feature Request & Voting System ✅
- [x] User can submit feature requests
- [x] Voting on features
- [x] Admin can update status (Pending, Under Review, Planned, In Progress, Completed, Declined)
- [x] Admin response capability

### Data Privacy (GDPR/CCPA) ✅
- [x] Privacy Settings page (/app/privacy)
- [x] Privacy Policy page (/privacy-policy)
- [x] Data export functionality (JSON download)
- [x] Account deletion request with 30-day grace period
- [x] Consent preferences (marketing, analytics, third-party)
- [x] User data overview

### Content Safety ✅
- [x] Frontend content filtering with blocked words list
- [x] Backend ContentFilterService with validation
- [x] Separate filter for kids content (stricter)
- [x] XSS protection/text sanitization

### Share Your Creation ✅
- [x] ShareButton component
- [x] Generate share card image (canvas)
- [x] Download share card
- [x] Copy share link to clipboard

## Database Schema
- users: {id, name, email, password_hash, role}
- credit_wallet: {user_id, balance_credits}
- credit_ledger: {id, user_id, type, amount, reason}
- products: {id, name, type, price_inr, price_usd, price_eur, price_gbp, credits, razorpay_plan_id, is_active}
- payments: {id, user_id, product_id, status, provider_order_id, currency, amount_in_currency, converted_amount_inr}
- generations: {id, user_id, type, status, input_json, output_json, credits_used}
- page_visit: {id, path, user_id, timestamp}
- feature_usage: {id, feature_name, user_id, timestamp}
- user_session: {id, user_id, start_time, end_time, duration_seconds}
- feature_request: {id, title, description, category, status, user_id, created_at}
- feature_vote: {id, user_id, feature_request_id, created_at}
- feedback: {id, user_id, rating, comment, type}

## API Endpoints

### Public Endpoints
- POST /api/auth/register - User registration
- POST /api/auth/login - User login
- GET /api/auth/google - Google OAuth initiation
- GET /api/payments/products - List products
- GET /api/payments/currencies - Supported currencies
- POST /api/generate/demo-reel - Demo reel generation
- GET /api/privacy/policy - Privacy policy info
- GET /api/health/* - Health checks

### Protected Endpoints
- GET /api/auth/me - Current user info
- GET /api/credits/balance - Credit balance
- GET /api/credits/ledger - Transaction history
- POST /api/generate/reel - Generate reel script
- POST /api/generate/story - Generate story pack
- GET /api/generate/generations/{id} - Get generation status
- GET /api/generate/generations/{id}/pdf - Download story PDF
- POST /api/payments/create-order - Create Razorpay order
- POST /api/payments/verify - Verify payment
- GET /api/payments/history - Payment history

### Privacy Endpoints
- GET /api/privacy/my-data - User data overview
- GET /api/privacy/export - Export user data (JSON)
- POST /api/privacy/delete-request - Request account deletion
- POST /api/privacy/consent - Update consent preferences

### Admin Endpoints
- GET /api/admin/analytics/dashboard - Full analytics data
- PUT /api/feature-requests/{id}/status - Update feature request status

## File Structure
```
/app/
├── backend-springboot/
│   ├── src/main/java/com/creatorstudio/
│   │   ├── config/         # Security, CORS, Redis, RabbitMQ
│   │   ├── controller/     # API endpoints
│   │   ├── dto/            # Data Transfer Objects
│   │   ├── entity/         # JPA entities
│   │   ├── exception/      # Custom exceptions
│   │   ├── repository/     # Data repositories
│   │   ├── security/       # JWT filter, UserDetailsService
│   │   └── service/        # Business logic (incl. ContentFilterService)
│   └── pom.xml
├── frontend/
│   └── src/
│       ├── components/ui/  # Shadcn components
│       ├── pages/          # Route components
│       │   ├── ReelGenerator.js    # With content filtering
│       │   ├── StoryGenerator.js   # With content filtering
│       │   ├── Pricing.js          # With currency selector
│       │   ├── PrivacySettings.js  # GDPR/CCPA features
│       │   ├── PrivacyPolicy.js    # Static policy page
│       │   └── AdminDashboard.js   # Analytics dashboard
│       └── utils/
│           └── api.js
├── worker/
│   └── app.py              # Python AI worker
└── memory/
    └── PRD.md
```

## Test Credentials
- **Demo User:** Use signup to create new account (54 free credits)
- **Test Razorpay:** Use test cards (4111 1111 1111 1111)

## Known Limitations
1. **Razorpay** - TEST MODE with test keys
2. **Currency Conversion** - Uses hardcoded exchange rates, not live API
3. **Google Sign-On** - Requires Emergent OAuth integration

## Completed Work (December 2025)

### Session Summary
1. ✅ Backend Content Filtering Service - Blocks inappropriate words
2. ✅ Frontend Content Filtering - Validates before API call
3. ✅ Privacy Settings Page - GDPR/CCPA compliance
4. ✅ Privacy Policy Page - Public static page
5. ✅ International Payments Frontend - Currency selector (INR/USD/EUR/GBP)
6. ✅ Fixed CORS configuration
7. ✅ Fixed PostgreSQL authentication
8. ✅ Cleared Redis cache issues
9. ✅ Seeded products table

## Upcoming/Backlog Tasks
- [ ] Razorpay Production Setup (live keys)
- [ ] Subscription Webhooks for recurring billing
- [ ] AdminDashboard refactoring (split into smaller components)
- [ ] Complete Share Your Creation e2e testing
- [ ] Copyright review of app content
- [ ] Live currency conversion API integration
