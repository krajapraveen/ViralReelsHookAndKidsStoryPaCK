# Visionary Suite — PRD

## Product Vision
AI-powered creator suite that turns ideas into cinematic videos, comics, GIFs, and more. The platform features a comprehensive AI Character Memory system and a Growth Engine designed for viral user acquisition and retention.

## Core Features (Implemented)
- Story Video Studio (create, edit, remix)
- Comic Storybook Builder
- Photo to Comic
- GIF Maker
- Story Series Engine (stateful narratives)
- AI Character Memory System (3 sprints complete)
- Pricing & Monetization (4-tier system)
- Public explore/gallery/sharing pages
- Admin dashboards (analytics, security, health)

## Growth Engine (P0 — IMPLEMENTED)

### 1. Auto-Character Extraction
- On series creation, AI scores characters from Episode 1 with confidence threshold >= 0.7
- Role scoring (main=0.4, supporting=0.25, background=0.05) + scene presence + detail richness
- Deduplication by name similarity, max 3 characters
- User confirmation UI before locking characters to series
- Endpoints: GET/POST extracted-characters, POST confirm-characters, POST dismiss-extraction

### 2. Character-Based Sharing Loop (Viral Engine)
- Public character pages at /character/:characterId — NO login wall
- Displays character profile, visual bible, personality, goals/fears
- Social proof: episode count, story moments, series title, creator name
- Primary CTA: "Create Your Own Story With [Character]"
- Integrates with remix_data pipeline -> prefilled StoryVideoStudio
- Share button on CharacterDetail and SeriesTimeline

### 3. Series Completion Rewards (Retention Engine)
- Milestones at 3, 5, 10 episodes
- 3 episodes: "Story Taking Shape" — unlock Alternate Ending
- 5 episodes: "Story Complete" — unlock Season 2, Villain Origin Story
- 10 episodes: "Epic Saga" — unlock Alternate Universe, Character Spinoff, 50 bonus credits
- RewardModal with emotional message + functional rewards
- MilestoneProgress widget in SeriesTimeline sidebar
- Completion -> new creation loop (Season 2, Spinoff, etc.)

## UI Polish & In-Product Guidance (IMPLEMENTED)

### Background Consistency
- Fixed visually broken pages: AutomationDashboard (white cards -> dark), Gallery (custom hex -> standard), AdminDashboard (lighter bg -> gradient), MyDownloads (CSS vars -> standard), PublicCreation (custom hex -> standard)
- Standard: bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950

### In-Product Guidance (replaces static manual)
- 5-step Quick Start Guide overlay for new users (Create, Series, Characters, Share, Rewards)
- Re-accessible from Dashboard sidebar "Quick Start Guide" button
- Inline tips on empty prompts: StoryVideoStudio, CreateSeries, CharacterCreator
- Improved empty states: StorySeries ("Your Story Universe Awaits"), CharacterLibrary ("Build Your Character Cast")

### Legal Safeguards
- Copyright disclaimers on all creation tools (StoryVideoStudio, CreateSeries, CharacterCreator, GifMaker)
- Real-person consent warnings on character creation
- PhotoToComic already had copyright notice

## AI Character Memory System (Complete)
### Sprint A (MVP): Core entities, APIs, integration into Story Video pipeline
### Sprint B: Continuity Validator, Cross-Tool Persistence, Voice Profiles
### Sprint C: Editable Visual Bibles (versioning), Relationship Graph, Emotional Memory

## Key DB Collections
- story_series, story_episodes, character_bibles, world_bibles, story_memories
- character_profiles, character_visual_bibles, character_visual_bible_history
- character_voice_profiles, character_memory_logs, character_safety_profiles
- character_relationships, series_rewards

## Tech Stack
- Frontend: React, Tailwind CSS, Shadcn/UI, lucide-react
- Backend: FastAPI, Python
- Database: MongoDB
- Integrations: OpenAI (GPT-4o-mini, GPT Image 1, Sora 2, TTS), Gemini, Google Auth, Cloudflare R2
- Other: Redis, apscheduler, ffmpeg, JSZip

## Authentication
- JWT-based custom auth + Emergent-managed Google Auth
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Backlog
- (P1) Admin Observability Dashboard UI
- (P2) Style preset preview thumbnails for Photo to Comic
- (P2) Full background uniformity cleanup (remaining pages)
