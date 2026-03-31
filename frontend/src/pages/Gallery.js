import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import {
  Play, Sparkles, Eye, RefreshCcw, ChevronRight, ChevronLeft,
  Flame, Heart, Film, Clock, Search, X, ArrowRight, Star, Zap,
  BookOpen, Briefcase, GraduationCap, Camera, Clapperboard,
} from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';
import { SafeImage } from '../components/SafeImage';
import { trackPageView } from '../utils/growthAnalytics';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// ── Format large numbers ────────────────────────────────
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

// ── Skeleton Components ─────────────────────────────────
function HeroSkeleton() {
  return (
    <div className="relative h-[340px] sm:h-[420px] rounded-2xl overflow-hidden bg-slate-800/50 animate-pulse" data-testid="hero-skeleton">
      <div className="absolute bottom-0 left-0 right-0 p-6 sm:p-10">
        <div className="h-3 w-24 bg-slate-700 rounded mb-3" />
        <div className="h-8 w-80 bg-slate-700 rounded mb-2" />
        <div className="h-4 w-64 bg-slate-700 rounded mb-4" />
        <div className="flex gap-3">
          <div className="h-10 w-28 bg-slate-700 rounded-full" />
          <div className="h-10 w-28 bg-slate-700 rounded-full" />
        </div>
      </div>
    </div>
  );
}

function CardSkeleton() {
  return (
    <div className="flex-shrink-0 w-[220px] sm:w-[260px] rounded-xl overflow-hidden bg-slate-800/30 border border-white/[0.04]">
      <div className="aspect-video bg-slate-800/50 animate-pulse" />
      <div className="p-3 space-y-2">
        <div className="h-4 w-3/4 bg-slate-800/50 rounded animate-pulse" />
        <div className="h-3 w-1/2 bg-slate-800/50 rounded animate-pulse" />
      </div>
    </div>
  );
}

function RailSkeleton() {
  return (
    <div className="mb-8">
      <div className="h-5 w-40 bg-slate-800/50 rounded animate-pulse mb-4" />
      <div className="flex gap-3 overflow-hidden">
        {[0, 1, 2, 3, 4].map(i => <CardSkeleton key={i} />)}
      </div>
    </div>
  );
}

