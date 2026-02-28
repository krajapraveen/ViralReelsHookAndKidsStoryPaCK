# Visionary Suite - Changelog

## 2026-02-28: Admin Credentials Update & CI/CD Integration (Iteration 109)

### Admin Credentials Changed
- **Old Email**: admin@creatorstudio.ai
- **New Email**: krajapraveen.katta@creatorstudio.ai
- **Password**: Updated to new secure password
- **Verified**: Login tested and working on preview environment

### CI/CD Pipeline Integration
- Updated `/app/.github/workflows/playwright.yml` with:
  - Manual workflow dispatch option
  - Environment selection (preview/production)
  - Chromium and Firefox browser support
  - Test artifacts upload
  - GitHub Step Summary generation
  - Failure notifications

### Package.json Scripts Added
```json
{
  "test": "npx playwright test --project=chromium",
  "test:all": "npx playwright test",
  "test:smoke": "npx playwright test --project=chromium --grep 'should login|should load|health' --workers=1",
  "test:report": "npx playwright show-report"
}
```

### Downloads Endpoint Error Handling
- Enhanced `/api/downloads/my-downloads` with try-catch blocks
- Added logging for debugging production issues
- Production 502 error identified as Cloudflare/nginx issue (not code)

---

## 2026-02-28: Production Stabilization Verified (Iteration 107-108)

### Regression Testing Results:
- Production Tests: 95% PASS
- Preview Tests: 100% PASS
- Playwright Automated Tests: 28/31 PASS (90%)

### Comic Generation Verified:
- Job ID: 6a87fee1-2dcc-4818-bfa8-38c6a34c6913
- Result: BASE64 DATA URL (1,056,382 chars)
- Status: COMPLETED on production

---

## Previous Changes

### Notification System (2026-02-27)
- Bell icon in header
- Notification dropdown panel
- Real-time polling

### 5-Minute Download Expiry (2026-02-27)
- Countdown timer
- Auto-cleanup service
- Premium extension feature

### Worker System (2026-02-26)
- Per-feature worker pools
- Auto-scaling at 80% utilization
- Admin dashboard at /app/admin/workers
