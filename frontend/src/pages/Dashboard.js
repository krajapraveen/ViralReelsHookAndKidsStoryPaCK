import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { useCredits } from '../contexts/CreditContext';
import axios from 'axios';
import { trackLoop } from '../utils/growthTracker';
import {
  Play, ChevronRight, ChevronLeft, Sparkles, Zap,
  Flame, Clock, Search, Plus,
  Film, BookOpen, Star, ArrowRight, Shield, User,
  Camera, Palette, PenTool, RefreshCw, Share2, Activity,
  Home, Heart, Wand2, Megaphone, Lightbulb, Image as ImageIcon
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

const BG = '#0B0B0F';
const CARD_BG = '#121218';

function isAdminUser() {
  try {
    const token = localStorage.getItem('token');
    if (!token) return false;
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.role?.toUpperCase() === 'ADMIN' || payload.role?.toUpperCase() === 'SUPERADMIN';
  } catch { return false; }
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

const SEED_CARDS = [
  { job_id: 'seed-1', title: 'A Midnight Train to Nowhere', hook_text: "The station was empty... except for the girl with no shadow.", is_seed: true, badge: 'UNFINISHED', animation_style: 'watercolor' },
  { job_id: 'seed-2', title: "The Last Dragon's Secret", hook_text: "She found the egg under the floorboards. It was warm.", is_seed: true, badge: 'UNFINISHED', animation_style: 'anime' },
  { job_id: 'seed-3', title: 'Echoes in the Library', hook_text: "The book opened itself to page 47. It was blank yesterday.", is_seed: true, badge: 'UNFINISHED', animation_style: 'cartoon_2d' },
  { job_id: 'seed-4', title: "The Clockmaker's Daughter", hook_text: "Every clock in town stopped at 3:33 AM.", is_seed: true, badge: 'UNFINISHED', animation_style: 'cinematic' },
  { job_id: 'seed-5', title: 'Whispers Under the Ice', hook_text: "Something was moving beneath the frozen lake.", is_seed: true, badge: 'UNFINISHED', animation_style: 'watercolor' },
  { job_id: 'seed-6', title: 'The Map That Bleeds', hook_text: "The old map showed a country that doesn't exist.", is_seed: true, badge: 'UNFINISHED', animation_style: 'anime' },
];

function getHook(story, idx) {
  if (story.hook_text && story.hook_text.length > 15) return story.hook_text;
  if (story.story_prompt) {
    const s = story.story_prompt.split(/[.!?]+/).filter(s => s.trim().length > 10);
    if (s.length > 0) return s[0].trim() + '...';
  }
  return HOOK_BANK[idx % HOOK_BANK.length];
}

const BADGE_STYLES = {
  TRENDING: 'bg-amber-500 text-black', FEATURED: 'bg-rose-600 text-white',
  '#1': 'bg-rose-500 text-white', HOT: 'bg-rose-500/80 text-white',
  FRESH: 'bg-emerald-500 text-white', CONTINUE: 'bg-blue-500 text-white',
  UNFINISHED: 'bg-amber-500/90 text-black', NEW: 'bg-white/15 text-white',
};

const GRAD_COLORS = [
  'from-indigo-500 to-blue-800', 'from-rose-500 to-purple-800',
  'from-emerald-500 to-teal-800', 'from-cyan-500 to-blue-800',
  'from-amber-500 to-orange-800', 'from-pink-500 to-rose-800',
];

/* ═══════════════════════════════════════════════════════════════════
   SHIMMER — replaces all spinners
   ═══════════════════════════════════════════════════════════════════ */
function Shimmer({ w, h, rounded = 'rounded-xl', className = '' }) {
  return (
    <div className={`${rounded} ${className} flex-shrink-0 overflow-hidden`}
      style={{ width: w, height: h, background: 'rgba(255,255,255,.04)' }}>
      <div className="w-full h-full shimmer-bar" />
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   1. HERO — 60vh mobile / 72vh desktop, POSTER-ONLY (no video)
      Ken Burns slow-zoom on poster. Light sweep overlay for motion.
      Real video lives on watch/result pages, not the homepage.
   ═══════════════════════════════════════════════════════════════════ */
function HeroSection({ stories, navigate }) {
  const [activeIdx, setActiveIdx] = useState(0);
  const [posterLoaded, setPosterLoaded] = useState(false);
  const [posterFailed, setPosterFailed] = useState(false);
  const [paused, setPaused] = useState(false);
  const timerRef = useRef(null);
  const posterTimeoutRef = useRef(null);

  const heroStories = stories.length > 0 ? stories.slice(0, 5) : [];
  const current = heroStories[activeIdx] || {};
  // Same-origin proxy image — Safari-safe, auto-resized, LRU-cached
  const posterSrc = current.poster_url ? `${API}${current.poster_url}` : null;
  const hasHero = heroStories.length > 0;

  const startTimer = useCallback(() => {
    clearInterval(timerRef.current);
    if (heroStories.length <= 1) return;
    timerRef.current = setInterval(() => setActiveIdx(prev => (prev + 1) % heroStories.length), 8000);
  }, [heroStories.length]);

  useEffect(() => { if (!paused) startTimer(); return () => clearInterval(timerRef.current); }, [paused, startTimer]);

  useEffect(() => {
    setPosterFailed(false); setPosterLoaded(false);
    clearTimeout(posterTimeoutRef.current);
    posterTimeoutRef.current = setTimeout(() => {
      setPosterFailed(prev => prev ? prev : true);
    }, 12000);
    return () => clearTimeout(posterTimeoutRef.current);
  }, [activeIdx]);

  const handlePosterLoad = () => { clearTimeout(posterTimeoutRef.current); setPosterLoaded(true); setPosterFailed(false); };
  const goTo = (idx) => { clearInterval(timerRef.current); setActiveIdx(idx); startTimer(); };
  const hash = (current.title || 'story').split('').reduce((a, c) => a + c.charCodeAt(0), 0);
  const fallbackGrad = GRAD_COLORS[hash % GRAD_COLORS.length];

  const prefillObj = {
    title: current.title || '', prompt: current.hook_text || current.story_prompt || '',
    hook_text: current.hook_text || '', animation_style: current.animation_style || '',
    parent_video_id: current.job_id || null, source_surface: 'hero',
  };

  return (
    <section className="relative w-full h-[60vh] lg:h-[72vh]" style={{ minHeight: '360px' }}
      onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)} data-testid="hero-section">

      <div className="absolute inset-0 overflow-hidden" style={{ background: BG }}>
        {/* Layer 1: Gradient fallback — always present */}
        <div className={`absolute inset-0 bg-gradient-to-br ${fallbackGrad} transition-opacity duration-700`}
          style={{ opacity: posterLoaded ? 0.5 : 1 }} />

        {/* Layer 2: Poster with Ken Burns slow zoom/pan */}
        {posterSrc && !posterFailed && (
          <img src={posterSrc} alt="" loading="eager" fetchPriority="high" decoding="sync"
            key={`poster-${activeIdx}`}
            className="absolute inset-0 w-full h-full object-cover transition-opacity duration-700"
            style={{
              opacity: posterLoaded ? 1 : 0,
              filter: 'brightness(0.55) saturate(1.3)',
              animation: posterLoaded ? `kenBurns ${heroStories.length > 1 ? '8s' : '20s'} ease-in-out forwards` : 'none',
              transformOrigin: `${50 + (hash % 30 - 15)}% ${50 + (hash % 20 - 10)}%`,
            }}
            onLoad={handlePosterLoad}
            onError={() => { clearTimeout(posterTimeoutRef.current); setPosterFailed(true); }}
            data-testid="hero-poster" />
        )}

        {/* Layer 3: Light sweep shimmer — subtle motion illusion */}
        {posterLoaded && <div className="absolute inset-0 hero-light-sweep pointer-events-none" />}
      </div>

      {/* Overlays */}
      <div className="absolute inset-0" style={{ background: posterLoaded ? 'linear-gradient(to right, rgba(0,0,0,.65), rgba(0,0,0,.25), transparent)' : 'linear-gradient(to right, rgba(0,0,0,.35), rgba(0,0,0,.1), transparent)' }} />
      <div className="absolute inset-0" style={{ background: posterLoaded ? `linear-gradient(to top, ${BG}, transparent 55%)` : `linear-gradient(to top, ${BG}, transparent 35%)` }} />

      {/* Content */}
      <div className="relative h-full flex flex-col justify-end px-5 sm:px-10 lg:px-14 pb-6 sm:pb-10 z-10 max-w-full lg:max-w-[40%] lg:min-w-[320px]"
        style={{ animation: 'fadeUp .5s ease-out' }}>
        {hasHero ? (
          <>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[10px] font-black tracking-widest px-2.5 py-0.5 rounded-md text-white"
                style={{ background: 'linear-gradient(135deg, #6C5CE7, #00C2FF)' }} data-testid="hero-featured-badge">FEATURED</span>
            </div>
            <h1 className="text-2xl sm:text-4xl lg:text-5xl font-black text-white leading-[1.1] mb-1.5 sm:mb-3 drop-shadow-2xl" data-testid="hero-title">
              {current.title || 'Untitled Story'}
            </h1>
            <p className="text-sm sm:text-base text-white/60 leading-relaxed mb-4 sm:mb-6 line-clamp-2 italic" data-testid="hero-hook">
              "{getHook(current, activeIdx)}"
            </p>
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 sm:gap-3">
              <button onClick={() => { trackLoop('click', { story_id: current.job_id, story_title: current.title, source_surface: 'hero' }); navigate('/app/story-video-studio', { state: { prefill: prefillObj, freshSession: true } }); }}
                className="flex items-center justify-center gap-2 px-6 py-3 sm:py-3.5 font-extrabold rounded-xl text-sm text-white cta-glow transition-all hover:scale-[1.03] active:scale-[0.97]"
                style={{ background: 'linear-gradient(135deg, #6C5CE7, #00C2FF)' }}
                data-testid="hero-play-btn">
                <Play className="w-4 h-4 fill-white" /> Continue Story
              </button>
              <button onClick={() => navigate('/app/story-video-studio', { state: { freshSession: true } })}
                className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-5 py-3 sm:py-3.5 font-extrabold rounded-xl text-sm text-white/80 hover:text-white border border-white/15 hover:border-white/30 transition-all"
                style={{ background: 'rgba(255,255,255,.08)', backdropFilter: 'blur(12px)' }}
                data-testid="hero-create-btn">
                <Plus className="w-4 h-4" /> Remix
              </button>
            </div>
          </>
        ) : (
          <>
            <span className="bg-amber-500 text-black text-[10px] font-black tracking-widest px-2.5 py-0.5 rounded w-fit mb-2">UNFINISHED</span>
            <h1 className="text-2xl sm:text-4xl lg:text-5xl font-black text-white leading-[1.1] mb-2" data-testid="hero-title">Every Story is Waiting for You</h1>
            <p className="text-sm text-white/50 leading-relaxed mb-4">Worlds half-built. Characters mid-sentence. Pick any story and decide what happens next.</p>
            <button onClick={() => navigate('/app/story-video-studio', { state: { freshSession: true } })}
              className="flex items-center justify-center gap-2 px-6 py-3 font-bold rounded-xl text-sm text-white cta-glow transition-all hover:scale-[1.03] w-full sm:w-fit"
              style={{ background: 'linear-gradient(135deg, #6C5CE7, #00C2FF)' }} data-testid="hero-create-btn">
              <Play className="w-4 h-4 fill-white" /> Start a Story
            </button>
          </>
        )}
      </div>

      {/* Dots */}
      {heroStories.length > 1 && (
        <div className="absolute bottom-3 sm:bottom-5 right-5 sm:right-8 flex items-center gap-1.5 z-10" data-testid="hero-dots">
          {heroStories.map((_, i) => (
            <button key={i} onClick={() => goTo(i)}
              className={`h-[3px] rounded-full transition-all duration-500 ${i === activeIdx ? 'w-6 sm:w-8 bg-white' : 'w-2.5 sm:w-3 bg-white/25 hover:bg-white/40'}`}
              data-testid={`hero-dot-${i}`} />
          ))}
        </div>
      )}
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   2. METRICS STRIP — horizontal scroll pills on mobile
   ═══════════════════════════════════════════════════════════════════ */
function MetricsStrip({ metrics }) {
  const items = [
    { label: 'Continue', value: `${metrics.continue_rate || 0}%`, icon: ArrowRight, color: '#6C5CE7' },
    { label: 'Share', value: `${metrics.share_rate || 0}%`, icon: Share2, color: '#00C2FF' },
    { label: 'K-Factor', value: `${metrics.k_factor || 0}`, icon: Activity, color: '#6C5CE7' },
    { label: 'Live', value: `${metrics.active_users || 0}`, icon: Zap, color: '#00C2FF' },
  ];
  return (
    <div className="px-4 sm:px-10 lg:px-14 -mt-5 sm:-mt-6 relative z-20" data-testid="metrics-strip">
      <div className="flex gap-3 overflow-x-auto scrollbar-hide sm:grid sm:grid-cols-4 sm:gap-4 pb-1">
        {items.map(m => (
          <div key={m.label} className="flex-shrink-0 sm:flex-shrink rounded-xl px-4 py-3 sm:p-4 border border-white/[0.06] min-w-[130px] sm:min-w-0 group hover:-translate-y-0.5 transition-all"
            style={{ background: CARD_BG, boxShadow: '0 4px 20px rgba(0,0,0,.5)' }}>
            <div className="flex items-center gap-1.5 mb-1 sm:mb-2">
              <m.icon className="w-3 h-3 sm:w-3.5 sm:h-3.5" style={{ color: m.color }} />
              <span className="text-[9px] sm:text-[10px] text-white/40 uppercase tracking-wider font-medium whitespace-nowrap">{m.label}</span>
            </div>
            <p className="text-xl sm:text-2xl font-black text-white font-mono">{m.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   3. STORY CARD — 160×220 mobile / 220×300 desktop
      Poster-only. No video. CSS hover effects for alive feel.
   ═══════════════════════════════════════════════════════════════════ */
function StoryCard({ story, idx, navigate, priority = false }) {
  const [hovered, setHovered] = useState(false);
  const cardRef = useRef(null);
  const impressionFired = useRef(false);

  const hook = getHook(story, idx);
  const badge = story.badge || 'NEW';
  const badgeStyle = BADGE_STYLES[badge] || BADGE_STYLES.NEW;
  // Same-origin proxy image — Safari-safe, auto-resized, LRU-cached
  const thumbSrc = (story.thumbnail_small_url || story.thumbnail_url)
    ? `${API}${story.thumbnail_small_url || story.thumbnail_url}`
    : null;
  const isSeed = story.is_seed;
  const gradIdx = (story.title || '').split('').reduce((a, c) => a + c.charCodeAt(0), 0) % GRAD_COLORS.length;

  useEffect(() => {
    const el = cardRef.current;
    if (!el || impressionFired.current) return;
    const obs = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !impressionFired.current) {
        impressionFired.current = true;
        trackLoop('impression', { story_id: story.job_id, story_title: story.title, hook_variant: story.hook_text, category: story.category, source_surface: story.badge || 'dashboard' });
        obs.disconnect();
      }
    }, { threshold: 0.5 });
    obs.observe(el);
    return () => obs.disconnect();
  }, [story]);

  const handleClick = () => {
    trackLoop('click', { story_id: story.job_id, story_title: story.title, hook_variant: story.hook_text, category: story.category, source_surface: story.badge || 'dashboard' });
    navigate('/app/story-video-studio', {
      state: {
        prefill: {
          title: story.title || '', prompt: story.hook_text || story.story_prompt || '',
          hook_text: story.hook_text || '', animation_style: story.animation_style || '',
          parent_video_id: isSeed ? null : story.job_id,
          source_surface: story.badge === 'TRENDING' ? 'trending' : story.badge === 'FRESH' ? 'fresh' : story.badge === 'CONTINUE' ? 'continue' : 'dashboard',
        },
        freshSession: true,
      },
    });
  };

  return (
    <div ref={cardRef} className="flex-shrink-0 group relative cursor-pointer card-float w-[160px] lg:w-[220px]"
      style={{ scrollSnapAlign: 'start' }}
      onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)}
      onClick={handleClick} data-testid={`story-card-${idx}`}>
      <div className="relative overflow-hidden rounded-xl w-[160px] h-[220px] lg:w-[220px] lg:h-[300px]" style={{
        background: CARD_BG,
        transition: 'transform .25s ease, box-shadow .25s ease',
        transform: hovered ? 'scale(1.05)' : 'scale(1)',
        boxShadow: hovered ? '0 20px 50px rgba(0,0,0,.8)' : '0 4px 12px rgba(0,0,0,.4)',
      }}>
        {thumbSrc ? (
          <img src={thumbSrc} alt={story.title || ''} loading={priority ? 'eager' : 'lazy'} decoding={priority ? 'sync' : 'async'}
            className={`absolute inset-0 w-full h-full object-cover transition-transform duration-700 ${hovered ? 'scale-110' : 'scale-100'}`} />
        ) : (
          <div className={`absolute inset-0 bg-gradient-to-br ${GRAD_COLORS[gradIdx]}`}>
            <div className="absolute inset-0 flex items-center justify-center">
              {isSeed ? <Sparkles className="w-10 h-10 lg:w-12 lg:h-12 text-white/30" /> : <Film className="w-10 h-10 lg:w-12 lg:h-12 text-white/30" />}
            </div>
          </div>
        )}

        {/* Card light sweep on hover */}
        {hovered && <div className="absolute inset-0 card-light-sweep pointer-events-none" />}

        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/20 to-transparent pointer-events-none" />
        <div className="absolute top-2.5 left-2.5 lg:top-3 lg:left-3">
          <span className={`${badgeStyle} text-[9px] lg:text-[10px] font-black tracking-wider px-2 py-0.5 lg:px-2.5 lg:py-1 rounded-md shadow-lg badge-pulse`}>{badge}</span>
        </div>
        <div className={`absolute inset-0 flex items-center justify-center transition-opacity duration-200 ${hovered ? 'opacity-100' : 'opacity-0'} pointer-events-none`}>
          <div className="w-11 h-11 lg:w-14 lg:h-14 rounded-full flex items-center justify-center border border-white/20" style={{ background: 'rgba(255,255,255,.15)', backdropFilter: 'blur(8px)' }}>
            <Play className="w-4 h-4 lg:w-5 lg:h-5 text-white fill-white ml-0.5" />
          </div>
        </div>
        <div className="absolute bottom-0 left-0 right-0 p-3 lg:p-3.5">
          <h3 className="text-xs lg:text-sm font-extrabold text-white leading-tight mb-0.5 lg:mb-1 line-clamp-1 drop-shadow-lg">{story.title || 'Untitled'}</h3>
          <p className={`text-[9px] lg:text-[10px] text-white/50 leading-snug line-clamp-2 italic mb-2 transition-all duration-300 ${hovered ? 'opacity-100 translate-y-0' : 'opacity-60 translate-y-0.5'}`}>"{hook}"</p>
          <div className={`flex items-center gap-1 text-[9px] lg:text-[10px] font-bold transition-all ${hovered ? 'text-white translate-x-0.5' : 'text-white/40'}`}>
            <Play className="w-2.5 h-2.5 lg:w-3 lg:h-3 fill-current" />
            {badge === 'CONTINUE' ? 'Continue watching' : 'Continue'} <ArrowRight className="w-2.5 h-2.5 lg:w-3 lg:h-3" />
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   SCROLL ROW — horizontal, lazy loaded, progressive reveal
   ═══════════════════════════════════════════════════════════════════ */
function ScrollRow({ title, icon: Icon, iconColor, children, testId, delay = 0 }) {
  const scrollRef = useRef(null);
  const sectionRef = useRef(null);
  const [showLeft, setShowLeft] = useState(false);
  const [showRight, setShowRight] = useState(true);
  const [visible, setVisible] = useState(false);

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

  useEffect(() => {
    const el = sectionRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) { setVisible(true); obs.disconnect(); }
    }, { rootMargin: '200px' });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  const shimmerW = typeof window !== 'undefined' && window.innerWidth < 1024 ? 160 : 220;
  const shimmerH = typeof window !== 'undefined' && window.innerWidth < 1024 ? 220 : 300;

  return (
    <section ref={sectionRef} className="relative pt-6 sm:pt-8" data-testid={testId}
      style={{ animationDelay: `${delay}ms` }}>
      <div className="flex items-center justify-between px-4 sm:px-10 lg:px-14 mb-2.5 sm:mb-3">
        <h2 className="flex items-center gap-2 text-sm sm:text-base lg:text-lg font-extrabold text-white tracking-tight">
          {Icon && <Icon className={`w-4 h-4 sm:w-5 sm:h-5 ${iconColor || 'text-white/60'}`} />}
          {title}
        </h2>
        <button onClick={() => scroll(1)} className="text-[10px] sm:text-[11px] text-white/40 hover:text-white font-medium flex items-center gap-1 transition-colors">
          See all <ChevronRight className="w-3 h-3" />
        </button>
      </div>
      <div className="relative group/row">
        {showLeft && (
          <button onClick={() => scroll(-1)} className="absolute left-1 top-1/2 -translate-y-1/2 z-10 w-8 h-8 sm:w-10 sm:h-10 rounded-full hidden sm:flex items-center justify-center text-white opacity-0 group-hover/row:opacity-100 transition-opacity border border-white/10" style={{ background: 'rgba(0,0,0,.8)' }} data-testid={`${testId}-scroll-left`}>
            <ChevronLeft className="w-4 h-4" />
          </button>
        )}
        <div ref={scrollRef} onScroll={checkScroll}
          className="flex overflow-x-auto px-4 sm:px-10 lg:px-14 pb-2 scrollbar-hide"
          style={{ gap: '12px', scrollSnapType: 'x mandatory', scrollbarWidth: 'none' }}>
          {visible ? children : (
            <div className="flex" style={{ gap: '12px' }}>
              {[1,2,3,4,5].map(i => <Shimmer key={i} w={shimmerW} h={shimmerH} />)}
            </div>
          )}
        </div>
        {showRight && (
          <button onClick={() => scroll(1)} className="absolute right-1 top-1/2 -translate-y-1/2 z-10 w-8 h-8 sm:w-10 sm:h-10 rounded-full hidden sm:flex items-center justify-center text-white opacity-0 group-hover/row:opacity-100 transition-opacity border border-white/10" style={{ background: 'rgba(0,0,0,.8)' }} data-testid={`${testId}-scroll-right`}>
            <ChevronRight className="w-4 h-4" />
          </button>
        )}
        <div className="absolute top-0 left-0 bottom-0 w-6 sm:w-12 pointer-events-none" style={{ background: `linear-gradient(to right, ${BG}, transparent)` }} />
        <div className="absolute top-0 right-0 bottom-0 w-6 sm:w-12 pointer-events-none" style={{ background: `linear-gradient(to left, ${BG}, transparent)` }} />
      </div>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   5. FEATURE BLOCKS — 2-col mobile / 4-col desktop, 10 tools
   ═══════════════════════════════════════════════════════════════════ */
const FEATURES = [
  { name: 'Story Video', desc: 'Turn ideas into cinematic stories', icon: Film, path: '/app/story-video-studio', gradient: 'from-indigo-500 to-blue-700' },
  { name: 'Story Series', desc: 'Multi-episode sagas with memory', icon: BookOpen, path: '/app/story-series', gradient: 'from-purple-500 to-fuchsia-700' },
  { name: 'Character Memory', desc: 'Persistent characters across stories', icon: User, path: '/app/characters', gradient: 'from-cyan-500 to-blue-700' },
  { name: 'Reel Generator', desc: 'Viral short-form video reels', icon: Play, path: '/app/reels', gradient: 'from-rose-500 to-pink-700' },
  { name: 'Photo to Comic', desc: 'Transform photos into comic panels', icon: Camera, path: '/app/photo-to-comic', gradient: 'from-amber-500 to-orange-700' },
  { name: 'Comic Storybook', desc: 'Panel-by-panel illustrated stories', icon: Palette, path: '/app/comic-storybook', gradient: 'from-emerald-500 to-green-700' },
  { name: 'Bedtime Stories', desc: 'Narrated sleep tales with visuals', icon: Star, path: '/app/bedtime-stories', gradient: 'from-indigo-500 to-purple-700' },
  { name: 'Reaction GIF', desc: 'Photo-to-reaction GIF in seconds', icon: ImageIcon, path: '/app/gif-maker', gradient: 'from-pink-500 to-rose-700' },
  { name: 'Brand Story', desc: 'Cinematic brand narratives', icon: Megaphone, path: '/app/brand-story-builder', gradient: 'from-teal-500 to-cyan-700' },
  { name: 'Daily Viral Ideas', desc: 'AI-generated trending prompts', icon: Lightbulb, path: '/app/daily-viral-ideas', gradient: 'from-amber-500 to-red-700' },
];

function FeaturesGrid({ navigate }) {
  return (
    <section className="px-4 sm:px-10 lg:px-14 pt-6 sm:pt-8 pb-4 sm:pb-6" data-testid="features-grid">
      <h2 className="flex items-center gap-2 text-sm sm:text-base lg:text-lg font-extrabold text-white tracking-tight mb-4 sm:mb-5">
        <Zap className="w-4 h-4 sm:w-5 sm:h-5 text-amber-400" /> Creator Tools
      </h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3 sm:gap-4">
        {FEATURES.map(f => {
          const Icon = f.icon;
          return (
            <button key={f.name} onClick={() => navigate(f.path, { state: { freshSession: true } })}
              className="group relative overflow-hidden rounded-2xl border border-white/[0.06] text-left cursor-pointer transition-all hover:-translate-y-1 active:scale-[0.97]"
              style={{ background: CARD_BG, padding: '16px' }}
              data-testid={`feature-${f.name.replace(/\s/g, '-').toLowerCase()}`}>
              <div className={`w-10 h-10 sm:w-12 sm:h-12 rounded-xl bg-gradient-to-br ${f.gradient} flex items-center justify-center mb-3 group-hover:scale-110 transition-transform shadow-lg`}>
                <Icon className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
              </div>
              <h3 className="text-xs sm:text-sm font-bold text-white leading-tight mb-0.5">{f.name}</h3>
              <p className="text-[10px] sm:text-xs text-white/40 leading-relaxed mb-2 line-clamp-1">{f.desc}</p>
              <span className="flex items-center gap-1 text-[9px] sm:text-[10px] font-bold text-white/30 group-hover:text-white transition-colors">
                Continue <ArrowRight className="w-2.5 h-2.5 sm:w-3 sm:h-3" />
              </span>
              <div className={`absolute inset-0 bg-gradient-to-br ${f.gradient} opacity-0 group-hover:opacity-[0.08] transition-opacity pointer-events-none rounded-2xl`} />
            </button>
          );
        })}
      </div>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   6. REAL-TIME ACTIVITY BAR (Technique 6)
   ═══════════════════════════════════════════════════════════════════ */
function ActivityBar({ feed }) {
  const [visible, setVisible] = useState(true);
  const [currentIdx, setCurrentIdx] = useState(0);

  useEffect(() => {
    if (!feed || feed.length === 0) return;
    const iv = setInterval(() => setCurrentIdx(prev => (prev + 1) % feed.length), 4000);
    return () => clearInterval(iv);
  }, [feed]);

  if (!feed || feed.length === 0 || !visible) return null;
  const item = feed[currentIdx] || feed[0];
  const labels = { continue: 'continued', share: 'shared', watch_complete: 'finished watching', signup_from_share: 'signed up from' };

  return (
    <div className="fixed bottom-20 sm:bottom-6 right-4 sm:right-6 z-30 max-w-[280px] sm:max-w-xs" data-testid="activity-bar"
      style={{ animation: 'fadeUp .4s ease-out' }}>
      <div className="rounded-xl border border-white/[0.08] px-3 sm:px-4 py-2.5 sm:py-3 flex items-center gap-2.5 shadow-2xl" style={{ background: 'rgba(18,18,24,.95)', backdropFilter: 'blur(16px)' }}>
        <div className={`w-2 h-2 rounded-full flex-shrink-0 animate-pulse ${item.event === 'continue' ? 'bg-violet-400' : item.event === 'share' ? 'bg-blue-400' : 'bg-emerald-400'}`} />
        <p className="text-[10px] sm:text-xs text-white/50 flex-1 line-clamp-1">
          Someone <span className="text-white font-medium">{labels[item.event] || item.event}</span> "{item.story_title}"
        </p>
        <button onClick={() => setVisible(false)} className="text-white/20 hover:text-white/60 text-xs flex-shrink-0">x</button>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   7. STICKY BOTTOM NAV — mobile only
   ═══════════════════════════════════════════════════════════════════ */
function StickyBottomNav({ navigate, currentPath }) {
  const items = [
    { label: 'Home', icon: Home, path: '/app' },
    { label: 'Explore', icon: Search, path: '/app/explore' },
    { label: 'Create', icon: Plus, path: '/app/story-video-studio', isCenter: true },
    { label: 'Stories', icon: Heart, path: '/app/my-stories' },
    { label: 'Profile', icon: User, path: '/app/profile' },
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 lg:hidden border-t border-white/[0.06]"
      style={{ background: 'rgba(11,11,15,.92)', backdropFilter: 'blur(20px)' }}
      data-testid="sticky-bottom-nav">
      <div className="flex items-center justify-around px-2 py-1.5 safe-bottom">
        {items.map(item => {
          const Icon = item.icon;
          const isActive = currentPath === item.path || (item.path === '/app' && currentPath === '/app');
          if (item.isCenter) {
            return (
              <button key={item.label} onClick={() => navigate(item.path, { state: { freshSession: true } })}
                className="flex flex-col items-center gap-0.5 -mt-4"
                data-testid="nav-create-btn">
                <div className="w-12 h-12 rounded-full flex items-center justify-center shadow-lg cta-glow"
                  style={{ background: 'linear-gradient(135deg, #6C5CE7, #00C2FF)' }}>
                  <Icon className="w-5 h-5 text-white" strokeWidth={2.5} />
                </div>
                <span className="text-[9px] font-bold text-white/80">{item.label}</span>
              </button>
            );
          }
          return (
            <button key={item.label} onClick={() => navigate(item.path)}
              className="flex flex-col items-center gap-0.5 py-1 px-3 transition-colors"
              data-testid={`nav-${item.label.toLowerCase()}`}>
              <Icon className={`w-5 h-5 transition-colors ${isActive ? 'text-white' : 'text-white/30'}`} strokeWidth={isActive ? 2 : 1.5} />
              <span className={`text-[9px] font-medium transition-colors ${isActive ? 'text-white' : 'text-white/30'}`}>{item.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   SHIMMER SKELETON (Technique 2 — no spinners)
   ═══════════════════════════════════════════════════════════════════ */
function DashboardSkeleton() {
  return (
    <div className="min-h-screen" style={{ background: BG }} data-testid="dashboard-skeleton">
      <div className="w-full h-[60vh] lg:h-[72vh]" style={{ minHeight: '360px', background: 'linear-gradient(135deg, #1a1a2e, #0B0B0F)' }}>
        <div className="h-full flex flex-col justify-end p-5 sm:p-10 max-w-full lg:max-w-[40%] lg:min-w-[320px]">
          <Shimmer w={72} h={18} rounded="rounded-md" className="mb-3" />
          <Shimmer w={280} h={36} rounded="rounded-md" className="mb-2" />
          <Shimmer w={200} h={16} rounded="rounded-md" className="mb-5" />
          <div className="flex gap-3">
            <Shimmer w={140} h={44} rounded="rounded-xl" />
            <Shimmer w={100} h={44} rounded="rounded-xl" />
          </div>
        </div>
      </div>
      <div className="flex gap-3 px-4 sm:px-10 -mt-5 overflow-hidden">
        {[1,2,3,4].map(i => <Shimmer key={i} w={130} h={70} className="flex-shrink-0 sm:flex-1" />)}
      </div>
      {[1,2].map(r => (
        <div key={r} className="px-4 sm:px-10 pt-6 sm:pt-8">
          <Shimmer w={120} h={16} rounded="rounded-md" className="mb-3" />
          <div className="flex gap-3">{[1,2,3,4,5].map(c => <Shimmer key={c} w={160} h={220} />)}</div>
        </div>
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   MAIN DASHBOARD — Progressive loading (Technique 3)
   Hero → Metrics → Rows → Features → Nav
   ═══════════════════════════════════════════════════════════════════ */
export default function Dashboard() {
  const navigate = useNavigate();
  const location = useLocation();
  const { credits, creditsLoaded, refreshCredits } = useCredits();
  const [feed, setFeed] = useState(null);
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState({});
  const [liveFeed, setLiveFeed] = useState([]);
  const isAdmin = isAdminUser();
  const isLoggedIn = !!localStorage.getItem('token');

  useEffect(() => {
    refreshCredits();
    const load = async () => {
      try {
        const [feedRes, metricsRes] = await Promise.all([
          axios.get(`${API}/api/engagement/story-feed`, auth()),
          axios.get(`${API}/api/growth/loop-dashboard?days=7`, auth()).catch(() => ({ data: { health: {}, live_feed: [], raw: {} } })),
        ]);
        setFeed(feedRes.data);
        setMetrics({ ...metricsRes.data.health, active_users: metricsRes.data.raw?.active_users || 0 });
        setLiveFeed(metricsRes.data.live_feed || []);
      } catch (e) {
        console.error('[Dashboard] Feed load failed:', e.message);
        setFeed({ featured_story: null, trending_stories: [], fresh_stories: [], continue_stories: [], unfinished_worlds: [], live_stats: {} });
      }
      setLoading(false);
    };
    load();
  }, []);

  // ── Preload hero poster + first 4 card thumbnails for instant perception ──
  useEffect(() => {
    if (!feed) return;
    const hero = feed.featured_story;
    const preloads = [];
    if (hero?.poster_url) {
      preloads.push(`${API}${hero.poster_url}`);
    }
    (feed.trending_stories || []).slice(0, 4).forEach(s => {
      if (s?.thumbnail_small_url) preloads.push(`${API}${s.thumbnail_small_url}`);
    });
    const links = preloads.map((href, i) => {
      const link = document.createElement('link');
      link.rel = 'preload';
      link.as = 'image';
      link.href = href;
      if (i === 0) link.fetchPriority = 'high';
      document.head.appendChild(link);
      return link;
    });
    return () => links.forEach(l => l.remove());
  }, [feed]);

  if (loading) return <DashboardSkeleton />;

  const { featured_story, trending_stories = [], fresh_stories = [], continue_stories = [], unfinished_worlds = [], live_stats = {} } = feed || {};
  const heroPool = [featured_story, ...trending_stories.filter(s => s?.job_id !== featured_story?.job_id)].filter(Boolean).slice(0, 5);

  const trendingRow = trending_stories.length > 0 ? trending_stories : SEED_CARDS;
  const freshRow = fresh_stories.length > 0 ? fresh_stories : [...SEED_CARDS].reverse();
  const continueRow = continue_stories.length > 0 ? continue_stories : SEED_CARDS.slice(0, 4).map(s => ({ ...s, badge: 'CONTINUE' }));
  const unfinishedRow = unfinished_worlds.length > 0 ? unfinished_worlds : SEED_CARDS;

  return (
    <div className="min-h-screen pb-16 lg:pb-0" style={{ background: BG }} data-testid="dashboard">

      {/* ADMIN BAR — desktop only */}
      {isAdmin && (
        <div className="fixed top-0 left-0 right-0 z-50 border-b border-indigo-500/20 hidden lg:block" style={{ background: 'rgba(11,11,15,.95)', backdropFilter: 'blur(12px)' }} data-testid="admin-top-bar">
          <div className="flex items-center justify-between px-8 py-2">
            <Link to="/app/admin" className="flex items-center gap-2 text-indigo-400 hover:text-indigo-300 transition-colors" data-testid="admin-menu-link">
              <Shield className="w-4 h-4" /><span className="text-xs font-bold tracking-wide">ADMIN PANEL</span>
            </Link>
            <div className="flex items-center gap-3">
              <Link to="/app/admin/growth" className="text-[11px] text-slate-400 hover:text-white font-medium transition-colors" data-testid="admin-quick-growth">Growth</Link>
              <Link to="/app/admin/content-engine" className="text-[11px] text-slate-400 hover:text-white font-medium transition-colors">Content</Link>
              <Link to="/app/admin/workers" className="text-[11px] text-slate-400 hover:text-white font-medium transition-colors">Jobs</Link>
              <Link to="/app/admin/system-health" className="text-[11px] text-slate-400 hover:text-white font-medium transition-colors">Health</Link>
              <Link to="/app/profile" className="w-7 h-7 rounded-full bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center">
                <User className="w-3.5 h-3.5 text-indigo-400" />
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* 1. HERO */}
      <div className={isAdmin ? 'lg:pt-10' : ''}>
        <HeroSection stories={heroPool} navigate={navigate} />
      </div>

      {/* 2. METRICS STRIP */}
      <MetricsStrip metrics={metrics} />

      {/* 3. STORY ROWS — progressive reveal with staggered delays */}
      <ScrollRow title="Trending Now" icon={Flame} iconColor="text-amber-400" testId="trending-now" delay={0}>
        {trendingRow.map((story, idx) => <StoryCard key={story.job_id || `t-${idx}`} story={story} idx={idx} navigate={navigate} priority={idx < 4} />)}
      </ScrollRow>

      {/* 4. CONTINUE ROW — personal, prioritized */}
      <ScrollRow title="Continue Your Story" icon={RefreshCw} iconColor="text-blue-400" testId="continue-stories" delay={100}>
        {continueRow.map((story, idx) => <StoryCard key={`c-${story.job_id || idx}`} story={story} idx={idx + 40} navigate={navigate} />)}
      </ScrollRow>

      <ScrollRow title="Fresh Stories" icon={Sparkles} iconColor="text-violet-400" testId="fresh-stories" delay={200}>
        {freshRow.map((story, idx) => <StoryCard key={`f-${story.job_id || idx}`} story={story} idx={idx + 20} navigate={navigate} priority={idx < 4} />)}
      </ScrollRow>

      <ScrollRow title="Unfinished Worlds" icon={Clock} iconColor="text-emerald-400" testId="unfinished-worlds" delay={300}>
        {unfinishedRow.map((story, idx) => <StoryCard key={`u-${story.job_id || idx}`} story={story} idx={idx + 60} navigate={navigate} />)}
      </ScrollRow>

      {/* 5. FEATURE BLOCKS */}
      <FeaturesGrid navigate={navigate} />

      {/* FOOTER */}
      <div className="border-t border-white/[0.04]">
        <div className="flex items-center justify-between px-4 sm:px-10 lg:px-14 py-3 sm:py-4">
          <div className="flex items-center gap-4 text-[10px] sm:text-xs text-white/30">
            <span className="flex items-center gap-1.5 font-medium">
              <span className="w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full bg-emerald-500 animate-pulse" /> {live_stats.total_stories || 0} stories
            </span>
            <span className="flex items-center gap-1.5" data-testid="credits-display">
              <Zap className="w-3 h-3 sm:w-3.5 sm:h-3.5" style={{ color: '#6C5CE7' }} />
              {!isLoggedIn ? (
                <button onClick={() => navigate('/login')} className="font-bold hover:text-white transition-colors" style={{ color: '#6C5CE7' }} data-testid="credits-login-cta">
                  Sign in to create
                </button>
              ) : !creditsLoaded ? (
                <span className="inline-block w-10 h-3 bg-white/10 rounded shimmer-bar" data-testid="credits-skeleton" />
              ) : (
                <span className="text-white/50 font-bold" data-testid="credits-value">{credits >= 999999 ? 'Unlimited' : `${credits} credits`}</span>
              )}
            </span>
          </div>
        </div>
      </div>

      {/* 6. ACTIVITY BAR (Technique 6) */}
      <ActivityBar feed={liveFeed} />

      {/* 7. STICKY BOTTOM NAV — mobile only */}
      <StickyBottomNav navigate={navigate} currentPath={location.pathname} />

      {/* Global styles */}
      <style>{`
        .scrollbar-hide::-webkit-scrollbar{display:none}
        .scrollbar-hide{-ms-overflow-style:none;scrollbar-width:none}
        @keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
        @keyframes shimmer{0%{background-position:-200% 0}100%{background-position:200% 0}}
        .shimmer-bar{background:linear-gradient(90deg,transparent 0%,rgba(255,255,255,.06) 50%,transparent 100%);background-size:200% 100%;animation:shimmer 1.5s infinite}
        .cta-glow{box-shadow:0 0 20px rgba(108,92,231,.35),0 0 60px rgba(0,194,255,.15)}
        .card-float{transition:transform .3s ease}
        .card-float:hover{transform:translateY(-2px)}
        .safe-bottom{padding-bottom:env(safe-area-inset-bottom,0)}

        /* Ken Burns slow zoom for hero poster */
        @keyframes kenBurns{
          0%{transform:scale(1)}
          100%{transform:scale(1.08)}
        }

        /* Hero light sweep — subtle diagonal shimmer across poster */
        @keyframes heroSweep{
          0%{transform:translateX(-100%) skewX(-15deg)}
          100%{transform:translateX(300%) skewX(-15deg)}
        }
        .hero-light-sweep{
          background:linear-gradient(90deg,transparent 0%,rgba(255,255,255,.04) 40%,rgba(255,255,255,.07) 50%,rgba(255,255,255,.04) 60%,transparent 100%);
          animation:heroSweep 6s ease-in-out infinite;
          animation-delay:1s;
        }

        /* Card light sweep on hover */
        @keyframes cardSweep{
          0%{transform:translateX(-100%) skewX(-15deg)}
          100%{transform:translateX(300%) skewX(-15deg)}
        }
        .card-light-sweep{
          background:linear-gradient(90deg,transparent 0%,rgba(255,255,255,.06) 40%,rgba(255,255,255,.12) 50%,rgba(255,255,255,.06) 60%,transparent 100%);
          animation:cardSweep .8s ease-out forwards;
        }

        /* Badge pulse — subtle glow for NEW/TRENDING/CONTINUE badges */
        .badge-pulse{animation:badgePulse 3s ease-in-out infinite}
        @keyframes badgePulse{
          0%,100%{box-shadow:0 0 4px rgba(255,255,255,.1)}
          50%{box-shadow:0 0 12px rgba(255,255,255,.2)}
        }
      `}</style>
    </div>
  );
}
