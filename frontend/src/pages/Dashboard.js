import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCredits } from '../contexts/CreditContext';
import axios from 'axios';
import { SafeImage } from '../components/SafeImage';
import {
  Play, ChevronRight, ChevronLeft, Sparkles, Zap,
  Flame, Clock, LogIn, Search, Plus, Volume2, VolumeX,
  Film, BookOpen, Star, ArrowRight
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
];

// Seed cards shown when no real data exists — these are CTAs, not fake data
const SEED_CARDS = [
  { job_id: 'seed-1', title: 'A Midnight Train to Nowhere', hook_text: "The station was empty... except for the girl with no shadow.", is_seed: true },
  { job_id: 'seed-2', title: 'The Last Dragon\'s Secret', hook_text: "She found the egg under the floorboards. It was warm.", is_seed: true },
  { job_id: 'seed-3', title: 'Echoes in the Library', hook_text: "The book opened itself to page 47. It was blank yesterday.", is_seed: true },
  { job_id: 'seed-4', title: 'The Clockmaker\'s Daughter', hook_text: "Every clock in town stopped at 3:33 AM.", is_seed: true },
  { job_id: 'seed-5', title: 'Whispers Under the Ice', hook_text: "Something was moving beneath the frozen lake.", is_seed: true },
  { job_id: 'seed-6', title: 'The Map That Bleeds', hook_text: "The old map showed a country that doesn't exist.", is_seed: true },
];

function getHook(story, idx) {
  if (story.hook_text && story.hook_text.length > 15) return story.hook_text;
  if (story.story_text) {
    const sentences = story.story_text.split(/[.!?]+/).filter(s => s.trim().length > 10);
    if (sentences.length > 0) return sentences[0].trim() + '...';
  }
  return HOOK_BANK[idx % HOOK_BANK.length];
}

function getBadge(story, idx) {
  if (story.is_seed) return { text: 'CREATE', color: 'bg-violet-500 text-white' };
  const rm = story.remix_count || 0;
  if (rm >= 5) return { text: 'TRENDING', color: 'bg-amber-500 text-black' };
  if (idx === 0) return { text: '#1', color: 'bg-rose-500 text-white' };
  if (idx < 3) return { text: 'HOT', color: 'bg-rose-500/80 text-white' };
  return { text: 'NEW', color: 'bg-white/15 text-white' };
}

const GRAD_COLORS = [
  'from-violet-600 to-indigo-900',
  'from-rose-600 to-purple-900',
  'from-emerald-600 to-teal-900',
  'from-cyan-600 to-blue-900',
  'from-amber-600 to-orange-900',
  'from-pink-600 to-fuchsia-900',
];

