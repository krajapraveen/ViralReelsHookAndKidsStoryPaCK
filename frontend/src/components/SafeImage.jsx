import React, { useState, useRef } from 'react';
import { ImageOff } from 'lucide-react';

/**
 * SafeImage — bulletproof image renderer.
 *
 * Handles: null, empty, data URIs, broken URLs, failed loads.
 * Always shows fallback or gradient placeholder. Never a broken image icon.
 *
 * Props:
 *   src           - image URL or data URI (can be null/empty)
 *   alt           - alt text
 *   fallbackType  - 'gradient' | 'icon' | 'initials' (default: 'gradient')
 *   aspectRatio   - CSS aspect-ratio value (default: '1/1')
 *   objectFit     - CSS object-fit (default: 'cover')
 *   titleOverlay  - text to overlay when image missing
 *   showSkeleton  - show pulse animation while loading
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
  showSkeleton = true,
  className = '',
  imgClassName = '',
  ...rest
}) {
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const imgRef = useRef(null);

  // Determine if src is usable
  const isDataUri = src && src.startsWith('data:');
  const isPlaceholder = src && src.includes('placehold.co');
  const hasValidSrc = src && !isPlaceholder && src.length > 5;
  const showImage = hasValidSrc && !failed;

  // Gradient colors derived from alt/title for variety
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
      {/* Skeleton loader */}
      {showSkeleton && showImage && !loaded && (
        <div className="absolute inset-0 bg-slate-800 animate-pulse" />
      )}

      {/* Actual image */}
      {showImage && (
        <img
          ref={imgRef}
          src={src}
          alt={alt}
          loading="lazy"
          {...(!isDataUri && { crossOrigin: 'anonymous' })}
          style={{ objectFit }}
          className={`w-full h-full transition-opacity duration-300 ${loaded ? 'opacity-100' : 'opacity-0'} ${imgClassName}`}
          onLoad={() => setLoaded(true)}
          onError={() => setFailed(true)}
        />
      )}

      {/* Fallback — shown when no valid src or image failed to load */}
      {!showImage && (
        <div className={`absolute inset-0 flex items-center justify-center bg-gradient-to-br ${grad}`}>
          {fallbackType === 'icon' && (
            <ImageOff className="w-6 h-6 text-white/20" />
          )}
          {fallbackType === 'initials' && titleOverlay && (
            <span className="text-xl font-bold text-white/30 uppercase">
              {titleOverlay.charAt(0)}
            </span>
          )}
          {titleOverlay && (
            <div className="absolute inset-0 flex items-end p-2">
              <span className="text-[10px] text-white/60 font-medium truncate leading-tight">
                {titleOverlay}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
