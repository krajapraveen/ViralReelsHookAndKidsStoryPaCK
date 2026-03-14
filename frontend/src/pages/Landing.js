import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import {
  Sparkles, Clapperboard, PenLine, Wand2, Download, ArrowRight,
  Menu, X, Film, BookOpen, Image, Zap, ChevronRight, Star, Check,
  Clock, Layers, Mic, Palette, Shield, RefreshCcw
} from 'lucide-react';

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
  { icon: PenLine, title: 'Write Any Story', desc: 'Type a story or pick from our templates. Fantasy, bedtime, sci-fi — any genre works.', accent: 'indigo' },
  { icon: Wand2, title: 'AI Scene Generation', desc: 'GPT breaks your story into cinematic scenes with visual prompts and dialogue automatically.', accent: 'purple' },
  { icon: Image, title: 'AI Image Creation', desc: 'Each scene gets a unique, high-quality illustration in your chosen animation style.', accent: 'pink' },
  { icon: Mic, title: 'Professional Voiceover', desc: 'Natural-sounding AI narration with multiple voice presets matched to your audience.', accent: 'amber' },
  { icon: Film, title: 'Video Rendering', desc: 'Scenes, images, and audio assembled into a polished video — ready to download.', accent: 'emerald' },
  { icon: Clock, title: 'Under 90 Seconds', desc: 'From story text to finished video in about 90 seconds. No editing needed.', accent: 'cyan' },
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
  const [stats, setStats] = useState({ videosCreated: 36, creatorsOnline: 12 });

  useEffect(() => {
    fetch(`${API_URL}/api/live-stats/public`)
      .then(r => r.json())
      .then(d => {
        if (d.success && d.stats) {
          setStats({ videosCreated: d.stats.content_created_today || 36, creatorsOnline: d.stats.creators_online || 12 });
        }
      })
      .catch(() => {});
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950/80 to-slate-950 text-white overflow-x-hidden">
      <style>{`
        .grid-bg { background-image: linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px); background-size: 80px 80px; }
        @keyframes fadeUp { from { opacity: 0; transform: translateY(24px); } to { opacity: 1; transform: translateY(0); } }
        .fade-up { animation: fadeUp 0.7s ease-out forwards; }
        .fade-up-2 { animation: fadeUp 0.7s ease-out 0.15s forwards; opacity: 0; }
        .fade-up-3 { animation: fadeUp 0.7s ease-out 0.3s forwards; opacity: 0; }
        .feature-glow:hover { box-shadow: 0 0 40px -12px rgba(99,102,241,0.15); }
      `}</style>

      {/* Navbar */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/[0.04] bg-[#06060b]/80 backdrop-blur-2xl" data-testid="landing-nav">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2.5">
            <Clapperboard className="w-6 h-6 text-indigo-400" />
            <span className="text-lg font-bold tracking-tight text-white">Visionary Suite</span>
          </Link>
          <div className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-sm font-medium text-slate-400 hover:text-white transition-colors">Features</a>
            <a href="#how-it-works" className="text-sm font-medium text-slate-400 hover:text-white transition-colors">How It Works</a>
            <Link to="/gallery" className="text-sm font-medium text-slate-400 hover:text-white transition-colors">Gallery</Link>
            <Link to="/pricing" className="text-sm font-medium text-slate-400 hover:text-white transition-colors">Pricing</Link>
            <Link to="/login" className="text-sm font-medium text-slate-400 hover:text-white transition-colors" data-testid="nav-login-link">Login</Link>
            <Link to="/signup">
              <Button className="bg-indigo-600 hover:bg-indigo-500 text-white rounded-full px-6 py-2 text-sm font-semibold transition-all hover:shadow-[0_0_24px_-4px_rgba(99,102,241,0.5)]" data-testid="nav-signup-btn">
                Start Free
              </Button>
            </Link>
          </div>
          <button className="md:hidden text-white p-2" onClick={() => setMobileMenuOpen(!mobileMenuOpen)} data-testid="mobile-menu-btn">
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-white/[0.04] bg-[#06060b]/95 backdrop-blur-2xl px-4 py-4 space-y-3">
            <a href="#features" className="block text-slate-300 hover:text-white py-2" onClick={() => setMobileMenuOpen(false)}>Features</a>
            <a href="#how-it-works" className="block text-slate-300 hover:text-white py-2" onClick={() => setMobileMenuOpen(false)}>How It Works</a>
            <Link to="/gallery" className="block text-slate-300 hover:text-white py-2" onClick={() => setMobileMenuOpen(false)}>Gallery</Link>
            <Link to="/pricing" className="block text-slate-300 hover:text-white py-2" onClick={() => setMobileMenuOpen(false)}>Pricing</Link>
            <Link to="/login" className="block text-slate-300 hover:text-white py-2" onClick={() => setMobileMenuOpen(false)}>Login</Link>
            <Link to="/signup" className="block" onClick={() => setMobileMenuOpen(false)}>
              <Button className="w-full bg-indigo-600 hover:bg-indigo-500 text-white rounded-full font-semibold">Start Free</Button>
            </Link>
          </div>
        )}
      </nav>

      {/* Hero */}
      <section className="relative pt-32 pb-20 md:pt-48 md:pb-32 px-4">
        <div className="absolute inset-0 grid-bg pointer-events-none" />
        <div className="absolute top-16 left-1/3 w-[500px] h-[500px] bg-indigo-600/[0.06] rounded-full blur-[150px] pointer-events-none" />
        <div className="absolute bottom-0 right-1/3 w-[400px] h-[400px] bg-amber-500/[0.04] rounded-full blur-[120px] pointer-events-none" />

        <div className="relative max-w-5xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-white/[0.04] border border-white/[0.06] rounded-full px-5 py-2 mb-8 fade-up" data-testid="hero-tagline">
            <Sparkles className="w-4 h-4 text-indigo-400" />
            <span className="text-sm font-medium text-slate-300">AI Story-to-Video Engine</span>
          </div>

          <h1 className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-black tracking-[-0.04em] leading-[0.95] mb-8 fade-up" data-testid="hero-heading">
            <span className="text-white">Stories become</span><br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-300 via-violet-300 to-amber-200">
              cinematic videos
            </span>
          </h1>

          <p className="text-lg md:text-xl text-slate-300/90 max-w-2xl mx-auto leading-relaxed mb-10 fade-up-2">
            Write any story. Our AI generates scenes, creates images, adds voiceover,
            and renders a finished video — all in under 90 seconds.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12 fade-up-3">
            <Link to="/signup">
              <Button className="bg-indigo-600 hover:bg-indigo-500 text-white rounded-full px-10 py-5 text-lg font-semibold transition-all hover:scale-[1.02] hover:shadow-[0_0_40px_-8px_rgba(99,102,241,0.5)]" data-testid="hero-cta-btn">
                Create Your First Video
                <ArrowRight className="w-5 h-5 ml-2" />
              </Button>
            </Link>
            <Link to="/gallery">
              <Button variant="ghost" className="text-slate-300 hover:text-white hover:bg-white/[0.04] rounded-full px-8 py-5 text-lg font-medium" data-testid="hero-gallery-btn">
                View Gallery
              </Button>
            </Link>
          </div>

          <div className="flex items-center justify-center gap-6 md:gap-8 text-sm text-slate-400 font-medium fade-up-3">
            <span className="flex items-center gap-1.5"><Check className="w-4 h-4 text-emerald-400" /> 10 free credits</span>
            <span className="flex items-center gap-1.5"><Check className="w-4 h-4 text-emerald-400" /> No credit card</span>
            <span className="flex items-center gap-1.5"><Check className="w-4 h-4 text-emerald-400" /> Cancel anytime</span>
          </div>
        </div>
      </section>

      {/* Stats Bar */}
      <section className="border-y border-white/[0.04] py-10 px-4">
        <div className="max-w-5xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          <div>
            <div className="text-3xl md:text-4xl font-black text-white">{stats.videosCreated}+</div>
            <div className="text-sm text-slate-500 mt-1.5">Videos Created</div>
          </div>
          <div>
            <div className="text-3xl md:text-4xl font-black text-white">90s</div>
            <div className="text-sm text-slate-500 mt-1.5">Generation Time</div>
          </div>
          <div>
            <div className="text-3xl md:text-4xl font-black text-white">6</div>
            <div className="text-sm text-slate-500 mt-1.5">Animation Styles</div>
          </div>
          <div>
            <div className="text-3xl md:text-4xl font-black text-white">5</div>
            <div className="text-sm text-slate-500 mt-1.5">AI Pipeline Stages</div>
          </div>
        </div>
      </section>

      {/* Features — THE CORE SECTION */}
      <section id="features" className="py-24 md:py-36 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-20">
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

      {/* Animation Styles */}
      <section className="py-24 md:py-32 px-4 border-t border-white/[0.04]">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
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

      {/* How It Works */}
      <section id="how-it-works" className="py-24 md:py-32 px-4 border-t border-white/[0.04]">
        <div className="max-w-7xl mx-auto">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-indigo-400 mb-4">How It Works</p>
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight mb-20 text-white">Three steps to a finished video</h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { step: '01', icon: PenLine, title: 'Write Your Story', desc: 'Type any story or pick a template. A bedtime tale, fantasy adventure, educational lesson — anything goes.' },
              { step: '02', icon: Wand2, title: 'AI Does Everything', desc: 'Scene splitting, image generation, voiceover recording, and video rendering — fully automated.' },
              { step: '03', icon: Download, title: 'Download & Share', desc: 'Get your finished video in under 90 seconds. Download, share on social media, or remix it.' },
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

      {/* Story Prompts */}
      <section className="py-24 md:py-32 px-4 border-t border-white/[0.04]">
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

      {/* Pricing */}
      <section className="py-24 md:py-32 px-4 border-t border-white/[0.04]">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-indigo-400 mb-4">Simple Pricing</p>
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight mb-4 text-white">Start free, scale when ready</h2>
            <p className="text-lg text-slate-400">Subscribe monthly or buy credits as you go.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="flex flex-col rounded-2xl border border-white/[0.06] bg-white/[0.015] p-8">
              <h3 className="text-xl font-bold mb-2 text-white">Free</h3>
              <div className="text-4xl font-black mb-1 text-white">10</div>
              <p className="text-slate-500 mb-6">credits to start</p>
              <ul className="space-y-3 mb-8 flex-1">
                <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400" /> 1 Story Video</li>
                <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400" /> All features unlocked</li>
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
                <span className="text-4xl font-black text-white">$9</span>
                <span className="text-slate-500">/month</span>
              </div>
              <p className="text-indigo-300/80 text-sm mt-1 mb-6">100 credits/month</p>
              <ul className="space-y-3 mb-8 flex-1">
                <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400" /> ~5 Story Videos</li>
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
                <span className="text-4xl font-black text-white">$19</span>
                <span className="text-slate-500">/month</span>
              </div>
              <p className="text-amber-300/80 text-sm mt-1 mb-6">250 credits/month</p>
              <ul className="space-y-3 mb-8 flex-1">
                <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400" /> ~12 Story Videos</li>
                <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400" /> No watermark</li>
                <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400" /> Gallery featured</li>
                <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400" /> Priority support</li>
              </ul>
              <Link to="/pricing">
                <Button className="w-full bg-white/[0.04] hover:bg-white/[0.08] text-white border border-white/[0.08] rounded-full py-3 font-medium" data-testid="pricing-pro-btn">Subscribe</Button>
              </Link>
            </div>
          </div>

          <p className="text-center text-sm text-slate-600 mt-8">
            Need more? <Link to="/pricing" className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2">Buy credit top-ups</Link> starting from $5 for 50 credits.
          </p>
        </div>
      </section>

      {/* Remix / Growth Feature */}
      <section className="py-24 md:py-32 px-4 border-t border-white/[0.04]">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-pink-500/10 border border-pink-500/20 rounded-full px-5 py-2 mb-8">
            <RefreshCcw className="w-4 h-4 text-pink-400" />
            <span className="text-sm font-medium text-pink-300">Viral Growth Feature</span>
          </div>
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight mb-6 text-white">
            Remix any video
          </h2>
          <p className="text-lg text-slate-400 max-w-xl mx-auto mb-10">
            See a video you love in our gallery? Hit "Remix" to create your own version with a different story twist, style, or voice. It's how great stories spread.
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

      {/* More Tools */}
      <section className="py-24 md:py-32 px-4 border-t border-white/[0.04]">
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

      {/* Final CTA */}
      <section className="py-24 md:py-32 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight mb-6 text-white">
            Your story deserves to be seen
          </h2>
          <p className="text-lg text-slate-400 mb-10 max-w-xl mx-auto">
            Join creators turning stories into AI videos. Start with 10 free credits — no strings attached.
          </p>
          <Link to="/signup">
            <Button className="bg-indigo-600 hover:bg-indigo-500 text-white rounded-full px-10 py-5 text-lg font-semibold transition-all hover:scale-[1.02] hover:shadow-[0_0_40px_-8px_rgba(99,102,241,0.5)]" data-testid="final-cta-btn">
              Create Your First Video
              <ArrowRight className="w-5 h-5 ml-2" />
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
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
