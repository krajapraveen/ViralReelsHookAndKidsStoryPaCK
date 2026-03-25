# Visionary Suite — Self-Hosted Story-to-Video Stack

## Architecture Overview

### GPU Infrastructure (Recommended)

| Tier | Role | GPU | Cost Est. |
|------|------|-----|-----------|
| **CPU Node** | API, Auth, Credits, Payments, Queue | None | ~$50/mo |
| **Tier A: Light** | Planning fallback, reference jobs | 1x L4 | ~$0.40/hr |
| **Tier B: Heavy** | Video gen, keyframes, upscaling | 1x L40S | ~$1.00/hr |

**Start with**: 1 GPU worker (L40S or RTX 4090) + 1 CPU app node.
**Scale to**: 2x L40S + 1x L4 + CPU node + Redis queue + autoscaling.

---

## Model Stack (Apache-2.0 Safe)

| Function | Model | License | Notes |
|----------|-------|---------|-------|
| **Planning LLM** | Qwen2.5-14B-Instruct | Apache 2.0 | Episode planning, scene breakdown, continuity |
| **Text-to-Video** | Wan2.1-T2V-14B | Apache 2.0 | Moving scene clips from text prompts |
| **Image-to-Video** | Wan2.1-I2V-14B-480P | Apache 2.0 | Scene clips from keyframes |
| **Unified Path** | Wan2.1-VACE-14B | Apache 2.0 | Optional unified image/video |
| **TTS** | Kokoro-82M | Apache 2.0 | Narration audio |
| **Assembly** | FFmpeg | LGPL | Stitch, mix, subtitle, preview, thumbnail |

---

## Pipeline Architecture (11 Steps)

```
1. CREDIT CHECK → atomic deduction, refund on failure
2. CREATE JOB → story_engine_jobs collection
3. PLANNING → Qwen generates structured episode_plan JSON
4. CHARACTER CONTEXT → character continuity package locked
5. SCENE MOTION PLAN → per-scene motion/camera/transition plans
6. KEYFRAMES → Wan2.1 generates still keyframes per scene
7. SCENE CLIPS → Wan2.1 generates MOVING clips (T2V or I2V)
8. AUDIO → Kokoro generates narration
9. ASSEMBLY → FFmpeg stitches clips + audio + subtitles
10. VALIDATION → check all assets, continuity, style drift
11. MARK READY → READY / PARTIAL_READY / FAILED (truth-based)
```

**Critical rule**: FFmpeg is assembly ONLY. Moving clips come from Wan2.1.

---

## State Machine

```
INIT → PLANNING → BUILDING_CHARACTER_CONTEXT → PLANNING_SCENE_MOTION
→ GENERATING_KEYFRAMES → GENERATING_SCENE_CLIPS → GENERATING_AUDIO
→ ASSEMBLING_VIDEO → VALIDATING → READY | PARTIAL_READY | FAILED
```

No fake completion states. `PARTIAL_READY` = some scenes missing.

---

## Schemas

### Episode Plan (Mandatory Structure)
- title, summary, emotional_arc
- scene_breakdown[] (location, time, characters, action, dialogue, emotional_beat, visual_style)
- character_arcs[] (name, role, emotional_journey, appearance, voice_tone)
- cliffhanger (always unresolved)
- visual_style_constraints, negative_constraints

### Scene Motion Plan (Per-Scene)
- action, emotion, camera_motion, transition_type
- motion_intensity (subtle/moderate/dynamic/intense)
- clip_duration_seconds, movement_notes
- keyframe_prompt, video_prompt

### Character Continuity Package
- characters[] (name, gender, age, build, hair, eyes, skin, clothing, features, reference_prompt)
- style_lock, color_palette, environment_consistency

---

## API Endpoints

### User Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/story-engine/credit-check` | Pre-flight credit check |
| POST | `/api/story-engine/create` | Create job + run pipeline |
| GET | `/api/story-engine/status/{job_id}` | Poll job status |
| GET | `/api/story-engine/my-jobs` | List user's jobs |
| GET | `/api/story-engine/chain/{chain_id}` | Get story chain episodes |

### Admin Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/story-engine/admin/jobs` | List all jobs with filters |
| GET | `/api/story-engine/admin/job/{job_id}` | Full job details |
| POST | `/api/story-engine/admin/retry/{job_id}` | Retry failed job |
| GET | `/api/story-engine/admin/pipeline-health` | Pipeline health + GPU status |

---

## Credit System

- **Default cost**: 21 credits per Story-to-Video job
- **Breakdown**: Planning (1) + Character (1) + Motion (1) + Keyframes (5) + Clips (10) + Audio (2) + Assembly (1)
- **Pre-flight check**: `/credit-check` endpoint before showing generation form
- **Atomic deduction**: MongoDB `update_one` with `credits >= required` guard
- **Auto-refund**: On pipeline failure, credits refunded + logged in credit_transactions

---

## Safety & Anti-Abuse

- **Copyright blocking**: Disney, Marvel, DC, anime characters blocked at input
- **Celebrity blocking**: Real person names blocked
- **Brand blocking**: Trademarked brands blocked
- **Rate limits**: 2 concurrent jobs, 10/hour, 50/day per user
- **Abuse detection**: Rapid-fire submission flagging, high failure rate alerts
- **Universal negative prompt**: Applied to ALL visual generation (non-removable)

---

## Deployment Checklist

When connecting GPU workers, set these env vars:
```
WAN_T2V_ENDPOINT=http://gpu-worker:8080/t2v
WAN_I2V_ENDPOINT=http://gpu-worker:8080/i2v
KEYFRAME_GEN_ENDPOINT=http://gpu-worker:8080/keyframe
KOKORO_TTS_ENDPOINT=http://tts-worker:8080/synthesize
```

---

## FFmpeg Commands Reference

### Stitch clips with crossfades
```bash
ffmpeg -i scene_01.mp4 -i scene_02.mp4 -i scene_03.mp4 \
  -filter_complex "[0:v][1:v]xfade=transition=fade:duration=0.5:offset=4.5[v01];[v01][2:v]xfade=transition=fade:duration=0.5:offset=9.0[v]" \
  -map "[v]" -c:v libx264 -pix_fmt yuv420p -crf 20 crossfaded.mp4
```

### Mix narration + music
```bash
ffmpeg -i crossfaded.mp4 -i narration.wav -i music.wav \
  -filter_complex "[1:a]volume=1.2[narr];[2:a]volume=0.18[music];[narr][music]amix=inputs=2:duration=first:dropout_transition=2[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k final.mp4
```

### Generate preview + thumbnail
```bash
ffmpeg -i final.mp4 -t 8 -c:v libx264 -crf 24 preview.mp4
ffmpeg -i final.mp4 -ss 2 -vframes 1 -q:v 2 thumbnail.jpg
```
