# MongoDB Collection Relationships — Mandatory Reference
# This file is READ-ONLY documentation of the current platform's data model.

## Source of Truth Rules
- Story output truth = `story_engine_jobs`
- Share/public truth = `share_links`
- Series truth = `story_series` + `story_episodes`
- Character truth = `character_profiles` + `character_visual_bibles`
- Growth truth = `growth_events`
- Homepage feed truth = assembled from jobs + growth + seeded content
- Legacy compatibility = `pipeline_jobs` (read-only, do not expand)

## Feed API Data Priority
1. `story_engine_jobs` (primary — READY state)
2. `pipeline_jobs` (legacy fallback — COMPLETED status)
3. `character_profiles` (character data — sole source)

## Compatibility Layer
- DB stores: `state` field in `story_engine_jobs`
- API returns: `status` via `_map_state_to_legacy_status()` mapping
- DB stores: flat media fields (`thumbnail_url`, `output_url`)
- Feed returns: CDN URLs for images, proxy URLs for videos
- No full DB migration — mapping at response layer only

## Join Rules
- Join on IDs only: user_id, job_id, series_id, episode_id, character_id, slug, variant_id
- Never join on title text or derived fields

## Media Field Names (consistent across all responses)
- thumbnail_url
- thumbnail_small_url
- poster_url
- preview_url
- output_url
