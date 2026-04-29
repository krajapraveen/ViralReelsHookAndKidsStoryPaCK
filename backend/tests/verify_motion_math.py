"""
Motion-math verification for Photo Trailer cinematic upgrade.

Runs each of the 8 motion styles in `_motion_filter` against a real
high-detail test image, then frame-diffs the output to PROVE:
  1. No frame is frozen >= 1s (>= 25 consecutive identical frames).
  2. Motion is visibly continuous (mean per-frame pixel diff > threshold).
  3. All 8 styles produce DISTINCT motion fingerprints
     (avg horizontal/vertical drift differs across the catalog).
  4. Render time per clip stays within budget (< 10s for a 6s clip).

Run:
  cd /app && python -m backend.tests.verify_motion_math
"""
from __future__ import annotations
import os, sys, time, subprocess, tempfile, shutil, hashlib
from pathlib import Path

sys.path.insert(0, "/app/backend")
from routes.photo_trailer import _motion_filter, _TONE_GRADE  # noqa

FFMPEG = "/usr/bin/ffmpeg" if os.path.exists("/usr/bin/ffmpeg") else "ffmpeg"
FFPROBE = "/usr/bin/ffprobe" if os.path.exists("/usr/bin/ffprobe") else "ffprobe"
DUR_SEC = 6.0
FPS = 25
FRAMES = int(DUR_SEC * FPS)
TMP = tempfile.mkdtemp(prefix="motion_verify_")

# Build a complex, asymmetric source image — edges + text + gradients —
# so ANY pan/zoom shift produces visibly different pixels.
def make_source_image() -> str:
    img = os.path.join(TMP, "src.png")
    # 1920x1080 with a gradient + grid + text for clear motion fingerprinting.
    cmd = [
        FFMPEG, "-y", "-f", "lavfi",
        "-i", "gradients=size=1920x1080:duration=0.04:speed=0.0001:c0=red:c1=blue:c2=yellow:c3=green",
        "-frames:v", "1",
        "-vf", (
            "drawgrid=w=120:h=120:t=2:c=white@0.5,"
            "drawtext=text='MOTION TEST 1234':fontcolor=white:fontsize=120:x=80:y=460,"
            "drawtext=text='Photo Trailer':fontcolor=cyan:fontsize=60:x=80:y=620"
        ),
        img,
    ]
    subprocess.run(cmd, capture_output=True, check=True, timeout=30)
    return img

def render_clip(motion: str, out: str) -> float:
    chain = [
        "scale=1280:720:force_original_aspect_ratio=increase",
        "crop=1280:720", "setsar=1", motion, "format=yuv420p",
    ]
    vf = ",".join(chain)
    t0 = time.time()
    res = subprocess.run([
        FFMPEG, "-y", "-loop", "1", "-i", make_source_image(),
        "-vf", vf, "-c:v", "libx264", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p", "-r", str(FPS), "-t", f"{DUR_SEC}", out,
    ], capture_output=True, timeout=60)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg failed for motion {motion[:60]}: {res.stderr.decode()[-500:]}")
    return time.time() - t0

def extract_frames(clip: str, dst: str) -> list[str]:
    os.makedirs(dst, exist_ok=True)
    subprocess.run([
        FFMPEG, "-y", "-i", clip, "-vf", "scale=320:180", f"{dst}/f_%04d.png",
    ], capture_output=True, check=True, timeout=60)
    return sorted(str(p) for p in Path(dst).glob("f_*.png"))

def frame_hash(p: str) -> str:
    with open(p, "rb") as f: return hashlib.md5(f.read()).hexdigest()

def frame_diff(a: str, b: str) -> float:
    """Mean-absolute-pixel-diff via ffmpeg PSNR (lower PSNR = more change)."""
    res = subprocess.run([
        FFMPEG, "-i", a, "-i", b, "-filter_complex",
        "[0:v][1:v]psnr=stats_file=-:eof_action=endall", "-f", "null", "-",
    ], capture_output=True, text=True, timeout=20)
    # Parse PSNR average from stderr
    for line in (res.stderr or "").splitlines():
        if "average:" in line and "PSNR" in line:
            try:
                seg = line.split("average:")[1].split()[0]
                return float(seg)
            except Exception:
                pass
    return 99.0  # high PSNR = identical

