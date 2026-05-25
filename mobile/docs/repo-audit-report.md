# Visionary Suite mobile repo audit

## Scope

This audit covers the existing Visionary Suite repository before adding native mobile code. The mobile app is intentionally added as a separate top-level Expo app in `mobile/` so the existing CRA web app and FastAPI backend remain untouched.

## Web routes found

### Public routes

- `/` landing
- `/pricing`
- `/contact`
- `/reviews`
- `/about`
- `/blog`, `/blog/:slug`
- `/gallery`
- `/explore`, `/app/explore`
- `/experience`
- `/refer`
- `/share/:shareId`
- `/viral/:jobId`
- `/v/:slug`
- `/character/:characterId`
- `/creator/:username`
- `/series/:seriesId`
- `/trailer/:slug`

### Auth routes

- `/login`
- `/signup`
- `/auth/callback`
- `/verify-email`
- `/forgot-password`
- `/reset-password`

### Legal, support, and security routes

- `/privacy-policy`
- `/cookie-policy`
- `/terms`, `/terms-of-service`
- `/user-manual`, `/help`
- `/security`
- `/security/report`
- `/security/report/submitted`

### Authenticated product routes

- `/app` dashboard
- `/app/create`
- `/app/browse`
- `/app/dashboard`
- `/app/my-space`, `/app/my-space/:assetId`
- `/app/history`
- `/app/analytics`
- `/app/story-video-studio`
- `/app/story-preview/:jobId`
- `/app/story-viewer/:jobId`
- `/app/story-battle/:storyId`
- `/app/story-chain/:chainId`
- `/app/story-chain-timeline/:storyId`
- `/app/my-stories`
- `/app/war`
- `/app/story-series`, `/app/story-series/create`, `/app/story-series/:seriesId`
- `/app/characters`, `/app/characters/create`, `/app/characters/:characterId`
- `/app/reels`, `/app/reel-generator`, `/app/reel`
- `/app/stories`, `/app/kids-story`, `/app/story-generator`, `/app/story`, `/app/story-pack`
- `/app/photo-trailer`, `/app/youstar`, `/app/my-movie-trailer`
- `/app/character-studio`, `/app/story-video-studio/characters`
- `/app/coloring-book`
- `/app/comic`, `/app/comix`, `/app/comix-ai`, `/app/photo-to-comic`
- `/app/gif-maker`, `/app/reaction-gif`
- `/app/comic-storybook`, `/app/comic-story-builder`
- `/app/bedtime-story-builder`, `/app/bedtime-stories`
- `/app/story-episode-creator`
- `/app/content-challenge-planner`
- `/app/caption-rewriter`
- `/app/promo-videos`
- `/app/creator-tools`
- `/app/creator-pro`
- `/app/blueprint-library`
- `/app/twinfinder`
- `/app/challenge-generator`
- `/app/tone-switcher`
- `/app/instagram-bio-generator`, `/app/bio-generator`
- `/app/comment-reply-bank`, `/app/reply-bank`
- `/app/thumbnail-generator`
- `/app/brand-story-builder`
- `/app/offer-generator`
- `/app/story-hook-generator`
- `/app/daily-viral-ideas`
- `/app/profile`
- `/app/privacy`
- `/app/copyright`
- `/app/billing`
- `/app/pricing`
- `/app/subscription`
- `/app/payment-history`
- `/app/downloads`, `/app/my-downloads`
- `/app/referrals`, `/dashboard/referrals`
- `/app/referral`, `/app/gift-cards`
- `/app/feature-requests`

### Admin routes intentionally not ported now

`/app/admin/*` contains many operational dashboards for analytics, users, monitoring, revenue, workers, security reports, audit logs, self-healing, and similar internal surfaces. These are not included in the native app because they are desktop-heavy admin workflows.

## Backend APIs found

The backend is a FastAPI monolith mounted primarily under `/api`.

### Mobile-relevant groups

