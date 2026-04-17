import React, { useEffect, useRef, useCallback } from 'react';
import { X, RotateCw } from 'lucide-react';

/**
 * Fullscreen media viewer — modal overlay for immersive video/image viewing.
 * Works on iOS Safari + Android Chrome without native fullscreen API dependency.
 * 
 * Props:
 *  - src: string (video or image URL)
 *  - type: 'video' | 'image' (default: auto-detect)
 *  - poster: string (video poster image)
 *  - onClose: () => void
 *  - open: boolean
 */
export default function FullscreenMediaViewer({ src, type, poster, onClose, open }) {
  const videoRef = useRef(null);
  const containerRef = useRef(null);

  // Detect type from URL if not provided
  const mediaType = type || (src && /\.(mp4|webm|mov|avi|mkv)/i.test(src) ? 'video' : 'image');

  // Lock body scroll when open
  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden';
      document.body.style.touchAction = 'none';
    }
    return () => {
      document.body.style.overflow = '';
      document.body.style.touchAction = '';
    };
  }, [open]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose]);

  // Close on backdrop click (not on media)
  const handleBackdropClick = useCallback((e) => {
    if (e.target === containerRef.current) onClose();
  }, [onClose]);

  if (!open || !src) return null;

  return (
    <div
      ref={containerRef}
      className="fixed inset-0 z-[10010] bg-black/95 flex items-center justify-center"
      style={{
        paddingTop: 'env(safe-area-inset-top, 0px)',
        paddingBottom: 'env(safe-area-inset-bottom, 0px)',
        paddingLeft: 'env(safe-area-inset-left, 0px)',
        paddingRight: 'env(safe-area-inset-right, 0px)',
      }}
      onClick={handleBackdropClick}
      data-testid="fullscreen-media-viewer"
    >
      {/* Close button */}
      <button
        onClick={onClose}
        className="absolute top-3 right-3 z-[10011] w-10 h-10 rounded-full bg-black/60 border border-white/20 flex items-center justify-center text-white hover:bg-white/20 transition-colors"
        style={{ marginTop: 'env(safe-area-inset-top, 8px)' }}
        data-testid="fullscreen-close-btn"
      >
        <X className="w-5 h-5" />
      </button>

      {/* Rotate hint — show briefly for landscape content in portrait mode */}
      <div className="absolute top-3 left-3 z-[10011] flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-black/60 border border-white/10 text-white/60 text-[10px] animate-in fade-in duration-500"
        style={{ marginTop: 'env(safe-area-inset-top, 8px)', animationDelay: '1s', animationFillMode: 'both' }}
      >
        <RotateCw className="w-3 h-3" />
        Rotate for best view
      </div>

      {/* Media container — hard-bounded to viewport */}
      <div
        className="w-full h-full flex items-center justify-center p-2"
        style={{ maxWidth: '100vw', maxHeight: '100dvh', touchAction: 'manipulation' }}
      >
        {mediaType === 'video' ? (
          <video
            ref={videoRef}
            src={src}
            poster={poster}
            controls
            autoPlay
            playsInline
            controlsList="nodownload noplaybackrate"
            className="max-w-full max-h-full rounded-lg"
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'contain',
              touchAction: 'manipulation',
            }}
            data-testid="fullscreen-video"
          />
        ) : (
          <img
            src={src}
            alt="Full view"
            className="max-w-full max-h-full rounded-lg"
            style={{
              objectFit: 'contain',
              touchAction: 'manipulation',
            }}
            data-testid="fullscreen-image"
          />
        )}
      </div>
    </div>
  );
}
