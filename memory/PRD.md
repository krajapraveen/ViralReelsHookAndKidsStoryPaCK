# CreatorStudio AI - Product Requirements Document

## Overview
**Tagline:** "Generate viral reels + kids story videos in minutes."

## Tech Stack
- **Frontend:** React + TailwindCSS + Shadcn/UI
- **Backend:** Python/FastAPI on port 8001 (migrated from Spring Boot)
- **Database:** MongoDB
- **AI Worker:** Python/Flask on port 5000 (GPT-5.2 via emergentintegrations)
- **Automation:** Python scripts managed by Supervisor

## Core Features

### Implemented ✅
- [x] AI Reel Script Generator (instant generation, 1 credit)
- [x] Kids Story Video Pack Generator (async, 6-10 credits)
- [x] Credit System (54 free credits on signup)
- [x] User Authentication (JWT & Google Sign-On)
- [x] Admin Dashboard with Analytics
- [x] Feature Voting System
- [x] International Currency Support (INR, USD, EUR, GBP)
- [x] AI Chatbot (GPT-5.2)
- [x] Feedback Widget & Admin View
- [x] Privacy Policy & Settings
- [x] Automation Dashboard

### In Test Mode / Mocked
- Razorpay Payments (test keys)
- Currency Exchange Rates (hardcoded)
- Email Service (stub)

## Security Features
- JWT Authentication with role-based access
- Input validation & sanitization
- CORS configuration
- Admin-only routes protection

## API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - Email/password login
- `POST /api/auth/google-callback` - Google OAuth callback
- `GET /api/auth/me` - Get current user

### Credits
- `GET /api/credits/balance` - Get credit balance
- `GET /api/credits/ledger` - Get credit history

### Generation
- `POST /api/generate/reel` - Generate reel script
- `POST /api/generate/story` - Generate story pack
- `GET /api/generate/generations` - Get user generations
- `GET /api/generate/generations/{id}` - Get specific generation
- `POST /api/generate/demo-reel` - Public demo endpoint

### Payments
- `GET /api/payments/products` - Get products
- `GET /api/payments/currencies` - Get currencies & rates
- `POST /api/payments/create-order` - Create order
- `POST /api/payments/verify` - Verify payment
- `GET /api/payments/history` - Payment history

### Feedback
- `POST /api/feedback/suggestion` - Submit feedback
- `POST /api/feedback` - Legacy feedback endpoint
- `POST /api/contact` - Contact form

### Admin
- `GET /api/admin/analytics/dashboard` - Analytics data
- `GET /api/admin/feedback/all` - All feedback
- `DELETE /api/admin/feedback/{id}` - Delete feedback

### Chatbot
- `POST /api/chatbot/message` - Chat with AI
- `POST /api/chat` - Chat proxy

## Test Credentials
- **Admin:** admin@creatorstudio.ai / Admin@123
- **Demo User:** demo@example.com / Password123!

## File Structure
```
/app/
├── backend/                # FastAPI backend
│   └── server.py          # Main API server
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── admin/     # Refactored admin components
│       │   │   ├── StatCard.js
│       │   │   ├── OverviewTab.js
│       │   │   ├── VisitorsTab.js
│       │   │   ├── FeaturesTab.js
│       │   │   ├── PaymentsTab.js
│       │   │   ├── SatisfactionTab.js
│       │   │   ├── FeatureRequestsTab.js
│       │   │   └── UserFeedbackTab.js
│       │   ├── AIChatbot.js
│       │   └── FeedbackWidget.js
│       └── pages/
│           ├── AdminDashboard.js (refactored)
│           ├── Dashboard.js
│           ├── Login.js
│           └── ...
├── worker/                 # AI generation worker
│   └── app.py
└── automation/             # Self-healing scripts
```

## Recent Updates (February 2026)

### Fixed Issues
1. **P0 Bug: Feedback not showing on Admin Dashboard** - FIXED
   - Migrated backend to FastAPI with proper feedback endpoints
   - Feedback now saves to MongoDB and displays on admin dashboard

2. **P0 Bug: Browser back button to login** - FIXED
   - Using `navigate('/app', { replace: true })` to prevent history stack issues

### Completed Tasks
- Refactored AdminDashboard.js into 8 separate components
- Migrated backend from Spring Boot to FastAPI (due to Java unavailability)
- Implemented all core API endpoints in FastAPI
- Created comprehensive admin analytics dashboard

## Remaining Tasks

### P1 (High Priority)
- [ ] Verify "Share Your Creation" feature
- [ ] Integrate Email Notification Service
- [ ] Add more comprehensive error handling

### P2 (Medium Priority)
- [ ] Razorpay Production Setup
- [ ] Implement Razorpay Subscription Webhooks
- [ ] Real currency conversion API integration

### P3 (Low Priority)
- [ ] Conduct Copyright Review
- [ ] Add user profile management
- [ ] Enhanced analytics tracking

## Known Limitations
- Razorpay in test mode only
- Currency rates are hardcoded
- Email service is stubbed
- Story generation is simplified (no RabbitMQ)
