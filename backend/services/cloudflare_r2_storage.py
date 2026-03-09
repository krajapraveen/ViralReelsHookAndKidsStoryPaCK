"""
Cloudflare R2 Storage Service - Performance Optimized
Handles all file uploads/downloads for Visionary Suite assets (images, audio, video)

Performance Features:
- Presigned URLs for direct browser upload/download (bypasses backend)
- Multipart upload for large files (>5MB)
- Detailed timing logs for performance monitoring
- Cache-optimized headers for CDN acceleration
"""
import os
import boto3
import uuid
import logging
import aiofiles
import asyncio
import time
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from botocore.config import Config
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# R2 Configuration from environment
R2_ACCOUNT_ID = os.environ.get("CLOUDFLARE_R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.environ.get("CLOUDFLARE_R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.environ.get("CLOUDFLARE_R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.environ.get("CLOUDFLARE_R2_BUCKET_NAME", "visionary-suite-assets-prod")
R2_PUBLIC_URL = os.environ.get("CLOUDFLARE_R2_PUBLIC_URL", "")
R2_CUSTOM_DOMAIN = os.environ.get("CLOUDFLARE_R2_CUSTOM_DOMAIN", "")  # For CDN caching
R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

# Multipart upload threshold (5MB)
MULTIPART_THRESHOLD = 5 * 1024 * 1024
MULTIPART_CHUNK_SIZE = 5 * 1024 * 1024

# Asset paths in bucket
ASSET_PATHS = {
    "image": "images",
    "audio": "audio", 
    "voice": "audio/voices",
    "video": "videos",
    "music": "audio/music",
    "thumbnail": "thumbnails"
}

# Cache durations by asset type (in seconds)
CACHE_DURATIONS = {
    "image": 31536000,      # 1 year - images are immutable
    "audio": 31536000,      # 1 year
    "voice": 31536000,      # 1 year
    "video": 31536000,      # 1 year - final videos are immutable
    "music": 31536000,      # 1 year
    "thumbnail": 86400      # 1 day - thumbnails might change
}


class PerformanceTimer:
    """Context manager for timing operations"""
    def __init__(self, operation_name: str, logger_func=None):
        self.operation_name = operation_name
        self.logger_func = logger_func or logger.info
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, *args):
        self.end_time = time.time()
        duration_ms = (self.end_time - self.start_time) * 1000
        self.logger_func(f"⏱️ TIMING [{self.operation_name}]: {duration_ms:.2f}ms")
    
    @property
    def duration_ms(self):
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time) * 1000
        return 0


