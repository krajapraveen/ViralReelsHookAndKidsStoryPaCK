import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { useCredits } from '../contexts/CreditContext';
import { useFeedback } from '../contexts/FeedbackContext';
import axios from 'axios';
import { toast } from 'sonner';
import { trackLoop } from '../utils/growthTracker';
import { trackFunnel } from '../utils/funnelTracker';
import { useActionGuide } from '../utils/ActionGuide';
import { setCdnBase } from '../utils/mediaUrl';
import { safeMediaUrl } from '../components/SafeImage';
import { sendFeedEvent, fetchMoreStories, updateScrollSpeed, getDynamicHookDelay, wasSkippedFast } from '../utils/feedTracker';
import { startSession, endSession, trackAction } from '../utils/sessionTracker';
import ReviewModal from '../components/ReviewModal';
import {
  Play, ChevronRight, ChevronLeft, Sparkles, Zap,
  Flame, Clock, Search, Plus,
  Film, BookOpen, Star, ArrowRight, Shield, User,
  Camera, Palette, Megaphone, Lightbulb, Image as ImageIcon,
  RefreshCw, Share2, Activity, Home, Heart, LogOut, CreditCard,
  Eye, Trophy, Award, TrendingUp, Users, Swords,
} from 'lucide-react';

import HeroMedia from '../components/HeroMedia';
import StoryCardMedia from '../components/StoryCardMedia';
import MediaPreloader from '../components/MediaPreloader';
import WarBanner from '../components/WarBanner';
import PersonalAlertStrip from '../components/PersonalAlertStrip';
import TrendingPublicFeed from '../components/TrendingPublicFeed';
import YourCreationsStrip from '../components/YourCreationsStrip';
import HottestBattle from '../components/HottestBattle';
import StreakBadge from '../components/StreakBadge';
import LiveBattleHero from '../components/LiveBattleHero';
import QuickActions from '../components/QuickActions';
import MomentumSection from '../components/MomentumSection';

import heroFallback from '../assets/fallbacks/hero-fallback.jpg';
import cardFallback from '../assets/fallbacks/card-fallback.jpg';

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
  "She opened the door... and saw herself inside.",
  "This message appeared at 2:13 AM — then his phone died.",
  "He pressed play... and the video showed tomorrow.",
  "The mirror showed someone else staring back.",
  "They said the forest was empty. They were wrong.",
  "The clock struck thirteen.",
  "She recognized the voice... but he'd been dead for years.",
  "The letter was written in her handwriting. She never wrote it.",
  "He woke up in a room with no doors. The walls were breathing.",
  "The last photo on her phone was taken 3 days from now.",
];

