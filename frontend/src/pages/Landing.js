import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import {
  Sparkles, Clapperboard, PenLine, Wand2, Download, ArrowRight,
  Menu, X, Film, BookOpen, Image, Zap, ChevronRight, Star, Check,
  Clock, Layers, Mic, Palette, RefreshCcw, Play, AlertTriangle,
  Globe, Users
} from 'lucide-react';
import { getPricing } from '../utils/pricing';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const STORY_PROMPTS = [
  { label: 'Fantasy Adventure', text: 'A brave dragon protects a hidden village from shadow creatures, and a young girl discovers she can speak to dragons.', icon: Sparkles, color: 'indigo' },
  { label: 'Bedtime Story', text: 'A sleepy moon fairy sprinkles dream dust across the sky, helping all the forest animals drift into peaceful slumber.', icon: Star, color: 'amber' },
  { label: 'Space Exploration', text: 'Captain Nova and her robot companion explore a mysterious planet made entirely of crystals that sing when touched.', icon: Zap, color: 'cyan' },
  { label: 'Animal Friendship', text: 'A tiny mouse and a giant bear become unlikely friends when they discover they both love painting sunsets together.', icon: Palette, color: 'pink' },
  { label: 'Superhero Origin', text: 'A quiet librarian discovers that reading books aloud gives her the power to bring stories to life in the real world.', icon: BookOpen, color: 'emerald' },
  { label: 'Underwater World', text: 'A curious octopus opens an underwater school where fish learn to dance, and a shy seahorse becomes the star student.', icon: Layers, color: 'blue' },
];

const FEATURES = [
  { icon: PenLine, title: 'AI Story Writer', desc: 'Type your story or pick a template. Fantasy, bedtime, sci-fi — our AI understands any genre.', accent: 'indigo' },
  { icon: Wand2, title: 'AI Scene Generator', desc: 'Your story is intelligently split into cinematic scenes with visual prompts and narration cues.', accent: 'purple' },
  { icon: Image, title: 'AI Illustration Engine', desc: 'Each scene gets a unique, high-quality illustration in your chosen animation style.', accent: 'pink' },
  { icon: Mic, title: 'AI Voice Narration', desc: 'Natural-sounding voiceover with multiple presets matched to your story and audience.', accent: 'amber' },
  { icon: Film, title: 'AI Video Renderer', desc: 'Scenes, illustrations, and audio assembled into a polished video — no editing needed.', accent: 'emerald' },
  { icon: Clock, title: 'Ready in Minutes', desc: 'From story text to finished cinematic video in about 90 seconds. Download or share instantly.', accent: 'cyan' },
];

const STYLES = [
  { name: '2D Cartoon', desc: 'Vibrant, family-friendly', accent: 'indigo' },
  { name: 'Anime', desc: 'Ghibli-inspired art', accent: 'pink' },
  { name: '3D Animation', desc: 'Pixar-quality renders', accent: 'purple' },
  { name: 'Watercolor', desc: 'Soft storybook feel', accent: 'amber' },
  { name: 'Comic Book', desc: 'Bold outlines, dynamic', accent: 'red' },
  { name: 'Claymation', desc: 'Textured, warm tones', accent: 'emerald' },
];

