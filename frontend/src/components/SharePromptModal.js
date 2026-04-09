import React, { useState, useEffect, useRef } from 'react';
import { Share2, Copy, Check, X, Sparkles, ChevronRight, Trophy, TrendingUp, Heart, Link2 } from 'lucide-react';
import { toast } from 'sonner';
import { trackEvent } from '../utils/analytics';

const API = process.env.REACT_APP_BACKEND_URL;

// Context-driven messaging — adapts to the story's status
function getShareContext(context) {
  if (context?.isChallengeWinner) {
    return {
      icon: Trophy,
      iconColor: 'from-amber-500/20 to-yellow-500/20',
      iconTextColor: 'text-amber-400',
      title: 'Share your winning challenge story!',
      subtitle: 'You won — let the world see your creation',
    };
  }
  if (context?.isTrending) {
    return {
      icon: TrendingUp,
      iconColor: 'from-rose-500/20 to-orange-500/20',
      iconTextColor: 'text-rose-400',
      title: 'Your story is gaining momentum — share it now!',
      subtitle: 'Trending stories reach more viewers when shared early',
    };
  }
  if (context?.remixCount > 2) {
    return {
      icon: Heart,
      iconColor: 'from-pink-500/20 to-rose-500/20',
      iconTextColor: 'text-pink-400',
      title: 'People love this story — invite more viewers!',
      subtitle: `${context.remixCount} people have already remixed it`,
    };
  }
  return {
    icon: Sparkles,
    iconColor: 'from-violet-500/20 to-rose-500/20',
    iconTextColor: 'text-violet-400',
    title: 'Share your new AI story with friends',
    subtitle: 'Every share helps your story reach more creators',
  };
}

