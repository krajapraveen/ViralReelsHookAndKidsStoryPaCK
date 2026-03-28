import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCredits } from '../contexts/CreditContext';
import axios from 'axios';
import { SafeImage } from '../components/SafeImage';
import {
  Play, ChevronRight, ChevronLeft, Sparkles, Zap,
  Flame, Clock, LogIn, Search, Plus, Volume2, VolumeX,
  Film, BookOpen, Star
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

function mediaUrl(path) {
  if (!path) return null;
  if (path.startsWith('/api/media/')) return `${API}${path}`;
  return path;
}

const HOOK_BANK = [
  "The door wasn't supposed to exist...",
  "He heard his name... from inside the wall.",
  "She waited... but no one came.",
  "The last message read: 'Don't look behind you.'",
  "The mirror showed someone else staring back.",
  "They said the forest was empty. They were wrong.",
  "The clock struck thirteen.",
  "She recognized the voice... but he'd been dead for years.",
  "The letter had no sender — just a date. Tomorrow.",
  "The child smiled... and the lights went out.",
];

function getHook(story, idx) {
  if (story.hook_text && story.hook_text.length > 20) return story.hook_text;
  if (story.story_text && story.story_text.length > 20) {
    const sentences = story.story_text.split(/[.!?]+/).filter(s => s.trim().length > 10);
    if (sentences.length > 0) return sentences[0].trim() + '...';
  }
  return HOOK_BANK[idx % HOOK_BANK.length];
}

function getBadge(story, idx) {
  const rm = story.remix_count || 0;
  if (rm >= 5) return { text: 'TRENDING', color: 'bg-amber-500 text-black' };
  if (idx === 0) return { text: '#1', color: 'bg-rose-500 text-white' };
  if (idx < 3) return { text: 'HOT', color: 'bg-rose-500/80 text-white' };
  return { text: 'NEW', color: 'bg-white/15 text-white' };
}

/* ═══════════ HERO — Full-bleed autoplay video ═══════════ */
function HeroSection({ stories, navigate }) {
  const [activeIdx, setActiveIdx] = useState(0);
  const [isMuted, setIsMuted] = useState(true);
  const videoRef = useRef(null);
  const timerRef = useRef(null);

  const heroStories = stories.slice(0, 5);
  const current = heroStories[activeIdx] || {};
  const videoSrc = mediaUrl(current.preview_url || current.output_url);

  useEffect(() => {
    if (heroStories.length <= 1) return;
    timerRef.current = setInterval(() => {
      setActiveIdx(prev => (prev + 1) % heroStories.length);
    }, 10000);
    return () => clearInterval(timerRef.current);
  }, [heroStories.length]);

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.load();
      videoRef.current.play().catch(() => {});
    }
  }, [activeIdx]);

  const goTo = (idx) => {
    clearInterval(timerRef.current);
    setActiveIdx(idx);
    timerRef.current = setInterval(() => {
      setActiveIdx(prev => (prev + 1) % heroStories.length);
    }, 10000);
  };

  if (!heroStories.length) return null;

  const hookText = getHook(current, activeIdx);
  const hash = (current.title || '').split('').reduce((a, c) => a + c.charCodeAt(0), 0);
  const fallbackGrads = [
    'from-violet-900 via-indigo-950 to-black',
    'from-rose-900 via-purple-950 to-black',
    'from-emerald-900 via-teal-950 to-black',
  ];

  return (
    <section className="relative w-full" style={{ height: '50vh', minHeight: '360px' }} data-testid="hero-section">
      {/* Video or gradient background */}
      <div className="absolute inset-0 overflow-hidden bg-black">
        {videoSrc ? (
          <video
            ref={videoRef}
            key={`hero-${current.job_id}`}
            src={videoSrc}
            muted={isMuted}
            autoPlay
            loop
            playsInline
            className="absolute inset-0 w-full h-full object-cover"
            style={{ filter: 'brightness(0.6) saturate(1.2)' }}
            data-testid="hero-video"
          />
        ) : (
          <div className={`absolute inset-0 bg-gradient-to-br ${fallbackGrads[hash % fallbackGrads.length]}`} />
        )}
      </div>

      {/* Layered gradients for text readability */}
      <div className="absolute inset-0 bg-gradient-to-r from-black/70 via-black/30 to-transparent" />
      <div className="absolute inset-0 bg-gradient-to-t from-[#0a0a0f] via-transparent to-transparent" />

      {/* Content */}
      <div className="relative h-full flex flex-col justify-end px-6 sm:px-10 lg:px-14 pb-8 max-w-3xl z-10">
        <div style={{ animation: 'fadeUp .5s ease-out' }}>
          <div className="flex items-center gap-2 mb-2">
            <span className="bg-rose-600 text-white text-[10px] font-black tracking-widest px-2.5 py-0.5 rounded" data-testid="hero-featured-badge">
              FEATURED
            </span>
            {current.animation_style && (
              <span className="bg-white/10 backdrop-blur text-white/60 text-[10px] font-bold px-2 py-0.5 rounded">
                {current.animation_style.replace(/_/g, ' ').toUpperCase()}
              </span>
            )}
            {videoSrc && (
              <span className="flex items-center gap-1 bg-red-600/80 text-white text-[9px] font-black px-2 py-0.5 rounded">
                <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" /> LIVE
              </span>
            )}
          </div>

          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black text-white leading-[1.1] mb-2 drop-shadow-2xl" data-testid="hero-title">
            {current.title || 'Untitled Story'}
          </h1>

          <p className="text-sm sm:text-base text-white/70 leading-relaxed mb-5 max-w-xl line-clamp-2 italic" data-testid="hero-hook">
            "{hookText}"
          </p>

          <div className="flex items-center gap-2.5">
            <button
              onClick={() => navigate('/app/story-video-studio', { state: { continueJob: current.job_id } })}
              className="flex items-center gap-2 px-5 py-2.5 bg-white text-black font-bold rounded-lg text-sm hover:scale-[1.03] active:scale-[0.97] transition-transform shadow-xl shadow-white/10"
              data-testid="hero-play-btn"
            >
              <Play className="w-4 h-4 fill-black" /> Watch & Continue
            </button>
            <button
              onClick={() => navigate('/app/story-video-studio')}
              className="flex items-center gap-2 px-5 py-2.5 bg-white/10 backdrop-blur text-white font-bold rounded-lg text-sm hover:bg-white/20 transition-colors border border-white/10"
              data-testid="hero-create-btn"
            >
              <Plus className="w-4 h-4" /> Create New
            </button>
            {videoSrc && (
              <button
                onClick={() => setIsMuted(!isMuted)}
                className="w-9 h-9 flex items-center justify-center rounded-full bg-black/40 backdrop-blur border border-white/10 text-white/60 hover:text-white hover:bg-black/60 transition-all"
                data-testid="hero-mute-btn"
              >
                {isMuted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Progress dots */}
      {heroStories.length > 1 && (
        <div className="absolute bottom-4 right-6 sm:right-10 flex items-center gap-1 z-10" data-testid="hero-dots">
          {heroStories.map((_, i) => (
            <button key={i} onClick={() => goTo(i)}
              className={`h-[3px] rounded-full transition-all duration-500 ${i === activeIdx ? 'w-8 bg-white' : 'w-3 bg-white/25 hover:bg-white/40'}`}
              data-testid={`hero-dot-${i}`}
            />
          ))}
        </div>
      )}

      <style>{`@keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}`}</style>
    </section>
  );
}

/* ═══════════ STORY CARD — Premium card with hover video ═══════════ */
function StoryCard({ story, idx, navigate, size = 'md' }) {
  const [hovered, setHovered] = useState(false);
  const videoRef = useRef(null);
  const hook = getHook(story, idx);
  const badge = getBadge(story, idx);
  const videoSrc = mediaUrl(story.preview_url || story.output_url);

  useEffect(() => {
    if (hovered && videoRef.current) {
      videoRef.current.play().catch(() => {});
    } else if (!hovered && videoRef.current) {
      videoRef.current.pause();
      videoRef.current.currentTime = 0;
    }
  }, [hovered]);

  const sizes = {
    sm: 'w-40 sm:w-48',
    md: 'w-48 sm:w-56 lg:w-60',
    lg: 'w-56 sm:w-64 lg:w-72',
  };

  return (
    <div
      className={`${sizes[size]} flex-shrink-0 group relative rounded-xl overflow-hidden cursor-pointer`}
      style={{ scrollSnapAlign: 'start' }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={() => navigate('/app/story-video-studio', { state: { continueJob: story.job_id } })}
      data-testid={`story-card-${idx}`}
    >
      <div
        className="relative aspect-[3/4] overflow-hidden bg-black"
        style={{ transition: 'transform .3s ease, box-shadow .3s ease', transform: hovered ? 'scale(1.03)' : 'scale(1)', boxShadow: hovered ? '0 12px 32px rgba(0,0,0,.6)' : '0 2px 8px rgba(0,0,0,.3)' }}
      >
        {/* Thumbnail always present */}
        <SafeImage
          src={mediaUrl(story.thumbnail_url)}
          alt={story.title}
          aspectRatio="3/4"
          fallbackType="gradient"
          titleOverlay={story.title}
          className="w-full h-full"
          imgClassName="w-full h-full object-cover"
        />

        {/* Video overlay on hover */}
        {videoSrc && (
          <video
            ref={videoRef}
            src={videoSrc}
            muted
            loop
            playsInline
            preload="none"
            className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-500 ${hovered ? 'opacity-100' : 'opacity-0'}`}
          />
        )}

        {/* Dark gradient from bottom */}
        <div className="absolute inset-0 bg-gradient-to-t from-black via-black/40 to-transparent pointer-events-none" />

        {/* Badge */}
        <div className="absolute top-2 left-2">
          <span className={`${badge.color} text-[9px] font-black tracking-wider px-2 py-0.5 rounded`}>
            {badge.text}
          </span>
        </div>

        {/* Play button on hover */}
        <div className={`absolute inset-0 flex items-center justify-center transition-opacity duration-200 ${hovered ? 'opacity-100' : 'opacity-0'} pointer-events-none`}>
          <div className="w-11 h-11 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center border border-white/20">
            <Play className="w-4 h-4 text-white fill-white ml-0.5" />
          </div>
        </div>

        {/* Bottom content */}
        <div className="absolute bottom-0 left-0 right-0 p-2.5">
          <h3 className="text-[11px] font-bold text-white leading-tight mb-0.5 line-clamp-1">{story.title || 'Untitled'}</h3>
          <p className="text-[9px] text-white/60 leading-snug line-clamp-2 italic mb-1.5">"{hook}"</p>
          <div className={`flex items-center gap-1 text-[9px] font-bold transition-colors ${hovered ? 'text-white' : 'text-white/40'}`}>
            <Play className="w-2.5 h-2.5 fill-current" />
            Continue <ChevronRight className="w-2.5 h-2.5" />
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══════════ SCROLL ROW — Horizontal with nav arrows ═══════════ */
function ScrollRow({ title, icon: Icon, iconColor, children, seeAllAction, testId }) {
  const scrollRef = useRef(null);
  const [showLeft, setShowLeft] = useState(false);
  const [showRight, setShowRight] = useState(true);

  const checkScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    setShowLeft(el.scrollLeft > 10);
    setShowRight(el.scrollLeft < el.scrollWidth - el.clientWidth - 10);
  }, []);

  const scroll = (dir) => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollBy({ left: dir * el.clientWidth * 0.75, behavior: 'smooth' });
    setTimeout(checkScroll, 400);
  };

  useEffect(() => { checkScroll(); }, [checkScroll, children]);

  return (
    <section className="relative pt-3 pb-0" data-testid={testId}>
      <div className="flex items-center justify-between px-6 sm:px-10 lg:px-14 mb-2">
        <h2 className="flex items-center gap-2 text-sm sm:text-base font-bold text-white tracking-tight">
          {Icon && <Icon className={`w-4 h-4 ${iconColor || 'text-white/60'}`} />}
          {title}
        </h2>
        {seeAllAction && (
          <button onClick={seeAllAction} className="flex items-center gap-1 text-[11px] text-white/30 hover:text-white/60 font-semibold transition-colors" data-testid={`${testId}-see-all`}>
            See all <ChevronRight className="w-3 h-3" />
          </button>
        )}
      </div>

      <div className="relative group/row">
        {showLeft && (
          <button onClick={() => scroll(-1)}
            className="absolute left-1 top-1/2 -translate-y-1/2 z-10 w-9 h-9 bg-black/80 backdrop-blur rounded-full flex items-center justify-center text-white opacity-0 group-hover/row:opacity-100 transition-opacity border border-white/10"
            data-testid={`${testId}-scroll-left`}>
            <ChevronLeft className="w-4 h-4" />
          </button>
        )}

        <div
          ref={scrollRef}
          onScroll={checkScroll}
          className="flex gap-2.5 overflow-x-auto px-6 sm:px-10 lg:px-14 pb-1 scrollbar-hide"
          style={{ scrollSnapType: 'x mandatory', scrollbarWidth: 'none' }}
        >
          {children}
        </div>

        {showRight && (
          <button onClick={() => scroll(1)}
            className="absolute right-1 top-1/2 -translate-y-1/2 z-10 w-9 h-9 bg-black/80 backdrop-blur rounded-full flex items-center justify-center text-white opacity-0 group-hover/row:opacity-100 transition-opacity border border-white/10"
            data-testid={`${testId}-scroll-right`}>
            <ChevronRight className="w-4 h-4" />
          </button>
        )}

        <div className="absolute top-0 left-0 bottom-0 w-10 bg-gradient-to-r from-[#0a0a0f] to-transparent pointer-events-none" />
        <div className="absolute top-0 right-0 bottom-0 w-10 bg-gradient-to-l from-[#0a0a0f] to-transparent pointer-events-none" />
      </div>
    </section>
  );
}

/* ═══════════ INLINE CREATE BAR — Compact ═══════════ */
function CreateBar({ navigate }) {
  const [prompt, setPrompt] = useState('');
  const go = () => navigate('/app/story-video-studio', { state: { prefill: prompt || undefined } });

  return (
    <div className="px-6 sm:px-10 lg:px-14 pt-4 pb-2" data-testid="create-bar">
      <div className="max-w-xl">
        <div className="flex items-center gap-2 bg-white/[0.04] border border-white/[0.08] rounded-xl px-3 py-2 focus-within:border-violet-500/40 transition-colors">
          <Search className="w-4 h-4 text-white/25 flex-shrink-0" />
          <input
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && go()}
            placeholder="Type a story idea..."
            className="flex-1 bg-transparent text-white text-xs placeholder-white/25 outline-none"
            data-testid="create-bar-input"
          />
          <button onClick={go}
            className="flex items-center gap-1 px-3 py-1.5 bg-gradient-to-r from-rose-600 to-violet-600 text-white text-[10px] font-bold rounded-lg hover:opacity-90 transition-opacity flex-shrink-0"
            data-testid="create-bar-btn">
            <Sparkles className="w-3 h-3" /> Create
          </button>
        </div>
      </div>
    </div>
  );
}

/* ═══════════ QUICK TOOLS — Inline pills ═══════════ */
function QuickToolsPills({ navigate }) {
  const tools = [
    { name: 'Story Video', icon: Film, path: '/app/story-video-studio', color: 'text-violet-400' },
    { name: 'Reels', icon: Play, path: '/app/reels', color: 'text-rose-400' },
    { name: 'Comic', icon: BookOpen, path: '/app/comic-storybook', color: 'text-cyan-400' },
    { name: 'Bedtime', icon: Star, path: '/app/bedtime-stories', color: 'text-amber-400' },
  ];

  return (
    <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-hide" data-testid="quick-tools">
      {tools.map(t => (
        <button key={t.name} onClick={() => navigate(t.path)}
          className="flex items-center gap-1 px-2.5 py-1 bg-white/[0.03] border border-white/[0.06] rounded-md text-[10px] font-semibold text-white/35 hover:text-white/70 hover:bg-white/[0.06] transition-all flex-shrink-0"
          data-testid={`tool-${t.name.replace(/\s/g, '-').toLowerCase()}`}>
          <t.icon className={`w-2.5 h-2.5 ${t.color}`} />
          {t.name}
        </button>
      ))}
    </div>
  );
}

/* ═══════════ LOADING SKELETON ═══════════ */
function DashboardSkeleton() {
  return (
    <div className="min-h-screen bg-[#0a0a0f]" data-testid="dashboard-skeleton">
      {/* Hero skeleton */}
      <div className="w-full bg-black/50 animate-pulse" style={{ height: '60vh', minHeight: '420px' }}>
        <div className="h-full flex flex-col justify-end p-10 max-w-3xl">
          <div className="w-20 h-4 bg-white/10 rounded mb-3" />
          <div className="w-80 h-10 bg-white/10 rounded mb-2" />
          <div className="w-64 h-5 bg-white/5 rounded mb-5" />
          <div className="flex gap-3">
            <div className="w-36 h-10 bg-white/10 rounded-lg" />
            <div className="w-28 h-10 bg-white/5 rounded-lg" />
          </div>
        </div>
      </div>
      {/* Row skeletons */}
      {[1, 2].map(r => (
        <div key={r} className="px-10 pt-5">
          <div className="w-32 h-5 bg-white/10 rounded mb-3" />
          <div className="flex gap-3">
            {[1, 2, 3, 4, 5].map(c => (
              <div key={c} className="w-56 aspect-[3/4] bg-white/5 rounded-xl animate-pulse flex-shrink-0" />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   MAIN DASHBOARD
   ═══════════════════════════════════════════════════════ */
export default function Dashboard() {
  const navigate = useNavigate();
  const { credits, creditsLoaded, refreshCredits } = useCredits();
  const [feed, setFeed] = useState({ hero: null, trending: [], characters: [], live_stats: {} });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    refreshCredits();
    const load = async () => {
      try {
        const res = await axios.get(`${API}/api/engagement/story-feed`, auth());
        setFeed(res.data);
      } catch (e) {
        console.error('Feed load failed', e);
      }
      setLoading(false);
    };
    load();
  }, []);

  if (loading) return <DashboardSkeleton />;

  const { trending, hero, live_stats } = feed;

  // Hero candidates: stories with thumbnails (prefer ones with video)
  const heroPool = [hero, ...trending.filter(s => s.job_id !== hero?.job_id)]
    .filter(Boolean)
    .filter(s => s.thumbnail_url);

  // Row 1 — Trending Now: top stories by engagement (first 8)
  const trendingStories = trending.filter(s => s.thumbnail_url).slice(0, 8);

  // Row 2 — Fresh Stories: sort by created_at desc (different order than trending)
  const freshStories = [...trending]
    .filter(s => s.thumbnail_url)
    .sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))
    .slice(0, 8);

  // Row 3 — Watch Now: stories with actual video output
  const watchableStories = trending
    .filter(s => s.thumbnail_url && s.output_url)
    .slice(0, 8);

  const hasContent = heroPool.length > 0 || trendingStories.length > 0;
  const isLoggedIn = !!localStorage.getItem('token');

  return (
    <div className="min-h-screen bg-[#0a0a0f]" data-testid="dashboard">
      {/* Hero */}
      {heroPool.length > 0 && <HeroSection stories={heroPool} navigate={navigate} />}

      {/* Trending Now — immediately after hero, no gap */}
      {trendingStories.length > 0 && (
        <ScrollRow
          title="Trending Now"
          icon={Flame}
          iconColor="text-amber-400"
          seeAllAction={() => navigate('/app/explore')}
          testId="trending-now"
        >
          {trendingStories.map((story, idx) => (
            <StoryCard key={story.job_id} story={story} idx={idx} navigate={navigate} size="lg" />
          ))}
        </ScrollRow>
      )}

      {/* Fresh Stories */}
      {freshStories.length > 0 && (
        <ScrollRow
          title="Fresh Stories"
          icon={Sparkles}
          iconColor="text-violet-400"
          testId="fresh-stories"
        >
          {freshStories.map((story, idx) => (
            <StoryCard key={`fresh-${story.job_id}`} story={story} idx={idx + 20} navigate={navigate} size="md" />
          ))}
        </ScrollRow>
      )}

      {/* Watch Now — stories with video */}
      {watchableStories.length > 0 && (
        <ScrollRow
          title="Watch Now"
          icon={Play}
          iconColor="text-emerald-400"
          testId="watch-now"
        >
          {watchableStories.map((story, idx) => (
            <StoryCard key={`watch-${story.job_id}`} story={story} idx={idx + 40} navigate={navigate} size="md" />
          ))}
        </ScrollRow>
      )}

      {/* Create bar + credits + tools — compact footer section */}
      <div className="mt-2 border-t border-white/[0.04]">
        <CreateBar navigate={navigate} />
        <div className="flex items-center justify-between px-6 sm:px-10 lg:px-14 py-1.5">
          <div className="flex items-center gap-4 text-[11px] text-white/25">
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              {live_stats.total_stories || 0} stories
            </span>
            <span className="flex items-center gap-1.5" data-testid="credits-display">
              <Zap className="w-3 h-3 text-violet-400" />
              {!isLoggedIn ? (
                <button onClick={() => navigate('/login')} className="flex items-center gap-1 text-violet-400 hover:text-violet-300 font-semibold" data-testid="credits-login-cta">
                  <LogIn className="w-3 h-3" /> Sign in to create
                </button>
              ) : !creditsLoaded ? (
                <span className="inline-block w-10 h-3 bg-white/10 rounded animate-pulse" data-testid="credits-skeleton" />
              ) : (
                <span className="text-white/40 font-medium" data-testid="credits-value">
                  {credits >= 999999 ? 'Unlimited' : `${credits}`} credits
                </span>
              )}
            </span>
          </div>
          <QuickToolsPills navigate={navigate} />
        </div>
      </div>

      {/* Empty state — only if truly no content */}
      {!hasContent && (
        <div className="flex flex-col items-center justify-center py-16 px-6 text-center" data-testid="empty-state">
          <Film className="w-12 h-12 text-white/10 mb-4" />
          <h2 className="text-lg font-bold text-white/50 mb-2">No stories yet</h2>
          <p className="text-sm text-white/30 mb-6 max-w-md">Create your first AI story video and watch the feed come alive.</p>
          <button onClick={() => navigate('/app/story-video-studio')}
            className="px-6 py-2.5 bg-gradient-to-r from-rose-600 to-violet-600 text-white text-sm font-bold rounded-lg hover:opacity-90 transition-opacity"
            data-testid="empty-create-btn">
            <Sparkles className="w-4 h-4 inline mr-1.5" /> Create Your First Story
          </button>
        </div>
      )}

      {/* Scrollbar hide */}
      <style>{`.scrollbar-hide::-webkit-scrollbar{display:none}.scrollbar-hide{-ms-overflow-style:none;scrollbar-width:none}`}</style>
    </div>
  );
}
