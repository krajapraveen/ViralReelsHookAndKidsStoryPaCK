import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { RefreshCw, Eye, Flame, ChevronLeft, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';

const SECTION_COPY = {
  completion: 'Try what others created',
  myspace: 'People are remixing these',
  waiting: 'While you wait\u2026 remix a trending story',
};

function formatCount(n) {
  if (!n) return '0';
  if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return String(n);
}

export default function RemixGallery({ placement = 'myspace', limit = 8, className = '' }) {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scrollIdx, setScrollIdx] = useState(0);

  useEffect(() => {
    const fetchItems = async () => {
      try {
        const res = await api.get(`/api/gallery/remix-feed?limit=${limit}`);
        if (res.data?.items) setItems(res.data.items);
      } catch { /* silent */ }
      finally { setLoading(false); }
    };
    fetchItems();
  }, [limit]);

  const handleRemix = async (item) => {
    try {
      await api.post(`/api/gallery/${item.item_id}/remix`);
    } catch { /* fire-and-forget */ }

    navigate('/app/story-video-studio', {
      state: {
        prompt: item.story_text || item.description || '',
        remixFrom: {
          title: item.title,
          item_id: item.item_id,
          remixes_count: (item.remixes_count || 0) + 1,
          source: 'remix_gallery',
        },
        source_tool: 'remix-gallery',
        isRemix: true,
      },
    });

    toast.success("You're remixing a trending story", { duration: 3000 });
  };

  const visibleCount = placement === 'completion' ? 3 : 4;
  const canScrollLeft = scrollIdx > 0;
  const canScrollRight = scrollIdx + visibleCount < items.length;
  const scrollLeft = () => setScrollIdx(Math.max(0, scrollIdx - visibleCount));
  const scrollRight = () => setScrollIdx(Math.min(items.length - visibleCount, scrollIdx + visibleCount));
  const visible = items.slice(scrollIdx, scrollIdx + visibleCount);

  if (loading || items.length === 0) return null;

  return (
    <div className={`${className}`} data-testid={`remix-gallery-${placement}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Flame className="w-4 h-4 text-orange-400" />
          <h3 className="text-sm font-semibold text-zinc-300">
            {SECTION_COPY[placement] || SECTION_COPY.myspace}
          </h3>
        </div>
        {items.length > visibleCount && (
          <div className="flex gap-1">
            <button
              onClick={scrollLeft}
              disabled={!canScrollLeft}
              className={`p-1 rounded-md transition-colors ${canScrollLeft ? 'bg-white/[0.06] text-zinc-300 hover:bg-white/10' : 'text-zinc-700 cursor-not-allowed'}`}
              data-testid="remix-scroll-left"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={scrollRight}
              disabled={!canScrollRight}
              className={`p-1 rounded-md transition-colors ${canScrollRight ? 'bg-white/[0.06] text-zinc-300 hover:bg-white/10' : 'text-zinc-700 cursor-not-allowed'}`}
              data-testid="remix-scroll-right"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>

      {/* Cards Grid */}
      <div className={`grid gap-2 ${placement === 'completion' ? 'grid-cols-3' : 'grid-cols-2 sm:grid-cols-4'}`}>
        {visible.map((item) => (
          <RemixCard key={item.item_id} item={item} onRemix={handleRemix} compact={placement === 'completion'} />
        ))}
      </div>

      {/* Competitive nudge */}
      <p className="text-[10px] text-zinc-600 text-center mt-2" data-testid="remix-nudge">
        Can you make a better version?
      </p>
    </div>
  );
}

function RemixCard({ item, onRemix, compact }) {
  // Trending badge logic
  const remixes = item.remixes_count || 0;
  let badge = null;
  if (remixes >= 10000) badge = { label: 'Trending', color: 'bg-orange-500/80 text-white' };
  else if (remixes >= 5000) badge = { label: 'Popular', color: 'bg-amber-500/80 text-white' };
  else if (remixes >= 1000) badge = { label: 'Rising', color: 'bg-blue-500/80 text-white' };

  return (
    <div
      className="group rounded-lg border border-white/[0.06] bg-white/[0.02] overflow-hidden hover:border-indigo-500/30 hover:bg-indigo-500/5 transition-all cursor-pointer"
      onClick={() => onRemix(item)}
      data-testid={`remix-card-${item.item_id}`}
    >
      {/* Thumbnail */}
      <div className={`relative ${compact ? 'aspect-[4/3]' : 'aspect-video'} bg-zinc-800/60 overflow-hidden`}>
        {item.thumbnail_url ? (
          <img
            src={item.thumbnail_url}
            alt={item.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Flame className="w-6 h-6 text-zinc-700" />
          </div>
        )}
        {/* Trending badge */}
        {badge && (
          <span className={`absolute top-1.5 left-1.5 text-[8px] font-bold px-1.5 py-0.5 rounded-full ${badge.color}`} data-testid={`trending-badge-${item.item_id}`}>
            {badge.label}
          </span>
        )}
        {/* Remix count overlay */}
        {item.remixes_count > 0 && (
          <span className="absolute top-1.5 right-1.5 flex items-center gap-0.5 bg-black/60 backdrop-blur-sm text-[9px] text-white font-semibold px-1.5 py-0.5 rounded-full">
            <RefreshCw className="w-2.5 h-2.5" /> {formatCount(item.remixes_count)}
          </span>
        )}
        {/* Hover overlay */}
        <div className="absolute inset-0 bg-indigo-600/0 group-hover:bg-indigo-600/20 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
          <span className="bg-white/90 text-zinc-900 text-[11px] font-bold px-3 py-1.5 rounded-full flex items-center gap-1 shadow-lg">
            <RefreshCw className="w-3 h-3" /> Remix This
          </span>
        </div>
      </div>

      {/* Info */}
      <div className="p-2">
        <p className="text-[11px] font-medium text-zinc-300 truncate group-hover:text-indigo-300 transition-colors">
          {item.title}
        </p>
        {!compact && (
          <p className="text-[9px] text-zinc-600 truncate mt-0.5">
            {item.description}
          </p>
        )}
        <div className="flex items-center gap-2 mt-1">
          {item.remixes_count > 0 && (
            <span className="text-[9px] text-orange-400/80 flex items-center gap-0.5">
              <RefreshCw className="w-2.5 h-2.5" /> {formatCount(item.remixes_count)} remixed today
            </span>
          )}
          {item.views_count > 0 && (
            <span className="text-[9px] text-zinc-600 flex items-center gap-0.5">
              <Eye className="w-2.5 h-2.5" /> {formatCount(item.views_count)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