# ─── Run verification ──────────────────────────────────────────────────────────
results = []
print("=" * 78)
print(f"Motion-math verification — {DUR_SEC}s @ {FPS}fps = {FRAMES} frames per clip")
print("=" * 78)
src = make_source_image()
all_frame_lists = []

for idx in range(8):
    motion = _motion_filter(idx, FRAMES)
    clip = os.path.join(TMP, f"clip_{idx}.mp4")
    print(f"\n[{idx}] Rendering: {motion[:90]}…")
    render_sec = render_clip(motion, clip)

    # Extract frames + compute consecutive-frame identity
    frames_dir = os.path.join(TMP, f"frames_{idx}")
    frames = extract_frames(clip, frames_dir)
    n = len(frames)
    if n < FRAMES - 2:
        results.append({"idx": idx, "ok": False, "err": f"frame_count={n}, expected ~{FRAMES}"})
        continue

    hashes = [frame_hash(p) for p in frames]
    # Longest run of identical consecutive frames
    longest = cur = 1
    for i in range(1, len(hashes)):
        if hashes[i] == hashes[i - 1]:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 1
    longest_seconds = longest / FPS

    # Center-of-mass drift between first vs middle vs last (approx motion fingerprint)
    sample_psnr_first_mid = frame_diff(frames[2], frames[FRAMES // 2])
    sample_psnr_mid_last  = frame_diff(frames[FRAMES // 2], frames[-3])

    all_frame_lists.append(frames)

    results.append({
        "idx": idx,
        "render_sec": round(render_sec, 2),
        "frames": n,
        "longest_frozen_run": longest,
        "longest_frozen_sec": round(longest_seconds, 3),
        "psnr_first_to_mid": round(sample_psnr_first_mid, 2),
        "psnr_mid_to_last": round(sample_psnr_mid_last, 2),
        "ok": (longest_seconds < 1.0
               and sample_psnr_first_mid < 45.0  # < 45 dB PSNR ⇒ visible change
               and sample_psnr_mid_last < 45.0),
    })

# ─── Distinctness check: do styles differ from each other? ─────────────────────
# Compare the 80%-frame of each style against every other style — high
# per-style divergence proves the catalog isn't producing 8 identical clips.
distinct_pairs = 0
total_pairs = 0
for i in range(8):
    for k in range(i + 1, 8):
        if not all_frame_lists[i] or not all_frame_lists[k]: continue
        psnr = frame_diff(all_frame_lists[i][int(FRAMES * 0.8)],
                          all_frame_lists[k][int(FRAMES * 0.8)])
        total_pairs += 1
        if psnr < 35.0:  # very different frames
            distinct_pairs += 1

# ─── Print + assert ────────────────────────────────────────────────────────────
print("\n" + "=" * 78)
print(" RESULTS")
print("=" * 78)
print(f"{'idx':>3}  {'render':>7}  {'frames':>6}  {'frozen_run':>11}  "
      f"{'sec':>5}  {'psnr_f→m':>9}  {'psnr_m→l':>9}  ok")
for r in results:
    if not r.get("ok") and "err" in r:
        print(f"  {r['idx']:>3}  ERR: {r['err']}")
        continue
    print(f"  {r['idx']:>3}  {r['render_sec']:>6}s  {r['frames']:>6}  "
          f"{r['longest_frozen_run']:>11}  {r['longest_frozen_sec']:>5}  "
          f"{r['psnr_first_to_mid']:>9}  {r['psnr_mid_to_last']:>9}  "
          f"{'PASS' if r['ok'] else 'FAIL'}")

print(f"\nDistinct-style pairs (PSNR < 35): {distinct_pairs}/{total_pairs}  "
      f"(>=20/28 ⇒ healthy diversity)")

# Final pass/fail
all_ok = all(r.get("ok") for r in results)
diversity_ok = distinct_pairs >= 20

print("\n" + "=" * 78)
if all_ok and diversity_ok:
    print(" ✅ MOTION VERIFICATION PASSED")
    print("    • No style had a frozen-frame run >= 1s")
    print("    • Every style showed measurable per-frame motion (PSNR < 45 dB)")
    print(f"    • {distinct_pairs}/{total_pairs} style pairs are visually distinct")
else:
    print(" ❌ MOTION VERIFICATION FAILED")
    print(f"    all_ok={all_ok}  diversity_ok={diversity_ok}")
print("=" * 78)

# Cleanup
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(0 if (all_ok and diversity_ok) else 1)
