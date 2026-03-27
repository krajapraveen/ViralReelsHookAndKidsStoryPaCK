import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Play, ArrowRight, Menu, X, Eye, RefreshCcw, Zap, Command,
  ChevronRight, Sparkles, Film, BookOpen, Users
} from 'lucide-react';
import axios from 'axios';
import { SafeImage } from '../components/SafeImage';

const API = process.env.REACT_APP_BACKEND_URL;

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
  const [showcase, setShowcase] = useState([]);
  const [liveFeed, setLiveFeed] = useState([]);
  const navigate = useNavigate();
  const showcaseRef = useRef(null);

  useEffect(() => {
    axios.get(`${API}/api/public/stats`).then(r => setStats(r.data)).catch(() => {});
    axios.get(`${API}/api/public/trending-weekly?limit=12`).then(r => setShowcase(r.data.items || [])).catch(() => {});
    axios.get(`${API}/api/public/live-activity?limit=6`).then(r => setLiveFeed(r.data.items || [])).catch(() => {});
  }, []);

  // Auto-refresh live feed
  useEffect(() => {
    const iv = setInterval(() => {
      axios.get(`${API}/api/public/live-activity?limit=6`).then(r => setLiveFeed(r.data.items || [])).catch(() => {});
    }, 8000);
    return () => clearInterval(iv);
  }, []);

  const continueStory = (item) => {
    const data = {
      prompt: item.story_text || item.title || '',
      timestamp: Date.now(),
      source_tool: 'landing-continue',
      remixFrom: {
        tool: 'story-video-studio',
        prompt: item.story_text || item.title,
        title: item.title,
        settings: { animation_style: item.animation_style },
        parentId: item.job_id,
      },
    };
    localStorage.setItem('remix_data', JSON.stringify(data));
    navigate('/app/story-video-studio');
  };

  const startFromHook = (hook) => {
    localStorage.setItem('onboarding_prompt', hook.prompt);
    navigate('/app/story-video-studio?prompt=' + encodeURIComponent(hook.prompt));
  };

  const goCreateFresh = () => {
    navigate('/app/story-video-studio');
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
            <Link to="/pricing" className="block text-slate-300 hover:text-white py-2" onClick={() => setMobileMenuOpen(false)}>Pricing</Link>
            <Link to="/login" className="block text-slate-300 hover:text-white py-2" onClick={() => setMobileMenuOpen(false)}>Login</Link>
            <button onClick={() => { setMobileMenuOpen(false); goCreateFresh(); }} className="w-full h-10 text-sm font-semibold rounded-lg bg-gradient-to-r from-violet-600 to-rose-600 text-white">Start Creating</button>
          </div>
        )}
      </nav>

      {/* ═══════ 1. HERO — STORY-DRIVEN ═══════ */}
      <section className="relative pt-24 pb-8 md:pt-32 md:pb-12 px-4" data-testid="hero-section">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-20 left-1/4 w-[600px] h-[600px] bg-violet-600/[0.06] rounded-full blur-[180px]" />
          <div className="absolute bottom-0 right-1/3 w-[400px] h-[400px] bg-rose-500/[0.04] rounded-full blur-[120px]" />
        </div>

        <div className="relative max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-violet-500/10 border border-violet-500/20 text-violet-300 text-xs font-medium mb-6 fade-up" data-testid="hero-badge">
            <Sparkles className="w-3 h-3" /> Every story here is unfinished
          </div>

          <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-black tracking-[-0.04em] leading-[0.92] mb-5 fade-up" data-testid="hero-heading">
            <span className="text-white">Stories that don't end</span><br />
            <span className="bg-gradient-to-r from-violet-400 via-rose-400 to-amber-400 bg-clip-text text-transparent">until you continue them</span>
          </h1>

          <p className="text-lg md:text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed mb-8 fade-up-2" data-testid="hero-subtitle">
            Create, watch, and shape stories powered by AI. What happens next is up to you.
          </p>

          {/* ─── TWO BIG CTAs ─── */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mb-8 fade-up-3" data-testid="hero-ctas">
            <button
              onClick={() => showcaseRef.current?.scrollIntoView({ behavior: 'smooth' })}
              className="group h-14 px-8 rounded-xl bg-gradient-to-r from-violet-600 to-rose-600 text-white font-bold text-base hover:shadow-[0_0_40px_-8px_rgba(139,92,246,0.5)] transition-all hover:scale-[1.02] flex items-center gap-2 pulse-glow"
              data-testid="hero-continue-btn"
            >
              <Play className="w-5 h-5" /> See What Happens Next
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>
            <button
              onClick={goCreateFresh}
              className="h-14 px-8 rounded-xl border border-white/10 bg-white/[0.03] text-white font-bold text-base hover:bg-white/[0.06] transition-all flex items-center gap-2"
              data-testid="hero-create-btn"
            >
              <Sparkles className="w-5 h-5 text-violet-400" /> Create Your Version
            </button>
          </div>

          {/* Social proof line removed — no misleading claims */}
        </div>
      </section>

      {/* ═══════ 2. SHOWCASE — REAL STORIES (autoplay-ready) ═══════ */}
      <section ref={showcaseRef} className="py-12 px-4" data-testid="showcase-section">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-end justify-between mb-6">
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-[10px] font-bold tracking-[0.2em] uppercase text-emerald-400">Trending Now</span>
              </div>
              <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">Stories you can continue</h2>
            </div>
            <Link to="/explore" className="hidden sm:flex items-center gap-1 text-sm text-violet-400 hover:text-violet-300 font-medium transition-colors">
              See all <ChevronRight className="w-4 h-4" />
            </Link>
          </div>

          {showcase.length > 0 ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3" data-testid="showcase-grid">
              {showcase.slice(0, 10).map((item, idx) => (
                <div key={item.job_id || idx} className="story-card group relative rounded-2xl overflow-hidden border border-white/[0.06] bg-white/[0.02] cursor-pointer transition-all hover:border-violet-500/30" data-testid={`showcase-card-${idx}`}>
                  <div className="relative aspect-[3/4] overflow-hidden bg-slate-900">
                    <div className="story-thumb transition-transform duration-500">
                      <SafeImage src={item.thumbnail_url} alt={item.title} aspectRatio="3/4" titleOverlay={item.title} fallbackType="gradient" className="w-full h-full object-cover" />
                    </div>
                    {/* Dark gradient overlay */}
                    <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/20 to-transparent" />
                    {/* Hover overlay */}
                    <div className="story-overlay absolute inset-0 bg-violet-900/30 backdrop-blur-[2px] opacity-0 transition-opacity duration-300 flex items-center justify-center">
                      <div className="w-14 h-14 rounded-full bg-white/20 flex items-center justify-center backdrop-blur-sm">
                        <Play className="w-7 h-7 text-white ml-1" />
                      </div>
                    </div>
                    {/* Rank badge */}
                    {idx < 3 && (
                      <div className="absolute top-2 left-2 px-2 py-0.5 rounded-md text-[10px] font-black bg-black/60 backdrop-blur-sm text-amber-400 border border-amber-500/20">
                        #{idx + 1}
                      </div>
                    )}
                    {/* Views badge */}
                    {(item.views > 0) && (
                      <div className="absolute top-2 right-2 flex items-center gap-1 bg-black/60 backdrop-blur-sm px-1.5 py-0.5 rounded-md text-[10px] text-white/70">
                        <Eye className="w-2.5 h-2.5" /> {item.views}
                      </div>
                    )}
                    {/* Bottom content */}
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
              ))}
            </div>
          ) : (
            /* Skeleton loading */
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="rounded-2xl overflow-hidden border border-white/[0.04] bg-white/[0.01]">
                  <div className="aspect-[3/4] bg-slate-800/50 animate-pulse" />
                </div>
              ))}
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
            <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight mb-2">Pick a story. Make it yours.</h2>
            <p className="text-sm text-slate-400">Click any hook below — it opens the studio prefilled and ready to go.</p>
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
            <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight mb-2">Story to video in 3 clicks</h2>
            <p className="text-sm text-slate-400">No prompting skills. No editing. No login to start.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-4">
            {[
              { step: '1', title: 'Pick or type a story', desc: 'Choose from trending stories or write your own hook. One sentence is enough.', icon: BookOpen, color: 'from-violet-500 to-indigo-500' },
              { step: '2', title: 'AI brings it alive', desc: 'Scenes, illustrations, voiceover, and music — generated in under a minute.', icon: Film, color: 'from-rose-500 to-pink-500' },
              { step: '3', title: 'Continue or share', desc: 'Add episodes, remix, or share — others can continue your story.', icon: Users, color: 'from-amber-500 to-orange-500' },
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
            Someone already started this story
          </h2>
          <p className="text-lg text-slate-400 mb-8">
            Will you finish it? Watch it. Change it. Continue it.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <button
              onClick={goCreateFresh}
              className="h-14 px-10 rounded-xl bg-gradient-to-r from-violet-600 to-rose-600 text-white font-bold text-lg hover:shadow-[0_0_40px_-8px_rgba(139,92,246,0.5)] transition-all hover:scale-[1.02] flex items-center gap-2"
              data-testid="final-cta-create"
            >
              <Sparkles className="w-5 h-5" /> Create Your Version <ArrowRight className="w-5 h-5" />
            </button>
            <Link to="/explore">
              <button className="h-14 px-10 rounded-xl border border-white/10 text-white font-medium text-lg hover:bg-white/[0.04] transition-colors" data-testid="final-cta-explore">
                Explore Stories
              </button>
            </Link>
          </div>
        </div>
      </section>

      {/* ═══════ FOOTER ═══════ */}
      <footer className="border-t border-white/[0.04] py-10 px-4" data-testid="landing-footer">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-8">
            <div>
              <h4 className="text-sm font-semibold text-white mb-3">Create</h4>
              <div className="space-y-3">
                <Link to="/app/story-video-studio" className="block group">
                  <span className="text-sm text-slate-400 group-hover:text-white transition-colors font-medium">Story Video</span>
                  <p className="text-[11px] text-slate-600 leading-snug mt-0.5">Turn your ideas into cinematic AI stories with characters, voice, and motion.</p>
                </Link>
                <Link to="/app/reels" className="block group">
                  <span className="text-sm text-slate-400 group-hover:text-white transition-colors font-medium">Reel Generator</span>
                  <p className="text-[11px] text-slate-600 leading-snug mt-0.5">Create viral short videos with powerful hooks, captions, and ready-to-post formats.</p>
                </Link>
                <Link to="/app/comic-storybook" className="block group">
                  <span className="text-sm text-slate-400 group-hover:text-white transition-colors font-medium">Comic Storybook</span>
                  <p className="text-[11px] text-slate-600 leading-snug mt-0.5">Transform your stories into illustrated comics with scenes, dialogues, and visuals.</p>
                </Link>
                <Link to="/app/bedtime-story-builder" className="block group">
                  <span className="text-sm text-slate-400 group-hover:text-white transition-colors font-medium">Bedtime Stories</span>
                  <p className="text-[11px] text-slate-600 leading-snug mt-0.5">Generate soothing, magical stories for kids with gentle narration and calming visuals.</p>
                </Link>
              </div>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-white mb-3">Discover</h4>
              <div className="space-y-3">
                <Link to="/explore" className="block group">
                  <span className="text-sm text-slate-400 group-hover:text-white transition-colors font-medium">Explore</span>
                  <p className="text-[11px] text-slate-600 leading-snug mt-0.5">Discover trending AI stories, videos, and creative content from across the platform.</p>
                </Link>
                <Link to="/gallery" className="block group">
                  <span className="text-sm text-slate-400 group-hover:text-white transition-colors font-medium">Gallery</span>
                  <p className="text-[11px] text-slate-600 leading-snug mt-0.5">Browse a growing collection of stories, videos, comics, and creative outputs.</p>
                </Link>
                <Link to="/explore?tab=most_remixed" className="block group">
                  <span className="text-sm text-slate-400 group-hover:text-white transition-colors font-medium">Most Remixed</span>
                  <p className="text-[11px] text-slate-600 leading-snug mt-0.5">See the stories people love to continue, remix, and transform into new versions.</p>
                </Link>
              </div>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-white mb-3">Company</h4>
              <div className="space-y-3">
                <Link to="/pricing" className="block group">
                  <span className="text-sm text-slate-400 group-hover:text-white transition-colors font-medium">Pricing</span>
                  <p className="text-[11px] text-slate-600 leading-snug mt-0.5">Choose the plan that fits your creativity and unlock powerful AI features.</p>
                </Link>
                <Link to="/blog" className="block group">
                  <span className="text-sm text-slate-400 group-hover:text-white transition-colors font-medium">Blog</span>
                  <p className="text-[11px] text-slate-600 leading-snug mt-0.5">Learn how to create better stories, grow your content, and use AI effectively.</p>
                </Link>
                <div className="block">
                  <span className="text-sm text-slate-400 font-medium">Contact</span>
                  <p className="text-[11px] text-slate-600 leading-snug mt-0.5">Have questions or feedback? Reach out anytime.</p>
                  <a href="mailto:krajapraveen@visionary-suite.com" className="text-[11px] text-violet-400 hover:text-violet-300 transition-colors mt-0.5 block">krajapraveen@visionary-suite.com</a>
                </div>
              </div>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-white mb-3">Legal</h4>
              <div className="space-y-3">
                <Link to="/privacy" className="block group">
                  <span className="text-sm text-slate-400 group-hover:text-white transition-colors font-medium">Privacy Policy</span>
                  <p className="text-[11px] text-slate-600 leading-snug mt-0.5">Learn how we collect, use, and protect your data while you use our platform.</p>
                </Link>
                <Link to="/terms" className="block group">
                  <span className="text-sm text-slate-400 group-hover:text-white transition-colors font-medium">Terms of Service</span>
                  <p className="text-[11px] text-slate-600 leading-snug mt-0.5">Understand your rights, responsibilities, and the rules for using our services.</p>
                </Link>
                <Link to="/cookies" className="block group">
                  <span className="text-sm text-slate-400 group-hover:text-white transition-colors font-medium">Cookie Policy</span>
                  <p className="text-[11px] text-slate-600 leading-snug mt-0.5">See how cookies help improve your experience and how you can manage them.</p>
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
            <p className="text-xs text-slate-600">Stories that don't end... until you continue them.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
