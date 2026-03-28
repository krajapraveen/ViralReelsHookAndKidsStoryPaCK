import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCredits } from '../contexts/CreditContext';
import axios from 'axios';
import { SafeImage } from '../components/SafeImage';
import {
  Play, ChevronRight, ChevronLeft, Sparkles, Zap,
  Flame, Clock, ArrowRight, Search, Plus, Volume2, VolumeX,
  Film, BookOpen, Wand2, Star
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

/* ── Hook text bank — ensures every card has tension ── */
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

/* ── Hero Background with image + gradient fallback ── */
function HeroBg({ url, title }) {
  const [imgOk, setImgOk] = useState(false);
  const hash = (title || '').split('').reduce((a, c) => a + c.charCodeAt(0), 0);
  const bgs = [
    'from-violet-900 via-indigo-900 to-slate-950',
    'from-rose-900 via-purple-900 to-slate-950',
    'from-emerald-900 via-teal-900 to-slate-950',
    'from-amber-900 via-orange-900 to-slate-950',
    'from-cyan-900 via-blue-900 to-slate-950',
  ];
  const bg = bgs[hash % bgs.length];

  return (
    <div className="absolute inset-0">
      {/* Animated gradient background — always present */}
      <div className={`absolute inset-0 bg-gradient-to-br ${bg}`} style={{ animation: 'heroShimmer 8s ease-in-out infinite alternate' }} />
      {/* Subtle animated particles */}
      <div className="absolute inset-0" style={{ background: 'radial-gradient(circle at 20% 50%, rgba(139,92,246,0.1) 0%, transparent 50%), radial-gradient(circle at 80% 30%, rgba(236,72,153,0.08) 0%, transparent 50%)', animation: 'heroDrift 10s ease-in-out infinite alternate' }} />
      {/* Try to load actual image on top */}
      {url && (
        <img
          src={url}
          alt=""
          className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-700 ${imgOk ? 'opacity-100' : 'opacity-0'}`}
          style={{ filter: 'brightness(0.55) saturate(1.2)' }}
          onLoad={() => setImgOk(true)}
          onError={() => setImgOk(false)}
        />
      )}
      <style>{`
        @keyframes heroShimmer { 0% { opacity: 0.7; } 100% { opacity: 1; } }
        @keyframes heroDrift { 0% { transform: translateX(0) scale(1); } 100% { transform: translateX(-20px) scale(1.05); } }
      `}</style>
    </div>
  );
}

function getHook(story, idx) {
  if (story.hook_text && story.hook_text.length > 20) return story.hook_text;
  if (story.story_text && story.story_text.length > 20) {
    const sentences = story.story_text.split(/[.!?]+/).filter(s => s.trim().length > 10);
    if (sentences.length > 0) return sentences[0].trim() + '...';
  }
  return HOOK_BANK[idx % HOOK_BANK.length];
}

function getBadge(story, idx) {
  if (idx === 0) return { text: 'TRENDING', color: 'bg-amber-500 text-black' };
  if (story.continuations > 0) return { text: 'CONTINUING', color: 'bg-emerald-500 text-black' };
  if (idx < 4) return { text: 'HOT', color: 'bg-rose-500 text-white' };
  return { text: 'NEW', color: 'bg-violet-500 text-white' };
}

/* ═══════════════════════════════════════════════════════
   HERO SECTION — Full-width autoplay video / thumbnail
   ═══════════════════════════════════════════════════════ */
function HeroSection({ stories, navigate }) {
  const [activeIdx, setActiveIdx] = useState(0);
  const [isMuted, setIsMuted] = useState(true);
  const videoRef = useRef(null);
  const timerRef = useRef(null);

  const heroStories = stories.filter(s => s.thumbnail_url).slice(0, 5);
  const current = heroStories[activeIdx] || {};

  useEffect(() => {
    if (heroStories.length <= 1) return;
    timerRef.current = setInterval(() => {
      setActiveIdx(prev => (prev + 1) % heroStories.length);
    }, 8000);
    return () => clearInterval(timerRef.current);
  }, [heroStories.length]);

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.play().catch(() => {});
    }
  }, [activeIdx]);

  const goTo = (idx) => {
    clearInterval(timerRef.current);
    setActiveIdx(idx);
    timerRef.current = setInterval(() => {
      setActiveIdx(prev => (prev + 1) % heroStories.length);
    }, 8000);
  };

  if (!heroStories.length) return null;

  const hookText = getHook(current, activeIdx);

  return (
    <section className="relative w-full" style={{ height: '65vh', minHeight: '420px' }} data-testid="hero-section">
      {/* Background media */}
      <div className="absolute inset-0 overflow-hidden">
        {current.output_url || current.preview_url ? (
          <video
            ref={videoRef}
            key={current.job_id}
            src={current.preview_url || current.output_url}
            muted={isMuted}
            autoPlay
            loop
            playsInline
            className="absolute inset-0 w-full h-full object-cover"
            style={{ filter: 'brightness(0.5)' }}
          />
        ) : (
          <HeroBg url={current.thumbnail_url} title={current.title} />
        )}
      </div>

      {/* Gradient overlays */}
      <div className="absolute inset-0 bg-gradient-to-r from-black/90 via-black/50 to-transparent" />
      <div className="absolute inset-0 bg-gradient-to-t from-[#0a0a0f] via-transparent to-transparent" />

      {/* Content overlay */}
      <div className="relative h-full flex flex-col justify-end px-6 sm:px-10 lg:px-16 pb-16 max-w-3xl">
        <div className="animate-[fadeInUp_0.6s_ease-out]">
          <div className="flex items-center gap-2 mb-3">
            <span className="bg-rose-600 text-white text-[10px] font-black tracking-wider px-2 py-0.5 rounded">
              FEATURED
            </span>
            {current.animation_style && (
              <span className="bg-white/10 backdrop-blur-sm text-white/70 text-[10px] font-bold px-2 py-0.5 rounded">
                {current.animation_style.replace(/_/g, ' ').toUpperCase()}
              </span>
            )}
          </div>

          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black text-white leading-tight mb-3 drop-shadow-lg" data-testid="hero-title">
            {current.title || 'Untitled Story'}
          </h1>

          <p className="text-base sm:text-lg text-white/80 leading-relaxed mb-6 max-w-xl line-clamp-2 italic" data-testid="hero-hook">
            "{hookText}"
          </p>

          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/app/story-video-studio', { state: { continueJob: current.job_id } })}
              className="flex items-center gap-2 px-6 py-3 bg-white text-black font-bold rounded-lg text-sm hover:bg-white/90 transition-all shadow-lg shadow-white/10"
              data-testid="hero-continue-btn"
            >
              <Play className="w-4 h-4 fill-black" /> Continue Story
            </button>
            <button
              onClick={() => navigate('/app/story-video-studio')}
              className="flex items-center gap-2 px-6 py-3 bg-white/10 backdrop-blur-sm text-white font-bold rounded-lg text-sm hover:bg-white/20 transition-all border border-white/10"
              data-testid="hero-create-btn"
            >
              <Sparkles className="w-4 h-4" /> Create Your Own
            </button>
            {(current.output_url || current.preview_url) && (
              <button
                onClick={() => setIsMuted(!isMuted)}
                className="w-10 h-10 flex items-center justify-center rounded-full bg-white/10 backdrop-blur-sm border border-white/10 text-white hover:bg-white/20 transition-all"
                data-testid="hero-mute-btn"
              >
                {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Carousel dots */}
      {heroStories.length > 1 && (
        <div className="absolute bottom-6 right-6 sm:right-10 lg:right-16 flex items-center gap-1.5" data-testid="hero-dots">
          {heroStories.map((_, i) => (
            <button key={i} onClick={() => goTo(i)}
              className={`h-1 rounded-full transition-all duration-500 ${i === activeIdx ? 'w-8 bg-white' : 'w-3 bg-white/30 hover:bg-white/50'}`}
              data-testid={`hero-dot-${i}`}
            />
          ))}
        </div>
      )}

      <style>{`
        @keyframes fadeInUp { from { opacity:0; transform:translateY(20px); } to { opacity:1; transform:translateY(0); } }
      `}</style>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════
   STORY CARD — Netflix 4:5 card with hover effects
   ═══════════════════════════════════════════════════════ */
function StoryCard({ story, idx, navigate, size = 'md' }) {
  const [isHovered, setIsHovered] = useState(false);
  const hook = getHook(story, idx);
  const badge = getBadge(story, idx);

  const sizeClasses = {
    sm: 'w-36 sm:w-40',
    md: 'w-44 sm:w-52',
    lg: 'w-52 sm:w-60',
  };

  return (
    <div
      className={`${sizeClasses[size]} flex-shrink-0 group relative rounded-2xl overflow-hidden cursor-pointer select-none`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={() => navigate('/app/story-video-studio', { state: { continueJob: story.job_id } })}
      data-testid={`story-card-${idx}`}
      style={{ transition: 'transform 0.3s ease, box-shadow 0.3s ease', transform: isHovered ? 'scale(1.05)' : 'scale(1)', boxShadow: isHovered ? '0 16px 40px rgba(0,0,0,0.5)' : 'none' }}
    >
      <div className="relative aspect-[4/5] overflow-hidden bg-slate-900">
        {/* Thumbnail / Video preview */}
        <div className="absolute inset-0" style={{ transition: 'filter 0.3s', filter: isHovered ? 'brightness(1.15)' : 'brightness(0.85)' }}>
          {isHovered && (story.preview_url || story.output_url) ? (
            <video
              src={story.preview_url || story.output_url}
              muted autoPlay loop playsInline
              className="w-full h-full object-cover"
            />
          ) : (
            <SafeImage
              src={story.thumbnail_url}
              alt={story.title}
              aspectRatio="4/5"
              fallbackType="gradient"
              titleOverlay={story.title}
              className="w-full h-full"
              imgClassName="w-full h-full object-cover"
            />
          )}
        </div>

        {/* Gradient */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent pointer-events-none" />

        {/* Badge */}
        <div className="absolute top-2.5 left-2.5">
          <span className={`${badge.color} text-[9px] font-black tracking-wider px-2 py-0.5 rounded-md`}>
            {badge.text}
          </span>
        </div>

        {/* Hover play icon */}
        <div className={`absolute inset-0 flex items-center justify-center transition-opacity duration-300 ${isHovered ? 'opacity-100' : 'opacity-0'}`}>
          <div className="w-12 h-12 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center border border-white/20">
            <Play className="w-5 h-5 text-white fill-white ml-0.5" />
          </div>
        </div>

        {/* Bottom content */}
        <div className="absolute bottom-0 left-0 right-0 p-3">
          <h3 className="text-xs font-bold text-white leading-tight mb-1 line-clamp-1">{story.title || 'Untitled'}</h3>
          <p className="text-[10px] text-white/70 leading-snug line-clamp-2 italic mb-2">"{hook}"</p>
          <div
            className={`flex items-center gap-1.5 text-[10px] font-bold transition-all duration-300 ${isHovered ? 'text-white translate-x-1' : 'text-white/50'}`}
          >
            <Play className="w-2.5 h-2.5 fill-current" />
            Continue Story <ChevronRight className="w-2.5 h-2.5" />
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   HORIZONTAL SCROLL ROW — With nav arrows
   ═══════════════════════════════════════════════════════ */
function ScrollRow({ title, icon: Icon, iconColor, children, seeAllAction, testId }) {
  const scrollRef = useRef(null);
  const [showLeft, setShowLeft] = useState(false);
  const [showRight, setShowRight] = useState(true);

  const checkScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    setShowLeft(el.scrollLeft > 20);
    setShowRight(el.scrollLeft < el.scrollWidth - el.clientWidth - 20);
  }, []);

  const scroll = (dir) => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollBy({ left: dir * el.clientWidth * 0.7, behavior: 'smooth' });
    setTimeout(checkScroll, 400);
  };

  useEffect(() => { checkScroll(); }, [checkScroll, children]);

  return (
    <section className="relative py-3" data-testid={testId}>
      <div className="flex items-center justify-between px-6 sm:px-10 lg:px-16 mb-3">
        <h2 className="flex items-center gap-2 text-base sm:text-lg font-black text-white">
          {Icon && <Icon className={`w-5 h-5 ${iconColor || 'text-white'}`} />}
          {title}
        </h2>
        {seeAllAction && (
          <button onClick={seeAllAction} className="flex items-center gap-1 text-xs text-white/40 hover:text-white/70 font-semibold transition-colors" data-testid={`${testId}-see-all`}>
            See All <ChevronRight className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      <div className="relative group/row">
        {/* Left arrow */}
        {showLeft && (
          <button onClick={() => scroll(-1)}
            className="absolute left-1 top-1/2 -translate-y-1/2 z-10 w-10 h-10 bg-black/70 backdrop-blur-sm rounded-full flex items-center justify-center text-white opacity-0 group-hover/row:opacity-100 transition-opacity border border-white/10 hover:bg-black/90"
            data-testid={`${testId}-scroll-left`}>
            <ChevronLeft className="w-5 h-5" />
          </button>
        )}

        {/* Scroll container */}
        <div
          ref={scrollRef}
          onScroll={checkScroll}
          className="flex gap-3 overflow-x-auto px-6 sm:px-10 lg:px-16 pb-2 scrollbar-hide"
          style={{ scrollSnapType: 'x mandatory', scrollbarWidth: 'none', msOverflowStyle: 'none' }}
        >
          {children}
        </div>

        {/* Right arrow */}
        {showRight && (
          <button onClick={() => scroll(1)}
            className="absolute right-1 top-1/2 -translate-y-1/2 z-10 w-10 h-10 bg-black/70 backdrop-blur-sm rounded-full flex items-center justify-center text-white opacity-0 group-hover/row:opacity-100 transition-opacity border border-white/10 hover:bg-black/90"
            data-testid={`${testId}-scroll-right`}>
            <ChevronRight className="w-5 h-5" />
          </button>
        )}

        {/* Fade edges */}
        <div className="absolute top-0 left-0 bottom-0 w-12 bg-gradient-to-r from-[#0a0a0f] to-transparent pointer-events-none" />
        <div className="absolute top-0 right-0 bottom-0 w-12 bg-gradient-to-l from-[#0a0a0f] to-transparent pointer-events-none" />
      </div>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════
   SCROLL HOOK — Tension between sections
   ═══════════════════════════════════════════════════════ */
function ScrollHook({ text }) {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) setVisible(true);
    }, { threshold: 0.5 });
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={ref} className="py-10 text-center" data-testid="scroll-hook">
      <p className={`text-lg sm:text-xl font-bold bg-gradient-to-r from-rose-400 via-violet-400 to-amber-400 bg-clip-text text-transparent transition-all duration-1000 ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
        {text}
      </p>
      <div className={`flex justify-center gap-1 mt-3 transition-all duration-1000 delay-300 ${visible ? 'opacity-100' : 'opacity-0'}`}>
        <span className="w-1.5 h-1.5 rounded-full bg-rose-400 animate-pulse" />
        <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" style={{ animationDelay: '0.2s' }} />
        <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" style={{ animationDelay: '0.4s' }} />
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   CREATE PROMPT — Compact inline prompt
   ═══════════════════════════════════════════════════════ */
function CreatePrompt({ navigate }) {
  const [prompt, setPrompt] = useState('');

  const go = () => {
    navigate('/app/story-video-studio', { state: { prefill: prompt || undefined } });
  };

  return (
    <section className="px-6 sm:px-10 lg:px-16 py-6" data-testid="create-prompt">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-3 bg-white/[0.04] border border-white/[0.08] rounded-2xl px-4 py-3 focus-within:border-violet-500/40 transition-colors">
          <Search className="w-5 h-5 text-white/30 flex-shrink-0" />
          <input
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && go()}
            placeholder="Type a story idea... A fox in a dark forest, a robot learning emotions..."
            className="flex-1 bg-transparent text-white text-sm placeholder-white/30 outline-none"
            data-testid="create-prompt-input"
          />
          <button onClick={go}
            className="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-rose-600 to-violet-600 text-white text-xs font-bold rounded-lg hover:opacity-90 transition-opacity flex-shrink-0"
            data-testid="create-prompt-btn">
            <Sparkles className="w-3.5 h-3.5" /> Create
          </button>
        </div>
        <div className="flex flex-wrap gap-2 mt-2.5 justify-center">
          {['A brave fox...', 'The door opened...', 'She trusted him...', 'The robot refused...'].map(chip => (
            <button key={chip} onClick={() => { setPrompt(chip); }}
              className="px-3 py-1 bg-white/[0.04] border border-white/[0.06] rounded-full text-[11px] text-white/40 hover:text-white/70 hover:border-white/15 transition-all"
              data-testid={`chip-${chip.slice(0,8)}`}>
              {chip}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════
   QUICK TOOLS — Compact row, not the main focus
   ═══════════════════════════════════════════════════════ */
function QuickTools({ navigate }) {
  const tools = [
    { name: 'Story Video', icon: Film, path: '/app/story-video-studio', color: 'text-violet-400' },
    { name: 'Reels', icon: Play, path: '/app/reels', color: 'text-rose-400' },
    { name: 'Comic Book', icon: BookOpen, path: '/app/comic-storybook', color: 'text-cyan-400' },
    { name: 'Bedtime Story', icon: Star, path: '/app/bedtime-stories', color: 'text-amber-400' },
    { name: 'Caption AI', icon: Wand2, path: '/app/caption-rewriter', color: 'text-emerald-400' },
  ];

  return (
    <section className="px-6 sm:px-10 lg:px-16 py-4" data-testid="quick-tools">
      <div className="flex items-center gap-3 overflow-x-auto scrollbar-hide pb-1">
        <span className="text-[10px] font-bold text-white/20 uppercase tracking-wider flex-shrink-0">Tools</span>
        {tools.map(t => (
          <button key={t.name} onClick={() => navigate(t.path)}
            className="flex items-center gap-2 px-4 py-2 bg-white/[0.03] border border-white/[0.06] rounded-xl text-xs font-semibold text-white/50 hover:text-white hover:bg-white/[0.06] hover:border-white/[0.12] transition-all flex-shrink-0"
            data-testid={`tool-${t.name.replace(/\s/g,'-').toLowerCase()}`}>
            <t.icon className={`w-3.5 h-3.5 ${t.color}`} />
            {t.name}
          </button>
        ))}
      </div>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════
   MAIN DASHBOARD — Netflix-style story platform
   ═══════════════════════════════════════════════════════ */
export default function Dashboard() {
  const navigate = useNavigate();
  const { credits } = useCredits();
  const [feed, setFeed] = useState({ hero: null, trending: [], characters: [], live_stats: {} });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
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

  const { trending, hero, live_stats } = feed;

  // Build sections from data
  const heroStories = [hero, ...trending.filter(s => s.job_id !== hero?.job_id)].filter(Boolean).filter(s => s.thumbnail_url);
  const trendingStories = trending.filter(s => s.thumbnail_url);
  const continueStories = trending.filter(s => s.continuations > 0 || s.output_url).slice(0, 8);
  const newStories = trending.filter(s => !s.continuations).slice(0, 8);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-white/40">Loading your stories...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f]" data-testid="dashboard">
      {/* Hero — Full width autoplay */}
      <HeroSection stories={heroStories} navigate={navigate} />

      {/* Create prompt — subtle */}
      <CreatePrompt navigate={navigate} />

      {/* Continue Watching / Active Stories */}
      {continueStories.length > 0 && (
        <ScrollRow
          title="Continue Watching"
          icon={Play}
          iconColor="text-emerald-400"
          testId="continue-watching"
        >
          {continueStories.map((story, idx) => (
            <StoryCard key={story.job_id || idx} story={story} idx={idx} navigate={navigate} size="md" />
          ))}
        </ScrollRow>
      )}

      {/* Trending Now */}
      {trendingStories.length > 0 && (
        <ScrollRow
          title="Trending Now"
          icon={Flame}
          iconColor="text-amber-400"
          seeAllAction={() => navigate('/app/explore')}
          testId="trending-now"
        >
          {trendingStories.map((story, idx) => (
            <StoryCard key={story.job_id || idx} story={story} idx={idx} navigate={navigate} size="lg" />
          ))}
        </ScrollRow>
      )}

      {/* Scroll hook */}
      <ScrollHook text="You won't believe what happens next..." />

      {/* Just Dropped / New Stories */}
      {newStories.length > 0 && (
        <ScrollRow
          title="Just Dropped"
          icon={Sparkles}
          iconColor="text-violet-400"
          testId="just-dropped"
        >
          {newStories.map((story, idx) => (
            <StoryCard key={story.job_id || idx} story={story} idx={idx + 10} navigate={navigate} size="md" />
          ))}
        </ScrollRow>
      )}

      {/* Live pulse */}
      <div className="px-6 sm:px-10 lg:px-16 py-4">
        <div className="flex items-center justify-center gap-6 text-xs text-white/30">
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            {live_stats.total_stories || 0} stories created
          </span>
          <span className="flex items-center gap-1.5">
            <Clock className="w-3 h-3" />
            Stories ready in minutes
          </span>
          <span className="flex items-center gap-1.5">
            <Zap className="w-3 h-3 text-violet-400" />
            {credits === null ? <span className="inline-block w-8 h-3 bg-white/10 rounded animate-pulse" /> : credits >= 999999 ? 'Unlimited' : credits} credits
          </span>
        </div>
      </div>

      {/* Quick tools — compact, bottom */}
      <QuickTools navigate={navigate} />

      {/* Bottom gradient fade */}
      <div className="h-20" />

      {/* Hide scrollbar globally for this page */}
      <style>{`
        .scrollbar-hide::-webkit-scrollbar { display: none; }
        .scrollbar-hide { -ms-overflow-style: none; scrollbar-width: none; }
      `}</style>
    </div>
  );
}