export default function SharePromptModal({ jobId, title, characterName, slug, onClose, context = {} }) {
  const [copied, setCopied] = useState(false);
  const dismissed = useRef(false);
  const shareUrl = slug ? `${window.location.origin}/v/${slug}` : '';
  const { icon: CtxIcon, iconColor, iconTextColor, title: ctxTitle, subtitle: ctxSubtitle } = getShareContext(context);

  // Personalized viral-proof subtitle: use real numbers when available
  let viralProof = ctxSubtitle;
  if (context?.userViralStats?.total_remix_conversions > 0) {
    viralProof = `Your stories inspired ${context.userViralStats.total_remix_conversions} creators — share this one to extend your reach`;
  } else if (!context?.isChallengeWinner && !context?.isTrending && !(context?.remixCount > 2)) {
    viralProof = 'Stories shared early reach more creators';
  }

  // "Share Again" CTA for stories with existing viral traction
  const showShareAgain = (context?.remixCount || 0) > 0;
  const shareAgainMessage = showShareAgain
    ? `This story already has ${context.remixCount} remix${context.remixCount !== 1 ? 'es' : ''} — share again to keep it growing`
    : null;

  const shareText = characterName
    ? `I just created "${title}" starring ${characterName} with AI in seconds! Continue the story:`
    : `I just created "${title}" with AI in seconds! See what happens next:`;

  // Track impression
  useEffect(() => {
    trackEvent('share_prompt_shown', {
      job_id: jobId,
      context_type: context?.isChallengeWinner ? 'challenge_winner' : context?.isTrending ? 'trending' : context?.remixCount > 2 ? 'highly_remixed' : 'standard',
    });
  }, [jobId, context]);

  const handleDismiss = () => {
    if (!dismissed.current) {
      dismissed.current = true;
      trackEvent('share_dismissed', { job_id: jobId });
    }
    onClose();
  };

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      toast.success('Link copied!');
      trackEvent('share_link_copied', { job_id: jobId });
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error('Failed to copy');
    }
  };

  const shareTo = (platform) => {
    const urls = {
      instagram: null, // Instagram doesn't support direct URL sharing — copy link instead
      twitter: `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(shareUrl)}`,
      whatsapp: `https://wa.me/?text=${encodeURIComponent(`${shareText} ${shareUrl}`)}`,
    };

    if (platform === 'instagram') {
      // Copy link and prompt user to paste in Instagram
      navigator.clipboard.writeText(shareUrl).then(() => {
        toast.success('Link copied! Paste it in your Instagram story or bio');
      }).catch(() => {});
      trackEvent('share_instagram_clicked', { job_id: jobId });
      return;
    }
    if (platform === 'reel') {
      navigator.clipboard.writeText(shareUrl).then(() => {
        toast.success('Link copied! Add it to your Reel caption');
      }).catch(() => {});
      trackEvent('share_reel_clicked', { job_id: jobId });
      return;
    }

    if (urls[platform]) window.open(urls[platform], '_blank', 'width=600,height=400');
    trackEvent('share_completed', { job_id: jobId, platform });

    // Also track via growth endpoint
    try {
      fetch(`${API}/api/growth/event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event: 'share_click',
          session_id: sessionStorage.getItem('growth_session_id') || 'unknown',
          meta: { platform, source: 'auto_share_prompt', job_id: jobId },
        }),
      }).catch(() => {});
    } catch {}
  };

  if (!slug) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" data-testid="share-prompt-modal">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={handleDismiss} />
      <div className="relative bg-[#0d0d18] border border-white/10 rounded-2xl max-w-sm w-full p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        <button onClick={handleDismiss} className="absolute top-3 right-3 text-slate-500 hover:text-white" data-testid="share-prompt-close">
          <X className="w-4 h-4" />
        </button>

        <div className="text-center mb-5">
          <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${iconColor} flex items-center justify-center mx-auto mb-3`}>
            <CtxIcon className={`w-6 h-6 ${iconTextColor}`} />
          </div>
          <h3 className="text-lg font-bold text-white" data-testid="share-prompt-title">
            {ctxTitle}
          </h3>
          <p className="text-xs text-slate-400 mt-1" data-testid="share-prompt-subtitle">
            {viralProof}
          </p>
        </div>

        {/* Primary: Copy Share Link */}
        <button
          onClick={copyLink}
          className="w-full flex items-center justify-between px-4 py-3 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-violet-600 to-rose-600 hover:opacity-90 transition-opacity mb-2"
          data-testid="share-prompt-copy-link"
        >
          <span className="flex items-center gap-2">
            {copied ? <Check className="w-4 h-4 text-emerald-300" /> : <Link2 className="w-4 h-4" />}
            {copied ? 'Copied!' : 'Copy Share Link'}
          </span>
          <ChevronRight className="w-4 h-4 text-white/50" />
        </button>

        {/* Secondary: Share to Instagram */}
        <button
          onClick={() => shareTo('instagram')}
          className="w-full flex items-center justify-between px-4 py-3 rounded-xl text-sm font-medium text-white bg-slate-700 hover:bg-slate-600 transition-colors mb-2"
          data-testid="share-prompt-instagram"
        >
          <span>Share to Instagram</span>
          <ChevronRight className="w-4 h-4 text-white/50" />
        </button>

        {/* Third: Share as Reel */}
        <button
          onClick={() => shareTo('reel')}
          className="w-full flex items-center justify-between px-4 py-3 rounded-xl text-sm font-medium text-slate-300 bg-white/[0.04] border border-white/[0.08] hover:bg-white/[0.08] transition-colors mb-2"
          data-testid="share-prompt-reel"
        >
          <span>Share as Reel</span>
          <ChevronRight className="w-4 h-4 text-white/30" />
        </button>

        {/* Additional: WhatsApp / Post Online */}
        <div className="flex gap-2 mt-1">
          <button
            onClick={() => shareTo('whatsapp')}
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl text-xs text-slate-400 bg-white/[0.03] hover:bg-white/[0.06] transition-colors"
            data-testid="share-prompt-whatsapp"
          >
            Send via Message
          </button>
          <button
            onClick={() => shareTo('twitter')}
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl text-xs text-slate-400 bg-white/[0.03] hover:bg-white/[0.06] transition-colors"
            data-testid="share-prompt-twitter"
          >
            Post Online
          </button>
        </div>

        <p className="text-center text-[10px] text-slate-600 mt-4">
          Every share helps {characterName || 'your story'} reach more creators
        </p>

        {/* Share Again CTA for stories with existing viral traction */}
        {showShareAgain && shareAgainMessage && (
          <div className="mt-2 space-y-1.5" data-testid="share-again-section">
            <p className="text-[10px] text-emerald-400/80 text-center px-2">{shareAgainMessage}</p>
            <button
              onClick={() => {
                copyLink();
                trackEvent('share_again_clicked', { job_id: jobId, copy_variant_id: 'share_again_momentum', remixes: context?.remixCount });
              }}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold text-emerald-300 bg-emerald-500/[0.06] border border-emerald-500/15 hover:bg-emerald-500/10 transition-colors"
              data-testid="share-prompt-share-again"
            >
              <TrendingUp className="w-3.5 h-3.5" />
              Share Again to Keep Momentum
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
