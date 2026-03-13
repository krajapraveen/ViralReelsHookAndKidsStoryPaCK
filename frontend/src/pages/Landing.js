import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import {
  Play, Sparkles, Clapperboard, PenLine, Wand2, Download, ArrowRight,
  Menu, X, Film, BookOpen, Image, Zap, ChevronRight, Clock, Star, Check, RefreshCcw
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const STORY_PROMPTS = [
  { label: 'Fantasy Adventure', text: 'A brave dragon protects a hidden village from shadow creatures, and a young girl discovers she can speak to dragons.', icon: '🐉' },
  { label: 'Bedtime Story', text: 'A sleepy moon fairy sprinkles dream dust across the sky, helping all the forest animals drift into peaceful slumber.', icon: '🌙' },
  { label: 'Space Exploration', text: 'Captain Nova and her robot companion explore a mysterious planet made entirely of crystals that sing when touched.', icon: '🚀' },
  { label: 'Animal Friendship', text: 'A tiny mouse and a giant bear become unlikely friends when they discover they both love painting sunsets together.', icon: '🐻' },
  { label: 'Superhero Origin', text: 'A quiet librarian discovers that reading books aloud gives her the power to bring stories to life in the real world.', icon: '📖' },
  { label: 'Underwater World', text: 'A curious octopus opens an underwater school where fish learn to dance, and a shy seahorse becomes the star student.', icon: '🌊' },
];

export default function Landing() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [galleryVideos, setGalleryVideos] = useState([]);
  const [stats, setStats] = useState({ videosCreated: 36, creatorsOnline: 12 });
  const [selectedPrompt, setSelectedPrompt] = useState(null);

  useEffect(() => {
    fetch(`${API_URL}/api/pipeline/gallery`)
      .then(r => r.json())
      .then(d => { if (d.videos) setGalleryVideos(d.videos.slice(0, 6)); })
      .catch(() => {});

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
    <div className="min-h-screen bg-[#0a0a0f] text-white overflow-x-hidden" style={{ fontFamily: "'Inter', system-ui, sans-serif" }}>
      {/* CSS variables for the design system */}
      <style>{`
        .landing-glow { background: radial-gradient(600px circle at var(--mx, 50%) var(--my, 30%), rgba(99,102,241,0.08), transparent 60%); }
        .hero-grid { background-image: linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px); background-size: 60px 60px; }
        @keyframes float { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }
        .float-anim { animation: float 6s ease-in-out infinite; }
      `}</style>

      {/* Navbar */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/[0.06] bg-[#0a0a0f]/80 backdrop-blur-2xl" data-testid="landing-nav">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2.5">
            <Clapperboard className="w-6 h-6 text-indigo-400" />
            <span className="text-lg font-bold tracking-tight text-white">Visionary Suite</span>
          </Link>

          <div className="hidden md:flex items-center gap-8">
            <a href="#gallery" className="text-sm font-medium text-slate-300 hover:text-white transition-colors">Gallery</a>
            <a href="#how-it-works" className="text-sm font-medium text-slate-300 hover:text-white transition-colors">How It Works</a>
            <Link to="/pricing" className="text-sm font-medium text-slate-300 hover:text-white transition-colors">Pricing</Link>
            <Link to="/login" className="text-sm font-medium text-slate-300 hover:text-white transition-colors" data-testid="nav-login-link">Login</Link>
            <Link to="/signup">
              <Button className="bg-indigo-600 hover:bg-indigo-500 text-white rounded-full px-6 py-2 text-sm font-semibold transition-all hover:shadow-[0_0_24px_-4px_rgba(99,102,241,0.5)]" data-testid="nav-signup-btn">
                Start Creating
              </Button>
            </Link>
          </div>

          <button className="md:hidden text-white p-2" onClick={() => setMobileMenuOpen(!mobileMenuOpen)} data-testid="mobile-menu-btn">
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>

        {mobileMenuOpen && (
          <div className="md:hidden border-t border-white/[0.06] bg-[#0a0a0f]/95 backdrop-blur-2xl px-4 py-4 space-y-3">
            <a href="#gallery" className="block text-slate-300 hover:text-white py-2" onClick={() => setMobileMenuOpen(false)}>Gallery</a>
            <a href="#how-it-works" className="block text-slate-300 hover:text-white py-2" onClick={() => setMobileMenuOpen(false)}>How It Works</a>
            <Link to="/pricing" className="block text-slate-300 hover:text-white py-2" onClick={() => setMobileMenuOpen(false)}>Pricing</Link>
            <Link to="/login" className="block text-slate-300 hover:text-white py-2" onClick={() => setMobileMenuOpen(false)}>Login</Link>
            <Link to="/signup" className="block" onClick={() => setMobileMenuOpen(false)}>
              <Button className="w-full bg-indigo-600 hover:bg-indigo-500 text-white rounded-full font-semibold">Start Creating</Button>
            </Link>
          </div>
        )}
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-24 md:pt-44 md:pb-32 px-4">
        {/* Background layers */}
        <div className="absolute inset-0 hero-grid pointer-events-none opacity-60" />
        <div className="absolute inset-0 landing-glow pointer-events-none" />
        <div className="absolute top-20 left-1/4 w-96 h-96 bg-indigo-600/10 rounded-full blur-[120px] pointer-events-none" />
        <div className="absolute bottom-0 right-1/4 w-80 h-80 bg-amber-500/8 rounded-full blur-[100px] pointer-events-none" />

        <div className="relative max-w-7xl mx-auto">
          <div className="max-w-4xl">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-indigo-400 mb-6" data-testid="hero-tagline">AI-Powered Story Engine</p>

            <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-black tracking-tighter leading-[1.05] mb-8 text-white">
              Turn stories into{' '}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-300 via-sky-300 to-amber-300">
                cinematic videos
              </span>
              {' '}using AI
            </h1>

            <p className="text-lg md:text-xl text-slate-300 font-normal leading-relaxed max-w-2xl mb-10">
              Write any story. Our AI generates scenes, creates images, adds voiceover,
              and renders a complete video — all in under 90 seconds.
            </p>

            <div className="flex flex-col sm:flex-row items-start gap-4 mb-12">
              <Link to="/signup">
                <Button className="bg-indigo-600 hover:bg-indigo-500 text-white rounded-full px-8 py-4 text-lg font-semibold transition-all hover:scale-[1.03] hover:shadow-[0_0_30px_-6px_rgba(99,102,241,0.6)]" data-testid="hero-cta-btn">
                  Create Your First Video
                  <ArrowRight className="w-5 h-5 ml-2" />
                </Button>
              </Link>
              <a href="#how-it-works">
                <Button variant="ghost" className="text-slate-200 hover:text-white hover:bg-white/[0.06] rounded-full px-6 py-4 text-lg font-medium" data-testid="hero-howit-btn">
                  <Play className="w-5 h-5 mr-2" />
                  See How It Works
                </Button>
              </a>
            </div>

            <div className="flex items-center gap-6 text-sm text-slate-400 font-medium">
              <span className="flex items-center gap-1.5"><Check className="w-4 h-4 text-emerald-400" /> 10 free credits</span>
              <span className="flex items-center gap-1.5"><Check className="w-4 h-4 text-emerald-400" /> No credit card</span>
              <span className="flex items-center gap-1.5"><Check className="w-4 h-4 text-emerald-400" /> Cancel anytime</span>
            </div>
          </div>

          {/* Hero video */}
          <div className="mt-16 relative rounded-2xl overflow-hidden border border-white/[0.08] shadow-[0_0_80px_-20px_rgba(99,102,241,0.25)]" data-testid="hero-video-preview">
            {galleryVideos.length > 0 ? (
              <video
                src={galleryVideos[0]?.output_url}
                controls
                className="w-full aspect-video bg-black"
                preload="metadata"
              />
            ) : (
              <div className="w-full aspect-video bg-gradient-to-br from-[#0f0f1a] to-[#0a0a0f] flex items-center justify-center">
                <div className="text-center">
                  <Play className="w-16 h-16 text-indigo-400 mx-auto mb-4 opacity-40" />
                  <p className="text-slate-500">AI-generated story video preview</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Social Proof Bar */}
      <section className="border-y border-white/[0.06] py-8 px-4 bg-white/[0.01]">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-center gap-8 md:gap-16">
          <div className="text-center">
            <div className="text-3xl font-bold text-white">{stats.videosCreated}+</div>
            <div className="text-sm text-slate-400 mt-1">Videos Created</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-white">90s</div>
            <div className="text-sm text-slate-400 mt-1">Avg Generation Time</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-white">5</div>
            <div className="text-sm text-slate-400 mt-1">AI Pipeline Stages</div>
          </div>
          <div className="text-center">
            <div className="flex items-center gap-1 justify-center">
              {[1,2,3,4,5].map(i => <Star key={i} className="w-5 h-5 text-amber-400 fill-amber-400" />)}
            </div>
            <div className="text-sm text-slate-400 mt-1">Creator Rated</div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="py-24 md:py-32 px-4">
        <div className="max-w-7xl mx-auto">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-indigo-400 mb-4">How It Works</p>
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight mb-16 text-white">Three steps to your first video</h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { step: '01', icon: PenLine, title: 'Write Your Story', desc: 'Type any story or pick a prompt template. A bedtime tale, a fantasy adventure, an educational lesson — anything.' },
              { step: '02', icon: Wand2, title: 'AI Creates Everything', desc: 'Our pipeline generates scenes, creates unique images, adds professional voiceover, and renders full video automatically.' },
              { step: '03', icon: Download, title: 'Download & Share', desc: 'Get your finished video in under 90 seconds. Download, share on social media, or embed anywhere.' },
            ].map(({ step, icon: Icon, title, desc }) => (
              <div key={step} className="group relative rounded-2xl border border-white/[0.06] bg-white/[0.02] p-8 transition-all hover:border-indigo-500/30 hover:bg-white/[0.04]">
                <span className="text-7xl font-black text-white/[0.03] absolute -top-3 -right-3 group-hover:text-indigo-500/10 transition-colors select-none">{step}</span>
                <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mb-6">
                  <Icon className="w-6 h-6 text-indigo-400" strokeWidth={1.5} />
                </div>
                <h3 className="text-xl font-bold tracking-tight mb-3 text-white">{title}</h3>
                <p className="text-slate-400 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Story Prompt Templates */}
      <section className="py-24 md:py-32 px-4 border-t border-white/[0.06]">
        <div className="max-w-7xl mx-auto">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-indigo-400 mb-4">Try It Now</p>
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight mb-6 text-white">Pick a story, create a video</h2>
          <p className="text-lg text-slate-300 max-w-2xl mb-12">Click any prompt below, then sign up to generate your AI video instantly.</p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {STORY_PROMPTS.map((prompt, i) => (
              <Link
                key={i}
                to={`/signup?prompt=${encodeURIComponent(prompt.text)}`}
                className={`group relative rounded-2xl border p-6 transition-all cursor-pointer ${
                  selectedPrompt === i
                    ? 'border-indigo-500/50 bg-indigo-500/10'
                    : 'border-white/[0.06] bg-white/[0.02] hover:border-indigo-500/30 hover:bg-white/[0.04]'
                }`}
                onClick={() => setSelectedPrompt(i)}
                data-testid={`prompt-${i}`}
              >
                <div className="flex items-start gap-4">
                  <span className="text-2xl">{prompt.icon}</span>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-white mb-2 group-hover:text-indigo-300 transition-colors">{prompt.label}</h3>
                    <p className="text-sm text-slate-400 leading-relaxed line-clamp-2">{prompt.text}</p>
                  </div>
                  <ChevronRight className="w-5 h-5 text-slate-600 group-hover:text-indigo-400 group-hover:translate-x-1 transition-all flex-shrink-0 mt-1" />
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Video Gallery */}
      <section id="gallery" className="py-24 md:py-32 px-4 border-t border-white/[0.06]">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-end justify-between mb-12">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-indigo-400 mb-4">Gallery</p>
              <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight text-white">Made with Visionary Suite</h2>
            </div>
            <Link to="/gallery" className="hidden md:block">
              <Button variant="ghost" className="text-slate-300 hover:text-white transition-colors">
                View all <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </Link>
          </div>

          {galleryVideos.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {galleryVideos.map((video, i) => (
                <div key={i} className="group rounded-2xl overflow-hidden border border-white/[0.06] bg-white/[0.02] hover:border-white/[0.12] transition-all" data-testid={`gallery-video-${i}`}>
                  <div className="aspect-video bg-black relative">
                    <video src={video.output_url} className="w-full h-full object-cover" preload="metadata" controls muted />
                  </div>
                  <div className="p-4">
                    <h3 className="font-medium text-white truncate">{video.title || 'AI Story Video'}</h3>
                    <div className="flex items-center gap-3 mt-2 text-xs text-slate-500">
                      <span className="flex items-center gap-1"><Film className="w-3 h-3" /> {video.animation_style || 'cartoon_2d'}</span>
                      {video.timing?.total_ms && <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {Math.round(video.timing.total_ms / 1000)}s</span>}
                      {video.remix_count > 0 && <span className="flex items-center gap-1"><RefreshCcw className="w-3 h-3 text-pink-400" /> {video.remix_count} remixes</span>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-16 text-slate-500">
              <Film className="w-12 h-12 mx-auto mb-4 opacity-30" />
              <p>Videos will appear here as creators generate them.</p>
            </div>
          )}
        </div>
      </section>

      {/* Pricing Section */}
      <section className="py-24 md:py-32 px-4 border-t border-white/[0.06]">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-indigo-400 mb-4">Simple Pricing</p>
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight mb-4 text-white">Start free, scale when ready</h2>
            <p className="text-lg text-slate-300">Subscribe monthly or buy credits as you need them.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Free */}
            <div className="flex flex-col rounded-2xl border border-white/[0.08] bg-white/[0.02] p-8">
              <h3 className="text-xl font-bold mb-2 text-white">Free</h3>
              <div className="text-4xl font-black mb-1 text-white">10</div>
              <p className="text-slate-400 mb-6">credits to start</p>
              <ul className="space-y-3 mb-8 flex-1">
                <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400" /> 1 Story Video</li>
                <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400" /> 1 Reel Script</li>
                <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400" /> All features unlocked</li>
              </ul>
              <Link to="/signup">
                <Button className="w-full bg-white/[0.06] hover:bg-white/10 text-white border border-white/[0.1] rounded-full py-3 font-medium" data-testid="pricing-free-btn">Get Started</Button>
              </Link>
            </div>

            {/* Creator $9/mo */}
            <div className="flex flex-col rounded-2xl border-2 border-indigo-500/50 bg-indigo-500/[0.05] p-8 relative">
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-indigo-600 text-white text-xs font-bold px-4 py-1 rounded-full">POPULAR</div>
              <h3 className="text-xl font-bold mb-2 text-white">Creator</h3>
              <div className="flex items-baseline gap-1">
                <span className="text-4xl font-black text-white">$9</span>
                <span className="text-slate-400">/month</span>
              </div>
              <p className="text-indigo-300 text-sm mt-1 mb-6">100 credits/month</p>
              <ul className="space-y-3 mb-8 flex-1">
                <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400" /> 5 Story Videos</li>
                <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400" /> All animation styles</li>
                <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400" /> Priority rendering</li>
              </ul>
              <Link to="/pricing">
                <Button className="w-full bg-indigo-600 hover:bg-indigo-500 text-white rounded-full py-3 font-semibold transition-all hover:shadow-[0_0_24px_-4px_rgba(99,102,241,0.5)]" data-testid="pricing-starter-btn">Subscribe</Button>
              </Link>
            </div>

            {/* Pro $19/mo */}
            <div className="flex flex-col rounded-2xl border border-white/[0.08] bg-white/[0.02] p-8">
              <h3 className="text-xl font-bold mb-2 text-white">Pro</h3>
              <div className="flex items-baseline gap-1">
                <span className="text-4xl font-black text-white">$19</span>
                <span className="text-slate-400">/month</span>
              </div>
              <p className="text-amber-300 text-sm mt-1 mb-6">250 credits/month</p>
              <ul className="space-y-3 mb-8 flex-1">
                <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400" /> 12+ Story Videos</li>
                <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400" /> No watermark</li>
                <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400" /> Gallery featured</li>
                <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400" /> Priority rendering</li>
              </ul>
              <Link to="/pricing">
                <Button className="w-full bg-white/[0.06] hover:bg-white/10 text-white border border-white/[0.1] rounded-full py-3 font-medium" data-testid="pricing-pro-btn">Subscribe</Button>
              </Link>
            </div>
          </div>

          {/* Top-up mention */}
          <p className="text-center text-sm text-slate-500 mt-8">
            Need more? <Link to="/pricing" className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2">Buy credit top-ups</Link> starting from $5 for 50 credits.
          </p>
        </div>
      </section>

      {/* More Tools */}
      <section className="py-24 md:py-32 px-4 border-t border-white/[0.06]">
        <div className="max-w-7xl mx-auto">
          <p className="text-sm font-medium uppercase tracking-widest text-slate-500 mb-4">More Creator Tools</p>
          <h2 className="text-2xl md:text-3xl font-semibold tracking-tight text-slate-200 mb-12">Everything else you need</h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { icon: Zap, title: 'Reel Scripts', desc: 'Viral hooks, scripts & hashtags in seconds', cost: '10 credits', href: '/app/reel-generator' },
              { icon: Image, title: 'Photo to Comic', desc: 'Transform any photo into a comic avatar', cost: '15 credits', href: '/app/photo-to-comic' },
              { icon: Film, title: 'GIF Creator', desc: 'Turn photos into animated reaction GIFs', cost: '10 credits', href: '/app/gif-maker' },
              { icon: BookOpen, title: 'Comic Storybook', desc: 'Create illustrated comic storybooks', cost: '20+ credits', href: '/app/comic-storybook' },
            ].map(({ icon: Icon, title, desc, cost, href }) => (
              <Link key={title} to={href} className="group rounded-2xl border border-white/[0.06] bg-white/[0.02] p-6 hover:border-white/[0.12] hover:bg-white/[0.04] transition-all">
                <Icon className="w-5 h-5 text-slate-400 group-hover:text-indigo-400 transition-colors mb-4" strokeWidth={1.5} />
                <h3 className="font-semibold text-white mb-1">{title}</h3>
                <p className="text-sm text-slate-500 mb-3">{desc}</p>
                <span className="text-xs text-slate-600">{cost}</span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-24 md:py-32 px-4">
        <div className="relative max-w-4xl mx-auto text-center">
          <div className="absolute inset-0 bg-indigo-600/5 rounded-3xl blur-3xl pointer-events-none" />
          <h2 className="relative text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight mb-6 text-white">
            Your story deserves to be seen
          </h2>
          <p className="relative text-lg text-slate-300 mb-10 max-w-xl mx-auto">
            Join creators turning stories into videos with AI. Start with 10 free credits — no strings attached.
          </p>
          <Link to="/signup">
            <Button className="relative bg-indigo-600 hover:bg-indigo-500 text-white rounded-full px-10 py-5 text-lg font-semibold transition-all hover:scale-[1.03] hover:shadow-[0_0_30px_-6px_rgba(99,102,241,0.6)]" data-testid="final-cta-btn">
              Create Your First Video
              <ArrowRight className="w-5 h-5 ml-2" />
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/[0.06] py-12 px-4 bg-white/[0.01]">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Clapperboard className="w-5 h-5 text-indigo-400" />
                <span className="font-bold text-white">Visionary Suite</span>
              </div>
              <p className="text-sm text-slate-500">AI-powered story-to-video engine for creators.</p>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-slate-300 mb-3">Product</h4>
              <div className="space-y-2 text-sm text-slate-500">
                <Link to="/signup" className="block hover:text-white transition-colors">Create Video</Link>
                <Link to="/gallery" className="block hover:text-white transition-colors">Gallery</Link>
                <Link to="/pricing" className="block hover:text-white transition-colors">Pricing</Link>
              </div>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-slate-300 mb-3">Resources</h4>
              <div className="space-y-2 text-sm text-slate-500">
                <Link to="/blog" className="block hover:text-white transition-colors">Blog</Link>
                <Link to="/user-manual" className="block hover:text-white transition-colors">Help Center</Link>
                <Link to="/contact" className="block hover:text-white transition-colors">Contact</Link>
              </div>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-slate-300 mb-3">Legal</h4>
              <div className="space-y-2 text-sm text-slate-500">
                <Link to="/privacy-policy" className="block hover:text-white transition-colors">Privacy Policy</Link>
                <Link to="/terms-of-service" className="block hover:text-white transition-colors">Terms of Service</Link>
                <Link to="/cookie-policy" className="block hover:text-white transition-colors">Cookies</Link>
              </div>
            </div>
          </div>
          <div className="border-t border-white/[0.06] pt-8 text-center text-sm text-slate-600">
            &copy; 2026 Visionary Suite. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
}
