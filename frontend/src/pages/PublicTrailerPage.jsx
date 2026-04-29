/* eslint-disable */
// PublicTrailerPage — public share landing for `/trailer/:slug`.
// Fetches a fresh short-lived signed video URL from the backend so the
// raw bucket key is never exposed. Periodically re-signs (every 9 minutes)
// when the video stays paused/idle and the previous URL is about to expire.
import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Loader2, Film, Sparkles, Share2, MessageCircle, Heart } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

export default function PublicTrailerPage() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  // Auto-pick the right aspect for the viewer's device. Mobile (≤640px)
  // gets the 9:16 vertical cut, desktop gets the 16:9 widescreen — both
  // re-fetched fresh from /share/:slug so the URL is always signed.
  const initialFormat = typeof window !== 'undefined' && window.matchMedia
    ? (window.matchMedia('(max-width: 640px)').matches ? 'vertical' : 'wide')
    : 'wide';
  const [format, setFormat] = useState(initialFormat);
  const refreshTimerRef = useRef(null);

  // Fetch the share payload (mints a fresh signed URL each call).
  const fetchShare = async () => {
    try {
      const r = await fetch(`${API}/api/photo-trailer/share/${slug}`);
      if (!r.ok) {
        if (r.status === 404) setError('This trailer is no longer available.');
        else setError('Could not load this trailer.');
        return null;
      }
      const j = await r.json();
      setData(j);
      setLoading(false);
      return j;
    } catch (e) {
      setError('Network error loading trailer.');
      setLoading(false);
      return null;
    }
  };

  useEffect(() => {
    fetchShare();
    return () => { if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug]);

  // Re-sign 30s before expiry if the page is still open
  useEffect(() => {
    if (!data?.expires_in) return;
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    const ms = Math.max(60_000, (data.expires_in - 30) * 1000);
    refreshTimerRef.current = setTimeout(() => fetchShare(), ms);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data?.expires_in]);

  const shareThis = async () => {
    const url = window.location.href;
    const text = `🎬 Watch ${data?.creator_first_name || 'their'} AI movie trailer on Visionary Suite: ${url}`;
    try {
      if (navigator.share) await navigator.share({ title: data?.title || 'AI Movie Trailer', text, url });
      else { await navigator.clipboard.writeText(text); toast.success('Link copied'); }
    } catch {}
  };

  const shareWhatsApp = () => {
    const url = window.location.href;
    const text = `🎬 Watch this AI movie trailer on Visionary Suite: ${url}`;
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank', 'noopener,noreferrer');
  };

  const makeYourOwn = () => {
    navigate('/app/photo-trailer');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a10] text-white flex items-center justify-center" data-testid="public-trailer-loading">
        <Loader2 className="w-8 h-8 animate-spin text-violet-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#0a0a10] text-white flex items-center justify-center px-6" data-testid="public-trailer-error">
        <div className="max-w-md w-full text-center space-y-5">
          <Film className="w-12 h-12 mx-auto text-slate-500" />
          <h1 className="text-2xl font-bold">{error}</h1>
          <p className="text-slate-400 text-sm">It may have been removed by its creator. You can still create your own.</p>
          <button onClick={makeYourOwn} className="px-6 py-3 rounded-xl font-bold bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 transition-colors" data-testid="public-trailer-make-your-own">
            Make My Movie Trailer
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a10] text-white" data-testid="public-trailer-page">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        <header className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-[11px] uppercase tracking-widest text-violet-300 font-bold">YouStar</span>
            <span className="text-xs text-slate-500">·</span>
            <span className="text-xs text-slate-400">Visionary Suite</span>
          </div>
          <button onClick={shareThis} className="text-slate-300 hover:text-white inline-flex items-center gap-1.5 text-sm" data-testid="public-trailer-share-btn">
            <Share2 className="w-4 h-4" /> Share
          </button>
        </header>

        <div className="mb-5">
          <p className="text-xs uppercase tracking-wide text-violet-400 font-semibold mb-1">A trailer by {data.creator_first_name}</p>
          <h1 className="text-2xl sm:text-3xl font-bold">{data.title}</h1>
          <p className="text-sm text-slate-400 mt-1">{data.duration_seconds}s · AI-generated · with Visionary Suite</p>
        </div>

        <video
          key={format}
          src={(format === 'vertical' && data.vertical_video_url) ? data.vertical_video_url : data.video_url}
          poster={data.thumbnail_url || undefined}
          controls
          playsInline
          className={`w-full rounded-2xl border border-white/10 bg-black ${format === 'vertical' ? 'max-w-[420px] mx-auto block' : ''}`}
          data-testid="public-trailer-video"
        />

        {/* Format toggle — only when vertical is available */}
        {data.vertical_video_url && (
          <div className="mt-4 flex justify-center" data-testid="public-trailer-format-toggle">
            <div className="inline-flex p-1 rounded-xl border border-white/10 bg-white/[0.04]">
              <button
                type="button"
                onClick={() => setFormat('wide')}
                className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-colors ${format === 'wide' ? 'bg-violet-600 text-white' : 'text-slate-300 hover:text-white'}`}
                data-testid="public-trailer-format-wide"
              >
                16:9 Wide
              </button>
              <button
                type="button"
                onClick={() => setFormat('vertical')}
                className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-colors ${format === 'vertical' ? 'bg-fuchsia-600 text-white' : 'text-slate-300 hover:text-white'}`}
                data-testid="public-trailer-format-vertical"
              >
                9:16 Vertical
              </button>
            </div>
          </div>
        )}

        <div className="mt-6 grid grid-cols-2 gap-3">
          <button onClick={shareWhatsApp} className="py-3.5 rounded-xl font-semibold text-sm bg-[#25D366] hover:bg-[#1EA952] text-white inline-flex items-center justify-center gap-2 transition-colors" data-testid="public-trailer-whatsapp-btn">
            <MessageCircle className="w-4 h-4" /> Share on WhatsApp
          </button>
          <button onClick={shareThis} className="py-3.5 rounded-xl font-semibold text-sm bg-white/[0.06] hover:bg-white/[0.10] border border-white/10 inline-flex items-center justify-center gap-2 transition-colors" data-testid="public-trailer-copy-btn">
            <Share2 className="w-4 h-4" /> Copy / Share
          </button>
        </div>

        <div className="mt-8 p-5 rounded-2xl border border-violet-400/30 bg-gradient-to-br from-violet-500/10 to-fuchsia-500/5">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="w-5 h-5 text-amber-300" />
            <p className="text-base font-bold">Make yours in 60 seconds</p>
          </div>
          <p className="text-sm text-slate-300 mb-4">Upload 1–10 photos · Pick a template · Get your own personalized AI trailer.</p>
          <button onClick={makeYourOwn} className="w-full py-3.5 rounded-xl font-bold text-white bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 transition-colors inline-flex items-center justify-center gap-2" data-testid="public-trailer-cta-make-own">
            <Heart className="w-4 h-4" /> Make My Movie Trailer
          </button>
        </div>

        <footer className="mt-10 text-center text-[11px] text-slate-500">
          Visionary Suite · Trailers carry watermark + provenance metadata · 
          <a href="/" className="ml-1 text-slate-300 hover:text-white">visionary-suite.com</a>
        </footer>
      </div>
    </div>
  );
}
