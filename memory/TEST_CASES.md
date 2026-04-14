# Visionary Suite — Complete End-to-End Test Cases

**App URL**: https://trust-engine-5.preview.emergentagent.com
**Test User**: test@visionary-suite.com / Test@2026#
**Fresh User**: fresh@test-overlay.com / Fresh@2026#
**Admin User**: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

---

## 1. AUTHENTICATION & ACCOUNT MANAGEMENT

### 1.1 Email Registration
| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 1.1.1 | Positive | Register with valid name, email, password (8+ chars, uppercase, number, special) | Account created, redirect to /app, welcome toast |
| 1.1.2 | Negative | Register with already registered email | Error: "Email already registered" |
| 1.1.3 | Negative | Register with password < 8 characters | Validation error shown |
| 1.1.4 | Negative | Register with empty name field | Validation error shown |
| 1.1.5 | Negative | Register with invalid email format (no @, no domain) | Validation error shown |
| 1.1.6 | Negative | Register with same IP more than 2 times/month | Error: "Maximum accounts per IP exceeded" |
| 1.1.7 | Positive | Register and check initial credits (should be 50) | Credits = 50 on dashboard |

### 1.2 Email Login
| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 1.2.1 | Positive | Login with valid test@visionary-suite.com / Test@2026# | Redirects to /app dashboard |
| 1.2.2 | Negative | Login with wrong password | Error toast: "Invalid credentials" |
| 1.2.3 | Negative | Login with non-existent email | Error toast: "Invalid credentials" |
| 1.2.4 | Negative | Login with empty email/password | Validation error, submit disabled |
| 1.2.5 | Positive | Login and verify JWT token stored in localStorage | localStorage.token exists |
| 1.2.6 | Positive | Login with return URL parameter (?return=/app/story-battle/xxx) | Redirects to the return URL after login |
| 1.2.7 | Negative | Login with locked account (brute force) | Error: "Account locked" message |

