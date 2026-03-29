import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useCredits } from '../contexts/CreditContext';
import axios from 'axios';
import { SafeImage } from '../components/SafeImage';
import { trackLoop } from '../utils/growthTracker';
import {
  Play, ChevronRight, ChevronLeft, Sparkles, Zap,
  Flame, Clock, LogIn, Search, Plus, Volume2, VolumeX,
  Film, BookOpen, Star, ArrowRight, Shield, User,
  Camera, Palette, PenTool, Lightbulb, RefreshCw, Mic, Share2, Activity
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

// ── Design tokens ──
const BG = '#0B0B0F';
const CARD_BG = '#121218';

function mediaUrl(path) {
  if (!path) return null;
  if (path.startsWith('/api/media/')) return `${API}${path}`;
  return path;
}

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
   1. HERO SECTION — 72vh, auto-rotate 6s, pause on hover
   ═══════════════════════════════════════════════════════════════════ */
function HeroSection({ stories, navigate }) {
  const [activeIdx, setActiveIdx] = useState(0);
  const [isMuted, setIsMuted] = useState(true);
  const [videoFailed, setVideoFailed] = useState(false);
  const [posterFailed, setPosterFailed] = useState(false);
  const [paused, setPaused] = useState(false);
  const videoRef = useRef(null);
  const timerRef = useRef(null);

  const heroStories = stories.length > 0 ? stories.slice(0, 5) : [];
  const current = heroStories[activeIdx] || {};
  const videoSrc = mediaUrl(current.preview_url || current.output_url);
  const posterSrc = mediaUrl(current.thumbnail_url);
  const canShowVideo = videoSrc && !videoFailed;
  const hasHero = heroStories.length > 0;
  const mediaVisible = (posterSrc && !posterFailed) || canShowVideo;

  const startTimer = useCallback(() => {
    clearInterval(timerRef.current);
    if (heroStories.length <= 1) return;
    timerRef.current = setInterval(() => {
      setActiveIdx(prev => (prev + 1) % heroStories.length);
    }, 6000);
  }, [heroStories.length]);

  useEffect(() => {
    if (!paused) startTimer();
    return () => clearInterval(timerRef.current);
  }, [paused, startTimer]);

  useEffect(() => {
    setVideoFailed(false);
    setPosterFailed(false);
    if (videoRef.current) { videoRef.current.load(); videoRef.current.play().catch(() => {}); }
  }, [activeIdx]);

  const goTo = (idx) => { clearInterval(timerRef.current); setActiveIdx(idx); startTimer(); };

  const hash = (current.title || 'story').split('').reduce((a, c) => a + c.charCodeAt(0), 0);
  const fallbackGrad = GRAD_COLORS[hash % GRAD_COLORS.length];

  const prefillObj = {
    title: current.title || '', prompt: current.hook_text || current.story_prompt || '',
    hook_text: current.hook_text || '', animation_style: current.animation_style || '',
    parent_video_id: current.job_id || null, source_surface: 'hero',
  };

  return (
    <section className="relative w-full" style={{ height: '72vh', minHeight: '420px' }}
      onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)} data-testid="hero-section">

      <div className="absolute inset-0 overflow-hidden" style={{ background: BG }}>
        {/* Always-visible gradient fallback — saturated when no media loads */}
        <div className={`absolute inset-0 bg-gradient-to-br ${fallbackGrad} transition-opacity duration-500`}
          style={{ opacity: mediaVisible ? 0.6 : 1 }} />
        {posterSrc && !posterFailed && (
          <img src={posterSrc} alt="" loading="eager" fetchPriority="high" decoding="sync"
            className="absolute inset-0 w-full h-full object-cover" style={{ filter: 'brightness(0.6) saturate(1.3)' }}
            onError={() => setPosterFailed(true)}
            data-testid="hero-poster" />
        )}
        {canShowVideo && (
          <video ref={videoRef} key={`hero-${current.job_id}`} src={videoSrc} muted={isMuted} autoPlay loop playsInline preload="auto"
            className="absolute inset-0 w-full h-full object-cover" style={{ filter: 'brightness(0.6) saturate(1.3)' }}
            data-testid="hero-video" onError={() => setVideoFailed(true)} />
        )}
      </div>
      {/* Gradient overlays: lighter when no media loaded so fallback gradient stays vivid */}
      <div className="absolute inset-0" style={{ background: mediaVisible ? 'linear-gradient(to right, rgba(0,0,0,.7), rgba(0,0,0,.3), transparent)' : 'linear-gradient(to right, rgba(0,0,0,.4), rgba(0,0,0,.1), transparent)' }} />
      <div className="absolute inset-0" style={{ background: mediaVisible ? `linear-gradient(to top, ${BG}, transparent 60%)` : `linear-gradient(to top, ${BG}, transparent 40%)` }} />

      <div className="relative h-full flex flex-col justify-end px-6 sm:px-10 lg:px-14 pb-10 z-10" style={{ maxWidth: '40%', minWidth: '320px', animation: 'fadeUp .5s ease-out' }}>
        {hasHero ? (
          <>
            <div className="flex items-center gap-2 mb-3">
              <span className="text-[11px] font-black tracking-widest px-3 py-1 rounded-md shadow-lg text-white" style={{ background: 'linear-gradient(135deg, #6C5CE7, #00C2FF)', boxShadow: '0 4px 15px rgba(108,92,231,.3)' }} data-testid="hero-featured-badge">FEATURED</span>
              {canShowVideo && (
                <span className="flex items-center gap-1 bg-red-600 text-white text-[10px] font-black px-2.5 py-1 rounded-md shadow-lg shadow-red-600/30">
                  <span className="w-2 h-2 rounded-full bg-white animate-pulse" /> LIVE
                </span>
              )}
            </div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black text-white leading-[1.05] mb-3 drop-shadow-2xl" data-testid="hero-title">
              {current.title || 'Untitled Story'}
            </h1>
            <p className="text-base sm:text-lg text-[#A0A0B2] leading-relaxed mb-6 line-clamp-2 italic" data-testid="hero-hook">
              "{getHook(current, activeIdx)}"
            </p>
            <div className="flex items-center gap-3">
              <button onClick={() => { trackLoop('click', { story_id: current.job_id, story_title: current.title, source_surface: 'hero' }); navigate('/app/story-video-studio', { state: { prefill: prefillObj, freshSession: true } }); }}
                className="flex items-center gap-2 px-7 py-3.5 font-extrabold rounded-xl text-sm text-white transition-all hover:scale-[1.03] active:scale-[0.97] shadow-xl"
                style={{ background: 'linear-gradient(135deg, #6C5CE7, #00C2FF)', boxShadow: '0 8px 30px rgba(108,92,231,.4)' }}
                data-testid="hero-play-btn">
                <Play className="w-5 h-5 fill-white" /> Continue Story
              </button>
              <button onClick={() => navigate('/app/story-video-studio', { state: { freshSession: true } })}
                className="flex items-center gap-2 px-6 py-3.5 font-extrabold rounded-xl text-sm text-white/80 hover:text-white transition-all border border-white/15 hover:border-white/30"
                style={{ background: 'rgba(255,255,255,.08)', backdropFilter: 'blur(12px)' }}
                data-testid="hero-create-btn">
                <Plus className="w-5 h-5" /> Remix
              </button>
              {canShowVideo && (
                <button onClick={() => setIsMuted(!isMuted)} className="w-10 h-10 flex items-center justify-center rounded-full border border-white/10 text-white/50 hover:text-white transition-all" style={{ background: 'rgba(0,0,0,.4)', backdropFilter: 'blur(8px)' }} data-testid="hero-mute-btn">
                  {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
                </button>
              )}
            </div>
          </>
        ) : (
          <>
            <span className="bg-amber-500 text-black text-[10px] font-black tracking-widest px-2.5 py-0.5 rounded w-fit mb-2">UNFINISHED</span>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black text-white leading-[1.1] mb-2 drop-shadow-2xl" data-testid="hero-title">Every Story is Waiting for You</h1>
            <p className="text-sm sm:text-base text-[#A0A0B2] leading-relaxed mb-5">Worlds half-built. Characters mid-sentence. Pick any story and decide what happens next.</p>
            <button onClick={() => navigate('/app/story-video-studio', { state: { freshSession: true } })}
              className="flex items-center gap-2 px-7 py-3.5 font-bold rounded-xl text-sm text-white transition-all hover:scale-[1.03] shadow-xl w-fit"
              style={{ background: 'linear-gradient(135deg, #6C5CE7, #00C2FF)' }} data-testid="hero-create-btn">
              <Play className="w-4 h-4 fill-white" /> Start a Story
            </button>
          </>
        )}
      </div>

      {heroStories.length > 1 && (
        <div className="absolute bottom-5 right-8 flex items-center gap-1.5 z-10" data-testid="hero-dots">
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

/* ═══════════════════════════════════════════════════════════════════
   2. METRICS STRIP — Stripe-style
   ═══════════════════════════════════════════════════════════════════ */
function MetricsStrip({ metrics }) {
  const items = [
    { label: 'Continue Rate', value: `${metrics.continue_rate || 0}%`, icon: ArrowRight, color: '#6C5CE7' },
    { label: 'Share Rate', value: `${metrics.share_rate || 0}%`, icon: Share2, color: '#00C2FF' },
    { label: 'K-Factor', value: `${metrics.k_factor || 0}`, icon: Activity, color: '#6C5CE7' },
    { label: 'Active Now', value: `${metrics.active_users || 0}`, icon: Zap, color: '#00C2FF' },
  ];
  return (
    <div className="px-6 sm:px-10 lg:px-14 -mt-6 relative z-20" data-testid="metrics-strip">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {items.map(m => (
          <div key={m.label} className="rounded-xl p-4 border border-white/[0.06] group hover:-translate-y-0.5 transition-all cursor-default"
            style={{ background: CARD_BG, boxShadow: '0 4px 20px rgba(0,0,0,.5)' }}>
            <div className="flex items-center gap-2 mb-2">
              <m.icon className="w-3.5 h-3.5" style={{ color: m.color }} />
              <span className="text-[10px] text-[#A0A0B2] uppercase tracking-wider font-medium">{m.label}</span>
            </div>
            <p className="text-2xl font-black text-white font-mono">{m.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   3. STORY CARD — 220×300, 4:5, hover scale(1.05), preview video
   ═══════════════════════════════════════════════════════════════════ */
function StoryCard({ story, idx, navigate, priority = false }) {
  const [hovered, setHovered] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const videoRef = useRef(null);
  const previewTimer = useRef(null);
  const cardRef = useRef(null);
  const impressionFired = useRef(false);

  const hook = getHook(story, idx);
  const badge = story.badge || 'NEW';
  const badgeStyle = BADGE_STYLES[badge] || BADGE_STYLES.NEW;
  const videoSrc = mediaUrl(story.preview_url || story.output_url);
  const isSeed = story.is_seed;
  const gradIdx = (story.title || '').split('').reduce((a, c) => a + c.charCodeAt(0), 0) % GRAD_COLORS.length;

  // Impression tracking
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

  // Preview video: start after 300ms hover
  useEffect(() => {
    if (!videoSrc || isSeed) return;
    if (hovered) {
      previewTimer.current = setTimeout(() => {
        setShowPreview(true);
        if (videoRef.current) videoRef.current.play().catch(() => {});
      }, 300);
    } else {
      clearTimeout(previewTimer.current);
      setShowPreview(false);
      if (videoRef.current) { videoRef.current.pause(); videoRef.current.currentTime = 0; }
    }
    return () => clearTimeout(previewTimer.current);
  }, [hovered, videoSrc, isSeed]);

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
    <div ref={cardRef} className="flex-shrink-0 group relative cursor-pointer" style={{ width: '220px', scrollSnapAlign: 'start' }}
      onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)}
      onClick={handleClick} data-testid={`story-card-${idx}`}>
      <div className="relative overflow-hidden rounded-xl" style={{
        width: '220px', height: '300px', background: CARD_BG,
        transition: 'transform .25s ease, box-shadow .25s ease',
        transform: hovered ? 'scale(1.05)' : 'scale(1)',
        boxShadow: hovered ? '0 20px 50px rgba(0,0,0,.8)' : '0 4px 12px rgba(0,0,0,.4)',
        filter: hovered ? 'brightness(1.1)' : 'brightness(1)',
      }}>
        {/* Thumbnail (always loads first) */}
        {story.thumbnail_url ? (
          <SafeImage src={mediaUrl(story.thumbnail_url)} alt={story.title} aspectRatio="4/5" fallbackType="gradient" titleOverlay={story.title}
            priority={priority} className="w-full h-full" imgClassName="w-full h-full object-cover" />
        ) : (
          <div className={`absolute inset-0 bg-gradient-to-br ${GRAD_COLORS[gradIdx]}`}>
            <div className="absolute inset-0 flex items-center justify-center">
              {isSeed ? <Sparkles className="w-12 h-12 text-white/30" /> : <Film className="w-12 h-12 text-white/30" />}
            </div>
            <div className="absolute bottom-8 left-3 right-3">
              <p className="text-[10px] text-white/30 font-medium truncate">{story.title || 'Untitled'}</p>
            </div>
          </div>
        )}
        {/* Preview video (on hover after 300ms) */}
        {videoSrc && !isSeed && (
          <video ref={videoRef} src={videoSrc} muted loop playsInline preload="metadata"
            className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-500 ${showPreview ? 'opacity-100' : 'opacity-0'}`} />
        )}
        {/* Gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/20 to-transparent pointer-events-none" />
        {/* Badge */}
        <div className="absolute top-3 left-3">
          <span className={`${badgeStyle} text-[10px] font-black tracking-wider px-2.5 py-1 rounded-md shadow-lg`}>{badge}</span>
        </div>
        {/* Hover play icon */}
        <div className={`absolute inset-0 flex items-center justify-center transition-opacity duration-200 ${hovered ? 'opacity-100' : 'opacity-0'} pointer-events-none`}>
          <div className="w-14 h-14 rounded-full flex items-center justify-center border border-white/20" style={{ background: 'rgba(255,255,255,.15)', backdropFilter: 'blur(8px)' }}>
            <Play className="w-5 h-5 text-white fill-white ml-0.5" />
          </div>
        </div>
        {/* Bottom text */}
        <div className="absolute bottom-0 left-0 right-0 p-3.5">
          <h3 className="text-sm font-extrabold text-white leading-tight mb-1 line-clamp-1 drop-shadow-lg">{story.title || 'Untitled'}</h3>
          <p className="text-[10px] text-[#A0A0B2] leading-snug line-clamp-2 italic mb-2.5">"{hook}"</p>
          <div className={`flex items-center gap-1.5 text-[10px] font-bold transition-all ${hovered ? 'text-white translate-x-0.5' : 'text-white/40'}`}>
            <Play className="w-3 h-3 fill-current" />
            {badge === 'CONTINUE' ? 'Continue watching' : 'Continue'} <ArrowRight className="w-3 h-3" />
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   SCROLL ROW — horizontal, lazy loaded via IntersectionObserver
   ═══════════════════════════════════════════════════════════════════ */
function ScrollRow({ title, icon: Icon, iconColor, children, testId }) {
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

  // Lazy load via IntersectionObserver (Tier 2)
  useEffect(() => {
    const el = sectionRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) { setVisible(true); obs.disconnect(); }
    }, { rootMargin: '200px' });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <section ref={sectionRef} className="relative" style={{ paddingTop: '32px' }} data-testid={testId}>
      <div className="flex items-center justify-between px-6 sm:px-10 lg:px-14 mb-3">
        <h2 className="flex items-center gap-2 text-base sm:text-lg font-extrabold text-white tracking-tight">
          {Icon && <Icon className={`w-5 h-5 ${iconColor || 'text-white/60'}`} />}
          {title}
        </h2>
        <button onClick={() => scroll(1)} className="text-[11px] text-[#A0A0B2] hover:text-white font-medium flex items-center gap-1 transition-colors">
          See all <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>
      <div className="relative group/row">
        {showLeft && (
          <button onClick={() => scroll(-1)} className="absolute left-1 top-1/2 -translate-y-1/2 z-10 w-10 h-10 rounded-full flex items-center justify-center text-white opacity-0 group-hover/row:opacity-100 transition-opacity border border-white/10" style={{ background: 'rgba(0,0,0,.8)', backdropFilter: 'blur(8px)' }} data-testid={`${testId}-scroll-left`}>
            <ChevronLeft className="w-4 h-4" />
          </button>
        )}
        <div ref={scrollRef} onScroll={checkScroll}
          className="flex overflow-x-auto px-6 sm:px-10 lg:px-14 pb-2 scrollbar-hide"
          style={{ gap: '16px', scrollSnapType: 'x mandatory', scrollbarWidth: 'none' }}>
          {visible ? children : <div className="flex gap-4">{[1,2,3,4,5].map(i => <div key={i} className="rounded-xl animate-pulse flex-shrink-0" style={{ width: 220, height: 300, background: 'rgba(255,255,255,.03)' }} />)}</div>}
        </div>
        {showRight && (
          <button onClick={() => scroll(1)} className="absolute right-1 top-1/2 -translate-y-1/2 z-10 w-10 h-10 rounded-full flex items-center justify-center text-white opacity-0 group-hover/row:opacity-100 transition-opacity border border-white/10" style={{ background: 'rgba(0,0,0,.8)', backdropFilter: 'blur(8px)' }} data-testid={`${testId}-scroll-right`}>
            <ChevronRight className="w-4 h-4" />
          </button>
        )}
        <div className="absolute top-0 left-0 bottom-0 w-12 pointer-events-none" style={{ background: `linear-gradient(to right, ${BG}, transparent)` }} />
        <div className="absolute top-0 right-0 bottom-0 w-12 pointer-events-none" style={{ background: `linear-gradient(to left, ${BG}, transparent)` }} />
      </div>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   6. FEATURE TOOLS — 2 rows × 4 columns
   ═══════════════════════════════════════════════════════════════════ */
const FEATURES = [
  { name: 'Story Video', desc: 'Turn ideas into cinematic stories', icon: Film, path: '/app/story-video-studio', gradient: 'from-violet-600 to-indigo-800' },
  { name: 'Story Series', desc: 'Multi-episode sagas with memory', icon: BookOpen, path: '/app/story-series', gradient: 'from-purple-600 to-fuchsia-800' },
  { name: 'Character Memory', desc: 'Persistent characters across stories', icon: User, path: '/app/characters', gradient: 'from-cyan-600 to-blue-800' },
  { name: 'Reel Generator', desc: 'Viral short-form video reels', icon: Play, path: '/app/reels', gradient: 'from-rose-600 to-pink-800' },
  { name: 'Photo to Comic', desc: 'Transform photos into comic panels', icon: Camera, path: '/app/photo-to-comic', gradient: 'from-amber-600 to-orange-800' },
  { name: 'Comic Storybook', desc: 'Panel-by-panel illustrated stories', icon: Palette, path: '/app/comic-storybook', gradient: 'from-emerald-600 to-green-800' },
  { name: 'Bedtime Stories', desc: 'Narrated sleep tales with visuals', icon: Star, path: '/app/bedtime-stories', gradient: 'from-indigo-600 to-blue-800' },
  { name: 'Caption Rewriter', desc: 'AI-powered caption rewriting', icon: PenTool, path: '/app/caption-rewriter', gradient: 'from-teal-600 to-cyan-800' },
];

function FeaturesGrid({ navigate }) {
  return (
    <section className="px-6 sm:px-10 lg:px-14" style={{ paddingTop: '32px', paddingBottom: '24px' }} data-testid="features-grid">
      <h2 className="flex items-center gap-2.5 text-base sm:text-lg font-extrabold text-white tracking-tight mb-5">
        <Zap className="w-5 h-5 text-amber-400" /> Creator Tools
      </h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        {FEATURES.map(f => {
          const Icon = f.icon;
          return (
            <button key={f.name} onClick={() => navigate(f.path, { state: { freshSession: true } })}
              className="group relative overflow-hidden rounded-2xl border border-white/[0.06] text-left cursor-pointer transition-all hover:-translate-y-1"
              style={{ background: CARD_BG, padding: '24px' }}
              data-testid={`feature-${f.name.replace(/\s/g, '-').toLowerCase()}`}>
              <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${f.gradient} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform shadow-lg`}>
                <Icon className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-sm font-bold text-white leading-tight mb-1">{f.name}</h3>
              <p className="text-xs text-[#A0A0B2] leading-relaxed mb-3">{f.desc}</p>
              <span className="flex items-center gap-1 text-[10px] font-bold text-white/40 group-hover:text-white transition-colors">
                Continue Creating <ArrowRight className="w-3 h-3" />
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
   7. REAL-TIME ACTIVITY BAR — floating bottom-right
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
    <div className="fixed bottom-6 right-6 z-40 max-w-xs animate-in slide-in-from-right" data-testid="activity-bar">
      <div className="rounded-xl border border-white/[0.08] px-4 py-3 flex items-center gap-3 shadow-2xl" style={{ background: 'rgba(18,18,24,.95)', backdropFilter: 'blur(16px)' }}>
        <div className={`w-2 h-2 rounded-full flex-shrink-0 animate-pulse ${item.event === 'continue' ? 'bg-violet-400' : item.event === 'share' ? 'bg-blue-400' : 'bg-emerald-400'}`} />
        <p className="text-xs text-[#A0A0B2] flex-1">
          User {item.location ? `in ${item.location} ` : ''}<span className="text-white font-medium">{labels[item.event] || item.event}</span> "{item.story_title}"
        </p>
        <button onClick={() => setVisible(false)} className="text-white/20 hover:text-white/60 text-xs">x</button>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   LOADING SKELETON
   ═══════════════════════════════════════════════════════════════════ */
function DashboardSkeleton() {
  return (
    <div className="min-h-screen" style={{ background: BG }} data-testid="dashboard-skeleton">
      <div className="w-full" style={{ height: '72vh', minHeight: '420px', background: 'linear-gradient(135deg, #1a1a2e, #0B0B0F)' }}>
        <div className="h-full flex flex-col justify-end p-10" style={{ maxWidth: '40%', minWidth: '320px' }}>
          <div className="w-20 h-4 bg-white/10 rounded mb-3 animate-pulse" />
          <div className="w-72 h-9 bg-white/10 rounded mb-2 animate-pulse" />
          <div className="w-56 h-5 bg-white/5 rounded mb-5 animate-pulse" />
          <div className="flex gap-3"><div className="w-36 h-11 bg-white/10 rounded-xl animate-pulse" /><div className="w-28 h-11 bg-white/5 rounded-xl animate-pulse" /></div>
        </div>
      </div>
      <div className="px-10 -mt-6 relative z-20 grid grid-cols-4 gap-4">
        {[1,2,3,4].map(i => <div key={i} className="rounded-xl animate-pulse" style={{ height: 80, background: CARD_BG }} />)}
      </div>
      {[1,2,3,4].map(r => (
        <div key={r} className="px-10" style={{ paddingTop: 32 }}>
          <div className="w-28 h-4 bg-white/10 rounded mb-3 animate-pulse" />
          <div className="flex gap-4">{[1,2,3,4,5].map(c => <div key={c} className="rounded-xl animate-pulse flex-shrink-0" style={{ width: 220, height: 300, background: 'rgba(255,255,255,.03)' }} />)}</div>
        </div>
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   MAIN DASHBOARD
   Hero → Metrics → Story Rows → Features → Footer
   ═══════════════════════════════════════════════════════════════════ */
export default function Dashboard() {
  const navigate = useNavigate();
  const { credits, creditsLoaded, refreshCredits } = useCredits();
  const [feed, setFeed] = useState(null);
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState({});
  const [liveFeed, setLiveFeed] = useState([]);
  const isAdmin = isAdminUser();

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
        // Preload hero image
        const heroUrl = feedRes.data.featured_story?.thumbnail_url;
        if (heroUrl) { const img = new Image(); img.src = mediaUrl(heroUrl); }
      } catch (e) {
        console.error('[Dashboard] Feed load failed:', e.message);
        setFeed({ featured_story: null, trending_stories: [], fresh_stories: [], continue_stories: [], unfinished_worlds: [], live_stats: {} });
      }
      setLoading(false);
    };
    load();
  }, []);

  if (loading) return <DashboardSkeleton />;

  const { featured_story, trending_stories = [], fresh_stories = [], continue_stories = [], unfinished_worlds = [], live_stats = {} } = feed || {};
  const isLoggedIn = !!localStorage.getItem('token');
  const heroPool = [featured_story, ...trending_stories.filter(s => s?.job_id !== featured_story?.job_id)].filter(Boolean).slice(0, 5);

  const trendingRow = trending_stories.length > 0 ? trending_stories : SEED_CARDS;
  const freshRow = fresh_stories.length > 0 ? fresh_stories : [...SEED_CARDS].reverse();
  const continueRow = continue_stories.length > 0 ? continue_stories : SEED_CARDS.slice(0, 4).map(s => ({ ...s, badge: 'CONTINUE' }));
  const unfinishedRow = unfinished_worlds.length > 0 ? unfinished_worlds : SEED_CARDS;

  return (
    <div className="min-h-screen" style={{ background: BG }} data-testid="dashboard">

      {/* ADMIN BAR */}
      {isAdmin && (
        <div className="fixed top-0 left-0 right-0 z-50 border-b border-indigo-500/20" style={{ background: 'rgba(11,11,15,.95)', backdropFilter: 'blur(12px)' }} data-testid="admin-top-bar">
          <div className="flex items-center justify-between px-4 sm:px-8 py-2">
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
      <div className={isAdmin ? 'pt-10' : ''}>
        <HeroSection stories={heroPool} navigate={navigate} />
      </div>

      {/* 2. METRICS STRIP */}
      <MetricsStrip metrics={metrics} />

      {/* 3. STORY ROWS — Netflix-style, all 4 always render */}
      <ScrollRow title="Trending Now" icon={Flame} iconColor="text-amber-400" testId="trending-now">
        {trendingRow.map((story, idx) => <StoryCard key={story.job_id || `t-${idx}`} story={story} idx={idx} navigate={navigate} priority={idx < 4} />)}
      </ScrollRow>

      <ScrollRow title="Fresh Stories" icon={Sparkles} iconColor="text-violet-400" testId="fresh-stories">
        {freshRow.map((story, idx) => <StoryCard key={`f-${story.job_id || idx}`} story={story} idx={idx + 20} navigate={navigate} priority={idx < 4} />)}
      </ScrollRow>

      <ScrollRow title="Continue Your Story" icon={RefreshCw} iconColor="text-blue-400" testId="continue-stories">
        {continueRow.map((story, idx) => <StoryCard key={`c-${story.job_id || idx}`} story={story} idx={idx + 40} navigate={navigate} />)}
      </ScrollRow>

      <ScrollRow title="Unfinished Worlds" icon={Clock} iconColor="text-emerald-400" testId="unfinished-worlds">
        {unfinishedRow.map((story, idx) => <StoryCard key={`u-${story.job_id || idx}`} story={story} idx={idx + 60} navigate={navigate} />)}
      </ScrollRow>

      {/* 6. FEATURE TOOLS */}
      <FeaturesGrid navigate={navigate} />

      {/* FOOTER */}
      <div className="border-t border-white/[0.04]">
        <div className="flex items-center justify-between px-6 sm:px-10 lg:px-14 py-4">
          <div className="flex items-center gap-5 text-xs text-[#A0A0B2]">
            <span className="flex items-center gap-1.5 font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" /> {live_stats.total_stories || 0} stories
            </span>
            <span className="flex items-center gap-1.5" data-testid="credits-display">
              <Zap className="w-3.5 h-3.5" style={{ color: '#6C5CE7' }} />
              {!isLoggedIn ? (
                <button onClick={() => navigate('/login')} className="flex items-center gap-1 font-bold hover:text-white transition-colors" style={{ color: '#6C5CE7' }} data-testid="credits-login-cta">
                  <LogIn className="w-3 h-3" /> Sign in to create
                </button>
              ) : !creditsLoaded ? (
                <span className="inline-block w-10 h-3 bg-white/10 rounded animate-pulse" data-testid="credits-skeleton" />
              ) : (
                <span className="text-white/50 font-bold" data-testid="credits-value">{credits >= 999999 ? 'Unlimited' : `${credits} credits`}</span>
              )}
            </span>
          </div>
        </div>
      </div>

      {/* 7. REAL-TIME ACTIVITY BAR */}
      <ActivityBar feed={liveFeed} />

      <style>{`.scrollbar-hide::-webkit-scrollbar{display:none}.scrollbar-hide{-ms-overflow-style:none;scrollbar-width:none}`}</style>
    </div>
  );
}
