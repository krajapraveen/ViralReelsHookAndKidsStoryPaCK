"""Generate thumbnails for all gallery videos using ffmpeg."""
import os
import sys
import boto3
import subprocess
import tempfile
from botocore.config import Config
from pymongo import MongoClient

# R2 config
R2_ACCOUNT_ID = "77f89e95431bdd21ae580784bffb6db1"
R2_ACCESS_KEY = "3cb01c5dafa23aa1b309979d1096e81c"
R2_SECRET_KEY = "88d49cabeb0b0a2b27cd28a2e96b9dfb430cbb4bbf74eb5909e82a21398bc1b6"
R2_BUCKET = "visionary-suite-assets-prod"
R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
R2_PUBLIC_URL = "https://pub-c251248e414545848d34b8c1b97ecdb3.r2.dev"

client = boto3.client(
    's3',
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    config=Config(signature_version='s3v4'),
    region_name='auto'
)

db = MongoClient('mongodb://localhost:27017')['creatorstudio_production']

jobs = list(db.pipeline_jobs.find(
    {"status": "COMPLETED", "output_url": {"$exists": True, "$ne": None}},
    {"_id": 0, "job_id": 1, "title": 1, "output_url": 1}
).sort("completed_at", -1))

print(f"Processing {len(jobs)} videos...")

success_count = 0
fail_count = 0

for i, job in enumerate(jobs):
    job_id = job["job_id"]
    title = job["title"]
    output_url = job["output_url"]
    
    # Extract R2 key from output_url
    if ".r2.dev/" in output_url:
        r2_key = output_url.split(".r2.dev/")[1]
    else:
        print(f"  [{i+1}] SKIP: Unknown URL format for '{title}'")
        fail_count += 1
        continue
    
    print(f"  [{i+1}/{len(jobs)}] Processing '{title}'...", end=" ", flush=True)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "video.mp4")
        thumb_path = os.path.join(tmpdir, "thumb.jpg")
        
        # Download video
        try:
            client.download_file(R2_BUCKET, r2_key, video_path)
        except Exception as e:
            print(f"DOWNLOAD FAILED: {e}")
            fail_count += 1
            continue
        
        # Extract frame at 1 second using ffmpeg
        try:
            result = subprocess.run(
                ["ffmpeg", "-i", video_path, "-ss", "1", "-vframes", "1", 
                 "-q:v", "2", "-y", thumb_path],
                capture_output=True, timeout=30
            )
            if not os.path.exists(thumb_path) or os.path.getsize(thumb_path) == 0:
                # Try at 0 seconds if 1 second fails
                subprocess.run(
                    ["ffmpeg", "-i", video_path, "-ss", "0", "-vframes", "1",
                     "-q:v", "2", "-y", thumb_path],
                    capture_output=True, timeout=30
                )
        except Exception as e:
            print(f"FFMPEG FAILED: {e}")
            fail_count += 1
            continue
        
        if not os.path.exists(thumb_path) or os.path.getsize(thumb_path) == 0:
            print("THUMB EMPTY")
            fail_count += 1
            continue
        
        # Upload thumbnail to R2
        thumb_key = f"thumbnails/{job_id}/thumb.jpg"
        try:
            client.upload_file(
                thumb_path, R2_BUCKET, thumb_key,
                ExtraArgs={
                    "ContentType": "image/jpeg",
                    "CacheControl": "public, max-age=86400"
                }
            )
        except Exception as e:
            print(f"UPLOAD FAILED: {e}")
            fail_count += 1
            continue
        
        # Store thumbnail URL (public URL) in DB
        thumb_url = f"{R2_PUBLIC_URL}/{thumb_key}"
        db.pipeline_jobs.update_one(
            {"job_id": job_id},
            {"$set": {"thumbnail_url": thumb_url}}
        )
        
        thumb_size = os.path.getsize(thumb_path)
        print(f"OK ({thumb_size} bytes)")
        success_count += 1

print(f"\nDone! {success_count} thumbnails generated, {fail_count} failed")
