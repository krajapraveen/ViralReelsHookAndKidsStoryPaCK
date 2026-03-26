import React, { useState, useEffect, useRef } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import {
  Film, Eye, RefreshCcw, Share2, Play, ArrowRight, Command,
  User, Copy, Check, Zap, Sparkles, ChevronRight, BookOpen,
  Clock, Flame, TrendingUp, Volume2, VolumeX, Pause,
  Download, MessageSquare
} from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';
import { SafeImage } from '../components/SafeImage';
import { AnimatedViewerCount } from '../components/AnimatedSocialProof';
import { trackPageView, trackRemixClick, trackShareClick } from '../utils/growthAnalytics';
import { getVariant, trackConversion } from '../lib/abTesting';

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
  const videoRef = useRef(null);
  const [creation, setCreation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeScene, setActiveScene] = useState(0);
  const [copied, setCopied] = useState(false);
  const [showUrgency, setShowUrgency] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(true);
  const [videoEnded, setVideoEnded] = useState(false);
  const [showOverlay, setShowOverlay] = useState(false);
  const [hookVariant, setHookVariant] = useState(null);

  useEffect(() => {
    fetchCreation();
  }, [slug]);

  // Fetch A/B hook variant and track impression
  useEffect(() => {
    if (!creation) return;
    let cancelled = false;
    (async () => {
      try {
        const v = await getVariant('story_hook');
        if (!cancelled && v?.variant_data) setHookVariant(v);
      } catch {}
      // Track impression regardless
      trackConversion('story_hook', 'impression');
    })();
    return () => { cancelled = true; };
  }, [creation]);

  useEffect(() => {
    const timer = setTimeout(() => setShowUrgency(true), 4000);
    return () => clearTimeout(timer);
  }, []);

  const fetchCreation = async () => {
    try {
      const r = await axios.get(`${API}/api/public/creation/${slug}`);
      setCreation(r.data.creation);
      trackPageView({ source_page: `/v/${slug}`, source_slug: slug, origin: 'share_page', origin_slug: slug });

      const jobId = r.data.creation?.job_id;
      if (jobId) {
        localStorage.setItem('referral_source', JSON.stringify({
          job_id: jobId, slug, character_name: r.data.creation?.character_name || null, timestamp: Date.now(),
        }));
      }

      try {
        const session = sessionStorage.getItem('growth_session_id') || '';
        const parentId = r.data.creation?.remix_parent_id || r.data.creation?.job_id;
        if (parentId) {
          axios.post(`${API}/api/growth/continuation-reward`, { parent_job_id: parentId, session_id: session }).catch(() => {});
        }
      } catch {}
    } catch (e) {
      setError(e.response?.status === 404 ? 'Creation not found' : 'Failed to load');
    }
    setLoading(false);
  };

  const handleVideoPlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play();
      setIsPlaying(true);
      setVideoEnded(false);
    }
  };

  const handleVideoEnd = () => {
    setIsPlaying(false);
    setVideoEnded(true);
    setShowOverlay(true);
  };

  const toggleMute = (e) => {
    e.stopPropagation();
    if (videoRef.current) {
      videoRef.current.muted = !isMuted;
      setIsMuted(!isMuted);
    }
  };

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
      prompt, timestamp: Date.now(), source_tool: 'public-page',
      remixFrom: {
        tool: creation.tool_type || 'story-video-studio', prompt,
        settings: { animation_style: creation.animation_style, age_group: creation.age_group, voice_preset: creation.voice_preset },
        title, parentId: creation.job_id,
      },
    }));

    trackRemixClick({ source_page: `/v/${slug}`, source_slug: slug, tool_type: creation.tool_type || 'story_video', origin: 'share_page' });
    trackConversion('cta_copy', 'remix_click');
    trackConversion('story_hook', 'continue_click');
    axios.post(`${API}/api/public/creation/${slug}/remix`).catch(() => {});
    try {
      fetch(`${API}/api/growth/event`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event: type === 'twist' ? 'add_twist_click' : type === 'funny' ? 'make_funny_click' : type === 'episode' ? 'next_episode_click' : 'continue_click', session_id: sessionStorage.getItem('growth_session_id') || 'unknown', source_slug: slug, meta: { type } }),
      }).catch(() => {});
    } catch {}
    navigate(tool.path);
  };

  const pageUrl = `${window.location.origin}/v/${slug}`;
  const shareUrl = `${API}/api/public/s/${slug}`;
  const ogTitle = creation ? `${creation.title} — Made with AI` : 'AI Creation';
  const ogDescription = creation?.cliffhanger
    ? `"${creation.cliffhanger.slice(0, 140)}" — What happens next?`
    : creation?.prompt
      ? `"${creation.prompt.slice(0, 120)}" — Continue the story!`
      : 'Continue the story on Visionary Suite';
  const ogImage = `${API}/api/public/og-image/${slug}`;

  const shareTo = (platform) => {
    const text = creation?.title
      ? `"${creation.title}" — created with AI in seconds! What happens next?`
      : 'This was created with AI in seconds! Continue the story:';
    trackShareClick({ source_page: `/v/${slug}`, source_slug: slug, origin: 'share_page', meta: { platform } });
    trackConversion('story_hook', 'share_click');
    const urls = {
      twitter: `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(shareUrl)}`,
      whatsapp: `https://wa.me/?text=${encodeURIComponent(`${text} ${shareUrl}`)}`,
      instagram: `https://www.instagram.com/`,
    };
    if (urls[platform]) window.open(urls[platform], '_blank', 'width=600,height=400');
  };

  const copyLink = async () => {
    await navigator.clipboard.writeText(pageUrl);
    setCopied(true);
    toast.success('Link copied — share it anywhere!');
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

  const hasVideo = !!creation.video_url;
  const currentScene = creation.scenes?.[activeScene];
  const lastScene = creation.scenes?.[creation.scenes.length - 1];
  const cliffhangerText = creation.cliffhanger || lastScene?.narration || creation.story_text || creation.prompt || '';
  const characterName = creation.character_name || creation.characters?.[0]?.name || null;
  const primaryChar = creation.characters?.[0];
  const lastContTime = timeAgo(creation.last_continuation_at);
  const contCount = creation.remix_count || 0;

  // A/B Hook variant data
  const hv = hookVariant?.variant_data || {};
  const hookLabel = hv.section_label || (creation.cliffhanger ? 'The Cliffhanger' : 'Where the story left off...');
  const hookSuffix = hv.hook_suffix || 'But something unexpected happens next...';
  const hookCta = hv.cta_text || 'Continue This Story';
  const hookAccent = hv.accent || 'amber';
  const accentMap = {
    amber: { bg: 'from-amber-500/[0.06] to-rose-500/[0.06]', border: 'border-amber-500/15', icon: 'text-amber-400', text: 'text-amber-400/80', label: 'text-amber-400' },
    rose: { bg: 'from-rose-500/[0.06] to-pink-500/[0.06]', border: 'border-rose-500/15', icon: 'text-rose-400', text: 'text-rose-400/80', label: 'text-rose-400' },
    red: { bg: 'from-red-500/[0.06] to-orange-500/[0.06]', border: 'border-red-500/15', icon: 'text-red-400', text: 'text-red-400/80', label: 'text-red-400' },
    cyan: { bg: 'from-cyan-500/[0.06] to-blue-500/[0.06]', border: 'border-cyan-500/15', icon: 'text-cyan-400', text: 'text-cyan-400/80', label: 'text-cyan-400' },
  };
  const ac = accentMap[hookAccent] || accentMap.amber;

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
            <button onClick={copyLink} className="px-3 py-1.5 text-xs font-semibold text-emerald-400 border border-emerald-500/30 bg-emerald-500/[0.06] hover:bg-emerald-500/[0.12] rounded-lg flex items-center gap-1.5" data-testid="header-share-btn">
              {copied ? <Check className="w-3 h-3" /> : <Share2 className="w-3 h-3" />} {copied ? 'Copied!' : 'Share'}
            </button>
            <button onClick={() => handleContinue('continue')} className="px-4 py-1.5 text-xs font-semibold text-white bg-gradient-to-r from-violet-600 to-rose-600 hover:opacity-90 rounded-lg flex items-center gap-1.5" data-testid="header-continue-btn">
              <Play className="w-3 h-3" /> Continue Story
            </button>
          </div>
        </div>
      </header>

      {/* ═══ SOCIAL PROOF BANNER ═══ */}
      <section className="bg-gradient-to-r from-violet-600/[0.04] to-rose-600/[0.04] border-b border-white/[0.04]" data-testid="social-proof-banner">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-center gap-4 flex-wrap">
          {contCount > 0 && (
            <span className="inline-flex items-center gap-1.5 text-sm font-bold text-amber-400">
              <Flame className="w-4 h-4" /> {contCount} people continued this story
            </span>
          )}
          <span className="text-sm text-slate-300">Be the next to decide what happens</span>
          {showUrgency && (
            <span className="inline-flex items-center gap-1 text-xs text-rose-400 font-semibold animate-pulse" data-testid="urgency-badge">
              <TrendingUp className="w-3 h-3" /> Trending now
            </span>
          )}
          <AnimatedViewerCount />
        </div>
      </section>

      <section className="relative" data-testid="hero-section">
        <div className="max-w-5xl mx-auto px-4 pt-6 pb-4">
          {/* CHARACTER INTRO */}
          {characterName && (
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-violet-500/10 border border-violet-500/20 mb-4" data-testid="character-intro">
              <User className="w-3 h-3 text-violet-400" />
              <span className="text-xs font-bold text-violet-300">Meet {characterName}</span>
              {primaryChar?.role && (
                <span className="text-[10px] text-violet-400/60 capitalize">— {primaryChar.role}</span>
              )}
              {primaryChar?.personality && (
                <span className="text-[10px] text-violet-400/40 hidden sm:inline">— {primaryChar.personality.slice(0, 40)}</span>
              )}
            </div>
          )}

          {creation.episode_number > 1 && (
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 mb-3 ml-2" data-testid="episode-badge">
              <Film className="w-3 h-3 text-amber-400" />
              <span className="text-xs font-bold text-amber-300">Episode {creation.episode_number}</span>
            </div>
          )}

          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-black text-white mb-3" data-testid="creation-title">
            {creation.title}
          </h1>

          {/* SOCIAL PROOF STATS */}
          <div className="flex items-center gap-4 text-sm mb-4" data-testid="social-proof">
            <span className="flex items-center gap-1.5 text-slate-400">
              <Eye className="w-3.5 h-3.5 text-blue-400" />
              <strong className="text-white text-xs">{(creation.views || 0).toLocaleString()}</strong> views
            </span>
            <span className="flex items-center gap-1.5 text-slate-400">
              <RefreshCcw className="w-3.5 h-3.5 text-rose-400" />
              <strong className="text-white text-xs">{contCount.toLocaleString()}</strong> continuations
            </span>
            {lastContTime && (
              <span className="flex items-center gap-1.5 text-slate-400">
                <Clock className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-xs">Last continued <strong className="text-emerald-300">{lastContTime}</strong></span>
              </span>
            )}
          </div>

          <div className="grid lg:grid-cols-5 gap-6">
            {/* LEFT: Video/Scene Viewer + Story */}
            <div className="lg:col-span-3">
              <div className="rounded-2xl overflow-hidden border border-white/[0.06]" data-testid="media-viewer">
                <div className="relative w-full aspect-video bg-[#0d0d15]">

                  {/* ═══ AUTO-PLAY VIDEO PLAYER ═══ */}
                  {hasVideo ? (
                    <>
                      <video
                        ref={videoRef}
                        src={creation.video_url}
                        poster={creation.thumbnail_url || currentScene?.image_url}
                        className="w-full h-full object-cover"
                        muted={isMuted}
                        playsInline
                        autoPlay
                        onPlay={() => setIsPlaying(true)}
                        onPause={() => setIsPlaying(false)}
                        onEnded={handleVideoEnd}
                        data-testid="video-player"
                      />
                      {/* Video Controls Overlay */}
                      <div className="absolute inset-0 flex items-center justify-center" onClick={handleVideoPlay} data-testid="video-controls">
                        {!isPlaying && !videoEnded && (
                          <div className="w-16 h-16 rounded-full bg-black/50 backdrop-blur-sm flex items-center justify-center cursor-pointer hover:bg-black/70 transition-all">
                            <Play className="w-7 h-7 text-white ml-1" />
                          </div>
                        )}
                      </div>
                      {/* Mute toggle */}
                      <button onClick={toggleMute} className="absolute bottom-4 left-4 w-9 h-9 rounded-full bg-black/50 backdrop-blur-sm flex items-center justify-center hover:bg-black/70 transition-all z-10" data-testid="mute-toggle">
                        {isMuted ? <VolumeX className="w-4 h-4 text-white" /> : <Volume2 className="w-4 h-4 text-white" />}
                      </button>

                      {/* ═══ POST-VIDEO CTA OVERLAY ═══ */}
                      {videoEnded && showOverlay && (
                        <div className="absolute inset-0 bg-black/80 backdrop-blur-sm flex flex-col items-center justify-center z-20 animate-in fade-in duration-500" data-testid="post-video-overlay">
                          <p className="text-xl sm:text-2xl font-black text-white mb-2 text-center px-4">The story doesn't end here...</p>
                          <p className="text-sm text-slate-300 mb-6 text-center px-4">You decide what happens next</p>
                          <div className="flex flex-col sm:flex-row gap-3">
                            <button
                              onClick={() => handleContinue('continue')}
                              className="inline-flex items-center gap-2 h-12 px-8 rounded-xl bg-gradient-to-r from-violet-600 to-rose-600 text-white font-bold text-sm hover:opacity-90 shadow-lg shadow-violet-500/30"
                              style={{ animation: 'cta-glow 2s ease-in-out infinite' }}
                              data-testid="overlay-continue-btn"
                            >
                              <Play className="w-4 h-4" /> Continue This Story <ArrowRight className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => { setShowOverlay(false); setVideoEnded(false); videoRef.current?.play(); }}
                              className="inline-flex items-center gap-2 h-12 px-6 rounded-xl border border-white/20 text-white/70 text-sm hover:bg-white/5"
                              data-testid="overlay-replay-btn"
                            >
                              <RefreshCcw className="w-4 h-4" /> Replay
                            </button>
                          </div>
                        </div>
                      )}
                    </>
                  ) : (
                    /* ═══ FALLBACK: SCENE IMAGE VIEWER ═══ */
                    <>
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
                    </>
                  )}
                </div>

                {/* Scene thumbnails (show for both video and non-video) */}
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

              {/* ═══ CLIFFHANGER HOOK (A/B Tested) ═══ */}
              {cliffhangerText && (
                <div className={`mt-4 bg-gradient-to-r ${ac.bg} border ${ac.border} rounded-2xl p-5`} data-testid="story-hook" data-hook-variant={hookVariant?.variant_id || 'default'}>
                  <div className="flex items-center gap-2 mb-2">
                    <BookOpen className={`w-4 h-4 ${ac.icon}`} />
                    <span className={`text-[10px] font-bold ${ac.label} uppercase tracking-wider`}>
                      {hookLabel}
                    </span>
                  </div>
                  <p className="text-sm text-slate-300 italic leading-relaxed">
                    "{cliffhangerText.length > 300 ? '...' + cliffhangerText.slice(-300) : cliffhangerText}"
                  </p>
                  <p className={`text-xs ${ac.text} font-semibold mt-3`}>{hookSuffix}</p>
                </div>
              )}

              {/* ═══ MID-PAGE CTA ═══ */}
              <div className="mt-4 text-center py-6 border border-white/[0.06] rounded-2xl bg-white/[0.01]" data-testid="no-ending-hook">
                <p className="text-lg font-black text-white mb-1">This story has no ending...</p>
                <p className="text-sm text-slate-400 mb-4">You decide what happens next</p>
                <button
                  onClick={() => handleContinue('continue')}
                  className="inline-flex items-center gap-2 h-11 px-6 rounded-xl bg-gradient-to-r from-violet-600 to-rose-600 text-white font-bold text-sm hover:opacity-90 shadow-lg shadow-violet-500/20"
                  style={{ animation: 'cta-glow 2s ease-in-out infinite' }}
                  data-testid="midpage-continue-btn"
                >
                  <Play className="w-4 h-4" /> Continue It Yourself <ArrowRight className="w-4 h-4" />
                </button>
              </div>

              {currentScene?.narration && (
                <div className="mt-3 bg-white/[0.02] border border-white/[0.04] rounded-xl p-4">
                  <p className="text-sm text-slate-300 italic leading-relaxed">"{currentScene.narration}"</p>
                </div>
              )}
            </div>

            {/* RIGHT: CONVERSION CTA ZONE */}
            <div className="lg:col-span-2 space-y-3" data-testid="cta-zone">

              {/* ═══ PRIMARY CTA ═══ */}
              <button
                onClick={() => handleContinue('continue')}
                className="w-full group relative overflow-hidden rounded-2xl p-5 text-left transition-all hover:scale-[1.01] active:scale-[0.99]"
                style={{ animation: 'cta-glow 2s ease-in-out infinite' }}
                data-testid="continue-story-btn"
              >
                <div className="absolute inset-0 bg-gradient-to-br from-violet-600 to-rose-600 opacity-90 group-hover:opacity-100 transition-opacity" />
                <div className="relative z-10">
                  <div className="flex items-center gap-2 mb-2">
                    <Play className="w-5 h-5 text-white" />
                    <span className="text-lg font-bold text-white">{hookCta}</span>
                  </div>
                  <p className="text-sm text-white/70 mb-2">See what happens next — your prompt is ready</p>
                  <div className="flex items-center gap-2 text-xs text-white/50">
                    <Zap className="w-3 h-3" /> No signup needed to start
                  </div>
                </div>
                <ArrowRight className="absolute top-5 right-5 w-5 h-5 text-white/30 group-hover:text-white/70 group-hover:translate-x-1 transition-all z-10" />
              </button>

              {/* ═══ SHARE & EARN ═══ */}
              <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/[0.04] p-4" data-testid="share-earn-section">
                <div className="flex items-center gap-2 mb-2">
                  <Share2 className="w-4 h-4 text-emerald-400" />
                  <span className="text-sm font-bold text-white">Share & Earn Credits</span>
                </div>
                <div className="flex gap-2 mb-3">
                  <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full">+5 share</span>
                  <span className="text-[10px] font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full">+15 friend continues</span>
                  <span className="text-[10px] font-bold text-violet-400 bg-violet-500/10 px-2 py-0.5 rounded-full">+25 friend signs up</span>
                </div>
                <div className="grid grid-cols-4 gap-2" data-testid="share-buttons">
                  <button onClick={() => shareTo('whatsapp')} className="py-2.5 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg flex items-center justify-center gap-1" data-testid="share-whatsapp-btn">WA</button>
                  <button onClick={() => shareTo('twitter')} className="py-2.5 text-xs font-bold text-white bg-slate-700 hover:bg-slate-600 rounded-lg flex items-center justify-center" data-testid="share-twitter-btn">X</button>
                  <button onClick={() => shareTo('instagram')} className="py-2.5 text-xs font-bold text-white bg-pink-600 hover:bg-pink-500 rounded-lg flex items-center justify-center" data-testid="share-instagram-btn">IG</button>
                  <button onClick={copyLink} className="py-2.5 text-xs font-bold text-white bg-slate-800 hover:bg-slate-700 rounded-lg flex items-center justify-center gap-1" data-testid="share-copy-btn">
                    {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />} {copied ? 'Done' : 'Link'}
                  </button>
                </div>
              </div>

              {/* ═══ SECONDARY CTAs ═══ */}
              <div className="grid grid-cols-3 gap-2" data-testid="secondary-ctas">
                <button onClick={() => handleContinue('twist')} className="p-3 rounded-xl border border-amber-500/20 bg-amber-500/[0.04] hover:bg-amber-500/[0.08] transition-all text-center" data-testid="add-twist-btn">
                  <Sparkles className="w-4 h-4 text-amber-400 mx-auto mb-1" />
                  <span className="text-xs font-bold text-white block">Add Twist</span>
                </button>
                <button onClick={() => handleContinue('funny')} className="p-3 rounded-xl border border-pink-500/20 bg-pink-500/[0.04] hover:bg-pink-500/[0.08] transition-all text-center" data-testid="make-funny-btn">
                  <MessageSquare className="w-4 h-4 text-pink-400 mx-auto mb-1" />
                  <span className="text-xs font-bold text-white block">Make Funny</span>
                </button>
                <button onClick={() => handleContinue('episode')} className="p-3 rounded-xl border border-purple-500/20 bg-purple-500/[0.04] hover:bg-purple-500/[0.08] transition-all text-center" data-testid="next-episode-btn">
                  <Film className="w-4 h-4 text-purple-400 mx-auto mb-1" />
                  <span className="text-xs font-bold text-white block">Next Episode</span>
                </button>
              </div>

              {/* ═══ CREATE YOUR OWN ═══ */}
              <button onClick={() => navigate(getToolRoute(creation).path)} className="w-full group rounded-2xl border border-white/[0.08] hover:border-violet-500/20 bg-white/[0.02] hover:bg-white/[0.04] p-4 text-left transition-all" data-testid="create-own-btn">
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

              {/* ═══ CHARACTER CARD (when characters exist) ═══ */}
              {creation.characters?.length > 0 && (
                <div className="rounded-2xl border border-violet-500/15 bg-violet-500/[0.03] p-4" data-testid="character-card">
                  <div className="flex items-center gap-2 mb-3">
                    <User className="w-4 h-4 text-violet-400" />
                    <span className="text-xs font-bold text-violet-300 uppercase tracking-wider">Characters in this story</span>
                  </div>
                  {creation.characters.slice(0, 3).map((char, i) => (
                    <div key={i} className="flex items-start gap-3 mb-2 last:mb-0">
                      <div className="w-8 h-8 rounded-full bg-violet-500/20 flex items-center justify-center flex-shrink-0 text-xs font-bold text-violet-300">
                        {char.name?.[0] || '?'}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-white">{char.name} <span className="text-xs text-violet-400/60 capitalize ml-1">{char.role}</span></p>
                        {char.personality && <p className="text-xs text-slate-400 truncate">{char.personality}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* ═══ SOCIAL PROOF ═══ */}
              <div className="bg-white/[0.02] border border-white/[0.04] rounded-xl p-4" data-testid="momentum-section">
                <p className="text-xs text-slate-400 mb-2 font-semibold">
                  {contCount > 0 ? `${contCount} people already continued this — join them` : 'Be the first to continue this story'}
                </p>
                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  {creation.animation_style && (
                    <div><span className="text-slate-500">Style</span> <span className="text-slate-300 ml-1">{(creation.animation_style || '').replace(/_/g, ' ')}</span></div>
                  )}
                  <div><span className="text-slate-500">Scenes</span> <span className="text-slate-300 ml-1">{creation.scenes?.length || 0}</span></div>
                  {creation.created_at && (
                    <div><span className="text-slate-500">Created</span> <span className="text-slate-300 ml-1">{new Date(creation.created_at).toLocaleDateString()}</span></div>
                  )}
                  <div><span className="text-slate-500">Creator</span> <span className="text-slate-300 ml-1">{creation.creator?.name || 'Anonymous'}</span></div>
                </div>
              </div>

              {/* ═══ REMIX VARIANTS ═══ */}
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
                          prompt: remixPrompt, timestamp: Date.now(), source_tool: 'remix-variant',
                          remixFrom: { tool: remix.key, prompt: remixPrompt, settings: { animation_style: creation.animation_style }, title: creation.title, parentId: creation.job_id },
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

      <style>{`
        @keyframes cta-glow {
          0%, 100% { box-shadow: 0 0 30px -8px rgba(139,92,246,0.4); }
          50% { box-shadow: 0 0 50px -5px rgba(139,92,246,0.6); }
        }
      `}</style>
    </div>
  );
}
