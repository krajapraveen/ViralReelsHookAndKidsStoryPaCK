/**
 * R2 Direct Upload Utility
 * Handles direct browser-to-R2 uploads using presigned URLs
 * Bypasses backend for improved performance
 */
import api from './api';

/**
 * Upload a file directly to R2 cloud storage using presigned URL
 * @param {File|Blob} file - The file to upload
 * @param {string} assetType - Type of asset (image, audio, video)
 * @param {string} projectId - Project ID for organization
 * @param {Function} onProgress - Progress callback (0-100)
 * @returns {Promise<{success: boolean, url: string, key: string}>}
 */
export async function uploadToR2Direct(file, assetType, projectId, onProgress = null) {
  try {
    // Step 1: Get presigned upload URL from backend
    const filename = file.name || `${assetType}_${Date.now()}.${getExtension(file.type)}`;
    
    const presignedRes = await api.post('/api/story-video-studio/generation/storage/presigned-upload', {
      filename,
      asset_type: assetType,
      project_id: projectId,
      content_type: file.type
    });

    if (!presignedRes.data.success) {
      throw new Error(presignedRes.data.error || 'Failed to get presigned URL');
    }

    const { presigned } = presignedRes.data;
    const { upload_url, public_url, key } = presigned;

    // Step 2: Upload directly to R2 using the presigned URL
    await uploadWithProgress(upload_url, file, file.type, onProgress);

    return {
      success: true,
      url: public_url,
      key: key
    };
  } catch (error) {
    console.error('R2 direct upload failed:', error);
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * Upload a file with progress tracking
 */
async function uploadWithProgress(url, file, contentType, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    
    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable && onProgress) {
        const percentComplete = Math.round((event.loaded / event.total) * 100);
        onProgress(percentComplete);
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(xhr.response);
      } else {
        reject(new Error(`Upload failed with status ${xhr.status}`));
      }
    });

    xhr.addEventListener('error', () => {
      reject(new Error('Upload failed'));
    });

    xhr.open('PUT', url);
    xhr.setRequestHeader('Content-Type', contentType);
    xhr.send(file);
  });
}

/**
 * Get file extension from MIME type
 */
function getExtension(mimeType) {
  const mimeToExt = {
    'image/png': 'png',
    'image/jpeg': 'jpg',
    'image/webp': 'webp',
    'audio/mpeg': 'mp3',
    'audio/wav': 'wav',
    'video/mp4': 'mp4',
    'video/webm': 'webm'
  };
  return mimeToExt[mimeType] || 'bin';
}

/**
 * Get a presigned download URL for an asset
 * @param {string} key - The R2 object key
 * @param {number} expiresIn - Expiration time in seconds (default 1 hour)
 * @returns {Promise<string>} - The presigned download URL
 */
export async function getPresignedDownloadUrl(key, expiresIn = 3600) {
  try {
    const res = await api.post('/api/story-video-studio/generation/storage/presigned-download', {
      key,
      expires_in: expiresIn
    });

    if (res.data.success) {
      return res.data.url;
    }
    throw new Error(res.data.error || 'Failed to get download URL');
  } catch (error) {
    console.error('Failed to get presigned download URL:', error);
    return null;
  }
}

/**
 * Resolve a URL - returns R2 URLs as-is, prefixes local paths with backend URL
 * @param {string} url - The URL or path to resolve
 * @returns {string} - The resolved full URL
 */
export function resolveAssetUrl(url) {
  if (!url) return '';
  
  // If it's already a full URL (R2 or other), return as-is
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }
  
  // Otherwise, prefix with backend URL for local paths
  const backendUrl = process.env.REACT_APP_BACKEND_URL || '';
  return `${backendUrl}${url}`;
}

export default {
  uploadToR2Direct,
  getPresignedDownloadUrl,
  resolveAssetUrl
};
