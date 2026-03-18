"""
Ken Burns Motion Verification — End-to-End FFmpeg Test
=====================================================
Creates a test image, applies each Ken Burns motion pattern via the real
ffmpeg zoompan pipeline (same filters used in production), then verifies
the output video has actual pixel-level motion (not a static slideshow).
"""
import os
import sys
import subprocess
import tempfile
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.pipeline_engine import _build_ken_burns_filter, MOTION_PATTERNS

RENDER_W = 960
RENDER_H = 540
FPS = 24
DURATION = 2.0  # seconds per test clip


def create_test_image(path, w, h):
    """Create a gradient test image with ffmpeg (no PIL needed)."""
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi", "-i",
        f"color=c=blue:s={w}x{h}:d=1,drawtext=text='KEN BURNS TEST':fontcolor=white:fontsize=40:x=(w-text_w)/2:y=(h-text_h)/2",
        "-frames:v", "1", path
    ]
    r = subprocess.run(cmd, capture_output=True, timeout=15)
    return r.returncode == 0 and os.path.exists(path)


def extract_frames(video_path, out_dir, count=5):
    """Extract evenly-spaced frames from video."""
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
         "-show_entries", "stream=nb_read_frames,duration", "-of", "json", video_path],
        capture_output=True, text=True, timeout=15
    )
    info = json.loads(probe.stdout)
    nb_frames = int(info["streams"][0].get("nb_read_frames", 48))
    step = max(nb_frames // count, 1)

    frames = []
    for i in range(count):
        frame_num = i * step
        out_path = os.path.join(out_dir, f"frame_{i}.png")
        subprocess.run(
            ["ffmpeg", "-y", "-i", video_path, "-vf", f"select=eq(n\\,{frame_num})",
             "-frames:v", "1", out_path],
            capture_output=True, timeout=15
        )
        if os.path.exists(out_path):
            frames.append(out_path)
    return frames


def frames_have_motion(frames):
    """Compare frame file sizes — motion causes different compression ratios."""
    if len(frames) < 2:
        return False
    sizes = [os.path.getsize(f) for f in frames]
    # If all frames are identical, sizes will be very close (within ~1%)
    avg = sum(sizes) / len(sizes)
    if avg == 0:
        return False
    max_deviation = max(abs(s - avg) / avg for s in sizes)
    return max_deviation > 0.01  # >1% deviation = motion detected


def pixel_diff(frames):
    """Use ffmpeg to compute pixel diff between first and last frame."""
    if len(frames) < 2:
        return 0
    cmd = [
        "ffmpeg", "-y", "-i", frames[0], "-i", frames[-1],
        "-filter_complex", "blend=all_mode=difference,blackframe=98:32",
        "-f", "null", "-"
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    # If blackframe filter detects the diff is NOT all black, there's motion
    # blackframe outputs lines like "Parsed_blackframe_1 ... pblack:XX"
    stderr = r.stderr
    # No blackframe detection = frames are different = motion exists
    has_blackframe = "pblack:100" in stderr or "pblack: 100" in stderr
    return not has_blackframe


def run_ken_burns_test(motion_name, scene_idx, test_img, tmp_dir):
    """Run a single Ken Burns motion test."""
    src_w, src_h, zoompan_filter = _build_ken_burns_filter(
        scene_idx=scene_idx, dur=DURATION, w=RENDER_W, h=RENDER_H, fps=FPS
    )

    output_path = os.path.join(tmp_dir, f"kb_{motion_name}.mp4")

    # This is the EXACT filter chain used in production (pipeline_engine.py line 1219-1224)
    filter_str = (
        f"scale={src_w}:{src_h}:force_original_aspect_ratio=decrease,"
        f"pad={src_w}:{src_h}:(ow-iw)/2:(oh-ih)/2:black,"
        f"{zoompan_filter},"
        f"setsar=1"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", f"{DURATION:.1f}", "-i", test_img,
        "-vf", filter_str,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return {"motion": motion_name, "status": "FFMPEG_ERROR", "error": result.stderr[-200:]}

    if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
        return {"motion": motion_name, "status": "NO_OUTPUT"}

    # Extract frames and check for motion
    frame_dir = os.path.join(tmp_dir, f"frames_{motion_name}")
    os.makedirs(frame_dir, exist_ok=True)
    frames = extract_frames(output_path, frame_dir, count=5)

    size_motion = frames_have_motion(frames)
    pixel_motion = pixel_diff(frames) if len(frames) >= 2 else False

    file_size = os.path.getsize(output_path)

    return {
        "motion": motion_name,
        "status": "PASS" if (size_motion or pixel_motion) else "FAIL_STATIC",
        "file_size_bytes": file_size,
        "frames_extracted": len(frames),
        "size_motion_detected": size_motion,
        "pixel_motion_detected": pixel_motion,
        "filter": zoompan_filter[:80] + "...",
    }


def main():
    print("=" * 60)
    print("KEN BURNS MOTION VERIFICATION — E2E FFmpeg Test")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Step 1: Create test image
        test_img = os.path.join(tmp_dir, "test_input.png")
        print(f"\n1. Creating test image ({RENDER_W*1.5:.0f}x{RENDER_H*1.5:.0f})...")
        if not create_test_image(test_img, int(RENDER_W * 1.5), int(RENDER_H * 1.5)):
            print("   FAIL: Could not create test image")
            sys.exit(1)
        print(f"   OK: {os.path.getsize(test_img)} bytes")

        # Step 2: Test each motion pattern
        print(f"\n2. Testing {len(MOTION_PATTERNS)} motion patterns...")
        results = []
        for i, pattern in enumerate(MOTION_PATTERNS):
            print(f"   [{i+1}/{len(MOTION_PATTERNS)}] {pattern}...", end=" ", flush=True)
            r = run_ken_burns_test(pattern, i, test_img, tmp_dir)
            results.append(r)
            print(r["status"], f"({r.get('file_size_bytes', 0)} bytes)")

        # Step 3: Summary
        print(f"\n{'=' * 60}")
        print("RESULTS SUMMARY")
        print(f"{'=' * 60}")

        passed = sum(1 for r in results if r["status"] == "PASS")
        total = len(results)

        for r in results:
            icon = "PASS" if r["status"] == "PASS" else "FAIL"
            print(f"  [{icon}] {r['motion']:15s} | size_motion={r.get('size_motion_detected', '?')} pixel_motion={r.get('pixel_motion_detected', '?')} | {r.get('file_size_bytes', 0)} bytes")

        print(f"\n  Total: {passed}/{total} patterns produce detectable motion")
        print(f"  Verdict: {'ALL MOTION PATTERNS WORKING' if passed == total else 'SOME PATTERNS MAY NEED REVIEW'}")

        # Save report
        report = {
            "test": "ken_burns_motion_verification",
            "render_config": {"width": RENDER_W, "height": RENDER_H, "fps": FPS, "duration_sec": DURATION},
            "patterns_tested": len(MOTION_PATTERNS),
            "patterns_passed": passed,
            "verdict": "PASS" if passed == total else "PARTIAL",
            "results": results,
        }
        report_path = "/app/test_reports/ken_burns_motion_verification.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n  Report saved: {report_path}")

        return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
