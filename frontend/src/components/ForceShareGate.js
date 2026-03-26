import React, { useState, useEffect } from 'react';
import { Share2, Play, ArrowRight, Copy, Check, Zap, Gift } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * ForceShareGate — "Your story is live!" modal after video completion.
 * Rewards: +5 share, +15 friend continues, +25 friend signs up.
 * Always shows Continue — sharing is strongly incentivized but not blocking.
 */
export function ForceShareGate({ jobId, title, slug, shareUrl, downloadUrl, onContinue, onDismiss }) {
  const [shared, setShared] = useState(false);
  const [countdown, setCountdown] = useState(5);
  const [copiedLink, setCopiedLink] = useState(false);

  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setTimeout(() => setCountdown(c => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [countdown]);

  const shareUrl_ = shareUrl || downloadUrl || `${window.location.origin}/v/${slug || jobId}`;

  const handleShare = async (platform) => {
    const url = encodeURIComponent(shareUrl_);
    const text = encodeURIComponent(`Check out this AI story: "${title}" — Made with Visionary Suite`);
    const links = {
      whatsapp: `https://wa.me/?text=${text}%20${url}`,
      twitter: `https://twitter.com/intent/tweet?text=${text}&url=${url}`,
      instagram: null,
      copy: null,
    };

    if (platform === 'copy') {
      try {
        await navigator.clipboard.writeText(decodeURIComponent(url));
        setCopiedLink(true);
        toast.success('Link copied! Share it anywhere.');
        setTimeout(() => setCopiedLink(false), 2000);
      } catch {}
    } else if (platform === 'instagram') {
      try {
        await navigator.clipboard.writeText(decodeURIComponent(url));
        toast.success('Link copied! Paste it in your Instagram story or bio.');
      } catch {}
    } else if (links[platform]) {
      window.open(links[platform], '_blank', 'width=600,height=400');
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
        if (data.rewarded) {
          toast.success(
            <div className="text-center">
              <p className="font-bold">+5 credits earned</p>
              <p className="text-xs opacity-70 mt-0.5">Share more to earn more</p>
            </div>,
            { duration: 4000 }
          );
        }
      }
    } catch {}
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 backdrop-blur-sm" data-testid="force-share-gate">
      <div className="w-full max-w-md mx-4 bg-[#0c0c14] border border-violet-500/30 rounded-2xl overflow-hidden shadow-2xl shadow-violet-500/10" style={{ animation: 'gate-enter 0.3s ease-out' }}>
        <div className="h-1 bg-gradient-to-r from-violet-600 via-rose-500 to-amber-500" />

        <div className="p-6 text-center">
          {/* Celebration icon */}
          <div className="w-16 h-16 rounded-full bg-gradient-to-r from-emerald-500 to-teal-500 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-emerald-500/20">
            <Zap className="w-8 h-8 text-white" />
          </div>

          <h2 className="text-xl font-black text-white mb-1" data-testid="share-gate-title">
            Your story is live!
          </h2>
          <p className="text-sm text-slate-400 mb-5">
            Share it with friends and earn credits when they engage.
          </p>

          {/* Reward breakdown — visible BEFORE sharing */}
          <div className="grid grid-cols-3 gap-2 mb-5" data-testid="reward-breakdown">
            <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-2.5">
              <p className="text-lg font-black text-emerald-400">+5</p>
              <p className="text-[10px] text-emerald-400/70 font-medium">per share</p>
            </div>
            <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-2.5">
              <p className="text-lg font-black text-amber-400">+15</p>
              <p className="text-[10px] text-amber-400/70 font-medium">friend continues</p>
            </div>
            <div className="bg-violet-500/10 border border-violet-500/20 rounded-xl p-2.5">
              <p className="text-lg font-black text-violet-400">+25</p>
              <p className="text-[10px] text-violet-400/70 font-medium">friend signs up</p>
            </div>
          </div>

          {/* Share buttons */}
          <div className="grid grid-cols-4 gap-2 mb-4" data-testid="share-buttons">
            <button onClick={() => handleShare('whatsapp')}
              className="py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-colors"
              data-testid="share-whatsapp">
              WhatsApp
            </button>
            <button onClick={() => handleShare('twitter')}
              className="py-3 rounded-xl bg-slate-700 hover:bg-slate-600 text-white text-xs font-bold transition-colors"
              data-testid="share-twitter">
              X
            </button>
            <button onClick={() => handleShare('instagram')}
              className="py-3 rounded-xl bg-gradient-to-br from-purple-600 to-pink-500 hover:opacity-90 text-white text-xs font-bold transition-opacity"
              data-testid="share-instagram">
              Instagram
            </button>
            <button onClick={() => handleShare('copy')}
              className="py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold transition-colors flex items-center justify-center gap-1"
              data-testid="share-copy">
              {copiedLink ? <><Check className="w-3 h-3" /> Copied</> : <><Copy className="w-3 h-3" /> Link</>}
            </button>
          </div>

          <p className="text-xs text-emerald-400/80 font-semibold mb-5">
            <Gift className="w-3.5 h-3.5 inline mr-1" />
            Earn up to +45 credits per share
          </p>

          {/* OR divider */}
          <div className="flex items-center gap-3 mb-4">
            <div className="flex-1 h-px bg-slate-700" />
            <span className="text-xs text-slate-500 font-medium">OR</span>
            <div className="flex-1 h-px bg-slate-700" />
          </div>

          {/* Continue button */}
          <button onClick={onContinue}
            className="w-full py-3.5 rounded-xl bg-gradient-to-r from-violet-600 to-rose-600 text-white font-bold text-sm flex items-center justify-center gap-2 hover:opacity-90 transition-opacity"
            style={{ animation: shared ? 'none' : 'cta-glow 2s ease-in-out infinite' }}
            data-testid="share-gate-continue">
            <Play className="w-4 h-4" /> Continue Next Episode <ArrowRight className="w-4 h-4" />
          </button>

          {/* Skip */}
          {countdown > 0 ? (
            <p className="text-[10px] text-slate-600 mt-3">Skip available in {countdown}s</p>
          ) : (
            <button onClick={onDismiss}
              className="text-[10px] text-slate-600 hover:text-slate-400 mt-3 transition-colors"
              data-testid="share-gate-skip">
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

/**
 * ShareRewardBar — Inline share section for post-gen result page.
 * Shows above Download with reward incentive.
 */
export function ShareRewardBar({ jobId, title, slug, shareUrl, downloadUrl }) {
  const [copiedLink, setCopiedLink] = useState(false);

  const shareUrl_ = shareUrl || downloadUrl || `${window.location.origin}/v/${slug || jobId}`;

  const handleShare = async (platform) => {
    const url = encodeURIComponent(shareUrl_);
    const text = encodeURIComponent(`Check out this AI story: "${title}"`);

    if (platform === 'copy') {
      try {
        await navigator.clipboard.writeText(decodeURIComponent(url));
        setCopiedLink(true);
        toast.success('Link copied!');
        setTimeout(() => setCopiedLink(false), 2000);
      } catch {}
    } else if (platform === 'instagram') {
      try {
        await navigator.clipboard.writeText(decodeURIComponent(url));
        toast.success('Link copied! Paste in your Instagram story.');
      } catch {}
    } else {
      const links = {
        whatsapp: `https://wa.me/?text=${text}%20${url}`,
        twitter: `https://twitter.com/intent/tweet?text=${text}&url=${url}`,
      };
      if (links[platform]) window.open(links[platform], '_blank', 'width=600,height=400');
    }

    // Track share
    try {
      const token = localStorage.getItem('token');
      if (token) {
        const res = await fetch(`${API}/api/growth/share-reward`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ job_id: jobId, platform }),
        });
        const data = await res.json();
        if (data.rewarded) {
          toast.success('+5 credits earned for sharing!', { duration: 3000 });
        }
      }
    } catch {}
  };

  return (
    <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/[0.05] p-4" data-testid="share-reward-bar">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Share2 className="w-4 h-4 text-emerald-400" />
          <span className="text-sm font-bold text-white">Share & Earn Credits</span>
        </div>
        <span className="text-[10px] text-emerald-400 font-semibold bg-emerald-500/15 px-2 py-0.5 rounded-full">
          up to +45 credits
        </span>
      </div>
      <div className="flex gap-2">
        <button onClick={() => handleShare('whatsapp')}
          className="flex-1 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-colors"
          data-testid="reward-share-whatsapp">WhatsApp</button>
        <button onClick={() => handleShare('twitter')}
          className="flex-1 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-white text-xs font-bold transition-colors"
          data-testid="reward-share-twitter">X</button>
        <button onClick={() => handleShare('instagram')}
          className="flex-1 py-2 rounded-lg bg-gradient-to-br from-purple-600 to-pink-500 hover:opacity-90 text-white text-xs font-bold transition-opacity"
          data-testid="reward-share-instagram">Instagram</button>
        <button onClick={() => handleShare('copy')}
          className="flex-1 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold transition-colors flex items-center justify-center gap-1"
          data-testid="reward-share-copy">
          {copiedLink ? <><Check className="w-3 h-3" /> Copied</> : <><Copy className="w-3 h-3" /> Copy</>}
        </button>
      </div>
      <div className="flex justify-center gap-3 mt-2.5 text-[10px]">
        <span className="text-emerald-400">+5 share</span>
        <span className="text-slate-600">|</span>
        <span className="text-amber-400">+15 friend continues</span>
        <span className="text-slate-600">|</span>
        <span className="text-violet-400">+25 friend signs up</span>
      </div>
    </div>
  );
}