### 1.3 Google Sign-In
| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 1.3.1 | Positive | Click "Sign in with Google" → complete OAuth popup | Redirects to /app, user created/logged in |
| 1.3.2 | Negative | Click Google button → close popup mid-flow | Toast: "Google sign-in was cancelled", button re-enabled |
| 1.3.3 | Negative | Click Google button rapidly 3 times | Only 1 popup opens (button disabled after first click) |
| 1.3.4 | Positive | Google sign-in on /signup page | Same flow, "Sign up with Google" text |
| 1.3.5 | Negative | Google returns invalid token | Toast: error message from backend, no stuck loader |
| 1.3.6 | Positive | Existing Google user logs in again | Logs in (doesn't create duplicate account) |
| 1.3.7 | Positive | Google loading overlay shows during token exchange | "Signing you in..." spinner visible |

### 1.4 Password Management
| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 1.4.1 | Positive | Click "Forgot Password" → enter valid email → submit | Success message: "Reset email sent" |
| 1.4.2 | Negative | Forgot password with non-existent email | Error or generic "If account exists, email sent" |
| 1.4.3 | Positive | Reset password with valid token + new password | Password changed, can login with new password |
| 1.4.4 | Negative | Reset password with expired/invalid token | Error: "Invalid or expired token" |
| 1.4.5 | Positive | Change password from profile (old + new password) | Success, old password stops working |
| 1.4.6 | Negative | Change password with wrong current password | Error: "Current password is incorrect" |

### 1.5 Session & Auth Guards
| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 1.5.1 | Positive | Access /app while logged in | Dashboard loads |
| 1.5.2 | Negative | Access /app while logged out | Redirects to /login |
| 1.5.3 | Negative | Access /app/story-battle/:id while logged out | Redirects to /login |
| 1.5.4 | Positive | Access /login while already logged in | Redirects to /app |
| 1.5.5 | Positive | Logout (clear localStorage) → access /app | Redirects to /login |
| 1.5.6 | Positive | Token persists across page refresh | Still authenticated after F5 |

---

## 2. LANDING PAGE (Public — /)

| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 2.1 | Positive | Open landing page (/) | Loads with hero, showcase grid, stats, live activity |
| 2.2 | Positive | Showcase grid shows story cards with images | At least 5+ cards with real thumbnails |
| 2.3 | Positive | Public stats load (creators, videos created) | Numbers displayed (e.g., "36 creators, 64 videos") |
| 2.4 | Positive | Live activity section shows recent stories | "Happening now" section with story titles |
| 2.5 | Positive | CTA buttons navigate to /signup or /login | Correct navigation |
| 2.6 | Positive | Navigation links (Gallery, Explore, Pricing, About) work | Each loads correct page |
| 2.7 | Positive | Mobile responsive layout | Hero stacks, cards resize, no overflow |
| 2.8 | Negative | Landing page with slow network | Skeleton/loader shows, content loads progressively |

---

## 3. DASHBOARD (/app) — Battle-First Layout

### 3.1 Dashboard Loading
| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 3.1.1 | Positive | Login → Dashboard loads within 3s | Hero, QuickActions, Feed all visible |
| 3.1.2 | Positive | Dashboard makes consolidated API call (/api/dashboard/init) | Single init request + feed request (2 total, not 7) |
| 3.1.3 | Positive | Repeat visit (navigate to /app) loads faster | < 2s with cached data |
| 3.1.4 | Positive | Skeleton/loading state shows before content | Shimmer/skeleton visible during load |

### 3.2 LiveBattleHero Component
| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 3.2.1 | Positive | Hero shows live battle with #1 entry autoplay video | Video plays automatically, muted |
| 3.2.2 | Positive | Hero shows user rank ("You're #6"), watching count, competing count | Stats visible and accurate |
| 3.2.3 | Positive | "Take #1 Spot" CTA navigates to /app/story-battle/{rootId} | Navigates to battle page (NOT paywall) |
| 3.2.4 | Positive | "Post in 10 Seconds" CTA triggers Quick Shot flow | For paid user: fires API → navigate to studio. For free-exhausted: paywall modal |
| 3.2.5 | Positive | "Think you can beat this?" overlay on video preview | Clicking navigates to battle page |
| 3.2.6 | Positive | Credit-aware micro-copy shows for free-exhausted user | "Entry requires credits · View the battle first, then decide" |
| 3.2.7 | Positive | Credit-aware micro-copy for user with free entries | "X free entries left · Fastest way to climb right now" |
| 3.2.8 | Positive | Hero polls battle pulse every 12-18s | Network requests visible, rank updates live |
| 3.2.9 | Negative | No active battle exists | Hero shows graceful fallback state |
| 3.2.10 | Positive | #1 entry shows title, creator name, points | All metadata displayed correctly |

### 3.3 QuickActions ("Choose Your Path")
| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 3.3.1 | Positive | "Enter Battle Instantly" (primary, spans 2 cols) visible with badge | "Fastest path to the leaderboard" badge, violet border |
| 3.3.2 | Positive | Click "Enter Battle Instantly" (free-exhausted user) | Paywall modal opens via show-battle-paywall event |
| 3.3.3 | Positive | Click "Enter Battle Instantly" (user with credits) | Quick Shot API fires → navigate to studio with progress |
| 3.3.4 | Positive | "Write Your Own Story" navigates to /app/story-video-studio | Fresh blank studio (no Recent Videos sidebar) |
| 3.3.5 | Positive | "Beat the Leader" navigates to /app/story-battle/{rootId} | Battle leaderboard page loads (NOT studio) |
| 3.3.6 | Negative | "Write Your Own Story" and "Beat the Leader" go to DIFFERENT URLs | URLs must differ — this is a critical test |
| 3.3.7 | Positive | "Beat the Leader" shows dynamic #1 entry title | "See who's #1: [title]. Think you can do better?" |
| 3.3.8 | Positive | Credit indicator on "Enter Battle Instantly" shows pre-click | "Credits required" or "X free entries left" |
| 3.3.9 | Positive | Section title = "Choose Your Path" | Correct heading visible |

### 3.4 Trending Feed ("Trending Now")
| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 3.4.1 | Positive | Feed shows diverse story cards (different titles, styles) | At least 4 different titles/themes visible |
| 3.4.2 | Positive | Cards show real thumbnails (not blank dark boxes) | Poster images or gradient fallback with title |
| 3.4.3 | Positive | Cards show LIVE badges, hook text, view/share counts | Metadata overlays visible |
| 3.4.4 | Positive | Click on feed card navigates to /app/story-viewer/{jobId} | Story viewer loads |
| 3.4.5 | Positive | Feed images lazy load (below-the-fold) | `loading="lazy"` on img elements |
| 3.4.6 | Negative | Story with no thumbnail | Gradient fallback with title + animation style text |
| 3.4.7 | Positive | Feed autoplay video preview on scroll (IntersectionObserver) | Video plays at 60% visibility, pauses on scroll-out |

### 3.5 PostValueOverlay
| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 3.5.1 | Positive | First visit to dashboard | Overlay does NOT appear (suppressed) |
| 3.5.2 | Positive | Second visit to dashboard (after navigating away) | Overlay may appear if user has generations |
| 3.5.3 | Positive | Click "Continue with limited access" | Overlay dismissed |
| 3.5.4 | Negative | User with 0 generations | Overlay never appears |

### 3.6 BattlePaywallModal
| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 3.6.1 | Positive | Triggered by show-battle-paywall event | Modal opens with pricing tiers |
| 3.6.2 | Positive | Shows user's rank, competing count, credits | Context data accurate |
| 3.6.3 | Positive | Shows 3 pricing tiers (₹29/₹49/₹149) | All packs visible with descriptions |
| 3.6.4 | Positive | Close modal | Closes without navigation change |
| 3.6.5 | Positive | Select a pack → Cashfree payment flow | Payment SDK initiates (or sandbox mode activates) |

---

## 4. STORY VIDEO STUDIO (/app/story-video-studio)

### 4.1 Fresh Session Entry
| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 4.1.1 | Positive | Navigate via "Write Your Own Story" CTA | Blank studio, empty title/text, NO "Recent Videos" sidebar |
| 4.1.2 | Positive | Navigate via URL directly | Studio loads (may show Recent Videos) |
| 4.1.3 | Positive | Resume Draft modal appears (if draft exists) | "Resume your last draft?" with Continue/Start Fresh |
| 4.1.4 | Positive | Click "Continue" on resume modal | Draft content restored (title, text, style) |
| 4.1.5 | Positive | Click "Start Fresh" on resume modal | Empty form, draft discarded from DB |
| 4.1.6 | Negative | No existing draft | Resume modal does NOT appear |

### 4.2 Guided Start (Vibe Picker)
| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 4.2.1 | Positive | Fresh session + empty text → vibes appear | "What do you want to create?" with 4 pills |
| 4.2.2 | Positive | Click "Bedtime Magic" | Story text auto-fills with kids story idea, toast shown |
| 4.2.3 | Positive | Click "Emotional Story" | Story text auto-fills with emotional idea |
| 4.2.4 | Positive | Click "Mind-Blowing Twist" | Story text auto-fills with thriller idea |
| 4.2.5 | Positive | Click "1M Views Hook" | Story text auto-fills with viral idea |
| 4.2.6 | Positive | Click "Random Idea" | Story text auto-fills with random category idea |
| 4.2.7 | Positive | Click "Use Sample" | Title + Story text pre-filled with editable sample |
| 4.2.8 | Positive | After text is entered, vibes disappear | Vibe picker hidden once text exists |
| 4.2.9 | Negative | Not in fresh session → vibes don't appear | Guided start hidden |

### 4.3 Story Creation Form
| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 4.3.1 | Positive | Fill title (3-100 chars) + story text (50+ chars) + select style | Form valid, Generate button enabled |
| 4.3.2 | Negative | Story text < 50 characters | "need X more" indicator, Generate disabled |
| 4.3.3 | Negative | Title empty | Validation error on submit |
| 4.3.4 | Positive | Select animation style (watercolor, cartoon_2d, anime_style, etc.) | Style selected, visual indicator |
| 4.3.5 | Positive | Select age group (kids_5_8, tweens_9_12, teens_13_plus) | Age group set |
| 4.3.6 | Positive | Select voice preset (narrator_warm, narrator_dramatic, etc.) | Voice preset set |
| 4.3.7 | Positive | Select quality mode (fast, balanced) | Mode set |

### 4.4 Draft Persistence
| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 4.4.1 | Positive | Type title + text → wait 3s → refresh page | Draft saved, resume modal shows on return |
| 4.4.2 | Positive | Draft auto-saves only when content changes (debounced) | No save on identical content |
| 4.4.3 | Positive | Generate story → draft marked "processing" (not deleted) | Draft status = "processing" in DB |
| 4.4.4 | Positive | Generation succeeds → draft marked "completed" | Draft status = "completed" |
| 4.4.5 | Positive | Generation FAILS → draft reverts to "draft" | Draft recovered, can resume |
| 4.4.6 | Positive | Click "Start Fresh" on resume → draft discarded | Draft deleted from DB |

### 4.5 Navigation Guard
| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 4.5.1 | Positive | Type 20+ chars → try to close/refresh browser tab | Browser "Leave site?" confirmation dialog |
| 4.5.2 | Negative | Type < 20 chars → close tab | No confirmation dialog |
| 4.5.3 | Positive | In processing phase → no guard | No dialog (draft already saved) |

### 4.6 Recent Drafts Panel
| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 4.6.1 | Positive | Fresh session + type 20+ chars → Recent Drafts appears | Collapsed panel with "Your unfinished stories are waiting" |
| 4.6.2 | Positive | Expand Recent Drafts | Shows max 3 items with title, date, status badge |
| 4.6.3 | Positive | Status badges: Draft (amber), Rendering (blue), Ready (green) | Correct colors/labels |
| 4.6.4 | Positive | Click a "Ready" item → navigates to that project | Opens /app/story-video-studio?projectId={id} |
| 4.6.5 | Negative | No recent items | Panel does not appear |
| 4.6.6 | Negative | Fresh session + < 20 chars typed | Panel hidden |

### 4.7 Story Generation Pipeline
| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 4.7.1 | Positive | Click Generate → pipeline starts | Phase transitions: input → processing, progress UI shown |
| 4.7.2 | Positive | Pipeline stages visible: Planning → Keyframes → Scene Clips → Audio → Assembly | Each stage reflected in UI |
| 4.7.3 | Positive | Generation completes → video plays | Phase = postgen, video player visible |
| 4.7.4 | Negative | Insufficient credits | 402 credit gate modal appears (inline) |
| 4.7.5 | Negative | Pipeline fails | Error state with retry option |
| 4.7.6 | Positive | Retry failed generation | Pipeline restarts |
| 4.7.7 | Positive | Rate limit check passes for normal user | Creation allowed if within limits |
| 4.7.8 | Negative | Rate limit exceeded (5+ videos in 10 min) | Error: "Please wait a few minutes" |
| 4.7.9 | Positive | Admin user bypasses rate limit and queue | Immediate processing, no QUEUED state |

### 4.8 Post-Generation Loop
| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 4.8.1 | Positive | After video ready → "Keep creating" section visible | 3 CTAs below video |
| 4.8.2 | Positive | "Make it 10x better?" → navigates to studio with remix context | Fresh studio with remixFrom state |
| 4.8.3 | Positive | "Not the vibe you wanted?" → navigates to studio with prefilled text | Same story text, can change style |
| 4.8.4 | Positive | "You're Rank #3 right now" → navigates to battle page | /app/story-battle/{rootId} loads |
| 4.8.5 | Positive | "Create Entirely New Story" → blank studio | Fresh session studio |
| 4.8.6 | Positive | Funnel events tracked for each CTA click | POST /api/funnel/track fires |

---

## 5. STORY BATTLE PAGE (/app/story-battle/:storyId)

| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 5.1 | Positive | Navigate to battle page with valid storyId | Leaderboard with ranked entries, scores, share CTA |
| 5.2 | Positive | #1 entry shows gold badge + "Share this battle" | Crown icon, share button visible |
| 5.3 | Positive | #2+ entries show "Take it back" prompt | Rose-colored rank indicator |
| 5.4 | Positive | Battle Pulse polls every 12s | Network requests visible, live updates |
| 5.5 | Positive | "Enter Battle" CTA → paywall check | Free user: enters directly. Exhausted user: paywall |
| 5.6 | Positive | Video autoplay for #1 contender | Video plays if output_url exists |
| 5.7 | Positive | Share button generates share link | Link copied to clipboard |
| 5.8 | Negative | Invalid storyId | Error state or redirect to /app |
| 5.9 | Positive | User's own entry highlighted | "is_mine" flag shows visual indicator |
| 5.10 | Positive | Competing count + viewer count shown | Real-time battle stats |

---

## 6. STORY VIEWER (/app/story-viewer/:jobId)

| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 6.1 | Positive | Navigate with valid jobId | Video player loads, story plays |
| 6.2 | Positive | Battle status banner shows rank/score | Rank badge visible if in battle |
| 6.3 | Positive | Share CTA visible | Share button works (copies link) |
| 6.4 | Positive | "Enter Battle" CTA (paywall-gated) | Free: enters. Exhausted: paywall modal |
| 6.5 | Negative | Invalid jobId | Error: "Story not found" |
| 6.6 | Positive | View count increments | total_views increases in DB |

---

## 7. QUICK SHOT (API-driven, no dedicated page)

| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 7.1 | Positive | Click Quick Shot (user with credits) | POST /api/stories/quick-shot → job created → redirect to studio |
| 7.2 | Negative | Click Quick Shot (free entries exhausted, no credits) | Paywall modal opens |
| 7.3 | Positive | Quick Shot generates AI story without user input | Story text auto-generated, pipeline starts |
| 7.4 | Negative | Quick Shot with no active battle (no root_story_id) | Fallback: redirect to fresh studio |

---

## 8. PAYMENT SYSTEM (Cashfree)

### 8.1 Payment Flow
| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 8.1.1 | Positive | Select credit pack in paywall → create order | POST /api/cashfree/create-order returns order_id |
| 8.1.2 | Positive | Complete Cashfree payment → verify | POST /api/cashfree/verify → credits added |
| 8.1.3 | Positive | After payment → credits visible on dashboard | Credit count updated |
| 8.1.4 | Negative | Payment fails/cancelled | Error toast, no credits added, can retry |
| 8.1.5 | Positive | Payment webhook received | Credits delivered even if verify call fails |
| 8.1.6 | Positive | Payment history visible | GET /api/cashfree/payments/history returns orders |

### 8.2 Free Entry Limit
| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 8.2.1 | Positive | New user gets 3 free battle entries | battle-entry-status: free_remaining = 3 |
| 8.2.2 | Positive | After 3 entries + 0 credits → needs_payment = true | Paywall triggers on next action |
| 8.2.3 | Positive | After payment → entries available again | needs_payment = false |

---

## 9. FIRST-TIME USER ONBOARDING

| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 9.1 | Positive | Fresh user first login → onboarding overlay appears | "Create your first AI story in 10 seconds" |
| 9.2 | Positive | Click X (close button) → overlay dismissed | Dashboard visible, onboarding_dismissed in localStorage |
| 9.3 | Positive | Click "Skip for now" → overlay dismissed | Same as X close behavior |
| 9.4 | Positive | Click "Start Now" → navigate to studio | /app/story-video-studio with freshSession |
| 9.5 | Positive | Reload after dismiss → overlay does NOT reappear | Persisted via localStorage |
| 9.6 | Negative | User with 1+ generations → overlay never shows | Suppressed for returning users |
| 9.7 | Negative | Admin user → overlay never shows | Suppressed for admin role |
| 9.8 | Positive | Progress indicator shows "Step 1 of 5" | Visual progress bar visible |

---

## 10. PERFORMANCE

| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 10.1 | Positive | First login → dashboard load time | < 3s (target < 2.5s) |
| 10.2 | Positive | Repeat visit (navigate to /app) | < 2s |
| 10.3 | Positive | Landing page cold load | < 2s |
| 10.4 | Positive | Route-level code splitting active | Only critical JS loaded initially (not admin/studio/tools) |
| 10.5 | Positive | Lazy-loaded page shows loading spinner during chunk fetch | PageLoader spinner visible briefly |
| 10.6 | Positive | Feed scroll smooth | No jank, lazy images load on scroll |
| 10.7 | Positive | Dashboard consolidated API (/api/dashboard/init) | Returns feed + challenge + leaderboard in 1 call |
| 10.8 | Positive | API responses compressed (gzip) | Content-Encoding: gzip header present |
| 10.9 | Positive | TTL cache on hottest-battle and feed endpoints | Second call within 15s returns cached data (faster) |
| 10.10 | Negative | Slow 4G simulation | Content loads progressively, no blank screens |

---

## 11. FEED & DISCOVERY APIs

| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 11.1 | Positive | GET /api/stories/feed/discover?limit=8&sort_by=trending | Returns 8 stories sorted by battle_score desc |
| 11.2 | Positive | GET /api/stories/feed/discover?sort_by=latest | Returns stories sorted by created_at desc |
| 11.3 | Positive | GET /api/stories/feed/discover?sort_by=most_continued | Returns stories sorted by total_children desc |
| 11.4 | Positive | Pagination: offset=0&limit=4, then offset=4&limit=4 | Different stories in each page, has_more flag correct |
| 11.5 | Positive | Stories include preview_media (poster_url, preview_url) | Media URLs present for generated stories |
| 11.6 | Negative | is_seed_content: true stories excluded from feed | Seed-flagged stories don't appear |
| 11.7 | Positive | Feed returns total count | total field matches actual count |

---

## 12. BATTLE SYSTEM APIs

| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 12.1 | Positive | GET /api/stories/hottest-battle | Returns battle with root_title, contenders[3], branch_count |
| 12.2 | Positive | Contenders include output_url + thumbnail_url | Video URLs present for generated entries |
| 12.3 | Positive | GET /api/stories/battle-entry-status | Returns needs_payment, free_remaining, credits |
| 12.4 | Positive | GET /api/stories/battle/{storyId} | Returns full battle with all branches, ranked |
| 12.5 | Positive | GET /api/stories/battle-pulse/{rootId} | Returns live pulse with top_3, total entries, watching |
| 12.6 | Positive | Pulse includes output_url/thumbnail_url for contenders | Video data in pulse response |
| 12.7 | Positive | POST /api/stories/quick-shot | Creates new story entry in battle |
| 12.8 | Negative | Quick shot with insufficient credits | 402 error |
| 12.9 | Positive | POST /api/stories/continue-branch | Creates branch entry linked to root |

---

## 13. DRAFT SYSTEM APIs

| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 13.1 | Positive | POST /api/drafts/save (title + story_text) | Draft saved/updated, success: true |
| 13.2 | Positive | GET /api/drafts/current | Returns active draft with content |
| 13.3 | Positive | POST /api/drafts/status {status: "processing"} | Draft state transitions to processing |
| 13.4 | Positive | POST /api/drafts/status {status: "completed"} | Draft state transitions to completed |
| 13.5 | Positive | POST /api/drafts/status {status: "draft"} (failure recovery) | Draft reverts from processing to draft |
| 13.6 | Positive | DELETE /api/drafts/discard | Active draft deleted |
| 13.7 | Positive | GET /api/drafts/recent | Returns max 3 items (draft + recent projects) |
| 13.8 | Positive | GET /api/drafts/idea | Returns random story idea |
| 13.9 | Positive | GET /api/drafts/idea?vibe=kids | Returns kids category idea |
| 13.10 | Positive | GET /api/drafts/idea?vibe=thriller | Returns thriller category idea |
| 13.11 | Negative | GET /api/drafts/current with no draft | Returns {draft: null} |
| 13.12 | Negative | GET /api/drafts/current (draft with empty title AND text) | Returns {draft: null} (filtered) |

---

## 14. FUNNEL TRACKING & ANALYTICS

| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 14.1 | Positive | POST /api/funnel/track with valid event | Event stored in funnel_events collection |
| 14.2 | Positive | Events include device_type, traffic_source, has_preview | Segmented data stored |
| 14.3 | Positive | CTA clicks fire funnel events | Each button click tracked with type |
| 14.4 | Positive | Battle paywall viewed → tracked | battle_paywall_viewed event in DB |
| 14.5 | Positive | Payment success → tracked | battle_payment_success event in DB |

---

## 15. PUSH NOTIFICATIONS

| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 15.1 | Positive | Rank drop triggers push notification | Notification sent to dropped users |
| 15.2 | Positive | WIN event triggers share prompt | Persistent share CTA |
| 15.3 | Positive | Push prompt appears in BattlePulse | Notification permission request shown |
| 15.4 | Negative | User denies push permission | Graceful fallback, no repeated prompts |

---

## 16. PUBLIC PAGES

| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 16.1 | Positive | /pricing loads | Pricing plans visible |
| 16.2 | Positive | /about loads | Founder Authority Block + about content |
| 16.3 | Positive | /gallery loads | Public gallery of stories |
| 16.4 | Positive | /explore loads | Explore/discovery feed |
| 16.5 | Positive | /share/:shareId loads | Shared story visible (public) |
| 16.6 | Positive | /v/:slug loads | Public creation page |
| 16.7 | Positive | /creator/:username loads | Creator profile page |
| 16.8 | Positive | /blog loads | Blog listing |
| 16.9 | Positive | /privacy-policy, /terms, /cookie-policy load | Legal pages render |
| 16.10 | Positive | /user-manual or /help loads | Help documentation |

---

## 17. USER PROFILE & SETTINGS

| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 17.1 | Positive | GET /api/auth/me returns user data | Name, email, credits, role |
| 17.2 | Positive | PUT /api/auth/profile updates name | Name updated |
| 17.3 | Positive | /app/profile page loads | Profile editing form |
| 17.4 | Positive | /app/billing page loads | Credit balance + payment history |
| 17.5 | Positive | /app/history page loads | Generation history |
| 17.6 | Positive | /app/my-stories page loads | User's created stories |
| 17.7 | Positive | Export data (GET /api/auth/export-data) | Returns user data export |
| 17.8 | Positive | Delete account (DELETE /api/auth/account) | Account deleted |

---

## 18. ADMIN FUNCTIONALITY

| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 18.1 | Positive | Login as admin → /app/admin loads | Admin dashboard with analytics |
| 18.2 | Positive | Admin sees unlimited credits | Credits display shows unlimited |
| 18.3 | Positive | Admin can view all users (/app/admin/users) | User management list |
| 18.4 | Positive | Admin can adjust user credits | PUT /api/admin/users/{id}/credits works |
| 18.5 | Positive | Admin bypasses rate limiting | Can create unlimited stories |
| 18.6 | Positive | Admin bypasses abuse detection | No "submitted several videos" error |
| 18.7 | Positive | Admin bypasses queue (no QUEUED state) | Jobs start immediately |
| 18.8 | Positive | Admin analytics dashboard shows metrics | Revenue, users, conversions |
| 18.9 | Positive | Admin can trigger backfill previews | POST /api/stories/admin/backfill-previews works |

---

## 19. FEATURE FLAGS

| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 19.1 | Positive | draftPersistenceV2 = true → draft auto-save works | Drafts saved on content change |
| 19.2 | Positive | postGenerationLoop = true → loop CTAs visible after generation | 3 CTAs appear below video |
| 19.3 | Positive | recentDraftsPanel = true → panel appears after 20+ chars | Collapsed drafts panel visible |
| 19.4 | Positive | guidedStartV2 = true → vibe picker shows | Category pills visible in fresh session |
| 19.5 | Negative | If flag is false → feature hidden | Component not rendered |

---

## 20. CODE SPLITTING & LAZY LOADING

| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 20.1 | Positive | Landing page loads only critical JS (not admin/studio) | Network tab shows small initial bundle |
| 20.2 | Positive | Navigate to /app/story-video-studio → lazy chunk loads | Additional JS chunk fetched on navigation |
| 20.3 | Positive | Navigate to /app/admin → admin chunk loads | Admin code not in initial bundle |
| 20.4 | Positive | PageLoader spinner shows during chunk loading | "Loading..." spinner visible briefly |
| 20.5 | Negative | Navigate to non-existent route | Redirects to / or /app (catch-all) |

---

## 21. MOBILE RESPONSIVENESS

| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 21.1 | Positive | Dashboard on 390px viewport | Hero stacks, QuickActions stack vertically |
| 21.2 | Positive | QuickActions primary card full-width on mobile | No horizontal overflow |
| 21.3 | Positive | Feed cards resize on mobile | Cards stack/grid adjusts |
| 21.4 | Positive | Studio form on mobile | Textarea full-width, buttons accessible |
| 21.5 | Positive | Login/Signup on mobile | Form fits, Google button full-width |
| 21.6 | Positive | Battle page on mobile | Leaderboard stacks, CTAs accessible |
| 21.7 | Positive | Close/Skip buttons have 40px+ touch targets | Tappable on mobile |

---

## 22. ERROR HANDLING & EDGE CASES

| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 22.1 | Negative | API returns 500 on dashboard init | Error toast, partial content loads |
| 22.2 | Negative | Network disconnects during story generation | Generation continues server-side, reconnect shows progress |
| 22.3 | Negative | Expired JWT token → API call | 401 → redirect to login |
| 22.4 | Negative | MongoDB connection drops | Graceful error messages, not raw stack traces |
| 22.5 | Negative | Cashfree payment timeout | User informed, can retry |
| 22.6 | Negative | FFmpeg not installed (container restart) | FAILED_RENDER state, retry option |
| 22.7 | Negative | LLM budget exceeded | Story fails with clear error message |
| 22.8 | Negative | Invalid story content (safety filter) | Content rewritten or error with explanation |
| 22.9 | Negative | Concurrent duplicate requests | Deduplicated, no double-charge |
| 22.10 | Positive | ErrorBoundary catches React crash in studio | Fallback UI instead of white screen |

---

## 23. COOKIE CONSENT & LEGAL

| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 23.1 | Positive | First visit shows cookie consent banner | Banner appears at bottom |
| 23.2 | Positive | Accept cookies → banner dismissed | Banner hidden, preference stored |
| 23.3 | Positive | Cookie preference persists across sessions | Banner doesn't reappear |

---

## 24. SHARING & VIRAL

| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 24.1 | Positive | Share battle link → /share/:shareId loads | Public share page with battle context |
| 24.2 | Positive | Viral pack share → /viral/:jobId loads | Viral share page |
| 24.3 | Positive | Share button copies link to clipboard | "Link copied" toast |
| 24.4 | Positive | WIN share prompt is persistent and unmissable | Crown icon, share CTA stays visible |

---

## 25. CONTENT SEEDING VALIDATION

| # | Type | Test Case | Expected Result |
|---|------|-----------|-----------------|
| 25.1 | Positive | Feed shows 5+ different story titles/themes | No content repetition |
| 25.2 | Positive | Top stories have real video thumbnails | No blank/gradient cards for seeded content |
| 25.3 | Positive | Battle contenders have output_url | Autoplay hero has real video |
| 25.4 | Positive | View counts and scores look realistic | 80-890 views, 60-200 scores |
| 25.5 | Positive | Multiple animation styles represented | watercolor, cartoon, cinematic, anime, comic |

---

## TOTAL: 25 categories, ~200 test cases
