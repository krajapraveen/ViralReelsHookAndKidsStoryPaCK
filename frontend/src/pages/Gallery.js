import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import {
  Play, Sparkles, Eye, RefreshCcw, ChevronRight, ChevronLeft, ChevronUp, ChevronDown,
  Flame, Heart, Film, Clock, Search, X, ArrowRight, Star, Zap,
  Briefcase, GraduationCap, Camera, Clapperboard, Volume2, VolumeX, Share2, Folder,
} from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';
import { SafeImage } from '../components/SafeImage';
import { trackPageView } from '../utils/growthAnalytics';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// ── Helpers ─────────────────────────────────────────────
function fmtNum(n) {
  if (!n) return '0';
  if (n >= 1000000) return (n / 1000000).toFixed(1).replace(/\.0$/, '') + 'M';
  if (n >= 1000) return (n / 1000).toFixed(1).replace(/\.0$/, '') + 'K';
  return n.toString();
}
function fmtDuration(s) {
  if (!s) return '';
  if (s < 60) return `${s}s`;
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

const RAIL_ICONS = {
  fire: Flame, remix: RefreshCcw, star: Star, film: Film,
  heart: Heart, camera: Camera, briefcase: Briefcase,
  sparkles: Sparkles, bulb: GraduationCap,
  folder: Folder, eye: Eye, zap: Zap,
};

const FILTER_TABS = [
  { id: 'all', label: 'All' },
  { id: 'trending', label: 'Trending' },
  { id: 'Kids Stories', label: 'Kids Stories' },
  { id: 'Reels & Shorts', label: 'Reels' },
  { id: 'Emotional', label: 'Emotional' },
  { id: 'Cinematic AI', label: 'Cinematic' },
  { id: 'Business', label: 'Business' },
  { id: 'Luxury', label: 'Luxury' },
  { id: 'Educational', label: 'Educational' },
];

// ── Skeletons ───────────────────────────────────────────
function HeroSkeleton() {
  return (
    <div className="relative h-[340px] sm:h-[420px] rounded-2xl overflow-hidden bg-slate-800/50 animate-pulse" data-testid="hero-skeleton">
      <div className="absolute bottom-0 left-0 right-0 p-6 sm:p-10">
        <div className="h-3 w-24 bg-slate-700 rounded mb-3" />
        <div className="h-8 w-80 bg-slate-700 rounded mb-2" />
        <div className="h-4 w-64 bg-slate-700 rounded mb-4" />
        <div className="flex gap-3"><div className="h-10 w-28 bg-slate-700 rounded-full" /><div className="h-10 w-28 bg-slate-700 rounded-full" /></div>
      </div>
    </div>
  );
}
function CardSkeleton() {
  return (
    <div className="flex-shrink-0 w-[200px] sm:w-[240px] rounded-xl overflow-hidden bg-slate-800/30 border border-white/[0.04]">
      <div className="aspect-video bg-slate-800/50 animate-pulse" />
      <div className="p-3 space-y-2"><div className="h-4 w-3/4 bg-slate-800/50 rounded animate-pulse" /><div className="h-3 w-1/2 bg-slate-800/50 rounded animate-pulse" /></div>
    </div>
  );
}
function RailSkeleton() {
  return <div className="mb-8"><div className="h-5 w-40 bg-slate-800/50 rounded animate-pulse mb-4" /><div className="flex gap-3 overflow-hidden">{[0,1,2,3,4].map(i => <CardSkeleton key={i} />)}</div></div>;
}

// ── Gallery Card with hover preview ─────────────────────
const activePreviewRef = { current: null };

function GalleryCard({ item, onPreview, onRemix }) {
  const [hovered, setHovered] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const hoverTimer = useRef(null);
  const videoRef = useRef(null);

  const onEnter = () => {
    setHovered(true);
    hoverTimer.current = setTimeout(() => {
      if (activePreviewRef.current && activePreviewRef.current !== videoRef) {
        const prev = activePreviewRef.current.current;
        if (prev) { prev.pause(); prev.currentTime = 0; }
      }
      setShowPreview(true);
      activePreviewRef.current = videoRef;
    }, 400);
  };
  const onLeave = () => {
    setHovered(false);
    clearTimeout(hoverTimer.current);
    setShowPreview(false);
    if (videoRef.current) { videoRef.current.pause(); videoRef.current.currentTime = 0; }
    if (activePreviewRef.current === videoRef) activePreviewRef.current = null;
  };

  const hasVideo = !!(item.output_url || item.full_video_url || item.preview_video_url);

  return (
    <div
      className="flex-shrink-0 w-[200px] sm:w-[240px] rounded-xl overflow-hidden border border-white/[0.04] bg-white/[0.01] hover:border-indigo-500/20 transition-all duration-300 group cursor-pointer"
      onMouseEnter={onEnter} onMouseLeave={onLeave}
      onClick={() => onPreview(item)}
      data-testid={`gallery-card-${item.item_id || ''}`}
    >
      <div className="aspect-video bg-black/50 relative overflow-hidden">
        {/* Hover video preview (desktop) */}
        {showPreview && hasVideo && (
          <video
            ref={videoRef}
            src={item.preview_video_url || item.output_url || item.full_video_url}
            className="absolute inset-0 w-full h-full object-cover z-10"
            muted autoPlay loop playsInline
            onError={() => setShowPreview(false)}
          />
        )}
        {/* Hover zoom effect on thumbnail */}
        <div className={`transition-transform duration-700 ${hovered ? 'scale-110' : 'scale-100'}`}>
          <SafeImage src={item.thumbnail_url} alt={item.title} aspectRatio="16/9" titleOverlay={item.title} fallbackType="gradient" className="rounded-none" />
        </div>
        {item.duration_seconds > 0 && (
          <span className="absolute bottom-2 right-2 z-20 text-[10px] font-mono font-bold bg-black/70 backdrop-blur-sm text-white px-1.5 py-0.5 rounded">{fmtDuration(item.duration_seconds)}</span>
        )}
        <div className="absolute top-2 left-2 z-20 flex items-center gap-1.5">
          {item.remixes_count > 0 && <span className="flex items-center gap-0.5 bg-black/60 backdrop-blur-sm text-pink-300 px-1.5 py-0.5 rounded text-[10px] font-semibold"><RefreshCcw className="w-2.5 h-2.5" /> {fmtNum(item.remixes_count)}</span>}
          {item.views_count > 0 && <span className="flex items-center gap-0.5 bg-black/60 backdrop-blur-sm text-slate-300 px-1.5 py-0.5 rounded text-[10px] font-semibold"><Eye className="w-2.5 h-2.5" /> {fmtNum(item.views_count)}</span>}
        </div>
        <div className={`absolute inset-0 bg-black/40 flex items-center justify-center gap-2 transition-opacity duration-200 z-20 ${hovered && !showPreview ? 'opacity-100' : 'opacity-0'}`}>
          <button onClick={(e) => { e.stopPropagation(); onPreview(item); }} className="p-2.5 rounded-full bg-white/10 hover:bg-white/25 text-white backdrop-blur-sm"><Play className="w-5 h-5 ml-0.5" /></button>
          <button onClick={(e) => { e.stopPropagation(); onRemix(item); }} className="p-2.5 rounded-full bg-pink-500/20 hover:bg-pink-500/40 text-pink-200 backdrop-blur-sm" data-testid="card-remix-btn"><RefreshCcw className="w-4 h-4" /></button>
        </div>
      </div>
      <div className="p-2.5">
        <p className="text-sm font-medium text-white truncate leading-tight">{item.title || 'AI Story'}</p>
        <div className="flex items-center justify-between mt-1.5">
          <span className="text-[10px] text-slate-500 truncate">{item.category || ''}</span>
          <button onClick={(e) => { e.stopPropagation(); onRemix(item); }} className="text-[10px] font-semibold text-pink-400 hover:text-pink-300 flex items-center gap-0.5">Remix <ChevronRight className="w-2.5 h-2.5" /></button>
        </div>
      </div>
    </div>
  );
}

// ── Content Rail ────────────────────────────────────────
function ContentRail({ rail, onPreview, onRemix, icon }) {
  const scrollRef = useRef(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(true);
  const Icon = icon || RAIL_ICONS[rail.emoji] || Flame;

  const updateScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    setCanScrollLeft(el.scrollLeft > 10);
    setCanScrollRight(el.scrollLeft < el.scrollWidth - el.clientWidth - 10);
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) { el.addEventListener('scroll', updateScroll, { passive: true }); updateScroll(); return () => el.removeEventListener('scroll', updateScroll); }
  }, [updateScroll, rail.items]);

  const scroll = (dir) => { scrollRef.current?.scrollBy({ left: dir * 600, behavior: 'smooth' }); };

  if (!rail.items?.length) return null;
  return (
    <div className="mb-8 group/rail" data-testid={`rail-${rail.id}`}>
      <div className="flex items-center justify-between mb-3 px-1">
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 text-indigo-400" /><h3 className="text-base font-bold text-white">{rail.name}</h3>
          <span className="text-[10px] text-slate-600 font-medium">{rail.items.length}</span>
        </div>
        <div className="flex items-center gap-1 opacity-0 group-hover/rail:opacity-100 transition-opacity">
          {canScrollLeft && <button onClick={() => scroll(-1)} className="p-1 rounded-full bg-white/5 hover:bg-white/10 text-slate-400"><ChevronLeft className="w-4 h-4" /></button>}
          {canScrollRight && <button onClick={() => scroll(1)} className="p-1 rounded-full bg-white/5 hover:bg-white/10 text-slate-400"><ChevronRight className="w-4 h-4" /></button>}
        </div>
      </div>
      <div ref={scrollRef} className="flex gap-3 overflow-x-auto scrollbar-hide pb-1 -mx-1 px-1 scroll-smooth">
        {rail.items.map((item, idx) => <GalleryCard key={item.item_id || idx} item={item} onPreview={onPreview} onRemix={onRemix} />)}
      </div>
    </div>
  );
}

