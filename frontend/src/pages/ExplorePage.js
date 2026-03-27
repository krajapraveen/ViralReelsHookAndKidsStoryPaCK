import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  Play, Flame, Sparkles, Zap, Film, Heart, Eye,
  SlidersHorizontal, ChevronDown, Rocket, ArrowRight, Wand2
} from 'lucide-react';
import { SafeImage } from '../components/SafeImage';

const API = process.env.REACT_APP_BACKEND_URL;

/* ── Shared: proof labels ── */
function getProofLabel(count) {
  if (count >= 10) return { text: 'Trending', Icon: Flame, bg: 'bg-amber-500/20', fg: 'text-amber-400' };
  if (count > 0)   return { text: 'Early story', Icon: Zap, bg: 'bg-violet-500/20', fg: 'text-violet-400' };
  return { text: 'Just dropped', Icon: Sparkles, bg: 'bg-emerald-500/20', fg: 'text-emerald-400' };
}

/* ── Click psychology ── */
const CTA_VARIANTS = ['See What Happens Next', 'Continue This Story', 'What Happens Next?'];
const URGENCY_ACTIVE = ['Someone just continued this', 'This story is gaining momentum', 'Others are watching this'];
const URGENCY_FIRST = ['Your turn to continue', "This story isn\u2019t finished", 'Be the one who writes what\u2019s next'];

function formatHook(text) {
  if (!text) return 'A story waiting to unfold\u2026';
  const clean = text.replace(/\n/g, ' ').trim();
  if (clean.length <= 65) return clean;
  const cut = clean.substring(0, 65).lastIndexOf(' ');
  return clean.substring(0, cut > 20 ? cut : 60) + '\u2026';
}

const STICKY_MSGS = [
  'Someone just continued one of these stories\u2026',
  'This story has no ending yet\u2026',
  'What happens next is up to you\u2026',
  'These stories are still being written\u2026',
];

const CATEGORIES = [
  { key: 'all',       label: 'All',        icon: Flame },
  { key: 'emotional', label: 'Emotional',  icon: Heart },
  { key: 'mystery',   label: 'Mystery',    icon: Eye },
  { key: 'kids',      label: 'Kids',       icon: Sparkles },
  { key: 'viral',     label: 'Viral Hooks',icon: Rocket },
];

const SORTS = [
  { key: 'trending',       label: 'Trending' },
  { key: 'new',            label: 'New' },
  { key: 'most_continued', label: 'Most Continued' },
];

