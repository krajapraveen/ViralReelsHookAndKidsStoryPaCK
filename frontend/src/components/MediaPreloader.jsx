import { useEffect } from "react";

function createPreloadLink(href) {
  if (!href) return null;
  const link = document.createElement("link");
  link.rel = "preload";
  link.as = "image";
  link.href = href;
  return link;
}

function createPreconnectLink(origin) {
  if (!origin) return null;
  const link = document.createElement("link");
  link.rel = "preconnect";
  link.href = origin;
  return link;
}

function createDnsPrefetchLink(origin) {
  if (!origin) return null;
  const link = document.createElement("link");
  link.rel = "dns-prefetch";
  link.href = origin;
  return link;
}

function safeOrigin(url) {
  try {
    return new URL(url).origin;
  } catch {
    return null;
  }
}

export default function MediaPreloader({
  hero,
  firstRowCards = [],
  imageOrigin = null,
}) {
  useEffect(() => {
    const head = document.head;
    const added = [];

    const resolvedOrigin =
      imageOrigin ||
      safeOrigin(hero?.poster_large_url) ||
      safeOrigin(firstRowCards?.[0]?.thumbnail_small_url);

    const preconnect = createPreconnectLink(resolvedOrigin);
    const dnsPrefetch = createDnsPrefetchLink(resolvedOrigin);

    if (preconnect) {
      head.appendChild(preconnect);
      added.push(preconnect);
    }

    if (dnsPrefetch) {
      head.appendChild(dnsPrefetch);
      added.push(dnsPrefetch);
    }

    // Preload hero poster only
    if (hero?.poster_large_url) {
      const heroPreload = createPreloadLink(hero.poster_large_url);
      if (heroPreload) {
        head.appendChild(heroPreload);
        added.push(heroPreload);
      }
    }

    // Preload only first 4 visible thumbnails
    const topThumbs = (firstRowCards || [])
      .map((c) => c?.thumbnail_small_url)
      .filter(Boolean)
      .slice(0, 4);

    topThumbs.forEach((thumbUrl) => {
      const thumbPreload = createPreloadLink(thumbUrl);
      if (thumbPreload) {
        head.appendChild(thumbPreload);
        added.push(thumbPreload);
      }
    });

    return () => {
      added.forEach((el) => {
        if (el.parentNode) el.parentNode.removeChild(el);
      });
    };
  }, [hero?.poster_large_url, firstRowCards, imageOrigin]);

  return null;
}