const SEED_CARDS = [
  { job_id: 'seed-1', title: 'A Midnight Train to Nowhere', hook_text: "The station was empty... except for the girl with no shadow.", is_seed: true, badge: 'UNFINISHED', animation_style: 'watercolor', media: null },
  { job_id: 'seed-2', title: "The Last Dragon's Secret", hook_text: "She found the egg under the floorboards. It was warm.", is_seed: true, badge: 'UNFINISHED', animation_style: 'anime', media: null },
  { job_id: 'seed-3', title: 'Echoes in the Library', hook_text: "The book opened itself to page 47. It was blank yesterday.", is_seed: true, badge: 'UNFINISHED', animation_style: 'cartoon_2d', media: null },
  { job_id: 'seed-4', title: "The Clockmaker's Daughter", hook_text: "Every clock in town stopped at 3:33 AM.", is_seed: true, badge: 'UNFINISHED', animation_style: 'cinematic', media: null },
  { job_id: 'seed-5', title: 'Whispers Under the Ice', hook_text: "Something was moving beneath the frozen lake.", is_seed: true, badge: 'UNFINISHED', animation_style: 'watercolor', media: null },
  { job_id: 'seed-6', title: 'The Map That Bleeds', hook_text: "The old map showed a country that doesn't exist.", is_seed: true, badge: 'UNFINISHED', animation_style: 'anime', media: null },
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

/* ═══════════════════════════════════════════════════════════════════
   RESOLVE MEDIA — Convert API proxy paths to absolute URLs
   ═══════════════════════════════════════════════════════════════════ */
function resolveMedia(rawMedia) {
  if (!rawMedia) return null;
  return {
    thumb_blur: rawMedia.thumb_blur || null,
    thumbnail_small_url: rawMedia.thumbnail_small_url || null,
    poster_large_url: rawMedia.poster_large_url || null,
    preview_short_url: rawMedia.preview_short_url || null,
    media_version: rawMedia.media_version || null,
  };
}

/* ═══════════════════════════════════════════════════════════════════
   SHIMMER — replaces all spinners
   ═══════════════════════════════════════════════════════════════════ */
function Shimmer({ w, h, rounded = 'rounded-xl', className = '' }) {
  return (
    <div className={`${rounded} ${className} relative overflow-hidden bg-white/[0.08] flex-shrink-0`}
      style={{ width: w, height: h }}>
      <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/10 to-transparent animate-[shimmer_1.6s_infinite]" />
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   1. HERO — Uses HeroMedia component for deterministic media
      Dashboard handles carousel, CTAs, dots, pause-on-hover.
   ═══════════════════════════════════════════════════════════════════ */
function HeroSection({ stories, navigate }) {
  const [activeIdx, setActiveIdx] = useState(0);
  const [paused, setPaused] = useState(false);
  const timerRef = useRef(null);

  // P0 Action Guides — first-time onboarding for the 4 hero CTAs.
  const battleGuide = useActionGuide('battle');
  const remixGuide = useActionGuide('remix');
  const videoGuide = useActionGuide('story_video');
  // (remixGuide is consumed by FeaturedWinnerHero; kept here so the hook
  // suite is consistent — useful when we later wire a remix CTA on this hero.)
  void remixGuide;

  const heroStories = stories.length > 0 ? stories.slice(0, 5) : [];
  const current = heroStories[activeIdx] || {};
  const hasHero = heroStories.length > 0;
  const media = resolveMedia(current.media);

  const startTimer = useCallback(() => {
    clearInterval(timerRef.current);
    if (heroStories.length <= 1) return;
    timerRef.current = setInterval(() => setActiveIdx(prev => (prev + 1) % heroStories.length), 8000);
  }, [heroStories.length]);

  useEffect(() => { if (!paused) startTimer(); return () => clearInterval(timerRef.current); }, [paused, startTimer]);

  const goTo = (idx) => { clearInterval(timerRef.current); setActiveIdx(idx); startTimer(); };

  return (
    <section className="relative w-full h-[58vh] sm:h-[64vh] lg:h-[72vh] overflow-hidden rounded-none bg-[#0B0B0F]"
      onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)} data-testid="hero-section">

      {/* HeroMedia — handles media rendering per contract (poster, blur, fallback) */}
      <div className="absolute inset-0">
        <HeroMedia
          key={`hero-${activeIdx}`}
          title={null}
          media={media}
          jobId={current.job_id}
          eager={true}
          enablePreview={true}
          fallbackImageUrl={heroFallback}
        />
      </div>

      {/* Content — title, hook, CTAs per visual contract */}
      <div className="absolute inset-x-0 bottom-0 z-10 px-4 pb-6 sm:px-6 sm:pb-8 lg:px-10 lg:pb-10"
        style={{ animation: 'fadeUp .5s ease-out' }}>
        {hasHero ? (
          <>
            <div className="mb-3 flex items-center gap-2 flex-wrap">
              <span className="inline-flex items-center rounded-full bg-white/15 backdrop-blur-md text-white text-[10px] sm:text-xs font-semibold px-3 py-1 border border-white/20"
                data-testid="hero-featured-badge">FEATURED</span>
            </div>
            <h1 className="max-w-3xl text-white font-extrabold tracking-tight text-2xl sm:text-4xl lg:text-5xl leading-tight drop-shadow-[0_2px_12px_rgba(0,0,0,0.45)]" data-testid="hero-title">
              {current.title || 'Untitled Story'}
            </h1>
            <p className="mt-3 max-w-2xl text-white/85 text-sm sm:text-base lg:text-lg leading-relaxed pointer-events-none" data-testid="hero-hook">
              "{getHook(current, activeIdx)}"
            </p>
            <div className="mt-5 flex flex-wrap items-center gap-3 relative z-20">
              <button onClick={() => {
                if (!current.job_id || current.is_seed) {
                  navigate('/app/story-video-studio', {
                    state: { prefill: { title: current.title || '', prompt: current.hook_text || '', animation_style: current.animation_style || '' }, freshSession: true },
                  });
                  return;
                }
                trackLoop('click', { story_id: current.job_id, story_title: current.title, source_surface: 'hero' });
                trackFunnel('cta_clicked', { meta: { type: 'watch_now', source: 'hero', story_id: current.job_id } });
                if (current.hook_variant_id) { axios.post(`${API}/api/engagement/hook-event`, { job_id: current.job_id, hook_variant_id: current.hook_variant_id, event_type: 'continue' }).catch(() => {}); }
                navigate(`/app/story-viewer/${current.job_id}`);
              }}
                className="inline-flex items-center justify-center rounded-xl px-5 py-3 text-sm sm:text-base font-bold text-white bg-gradient-to-r from-[#6C5CE7] to-[#00C2FF] shadow-[0_0_24px_rgba(0,194,255,0.28)] hover:scale-[1.02] transition-transform duration-200"
                data-testid="hero-play-btn"
                data-guide="continue-story">
                <Play className="w-4 h-4 fill-white mr-2" /> Watch Now
              </button>
              <button onClick={() => {
                const run = () => {
                  if (!current.job_id || current.is_seed) { navigate('/app/story-video-studio', { state: { freshSession: true } }); return; }
                  trackFunnel('cta_clicked', { meta: { type: 'enter_battle', source: 'hero', story_id: current.job_id } });
                  navigate('/app/story-video-studio', {
                    state: {
                      prompt: current.story_text || current.hook_text || '',
                      remixFrom: { title: current.title, job_id: current.job_id },
                      source_surface: 'hero_remix',
                      isRemix: true,
                    },
                  });
                };
                battleGuide.runWithGuide(run);
              }}
                className="inline-flex items-center justify-center rounded-xl px-5 py-3 text-sm sm:text-base font-semibold text-white bg-white/10 backdrop-blur-md border border-white/15 hover:bg-white/15 transition-colors duration-200"
                data-testid="hero-remix-btn">
                <Swords className="w-4 h-4 mr-2" /> Enter Battle
                <span className="ml-2 text-[10px] font-bold uppercase tracking-widest text-rose-300/90 bg-rose-500/15 px-1.5 py-0.5 rounded">Best for reach</span>
              </button>
              <button onClick={() => {
                const run = () => {
                  trackFunnel('cta_clicked', { meta: { type: 'create_later', source: 'hero' } });
                  navigate('/app/story-video-studio', { state: { freshSession: true } });
                };
                videoGuide.runWithGuide(run);
              }}
                className="inline-flex items-center justify-center rounded-xl px-4 py-2.5 text-xs text-white/50 hover:text-white/70 transition-colors duration-200"
                data-testid="hero-create-btn">
                <Plus className="w-3.5 h-3.5 mr-1" /> Create Later
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="mb-3 flex items-center gap-2">
              <span className="inline-flex items-center rounded-full bg-white/15 backdrop-blur-md text-white text-[10px] sm:text-xs font-semibold px-3 py-1 border border-white/20">UNFINISHED</span>
            </div>
            <h1 className="max-w-3xl text-white font-extrabold tracking-tight text-2xl sm:text-4xl lg:text-5xl leading-tight drop-shadow-[0_2px_12px_rgba(0,0,0,0.45)]" data-testid="hero-title">Every Story is Waiting for You</h1>
            <p className="mt-3 max-w-2xl text-white/85 text-sm sm:text-base leading-relaxed">Worlds half-built. Characters mid-sentence. Pick any story and decide what happens next.</p>
            <div className="mt-5">
              <button onClick={() => {
                videoGuide.runWithGuide(() => navigate('/app/story-video-studio', { state: { freshSession: true } }));
              }}
                className="inline-flex items-center justify-center rounded-xl px-5 py-3 text-sm sm:text-base font-bold text-white bg-gradient-to-r from-[#6C5CE7] to-[#00C2FF] shadow-[0_0_24px_rgba(0,194,255,0.28)] hover:scale-[1.02] transition-transform duration-200"
                data-testid="hero-create-btn">
                <Play className="w-4 h-4 fill-white mr-2" /> Start a Story
              </button>
            </div>
          </>
        )}
      </div>

      {/* Dots */}
      {heroStories.length > 1 && (
        <div className="absolute bottom-3 sm:bottom-5 right-5 sm:right-8 flex items-center gap-1.5 z-[5]" data-testid="hero-dots">
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
    <div className="px-4 py-5 sm:px-6 lg:px-10" data-testid="metrics-strip">
      <div className="flex gap-3 overflow-x-auto no-scrollbar">
        {items.map(m => (
          <div key={m.label} className="min-w-[140px] sm:min-w-[180px] rounded-2xl bg-[#121218] border border-white/[0.08] px-4 py-4 shadow-[0_8px_30px_rgba(0,0,0,0.18)]">
            <div className="flex items-center gap-1.5">
              <m.icon className="w-3.5 h-3.5" style={{ color: m.color }} />
              <span className="text-[11px] uppercase tracking-[0.14em] text-white/50 font-semibold whitespace-nowrap">{m.label}</span>
            </div>
            <p className="mt-2 text-white text-xl sm:text-2xl font-bold font-mono">{m.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   3. STORY CARD — Uses StoryCardMedia for deterministic media
      Dashboard handles badge, hook, click tracking, navigation.
   ═══════════════════════════════════════════════════════════════════ */
function StoryCard({ story, idx, navigate, priority = false }) {
  const cardRef = useRef(null);
  const impressionFired = useRef(false);
  const visibleSince = useRef(null);

  const hook = getHook(story, idx);
  const badge = story.badge || 'NEW';
  const media = resolveMedia(story.media);

  useEffect(() => {
    const el = cardRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        visibleSince.current = Date.now();
        if (!impressionFired.current) {
          impressionFired.current = true;
          trackLoop('impression', { story_id: story.job_id, story_title: story.title, hook_variant: story.hook_text, category: story.category, source_surface: story.badge || 'dashboard' });
          if (story.job_id && story.hook_variant_id) {
            axios.post(`${API}/api/engagement/hook-event`, { job_id: story.job_id, hook_variant_id: story.hook_variant_id, event_type: 'impression' }).catch(() => {});
          }
        }
      } else if (visibleSince.current) {
        const visMs = Date.now() - visibleSince.current;
        if (wasSkippedFast(visMs)) {
          sendFeedEvent('skip_fast', { jobId: story.job_id, category: story.animation_style });
        }
        visibleSince.current = null;
      }
    }, { threshold: 0.5 });
    obs.observe(el);
    return () => obs.disconnect();
  }, [story]);

  const handleClick = () => {
    trackAction();
    trackLoop('click', { story_id: story.job_id, story_title: story.title, hook_variant: story.hook_text, category: story.category, source_surface: story.badge || 'dashboard' });
    sendFeedEvent('click', { jobId: story.job_id, category: story.animation_style, hookText: story.hook_text });
    if (story.job_id && story.hook_variant_id) {
      axios.post(`${API}/api/engagement/hook-event`, { job_id: story.job_id, hook_variant_id: story.hook_variant_id, event_type: 'continue' }).catch(() => {});
    }

    // Phase 0: Track story_card_clicked
    trackFunnel('story_card_clicked', { meta: { badge, story_id: story.job_id, story_title: story.title } });

    // CONSUMPTION-FIRST: ALL cards → Watch Page (unless seed/no real content)
    if (story.job_id && !story.is_seed) {
      navigate(`/app/story-viewer/${story.job_id}`);
    } else {
      // Seed cards → Studio (creation mode, no content to watch)
      navigate('/app/story-video-studio', {
        state: {
          prefill: {
            title: story.title || '', prompt: story.hook_text || story.story_prompt || '',
            hook_text: story.hook_text || '', animation_style: story.animation_style || '',
            parent_video_id: null,
            source_surface: 'dashboard',
          },
          freshSession: true,
        },
      });
    }
  };

  // CTA text — Watch-first hierarchy
  let ctaLabel = 'Watch Now';
  if (badge === 'CONTINUE') ctaLabel = 'Continue watching';
  else if (badge === 'UNFINISHED') ctaLabel = 'Watch Story';
  else if (badge === 'FRESH') ctaLabel = 'Watch Now';

  return (
    <div ref={cardRef} className="group relative shrink-0 cursor-pointer w-[160px] h-[220px] sm:w-[200px] sm:h-[280px] lg:w-[220px] lg:h-[300px] rounded-2xl overflow-hidden bg-[#121218] border border-white/[0.08] shadow-[0_10px_32px_rgba(0,0,0,0.18)] hover:scale-[1.03] hover:shadow-[0_16px_40px_rgba(0,0,0,0.28)] transition-all duration-200"
      style={{ scrollSnapAlign: 'start' }}
      onClick={handleClick} data-testid={`story-card-${idx}`}>

      {/* StoryCardMedia — deterministic media per contract + autoplay */}
      <StoryCardMedia
        title={null}
        media={media}
        jobId={story.job_id}
        eager={priority}
        enablePreviewOnHover={true}
        enablePreviewOnVisible={true}
        fallbackImageUrl={cardFallback}
        className="absolute inset-0 w-full h-full rounded-none"
      />

      {/* Card overlay */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/15 to-transparent pointer-events-none" />

      {/* Badge */}
      <div className="absolute top-2.5 left-2.5 z-[3]">
        <span className="mb-2 inline-flex items-center rounded-full bg-black/35 backdrop-blur-md text-white text-[10px] font-semibold px-2.5 py-1 border border-white/15">{badge}</span>
      </div>

      {/* Play button on hover */}
      <div className="absolute inset-0 flex items-center justify-center transition-opacity duration-200 z-[3] opacity-0 group-hover:opacity-100 pointer-events-none">
        <div className="w-11 h-11 lg:w-14 lg:h-14 rounded-full flex items-center justify-center border border-white/20" style={{ background: 'rgba(255,255,255,.15)', backdropFilter: 'blur(8px)' }}>
          <Play className="w-4 h-4 lg:w-5 lg:h-5 text-white fill-white ml-0.5" />
        </div>
      </div>

      {/* Content */}
      <div className="absolute inset-x-0 bottom-0 z-[3] p-3 sm:p-4">
        <h3 className="text-white text-sm sm:text-base font-bold leading-snug line-clamp-2 drop-shadow-[0_2px_10px_rgba(0,0,0,0.45)]">{story.title || 'Untitled'}</h3>
        <p className="mt-1 text-white/80 text-[12px] sm:text-sm leading-snug line-clamp-2">"{hook}"</p>
        {/* Social proof — views + competition */}
        <div className="mt-1.5 flex items-center gap-2 text-[10px] text-white/40">
          {(story.total_views || 0) > 0 && (
            <span className="flex items-center gap-0.5"><Eye className="w-2.5 h-2.5" />{story.total_views > 1000 ? `${(story.total_views / 1000).toFixed(1)}K` : story.total_views}</span>
          )}
          {(story.total_children || 0) > 0 && (
            <span className="flex items-center gap-0.5"><Users className="w-2.5 h-2.5" />{story.total_children} competing</span>
          )}
        </div>
        <div className="mt-2 inline-flex items-center text-white text-xs sm:text-sm font-semibold">
          <Play className="w-2.5 h-2.5 lg:w-3 lg:h-3 fill-current mr-1" />
          {ctaLabel}
          <ArrowRight className="w-2.5 h-2.5 lg:w-3 lg:h-3 ml-1" />
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   SCROLL ROW — horizontal, lazy loaded, progressive reveal
   ═══════════════════════════════════════════════════════════════════ */
function ScrollRow({ title, subtitle, icon: Icon, iconColor, children, testId, delay = 0, eager = false }) {
  const scrollRef = useRef(null);
  const sectionRef = useRef(null);
  const [showLeft, setShowLeft] = useState(false);
  const [showRight, setShowRight] = useState(true);
  const [visible, setVisible] = useState(eager);

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
    <section ref={sectionRef} className="px-4 py-4 sm:px-6 lg:px-10" data-testid={testId}
      style={{ animationDelay: `${delay}ms` }}>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-white text-xl sm:text-2xl font-bold tracking-tight">
          {Icon && <Icon className={`w-4 h-4 sm:w-5 sm:h-5 ${iconColor || 'text-white/60'}`} />}
          {title}
        </h2>
        {subtitle && <span className="text-[10px] text-white/25 ml-1">{subtitle}</span>}
        <button onClick={() => scroll(1)} className="text-white/70 text-sm font-medium hover:text-white transition-colors flex items-center gap-1">
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
          className="flex gap-4 overflow-x-auto no-scrollbar pb-1"
          style={{ scrollSnapType: 'x mandatory' }}>
          {visible ? children : (
            <div className="flex gap-4">
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
   5. FEATURE BLOCKS — Rendered in API-determined order (personalized)
   ═══════════════════════════════════════════════════════════════════ */
const ICON_MAP = {
  Film, BookOpen, User, Play, Camera, Palette, Star, ImageIcon, Megaphone, Lightbulb,
};

// REGRESSION GUARD: Static default feature list — NEVER let features section be empty
const DEFAULT_FEATURES = [
  { name: 'My Movie Trailer', desc: 'Upload photos → 20-60s personalized AI trailer', icon: 'Camera', path: '/app/photo-trailer', key: 'photo-trailer', gradient: 'from-violet-500 to-fuchsia-700', score: 100, badge: 'NEW' },
  { name: 'Story Video', desc: 'Turn ideas into cinematic stories', icon: 'Film', path: '/app/story-video-studio', key: 'story-video-studio', gradient: 'from-indigo-500 to-blue-700', score: 0 },
  { name: 'Story Series', desc: 'Multi-episode sagas with memory', icon: 'BookOpen', path: '/app/story-series', key: 'story-series', gradient: 'from-purple-500 to-fuchsia-700', score: 0 },
  { name: 'Character Memory', desc: 'Persistent characters across stories', icon: 'User', path: '/app/characters', key: 'characters', gradient: 'from-cyan-500 to-blue-700', score: 0 },
  { name: 'Reel Generator', desc: 'Viral short-form video reels', icon: 'Play', path: '/app/reels', key: 'reels', gradient: 'from-rose-500 to-pink-700', score: 0 },
  { name: 'Photo to Comic', desc: 'Transform photos into comic panels', icon: 'Camera', path: '/app/photo-to-comic', key: 'photo-to-comic', gradient: 'from-amber-500 to-orange-700', score: 0 },
  { name: 'Comic Storybook', desc: 'Panel-by-panel illustrated stories', icon: 'Palette', path: '/app/comic-storybook', key: 'comic-storybook', gradient: 'from-emerald-500 to-green-700', score: 0 },
  { name: 'Bedtime Stories', desc: 'Narrated sleep tales with visuals', icon: 'Star', path: '/app/bedtime-stories', key: 'bedtime-stories', gradient: 'from-indigo-500 to-purple-700', score: 0 },
  { name: 'Reaction GIF', desc: 'Photo-to-reaction GIF in seconds', icon: 'ImageIcon', path: '/app/gif-maker', key: 'gif-maker', gradient: 'from-pink-500 to-rose-700', score: 0 },
  { name: 'Brand Story', desc: 'Cinematic brand narratives', icon: 'Megaphone', path: '/app/brand-story-builder', key: 'brand-story-builder', gradient: 'from-teal-500 to-cyan-700', score: 0 },
  { name: 'Daily Viral Ideas', desc: 'AI-generated trending prompts', icon: 'Lightbulb', path: '/app/daily-viral-ideas', key: 'daily-viral-ideas', gradient: 'from-amber-500 to-red-700', score: 0 },
];

// REGRESSION GUARD: Default rows when API returns empty
const DEFAULT_ROWS = [
  { key: 'trending_now', title: 'Trending Now', icon: 'Flame', icon_color: 'text-amber-400', stories: SEED_CARDS.map(s => ({ ...s, badge: 'TRENDING' })) },
  { key: 'fresh_stories', title: 'Fresh Stories', icon: 'Sparkles', icon_color: 'text-violet-400', stories: [...SEED_CARDS].reverse().map(s => ({ ...s, badge: 'FRESH' })) },
  { key: 'unfinished_worlds', title: 'Unfinished Worlds', icon: 'Clock', icon_color: 'text-emerald-400', stories: SEED_CARDS.slice(0, 4) },
];

function FeaturesGrid({ features, navigate }) {
  return (
    <section className="px-4 py-8 sm:px-6 lg:px-10" data-testid="features-grid">
      <h2 className="flex items-center gap-2 text-white text-xl sm:text-2xl font-bold tracking-tight mb-4 sm:mb-5">
        <Zap className="w-4 h-4 sm:w-5 sm:h-5 text-amber-400" /> Creator Tools
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {features.map(f => {
          const Icon = ICON_MAP[f.icon] || Zap;
          return (
            <button key={f.key} onClick={() => navigate(f.path, { state: { freshSession: true } })}
              className="group rounded-2xl border border-white/[0.08] bg-[#121218] p-5 shadow-[0_8px_24px_rgba(0,0,0,0.16)] hover:border-white/15 hover:shadow-[0_12px_30px_rgba(0,0,0,0.24)] transition-all duration-200 text-left"
              data-testid={`feature-${f.key}`}>
              <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-[#6C5CE7]/25 to-[#00C2FF]/25 text-white text-xl border border-white/10 group-hover:scale-110 transition-transform">
                <Icon className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
              </div>
              <h3 className="text-white text-lg font-bold tracking-tight flex items-center gap-2">{f.name}{f.badge && <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-300 border border-violet-500/30">{f.badge}</span>}</h3>
              <p className="mt-2 text-white/70 text-sm leading-relaxed line-clamp-1">{f.desc}</p>
              <span className="mt-4 inline-flex items-center text-white text-sm font-semibold group-hover:text-white transition-colors">
                Continue <ArrowRight className="w-3 h-3 ml-1" />
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   6. REAL-TIME ACTIVITY BAR
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
      <div className="rounded-2xl border border-white/[0.08] bg-[#121218] px-4 py-3 flex items-center gap-3 overflow-hidden shadow-2xl" style={{ backdropFilter: 'blur(16px)' }}>
        <div className="h-2.5 w-2.5 rounded-full bg-[#00C2FF] animate-pulse flex-shrink-0" />
        <p className="text-white/80 text-sm flex-1 line-clamp-1 whitespace-nowrap">
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
    <nav className="fixed bottom-0 inset-x-0 z-40 lg:hidden border-t border-white/10 bg-[#0B0B0F]/95 backdrop-blur-lg"
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
   SHIMMER SKELETON (loading state)
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
   PERSONALIZED HERO MESSAGE — 3 segments: challenge-heavy, remix-heavy, inactive
   + Viral attribution badge showing weekly remix conversions
   ═══════════════════════════════════════════════════════════════════ */
function PersonalizedHero({ metrics, viralStats, navigate }) {
  // Determine user behavior segment
  const challengeCount = metrics?.challenge_participations || 0;
  const remixConversions = viralStats?.total_remix_conversions || 0;
  const creditsEarned = viralStats?.total_credits_earned || 0;

  let message = null;

  if (challengeCount > 3) {
    message = { text: "Today's challenge awaits your next winning story", icon: Trophy, color: 'text-amber-400', bg: 'bg-amber-500/[0.04]', border: 'border-amber-500/10' };
  } else if (remixConversions > 0) {
    message = { text: "Your stories are getting remixed — create another hit", icon: TrendingUp, color: 'text-emerald-400', bg: 'bg-emerald-500/[0.04]', border: 'border-emerald-500/10' };
  }
  // Don't show for active users with no special segment — avoid noise

  const showViral = remixConversions > 0;

  if (!message && !showViral) return null;

  return (
    <div className="px-4 sm:px-6 lg:px-10 py-1 space-y-2">
      {message && (
        <div className={`flex items-center gap-3 px-4 py-3 rounded-xl ${message.bg} border ${message.border}`} data-testid="personalized-hero-message">
          <message.icon className={`w-4 h-4 ${message.color} flex-shrink-0`} />
          <span className={`text-sm font-medium ${message.color}`}>{message.text}</span>
        </div>
      )}
      {showViral && (
        <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl bg-violet-500/[0.04] border border-violet-500/10" data-testid="viral-attribution-badge">
          <Flame className="w-4 h-4 text-violet-400 flex-shrink-0" />
          <span className="text-sm font-medium text-violet-300">
            Your stories generated <span className="font-bold text-white">{remixConversions}</span> viral remix{remixConversions !== 1 ? 'es' : ''}
            {creditsEarned > 0 && <span className="text-emerald-400 ml-1">(+{creditsEarned} bonus credits earned)</span>}
          </span>
        </div>
      )}
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════════
   FEATURED CHALLENGE WINNER — Prestige Hero Slot
   Must feel aspirational, not like a regular card.
   Graceful fallback when no winner exists.
   ═══════════════════════════════════════════════════════════════════ */
function FeaturedWinnerHero({ winner, navigate }) {  const sectionRef = useRef(null);
  const impressionFired = useRef(false);
  const remixGuide = useActionGuide('remix');

  useEffect(() => {
    const el = sectionRef.current;
    if (!el || !winner) return;
    const obs = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !impressionFired.current) {
        impressionFired.current = true;
        trackLoop('hero_winner_impression', {
          job_id: winner.job_id,
          title: winner.title,
          creator: winner.creator_name,
          reason: winner.reason_badge,
        });
      }
    }, { threshold: 0.3 });
    obs.observe(el);
    return () => obs.disconnect();
  }, [winner]);

  const handleRemix = () => {
    trackLoop('hero_winner_remix_clicked', {
      job_id: winner.job_id,
      title: winner.title,
    });
    // P0 — first-time guide before navigating to studio with remix prefill.
    remixGuide.runWithGuide(() => {
      navigate('/app/story-video-studio', {
        state: { prompt: '', remixFrom: { title: winner.title, job_id: winner.job_id }, source_surface: 'hero_winner' },
      });
    });
  };

  const handleView = () => {
    trackLoop('hero_winner_view_clicked', {
      job_id: winner.job_id,
      title: winner.title,
    });
    navigate(`/app/story-video-studio?projectId=${winner.job_id}`);
  };

  // Graceful fallback: No valid winner
  if (!winner) {
    return (
      <div className="px-4 sm:px-6 lg:px-10 py-2" data-testid="challenge-winner-slot">
        <div className="relative overflow-hidden rounded-2xl border border-amber-500/10 bg-gradient-to-r from-amber-500/[0.03] to-transparent p-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center flex-shrink-0">
              <Trophy className="w-5 h-5 text-amber-500/40" />
            </div>
            <div>
              <p className="text-sm font-semibold text-amber-400/60" data-testid="winner-fallback-text">Today's challenge winner will appear soon</p>
              <p className="text-[11px] text-zinc-600 mt-0.5">Winners are selected from today's challenge entries</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div ref={sectionRef} className="px-4 sm:px-6 lg:px-10 py-2" data-testid="challenge-winner-slot">
      <div className="relative overflow-hidden rounded-2xl border border-amber-500/25 bg-[#121218] shadow-[0_8px_32px_rgba(245,158,11,0.06)]">
        {/* Subtle prestige glow */}
        <div className="absolute -top-20 -right-20 w-56 h-56 bg-amber-500/[0.04] rounded-full blur-3xl pointer-events-none" />

        <div className="flex items-stretch">
          {/* Winner thumbnail — large, prominent */}
          <div className="w-36 sm:w-48 lg:w-56 flex-shrink-0 relative bg-zinc-900/80 overflow-hidden">
            {winner.thumbnail_url ? (
              <img
                src={safeMediaUrl(winner.thumbnail_url)}
                alt={winner.title}
                className="w-full h-full object-cover"
                loading="lazy"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center min-h-[140px] bg-gradient-to-br from-amber-900/20 to-zinc-900">
                <Film className="w-10 h-10 text-amber-500/20" />
              </div>
            )}
            {/* Gradient overlay */}
            <div className="absolute inset-0 bg-gradient-to-r from-transparent to-[#121218]/60 pointer-events-none" />
            {/* Trophy badge overlay */}
            <div className="absolute top-2.5 left-2.5 flex items-center gap-1 px-2 py-1 rounded-lg bg-amber-500/90 backdrop-blur-sm" data-testid="winner-trophy-badge">
              <Trophy className="w-3 h-3 text-white" />
              <span className="text-[9px] font-extrabold text-white uppercase tracking-wider">Winner</span>
            </div>
            {/* Reason badge */}
            <div className="absolute bottom-2 left-2 right-2" data-testid="winner-reason-badge">
              <span className="inline-flex items-center gap-1 text-[9px] font-bold px-2 py-1 rounded-full bg-black/60 backdrop-blur-sm text-amber-300 border border-amber-500/20">
                <Award className="w-2.5 h-2.5" />
                {winner.reason_badge}
              </span>
            </div>
          </div>

          {/* Winner info — prestige layout */}
          <div className="flex-1 p-4 sm:p-5 lg:p-6 flex flex-col justify-center min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <Star className="w-4 h-4 text-amber-400" />
              <span className="text-[10px] font-extrabold uppercase tracking-[0.15em] text-amber-400">Featured Winner</span>
              <span className="text-[10px] text-zinc-600 font-medium">Today's challenge</span>
            </div>

            <h3 className="text-lg sm:text-xl font-bold text-white truncate mb-1.5 leading-tight" data-testid="winner-title">
              {winner.title}
            </h3>

            <div className="flex items-center gap-3 text-xs text-zinc-400 mb-4">
              <span className="font-medium">by <span className="text-zinc-300">{winner.creator_name}</span></span>
              {winner.remix_count > 0 && (
                <span className="flex items-center gap-1">
                  <RefreshCw className="w-2.5 h-2.5" /> {winner.remix_count} remix{winner.remix_count !== 1 ? 'es' : ''}
                </span>
              )}
              {winner.views > 0 && (
                <span className="flex items-center gap-1">
                  <Eye className="w-2.5 h-2.5" /> {winner.views} view{winner.views !== 1 ? 's' : ''}
                </span>
              )}
            </div>

            <div className="flex items-center gap-2.5">
              {/* Primary CTA — Remix */}
              <button
                onClick={handleRemix}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 text-white text-xs sm:text-sm font-bold shadow-[0_0_20px_rgba(245,158,11,0.2)] hover:shadow-[0_0_28px_rgba(245,158,11,0.3)] hover:scale-[1.02] transition-all duration-200"
                data-testid="winner-remix-btn"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Remix This Winner
              </button>
              {/* Secondary CTA — View */}
              <button
                onClick={handleView}
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-white/[0.08] text-zinc-400 text-xs font-medium hover:text-white hover:border-white/15 hover:bg-white/[0.03] transition-all duration-200"
                data-testid="winner-view-btn"
              >
                <Eye className="w-3 h-3" /> View Winning Story
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════════
   MAIN DASHBOARD — Progressive loading, API-driven ordering
   Backend owns ALL ordering — frontend is a DUMB RENDERER.
   Uses: HeroMedia, StoryCardMedia, MediaPreloader per contract
   ═══════════════════════════════════════════════════════════════════ */

// Map backend icon string names to Lucide components
const ROW_ICON_MAP = {
  Flame, RefreshCw, Sparkles, Clock, Zap, Star,
};

export default function Dashboard() {
  const navigate = useNavigate();
  const location = useLocation();
  const { credits, creditsLoaded, refreshCredits } = useCredits();
  const { handleLogoutWithFeedback } = useFeedback();
  const [feed, setFeed] = useState(null);
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState({});
  const [liveFeed, setLiveFeed] = useState([]);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [dailyChallenge, setDailyChallenge] = useState(null);
  const [topStories, setTopStories] = useState([]);
  const [challengeWinner, setChallengeWinner] = useState(null);
  const [personalHero, setPersonalHero] = useState(null);
  const [viralStats, setViralStats] = useState(null);
  const [viralLeaderboard, setViralLeaderboard] = useState([]);
  const isAdmin = isAdminUser();
  const isLoggedIn = !!localStorage.getItem('token');

  // ── Review modal — trigger after value delivery ──
  const [showReview, setShowReview] = useState(false);
  useEffect(() => {
    // Canonical activation funnel — dashboard mount
    try {
      trackFunnel('dashboard_loaded', {
        source_page: 'dashboard',
        meta: { authed: !!localStorage.getItem('token') },
      });
    } catch (_) { /* noop */ }

    // Show review prompt after 2nd visit if user has generations and hasn't reviewed
    const visitCount = parseInt(localStorage.getItem('dashboard_visits') || '0', 10) + 1;
    localStorage.setItem('dashboard_visits', String(visitCount));
    if (visitCount >= 3 && !localStorage.getItem('review_prompted')) {
      // Check if user has reviewed
      import('../utils/api').then(({ default: apiUtil }) => {
        apiUtil.get('/api/reviews/my-review').then(r => {
          if (!r.data?.has_review) {
            setTimeout(() => {
              setShowReview(true);
              localStorage.setItem('review_prompted', 'true');
            }, 8000); // 8s delay for non-intrusive timing
          }
        }).catch(() => {});
      });
    }
  }, []);

  // ── Infinite scroll state ──
  const [extraStories, setExtraStories] = useState([]);
  const [scrollOffset, setScrollOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const sentinelRef = useRef(null);
  const softBreakCounter = useRef(0);

  useEffect(() => {
    refreshCredits();
    const load = async () => {
      try {
        // Single consolidated API call replaces 7 separate calls
        const [feedRes, initRes] = await Promise.all([
          axios.get(`${API}/api/engagement/story-feed`, auth()),
          axios.get(`${API}/api/dashboard/init`, auth()).catch(() => ({ data: {} })),
        ]);
        setFeed(feedRes.data);
        if (feedRes.data.cdn_base) setCdnBase(feedRes.data.cdn_base);

        // Hydrate from consolidated init response
        const init = initRes.data || {};
        if (init.daily_challenge) setDailyChallenge(init.daily_challenge);
        if (init.top_stories?.length) setTopStories(init.top_stories.slice(0, 5));
        if (init.challenge_winner) setChallengeWinner(init.challenge_winner);
        if (init.viral_status) setViralStats(init.viral_status);
        if (init.viral_leaderboard?.length) setViralLeaderboard(init.viral_leaderboard);

        const initialStories = (feedRes.data.rows || []).reduce((acc, r) => acc + (r.stories?.length || 0), 0);
        setScrollOffset(initialStories);
      } catch (e) {
        console.error('[Dashboard] Feed load failed:', e.message);
        setFeed({ hero: null, rows: [], features: [], live_stats: {} });
        toast.error('Failed to load your feed. Try refreshing the page.');
      }
      setLoading(false);
    };
    load();
  }, []);

  // ── Session tracking ──
  useEffect(() => {
    startSession();
    return () => endSession();
  }, []);

  // ── Scroll speed tracking for dynamic hook timing ──
  useEffect(() => {
    const onScroll = () => updateScrollSpeed();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // ── Floating Create CTA: show only after watch or 50% scroll ──
  const [showFloatingCreate, setShowFloatingCreate] = useState(false);
  const scrollDepthTracked = useRef(false);
  useEffect(() => {
    const onScroll = () => {
      const scrollPct = (window.scrollY / (document.documentElement.scrollHeight - window.innerHeight)) * 100;
      if (scrollPct > 50 && !scrollDepthTracked.current) {
        scrollDepthTracked.current = true;
        setShowFloatingCreate(true);
        trackFunnel('scroll_depth_50', {});
      }
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // ── Infinite scroll: IntersectionObserver at 70% scroll ──
  const loadMore = useCallback(async () => {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    const data = await fetchMoreStories(scrollOffset, 12);
    if (data && data.stories && data.stories.length > 0) {
      setExtraStories(prev => [...prev, ...data.stories]);
      setScrollOffset(data.offset || scrollOffset + data.stories.length);
      setHasMore(data.has_more || false);
    } else {
      setHasMore(false);
    }
    setLoadingMore(false);
  }, [scrollOffset, loadingMore, hasMore]);

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) loadMore();
    }, { rootMargin: '400px' });
    obs.observe(el);
    return () => obs.disconnect();
  }, [loadMore]);

  if (loading) return <DashboardSkeleton />;

  // ═══════════════════════════════════════════════════════════════
  // REGRESSION GUARD: Every section has a guaranteed fallback.
  // If API fails, page still renders full content. NEVER empty.
  // ═══════════════════════════════════════════════════════════════
  const rawFeed = feed || {};
  const hero = rawFeed.hero || null;
  const apiRows = Array.isArray(rawFeed.rows) ? rawFeed.rows.filter(r => r && r.key && Array.isArray(r.stories) && r.stories.length > 0) : [];
  const apiFeatures = Array.isArray(rawFeed.features) ? rawFeed.features : [];
  const live_stats = rawFeed.live_stats || {};

  // FALLBACK: If API rows empty, use DEFAULT_ROWS (SEED_CARDS)
  const rows = apiRows.length > 0 ? apiRows : DEFAULT_ROWS;

  // FALLBACK: If API features empty, use DEFAULT_FEATURES
  const featureList = apiFeatures.length > 0 ? apiFeatures : DEFAULT_FEATURES;

  // Hero pool: hero + first trending row stories for carousel
  const firstTrendingRow = rows.find(r => r.key === 'trending_now') || rows.find(r => r.key === 'fresh_stories') || rows[0];
  const heroPool = [
    hero,
    ...(firstTrendingRow?.stories || []).filter(s => s?.job_id !== hero?.job_id),
  ].filter(Boolean).slice(0, 5);
  // FALLBACK: If no hero pool at all, use seed cards
  const safeHeroPool = heroPool.length > 0 ? heroPool : SEED_CARDS.slice(0, 3);

  // First row's stories for preloading
  const firstRow = rows[0] || { stories: [] };

  // MediaPreloader inputs — proxy paths passed, resolved to CDN at render time
  const heroPreloadMedia = (safeHeroPool[0])?.media ? {
    poster_large_url: safeHeroPool[0].media.poster_large_url || null,
  } : null;
  const firstRowPreloadCards = (firstRow.stories || []).slice(0, 4).map(s => ({
    thumbnail_small_url: s?.media?.thumbnail_small_url || null,
  }));

  return (
    <div className="min-h-screen pb-16 lg:pb-0" style={{ background: BG }} data-testid="dashboard">

      {/* MediaPreloader — hero poster + first 4 thumbnails ONLY */}
      <MediaPreloader hero={heroPreloadMedia} firstRowCards={firstRowPreloadCards} />

      {/* ADMIN BAR — desktop only */}
      {isAdmin && (
        <div className="fixed top-0 left-0 right-0 z-[10001] border-b border-indigo-500/30" style={{ background: 'linear-gradient(135deg, rgba(15,15,25,.98), rgba(25,20,50,.98))', backdropFilter: 'blur(16px)' }} data-testid="admin-top-bar">
          <div className="flex items-center justify-between px-4 sm:px-8 py-2.5">
            <Link to="/app/admin" className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-indigo-500/15 border border-indigo-500/30 hover:bg-indigo-500/25 transition-all" data-testid="admin-menu-link">
              <Shield className="w-4 h-4 text-indigo-400" />
              <span className="text-sm font-bold tracking-wide text-indigo-300">Admin Panel</span>
            </Link>
            <div className="flex items-center gap-1 sm:gap-3">
              <Link to="/app/admin/growth" className="px-2.5 py-1 rounded-md text-xs text-slate-400 hover:text-white hover:bg-white/5 font-medium transition-all" data-testid="admin-quick-growth">Growth</Link>
              <Link to="/app/admin/content-engine" className="px-2.5 py-1 rounded-md text-xs text-slate-400 hover:text-white hover:bg-white/5 font-medium transition-all hidden sm:block">Content</Link>
              <Link to="/app/admin/workers" className="px-2.5 py-1 rounded-md text-xs text-slate-400 hover:text-white hover:bg-white/5 font-medium transition-all hidden sm:block">Jobs</Link>
              <Link to="/app/admin/system-health" className="px-2.5 py-1 rounded-md text-xs text-slate-400 hover:text-white hover:bg-white/5 font-medium transition-all">Health</Link>
              <Link to="/app/profile" className="w-8 h-8 rounded-full bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center ml-1">
                <User className="w-4 h-4 text-indigo-400" />
              </Link>
            </div>
          </div>
        </div>
      )}


      {/* ═══ 0. PERSONAL ALERT STRIP — THE RETURN TRIGGER (TOP) ═══ */}
      <PersonalAlertStrip />

      {/* ═══ SECTION 1: LIVE BATTLE HERO — Above the fold, instant engagement ═══ */}
      <div className="px-4 sm:px-6 lg:px-10 py-2">
        <LiveBattleHero />
      </div>

      {/* ═══ SECTION 2: QUICK ACTIONS — Fast entry paths ═══ */}
      <div className="px-4 sm:px-6 lg:px-10 py-2">
        <QuickActions />
      </div>

      {/* ═══ SECTION 2.5: PHOTO TRAILER CTA — P0 NEW FEATURE ═══ */}
      <div className="px-4 sm:px-6 lg:px-10 py-3">
        <button
          onClick={() => navigate('/app/photo-trailer')}
          data-testid="dash-photo-trailer-cta"
          className="group relative w-full overflow-hidden rounded-2xl border border-violet-500/30 bg-gradient-to-r from-violet-600/20 via-fuchsia-600/15 to-rose-600/10 px-5 sm:px-6 py-5 sm:py-6 text-left transition-all duration-200 hover:-translate-y-0.5 hover:border-violet-400/50 hover:shadow-xl hover:shadow-violet-900/30"
        >
          <div className="flex items-center justify-between gap-4 flex-wrap sm:flex-nowrap">
            <div className="flex items-start gap-3 sm:gap-4 flex-1 min-w-0">
              <div className="rounded-xl border border-violet-400/25 bg-violet-500/15 p-2.5 sm:p-3 flex-shrink-0">
                <Camera className="w-5 h-5 sm:w-6 sm:h-6 text-violet-200" />
              </div>
              <div className="min-w-0 flex-1">
                <span className="inline-flex items-center text-[9px] font-bold uppercase tracking-wider bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white px-2 py-0.5 rounded-full shadow-sm mb-1.5">
                  NEW · YouStar
                </span>
                <h3 className="text-base sm:text-lg font-bold text-white leading-tight">My Movie Trailer</h3>
                <p className="text-xs sm:text-sm text-slate-300/90 leading-snug mt-1">
                  Upload your photos → pick a template → generate a 20–60s personalized cinematic AI trailer.
                </p>
              </div>
            </div>
            <span className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-white text-slate-900 text-sm font-bold whitespace-nowrap group-hover:bg-violet-100 transition-colors flex-shrink-0 self-center">
              Try it <ArrowRight className="w-4 h-4" />
            </span>
          </div>
        </button>
      </div>

      {/* ═══ SECTION 3: TRENDING BATTLES — Scroll hook ═══ */}
      <TrendingPublicFeed />

      {/* ═══ SECTION 4: YOUR MOMENTUM — Retention stats ═══ */}
      <div className="px-4 sm:px-6 lg:px-10 py-2">
        <MomentumSection />
      </div>

      {/* ═══ SECTION 5: CREATION STUDIO (moved down) ═══ */}
      <div className={isAdmin ? 'pt-14' : ''}>
        <HeroSection stories={safeHeroPool} navigate={navigate} />
      </div>

      {/* TRACTION BANNER — return-to-inspect trigger */}
      {viralStats && (viralStats.total_remix_conversions > 0 || viralStats.total_credits_earned > 0) && (
        <div className="px-4 sm:px-6 lg:px-10 py-2" data-testid="traction-banner">
          <div className="rounded-xl border border-violet-500/20 bg-violet-500/[0.05] px-4 py-3 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2.5 min-w-0">
              <TrendingUp className="w-4 h-4 text-violet-400 flex-shrink-0" />
              <p className="text-xs text-slate-300 truncate">
                <span className="text-violet-300 font-semibold">Your stories are gaining traction</span>
                {viralStats.total_remix_conversions > 0 && (
                  <span className="text-slate-400"> — {viralStats.total_remix_conversions} {viralStats.total_remix_conversions === 1 ? 'remix' : 'remixes'} so far</span>
                )}
                {viralStats.total_credits_earned > 0 && (
                  <span className="text-emerald-400"> (+{viralStats.total_credits_earned} credits earned)</span>
                )}
              </p>
            </div>
            <Link
              to="/app/my-space"
              className="text-[10px] text-violet-400 hover:text-violet-300 whitespace-nowrap font-medium"
              data-testid="traction-inspect-link"
              onClick={() => trackFunnel('return_to_inspect', { source_page: 'dashboard', meta: { trigger: 'traction_banner', remixes: viralStats.total_remix_conversions, credits_earned: viralStats.total_credits_earned } })}
            >
              View Details <ArrowRight className="w-3 h-3 inline" />
            </Link>
          </div>
        </div>
      )}

      {/* DAILY CHALLENGE BANNER */}
      {dailyChallenge && (
        <div className="px-4 sm:px-6 lg:px-10 py-3" data-testid="daily-challenge-banner">
          <div className="relative overflow-hidden rounded-2xl border border-emerald-500/20 bg-gradient-to-r from-emerald-500/[0.08] to-teal-500/[0.04] p-4 sm:p-5">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-10 h-10 rounded-xl bg-emerald-500/15 flex items-center justify-center flex-shrink-0">
                  <Sparkles className="w-5 h-5 text-emerald-400" />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">Today's Challenge</span>
                    {dailyChallenge.participants > 0 && (
                      <span className="text-[10px] text-emerald-500/70">{dailyChallenge.participants} joined</span>
                    )}
                  </div>
                  <p className="text-sm sm:text-base font-semibold text-white truncate" data-testid="challenge-title">{dailyChallenge.title}</p>
                </div>
              </div>
              <button
                onClick={() => {
                  navigate(`/app/story-video-studio?challenge=${dailyChallenge.challenge_id}`, {
                    state: { prompt: dailyChallenge.prompt_seed, challengeTitle: dailyChallenge.title }
                  });
                }}
                className="flex-shrink-0 flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-sm font-semibold hover:bg-emerald-500/30 transition-colors"
                data-testid="challenge-join-btn"
              >
                Join Challenge <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* FEATURED CHALLENGE WINNER — Prestige Slot */}
      <FeaturedWinnerHero winner={challengeWinner} navigate={navigate} />

      {/* ═══ 2. DAILY STORY WAR — urgency block ═══ */}
      <div className="px-4 sm:px-6 lg:px-10 py-2">
        <WarBanner />
      </div>

      {/* PERSONALIZED HERO + VIRAL ATTRIBUTION */}
      <PersonalizedHero metrics={metrics} viralStats={viralStats} navigate={navigate} />

      {/* 2. METRICS STRIP */}
      <MetricsStrip metrics={metrics} />

      {/* 3. STORY ROWS — Backend-determined order, first row eager */}
      {rows.map((row, rowIdx) => {
        const RowIcon = ROW_ICON_MAP[row.icon] || Zap;
        const stories = row.stories?.length > 0 ? row.stories : SEED_CARDS.map(s => ({ ...s, badge: row.key === 'continue_stories' ? 'CONTINUE' : s.badge }));
        const storyCount = stories.length;
        const totalViews = stories.reduce((sum, s) => sum + (s.total_views || 0), 0);
        const subtitle = totalViews > 0
          ? `${storyCount} stories${totalViews > 100 ? ` · ${totalViews > 1000 ? `${(totalViews / 1000).toFixed(1)}K` : totalViews} views` : ''}`
          : `${storyCount} stories`;
        return (
          <ScrollRow
            key={row.key}
            title={row.title}
            subtitle={subtitle}
            icon={RowIcon}
            iconColor={row.icon_color || 'text-white/60'}
            testId={row.key}
            delay={rowIdx * 100}
            eager={rowIdx < 2}
          >
            {stories.map((story, idx) => (
              <StoryCard
                key={`${row.key}-${story.job_id || idx}`}
                story={story}
                idx={idx + rowIdx * 20}
                navigate={navigate}
                priority={rowIdx === 0 && idx < 6}
              />
            ))}
          </ScrollRow>
        );
      })}

      {/* ═══ 5. YOUR CREATIONS — with rank + movement ═══ */}
      <YourCreationsStrip />

      {/* TOP VIRAL CREATORS LEADERBOARD */}
      {viralLeaderboard.length > 0 && (
        <div className="px-4 sm:px-6 lg:px-10 py-4" data-testid="viral-leaderboard">
          <div className="bg-gradient-to-br from-violet-500/[0.04] to-rose-500/[0.04] border border-white/[0.06] rounded-2xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <Share2 className="w-4 h-4 text-violet-400" />
              <h3 className="text-sm font-bold text-white">Top Viral Creators This Week</h3>
            </div>
            <div className="space-y-2">
              {viralLeaderboard.map((entry, i) => (
                <div key={entry.user_id} className="flex items-center gap-3 px-3 py-2 rounded-xl bg-white/[0.02]" data-testid={`viral-leader-${i}`}>
                  <span className={`text-sm font-extrabold w-6 text-center ${i === 0 ? 'text-amber-400' : i === 1 ? 'text-slate-300' : i === 2 ? 'text-amber-600' : 'text-slate-500'}`}>
                    {i + 1}
                  </span>
                  <div className="w-7 h-7 rounded-full bg-gradient-to-br from-violet-500 to-rose-500 flex items-center justify-center flex-shrink-0">
                    {entry.picture ? (
                      <img src={entry.picture} alt="" className="w-full h-full rounded-full object-cover" />
                    ) : (
                      <User className="w-3.5 h-3.5 text-white" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="text-xs font-semibold text-white truncate block">{entry.name}</span>
                    <span className="text-[10px] text-slate-500">{entry.referred_remixes} remixes inspired</span>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-bold text-violet-400">{entry.viral_score}</span>
                    <span className="text-[9px] text-slate-600 block">score</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── INFINITE SCROLL: Extra rows loaded on demand ── */}
      {extraStories.length > 0 && (() => {
        // Group extra stories into rows of 12, with soft breaks every 12 items
        const chunks = [];
        for (let i = 0; i < extraStories.length; i += 12) {
          chunks.push(extraStories.slice(i, i + 12));
        }
        softBreakCounter.current = 0;
        return chunks.map((chunk, chunkIdx) => {
          softBreakCounter.current += chunk.length;
          const showSoftBreak = softBreakCounter.current >= 12 && chunkIdx < chunks.length - 1;
          return (
            <React.Fragment key={`extra-${chunkIdx}`}>
              <ScrollRow
                title={chunkIdx === 0 ? "Discover More" : `More Stories`}
                icon={Sparkles}
                iconColor="text-purple-400"
                testId={`infinite-row-${chunkIdx}`}
                delay={0}
                eager={false}
              >
                {chunk.map((story, idx) => (
                  <StoryCard
                    key={`extra-${chunkIdx}-${story.job_id || idx}`}
                    story={story}
                    idx={900 + chunkIdx * 20 + idx}
                    navigate={navigate}
                    priority={false}
                  />
                ))}
              </ScrollRow>
              {showSoftBreak && (
                <div className="px-4 py-6 sm:px-6 lg:px-10" data-testid={`soft-break-${chunkIdx}`}>
                  <div className="rounded-2xl border border-white/[0.06] bg-[#121218] px-6 py-5 flex items-center justify-between">
                    <div>
                      <p className="text-white/80 text-sm font-semibold">Try something different?</p>
                      <p className="text-white/40 text-xs mt-1">Switch it up — explore a new style or genre</p>
                    </div>
                    <button
                      onClick={() => navigate('/app/story-video-studio', { state: { freshSession: true } })}
                      className="shrink-0 px-4 py-2 rounded-xl text-xs font-bold text-white border border-white/10 hover:bg-white/5 transition-colors"
                      data-testid={`soft-break-cta-${chunkIdx}`}
                    >
                      Create New
                    </button>
                  </div>
                </div>
              )}
            </React.Fragment>
          );
        });
      })()}

      {/* Infinite scroll sentinel — triggers load at 70% scroll depth */}
      {hasMore && (
        <div ref={sentinelRef} className="h-4" data-testid="infinite-scroll-sentinel" />
      )}
      {loadingMore && (
        <div className="flex justify-center py-6" data-testid="loading-more">
          <div className="w-6 h-6 border-2 border-white/20 border-t-white/70 rounded-full animate-spin" />
        </div>
      )}

      {/* 4. FEATURE BLOCKS — API-determined order */}
      <FeaturesGrid features={featureList} navigate={navigate} />

      {/* 5. TOP STORIES LEADERBOARD */}
      {topStories.length > 0 && (
        <div className="px-4 sm:px-6 lg:px-10 py-4" data-testid="top-stories-leaderboard">
          <div className="rounded-2xl border border-white/[0.06] bg-[#121218] overflow-hidden">
            <div className="px-5 py-3.5 border-b border-white/[0.04] flex items-center gap-2">
              <Star className="w-4 h-4 text-amber-400" />
              <span className="text-sm font-bold text-white">Top Stories Today</span>
              <span className="text-[10px] text-white/30 ml-auto">This week</span>
            </div>
            <div className="divide-y divide-white/[0.03]">
              {topStories.map((story, idx) => (
                <div
                  key={story.job_id}
                  className="flex items-center gap-3 px-5 py-3 hover:bg-white/[0.02] cursor-pointer transition-colors"
                  onClick={() => navigate(`/app/story-viewer/${story.job_id}`)}
                  data-testid={`top-story-${idx}`}
                >
                  <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                    idx === 0 ? 'bg-amber-500/20 text-amber-400' : idx === 1 ? 'bg-slate-400/15 text-slate-400' : idx === 2 ? 'bg-orange-500/15 text-orange-400' : 'bg-white/5 text-white/40'
                  }`}>
                    {idx + 1}
                  </span>
                  {story.thumbnail_url ? (
                    <img src={safeMediaUrl(story.thumbnail_url)} alt="" className="w-10 h-10 rounded-lg object-cover flex-shrink-0" />
                  ) : (
                    <div className="w-10 h-10 rounded-lg bg-white/5 flex items-center justify-center flex-shrink-0"><Film className="w-4 h-4 text-white/20" /></div>
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{story.title}</p>
                    <p className="text-[10px] text-white/30">{story.animation_style?.replace(/_/g, ' ')}</p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <span className="text-xs text-white/50">{story.views || 0} views</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

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

      {/* 5. ACTIVITY BAR */}
      <ActivityBar feed={liveFeed} />

      {/* ═══ FLOATING CREATE CTA — delayed, conditional ═══ */}
      {showFloatingCreate && (
        <button
          onClick={() => {
            trackFunnel('create_clicked', { meta: { source: 'floating_cta' } });
            navigate('/app/story-video-studio', { state: { freshSession: true } });
          }}
          className="fixed bottom-24 lg:bottom-8 right-4 sm:right-6 z-30 flex items-center gap-2 px-4 py-3 rounded-full bg-gradient-to-r from-[#6C5CE7] to-[#00C2FF] text-white text-sm font-bold shadow-[0_4px_20px_rgba(108,92,231,0.4)] hover:scale-105 transition-all duration-200 animate-in fade-in slide-in-from-bottom-4"
          data-testid="floating-create-cta"
        >
          <Zap className="w-4 h-4" /> Create Story
        </button>
      )}

      {/* 6. STICKY BOTTOM NAV — mobile only */}
      <StickyBottomNav navigate={navigate} currentPath={location.pathname} />

      {/* Global styles — visual contract */}
      <style>{`
        .no-scrollbar::-webkit-scrollbar{display:none}
        .no-scrollbar{-ms-overflow-style:none;scrollbar-width:none}
        @keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
        @keyframes shimmer{100%{transform:translateX(200%)}}
        .safe-bottom{padding-bottom:env(safe-area-inset-bottom,0)}
      `}</style>
      <ReviewModal open={showReview} onClose={() => setShowReview(false)} sourceEvent="dashboard_visit" />
    </div>
  );
}
