# CreatorStudio AI - Product Requirements Document

## Original Problem Statement
Build a full-stack application named "CreatorStudio AI" for generating viral reels and kids story videos, with expanded capabilities including:
- GenStudio AI generation suite (Text-to-Image, Text-to-Video, etc.)
- Security hardening and content moderation
- Admin dashboard with payment and exception monitoring
- Creator Pro Tools (15+ features)
- TwinFinder face lookalike finder (future)

## User Personas
1. **Content Creators** - Need viral content scripts, hooks, captions for social media
2. **Parents/Educators** - Need kid-friendly story generation
3. **Business Owners** - Need AI image/video generation for marketing
4. **Admin Users** - Need monitoring of payments, exceptions, and system health

## Core Requirements
- [x] Viral reel script generation with hooks, captions, hashtags
- [x] Kids story generation with scenes and narration
- [x] GenStudio suite (Text-to-Image, Text-to-Video)
- [x] User authentication (Email/Password + Google OAuth)
- [x] Credit-based system with Razorpay payments
- [x] Admin dashboard with analytics
- [x] Payment monitoring (successful/failed/refunded)
- [x] Exception monitoring and logging
- [x] Content moderation and security hardening
- [x] File expiry (3 minutes for security)

## Tech Stack
- **Frontend**: React, TailwindCSS, Shadcn/UI
- **Backend**: FastAPI, MongoDB (motor)
- **AI**: Gemini (text/image), Sora 2 (video) via emergentintegrations
- **Auth**: JWT + Emergent-managed Google Auth
- **Payments**: Razorpay (test mode)
- **Security**: Rate limiting, CSP headers, ML content moderation

## What's Been Implemented

### February 17, 2026
- ✅ Admin dashboard payment monitoring tab
- ✅ Admin dashboard exception monitoring tab
- ✅ Updated landing page text to include "much more"
- ✅ Updated description with GenStudio, content tools, etc.
- ✅ Backend routes for /admin/payments/successful, /failed, /refunded
- ✅ Backend routes for /admin/exceptions/all, resolve, delete
- ✅ Exception logging utility for all features
- ✅ Payment logging with refund support
- ✅ Modular route files created (routes/*.py)

### Previous Sessions
- ✅ GenStudio suite (Text-to-Image, Text-to-Video, Image-to-Video, Video Remix)
- ✅ Async job pattern for video generation (background tasks + polling)
- ✅ Security middleware (CSP headers, rate limiting, attack pattern blocking)
- ✅ ML content moderation
- ✅ 3-minute file expiry for security
- ✅ Style profiles for GenStudio
- ✅ Content vault and trending topics
- ✅ Story tools (worksheets, printable books)
- ✅ Creator tools (hashtag bank, thumbnails, calendar, carousel)
- ✅ Convert tools (reel-to-carousel, story-to-reel, etc.)

## Prioritized Backlog

### P0 - Critical (Next Sprint)
1. Complete backend refactoring (server.py → modular routes)
   - Move remaining logic from server.py to routes/
   - Reduce server.py to thin orchestrator
2. TwinFinder implementation (face lookalike finder)
3. Creator Pro Tools implementation (15+ features)

### P1 - High Priority
1. Razorpay production setup (awaiting live keys)
2. Subscription webhooks for auto-renewal
3. Advanced ML threat detection model
4. Performance optimization for high load

### P2 - Medium Priority
1. Style Profile Gallery UI improvements
2. Additional content repurposing formats
3. API rate limiting refinement
4. Enhanced error messages

## Known Issues
1. **Image-to-Video Workaround**: Uses Gemini image-to-text + Sora text-to-video instead of direct image-to-video API (library limitation)
2. **server.py Size**: ~4900 lines, needs refactoring into modular routes

## API Endpoints

### Core Generation
- POST /api/generate/reel - Generate reel script (10 credits)
- POST /api/generate/story - Generate kids story (10 credits)

### GenStudio
- POST /api/genstudio/text-to-image - Generate image (10 credits)
- POST /api/genstudio/text-to-video - Generate video (10 credits, async)
- GET /api/genstudio/job/{id} - Poll job status
- GET /api/genstudio/download/{id}/{filename} - Download file

### Admin
- GET /api/admin/analytics/dashboard - Full analytics
- GET /api/admin/payments/successful - Success payments
- GET /api/admin/payments/failed - Failed payments with reasons
- GET /api/admin/payments/refunded - Refunded payments
- GET /api/admin/exceptions/all - All logged exceptions
- PUT /api/admin/exceptions/{id}/resolve - Mark resolved
- DELETE /api/admin/exceptions/{id} - Delete exception

### Payments
- GET /api/payments/products - Available products
- POST /api/payments/create-order - Create Razorpay order
- POST /api/payments/verify - Verify and complete payment

## Database Collections
- users: User accounts with credits
- generations: Reel/Story generation history
- genstudio_jobs: AI generation jobs with status
- orders: Payment orders
- payment_logs: Payment transaction logs
- exception_logs: System exception logs
- credit_ledger: Credit transaction history
- style_profiles: GenStudio brand profiles
- feedback: User feedback
- trending_topics: Admin-managed trending topics

## Security Measures
- JWT authentication with 7-day expiry
- Rate limiting on auth/payment endpoints
- CSP headers and X-Frame-Options
- ML content moderation on prompts
- Input sanitization for attack patterns
- 3-minute file expiry for generated content
- Exception logging for monitoring

## Test Credentials
- **Admin**: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
- **User**: demo@example.com / Password123!
