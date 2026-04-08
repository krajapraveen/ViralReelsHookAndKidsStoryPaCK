# Visionary Suite - Product Requirements Document

## Original Problem Statement
Build a full-stack AI Creator Suite with compulsion-driven growth engine, monetization, activation, conversion funnel, retention engine, content protection, and production-grade scale readiness. Latest: Make the pipeline production-resilient so generation failures don't kill the user experience.

## Architecture
```
/app/
├── backend/
│   ├── routes/
│   │   ├── instant_story.py                 # Zero-friction generation + multi-signal first-time detection
│   │   ├── story_video_generation.py        # Image/voice/video generation + admission control + idempotency + time-estimates
│   │   ├── story_video_studio.py            # Project CRUD with strict auth
│   │   ├── funnel_tracking.py               # Funnel events
│   │   ├── system_health_api.py             # System health + Load Guard
│   │   └── pricing_api.py                   # Dynamic pricing
│   ├── services/
│   │   ├── story_engine/
│   │   │   ├── pipeline.py                  # CORE: Stage orchestrator with fallback-resilient character context
│   │   │   ├── state_machine.py             # State transitions + retry limits
│   │   │   ├── adapters/planning_llm.py     # LLM calls for planning, continuity, scene motion
│   │   │   └── schemas.py                   # Job states + error codes
│   │   ├── admission_controller.py          # Load Guard
│   │   └── load_guard_alerts.py             # Slack alerts
│   └── security.py                          # Global rate limits
├── frontend/src/
│   ├── pages/
│   │   ├── InstantStoryExperience.jsx       # Demo + continuation + free-view + tooltip + paywall
│   │   ├── StoryVideoPipeline.js            # Result page with soft recovery error UX
│   │   ├── StoryVideoStudio.js              # Video creation with idempotency + refresh-safe resume
│   │   ├── MySpacePage.js                   # Full conversion UX with re-engagement + credit psychology
│   │   └── PhotoToComic.js                  # Photo conversion with soft error UX
│   └── App.js                               # Routes
```

## Completed Systems
1-14. [Previous systems — see CHANGELOG.md]

### Latest: Conversion & Retention Layer (2026-04-08)
15. **Re-engagement Buttons** — 4 variants on completed cards (funnier, change style, reel, storybook)
16. **Credit Psychology** — Credits badge + nudge text on completed cards
17. **Dynamic Time Estimates** — Backend rolling averages + fuzzy frontend labels
18. **Failure Recovery UX** — Encouraging copy + tip on failed cards
19. **Skeleton Loading** — Animated placeholder cards during fetch
20. **Completion Pulse** — Bounce badge + auto-scroll on just-completed

### Latest: Pipeline Resilience Fix (2026-04-08)
21. **Character Context Fallback** — `_stage_character_context` no longer fails the entire pipeline when LLM call fails. Builds basic character continuity from episode plan (names + minimal descriptions). Downstream stages handle it gracefully.
22. **Soft Error UX** — All "Generation Issue" replaced with "Something needs a quick fix" (amber, not red). Retry is primary CTA. "Start Fresh" removed as primary — now ghost secondary "or start over with a new story". Encouraging copy: "This usually works on retry. Your credits have been preserved."
23. **Character-Specific Tip** — When failure involves character continuity, shows: "Tip: We'll automatically use simpler character descriptions on retry."

## Key Pipeline Resilience Design
```python
# OLD (fragile):
if not continuity:
    return {"status": "failed"}  # kills entire pipeline

# NEW (resilient):
if not continuity:
    continuity = _build_fallback_continuity(episode_plan)  # basic characters from plan
    # Pipeline continues with simpler descriptions
```

**Fallback continuity format:**
```json
{
  "characters": [{"name": "...", "description": "A character named ...", "visual_tags": [], "color_palette": []}],
  "style_notes": "",
  "consistency_level": "basic",
  "_fallback": true
}
```

## Backlog
### P0 (Immediate)
- Push Instagram traffic to /experience and collect 100+ paywall_shown events

### P1
- Paywall conversion analytics & optimization
- A/B test hook text variations

### P2
- Explore Feed (TikTok-style scroll)
- Viral Story re-engagement hook
- Character consistency system (prompt templates + embeddings + seed control)
- WebSocket admin dashboard
- Story Chain leaderboard

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
