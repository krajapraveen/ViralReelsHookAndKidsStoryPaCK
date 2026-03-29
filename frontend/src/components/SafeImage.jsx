import React, { useState, useRef, useEffect } from 'react';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * Convert R2 CDN URLs to backend proxy URLs for cross-browser CORS compatibility.
 * Safari and mobile browsers block direct R2 CDN requests (no CORS headers).
 */
function safeMediaUrl(url) {
  if (!url) return url;
  const r2Match = url.match(/^https?:\/\/pub-[a-f0-9]+\.r2\.dev\/(.+)$/);
  if (r2Match) return `${API}/api/media/r2/${r2Match[1]}`;
  return url;
}

/**
 * SafeImage — viewport-aware image loader with IntersectionObserver.
 *
 * Priority images (hero, first 4 visible) load eagerly.
 * All others defer loading until they enter the viewport.
 */
export function SafeImage({
  src: rawSrc,
  alt = '',
  fallbackType = 'gradient',
  aspectRatio = '1/1',
  objectFit = 'cover',
  titleOverlay,
  priority = false,
  className = '',
  imgClassName = '',
  ...rest
}) {
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [retried, setRetried] = useState(false);
  const [inView, setInView] = useState(priority);
  const containerRef = useRef(null);
  const imgRef = useRef(null);

  // Convert R2 CDN URLs to proxy for cross-browser safety
  const src = safeMediaUrl(rawSrc);

  // Reset state when src changes
  useEffect(() => {
    setFailed(false);
    setLoaded(false);
    setRetried(false);
    if (!priority) setInView(false);
  }, [src, priority]);

  // IntersectionObserver — only observe non-priority images
  useEffect(() => {
    if (priority || inView) return;
    const el = containerRef.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          observer.disconnect();
        }
      },
      { rootMargin: '200px 0px' }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [priority, inView]);

  const isPlaceholder = src && src.includes('placehold.co');
  const hasValidSrc = src && !isPlaceholder && src.length > 5;
  const shouldRender = hasValidSrc && !failed && inView;

  // Gradient colors for fallback
  const hash = (alt || titleOverlay || 'a').split('').reduce((a, c) => a + c.charCodeAt(0), 0);
  const gradients = [
    'from-indigo-600/60 to-cyan-700/50',
    'from-purple-600/60 to-pink-700/50',
    'from-emerald-600/60 to-teal-700/50',
    'from-amber-600/60 to-orange-700/50',
    'from-rose-600/60 to-red-700/50',
    'from-blue-600/60 to-indigo-700/50',
  ];
  const grad = gradients[hash % gradients.length];

  return (
    <div
      ref={containerRef}
      className={`relative overflow-hidden bg-slate-800 ${className}`}
      style={{ aspectRatio }}
      data-testid={rest['data-testid'] || undefined}
    >
      {/* Skeleton pulse while loading */}
      {shouldRender && !loaded && (
        <div className="absolute inset-0 bg-slate-800 animate-pulse" />
      )}

      {/* Actual image — only rendered when in viewport */}
      {shouldRender && (
        <img
          ref={imgRef}
          src={src}
          alt={alt}
          loading={priority ? 'eager' : 'lazy'}
          fetchPriority={priority ? 'high' : 'auto'}
          decoding={priority ? 'sync' : 'async'}
          style={{ objectFit }}
          className={`w-full h-full transition-opacity duration-300 ${loaded ? 'opacity-100' : 'opacity-0'} ${imgClassName}`}
          onLoad={() => setLoaded(true)}
          onError={() => {
            if (!retried && src) {
              setRetried(true);
              setTimeout(() => {
                if (imgRef.current) {
                  const bust = src.includes('?') ? '&_r=1' : '?_r=1';
                  imgRef.current.src = src + bust;
                }
              }, 800);
            } else {
              setFailed(true);
            }
          }}
        />
      )}

      {/* Gradient fallback — clean, no broken image icon */}
      {(!shouldRender && inView) || (!hasValidSrc) || failed ? (
        <div className={`absolute inset-0 flex items-center justify-center bg-gradient-to-br ${grad}`}>
          {fallbackType === 'initials' && titleOverlay && (
            <span className="text-2xl font-black text-white/20 uppercase">
              {titleOverlay.charAt(0)}
            </span>
          )}
          {titleOverlay && (
            <div className="absolute inset-0 flex items-end p-3">
              <span className="text-xs text-white/50 font-semibold truncate leading-tight">
                {titleOverlay}
              </span>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
