# CreatorStudio AI - Product Requirements Document

## Overview
**Tagline:** "Generate viral reels + kids story videos in minutes."

CreatorStudio AI is a full-stack SaaS application that helps content creators generate:
1. **AI Reel Scripts (Module A)** - Instant Instagram Reel scripts with hooks, captions, hashtags, and posting tips
2. **Kids Story Video Packs (Module B)** - Complete story packages with scenes, narration, and YouTube metadata

## Tech Stack
- **Frontend:** React + TailwindCSS + Shadcn/UI
- **Backend:** Spring Boot (Java 17) on port 8001
- **Database:** PostgreSQL
- **Message Queue:** RabbitMQ for async story generation
- **AI Worker:** Python/Flask on port 5000 using emergentintegrations library (GPT-5.2)
- **Cache:** Redis
- **Authentication:** JWT + Emergent-managed Google OAuth

## Core Features Implemented

### Authentication ✅
- [x] Email/Password registration and login
- [x] JWT token-based session management  
- [x] Google Sign-On via Emergent Auth
- [x] Role-based access (USER, ADMIN)

### AI Reel Generator ✅
- [x] Form with niche, tone, duration, goal, topic inputs
- [x] Real-time AI generation using GPT-5.2
- [x] JSON output with hooks, script, captions, hashtags, posting tips
- [x] Content Filtering - Blocks inappropriate/vulgar content

### Kids Story Generator ✅
- [x] Async generation via RabbitMQ queue
- [x] Age groups from 3-17 years
- [x] 12 story genres + Custom genre option
- [x] 8-12 scene options
- [x] Progress bar during generation
- [x] PDF export for story packs
- [x] Content Filtering - Stricter filter for kids content

### AI Chatbot ✅ (NEW - Dec 2025)
- [x] GPT-5.2 powered customer support chatbot
- [x] Floating button on all pages (bottom-right corner)
- [x] Multi-turn conversation support
- [x] Quick question suggestions
- [x] Session-based chat history
- [x] Answers questions about features, pricing, credits

### Credit System ✅
- [x] Credit wallet per user
- [x] 54 free credits for new users
- [x] Credit ledger for transaction history

### Billing & Payments ✅
- [x] Razorpay checkout integration (TEST MODE)
- [x] International Payments - USD, EUR, GBP currency support
- [x] Currency selector on pricing page
- [x] Payment exception handling with custom exceptions
- [x] Credits automatically added after successful payment

### Circuit Breaker (Resilience4j) ✅ (NEW - Dec 2025)
- [x] Circuit breaker for payment service
- [x] Circuit breaker for worker service
- [x] Retry mechanism with exponential backoff
- [x] Rate limiter configuration

### Admin Dashboard ✅
- [x] User statistics and growth trends
- [x] Visitor tracking with daily trends
- [x] Feature usage analytics
- [x] Payment/transaction summary
- [x] Feature request management

### Data Privacy (GDPR/CCPA) ✅
- [x] Privacy Settings page (/app/privacy)
- [x] Privacy Policy page (/privacy-policy)
- [x] Data export functionality (JSON download)
- [x] Account deletion request
- [x] Consent preferences management

### Generation History ✅
- [x] History page (/app/history)
- [x] Stats cards (total generations, reels, stories, credits used)
- [x] Detailed view with input parameters and output preview
- [x] PDF download for story packs
- [x] Filter by type (All/Reels/Stories)

### Content Safety ✅
- [x] Frontend content filtering with blocked words list
- [x] Backend ContentFilterService with validation
- [x] Separate filter for kids content (stricter)
- [x] XSS protection/text sanitization

### Automation System ✅ (NEW - Dec 2025)
- [x] Health monitor - checks every 1 minute
- [x] Auto-recovery - restarts failed services
- [x] API validator - tests endpoints every 5 minutes
- [x] Database maintenance - cleanup every hour
- [x] Security scanner - comprehensive vulnerability scan
- [x] Automation dashboard (/app/admin/automation)

### Security Features ✅ (NEW - Dec 2025)
- [x] Security scanner script
- [x] SQL injection protection testing
- [x] XSS protection testing
- [x] Authentication vulnerability checks
- [x] CORS configuration validation
- [x] JWT security verification
- [x] Rate limiting checks

