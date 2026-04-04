"""
Packaging Service — assembles ZIP bundle from completed assets
ZIP failure must NOT block direct asset downloads.
"""
import io
import os
import uuid
import logging
import zipfile
from datetime import datetime, timezone

logger = logging.getLogger("viral.packaging")

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static", "generated", "viral_packs")


async def create_bundle(db, job_id: str) -> dict:
    """
    Assemble all assets for a job into a ZIP bundle.
    Returns {"zip_path": str, "zip_url": str, "success": bool}
    """
    os.makedirs(STATIC_DIR, exist_ok=True)

    assets = await db.viral_assets.find({"job_id": job_id}, {"_id": 0}).to_list(50)
    if not assets:
        logger.warning(f"[PACKAGING] No assets found for job {job_id}")
        return {"success": False, "zip_path": None, "zip_url": None}

    zip_filename = f"viral_pack_{job_id[:8]}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.zip"
    zip_path = os.path.join(STATIC_DIR, zip_filename)

    try:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for asset in assets:
                if asset.get("asset_type") == "zip_bundle":
                    continue
                fname = _asset_filename(asset)
                if asset.get("content"):
                    zf.writestr(fname, asset["content"])
                elif asset.get("file_path") and os.path.exists(asset["file_path"]):
                    zf.write(asset["file_path"], fname)

        with open(zip_path, "wb") as f:
            f.write(buf.getvalue())

        zip_url = f"/api/static/generated/viral_packs/{zip_filename}"
        logger.info(f"[PACKAGING] Bundle created: {zip_path} ({len(assets)} assets)")
        return {"success": True, "zip_path": zip_path, "zip_url": zip_url}

    except Exception as e:
        logger.error(f"[PACKAGING] ZIP creation failed: {e}")
        return {"success": False, "zip_path": None, "zip_url": None}


def _asset_filename(asset: dict) -> str:
    atype = asset.get("asset_type", "unknown")
    names = {
        "hooks": "01_viral_hooks.txt",
        "script": "02_video_script.md",
        "captions": "03_social_captions.txt",
        "thumbnail": "04_thumbnail.png",
    }
    return names.get(atype, f"{atype}.txt")
