# CreatorStudio AI - Product Requirements Document

## Overview
**Tagline:** "Generate viral reels + kids story videos in minutes."
**URL:** https://creator-studio-ai-1.preview.emergentagent.com
**Last Updated:** February 17, 2026

## Latest Implementation (Feb 17, 2026)

### 1. Backend Refactoring ✅
Created modular architecture with separate files:
- `/app/backend/shared.py` - Shared dependencies (db, auth, credits)
- `/app/backend/security.py` - Security module (rate limiting, headers)
- `/app/backend/ml_threat_detection.py` - ML-based threat detection
- `/app/backend/routes/style_profiles.py` - Style profile management
- `/app/backend/routes/convert.py` - Content conversion endpoints

### 2. Style Profile Training ✅
**Endpoints:**
- `POST /api/genstudio/style-profile` - Create profile (20 credits)
- `POST /api/genstudio/style-profile/{id}/upload-image` - Upload reference image
- `POST /api/genstudio/style-profile/{id}/train` - Train profile (needs 5+ images)
- `DELETE /api/genstudio/style-profile/{id}` - Delete profile

**Features:**
- Upload up to 20 reference images per profile
- Minimum 5 images required for training
- Gemini-powered style analysis
- Generated style guide for consistent content

### 3. Convert Feature Backend ✅
**Endpoints:**
- `POST /api/convert/text-to-story` - Convert text to kids story (10 credits)
- `POST /api/convert/text-to-reel` - Convert text to reel script (15 credits)
- `GET /api/convert/status/{job_id}` - Poll conversion status
- `GET /api/convert/history` - Get conversion history
- `GET /api/convert/costs` - Get conversion costs

**Conversion Types:**
| Type | Cost | Description |
|------|------|-------------|
| text-to-story | 10 | Transform any text into a kids story |
| text-to-reel | 15 | Transform text into viral reel script |
| story-to-reel | 1 | Convert story to reel (existing) |
| reel-to-carousel | 1 | Convert reel to carousel (existing) |

### 4. Advanced ML Threat Detection ✅
**Components:**
- `RequestPatternAnalyzer` - Anomaly detection using statistical analysis
- `BotDetector` - Bot detection using user agent and behavior analysis
- `ContentModerator` - ML-based content moderation with severity levels

**Content Categories Blocked:**
| Category | Severity | Examples |
|----------|----------|----------|
| identity_theft | CRITICAL | deepfake, face swap, impersonate |
| celebrity | HIGH | celebrity, famous person, public figure |
| explicit | CRITICAL | nude, porn, nsfw |
| violence | CRITICAL | gore, murder, terrorist |
| child_safety | CRITICAL | child abuse, minor |
| illegal | CRITICAL | drug dealing, weapon sale |
| hate_speech | HIGH | racist, discrimination |
| scam | HIGH | phishing, fraud |
| copyright | MEDIUM | copyright infringement |

**Integration:**
- Integrated into GenStudio text-to-image endpoint
- Integrated into reel generation endpoint
- Integrated into story generation endpoint
- All blocked content is logged for security audit

## Test Credentials
| Role | Email | Password |
|------|-------|----------|
| **Admin** | `admin@creatorstudio.ai` | `Cr3@t0rStud!o#2026` |
| **Demo User** | `demo@example.com` | `Password123!` |

## Security Configuration
- File expiry: 3 minutes (aggressive cleanup)
- Rate limiting: Register 5/min, Login 10/min, Payments 10-20/min
- Security headers: CSP, HSTS, X-Frame-Options, etc.
- IP blocking after 10 suspicious attempts

## Test Reports
- `/app/test_reports/iteration_22.json` - Security testing (30/30 PASS)
- `/app/test_reports/iteration_23.json` - New features testing

## Architecture
```
/app/backend/
├── server.py           # Main server (4600+ lines)
├── shared.py           # Shared dependencies
├── security.py         # Security module
├── ml_threat_detection.py  # ML threat detection
├── pdf_generator.py    # PDF generation
└── routes/
    ├── style_profiles.py   # Style profile CRUD
    ├── convert.py          # Content conversion
    └── ...
```

## Backlog
- [ ] Complete server.py refactoring (move all routes to /routes/)
- [ ] Razorpay production setup
- [ ] Style profile gallery preview
- [ ] Batch generation capability
