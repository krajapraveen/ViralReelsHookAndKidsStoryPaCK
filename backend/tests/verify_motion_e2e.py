"""
End-to-end Photo Trailer motion verification.

What this proves:
  1. A real trailer renders successfully end-to-end (admin user, 15s template).
  2. The output video has motion (PSNR-based frame-diff between sampled frames).
  3. No frame run >= 1s frozen (>=25 identical frames in a row at 25fps).
  4. >= 4 distinct camera moves visible (clusters of frame-diff signatures).
  5. API stays responsive while pipeline runs (templates endpoint < 500ms).

Usage:
    cd /app && python -m backend.tests.verify_motion_e2e
"""
from __future__ import annotations
import os, sys, time, asyncio, hashlib, subprocess, tempfile, shutil
from pathlib import Path
import httpx

BACKEND = "http://localhost:8001"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASS  = "Cr3@t0rStud!o#2026"
FFMPEG  = "/usr/bin/ffmpeg"
FFPROBE = "/usr/bin/ffprobe"
TMP = tempfile.mkdtemp(prefix="trailer_e2e_")
print(f"workdir={TMP}")

def gen_test_photo(path: str):
    """A face-like image so safety checks don't reject. We synthesize a
    portrait via ffmpeg's lavfi gradient + drawtext."""
    subprocess.run([
        FFMPEG, "-y", "-f", "lavfi",
        "-i", "color=c=#f4d4b8:s=720x720:d=0.04",
        "-frames:v", "1",
        "-vf", (
            # head ellipse
            "drawbox=x=200:y=140:w=320:h=420:color=#e8c7a3@1.0:t=fill,"
            # eyes
            "drawbox=x=270:y=290:w=40:h=24:color=black@1.0:t=fill,"
            "drawbox=x=410:y=290:w=40:h=24:color=black@1.0:t=fill,"
            # mouth
            "drawbox=x=320:y=440:w=80:h=18:color=#a04040@1.0:t=fill,"
            # caption
            "drawtext=text='HERO':fontcolor=white:fontsize=70:x=(w-tw)/2:y=620"
        ),
        path,
    ], capture_output=True, check=True, timeout=20)