export default function ExplorePage() {
  const navigate = useNavigate();
  const [stories, setStories] = useState([]);
  const [category, setCategory] = useState('all');
  const [sort, setSort] = useState('trending');
  const [cursor, setCursor] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [total, setTotal] = useState(0);
  const [categoryCounts, setCategoryCounts] = useState({});
  const [showSortMenu, setShowSortMenu] = useState(false);
  const sentinelRef = useRef(null);

  const fetchStories = useCallback(async (cat, srt, cur, append = false) => {
    if (append) setLoadingMore(true); else setLoading(true);
    try {
      const res = await axios.get(`${API}/api/engagement/explore`, {
        params: { category: cat, sort: srt, cursor: cur, limit: 12 },
      });
      const data = res.data;
      setStories(prev => append ? [...prev, ...data.stories] : data.stories);
      setCursor(data.next_cursor);
      setHasMore(data.next_cursor !== null);
      setTotal(data.total);
      setCategoryCounts(data.categories || {});
    } catch (e) {
      console.error('Explore fetch failed:', e);
    }
    setLoading(false);
    setLoadingMore(false);
  }, []);

  useEffect(() => {
    setCursor(0);
    setStories([]);
    setHasMore(true);
    fetchStories(category, sort, 0, false);
  }, [category, sort, fetchStories]);

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && hasMore && !loadingMore && cursor !== null) {
        fetchStories(category, sort, cursor, true);
      }
    }, { rootMargin: '200px' });
    obs.observe(el);
    return () => obs.disconnect();
  }, [hasMore, loadingMore, cursor, category, sort, fetchStories]);

  return (
    <div className="min-h-screen bg-[#06060e] text-white" data-testid="explore-page">
      <style>{`
        @keyframes shimmer-glow {
          0%,100%{box-shadow:0 0 8px rgba(245,158,11,.15)}
          50%{box-shadow:0 0 22px rgba(245,158,11,.4)}
        }
        .shimmer-cta{animation:shimmer-glow 2.5s ease-in-out infinite}
      `}</style>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl sm:text-3xl font-black text-white" data-testid="explore-title">Explore Stories</h1>
            <p className="text-sm text-slate-500 mt-1">
              {total > 0 ? `${total} stories to discover` : 'Discover stories created by the community'}
            </p>
          </div>
          <button onClick={() => navigate('/app/story-video-studio')}
            className="h-10 px-5 bg-gradient-to-r from-amber-600 to-rose-600 rounded-xl text-white text-sm font-bold flex items-center gap-2 hover:opacity-90 transition-opacity shimmer-cta"
            data-testid="explore-create-btn">
            <Wand2 className="w-4 h-4" /> Create Story
          </button>
        </div>

        {/* Category filters */}
        <div className="flex items-center gap-2 mb-4 overflow-x-auto pb-1" data-testid="category-filters">
          {CATEGORIES.map(cat => {
            const Icon = cat.icon;
            const count = categoryCounts[cat.key] || 0;
            const active = category === cat.key;
            return (
              <button key={cat.key} onClick={() => setCategory(cat.key)}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-bold whitespace-nowrap transition-all ${
                  active
                    ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                    : 'bg-slate-900/60 text-slate-400 border border-slate-800/40 hover:text-white hover:border-slate-700'
                }`}
                data-testid={`filter-${cat.key}`}>
                <Icon className="w-3.5 h-3.5" /> {cat.label}
                {count > 0 && <span className="text-[10px] opacity-60">({count})</span>}
              </button>
            );
          })}
        </div>

        {/* Sort */}
        <div className="flex items-center justify-between mb-6">
          <p className="text-xs text-slate-500">{total} stories</p>
          <div className="relative">
            <button onClick={() => setShowSortMenu(!showSortMenu)}
              className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors"
              data-testid="sort-toggle">
              <SlidersHorizontal className="w-3.5 h-3.5" />
              {SORTS.find(s => s.key === sort)?.label}
              <ChevronDown className="w-3 h-3" />
            </button>
            {showSortMenu && (
              <div className="absolute right-0 top-full mt-1 bg-slate-900 border border-slate-800 rounded-xl py-1 z-10 shadow-xl" data-testid="sort-menu">
                {SORTS.map(s => (
                  <button key={s.key} onClick={() => { setSort(s.key); setShowSortMenu(false); }}
                    className={`block w-full px-4 py-2 text-xs text-left transition-colors ${sort === s.key ? 'text-amber-400' : 'text-slate-400 hover:text-white'}`}
                    data-testid={`sort-${s.key}`}>
                    {s.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Loading */}
        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="w-8 h-8 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
          </div>
        )}

        {/* Empty state */}
        {!loading && stories.length === 0 && (
          <div className="text-center py-20" data-testid="empty-state">
            <div className="w-16 h-16 mx-auto rounded-full bg-amber-500/10 flex items-center justify-center mb-4">
              <Rocket className="w-8 h-8 text-amber-400" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">Be the first to create a story in this category</h3>
            <p className="text-sm text-slate-500 mb-4">Start a new story and it will appear here for others to discover.</p>
            <button onClick={() => navigate('/app/story-video-studio')}
              className="h-10 px-6 bg-gradient-to-r from-amber-500 to-rose-500 rounded-xl text-white text-sm font-bold hover:opacity-90 transition-opacity"
              data-testid="empty-create-btn">
              Create Story
            </button>
          </div>
        )}

        {/* Stories grid */}
        {!loading && stories.length > 0 && (
          <div data-testid="stories-grid">
            <StoriesWithTriggers stories={stories} navigate={navigate} />
          </div>
        )}

        {/* Sentinel */}
        <div ref={sentinelRef} className="h-1" />

        {loadingMore && (
          <div className="flex items-center justify-center py-8" data-testid="loading-more">
            <div className="w-6 h-6 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
            <span className="ml-3 text-xs text-slate-500">Loading more stories...</span>
          </div>
        )}

        {!hasMore && stories.length > 0 && (
          <div className="text-center py-8" data-testid="end-of-list">
            <p className="text-sm text-slate-600">You've explored all stories</p>
            <button onClick={() => navigate('/app/story-video-studio')}
              className="mt-3 text-xs text-amber-400 hover:text-amber-300 font-bold transition-colors">
              Create your own story <ArrowRight className="w-3 h-3 inline ml-1" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}


function StoriesWithTriggers({ stories, navigate }) {
  const rows = [];
  const ROW = 4;
  for (let i = 0; i < stories.length; i += ROW) {
    const chunk = stories.slice(i, i + ROW);
    rows.push(
      <div key={`row-${i}`} className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {chunk.map((story, idx) => (
          <ExploreCard key={story.job_id} story={story} navigate={navigate} index={i + idx} />
        ))}
      </div>
    );
    if (i > 0 && i % (ROW * 2) === 0 && i < stories.length - ROW) {
      const msg = STICKY_MSGS[Math.floor(i / (ROW * 2)) % STICKY_MSGS.length];
      rows.push(
        <div key={`sticky-${i}`} className="my-6 py-4 text-center" data-testid="stickiness-trigger">
          <p className="text-sm font-bold text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-rose-400">{msg}</p>
          <div className="mt-2 flex justify-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500/60 animate-pulse" />
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500/60 animate-pulse" style={{ animationDelay: '0.2s' }} />
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500/60 animate-pulse" style={{ animationDelay: '0.4s' }} />
          </div>
        </div>
      );
    }
  }
  return <div className="space-y-3">{rows}</div>;
}


function ExploreCard({ story, navigate, index = 0 }) {
  const [hovered, setHovered] = useState(false);
  const proof = getProofLabel(story.remix_count || 0);
  const ProofIcon = proof.Icon;
  const isActive = (story.remix_count || 0) > 0;
  const hook = formatHook(story.hook_text || story.title);
  const ctaText = CTA_VARIANTS[index % CTA_VARIANTS.length];
  const urgencyPool = isActive ? URGENCY_ACTIVE : URGENCY_FIRST;
  const urgency = urgencyPool[index % urgencyPool.length];

  const handleClick = () => {
    axios.post(`${API}/api/engagement/card-click`, {
      story_id: story.job_id, cta_variant: ctaText, source: 'explore'
    }).catch(() => {});
    localStorage.setItem('remix_data', JSON.stringify({
      prompt: story.hook_text || story.title || '',
      timestamp: Date.now(), source_tool: 'explore-continue',
      remixFrom: { parent_video_id: story.job_id, title: story.title }
    }));
    navigate('/app/story-video-studio');
  };

  return (
    <div className="group relative rounded-xl overflow-hidden cursor-pointer transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-amber-500/10 border border-slate-800/40 hover:border-amber-500/30"
      onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)}
      onClick={handleClick} data-testid="explore-card">
      <div className="aspect-[4/5] relative overflow-hidden bg-slate-900">
        <SafeImage src={story.thumbnail_url} alt={story.title} aspectRatio="4/5" fallbackType="gradient" titleOverlay={story.title}
          className="rounded-none" imgClassName={`transition-all duration-700 ${hovered ? 'scale-110 brightness-110' : 'scale-100 brightness-[0.85]'}`} />
        <div className="absolute inset-0 bg-gradient-to-t from-black via-black/40 to-transparent" />
        <div className={`absolute top-2.5 left-2.5 flex items-center gap-1 backdrop-blur-md rounded-full px-2.5 py-1 ${proof.bg} ${proof.fg}`}>
          <ProofIcon className="w-3 h-3" /><span className="text-[10px] font-bold">{proof.text}</span>
        </div>
        <div className={`absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 transition-all duration-300 ${hovered ? 'opacity-100 scale-100' : 'opacity-0 scale-75'}`}>
          <div className="w-14 h-14 rounded-full bg-amber-500/90 flex items-center justify-center shadow-xl shadow-amber-500/30 shimmer-cta">
            <Play className="w-7 h-7 text-white fill-white ml-0.5" />
          </div>
        </div>
        <div className="absolute bottom-0 left-0 right-0 p-3.5 space-y-1.5">
          <p className="text-sm font-black text-white leading-snug line-clamp-2" data-testid="explore-hook">{hook}</p>
          <p className="text-[10px] text-slate-300/60 font-medium">{urgency}</p>
          <button className={`w-full py-2 rounded-lg text-[11px] font-bold flex items-center justify-center gap-1.5 transition-all duration-300 ${
            hovered ? 'bg-amber-500 text-black shadow-lg shadow-amber-500/30' : 'bg-white/10 backdrop-blur-sm text-white border border-white/10'
          }`} data-testid="explore-cta">
            <Play className={`w-3.5 h-3.5 ${hovered ? 'fill-black' : 'fill-white'}`} /> {ctaText}
          </button>
        </div>
      </div>
    </div>
  );
}
