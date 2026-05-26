# Story Video mobile/backend contract

## Problem fixed

The mobile Story Video form must not send UI display labels to the backend. The backend endpoint is:

```text
POST /api/story-engine/create
```

Backend model: `CreateEngineRequest` in `backend/routes/story_engine_routes.py`.

## Canonical request payload

Mobile sends exactly these fields for Story Video:

```json
{
  "title": "Lighthouse Keeper",
  "story_text": "A complete story prompt of at least 50 characters...",
  "animation_style": "cartoon_2d",
  "age_group": "kids_5_8",
  "voice_preset": "narrator_warm",
  "quality_mode": "fast"
}
```

## UI label to API value mapping

| UI input | API field | API value |
| --- | --- | --- |
| `Title` | `title` | trimmed string, 3-100 chars |
| `Prompt` | `story_text` | trimmed string, 50-10000 chars |
| `Cartoon`, `2D Cartoon` | `animation_style` | `cartoon_2d` |
| `Anime` | `animation_style` | `anime_style` |
| `3D`, `3D Animation`, `Pixar` | `animation_style` | `3d_pixar` |
| `Watercolor` | `animation_style` | `watercolor` |
| `Comic`, `Comic Book` | `animation_style` | `comic_book` |
| `Claymation` | `animation_style` | `claymation` |
| `2-4` | `age_group` | `toddler` |
| `5-8`, `6-10` | `age_group` | `kids_5_8` |
| `9-12` | `age_group` | `kids_9_12` |
| `13+`, `Teen` | `age_group` | `teen` |
| `All ages` | `age_group` | `all_ages` |
| `15-30 seconds` | `quality_mode` | `fast` |
| `31-60 seconds` | `quality_mode` | `balanced` |
| `61-180 seconds` | `quality_mode` | `high_quality` |

`duration_seconds` is intentionally not sent to `/api/story-engine/create` because the current backend model does not accept it. Mobile maps duration intent to `quality_mode` until the backend exposes a real duration field.

## Required production behavior

- Validate with Zod before submit.
- Never show a generic validation banner.
- Highlight failing fields inline.
- Log outbound request payloads for generation submissions.
- Log response status and job id.
- Log field-level backend validation errors.
- Keep the Generate button disabled while required fields are empty or known field errors exist.

## Generation state machine target

Mobile result/status UI should converge on these user-facing states:

```text
queued
→ scripting
→ storyboard
→ image_generation
→ narration
→ soundtrack
→ rendering
→ uploading
→ completed
```

Failure states:

```text
moderation_failed
render_failed
timeout
insufficient_credits
```

## Backend follow-up

FastAPI already returns field-level Pydantic errors for schema failures. For custom validation failures, backend routes should return:

```json
{
  "error": "validation_failed",
  "fields": {
    "animation_style": "unsupported style",
    "age_group": "unsupported audience"
  }
}
```

Do not return generic validation copy from backend routes.
