# Self-Hosted Story-to-Video Architecture Specification
# Visionary Suite — Private Generation Stack

## Overview
This document specifies the exact self-hosted model stack, GPU infrastructure, and pipeline flow
for replacing external API dependencies with a fully private Story-to-Video generation system.

## 1. GPU Infrastructure

### Recommended Starting Configuration
| Component | Hardware | Purpose | Est. Cost/hr |
|-----------|----------|---------|-------------|
| App Node | CPU-only | API, auth, credits, payments, queue | ~$0.05 |
| GPU Worker (Primary) | 1× L40S or L4 | Video/image generation, keyframes | $0.50-1.19 |
| GPU Worker (Overflow) | 1× RTX 4090 (optional) | Light inference, overflow | $0.34 |

### Scale-Ready Configuration
- 2× L40S generation workers
- 1× L4 auxiliary worker
- CPU app node
- Redis queue + autoscaling workers

## 2. Model Stack (Apache 2.0 Licensed — Commercially Safe)

### A. Planning LLM
- **Model**: Qwen2.5-14B-Instruct (or Qwen2.5-1.5B for lighter tasks)
- **License**: Apache 2.0
- **Use for**: Episode planning, scene breakdown, continuity extraction, cliffhanger generation, character extraction

### B. Video Generation
- **Text-to-Video**: Wan2.1-T2V-14B (Apache 2.0)
- **Image-to-Video**: Wan2.1-I2V-14B-480P (Apache 2.0)
- **Unified path**: Wan2.1-VACE-14B (optional, Apache 2.0)

### C. Alternative Video (requires license review)
- HunyuanVideo / HunyuanVideo-1.5 / HunyuanVideo-I2V
- License: Tencent Model License/AUP (not Apache)
- Use only if Tencent license is reviewed and accepted

### D. TTS / Narration
- **Model**: Kokoro-82M (Apache 2.0)
- **Avoid**: XTTS-v2 as primary (Coqui Public Model License, not Apache)

## 3. Pipeline Flow (Exact Order)

```
1. Credit check (frontend + backend atomic)
2. Create job record
3. Plan episode with Qwen (scene breakdown, character continuity)
4. Build character continuity package
5. Generate scene motion plan
6. Generate keyframes (image generation)
7. Generate moving clips per scene (Wan2.1 T2V or I2V)
8. Generate narration with Kokoro
9. FFmpeg assembly (stitch, transitions, audio mix, subtitles, preview, thumbnail)
10. Validate outputs (video_url, thumbnail_url must exist)
11. Mark READY only if all assets are valid
```

## 4. FFmpeg Commands

### A. Stitch clips
```bash
ffmpeg -f concat -safe 0 -i inputs.txt -c:v libx264 -pix_fmt yuv420p -preset medium -crf 20 stitched.mp4
```

### B. Crossfades
```bash
ffmpeg \
  -i scene_01.mp4 -i scene_02.mp4 -i scene_03.mp4 \
  -filter_complex "\
  [0:v][1:v]xfade=transition=fade:duration=0.5:offset=4.5[v01]; \
  [v01][2:v]xfade=transition=fade:duration=0.5:offset=9.0[v]" \
  -map "[v]" -c:v libx264 -pix_fmt yuv420p -crf 20 crossfaded.mp4
```

### C. Add narration + background music
```bash
ffmpeg -i crossfaded.mp4 -i narration.wav -i music.wav \
  -filter_complex "\
  [1:a]volume=1.2[narr]; \
  [2:a]volume=0.18[music]; \
  [narr][music]amix=inputs=2:duration=first:dropout_transition=2[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k final_with_audio.mp4
```

### D. Burn subtitles
```bash
ffmpeg -i final_with_audio.mp4 -vf "subtitles=subs.srt" -c:v libx264 -crf 20 -c:a copy subtitled.mp4
```

### E. Preview + Thumbnail
```bash
# Preview (8 second clip)
ffmpeg -i final_with_audio.mp4 -t 8 -c:v libx264 -pix_fmt yuv420p -crf 24 preview.mp4

# Thumbnail
ffmpeg -i final_with_audio.mp4 -ss 00:00:02 -vframes 1 -q:v 2 thumbnail.jpg
```

### F. Fallback: Animate still keyframes (Ken Burns)
```bash
ffmpeg -loop 1 -i keyframe.jpg \
  -vf "zoompan=z='min(zoom+0.0015,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=125:s=1280x720,framerate=25" \
  -t 5 -c:v libx264 -pix_fmt yuv420p fallback_scene.mp4
```

## 5. Credit Gating (Already Implemented)

### Frontend Flow
```
User clicks Story-to-Video →
  fetch credits →
  if insufficient: show paywall (required / current / shortfall / Buy CTA) →
  if sufficient: proceed to generation
```

### Backend Enforcement
```python
if user.credits < required_credits:
    return 402 business error

# Atomic deduction
BEGIN
  check current credits
  if enough: deduct credits + create job
  else: fail
COMMIT

# On failure: automatic refund with source = "story_video_failure_refund"
```

## 6. Universal Negative Prompt
Must be injected into ALL image/keyframe/video generation calls:
```
No watermarks, no text overlays, no logos, no copyrighted characters,
no celebrity likenesses, no real-person faces, no NSFW content,
no violence, no gore, no weapons, no drugs, no political content
```

## 7. Content Safety Rules
Even with open models:
- Block copyrighted character cloning
- Block celebrity likeness persistence
- Block real-person likeness without consent
- Model license ≠ output safety

## 8. Implementation Priority
1. Set up GPU worker with Wan2.1-T2V-14B
2. Integrate Qwen2.5-14B for planning (replace external LLM calls)
3. Add Kokoro-82M for TTS (replace external TTS)
4. Wire FFmpeg assembly pipeline
5. Add Wan2.1-I2V-14B for image-to-video
6. Scale with Redis queue + autoscaling workers
