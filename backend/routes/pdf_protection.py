"""
PDF Protection Routes
======================
Secure PDF delivery with:
- PDF flattening (text to image conversion)
- Watermarking
- Signed download URLs
"""
import os
import io
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, get_current_user
from services.pdf_protection import protect_pdf, add_pdf_watermark, flatten_pdf_for_protection

router = APIRouter(prefix="/pdf-protection", tags=["pdf-protection"])


@router.get("/config")
async def get_pdf_protection_config():
    """Get PDF protection configuration"""
    return {
        "protection_features": [
            "watermarking",
            "flattening",
            "copy_protection"
        ],
        "watermark_format": "user_email | site_domain | date",
        "flatten_dpi": 150,
        "enabled": True
    }


@router.post("/protect")
async def protect_pdf_endpoint(
    pdf_id: str,
    flatten: bool = True,
    add_watermark: bool = True,
    user: dict = Depends(get_current_user)
):
    """
    Apply protection to a PDF document
    - flatten: Convert text to non-selectable format
    - add_watermark: Add user watermark to all pages
    """
    user_id = user.get("id")
    user_email = user.get("email", "user@example.com")
    
    # Get the PDF from storage
    pdf_record = await db.user_pdfs.find_one({
        "_id": pdf_id,
        "user_id": user_id
    })
    
    if not pdf_record:
        pdf_record = await db.generated_pdfs.find_one({
            "_id": pdf_id,
            "user_id": user_id
        })
    
    if not pdf_record:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    file_path = pdf_record.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    # Read original PDF
    with open(file_path, "rb") as f:
        pdf_bytes = f.read()
    
    # Apply protection
    protected_bytes = protect_pdf(
        pdf_bytes=pdf_bytes,
        user_email=user_email,
        flatten=flatten,
        add_watermark=add_watermark
    )
    
    # Generate filename
    original_name = pdf_record.get("filename", "document")
    protected_filename = f"protected_{original_name}.pdf"
    
    # Log protection
    await db.pdf_protection_logs.insert_one({
        "user_id": user_id,
        "pdf_id": pdf_id,
        "flatten": flatten,
        "watermark": add_watermark,
        "original_size": len(pdf_bytes),
        "protected_size": len(protected_bytes),
        "timestamp": datetime.now(timezone.utc)
    })
    
    # Return protected PDF
    return StreamingResponse(
        io.BytesIO(protected_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{protected_filename}"',
            "Content-Length": str(len(protected_bytes)),
            "Cache-Control": "no-store"
        }
    )


@router.post("/watermark-only")
async def watermark_pdf_only(
    pdf_id: str,
    user: dict = Depends(get_current_user)
):
    """Add watermark without flattening"""
    user_id = user.get("id")
    user_email = user.get("email", "user@example.com")
    
    pdf_record = await db.user_pdfs.find_one({"_id": pdf_id, "user_id": user_id})
    if not pdf_record:
        pdf_record = await db.generated_pdfs.find_one({"_id": pdf_id, "user_id": user_id})
    
    if not pdf_record:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    file_path = pdf_record.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    with open(file_path, "rb") as f:
        pdf_bytes = f.read()
    
    watermarked_bytes = add_pdf_watermark(pdf_bytes, user_email)
    
    return StreamingResponse(
        io.BytesIO(watermarked_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="watermarked_{pdf_record.get("filename", "document")}.pdf"',
            "Cache-Control": "no-store"
        }
    )


@router.post("/flatten-only")
async def flatten_pdf_only(
    pdf_id: str,
    user: dict = Depends(get_current_user)
):
    """Flatten PDF without watermark (copy protection only)"""
    user_id = user.get("id")
    
    pdf_record = await db.user_pdfs.find_one({"_id": pdf_id, "user_id": user_id})
    if not pdf_record:
        pdf_record = await db.generated_pdfs.find_one({"_id": pdf_id, "user_id": user_id})
    
    if not pdf_record:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    file_path = pdf_record.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    with open(file_path, "rb") as f:
        pdf_bytes = f.read()
    
    flattened_bytes = flatten_pdf_for_protection(pdf_bytes)
    
    return StreamingResponse(
        io.BytesIO(flattened_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="flattened_{pdf_record.get("filename", "document")}.pdf"',
            "Cache-Control": "no-store"
        }
    )


@router.get("/stats")
async def get_protection_stats(
    user: dict = Depends(get_current_user)
):
    """Get PDF protection statistics for user"""
    user_id = user.get("id")
    
    total_protected = await db.pdf_protection_logs.count_documents({"user_id": user_id})
    
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {
            "_id": None,
            "total_original_size": {"$sum": "$original_size"},
            "total_protected_size": {"$sum": "$protected_size"},
            "flatten_count": {"$sum": {"$cond": ["$flatten", 1, 0]}},
            "watermark_count": {"$sum": {"$cond": ["$watermark", 1, 0]}}
        }}
    ]
    
    stats = await db.pdf_protection_logs.aggregate(pipeline).to_list(1)
    
    return {
        "total_pdfs_protected": total_protected,
        "stats": stats[0] if stats else {},
        "user_id": user_id
    }
