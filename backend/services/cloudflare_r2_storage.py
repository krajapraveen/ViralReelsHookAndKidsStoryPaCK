"""
Cloudflare R2 Storage Service
Handles all file uploads/downloads for Visionary Suite assets (images, audio, video)
"""
import os
import boto3
import uuid
import logging
import aiofiles
import asyncio
from pathlib import Path
from typing import Optional, Tuple
from botocore.config import Config
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# R2 Configuration from environment
R2_ACCOUNT_ID = os.environ.get("CLOUDFLARE_R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.environ.get("CLOUDFLARE_R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.environ.get("CLOUDFLARE_R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.environ.get("CLOUDFLARE_R2_BUCKET_NAME", "visionary-suite-assets-prod")
R2_PUBLIC_URL = os.environ.get("CLOUDFLARE_R2_PUBLIC_URL", "")
R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

# Asset paths in bucket
ASSET_PATHS = {
    "image": "images",
    "audio": "audio", 
    "voice": "audio/voices",
    "video": "videos",
    "music": "audio/music",
    "thumbnail": "thumbnails"
}


class CloudflareR2Storage:
    """Cloudflare R2 Storage client for Visionary Suite"""
    
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
                    retries={'max_attempts': 3, 'mode': 'adaptive'}
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
        """Get the public URL for an asset"""
        if R2_PUBLIC_URL:
            return f"{R2_PUBLIC_URL.rstrip('/')}/{key}"
        return f"{R2_ENDPOINT}/{R2_BUCKET_NAME}/{key}"
    
    async def upload_file(
        self,
        file_path: str,
        asset_type: str,
        project_id: str = None,
        custom_filename: str = None
    ) -> Tuple[bool, str, str]:
        """
        Upload a file to R2 storage
        
        Args:
            file_path: Local path to the file
            asset_type: Type of asset (image, audio, voice, video, music)
            project_id: Optional project ID for organizing files
            custom_filename: Optional custom filename (defaults to original + uuid)
            
        Returns:
            Tuple of (success, public_url, key)
        """
        if not self._client:
            logger.error("R2 client not initialized")
            return False, "", ""
        
        try:
            # Generate unique filename
            original_name = Path(file_path).name
            ext = Path(file_path).suffix
            
            if custom_filename:
                filename = custom_filename
            else:
                unique_id = str(uuid.uuid4())[:8]
                filename = f"{Path(original_name).stem}_{unique_id}{ext}"
            
            # Generate S3 key
            key = self._get_asset_key(asset_type, filename, project_id)
            
            # Determine content type
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
            content_type = content_types.get(ext.lower(), 'application/octet-stream')
            
            # Upload file (run in thread pool since boto3 is synchronous)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._client.upload_file(
                    file_path,
                    R2_BUCKET_NAME,
                    key,
                    ExtraArgs={
                        'ContentType': content_type,
                        'CacheControl': 'public, max-age=31536000'  # 1 year cache
                    }
                )
            )
            
            public_url = self._get_public_url(key)
            logger.info(f"Uploaded {asset_type} to R2: {key}")
            
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
        Upload bytes directly to R2 storage
        
        Args:
            data: File content as bytes
            asset_type: Type of asset
            filename: Filename with extension
            project_id: Optional project ID
            
        Returns:
            Tuple of (success, public_url, key)
        """
        if not self._client:
            logger.error("R2 client not initialized")
            return False, "", ""
        
        try:
            # Generate unique filename
            ext = Path(filename).suffix
            unique_id = str(uuid.uuid4())[:8]
            unique_filename = f"{Path(filename).stem}_{unique_id}{ext}"
            
            # Generate S3 key
            key = self._get_asset_key(asset_type, unique_filename, project_id)
            
            # Determine content type
            content_types = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.webp': 'image/webp',
                '.mp3': 'audio/mpeg',
                '.wav': 'audio/wav',
                '.mp4': 'video/mp4',
                '.webm': 'video/webm'
            }
            content_type = content_types.get(ext.lower(), 'application/octet-stream')
            
            # Upload bytes
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._client.put_object(
                    Bucket=R2_BUCKET_NAME,
                    Key=key,
                    Body=data,
                    ContentType=content_type,
                    CacheControl='public, max-age=31536000'
                )
            )
            
            public_url = self._get_public_url(key)
            logger.info(f"Uploaded {asset_type} bytes to R2: {key}")
            
            return True, public_url, key
            
        except Exception as e:
            logger.error(f"Failed to upload bytes to R2: {e}")
            return False, "", ""
    
    async def download_file(self, key: str, local_path: str) -> bool:
        """
        Download a file from R2 to local path
        
        Args:
            key: S3 key of the file
            local_path: Local path to save the file
            
        Returns:
            Success boolean
        """
        if not self._client:
            logger.error("R2 client not initialized")
            return False
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._client.download_file(R2_BUCKET_NAME, key, local_path)
            )
            logger.info(f"Downloaded from R2: {key} -> {local_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to download from R2: {e}")
            return False
    
    async def delete_file(self, key: str) -> bool:
        """
        Delete a file from R2
        
        Args:
            key: S3 key of the file
            
        Returns:
            Success boolean
        """
        if not self._client:
            return False
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._client.delete_object(Bucket=R2_BUCKET_NAME, Key=key)
            )
            logger.info(f"Deleted from R2: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete from R2: {e}")
            return False
    
    async def file_exists(self, key: str) -> bool:
        """Check if a file exists in R2"""
        if not self._client:
            return False
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._client.head_object(Bucket=R2_BUCKET_NAME, Key=key)
            )
            return True
        except Exception:
            return False
    
    async def list_project_assets(self, project_id: str, asset_type: str = None) -> list:
        """
        List all assets for a project
        
        Args:
            project_id: Project ID
            asset_type: Optional filter by asset type
            
        Returns:
            List of asset keys
        """
        if not self._client:
            return []
        
        try:
            assets = []
            
            if asset_type:
                prefix = f"{ASSET_PATHS.get(asset_type, 'misc')}/{project_id}/"
            else:
                # Search all asset types for this project
                for atype in ASSET_PATHS.values():
                    prefix = f"{atype}/{project_id}/"
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None,
                        lambda p=prefix: self._client.list_objects_v2(
                            Bucket=R2_BUCKET_NAME,
                            Prefix=p
                        )
                    )
                    for obj in response.get('Contents', []):
                        assets.append({
                            'key': obj['Key'],
                            'url': self._get_public_url(obj['Key']),
                            'size': obj['Size'],
                            'modified': obj['LastModified']
                        })
                return assets
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.list_objects_v2(
                    Bucket=R2_BUCKET_NAME,
                    Prefix=prefix
                )
            )
            
            for obj in response.get('Contents', []):
                assets.append({
                    'key': obj['Key'],
                    'url': self._get_public_url(obj['Key']),
                    'size': obj['Size'],
                    'modified': obj['LastModified']
                })
            
            return assets
            
        except Exception as e:
            logger.error(f"Failed to list project assets: {e}")
            return []
    
    def get_stats(self) -> dict:
        """Get storage configuration status"""
        return {
            "configured": self.is_configured,
            "account_id": R2_ACCOUNT_ID[:8] + "..." if R2_ACCOUNT_ID else None,
            "bucket": R2_BUCKET_NAME,
            "public_url": R2_PUBLIC_URL,
            "endpoint": R2_ENDPOINT if R2_ACCOUNT_ID else None
        }


# Singleton instance
_storage_instance = None

def get_r2_storage() -> CloudflareR2Storage:
    """Get the R2 storage singleton instance"""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = CloudflareR2Storage()
    return _storage_instance


# Convenience functions
async def upload_image(file_path: str, project_id: str) -> Tuple[bool, str]:
    """Upload an image to R2"""
    storage = get_r2_storage()
    success, url, key = await storage.upload_file(file_path, "image", project_id)
    return success, url

async def upload_voice(file_path: str, project_id: str) -> Tuple[bool, str]:
    """Upload a voice file to R2"""
    storage = get_r2_storage()
    success, url, key = await storage.upload_file(file_path, "voice", project_id)
    return success, url

async def upload_video(file_path: str, project_id: str) -> Tuple[bool, str]:
    """Upload a video to R2"""
    storage = get_r2_storage()
    success, url, key = await storage.upload_file(file_path, "video", project_id)
    return success, url

async def upload_image_bytes(data: bytes, filename: str, project_id: str) -> Tuple[bool, str]:
    """Upload image bytes to R2"""
    storage = get_r2_storage()
    success, url, key = await storage.upload_bytes(data, "image", filename, project_id)
    return success, url

async def upload_voice_bytes(data: bytes, filename: str, project_id: str) -> Tuple[bool, str]:
    """Upload voice bytes to R2"""
    storage = get_r2_storage()
    success, url, key = await storage.upload_bytes(data, "voice", filename, project_id)
    return success, url
