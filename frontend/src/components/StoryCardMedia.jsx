import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { resolveMediaUrl } from "../utils/mediaUrl";
import { requestPlay, requestPause, isVideoReady, trackPreviewEvent } from "../utils/videoController";

function getBlurSrc(thumbBlur) {
  if (!thumbBlur) return null;
  if (thumbBlur.type === "inline_base64") return thumbBlur.value || null;
  if (thumbBlur.type === "url") return thumbBlur.value || null;
  return null;
}

const HOVER_DELAY = 120;    // ms before play on desktop hover
const DEBOUNCE_VIS = 150;   // ms debounce for IntersectionObserver
const isMobile = typeof window !== "undefined" && /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent);

export default function StoryCardMedia({
  title,
  media,
  jobId,
  eager = false,
  enablePreviewOnHover = false,
  enablePreviewOnVisible = false,
  fallbackImageUrl,
  alt,
  className = "",
  onClick,
}) {
  const blurSrc = useMemo(() => getBlurSrc(media?.thumb_blur), [media?.thumb_blur]);
  const primarySrc = resolveMediaUrl(media?.thumbnail_small_url);
  const posterSrc = resolveMediaUrl(media?.poster_large_url);
  const previewSrc = resolveMediaUrl(media?.preview_short_url);
  const resolvedFallback = resolveMediaUrl(fallbackImageUrl);
  const effectiveAlt = alt || title || "Story card image";

  const containerRef = useRef(null);
  const videoRef = useRef(null);
  const hoverTimerRef = useRef(null);
  const visTimerRef = useRef(null);
  const impressionFired = useRef(false);
  const playFired = useRef(false);
  const watchStartRef = useRef(null);

  const [primaryLoaded, setPrimaryLoaded] = useState(false);
  const [primaryFailed, setPrimaryFailed] = useState(false);
  const [posterFailed, setPosterFailed] = useState(false);
  const [showingPreview, setShowingPreview] = useState(false);
  const [previewLoaded, setPreviewLoaded] = useState(false);
  const [previewFailed, setPreviewFailed] = useState(false);

  const resolvedImageSrc = !primaryFailed
    ? primarySrc
    : !posterFailed
      ? posterSrc
      : resolvedFallback;

  const canShowPreview = !!previewSrc && !previewFailed && (enablePreviewOnHover || enablePreviewOnVisible);

  // ── Poster must be loaded before any preview attempt ──
  const posterReady = primaryLoaded || primaryFailed;

  // ── Video warmup: load() when entering viewport ──
  useEffect(() => {
    if (!canShowPreview || !enablePreviewOnVisible) return;
    const el = containerRef.current;
    if (!el) return;

    const obs = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && videoRef.current) {
        // Pre-decode: call load() so readyState advances
        videoRef.current.load();
        // Track impression
        if (!impressionFired.current && jobId) {
          impressionFired.current = true;
          trackPreviewEvent(jobId, "preview_impression");
        }
      }
    }, { rootMargin: "200px", threshold: 0.1 });
    obs.observe(el);
    return () => obs.disconnect();
  }, [canShowPreview, enablePreviewOnVisible, jobId]);

  // ── Mobile: IntersectionObserver autoplay with debounce ──
  useEffect(() => {
    if (!isMobile || !canShowPreview || !enablePreviewOnVisible || !posterReady) return;
    const el = containerRef.current;
    if (!el) return;

    const obs = new IntersectionObserver(([entry]) => {
      clearTimeout(visTimerRef.current);
      if (entry.isIntersecting) {
        visTimerRef.current = setTimeout(() => {
          setShowingPreview(true);
        }, DEBOUNCE_VIS);
      } else {
        setShowingPreview(false);
      }
    }, { threshold: 0.6 });
    obs.observe(el);
    return () => { obs.disconnect(); clearTimeout(visTimerRef.current); };
  }, [canShowPreview, enablePreviewOnVisible, posterReady]);

  // ── Play/pause video when showingPreview changes ──
  useEffect(() => {
    const vid = videoRef.current;
    if (!vid) return;

    if (showingPreview && posterReady) {
      // Wait for readyState >= 2 before playing
      const tryPlay = () => {
        if (isVideoReady(vid)) {
          const ok = requestPlay(vid);
          if (ok && !playFired.current && jobId) {
            playFired.current = true;
            watchStartRef.current = Date.now();
            trackPreviewEvent(jobId, "preview_play");
          }
        } else {
          vid.addEventListener("canplay", tryPlay, { once: true });
        }
      };
      tryPlay();
    } else {
      requestPause(vid);
      // Track watch time
      if (watchStartRef.current && jobId) {
        const watchTime = (Date.now() - watchStartRef.current) / 1000;
        if (watchTime > 0.5) {
          trackPreviewEvent(jobId, "preview_watch_complete", { watch_time: Math.round(watchTime * 10) / 10 });
        }
        watchStartRef.current = null;
      }
    }
  }, [showingPreview, posterReady, jobId]);

  // ── Desktop hover handlers ──
  const handleMouseEnter = useCallback(() => {
    if (isMobile || !enablePreviewOnHover || !canShowPreview || !posterReady) return;
    hoverTimerRef.current = setTimeout(() => setShowingPreview(true), HOVER_DELAY);
  }, [enablePreviewOnHover, canShowPreview, posterReady]);

  const handleMouseLeave = useCallback(() => {
    clearTimeout(hoverTimerRef.current);
    if (!isMobile && enablePreviewOnHover) setShowingPreview(false);
  }, [enablePreviewOnHover]);

  // ── Click handler with conversion tracking ──
  const handleClick = useCallback(() => {
    if (jobId) trackPreviewEvent(jobId, "preview_click");
    if (onClick) onClick();
  }, [jobId, onClick]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearTimeout(hoverTimerRef.current);
      clearTimeout(visTimerRef.current);
      if (videoRef.current) requestPause(videoRef.current);
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className={`relative overflow-hidden rounded-2xl bg-[#121218] aspect-[4/5] ${className}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={handleClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={(e) => {
        if (!onClick) return;
        if (e.key === "Enter" || e.key === " ") handleClick();
      }}
      aria-label={title || "Story card"}
      data-testid="story-card-media"
    >
      {/* Blur placeholder — visible immediately, zero blank UI */}
      {blurSrc ? (
        <img
          src={blurSrc}
          alt=""
          aria-hidden="true"
          className="absolute inset-0 w-full h-full object-cover scale-105 blur-xl opacity-60"
        />
      ) : null}

      {/* Primary image */}
      {resolvedImageSrc ? (
        <img
          src={resolvedImageSrc}
          alt={effectiveAlt}
          loading={eager ? "eager" : "lazy"}
          fetchPriority={eager ? "high" : "auto"}
          decoding="async"
          className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-300 ${
            primaryLoaded ? "opacity-100" : "opacity-75"
          }`}
          onLoad={() => setPrimaryLoaded(true)}
          onError={() => {
            if (!primaryFailed) setPrimaryFailed(true);
            else if (!posterFailed) setPosterFailed(true);
          }}
          data-testid="story-card-media-image"
        />
      ) : null}

      {/* Preview video — always in DOM when available (for warmup), visibility controlled by opacity */}
      {canShowPreview ? (
        <video
          ref={videoRef}
          src={previewSrc}
          className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-200 ${
            showingPreview && previewLoaded ? "opacity-100" : "opacity-0"
          }`}
          muted
          loop
          playsInline
          preload={eager ? "metadata" : "none"}
          onLoadedData={() => setPreviewLoaded(true)}
          onError={() => {
            setPreviewFailed(true);
            setShowingPreview(false);
          }}
          data-testid="story-card-media-preview"
        />
      ) : null}

      {/* Overlay */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/15 to-transparent" />

      {/* Content slot */}
      <div className="absolute inset-x-0 bottom-0 z-10 p-3 sm:p-4 pointer-events-none">
        {title ? (
          <h3 className="text-white text-sm sm:text-base font-bold leading-snug line-clamp-2 drop-shadow-[0_2px_10px_rgba(0,0,0,0.45)]" data-testid="story-card-media-title">
            {title}
          </h3>
        ) : null}
      </div>
    </div>
  );
}
