# Visionary Suite - Product Requirements Document

## Original Problem Statement
Full-stack SaaS platform for creative content generation with comprehensive admin analytics, stability improvements, and user feedback systems.

## Core Features (Implemented)
- **Content Generation**: Reel Generator, Comic AI, GIF Maker, Story Generator, Comic Storybook
- **User Authentication**: JWT-based auth with email verification
- **Payment Integration**: Cashfree payment gateway
- **Credit System**: Wallet-based credit management for generations
- **Admin Dashboard**: Comprehensive analytics, user management, and monitoring

## Recent Changes

### 2025-02-26: SRE Phase 2 & 3 Implementation (P1)
**Worker & DB Optimization + Output Reliability**

#### Phase 2 - Worker Queues & Database Indexes
- **Separate Worker Queues**: Created `/app/backend/services/worker_queues.py` with dedicated queues for:
  - TEXT queue (fast jobs: stories, reels) - max 5 concurrent
  - IMAGE queue (image generation) - max 3 concurrent
  - VIDEO queue (slow jobs: videos) - max 2 concurrent
  - BATCH queue (bulk operations) - max 1 concurrent
- **Database Indexes**: Created `/app/backend/services/database_indexes.py` with comprehensive indexes for:
  - Users, Jobs, Generations, Credit Ledger, Orders
  - Analytics collections (visitor_events, sessions, feature_events, ratings)
  - Dead letter queue and fallback outputs
  - 55 indexes now in place for optimized queries

#### Phase 3 - Output Reliability
- **Idempotency Service**: `/app/backend/services/idempotency_service.py`
  - Prevents duplicate job creation
  - SHA256 hash-based request deduplication
  - Configurable TTL (default 24 hours)
- **Auto-Retry Logic**: Updated `/app/backend/routes/job_worker.py`
  - Max 3 retries with exponential backoff (10s, 30s, 90s)
  - Smart error classification (retryable vs non-retryable)
  - 5-minute timeout per job
- **Fallback Output Service**: `/app/backend/services/fallback_output_service.py`
  - Generates alternative content when primary generation fails
  - Fallback types: script for video, prompt enhancement for image, outline for story
  - Stores fallback in database for user retrieval

#### SRE Monitoring Endpoints
New `/api/sre/*` endpoints:
- `GET /api/sre/health` - Public health check
- `GET /api/sre/status` - Comprehensive SRE status (admin)
- `GET /api/sre/performance` - Performance metrics (admin)
- `GET /api/sre/indexes` - Database index status (admin)
- `POST /api/sre/indexes/create` - Manual index creation (admin)
- `GET /api/sre/dlq` - Dead letter queue items (admin)
- `POST /api/sre/dlq/{id}/retry` - Retry DLQ item (admin)
- `GET /api/sre/fallbacks` - View fallback outputs (admin)

### 2025-02-26: Admin Dashboard Resilience Fix (P0)
- Fixed partial API failure handling
- Dashboard now displays data even when some APIs fail
- Warning banner for specific failures instead of global error

## Architecture

```
/app/
├── backend/
│   ├── models/
│   ├── performance.py              # Performance middleware, metrics, circuit breakers
│   ├── routes/
│   │   ├── job_worker.py           # Updated with retry logic & fallbacks
│   │   ├── sre_monitoring.py       # NEW: SRE monitoring endpoints
│   │   └── wallet.py               # Credit & job management
│   ├── services/
│   │   ├── worker_queues.py        # NEW: Separate worker queues
│   │   ├── database_indexes.py     # NEW: Index management
│   │   ├── idempotency_service.py  # NEW: Request deduplication
│   │   └── fallback_output_service.py # NEW: Fallback outputs
│   └── server.py
├── frontend/
│   └── src/
│       ├── components/
│       │   └── admin/StatCard.js   # Updated with error state
│       └── pages/
│           └── AdminDashboard.js   # Updated with resilience
└── load_test.py
```

## Key API Endpoints

### SRE Monitoring (NEW)
- `GET /api/sre/health` - System health status
- `GET /api/sre/status` - Full SRE dashboard
- `GET /api/sre/performance` - Performance metrics

### Existing
- `POST /api/auth/login` - User authentication
- `GET /api/admin/analytics/dashboard` - Admin dashboard data
- `POST /api/wallet/jobs` - Create generation job (idempotent)

## 3rd Party Integrations
- Cashfree (payments)
- Gemini Nano Banana (AI generation)
- OpenAI/Sora 2 (video generation)
- fpdf2 (PDF generation)
- Pillow (GIF creation)
- Locust (load testing)

## Performance Characteristics
- **Database**: 55 optimized indexes across all collections
- **Worker Queues**: 4 priority lanes (TEXT, IMAGE, VIDEO, BATCH)
- **Retry Logic**: 3 attempts with exponential backoff
- **Circuit Breakers**: For Gemini, OpenAI, ElevenLabs, Storage
- **Request Tracking**: Correlation IDs on all requests
- **Latency Tracking**: Bucketed metrics (<100ms, <500ms, <1s, <5s, >5s)

## Backlog (Prioritized)

### P2 - In Progress
1. **Auto-Scaling & Self-Healing**
   - Auto-scale workers based on queue depth
   - Circuit breaker for failing external providers

2. **File Storage Optimization**
   - CDN integration for generated assets

### P3 - Future
1. **Observability Improvements**
   - Prometheus/Grafana integration
   - Distributed tracing (Jaeger/Zipkin)

2. **Advanced Failover**
   - Multi-region support
   - Database read replicas

## Test Credentials
- Admin: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`
- Demo: `demo@example.com` / `Password123!`
