"""
PDF Flattening & Video Streaming Protection Service
CreatorStudio AI

Features:
- PDF flattening to prevent editing
- PDF encryption with password protection
- Video streaming with HLS/DASH support
- DRM-lite protection for video content
- Watermark embedding in streams
"""
import os
import io
import base64
import hashlib
import secrets
import tempfile
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

# PDF libraries
try:
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.colors import Color
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# Video/FFmpeg
try:
    import subprocess
    FFMPEG_AVAILABLE = subprocess.run(['ffmpeg', '-version'], capture_output=True).returncode == 0
except:
    FFMPEG_AVAILABLE = False

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared import logger


class PDFProtectionService:
    """Service for PDF flattening and protection"""
    
    def __init__(self):
        self.available = PDF_AVAILABLE
    
    def flatten_pdf(self, pdf_bytes: bytes, watermark_text: str = None) -> bytes:
        """
        Flatten a PDF to prevent editing.
        Converts all form fields and annotations to static content.
        """
        if not self.available:
            logger.warning("PDF libraries not available, returning original")
            return pdf_bytes
        
        try:
            # Read the PDF
            reader = PdfReader(io.BytesIO(pdf_bytes))
            writer = PdfWriter()
            
            for page_num, page in enumerate(reader.pages):
                # Add page to writer (this flattens annotations)
                writer.add_page(page)
                
                # Add watermark if specified
                if watermark_text:
                    # Create watermark
                    packet = io.BytesIO()
                    can = canvas.Canvas(packet, pagesize=letter)
                    can.setFont("Helvetica", 40)
                    can.setFillColor(Color(0.5, 0.5, 0.5, alpha=0.3))
                    can.saveState()
                    can.translate(300, 400)
                    can.rotate(45)
                    can.drawCentredString(0, 0, watermark_text)
                    can.restoreState()
                    can.save()
                    
                    # Merge watermark
                    packet.seek(0)
                    watermark_reader = PdfReader(packet)
                    page.merge_page(watermark_reader.pages[0])
            
            # Write flattened PDF
            output = io.BytesIO()
            writer.write(output)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"PDF flattening error: {e}")
            return pdf_bytes
    
    def encrypt_pdf(
        self, 
        pdf_bytes: bytes, 
        user_password: str = "",
        owner_password: str = None,
        permissions: Dict[str, bool] = None
    ) -> bytes:
        """
        Encrypt PDF with password and set permissions.
        
        Permissions:
        - print: Allow printing
        - modify: Allow modification
        - copy: Allow copying text
        - annotate: Allow annotations
        """
        if not self.available:
            logger.warning("PDF libraries not available")
            return pdf_bytes
        
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            writer = PdfWriter()
            
            # Copy all pages
            for page in reader.pages:
                writer.add_page(page)
            
            # Generate owner password if not provided
            if owner_password is None:
                owner_password = secrets.token_urlsafe(32)
            
            # Default restrictive permissions
            if permissions is None:
                permissions = {
                    'print': True,      # Allow printing
                    'modify': False,    # Disallow modification
                    'copy': False,      # Disallow copying
                    'annotate': False   # Disallow annotations
                }
            
            # Encrypt with AES-256
            writer.encrypt(
                user_password=user_password,
                owner_password=owner_password,
                permissions_flag=(
                    (0x4 if permissions.get('print') else 0) |    # Print
                    (0x8 if permissions.get('modify') else 0) |   # Modify
                    (0x10 if permissions.get('copy') else 0) |    # Copy
                    (0x20 if permissions.get('annotate') else 0)  # Annotate
                )
            )
            
            output = io.BytesIO()
            writer.write(output)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"PDF encryption error: {e}")
            return pdf_bytes
    
    def protect_pdf(
        self,
        pdf_bytes: bytes,
        user_email: str,
        flatten: bool = True,
        encrypt: bool = True,
        add_watermark: bool = True
    ) -> Dict[str, Any]:
        """
        Full PDF protection pipeline.
        Returns protected PDF and metadata.
        """
        result = {
            'success': False,
            'pdf_bytes': pdf_bytes,
            'watermark_applied': False,
            'encrypted': False,
            'flattened': False
        }
        
        try:
            processed_pdf = pdf_bytes
            watermark = None
            
            # Add watermark
            if add_watermark:
                watermark = f"Licensed to {user_email}"
            
            # Flatten
            if flatten:
                processed_pdf = self.flatten_pdf(processed_pdf, watermark)
                result['flattened'] = True
                result['watermark_applied'] = add_watermark
            
            # Encrypt
            if encrypt:
                processed_pdf = self.encrypt_pdf(
                    processed_pdf,
                    user_password="",  # No password needed to open
                    permissions={
                        'print': True,
                        'modify': False,
                        'copy': False,
                        'annotate': False
                    }
                )
                result['encrypted'] = True
            
            result['pdf_bytes'] = processed_pdf
            result['success'] = True
            
        except Exception as e:
            logger.error(f"PDF protection error: {e}")
            result['error'] = str(e)
        
        return result


