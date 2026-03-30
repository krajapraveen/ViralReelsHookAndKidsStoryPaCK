import React, { useMemo, useState } from "react";

function getBlurSrc(thumbBlur) {
  if (!thumbBlur) return null;
  if (thumbBlur.type === "inline_base64") return thumbBlur.value || null;
  if (thumbBlur.type === "url") return thumbBlur.value || null;
  return null;
}

export default function StoryCardMedia({
  title,
  media,
  eager = false,
  enablePreviewOnHover = false,
  enablePreviewOnTap = false,
  fallbackImageUrl,
  alt,
  className = "",
  onClick,
}) {
  const blurSrc = useMemo(() => getBlurSrc(media?.thumb_blur), [media?.thumb_blur]);
  const primarySrc = media?.thumbnail_small_url || null;
  const posterSrc = media?.poster_large_url || null;
  const previewSrc = media?.preview_short_url || null;
  const effectiveAlt = alt || title || "Story card image";

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
      : fallbackImageUrl;

  const canShowPreview =
    !!previewSrc &&
    !previewFailed &&
    (enablePreviewOnHover || enablePreviewOnTap);

  return (
    <div
      className={`relative overflow-hidden rounded-2xl bg-[#121218] aspect-[4/5] ${className}`}
      onMouseEnter={() => {
        if (enablePreviewOnHover && canShowPreview) setShowingPreview(true);
      }}
      onMouseLeave={() => {
        if (enablePreviewOnHover) setShowingPreview(false);
      }}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={(e) => {
        if (!onClick) return;
        if (e.key === "Enter" || e.key === " ") onClick();
      }}
      aria-label={title || "Story card"}
      data-testid="story-card-media"
    >
      {/* Blur placeholder */}
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
          fetchpriority={eager ? "high" : "auto"}
          decoding="async"
          className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-300 ${
            primaryLoaded ? "opacity-100" : "opacity-75"
          }`}
          onLoad={() => setPrimaryLoaded(true)}
          onError={() => {
            if (!primaryFailed) {
              setPrimaryFailed(true);
            } else if (!posterFailed) {
              setPosterFailed(true);
            }
          }}
          data-testid="story-card-media-image"
        />
      ) : null}

      {/* Optional interaction-only preview */}
      {showingPreview && canShowPreview ? (
        <video
          src={previewSrc}
          className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-200 ${
            previewLoaded ? "opacity-100" : "opacity-0"
          }`}
          autoPlay
          muted
          loop
          playsInline
          preload="metadata"
          onLoadedData={() => setPreviewLoaded(true)}
          onError={() => {
            setPreviewFailed(true);
            setShowingPreview(false);
          }}
          data-testid="story-card-media-preview"
        />
      ) : null}

      {/* Overlay — lighter, does NOT crush media */}
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
