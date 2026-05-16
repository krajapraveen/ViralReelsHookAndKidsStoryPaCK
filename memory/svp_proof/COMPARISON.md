# Story-to-Video Reliability Sprint — Before / After Proof
2026-05-16

## Run #1 (BEFORE optimization)
Job ID: `687fd08b-6d8c-415e-a527-7099001c8672`
Quality mode: `fast` (but `use_sora=False` was being ignored)
Output: https://pub-c251248e414545848d34b8c1b97ecdb3.r2.dev/videos/687fd08b-6d8c-415e-a527-7099001c8672/se_687fd08b_final.mp4

| Stage                        | Duration | SLA  | Within? |
|------------------------------|---------:|-----:|:--------|
| PLANNING                     | 10.27s   | 25s  | ✓       |
| BUILDING_CHARACTER_CONTEXT   |  5.10s   | 25s  | ✓       |
| PLANNING_SCENE_MOTION        |  9.95s   | 25s  | ✓       |
| GENERATING_KEYFRAMES         | 24.11s   | 90s  | ✓       |
| **GENERATING_SCENE_CLIPS**   | **226.47s** | 180s | **✗ BREACH (+46s)** |
| GENERATING_AUDIO             |  2.26s   | 60s  | ✓       |
| ASSEMBLING_VIDEO             | 32.22s   | 90s  | ✓       |
| VALIDATING                   |  0.00s   | 45s  | ✓       |
| **TOTAL**                    | **310.38s** |       |        |

## Run #2 (AFTER optimization — same prompt, same quality_mode='fast')
Job ID: `e63e6055-ad8e-4b1f-ba0c-23df1f155f26`
Output: https://pub-c251248e414545848d34b8c1b97ecdb3.r2.dev/videos/e63e6055-ad8e-4b1f-ba0c-23df1f155f26/se_e63e6055_final.mp4

| Stage                        | Duration | SLA  | Within? |
|------------------------------|---------:|-----:|:--------|
| PLANNING                     | 11.08s   | 25s  | ✓       |
| BUILDING_CHARACTER_CONTEXT   |  3.98s   | 25s  | ✓       |
| PLANNING_SCENE_MOTION        |  4.18s   | 25s  | ✓       |
| GENERATING_KEYFRAMES         | 41.46s   | 90s  | ✓       |
| **GENERATING_SCENE_CLIPS**   | **9.01s** | 180s | **✓ (25× faster)** |
| GENERATING_AUDIO             |  3.58s   | 60s  | ✓       |
| ASSEMBLING_VIDEO             | 27.73s   | 90s  | ✓       |
| VALIDATING                   |  0.00s   | 45s  | ✓       |
| **TOTAL**                    | **101.02s** |       | **✓ Under 2 min target** |

## Delta
- Total: **310.38s → 101.02s = -209s (3.07× faster, -67%)**
- GENERATING_SCENE_CLIPS: 226.47s → 9.01s (25× faster)
- All stages now within their tightened SLAs.
- One video successfully generated end-to-end as proof.

## Root cause
`_stage_scene_clips` in `services/story_engine/pipeline.py` never read
`quality_config.use_sora` — it always called the Sora pipeline. In fast mode
the config explicitly said `use_sora: False` but the code ignored it. Sora
clip generation also ran sequentially in a `for` loop, multiplying the wait.

## Fix
1. `_stage_scene_clips` now reads `use_sora` from `quality_config`.
2. Fast mode short-circuits straight to Ken Burns on keyframes (~3s/scene).
3. The remaining sequential `for` loop was converted to `asyncio.gather`
   so when Sora IS used (balanced/high_quality), scenes generate in parallel.
