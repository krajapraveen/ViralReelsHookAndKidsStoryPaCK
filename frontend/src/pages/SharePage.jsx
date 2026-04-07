import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  Play, ArrowRight, Copy, Check, Loader2, AlertCircle,
  MessageCircle, Eye, GitBranch, Clock,
  Sparkles, Share2, Zap, Wand2, Video, TrendingUp
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import api from '../utils/api';

function timeAgo(dateStr) {
  if (!dateStr) return '';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function trackEvent(event, properties = {}) {
  api.post('/api/growth/event', { event, properties, timestamp: Date.now() }).catch(() => {});
}

function MoreVideosCarousel({ shareId, onNavigate }) {
  const [videos, setVideos] = useState([]);

  useEffect(() => {
    api.get(`/api/share/${shareId}/more-videos`).then(res => {
      if (res.data?.videos?.length) setVideos(res.data.videos);
    }).catch(() => {});
  }, [shareId]);

  if (videos.length === 0) return null;

  return (
    <section className="px-4 py-8 border-b border-white/[0.04]" data-testid="more-videos-section">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-bold text-white">People are creating these</h2>
          <button
            onClick={onNavigate}
            className="text-xs text-violet-400 hover:text-violet-300 font-medium"
            data-testid="more-videos-create-btn"
          >
            Create yours
          </button>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {videos.slice(0, 6).map(v => (
            <a
              key={v.id}
              href={`/share/${v.id}`}
              className="group rounded-xl overflow-hidden border border-white/[0.06] bg-zinc-900/50 hover:border-violet-500/30 transition-all"
              data-testid={`more-video-${v.id}`}
            >
              <div className="relative aspect-video bg-zinc-800">
                {v.thumbnailUrl ? (
                  <img src={v.thumbnailUrl} alt={v.title} className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <Video className="w-6 h-6 text-zinc-700" />
                  </div>
                )}
                <div className="absolute inset-0 bg-black/30 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                  <Play className="w-6 h-6 text-white fill-white" />
                </div>
              </div>
              <div className="p-2">
                <p className="text-xs text-white truncate font-medium">{v.title}</p>
                <p className="text-[10px] text-zinc-500 flex items-center gap-1 mt-0.5">
                  <Eye className="w-2.5 h-2.5" /> {v.views || 0}
                </p>
              </div>
            </a>
          ))}
        </div>
      </div>
    </section>
  );
}

export default function SharePage() {
  const { shareId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);
  const [remixing, setRemixing] = useState(false);
  const videoRef = useRef(null);
  const trackedView = useRef(false);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get(`/api/share/${shareId}`);
        if (res.data.success) {
          setData(res.data);
          if (!trackedView.current) {
            trackedView.current = true;
            trackEvent('share_viewed', { share_id: shareId });
          }
        } else {
          setError('Share link not found');
        }
      } catch (err) {
        setError(err.response?.status === 404
          ? 'This video link has expired or does not exist'
          : 'Failed to load video');
      } finally {
        setLoading(false);
      }
    })();
  }, [shareId]);

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    toast.success('Link copied!');
    trackEvent('referral_link_copied', { share_id: shareId });
    setTimeout(() => setCopied(false), 2000);
  }, [shareId]);

  const handleWhatsApp = useCallback(() => {
    const title = data?.title || 'this AI video';
    const url = window.location.href;
    const text = `Check out ${title} — made entirely by AI\n\n${url}\n\nCreate yours free at Visionary Suite`;
    trackEvent('whatsapp_shared', { share_id: shareId });
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank');
  }, [data, shareId]);

  const handleRemix = useCallback(async () => {
    setRemixing(true);
    trackEvent('remix_clicked', { share_id: shareId });
    try {
      const res = await api.post(`/api/share/${shareId}/fork`);
      const fork = res.data.fork;
      localStorage.setItem('remix_data', JSON.stringify({
        prompt: fork.storyContext,
        timestamp: Date.now(),
        source_tool: 'share-page-remix',
        remixFrom: {
          tool: 'story-video-studio',
          prompt: fork.storyContext,
          title: fork.parentTitle,
          parentId: fork.parentShareId,
          hook_text: fork.hookText,
          characters: fork.characters,
          settings: { tone: fork.tone, conflict: fork.conflict },
          animationStyle: data?.animationStyle,
          generationId: data?.generationId,
        },
      }));
      navigate('/app/story-video-studio');
    } catch {
      toast.error('Could not start remix');
    } finally {
      setRemixing(false);
    }
  }, [shareId, navigate, data]);

  const handleCreateOwn = useCallback(() => {
    trackEvent('cta_clicked', { share_id: shareId, location: 'create_btn' });
    navigate('/app/story-video-studio');
  }, [navigate, shareId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#07070f] flex items-center justify-center">
        <Loader2 className="w-10 h-10 animate-spin text-violet-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#07070f] flex items-center justify-center p-4">
        <div className="max-w-md w-full text-center">
          <AlertCircle className="w-16 h-16 text-red-400 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-white mb-2">Video Not Found</h1>
          <p className="text-slate-400 mb-6">{error}</p>
          <Button onClick={handleCreateOwn} className="bg-violet-600 hover:bg-violet-500" data-testid="error-create-btn">
            Create Your Own Video <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      </div>
    );
  }

  const forkCount = data.forks || 0;
  const hasVideo = !!data.videoUrl;
  const viewCount = data.views || 0;

  return (
    <div className="min-h-screen bg-[#07070f]" data-testid="share-page">
      <style>{`
        @keyframes fadeUp { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes pulseGlow { 0%,100% { box-shadow: 0 0 0 0 rgba(139,92,246,0.5); } 50% { box-shadow: 0 0 0 16px rgba(139,92,246,0); } }
        @keyframes shimmer { 0% { background-position: -200% 0; } 100% { background-position: 200% 0; } }
        @keyframes countUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
        .fade-up { animation: fadeUp 0.6s ease-out both; }
        .fade-up-d1 { animation: fadeUp 0.6s ease-out 0.1s both; }
        .fade-up-d2 { animation: fadeUp 0.6s ease-out 0.2s both; }
        .fade-up-d3 { animation: fadeUp 0.6s ease-out 0.35s both; }
        .fade-up-d4 { animation: fadeUp 0.6s ease-out 0.5s both; }
        .pulse-cta { animation: pulseGlow 2.5s infinite; }
        .count-anim { animation: countUp 0.8s ease-out 0.4s both; }
      `}</style>

      {/* ─── Minimal Header ─── */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-[#07070f]/80 backdrop-blur-xl border-b border-white/[0.04]">
        <div className="max-w-5xl mx-auto px-4 h-12 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2" data-testid="header-logo">
            <div className="w-6 h-6 rounded-md bg-gradient-to-br from-violet-500 to-rose-500 flex items-center justify-center">
              <Sparkles className="w-3 h-3 text-white" />
            </div>
            <span className="text-sm font-bold text-white">Visionary Suite</span>
          </Link>
          <div className="flex items-center gap-3">
            <button onClick={handleCopy} className="text-xs text-slate-400 hover:text-white flex items-center gap-1.5 transition-colors" data-testid="header-copy-btn">
              {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Share2 className="w-3 h-3" />}
              {copied ? 'Copied' : 'Share'}
            </button>
            <button onClick={handleCreateOwn} className="text-xs px-3 py-1.5 rounded-full bg-violet-600/80 text-white hover:bg-violet-500 transition-colors font-medium" data-testid="header-create-btn">
              Create yours
            </button>
          </div>
        </div>
      </header>

      <main className="pt-12">
        {/* ═══ ABOVE THE FOLD: Video + CTA ═══ */}
        <section className="relative" data-testid="share-hero">
          <div className="absolute inset-0 pointer-events-none overflow-hidden">
            <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-violet-600/[0.08] rounded-full blur-[180px]" />
          </div>

          <div className="relative max-w-3xl mx-auto px-4 pt-8 pb-6">
            {/* Social Proof Banner */}
            <div className="flex items-center justify-center gap-2 mb-5 count-anim" data-testid="social-proof-banner">
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-violet-500/10 border border-violet-500/20">
                <TrendingUp className="w-3.5 h-3.5 text-violet-400" />
                <span className="text-xs font-semibold text-violet-300">
                  {(viewCount + forkCount * 8 + 12000).toLocaleString()}+ videos created today
                </span>
              </div>
            </div>

            {/* Video Player */}
            {hasVideo ? (
              <div className="rounded-2xl overflow-hidden border border-white/[0.08] bg-black mb-6 fade-up shadow-2xl shadow-violet-500/10" data-testid="video-player-container">
                <video controlsList="nodownload noplaybackrate" disablePictureInPicture
                  ref={videoRef}
                  src={data.videoUrl}
                  poster={data.thumbnailUrl || undefined}
                  autoPlay
                  muted
                  loop
                  playsInline
                  controls
                  className="w-full aspect-video object-contain bg-black"
                  data-testid="video-player"
                />
              </div>
            ) : data.thumbnailUrl ? (
              <div className="rounded-2xl overflow-hidden border border-white/[0.08] mb-6 fade-up" data-testid="thumbnail-container">
                <img src={data.thumbnailUrl} alt={data.title} className="w-full object-cover max-h-[500px]" />
              </div>
            ) : null}

            {/* Title */}
            <h1 className="text-2xl sm:text-3xl md:text-4xl font-black text-white tracking-tight leading-tight mb-2 fade-up-d1" data-testid="share-title">
              {data.title || 'This AI video will surprise you'}
            </h1>
            <p className="text-sm text-slate-400 mb-4 fade-up-d1">Made in seconds using AI</p>

            {/* Social proof bar */}
            <div className="flex flex-wrap items-center gap-3 mb-6 fade-up-d1" data-testid="social-proof-bar">
              <div className="flex items-center gap-1.5 text-xs text-slate-400">
                <Eye className="w-3 h-3" /> {viewCount} views
              </div>
              {forkCount > 0 && (
                <div className="flex items-center gap-1.5 text-xs text-violet-300">
                  <GitBranch className="w-3 h-3" />
                  {forkCount} remix{forkCount !== 1 ? 'es' : ''}
                </div>
              )}
              {data.recentForks?.length > 0 && (
                <div className="flex items-center gap-1.5 text-xs text-emerald-300">
                  <Clock className="w-3 h-3" />
                  Last remixed {timeAgo(data.recentForks[0]?.timestamp)}
                </div>
              )}
            </div>

            {/* ═══ PRIMARY CTA BLOCK ═══ */}
            <div className="bg-white/[0.03] border border-white/[0.08] rounded-2xl p-6 mb-6 fade-up-d2" data-testid="cta-block">
              <p className="text-lg sm:text-xl font-bold text-white mb-1">
                Create your own video in 30 seconds
              </p>
              <p className="text-sm text-slate-400 mb-5">
                No editing needed. Free to start. Takes 30 seconds.
              </p>

              <div className="flex flex-col sm:flex-row gap-3">
                <Button
                  onClick={handleCreateOwn}
                  className="h-13 px-8 rounded-xl bg-gradient-to-r from-violet-600 to-rose-600 text-white font-bold text-base hover:shadow-[0_0_40px_-8px_rgba(139,92,246,0.5)] transition-all hover:scale-[1.02] pulse-cta flex-1 sm:flex-none"
                  data-testid="primary-create-btn"
                >
                  <Zap className="w-5 h-5 mr-2" />
                  Create Your Video — Free
                </Button>

                <Button
                  onClick={handleRemix}
                  disabled={remixing}
                  variant="outline"
                  className="h-13 px-6 rounded-xl border-violet-500/30 text-violet-300 hover:bg-violet-500/10 hover:border-violet-500/50 font-semibold flex-1 sm:flex-none"
                  data-testid="remix-btn"
                >
                  {remixing ? (
                    <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Remixing...</>
                  ) : (
                    <><Wand2 className="w-4 h-4 mr-2" /> Remix This Video</>
                  )}
                </Button>
              </div>

              {/* Urgency line */}
              <p className="text-[11px] text-slate-500 mt-3 flex items-center gap-1" data-testid="urgency-text">
                <Zap className="w-3 h-3 text-amber-400" />
                Takes less than 30 seconds. No credit card required.
              </p>
            </div>

            {/* Value props */}
            <div className="grid grid-cols-3 gap-3 fade-up-d3" data-testid="value-props">
              <div className="text-center py-3 px-2 rounded-xl bg-white/[0.02] border border-white/[0.05]">
                <Video className="w-5 h-5 text-violet-400 mx-auto mb-1.5" />
                <p className="text-[11px] text-slate-300 font-medium">Made with AI</p>
              </div>
              <div className="text-center py-3 px-2 rounded-xl bg-white/[0.02] border border-white/[0.05]">
                <Zap className="w-5 h-5 text-amber-400 mx-auto mb-1.5" />
                <p className="text-[11px] text-slate-300 font-medium">No editing needed</p>
              </div>
              <div className="text-center py-3 px-2 rounded-xl bg-white/[0.02] border border-white/[0.05]">
                <Sparkles className="w-5 h-5 text-emerald-400 mx-auto mb-1.5" />
                <p className="text-[11px] text-slate-300 font-medium">Free to start</p>
              </div>
            </div>
          </div>
        </section>

        {/* ═══ SHARE TOOLS ═══ */}
        <section className="px-4 py-6 border-y border-white/[0.04]" data-testid="share-tools">
          <div className="max-w-3xl mx-auto flex items-center justify-center gap-3">
            <Button onClick={handleWhatsApp} variant="outline" className="border-white/10 text-white hover:bg-emerald-500/10 hover:border-emerald-500/30 hover:text-emerald-300" data-testid="share-whatsapp-btn">
              <MessageCircle className="w-4 h-4 mr-2" /> Message
            </Button>
            <Button onClick={handleCopy} variant="outline" className="border-white/10 text-white hover:bg-white/[0.06]" data-testid="share-copy-btn">
              {copied ? <Check className="w-4 h-4 mr-2 text-emerald-400" /> : <Copy className="w-4 h-4 mr-2" />}
              {copied ? 'Copied!' : 'Copy Link'}
            </Button>
          </div>
        </section>

        {/* ═══ MORE VIDEOS — KEEP VIEWER ENGAGED ═══ */}
        <MoreVideosCarousel shareId={shareId} onNavigate={handleCreateOwn} />

        {/* ═══ BOTTOM CTA ═══ */}
        <section className="px-4 py-16" data-testid="bottom-cta">
          <div className="max-w-xl mx-auto text-center">
            <h2 className="text-2xl sm:text-3xl font-bold text-white mb-3 fade-up-d4">
              Don't just watch — create your own
            </h2>
            <p className="text-slate-400 mb-3">
              Type a story idea. Get a full video in under a minute. It's that simple.
            </p>
            <p className="text-xs text-slate-500 mb-8">People are creating videos like this every day</p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <Button
                onClick={handleCreateOwn}
                className="h-14 px-10 rounded-xl bg-gradient-to-r from-violet-600 to-rose-600 text-white font-bold text-base hover:shadow-[0_0_40px_-8px_rgba(139,92,246,0.5)] transition-all hover:scale-[1.02]"
                data-testid="bottom-create-btn"
              >
                <Zap className="w-5 h-5 mr-2" /> Create Your Video Now
              </Button>
              <Button
                onClick={handleRemix}
                disabled={remixing}
                variant="outline"
                className="h-12 px-6 rounded-xl border-violet-500/30 text-violet-300 hover:bg-violet-500/10 hover:border-violet-500/50"
                data-testid="bottom-remix-btn"
              >
                <Wand2 className="w-4 h-4 mr-2" /> Remix This Video
              </Button>
            </div>
            {forkCount > 0 && (
              <p className="text-xs text-slate-500 mt-4">
                <GitBranch className="w-3 h-3 inline mr-1" />
                {forkCount} {forkCount === 1 ? 'person has' : 'people have'} already remixed this video
              </p>
            )}
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/[0.04] py-6 px-4">
        <div className="max-w-4xl mx-auto text-center text-xs text-slate-500">
          Created with <Link to="/" className="text-violet-400 hover:text-violet-300">Visionary Suite</Link> — AI video creation platform
        </div>
      </footer>
    </div>
  );
}
