import React, { useRef, useEffect, useState } from 'react';
import { Lock, Download, Shield, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { 
  applyContentProtection, 
  protectedImageStyles, 
  watermarkOverlayStyles,
  generateWatermarkPattern 
} from '../utils/contentProtection';

const API_URL = process.env.REACT_APP_BACKEND_URL;

/**
 * Protected Image Component
 * Displays images with watermark and download protection
 */
export const ProtectedImage = ({ 
  src, 
  alt, 
  userEmail,
  fileId,
  showWatermark = true,
  allowDownload = true,
  className = ""
}) => {
  const containerRef = useRef(null);
  const [downloading, setDownloading] = useState(false);
  const [watermarkRemoved, setWatermarkRemoved] = useState(false);

  useEffect(() => {
    if (containerRef.current) {
      applyContentProtection(containerRef);
    }
  }, []);

  const handleSecureDownload = async () => {
    if (!fileId) {
      toast.error('Download not available');
      return;
    }

    setDownloading(true);
    try {
      const token = localStorage.getItem('token');
      
      // Get signed URL
      const signedRes = await fetch(`${API_URL}/api/protected-download/get-signed-url`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ file_id: fileId, file_type: 'image' })
      });

      if (!signedRes.ok) {
        throw new Error('Failed to get download link');
      }

      const { signed_url } = await signedRes.json();

      // Download using signed URL
      const downloadRes = await fetch(`${API_URL}${signed_url}`);
      if (!downloadRes.ok) {
        throw new Error('Download failed');
      }

      const blob = await downloadRes.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `download-${fileId}.png`;
      a.click();
      URL.revokeObjectURL(url);

      toast.success('Download complete');
    } catch (error) {
      toast.error(error.message || 'Download failed');
    } finally {
      setDownloading(false);
    }
  };

  const handleRemoveWatermark = async () => {
    if (!fileId) return;

    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/protected-download/remove-watermark`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ file_id: fileId })
      });

      const data = await res.json();

      if (res.ok) {
        setWatermarkRemoved(true);
        toast.success(data.message);
      } else {
        toast.error(data.detail || 'Failed to remove watermark');
      }
    } catch (error) {
      toast.error('Failed to remove watermark');
    }
  };

  const date = new Date().toISOString().split('T')[0];

  return (
    <div 
      ref={containerRef}
      className={`relative ${className}`}
      data-protected="true"
      onContextMenu={(e) => e.preventDefault()}
    >
      {/* Image with protection */}
      <div className="relative overflow-hidden rounded-lg">
        <img
          src={src}
          alt={alt}
          className="w-full h-auto"
          style={protectedImageStyles}
          draggable={false}
          onDragStart={(e) => e.preventDefault()}
        />

        {/* Subtle background watermark */}
        {showWatermark && !watermarkRemoved && (
          <div 
            className="absolute inset-0 pointer-events-none"
            style={{
              backgroundImage: generateWatermarkPattern(),
              backgroundRepeat: 'repeat',
              opacity: 0.5
            }}
          />
        )}

        {/* Visible watermark */}
        {showWatermark && !watermarkRemoved && (
          <div style={watermarkOverlayStyles}>
            <div className="text-[10px] leading-tight">
              Generated for {userEmail || 'user'}
            </div>
            <div className="text-[9px] opacity-80">
              visionary-suite.com | {date}
            </div>
          </div>
        )}

        {/* Protection indicator */}
        <div className="absolute top-2 left-2 flex items-center gap-1 bg-black/50 text-white text-xs px-2 py-1 rounded">
          <Shield className="w-3 h-3" />
          Protected
        </div>
      </div>

      {/* Action buttons */}
      {allowDownload && (
        <div className="flex gap-2 mt-2">
          <button
            onClick={handleSecureDownload}
            disabled={downloading}
            className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg disabled:opacity-50"
          >
            {downloading ? (
              <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            {watermarkRemoved ? 'Download HD' : 'Download (Watermarked)'}
          </button>

          {showWatermark && !watermarkRemoved && (
            <button
              onClick={handleRemoveWatermark}
              className="flex items-center gap-1 px-3 py-2 bg-purple-600 hover:bg-purple-500 text-white text-sm rounded-lg"
            >
              <Lock className="w-4 h-4" />
              Remove Watermark (5 Credits)
            </button>
          )}
        </div>
      )}
    </div>
  );
};

/**
 * Protected Content Container
 * Wraps any content with copy/context menu protection
 */
export const ProtectedContentContainer = ({ 
  children, 
  className = "",
  showNotice = true 
}) => {
  const containerRef = useRef(null);

  useEffect(() => {
    if (containerRef.current) {
      applyContentProtection(containerRef);
    }
  }, []);

  return (
    <div 
      ref={containerRef}
      className={`relative ${className}`}
      data-protected="true"
      onContextMenu={(e) => e.preventDefault()}
      onCopy={(e) => {
        e.preventDefault();
        toast.info('Content is protected. Use the download button.');
      }}
    >
      {children}
      
      {showNotice && (
        <div className="flex items-center gap-2 mt-2 text-xs text-slate-500">
          <Shield className="w-3 h-3" />
          <span>Content protected | Right-click disabled</span>
        </div>
      )}
    </div>
  );
};

/**
 * Content Protection Notice Banner
 */
export const ContentProtectionNotice = () => (
  <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 flex items-start gap-2">
    <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
    <div>
      <p className="text-amber-200 text-sm font-medium">Content Protection Active</p>
      <p className="text-amber-200/70 text-xs mt-1">
        All generated content is watermarked with your email. Downloads are secured with signed URLs.
        Remove watermark for +5 credits.
      </p>
    </div>
  </div>
);

export default ProtectedImage;