- Auth and profile: `/api/auth/register`, `/api/auth/login`, `/api/auth/me`, `/api/auth/profile`, `/api/auth/password`, `/api/auth/verify-email`, `/api/auth/resend-verification`, `/api/auth/forgot-password`, `/api/auth/reset-password`, `/api/auth/export-data`, `/api/auth/account`
- Credits and wallet: `/api/credits/balance`, `/api/credits/ledger`, `/api/wallet/me`, `/api/wallet/pricing`, `/api/wallet/jobs`, `/api/wallet/ledger`
- Pricing and subscriptions: `/api/pricing-catalog/plans`, `/api/pricing/plans`, `/api/cashfree/products`, `/api/cashfree/create-order`, `/api/cashfree/verify`, `/api/cashfree/payments/history`, `/api/subscriptions/*`
- Story video: `/api/story-engine/create`, `/api/story-engine/status/{job_id}`, `/api/story-engine/user-jobs`, `/api/story-engine/preview/{job_id}`, `/api/story-engine/share-link/{job_id}`
- Story series: `/api/story-series/create`, `/api/story-series/my-series`, `/api/story-series/{series_id}`, `/api/story-series/{series_id}/generate-episode`, `/api/story-series/{series_id}/share`
- Character memory: `/api/characters/create`, `/api/characters/my-characters`, `/api/characters/{character_id}`, `/api/characters/{character_id}/memory`
- Reels and stories: `/api/generate/reel`, `/api/generate/story`, `/api/generate/story/async`, `/api/generate/{id}`, `/api/generate/history`
- Photo trailer: `/api/photo-trailer/uploads/*`, `/api/photo-trailer/jobs`, `/api/photo-trailer/jobs/{job_id}`, `/api/photo-trailer/my-trailers`, `/api/photo-trailer/share/{slug}`
- Photo to comic: `/api/photo-to-comic/generate`, `/api/photo-to-comic/job/{job_id}`, `/api/photo-to-comic/history`, `/api/photo-to-comic/download/{job_id}`, `/api/photo-to-comic/my-chains`
- Comic storybook: `/api/comic-storybook-v2/genres`, `/api/comic-storybook-v2/preview`, `/api/comic-storybook-v2/generate`, `/api/comic-storybook-v2/job/{job_id}`, `/api/comic-storybook-v2/download/{job_id}`, `/api/comic-storybook-v2/history`
- Bedtime stories: `/api/bedtime-story-builder/config`, `/api/bedtime-story-builder/generate`, `/api/bedtime-story-builder/export`
- Reaction GIF: `/api/reaction-gif/reactions`, `/api/reaction-gif/pricing`, `/api/reaction-gif/generate`, `/api/reaction-gif/job/{job_id}`, `/api/reaction-gif/history`, `/api/reaction-gif/download/{job_id}`
- Brand story: `/api/brand-story-builder/config`, `/api/brand-story-builder/generate`, `/api/brand-story-builder/job/{job_id}`, `/api/brand-story-builder/job/{job_id}/result`
- Daily viral ideas: `/api/viral-ideas/daily-feed`, `/api/viral-ideas/generate-bundle`, `/api/viral-ideas/jobs/{job_id}`, `/api/viral-ideas/my-jobs`
- Downloads and media: `/api/downloads/my-downloads`, `/api/downloads/{download_id}/url`, `/api/media/*`, `/api/protected-download/*`
- Share: `/api/share/*`, `/api/public/*`
- Help/support/privacy: `/api/help/manual`, `/api/help/search`, `/api/feedback/*`, `/api/feature-requests/*`, `/api/privacy/*`, `/api/security/report`
- Notifications/realtime: `/api/notifications/*`, `/api/push/*`, `/api/sse/jobs`, `/ws/progress`

## Features found

The web feature source of truth is `frontend/src/data/creatorTools.js`:

- Story Video
- Story Series
- My Movie Trailer / Photo Trailer
- Character Memory
- Reel Generator
- Photo to Comic
- Comic Storybook
- Bedtime Stories
- Reaction GIF
- Brand Story
- Daily Viral Ideas

Additional user-facing surfaces include auth, dashboard, create hub, My Space/library, video preview/result, share/download, credits wallet, pricing/subscriptions/payments, profile/settings/privacy, help/support/contact, legal pages, referrals, downloads, and public share routes.

## Mobile screens needed

- Auth stack: login, signup, verify email, forgot password
- Main tabs: Home, Create, Library, Wallet, Profile
- Tool screens for every creator feature listed above
- Result screen with video playback, status polling, share, copy link, and download actions
- Story Series list/detail/create entry
- Character Memory list/create/detail entry
- Credits wallet and ledger
- Pricing/subscription screen
- Mobile payment handoff screen
- Profile/settings/privacy/account screen
- Help/support/contact screen
- Legal pages for privacy, terms, cookies, and security
- Offline, empty, loading, and error states
- Push notification registration placeholder
- Deep link entry handling

## Features to port now

- Expo project setup with TypeScript, Expo Router, NativeWind, React Query, SecureStore, EAS config, and deep link configuration
- JWT auth persistence and API service layer
- Core shell/navigation/theme
- Login/signup/verify/forgot-password flows
- Dashboard/create/library/wallet/profile tabs
- Mobile tool screens for all requested creator tools
- Generic async job result screen with video-player support and share/copy/download actions
- Pricing/payment placeholders connected to existing product APIs where available
- Help and legal screens

## Features to defer

- Admin dashboards under `/app/admin/*`
- Native Cashfree SDK or App Store / Play Store in-app purchase production flow
- Native Google/Apple OAuth until mobile OAuth client IDs and redirect URIs are configured
- Native push backend because the current backend exposes Web Push/VAPID, not Expo/FCM/APNS token registration
- Fully native media upload UX for photo-heavy tools until file picker/camera permissions and multipart contracts are validated against each endpoint
- Offline job queue/retry sync beyond clear offline states

## Risk areas

- Long-running generation must use async jobs and polling; sync web flows can exceed mobile/network timeouts.
- Some web APIs expect browser-only integrations such as reCAPTCHA, web Cashfree checkout, and Google web OAuth.
- Token refresh is not present; the backend issues long-lived JWTs.
- Several backend route groups share prefixes or have duplicate mounts, so the mobile API layer uses explicit paths.
- Native media downloads need entitlement-aware URLs and file permissions per platform.
- Push notifications require new native token registration endpoints.
- Deep links need App/Universal Link domain verification before production.

## Implementation phases

### Phase 1: Project setup, navigation, theme, auth

- Add isolated Expo app in `mobile/`.
- Configure Expo Router, NativeWind, React Query, SecureStore, EAS, deep links, and dark cinematic theme.
- Implement auth provider, token persistence, API client, login, signup, email verification, and forgot password.

### Phase 2: Core generation flows

- Add one mobile tool screen pattern for all creator tools.
- Use existing endpoints where contracts are clear.
- Add explicit TODOs instead of fake integrations where native upload/payment/OAuth gaps exist.

### Phase 3: Video result, library, share

- Add library screen backed by story jobs/download APIs.
- Add result screen with polling, video support, copy link, share, and download hooks.

### Phase 4: Credits, pricing, payments

- Add wallet and pricing screens backed by credits/wallet/pricing/product APIs.
- Add mobile payment handoff screen with TODOs for native Cashfree/IAP decisions.

### Phase 5: Remaining creator tools

- Cover Story Series, Character Memory, Reel Generator, Photo to Comic, Comic Storybook, Bedtime Stories, Reaction GIF, Brand Story, and Daily Viral Ideas using the common screen and API metadata.

### Phase 6: Polish, testing, build readiness

- Add typecheck script, EAS config, env example, reusable state components, offline handling, and production-ready folder architecture.
