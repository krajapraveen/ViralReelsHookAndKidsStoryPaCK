"""
PDF Protection Service
- PDF flattening (convert text to non-selectable)
- Watermarking
- Copy protection
"""
import io
from datetime import datetime, timezone
from typing import Optional
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color
from PyPDF2 import PdfReader, PdfWriter

def add_pdf_watermark(
    pdf_bytes: bytes,
    user_email: str,
    site_domain: str = "visionary-suite.com"
) -> bytes:
    """Add watermark to PDF pages"""
    try:
        # Read original PDF
        reader = PdfReader(io.BytesIO(pdf_bytes))
        writer = PdfWriter()
        
        # Create watermark
        watermark_buffer = io.BytesIO()
        c = canvas.Canvas(watermark_buffer, pagesize=letter)
        
        # Watermark text
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        watermark_text = f"Generated for {user_email} | {site_domain} | {date_str}"
        
        # Semi-transparent watermark
        c.setFillColor(Color(0.5, 0.5, 0.5, alpha=0.3))
        c.setFont("Helvetica", 10)
        
        # Bottom watermark
        c.drawString(50, 30, watermark_text)
        
        # Diagonal repeating watermark
        c.setFillColor(Color(0.5, 0.5, 0.5, alpha=0.08))
        c.setFont("Helvetica", 14)
        
        for y in range(0, 800, 100):
            for x in range(-200, 800, 200):
                c.saveState()
                c.translate(x, y)
                c.rotate(45)
                c.drawString(0, 0, site_domain)
                c.restoreState()
        
        c.save()
        
        # Read watermark PDF
        watermark_buffer.seek(0)
        watermark_pdf = PdfReader(watermark_buffer)
        watermark_page = watermark_pdf.pages[0]
        
        # Apply watermark to each page
        for page in reader.pages:
            page.merge_page(watermark_page)
            writer.add_page(page)
        
        # Output
        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()
        
    except Exception as e:
        print(f"PDF watermark error: {e}")
        return pdf_bytes

def flatten_pdf_for_protection(pdf_bytes: bytes) -> bytes:
    """
    Flatten PDF to make text non-selectable
    Converts text layers to image-like format
    """
    try:
        from pdf2image import convert_from_bytes
        from PIL import Image
        
        # Convert PDF pages to images
        images = convert_from_bytes(pdf_bytes, dpi=150)
        
        # Create new PDF from images
        output = io.BytesIO()
        
        if images:
            # Convert first image to PDF
            first_image = images[0].convert('RGB')
            
            if len(images) > 1:
                # Multiple pages
                other_images = [img.convert('RGB') for img in images[1:]]
                first_image.save(output, 'PDF', save_all=True, append_images=other_images)
            else:
                first_image.save(output, 'PDF')
        
        return output.getvalue()
        
    except ImportError:
        # pdf2image not available, return original with watermark note
        print("pdf2image not available for flattening")
        return pdf_bytes
    except Exception as e:
        print(f"PDF flatten error: {e}")
        return pdf_bytes

def protect_pdf(
    pdf_bytes: bytes,
    user_email: str,
    flatten: bool = True,
    add_watermark: bool = True
) -> bytes:
    """Apply full PDF protection"""
    result = pdf_bytes
    
    # First add watermark
    if add_watermark:
        result = add_pdf_watermark(result, user_email)
    
    # Then flatten (makes text non-selectable)
    if flatten:
        result = flatten_pdf_for_protection(result)
    
    return result
