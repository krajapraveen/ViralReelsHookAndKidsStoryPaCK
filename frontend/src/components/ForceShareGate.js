import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Share2, Play, ArrowRight, Copy, Check, Zap, Gift, Clock, Sparkles } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * ForceShareGate — Character-driven share prompt at peak emotional moment.
 * Uses character name + cliffhanger to personalize the share message.
 * Triggers after video completes, capturing excitement/curiosity/ownership.
 */
export function ForceShareGate({
  jobId, title, slug, shareUrl,
  onContinue, onDismiss,
  characterName, cliffhanger, characters,
}) {
  const [shared, setShared] = useState(false);
  const [countdown, setCountdown] = useState(5);
  const [copiedLink, setCopiedLink] = useState(false);

  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setTimeout(() => setCountdown(c => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [countdown]);

  const shareUrl_ = shareUrl || `${window.location.origin}/v/${slug || jobId}`;
  const charName = characterName || characters?.[0]?.name || '';
  const hookText = cliffhanger || '';

  // Build personalized share text per platform
  const buildShareText = (platform) => {
    if (charName && hookText) {
      const shortHook = hookText.length > 80 ? hookText.slice(0, 80) + '...' : hookText;
      return `"${shortHook}" — What happens to ${charName} next? Continue the story:`;
    }
    if (charName) {
      return `${charName}'s story isn't over yet... What happens next? Continue it here:`;
    }
    if (hookText) {
      const shortHook = hookText.length > 100 ? hookText.slice(0, 100) + '...' : hookText;
      return `"${shortHook}" — The story isn't over. You decide what happens next:`;
    }
    return `"${title}" — This AI story has no ending yet. Continue it here:`;
  };

  const handleShare = async (platform) => {
    const url = encodeURIComponent(shareUrl_);
    const text = encodeURIComponent(buildShareText(platform));
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

  return createPortal(
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 backdrop-blur-sm" data-testid="force-share-gate">
      <div
        className="w-full max-w-md mx-4 bg-[#0c0c14] border border-violet-500/30 rounded-2xl overflow-hidden shadow-2xl shadow-violet-500/10"
        style={{ animation: 'gate-enter 0.4s cubic-bezier(0.16,1,0.3,1)' }}
      >
        <div className="h-1 bg-gradient-to-r from-violet-600 via-rose-500 to-amber-500" />

        <div className="p-6">
          {/* ─── CHARACTER-DRIVEN HOOK ─── */}
          {charName ? (
            <div className="text-center mb-5" data-testid="character-hook">
              <div className="w-14 h-14 rounded-full bg-gradient-to-br from-violet-500 to-rose-500 flex items-center justify-center mx-auto mb-3 text-xl font-black text-white shadow-lg shadow-violet-500/20">
                {charName[0]}
              </div>
              <h2 className="text-lg font-black text-white leading-snug" data-testid="share-gate-title">
                {charName}'s story isn't over yet...
              </h2>
              {hookText ? (
                <p className="text-sm text-slate-300 mt-2 italic leading-relaxed" data-testid="share-gate-hook">
                  "{hookText.length > 120 ? hookText.slice(0, 120) + '...' : hookText}"
                </p>
              ) : (
                <p className="text-sm text-slate-400 mt-2">
                  But what happens next?
                </p>
              )}
            </div>
          ) : (
            <div className="text-center mb-5">
              <div className="w-14 h-14 rounded-full bg-gradient-to-r from-emerald-500 to-teal-500 flex items-center justify-center mx-auto mb-3 shadow-lg shadow-emerald-500/20">
                <Sparkles className="w-7 h-7 text-white" />
              </div>
              <h2 className="text-lg font-black text-white" data-testid="share-gate-title">
                Your story is live!
              </h2>
              <p className="text-sm text-slate-400 mt-1">
                {hookText || 'The story has no ending yet... someone else will decide.'}
              </p>
            </div>
          )}

          {/* ─── URGENCY LINE ─── */}
          <div className="flex items-center justify-center gap-2 mb-4 py-2 rounded-lg bg-rose-500/[0.06] border border-rose-500/10" data-testid="urgency-line">
            <Clock className="w-3.5 h-3.5 text-rose-400" />
            <p className="text-xs text-rose-300 font-semibold">
              Someone else might continue {charName ? `${charName}'s` : 'your'} story first...
            </p>
          </div>

          {/* ─── SHARE CTA ─── */}
          <p className="text-center text-xs text-slate-500 font-medium mb-2">
            Will you share it — or let someone else decide what happens next?
          </p>

          <div className="grid grid-cols-4 gap-2 mb-3" data-testid="share-buttons">
            <button onClick={() => handleShare('whatsapp')}
              className="py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-all hover:scale-[1.02] active:scale-[0.98]"
              data-testid="share-whatsapp">
              WhatsApp
            </button>
            <button onClick={() => handleShare('twitter')}
              className="py-3 rounded-xl bg-slate-700 hover:bg-slate-600 text-white text-xs font-bold transition-all hover:scale-[1.02] active:scale-[0.98]"
              data-testid="share-twitter">
              X
            </button>
            <button onClick={() => handleShare('instagram')}
              className="py-3 rounded-xl bg-gradient-to-br from-purple-600 to-pink-500 hover:opacity-90 text-white text-xs font-bold transition-all hover:scale-[1.02] active:scale-[0.98]"
              data-testid="share-instagram">
              Instagram
            </button>
            <button onClick={() => handleShare('copy')}
              className="py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-1"
              data-testid="share-copy">
              {copiedLink ? <><Check className="w-3 h-3" /> Copied</> : <><Copy className="w-3 h-3" /> Link</>}
            </button>
          </div>

          {/* ─── REWARD BREAKDOWN ─── */}
          <div className="grid grid-cols-3 gap-2 mb-4" data-testid="reward-breakdown">
            <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-2 text-center">
              <p className="text-base font-black text-emerald-400">+5</p>
              <p className="text-[10px] text-emerald-400/70 font-medium">you share</p>
            </div>
            <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-2 text-center">
              <p className="text-base font-black text-amber-400">+15</p>
              <p className="text-[10px] text-amber-400/70 font-medium">friend continues</p>
            </div>
            <div className="bg-violet-500/10 border border-violet-500/20 rounded-xl p-2 text-center">
              <p className="text-base font-black text-violet-400">+25</p>
              <p className="text-[10px] text-violet-400/70 font-medium">friend signs up</p>
            </div>
          </div>

          {/* ─── DIVIDER ─── */}
          <div className="flex items-center gap-3 mb-3">
            <div className="flex-1 h-px bg-white/[0.06]" />
            <span className="text-[10px] text-slate-600 font-medium uppercase tracking-wider">or</span>
            <div className="flex-1 h-px bg-white/[0.06]" />
          </div>

          {/* ─── CONTINUE BUTTON ─── */}
          <button onClick={onContinue}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-violet-600 to-rose-600 text-white font-bold text-sm flex items-center justify-center gap-2 hover:opacity-90 transition-opacity"
            style={{ animation: shared ? 'none' : 'cta-glow 2s ease-in-out infinite' }}
            data-testid="share-gate-continue">
            <Play className="w-4 h-4" /> Continue {charName ? `${charName}'s` : 'the'} Story <ArrowRight className="w-4 h-4" />
          </button>

          {/* ─── SKIP ─── */}
          {countdown > 0 ? (
            <p className="text-[10px] text-slate-600 mt-3 text-center">Skip available in {countdown}s</p>
          ) : (
            <button onClick={onDismiss}
              className="block mx-auto text-[10px] text-slate-600 hover:text-slate-400 mt-3 transition-colors"
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
    </div>,
    document.body
  );
}

/**
 * ShareRewardBar — Inline share section for post-gen result page.
 * Character-driven: personalizes the share text.
 */
export function ShareRewardBar({ jobId, title, slug, shareUrl, characterName, cliffhanger }) {
  const [copiedLink, setCopiedLink] = useState(false);
  const shareUrl_ = shareUrl || `${window.location.origin}/v/${slug || jobId}`;
  const charName = characterName || '';

  const handleShare = async (platform) => {
    const url = encodeURIComponent(shareUrl_);
    let shareText;
    if (charName && cliffhanger) {
      shareText = `"${cliffhanger.slice(0, 80)}..." — What happens to ${charName} next?`;
    } else if (charName) {
      shareText = `${charName}'s story isn't over yet... Continue it here:`;
    } else {
      shareText = `"${title}" — This AI story needs an ending. Continue it:`;
    }
    const text = encodeURIComponent(shareText);

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
          <span className="text-sm font-bold text-white">
            {charName ? `Share ${charName}'s story` : 'Share & Earn Credits'}
          </span>
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
