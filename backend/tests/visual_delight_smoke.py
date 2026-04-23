"""
Visual Delight Sprint — Smoke Test
===================================
Generates 3 test stories (Kids / Action / Emotional) via the real
production pipeline and collects objective metrics to validate the new
Cinematic Motion Pack, pacing engine, audio ducking, and Safari-safe encode.

Usage (from /app/backend):
    python tests/visual_delight_smoke.py

Outputs:
    /app/test_reports/visual_delight_smoke_<timestamp>.json
"""
import os
import sys
import json
import time
import subprocess
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# Load backend .env so MongoDB is accessible
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from pymongo import MongoClient
_mongo = MongoClient(os.environ["MONGO_URL"])
_db = _mongo[os.environ["DB_NAME"]]

# Resolve backend URL from frontend .env (single source of truth)
FRONTEND_ENV = Path("/app/frontend/.env")
API_BASE = None
for line in FRONTEND_ENV.read_text().splitlines():
    if line.startswith("REACT_APP_BACKEND_URL="):
        API_BASE = line.split("=", 1)[1].strip()
        break
if not API_BASE:
    print("Cannot find REACT_APP_BACKEND_URL in /app/frontend/.env")
    sys.exit(1)

# Allow localhost fallback for smoke tests run inside the container
if os.environ.get("SMOKE_LOCAL") == "1":
    API_BASE = "http://localhost:8001"

ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"

TEST_CASES = [
    {
        "slug": "kids",
        "pacing_mode": "kids",
        "animation_style": "cartoon_2d",
        "age_group": "kids_5_8",
        "voice_preset": "narrator_warm",
        "title": "The Rainbow Bunny's Wiggle Party",
        "story_text": (
            "Once upon a time in a magical playground, there lived a silly little bunny with rainbow-colored ears. "
            "Every morning, the fluffy bunny would giggle with the tiny puppy next door and tickle the sleepy kitten. "
            "One bright bedtime evening, the bunny found a sparkling fairy sitting on a unicorn's horn. "
            "The fairy waved her magical wand and made the puppy wiggle, the kitten dance, and the bunny giggle until stars twinkled. "
            "Mommy rabbit called the bunny home, but the fairy promised another magical rainbow adventure tomorrow. "
            "The bunny hopped home, hugged daddy rabbit, and dreamed of the giggly fairy and her unicorn friends."
        ),
    },
    {
        "slug": "action",
        "pacing_mode": "action",
        "animation_style": "comic_book",
        "age_group": "kids_9_12",
        "voice_preset": "narrator_dramatic",
        "title": "The Warrior's Last Sprint",
        "story_text": (
            "The warrior clutched his sword as the storm exploded behind him — the ambush had begun. "
            "Arrows crashed into the rocks as he sprinted, heart pounding, through the narrow canyon escape. "
            "A pursuit party of shadow-knights thundered on black horses, their swords flashing in the lightning. "
            "He leapt across a collapsing bridge, the chase closing in as thunder and battle-cries tore the sky. "
            "With one final impossible leap, he crashed into the hidden fortress gate and sealed it before the hunters could breach. "
            "The battle was not over — but tonight, the warrior had escaped the danger and lived to fight another dawn."
        ),
    },
    {
        "slug": "emotional",
        "pacing_mode": "emotional",
        "animation_style": "watercolor",
        "age_group": "all_ages",
        "voice_preset": "narrator_calm",
        "title": "A Letter from Grandmother",
        "story_text": (
            "On the quietest morning of autumn, a tear fell on the old wooden table as the little girl read her grandmother's last letter. "
            "The letter whispered of summers lost, of promises her grandmother had kept, and of the love she carried in her gentle heart. "
            "The girl remembered her grandmother's embrace, the warmth of her hands, the way she always said goodbye without really leaving. "
            "She walked through the empty garden, feeling her grandmother's whisper in the wind and her hope in every leaf. "
            "At sunset, the girl sat by the old oak tree, and for the first time she forgave the goodbye — she knew love remains. "
            "A soft reunion of memory filled her heart as she folded the letter, and the evening light felt like grandmother's hand holding hers."
        ),
    },
]


