import React, { useState, useEffect } from 'react';
import { Share2, Play, ArrowRight, Lock } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * ForceShareGate — Appears after video completion.
 * User must either Share or Continue to proceed.
 * This maximizes K-factor by gating the next episode behind a share action.
 */
export function ForceShareGate({ jobId, title, slug, shareUrl, downloadUrl, onContinue, onDismiss }) {
  const [shared, setShared] = useState(false);
  const [countdown, setCountdown] = useState(5);

  // Allow dismiss after 5 seconds (so it's not permanently blocking)
  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setTimeout(() => setCountdown(c => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [countdown]);

  const handleShare = async (platform) => {
    const url = encodeURIComponent(shareUrl || downloadUrl || `${window.location.origin}/v/${slug || jobId}`);
    const text = encodeURIComponent(`Check out this AI story: "${title}" — Made with Visionary Suite`);
    const urls = {
      whatsapp: `https://wa.me/?text=${text}%20${url}`,
      twitter: `https://twitter.com/intent/tweet?text=${text}&url=${url}`,
      copy: null,
    };

    if (platform === 'copy') {
      try {
        await navigator.clipboard.writeText(decodeURIComponent(url));
        toast.success('Link copied!');
      } catch {}
    } else if (urls[platform]) {
      window.open(urls[platform], '_blank', 'width=600,height=400');
    }

    setShared(true);

    // Claim share reward
    try {
      const token = localStorage.getItem('token');
      if (token) {
        const res = await fetch(`${API}/api/growth/share-reward`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ job_id: jobId, platform }),
        });
        const data = await res.json();
        if (data.rewarded) toast.success('+5 credits for sharing!');
      }
    } catch {}
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 backdrop-blur-sm" data-testid="force-share-gate">
      <div className="w-full max-w-md mx-4 bg-[#0c0c14] border border-violet-500/30 rounded-2xl overflow-hidden shadow-2xl shadow-violet-500/10" style={{ animation: 'gate-enter 0.3s ease-out' }}>
        {/* Header gradient bar */}
        <div className="h-1 bg-gradient-to-r from-violet-600 via-rose-500 to-orange-500" />

        <div className="p-6 text-center">
          <div className="w-14 h-14 rounded-full bg-gradient-to-r from-violet-600 to-rose-600 flex items-center justify-center mx-auto mb-4">
            <Share2 className="w-7 h-7 text-white" />
          </div>

          <h2 className="text-xl font-black text-white mb-2" data-testid="force-share-title">
            Share to unlock the next episode
          </h2>
          <p className="text-sm text-slate-400 mb-6">
            Your story is spreading. Share it and earn +5 credits, or continue the adventure.
          </p>

          {/* Share buttons */}
          <div className="grid grid-cols-3 gap-2 mb-4">
            <button
              onClick={() => handleShare('whatsapp')}
              className="py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-colors"
              data-testid="force-share-whatsapp"
            >
              WhatsApp
            </button>
            <button
              onClick={() => handleShare('twitter')}
              className="py-3 rounded-xl bg-slate-700 hover:bg-slate-600 text-white text-xs font-bold transition-colors"
              data-testid="force-share-twitter"
            >
              X / Twitter
            </button>
            <button
              onClick={() => handleShare('copy')}
              className="py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold transition-colors"
              data-testid="force-share-copy"
            >
              Copy Link
            </button>
          </div>

          {/* Reward badges */}
          <div className="flex justify-center gap-2 mb-5 text-[10px]">
            <span className="text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full font-bold">+5 share</span>
            <span className="text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full font-bold">+15 friend continues</span>
            <span className="text-violet-400 bg-violet-500/10 px-2 py-0.5 rounded-full font-bold">+25 friend signs up</span>
          </div>

          {/* OR divider */}
          <div className="flex items-center gap-3 mb-4">
            <div className="flex-1 h-px bg-slate-700" />
            <span className="text-xs text-slate-500 font-medium">OR</span>
            <div className="flex-1 h-px bg-slate-700" />
          </div>

          {/* Continue button (always available) */}
          <button
            onClick={onContinue}
            className="w-full py-3.5 rounded-xl bg-gradient-to-r from-violet-600 to-rose-600 text-white font-bold text-sm flex items-center justify-center gap-2 hover:opacity-90 transition-opacity"
            style={{ animation: shared ? 'none' : 'cta-glow 2s ease-in-out infinite' }}
            data-testid="force-share-continue"
          >
            <Play className="w-4 h-4" /> Continue Next Episode <ArrowRight className="w-4 h-4" />
          </button>

          {/* Skip after countdown */}
          {countdown > 0 ? (
            <p className="text-[10px] text-slate-600 mt-3">Skip available in {countdown}s</p>
          ) : (
            <button
              onClick={onDismiss}
              className="text-[10px] text-slate-600 hover:text-slate-400 mt-3 transition-colors"
              data-testid="force-share-skip"
            >
              Skip for now
            </button>
          )}
        </div>
      </div>

      <style>{`
        @keyframes gate-enter { from { opacity: 0; transform: scale(0.95) translateY(10px); } to { opacity: 1; transform: scale(1) translateY(0); } }
        @keyframes cta-glow { 0%, 100% { box-shadow: 0 0 30px -8px rgba(139,92,246,0.4); } 50% { box-shadow: 0 0 50px -5px rgba(139,92,246,0.6); } }
      `}</style>
    </div>
  );
}