## API Endpoints

### Public Endpoints
- POST /api/auth/register - User registration
- POST /api/auth/login - User login
- GET /api/auth/google - Google OAuth
- GET /api/payments/products - List products
- GET /api/payments/currencies - Supported currencies
- POST /api/generate/demo-reel - Demo reel generation
- POST /api/chatbot/message - AI Chatbot messages
- POST /api/chatbot/clear - Clear chat session
- GET /api/privacy/policy - Privacy policy info
- GET /api/health/* - Health checks

### Protected Endpoints
- GET /api/auth/me - Current user info
- GET /api/credits/balance - Credit balance
- GET /api/credits/ledger - Transaction history
- POST /api/generate/reel - Generate reel script
- POST /api/generate/story - Generate story pack
- GET /api/generate/generations - Generation history
- GET /api/generate/generations/{id}/pdf - Download story PDF
- POST /api/payments/create-order - Create Razorpay order
- POST /api/payments/verify - Verify payment
- GET /api/privacy/my-data - User data overview
- GET /api/privacy/export - Export user data
- POST /api/privacy/delete-request - Request account deletion

### Admin Endpoints
- GET /api/admin/analytics/dashboard - Full analytics
- PUT /api/feature-requests/{id}/status - Update feature status

## File Structure
```
/app/
├── backend-springboot/
│   ├── src/main/java/com/creatorstudio/
│   │   ├── config/         # Security, CORS, Redis, Circuit Breaker
│   │   ├── controller/     # API endpoints (incl. ChatbotController)
│   │   ├── dto/            # Data Transfer Objects
│   │   ├── entity/         # JPA entities
│   │   ├── exception/      # Payment exceptions, Circuit breaker
│   │   ├── repository/     # Data repositories
│   │   ├── security/       # JWT filter, UserDetailsService
│   │   └── service/        # Business logic, ContentFilterService
│   └── pom.xml
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── ui/         # Shadcn components
│       │   └── AIChatbot.js # AI Chatbot component
│       ├── pages/          # Route components
│       └── utils/
├── worker/
│   └── app.py              # Python AI worker + Chatbot endpoint
├── automation/
│   ├── scripts/            # Health monitor, security scanner
│   ├── logs/               # Automation logs
│   └── reports/            # Health & security reports
└── memory/
    └── PRD.md
```

## Test Credentials
- **Admin User:** admin@creatorstudio.ai / Admin@123
- **Test User:** corstest1771172193@example.com / CorsTest123!

## Known Limitations / MOCKED
1. **Razorpay** - TEST MODE with test keys (not live payments)
2. **Currency Conversion** - Uses HARDCODED exchange rates, not live API
3. **Google Sign-On** - Requires Emergent OAuth integration

## Completed Work (December 2025)

### Latest Session Summary
1. ✅ **AI Chatbot** - GPT-5.2 powered customer support bot on all pages
2. ✅ **Circuit Breaker** - Resilience4j for payment and worker services
3. ✅ **Payment Exception Handling** - Custom exceptions for payment errors
4. ✅ **Security Scanner** - Automated vulnerability scanning
5. ✅ **Automation System** - Health monitoring, auto-recovery, API validation
6. ✅ **Content Filtering** - Backend validation added to Reel/Story generators
7. ✅ **Generation History** - Enhanced history page with stats and details
8. ✅ **International Payments** - Currency selector (INR/USD/EUR/GBP)
9. ✅ **Privacy Features** - GDPR/CCPA compliance pages

## Security Scan Results
- **Vulnerabilities Found:** 11 (mostly false positives from SPA routing)
- **Warnings:** 8 (missing security headers, rate limiting)
- **Action Items:** Add security headers to frontend

## Upcoming/Backlog Tasks
- [ ] Razorpay Production Setup (live keys)
- [ ] Subscription Webhooks for recurring billing
- [ ] Live currency conversion API integration
- [ ] Add security headers to frontend
- [ ] Rate limiting on login endpoint
- [ ] AdminDashboard component refactoring
