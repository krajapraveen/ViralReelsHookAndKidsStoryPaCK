import React, { useEffect, useMemo, useRef, useState } from "react";
import { resolveMediaUrl } from "../utils/mediaUrl";
import { requestPlay, requestPause, isVideoReady, trackPreviewEvent } from "../utils/videoController";

function getBlurSrc(thumbBlur) {
  if (!thumbBlur) return null;
  if (thumbBlur.type === "inline_base64") return thumbBlur.value || null;
  if (thumbBlur.type === "url") return thumbBlur.value || null;
  return null;
}

const HERO_AUTOPLAY_DELAY = 1000; // ms after poster loads before hero preview starts

export default function HeroMedia({
  title,
  hookText = null,
  badge = null,
  media,
  jobId,
  eager = true,
  enablePreview = false,
  fallbackImageUrl,
  alt,
  className = "",
  onClick,
}) {
  const blurSrc = useMemo(() => getBlurSrc(media?.thumb_blur), [media?.thumb_blur]);
  const posterSrc = resolveMediaUrl(media?.poster_large_url);
  const previewSrc = resolveMediaUrl(media?.preview_short_url);
  const resolvedFallback = resolveMediaUrl(fallbackImageUrl);
  const effectiveAlt = alt || title || "Story hero image";

  const videoRef = useRef(null);
  const delayTimerRef = useRef(null);
  const playFired = useRef(false);
  const watchStartRef = useRef(null);

  const [posterLoaded, setPosterLoaded] = useState(false);
  const [posterFailed, setPosterFailed] = useState(false);
  const [previewEnabled, setPreviewEnabled] = useState(false);
  const [previewLoaded, setPreviewLoaded] = useState(false);
  const [previewFailed, setPreviewFailed] = useState(false);

  // ── Delayed autoplay: only after poster is fully loaded ──
  useEffect(() => {
    if (!enablePreview || !posterLoaded || posterFailed || !previewSrc) return;

    delayTimerRef.current = setTimeout(() => {
      setPreviewEnabled(true);
    }, HERO_AUTOPLAY_DELAY);

    return () => clearTimeout(delayTimerRef.current);
  }, [enablePreview, posterLoaded, posterFailed, previewSrc]);

  // ── Play video when enabled and ready ──
  useEffect(() => {
    const vid = videoRef.current;
    if (!vid || !previewEnabled) return;

    const tryPlay = () => {
      if (isVideoReady(vid)) {
        const ok = requestPlay(vid);
        if (ok && !playFired.current && jobId) {
          playFired.current = true;
          watchStartRef.current = Date.now();
          trackPreviewEvent(jobId, "preview_play", { surface: "hero" });
        }
      } else {
        vid.addEventListener("canplay", tryPlay, { once: true });
      }
    };
    tryPlay();

    return () => {
      requestPause(vid);
      if (watchStartRef.current && jobId) {
        const watchTime = (Date.now() - watchStartRef.current) / 1000;
        if (watchTime > 0.5) {
          trackPreviewEvent(jobId, "preview_watch_complete", { watch_time: Math.round(watchTime * 10) / 10, surface: "hero" });
        }
        watchStartRef.current = null;
      }
    };
  }, [previewEnabled, jobId]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearTimeout(delayTimerRef.current);
      if (videoRef.current) requestPause(videoRef.current);
    };
  }, []);

  const showPoster = !!posterSrc && !posterFailed;
  const showFallback = !showPoster && !!fallbackImageUrl;
  const showPreview = previewEnabled && !!previewSrc && !previewFailed;

  return (
    <div
      className={`relative w-full h-full overflow-hidden rounded-none bg-[#0B0B0F] ${className}`}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={(e) => {
        if (!onClick) return;
        if (e.key === "Enter" || e.key === " ") onClick();
      }}
      aria-label={title || "Featured story"}
      data-testid="hero-media"
    >
      {/* Blur placeholder: visible immediately */}
      {blurSrc ? (
        <img
          src={blurSrc}
          alt=""
          aria-hidden="true"
          className="absolute inset-0 w-full h-full object-cover scale-105 blur-2xl opacity-70"
        />
      ) : null}

      {/* Poster: must load before preview can start */}
      {showPoster ? (
        <img
          src={posterSrc}
          alt={effectiveAlt}
          loading={eager ? "eager" : "lazy"}
          fetchPriority={eager ? "high" : "auto"}
          decoding="async"
          className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-300 ${
            posterLoaded ? "opacity-100" : "opacity-70"
          }`}
          onLoad={() => setPosterLoaded(true)}
          onError={() => setPosterFailed(true)}
          data-testid="hero-media-poster"
        />
      ) : null}

      {/* Preview video: delayed autoplay after poster loads */}
      {showPreview ? (
        <video
          ref={videoRef}
          src={previewSrc}
          className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-500 ${
            previewLoaded ? "opacity-100" : "opacity-0"
          }`}
          muted
          loop
          playsInline
          preload="metadata"
          onLoadedData={() => setPreviewLoaded(true)}
          onError={() => setPreviewFailed(true)}
          data-testid="hero-media-preview"
        />
      ) : null}

      {/* Local designed fallback only after real media fails */}
      {showFallback ? (
        <img
          src={resolvedFallback}
          alt={effectiveAlt}
          loading={eager ? "eager" : "lazy"}
          fetchPriority={eager ? "high" : "auto"}
          decoding="async"
          className="absolute inset-0 w-full h-full object-cover"
          data-testid="hero-media-fallback"
        />
      ) : null}

      {/* Main overlay */}
      <div className="absolute inset-0 bg-gradient-to-r from-black/55 via-black/20 to-transparent pointer-events-none" />
      {/* Bottom fade */}
      <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-black/70 to-transparent pointer-events-none" />

      <div className="absolute inset-x-0 bottom-0 z-10 px-4 pb-6 sm:px-6 sm:pb-8 lg:px-10 lg:pb-10 pointer-events-none">
        {badge ? (
          <div className="mb-3 flex items-center gap-2 flex-wrap">
            <span className="inline-flex items-center rounded-full bg-white/15 backdrop-blur-md text-white text-[10px] sm:text-xs font-semibold px-3 py-1 border border-white/20" data-testid="hero-media-badge">
              {badge}
            </span>
          </div>
        ) : null}

        {title ? (
          <h2 className="max-w-3xl text-white font-extrabold tracking-tight text-2xl sm:text-4xl lg:text-5xl leading-tight drop-shadow-[0_2px_12px_rgba(0,0,0,0.45)]" data-testid="hero-media-title">
            {title}
          </h2>
        ) : null}

        {hookText ? (
          <p className="mt-3 max-w-2xl text-white/85 text-sm sm:text-base lg:text-lg leading-relaxed" data-testid="hero-media-hook">
            {hookText}
          </p>
        ) : null}
      </div>
    </div>
  );
}
