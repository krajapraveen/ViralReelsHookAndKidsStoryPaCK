import React, { useState, useRef, useEffect } from 'react';

/**
 * SafeImage — bulletproof image renderer with priority loading support.
 *
 * Props:
 *   src           - image URL (can be null/empty)
 *   alt           - alt text
 *   fallbackType  - 'gradient' | 'initials' (default: 'gradient')
 *   aspectRatio   - CSS aspect-ratio value (default: '1/1')
 *   objectFit     - CSS object-fit (default: 'cover')
 *   titleOverlay  - text to overlay when image missing
 *   priority      - if true, use eager loading + fetchpriority=high
 *   className     - additional classes for the container
 *   imgClassName  - additional classes for the <img> tag
 */
export function SafeImage({
  src,
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
  const imgRef = useRef(null);

  // Reset state when src changes
  useEffect(() => {
    setFailed(false);
    setLoaded(false);
    setRetried(false);
  }, [src]);

  const isPlaceholder = src && src.includes('placehold.co');
  const hasValidSrc = src && !isPlaceholder && src.length > 5;
  const showImage = hasValidSrc && !failed;

  // Gradient colors for fallback
  const hash = (alt || titleOverlay || 'a').split('').reduce((a, c) => a + c.charCodeAt(0), 0);
  const gradients = [
    'from-indigo-600/40 to-cyan-600/30',
    'from-purple-600/40 to-pink-600/30',
    'from-emerald-600/40 to-teal-600/30',
    'from-amber-600/40 to-orange-600/30',
    'from-rose-600/40 to-red-600/30',
    'from-blue-600/40 to-violet-600/30',
  ];
  const grad = gradients[hash % gradients.length];

  return (
    <div
      className={`relative overflow-hidden bg-slate-800 ${className}`}
      style={{ aspectRatio }}
      data-testid={rest['data-testid'] || undefined}
    >
      {/* Skeleton pulse while image loading */}
      {showImage && !loaded && (
        <div className="absolute inset-0 bg-slate-800 animate-pulse" />
      )}

      {/* Actual image */}
      {showImage && (
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
                  const bust = src.includes('?') ? `&_r=1` : `?_r=1`;
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
      {!showImage && (
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
      )}
    </div>
  );
}
