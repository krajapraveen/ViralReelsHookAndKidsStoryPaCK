import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Play, ArrowRight, Menu, X, Eye, RefreshCcw, Zap, Command,
  ChevronRight, Sparkles, Film, BookOpen, Users, GitBranch, Clock, Activity
} from 'lucide-react';
import axios from 'axios';
import { getStaticCardImg, getAllStaticBanners } from '../data/staticBanners';
import { trackFunnel } from '../utils/funnelTracker';
import FounderAuthorityBlock from '../components/FounderAuthorityBlock';

const API = process.env.REACT_APP_BACKEND_URL;

// ─── A/B TEST HERO VARIANTS ─────────────────────────────────────────────────
// Week 1: A (Control - Emotional) vs B (Challenger - Prestige)
// Only headline text changes. Layout, font, CTA, colors stay identical.

function _timeAgo(dateStr) {
  if (!dateStr) return '';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

// Hardcoded variant data — only headline/badge/subtitle differ
const HERO_VARIANTS = {
  headline_a: {
    badge: 'Stories that stay with them',
    heading: ['Create stories kids will', 'remember forever'],
    subtitle: 'Create cinematic videos, reels, and stories with AI — no editing, no experience needed. Free to start.',
  },
  headline_b: {
    badge: 'No editing. No experience needed.',
    heading: ['Create award-worthy', 'AI stories in minutes'],
    subtitle: 'Type a sentence. AI creates scenes, voiceover, and music. Download or share instantly.',
  },
};

// Detect traffic source from referrer
function _detectTrafficSource() {
  const ref = document.referrer || '';
  if (!ref) return 'direct';
  if (ref.includes('instagram.com')) return 'instagram';
  if (ref.includes('google.') || ref.includes('bing.') || ref.includes('duckduckgo.')) return 'organic';
  if (ref.includes(window.location.hostname)) return 'internal';
  return 'referral';
}

// Get or create a sticky session ID for anonymous A/B tracking
function _getSessionId() {
  let sid = localStorage.getItem('ab_session_id');
  if (!sid) {
    sid = 'ses_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem('ab_session_id', sid);
  }
  return sid;
}

// ─── STORY HOOK TEMPLATES (rotate for variety) ──────────────────────────────
const STORY_HOOKS = [
  { prompt: 'A fox who saved the forest… but something followed him home', category: 'Adventure' },
  { prompt: 'She opened the old music box — and heard her grandmother\'s voice', category: 'Emotional' },
  { prompt: 'The robot woke up. It wasn\'t supposed to have feelings.', category: 'Sci-Fi' },
  { prompt: 'He found a door in the garden wall that wasn\'t there yesterday', category: 'Mystery' },
  { prompt: 'The last dragon in the kingdom trusted the wrong knight', category: 'Fantasy' },
  { prompt: 'Two best friends made a promise under the stars. Only one kept it.', category: 'Drama' },
];

export default function Landing() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [stats, setStats] = useState(null);
  const [liveFeed, setLiveFeed] = useState([]);
  const [aliveSignals, setAliveSignals] = useState(null);
  const [featuredStory, setFeaturedStory] = useState(null);
  const navigate = useNavigate();
  const showcaseRef = useRef(null);

  // Showcase = 100% static bundled data. ZERO API dependency for images.
  const showcase = getAllStaticBanners();

  // A/B variant — Sticky assignment via backend deterministic hash
  const sessionId = _getSessionId();
  const trafficSource = _detectTrafficSource();
  const [heroVariant, setHeroVariant] = useState(() => {
    // Use cached variant if available (instant render, no flash)
    const cached = localStorage.getItem('ab_hero_variant_id');
    if (cached && HERO_VARIANTS[cached]) return cached;
    return 'headline_a'; // Default to control until backend responds
  });
  const hero = HERO_VARIANTS[heroVariant];

  useEffect(() => {
    // 1. Try smart headline route first (uses source-specific winner if confident)
    const source = trafficSource;
    axios.get(`${API}/api/ab/smart-route?experiment_id=hero_headline&traffic_source=${source}`)
      .then(r => {
        const vid = r.data?.variant_id;
        const reason = r.data?.reason;
        if (vid && HERO_VARIANTS[vid] && reason === 'source_winner') {
          // Use source-specific winner
          setHeroVariant(vid);
          localStorage.setItem('ab_hero_variant_id', vid);
          axios.post(`${API}/api/public/ab-impression`, {
            variant: vid, action: 'ab_variant_assigned', session_id: sessionId,
            traffic_source: source, experiment_id: 'hero_headline',
          }).catch(() => {});
          return;
        }
        // 2. Fallback: use standard sticky assignment
        return axios.post(`${API}/api/ab/assign`, {
          session_id: sessionId, experiment_id: 'hero_headline',
        });
      })
      .then(r => {
        if (r?.data?.variant_id) {
          const vid = r.data.variant_id;
          if (HERO_VARIANTS[vid]) {
            setHeroVariant(vid);
            localStorage.setItem('ab_hero_variant_id', vid);
            axios.post(`${API}/api/public/ab-impression`, {
              variant: vid, action: 'ab_variant_assigned', session_id: sessionId,
              traffic_source: source, experiment_id: 'hero_headline',
            }).catch(() => {});
          }
        }
      })
      .catch(() => {});

    // 3. Fetch public data
    axios.get(`${API}/api/public/stats`).then(r => setStats(r.data)).catch(() => {});
    axios.get(`${API}/api/public/live-activity?limit=6`).then(r => setLiveFeed(r.data.items || [])).catch(() => {});
    axios.get(`${API}/api/public/alive`).then(r => setAliveSignals(r.data)).catch(() => {});
    axios.get(`${API}/api/public/featured-story`).then(r => {
      if (r.data?.found) setFeaturedStory(r.data);
    }).catch(() => {});

    // 4. Track landing funnel event
    trackFunnel('landing_view', { source_page: 'landing' });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Track impression once variant is stable
  useEffect(() => {
    axios.post(`${API}/api/public/ab-impression`, {
      variant: heroVariant,
      action: 'impression',
      session_id: sessionId,
      traffic_source: trafficSource,
      experiment_id: 'hero_headline',
    }).catch(() => {});
    // Also track via the A/B conversion system
    axios.post(`${API}/api/ab/convert`, {
      session_id: sessionId,
      experiment_id: 'hero_headline',
      event: 'impression',
    }).catch(() => {});
  }, [heroVariant]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-refresh live feed
  useEffect(() => {
    const iv = setInterval(() => {
      axios.get(`${API}/api/public/live-activity?limit=6`).then(r => setLiveFeed(r.data.items || [])).catch(() => {});
    }, 8000);
    return () => clearInterval(iv);
  }, []);

  const continueStory = (item) => {
    const data = {
      prompt: item.story_prompt || item.hook_text || item.title || '',
      timestamp: Date.now(),
      source_tool: 'landing-continue',
      remixFrom: {
        tool: 'story-video-studio',
        prompt: item.story_prompt || item.hook_text || item.title,
        title: item.title,
        settings: { animation_style: item.animation_style },
        parentId: item.job_id,
      },
    };
    localStorage.setItem('remix_data', JSON.stringify(data));
    navigate('/experience?source=landing&title=' + encodeURIComponent(item.title || '') + '&snippet=' + encodeURIComponent((item.story_text || '').slice(0, 300)));
  };

  const startFromHook = (hook) => {
    localStorage.setItem('onboarding_prompt', hook.prompt);
    navigate('/experience?source=landing&theme=' + encodeURIComponent(hook.prompt));
  };

  const goCreateFresh = () => {
    trackFunnel('first_action_click', { source_page: 'landing', meta: { action: 'create_fresh' } });
    navigate('/experience?source=landing');
  };

  return (
    <div className="vs-page overflow-x-hidden" data-testid="landing-page">
      <style>{`
        @keyframes fadeUp { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes shimmer { 0% { background-position: -200% 0; } 100% { background-position: 200% 0; } }
        .fade-up { animation: fadeUp 0.6s ease-out both; }
        .fade-up-2 { animation: fadeUp 0.6s ease-out 0.15s both; }
        .fade-up-3 { animation: fadeUp 0.6s ease-out 0.3s both; }
        .fade-up-4 { animation: fadeUp 0.6s ease-out 0.45s both; }
        .showcase-scroll { scroll-behavior: smooth; scrollbar-width: none; }
        .showcase-scroll::-webkit-scrollbar { display: none; }
        .story-card:hover .story-overlay { opacity: 1; }
        .story-card:hover .story-thumb { transform: scale(1.05); }
        .pulse-glow { box-shadow: 0 0 0 0 rgba(139,92,246,0.4); animation: pulseGlow 2s infinite; }
        @keyframes pulseGlow { 0%, 100% { box-shadow: 0 0 0 0 rgba(139,92,246,0.4); } 50% { box-shadow: 0 0 0 12px rgba(139,92,246,0); } }
      `}</style>

      {/* ═══════ NAVBAR ═══════ */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-[#07070f]/80 backdrop-blur-xl border-b border-white/[0.04]" data-testid="landing-nav">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-14">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-rose-500 flex items-center justify-center">
              <Command className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="text-base font-bold tracking-tight text-white">Visionary Suite</span>
          </Link>
          <div className="hidden md:flex items-center gap-5">
            <Link to="/explore" className="text-sm text-slate-400 hover:text-white transition-colors">Explore</Link>
            <Link to="/gallery" className="text-sm text-slate-400 hover:text-white transition-colors">Gallery</Link>
            <Link to="/about" className="text-sm text-slate-400 hover:text-white transition-colors">About</Link>
            <Link to="/pricing" className="text-sm text-slate-400 hover:text-white transition-colors">Pricing</Link>
            <Link to="/login" className="text-sm text-slate-400 hover:text-white transition-colors" data-testid="nav-login-link">Login</Link>
            <button onClick={goCreateFresh} className="h-8 px-4 text-sm font-semibold rounded-lg bg-gradient-to-r from-violet-600 to-rose-600 text-white hover:opacity-90 transition-opacity" data-testid="nav-create-btn">
              Start Creating
            </button>
          </div>
          <button className="md:hidden text-white p-2" onClick={() => setMobileMenuOpen(!mobileMenuOpen)} data-testid="mobile-menu-btn">
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-white/[0.04] bg-[#07070f]/95 backdrop-blur-2xl px-4 py-4 space-y-3">
            <Link to="/explore" className="block text-slate-300 hover:text-white py-2" onClick={() => setMobileMenuOpen(false)}>Explore</Link>
            <Link to="/gallery" className="block text-slate-300 hover:text-white py-2" onClick={() => setMobileMenuOpen(false)}>Gallery</Link>
            <Link to="/about" className="block text-slate-300 hover:text-white py-2" onClick={() => setMobileMenuOpen(false)}>About</Link>
            <Link to="/pricing" className="block text-slate-300 hover:text-white py-2" onClick={() => setMobileMenuOpen(false)}>Pricing</Link>
            <Link to="/login" className="block text-slate-300 hover:text-white py-2" onClick={() => setMobileMenuOpen(false)}>Login</Link>
            <button onClick={() => { setMobileMenuOpen(false); goCreateFresh(); }} className="w-full h-10 text-sm font-semibold rounded-lg bg-gradient-to-r from-violet-600 to-rose-600 text-white">Start Creating</button>
          </div>
        )}
      </nav>

      {/* ═══════ 1. HERO — A/B TESTED ═══════ */}
      <section className="relative pt-24 pb-8 md:pt-32 md:pb-12 px-4" data-testid="hero-section">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-20 left-1/4 w-[600px] h-[600px] bg-violet-600/[0.06] rounded-full blur-[180px]" />
          <div className="absolute bottom-0 right-1/3 w-[400px] h-[400px] bg-rose-500/[0.04] rounded-full blur-[120px]" />
        </div>

        <div className="relative max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-violet-500/10 border border-violet-500/20 text-violet-300 text-xs font-medium mb-6 fade-up" data-testid="hero-badge">
            <Sparkles className="w-3 h-3" /> {hero.badge}
          </div>

          <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-black tracking-[-0.04em] leading-[0.92] mb-5 fade-up" data-testid="hero-heading" data-variant={heroVariant}>
            <span className="text-white">{hero.heading[0]}</span><br />
            <span className="bg-gradient-to-r from-violet-400 via-rose-400 to-amber-400 bg-clip-text text-transparent">{hero.heading[1]}</span>
          </h1>

          <p className="text-lg md:text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed mb-8 fade-up-2" data-testid="hero-subtitle">
            {hero.subtitle}
          </p>

          {/* ─── TWO BIG CTAs ─── */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mb-8 fade-up-3" data-testid="hero-ctas">
            <button
              onClick={() => {
                axios.post(`${API}/api/ab/convert`, { session_id: sessionId, experiment_id: 'hero_headline', event: 'experience_click' }).catch(() => {});
                axios.post(`${API}/api/public/ab-impression`, { variant: heroVariant, action: 'cta_click', session_id: sessionId, traffic_source: trafficSource, experiment_id: 'hero_headline' }).catch(() => {});
                goCreateFresh();
              }}
              className="group h-14 px-8 rounded-xl bg-gradient-to-r from-violet-600 to-rose-600 text-white font-bold text-base hover:shadow-[0_0_40px_-8px_rgba(139,92,246,0.5)] transition-all hover:scale-[1.02] flex items-center gap-2 pulse-glow"
              data-testid="hero-continue-btn"
            >
              <Zap className="w-5 h-5" /> Create Your Story &amp; Take #1 Spot
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>
            <button
              onClick={() => {
                axios.post(`${API}/api/ab/convert`, { session_id: sessionId, experiment_id: 'hero_headline', event: 'click' }).catch(() => {});
                axios.post(`${API}/api/public/ab-impression`, { variant: heroVariant, action: 'create_click', session_id: sessionId, traffic_source: trafficSource, experiment_id: 'hero_headline' }).catch(() => {});
                if (showcaseRef.current) showcaseRef.current.scrollIntoView({ behavior: 'smooth' });
              }}
              className="h-14 px-8 rounded-xl border border-white/10 bg-white/[0.03] text-white font-bold text-base hover:bg-white/[0.06] transition-all flex items-center gap-2"
              data-testid="hero-create-btn"
            >
              <Play className="w-5 h-5 text-violet-400" /> Watch Examples
            </button>
          </div>

          {/* Trust line */}
          <p className="text-xs text-slate-500 mb-6 fade-up-3" data-testid="hero-trust-line">
            No credit card required &bull; Free to start &bull; Compete for #1
          </p>

          {/* ─── ALIVE SIGNALS ─── */}
          {aliveSignals && (
            <div className="flex flex-wrap items-center justify-center gap-3 fade-up-4" data-testid="alive-signals">
              {aliveSignals.stories_today > 0 && (
                <div className="flex items-center gap-1.5 text-xs text-violet-300 bg-violet-500/8 border border-violet-500/15 px-3 py-1.5 rounded-full">
                  <Activity className="w-3 h-3" />
                  <span className="font-semibold">{aliveSignals.stories_today}</span> stories created today
                </div>
              )}
              {aliveSignals.continuations_today > 0 && (
                <div className="flex items-center gap-1.5 text-xs text-emerald-300 bg-emerald-500/8 border border-emerald-500/15 px-3 py-1.5 rounded-full">
                  <GitBranch className="w-3 h-3" />
                  <span className="font-semibold">{aliveSignals.continuations_today}</span> continued today
                </div>
              )}
              {aliveSignals.active_creators > 0 && (
                <div className="flex items-center gap-1.5 text-xs text-amber-300 bg-amber-500/8 border border-amber-500/15 px-3 py-1.5 rounded-full">
                  <Users className="w-3 h-3" />
                  <span className="font-semibold">{aliveSignals.active_creators}</span> creating right now
                </div>
              )}
              {aliveSignals.latest_fork?.timestamp && (
                <div className="flex items-center gap-1.5 text-xs text-slate-400 bg-white/[0.03] px-3 py-1.5 rounded-full">
                  <Clock className="w-3 h-3" />
                  New version created {_timeAgo(aliveSignals.latest_fork.timestamp)}
                </div>
              )}
            </div>
          )}
        </div>
      </section>

      {/* ═══════ FOUNDER AUTHORITY BLOCK ═══════ */}
      <FounderAuthorityBlock onExplore={goCreateFresh} />

      {/* ═══════ FIRST SESSION — FEATURED STORY ═══════ */}
      {featuredStory && (
        <section className="px-4 pb-8" data-testid="featured-story">
          <div className="max-w-2xl mx-auto">
            <div className="relative rounded-2xl border border-violet-500/20 bg-gradient-to-br from-violet-500/[0.04] to-rose-500/[0.04] p-6 text-center">
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full bg-violet-600 text-white text-[10px] font-bold tracking-wider uppercase">
                Continue this story
              </div>
              <h3 className="text-xl font-bold text-white mt-2 mb-2" data-testid="featured-title">
                {featuredStory.title || 'Untitled Story'}
              </h3>
              {featuredStory.hookText && (
                <p className="text-sm text-violet-300 italic mb-4">"{featuredStory.hookText}"</p>
              )}
              {featuredStory.preview && !featuredStory.hookText && (
                <p className="text-sm text-slate-400 mb-4 line-clamp-2">{featuredStory.preview}</p>
              )}
              <div className="flex items-center justify-center gap-3 mb-3">
                {featuredStory.forks > 0 && (
                  <span className="text-xs text-violet-300 flex items-center gap-1"><GitBranch className="w-3 h-3" /> {featuredStory.forks} versions</span>
                )}
                {featuredStory.views > 0 && (
                  <span className="text-xs text-slate-400 flex items-center gap-1"><Eye className="w-3 h-3" /> {featuredStory.views} views</span>
                )}
              </div>
              <button
                onClick={() => {
                  if (featuredStory.shareId) navigate(`/share/${featuredStory.shareId}`);
                  else goCreateFresh();
                }}
                className="h-12 px-8 rounded-xl bg-gradient-to-r from-violet-600 to-rose-600 text-white font-bold hover:shadow-[0_0_30px_-8px_rgba(139,92,246,0.4)] transition-all hover:scale-[1.02] flex items-center gap-2 mx-auto"
                data-testid="featured-continue-btn"
              >
                <Play className="w-5 h-5" /> Continue This Story
              </button>
            </div>
          </div>
        </section>
      )}

      {/* ═══════ 2. SHOWCASE — REAL STORIES (autoplay-ready) ═══════ */}
      <section ref={showcaseRef} className="py-12 px-4" data-testid="showcase-section">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-end justify-between mb-6">
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-[10px] font-bold tracking-[0.2em] uppercase text-emerald-400">Trending Now</span>
              </div>
              <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">See what people are creating</h2>
            </div>
            <Link to="/explore" className="hidden sm:flex items-center gap-1 text-sm text-violet-400 hover:text-violet-300 font-medium transition-colors">
              See all <ChevronRight className="w-4 h-4" />
            </Link>
          </div>

          {showcase.length > 0 ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3" data-testid="showcase-grid">
              {showcase.slice(0, 10).map((item, idx) => {
                // Direct webpack-bundled image — part of the JS build
                const bundledImg = item.card_img;
                return (
                <div key={item.job_id || idx} className="story-card group relative rounded-2xl overflow-hidden border border-white/[0.06] bg-white/[0.02] cursor-pointer transition-all hover:border-violet-500/30" data-testid={`showcase-card-${idx}`}>
                  <div className="relative aspect-[3/4] overflow-hidden bg-slate-900">
                    <div className="story-thumb transition-transform duration-500">
                      {bundledImg ? (
                        <img src={bundledImg} alt={item.title || ''} loading={idx < 4 ? 'eager' : 'lazy'}
                          className="w-full h-full object-cover" />
                      ) : (
                        <div className="w-full h-full bg-gradient-to-br from-violet-800 to-rose-800 flex items-center justify-center">
                          <Film className="w-10 h-10 text-white/20" />
                        </div>
                      )}
                    </div>
                    <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/20 to-transparent" />
                    <div className="story-overlay absolute inset-0 bg-violet-900/30 backdrop-blur-[2px] opacity-0 transition-opacity duration-300 flex items-center justify-center">
                      <div className="w-14 h-14 rounded-full bg-white/20 flex items-center justify-center backdrop-blur-sm">
                        <Play className="w-7 h-7 text-white ml-1" />
                      </div>
                    </div>
                    {idx < 3 && (
                      <div className="absolute top-2 left-2 px-2 py-0.5 rounded-md text-[10px] font-black bg-black/60 backdrop-blur-sm text-amber-400 border border-amber-500/20">
                        #{idx + 1}
                      </div>
                    )}
                    {(item.views > 0) && (
                      <div className="absolute top-2 right-2 flex items-center gap-1 bg-black/60 backdrop-blur-sm px-1.5 py-0.5 rounded-md text-[10px] text-white/70">
                        <Eye className="w-2.5 h-2.5" /> {item.views}
                      </div>
                    )}
                    <div className="absolute bottom-0 left-0 right-0 p-3">
                      <h3 className="text-sm font-bold text-white leading-tight mb-1 line-clamp-2">{item.title || 'Untitled Story'}</h3>
                      <p className="text-[10px] text-white/50 mb-2.5 line-clamp-1">{item.animation_style?.replace(/_/g, ' ')}</p>
                      <button
                        onClick={(e) => { e.stopPropagation(); continueStory(item); }}
                        className="w-full h-8 rounded-lg bg-gradient-to-r from-violet-600 to-rose-600 text-white text-xs font-bold flex items-center justify-center gap-1.5 hover:opacity-90 transition-opacity"
                        data-testid={`continue-story-${idx}`}
                      >
                        <Play className="w-3 h-3" /> Continue Story
                      </button>
                    </div>
                  </div>
                </div>
                );
              })}
            </div>
          ) : (
            /* Curated fallback — no empty skeletons */
            <div data-testid="showcase-fallback">
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {STORY_HOOKS.slice(0, 3).map((hook, i) => (
                  <button key={i} onClick={() => startFromHook(hook)}
                    className="group text-left p-6 rounded-2xl border border-white/[0.06] bg-gradient-to-br from-violet-500/[0.04] to-rose-500/[0.04] hover:border-violet-500/30 transition-all">
                    <span className="text-[10px] font-bold tracking-wider uppercase text-violet-400/60 mb-2 block">{hook.category}</span>
                    <p className="text-base font-bold text-white leading-relaxed mb-3 group-hover:text-violet-200 transition-colors">"{hook.prompt}"</p>
                    <div className="flex items-center gap-1.5 text-xs text-violet-400 font-semibold">
                      <Sparkles className="w-3.5 h-3.5" /> Be the first to create this story
                    </div>
                  </button>
                ))}
              </div>
              <p className="text-center text-sm text-slate-500 mt-4">No trending stories yet — start one and it could be featured here.</p>
            </div>
          )}

          <div className="text-center mt-6 sm:hidden">
            <Link to="/explore">
              <button className="h-10 px-6 text-sm font-medium rounded-lg border border-white/10 text-white hover:bg-white/[0.04] transition-colors">See all stories <ArrowRight className="w-3.5 h-3.5 inline ml-1" /></button>
            </Link>
          </div>
        </div>
      </section>

      {/* ═══════ 3. STORY HOOKS — CLICK-TO-CREATE ═══════ */}
      <section className="py-12 px-4 border-t border-white/[0.04]" data-testid="hooks-section">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-8">
            <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight mb-2">Everything you need to create viral content</h2>
            <p className="text-sm text-slate-400">Pick a story idea — or type your own. AI does the rest in under a minute.</p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3" data-testid="hooks-grid">
            {STORY_HOOKS.map((hook, i) => (
              <button
                key={i}
                onClick={() => startFromHook(hook)}
                className="group text-left p-5 rounded-2xl border border-white/[0.06] bg-white/[0.02] hover:border-violet-500/30 hover:bg-violet-500/[0.04] transition-all"
                data-testid={`hook-card-${i}`}
              >
                <span className="text-[10px] font-bold tracking-wider uppercase text-violet-400/60 mb-2 block">{hook.category}</span>
                <p className="text-sm font-medium text-white leading-relaxed group-hover:text-violet-200 transition-colors">"{hook.prompt}"</p>
                <div className="flex items-center gap-1.5 mt-3 text-[10px] text-slate-500 group-hover:text-violet-400 transition-colors">
                  <Sparkles className="w-3 h-3" /> Click to create this story
                </div>
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════ 4. SOCIAL PROOF (Real) ═══════ */}
      {stats && (
        <section className="border-y border-white/[0.04] py-10 px-4" data-testid="social-proof">
          <div className="max-w-5xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            {[
              { value: stats.videos_created || 0, label: 'Stories Created', suffix: '+' },
              { value: stats.creators || 0, label: 'Creators', suffix: '' },
              { value: stats.ai_scenes || 0, label: 'Scenes Generated', suffix: '+' },
              { value: stats.total_creations || 0, label: 'Total Creations', suffix: '+' },
            ].filter(s => s.value > 0).map((stat) => (
              <div key={stat.label}>
                <div className="text-3xl md:text-4xl font-black text-white tabular-nums">
                  {stat.value.toLocaleString()}{stat.suffix}
                </div>
                <div className="text-sm text-slate-500 mt-1">{stat.label}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ═══════ 5. HOW IT WORKS — 3 STEPS ═══════ */}
      <section className="py-16 px-4" data-testid="how-it-works">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-10">
            <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight mb-2">Create in 3 simple steps</h2>
            <p className="text-sm text-slate-400">No prompting skills. No editing. No experience needed.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-4">
            {[
              { step: '1', title: 'Enter your idea', desc: 'Type a sentence — a story hook, a concept, or a scene. That\'s all you need.', icon: BookOpen, color: 'from-violet-500 to-indigo-500' },
              { step: '2', title: 'AI creates everything', desc: 'Story, visuals, voiceover, and music — generated automatically in under a minute.', icon: Film, color: 'from-rose-500 to-pink-500' },
              { step: '3', title: 'Download or share instantly', desc: 'Get your video instantly. Share it with friends, post it online, or remix it into something new.', icon: Users, color: 'from-amber-500 to-orange-500' },
            ].map((item) => (
              <div key={item.step} className="relative rounded-2xl border border-white/[0.06] bg-white/[0.02] p-6 text-center" data-testid={`step-${item.step}`}>
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${item.color} flex items-center justify-center mx-auto mb-4`}>
                  <item.icon className="w-6 h-6 text-white" />
                </div>
                <div className="absolute -top-2.5 left-1/2 -translate-x-1/2 w-5 h-5 rounded-full bg-gradient-to-br from-violet-500 to-rose-500 flex items-center justify-center text-[10px] font-bold text-white">{item.step}</div>
                <h3 className="text-base font-bold text-white mb-2">{item.title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════ 6. LIVE FEED ═══════ */}
      {liveFeed.length > 0 && (
        <section className="py-12 px-4 border-t border-white/[0.04]" data-testid="live-feed-section">
          <div className="max-w-3xl mx-auto">
            <div className="flex items-center gap-3 mb-6">
              <div className="relative">
                <div className="w-2 h-2 rounded-full bg-emerald-400" />
                <div className="w-2 h-2 rounded-full bg-emerald-400 absolute inset-0 animate-ping" />
              </div>
              <span className="text-sm font-semibold text-white">Happening now</span>
            </div>
            <div className="space-y-0 divide-y divide-white/[0.04]">
              {liveFeed.map((item, idx) => (
                <div key={item.id || idx} className="flex items-center gap-3 py-2.5 text-sm">
                  <span className="text-white font-medium">{item.creator}</span>
                  <span className="text-slate-500">{item.action}</span>
                  <span className="text-violet-400 font-medium truncate">"{item.title}"</span>
                  <span className="text-xs text-slate-600 ml-auto flex-shrink-0 tabular-nums">{item.time_ago}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ═══════ 7. FINAL CTA ═══════ */}
      <section className="py-20 px-4 border-t border-white/[0.04]" data-testid="final-cta">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl md:text-5xl font-black text-white mb-4 tracking-tight">
            Create your first AI video now
          </h2>
          <p className="text-lg text-slate-400 mb-3">
            It takes less than 30 seconds. No editing needed. Completely free to start.
          </p>
          <p className="text-sm text-slate-500 mb-8">People are creating viral videos every day — 12,000+ and growing</p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <button
              onClick={goCreateFresh}
              className="h-14 px-10 rounded-xl bg-gradient-to-r from-violet-600 to-rose-600 text-white font-bold text-lg hover:shadow-[0_0_40px_-8px_rgba(139,92,246,0.5)] transition-all hover:scale-[1.02] flex items-center gap-2"
              data-testid="final-cta-create"
            >
              <Zap className="w-5 h-5" /> Start Creating — Free <ArrowRight className="w-5 h-5" />
            </button>
            <Link to="/explore">
              <button className="h-14 px-10 rounded-xl border border-white/10 text-white font-medium text-lg hover:bg-white/[0.04] transition-colors" data-testid="final-cta-explore">
                Watch Examples
              </button>
            </Link>
          </div>
        </div>
      </section>

      {/* ═══════ FOOTER ═══════ */}
      <footer className="border-t border-white/[0.04]" data-testid="landing-footer">
        {/* CTA Strip */}
        <div className="py-8 px-4 bg-gradient-to-r from-violet-600/[0.06] to-rose-600/[0.06] border-b border-white/[0.04]" data-testid="footer-cta-strip">
          <div className="max-w-3xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
            <div>
              <p className="text-base font-bold text-white">Create your first AI video in seconds — free</p>
              <p className="text-xs text-slate-400 mt-0.5">No credit card. No editing skills. Just your idea.</p>
            </div>
            <button
              onClick={goCreateFresh}
              className="h-11 px-6 rounded-xl bg-gradient-to-r from-violet-600 to-rose-600 text-white font-bold text-sm hover:opacity-90 transition-opacity flex items-center gap-2 whitespace-nowrap flex-shrink-0"
              data-testid="footer-cta-btn"
            >
              <Zap className="w-4 h-4" /> Start Creating
            </button>
          </div>
        </div>

        <div className="py-10 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-8">
            <div>
              <h4 className="text-sm font-semibold text-white mb-3">Create</h4>
              <div className="space-y-3">
                <Link to="/app/story-video-studio" className="block group">
                  <span className="text-sm text-slate-400 group-hover:text-white transition-colors font-medium">Story Video</span>
                  <p className="text-[11px] text-slate-600 leading-snug mt-0.5">Turn simple ideas into cinematic AI stories with characters, voice, and motion — in minutes.</p>
                </Link>
                <Link to="/app/reels" className="block group">
                  <span className="text-sm text-slate-400 group-hover:text-white transition-colors font-medium">Reel Generator</span>
                  <p className="text-[11px] text-slate-600 leading-snug mt-0.5">Create viral-ready short videos with powerful hooks, captions, and scroll-stopping visuals.</p>
                </Link>
                <Link to="/app/comic-storybook" className="block group">
                  <span className="text-sm text-slate-400 group-hover:text-white transition-colors font-medium">Comic Storybook</span>
                  <p className="text-[11px] text-slate-600 leading-snug mt-0.5">Bring your stories to life as beautiful illustrated comics with scenes, dialogue, and emotion.</p>
                </Link>
                <Link to="/app/bedtime-story-builder" className="block group">
                  <span className="text-sm text-slate-400 group-hover:text-white transition-colors font-medium">Bedtime Stories</span>
                  <p className="text-[11px] text-slate-600 leading-snug mt-0.5">Create magical, calming bedtime stories for kids with soothing narration and dreamy visuals.</p>
                </Link>
              </div>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-white mb-3">Discover</h4>
              <div className="space-y-3">
                <Link to="/explore" className="block group">
                  <span className="text-sm text-slate-400 group-hover:text-white transition-colors font-medium">Explore</span>
                  <p className="text-[11px] text-slate-600 leading-snug mt-0.5">Discover trending AI stories and viral videos created by people around the world.</p>
                </Link>
                <Link to="/gallery" className="block group">
                  <span className="text-sm text-slate-400 group-hover:text-white transition-colors font-medium">Gallery</span>
                  <p className="text-[11px] text-slate-600 leading-snug mt-0.5">Browse a growing collection of jaw-dropping AI creations — stories, videos, comics, and more.</p>
                </Link>
                <Link to="/explore?tab=most_remixed" className="block group">
                  <span className="text-sm text-slate-400 group-hover:text-white transition-colors font-medium">Most Remixed</span>
                  <p className="text-[11px] text-slate-600 leading-snug mt-0.5">See the stories everyone is remixing, evolving, and turning into something new.</p>
                </Link>
              </div>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-white mb-3">Company</h4>
              <div className="space-y-3">
                <Link to="/pricing" className="block group">
                  <span className="text-sm text-slate-400 group-hover:text-white transition-colors font-medium">Pricing</span>
                  <p className="text-[11px] text-slate-600 leading-snug mt-0.5">Choose a plan that unlocks your creative superpowers with AI.</p>
                </Link>
                <Link to="/blog" className="block group">
                  <span className="text-sm text-slate-400 group-hover:text-white transition-colors font-medium">Blog</span>
                  <p className="text-[11px] text-slate-600 leading-snug mt-0.5">Learn how to create viral content, tell better stories, and grow faster with AI.</p>
                </Link>
                <div className="block">
                  <span className="text-sm text-slate-400 font-medium">Contact</span>
                  <p className="text-[11px] text-slate-600 leading-snug mt-0.5">Have questions or ideas? We'd love to hear from you.</p>
                  <a href="mailto:krajapraveen@visionary-suite.com" className="text-[11px] text-violet-400 hover:text-violet-300 transition-colors mt-0.5 block">krajapraveen@visionary-suite.com</a>
                  <a href="mailto:krajapraveen@gmail.com" className="text-[11px] text-violet-400 hover:text-violet-300 transition-colors mt-0.5 block">krajapraveen@gmail.com</a>
                </div>
              </div>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-white mb-3">Legal</h4>
              <div className="space-y-3">
                <Link to="/privacy" className="block group">
                  <span className="text-sm text-slate-400 group-hover:text-white transition-colors font-medium">Privacy Policy</span>
                  <p className="text-[11px] text-slate-600 leading-snug mt-0.5">How we protect your data and respect your privacy.</p>
                </Link>
                <Link to="/terms" className="block group">
                  <span className="text-sm text-slate-400 group-hover:text-white transition-colors font-medium">Terms of Service</span>
                  <p className="text-[11px] text-slate-600 leading-snug mt-0.5">Clear guidelines on using Visionary Suite responsibly and safely.</p>
                </Link>
                <Link to="/cookies" className="block group">
                  <span className="text-sm text-slate-400 group-hover:text-white transition-colors font-medium">Cookie Policy</span>
                  <p className="text-[11px] text-slate-600 leading-snug mt-0.5">How we use cookies to improve your experience and performance.</p>
                </Link>
              </div>
            </div>
          </div>
          <div className="border-t border-white/[0.04] pt-6 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-5 h-5 rounded-md bg-gradient-to-br from-violet-500 to-rose-500 flex items-center justify-center">
                <Command className="w-2.5 h-2.5 text-white" />
              </div>
              <span className="text-sm font-semibold text-slate-500">Visionary Suite</span>
            </div>
            <p className="text-xs text-slate-600">AI video creation platform — create, share, go viral.</p>
          </div>
        </div>
        </div>
      </footer>
    </div>
  );
}