async def main():
    async with httpx.AsyncClient(base_url=BACKEND, timeout=120.0) as c:
        # 1. Login as admin
        r = await c.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
        assert r.status_code == 200, f"login: {r.status_code} {r.text}"
        token = r.json()["token"]
        H = {"Authorization": f"Bearer {token}"}

        # 2. Init upload session
        r = await c.post("/api/photo-trailer/uploads/init", headers=H, json={
            "file_count": 1, "mime_types": ["image/png"], "file_sizes": [200000],
        })
        assert r.status_code == 200, f"init: {r.text}"
        sid = r.json()["upload_session_id"]
        print(f"upload_session={sid}")

        # 3. Upload one photo
        photo = os.path.join(TMP, "hero.png")
        gen_test_photo(photo)
        with open(photo, "rb") as f:
            r = await c.post("/api/photo-trailer/uploads/photo", headers=H,
                             data={"upload_session_id": sid},
                             files={"file": ("hero.png", f, "image/png")})
        assert r.status_code == 200, f"upload: {r.text}"
        hero_id = r.json()["asset_id"]
        print(f"hero_asset={hero_id}")

        # 4. Complete upload (consent)
        r = await c.post("/api/photo-trailer/uploads/complete", headers=H, json={
            "upload_session_id": sid, "consent_confirmed": True,
        })
        assert r.status_code == 200, f"complete: {r.text}"

        # 5. Create job — 15s superhero
        r = await c.post("/api/photo-trailer/jobs", headers=H, json={
            "upload_session_id": sid,
            "hero_asset_id": hero_id,
            "supporting_asset_ids": [],
            "template_id": "superhero_origin",
            "duration_target_seconds": 15,
        })
        assert r.status_code in (200, 201), f"create job: {r.status_code} {r.text}"
        job = r.json(); job_id = job.get("id") or job.get("job_id") or job.get("_id")
        print(f"job={job_id} status={job.get('status')}")

        # 6. Poll status while sampling templates endpoint for responsiveness
        latencies = []
        last_stage = None
        t0 = time.time()
        final = None
        while time.time() - t0 < 240:
            # Sample templates endpoint latency in parallel
            t_start = time.time()
            tr = await c.get("/api/photo-trailer/templates", headers=H)
            latencies.append((time.time() - t_start) * 1000.0)
            assert tr.status_code == 200

            sr = await c.get(f"/api/photo-trailer/jobs/{job_id}", headers=H)
            if sr.status_code == 200:
                j = sr.json()
                stg = j.get("current_stage")
                if stg != last_stage:
                    print(f"  [{int(time.time()-t0):3}s] stage={stg} status={j.get('status')}")
                    last_stage = stg
                if j.get("status") in ("COMPLETED", "FAILED"):
                    final = j
                    break
            await asyncio.sleep(2)

        assert final, "pipeline didn't complete within 240s"
        assert final["status"] == "COMPLETED", f"FAILED: {final.get('error_message')}"
        video_url = final.get("result_video_url") or final.get("result_video_asset_id")
        print(f"COMPLETED in {int(time.time()-t0)}s — url={video_url}")

        # 7. API responsiveness during render
        p50 = sorted(latencies)[len(latencies) // 2]
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        print(f"templates latency during render: p50={p50:.0f}ms p95={p95:.0f}ms (n={len(latencies)})")

        # 8. Download the video
        out_video = os.path.join(TMP, "trailer.mp4")
        async with httpx.AsyncClient(timeout=60.0) as dlc:
            vr = await dlc.get(video_url)
            assert vr.status_code == 200
            with open(out_video, "wb") as f: f.write(vr.content)
        size_mb = os.path.getsize(out_video) / 1e6
        print(f"video size: {size_mb:.2f} MB")

        # 9. Frame extraction + diff analysis
        frames_dir = os.path.join(TMP, "frames")
        os.makedirs(frames_dir, exist_ok=True)
        subprocess.run([FFMPEG, "-y", "-i", out_video,
                        "-vf", "fps=25,scale=320:180", f"{frames_dir}/f_%04d.png"],
                       capture_output=True, check=True, timeout=120)
        all_frames = sorted(str(p) for p in Path(frames_dir).glob("f_*.png"))
        # Trailer body = everything before the 2.5s static end-card
        ENDCARD_FRAMES = int(2.5 * 25) + 5  # +5 buffer
        frames = all_frames[:-ENDCARD_FRAMES] if len(all_frames) > ENDCARD_FRAMES else all_frames
        print(f"frames total: {len(all_frames)}  body: {len(frames)} (excluding {ENDCARD_FRAMES}-frame end card)")

        # Frame hash → longest frozen run, body only
        hashes = []
        for fp in frames:
            with open(fp, "rb") as f: hashes.append(hashlib.md5(f.read()).hexdigest())
        longest = cur = 1
        longest_at = 0
        for i in range(1, len(hashes)):
            if hashes[i] == hashes[i - 1]:
                cur += 1
                if cur > longest:
                    longest = cur; longest_at = i - cur + 1
            else: cur = 1
        longest_sec = longest / 25.0
        print(f"longest frozen run (body): {longest} frames = {longest_sec:.2f}s @ frame {longest_at}")

        # PSNR helper
        def psnr(a, b):
            r = subprocess.run([FFMPEG, "-i", a, "-i", b, "-filter_complex",
                                "[0:v][1:v]psnr=stats_file=-:eof_action=endall",
                                "-f", "null", "-"], capture_output=True, text=True, timeout=20)
            for line in (r.stderr or "").splitlines():
                if "average:" in line and "PSNR" in line:
                    try:
                        return float(line.split("average:")[1].split()[0])
                    except: pass
            return 99.0

        # Scene cuts: pairs of frames straddling the 0.25s fade-out → fade-in
        # window. We check frame-pairs spaced ~3s apart (typical scene length)
        # and look for local PSNR minima below 22 dB (strong content change).
        cuts = []
        step = 25  # 1s window
        prev_psnr = 99.0
        for i in range(step, len(frames) - 1, step):
            p = psnr(frames[i - step // 2], frames[i + step // 2])
            if p < 22.0 and abs(p - prev_psnr) > 2.0:
                cuts.append(i)
            prev_psnr = p
        # De-dupe close cuts (within 1s)
        deduped = []
        for c in cuts:
            if not deduped or c - deduped[-1] > 25:
                deduped.append(c)
        cuts = deduped
        print(f"scene cuts detected (body): {len(cuts)} at {cuts[:10]}")

        # Intra-scene motion: between two adjacent cuts (or trailer
        # start/end), the mid-frame PSNR vs early-frame must show motion.
        motion_segments = 0
        boundaries = [0] + cuts + [len(frames) - 1]
        for k in range(len(boundaries) - 1):
            a, b = boundaries[k], boundaries[k + 1]
            if b - a < 50: continue  # < 2s segment skipped
            mid = (a + b) // 2
            pq = psnr(frames[a + 8], frames[mid])
            if pq < 42.0:
                motion_segments += 1
        print(f"scenes with intra-motion: {motion_segments}")

        # Acceptance
        passed = (longest_sec < 1.0
                  and len(cuts) >= 4
                  and motion_segments >= 4
                  and p50 < 500.0)
        print()
        print("=" * 70)
        print(" RESULTS")
        print("=" * 70)
        print(f"  longest frozen run < 1s        : {'PASS' if longest_sec < 1.0 else 'FAIL'}  ({longest_sec:.2f}s)")
        print(f"  scene cuts >= 4                : {'PASS' if len(cuts) >= 4 else 'FAIL'}  ({len(cuts)})")
        print(f"  intra-scene motion segments >=4: {'PASS' if motion_segments >= 4 else 'FAIL'}  ({motion_segments})")
        print(f"  templates p50 < 500ms          : {'PASS' if p50 < 500.0 else 'FAIL'}  ({p50:.0f}ms)")
        print(f"  render duration                : {int(time.time() - t0)}s")
        print(f"  output size                    : {size_mb:.2f} MB")
        print("=" * 70)
        print(" ✅ E2E MOTION VERIFICATION PASSED" if passed else " ❌ E2E FAILED")
        return 0 if passed else 1

if __name__ == "__main__":
    rc = asyncio.run(main())
    shutil.rmtree(TMP, ignore_errors=True)
    sys.exit(rc)
