import React, { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import {
  Film, Eye, RefreshCcw, Share2, Play, ArrowRight, Command,
  User, Copy, Check, Quote, Zap, Sparkles, ExternalLink,
  ChevronRight, BookOpen, Clock
} from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';
import { SafeImage } from '../components/SafeImage';
import { trackPageView, trackRemixClick, trackShareClick, setOrigin } from '../utils/growthAnalytics';
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
  const [abVariants, setAbVariants] = useState({});

  useEffect(() => {
    fetchCreation();
    loadAbVariants();
  }, [slug]);

  const loadAbVariants = async () => {
    const assignments = await getAssignments();
    setAbVariants(assignments);
    const loginTiming = assignments?.login_timing?.variant_data?.gate_timing;
    if (loginTiming) sessionStorage.setItem('ab_login_timing', loginTiming);
  };

  const fetchCreation = async () => {
    try {
      const r = await axios.get(`${API}/api/public/creation/${slug}`);
      setCreation(r.data.creation);
      trackPageView({ source_page: `/v/${slug}`, source_slug: slug, origin: 'share_page', origin_slug: slug });
    } catch (e) {
      setError(e.response?.status === 404 ? 'Creation not found' : 'Failed to load');
    }
    setLoading(false);
  };

  // ─── REMIX: Continue this story (pre-filled) ──────────────────────
  const handleContinue = () => {
    if (!creation) return;
    const tool = getToolRoute(creation);
    const prompt = creation.story_text || creation.prompt || '';

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

    localStorage.setItem('remix_return_url', tool.path);
    trackRemixClick({ source_page: `/v/${slug}`, source_slug: slug, tool_type: creation.tool_type || 'story_video', origin: 'share_page', origin_slug: slug });
    trackConversion('cta_copy', 'remix_click');
    trackConversion('hook_text', 'remix_click');

    axios.post(`${API}/api/public/creation/${slug}/remix`).catch(() => {});
    navigate(tool.path);
  };

  // ─── Create your own (fresh start in same tool) ───────────────────
  const handleCreateOwn = () => {
    if (!creation) return;
    const tool = getToolRoute(creation);
    trackRemixClick({ source_page: `/v/${slug}`, source_slug: slug, tool_type: creation.tool_type || 'story_video', origin: 'share_page', origin_slug: slug, meta: { cta_type: 'create_own' } });
    navigate(tool.path);
  };

  const playSceneAudio = (idx) => {
    setActiveScene(idx);
    const scene = creation?.scenes?.[idx];
    if (scene?.audio_url) new Audio(scene.audio_url).play().catch(() => {});
  };

  // Share helpers
  const shareUrl = `${API}/api/public/s/${slug}`;
  const pageUrl = `${window.location.origin}/v/${slug}`;
  const ogTitle = creation ? `${creation.title} — Made with AI` : 'AI Creation — Visionary Suite';
  const ogDescription = creation?.prompt
    ? `AI-generated in seconds: "${creation.prompt.slice(0, 120)}" — Continue the story!`
    : 'AI-generated creation — Continue the story on Visionary Suite';
  const ogImage = `${API}/api/public/og-image/${slug}`;

  const shareTo = (platform) => {
    const text = `This was created with AI in seconds! Continue the story:`;
    trackShareClick({ source_page: `/v/${slug}`, source_slug: slug, origin: 'share_page', meta: { platform } });
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

  // ─── LOADING ──────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
        <div className="animate-pulse text-center">
          <Film className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <p className="text-sm text-slate-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (error || !creation) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
        <div className="text-center" data-testid="creation-not-found">
          <Film className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <h2 className="text-lg font-bold text-white mb-2">{error || 'Creation not found'}</h2>
          <Link to="/explore"><button className="mt-3 px-5 py-2 bg-violet-600 hover:bg-violet-700 text-white rounded-lg text-sm">Explore Creations</button></Link>
        </div>
      </div>
    );
  }

  const currentScene = creation.scenes?.[activeScene];
  const prompt = creation.prompt || creation.story_text || '';
  const tool = getToolRoute(creation);
  const lastScene = creation.scenes?.[creation.scenes.length - 1];
  const cliffhangerText = lastScene?.narration || prompt;

  // ─── A/B VARIANT DATA ─────────────────────────────────────────────
  const hookVariant = abVariants?.hook_text?.variant_data || {};
  const ctaVariant = abVariants?.cta_copy?.variant_data || {};
  const hookText = hookVariant.hook_text || 'This was created with AI in seconds — continue the story!';
  const ctaText = ctaVariant.cta_text || 'Continue This Story';

  // Momentum helpers
  const timeAgo = (isoStr) => {
    if (!isoStr) return null;
    const diff = Date.now() - new Date(isoStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
  };

  const lastContTime = timeAgo(creation.last_continuation_at);
  const isDormant = !creation.is_alive && creation.remix_count > 0;
  const momentumMsg = creation.is_alive
    ? (creation.continuations_1h > 0
        ? `${creation.continuations_1h} people continued in the last hour`
        : `${creation.continuations_24h} new episodes today — story is still evolving`)
    : (creation.remix_count > 0
        ? 'Be the first to continue this story today'
        : 'Be the first to continue this story');

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

      {/* ═══ STICKY HEADER ═══ */}
      <header className="sticky top-0 z-40 bg-[#0a0a0f]/90 backdrop-blur-xl border-b border-white/[0.06]">
        <div className="max-w-5xl mx-auto px-4 h-13 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 py-3">
            <div className="w-6 h-6 rounded-md bg-gradient-to-br from-violet-500 to-rose-500 flex items-center justify-center">
              <Command className="w-3 h-3 text-white" />
            </div>
            <span className="text-xs font-semibold text-white hidden sm:inline">Visionary Suite</span>
          </Link>
          <div className="flex items-center gap-2">
            <div className="relative">
              <button onClick={() => setShowShareMenu(!showShareMenu)} className="px-3 py-1.5 text-xs text-slate-400 hover:text-white border border-white/[0.08] rounded-lg flex items-center gap-1.5 transition-colors" data-testid="share-btn">
                <Share2 className="w-3 h-3" /> Share
              </button>
              {showShareMenu && (
                <div className="absolute right-0 top-10 w-44 bg-slate-900 border border-white/10 rounded-xl p-1.5 shadow-2xl z-50" data-testid="share-menu">
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
            <button onClick={handleContinue} className="px-4 py-1.5 text-xs font-semibold text-white bg-violet-600 hover:bg-violet-500 rounded-lg flex items-center gap-1.5 transition-colors" data-testid="header-remix-btn">
              <Play className="w-3 h-3" /> Continue Story
            </button>
          </div>
        </div>
      </header>
      {showShareMenu && <div className="fixed inset-0 z-30" onClick={() => setShowShareMenu(false)} />}

      {/* ═══ HERO — STORY HOOK ═══ */}
      <section className="relative overflow-hidden" data-testid="hero-section">
        <div className="absolute inset-0 bg-gradient-to-b from-violet-500/[0.04] to-transparent pointer-events-none" />

        <div className="max-w-5xl mx-auto px-4 pt-8 pb-6">
          {/* Title + Social Proof + Momentum */}
          <div className="text-center mb-6">
            {/* Trending badge — only if REAL */}
            {creation.is_trending && (
              <span className="inline-flex items-center gap-1.5 text-[10px] font-bold text-amber-400 bg-amber-500/10 border border-amber-500/20 px-3 py-1 rounded-full mb-3 uppercase tracking-wider" data-testid="trending-badge">
                <Zap className="w-3 h-3" /> Trending now
              </span>
            )}

            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-black text-white mb-3" data-testid="creation-title">
              {creation.title}
            </h1>

            {/* Core stats row */}
            <div className="flex items-center justify-center gap-4 text-sm" data-testid="social-proof">
              <span className="flex items-center gap-1.5 text-slate-400">
                <Eye className="w-3.5 h-3.5 text-blue-400" />
                <strong className="text-white font-mono text-xs">{(creation.views || 0).toLocaleString()}</strong> views
              </span>
              <span className="flex items-center gap-1.5 text-slate-400">
                <RefreshCcw className="w-3.5 h-3.5 text-rose-400" />
                <strong className="text-white font-mono text-xs">{(creation.remix_count || 0).toLocaleString()}</strong> continuations
              </span>
              {lastContTime && (
                <span className="flex items-center gap-1.5 text-slate-400">
                  <Clock className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-xs">Last continued <strong className="text-emerald-300">{lastContTime}</strong></span>
                </span>
              )}
            </div>

            {/* Momentum message */}
            <p className="text-xs mt-2 text-slate-500" data-testid="momentum-msg">
              {creation.is_alive
                ? <span className="text-emerald-400/80">{momentumMsg}</span>
                : <span className="text-amber-400/60">{momentumMsg}</span>
              }
            </p>
          </div>

          <div className="grid lg:grid-cols-5 gap-6">
            {/* LEFT: Scene Viewer */}
            <div className="lg:col-span-3">
              <div className="rounded-2xl overflow-hidden border border-white/[0.06]" data-testid="scene-viewer">
                <div className="relative w-full aspect-video bg-[#0d0d15]">
                  {currentScene?.image_url ? (
                    <SafeImage src={currentScene.image_url} alt={`Scene ${activeScene + 1}`} aspectRatio="16/9" titleOverlay={`Scene ${activeScene + 1}`} className="rounded-none" />
                  ) : creation.thumbnail_url ? (
                    <SafeImage src={creation.thumbnail_url} alt={creation.title} aspectRatio="16/9" titleOverlay={creation.title} className="rounded-none" />
                  ) : (
                    <SafeImage src={null} alt={creation.title} aspectRatio="16/9" titleOverlay={creation.title} fallbackType="gradient" className="rounded-none" />
                  )}
                  {currentScene?.audio_url && (
                    <button onClick={() => playSceneAudio(activeScene)} className="absolute bottom-4 right-4 w-11 h-11 rounded-full bg-violet-600 hover:bg-violet-500 flex items-center justify-center shadow-xl transition-all" data-testid="play-scene-audio">
                      <Play className="w-4 h-4 text-white ml-0.5" />
                    </button>
                  )}
                </div>
                {creation.scenes?.length > 1 && (
                  <div className="flex gap-2 p-3 overflow-x-auto bg-[#0d0d15]" data-testid="scene-thumbnails">
                    {creation.scenes.map((s, i) => (
                      <button key={i} onClick={() => setActiveScene(i)} className={`flex-shrink-0 w-20 h-14 rounded-lg overflow-hidden border-2 transition-all ${i === activeScene ? 'border-violet-500 ring-1 ring-violet-500/30' : 'border-transparent opacity-50 hover:opacity-90'}`}>
                        {s.image_url ? <SafeImage src={s.image_url} alt={`Scene ${i + 1}`} aspectRatio="16/10" /> : <div className="w-full h-full bg-slate-800 flex items-center justify-center text-xs text-slate-500">{i + 1}</div>}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Narration for current scene */}
              {currentScene?.narration && (
                <div className="mt-3 bg-white/[0.02] border border-white/[0.04] rounded-xl p-4">
                  <p className="text-sm text-slate-300 italic leading-relaxed">"{currentScene.narration}"</p>
                </div>
              )}
            </div>

            {/* RIGHT: CTA ZONE */}
            <div className="lg:col-span-2 space-y-4" data-testid="cta-zone">

              {/* ═══ PRIMARY CTA: Continue the story (A/B tested) ═══ */}
              <button
                onClick={handleContinue}
                className="w-full group relative overflow-hidden rounded-2xl p-5 text-left transition-all hover:scale-[1.01] active:scale-[0.99]"
                data-testid="continue-story-btn"
              >
                <div className="absolute inset-0 bg-gradient-to-br from-violet-600 to-rose-600 opacity-90 group-hover:opacity-100 transition-opacity" />
                <div className="relative z-10">
                  <div className="flex items-center gap-2 mb-2">
                    <Play className="w-5 h-5 text-white" />
                    <span className="text-lg font-bold text-white">{ctaText}</span>
                  </div>
                  <p className="text-sm text-white/70 mb-3">{hookText}</p>
                  <div className="flex items-center gap-2 text-xs text-white/50">
                    <Zap className="w-3 h-3" /> No signup needed to start
                  </div>
                </div>
                <ArrowRight className="absolute top-5 right-5 w-5 h-5 text-white/30 group-hover:text-white/70 group-hover:translate-x-1 transition-all z-10" />
              </button>

              {/* ═══ SECONDARY CTA: Continue where others left off ═══ */}
              <button
                onClick={handleContinue}
                className="w-full group rounded-2xl border border-white/[0.08] hover:border-violet-500/20 bg-white/[0.02] hover:bg-white/[0.04] p-4 text-left transition-all"
                data-testid="continue-others-btn"
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-violet-500/10 flex items-center justify-center flex-shrink-0">
                    <RefreshCcw className="w-4 h-4 text-violet-400" />
                  </div>
                  <div className="flex-1">
                    <span className="text-sm font-semibold text-white block">Continue where others left off</span>
                    <span className="text-xs text-slate-500">
                      {creation.remix_count > 0 ? `${creation.remix_count} people already continued` : 'Be the first to add your chapter'}
                    </span>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-violet-400 transition-colors" />
                </div>
              </button>

              {/* ═══ STORY CLIFFHANGER TEASER ═══ */}
              {cliffhangerText && (
                <div className="bg-white/[0.02] border border-amber-500/10 rounded-2xl p-4" data-testid="cliffhanger-teaser">
                  <div className="flex items-center gap-2 mb-2">
                    <BookOpen className="w-3.5 h-3.5 text-amber-400" />
                    <span className="text-[10px] font-semibold text-amber-400 uppercase tracking-wider">Where the story left off...</span>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed italic">
                    "{cliffhangerText.length > 200 ? cliffhangerText.slice(-200) + '...' : cliffhangerText}"
                  </p>
                  <button
                    onClick={handleContinue}
                    className="mt-3 w-full py-2 text-xs font-medium text-amber-400 bg-amber-500/5 hover:bg-amber-500/10 border border-amber-500/10 rounded-lg transition-colors"
                    data-testid="cliffhanger-continue-btn"
                  >
                    What happens next? Find out...
                  </button>
                </div>
              )}

              {/* Prompt Display */}
              {prompt && (
                <div className="bg-white/[0.02] border border-white/[0.04] rounded-xl p-4" data-testid="prompt-display">
                  <div className="flex items-center gap-2 mb-2">
                    <Quote className="w-3 h-3 text-violet-400" />
                    <span className="text-[10px] font-medium text-violet-400 uppercase tracking-wider">Prompt used</span>
                  </div>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    "{prompt.length > 200 ? prompt.slice(0, 200) + '...' : prompt}"
                  </p>
                </div>
              )}

              {/* Creation Meta */}
              <div className="bg-white/[0.02] border border-white/[0.04] rounded-xl p-4 space-y-2" data-testid="creation-meta">
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
                  {creation.created_at && (
                    <div><span className="text-slate-500">Created</span> <span className="text-slate-300 ml-1">{new Date(creation.created_at).toLocaleDateString()}</span></div>
                  )}
                </div>
              </div>

              {/* Share grid */}
              <div className="grid grid-cols-4 gap-2" data-testid="share-buttons">
                {[
                  { id: 'twitter', label: 'X' },
                  { id: 'linkedin', label: 'In' },
                  { id: 'whatsapp', label: 'WA' },
                  { id: 'reddit', label: 'Rd' },
                ].map(p => (
                  <button key={p.id} onClick={() => shareTo(p.id)}
                    className="py-2 text-[10px] font-medium text-slate-400 hover:text-white bg-white/[0.02] hover:bg-white/[0.04] rounded-lg border border-white/[0.04] transition-colors"
                    data-testid={`share-${p.id}-btn`}
                  >{p.label}</button>
                ))}
              </div>

              {/* ═══ REMIX VARIANTS — Try in different formats ═══ */}
              <div className="bg-white/[0.02] border border-white/[0.06] rounded-2xl p-4" data-testid="remix-variants">
                <div className="flex items-center gap-2 mb-3">
                  <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                  <span className="text-[10px] font-semibold text-cyan-400 uppercase tracking-wider">Remix as...</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { key: 'comic-storybook', label: 'Comic Book', icon: BookOpen, color: 'text-amber-400 bg-amber-500/10 border-amber-500/15' },
                    { key: 'gif-maker', label: 'GIF', icon: Film, color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/15' },
                    { key: 'reels', label: 'Reel Script', icon: Play, color: 'text-rose-400 bg-rose-500/10 border-rose-500/15' },
                    { key: 'bedtime-story-builder', label: 'Bedtime Story', icon: BookOpen, color: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/15' },
                  ].filter(r => r.key !== (creation.tool_type || 'story-video-studio')).map(remix => {
                    const RemixIcon = remix.icon;
                    return (
                      <button
                        key={remix.key}
                        onClick={() => {
                          const remixPrompt = creation.story_text || creation.prompt || '';
                          localStorage.setItem('remix_data', JSON.stringify({
                            prompt: remixPrompt,
                            timestamp: Date.now(),
                            source_tool: 'remix-variant',
                            remixFrom: {
                              tool: remix.key,
                              prompt: remixPrompt,
                              settings: { animation_style: creation.animation_style },
                              title: creation.title,
                              parentId: creation.job_id,
                            },
                          }));
                          trackRemixClick({ source_page: `/v/${slug}`, source_slug: slug, tool_type: remix.key, origin: 'remix_variant', origin_slug: slug });
                          trackConversion('cta_copy', 'remix_click');
                          axios.post(`${API}/api/public/creation/${slug}/remix`).catch(() => {});
                          navigate(TOOL_ROUTES[remix.key]?.path || '/app/story-video-studio');
                        }}
                        className={`flex items-center gap-2 px-3 py-2.5 rounded-xl border text-xs font-medium transition-all hover:scale-[1.02] ${remix.color}`}
                        data-testid={`remix-${remix.key}`}
                      >
                        <RemixIcon className="w-3.5 h-3.5" />
                        {remix.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══ FOOTER ═══ */}
      <footer className="border-t border-white/[0.04] py-6" data-testid="cta-footer">
        <div className="max-w-5xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-slate-600">Made with AI — no design skills required</p>
          <Link to="/" className="flex items-center gap-2 group" data-testid="cta-branding-link">
            <span className="text-sm font-semibold text-transparent bg-clip-text bg-gradient-to-r from-violet-400 to-rose-400">Create yours</span>
            <ExternalLink className="w-3 h-3 text-violet-400 group-hover:translate-x-0.5 transition-transform" />
          </Link>
        </div>
      </footer>
    </div>
  );
}