/* ═══════════ HERO SECTION — Always renders ═══════════ */
function HeroSection({ stories, navigate }) {
  const [activeIdx, setActiveIdx] = useState(0);
  const [isMuted, setIsMuted] = useState(true);
  const [videoFailed, setVideoFailed] = useState(false);
  const videoRef = useRef(null);
  const timerRef = useRef(null);

  const heroStories = stories.length > 0 ? stories.slice(0, 5) : [];
  const current = heroStories[activeIdx] || {};
  const videoSrc = mediaUrl(current.preview_url || current.output_url);
  const posterSrc = mediaUrl(current.thumbnail_url);
  const canShowVideo = videoSrc && !videoFailed;
  const hasHero = heroStories.length > 0;

  useEffect(() => {
    if (heroStories.length <= 1) return;
    timerRef.current = setInterval(() => {
      setActiveIdx(prev => (prev + 1) % heroStories.length);
    }, 10000);
    return () => clearInterval(timerRef.current);
  }, [heroStories.length]);

  useEffect(() => {
    setVideoFailed(false);
    if (videoRef.current) {
      videoRef.current.load();
      videoRef.current.play().catch(() => {});
    }
  }, [activeIdx]);

  const goTo = (idx) => {
    clearInterval(timerRef.current);
    setActiveIdx(idx);
    if (heroStories.length > 1) {
      timerRef.current = setInterval(() => {
        setActiveIdx(prev => (prev + 1) % heroStories.length);
      }, 10000);
    }
  };

  const hash = (current.title || 'story').split('').reduce((a, c) => a + c.charCodeAt(0), 0);
  const fallbackGrad = GRAD_COLORS[hash % GRAD_COLORS.length];

  return (
    <section className="relative w-full" style={{ height: '48vh', minHeight: '340px' }} data-testid="hero-section">
      {/* Background layers: gradient → image → video */}
      <div className="absolute inset-0 overflow-hidden bg-black">
        <div className={`absolute inset-0 bg-gradient-to-br ${fallbackGrad}`} />
        {posterSrc && (
          <img src={posterSrc} alt="" className="absolute inset-0 w-full h-full object-cover" style={{ filter: 'brightness(0.7) saturate(1.2)' }} data-testid="hero-poster" />
        )}
        {canShowVideo && (
          <video ref={videoRef} key={`hero-${current.job_id}`} src={videoSrc} muted={isMuted} autoPlay loop playsInline
            className="absolute inset-0 w-full h-full object-cover"
            style={{ filter: 'brightness(0.7) saturate(1.2)' }}
            data-testid="hero-video" onError={() => setVideoFailed(true)} />
        )}
      </div>

      {/* Gradient overlays */}
      <div className="absolute inset-0 bg-gradient-to-r from-black/60 via-black/20 to-transparent" />
      <div className="absolute inset-0 bg-gradient-to-t from-[#0a0a0f] via-transparent to-transparent" />

      {/* Content */}
      <div className="relative h-full flex flex-col justify-end px-6 sm:px-10 lg:px-14 pb-8 max-w-3xl z-10" style={{ animation: 'fadeUp .5s ease-out' }}>
        {hasHero ? (
          <>
            <div className="flex items-center gap-2 mb-2">
              <span className="bg-rose-600 text-white text-[10px] font-black tracking-widest px-2.5 py-0.5 rounded" data-testid="hero-featured-badge">FEATURED</span>
              {current.animation_style && (
                <span className="bg-white/10 backdrop-blur text-white/60 text-[10px] font-bold px-2 py-0.5 rounded">{current.animation_style.replace(/_/g, ' ').toUpperCase()}</span>
              )}
              {canShowVideo && (
                <span className="flex items-center gap-1 bg-red-600/80 text-white text-[9px] font-black px-2 py-0.5 rounded">
                  <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" /> LIVE
                </span>
              )}
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black text-white leading-[1.1] mb-2 drop-shadow-2xl" data-testid="hero-title">
              {current.title || 'Untitled Story'}
            </h1>
            <p className="text-sm sm:text-base text-white/70 leading-relaxed mb-5 max-w-xl line-clamp-2 italic" data-testid="hero-hook">
              "{getHook(current, activeIdx)}"
            </p>
            <div className="flex items-center gap-2.5">
              <button onClick={() => navigate('/app/story-video-studio', { state: { continueJob: current.job_id } })}
                className="flex items-center gap-2 px-5 py-2.5 bg-white text-black font-bold rounded-lg text-sm hover:scale-[1.03] active:scale-[0.97] transition-transform shadow-xl shadow-white/10" data-testid="hero-play-btn">
                <Play className="w-4 h-4 fill-black" /> Watch & Continue
              </button>
              <button onClick={() => navigate('/app/story-video-studio')}
                className="flex items-center gap-2 px-5 py-2.5 bg-white/10 backdrop-blur text-white font-bold rounded-lg text-sm hover:bg-white/20 transition-colors border border-white/10" data-testid="hero-create-btn">
                <Plus className="w-4 h-4" /> Create New
              </button>
              {canShowVideo && (
                <button onClick={() => setIsMuted(!isMuted)} className="w-9 h-9 flex items-center justify-center rounded-full bg-black/40 backdrop-blur border border-white/10 text-white/60 hover:text-white hover:bg-black/60 transition-all" data-testid="hero-mute-btn">
                  {isMuted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
                </button>
              )}
            </div>
          </>
        ) : (
          /* Fallback hero when NO stories exist at all */
          <>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black text-white leading-[1.1] mb-2 drop-shadow-2xl" data-testid="hero-title">
              Your Story Universe Awaits
            </h1>
            <p className="text-sm sm:text-base text-white/70 leading-relaxed mb-5 max-w-xl">
              Create AI-powered story videos, comics, and more. Type an idea and watch it come to life.
            </p>
            <button onClick={() => navigate('/app/story-video-studio')}
              className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-rose-600 to-violet-600 text-white font-bold rounded-lg text-sm hover:scale-[1.03] active:scale-[0.97] transition-transform shadow-xl shadow-violet-600/20" data-testid="hero-create-btn">
              <Sparkles className="w-4 h-4" /> Create Your First Story
            </button>
          </>
        )}
      </div>

      {/* Carousel dots */}
      {heroStories.length > 1 && (
        <div className="absolute bottom-4 right-6 sm:right-10 flex items-center gap-1 z-10" data-testid="hero-dots">
          {heroStories.map((_, i) => (
            <button key={i} onClick={() => goTo(i)}
              className={`h-[3px] rounded-full transition-all duration-500 ${i === activeIdx ? 'w-8 bg-white' : 'w-3 bg-white/25 hover:bg-white/40'}`}
              data-testid={`hero-dot-${i}`} />
          ))}
        </div>
      )}

      <style>{`@keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}`}</style>
    </section>
  );
}

/* ═══════════ STORY CARD ═══════════ */
function StoryCard({ story, idx, navigate, size = 'md' }) {
  const [hovered, setHovered] = useState(false);
  const videoRef = useRef(null);
  const hook = getHook(story, idx);
  const badge = getBadge(story, idx);
  const videoSrc = mediaUrl(story.preview_url || story.output_url);
  const isSeed = story.is_seed;
  const gradIdx = (story.title || '').split('').reduce((a, c) => a + c.charCodeAt(0), 0) % GRAD_COLORS.length;

  useEffect(() => {
    if (!videoSrc || isSeed) return;
    if (hovered && videoRef.current) {
      videoRef.current.play().catch(() => {});
    } else if (!hovered && videoRef.current) {
      videoRef.current.pause();
      videoRef.current.currentTime = 0;
    }
  }, [hovered, videoSrc, isSeed]);

  const sizes = { sm: 'w-40 sm:w-48', md: 'w-48 sm:w-56 lg:w-60', lg: 'w-56 sm:w-64 lg:w-72' };

  const handleClick = () => {
    if (isSeed) {
      navigate('/app/story-video-studio', { state: { prefill: story.title } });
    } else {
      navigate('/app/story-video-studio', { state: { continueJob: story.job_id } });
    }
  };

  return (
    <div className={`${sizes[size]} flex-shrink-0 group relative rounded-xl overflow-hidden cursor-pointer`}
      style={{ scrollSnapAlign: 'start' }}
      onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)}
      onClick={handleClick} data-testid={`story-card-${idx}`}>
      <div className="relative aspect-[3/4] overflow-hidden bg-black"
        style={{ transition: 'transform .3s ease, box-shadow .3s ease', transform: hovered ? 'scale(1.03)' : 'scale(1)', boxShadow: hovered ? '0 12px 32px rgba(0,0,0,.6)' : '0 2px 8px rgba(0,0,0,.3)' }}>

        {/* Background: real thumbnail OR gradient for seed/no-thumb stories */}
        {story.thumbnail_url ? (
          <SafeImage src={mediaUrl(story.thumbnail_url)} alt={story.title} aspectRatio="3/4" fallbackType="gradient" titleOverlay={story.title}
            className="w-full h-full" imgClassName="w-full h-full object-cover" />
        ) : (
          <div className={`absolute inset-0 bg-gradient-to-br ${GRAD_COLORS[gradIdx]}`}>
            <div className="absolute inset-0 flex items-center justify-center p-4">
              {isSeed ? (
                <Sparkles className="w-10 h-10 text-white/20" />
              ) : (
                <Film className="w-10 h-10 text-white/20" />
              )}
            </div>
          </div>
        )}

        {/* Video hover overlay */}
        {videoSrc && !isSeed && (
          <video ref={videoRef} src={videoSrc} muted loop playsInline preload="none"
            className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-500 ${hovered ? 'opacity-100' : 'opacity-0'}`} />
        )}

        {/* Dark gradient from bottom */}
        <div className="absolute inset-0 bg-gradient-to-t from-black via-black/40 to-transparent pointer-events-none" />

        {/* Badge */}
        <div className="absolute top-2 left-2">
          <span className={`${badge.color} text-[9px] font-black tracking-wider px-2 py-0.5 rounded`}>{badge.text}</span>
        </div>

        {/* Play button on hover */}
        <div className={`absolute inset-0 flex items-center justify-center transition-opacity duration-200 ${hovered ? 'opacity-100' : 'opacity-0'} pointer-events-none`}>
          <div className="w-11 h-11 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center border border-white/20">
            {isSeed ? <Plus className="w-4 h-4 text-white" /> : <Play className="w-4 h-4 text-white fill-white ml-0.5" />}
          </div>
        </div>

        {/* Bottom text */}
        <div className="absolute bottom-0 left-0 right-0 p-2.5">
          <h3 className="text-[11px] font-bold text-white leading-tight mb-0.5 line-clamp-1">{story.title || 'Untitled'}</h3>
          <p className="text-[9px] text-white/60 leading-snug line-clamp-2 italic mb-1.5">"{hook}"</p>
          <div className={`flex items-center gap-1 text-[9px] font-bold transition-colors ${hovered ? 'text-white' : 'text-white/40'}`}>
            {isSeed ? <><Plus className="w-2.5 h-2.5" /> Create</> : <><Play className="w-2.5 h-2.5 fill-current" /> Continue</>}
            <ChevronRight className="w-2.5 h-2.5" />
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══════════ SCROLL ROW ═══════════ */
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
          <button onClick={() => scroll(-1)} className="absolute left-1 top-1/2 -translate-y-1/2 z-10 w-9 h-9 bg-black/80 backdrop-blur rounded-full flex items-center justify-center text-white opacity-0 group-hover/row:opacity-100 transition-opacity border border-white/10" data-testid={`${testId}-scroll-left`}>
            <ChevronLeft className="w-4 h-4" />
          </button>
        )}
        <div ref={scrollRef} onScroll={checkScroll}
          className="flex gap-2.5 overflow-x-auto px-6 sm:px-10 lg:px-14 pb-1 scrollbar-hide"
          style={{ scrollSnapType: 'x mandatory', scrollbarWidth: 'none' }}>
          {children}
        </div>
        {showRight && (
          <button onClick={() => scroll(1)} className="absolute right-1 top-1/2 -translate-y-1/2 z-10 w-9 h-9 bg-black/80 backdrop-blur rounded-full flex items-center justify-center text-white opacity-0 group-hover/row:opacity-100 transition-opacity border border-white/10" data-testid={`${testId}-scroll-right`}>
            <ChevronRight className="w-4 h-4" />
          </button>
        )}
        <div className="absolute top-0 left-0 bottom-0 w-10 bg-gradient-to-r from-[#0a0a0f] to-transparent pointer-events-none" />
        <div className="absolute top-0 right-0 bottom-0 w-10 bg-gradient-to-l from-[#0a0a0f] to-transparent pointer-events-none" />
      </div>
    </section>
  );
}

/* ═══════════ QUICK TOOLS ═══════════ */
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
          <t.icon className={`w-2.5 h-2.5 ${t.color}`} /> {t.name}
        </button>
      ))}
    </div>
  );
}

/* ═══════════ CREATE BAR ═══════════ */
function CreateBar({ navigate }) {
  const [prompt, setPrompt] = useState('');
  const go = () => navigate('/app/story-video-studio', { state: { prefill: prompt || undefined } });
  return (
    <div className="px-6 sm:px-10 lg:px-14 pt-4 pb-2" data-testid="create-bar">
      <div className="max-w-xl">
        <div className="flex items-center gap-2 bg-white/[0.04] border border-white/[0.08] rounded-xl px-3 py-2 focus-within:border-violet-500/40 transition-colors">
          <Search className="w-4 h-4 text-white/25 flex-shrink-0" />
          <input value={prompt} onChange={e => setPrompt(e.target.value)} onKeyDown={e => e.key === 'Enter' && go()}
            placeholder="Type a story idea..." className="flex-1 bg-transparent text-white text-xs placeholder-white/25 outline-none" data-testid="create-bar-input" />
          <button onClick={go}
            className="flex items-center gap-1 px-3 py-1.5 bg-gradient-to-r from-rose-600 to-violet-600 text-white text-[10px] font-bold rounded-lg hover:opacity-90 transition-opacity flex-shrink-0" data-testid="create-bar-btn">
            <Sparkles className="w-3 h-3" /> Create
          </button>
        </div>
      </div>
    </div>
  );
}

/* ═══════════ LOADING SKELETON ═══════════ */
function DashboardSkeleton() {
  return (
    <div className="min-h-screen bg-[#0a0a0f]" data-testid="dashboard-skeleton">
      <div className="w-full bg-gradient-to-br from-slate-900 to-black" style={{ height: '48vh', minHeight: '340px' }}>
        <div className="h-full flex flex-col justify-end p-10 max-w-3xl">
          <div className="w-20 h-4 bg-white/10 rounded mb-3 animate-pulse" />
          <div className="w-72 h-9 bg-white/10 rounded mb-2 animate-pulse" />
          <div className="w-56 h-5 bg-white/5 rounded mb-5 animate-pulse" />
          <div className="flex gap-3">
            <div className="w-36 h-10 bg-white/10 rounded-lg animate-pulse" />
            <div className="w-28 h-10 bg-white/5 rounded-lg animate-pulse" />
          </div>
        </div>
      </div>
      {[1, 2].map(r => (
        <div key={r} className="px-10 pt-4">
          <div className="w-28 h-4 bg-white/10 rounded mb-2 animate-pulse" />
          <div className="flex gap-2.5">
            {[1, 2, 3, 4, 5, 6].map(c => (
              <div key={c} className="w-60 aspect-[3/4] bg-white/[0.03] rounded-xl animate-pulse flex-shrink-0" />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   MAIN DASHBOARD — NEVER shows empty. Always has content.
   ═══════════════════════════════════════════════════════ */
export default function Dashboard() {
  const navigate = useNavigate();
  const { credits, creditsLoaded, refreshCredits } = useCredits();
  const [feed, setFeed] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    refreshCredits();
    const load = async () => {
      try {
        const res = await axios.get(`${API}/api/engagement/story-feed`, auth());
        console.log('[Dashboard] Feed loaded:', { hero: !!res.data.hero, trending: res.data.trending?.length, stats: res.data.live_stats });
        setFeed(res.data);
      } catch (e) {
        console.error('[Dashboard] Feed load FAILED:', e.message);
        setFeed({ hero: null, trending: [], characters: [], live_stats: {} });
      }
      setLoading(false);
    };
    load();
  }, []);

  if (loading) return <DashboardSkeleton />;

  const { trending = [], hero = null, live_stats = {} } = feed || {};
  const isLoggedIn = !!localStorage.getItem('token');

  // Hero pool: real stories, or empty (HeroSection handles empty internally)
  const heroPool = [hero, ...trending.filter(s => s.job_id !== hero?.job_id)].filter(Boolean);

  // Row data: real stories or seed cards. ROWS ALWAYS RENDER.
  const trendingStories = trending.length > 0 ? trending.slice(0, 10) : SEED_CARDS;
  const freshStories = trending.length > 0
    ? [...trending].sort((a, b) => (b.created_at || '').localeCompare(a.created_at || '')).slice(0, 10)
    : SEED_CARDS.slice().reverse();
  const watchableStories = trending.filter(s => s.output_url).slice(0, 10);

  return (
    <div className="min-h-screen bg-[#0a0a0f]" data-testid="dashboard">

      {/* ▸ HERO — ALWAYS renders */}
      <HeroSection stories={heroPool} navigate={navigate} />

      {/* ▸ TRENDING NOW — ALWAYS renders (real stories or seed cards) */}
      <ScrollRow title="Trending Now" icon={Flame} iconColor="text-amber-400"
        seeAllAction={trending.length > 0 ? () => navigate('/app/explore') : undefined} testId="trending-now">
        {trendingStories.map((story, idx) => (
          <StoryCard key={story.job_id} story={story} idx={idx} navigate={navigate} size="lg" />
        ))}
      </ScrollRow>

      {/* ▸ FRESH STORIES — ALWAYS renders (real stories or seed cards) */}
      <ScrollRow title="Fresh Stories" icon={Sparkles} iconColor="text-violet-400" testId="fresh-stories">
        {freshStories.map((story, idx) => (
          <StoryCard key={`fresh-${story.job_id}`} story={story} idx={idx + 20} navigate={navigate} size="md" />
        ))}
      </ScrollRow>

      {/* ▸ WATCH NOW — only if real video stories exist */}
      {watchableStories.length > 0 && (
        <ScrollRow title="Watch Now" icon={Play} iconColor="text-emerald-400" testId="watch-now">
          {watchableStories.map((story, idx) => (
            <StoryCard key={`watch-${story.job_id}`} story={story} idx={idx + 40} navigate={navigate} size="md" />
          ))}
        </ScrollRow>
      )}

      {/* ▸ CREATE BAR + CREDITS + TOOLS — footer section */}
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

      <style>{`.scrollbar-hide::-webkit-scrollbar{display:none}.scrollbar-hide{-ms-overflow-style:none;scrollbar-width:none}`}</style>
    </div>
  );
}
