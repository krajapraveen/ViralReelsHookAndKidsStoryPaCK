import React, { useEffect, useRef, useCallback } from 'react';
import { X } from 'lucide-react';
import './fullscreenMediaViewer.css';

/**
 * CSS-based fullscreen fallback viewer.
 * Used ONLY when native video.webkitEnterFullscreen() fails.
 * For videos: CSS-rotates to landscape in portrait mode.
 * For images: normal contained overlay.
 */
export default function FullscreenMediaViewer({ src, type, poster, onClose, open }) {
  const containerRef = useRef(null);
  const mediaType = type || 'image';

  // Lock body scroll
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

  const handleBackdropClick = useCallback((e) => {
    if (e.target === containerRef.current) onClose();
  }, [onClose]);

  if (!open || !src) return null;

  return (
    <div
      ref={containerRef}
      className={`fsm-overlay ${mediaType === 'video' ? 'fsm-video-mode' : ''}`}
      onClick={handleBackdropClick}
      data-testid="fullscreen-media-viewer"
    >
      <button onClick={onClose} className="fsm-close" data-testid="fullscreen-close-btn">
        <X className="w-5 h-5" />
      </button>

      <div className="fsm-content" onClick={(e) => e.stopPropagation()}>
        {mediaType === 'video' ? (
          <video
            src={src}
            poster={poster}
            controls
            autoPlay
            playsInline
            controlsList="nodownload noplaybackrate"
            className="fsm-video"
            data-testid="fullscreen-video"
          />
        ) : (
          <img
            src={src}
            alt="Full view"
            className="fsm-image"
            data-testid="fullscreen-image"
          />
        )}
      </div>
    </div>
  );
}
