import React, { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import {
  Film, Eye, RefreshCcw, Share2, Play, ArrowRight, Command,
  User, Copy, Check, Quote, Zap, Sparkles, ExternalLink
} from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';
import { SafeImage } from '../components/SafeImage';
import { trackPageView, trackRemixClick, trackShareClick } from '../utils/growthAnalytics';
import { getAssignments, trackConversion } from '../lib/abTesting';

const API = process.env.REACT_APP_BACKEND_URL;

// ─── TOOL ROUTING MAP ──────────────────────────────────────────────
const TOOL_ROUTES = {
  'story-video-studio': { path: '/app/story-video-studio', label: 'Story Video', verb: 'Create a Story Video' },
  'photo-to-comic': { path: '/app/photo-to-comic', label: 'Comic', verb: 'Create a Comic' },
  'reels': { path: '/app/reels', label: 'Reel Script', verb: 'Generate a Reel Script' },
  'gif-maker': { path: '/app/gif-maker', label: 'GIF', verb: 'Create a GIF' },
  'comic-storybook': { path: '/app/comic-storybook', label: 'Comic Storybook', verb: 'Create a Comic Book' },
  'bedtime-story-builder': { path: '/app/bedtime-story-builder', label: 'Bedtime Story', verb: 'Create a Bedtime Story' },
  'caption-rewriter': { path: '/app/caption-rewriter', label: 'Caption', verb: 'Rewrite Captions' },
  'brand-story-builder': { path: '/app/brand-story-builder', label: 'Brand Story', verb: 'Build a Brand Story' },
};

function getToolRoute(creation) {
  const toolType = creation?.tool_type || 'story-video-studio';
  return TOOL_ROUTES[toolType] || TOOL_ROUTES['story-video-studio'];
}

export default function PublicCreation() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [creation, setCreation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeScene, setActiveScene] = useState(0);
  const [copied, setCopied] = useState(false);
  const [showShareMenu, setShowShareMenu] = useState(false);

  // A/B experiment variants
  const [abVariants, setAbVariants] = useState({});
  const [showPreviewGate, setShowPreviewGate] = useState(false);

  useEffect(() => { fetchCreation(); loadAbVariants(); }, [slug]);

  const loadAbVariants = async () => {
    const assignments = await getAssignments();
    setAbVariants(assignments);
    // Store login timing variant for downstream use
    const loginTiming = assignments?.login_timing?.variant_data?.gate_timing;
    if (loginTiming) {
      sessionStorage.setItem('ab_login_timing', loginTiming);
    }
  };

  // Get A/B variant values with fallbacks
  const ctaText = abVariants?.cta_copy?.variant_data?.cta_text || 'Create This in 1 Click';
  const hookText = abVariants?.hook_text?.variant_data?.hook_text || 'Made in 30 seconds. No skills needed.';
  const ctaPosition = abVariants?.cta_placement?.variant_data?.cta_position || 'top';

  useEffect(() => { fetchCreation(); }, [slug]);

  const fetchCreation = async () => {
    try {
      const r = await axios.get(`${API}/api/public/creation/${slug}`);
      setCreation(r.data.creation);
      trackPageView(slug);
    } catch (e) {
      setError(e.response?.status === 404 ? 'Creation not found' : 'Failed to load');
    }
    setLoading(false);
  };

  // ─── REMIX HANDLER (uses auto-prefill system) ─────────────────────
  const handleRemix = () => {
    if (!creation) return;
    const tool = getToolRoute(creation);
    const prompt = creation.story_text || creation.prompt || '';

    // Store remix data for auto-prefill
    localStorage.setItem('remix_data', JSON.stringify({
      prompt,
      timestamp: Date.now(),
      source_tool: 'public-page',
      remixFrom: {
        tool: creation.tool_type || 'story-video-studio',
        prompt,
        settings: {
          animation_style: creation.animation_style,
          style: creation.animation_style,
          age_group: creation.age_group,
          voice_preset: creation.voice_preset,
        },
        title: creation.title,
        parentId: creation.job_id,
      },
    }));

    // Store return URL so login redirects back to the tool
    localStorage.setItem('remix_return_url', tool.path);
    trackRemixClick(slug, creation.tool_type || 'story-video-studio');

    // Track A/B conversions for all active experiments
    trackConversion('cta_copy', 'remix_click');
    trackConversion('hook_text', 'remix_click');
    trackConversion('login_timing', 'remix_click');
    trackConversion('cta_placement', 'remix_click');

    const isLoggedIn = !!localStorage.getItem('token');
    const gateTiming = abVariants?.login_timing?.variant_data?.gate_timing || 'after_generate';

    if (isLoggedIn) {
      navigate(tool.path);
    } else if (gateTiming === 'before_generate') {
      navigate('/signup');
    } else if (gateTiming === 'after_preview') {
      setShowPreviewGate(true);
      window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
    } else {
      navigate(tool.path);
    }
  };

  // ─── "TRY THIS EXACT PROMPT" HANDLER ─────────────────────────────
  const handleTryPrompt = () => {
    if (!creation) return;
    const tool = getToolRoute(creation);
    const prompt = creation.story_text || creation.prompt || '';

    localStorage.setItem('remix_data', JSON.stringify({
      prompt,
      timestamp: Date.now(),
      source_tool: 'public-page-exact',
      remixFrom: {
        tool: creation.tool_type || 'story-video-studio',
        prompt,
        settings: {
          animation_style: creation.animation_style,
          style: creation.animation_style,
          age_group: creation.age_group,
          voice_preset: creation.voice_preset,
        },
        title: `Exact: ${creation.title}`,
        parentId: creation.job_id,
      },
    }));

    localStorage.setItem('remix_return_url', tool.path);

    // Increment remix count
    axios.post(`${API}/api/public/creation/${slug}/remix`).catch(() => {});
    navigate(tool.path);
    toast.success('Prompt loaded — ready to generate!');
  };

  const playSceneAudio = (idx) => {
    setActiveScene(idx);
    const scene = creation?.scenes?.[idx];
    if (scene?.audio_url) {
      const audio = new Audio(scene.audio_url);
      audio.play().catch(() => {});
    }
  };

  // Share helpers
  const shareUrl = `${API}/api/public/s/${slug}`;
  const pageUrl = `${window.location.origin}/v/${slug}`;
  const ogTitle = creation ? `${creation.title} — Made with AI` : 'AI Creation — Visionary Suite';
  const ogDescription = creation?.prompt
    ? `AI-generated in seconds: "${creation.prompt.slice(0, 120)}" — Remix it yourself!`
    : 'AI-generated creation — Remix it yourself on Visionary Suite';
  const ogImage = `${API}/api/public/og-image/${slug}`;

  const shareTo = (platform) => {
    const text = `This was created with AI in seconds! Remix it yourself:`;
    trackShareClick(slug, platform);
    const urls = {
      twitter: `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(shareUrl)}`,
      linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`,
      reddit: `https://reddit.com/submit?url=${encodeURIComponent(shareUrl)}&title=${encodeURIComponent(`AI-Created: ${creation?.title}`)}`,
      whatsapp: `https://wa.me/?text=${encodeURIComponent(`${text} ${shareUrl}`)}`,
    };
    if (urls[platform]) window.open(urls[platform], '_blank', 'width=600,height=400');
  };

  const copyLink = async () => {
    await navigator.clipboard.writeText(pageUrl);
    setCopied(true);
    toast.success('Link copied!');
    setTimeout(() => setCopied(false), 2000);
  };

  // ─── LOADING STATE ──────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
        <div className="animate-pulse text-center">
          <Film className="w-12 h-12 text-slate-500 mx-auto mb-4" />
          <p className="text-slate-500">Loading creation...</p>
        </div>
      </div>
    );
  }

  if (error || !creation) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
        <div className="text-center" data-testid="creation-not-found">
          <Film className="w-12 h-12 text-slate-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">{error || 'Creation not found'}</h2>
          <Link to="/explore"><button className="mt-4 px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm">Explore Creations</button></Link>
        </div>
      </div>
    );
  }

  const currentScene = creation.scenes?.[activeScene];
  const prompt = creation.prompt || creation.story_text || '';
  const tool = getToolRoute(creation);

  return (
    <div className="min-h-screen bg-[#0a0a0f]" data-testid="public-creation-page">
      <Helmet>
        <title>{ogTitle}</title>
        <meta name="description" content={ogDescription} />
        <link rel="canonical" href={pageUrl} />
        <meta property="og:type" content="video.other" />
        <meta property="og:url" content={pageUrl} />
        <meta property="og:title" content={ogTitle} />
        <meta property="og:description" content={ogDescription} />
        <meta property="og:image" content={ogImage} />
        <meta property="og:image:width" content="1200" />
        <meta property="og:image:height" content="630" />
        <meta property="og:site_name" content="Visionary Suite" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content={ogTitle} />
        <meta name="twitter:description" content={ogDescription} />
        <meta name="twitter:image" content={ogImage} />
      </Helmet>

      {/* Minimal header */}
      <header className="sticky top-0 z-40 bg-[#0a0a0f]/80 backdrop-blur-xl border-b border-white/[0.06]">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
              <Command className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="text-sm font-semibold text-white hidden sm:inline">Visionary Suite</span>
          </Link>
          <div className="flex items-center gap-2">
            <div className="relative">
              <button onClick={() => setShowShareMenu(!showShareMenu)} className="px-3 py-1.5 text-xs text-slate-400 hover:text-white border border-white/10 rounded-lg flex items-center gap-1.5 transition-colors" data-testid="share-btn">
                <Share2 className="w-3.5 h-3.5" /> Share
              </button>
              {showShareMenu && (
                <div className="absolute right-0 top-10 w-48 bg-slate-900 border border-white/10 rounded-xl p-1.5 shadow-2xl z-50" data-testid="share-menu">
                  {[
                    { id: 'twitter', label: 'X / Twitter' },
                    { id: 'linkedin', label: 'LinkedIn' },
                    { id: 'whatsapp', label: 'WhatsApp' },
                    { id: 'reddit', label: 'Reddit' },
                  ].map(p => (
                    <button key={p.id} onClick={() => { shareTo(p.id); setShowShareMenu(false); }}
                      className="w-full text-left px-3 py-2 text-sm text-slate-300 hover:text-white hover:bg-white/[0.06] rounded-lg transition-colors"
                      data-testid={`share-${p.id}`}
                    >{p.label}</button>
                  ))}
                  <div className="border-t border-white/[0.06] my-1" />
                  <button onClick={() => { copyLink(); setShowShareMenu(false); }} className="w-full text-left px-3 py-2 text-sm text-slate-300 hover:text-white hover:bg-white/[0.06] rounded-lg transition-colors flex items-center gap-2" data-testid="copy-link-btn">
                    {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
                    {copied ? 'Copied!' : 'Copy Link'}
                  </button>
                </div>
              )}
            </div>
            <button onClick={handleRemix} className="px-4 py-1.5 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg flex items-center gap-1.5 transition-colors" data-testid="header-remix-btn">
              <RefreshCcw className="w-3.5 h-3.5" /> Remix
            </button>
          </div>
        </div>
      </header>
      {showShareMenu && <div className="fixed inset-0 z-30" onClick={() => setShowShareMenu(false)} />}

      {/* ═══════════════════════════════════════════════════════════════
           ABOVE THE FOLD — HERO CTA ZONE
         ═══════════════════════════════════════════════════════════════ */}
      <section className="relative overflow-hidden" data-testid="hero-section">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-b from-indigo-500/[0.06] to-transparent pointer-events-none" />

        <div className="max-w-6xl mx-auto px-4 pt-8 pb-6">
          {/* Viral hook */}
          <div className="text-center mb-6">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-medium mb-4" data-testid="viral-hook-badge">
              <Zap className="w-3 h-3" /> {hookText}
            </div>
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-white mb-2" data-testid="creation-title">
              {creation.title}
            </h1>

            {/* Social Proof — LOUD */}
            <div className="flex items-center justify-center gap-4 text-sm" data-testid="social-proof">
              <span className="flex items-center gap-1.5 text-slate-300">
                <Eye className="w-4 h-4 text-blue-400" />
                <strong className="text-white font-mono">{(creation.views || 0).toLocaleString()}</strong> views
              </span>
              <span className="flex items-center gap-1.5 text-slate-300">
                <RefreshCcw className="w-4 h-4 text-pink-400" />
                <strong className="text-white font-mono">{(creation.remix_count || 0).toLocaleString()}</strong> remixes
              </span>
            </div>
          </div>

          <div className="grid lg:grid-cols-5 gap-6">
            {/* LEFT: Scene Viewer */}
            <div className="lg:col-span-3">
              <div className="rounded-xl overflow-hidden border border-white/[0.08]" data-testid="scene-viewer">
                <div className="relative w-full aspect-video bg-slate-900">
                  {currentScene?.image_url ? (
                    <SafeImage src={currentScene.image_url} alt={`Scene ${activeScene + 1}`} aspectRatio="16/9" titleOverlay={`Scene ${activeScene + 1}`} className="rounded-none" />
                  ) : creation.thumbnail_url ? (
                    <SafeImage src={creation.thumbnail_url} alt={creation.title} aspectRatio="16/9" titleOverlay={creation.title} className="rounded-none" />
                  ) : (
                    <SafeImage src={null} alt={creation.title} aspectRatio="16/9" titleOverlay={creation.title} fallbackType="gradient" className="rounded-none" />
                  )}
                  {currentScene?.audio_url && (
                    <button onClick={() => playSceneAudio(activeScene)} className="absolute bottom-4 right-4 w-12 h-12 rounded-full bg-indigo-600 hover:bg-indigo-700 flex items-center justify-center shadow-xl transition-all" data-testid="play-scene-audio">
                      <Play className="w-5 h-5 text-white ml-0.5" />
                    </button>
                  )}
                </div>
                {creation.scenes?.length > 1 && (
                  <div className="flex gap-2 p-3 overflow-x-auto bg-slate-900/50" data-testid="scene-thumbnails">
                    {creation.scenes.map((s, i) => (
                      <button key={i} onClick={() => setActiveScene(i)} className={`flex-shrink-0 w-20 h-14 rounded-lg overflow-hidden border-2 transition-all ${i === activeScene ? 'border-indigo-500 ring-1 ring-indigo-500/30' : 'border-transparent opacity-60 hover:opacity-100'}`}>
                        {s.image_url ? <SafeImage src={s.image_url} alt={`Scene ${i + 1}`} aspectRatio="16/10" /> : <div className="w-full h-full bg-slate-800 flex items-center justify-center text-xs text-slate-500">{i + 1}</div>}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              {currentScene?.narration && (
                <div className="mt-3 bg-slate-900/50 border border-white/[0.06] rounded-lg p-4">
                  <p className="text-sm text-slate-300 italic leading-relaxed">"{currentScene.narration}"</p>
                </div>
              )}
            </div>

            {/* RIGHT: PRIMARY CTA ZONE */}
            <div className="lg:col-span-2 space-y-4" data-testid="cta-zone">
              {/* PRIMARY CTA — A/B Tested — "top" variant (default) */}
              {ctaPosition === 'top' && (
              <button
                onClick={handleRemix}
                className="w-full group relative overflow-hidden rounded-xl p-5 text-left transition-all hover:scale-[1.01]"
                data-testid="remix-main-btn"
              >
                <div className="absolute inset-0 bg-gradient-to-br from-indigo-600 to-purple-700 opacity-90 group-hover:opacity-100 transition-opacity" />
                <div className="relative z-10">
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles className="w-5 h-5 text-white" />
                    <span className="text-lg font-bold text-white">{ctaText}</span>
                  </div>
                  <p className="text-sm text-white/70 mb-3">Make your own version — different style, story, or voice</p>
                  <div className="flex items-center gap-2 text-xs text-white/50">
                    <Zap className="w-3 h-3" /> Auto-prefilled — ready to generate
                  </div>
                </div>
                <ArrowRight className="absolute top-5 right-5 w-5 h-5 text-white/30 group-hover:text-white/70 group-hover:translate-x-1 transition-all z-10" />
              </button>
              )}

              {/* SECONDARY CTA — Try This Exact Prompt */}
              {prompt && (
                <button
                  onClick={handleTryPrompt}
                  className="w-full group relative overflow-hidden rounded-xl border border-amber-500/20 bg-amber-500/[0.06] hover:bg-amber-500/[0.1] p-4 text-left transition-all"
                  data-testid="try-prompt-btn"
                >
                  <div className="flex items-center gap-2 mb-1.5">
                    <Zap className="w-4 h-4 text-amber-400" />
                    <span className="text-sm font-bold text-white">Try This Exact Prompt</span>
                  </div>
                  <p className="text-xs text-slate-400">Generate in 1 click — no typing needed</p>
                  <ArrowRight className="absolute top-4 right-4 w-4 h-4 text-amber-400/30 group-hover:text-amber-400/70 group-hover:translate-x-1 transition-all" />
                </button>
              )}

              {/* TERTIARY CTA — Create Your Own */}
              <Link to={tool.path} className="block">
                <button className="w-full rounded-xl border border-white/[0.08] hover:border-white/[0.15] bg-white/[0.02] hover:bg-white/[0.04] p-4 text-left transition-all group" data-testid="create-own-btn">
                  <div className="flex items-center gap-2 mb-1">
                    <Sparkles className="w-4 h-4 text-emerald-400" />
                    <span className="text-sm font-semibold text-white">Create Your Own</span>
                  </div>
                  <p className="text-xs text-slate-500">Start fresh with {tool.label} — no skills needed</p>
                  <ArrowRight className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-white/0 group-hover:text-white/40 transition-all" />
                </button>
              </Link>

              {/* Prompt Display */}
              {prompt && (
                <div className="bg-slate-900/50 border border-white/[0.06] rounded-lg p-4" data-testid="prompt-display">
                  <div className="flex items-center gap-2 mb-2">
                    <Quote className="w-3.5 h-3.5 text-indigo-400" />
                    <span className="text-[10px] font-medium text-indigo-400 uppercase tracking-wider">Prompt used</span>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    "{prompt.length > 250 ? prompt.slice(0, 250) + '...' : prompt}"
                  </p>
                </div>
              )}

              {/* Creation Meta */}
              <div className="bg-slate-900/30 border border-white/[0.04] rounded-lg p-4 space-y-2" data-testid="creation-meta">
                <div className="flex items-center gap-3">
                  <div className="w-7 h-7 rounded-full bg-slate-800 flex items-center justify-center">
                    <User className="w-3.5 h-3.5 text-slate-500" />
                  </div>
                  <div>
                    <p className="text-xs font-medium text-white">{creation.creator?.name || 'Anonymous'}</p>
                    <p className="text-[10px] text-slate-500">Creator</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[11px] pt-2 border-t border-white/[0.04]">
                  {creation.animation_style && (
                    <div><span className="text-slate-500">Style</span> <span className="text-slate-300 ml-1">{creation.animation_style.replace(/_/g, ' ')}</span></div>
                  )}
                  <div><span className="text-slate-500">Scenes</span> <span className="text-slate-300 ml-1">{creation.scenes?.length || 0}</span></div>
                  {creation.category && (
                    <div><span className="text-slate-500">Category</span> <span className="text-slate-300 ml-1">{creation.category}</span></div>
                  )}
                  {creation.created_at && (
                    <div><span className="text-slate-500">Created</span> <span className="text-slate-300 ml-1">{new Date(creation.created_at).toLocaleDateString()}</span></div>
                  )}
                </div>
              </div>

              {/* Share Buttons */}
              <div className="grid grid-cols-4 gap-2" data-testid="share-buttons">
                {[
                  { id: 'twitter', label: 'X' },
                  { id: 'linkedin', label: 'In' },
                  { id: 'whatsapp', label: 'WA' },
                  { id: 'reddit', label: 'Rd' },
                ].map(p => (
                  <button key={p.id} onClick={() => shareTo(p.id)}
                    className="py-2 text-[10px] font-medium text-slate-400 hover:text-white bg-white/[0.03] hover:bg-white/[0.06] rounded-lg border border-white/[0.06] transition-colors"
                    data-testid={`share-${p.id}-btn`}
                  >{p.label}</button>
                ))}
              </div>

              {/* PRIMARY CTA — A/B "bottom" variant */}
              {ctaPosition === 'bottom' && (
              <button
                onClick={handleRemix}
                className="w-full group relative overflow-hidden rounded-xl p-5 text-left transition-all hover:scale-[1.01]"
                data-testid="remix-main-btn"
              >
                <div className="absolute inset-0 bg-gradient-to-br from-indigo-600 to-purple-700 opacity-90 group-hover:opacity-100 transition-opacity" />
                <div className="relative z-10">
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles className="w-5 h-5 text-white" />
                    <span className="text-lg font-bold text-white">{ctaText}</span>
                  </div>
                  <p className="text-sm text-white/70 mb-3">Make your own version — different style, story, or voice</p>
                  <div className="flex items-center gap-2 text-xs text-white/50">
                    <Zap className="w-3 h-3" /> Auto-prefilled — ready to generate
                  </div>
                </div>
                <ArrowRight className="absolute top-5 right-5 w-5 h-5 text-white/30 group-hover:text-white/70 group-hover:translate-x-1 transition-all z-10" />
              </button>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════
           PREVIEW GATE — A/B "after_preview" variant
         ═══════════════════════════════════════════════════════════════ */}
      {showPreviewGate && (
        <section className="border-t border-indigo-500/20 bg-gradient-to-b from-indigo-500/[0.04] to-transparent py-10" data-testid="preview-gate-section">
          <div className="max-w-2xl mx-auto px-4 text-center">
            <h2 className="text-xl font-bold text-white mb-2">Ready to create your own?</h2>
            <p className="text-sm text-slate-400 mb-6">
              Sign up free — your prompt is already loaded. Just hit generate.
            </p>
            <button
              onClick={() => {
                trackConversion('login_timing', 'generate_click');
                navigate('/signup');
              }}
              className="px-8 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl transition-all hover:scale-[1.02]"
              data-testid="preview-gate-signup-btn"
            >
              Sign Up & Generate
            </button>
            <p className="text-xs text-slate-600 mt-3">Free account. No credit card needed.</p>
          </div>
        </section>
      )}

      {/* ═══════════════════════════════════════════════════════════════
           FLOATING CTA — A/B "floating" variant
         ═══════════════════════════════════════════════════════════════ */}
      {ctaPosition === 'floating' && (
        <div className="fixed bottom-0 inset-x-0 z-50 bg-[#0a0a0f]/90 backdrop-blur-xl border-t border-indigo-500/20 p-3" data-testid="floating-cta">
          <div className="max-w-4xl mx-auto flex items-center justify-between gap-4">
            <div className="flex items-center gap-3 min-w-0">
              <Sparkles className="w-5 h-5 text-indigo-400 flex-shrink-0" />
              <div className="min-w-0">
                <p className="text-sm font-bold text-white truncate">{ctaText}</p>
                <p className="text-xs text-slate-400 hidden sm:block">Auto-prefilled — ready to generate</p>
              </div>
            </div>
            <button
              onClick={() => { trackConversion('cta_placement', 'generate_click'); handleRemix(); }}
              className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-lg text-sm flex-shrink-0 flex items-center gap-2 transition-all hover:scale-[1.02]"
              data-testid="floating-remix-btn"
            >
              <RefreshCcw className="w-4 h-4" /> Remix Now
            </button>
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════════
           CTA BRANDING FOOTER — "Create yours"
         ═══════════════════════════════════════════════════════════════ */}
      <footer className="border-t border-white/[0.04] py-6" data-testid="cta-footer">
        <div className="max-w-6xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-slate-500">
            Powered by AI — no design skills required
          </p>
          <Link to="/" className="flex items-center gap-2 group" data-testid="cta-branding-link">
            <span className="text-sm font-semibold text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-400">
              Create yours
            </span>
            <ExternalLink className="w-3.5 h-3.5 text-indigo-400 group-hover:translate-x-0.5 transition-transform" />
            <span className="text-xs text-slate-500">visionary-suite.com</span>
          </Link>
        </div>
      </footer>
    </div>
  );
}