// ── Gallery Card ────────────────────────────────────────
function GalleryCard({ item, onPreview, onRemix, size = 'normal' }) {
  const [hovered, setHovered] = useState(false);
  const w = size === 'large' ? 'w-[280px] sm:w-[320px]' : 'w-[200px] sm:w-[240px]';

  return (
    <div
      className={`flex-shrink-0 ${w} rounded-xl overflow-hidden border border-white/[0.04] bg-white/[0.01] hover:border-indigo-500/20 transition-all duration-300 group cursor-pointer`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={() => onPreview(item)}
      data-testid={`gallery-card-${item.item_id || ''}`}
    >
      <div className="aspect-video bg-black/50 relative overflow-hidden">
        <SafeImage src={item.thumbnail_url} alt={item.title} aspectRatio="16/9" titleOverlay={item.title} fallbackType="gradient" className="rounded-none" />

        {/* Duration badge */}
        {item.duration_seconds > 0 && (
          <span className="absolute bottom-2 right-2 text-[10px] font-mono font-bold bg-black/70 backdrop-blur-sm text-white px-1.5 py-0.5 rounded">
            {fmtDuration(item.duration_seconds)}
          </span>
        )}

        {/* Stats overlay */}
        <div className="absolute top-2 left-2 flex items-center gap-1.5">
          {item.remixes_count > 0 && (
            <span className="flex items-center gap-0.5 bg-black/60 backdrop-blur-sm text-pink-300 px-1.5 py-0.5 rounded text-[10px] font-semibold">
              <RefreshCcw className="w-2.5 h-2.5" /> {fmtNum(item.remixes_count)}
            </span>
          )}
          {item.views_count > 0 && (
            <span className="flex items-center gap-0.5 bg-black/60 backdrop-blur-sm text-slate-300 px-1.5 py-0.5 rounded text-[10px] font-semibold">
              <Eye className="w-2.5 h-2.5" /> {fmtNum(item.views_count)}
            </span>
          )}
        </div>

        {/* Hover overlay */}
        <div className={`absolute inset-0 bg-black/50 flex items-center justify-center gap-2 transition-opacity duration-200 ${hovered ? 'opacity-100' : 'opacity-0'}`}>
          <button onClick={(e) => { e.stopPropagation(); onPreview(item); }} className="p-2.5 rounded-full bg-white/10 hover:bg-white/25 text-white transition-colors backdrop-blur-sm">
            <Play className="w-5 h-5 ml-0.5" />
          </button>
          <button onClick={(e) => { e.stopPropagation(); onRemix(item); }} className="p-2.5 rounded-full bg-pink-500/20 hover:bg-pink-500/40 text-pink-200 transition-colors backdrop-blur-sm" data-testid="card-remix-btn">
            <RefreshCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="p-2.5">
        <p className="text-sm font-medium text-white truncate leading-tight">{item.title || 'AI Story'}</p>
        <div className="flex items-center justify-between mt-1.5">
          <span className="text-[10px] text-slate-500 truncate">{item.category || ''}</span>
          <button
            onClick={(e) => { e.stopPropagation(); onRemix(item); }}
            className="text-[10px] font-semibold text-pink-400 hover:text-pink-300 flex items-center gap-0.5"
          >
            Remix <ChevronRight className="w-2.5 h-2.5" />
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Content Rail ────────────────────────────────────────
function ContentRail({ rail, onPreview, onRemix }) {
  const scrollRef = useRef(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(true);
  const Icon = RAIL_ICONS[rail.emoji] || Flame;

  const updateScrollState = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    setCanScrollLeft(el.scrollLeft > 10);
    setCanScrollRight(el.scrollLeft < el.scrollWidth - el.clientWidth - 10);
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      el.addEventListener('scroll', updateScrollState, { passive: true });
      updateScrollState();
      return () => el.removeEventListener('scroll', updateScrollState);
    }
  }, [updateScrollState, rail.items]);

  const scroll = (dir) => {
    const el = scrollRef.current;
    if (el) el.scrollBy({ left: dir * 600, behavior: 'smooth' });
  };

  if (!rail.items?.length) return null;

  return (
    <div className="mb-8 group/rail" data-testid={`rail-${rail.id}`}>
      <div className="flex items-center justify-between mb-3 px-1">
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 text-indigo-400" />
          <h3 className="text-base font-bold text-white">{rail.name}</h3>
          <span className="text-[10px] text-slate-600 font-medium">{rail.items.length}</span>
        </div>
        <div className="flex items-center gap-1 opacity-0 group-hover/rail:opacity-100 transition-opacity">
          {canScrollLeft && (
            <button onClick={() => scroll(-1)} className="p-1 rounded-full bg-white/5 hover:bg-white/10 text-slate-400"><ChevronLeft className="w-4 h-4" /></button>
          )}
          {canScrollRight && (
            <button onClick={() => scroll(1)} className="p-1 rounded-full bg-white/5 hover:bg-white/10 text-slate-400"><ChevronRight className="w-4 h-4" /></button>
          )}
        </div>
      </div>
      <div ref={scrollRef} className="flex gap-3 overflow-x-auto scrollbar-hide pb-1 -mx-1 px-1 scroll-smooth">
        {rail.items.map((item, idx) => (
          <GalleryCard key={item.item_id || idx} item={item} onPreview={onPreview} onRemix={onRemix} />
        ))}
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
      {/* Background image */}
      <div className="absolute inset-0">
        <img
          src={item.thumbnail_url}
          alt={item.title}
          className="w-full h-full object-cover"
          loading="eager"
          onError={(e) => { e.target.style.display = 'none'; }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/60 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-r from-slate-950/80 to-transparent" />
      </div>

      {/* Content */}
      <div className="absolute bottom-0 left-0 right-0 p-6 sm:p-10">
        <div className="flex items-center gap-2 mb-2">
          <Flame className="w-3.5 h-3.5 text-amber-400" />
          <span className="text-xs font-bold text-amber-400 uppercase tracking-wider">Trending Now</span>
        </div>
        <h2 className="text-2xl sm:text-4xl font-black text-white mb-1.5 max-w-lg leading-tight" data-testid="hero-title">{item.title}</h2>
        <p className="text-sm text-slate-300 mb-4 max-w-md line-clamp-2">{item.description}</p>
        <div className="flex items-center gap-3 text-xs text-slate-400 mb-4">
          <span className="flex items-center gap-1"><Eye className="w-3 h-3" /> {fmtNum(item.views_count)}</span>
          <span className="flex items-center gap-1"><Heart className="w-3 h-3" /> {fmtNum(item.likes_count)}</span>
          <span className="flex items-center gap-1"><RefreshCcw className="w-3 h-3" /> {fmtNum(item.remixes_count)} remixes</span>
          {item.duration_seconds > 0 && <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {fmtDuration(item.duration_seconds)}</span>}
        </div>
        <div className="flex gap-3">
          <Button onClick={() => onPreview(item)} className="bg-white text-black hover:bg-white/90 rounded-full px-5 font-bold text-sm" data-testid="hero-watch-btn">
            <Play className="w-4 h-4 mr-1.5 fill-black" /> Watch
          </Button>
          <Button onClick={() => onRemix(item)} variant="outline" className="rounded-full px-5 font-bold text-sm border-white/20 text-white hover:bg-white/10" data-testid="hero-remix-btn">
            <Sparkles className="w-4 h-4 mr-1.5" /> Remix This
          </Button>
          <Link to="/app/story-video-studio">
            <Button variant="outline" className="rounded-full px-5 font-bold text-sm border-white/20 text-white hover:bg-white/10" data-testid="hero-create-btn">
              <ArrowRight className="w-4 h-4 mr-1.5" /> Create Similar
            </Button>
          </Link>
        </div>
      </div>

      {/* Hero dots */}
      {items.length > 1 && (
        <div className="absolute bottom-6 right-6 sm:bottom-10 sm:right-10 flex gap-1.5">
          {items.map((_, i) => (
            <button key={i} onClick={() => setActiveIdx(i)} className={`w-2 h-2 rounded-full transition-all ${i === activeIdx ? 'bg-white w-5' : 'bg-white/30 hover:bg-white/50'}`} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Video Preview Modal ─────────────────────────────────
function PreviewModal({ item, onClose, onRemix }) {
  if (!item) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm" onClick={onClose} data-testid="video-preview-modal">
      <div className="relative w-full max-w-3xl mx-4 rounded-2xl overflow-hidden border border-white/[0.08] bg-[#0B0F1A]" onClick={(e) => e.stopPropagation()}>
        <button onClick={onClose} className="absolute top-3 right-3 z-10 p-1.5 rounded-full bg-black/50 hover:bg-black/70 text-white transition-colors">
          <X className="w-4 h-4" />
        </button>
        <div className="aspect-video bg-black">
          {item.output_url || item.full_video_url ? (
            <video src={item.output_url || item.full_video_url} className="w-full h-full object-contain" controls autoPlay />
          ) : (
            <div className="relative w-full h-full">
              <SafeImage src={item.thumbnail_url} alt={item.title} aspectRatio="16/9" titleOverlay={item.title} fallbackType="gradient" />
              <div className="absolute inset-0 flex items-center justify-center bg-black/30">
                <span className="px-4 py-2 bg-indigo-600/80 backdrop-blur-sm rounded-full text-white text-sm font-medium">Story Preview</span>
              </div>
            </div>
          )}
        </div>
        <div className="p-5">
          <h3 className="text-lg font-bold text-white mb-1">{item.title}</h3>
          <p className="text-sm text-slate-400 mb-3 line-clamp-2">{item.description}</p>
          <div className="flex items-center gap-4 text-xs text-slate-500 mb-4">
            <span className="flex items-center gap-1"><Eye className="w-3 h-3" /> {fmtNum(item.views_count)}</span>
            <span className="flex items-center gap-1"><Heart className="w-3 h-3" /> {fmtNum(item.likes_count)}</span>
            <span className="flex items-center gap-1"><RefreshCcw className="w-3 h-3 text-pink-400" /> {fmtNum(item.remixes_count)} remixes</span>
          </div>
          <div className="flex gap-2">
            <Button onClick={() => { onRemix(item); onClose(); }} className="flex-1 bg-gradient-to-r from-violet-600 to-pink-600 hover:opacity-90 text-white rounded-xl font-semibold" data-testid="modal-remix-btn">
              <Sparkles className="w-4 h-4 mr-2" /> Remix This Story
            </Button>
            <Button onClick={onClose} variant="outline" className="rounded-xl text-slate-400 border-white/10">Close</Button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════
// ── Main Gallery Page ─────────────────────────────────
// ═══════════════════════════════════════════════════════
export default function Gallery() {
  const [featured, setFeatured] = useState([]);
  const [rails, setRails] = useState([]);
  const [exploreItems, setExploreItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState('all');
  const [exploreSort, setExploreSort] = useState('trending');
  const [searchQuery, setSearchQuery] = useState('');
  const [previewItem, setPreviewItem] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadGallery();
    trackPageView({ source_page: '/explore', origin: 'direct' });
  }, []);

  useEffect(() => {
    loadExplore();
  }, [activeFilter, exploreSort]);

  const loadGallery = async () => {
    setLoading(true);
    try {
      const [featuredRes, railsRes, exploreRes] = await Promise.all([
        fetch(`${API_URL}/api/gallery/featured`).then(r => r.json()),
        fetch(`${API_URL}/api/gallery/rails`).then(r => r.json()),
        fetch(`${API_URL}/api/gallery/explore?sort=trending&limit=24`).then(r => r.json()),
      ]);
      setFeatured(featuredRes.featured || []);
      setRails(railsRes.rails || []);
      setExploreItems(exploreRes.items || []);
    } catch (err) {
      console.error('Gallery load error:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadExplore = async () => {
    try {
      const params = new URLSearchParams({ sort: exploreSort, limit: '24' });
      if (activeFilter !== 'all' && activeFilter !== 'trending') params.set('category', activeFilter);
      const res = await fetch(`${API_URL}/api/gallery/explore?${params}`);
      const data = await res.json();
      setExploreItems(data.items || []);
    } catch {}
  };

  const handleRemix = (item) => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/signup?redirect=/app/story-video-studio&remix=true');
      return;
    }
    try {
      axios.post(`${API_URL}/api/remix/track`, {
        source_tool: 'gallery', target_tool: 'story-video-studio',
        original_prompt: item.story_text || item.description || item.title || '',
        variation_type: 'gallery_remix', variation_label: 'Gallery Remix',
        original_generation_id: item.item_id || item.job_id,
      }, { headers: { Authorization: `Bearer ${token}` } });
    } catch {}
    const remixData = {
      prompt: item.story_text || item.description || item.title || '',
      remixFrom: { tool: 'gallery', prompt: item.story_text || item.description || item.title, title: item.title, parentId: item.item_id },
    };
    localStorage.setItem('remix_data', JSON.stringify(remixData));
    navigate('/app/story-video-studio', { state: remixData });
    toast.success(`Remixing "${item.title}"...`);
  };

  const handlePreview = (item) => setPreviewItem(item);

  const filteredExplore = searchQuery
    ? exploreItems.filter(i => i.title?.toLowerCase().includes(searchQuery.toLowerCase()) || i.description?.toLowerCase().includes(searchQuery.toLowerCase()) || i.tags?.some(t => t.toLowerCase().includes(searchQuery.toLowerCase())))
    : exploreItems;

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-[#0a0d1a] to-slate-950 text-white">
      {/* Nav */}
      <nav className="border-b border-white/[0.04] bg-slate-950/90 backdrop-blur-2xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-14">
          <Link to="/" className="flex items-center gap-2">
            <Clapperboard className="w-5 h-5 text-indigo-400" />
            <span className="text-base font-bold tracking-tight">Visionary Suite</span>
          </Link>
          <div className="flex items-center gap-3">
            <Link to="/" className="text-xs text-slate-400 hover:text-white transition-colors hidden sm:block">Home</Link>
            <Link to="/pricing" className="text-xs text-slate-400 hover:text-white transition-colors hidden sm:block">Pricing</Link>
            <Link to="/signup">
              <Button className="bg-indigo-600 hover:bg-indigo-500 text-white rounded-full px-4 py-1.5 text-xs font-bold" data-testid="gallery-cta">
                Create Your Own
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-12">
        {/* ──────────── HERO ──────────── */}
        {loading ? <HeroSkeleton /> : <FeaturedHero items={featured} onPreview={handlePreview} onRemix={handleRemix} />}

        {/* ──────────── RAILS ──────────── */}
        {loading ? (
          <>{[0, 1, 2].map(i => <RailSkeleton key={i} />)}</>
        ) : (
          rails.map(rail => (
            <ContentRail key={rail.id} rail={rail} onPreview={handlePreview} onRemix={handleRemix} />
          ))
        )}

        {/* ──────────── EXPLORE SECTION ──────────── */}
        <div className="mt-4" data-testid="explore-section">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-white">Explore All</h2>
          </div>

          {/* Search */}
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search stories, reels, topics..."
              className="w-full pl-10 pr-4 py-2.5 bg-white/[0.03] border border-white/[0.06] rounded-xl text-sm text-white placeholder:text-slate-600 focus:outline-none focus:border-indigo-500/30 transition-colors"
              data-testid="gallery-search"
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Filters */}
          <div className="flex gap-1.5 overflow-x-auto scrollbar-hide pb-3 -mx-1 px-1" data-testid="gallery-filters">
            {FILTER_TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveFilter(tab.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all flex-shrink-0 ${
                  activeFilter === tab.id
                    ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                    : 'text-slate-500 hover:text-white hover:bg-white/[0.04] border border-transparent'
                }`}
                data-testid={`filter-${tab.id}`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Sort */}
          <div className="flex gap-1.5 mb-4">
            {[
              { id: 'trending', label: 'Trending', icon: Flame },
              { id: 'newest', label: 'Newest', icon: Clock },
              { id: 'most_remixed', label: 'Most Remixed', icon: RefreshCcw },
            ].map(s => (
              <button
                key={s.id}
                onClick={() => setExploreSort(s.id)}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${
                  exploreSort === s.id ? 'bg-white/[0.06] text-white' : 'text-slate-600 hover:text-slate-300'
                }`}
                data-testid={`sort-${s.id}`}
              >
                <s.icon className="w-3 h-3" /> {s.label}
              </button>
            ))}
          </div>

          {/* Grid */}
          {filteredExplore.length > 0 ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4" data-testid="explore-grid">
              {filteredExplore.map((item, i) => (
                <div
                  key={item.item_id || i}
                  className="group rounded-xl overflow-hidden border border-white/[0.04] bg-white/[0.01] hover:border-indigo-500/20 transition-all cursor-pointer"
                  onClick={() => handlePreview(item)}
                  data-testid={`explore-card-${i}`}
                >
                  <div className="aspect-video bg-black/50 relative overflow-hidden">
                    <SafeImage src={item.thumbnail_url} alt={item.title} aspectRatio="16/9" titleOverlay={item.title} fallbackType="gradient" className="rounded-none" />
                    {item.duration_seconds > 0 && (
                      <span className="absolute bottom-1.5 right-1.5 text-[9px] font-mono font-bold bg-black/70 text-white px-1 py-0.5 rounded">{fmtDuration(item.duration_seconds)}</span>
                    )}
                    {item.remixes_count > 0 && (
                      <span className="absolute top-1.5 left-1.5 flex items-center gap-0.5 bg-black/60 text-pink-300 px-1.5 py-0.5 rounded text-[9px] font-semibold">
                        <RefreshCcw className="w-2.5 h-2.5" /> {fmtNum(item.remixes_count)}
                      </span>
                    )}
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                      <div className="w-10 h-10 rounded-full bg-white/15 flex items-center justify-center backdrop-blur-sm"><Play className="w-5 h-5 text-white ml-0.5" /></div>
                    </div>
                  </div>
                  <div className="p-2.5">
                    <p className="text-xs sm:text-sm font-medium text-white truncate">{item.title || 'AI Story'}</p>
                    <div className="flex items-center justify-between mt-1">
                      <div className="flex items-center gap-2 text-[9px] text-slate-500">
                        {item.views_count > 0 && <span>{fmtNum(item.views_count)} views</span>}
                        <span>{item.category}</span>
                      </div>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleRemix(item); }}
                        className="text-[10px] font-semibold text-pink-400 hover:text-pink-300 flex items-center gap-0.5"
                        data-testid={`remix-btn-${i}`}
                      >
                        <Sparkles className="w-2.5 h-2.5" /> Remix
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            /* NEVER truly empty — but if filters produce no results */
            <div className="text-center py-12" data-testid="gallery-empty-filtered">
              <Search className="w-10 h-10 mx-auto mb-3 text-slate-700" />
              <p className="text-sm text-slate-400 mb-1">No matches for this filter</p>
              <p className="text-xs text-slate-600 mb-4">Try a different category or search term</p>
              <Button onClick={() => { setActiveFilter('all'); setSearchQuery(''); }} variant="outline" className="text-xs border-slate-700 text-slate-400">
                Show All Content
              </Button>
            </div>
          )}
        </div>

        {/* Bottom CTA */}
        <div className="mt-12 rounded-2xl border border-indigo-500/10 bg-gradient-to-r from-indigo-500/[0.03] to-purple-500/[0.03] p-6 sm:p-8 text-center" data-testid="gallery-bottom-cta-section">
          <h3 className="text-base sm:text-lg font-bold text-white mb-2">Pick a story you love. Make it yours.</h3>
          <p className="text-sm text-slate-400 max-w-md mx-auto mb-5">Click Remix on any story above, or create something entirely new.</p>
          <div className="flex items-center justify-center gap-3">
            <Link to="/app/story-video-studio">
              <Button className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:opacity-90 text-white rounded-full px-6 py-2.5 text-sm font-bold" data-testid="gallery-create-cta">
                Create Your Version <ArrowRight className="w-4 h-4 ml-1.5" />
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Preview Modal */}
      <PreviewModal item={previewItem} onClose={() => setPreviewItem(null)} onRemix={handleRemix} />
    </div>
  );
}