def http_post(url: str, body: dict, token: str = None, timeout: int = 30) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def http_get(url: str, token: str = None, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, method="GET")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def login() -> str:
    r = http_post(f"{API_BASE}/api/auth/login", {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    return r["token"]


def ffprobe_metrics(local_path: str) -> dict:
    """Return duration, audio stream presence, codec, profile, faststart flag, etc."""
    out = {
        "duration_sec": None,
        "audio_present": False,
        "audio_codec": None,
        "audio_profile": None,
        "audio_channels": None,
        "audio_sample_rate": None,
        "video_codec": None,
        "video_resolution": None,
        "video_fps": None,
        "faststart": None,
        "file_size_bytes": None,
    }
    if not os.path.exists(local_path):
        return out
    out["file_size_bytes"] = os.path.getsize(local_path)

    # ffprobe via ffmpeg binary (symlinked -> imageio_ffmpeg)
    try:
        probe = subprocess.run(
            ["ffmpeg", "-i", local_path], capture_output=True, text=True, timeout=20
        )
        txt = probe.stderr
        import re
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", txt)
        if m:
            h, mm, ss = int(m.group(1)), int(m.group(2)), float(m.group(3))
            out["duration_sec"] = round(h * 3600 + mm * 60 + ss, 2)
        mv = re.search(r"Stream.*Video:\s*([a-z0-9]+).*?,\s*(\d+x\d+).*?,\s*(\d+(?:\.\d+)?)\s*fps", txt)
        if mv:
            out["video_codec"] = mv.group(1)
            out["video_resolution"] = mv.group(2)
            out["video_fps"] = float(mv.group(3))
        ma = re.search(r"Stream.*Audio:\s*([a-z0-9]+)(?:\s*\(([A-Za-z]+)\))?.*?,\s*(\d+)\s*Hz,\s*(\w+)", txt)
        if ma:
            out["audio_present"] = True
            out["audio_codec"] = ma.group(1)
            out["audio_profile"] = ma.group(2)
            out["audio_sample_rate"] = int(ma.group(3))
            out["audio_channels"] = ma.group(4)
    except Exception as e:
        out["probe_error"] = str(e)

    # Detect +faststart by checking moov atom position
    try:
        with open(local_path, "rb") as f:
            head = f.read(1024 * 256)  # first 256KB
        out["faststart"] = b"moov" in head
    except Exception:
        pass

    return out


def resolve_local_path(output_url: str) -> str:
    """Given the API-returned output_url, return the local filesystem path."""
    if not output_url:
        return ""
    if output_url.startswith("/static/"):
        return f"/app/backend{output_url}"
    if output_url.startswith("http"):
        # Download R2/CDN URL
        local = f"/tmp/delight_probe_{int(time.time())}.mp4"
        try:
            urllib.request.urlretrieve(output_url, local)
            return local
        except Exception:
            return ""
    return ""


def run_test_case(token: str, case: dict) -> dict:
    t0 = time.time()
    payload = {
        "title": case["title"],
        "story_text": case["story_text"],
        "animation_style": case["animation_style"],
        "age_group": case["age_group"],
        "voice_preset": case["voice_preset"],
        "include_watermark": False,
        "pacing_mode": case["pacing_mode"],
    }
    print(f"\n[{case['slug'].upper()}] Creating pipeline job (pacing={case['pacing_mode']})...")

    result = {
        "slug": case["slug"],
        "title": case["title"],
        "pacing_mode": case["pacing_mode"],
        "animation_style": case["animation_style"],
        "submitted_at": datetime.utcnow().isoformat() + "Z",
    }
    try:
        create = http_post(f"{API_BASE}/api/pipeline/create", payload, token=token, timeout=60)
    except urllib.error.HTTPError as e:
        result["error"] = f"HTTP {e.code}: {e.read().decode('utf-8')[:500]}"
        return result
    except Exception as e:
        result["error"] = f"create failed: {e}"
        return result

    job_id = create.get("job_id")
    if not job_id:
        result["error"] = f"No job_id in response: {create}"
        return result
    result["job_id"] = job_id
    result["credits_charged"] = create.get("credits_charged")
    result["estimated_scenes"] = create.get("estimated_scenes")
    print(f"[{case['slug'].upper()}] job_id={job_id[:12]} scenes={result['estimated_scenes']} credits={result['credits_charged']}")

    # Poll
    deadline = time.time() + 600  # 10 min max
    last_status = None
    last_stage = None
    last_progress = -1
    fallbacks_detected = []
    while time.time() < deadline:
        time.sleep(5)
        try:
            resp = http_get(f"{API_BASE}/api/pipeline/status/{job_id}", token=token, timeout=20)
            job = resp.get("job", resp)
        except Exception as e:
            print(f"  poll error: {e}")
            continue
        status = job.get("status")
        stage = job.get("current_stage") or job.get("current_step", "")
        progress = job.get("progress", 0)
        if status != last_status or progress != last_progress:
            print(f"  [{case['slug'][:3]}] status={status} progress={progress}% stage={stage[:60] if stage else ''}")
            last_status = status
            last_progress = progress
            last_stage = stage
        if status in ("COMPLETED", "FAILED"):
            result["final_status"] = status
            result["error"] = job.get("error")
            result["output_url"] = job.get("output_url")
            # Pull render_path directly from Mongo (not exposed via public endpoint)
            full = _db.pipeline_jobs.find_one({"job_id": job_id}, {"_id": 0})
            if full:
                result["render_path"] = full.get("render_path")
                result["total_scenes_emitted"] = len(full.get("scenes") or [])
                result["motion_plan"] = full.get("motion_plan")
                result["pacing_profile_used"] = full.get("pacing_mode")
                result["timing"] = full.get("timing") or {}
                result["validation_failures"] = full.get("validation_failures") or []
                result["diagnostics"] = full.get("diagnostics") or {}
            break
    else:
        result["final_status"] = "TIMEOUT"

    result["wall_clock_sec"] = round(time.time() - t0, 2)

    # Probe the output file
    if result.get("final_status") == "COMPLETED":
        local = result.get("render_path") or resolve_local_path(result.get("output_url") or "")
        result["probed_path"] = local
        metrics = ffprobe_metrics(local)
        result["probe"] = metrics

    return result


def main():
    print(f"API={API_BASE}")
    token = login()
    print(f"✓ Logged in as {ADMIN_EMAIL}")

    report = {
        "started_at": datetime.utcnow().isoformat() + "Z",
        "api_base": API_BASE,
        "cases": [],
    }
    for case in TEST_CASES:
        case_result = run_test_case(token, case)
        report["cases"].append(case_result)

    report["finished_at"] = datetime.utcnow().isoformat() + "Z"

    out_dir = Path("/app/test_reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"visual_delight_smoke_{int(time.time())}.json"
    out_path.write_text(json.dumps(report, indent=2, default=str))
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"REPORT: {out_path}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    for c in report["cases"]:
        p = c.get("probe", {})
        print(
            f"[{c['slug']:>9}] status={c.get('final_status'):>10} "
            f"scenes={c.get('total_scenes_emitted', '?'):>2}  "
            f"dur={p.get('duration_sec', '?'):>6}s  "
            f"size={round((p.get('file_size_bytes') or 0)/1024/1024, 2):>6}MB  "
            f"audio={p.get('audio_codec')}/{p.get('audio_profile')}/{p.get('audio_channels')}  "
            f"faststart={p.get('faststart')}  "
            f"wall={c.get('wall_clock_sec')}s"
        )
    return report


if __name__ == "__main__":
    main()
