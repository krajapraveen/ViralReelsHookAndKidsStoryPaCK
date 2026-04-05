import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  Play, ArrowRight, Copy, Check, Loader2, AlertCircle,
  MessageCircle, Twitter, Eye, GitBranch, Clock,
  Sparkles, Users, ChevronRight, Share2
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import api from '../utils/api';

const API = process.env.REACT_APP_BACKEND_URL;

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

export default function SharePage() {
  const { shareId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);
  const [forking, setForking] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get(`/api/share/${shareId}`);
        if (res.data.success) setData(res.data);
        else setError('Share link not found');
      } catch (err) {
        setError(err.response?.status === 404
          ? 'This story link has expired or does not exist'
          : 'Failed to load story');
      } finally {
        setLoading(false);
      }
    })();
  }, [shareId]);

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    toast.success('Link copied!');
    setTimeout(() => setCopied(false), 2000);
  }, []);

  const handleWhatsApp = useCallback(() => {
    const caption = data?.shareCaption || data?.hookText || `I started this story… can you finish it?`;
    const url = window.location.href;
    window.open(`https://wa.me/?text=${encodeURIComponent(caption + '\n' + url)}`, '_blank');
  }, [data]);

  const handleTwitter = useCallback(() => {
    const caption = data?.shareCaption || data?.hookText || `This story isn't finished yet…`;
    const url = window.location.href;
    window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(caption)}&url=${encodeURIComponent(url)}`, '_blank');
  }, [data]);

  const handleContinue = useCallback(async () => {
    setForking(true);
    try {
      const res = await api.post(`/api/share/${shareId}/fork`);
      const fork = res.data.fork;
      // Store fork context for the studio using remix_data format (matches StoryVideoPipeline)
      localStorage.setItem('remix_data', JSON.stringify({
        prompt: fork.storyContext,
        timestamp: Date.now(),
        source_tool: 'share-page-continue',
        remixFrom: {
          tool: 'story-video-studio',
          prompt: fork.storyContext,
          title: fork.parentTitle,
          parentId: fork.parentShareId,
          hook_text: fork.hookText,
          characters: fork.characters,
          settings: {
            tone: fork.tone,
            conflict: fork.conflict,
          },
        },
      }));
      // Also store fork_data for backward compatibility with StoryVideoStudio.js
      localStorage.setItem('fork_data', JSON.stringify({
        parentShareId: fork.parentShareId,
        parentTitle: fork.parentTitle,
        prompt: fork.storyContext,
        characters: fork.characters,
        tone: fork.tone,
        conflict: fork.conflict,
        timestamp: Date.now(),
        source: 'share-page-continue',
      }));
      navigate('/app/story-video-studio');
    } catch {
      toast.error('Could not start continuation');
    } finally {
      setForking(false);
    }
  }, [shareId, navigate]);

  const handleCreateOwn = useCallback(() => {
    navigate('/app/story-video-studio');
  }, [navigate]);

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
          <h1 className="text-2xl font-bold text-white mb-2">Story Not Found</h1>
          <p className="text-slate-400 mb-6">{error}</p>
          <Button onClick={() => navigate('/')} className="bg-violet-600 hover:bg-violet-500">
            Discover Stories <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      </div>
    );
  }

  const forkCount = data.forks || 0;
  const hookLine = data.hookText || data.preview?.slice(0, 120) || '';

  return (
    <div className="min-h-screen bg-[#07070f]" data-testid="share-page">
      <style>{`
        @keyframes fadeUp { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
        .fade-up { animation: fadeUp 0.5s ease-out both; }
        .fade-up-2 { animation: fadeUp 0.5s ease-out 0.1s both; }
        .fade-up-3 { animation: fadeUp 0.5s ease-out 0.2s both; }
        .fade-up-4 { animation: fadeUp 0.5s ease-out 0.3s both; }
        @keyframes pulseGlow { 0%,100% { box-shadow: 0 0 0 0 rgba(139,92,246,0.4); } 50% { box-shadow: 0 0 0 14px rgba(139,92,246,0); } }
        .pulse-cta { animation: pulseGlow 2s infinite; }
      `}</style>

      {/* Minimal Header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-[#07070f]/80 backdrop-blur-xl border-b border-white/[0.04]">
        <div className="max-w-4xl mx-auto px-4 h-12 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-gradient-to-br from-violet-500 to-rose-500 flex items-center justify-center">
              <Sparkles className="w-3 h-3 text-white" />
            </div>
            <span className="text-sm font-bold text-white">Visionary Suite</span>
          </Link>
          <button onClick={handleCopy} className="text-xs text-slate-400 hover:text-white flex items-center gap-1.5 transition-colors" data-testid="header-copy-btn">
            {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Share2 className="w-3 h-3" />}
            {copied ? 'Copied' : 'Share'}
          </button>
        </div>
      </header>

      <main className="pt-12">
        {/* ═══ HERO: Hook + CTA (above the fold) ═══ */}
        <section className="relative px-4 pt-10 pb-8" data-testid="share-hero">
          <div className="absolute inset-0 pointer-events-none">
            <div className="absolute top-0 left-1/3 w-[500px] h-[400px] bg-violet-600/[0.06] rounded-full blur-[160px]" />
          </div>

          <div className="relative max-w-2xl mx-auto">
            {/* Social proof bar */}
            <div className="flex items-center justify-center gap-4 mb-6 fade-up" data-testid="social-proof-bar">
              {forkCount > 0 && (
                <div className="flex items-center gap-1.5 text-xs text-violet-300 bg-violet-500/10 border border-violet-500/20 px-3 py-1.5 rounded-full">
                  <GitBranch className="w-3 h-3" />
                  <span className="font-semibold">{forkCount}</span> {forkCount === 1 ? 'person' : 'people'} continued this story
                </div>
              )}
              {data.recentForks?.length > 0 && (
                <div className="flex items-center gap-1.5 text-xs text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-full">
                  <Clock className="w-3 h-3" />
                  Last continued {timeAgo(data.recentForks[0]?.createdAt)}
                </div>
              )}
              <div className="flex items-center gap-1.5 text-xs text-slate-400 bg-white/[0.04] px-3 py-1.5 rounded-full">
                <Eye className="w-3 h-3" /> {data.views || 0} views
              </div>
            </div>

            {/* Hook text */}
            {hookLine && (
              <p className="text-center text-lg md:text-xl text-violet-200 font-medium italic leading-relaxed mb-4 fade-up" data-testid="hook-text">
                "{hookLine}"
              </p>
            )}

            {/* Title */}
            <h1 className="text-3xl sm:text-4xl md:text-5xl font-black text-center text-white tracking-tight leading-[1.1] mb-6 fade-up-2" data-testid="share-title">
              {data.title || 'Untitled Story'}
            </h1>

            {/* Primary CTA */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 fade-up-3" data-testid="hero-ctas">
              <Button
                onClick={handleContinue}
                disabled={forking}
                className="h-14 px-10 rounded-xl bg-gradient-to-r from-violet-600 to-rose-600 text-white font-bold text-base hover:shadow-[0_0_40px_-8px_rgba(139,92,246,0.5)] transition-all hover:scale-[1.02] pulse-cta"
                data-testid="continue-story-btn"
              >
                {forking ? (
                  <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> Loading story...</>
                ) : (
                  <><Play className="w-5 h-5 mr-2" /> Continue This Story</>
                )}
              </Button>
              <Button
                onClick={handleCreateOwn}
                variant="outline"
                className="h-12 px-6 rounded-xl border-white/10 text-white hover:bg-white/[0.06]"
                data-testid="create-own-btn"
              >
                <Sparkles className="w-4 h-4 mr-2 text-violet-400" /> Create Your Own Version
              </Button>
            </div>
          </div>
        </section>

        {/* ═══ STORY PREVIEW ═══ */}
        <section className="px-4 py-8" data-testid="story-preview">
          <div className="max-w-3xl mx-auto">
            {data.thumbnailUrl && (
              <div className="rounded-2xl overflow-hidden border border-white/[0.06] mb-6 fade-up-4">
                <img
                  src={data.thumbnailUrl}
                  alt={data.title}
                  className="w-full object-cover max-h-[500px]"
                  data-testid="story-thumbnail"
                />
              </div>
            )}

            {data.preview && (
              <div className="bg-white/[0.02] border border-white/[0.06] rounded-2xl p-6 mb-6" data-testid="story-text-preview">
                <p className="text-slate-300 leading-relaxed whitespace-pre-wrap">
                  {data.preview}
                </p>
                {data.preview.length > 200 && (
                  <div className="mt-4 pt-4 border-t border-white/[0.06] text-center">
                    <p className="text-sm text-violet-400 font-medium">
                      What happens next? Continue the story to find out...
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Characters */}
            {data.characters?.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-6" data-testid="character-tags">
                <span className="text-[10px] font-bold tracking-wider uppercase text-slate-500">Characters:</span>
                {data.characters.map((c, i) => (
                  <span key={i} className="text-xs px-2.5 py-1 rounded-full bg-violet-500/10 text-violet-300 border border-violet-500/20">
                    {c}
                  </span>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* ═══ BRANCH COUNT + SHARE (mid-page) ═══ */}
        <section className="px-4 py-8 border-y border-white/[0.04]" data-testid="branch-section">
          <div className="max-w-2xl mx-auto">
            {forkCount > 0 && (
              <div className="text-center mb-6">
                <div className="inline-flex items-center gap-2 text-lg font-bold text-white">
                  <GitBranch className="w-5 h-5 text-violet-400" />
                  This story has {forkCount} version{forkCount !== 1 ? 's' : ''}
                </div>
                <p className="text-sm text-slate-400 mt-1">Each person took it in a different direction</p>
              </div>
            )}

            {/* Share tools */}
            <div className="flex items-center justify-center gap-3">
              <Button onClick={handleWhatsApp} variant="outline" className="border-white/10 text-white hover:bg-emerald-500/10 hover:border-emerald-500/30 hover:text-emerald-300" data-testid="share-whatsapp-btn">
                <MessageCircle className="w-4 h-4 mr-2" /> WhatsApp
              </Button>
              <Button onClick={handleTwitter} variant="outline" className="border-white/10 text-white hover:bg-sky-500/10 hover:border-sky-500/30 hover:text-sky-300" data-testid="share-twitter-btn">
                <Twitter className="w-4 h-4 mr-2" /> Twitter
              </Button>
              <Button onClick={handleCopy} variant="outline" className="border-white/10 text-white hover:bg-white/[0.06]" data-testid="share-copy-btn">
                {copied ? <Check className="w-4 h-4 mr-2 text-emerald-400" /> : <Copy className="w-4 h-4 mr-2" />}
                {copied ? 'Copied!' : 'Copy Link'}
              </Button>
            </div>
          </div>
        </section>

        {/* ═══ BOTTOM CTA (repeated after scroll) ═══ */}
        <section className="px-4 py-16" data-testid="bottom-cta">
          <div className="max-w-xl mx-auto text-center">
            <h2 className="text-2xl sm:text-3xl font-bold text-white mb-3">
              This story isn't finished yet
            </h2>
            <p className="text-slate-400 mb-8">
              What happens next is up to you. Continue it — or start something entirely new.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <Button
                onClick={handleContinue}
                disabled={forking}
                className="h-14 px-10 rounded-xl bg-gradient-to-r from-violet-600 to-rose-600 text-white font-bold text-base hover:shadow-[0_0_40px_-8px_rgba(139,92,246,0.5)] transition-all hover:scale-[1.02]"
                data-testid="bottom-continue-btn"
              >
                <Play className="w-5 h-5 mr-2" /> Continue This Story
              </Button>
              <Button
                onClick={handleCreateOwn}
                variant="outline"
                className="h-12 px-6 rounded-xl border-white/10 text-white hover:bg-white/[0.06]"
                data-testid="bottom-create-btn"
              >
                Start Fresh <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </div>

            {forkCount > 0 && (
              <p className="text-xs text-slate-500 mt-4">
                <Users className="w-3 h-3 inline mr-1" />
                {forkCount} {forkCount === 1 ? 'person has' : 'people have'} already continued this story
              </p>
            )}
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/[0.04] py-6 px-4">
        <div className="max-w-4xl mx-auto text-center text-xs text-slate-500">
          Created with <Link to="/" className="text-violet-400 hover:text-violet-300">Visionary Suite</Link>
        </div>
      </footer>
    </div>
  );
}
