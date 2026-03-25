import React, { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import {
  Film, Eye, RefreshCcw, Share2, Play, ArrowRight, Command,
  User, Copy, Check, Zap, Sparkles, ChevronRight, BookOpen,
  Clock, AlertCircle
} from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';
import { SafeImage } from '../components/SafeImage';
import { trackPageView, trackRemixClick, trackShareClick } from '../utils/growthAnalytics';
import { getAssignments, trackConversion } from '../lib/abTesting';

const API = process.env.REACT_APP_BACKEND_URL;

const TOOL_ROUTES = {
  'story-video-studio': { path: '/app/story-video-studio', label: 'Story Video' },
  'photo-to-comic': { path: '/app/photo-to-comic', label: 'Comic' },
  'reels': { path: '/app/reels', label: 'Reel Script' },
  'gif-maker': { path: '/app/gif-maker', label: 'GIF' },
  'comic-storybook': { path: '/app/comic-storybook', label: 'Comic Storybook' },
  'bedtime-story-builder': { path: '/app/bedtime-story-builder', label: 'Bedtime Story' },
};

function getToolRoute(creation) {
  return TOOL_ROUTES[creation?.tool_type || 'story-video-studio'] || TOOL_ROUTES['story-video-studio'];
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
  };

  const fetchCreation = async () => {
    try {
      const r = await axios.get(`${API}/api/public/creation/${slug}`);
      setCreation(r.data.creation);
      trackPageView({ source_page: `/v/${slug}`, source_slug: slug, origin: 'share_page', origin_slug: slug });
      // Trigger continuation reward for original creator
      try {
        const session = sessionStorage.getItem('growth_session_id') || '';
        const parentId = r.data.creation?.remix_parent_id || r.data.creation?.job_id;
        if (parentId) {
          axios.post(`${API}/api/growth/continuation-reward`, {
            parent_job_id: parentId,
            session_id: session,
          }).catch(() => {});
        }
      } catch {}
    } catch (e) {
      setError(e.response?.status === 404 ? 'Creation not found' : 'Failed to load');
    }
    setLoading(false);
  };

  // ─── CONTINUE STORY ──────────────────────────────────────────────
  const handleContinue = (type = 'continue') => {
    if (!creation) return;
    const tool = getToolRoute(creation);
    const basePrompt = creation.story_text || creation.prompt || '';
    let prompt = basePrompt;
    let title = creation.title;

    if (type === 'twist') {
      prompt = `[Continuation with a TWIST of "${creation.title}"]\n\n${basePrompt.slice(0, 500)}...\n\nDirection: Introduce an unexpected betrayal, reveal, or surprise that changes everything.`;
      title = `Twist: ${creation.title}`;
    } else if (type === 'funny') {
      prompt = `[Funny Version of "${creation.title}"]\n\n${basePrompt.slice(0, 500)}...\n\nDirection: Convert this into a hilariously funny version with comedic timing and absurd situations.`;
      title = `Funny: ${creation.title}`;
    } else if (type === 'episode') {
      prompt = `[Episode 2 of "${creation.title}"]\n\n${basePrompt.slice(0, 500)}...\n\nDirection: Create Episode 2 continuing from the ending. Higher stakes, deeper conflict, new challenges.`;
      title = `Episode 2: ${creation.title}`;
    } else {
      prompt = `[Continuation of "${creation.title}"]\n\n${basePrompt.slice(0, 500)}...\n\nDirection: Continue with higher stakes and tension. Keep the same characters and world.`;
      title = creation.title.startsWith('From:') ? creation.title : `From: ${creation.title}`;
    }

    localStorage.setItem('remix_data', JSON.stringify({
      prompt,
      timestamp: Date.now(),
      source_tool: 'public-page',
      remixFrom: {
        tool: creation.tool_type || 'story-video-studio',
        prompt,
        settings: {
          animation_style: creation.animation_style,
          age_group: creation.age_group,
          voice_preset: creation.voice_preset,
        },
        title,
        parentId: creation.job_id,
      },
    }));

    // Track the event
    const eventName = type === 'twist' ? 'add_twist_click' : type === 'funny' ? 'make_funny_click' : type === 'episode' ? 'next_episode_click' : 'continue_click';
    trackRemixClick({ source_page: `/v/${slug}`, source_slug: slug, tool_type: creation.tool_type || 'story_video', origin: 'share_page' });
    trackConversion('cta_copy', 'remix_click');
    axios.post(`${API}/api/public/creation/${slug}/remix`).catch(() => {});
    try {
      fetch(`${API}/api/growth/event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event: eventName,
          session_id: sessionStorage.getItem('growth_session_id') || 'unknown',
          source_slug: slug,
          meta: { type },
        }),
      }).catch(() => {});
    } catch {}
    navigate(tool.path);
  };

  // ─── CREATE YOUR OWN ──────────────────────────────────────────────
  const handleCreateOwn = () => {
    if (!creation) return;
    navigate(getToolRoute(creation).path);
  };

  // ─── SHARE ──────────────────────────────────────────────────────
  const pageUrl = `${window.location.origin}/v/${slug}`;
  const shareUrl = `${API}/api/public/s/${slug}`;
  const ogTitle = creation ? `${creation.title} — Made with AI` : 'AI Creation';
  const ogDescription = creation?.prompt
    ? `"${creation.prompt.slice(0, 120)}" — Continue the story!`
    : 'Continue the story on Visionary Suite';
  const ogImage = `${API}/api/public/og-image/${slug}`;

  const shareTo = (platform) => {
    const text = creation?.title
      ? `"${creation.title}" — created with AI in seconds! What happens next?`
      : 'This was created with AI in seconds! Continue the story:';
    trackShareClick({ source_page: `/v/${slug}`, source_slug: slug, origin: 'share_page', meta: { platform } });
    const urls = {
      twitter: `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(shareUrl)}`,
      whatsapp: `https://wa.me/?text=${encodeURIComponent(`${text} ${shareUrl}`)}`,
      linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`,
    };
    if (urls[platform]) window.open(urls[platform], '_blank', 'width=600,height=400');
  };

  const copyLink = async () => {
    await navigator.clipboard.writeText(pageUrl);
    setCopied(true);
    toast.success('Link copied!');
    setTimeout(() => setCopied(false), 2000);
  };

  const timeAgo = (isoStr) => {
    if (!isoStr) return null;
    const diff = Date.now() - new Date(isoStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  };

  // ─── LOADING / ERROR ──────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
        <div className="animate-pulse text-center">
          <Film className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <p className="text-sm text-slate-600">Loading story...</p>
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
          <Link to="/explore"><button className="mt-3 px-5 py-2 bg-violet-600 hover:bg-violet-700 text-white rounded-lg text-sm">Explore Stories</button></Link>
        </div>
      </div>
    );
  }

  const currentScene = creation.scenes?.[activeScene];
  const lastScene = creation.scenes?.[creation.scenes.length - 1];
  const cliffhangerText = lastScene?.narration || creation.story_text || creation.prompt || '';
  const characterName = creation.characters?.[0]?.name || creation.character_name || null;
  const lastContTime = timeAgo(creation.last_continuation_at);
  const momentumMsg = creation.remix_count > 0
    ? `${creation.remix_count} people continued this story`
    : 'Be the first to continue this story';

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
            <button onClick={() => setShowShareMenu(!showShareMenu)} className="px-3 py-1.5 text-xs text-slate-400 hover:text-white border border-white/[0.08] rounded-lg flex items-center gap-1.5" data-testid="share-btn">
              <Share2 className="w-3 h-3" /> Share
            </button>
            <button onClick={() => handleContinue('continue')} className="px-4 py-1.5 text-xs font-semibold text-white bg-violet-600 hover:bg-violet-500 rounded-lg flex items-center gap-1.5" data-testid="header-continue-btn">
              <Play className="w-3 h-3" /> Continue Story
            </button>
          </div>
        </div>
        {showShareMenu && (
          <>
            <div className="fixed inset-0 z-30" onClick={() => setShowShareMenu(false)} />
            <div className="absolute right-4 top-14 w-44 bg-slate-900 border border-white/10 rounded-xl p-1.5 shadow-2xl z-50" data-testid="share-menu">
              {['Twitter', 'WhatsApp', 'LinkedIn'].map(p => (
                <button key={p} onClick={() => { shareTo(p.toLowerCase()); setShowShareMenu(false); }}
                  className="w-full text-left px-3 py-2 text-sm text-slate-300 hover:text-white hover:bg-white/[0.06] rounded-lg"
                  data-testid={`share-${p.toLowerCase()}`}
                >{p}</button>
              ))}
              <div className="border-t border-white/[0.06] my-1" />
              <button onClick={() => { copyLink(); setShowShareMenu(false); }} className="w-full text-left px-3 py-2 text-sm text-slate-300 hover:text-white hover:bg-white/[0.06] rounded-lg flex items-center gap-2">
                {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
                {copied ? 'Copied!' : 'Copy Link'}
              </button>
            </div>
          </>
        )}
      </header>

      {/* ═══ ABOVE THE FOLD: Character Intro + Story Hook + Cliffhanger ═══ */}
      <section className="relative" data-testid="hero-section">
        <div className="absolute inset-0 bg-gradient-to-b from-violet-500/[0.04] to-transparent pointer-events-none" />

        <div className="max-w-5xl mx-auto px-4 pt-8 pb-4">
          {/* CHARACTER INTRO (if available) */}
          {characterName && (
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-violet-500/10 border border-violet-500/20 mb-4" data-testid="character-intro">
              <User className="w-3 h-3 text-violet-400" />
              <span className="text-xs font-bold text-violet-300">Meet {characterName}</span>
              {creation.character_story_count > 0 && (
                <span className="text-[10px] text-violet-400/60">Featured in {creation.character_story_count} stories</span>
              )}
            </div>
          )}

          {/* STORY TITLE */}
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-black text-white mb-3" data-testid="creation-title">
            {creation.title}
          </h1>

          {/* SOCIAL PROOF */}
          <div className="flex items-center gap-4 text-sm mb-4" data-testid="social-proof">
            <span className="flex items-center gap-1.5 text-slate-400">
              <Eye className="w-3.5 h-3.5 text-blue-400" />
              <strong className="text-white text-xs">{(creation.views || 0).toLocaleString()}</strong> views
            </span>
            <span className="flex items-center gap-1.5 text-slate-400">
              <RefreshCcw className="w-3.5 h-3.5 text-rose-400" />
              <strong className="text-white text-xs">{(creation.remix_count || 0).toLocaleString()}</strong> continuations
            </span>
            {lastContTime && (
              <span className="flex items-center gap-1.5 text-slate-400">
                <Clock className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-xs">Last continued <strong className="text-emerald-300">{lastContTime}</strong></span>
              </span>
            )}
          </div>

          <div className="grid lg:grid-cols-5 gap-6">
            {/* LEFT: Scene Viewer + Story */}
            <div className="lg:col-span-3">
              {/* Video/Image viewer */}
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
                    <button onClick={() => setActiveScene(activeScene)} className="absolute bottom-4 right-4 w-11 h-11 rounded-full bg-violet-600 hover:bg-violet-500 flex items-center justify-center shadow-xl" data-testid="play-scene-audio">
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

              {/* STORY HOOK / CLIFFHANGER (above CTA zone) */}
              {cliffhangerText && (
                <div className="mt-4 bg-gradient-to-r from-amber-500/[0.06] to-rose-500/[0.06] border border-amber-500/15 rounded-2xl p-5" data-testid="story-hook">
                  <div className="flex items-center gap-2 mb-2">
                    <BookOpen className="w-4 h-4 text-amber-400" />
                    <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider">Where the story left off...</span>
                  </div>
                  <p className="text-sm text-slate-300 italic leading-relaxed">
                    "{cliffhangerText.length > 300 ? '...' + cliffhangerText.slice(-300) : cliffhangerText}"
                  </p>
                  <p className="text-xs text-amber-400/80 font-semibold mt-3">But something unexpected happens next...</p>
                </div>
              )}

              {/* Narration for current scene */}
              {currentScene?.narration && (
                <div className="mt-3 bg-white/[0.02] border border-white/[0.04] rounded-xl p-4">
                  <p className="text-sm text-slate-300 italic leading-relaxed">"{currentScene.narration}"</p>
                </div>
              )}
            </div>

            {/* RIGHT: CONVERSION CTA ZONE */}
            <div className="lg:col-span-2 space-y-3" data-testid="cta-zone">

              {/* ═══ PRIMARY CTA: Continue Story ═══ */}
              <button
                onClick={() => handleContinue('continue')}
                className="w-full group relative overflow-hidden rounded-2xl p-5 text-left transition-all hover:scale-[1.01] active:scale-[0.99]"
                data-testid="continue-story-btn"
              >
                <div className="absolute inset-0 bg-gradient-to-br from-violet-600 to-rose-600 opacity-90 group-hover:opacity-100 transition-opacity" />
                <div className="relative z-10">
                  <div className="flex items-center gap-2 mb-2">
                    <Play className="w-5 h-5 text-white" />
                    <span className="text-lg font-bold text-white">Continue This Story</span>
                  </div>
                  <p className="text-sm text-white/70 mb-2">See what happens next — your prompt is ready</p>
                  <div className="flex items-center gap-2 text-xs text-white/50">
                    <Zap className="w-3 h-3" /> No signup needed to start
                  </div>
                </div>
                <ArrowRight className="absolute top-5 right-5 w-5 h-5 text-white/30 group-hover:text-white/70 group-hover:translate-x-1 transition-all z-10" />
              </button>

              {/* ═══ SECONDARY: Add Twist / Make Funny / Next Episode ═══ */}
              <div className="grid grid-cols-3 gap-2" data-testid="secondary-ctas">
                <button
                  onClick={() => handleContinue('twist')}
                  className="p-3 rounded-xl border border-amber-500/20 bg-amber-500/[0.04] hover:bg-amber-500/[0.08] transition-all text-center"
                  data-testid="add-twist-btn"
                >
                  <Sparkles className="w-4 h-4 text-amber-400 mx-auto mb-1" />
                  <span className="text-xs font-bold text-white block">Add Twist</span>
                </button>
                <button
                  onClick={() => handleContinue('funny')}
                  className="p-3 rounded-xl border border-pink-500/20 bg-pink-500/[0.04] hover:bg-pink-500/[0.08] transition-all text-center"
                  data-testid="make-funny-btn"
                >
                  <AlertCircle className="w-4 h-4 text-pink-400 mx-auto mb-1" />
                  <span className="text-xs font-bold text-white block">Make Funny</span>
                </button>
                <button
                  onClick={() => handleContinue('episode')}
                  className="p-3 rounded-xl border border-purple-500/20 bg-purple-500/[0.04] hover:bg-purple-500/[0.08] transition-all text-center"
                  data-testid="next-episode-btn"
                >
                  <Film className="w-4 h-4 text-purple-400 mx-auto mb-1" />
                  <span className="text-xs font-bold text-white block">Next Episode</span>
                </button>
              </div>

              {/* ═══ CREATE YOUR OWN ═══ */}
              <button
                onClick={handleCreateOwn}
                className="w-full group rounded-2xl border border-white/[0.08] hover:border-violet-500/20 bg-white/[0.02] hover:bg-white/[0.04] p-4 text-left transition-all"
                data-testid="create-own-btn"
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-violet-500/10 flex items-center justify-center flex-shrink-0">
                    <Sparkles className="w-4 h-4 text-violet-400" />
                  </div>
                  <div className="flex-1">
                    <span className="text-sm font-semibold text-white block">Create Your Version</span>
                    <span className="text-xs text-slate-500">Start fresh in the same studio</span>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-violet-400 transition-colors" />
                </div>
              </button>

              {/* ═══ SOCIAL PROOF MOMENTUM ═══ */}
              <div className="bg-white/[0.02] border border-white/[0.04] rounded-xl p-4" data-testid="momentum-section">
                <p className="text-xs text-slate-500 mb-2">{momentumMsg}</p>
                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  {creation.animation_style && (
                    <div><span className="text-slate-500">Style</span> <span className="text-slate-300 ml-1">{creation.animation_style.replace(/_/g, ' ')}</span></div>
                  )}
                  <div><span className="text-slate-500">Scenes</span> <span className="text-slate-300 ml-1">{creation.scenes?.length || 0}</span></div>
                  {creation.created_at && (
                    <div><span className="text-slate-500">Created</span> <span className="text-slate-300 ml-1">{new Date(creation.created_at).toLocaleDateString()}</span></div>
                  )}
                  <div><span className="text-slate-500">Creator</span> <span className="text-slate-300 ml-1">{creation.creator?.name || 'Anonymous'}</span></div>
                </div>
              </div>

              {/* Share Buttons */}
              <div className="grid grid-cols-4 gap-2" data-testid="share-buttons">
                {[
                  { id: 'twitter', label: 'X' },
                  { id: 'whatsapp', label: 'WA' },
                  { id: 'linkedin', label: 'In' },
                  { id: 'copy', label: copied ? 'Done' : 'Link' },
                ].map(p => (
                  <button key={p.id} onClick={() => p.id === 'copy' ? copyLink() : shareTo(p.id)}
                    className="py-2 text-[10px] font-medium text-slate-400 hover:text-white bg-white/[0.02] hover:bg-white/[0.04] rounded-lg border border-white/[0.04] transition-colors"
                    data-testid={`share-${p.id}-btn`}
                  >{p.label}</button>
                ))}
              </div>

              {/* Remix as different format */}
              <div className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-3" data-testid="remix-variants">
                <span className="text-[10px] font-semibold text-cyan-400 uppercase tracking-wider mb-2 block">Remix as...</span>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { key: 'comic-storybook', label: 'Comic Book', color: 'text-amber-400 bg-amber-500/10 border-amber-500/15' },
                    { key: 'gif-maker', label: 'GIF', color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/15' },
                    { key: 'reels', label: 'Reel', color: 'text-rose-400 bg-rose-500/10 border-rose-500/15' },
                    { key: 'bedtime-story-builder', label: 'Bedtime', color: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/15' },
                  ].filter(r => r.key !== (creation.tool_type || 'story-video-studio')).map(remix => (
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
                        trackRemixClick({ source_page: `/v/${slug}`, source_slug: slug, tool_type: remix.key, origin: 'remix_variant' });
                        axios.post(`${API}/api/public/creation/${slug}/remix`).catch(() => {});
                        navigate(TOOL_ROUTES[remix.key]?.path || '/app/story-video-studio');
                      }}
                      className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-xs font-medium transition-all hover:scale-[1.02] ${remix.color}`}
                      data-testid={`remix-${remix.key}`}
                    >
                      {remix.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══ FOOTER ═══ */}
      <footer className="border-t border-white/[0.04] py-6 mt-8" data-testid="cta-footer">
        <div className="max-w-5xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-slate-600">Made with AI — no design skills required</p>
          <Link to="/" className="flex items-center gap-2 group">
            <span className="text-sm font-semibold text-transparent bg-clip-text bg-gradient-to-r from-violet-400 to-rose-400">Create yours on Visionary Suite</span>
            <ArrowRight className="w-3 h-3 text-violet-400 group-hover:translate-x-0.5 transition-transform" />
          </Link>
        </div>
      </footer>
    </div>
  );
}
