import React, { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { Film, Eye, RefreshCcw, Share2, Play, ArrowLeft, Command, User, ChevronRight, Copy, Check, MessageSquare, Quote } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

export default function PublicCreation() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [creation, setCreation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeScene, setActiveScene] = useState(0);
  const [copied, setCopied] = useState(false);
  const [showShareMenu, setShowShareMenu] = useState(false);

  useEffect(() => { fetchCreation(); }, [slug]);

  const fetchCreation = async () => {
    try {
      const r = await axios.get(`${API}/api/public/creation/${slug}`);
      setCreation(r.data.creation);
    } catch (e) {
      setError(e.response?.status === 404 ? 'Creation not found' : 'Failed to load');
    }
    setLoading(false);
  };

  const handleRemix = () => {
    if (!creation) return;
    navigate('/app/story-video-studio', {
      state: { prompt: creation.story_text || creation.prompt, remixFrom: creation.job_id, title: `Remix of ${creation.title}` }
    });
  };

  // Share URL uses the backend OG share page for rich previews
  const shareUrl = `${API}/api/public/s/${slug}`;
  const pageUrl = `${window.location.origin}/v/${slug}`;

  const shareToTwitter = () => {
    const text = `This video was generated with AI using Visionary-Suite.\n\nPrompt: "${(creation?.prompt || creation?.story_text || '').slice(0, 100)}"\n\nRemix it:`;
    window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(shareUrl)}`, '_blank');
  };

  const shareToLinkedIn = () => {
    window.open(`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`, '_blank');
  };

  const shareToReddit = () => {
    const title = `AI-Generated Video: ${creation?.title}`;
    window.open(`https://reddit.com/submit?url=${encodeURIComponent(shareUrl)}&title=${encodeURIComponent(title)}`, '_blank');
  };

  const copyLink = async () => {
    await navigator.clipboard.writeText(pageUrl);
    setCopied(true);
    toast.success('Link copied!');
    setTimeout(() => setCopied(false), 2000);
  };

  const playSceneAudio = (idx) => {
    setActiveScene(idx);
    const scene = creation?.scenes?.[idx];
    if (scene?.audio_url) {
      const audio = new Audio(scene.audio_url);
      audio.play().catch(() => {});
    }
  };

  // OG meta data
  const ogTitle = creation ? `${creation.title} — Visionary Suite AI` : 'Visionary Suite AI';
  const ogDescription = creation?.prompt
    ? `AI-generated video: ${creation.prompt.slice(0, 150)}`
    : creation?.title
      ? `Watch "${creation.title}" — created with Visionary Suite AI. Remix it!`
      : 'AI-generated video — Visionary Suite';
  const ogImage = `${API}/api/public/og-image/${slug}`;

  if (loading) {
    return (
      <div className="vs-page min-h-screen flex items-center justify-center">
        <div className="animate-pulse text-center">
          <Film className="w-12 h-12 text-[var(--vs-text-muted)] mx-auto mb-4" />
          <p className="text-[var(--vs-text-muted)]">Loading creation...</p>
        </div>
      </div>
    );
  }

  if (error || !creation) {
    return (
      <div className="vs-page min-h-screen flex items-center justify-center">
        <div className="text-center" data-testid="creation-not-found">
          <Film className="w-12 h-12 text-[var(--vs-text-muted)] mx-auto mb-4" />
          <h2 className="vs-h2 mb-2">{error || 'Creation not found'}</h2>
          <Link to="/explore"><button className="vs-btn-primary mt-4">Explore Creations</button></Link>
        </div>
      </div>
    );
  }

  const currentScene = creation.scenes?.[activeScene];
  const prompt = creation.prompt || creation.story_text || '';

  return (
    <div className="vs-page min-h-screen" data-testid="public-creation-page">
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

      {/* Header */}
      <header className="vs-glass sticky top-0 z-40 border-b border-[var(--vs-border-subtle)]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link to="/explore" className="text-[var(--vs-text-muted)] hover:text-white"><ArrowLeft className="w-5 h-5" /></Link>
            <Link to="/" className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg vs-gradient-bg flex items-center justify-center">
                <Command className="w-3.5 h-3.5 text-white" />
              </div>
              <span className="text-sm font-semibold text-white hidden sm:inline" style={{ fontFamily: 'var(--vs-font-heading)' }}>Visionary Suite</span>
            </Link>
          </div>
          <div className="flex items-center gap-2">
            {/* Share dropdown */}
            <div className="relative">
              <button
                onClick={() => setShowShareMenu(!showShareMenu)}
                className="vs-btn-secondary h-8 px-3 text-xs flex items-center gap-1.5"
                data-testid="share-btn"
              >
                <Share2 className="w-3.5 h-3.5" /> Share
              </button>
              {showShareMenu && (
                <div className="absolute right-0 top-10 w-52 vs-panel p-2 rounded-xl shadow-2xl z-50 border border-[var(--vs-border)]" data-testid="share-menu">
                  <button onClick={shareToTwitter} className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-[var(--vs-text-secondary)] hover:text-white hover:bg-white/[0.06] rounded-lg transition-colors" data-testid="share-twitter">
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
                    Share to X
                  </button>
                  <button onClick={shareToLinkedIn} className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-[var(--vs-text-secondary)] hover:text-white hover:bg-white/[0.06] rounded-lg transition-colors" data-testid="share-linkedin">
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
                    Share to LinkedIn
                  </button>
                  <button onClick={shareToReddit} className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-[var(--vs-text-secondary)] hover:text-white hover:bg-white/[0.06] rounded-lg transition-colors" data-testid="share-reddit">
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0zm5.01 4.744c.688 0 1.25.561 1.25 1.249a1.25 1.25 0 0 1-2.498.056l-2.597-.547-.8 3.747c1.824.07 3.48.632 4.674 1.488.308-.309.73-.491 1.207-.491.968 0 1.754.786 1.754 1.754 0 .716-.435 1.333-1.01 1.614a3.111 3.111 0 0 1 .042.52c0 2.694-3.13 4.87-7.004 4.87-3.874 0-7.004-2.176-7.004-4.87 0-.183.015-.366.043-.534A1.748 1.748 0 0 1 4.028 12c0-.968.786-1.754 1.754-1.754.463 0 .898.196 1.207.49 1.207-.883 2.878-1.43 4.744-1.487l.885-4.182a.342.342 0 0 1 .14-.197.35.35 0 0 1 .238-.042l2.906.617a1.214 1.214 0 0 1 1.108-.701zM9.25 12C8.561 12 8 12.562 8 13.25c0 .687.561 1.248 1.25 1.248.687 0 1.248-.561 1.248-1.249 0-.688-.561-1.249-1.249-1.249zm5.5 0c-.687 0-1.248.561-1.248 1.25 0 .687.561 1.248 1.249 1.248.688 0 1.249-.561 1.249-1.249 0-.687-.562-1.249-1.25-1.249zm-5.466 3.99a.327.327 0 0 0-.231.094.33.33 0 0 0 0 .463c.842.842 2.484.913 2.961.913.477 0 2.105-.056 2.961-.913a.361.361 0 0 0 .029-.463.33.33 0 0 0-.464 0c-.547.533-1.684.73-2.512.73-.828 0-1.979-.196-2.512-.73a.326.326 0 0 0-.232-.095z"/></svg>
                    Share to Reddit
                  </button>
                  <div className="border-t border-[var(--vs-border)] my-1"></div>
                  <button onClick={copyLink} className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-[var(--vs-text-secondary)] hover:text-white hover:bg-white/[0.06] rounded-lg transition-colors" data-testid="copy-link-btn">
                    {copied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
                    {copied ? 'Copied!' : 'Copy Link'}
                  </button>
                </div>
              )}
            </div>
            <button onClick={handleRemix} className="vs-btn-primary h-8 px-4 text-xs flex items-center gap-1.5" data-testid="remix-btn">
              <RefreshCcw className="w-3.5 h-3.5" /> Remix This
            </button>
          </div>
        </div>
      </header>

      {/* Close share menu on outside click */}
      {showShareMenu && <div className="fixed inset-0 z-30" onClick={() => setShowShareMenu(false)} />}

      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        <div className="grid lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6 vs-fade-up-1">
            {/* Scene Viewer */}
            <div className="vs-panel overflow-hidden" data-testid="scene-viewer">
              <div className="relative w-full aspect-video bg-[var(--vs-bg-elevated)]">
                {currentScene?.image_url ? (
                  <img src={currentScene.image_url} alt={`Scene ${activeScene + 1}`} className="w-full h-full object-contain" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center"><Film className="w-16 h-16 text-[var(--vs-text-muted)]" /></div>
                )}
                {currentScene?.audio_url && (
                  <button onClick={() => playSceneAudio(activeScene)} className="absolute bottom-4 right-4 w-12 h-12 rounded-full bg-[var(--vs-cta)] hover:bg-[var(--vs-cta-hover)] flex items-center justify-center shadow-lg transition-all" data-testid="play-scene-audio">
                    <Play className="w-5 h-5 text-white ml-0.5" />
                  </button>
                )}
              </div>
              {creation.scenes?.length > 1 && (
                <div className="flex gap-2 p-3 overflow-x-auto" data-testid="scene-thumbnails">
                  {creation.scenes.map((s, i) => (
                    <button key={i} onClick={() => setActiveScene(i)} className={`flex-shrink-0 w-20 h-14 rounded-lg overflow-hidden border-2 transition-all ${i === activeScene ? 'border-[var(--vs-primary-from)] ring-1 ring-[var(--vs-primary-from)]/30' : 'border-transparent opacity-60 hover:opacity-100'}`}>
                      {s.image_url ? <img src={s.image_url} alt={`Scene ${i + 1}`} className="w-full h-full object-cover" /> : <div className="w-full h-full bg-[var(--vs-bg-card)] flex items-center justify-center"><span className="text-xs text-[var(--vs-text-muted)]">{i + 1}</span></div>}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Narration Text */}
            {currentScene?.narration && (
              <div className="vs-panel p-5">
                <p className="text-sm text-[var(--vs-text-secondary)] leading-relaxed italic" style={{ fontFamily: 'var(--vs-font-body)' }}>"{currentScene.narration}"</p>
              </div>
            )}

            {/* Prompt + Remix CTA */}
            <div className="vs-card bg-gradient-to-r from-[var(--vs-primary-from)]/10 to-[var(--vs-secondary-to)]/10 border-[var(--vs-border-glow)] py-8 px-6" data-testid="remix-cta">
              {prompt && (
                <div className="mb-5" data-testid="prompt-display">
                  <div className="flex items-center gap-2 mb-2">
                    <Quote className="w-4 h-4 text-[var(--vs-text-accent)]" />
                    <span className="text-xs font-medium text-[var(--vs-text-accent)] uppercase tracking-wider">Prompt used</span>
                  </div>
                  <p className="text-sm text-[var(--vs-text-secondary)] leading-relaxed bg-black/20 rounded-lg p-4 border border-[var(--vs-border)]" style={{ fontFamily: 'var(--vs-font-body)' }}>
                    "{prompt.length > 300 ? prompt.slice(0, 300) + '...' : prompt}"
                  </p>
                </div>
              )}
              <div className="text-center">
                <h3 className="vs-h3 mb-2">Make It Yours</h3>
                <p className="text-sm text-[var(--vs-text-secondary)] mb-4">Create your own version with different styles, voices, or stories.</p>
                <button onClick={handleRemix} className="vs-btn-primary px-8 h-12 text-base" data-testid="remix-main-btn">
                  <RefreshCcw className="w-4 h-4" /> Remix This Creation
                </button>
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <aside className="space-y-4 vs-fade-up-2">
            <div className="vs-panel p-5" data-testid="creation-meta">
              <h1 className="vs-h2 mb-3" data-testid="creation-title">{creation.title}</h1>
              <div className="flex items-center gap-4 mb-4">
                <span className="flex items-center gap-1.5 text-sm text-[var(--vs-text-muted)]">
                  <Eye className="w-4 h-4" /> <span style={{ fontFamily: 'var(--vs-font-mono)' }}>{creation.views}</span> views
                </span>
                <span className="flex items-center gap-1.5 text-sm text-[var(--vs-text-muted)]">
                  <RefreshCcw className="w-4 h-4" /> <span style={{ fontFamily: 'var(--vs-font-mono)' }}>{creation.remix_count}</span> remixes
                </span>
              </div>
              {creation.tags?.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mb-4" data-testid="creation-tags">
                  {creation.tags.map((tag, i) => (
                    <span key={i} className="px-2 py-0.5 text-xs rounded-full bg-[var(--vs-bg-elevated)] text-[var(--vs-text-muted)] border border-[var(--vs-border)]">
                      {tag}
                    </span>
                  ))}
                </div>
              )}
              <div className="flex items-center gap-3 py-3 border-t border-[var(--vs-border)]">
                <div className="w-8 h-8 rounded-full bg-[var(--vs-bg-card)] flex items-center justify-center">
                  <User className="w-4 h-4 text-[var(--vs-text-muted)]" />
                </div>
                <div>
                  <p className="text-sm font-medium text-white">{creation.creator?.name || 'Anonymous'}</p>
                  <p className="text-xs text-[var(--vs-text-muted)]">Creator</p>
                </div>
              </div>
            </div>

            <div className="vs-panel p-5 space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-[var(--vs-text-muted)]">Style</span>
                <span className="text-white" style={{ fontFamily: 'var(--vs-font-mono)' }}>{creation.animation_style?.replace(/_/g, ' ')}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-[var(--vs-text-muted)]">Scenes</span>
                <span className="text-white" style={{ fontFamily: 'var(--vs-font-mono)' }}>{creation.scenes?.length || 0}</span>
              </div>
              {creation.category && (
                <div className="flex justify-between text-sm">
                  <span className="text-[var(--vs-text-muted)]">Category</span>
                  <span className="text-white">{creation.category}</span>
                </div>
              )}
              {creation.age_group && (
                <div className="flex justify-between text-sm">
                  <span className="text-[var(--vs-text-muted)]">Age Group</span>
                  <span className="text-white">{creation.age_group}</span>
                </div>
              )}
              {creation.created_at && (
                <div className="flex justify-between text-sm">
                  <span className="text-[var(--vs-text-muted)]">Created</span>
                  <span className="text-white">{new Date(creation.created_at).toLocaleDateString()}</span>
                </div>
              )}
            </div>

            {/* Social Share Buttons */}
            <div className="vs-panel p-5" data-testid="social-share-panel">
              <p className="text-xs font-medium text-[var(--vs-text-muted)] uppercase tracking-wider mb-3">Share this creation</p>
              <div className="grid grid-cols-2 gap-2">
                <button onClick={shareToTwitter} className="flex items-center justify-center gap-2 px-3 py-2.5 text-xs font-medium text-white bg-black/40 hover:bg-black/60 rounded-lg border border-[var(--vs-border)] transition-colors" data-testid="sidebar-share-twitter">
                  <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
                  X / Twitter
                </button>
                <button onClick={shareToLinkedIn} className="flex items-center justify-center gap-2 px-3 py-2.5 text-xs font-medium text-white bg-[#0077B5]/20 hover:bg-[#0077B5]/40 rounded-lg border border-[var(--vs-border)] transition-colors" data-testid="sidebar-share-linkedin">
                  <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
                  LinkedIn
                </button>
                <button onClick={shareToReddit} className="flex items-center justify-center gap-2 px-3 py-2.5 text-xs font-medium text-white bg-[#FF4500]/15 hover:bg-[#FF4500]/30 rounded-lg border border-[var(--vs-border)] transition-colors" data-testid="sidebar-share-reddit">
                  <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0zm5.01 4.744c.688 0 1.25.561 1.25 1.249a1.25 1.25 0 0 1-2.498.056l-2.597-.547-.8 3.747c1.824.07 3.48.632 4.674 1.488.308-.309.73-.491 1.207-.491.968 0 1.754.786 1.754 1.754 0 .716-.435 1.333-1.01 1.614a3.111 3.111 0 0 1 .042.52c0 2.694-3.13 4.87-7.004 4.87-3.874 0-7.004-2.176-7.004-4.87 0-.183.015-.366.043-.534A1.748 1.748 0 0 1 4.028 12c0-.968.786-1.754 1.754-1.754.463 0 .898.196 1.207.49 1.207-.883 2.878-1.43 4.744-1.487l.885-4.182a.342.342 0 0 1 .14-.197.35.35 0 0 1 .238-.042l2.906.617a1.214 1.214 0 0 1 1.108-.701zM9.25 12C8.561 12 8 12.562 8 13.25c0 .687.561 1.248 1.25 1.248.687 0 1.248-.561 1.248-1.249 0-.688-.561-1.249-1.249-1.249zm5.5 0c-.687 0-1.248.561-1.248 1.25 0 .687.561 1.248 1.249 1.248.688 0 1.249-.561 1.249-1.249 0-.687-.562-1.249-1.25-1.249zm-5.466 3.99a.327.327 0 0 0-.231.094.33.33 0 0 0 0 .463c.842.842 2.484.913 2.961.913.477 0 2.105-.056 2.961-.913a.361.361 0 0 0 .029-.463.33.33 0 0 0-.464 0c-.547.533-1.684.73-2.512.73-.828 0-1.979-.196-2.512-.73a.326.326 0 0 0-.232-.095z"/></svg>
                  Reddit
                </button>
                <button onClick={copyLink} className="flex items-center justify-center gap-2 px-3 py-2.5 text-xs font-medium text-white bg-white/[0.06] hover:bg-white/[0.12] rounded-lg border border-[var(--vs-border)] transition-colors" data-testid="sidebar-copy-link">
                  {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
                  {copied ? 'Copied!' : 'Copy Link'}
                </button>
              </div>
            </div>

            {/* Actions */}
            <div className="space-y-2">
              <button onClick={handleRemix} className="w-full vs-btn-primary h-11 text-sm flex items-center justify-center gap-2" data-testid="sidebar-remix-btn">
                <RefreshCcw className="w-4 h-4" /> Remix This Video
              </button>
              <Link to="/app/story-video-studio" className="block">
                <button className="w-full vs-btn-secondary h-11 text-sm flex items-center justify-center gap-2">
                  Create Your Own <ChevronRight className="w-4 h-4" />
                </button>
              </Link>
            </div>

            {/* Branding */}
            <div className="text-center pt-4">
              <p className="text-xs text-[var(--vs-text-muted)]">Created with</p>
              <Link to="/" className="text-sm font-semibold vs-gradient-text" style={{ fontFamily: 'var(--vs-font-heading)' }}>
                Visionary Suite AI
              </Link>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
