import React, { useEffect, useMemo, useState } from "react";

function getBlurSrc(thumbBlur) {
  if (!thumbBlur) return null;
  if (thumbBlur.type === "inline_base64") return thumbBlur.value || null;
  if (thumbBlur.type === "url") return thumbBlur.value || null;
  return null;
}

export default function HeroMedia({
  title,
  hookText = null,
  badge = null,
  media,
  eager = true,
  enablePreview = false,
  fallbackImageUrl,
  alt,
  className = "",
  onClick,
}) {
  const blurSrc = useMemo(() => getBlurSrc(media?.thumb_blur), [media?.thumb_blur]);
  const posterSrc = media?.poster_large_url || null;
  const previewSrc = media?.preview_short_url || null;
  const effectiveAlt = alt || title || "Story hero image";

  const [posterLoaded, setPosterLoaded] = useState(false);
  const [posterFailed, setPosterFailed] = useState(false);
  const [previewEnabled, setPreviewEnabled] = useState(false);
  const [previewLoaded, setPreviewLoaded] = useState(false);
  const [previewFailed, setPreviewFailed] = useState(false);

  useEffect(() => {
    // Preview is enhancement only.
    // Enable it only after poster is already present and if allowed.
    if (enablePreview && posterSrc && !posterFailed && previewSrc) {
      const timer = setTimeout(() => setPreviewEnabled(true), 250);
      return () => clearTimeout(timer);
    }
  }, [enablePreview, posterSrc, posterFailed, previewSrc]);

  const showPoster = !!posterSrc && !posterFailed;
  const showFallback = !showPoster && !!fallbackImageUrl;
  const showPreview = previewEnabled && !!previewSrc && !previewFailed;

  return (
    <div
      className={`relative w-full h-full overflow-hidden bg-black ${className}`}
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
          className="absolute inset-0 w-full h-full object-cover scale-105 blur-xl opacity-70"
        />
      ) : null}

      {/* Poster: must be visible immediately, not hidden behind onLoad */}
      {showPoster ? (
        <img
          src={posterSrc}
          alt={effectiveAlt}
          loading={eager ? "eager" : "lazy"}
          fetchpriority={eager ? "high" : "auto"}
          decoding="async"
          className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-300 ${
            posterLoaded ? "opacity-100" : "opacity-70"
          }`}
          onLoad={() => setPosterLoaded(true)}
          onError={() => setPosterFailed(true)}
          data-testid="hero-media-poster"
        />
      ) : null}

      {/* Preview: optional enhancement only */}
      {showPreview ? (
        <video
          src={previewSrc}
          className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-300 ${
            previewLoaded ? "opacity-100" : "opacity-0"
          }`}
          autoPlay
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
          src={fallbackImageUrl}
          alt={effectiveAlt}
          loading={eager ? "eager" : "lazy"}
          fetchpriority={eager ? "high" : "auto"}
          decoding="async"
          className="absolute inset-0 w-full h-full object-cover"
          data-testid="hero-media-fallback"
        />
      ) : null}

      {/* Overlay */}
      <div className="absolute inset-0 bg-gradient-to-r from-black/55 via-black/20 to-transparent pointer-events-none" />

      <div className="absolute bottom-0 left-0 right-0 p-4 sm:p-6 pointer-events-none">
        {badge ? (
          <div className="mb-2 inline-flex rounded-full bg-yellow-500 text-black text-xs font-bold px-3 py-1" data-testid="hero-media-badge">
            {badge}
          </div>
        ) : null}

        {title ? (
          <h2 className="text-white font-bold text-2xl sm:text-4xl leading-tight max-w-3xl" data-testid="hero-media-title">
            {title}
          </h2>
        ) : null}

        {hookText ? (
          <p className="mt-2 text-white/80 text-sm sm:text-lg max-w-2xl" data-testid="hero-media-hook">
            {hookText}
          </p>
        ) : null}
      </div>
    </div>
  );
}
