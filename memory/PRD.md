# Story Universe Engine — Product Requirements Document

## Original Problem Statement
Build a "Story Universe Engine" — a full-stack AI creator suite with a behavior-driven growth engine, monetization, and viral sharing.

## Core Architecture
- Frontend: React (CRA + Craco) on port 3000
- Backend: FastAPI on port 8001
- Database: MongoDB (creatorstudio_production)
- Storage: Cloudflare R2
- Payments: Cashfree
- AI: OpenAI GPT-4o-mini, Sora 2, TTS + Gemini 3 via Emergent LLM Key

## Reel Creation Engine (BUILT Mar 31 2026) — P0 COMPLETE

### Before vs After

**BEFORE**: Simple "Generate Reel Script" page with 6 basic inputs (Topic, Niche, Tone, Duration, Language, Goal). Output was a single scrollable list of hooks, script, captions, hashtags. Generic results with no platform optimization. "Quick Variations" were weak text rewrites. "Generate Video" was a vague black-box button.

**AFTER**: Full "Reel Engine" with 12 outcome-driven controls, structured 7-tab output, video generation configurator, 8 performance-focused variations, and AI recommendations.

### New Input Controls
| Control | Options | Why It Matters |
|---------|---------|----------------|
| Platform | Instagram, YouTube Shorts, TikTok, Facebook | Platform-native optimization |
| Hook Style | Curiosity, Shock, Emotional, Luxury, Educational, Story, FOMO, Problem-Solution | Controls psychological trigger |
| Reel Format | Talking Head, Faceless, Voiceover, Cinematic, Slideshow, UGC Ad, Meme, Story | Matches creator's production style |
| CTA Type | Follow, Save, Comment, Buy, DM, Share | Aligns output with desired action |
| Objective | Followers, Engagement, Sales, Leads, Education, Retention | Outcome-driven generation |
| Output Type | Script Only, Script+Caption, Script+Visual Prompts, Full Video Plan | Controls output depth |
| Advanced: Niche, Tone, Duration, Language, Audience | Collapsible section | Reduces friction for quick starts |

### Structured Output Tabs
| Tab | Content | User Outcome |
|-----|---------|-------------|
| Script | Scene-by-scene with on-screen text, voiceover, visual direction, b-roll, retention notes | Complete filming guide |
| Hook Variants | 5 hooks with different triggers + "Top Performer" highlight, copy buttons | A/B testing hooks |
| Caption | Short + Long captions, platform-optimized | Ready-to-post copy |
| Hashtags | 20 trending hashtags, clickable chips, "Copy All" | Discovery optimization |
| Shot List | Numbered shots with type, duration, notes | Production checklist |
| Visual Prompts | Scene-by-scene AI image/video generation prompts | Direct input for AI tools |
| Voiceover | Full flowing voiceover script | Voice recording guide |

### Video Generation Config
Before generating video, user sees modal with:
- Video Style (AI / Stock / Mixed / Avatar)
- Voiceover ON/OFF toggle
- Subtitles ON/OFF toggle
- Aspect Ratio (9:16 / 16:9 / 1:1)
- Quality Mode (Fast / High Quality)
- Estimated Credits display
Note: Video generation shows "coming soon" toast — actual video pipeline uses Story Video Studio.

### Performance Variations (replaces old "Quick Variations")
| Variation | What It Does |
|-----------|-------------|
| Stronger Hook | Rewrites with more scroll-stopping hook |
| Higher Retention | Adds pattern interrupts, cliffhangers |
| More Emotional | Injects storytelling, vulnerability |
| More Viral | Optimizes for shareability, trending formats |
| More Sales-focused | Sharpens CTA and value proposition |
| Shorter & Punchier | Cuts filler, compresses script |
| Better CTA | Rewrites CTA with urgency and natural feel |
| Platform Optimized | Tailors to selected platform's best practices |

### AI Recommendations Panel
Shows after generation:
- Best hook type for topic
- Recommended duration
- Suggested posting time
- Emotional trigger
- Retention strategy

### Backend Changes
- `GenerateReelRequest` schema: Added `platform`, `hookStyle`, `reelFormat`, `ctaType`, `outputType`, `audience`
- `REEL_USER_PROMPT_TEMPLATE`: Completely rewritten for outcome-driven, platform-specific generation
- `REEL_SYSTEM_PROMPT`: Upgraded to "content strategist" role
- Output JSON: Now includes `shot_list[]`, `visual_prompts[]`, `voiceover_full`, `ai_recommendations{}`

### Files Changed
| File | Change |
|------|--------|
| `frontend/src/pages/ReelGenerator.js` | Complete rewrite — new controls, tabbed output, video config modal, performance variations, AI recommendations |
| `backend/models/schemas.py` | Added 6 new fields to GenerateReelRequest |
| `backend/shared.py` | Upgraded REEL_SYSTEM_PROMPT and REEL_USER_PROMPT_TEMPLATE |
| `backend/routes/generation.py` | Updated prompt template call to pass new fields |

## Premium Login UX (VERIFIED Mar 31 2026)
- Full-screen branded overlay masks auth.emergentagent.com transition
- 150ms delay for overlay paint before redirect
- AuthCallback branded loading + error states
- No Emergent text on app-controlled screens
- Remaining: auth.emergentagent.com URL in browser bar (outside our control)

## Logout (BUILT Mar 31 2026)
- Dashboard: User menu dropdown with Profile, Billing, Sign out
- Profile page: Sign out button in header
- Mobile: Same user menu on mobile viewport
- Clears all auth tokens, forces full page reload to /login

## Entitlement-Based Media Access (BUILT Mar 31 2026)
- Free users: Preview only, "Upgrade to Download" CTA
- Paid: Presigned URLs via `/api/media/download-token/`

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026# (free plan)
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026 (admin role)

## Completed (This Session — Mar 31 2026)
- [x] Premium Login UX — 14/14 tests passed
- [x] Logout button — Dashboard + Profile, desktop + mobile
- [x] Reel Creation Engine P0 — 11/11 backend + all frontend P0 features verified

## Upcoming (P1 — Reel Engine Differentiation)
1. Reference-Based Generation (paste reel URL or text for inspired/improved/viral versions)
2. Presets (Viral Hook, Luxury, Product Promo, Storytelling, Kids Story, UGC Ad, Educational, Faceless Business)
3. Anti-crop watermark improvements + dynamic per-user watermarks
4. Telemetry pipeline for abnormal access patterns
5. Notification Center improvements (history, read/unread)

## Future/Backlog (P2)
- History + Compare Versions (save, compare side-by-side, restore)
- Brand Kit / Creator Memory (save tone, audience, CTA prefs)
- Output Scoring (Hook Strength, Retention Score, Conversion Potential)
- Invisible forensic watermarking
- Admin leak dashboard
- Remix Variants, Story Chain leaderboard
- Admin dashboard WebSocket upgrade