class CloudflareR2Storage:
    """Cloudflare R2 Storage client with performance optimizations"""
    
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the S3 client for R2"""
        if not all([R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY]):
            logger.warning("Cloudflare R2 credentials not fully configured")
            return
        
        try:
            self._client = boto3.client(
                's3',
                endpoint_url=R2_ENDPOINT,
                aws_access_key_id=R2_ACCESS_KEY_ID,
                aws_secret_access_key=R2_SECRET_ACCESS_KEY,
                config=Config(
                    signature_version='s3v4',
                    retries={'max_attempts': 3, 'mode': 'adaptive'},
                    max_pool_connections=50  # Increase connection pool for parallel uploads
                ),
                region_name='auto'
            )
            logger.info(f"Cloudflare R2 client initialized for bucket: {R2_BUCKET_NAME}")
        except Exception as e:
            logger.error(f"Failed to initialize R2 client: {e}")
            self._client = None
    
    @property
    def is_configured(self) -> bool:
        """Check if R2 is properly configured"""
        return self._client is not None and bool(R2_PUBLIC_URL)
    
    def _get_asset_key(self, asset_type: str, filename: str, project_id: str = None) -> str:
        """Generate the S3 key for an asset"""
        base_path = ASSET_PATHS.get(asset_type, "misc")
        if project_id:
            return f"{base_path}/{project_id}/{filename}"
        return f"{base_path}/{filename}"
    
    def _get_public_url(self, key: str) -> str:
        """Get the public URL for an asset - prefers custom domain for CDN caching"""
        # Prefer custom domain for CDN acceleration
        if R2_CUSTOM_DOMAIN:
            return f"https://{R2_CUSTOM_DOMAIN}/{key}"
        if R2_PUBLIC_URL:
            return f"{R2_PUBLIC_URL.rstrip('/')}/{key}"
        return f"{R2_ENDPOINT}/{R2_BUCKET_NAME}/{key}"
    
    def _get_content_type(self, filename: str) -> str:
        """Determine content type from filename"""
        ext = Path(filename).suffix.lower()
        content_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.webp': 'image/webp',
            '.gif': 'image/gif',
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.ogg': 'audio/ogg',
            '.mp4': 'video/mp4',
            '.webm': 'video/webm',
            '.mov': 'video/quicktime'
        }
        return content_types.get(ext, 'application/octet-stream')
    
    def _get_cache_control(self, asset_type: str) -> str:
        """Get cache-control header for asset type"""
        duration = CACHE_DURATIONS.get(asset_type, 86400)
        return f"public, max-age={duration}, immutable"
    
    # ==========================================
    # PRESIGNED URL METHODS (Direct Browser Access)
    # ==========================================
    
    def generate_presigned_upload_url(
        self,
        asset_type: str,
        filename: str,
        project_id: str = None,
        expiration: int = 3600,
        content_type: str = None
    ) -> Dict[str, Any]:
        """
        Generate a presigned URL for direct browser upload to R2.
        This bypasses the backend for large file uploads.
        
        Returns:
            {
                'upload_url': str,  # URL for PUT request
                'public_url': str,  # URL to access after upload
                'key': str,         # S3 key
                'expires_in': int   # Seconds until expiration
            }
        """
        if not self._client:
            return None
        
        with PerformanceTimer("generate_presigned_upload_url"):
            try:
                unique_id = str(uuid.uuid4())[:8]
                safe_filename = f"{Path(filename).stem}_{unique_id}{Path(filename).suffix}"
                key = self._get_asset_key(asset_type, safe_filename, project_id)
                
                content_type = content_type or self._get_content_type(filename)
                
                presigned_url = self._client.generate_presigned_url(
                    'put_object',
                    Params={
                        'Bucket': R2_BUCKET_NAME,
                        'Key': key,
                        'ContentType': content_type,
                        'CacheControl': self._get_cache_control(asset_type)
                    },
                    ExpiresIn=expiration
                )
                
                return {
                    'upload_url': presigned_url,
                    'public_url': self._get_public_url(key),
                    'key': key,
                    'content_type': content_type,
                    'expires_in': expiration
                }
            except Exception as e:
                logger.error(f"Failed to generate presigned upload URL: {e}")
                return None
    
    def generate_presigned_download_url(
        self,
        key: str,
        expiration: int = 3600,
        filename: str = None
    ) -> str:
        """
        Generate a presigned URL for direct browser download from R2.
        Use this for private files or when custom domain is not set up.
        
        For public files with custom domain, use _get_public_url() instead.
        """
        if not self._client:
            return None
        
        with PerformanceTimer("generate_presigned_download_url"):
            try:
                params = {
                    'Bucket': R2_BUCKET_NAME,
                    'Key': key
                }
                
                # Add Content-Disposition for download with filename
                if filename:
                    params['ResponseContentDisposition'] = f'attachment; filename="{filename}"'
                
                return self._client.generate_presigned_url(
                    'get_object',
                    Params=params,
                    ExpiresIn=expiration
                )
            except Exception as e:
                logger.error(f"Failed to generate presigned download URL: {e}")
                return None
    
    # ==========================================
    # MULTIPART UPLOAD (Large Files)
    # ==========================================
    
    async def upload_file_multipart(
        self,
        file_path: str,
        asset_type: str,
        project_id: str = None,
        custom_filename: str = None,
        progress_callback = None
    ) -> Tuple[bool, str, str]:
        """
        Upload a large file using multipart upload for better performance.
        
        Args:
            file_path: Local path to the file
            asset_type: Type of asset (image, audio, voice, video)
            project_id: Optional project ID
            custom_filename: Optional custom filename
            progress_callback: Optional async callback(uploaded_bytes, total_bytes)
        
        Returns:
            Tuple of (success, public_url, key)
        """
        if not self._client:
            return False, "", ""
        
        total_timing = {"start": time.time()}
        
        try:
            file_size = os.path.getsize(file_path)
            
            # Use simple upload for small files
            if file_size < MULTIPART_THRESHOLD:
                logger.info(f"File {file_path} is small ({file_size} bytes), using simple upload")
                return await self.upload_file(file_path, asset_type, project_id, custom_filename)
            
            logger.info(f"Starting multipart upload for {file_path} ({file_size} bytes)")
            
            # Generate key
            original_name = Path(file_path).name
            ext = Path(file_path).suffix
            if custom_filename:
                filename = custom_filename
            else:
                unique_id = str(uuid.uuid4())[:8]
                filename = f"{Path(original_name).stem}_{unique_id}{ext}"
            
            key = self._get_asset_key(asset_type, filename, project_id)
            content_type = self._get_content_type(filename)
            
            # Initiate multipart upload
            with PerformanceTimer("initiate_multipart_upload"):
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self._client.create_multipart_upload(
                        Bucket=R2_BUCKET_NAME,
                        Key=key,
                        ContentType=content_type,
                        CacheControl=self._get_cache_control(asset_type)
                    )
                )
            
            upload_id = response['UploadId']
            parts = []
            uploaded_bytes = 0
            part_number = 1
            
            # Upload parts
            with PerformanceTimer(f"upload_parts (total {file_size} bytes)"):
                async with aiofiles.open(file_path, 'rb') as f:
                    while True:
                        chunk = await f.read(MULTIPART_CHUNK_SIZE)
                        if not chunk:
                            break
                        
                        part_response = await loop.run_in_executor(
                            None,
                            lambda c=chunk, pn=part_number: self._client.upload_part(
                                Bucket=R2_BUCKET_NAME,
                                Key=key,
                                UploadId=upload_id,
                                PartNumber=pn,
                                Body=c
                            )
                        )
                        
                        parts.append({
                            'PartNumber': part_number,
                            'ETag': part_response['ETag']
                        })
                        
                        uploaded_bytes += len(chunk)
                        part_number += 1
                        
                        if progress_callback:
                            await progress_callback(uploaded_bytes, file_size)
            
            # Complete multipart upload
            with PerformanceTimer("complete_multipart_upload"):
                await loop.run_in_executor(
                    None,
                    lambda: self._client.complete_multipart_upload(
                        Bucket=R2_BUCKET_NAME,
                        Key=key,
                        UploadId=upload_id,
                        MultipartUpload={'Parts': parts}
                    )
                )
            
            public_url = self._get_public_url(key)
            total_ms = (time.time() - total_timing["start"]) * 1000
            logger.info(f"⏱️ TIMING [total_multipart_upload]: {total_ms:.2f}ms for {file_size} bytes")
            
            return True, public_url, key
            
        except Exception as e:
            logger.error(f"Multipart upload failed: {e}")
            # Try to abort the multipart upload
            try:
                if 'upload_id' in locals():
                    await loop.run_in_executor(
                        None,
                        lambda: self._client.abort_multipart_upload(
                            Bucket=R2_BUCKET_NAME,
                            Key=key,
                            UploadId=upload_id
                        )
                    )
            except:
                pass
            return False, "", ""
    
    # ==========================================
    # STANDARD UPLOAD METHODS
    # ==========================================
    
    async def upload_file(
        self,
        file_path: str,
        asset_type: str,
        project_id: str = None,
        custom_filename: str = None
    ) -> Tuple[bool, str, str]:
        """
        Upload a file to R2 storage with timing logs.
        """
        if not self._client:
            logger.error("R2 client not initialized")
            return False, "", ""
        
        total_start = time.time()
        
        try:
            # Generate unique filename
            original_name = Path(file_path).name
            ext = Path(file_path).suffix
            
            if custom_filename:
                filename = custom_filename
            else:
                unique_id = str(uuid.uuid4())[:8]
                filename = f"{Path(original_name).stem}_{unique_id}{ext}"
            
            key = self._get_asset_key(asset_type, filename, project_id)
            content_type = self._get_content_type(filename)
            cache_control = self._get_cache_control(asset_type)
            
            file_size = os.path.getsize(file_path)
            
            # Upload file
            with PerformanceTimer(f"upload_file ({file_size} bytes)"):
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self._client.upload_file(
                        file_path,
                        R2_BUCKET_NAME,
                        key,
                        ExtraArgs={
                            'ContentType': content_type,
                            'CacheControl': cache_control
                        }
                    )
                )
            
            public_url = self._get_public_url(key)
            total_ms = (time.time() - total_start) * 1000
            logger.info(f"⏱️ TIMING [total_upload]: {total_ms:.2f}ms | URL: {public_url[:60]}...")
            
            return True, public_url, key
            
        except Exception as e:
            logger.error(f"Failed to upload to R2: {e}")
            return False, "", ""
    
    async def upload_bytes(
        self,
        data: bytes,
        asset_type: str,
        filename: str,
        project_id: str = None
    ) -> Tuple[bool, str, str]:
        """
        Upload bytes directly to R2 storage with timing logs.
        """
        if not self._client:
            logger.error("R2 client not initialized")
            return False, "", ""
        
        total_start = time.time()
        
        try:
            ext = Path(filename).suffix
            unique_id = str(uuid.uuid4())[:8]
            unique_filename = f"{Path(filename).stem}_{unique_id}{ext}"
            
            key = self._get_asset_key(asset_type, unique_filename, project_id)
            content_type = self._get_content_type(filename)
            cache_control = self._get_cache_control(asset_type)
            
            # Upload bytes
            with PerformanceTimer(f"upload_bytes ({len(data)} bytes)"):
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self._client.put_object(
                        Bucket=R2_BUCKET_NAME,
                        Key=key,
                        Body=data,
                        ContentType=content_type,
                        CacheControl=cache_control
                    )
                )
            
            public_url = self._get_public_url(key)
            total_ms = (time.time() - total_start) * 1000
            logger.info(f"⏱️ TIMING [total_upload_bytes]: {total_ms:.2f}ms | Size: {len(data)} bytes")
            
            return True, public_url, key
            
        except Exception as e:
            logger.error(f"Failed to upload bytes to R2: {e}")
            return False, "", ""
    
    async def download_file(self, key: str, local_path: str) -> bool:
        """Download a file from R2 to local path with timing."""
        if not self._client:
            return False
        
        with PerformanceTimer(f"download_file ({key})"):
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self._client.download_file(R2_BUCKET_NAME, key, local_path)
                )
                return True
            except Exception as e:
                logger.error(f"Failed to download from R2: {e}")
                return False
    
    async def delete_file(self, key: str) -> bool:
        """Delete a file from R2."""
        if not self._client:
            return False
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._client.delete_object(Bucket=R2_BUCKET_NAME, Key=key)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete from R2: {e}")
            return False
    
    async def file_exists(self, key: str) -> bool:
        """Check if a file exists in R2."""
        if not self._client:
            return False
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._client.head_object(Bucket=R2_BUCKET_NAME, Key=key)
            )
            return True
        except:
            return False
    
    def get_stats(self) -> dict:
        """Get storage configuration status."""
        return {
            "configured": self.is_configured,
            "account_id": R2_ACCOUNT_ID[:8] + "..." if R2_ACCOUNT_ID else None,
            "bucket": R2_BUCKET_NAME,
            "public_url": R2_PUBLIC_URL,
            "custom_domain": R2_CUSTOM_DOMAIN,
            "endpoint": R2_ENDPOINT if R2_ACCOUNT_ID else None,
            "multipart_threshold_mb": MULTIPART_THRESHOLD / (1024 * 1024)
        }


# Singleton instance
_storage_instance = None

def get_r2_storage() -> CloudflareR2Storage:
    """Get the R2 storage singleton instance."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = CloudflareR2Storage()
    return _storage_instance


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

