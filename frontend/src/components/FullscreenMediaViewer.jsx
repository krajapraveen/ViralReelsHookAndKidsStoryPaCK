import React, { useEffect, useRef, useCallback } from 'react';
import { X, RotateCw } from 'lucide-react';
import './fullscreenMediaViewer.css';

/**
 * Fullscreen media viewer with native landscape video support.
 * Videos: attempts native fullscreen + orientation lock → CSS rotate fallback.
 * Images: contained overlay, no rotation.
 */
export default function FullscreenMediaViewer({ src, type, poster, onClose, open }) {
  const videoRef = useRef(null);
  const containerRef = useRef(null);
  const nativeFullscreenRef = useRef(false);

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

  // For VIDEO: attempt native fullscreen + orientation lock
  useEffect(() => {
    if (!open || mediaType !== 'video') return;

    const enterFullscreen = async () => {
      const video = videoRef.current;
      if (!video) return;

      // Try native fullscreen on the video element
      try {
        if (video.requestFullscreen) {
          await video.requestFullscreen();
          nativeFullscreenRef.current = true;
        } else if (video.webkitEnterFullscreen) {
          // iOS Safari — this gives native fullscreen player
          video.webkitEnterFullscreen();
          nativeFullscreenRef.current = true;
        }
      } catch (e) {
        nativeFullscreenRef.current = false;
      }

      // Try orientation lock to landscape
      try {
        if (screen.orientation && screen.orientation.lock) {
          await screen.orientation.lock('landscape');
        }
      } catch (e) {
        // Most mobile browsers restrict this — CSS fallback handles it
      }
    };

    // Small delay to let the modal mount and video element appear
    const timer = setTimeout(enterFullscreen, 300);
    return () => clearTimeout(timer);
  }, [open, mediaType]);

  // Cleanup on close
  useEffect(() => {
    if (open) return;
    return () => {
      // Unlock orientation
      try {
        if (screen.orientation && screen.orientation.unlock) {
          screen.orientation.unlock();
        }
      } catch (e) {}
      // Exit native fullscreen if active
      try {
        if (document.fullscreenElement) {
          document.exitFullscreen();
        }
      } catch (e) {}
      nativeFullscreenRef.current = false;
    };
  }, [open]);

  // Listen for native fullscreen exit → close our modal too
  useEffect(() => {
    if (!open || mediaType !== 'video') return;
    const handler = () => {
      if (!document.fullscreenElement && nativeFullscreenRef.current) {
        nativeFullscreenRef.current = false;
        onClose();
      }
    };
    document.addEventListener('fullscreenchange', handler);
    document.addEventListener('webkitfullscreenchange', handler);
    return () => {
      document.removeEventListener('fullscreenchange', handler);
      document.removeEventListener('webkitfullscreenchange', handler);
    };
  }, [open, mediaType, onClose]);

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

  const handleClose = useCallback(() => {
    // Exit native fullscreen first
    try {
      if (document.fullscreenElement) document.exitFullscreen();
    } catch (e) {}
    try {
      if (screen.orientation && screen.orientation.unlock) screen.orientation.unlock();
    } catch (e) {}
    nativeFullscreenRef.current = false;
    onClose();
  }, [onClose]);

  if (!open || !src) return null;

  return (
    <div
      ref={containerRef}
      className={`fsm-overlay ${mediaType === 'video' ? 'fsm-video-mode' : ''}`}
      onClick={handleBackdropClick}
      data-testid="fullscreen-media-viewer"
    >
      {/* Close button */}
      <button
        onClick={handleClose}
        className="fsm-close"
        data-testid="fullscreen-close-btn"
      >
        <X className="w-5 h-5" />
      </button>

      {/* Rotate hint for video */}
      {mediaType === 'video' && (
        <div className="fsm-rotate-hint">
          <RotateCw className="w-3 h-3" />
          Rotate for best view
        </div>
      )}

      {/* Media container */}
      <div className="fsm-content" onClick={(e) => e.stopPropagation()}>
        {mediaType === 'video' ? (
          <video
            ref={videoRef}
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
