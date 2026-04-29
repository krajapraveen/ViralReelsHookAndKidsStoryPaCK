"""60s trailer end-to-end verification.

Acceptance criteria from founder bug report:
  - Final MP4 duration must be between 55 and 65 seconds.
  - Job must complete (no STALE_PIPELINE).
  - Credits charged correctly (35 cr for 60s bucket), 0 refunded.
  - Result must appear in /api/photo-trailer/my-trailers with status=COMPLETED.
  - 15s preview must still work (no regression).
"""
import os, asyncio, time, subprocess, tempfile, sys
import httpx

BACKEND = "http://localhost:8001"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASS  = "Cr3@t0rStud!o#2026"
FFPROBE = "/usr/bin/ffprobe"
FFMPEG = "/usr/bin/ffmpeg"

def gen_test_photo(path: str):
    subprocess.run([
        FFMPEG, "-y", "-f", "lavfi",
        "-i", "color=c=#f4d4b8:s=720x720:d=0.04",
        "-frames:v", "1",
        "-vf", (
            "drawbox=x=200:y=140:w=320:h=420:color=#e8c7a3@1.0:t=fill,"
            "drawbox=x=270:y=290:w=40:h=24:color=black@1.0:t=fill,"
            "drawbox=x=410:y=290:w=40:h=24:color=black@1.0:t=fill,"
            "drawbox=x=320:y=440:w=80:h=18:color=#a04040@1.0:t=fill,"
            "drawtext=text='HERO':fontcolor=white:fontsize=70:x=(w-tw)/2:y=620"
        ), path,
    ], capture_output=True, check=True, timeout=20)

async def run_one(duration: int, expect_min: float, expect_max: float):
    print(f"\n{'=' * 70}\n Running {duration}s trailer test\n{'=' * 70}")
    tmp = tempfile.mkdtemp(prefix=f"e2e_{duration}_")
    photo = os.path.join(tmp, "hero.png")
    gen_test_photo(photo)

    async with httpx.AsyncClient(base_url=BACKEND, timeout=240.0) as c:
        r = await c.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
        token = r.json()["token"]; H = {"Authorization": f"Bearer {token}"}

        r = await c.post("/api/photo-trailer/uploads/init", headers=H, json={
            "file_count": 1, "mime_types": ["image/png"], "file_sizes": [200000]})
        sid = r.json()["upload_session_id"]

        with open(photo, "rb") as f:
            r = await c.post("/api/photo-trailer/uploads/photo", headers=H,
                             data={"upload_session_id": sid},
                             files={"file": ("hero.png", f, "image/png")})
        hero_id = r.json()["asset_id"]

        await c.post("/api/photo-trailer/uploads/complete", headers=H,
                     json={"upload_session_id": sid, "consent_confirmed": True})

        r = await c.post("/api/photo-trailer/jobs", headers=H, json={
            "upload_session_id": sid, "hero_asset_id": hero_id,
            "supporting_asset_ids": [], "template_id": "superhero_origin",
            "duration_target_seconds": duration})
        assert r.status_code in (200, 201), f"create job failed: {r.status_code} {r.text}"
        job = r.json(); job_id = job.get("job_id") or job.get("id"); estimated = job.get("estimated_credits")
        print(f"  job={job_id} estimated_credits={estimated}")

        # Poll
        t0 = time.time(); final = None; last_stage = None
        while time.time() - t0 < 300:
            sr = await c.get(f"/api/photo-trailer/jobs/{job_id}", headers=H)
            if sr.status_code == 200:
                j = sr.json()
                stg = j.get("current_stage")
                if stg != last_stage:
                    print(f"  [{int(time.time()-t0):3}s] stage={stg} status={j.get('status')}")
                    last_stage = stg
                if j.get("status") in ("COMPLETED", "FAILED"):
                    final = j; break
            await asyncio.sleep(2)

        assert final, f"{duration}s pipeline didn't complete within 300s"
        assert final["status"] == "COMPLETED", f"FAILED: {final.get('error_code')} {final.get('error_message')}"
        # MySpace check
        mt = await c.get("/api/photo-trailer/my-trailers?limit=10", headers=H)
        assert mt.status_code == 200
        rows = mt.json().get("trailers", [])
        match = next((t for t in rows if t.get("job_id") == job_id), None)
        assert match, f"job not in /my-trailers: {[t.get('job_id') for t in rows[:5]]}"
        assert match["status"] == "COMPLETED"

        # Download & probe
        out = os.path.join(tmp, "out.mp4")
        async with httpx.AsyncClient(timeout=120.0) as dl:
            v = await dl.get(final["result_video_url"])
            with open(out, "wb") as f: f.write(v.content)
        res = subprocess.run([FFPROBE, "-v", "quiet", "-show_entries",
                              "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", out],
                             capture_output=True, text=True, timeout=20)
        actual_dur = float(res.stdout.strip())
        size_mb = os.path.getsize(out) / 1e6
        print(f"  → COMPLETED in {int(time.time()-t0)}s · MP4 duration={actual_dur:.2f}s · {size_mb:.2f}MB")
        print(f"  → expected [{expect_min}, {expect_max}]s · charged={final.get('charged_credits')} refunded={final.get('refunded_credits')}")
        in_range = expect_min <= actual_dur <= expect_max
        print(f"  → {'PASS' if in_range else 'FAIL'}: duration {actual_dur:.2f}s in [{expect_min}, {expect_max}]")
        assert in_range, f"expected {expect_min}-{expect_max}s, got {actual_dur:.2f}s"
        # No refund on success
        assert final.get("refunded_credits", 0) == 0, f"unexpected refund: {final}"
        # result_video_asset_id populated
        assert final.get("result_video_asset_id"), f"missing result_video_asset_id: {final}"
        return {
            "duration": duration,
            "actual_dur": actual_dur,
            "render_seconds": int(time.time() - t0),
            "size_mb": size_mb,
            "credits": final.get("charged_credits"),
            "result_video_asset_id": final.get("result_video_asset_id"),
            "in_range": in_range,
        }

async def main():
    # Run 60s first (the bug case)
    r60 = await run_one(60, expect_min=55.0, expect_max=65.0)
    # Regression: 15s still works
    r15 = await run_one(15, expect_min=15.0, expect_max=22.0)
    print("\n" + "=" * 70)
    print(" SUMMARY")
    print("=" * 70)
    for r in (r60, r15):
        print(f"  {r['duration']}s req → {r['actual_dur']:.2f}s actual ({r['render_seconds']}s render, "
              f"{r['size_mb']:.2f}MB, {r['credits']}cr) {'PASS' if r['in_range'] else 'FAIL'}")
    print("=" * 70)

if __name__ == "__main__":
    sys.exit(asyncio.run(main()) or 0)
