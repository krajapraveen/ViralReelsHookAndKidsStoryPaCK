import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Sparkles, Clapperboard, ArrowRight, Menu, X, Film, Check, Play,
  RefreshCcw, Share2, Users, Eye, Send, Command, Wand2, Image, Mic,
  ChevronRight, Globe
} from 'lucide-react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

export default function Landing() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [stats, setStats] = useState(null);
  const [trending, setTrending] = useState([]);
  const [promptText, setPromptText] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    // Fetch real platform stats
    axios.get(`${API}/api/public/stats`).then(r => setStats(r.data)).catch(() => {});
    // Fetch trending creations
    axios.get(`${API}/api/public/explore?tab=trending&limit=6`).then(r => setTrending(r.data.items || [])).catch(() => {});
  }, []);

  const handlePromptSubmit = () => {
    if (!promptText.trim()) return;
    navigate('/signup', { state: { prompt: promptText } });
  };

  const tryExample = (text) => {
    setPromptText(text);
  };

  return (
    <div className="vs-page overflow-x-hidden">
      <style>{`
        .grid-bg { background-image: linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px); background-size: 80px 80px; }
      `}</style>

      {/* ═══════ NAVBAR ═══════ */}
      <nav className="fixed top-0 left-0 right-0 z-50 vs-glass border-b border-[var(--vs-border-subtle)]" data-testid="landing-nav">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg vs-gradient-bg flex items-center justify-center">
              <Command className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-bold tracking-tight text-white" style={{ fontFamily: 'var(--vs-font-heading)' }}>Visionary Suite</span>
          </Link>
          <div className="hidden md:flex items-center gap-6">
            <Link to="/explore" className="text-sm font-medium text-[var(--vs-text-muted)] hover:text-white transition-colors" style={{ fontFamily: 'var(--vs-font-body)' }}>Explore</Link>
            <a href="#how-it-works" className="text-sm font-medium text-[var(--vs-text-muted)] hover:text-white transition-colors" style={{ fontFamily: 'var(--vs-font-body)' }}>How It Works</a>
            <Link to="/pricing" className="text-sm font-medium text-[var(--vs-text-muted)] hover:text-white transition-colors" style={{ fontFamily: 'var(--vs-font-body)' }}>Pricing</Link>
            <Link to="/gallery" className="text-sm font-medium text-[var(--vs-text-muted)] hover:text-white transition-colors" style={{ fontFamily: 'var(--vs-font-body)' }}>Gallery</Link>
            <Link to="/login" className="text-sm font-medium text-[var(--vs-text-muted)] hover:text-white transition-colors" data-testid="nav-login-link" style={{ fontFamily: 'var(--vs-font-body)' }}>Login</Link>
            <Link to="/signup">
              <button className="vs-btn-primary h-9 px-5 text-sm rounded-lg" data-testid="nav-signup-btn">Start Creating</button>
            </Link>
          </div>
          <button className="md:hidden text-white p-2" onClick={() => setMobileMenuOpen(!mobileMenuOpen)} data-testid="mobile-menu-btn">
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-[var(--vs-border-subtle)] bg-[var(--vs-bg-base)]/95 backdrop-blur-2xl px-4 py-4 space-y-3">
            <Link to="/explore" className="block text-[var(--vs-text-secondary)] hover:text-white py-2" onClick={() => setMobileMenuOpen(false)}>Explore</Link>
            <Link to="/pricing" className="block text-[var(--vs-text-secondary)] hover:text-white py-2" onClick={() => setMobileMenuOpen(false)}>Pricing</Link>
            <Link to="/gallery" className="block text-[var(--vs-text-secondary)] hover:text-white py-2" onClick={() => setMobileMenuOpen(false)}>Gallery</Link>
            <Link to="/login" className="block text-[var(--vs-text-secondary)] hover:text-white py-2" onClick={() => setMobileMenuOpen(false)}>Login</Link>
            <Link to="/signup" className="block" onClick={() => setMobileMenuOpen(false)}>
              <button className="vs-btn-primary w-full h-10 text-sm">Start Creating</button>
            </Link>
          </div>
        )}
      </nav>

      {/* ═══════ 1. HERO — AI COMMAND CENTER ═══════ */}
      <section className="relative pt-32 pb-12 md:pt-44 md:pb-20 px-4">
        <div className="absolute inset-0 grid-bg pointer-events-none" />
        <div className="absolute top-16 left-1/3 w-[500px] h-[500px] bg-[var(--vs-primary-from)]/[0.06] rounded-full blur-[150px] pointer-events-none" />
        <div className="absolute bottom-0 right-1/4 w-[400px] h-[400px] bg-amber-500/[0.04] rounded-full blur-[120px] pointer-events-none" />

        <div className="relative max-w-4xl mx-auto text-center">
          <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-black tracking-[-0.04em] leading-[0.95] mb-5 vs-fade-up-1" data-testid="hero-heading" style={{ fontFamily: 'var(--vs-font-heading)' }}>
            <span className="text-white">Create Viral AI Videos</span><br />
            <span className="vs-gradient-text">in Minutes</span>
          </h1>

          <p className="text-lg md:text-xl text-[var(--vs-text-secondary)] max-w-2xl mx-auto leading-relaxed mb-10 vs-fade-up-2" style={{ fontFamily: 'var(--vs-font-body)' }}>
            Turn stories, photos, or ideas into cinematic videos using AI.
          </p>

          {/* ─── HERO PROMPT BOX ─── */}
          <div className="max-w-[800px] mx-auto vs-fade-up-2" data-testid="hero-prompt-box">
            <div className="relative flex items-center">
              <Sparkles className="absolute left-5 w-5 h-5 text-[var(--vs-primary-from)] z-10" />
              <input
                type="text"
                value={promptText}
                onChange={(e) => setPromptText(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handlePromptSubmit()}
                placeholder="What do you want to create today?"
                className="vs-input h-[70px] pl-14 pr-[140px] text-base"
                style={{ borderRadius: '14px', fontFamily: 'var(--vs-font-body)' }}
                data-testid="hero-prompt-input"
              />
              <button
                onClick={handlePromptSubmit}
                className="vs-btn-primary absolute right-3 h-[46px] px-6 rounded-[10px] text-base font-semibold"
                data-testid="hero-create-btn"
              >
                <Send className="w-4 h-4 mr-1.5" />
                Create
              </button>
            </div>

            {/* Suggestion prompts */}
            <div className="flex flex-wrap justify-center gap-2 mt-5">
              {[
                'Create a luxury car reel with narration',
                'Kids bedtime story video',
                'Dragon fantasy animation',
                'Luxury lifestyle reel',
              ].map((text) => (
                <button
                  key={text}
                  onClick={() => tryExample(text)}
                  className="vs-chip text-xs"
                  data-testid={`hero-chip-${text.slice(0, 10).replace(/\s/g, '-').toLowerCase()}`}
                >
                  {text}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-center gap-6 md:gap-8 text-sm text-[var(--vs-text-muted)] font-medium mt-8 vs-fade-up-3" style={{ fontFamily: 'var(--vs-font-body)' }}>
            <span className="flex items-center gap-1.5"><Check className="w-4 h-4 text-[var(--vs-success)]" /> Free to start</span>
            <span className="flex items-center gap-1.5"><Check className="w-4 h-4 text-[var(--vs-success)]" /> No credit card</span>
            <span className="flex items-center gap-1.5"><Check className="w-4 h-4 text-[var(--vs-success)]" /> Videos in minutes</span>
          </div>
        </div>
      </section>

      {/* ═══════ 2. SOCIAL PROOF (Real Data) ═══════ */}
      {stats && (
        <section className="border-y border-[var(--vs-border-subtle)] py-10 px-4" data-testid="social-proof">
          <div className="max-w-5xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            {[
              { value: stats.videos_created || 0, label: 'AI Videos Created', suffix: '+' },
              { value: stats.creators || 0, label: 'Creators', suffix: '' },
              { value: stats.ai_scenes || 0, label: 'AI Scenes Generated', suffix: '+' },
              { value: stats.total_creations || 0, label: 'Total Creations', suffix: '+' },
            ].filter(s => s.value > 0).map((stat) => (
              <div key={stat.label}>
                <div className="text-3xl md:text-4xl font-black text-white" style={{ fontFamily: 'var(--vs-font-mono)' }}>
                  {stat.value.toLocaleString()}{stat.suffix}
                </div>
                <div className="text-sm text-[var(--vs-text-muted)] mt-1.5" style={{ fontFamily: 'var(--vs-font-body)' }}>{stat.label}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ═══════ 3. THREE PILLARS — Create / Remix / Publish ═══════ */}
      <section className="py-20 px-4" data-testid="three-pillars">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="vs-h1 mb-3" style={{ fontFamily: 'var(--vs-font-heading)' }}>One Platform. Three Powers.</h2>
            <p className="text-[var(--vs-text-secondary)] text-lg" style={{ fontFamily: 'var(--vs-font-body)' }}>Everything you need to create, remix, and publish viral AI content.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                icon: Sparkles, title: 'Create',
                desc: 'Generate cinematic AI videos from any prompt. Stories, reels, comics — type an idea and watch AI bring it to life.',
                accent: 'from-violet-500 to-indigo-600',
                cta: 'Start Creating', link: '/signup'
              },
              {
                icon: RefreshCcw, title: 'Remix',
                desc: 'Take any creation and make it yours. Change the style, voice, or story — one click to create your own version.',
                accent: 'from-pink-500 to-rose-600',
                cta: 'Explore Remixes', link: '/explore?tab=most_remixed'
              },
              {
                icon: Share2, title: 'Publish',
                desc: 'Share your creations everywhere. Every video gets a public page with views, remixes, and social sharing built in.',
                accent: 'from-emerald-500 to-teal-600',
                cta: 'See Gallery', link: '/explore'
              },
            ].map(pillar => (
              <div key={pillar.title} className="vs-card group text-center py-10 px-6 hover:border-[var(--vs-border-glow)]" data-testid={`pillar-${pillar.title.toLowerCase()}`}>
                <div className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${pillar.accent} flex items-center justify-center mx-auto mb-5 group-hover:scale-110 transition-transform`}>
                  <pillar.icon className="w-7 h-7 text-white" />
                </div>
                <h3 className="vs-h2 mb-3" style={{ fontFamily: 'var(--vs-font-heading)' }}>{pillar.title}</h3>
                <p className="text-[var(--vs-text-secondary)] text-sm leading-relaxed mb-5" style={{ fontFamily: 'var(--vs-font-body)' }}>{pillar.desc}</p>
                <Link to={pillar.link}>
                  <button className="vs-btn-secondary h-9 px-5 text-xs">{pillar.cta} <ArrowRight className="w-3.5 h-3.5" /></button>
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════ 4. HOW IT WORKS ═══════ */}
      <section id="how-it-works" className="py-20 px-4 border-t border-[var(--vs-border-subtle)]" data-testid="how-it-works">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="vs-h1 mb-3" style={{ fontFamily: 'var(--vs-font-heading)' }}>How Visionary Suite Works</h2>
            <p className="text-[var(--vs-text-secondary)] text-lg" style={{ fontFamily: 'var(--vs-font-body)' }}>From idea to video in four simple steps.</p>
          </div>

          <div className="grid md:grid-cols-4 gap-4">
            {[
              { step: '1', icon: Send, title: 'Write a Prompt', desc: 'Type your story, idea, or script. Any genre, any style.' },
              { step: '2', icon: Wand2, title: 'AI Generates Scenes', desc: 'AI splits your story into cinematic scenes with illustrations.' },
              { step: '3', icon: Mic, title: 'Voice & Music', desc: 'Natural voiceover and music are added automatically.' },
              { step: '4', icon: Film, title: 'Export & Share', desc: 'Download your video or share it with one click.' },
            ].map((item, i) => (
              <div key={item.step} className="vs-card text-center py-8 px-4 relative" data-testid={`step-${item.step}`}>
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 w-7 h-7 rounded-full vs-gradient-bg flex items-center justify-center text-xs font-bold text-white" style={{ fontFamily: 'var(--vs-font-mono)' }}>
                  {item.step}
                </div>
                <item.icon className="w-8 h-8 text-[var(--vs-text-accent)] mx-auto mb-4 mt-2" />
                <h3 className="text-base font-semibold text-white mb-2" style={{ fontFamily: 'var(--vs-font-heading)' }}>{item.title}</h3>
                <p className="text-sm text-[var(--vs-text-muted)] leading-relaxed" style={{ fontFamily: 'var(--vs-font-body)' }}>{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════ 5. TRENDING CREATIONS ═══════ */}
      {trending.length > 0 && (
        <section className="py-20 px-4 border-t border-[var(--vs-border-subtle)]" data-testid="trending-section">
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-12">
              <h2 className="vs-h1 mb-3" style={{ fontFamily: 'var(--vs-font-heading)' }}>Trending Creations</h2>
              <p className="text-[var(--vs-text-secondary)] text-lg" style={{ fontFamily: 'var(--vs-font-body)' }}>Real AI videos created by our community. Every one started as a simple text prompt.</p>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {trending.slice(0, 6).map(item => (
                <Link key={item.job_id} to={`/v/${item.slug || item.job_id}`}>
                  <div className="vs-card group p-0 overflow-hidden cursor-pointer" data-testid={`trending-card-${item.job_id}`}>
                    <div className="relative w-full aspect-video bg-[var(--vs-bg-elevated)] overflow-hidden">
                      {item.thumbnail_url ? (
                        <img src={item.thumbnail_url} alt={item.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" loading="lazy" />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <Film className="w-10 h-10 text-[var(--vs-text-muted)]" />
                        </div>
                      )}
                      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center">
                        <Play className="w-10 h-10 text-white opacity-0 group-hover:opacity-80 transition-opacity drop-shadow-lg" />
                      </div>
                    </div>
                    <div className="p-3">
                      <h3 className="text-sm font-medium text-white truncate group-hover:text-[var(--vs-text-accent)] transition-colors">{item.title}</h3>
                      <div className="flex items-center gap-3 mt-1.5">
                        <span className="text-xs text-[var(--vs-text-muted)]" style={{ fontFamily: 'var(--vs-font-mono)' }}>{item.animation_style?.replace(/_/g, ' ')}</span>
                        {item.remix_count > 0 && (
                          <span className="flex items-center gap-1 text-xs text-[var(--vs-text-accent)]" style={{ fontFamily: 'var(--vs-font-mono)' }}>
                            <RefreshCcw className="w-3 h-3" /> {item.remix_count}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>

            <div className="text-center mt-8">
              <Link to="/explore">
                <button className="vs-btn-secondary px-8 h-11 text-base" data-testid="explore-more-btn">
                  Explore More <ArrowRight className="w-4 h-4 ml-1" />
                </button>
              </Link>
            </div>
          </div>
        </section>
      )}

      {/* ═══════ 6. REMIX CULTURE ═══════ */}
      <section className="py-20 px-4 border-t border-[var(--vs-border-subtle)]" data-testid="remix-section">
        <div className="max-w-4xl mx-auto text-center">
          <div className="vs-card bg-gradient-to-br from-[var(--vs-primary-from)]/10 via-transparent to-[var(--vs-secondary-to)]/10 border-[var(--vs-border-glow)] py-16 px-8">
            <RefreshCcw className="w-12 h-12 text-[var(--vs-text-accent)] mx-auto mb-6" />
            <h2 className="vs-h1 mb-4" style={{ fontFamily: 'var(--vs-font-heading)' }}>Take Any Creation.<br />Make It Yours.</h2>
            <p className="text-[var(--vs-text-secondary)] text-lg max-w-xl mx-auto mb-8" style={{ fontFamily: 'var(--vs-font-body)' }}>
              See something you love? Hit Remix. Change the story, switch the style, add your voice — and create your own version in seconds.
            </p>
            <div className="flex items-center justify-center gap-4">
              <Link to="/explore?tab=most_remixed">
                <button className="vs-btn-primary h-12 px-8 text-base font-semibold rounded-xl" data-testid="remix-explore-btn">
                  <RefreshCcw className="w-4 h-4 mr-2" /> Explore Remixes
                </button>
              </Link>
              <Link to="/signup">
                <button className="vs-btn-secondary h-12 px-8 text-base rounded-xl">Create Your Own</button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════ 7. FINAL CTA ═══════ */}
      <section className="py-24 px-4 border-t border-[var(--vs-border-subtle)]" data-testid="final-cta">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl md:text-5xl font-black text-white mb-4 tracking-tight" style={{ fontFamily: 'var(--vs-font-heading)' }}>
            Start Creating AI Videos Today
          </h2>
          <p className="text-lg text-[var(--vs-text-secondary)] mb-8" style={{ fontFamily: 'var(--vs-font-body)' }}>
            100 free credits for new creators. No credit card required.
          </p>
          <Link to="/signup">
            <button className="vs-btn-primary rounded-full px-12 h-14 text-lg font-semibold hover:shadow-[0_0_40px_-8px_rgba(124,58,237,0.5)] transition-all hover:scale-[1.02]" data-testid="final-cta-btn">
              Start Creating <ArrowRight className="w-5 h-5 ml-2" />
            </button>
          </Link>
        </div>
      </section>

      {/* ═══════ FOOTER ═══════ */}
      <footer className="border-t border-[var(--vs-border-subtle)] py-12 px-4" data-testid="landing-footer">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-10">
            <div>
              <h4 className="text-sm font-semibold text-white mb-4" style={{ fontFamily: 'var(--vs-font-heading)' }}>Product</h4>
              <div className="space-y-2">
                <Link to="/app/story-video-studio" className="block text-sm text-[var(--vs-text-muted)] hover:text-white transition-colors">Create Video</Link>
                <Link to="/explore" className="block text-sm text-[var(--vs-text-muted)] hover:text-white transition-colors">Explore</Link>
                <Link to="/gallery" className="block text-sm text-[var(--vs-text-muted)] hover:text-white transition-colors">Gallery</Link>
                <Link to="/pricing" className="block text-sm text-[var(--vs-text-muted)] hover:text-white transition-colors">Pricing</Link>
              </div>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-white mb-4" style={{ fontFamily: 'var(--vs-font-heading)' }}>Create</h4>
              <div className="space-y-2">
                <Link to="/app/story-video-studio" className="block text-sm text-[var(--vs-text-muted)] hover:text-white transition-colors">Story Video</Link>
                <Link to="/app/reels" className="block text-sm text-[var(--vs-text-muted)] hover:text-white transition-colors">Reel Generator</Link>
                <Link to="/app/photo-to-comic" className="block text-sm text-[var(--vs-text-muted)] hover:text-white transition-colors">Photo to Comic</Link>
                <Link to="/app/comic-storybook" className="block text-sm text-[var(--vs-text-muted)] hover:text-white transition-colors">Comic Storybook</Link>
              </div>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-white mb-4" style={{ fontFamily: 'var(--vs-font-heading)' }}>Company</h4>
              <div className="space-y-2">
                <Link to="/blog" className="block text-sm text-[var(--vs-text-muted)] hover:text-white transition-colors">Blog</Link>
                <Link to="/contact" className="block text-sm text-[var(--vs-text-muted)] hover:text-white transition-colors">Contact</Link>
                <Link to="/reviews" className="block text-sm text-[var(--vs-text-muted)] hover:text-white transition-colors">Reviews</Link>
              </div>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-white mb-4" style={{ fontFamily: 'var(--vs-font-heading)' }}>Legal</h4>
              <div className="space-y-2">
                <Link to="/privacy" className="block text-sm text-[var(--vs-text-muted)] hover:text-white transition-colors">Privacy Policy</Link>
                <Link to="/terms" className="block text-sm text-[var(--vs-text-muted)] hover:text-white transition-colors">Terms of Service</Link>
                <Link to="/cookies" className="block text-sm text-[var(--vs-text-muted)] hover:text-white transition-colors">Cookie Policy</Link>
              </div>
            </div>
          </div>
          <div className="border-t border-[var(--vs-border-subtle)] pt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-md vs-gradient-bg flex items-center justify-center">
                <Command className="w-3 h-3 text-white" />
              </div>
              <span className="text-sm font-semibold text-[var(--vs-text-muted)]" style={{ fontFamily: 'var(--vs-font-heading)' }}>Visionary Suite</span>
            </div>
            <p className="text-xs text-[var(--vs-text-muted)]" style={{ fontFamily: 'var(--vs-font-body)' }}>
              Made for AI creators worldwide
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
