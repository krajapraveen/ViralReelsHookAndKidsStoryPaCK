# CI/CD Pipeline Documentation

## Overview

This document describes the CI/CD pipeline configuration for CreatorStudio AI.

## Workflows

### 1. Main CI/CD Pipeline (`ci-cd-pipeline.yml`)

**Triggers:**
- Push to `main`, `master`, or `develop` branches
- Pull requests to `main` or `master`
- Manual trigger via workflow dispatch

**Jobs:**

| Job | Description | Duration |
|-----|-------------|----------|
| `lint-and-build` | Lint code and build frontend | ~3 min |
| `smoke-tests` | Run 15 critical path tests | ~1 min |
| `full-tests` | Run complete test suite | ~10 min |
| `deploy` | Deploy to production | ~2 min |
| `post-deploy-verify` | Verify deployment | ~2 min |

**Pipeline Flow:**
```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  Lint & Build   │────▶│ Smoke Tests  │────▶│   Deploy    │
└─────────────────┘     └──────────────┘     └─────────────┘
                               │                     │
                               ▼                     ▼
                        ┌──────────────┐     ┌─────────────┐
                        │ Full Tests   │     │  Verify     │
                        │ (optional)   │     │  Deployment │
                        └──────────────┘     └─────────────┘
```

### 2. Mobile & Visual Tests (`mobile-visual-tests.yml`)

**Triggers:**
- Pull requests affecting `frontend/**` or `playwright-tests/**`
- Manual trigger

**Features:**
- Tests across multiple viewports (iPhone SE, iPhone 12, iPad)
- Visual regression detection using pixelmatch
- Screenshot artifacts for review

### 3. Security & Performance (`security-performance.yml`)

**Triggers:**
- Weekly schedule (Sundays at 2 AM UTC)
- Manual trigger

**Tests:**
- API response time benchmarks
- Concurrent request handling
- Dependency vulnerability audits

## Required Secrets

Configure these secrets in your GitHub repository settings:

| Secret | Description | Required |
|--------|-------------|----------|
| `REACT_APP_BACKEND_URL` | Backend API URL for builds | Yes |
| `PREVIEW_URL` | Preview/staging environment URL | Yes |
| `PRODUCTION_URL` | Production environment URL | Yes |
| `VERCEL_TOKEN` | Vercel deployment token (if using Vercel) | Optional |

## Local Development

### Running Tests Locally

```bash
# Navigate to test directory
cd playwright-tests

# Install dependencies
yarn install
npx playwright install chromium --with-deps

# Run smoke tests (fast, ~1 min)
yarn test:smoke

# Run mobile tests
yarn test:mobile

# Run edge case tests
yarn test:edge

# Run all tests
yarn test:all

# Run visual comparison
yarn visual:compare
```

### Test Commands Reference

| Command | Description | Duration |
|---------|-------------|----------|
| `yarn test:smoke` | 15 critical path tests | ~1 min |
| `yarn test:desktop` | Desktop functional tests | ~4 min |
| `yarn test:mobile` | Mobile comprehensive tests | ~8 min |
| `yarn test:mobile:deep` | Deep mobile functionality | ~4 min |
| `yarn test:edge` | Edge case tests | ~3 min |
| `yarn test:all` | Complete test suite | ~15 min |

## Test Coverage

### Smoke Tests (15 tests)
- API health check
- Landing page load
- Login functionality
- Dashboard access
- Key feature pages
- Admin access
- Protected route security

### Mobile Tests (30 tests)
- Authentication flows
- Dashboard navigation
- Generation features (Comix AI, GIF Maker)
- Admin panel on mobile
- Form inputs and scrolling
- Touch target validation

### Edge Case Tests (26 tests)
- Form validation
- API error handling
- Session management
- Input sanitization (XSS, SQL injection)
- Concurrent operations
- Network conditions

## Artifacts

### Test Reports
- `smoke-test-results.json` - Smoke test JSON report
- `test-results/` - Detailed test output
- `playwright-report/` - HTML test report

### Screenshots
- `mobile-screenshots/` - Mobile viewport captures
- `visual-baselines/` - Baseline images for comparison
- `visual-diffs/` - Difference images

## Troubleshooting

### Common Issues

**Tests fail with timeout:**
- Check if the target URL is accessible
- Increase timeout in playwright.config.ts
- Verify network connectivity

**Visual regression false positives:**
- Update baselines: `yarn visual:compare`
- Check for dynamic content (timestamps, animations)

**Deployment verification fails:**
- Increase wait time after deployment
- Verify production URL is correct
- Check deployment logs

### Getting Help

1. Check test artifacts for screenshots
2. Review trace files: `npx playwright show-trace <trace.zip>`
3. Run tests with `--headed` flag for visual debugging

## Best Practices

1. **Always run smoke tests before merging PRs**
2. **Review mobile screenshots for UI changes**
3. **Update visual baselines when UI intentionally changes**
4. **Monitor weekly security scans**
5. **Keep test execution time under 15 minutes**

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-25 | Initial CI/CD setup |