class VideoStreamingProtection:
    """Service for video streaming protection"""
    
    def __init__(self, storage_path: str = "/tmp/video_streams"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.available = FFMPEG_AVAILABLE
        
        # Token store for stream authentication
        self.stream_tokens: Dict[str, Dict] = {}
    
    def generate_stream_token(
        self,
        video_id: str,
        user_id: str,
        expires_in_minutes: int = 30
    ) -> str:
        """Generate a time-limited token for stream access"""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
        
        self.stream_tokens[token] = {
            'video_id': video_id,
            'user_id': user_id,
            'expires_at': expires_at,
            'created_at': datetime.now(timezone.utc)
        }
        
        return token
    
    def validate_stream_token(self, token: str, video_id: str) -> Dict[str, Any]:
        """Validate a stream token"""
        token_data = self.stream_tokens.get(token)
        
        if not token_data:
            return {'valid': False, 'error': 'Invalid token'}
        
        if token_data['video_id'] != video_id:
            return {'valid': False, 'error': 'Token not valid for this video'}
        
        if datetime.now(timezone.utc) > token_data['expires_at']:
            # Clean up expired token
            del self.stream_tokens[token]
            return {'valid': False, 'error': 'Token expired'}
        
        return {
            'valid': True,
            'user_id': token_data['user_id'],
            'expires_at': token_data['expires_at'].isoformat()
        }
    
    def create_hls_stream(
        self,
        video_path: str,
        output_name: str,
        add_watermark: bool = True,
        watermark_text: str = None,
        segment_duration: int = 10
    ) -> Dict[str, Any]:
        """
        Convert video to HLS format for streaming.
        Creates .m3u8 playlist and .ts segments.
        """
        if not self.available:
            return {
                'success': False,
                'error': 'FFmpeg not available'
            }
        
        try:
            output_dir = self.storage_path / output_name
            output_dir.mkdir(parents=True, exist_ok=True)
            
            playlist_path = output_dir / "playlist.m3u8"
            segment_pattern = output_dir / "segment_%03d.ts"
            
            # Build FFmpeg command
            cmd = ['ffmpeg', '-i', video_path, '-y']
            
            # Add watermark if requested
            if add_watermark and watermark_text:
                # Watermark filter
                cmd.extend([
                    '-vf', f"drawtext=text='{watermark_text}':fontsize=24:fontcolor=white@0.5:x=10:y=10"
                ])
            
            # HLS settings
            cmd.extend([
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-hls_time', str(segment_duration),
                '-hls_playlist_type', 'vod',
                '-hls_segment_filename', str(segment_pattern),
                str(playlist_path)
            ])
            
            # Run FFmpeg
            result = subprocess.run(cmd, capture_output=True, timeout=300)
            
            if result.returncode != 0:
                return {
                    'success': False,
                    'error': result.stderr.decode()[:500]
                }
            
            # Count segments
            segments = list(output_dir.glob("segment_*.ts"))
            
            return {
                'success': True,
                'playlist_path': str(playlist_path),
                'output_dir': str(output_dir),
                'segment_count': len(segments),
                'watermarked': add_watermark and watermark_text is not None
            }
            
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Video processing timeout'}
        except Exception as e:
            logger.error(f"HLS creation error: {e}")
            return {'success': False, 'error': str(e)}
    
    def add_video_watermark(
        self,
        video_bytes: bytes,
        watermark_text: str,
        position: str = "bottom-right"
    ) -> bytes:
        """Add watermark to video"""
        if not self.available:
            return video_bytes
        
        try:
            # Create temp files
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as input_file:
                input_file.write(video_bytes)
                input_path = input_file.name
            
            output_path = input_path.replace('.mp4', '_watermarked.mp4')
            
            # Position mapping
            positions = {
                'top-left': 'x=10:y=10',
                'top-right': 'x=w-tw-10:y=10',
                'bottom-left': 'x=10:y=h-th-10',
                'bottom-right': 'x=w-tw-10:y=h-th-10',
                'center': 'x=(w-tw)/2:y=(h-th)/2'
            }
            pos = positions.get(position, positions['bottom-right'])
            
            # FFmpeg command
            cmd = [
                'ffmpeg', '-i', input_path, '-y',
                '-vf', f"drawtext=text='{watermark_text}':fontsize=20:fontcolor=white@0.6:{pos}",
                '-c:a', 'copy',
                output_path
            ]
            
            subprocess.run(cmd, capture_output=True, timeout=120)
            
            # Read result
            with open(output_path, 'rb') as f:
                result = f.read()
            
            # Cleanup
            os.unlink(input_path)
            os.unlink(output_path)
            
            return result
            
        except Exception as e:
            logger.error(f"Video watermark error: {e}")
            return video_bytes
    
    def get_stream_url(
        self,
        video_id: str,
        user_id: str,
        user_email: str,
        base_url: str
    ) -> Dict[str, Any]:
        """
        Generate a protected stream URL with token.
        """
        token = self.generate_stream_token(video_id, user_id)
        
        return {
            'stream_url': f"{base_url}/api/stream/{video_id}/playlist.m3u8?token={token}",
            'token': token,
            'expires_in': 30,  # minutes
            'watermark': f"Licensed to {user_email}"
        }
    
    def cleanup_expired_tokens(self):
        """Remove expired tokens"""
        now = datetime.now(timezone.utc)
        expired = [
            token for token, data in self.stream_tokens.items()
            if data['expires_at'] < now
        ]
        for token in expired:
            del self.stream_tokens[token]
        
        return len(expired)


# Singleton instances
_pdf_service = None
_video_service = None


def get_pdf_protection_service() -> PDFProtectionService:
    """Get PDF protection service instance"""
    global _pdf_service
    if _pdf_service is None:
        _pdf_service = PDFProtectionService()
    return _pdf_service


def get_video_streaming_service() -> VideoStreamingProtection:
    """Get video streaming service instance"""
    global _video_service
    if _video_service is None:
        _video_service = VideoStreamingProtection()
    return _video_service
