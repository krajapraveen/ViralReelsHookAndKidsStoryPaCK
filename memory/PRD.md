# CreatorStudio AI - Product Requirements Document

## Overview
**Tagline:** "Generate viral reels + kids story videos in minutes."

## Tech Stack
- **Frontend:** React + TailwindCSS + Shadcn/UI
- **Backend:** Spring Boot (Java 17) on port 8001
- **Database:** PostgreSQL
- **Message Queue:** RabbitMQ
- **AI Worker:** Python/Flask on port 5000 (GPT-5.2)
- **Cache:** Redis

## All Features Implemented ✅

### Core Features
- [x] AI Reel Script Generator (1 credit)
- [x] Kids Story Video Pack Generator (6-8 credits)
- [x] Content Filtering (Frontend + Backend)
- [x] Credit System (54 free credits for new users)
- [x] Generation History with stats

### AI Chatbot ✅
- [x] GPT-5.2 powered customer support bot
- [x] Floating button on all pages
- [x] Multi-turn conversation support
- [x] Quick question suggestions

### Payments ✅
- [x] Razorpay integration (TEST MODE)
- [x] International Payments (USD/EUR/GBP)
- [x] **Live Currency Conversion** - Frankfurter API
- [x] Payment exception handling
- [x] Circuit breaker for payment service

### Security Features ✅
- [x] **Security Headers** - X-Content-Type-Options, X-Frame-Options, CSP, XSS-Protection
- [x] **Rate Limiting on Login** - 5 attempts per minute per IP
- [x] JWT token authentication
- [x] CORS configuration
- [x] SQL injection protection
- [x] XSS protection

### Email Notifications ✅
- [x] **Payment Confirmation** - Beautiful HTML email with transaction details
- [x] **Reel Generation Complete** - Notification when reel is ready
- [x] **Story Generation Complete** - Notification with story details
- [x] **Low Credit Alert** - Warning when credits are low
- [x] **Welcome Email** - Onboarding email for new users
- [x] **Account Deletion Scheduled** - Confirmation email

### Data Privacy (GDPR/CCPA) ✅
- [x] Privacy Settings page
- [x] Privacy Policy page
- [x] Data export functionality
- [x] Account deletion request
- [x] Consent preferences

### Automation System ✅
- [x] Health monitor (every 1 min)
- [x] Auto-recovery for failed services
- [x] API validator (every 5 min)
- [x] Database maintenance (every hour)
- [x] Security scanner

### Circuit Breaker (Resilience4j) ✅
- [x] Payment service circuit breaker
- [x] Worker service circuit breaker
- [x] Retry mechanism
- [x] Rate limiter

## API Endpoints

### Public
- POST /api/auth/register, /api/auth/login
- GET /api/payments/products, /api/payments/currencies
- GET /api/payments/exchange-rate/{currency}
- POST /api/chatbot/message, /api/chatbot/clear

### Protected
- GET /api/auth/me
- GET /api/credits/balance, /api/credits/ledger
- POST /api/generate/reel, /api/generate/story
- GET /api/generate/generations
- POST /api/payments/create-order, /api/payments/verify
- GET /api/privacy/my-data, /api/privacy/export
- POST /api/privacy/delete-request

## Test Credentials
- **Admin:** admin@creatorstudio.ai / Admin@123
- **Test User:** corstest1771172193@example.com / CorsTest123!

## Security Scan Results
- Rate limiting: ✅ Working (5 attempts/minute)
- Security headers: ✅ Added (CSP, X-Frame-Options, etc.)
- CORS: ✅ Properly configured
- JWT: ✅ Secure (HS256)

## Mocked/Test Mode
- **Razorpay** - TEST MODE (not live payments)
- **Email** - Requires SMTP configuration for production

## Completed December 2025
1. ✅ Security Headers (X-Content-Type-Options, X-Frame-Options, CSP)
2. ✅ Rate Limiting on Login (5 attempts per IP per minute)
3. ✅ Live Currency Conversion (Frankfurter API)
4. ✅ Email Notifications Service (6 notification types)
5. ✅ AI Chatbot (GPT-5.2)
6. ✅ Circuit Breaker (Resilience4j)
7. ✅ Payment Exception Handling
8. ✅ Security Scanner Automation
