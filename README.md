# CreatorStudio AI

![CI/CD Pipeline](https://github.com/YOUR_USERNAME/YOUR_REPO/workflows/CI%2FCD%20Pipeline%20-%20Smoke%20Tests%20%26%20Deployment/badge.svg)
![Mobile Tests](https://github.com/YOUR_USERNAME/YOUR_REPO/workflows/Mobile%20%26%20Visual%20Regression%20Tests/badge.svg)

> AI-powered content creation platform for creators

## Quick Start

```bash
# Frontend
cd frontend && yarn install && yarn start

# Backend
cd backend && pip install -r requirements.txt && uvicorn server:app --reload
```

## Testing

```bash
cd playwright-tests

# Run smoke tests (recommended before commits)
yarn test:smoke

# Run full test suite
yarn test:all
```

## CI/CD Status

| Workflow | Status |
|----------|--------|
| Smoke Tests | Runs on every push |
| Full Tests | Runs on main branch |
| Mobile Tests | Runs on frontend PRs |
| Security Scan | Weekly |

See [CI/CD Documentation](.github/CI_CD_DOCUMENTATION.md) for details.

## Test Reports

- [QA Final Report](QA_Final_Report.md)
- [Mobile Test Report](Mobile_Test_Report.md)
- [A-Z Feature Map](A-Z_Feature_Map.md)