async def upload_image(file_path: str, project_id: str) -> Tuple[bool, str]:
    """Upload an image to R2."""
    storage = get_r2_storage()
    success, url, key = await storage.upload_file(file_path, "image", project_id)
    return success, url

async def upload_voice(file_path: str, project_id: str) -> Tuple[bool, str]:
    """Upload a voice file to R2."""
    storage = get_r2_storage()
    success, url, key = await storage.upload_file(file_path, "voice", project_id)
    return success, url

async def upload_video(file_path: str, project_id: str) -> Tuple[bool, str]:
    """Upload a video to R2 using multipart for large files."""
    storage = get_r2_storage()
    success, url, key = await storage.upload_file_multipart(file_path, "video", project_id)
    return success, url

async def upload_image_bytes(data: bytes, filename: str, project_id: str) -> Tuple[bool, str]:
    """Upload image bytes to R2."""
    storage = get_r2_storage()
    success, url, key = await storage.upload_bytes(data, "image", filename, project_id)
    return success, url

async def upload_voice_bytes(data: bytes, filename: str, project_id: str) -> Tuple[bool, str]:
    """Upload voice bytes to R2."""
    storage = get_r2_storage()
    success, url, key = await storage.upload_bytes(data, "voice", filename, project_id)
    return success, url

def get_presigned_upload_url(asset_type: str, filename: str, project_id: str = None) -> Dict[str, Any]:
    """Get a presigned URL for direct browser upload."""
    storage = get_r2_storage()
    return storage.generate_presigned_upload_url(asset_type, filename, project_id)

def get_presigned_download_url(key: str, filename: str = None) -> str:
    """Get a presigned URL for direct browser download."""
    storage = get_r2_storage()
    return storage.generate_presigned_download_url(key, filename=filename)
