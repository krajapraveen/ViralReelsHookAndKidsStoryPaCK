# CreatorStudio AI - Product Requirements Document

## Overview
**Tagline:** "Generate viral reels + kids story videos in minutes."

## Tech Stack
- **Frontend:** React + TailwindCSS + Shadcn/UI
- **Backend:** Python/FastAPI on port 8001
- **Database:** MongoDB
- **AI Worker:** Python/Flask on port 5000 (GPT-5.2 via emergentintegrations)
- **Automation:** Python scripts managed by Supervisor

## Core Features

### Implemented ✅
- [x] AI Reel Script Generator (instant generation, 1 credit)
- [x] Kids Story Video Pack Generator (async, 6-10 credits)
- [x] Credit System (54 free credits on signup)
- [x] User Authentication (JWT & Google Sign-On)
- [x] Admin Dashboard with Analytics (7 tabs)
- [x] Feature Voting System
- [x] International Currency Support (INR, USD, EUR, GBP)
- [x] AI Chatbot (GPT-5.2)
- [x] Feedback Widget & Admin View
- [x] Privacy Policy & Settings
- [x] Automation Dashboard
- [x] **Share Your Creation** - Download card & copy link for social sharing
- [x] **User Profile Management** - Full profile page with:
  - Profile information editing
  - Password change
  - Email notification preferences
  - Data export (GDPR compliance)
  - Account deletion
- [x] **Copyright & Legal Guidelines** - Comprehensive legal page with:
  - AI content ownership
  - Content usage guidelines
  - Kids story content safety
  - Third-party copyright protection
  - Platform-specific guidelines
- [x] **Email Notification Service** (STUBBED - Ready for SMTP)
  - Welcome emails
  - Payment confirmations
  - Generation completion alerts
  - Logged to `email_logs` collection

### In Test Mode / Mocked
- Razorpay Payments (test keys)
- Currency Exchange Rates (hardcoded)
- Email Service (logged but not sent)

## API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - Email/password login
- `POST /api/auth/google-callback` - Google OAuth callback
- `GET /api/auth/me` - Get current user
- `PUT /api/auth/profile` - Update profile name
- `PUT /api/auth/password` - Change password
- `GET /api/auth/export-data` - Export all user data
- `DELETE /api/auth/account` - Delete account

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
│   └── server.py          # Main API server (~800 lines)
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── admin/     # Refactored admin components (8 files)
│       │   ├── AIChatbot.js
│       │   ├── FeedbackWidget.js
│       │   └── ShareButton.js
│       └── pages/
│           ├── AdminDashboard.js (refactored)
│           ├── Dashboard.js (with Profile & Copyright links)
│           ├── Profile.js (NEW - user management)
│           ├── CopyrightInfo.js (NEW - legal guidelines)
│           ├── Login.js
│           └── ...
├── worker/                 # AI generation worker
│   └── app.py
└── automation/             # Self-healing scripts
```

## Recent Updates (February 2026)

### Session 2 - All Tasks Completed
1. **Share Your Creation Feature** - VERIFIED ✅
   - ShareButton component works on ReelGenerator and StoryGenerator
   - Download card (PNG) and copy link functionality
   
2. **Email Notification Service** - IMPLEMENTED (STUBBED) ✅
   - Functions: notify_welcome, notify_payment_success, notify_generation_complete
   - Logged to email_logs collection
   - Ready for SMTP integration (SendGrid, AWS SES, etc.)
   
3. **Copyright Review** - COMPLETED ✅
   - New CopyrightInfo.js page at /app/copyright
   - AI content ownership guidelines
   - Content usage permissions/prohibitions
   - Kids content safety guidelines
   - Platform-specific guidelines (Instagram, TikTok, YouTube)
   - Legal disclaimer and DMCA notice
   
4. **User Profile Management** - IMPLEMENTED ✅
   - New Profile.js page at /app/profile
   - Profile information editing
   - Password change (non-Google users)
   - Email notification preferences
   - Data export (GDPR compliance)
   - Account deletion with confirmation

### Session 1 - Bugs Fixed
- P0 Bug: Feedback visibility on Admin Dashboard - FIXED
- P0 Bug: Browser back button navigation - FIXED
- AdminDashboard refactored into 8 components

## Remaining Tasks

### P1 (High Priority)
- [ ] Connect email service to actual SMTP (SendGrid/AWS SES)
- [ ] Add user avatar upload
- [ ] Implement 2FA authentication

### P2 (Medium Priority)
- [ ] Razorpay Production Setup
- [ ] Implement Razorpay Subscription Webhooks
- [ ] Real currency conversion API integration

### P3 (Low Priority)
- [ ] Social media sharing integration
- [ ] User referral system
- [ ] Enhanced analytics tracking

## Known Limitations
- Email notifications are STUBBED (logged but not sent)
- Razorpay in test mode only
- Currency rates are hardcoded
- Story generation is simplified (no RabbitMQ queue)

## Security Features
- JWT Authentication with role-based access
- Input validation & sanitization
- Content filtering for kids' content
- CORS configuration
- Admin-only routes protection
- Password hashing with bcrypt
