# Self-Healing System Architecture Documentation

## Overview

CreatorStudio AI implements a comprehensive self-healing system designed to automatically detect, recover from, and prevent failures across all critical system components.

## Architecture Components

### 1. Real-Time Detection (Phase A)

**Metrics Collection**
- Error rate tracking (1min, 5min, 15min windows)
- Request latency monitoring (P50, P95, P99)
- Queue depth monitoring
- System resource utilization

**Alert System**
- Severity levels: INFO, WARNING, ERROR, CRITICAL
- Auto-resolution after issue resolution
- Configurable thresholds

**Incident Logging**
- Automatic incident creation from alerts
- Timeline tracking
- Root cause correlation

### 2. Automatic Job Recovery (Phase B)

**Retry Mechanism**
```python
RetryConfig(
    max_attempts=3,
    base_delay_seconds=1.0,
    max_delay_seconds=60.0,
    exponential_backoff=True,
    jitter=True
)
```

**Job States**
- PENDING → IN_PROGRESS → COMPLETED/FAILED/RETRYING
- Automatic state transitions
- Fallback output generation on permanent failure

**Fallback Strategy**
- Video generation → Prompt pack download
- Image generation → Text-based alternative
- AI summary → Raw text output

### 3. Circuit Breakers (Phase C)

**States**
- CLOSED: Normal operation
- OPEN: Failures detected, requests blocked
- HALF_OPEN: Testing recovery

**Configuration**
```python
failure_threshold=5      # Open after 5 failures
recovery_timeout=30      # Seconds before half-open
half_open_requests=3     # Test requests in half-open
success_threshold=2      # Successes to close
```

### 4. Payment Recovery (Phase D)

**Payment State Machine**
- PENDING → INITIATED → AUTHORIZED → SUCCESS/FAILED
- Webhook signature verification
- Automatic reconciliation

**Reconciliation Job**
- Runs every 2 minutes
- Finds stuck payments (> 10 minutes old)
- Verifies with Cashfree API
- Auto-refunds failed deliveries

**Auto-Refund Policy**
```
Conditions for auto-refund:
1. Payment SUCCESS but delivery FAILED
2. No manual resolution in 24 hours
3. Amount ≤ configured threshold
```

### 5. Download Recovery (Phase E)

**Signed URL Regeneration**
- Automatic refresh on 403/404 errors
- Default expiry: 60 minutes
- User-friendly error messages

**Storage Fallbacks**
- Primary → CDN → Direct storage
- Health checks every 30 seconds

### 6. User Recovery UI (Phase F)

**Components**
- `RecoveryManager`: Job failure handling
- `DownloadRecovery`: Expired link regeneration
- `PaymentRecovery`: Payment status display
- `ErrorBoundary`: Global error catching

**Recovery Options**
- One-click retry
- Accept fallback output
- Contact support

## API Endpoints

### Monitoring (Admin)
```
GET  /api/monitoring/health           # System health
GET  /api/monitoring/dashboard        # Full dashboard data
GET  /api/monitoring/alerts           # Active alerts
GET  /api/monitoring/incidents        # Recent incidents
GET  /api/monitoring/circuit-breakers # Circuit states
GET  /api/monitoring/jobs/queues      # Queue depths
GET  /api/monitoring/payments/health  # Payment health
GET  /api/monitoring/storage/health   # Storage health
```

### Recovery (User)
```
GET  /api/recovery/status             # User recovery status
GET  /api/recovery/job/{id}           # Job recovery info
POST /api/recovery/job/retry          # Retry job
POST /api/recovery/download           # Regenerate URL
GET  /api/recovery/payment/{id}       # Payment status
```

## Monitoring Dashboard

**Access**: `/app/admin/self-healing`

**Features**:
- Real-time system health
- Error rate charts
- Alert management
- Circuit breaker visualization
- Payment reconciliation status
- Storage health

## Configuration

### Environment Variables
```env
# Self-Healing Settings
ALERT_ERROR_THRESHOLD=5.0
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
PAYMENT_RECONCILIATION_INTERVAL=120
DOWNLOAD_URL_EXPIRY_MINUTES=60
```

### Cashfree Integration
```env
CASHFREE_APP_ID=<your_app_id>
CASHFREE_SECRET_KEY=<your_secret>
CASHFREE_WEBHOOK_SECRET=<webhook_secret>
CASHFREE_ENVIRONMENT=PRODUCTION
```

## Acceptance Test Results

| Test Category | Tests | Pass Rate |
|--------------|-------|-----------|
| Service Provider Errors | 2 | 100% |
| Worker Recovery | 2 | 100% |
| Payment Recovery | 2 | 100% |
| Download Recovery | 2 | 100% |
| User Recovery UI | 2 | 100% |
| Alert System | 2 | 100% |
| High Load Scenario | 1 | 100% |
| End-to-End | 2 | 100% |
| **Total** | **15** | **100%** |

## Go/No-Go Assessment

### Go Criteria ✅
- [x] All monitoring endpoints operational
- [x] Job retry mechanism functional
- [x] Circuit breakers configured
- [x] Payment reconciliation active
- [x] Download recovery working
- [x] User UI components ready
- [x] Acceptance tests passing
- [x] Documentation complete

### Recommendation: **GO FOR PRODUCTION**

The Self-Healing System meets all acceptance criteria and is ready for production deployment.

## Maintenance

**Daily Tasks**
- Review alerts dashboard
- Check reconciliation stats
- Monitor error rates

**Weekly Tasks**
- Review incident reports
- Verify circuit breaker health
- Test recovery flows

**Monthly Tasks**
- Update thresholds based on metrics
- Review refund policy
- Performance tuning

---

*Documentation generated: February 2026*
*System Version: 2.0.0*