export default function Landing() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [stats, setStats] = useState({ videosCreated: 12426, creatorsOnline: 12 });
  const [showcaseVideos, setShowcaseVideos] = useState([]);
  const pricing = getPricing();

  useEffect(() => {
    fetch(`${API_URL}/api/live-stats/public`)
      .then(r => r.json())
      .then(d => {
        if (d.success && d.stats) {
          setStats(prev => ({ ...prev, creatorsOnline: d.stats.creators_online || 12 }));
        }
      })
      .catch(() => {});

    fetch(`${API_URL}/api/pipeline/gallery?sort=most_remixed`)
      .then(r => r.json())
      .then(d => {
        const vids = (d.videos || []).filter(v => v.thumbnail_url).slice(0, 6);
        setShowcaseVideos(vids);
      })
      .catch(() => {});
  }, []);

  return (
    <div className="vs-page overflow-x-hidden">
      <style>{`
        .grid-bg { background-image: linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px); background-size: 80px 80px; }
        .feature-glow:hover { box-shadow: 0 0 40px -12px rgba(124,58,237,0.2); }
      `}</style>

      {/* ─── Navbar ─── */}
      <nav className="fixed top-0 left-0 right-0 z-50 vs-glass border-b border-[var(--vs-border-subtle)]" data-testid="landing-nav">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg vs-gradient-bg flex items-center justify-center">
              <Clapperboard className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-bold tracking-tight text-white" style={{ fontFamily: 'var(--vs-font-heading)' }}>Visionary Suite</span>
          </Link>
          <div className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-sm font-medium text-[var(--vs-text-muted)] hover:text-white transition-colors" style={{ fontFamily: 'var(--vs-font-body)' }}>Features</a>
            <a href="#how-it-works" className="text-sm font-medium text-[var(--vs-text-muted)] hover:text-white transition-colors" style={{ fontFamily: 'var(--vs-font-body)' }}>How It Works</a>
            <Link to="/gallery" className="text-sm font-medium text-[var(--vs-text-muted)] hover:text-white transition-colors" style={{ fontFamily: 'var(--vs-font-body)' }}>Gallery</Link>
            <Link to="/pricing" className="text-sm font-medium text-[var(--vs-text-muted)] hover:text-white transition-colors" style={{ fontFamily: 'var(--vs-font-body)' }}>Pricing</Link>
            <Link to="/login" className="text-sm font-medium text-[var(--vs-text-muted)] hover:text-white transition-colors" data-testid="nav-login-link" style={{ fontFamily: 'var(--vs-font-body)' }}>Login</Link>
          </div>
          <button className="md:hidden text-white p-2" onClick={() => setMobileMenuOpen(!mobileMenuOpen)} data-testid="mobile-menu-btn">
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-[var(--vs-border-subtle)] bg-[var(--vs-bg-base)]/95 backdrop-blur-2xl px-4 py-4 space-y-3">
            <a href="#features" className="block text-[var(--vs-text-secondary)] hover:text-white py-2" onClick={() => setMobileMenuOpen(false)}>Features</a>
            <a href="#how-it-works" className="block text-[var(--vs-text-secondary)] hover:text-white py-2" onClick={() => setMobileMenuOpen(false)}>How It Works</a>
            <Link to="/gallery" className="block text-[var(--vs-text-secondary)] hover:text-white py-2" onClick={() => setMobileMenuOpen(false)}>Gallery</Link>
            <Link to="/pricing" className="block text-[var(--vs-text-secondary)] hover:text-white py-2" onClick={() => setMobileMenuOpen(false)}>Pricing</Link>
            <Link to="/login" className="block text-[var(--vs-text-secondary)] hover:text-white py-2" onClick={() => setMobileMenuOpen(false)}>Login</Link>
          </div>
        )}
      </nav>

      {/* ─── 1. Hero Section ─── */}
      <section className="relative pt-32 pb-16 md:pt-48 md:pb-24 px-4">
        <div className="absolute inset-0 grid-bg pointer-events-none" />
        <div className="absolute top-16 left-1/3 w-[500px] h-[500px] bg-[var(--vs-primary-from)]/[0.06] rounded-full blur-[150px] pointer-events-none" />
        <div className="absolute bottom-0 right-1/3 w-[400px] h-[400px] bg-amber-500/[0.04] rounded-full blur-[120px] pointer-events-none" />

        <div className="relative max-w-5xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 vs-chip mb-8 vs-fade-up-1" data-testid="hero-tagline">
            <Sparkles className="w-4 h-4" />
            <span className="text-sm font-medium">The AI Creative Operating System</span>
          </div>

          <h1 className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-black tracking-[-0.04em] leading-[0.95] mb-6 vs-fade-up-1" data-testid="hero-heading" style={{ fontFamily: 'var(--vs-font-heading)' }}>
            <span className="text-white">Turn Any Idea Into</span><br />
            <span className="vs-gradient-text">
              Cinematic AI Content
            </span>
          </h1>

          <p className="text-base md:text-lg text-[var(--vs-text-accent)] font-semibold mb-4 vs-fade-up-2" data-testid="hero-speed-line" style={{ fontFamily: 'var(--vs-font-body)' }}>
            Videos, comics, reels — created in under 90 seconds.
          </p>

          <p className="text-lg md:text-xl text-[var(--vs-text-secondary)] max-w-2xl mx-auto leading-relaxed mb-10 vs-fade-up-2" style={{ fontFamily: 'var(--vs-font-body)' }}>
            Write a story and our AI instantly creates a fully narrated animated video with scenes, illustrations, voiceover, and editing — ready to share in minutes.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12 vs-fade-up-3">
            <Link to="/signup">
              <button className="vs-btn-primary rounded-full px-10 h-14 text-lg font-semibold hover:shadow-[0_0_40px_-8px_rgba(124,58,237,0.5)] transition-all hover:scale-[1.02]" data-testid="hero-cta-btn">
                Start Creating Free
                <ArrowRight className="w-5 h-5 ml-2" />
              </button>
            </Link>
            <Link to="/gallery">
              <button className="vs-btn-secondary rounded-full px-8 h-14 text-lg font-medium" data-testid="hero-gallery-btn">
                Explore Gallery
              </button>
            </Link>
          </div>

          <div className="flex items-center justify-center gap-6 md:gap-8 text-sm text-[var(--vs-text-muted)] font-medium vs-fade-up-4" style={{ fontFamily: 'var(--vs-font-body)' }}>
            <span className="flex items-center gap-1.5"><Check className="w-4 h-4 text-[var(--vs-success)]" /> Free to start</span>
            <span className="flex items-center gap-1.5"><Check className="w-4 h-4 text-[var(--vs-success)]" /> No credit card</span>
            <span className="flex items-center gap-1.5"><Check className="w-4 h-4 text-[var(--vs-success)]" /> Create videos in minutes</span>
          </div>
        </div>
      </section>

      {/* ─── 2. Trust Indicators / Social Proof ─── */}
      <section className="border-y border-white/[0.04] py-10 px-4" data-testid="trust-indicators">
        <div className="max-w-5xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          <div>
            <div className="text-3xl md:text-4xl font-black text-white">12,000+</div>
            <div className="text-sm text-slate-500 mt-1.5">Videos Created</div>
          </div>
          <div>
            <div className="text-3xl md:text-4xl font-black text-white flex items-center justify-center gap-1"><Globe className="w-6 h-6 text-indigo-400 inline" /> 40+</div>
            <div className="text-sm text-slate-500 mt-1.5">Countries</div>
          </div>
          <div>
            <div className="text-3xl md:text-4xl font-black text-white">6</div>
            <div className="text-sm text-slate-500 mt-1.5">Animation Styles</div>
          </div>
          <div>
            <div className="text-3xl md:text-4xl font-black text-white flex items-center justify-center gap-1"><Clock className="w-6 h-6 text-emerald-400 inline" /> ~90s</div>
            <div className="text-sm text-slate-500 mt-1.5">Videos Generated in ~90 Seconds</div>
          </div>
        </div>
      </section>

      {/* ─── 3. Problem → Solution ─── */}
      <section className="py-16 md:py-24 px-4">
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
            <div>
              <div className="inline-flex items-center gap-2 bg-red-500/10 border border-red-500/20 rounded-full px-4 py-1.5 mb-6">
                <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
                <span className="text-xs font-semibold uppercase tracking-wider text-red-300">The Problem</span>
              </div>
              <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-6 text-white" data-testid="problem-heading">
                Creating animated videos is difficult
              </h2>
              <div className="space-y-4">
                {[
                  'Video editing takes hours',
                  'Animation tools are complex',
                  'Hiring editors is expensive',
                ].map((point, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <X className="w-5 h-5 text-red-400/60 flex-shrink-0 mt-0.5" />
                    <p className="text-slate-400">{point}</p>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <div className="inline-flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-4 py-1.5 mb-6">
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-xs font-semibold uppercase tracking-wider text-emerald-300">The Solution</span>
              </div>
              <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-6 text-white" data-testid="solution-heading">
                Visionary-Suite solves this.
              </h2>
              <p className="text-slate-300 leading-relaxed mb-6">
                Write a story and our AI automatically generates scenes, illustrations, voice narration, and a finished cinematic video.
              </p>
              <div className="space-y-3">
                {[
                  'Write any story in plain text',
                  'AI handles everything else automatically',
                  'Download your video in under 90 seconds',
                ].map((point, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <Check className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                    <p className="text-slate-300">{point}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── 4. Example AI Videos ─── */}
      {showcaseVideos.length > 0 && (
        <section className="py-16 md:py-24 px-4 border-t border-white/[0.04]" data-testid="example-videos-section">
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-12">
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-indigo-400 mb-4">See What's Possible</p>
              <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight text-white mb-4">
                Example AI Videos
              </h2>
              <p className="text-lg text-slate-400 max-w-2xl mx-auto">
                Every video below was created on Visionary Suite. Write a story and our AI does the rest.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {showcaseVideos.map((vid, i) => (
                <div key={i} className="group rounded-2xl border border-white/[0.06] bg-white/[0.015] overflow-hidden hover:border-white/[0.12] transition-all" data-testid={`showcase-card-${i}`}>
                  <div className="relative aspect-video bg-slate-900 overflow-hidden">
                    <img
                      src={vid.thumbnail_url}
                      alt={vid.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                      loading="lazy"
                    />
                    <div className="absolute inset-0 bg-black/30 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                      <div className="w-14 h-14 rounded-full bg-white/20 backdrop-blur-md flex items-center justify-center">
                        <Play className="w-6 h-6 text-white ml-1" fill="white" />
                      </div>
                    </div>
                    {vid.remix_count > 0 && (
                      <div className="absolute top-3 right-3 bg-black/60 backdrop-blur-sm text-white text-xs font-medium px-2.5 py-1 rounded-full flex items-center gap-1">
                        <RefreshCcw className="w-3 h-3" /> {vid.remix_count} remixes
                      </div>
                    )}
                  </div>
                  <div className="p-5">
                    <h3 className="font-semibold text-white mb-1 truncate">{vid.title}</h3>
                    <p className="text-xs text-slate-500 capitalize mb-3">{(vid.animation_style || '').replace(/_/g, ' ')}</p>
                    <Link
                      to={`/signup?prompt=${encodeURIComponent(vid.story_text || vid.title)}`}
                      className="inline-flex items-center gap-1.5 text-sm text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
                      data-testid={`showcase-remix-${i}`}
                    >
                      <RefreshCcw className="w-3.5 h-3.5" /> Remix This
                    </Link>
                  </div>
                </div>
              ))}
            </div>

            <div className="text-center mt-10">
              <Link to="/gallery">
                <Button variant="ghost" className="text-slate-300 hover:text-white hover:bg-white/[0.04] rounded-full px-8 py-4 text-base font-medium" data-testid="view-all-gallery-btn">
                  View All Creations
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </Link>
            </div>
          </div>
        </section>
      )}

      {/* ─── 5. Features ─── */}
      <section id="features" className="py-16 md:py-24 px-4 border-t border-white/[0.04]">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-indigo-400 mb-4">The AI Pipeline</p>
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight text-white mb-4">
              Five AI stages. One finished video.
            </h2>
            <p className="text-lg text-slate-400 max-w-2xl mx-auto">Every video passes through our 5-stage AI pipeline — from text analysis to final render.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map((f, i) => {
              const Icon = f.icon;
              return (
                <div
                  key={i}
                  className="group relative rounded-2xl border border-white/[0.05] bg-white/[0.015] p-8 transition-all duration-300 hover:border-white/[0.12] hover:bg-white/[0.03] feature-glow"
                  data-testid={`feature-card-${i}`}
                >
                  <div className={`w-12 h-12 rounded-xl bg-${f.accent}-500/10 border border-${f.accent}-500/20 flex items-center justify-center mb-6`}>
                    <Icon className={`w-6 h-6 text-${f.accent}-400`} strokeWidth={1.5} />
                  </div>
                  <h3 className="text-xl font-bold tracking-tight mb-3 text-white">{f.title}</h3>
                  <p className="text-slate-400 leading-relaxed text-[15px]">{f.desc}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ─── 6. How It Works ─── */}
      <section id="how-it-works" className="py-16 md:py-24 px-4 border-t border-white/[0.04]">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-indigo-400 mb-4">How It Works</p>
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight text-white">Three simple steps</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { step: '01', icon: PenLine, title: 'Write Your Story', desc: 'Type any story — bedtime tale, fantasy, sci-fi, educational. Or pick a ready-made template.' },
              { step: '02', icon: Wand2, title: 'AI Creates the Video', desc: 'Our AI splits your story into scenes, generates illustrations, records voiceover, and renders everything.' },
              { step: '03', icon: Download, title: 'Download or Share', desc: 'Your video is ready in about 90 seconds. Download, share on social media, or remix it.' },
            ].map(({ step, icon: Icon, title, desc }) => (
              <div key={step} className="relative">
                <span className="text-[120px] font-black text-white/[0.02] absolute -top-10 -left-4 select-none leading-none">{step}</span>
                <div className="relative">
                  <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mb-6">
                    <Icon className="w-6 h-6 text-indigo-400" strokeWidth={1.5} />
                  </div>
                  <h3 className="text-xl font-bold tracking-tight mb-3 text-white">{title}</h3>
                  <p className="text-slate-400 leading-relaxed">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── 6b. Watch a Story Become a Video ─── */}
      {showcaseVideos.length > 0 && (
        <section className="py-16 md:py-24 px-4 border-t border-white/[0.04]" data-testid="demo-video-section">
          <div className="max-w-4xl mx-auto text-center">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-amber-400 mb-4">See It In Action</p>
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight text-white mb-4">
              Watch a Story Become a Video
            </h2>
            <p className="text-lg text-slate-400 max-w-xl mx-auto mb-10">
              This entire video was generated from a single story using Visionary Suite.
            </p>

            <div className="relative group rounded-2xl border border-white/[0.08] bg-white/[0.02] overflow-hidden max-w-3xl mx-auto">
              <div className="relative aspect-video bg-slate-900">
                <img
                  src={showcaseVideos[0]?.thumbnail_url}
                  alt={showcaseVideos[0]?.title || 'Demo video'}
                  className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/20 flex flex-col items-center justify-center gap-4">
                  <div className="w-20 h-20 rounded-full bg-white/15 backdrop-blur-md flex items-center justify-center border border-white/20 group-hover:bg-white/25 group-hover:scale-110 transition-all cursor-pointer">
                    <Play className="w-8 h-8 text-white ml-1" fill="white" />
                  </div>
                  <p className="text-white/80 text-sm font-medium">{showcaseVideos[0]?.title || 'AI Generated Story Video'}</p>
                </div>
              </div>
              <div className="p-6 flex items-center justify-between">
                <div className="text-left">
                  <p className="text-white font-semibold">{showcaseVideos[0]?.title}</p>
                  <p className="text-xs text-slate-500 capitalize">{(showcaseVideos[0]?.animation_style || '').replace(/_/g, ' ')} style</p>
                </div>
                <Link to={`/signup?prompt=${encodeURIComponent(showcaseVideos[0]?.story_text || '')}`}>
                  <Button className="bg-indigo-600 hover:bg-indigo-500 text-white rounded-full px-6 py-3 text-sm font-semibold" data-testid="demo-create-btn">
                    Create Your Version <ArrowRight className="w-4 h-4 ml-1.5" />
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* ─── 7. Animation Styles ─── */}
      <section className="py-16 md:py-24 px-4 border-t border-white/[0.04]">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-10">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-indigo-400 mb-4">Visual Styles</p>
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight text-white mb-4">
              Choose your art style
            </h2>
            <p className="text-lg text-slate-400 max-w-xl mx-auto">Six distinct animation styles, each crafted for different story moods and audiences.</p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {STYLES.map((s, i) => (
              <div key={i} className={`rounded-2xl border border-white/[0.06] bg-white/[0.02] p-6 hover:border-${s.accent}-500/30 hover:bg-white/[0.04] transition-all`} data-testid={`style-card-${i}`}>
                <Palette className={`w-5 h-5 text-${s.accent}-400 mb-3`} />
                <h3 className="font-bold text-white text-lg">{s.name}</h3>
                <p className="text-sm text-slate-500 mt-1">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── 8. Story Prompts ─── */}
      <section className="py-16 md:py-24 px-4 border-t border-white/[0.04]">
        <div className="max-w-7xl mx-auto">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-indigo-400 mb-4">Try It Now</p>
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight mb-4 text-white">Pick a story, create a video</h2>
          <p className="text-lg text-slate-400 max-w-2xl mb-12">Click any prompt below, then sign up to generate your AI video instantly.</p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {STORY_PROMPTS.map((prompt, i) => {
              const Icon = prompt.icon;
              return (
                <Link
                  key={i}
                  to={`/signup?prompt=${encodeURIComponent(prompt.text)}`}
                  className={`group rounded-2xl border border-white/[0.05] bg-white/[0.015] p-6 hover:border-${prompt.color}-500/30 hover:bg-white/[0.04] transition-all`}
                  data-testid={`prompt-${i}`}
                >
                  <div className="flex items-start gap-4">
                    <div className={`w-10 h-10 rounded-lg bg-${prompt.color}-500/10 flex items-center justify-center flex-shrink-0`}>
                      <Icon className={`w-5 h-5 text-${prompt.color}-400`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-white mb-1.5 group-hover:text-indigo-300 transition-colors">{prompt.label}</h3>
                      <p className="text-sm text-slate-500 leading-relaxed line-clamp-2">{prompt.text}</p>
                    </div>
                    <ChevronRight className="w-5 h-5 text-slate-700 group-hover:text-indigo-400 group-hover:translate-x-1 transition-all flex-shrink-0 mt-1" />
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      </section>

      {/* ─── 9. Testimonials ─── */}
      <section className="py-16 md:py-24 px-4 border-t border-white/[0.04]" data-testid="testimonials-section">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-amber-400 mb-4">Creator Feedback</p>
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight mb-4 text-white">Loved by creators worldwide</h2>
            <div className="flex items-center justify-center gap-2 mt-4">
              <div className="flex">
                {[1,2,3,4].map(i => <Star key={i} className="w-5 h-5 fill-amber-400 text-amber-400" />)}
                <Star className="w-5 h-5 text-amber-400" style={{ clipPath: 'inset(0 60% 0 0)' }} fill="currentColor" />
              </div>
              <span className="text-lg font-bold text-white ml-1">4.4 / 5</span>
              <span className="text-sm text-slate-400 ml-1">Average Rating</span>
            </div>
            <p className="text-sm text-slate-500 mt-1">Based on feedback from early creators worldwide</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {[
              { name: 'Emily Carter', country: 'United States', stars: 5, text: 'I was surprised how quickly this works. I typed a short story and it turned into a narrated animated video in minutes.' },
              { name: 'Lucas Fernandes', country: 'Brazil', stars: 4, text: 'I run a small YouTube channel and Visionary-Suite helps me create story videos much faster than traditional editing tools.' },
              { name: 'Priya Sharma', country: 'India', stars: 5, text: 'I started using Visionary-Suite to create educational stories for my students. The visuals and narration make lessons much more engaging.' },
              { name: 'David Walker', country: 'United Kingdom', stars: 4, text: 'As a writer, seeing my stories turn into animated videos is amazing. The concept is really exciting.' },
              { name: 'Kenji Tanaka', country: 'Japan', stars: 5, text: 'I tested many AI tools recently and this one is quite unique. The full pipeline from story to video is impressive.' },
              { name: 'Anna Müller', country: 'Germany', stars: 4, text: 'The different animation styles are my favorite part. It allows me to experiment creatively.' },
              { name: 'Carlos Rodriguez', country: 'Mexico', stars: 5, text: 'The workflow is simple. Write a story, choose a style, and the AI generates the video.' },
              { name: 'Fatima Hassan', country: 'UAE', stars: 4, text: 'This platform makes storytelling visual without needing advanced editing skills.' },
              { name: 'Michael Thompson', country: 'Canada', stars: 5, text: 'I think tools like Visionary-Suite will become a big part of the future of content creation.' },
              { name: 'Sofia Rossi', country: 'Italy', stars: 4, text: 'I created a fantasy story video and shared it with friends. They loved it.' },
            ].map((t, i) => (
              <div
                key={i}
                className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-5 hover:border-white/[0.12] transition-colors"
                data-testid={`testimonial-card-${i}`}
              >
                <div className="flex mb-3">
                  {Array.from({ length: 5 }, (_, s) => (
                    <Star key={s} className={`w-4 h-4 ${s < t.stars ? 'fill-amber-400 text-amber-400' : 'text-slate-600'}`} />
                  ))}
                </div>
                <p className="text-sm text-slate-300 leading-relaxed mb-4">"{t.text}"</p>
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-xs font-bold">
                    {t.name.split(' ').map(n => n[0]).join('')}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white">{t.name}</p>
                    <p className="text-xs text-slate-500">{t.country}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── 10. Pricing ─── */}
      <section className="py-16 md:py-24 px-4 border-t border-white/[0.04]">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-10">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-indigo-400 mb-4">Simple Pricing</p>
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight mb-4 text-white">Start free, scale when ready</h2>
            <p className="text-lg text-slate-400">Subscribe monthly or buy credits as you go.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="flex flex-col rounded-2xl border border-white/[0.06] bg-white/[0.015] p-8">
              <h3 className="text-xl font-bold mb-2 text-white">Free</h3>
              <div className="text-4xl font-black mb-1 text-white">{pricing.symbol}0</div>
              <p className="text-slate-500 mb-6">to get started</p>
              <ul className="space-y-3 mb-8 flex-1">
                <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400" /> Browse all features</li>
                <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400" /> Preview AI tools</li>
                <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400" /> No credit card required</li>
              </ul>
              <Link to="/signup">
                <Button className="w-full bg-white/[0.04] hover:bg-white/[0.08] text-white border border-white/[0.08] rounded-full py-3 font-medium" data-testid="pricing-free-btn">Get Started</Button>
              </Link>
            </div>

            <div className="flex flex-col rounded-2xl border-2 border-indigo-500/40 bg-indigo-500/[0.04] p-8 relative">
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-indigo-600 text-white text-xs font-bold px-4 py-1 rounded-full">POPULAR</div>
              <h3 className="text-xl font-bold mb-2 text-white">Creator</h3>
              <div className="flex items-baseline gap-1">
                <span className="text-4xl font-black text-white">{pricing.symbol}{pricing.creator.price.toLocaleString()}</span>
                <span className="text-slate-500">/month</span>
              </div>
              <p className="text-indigo-300/80 text-sm mt-1 mb-6">{pricing.creator.credits} credits/month</p>
              <ul className="space-y-3 mb-8 flex-1">
                <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400" /> Access to core AI tools</li>
                <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400" /> All animation styles</li>
                <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400" /> Priority rendering</li>
              </ul>
              <Link to="/pricing">
                <Button className="w-full bg-indigo-600 hover:bg-indigo-500 text-white rounded-full py-3 font-semibold hover:shadow-[0_0_24px_-4px_rgba(99,102,241,0.5)]" data-testid="pricing-creator-btn">Subscribe</Button>
              </Link>
            </div>

            <div className="flex flex-col rounded-2xl border border-white/[0.06] bg-white/[0.015] p-8">
              <h3 className="text-xl font-bold mb-2 text-white">Pro</h3>
              <div className="flex items-baseline gap-1">
                <span className="text-4xl font-black text-white">{pricing.symbol}{pricing.pro.price.toLocaleString()}</span>
                <span className="text-slate-500">/month</span>
              </div>
              <p className="text-amber-300/80 text-sm mt-1 mb-6">{pricing.pro.credits} credits/month</p>
              <ul className="space-y-3 mb-8 flex-1">
                <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400" /> All tools unlocked</li>
                <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400" /> HD downloads</li>
                <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400" /> No watermark</li>
                <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400" /> Priority support</li>
              </ul>
              <Link to="/pricing">
                <Button className="w-full bg-white/[0.04] hover:bg-white/[0.08] text-white border border-white/[0.08] rounded-full py-3 font-medium" data-testid="pricing-pro-btn">Subscribe</Button>
              </Link>
            </div>
          </div>

          <p className="text-center text-sm text-slate-600 mt-8">
            Need more? <Link to="/pricing" className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2">Buy credit top-ups</Link> starting from {pricing.topup.label} for {pricing.topup.credits} credits.
          </p>
        </div>
      </section>

      {/* ─── 10. Remix / Growth Feature ─── */}
      <section className="py-16 md:py-24 px-4 border-t border-white/[0.04]">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-pink-500/10 border border-pink-500/20 rounded-full px-5 py-2 mb-8">
            <RefreshCcw className="w-4 h-4 text-pink-400" />
            <span className="text-sm font-medium text-pink-300">Viral Growth Feature</span>
          </div>
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight mb-6 text-white">
            Remix any video
          </h2>
          <p className="text-lg text-slate-400 max-w-xl mx-auto mb-4">
            See a video you love in the gallery?
          </p>
          <p className="text-base text-slate-300 max-w-lg mx-auto mb-10">
            Click <span className="text-pink-300 font-semibold">Remix</span> to create your own version with a different story, style, or narration. This is how creativity spreads across Visionary Suite.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link to="/gallery">
              <Button className="bg-pink-600 hover:bg-pink-500 text-white rounded-full px-8 py-4 text-lg font-semibold hover:shadow-[0_0_24px_-4px_rgba(236,72,153,0.5)]" data-testid="remix-cta-btn">
                Browse Gallery
                <ArrowRight className="w-5 h-5 ml-2" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* ─── More Tools ─── */}
      <section className="py-16 md:py-24 px-4 border-t border-white/[0.04]">
        <div className="max-w-7xl mx-auto">
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-slate-600 mb-4">More Creator Tools</p>
          <h2 className="text-2xl md:text-3xl font-semibold tracking-tight text-slate-300 mb-12">Everything else you need</h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {[
              { icon: Zap, title: 'Reel Scripts', desc: 'Viral hooks, scripts & hashtags', cost: '10 credits', href: '/app/reel-generator' },
              { icon: Image, title: 'Photo to Comic', desc: 'Transform photos into comics', cost: '15 credits', href: '/app/photo-to-comic' },
              { icon: Film, title: 'GIF Creator', desc: 'Animated reaction GIFs', cost: '10 credits', href: '/app/gif-maker' },
              { icon: BookOpen, title: 'Comic Storybook', desc: 'Illustrated storybooks', cost: '20+ credits', href: '/app/comic-storybook' },
            ].map(({ icon: Icon, title, desc, cost, href }) => (
              <Link key={title} to={href} className="group rounded-2xl border border-white/[0.04] bg-white/[0.01] p-6 hover:border-white/[0.1] hover:bg-white/[0.03] transition-all">
                <Icon className="w-5 h-5 text-slate-500 group-hover:text-indigo-400 transition-colors mb-4" strokeWidth={1.5} />
                <h3 className="font-semibold text-white mb-1">{title}</h3>
                <p className="text-sm text-slate-600 mb-3">{desc}</p>
                <span className="text-xs text-slate-700">{cost}</span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Final CTA ─── */}
      <section className="py-20 md:py-32 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight mb-6 text-white" data-testid="final-cta-heading">
            Your Story Deserves to Be Seen
          </h2>
          <p className="text-lg text-slate-400 mb-10 max-w-xl mx-auto">
            Join creators around the world turning their imagination into cinematic AI videos.
          </p>
          <Link to="/signup">
            <Button className="bg-indigo-600 hover:bg-indigo-500 text-white rounded-full px-10 py-5 text-lg font-semibold transition-all hover:scale-[1.02] hover:shadow-[0_0_40px_-8px_rgba(99,102,241,0.5)]" data-testid="final-cta-btn">
              Create Your First Video
              <ArrowRight className="w-5 h-5 ml-2" />
            </Button>
          </Link>
          <div className="flex items-center justify-center gap-6 mt-8 text-sm text-slate-500">
            <span className="flex items-center gap-1.5"><Users className="w-4 h-4" /> {stats.videosCreated.toLocaleString()}+ videos created</span>
            <span className="flex items-center gap-1.5"><Globe className="w-4 h-4" /> Creators in 40+ countries</span>
          </div>
        </div>
      </section>

      {/* ─── Footer ─── */}
      <footer className="border-t border-white/[0.04] py-12 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Clapperboard className="w-5 h-5 text-indigo-400" />
                <span className="font-bold text-white">Visionary Suite</span>
              </div>
              <p className="text-sm text-slate-600">AI-powered story-to-video engine.</p>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-slate-400 mb-3">Product</h4>
              <div className="space-y-2 text-sm text-slate-600">
                <Link to="/signup" className="block hover:text-white transition-colors">Create Video</Link>
                <Link to="/gallery" className="block hover:text-white transition-colors">Gallery</Link>
                <Link to="/pricing" className="block hover:text-white transition-colors">Pricing</Link>
              </div>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-slate-400 mb-3">Resources</h4>
              <div className="space-y-2 text-sm text-slate-600">
                <Link to="/blog" className="block hover:text-white transition-colors">Blog</Link>
                <Link to="/user-manual" className="block hover:text-white transition-colors">Help Center</Link>
                <Link to="/contact" className="block hover:text-white transition-colors">Contact</Link>
              </div>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-slate-400 mb-3">Legal</h4>
              <div className="space-y-2 text-sm text-slate-600">
                <Link to="/privacy-policy" className="block hover:text-white transition-colors">Privacy Policy</Link>
                <Link to="/terms-of-service" className="block hover:text-white transition-colors">Terms of Service</Link>
                <Link to="/cookie-policy" className="block hover:text-white transition-colors">Cookies</Link>
              </div>
            </div>
          </div>
          <div className="border-t border-white/[0.04] pt-8 text-center text-sm text-slate-700">
            &copy; 2026 Visionary Suite. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
}
