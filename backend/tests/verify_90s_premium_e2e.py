"""Real 90s premium-tier e2e — proves a Premium user can render a 90s
trailer end-to-end and the final MP4 falls within the 85-95s acceptance
window. Run on demand; not part of the fast suite."""
import os, asyncio, time, subprocess, tempfile, sys, json as _json
import httpx

BACKEND = "http://localhost:8001"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASS  = "Cr3@t0rStud!o#2026"
FFMPEG = "/usr/bin/ffmpeg"
FFPROBE = "/usr/bin/ffprobe"

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

async def main():
    tmp = tempfile.mkdtemp(prefix="e2e_90s_")
    photo = os.path.join(tmp, "hero.png")
    gen_test_photo(photo)

    async with httpx.AsyncClient(base_url=BACKEND, timeout=300.0) as c:
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
            "duration_target_seconds": 90})
        assert r.status_code in (200, 201), f"create job 90s: {r.status_code} {r.text}"
        job_id = r.json()["job_id"]; estimated = r.json()["estimated_credits"]
        print(f"job={job_id} estimated_credits={estimated}")
        assert estimated == 60, f"90s should cost 60 credits, got {estimated}"

        t0 = time.time(); final = None; last_stage = None
        while time.time() - t0 < 360:
            sr = await c.get(f"/api/photo-trailer/jobs/{job_id}", headers=H)
            if sr.status_code == 200:
                j = sr.json()
                stg = j.get("current_stage")
                if stg != last_stage:
                    print(f"  [{int(time.time()-t0):3}s] stage={stg} status={j.get('status')}")
                    last_stage = stg
                if j.get("status") in ("COMPLETED", "FAILED"):
                    final = j; break
            await asyncio.sleep(3)

        assert final, "didn't complete within 360s"
        assert final["status"] == "COMPLETED", f"FAILED: {final.get('error_code')} {final.get('error_message')}"
        assert final.get("plan_tier_at_creation") == "PREMIUM", f"plan_tier missing: {final.get('plan_tier_at_creation')}"

        out = os.path.join(tmp, "trailer.mp4")
        async with httpx.AsyncClient(timeout=120.0) as dl:
            v = await dl.get(final["result_video_url"])
            with open(out, "wb") as f: f.write(v.content)

        res = subprocess.run([FFPROBE, "-v", "quiet", "-show_entries",
                              "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", out],
                             capture_output=True, text=True, timeout=20)
        actual = float(res.stdout.strip())
        size_mb = os.path.getsize(out) / 1e6
        in_range = 85.0 <= actual <= 95.0
        print()
        print("=" * 60)
        print(f"  90s job render time:        {int(time.time()-t0)}s")
        print(f"  Final MP4 duration:         {actual:.2f}s  (target [85, 95])")
        print(f"  Output size:                {size_mb:.2f} MB")
        print(f"  plan_tier_at_creation:      {final.get('plan_tier_at_creation')}")
        print(f"  is_priority:                {final.get('is_priority')}")
        print(f"  charged_credits:            {final.get('charged_credits')}")
        print(f"  refunded_credits:           {final.get('refunded_credits', 0)}")
        print("=" * 60)
        if in_range:
            print(" ✅ 90s PREMIUM e2e PASSED")
        else:
            print(f" ❌ FAILED: duration {actual:.2f}s outside [85, 95]")
        return 0 if in_range else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()) or 0)