// ── Featured Hero ───────────────────────────────────────
function FeaturedHero({ items, onPreview, onRemix }) {
  const [activeIdx, setActiveIdx] = useState(0);
  if (!items?.length) return <HeroSkeleton />;
  const item = items[activeIdx];
  return (
    <div className="relative h-[340px] sm:h-[420px] rounded-2xl overflow-hidden mb-8" data-testid="gallery-hero">
      <div className="absolute inset-0">
        <img src={item.thumbnail_url} alt={item.title} className="w-full h-full object-cover" loading="eager" onError={(e) => { e.target.style.display = 'none'; }} />
        <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/60 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-r from-slate-950/80 to-transparent" />
      </div>
      <div className="absolute bottom-0 left-0 right-0 p-6 sm:p-10">
        <div className="flex items-center gap-2 mb-2"><Flame className="w-3.5 h-3.5 text-amber-400" /><span className="text-xs font-bold text-amber-400 uppercase tracking-wider">Trending Now</span></div>
        <h2 className="text-2xl sm:text-4xl font-black text-white mb-1.5 max-w-lg leading-tight" data-testid="hero-title">{item.title}</h2>
        <p className="text-sm text-slate-300 mb-4 max-w-md line-clamp-2">{item.description}</p>
        <div className="flex items-center gap-3 text-xs text-slate-400 mb-4">
          <span className="flex items-center gap-1"><Eye className="w-3 h-3" /> {fmtNum(item.views_count)}</span>
          <span className="flex items-center gap-1"><Heart className="w-3 h-3" /> {fmtNum(item.likes_count)}</span>
          <span className="flex items-center gap-1"><RefreshCcw className="w-3 h-3" /> {fmtNum(item.remixes_count)} remixes</span>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => onPreview(item)} className="bg-white text-black hover:bg-white/90 rounded-full px-5 font-bold text-sm" data-testid="hero-watch-btn"><Play className="w-4 h-4 mr-1.5 fill-black" /> Watch</Button>
          <Button onClick={() => onRemix(item)} variant="outline" className="rounded-full px-5 font-bold text-sm border-white/20 text-white hover:bg-white/10" data-testid="hero-remix-btn"><Sparkles className="w-4 h-4 mr-1.5" /> Remix This</Button>
          <Link to="/app/story-video-studio"><Button variant="outline" className="rounded-full px-5 font-bold text-sm border-white/20 text-white hover:bg-white/10" data-testid="hero-create-btn"><ArrowRight className="w-4 h-4 mr-1.5" /> Create Similar</Button></Link>
        </div>
      </div>
      {items.length > 1 && (
        <div className="absolute bottom-6 right-6 sm:bottom-10 sm:right-10 flex gap-1.5">
          {items.map((_, i) => <button key={i} onClick={() => setActiveIdx(i)} className={`w-2 h-2 rounded-full transition-all ${i === activeIdx ? 'bg-white w-5' : 'bg-white/30 hover:bg-white/50'}`} />)}
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════
// ── IMMERSIVE VIEWER (Vertical-scroll style) ──────────────────
// ═══════════════════════════════════════════════════════
function ImmersiveViewer({ seedItem, allItems, onClose, onRemix }) {
  const [feed, setFeed] = useState([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [muted, setMuted] = useState(true);
  const containerRef = useRef(null);
  const videoRefs = useRef({});

  useEffect(() => {
    document.body.style.overflow = 'hidden';
    loadFeed();
    return () => { document.body.style.overflow = ''; };
  }, []);

  const loadFeed = async () => {
    try {
      const res = await fetch(`${API_URL}/api/gallery/feed?seed_item_id=${seedItem?.item_id || ''}&limit=20`);
      const data = await res.json();
      setFeed(data.items || []);
      setCurrentIdx(data.seed_index || 0);
    } catch {
      if (allItems?.length) { setFeed(allItems); }
    }
  };

  const trackView = (item) => {
    const token = localStorage.getItem('token');
    if (token && item?.item_id) {
      fetch(`${API_URL}/api/gallery/view`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ item_id: item.item_id }),
      }).catch(() => {});
    }
  };

  useEffect(() => {
    if (feed[currentIdx]) trackView(feed[currentIdx]);
  }, [currentIdx, feed]);

  useEffect(() => {
    Object.entries(videoRefs.current).forEach(([idx, ref]) => {
      if (!ref) return;
      if (parseInt(idx) === currentIdx) {
        ref.play().catch(() => {});
      } else {
        ref.pause();
        ref.currentTime = 0;
      }
    });
  }, [currentIdx]);

  const goNext = () => { if (currentIdx < feed.length - 1) setCurrentIdx(i => i + 1); };
  const goPrev = () => { if (currentIdx > 0) setCurrentIdx(i => i - 1); };

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowDown' || e.key === 'j') goNext();
      if (e.key === 'ArrowUp' || e.key === 'k') goPrev();
      if (e.key === 'm') setMuted(m => !m);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [currentIdx, feed.length]);

  // Touch swipe
  const touchStart = useRef(0);
  const onTouchStart = (e) => { touchStart.current = e.touches[0].clientY; };
  const onTouchEnd = (e) => {
    const diff = touchStart.current - e.changedTouches[0].clientY;
    if (diff > 60) goNext();
    else if (diff < -60) goPrev();
  };

  if (!feed.length) return null;
  const item = feed[currentIdx];
  const hasVideo = !!(item.output_url || item.full_video_url);

  return (
    <div
      className="fixed inset-0 z-[60] bg-black flex items-center justify-center"
      ref={containerRef}
      onTouchStart={onTouchStart} onTouchEnd={onTouchEnd}
      data-testid="immersive-viewer"
    >
      {/* Close button */}
      <button onClick={onClose} className="absolute top-4 left-4 z-50 p-2 rounded-full bg-white/10 hover:bg-white/20 text-white backdrop-blur-sm transition-colors" data-testid="immersive-close">
        <X className="w-5 h-5" />
      </button>

      {/* Navigation hint */}
      <div className="absolute top-4 right-4 z-50 text-[10px] text-white/30 hidden sm:block">
        <kbd className="px-1 py-0.5 bg-white/5 rounded text-[9px]">↑↓</kbd> navigate &middot; <kbd className="px-1 py-0.5 bg-white/5 rounded text-[9px]">m</kbd> mute &middot; <kbd className="px-1 py-0.5 bg-white/5 rounded text-[9px]">esc</kbd> close
      </div>

      {/* Up/Down navigation (desktop) */}
      {currentIdx > 0 && (
        <button onClick={goPrev} className="absolute top-1/2 -translate-y-1/2 left-1/2 -translate-x-1/2 -mt-[46vh] z-50 p-1.5 rounded-full bg-white/5 hover:bg-white/15 text-white/50 hover:text-white transition-all hidden sm:flex" data-testid="immersive-prev">
          <ChevronUp className="w-5 h-5" />
        </button>
      )}
      {currentIdx < feed.length - 1 && (
        <button onClick={goNext} className="absolute top-1/2 -translate-y-1/2 left-1/2 -translate-x-1/2 mt-[46vh] z-50 p-1.5 rounded-full bg-white/5 hover:bg-white/15 text-white/50 hover:text-white transition-all hidden sm:flex" data-testid="immersive-next">
          <ChevronDown className="w-5 h-5" />
        </button>
      )}

      {/* MAIN CONTENT — centered vertical video */}
      <div className="relative w-full h-full sm:w-auto sm:h-[90vh] sm:aspect-[9/16] sm:rounded-2xl overflow-hidden bg-black">
        {/* Video / Thumbnail */}
        {hasVideo ? (
          <>
            {/* Preload adjacent videos as hidden elements */}
            {feed[currentIdx - 1] && (feed[currentIdx - 1].output_url || feed[currentIdx - 1].full_video_url) && (
              <video
                key={`pre-${currentIdx - 1}`}
                ref={el => { videoRefs.current[currentIdx - 1] = el; }}
                src={feed[currentIdx - 1].output_url || feed[currentIdx - 1].full_video_url}
                className="hidden" preload="auto" muted
              />
            )}
            {feed[currentIdx + 1] && (feed[currentIdx + 1].output_url || feed[currentIdx + 1].full_video_url) && (
              <video
                key={`pre-${currentIdx + 1}`}
                ref={el => { videoRefs.current[currentIdx + 1] = el; }}
                src={feed[currentIdx + 1].output_url || feed[currentIdx + 1].full_video_url}
                className="hidden" preload="auto" muted
              />
            )}
            <video
              key={`main-${currentIdx}`}
              ref={el => { videoRefs.current[currentIdx] = el; }}
              src={item.output_url || item.full_video_url}
              className="w-full h-full object-contain bg-black"
              muted={muted} autoPlay loop playsInline
              poster={item.thumbnail_url}
            />
          </>
        ) : (
          /* ── Rich Preview Fallback (no video) ── */
          <div className="w-full h-full relative" data-testid="immersive-preview-fallback">
            {/* Background image with blur overlay */}
            <div className="absolute inset-0">
              <SafeImage src={item.thumbnail_url} alt={item.title} aspectRatio="9/16" titleOverlay={item.title} fallbackType="gradient" />
              <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />
            </div>
            {/* Centered preview card */}
            <div className="absolute inset-0 flex items-center justify-center p-4 sm:p-6 z-10">
              <div className="w-full max-w-sm space-y-4">
                {/* Thumbnail */}
                <div className="rounded-xl overflow-hidden border border-white/10 shadow-2xl">
                  <SafeImage src={item.thumbnail_url} alt={item.title} aspectRatio="16/9" titleOverlay={item.title} fallbackType="gradient" />
                </div>
                {/* Video unavailable badge */}
                <div className="flex items-center justify-center gap-1.5 text-[10px] text-amber-400/80 bg-amber-500/10 rounded-lg py-1.5 px-3 border border-amber-500/15">
                  <Film className="w-3 h-3" />
                  <span className="font-medium">Video preview not available</span>
                </div>
                {/* Title & description */}
                <div>
                  <h3 className="text-white font-bold text-base leading-tight mb-1">{item.title}</h3>
                  {item.description && <p className="text-white/50 text-xs leading-relaxed line-clamp-3">{item.description}</p>}
                </div>
                {/* Stats row */}
                <div className="flex items-center gap-3 text-[10px] text-white/40">
                  {item.views_count > 0 && <span className="flex items-center gap-0.5"><Eye className="w-2.5 h-2.5" /> {fmtNum(item.views_count)} views</span>}
                  {item.likes_count > 0 && <span className="flex items-center gap-0.5"><Heart className="w-2.5 h-2.5" /> {fmtNum(item.likes_count)}</span>}
                  {item.remixes_count > 0 && <span className="flex items-center gap-0.5"><RefreshCcw className="w-2.5 h-2.5" /> {fmtNum(item.remixes_count)} remixes</span>}
                  {item.category && <span>{item.category}</span>}
                </div>
                {/* Story excerpt if available */}
                {item.story_text && (
                  <div className="bg-white/[0.04] rounded-lg p-3 border border-white/[0.06]">
                    <p className="text-[10px] text-slate-500 font-medium mb-1 uppercase tracking-wider">Story Excerpt</p>
                    <p className="text-xs text-white/60 leading-relaxed line-clamp-4 italic">{item.story_text}</p>
                  </div>
                )}
                {/* Action buttons */}
                <div className="flex gap-2 pt-1">
                  <Button onClick={() => { onRemix(item); onClose(); }} className="flex-1 bg-gradient-to-r from-violet-600 to-pink-600 hover:opacity-90 text-white rounded-full py-2.5 text-xs font-bold" data-testid="preview-remix-cta">
                    <Sparkles className="w-3.5 h-3.5 mr-1.5" /> Remix This
                  </Button>
                  <Link to="/app/story-video-studio" onClick={onClose} className="flex-1">
                    <Button variant="outline" className="w-full rounded-full py-2.5 text-xs font-bold border-white/20 text-white hover:bg-white/10" data-testid="preview-create-cta">
                      <ArrowRight className="w-3.5 h-3.5 mr-1.5" /> Create Similar
                    </Button>
                  </Link>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Bottom gradient — only for video items */}
        {hasVideo && <div className="absolute inset-x-0 bottom-0 h-2/5 bg-gradient-to-t from-black/90 via-black/40 to-transparent pointer-events-none" />}

        {/* Right side actions */}
        <div className={`absolute right-3 ${hasVideo ? 'bottom-40 sm:bottom-48' : 'bottom-6'} flex flex-col items-center gap-4 z-30`}>
          <button className="flex flex-col items-center gap-0.5 text-white/80 hover:text-white transition-colors" onClick={() => {}}>
            <div className="w-10 h-10 rounded-full bg-white/10 backdrop-blur-sm flex items-center justify-center"><Heart className="w-5 h-5" /></div>
            <span className="text-[10px]">{fmtNum(item.likes_count)}</span>
          </button>
          <button className="flex flex-col items-center gap-0.5 text-white/80 hover:text-white transition-colors" onClick={() => { onRemix(item); onClose(); }} data-testid="immersive-remix-btn">
            <div className="w-10 h-10 rounded-full bg-pink-500/20 backdrop-blur-sm flex items-center justify-center"><RefreshCcw className="w-5 h-5 text-pink-300" /></div>
            <span className="text-[10px]">{fmtNum(item.remixes_count)}</span>
          </button>
          <button className="flex flex-col items-center gap-0.5 text-white/80 hover:text-white transition-colors" onClick={() => {}}>
            <div className="w-10 h-10 rounded-full bg-white/10 backdrop-blur-sm flex items-center justify-center"><Share2 className="w-5 h-5" /></div>
            <span className="text-[10px]">Share</span>
          </button>
          {hasVideo && (
            <button className="flex flex-col items-center gap-0.5 text-white/80 hover:text-white transition-colors" onClick={() => setMuted(m => !m)} data-testid="immersive-mute-btn">
              <div className="w-10 h-10 rounded-full bg-white/10 backdrop-blur-sm flex items-center justify-center">
                {muted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
              </div>
              <span className="text-[10px]">{muted ? 'Unmute' : 'Muted'}</span>
            </button>
          )}
        </div>

        {/* Bottom info — video items only */}
        {hasVideo && (
          <div className="absolute inset-x-0 bottom-0 p-4 sm:p-5 z-30">
            <p className="text-white font-bold text-base sm:text-lg leading-tight mb-1 max-w-[70%]">{item.title}</p>
            <p className="text-white/60 text-xs sm:text-sm mb-3 max-w-[70%] line-clamp-2">{item.description}</p>
            <div className="flex items-center gap-2 text-[10px] text-white/40 mb-3">
              <span className="flex items-center gap-0.5"><Eye className="w-2.5 h-2.5" /> {fmtNum(item.views_count)} views</span>
              <span>&middot;</span>
              <span>{item.category}</span>
              {item.duration_seconds > 0 && <><span>&middot;</span><span>{fmtDuration(item.duration_seconds)}</span></>}
            </div>
            <div className="flex gap-2">
              <Button onClick={() => { onRemix(item); onClose(); }} className="bg-gradient-to-r from-violet-600 to-pink-600 hover:opacity-90 text-white rounded-full px-4 py-2 text-xs font-bold" data-testid="immersive-remix-cta">
                <Sparkles className="w-3.5 h-3.5 mr-1.5" /> Remix This
              </Button>
              <Link to="/app/story-video-studio" onClick={onClose}>
                <Button variant="outline" className="rounded-full px-4 py-2 text-xs font-bold border-white/20 text-white hover:bg-white/10">
                  <ArrowRight className="w-3.5 h-3.5 mr-1.5" /> Create Similar
                </Button>
              </Link>
            </div>
          </div>
        )}

        {/* Position indicator */}
        <div className="absolute top-4 right-4 z-30 text-[10px] text-white/30 bg-black/30 rounded-full px-2 py-0.5 backdrop-blur-sm">
          {currentIdx + 1} / {feed.length}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════
// ── MAIN GALLERY PAGE ─────────────────────────────────
// ═══════════════════════════════════════════════════════
export default function Gallery() {
  const [featured, setFeatured] = useState([]);
  const [rails, setRails] = useState([]);
  const [exploreItems, setExploreItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState('all');
  const [exploreSort, setExploreSort] = useState('trending');
  const [searchQuery, setSearchQuery] = useState('');
  const [immersiveItem, setImmersiveItem] = useState(null);
  const [userFeed, setUserFeed] = useState(null);
  const navigate = useNavigate();

  const isLoggedIn = !!localStorage.getItem('token');

  useEffect(() => {
    loadGallery();
    if (isLoggedIn) loadUserFeed();
    trackPageView({ source_page: '/explore', origin: 'direct' });
  }, []);

  useEffect(() => { loadExplore(); }, [activeFilter, exploreSort]);

  const loadGallery = async () => {
    setLoading(true);
    try {
      const [f, r, e] = await Promise.all([
        fetch(`${API_URL}/api/gallery/featured`).then(r => r.json()),
        fetch(`${API_URL}/api/gallery/rails`).then(r => r.json()),
        fetch(`${API_URL}/api/gallery/explore?sort=trending&limit=24`).then(r => r.json()),
      ]);
      setFeatured(f.featured || []);
      setRails(r.rails || []);
      setExploreItems(e.items || []);
    } catch (err) { console.error('Gallery load:', err); }
    finally { setLoading(false); }
  };

  const loadUserFeed = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/gallery/user-feed`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      setUserFeed(data);
    } catch {}
  };

  const loadExplore = async () => {
    try {
      const params = new URLSearchParams({ sort: exploreSort, limit: '24' });
      if (activeFilter !== 'all' && activeFilter !== 'trending') params.set('category', activeFilter);
      const data = await fetch(`${API_URL}/api/gallery/explore?${params}`).then(r => r.json());
      setExploreItems(data.items || []);
    } catch {}
  };

  const handleRemix = (item) => {
    const token = localStorage.getItem('token');
    if (!token) { navigate('/signup?redirect=/app/story-video-studio&remix=true'); return; }
    try {
      axios.post(`${API_URL}/api/remix/track`, {
        source_tool: 'gallery', target_tool: 'story-video-studio',
        original_prompt: item.story_text || item.description || item.title || '',
        variation_type: 'gallery_remix', variation_label: 'Gallery Remix',
        original_generation_id: item.item_id || item.job_id,
      }, { headers: { Authorization: `Bearer ${token}` } });
    } catch {}
    const remixData = { prompt: item.story_text || item.description || item.title || '', remixFrom: { tool: 'gallery', prompt: item.story_text || item.description || item.title, title: item.title, parentId: item.item_id } };
    localStorage.setItem('remix_data', JSON.stringify(remixData));
    navigate('/app/story-video-studio', { state: remixData });
    toast.success(`Remixing "${item.title}"...`);
  };

  const handlePreview = (item) => {
    setImmersiveItem(item);
    // Track the view
    const token = localStorage.getItem('token');
    if (token && item?.item_id) {
      fetch(`${API_URL}/api/gallery/view`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ item_id: item.item_id }),
      }).catch(() => {});
    }
  };

  const filteredExplore = searchQuery
    ? exploreItems.filter(i => i.title?.toLowerCase().includes(searchQuery.toLowerCase()) || i.description?.toLowerCase().includes(searchQuery.toLowerCase()) || i.tags?.some(t => t.toLowerCase().includes(searchQuery.toLowerCase())))
    : exploreItems;

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-[#0a0d1a] to-slate-950 text-white">
      {/* Nav */}
      <nav className="border-b border-white/[0.04] bg-slate-950/90 backdrop-blur-2xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-14">
          <Link to="/" className="flex items-center gap-2"><Clapperboard className="w-5 h-5 text-indigo-400" /><span className="text-base font-bold tracking-tight">Visionary Suite</span></Link>
          <div className="flex items-center gap-3">
            <Link to="/" className="text-xs text-slate-400 hover:text-white transition-colors hidden sm:block">Home</Link>
            <Link to="/pricing" className="text-xs text-slate-400 hover:text-white transition-colors hidden sm:block">Pricing</Link>
            <Link to="/signup"><Button className="bg-indigo-600 hover:bg-indigo-500 text-white rounded-full px-4 py-1.5 text-xs font-bold" data-testid="gallery-cta">Create Your Own</Button></Link>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-12">
        {/* HERO */}
        {loading ? <HeroSkeleton /> : <FeaturedHero items={featured} onPreview={handlePreview} onRemix={handleRemix} />}

        {/* ──────── USER SECTIONS (logged-in) ──────── */}
        {isLoggedIn && userFeed && (
          <>
            {userFeed.continue_watching?.length > 0 && (
              <ContentRail
                rail={{ id: 'continue-watching', name: 'Continue Watching', emoji: 'eye', items: userFeed.continue_watching }}
                onPreview={handlePreview} onRemix={handleRemix} icon={Clock}
              />
            )}
            {userFeed.your_creations?.length > 0 && (
              <ContentRail
                rail={{ id: 'your-creations', name: 'Your Creations', emoji: 'folder', items: userFeed.your_creations }}
                onPreview={handlePreview} onRemix={handleRemix} icon={Folder}
              />
            )}
            {userFeed.for_you?.length > 0 && (
              <ContentRail
                rail={{ id: 'for-you', name: 'Recommended For You', emoji: 'sparkles', items: userFeed.for_you }}
                onPreview={handlePreview} onRemix={handleRemix} icon={Zap}
              />
            )}
          </>
        )}

        {/* CATEGORY RAILS */}
        {loading ? (
          <>{[0, 1, 2].map(i => <RailSkeleton key={i} />)}</>
        ) : (
          rails.map(rail => <ContentRail key={rail.id} rail={rail} onPreview={handlePreview} onRemix={handleRemix} />)
        )}

        {/* EXPLORE SECTION */}
        <div className="mt-4" data-testid="explore-section">
          <h2 className="text-lg font-bold text-white mb-4">Explore All</h2>
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="Search stories, reels, topics..." className="w-full pl-10 pr-4 py-2.5 bg-white/[0.03] border border-white/[0.06] rounded-xl text-sm text-white placeholder:text-slate-600 focus:outline-none focus:border-indigo-500/30 transition-colors" data-testid="gallery-search" />
            {searchQuery && <button onClick={() => setSearchQuery('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white"><X className="w-4 h-4" /></button>}
          </div>
          <div className="flex gap-1.5 overflow-x-auto scrollbar-hide pb-3 -mx-1 px-1" data-testid="gallery-filters">
            {FILTER_TABS.map(tab => (
              <button key={tab.id} onClick={() => setActiveFilter(tab.id)} className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all flex-shrink-0 ${activeFilter === tab.id ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30' : 'text-slate-500 hover:text-white hover:bg-white/[0.04] border border-transparent'}`} data-testid={`filter-${tab.id}`}>{tab.label}</button>
            ))}
          </div>
          <div className="flex gap-1.5 mb-4">
            {[{ id: 'trending', label: 'Trending', icon: Flame }, { id: 'newest', label: 'Newest', icon: Clock }, { id: 'most_remixed', label: 'Most Remixed', icon: RefreshCcw }].map(s => (
              <button key={s.id} onClick={() => setExploreSort(s.id)} className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${exploreSort === s.id ? 'bg-white/[0.06] text-white' : 'text-slate-600 hover:text-slate-300'}`} data-testid={`sort-${s.id}`}><s.icon className="w-3 h-3" /> {s.label}</button>
            ))}
          </div>
          {filteredExplore.length > 0 ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4" data-testid="explore-grid">
              {filteredExplore.map((item, i) => (
                <div key={item.item_id || i} className="group rounded-xl overflow-hidden border border-white/[0.04] bg-white/[0.01] hover:border-indigo-500/20 transition-all cursor-pointer" onClick={() => handlePreview(item)} data-testid={`explore-card-${i}`}>
                  <div className="aspect-video bg-black/50 relative overflow-hidden">
                    <div className="transition-transform duration-700 group-hover:scale-110"><SafeImage src={item.thumbnail_url} alt={item.title} aspectRatio="16/9" titleOverlay={item.title} fallbackType="gradient" className="rounded-none" /></div>
                    {item.duration_seconds > 0 && <span className="absolute bottom-1.5 right-1.5 z-10 text-[9px] font-mono font-bold bg-black/70 text-white px-1 py-0.5 rounded">{fmtDuration(item.duration_seconds)}</span>}
                    {item.remixes_count > 0 && <span className="absolute top-1.5 left-1.5 z-10 flex items-center gap-0.5 bg-black/60 text-pink-300 px-1.5 py-0.5 rounded text-[9px] font-semibold"><RefreshCcw className="w-2.5 h-2.5" /> {fmtNum(item.remixes_count)}</span>}
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center z-10"><div className="w-10 h-10 rounded-full bg-white/15 flex items-center justify-center backdrop-blur-sm"><Play className="w-5 h-5 text-white ml-0.5" /></div></div>
                  </div>
                  <div className="p-2.5">
                    <p className="text-xs sm:text-sm font-medium text-white truncate">{item.title || 'AI Story'}</p>
                    <div className="flex items-center justify-between mt-1">
                      <div className="flex items-center gap-2 text-[9px] text-slate-500">{item.views_count > 0 && <span>{fmtNum(item.views_count)} views</span>}<span>{item.category}</span></div>
                      <button onClick={(e) => { e.stopPropagation(); handleRemix(item); }} className="text-[10px] font-semibold text-pink-400 hover:text-pink-300 flex items-center gap-0.5" data-testid={`remix-btn-${i}`}><Sparkles className="w-2.5 h-2.5" /> Remix</button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12" data-testid="gallery-empty-filtered">
              <Search className="w-10 h-10 mx-auto mb-3 text-slate-700" />
              <p className="text-sm text-slate-400 mb-1">No matches for this filter</p>
              <Button onClick={() => { setActiveFilter('all'); setSearchQuery(''); }} variant="outline" className="text-xs border-slate-700 text-slate-400 mt-2">Show All Content</Button>
            </div>
          )}
        </div>

        {/* Bottom CTA */}
        <div className="mt-12 rounded-2xl border border-indigo-500/10 bg-gradient-to-r from-indigo-500/[0.03] to-purple-500/[0.03] p-6 sm:p-8 text-center" data-testid="gallery-bottom-cta-section">
          <h3 className="text-base sm:text-lg font-bold text-white mb-2">Pick a story you love. Make it yours.</h3>
          <p className="text-sm text-slate-400 max-w-md mx-auto mb-5">Click Remix on any story above, or create something entirely new.</p>
          <Link to="/app/story-video-studio"><Button className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:opacity-90 text-white rounded-full px-6 py-2.5 text-sm font-bold" data-testid="gallery-create-cta">Create Your Version <ArrowRight className="w-4 h-4 ml-1.5" /></Button></Link>
        </div>
      </div>

      {/* IMMERSIVE VIEWER */}
      {immersiveItem && (
        <ImmersiveViewer
          seedItem={immersiveItem}
          allItems={exploreItems}
          onClose={() => setImmersiveItem(null)}
          onRemix={handleRemix}
        />
      )}
    </div>
  );
}
