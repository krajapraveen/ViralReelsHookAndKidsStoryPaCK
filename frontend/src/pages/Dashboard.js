import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useCredits } from '../contexts/CreditContext';
import axios from 'axios';
import { SafeImage } from '../components/SafeImage';
import {
  Play, ChevronRight, ChevronLeft, Sparkles, Zap,
  Flame, Clock, LogIn, Search, Plus, Volume2, VolumeX,
  Film, BookOpen, Star, ArrowRight, Shield, User, Settings
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

function mediaUrl(path) {
  if (!path) return null;
  if (path.startsWith('/api/media/')) return `${API}${path}`;
  return path;
}

/** Decode JWT to check admin role */
function isAdminUser() {
  try {
    const token = localStorage.getItem('token');
    if (!token) return false;
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.role?.toUpperCase() === 'ADMIN' || payload.role?.toUpperCase() === 'SUPERADMIN';
  } catch { return false; }
}

/** Preload images in parallel using Image() workers for fast rendering */
function preloadImages(urls) {
  if (!urls || urls.length === 0) return;
  const batch = urls.slice(0, 16); // Preload first 16 images (hero + 3 rows x 5 visible)
  // Use staggered loading: first 6 immediately, rest after 200ms
  const immediate = batch.slice(0, 6);
  const deferred = batch.slice(6);

  immediate.forEach(url => {
    if (!url) return;
    const img = new Image();
    img.src = url;
  });

  if (deferred.length > 0) {
    setTimeout(() => {
      deferred.forEach(url => {
        if (!url) return;
        const img = new Image();
        img.src = url;
      });
    }, 200);
  }
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

// Seed cards shown when no real data exists — these feel like unfinished stories, not creation prompts
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
  if (story.is_seed) return { text: 'UNFINISHED', color: 'bg-amber-500/90 text-black' };
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
          <img src={posterSrc} alt="" loading="eager" fetchPriority="high" decoding="sync"
            className="absolute inset-0 w-full h-full object-cover" style={{ filter: 'brightness(0.7) saturate(1.2)' }} data-testid="hero-poster" />
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
            <div className="flex items-center gap-2 mb-3">
              <span className="bg-rose-600 text-white text-[11px] font-black tracking-widest px-3 py-1 rounded-md shadow-lg shadow-rose-600/30" data-testid="hero-featured-badge">FEATURED</span>
              {current.animation_style && (
                <span className="bg-white/15 backdrop-blur text-white/80 text-[10px] font-bold px-2.5 py-1 rounded-md">{current.animation_style.replace(/_/g, ' ').toUpperCase()}</span>
              )}
              {canShowVideo && (
                <span className="flex items-center gap-1 bg-red-600 text-white text-[10px] font-black px-2.5 py-1 rounded-md shadow-lg shadow-red-600/30">
                  <span className="w-2 h-2 rounded-full bg-white animate-pulse" /> LIVE
                </span>
              )}
            </div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black text-white leading-[1.05] mb-3 drop-shadow-2xl" data-testid="hero-title">
              {current.title || 'Untitled Story'}
            </h1>
            <p className="text-base sm:text-lg text-white/75 leading-relaxed mb-6 max-w-xl line-clamp-2 italic" data-testid="hero-hook">
              "{getHook(current, activeIdx)}"
            </p>
            <div className="flex items-center gap-3">
              <button onClick={() => navigate('/app/story-video-studio', { state: { prefill: current.title, freshSession: true } })}
                className="flex items-center gap-2 px-6 py-3 bg-white text-black font-extrabold rounded-lg text-sm hover:scale-[1.03] active:scale-[0.97] transition-transform shadow-xl shadow-white/15" data-testid="hero-play-btn">
                <Play className="w-5 h-5 fill-black" /> Watch & Continue
              </button>
              <button onClick={() => navigate('/app/story-video-studio', { state: { freshSession: true } })}
                className="flex items-center gap-2 px-6 py-3 bg-white/15 backdrop-blur text-white font-extrabold rounded-lg text-sm hover:bg-white/25 transition-colors border border-white/15" data-testid="hero-create-btn">
                <Plus className="w-5 h-5" /> Create New
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
            <div className="flex items-center gap-2 mb-2">
              <span className="bg-amber-500 text-black text-[10px] font-black tracking-widest px-2.5 py-0.5 rounded">UNFINISHED</span>
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black text-white leading-[1.1] mb-2 drop-shadow-2xl" data-testid="hero-title">
              Every Story is Waiting for You
            </h1>
            <p className="text-sm sm:text-base text-white/70 leading-relaxed mb-5 max-w-xl">
              Worlds half-built. Characters mid-sentence. Pick any story below and decide what happens next.
            </p>
            <button onClick={() => navigate('/app/story-video-studio', { state: { freshSession: true } })}
              className="flex items-center gap-2 px-6 py-3 bg-white text-black font-bold rounded-lg text-sm hover:scale-[1.03] active:scale-[0.97] transition-transform shadow-xl shadow-white/10" data-testid="hero-create-btn">
              <Play className="w-4 h-4 fill-black" /> Continue a Story
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
function StoryCard({ story, idx, navigate, size = 'md', priority = false }) {
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

  const sizes = { sm: 'w-44 sm:w-52', md: 'w-52 sm:w-60 lg:w-64', lg: 'w-60 sm:w-72 lg:w-80' };

  const handleClick = () => {
    if (isSeed) {
      navigate('/app/story-video-studio', { state: { prefill: story.title, freshSession: true } });
    } else {
      navigate('/app/story-video-studio', { state: { prefill: story.title, freshSession: true } });
    }
  };

  return (
    <div className={`${sizes[size]} flex-shrink-0 group relative rounded-xl overflow-hidden cursor-pointer`}
      style={{ scrollSnapAlign: 'start' }}
      onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)}
      onClick={handleClick} data-testid={`story-card-${idx}`}>
      <div className="relative aspect-[3/4] overflow-hidden bg-black rounded-xl"
        style={{ transition: 'transform .3s ease, box-shadow .3s ease', transform: hovered ? 'scale(1.03)' : 'scale(1)', boxShadow: hovered ? '0 16px 40px rgba(0,0,0,.7)' : '0 4px 12px rgba(0,0,0,.4)' }}>

        {/* Background: thumbnail via SafeImage with priority loading */}
        {story.thumbnail_url ? (
          <SafeImage src={mediaUrl(story.thumbnail_url)} alt={story.title} aspectRatio="3/4" fallbackType="gradient" titleOverlay={story.title}
            priority={priority} className="w-full h-full" imgClassName="w-full h-full object-cover" />
        ) : (
          <div className={`absolute inset-0 bg-gradient-to-br ${GRAD_COLORS[gradIdx]}`}>
            <div className="absolute inset-0 flex items-center justify-center p-4">
              {isSeed ? (
                <Sparkles className="w-12 h-12 text-white/25" />
              ) : (
                <Film className="w-12 h-12 text-white/25" />
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
        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent pointer-events-none" />

        {/* Badge — BIGGER + BRIGHTER */}
        <div className="absolute top-2.5 left-2.5">
          <span className={`${badge.color} text-[10px] font-black tracking-wider px-2.5 py-1 rounded-md shadow-lg`}>{badge.text}</span>
        </div>

        {/* Play button on hover */}
        <div className={`absolute inset-0 flex items-center justify-center transition-opacity duration-200 ${hovered ? 'opacity-100' : 'opacity-0'} pointer-events-none`}>
          <div className="w-14 h-14 rounded-full bg-white/25 backdrop-blur-md flex items-center justify-center border border-white/30 shadow-2xl">
            <Play className="w-5 h-5 text-white fill-white ml-0.5" />
          </div>
        </div>

        {/* Bottom text — BIGGER + BOLDER */}
        <div className="absolute bottom-0 left-0 right-0 p-3">
          <h3 className="text-sm font-extrabold text-white leading-tight mb-1 line-clamp-1 drop-shadow-lg">{story.title || 'Untitled'}</h3>
          <p className="text-[10px] text-white/70 leading-snug line-clamp-2 italic mb-2">"{hook}"</p>
          <div className={`flex items-center gap-1.5 text-[10px] font-bold transition-colors ${hovered ? 'text-white' : 'text-white/50'}`}>
            {isSeed ? <><Play className="w-3 h-3 fill-current" /> Continue this</> : <><Play className="w-3 h-3 fill-current" /> See what happens</>}
            <ChevronRight className="w-3 h-3" />
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
    <section className="relative pt-4 pb-1" data-testid={testId}>
      <div className="flex items-center justify-between px-6 sm:px-10 lg:px-14 mb-3">
        <h2 className="flex items-center gap-2 text-base sm:text-lg font-extrabold text-white tracking-tight">
          {Icon && <Icon className={`w-5 h-5 ${iconColor || 'text-white/60'}`} />}
          {title}
        </h2>
        {seeAllAction && (
          <button onClick={seeAllAction} className="flex items-center gap-1 text-xs text-white/40 hover:text-white/70 font-bold transition-colors" data-testid={`${testId}-see-all`}>
            See all <ChevronRight className="w-3.5 h-3.5" />
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

/* ═══════════ FEATURES GRID — 10 bold tools ═══════════ */
function FeaturesGrid({ navigate }) {
  const features = [
    { name: 'Story Series', desc: 'Multi-episode sagas', icon: Film, path: '/app/story-series', color: 'from-violet-600 to-purple-700', iconBg: 'bg-violet-500/20' },
    { name: 'Character Memory', desc: 'Persistent characters', icon: User, path: '/app/characters', color: 'from-cyan-600 to-blue-700', iconBg: 'bg-cyan-500/20' },
    { name: 'Reel Generator', desc: 'Viral short reels', icon: Play, path: '/app/reels', color: 'from-rose-600 to-pink-700', iconBg: 'bg-rose-500/20' },
    { name: 'Photo to Comic', desc: 'Photos become comics', icon: Sparkles, path: '/app/photo-to-comic', color: 'from-amber-600 to-orange-700', iconBg: 'bg-amber-500/20' },
    { name: 'Comic Storybook', desc: 'Panel-by-panel stories', icon: BookOpen, path: '/app/comic-storybook', color: 'from-emerald-600 to-green-700', iconBg: 'bg-emerald-500/20' },
    { name: 'Bedtime Stories', desc: 'Narrated sleep tales', icon: Star, path: '/app/bedtime-stories', color: 'from-indigo-600 to-blue-700', iconBg: 'bg-indigo-500/20' },
    { name: 'Reaction GIF', desc: 'Custom reaction GIFs', icon: Zap, path: '/app/reaction-gif', color: 'from-yellow-500 to-amber-600', iconBg: 'bg-yellow-500/20' },
    { name: 'Caption Rewriter', desc: 'AI-powered captions', icon: ArrowRight, path: '/app/caption-rewriter', color: 'from-teal-600 to-cyan-700', iconBg: 'bg-teal-500/20' },
    { name: 'Brand Story', desc: 'Business storytelling', icon: Shield, path: '/app/brand-story', color: 'from-slate-600 to-gray-700', iconBg: 'bg-slate-500/20' },
    { name: 'Daily Viral Ideas', desc: 'Trending content ideas', icon: Flame, path: '/app/daily-viral', color: 'from-red-600 to-rose-700', iconBg: 'bg-red-500/20' },
  ];

  return (
    <section className="px-6 sm:px-10 lg:px-14 py-6" data-testid="features-grid">
      <h2 className="flex items-center gap-2.5 text-lg sm:text-xl font-extrabold text-white tracking-tight mb-5">
        <Zap className="w-5 h-5 text-amber-400" />
        Creator Tools
      </h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
        {features.map(f => {
          const Icon = f.icon;
          return (
            <button
              key={f.name}
              onClick={() => navigate(f.path, { state: { freshSession: true } })}
              className="group relative overflow-hidden rounded-xl border border-white/[0.08] bg-white/[0.03] hover:bg-white/[0.08] hover:border-white/15 transition-all p-4 text-left cursor-pointer"
              data-testid={`feature-${f.name.replace(/\s/g, '-').toLowerCase()}`}
            >
              <div className={`w-10 h-10 rounded-lg ${f.iconBg} flex items-center justify-center mb-3 group-hover:scale-110 transition-transform`}>
                <Icon className="w-5 h-5 text-white" />
              </div>
              <h3 className="text-sm font-bold text-white leading-tight mb-0.5">{f.name}</h3>
              <p className="text-[10px] text-white/40 leading-tight">{f.desc}</p>
              <div className={`absolute inset-0 bg-gradient-to-br ${f.color} opacity-0 group-hover:opacity-[0.08] transition-opacity pointer-events-none`} />
            </button>
          );
        })}
      </div>
    </section>
  );
}

/* ═══════════ CREATE BAR ═══════════ */
function CreateBar({ navigate }) {
  const [prompt, setPrompt] = useState('');
  const go = () => navigate('/app/story-video-studio', { state: { prefill: prompt || undefined, freshSession: true } });
  return (
    <div className="px-6 sm:px-10 lg:px-14 pt-5 pb-2" data-testid="create-bar">
      <div className="max-w-2xl">
        <div className="flex items-center gap-3 bg-white/[0.05] border border-white/[0.10] rounded-xl px-4 py-3 focus-within:border-violet-500/50 focus-within:bg-white/[0.07] transition-all shadow-lg shadow-black/20">
          <Search className="w-4 h-4 text-white/30 flex-shrink-0" />
          <input value={prompt} onChange={e => setPrompt(e.target.value)} onKeyDown={e => e.key === 'Enter' && go()}
            placeholder="What happens next? Continue any story or start fresh..." className="flex-1 bg-transparent text-white text-sm placeholder-white/30 outline-none font-medium" data-testid="create-bar-input" />
          <button onClick={go}
            className="flex items-center gap-1.5 px-4 py-2 bg-white text-black text-xs font-extrabold rounded-lg hover:opacity-90 transition-opacity flex-shrink-0 shadow-md" data-testid="create-bar-btn">
            <ArrowRight className="w-3.5 h-3.5" /> Go
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
  const isAdmin = isAdminUser();

  useEffect(() => {
    refreshCredits();
    const load = async () => {
      try {
        const res = await axios.get(`${API}/api/engagement/story-feed`, auth());
        console.log('[Dashboard] Feed loaded:', { hero: !!res.data.hero, trending: res.data.trending?.length, stats: res.data.live_stats });
        setFeed(res.data);

        // PRELOAD WORKER: Eagerly fetch first 12 thumbnail images in parallel
        const allStories = [res.data.hero, ...(res.data.trending || [])].filter(Boolean);
        const imageUrls = allStories.map(s => mediaUrl(s.thumbnail_url)).filter(Boolean);
        preloadImages(imageUrls);
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

      {/* ADMIN MENU BAR — only visible to admin users */}
      {isAdmin && (
        <div className="fixed top-0 left-0 right-0 z-50 bg-slate-900/95 backdrop-blur-md border-b border-indigo-500/20" data-testid="admin-top-bar">
          <div className="flex items-center justify-between px-4 sm:px-8 py-2">
            <Link to="/app/admin" className="flex items-center gap-2 text-indigo-400 hover:text-indigo-300 transition-colors" data-testid="admin-menu-link">
              <Shield className="w-4 h-4" />
              <span className="text-xs font-bold tracking-wide">ADMIN PANEL</span>
            </Link>
            <div className="flex items-center gap-3">
              <Link to="/app/admin/content-engine" className="text-[11px] text-slate-400 hover:text-white font-medium transition-colors" data-testid="admin-quick-content">Content Engine</Link>
              <Link to="/app/admin/workers" className="text-[11px] text-slate-400 hover:text-white font-medium transition-colors" data-testid="admin-quick-workers">Jobs</Link>
              <Link to="/app/admin/system-health" className="text-[11px] text-slate-400 hover:text-white font-medium transition-colors" data-testid="admin-quick-health">Health</Link>
              <Link to="/app/admin/users" className="text-[11px] text-slate-400 hover:text-white font-medium transition-colors" data-testid="admin-quick-users">Users</Link>
              <Link to="/app/profile" className="w-7 h-7 rounded-full bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center" data-testid="admin-profile-link">
                <User className="w-3.5 h-3.5 text-indigo-400" />
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* ▸ HERO — ALWAYS renders */}
      <div className={isAdmin ? 'pt-10' : ''}>
        <HeroSection stories={heroPool} navigate={navigate} />
      </div>

      {/* ▸ TRENDING NOW — first 4 cards get priority loading */}
      <ScrollRow title="Trending Now" icon={Flame} iconColor="text-amber-400"
        seeAllAction={trending.length > 0 ? () => navigate('/app/explore') : undefined} testId="trending-now">
        {trendingStories.map((story, idx) => (
          <StoryCard key={story.job_id} story={story} idx={idx} navigate={navigate} size="lg" priority={idx < 4} />
        ))}
      </ScrollRow>

      {/* ▸ UNFINISHED WORLDS — ALWAYS renders */}
      <ScrollRow title="Unfinished Worlds" icon={Sparkles} iconColor="text-violet-400" testId="fresh-stories">
        {freshStories.map((story, idx) => (
          <StoryCard key={`fresh-${story.job_id}`} story={story} idx={idx + 20} navigate={navigate} size="md" priority={idx < 4} />
        ))}
      </ScrollRow>

      {/* ▸ CONTINUE WATCHING — only if real video stories exist */}
      {watchableStories.length > 0 && (
        <ScrollRow title="Continue Watching" icon={Play} iconColor="text-emerald-400" testId="watch-now">
          {watchableStories.map((story, idx) => (
            <StoryCard key={`watch-${story.job_id}`} story={story} idx={idx + 40} navigate={navigate} size="md" priority={idx < 4} />
          ))}
        </ScrollRow>
      )}

      {/* ▸ FEATURES GRID — 10 bold creator tools */}
      <FeaturesGrid navigate={navigate} />

      {/* ▸ CREATE BAR + CREDITS — footer */}
      <div className="border-t border-white/[0.06]">
        <CreateBar navigate={navigate} />
        <div className="flex items-center justify-between px-6 sm:px-10 lg:px-14 py-2">
          <div className="flex items-center gap-5 text-xs text-white/35">
            <span className="flex items-center gap-1.5 font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              {live_stats.total_stories || 0} stories
            </span>
            <span className="flex items-center gap-1.5" data-testid="credits-display">
              <Zap className="w-3.5 h-3.5 text-violet-400" />
              {!isLoggedIn ? (
                <button onClick={() => navigate('/login')} className="flex items-center gap-1 text-violet-400 hover:text-violet-300 font-bold" data-testid="credits-login-cta">
                  <LogIn className="w-3 h-3" /> Sign in to create
                </button>
              ) : !creditsLoaded ? (
                <span className="inline-block w-10 h-3 bg-white/10 rounded animate-pulse" data-testid="credits-skeleton" />
              ) : (
                <span className="text-white/50 font-bold" data-testid="credits-value">
                  {credits >= 999999 ? 'Unlimited' : `${credits}`} credits
                </span>
              )}
            </span>
          </div>
        </div>
      </div>

      <style>{`.scrollbar-hide::-webkit-scrollbar{display:none}.scrollbar-hide{-ms-overflow-style:none;scrollbar-width:none}`}</style>
    </div>
  );
}
