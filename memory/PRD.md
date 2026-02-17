# CreatorStudio AI - Product Requirements Document

## Overview
**Tagline:** "Generate viral reels + kids story videos in minutes."
**URL:** https://creator-studio-ai-1.preview.emergentagent.com
**Last Updated:** February 17, 2026

## Tech Stack
- **Frontend:** React + TailwindCSS + Shadcn/UI
- **Backend:** Python/FastAPI on port 8001
- **Database:** MongoDB
- **AI Integrations:**
  - Story Generation: Template-based (no LLM cost)
  - Reel Generation: Gemini 2.0 Flash
  - Image Generation: Gemini 3 Pro Image Preview
  - Video Generation: **Sora 2** (NEW - via emergentintegrations)
- **Payments:** Razorpay (TEST MODE)
- **PDF Generation:** HTML Templates + Playwright

## Test Credentials
| Role | Email | Password |
|------|-------|----------|
| **Admin** | `admin@creatorstudio.ai` | `Cr3@t0rStud!o#2026` |
| **Demo User** | `demo@example.com` | `Password123!` |

## Implementation Status

### ✅ GenStudio Suite - COMPLETE (Feb 17, 2026)

All GenStudio features are now fully functional with:
- **Async Job Pattern** - Video endpoints return immediately with job ID, frontend polls for completion
- **Auto-refund on failure** - Credits refunded automatically if generation fails
- **15-minute file expiry** - Generated files auto-deleted

| Feature | Status | Cost | Time |
|---------|--------|------|------|
| Text → Image | ✅ Working | 10 credits | ~17s |
| Text → Video | ✅ Working | 10 credits | ~60-90s |
| Image → Video | ✅ Working | 10 credits | ~60-90s |
| Video Remix | ✅ Working | 12 credits | ~60-90s |
| Style Profiles | ✅ Working | 20 credits | instant |
| History | ✅ Working | - | - |

### API Endpoints

**GenStudio:**
- `GET /api/genstudio/dashboard` - Dashboard stats
- `POST /api/genstudio/text-to-image` - Image generation
- `POST /api/genstudio/text-to-video` - Video generation (async)
- `POST /api/genstudio/image-to-video` - Image animation (async)
- `POST /api/genstudio/video-remix` - Video remix (async)
- `GET /api/genstudio/job/{job_id}` - Poll job status
- `GET /api/genstudio/download/{job_id}/{filename}` - Download file
- `POST /api/genstudio/style-profile` - Create style profile
- `GET /api/genstudio/style-profiles` - List profiles
- `GET /api/genstudio/history` - Generation history

### Credit System
| Action | Cost |
|--------|------|
| Signup Bonus | +100 credits |
| Reel Generation | 10 credits |
| Story Generation | 10 credits |
| Text → Image | 10 credits |
| Text → Video | 10 credits |
| Image → Video | 10 credits |
| Video Remix | 12 credits |
| Style Profile Create | 20 credits |

### Routes
| Route | Page | Status |
|-------|------|--------|
| `/app/gen-studio` | GenStudio Dashboard | ✅ |
| `/app/gen-studio/text-to-image` | Text to Image | ✅ |
| `/app/gen-studio/text-to-video` | Text to Video | ✅ |
| `/app/gen-studio/image-to-video` | Image to Video | ✅ |
| `/app/gen-studio/video-remix` | Video Remix | ✅ |
| `/app/gen-studio/style-profiles` | Style Profiles | ✅ |
| `/app/gen-studio/history` | Generation History | ✅ |

## Key Files
- `/app/backend/server.py` - Main backend with GenStudio endpoints
- `/app/backend/routes/genstudio.py` - Extracted GenStudio router (partial)
- `/app/frontend/src/pages/GenStudio*.js` - GenStudio UI pages (7 files)

## Test Reports
- `/app/test_reports/iteration_19.json` - GenStudio UI (100% pass)
- `/app/test_reports/iteration_20.json` - Initial E2E (Cloudflare timeout identified)
- `/app/test_reports/iteration_21.json` - Full E2E (100% pass with async pattern)

## Architecture Notes

### Async Video Generation Pattern
Video endpoints (text-to-video, image-to-video, video-remix) use background tasks:
1. Validate request and deduct credits upfront
2. Create job with status "processing"
3. Start `asyncio.create_task()` for generation
4. Return immediately with job ID and poll URL
5. Frontend polls `/api/genstudio/job/{job_id}` every 5 seconds
6. On completion: job status = "completed" with output URLs
7. On failure: credits auto-refunded, job status = "failed"

### Image-to-Video Flow
Since Sora 2 doesn't have direct image-to-video API:
1. Upload image saved temporarily
2. Gemini analyzes image and creates detailed prompt
3. Sora 2 generates video from enhanced text prompt
4. Input image deleted after generation

## Backlog
- [ ] Backend refactoring (server.py → modular routes)
- [ ] Razorpay production setup
- [ ] Style profile image upload and training
- [ ] Convert feature backend implementation
