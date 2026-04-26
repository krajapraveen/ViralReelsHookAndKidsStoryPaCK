import React, { useEffect, useRef, useState } from 'react';
import { X, Zap, Sparkles, Clock, ShieldCheck, Users, Captions } from 'lucide-react';
import { trackFunnel } from '../utils/funnelTracker';

const API = process.env.REACT_APP_BACKEND_URL;

// Situational urgency — purely time-based copy. NO fake countdowns.
function getSituationalUrgency() {
  const now = new Date();
  const hour = now.getHours();
  const day = now.getDay(); // 0 = Sun
  if (hour >= 19 && hour < 23) return "Make tonight's bedtime story unforgettable";
  if (hour >= 23 || hour < 6) return "Tuck them in with their own story";
  if (hour >= 6 && hour < 11) return "Start the morning with a magical story";
  if (day === 0 || day === 6) return "Perfect for a weekend afternoon";
  return "Worth telling. Worth keeping.";
}

/**
 * P1.2 Visual Reward Preview — show what they're paying for BEFORE the paywall.
 *
 * Pattern: Ken Burns thumbnail + waveform + subtitle preview + countdown.
 * Pure CSS animation — no real render needed. The illusion of motion drives intent.
 *
 * Open this in response to a "Turn into Video" intent click. On primary CTA,
 * fire video_reward_preview_cta_clicked then call onContinue() to proceed to
 * paywall/login as before.
 */
export default function VideoRewardPreview({
  open,
  onClose,
  onContinue,
  storyTitle,
  storyText,
  heroImage,
  storyId,
  source,
  priceLabel = '₹29',
}) {
  const [eta, setEta] = useState(45);
  const [socialProof, setSocialProof] = useState(null);
  const intervalRef = useRef(null);
  const subtitleHook = (storyText || '').split('\n').filter(p => p.trim())[0]?.slice(0, 110) || storyTitle || '';
  const urgency = useRef(getSituationalUrgency()).current;

  useEffect(() => {
    if (!open) return;
    try {
      trackFunnel('video_reward_preview_shown', {
        meta: { story_id: storyId, source, price_label: priceLabel },
      });
    } catch {}
    setEta(45);
    intervalRef.current = setInterval(() => {
      setEta(prev => (prev > 1 ? prev - 1 : prev));
    }, 1000);
    // Fetch real social proof — fallback if low volume.
    if (!socialProof) {
      fetch(`${API}/api/public/social-proof`)
        .then(r => r.ok ? r.json() : null)
        .then(d => { if (d?.label) setSocialProof(d); })
        .catch(() => {});
    }
    return () => clearInterval(intervalRef.current);
  }, [open, storyId, source, priceLabel, socialProof]);

  if (!open) return null;

  const handlePrimary = () => {
    try {
      trackFunnel('video_reward_preview_cta_clicked', {
        meta: { story_id: storyId, source, price_label: priceLabel },
      });
    } catch {}
    onContinue?.();
  };

  const handleDismiss = () => {
    try {
      trackFunnel('video_reward_preview_dismissed', {
        meta: { story_id: storyId, source },
      });
    } catch {}
    onClose?.();
  };

  return (
    <div
      className="fixed inset-0 z-[9999] flex items-end sm:items-center justify-center"
      data-testid="video-reward-preview-overlay"
    >
      <div className="absolute inset-0 bg-black/80 backdrop-blur-md" onClick={handleDismiss} />

      <div
        className="relative w-full max-w-md mx-auto sm:mx-4 bg-[#0d0d18] border border-white/10 sm:rounded-2xl rounded-t-2xl overflow-hidden max-h-[92vh] overflow-y-auto vrp-slide-up"
        data-testid="video-reward-preview-modal"
      >
        <button
          onClick={handleDismiss}
          className="absolute top-3 right-3 z-10 p-1.5 rounded-full bg-black/40 hover:bg-black/60 transition-colors"
          data-testid="vrp-close-btn"
          aria-label="Close preview"
        >
          <X className="w-4 h-4 text-slate-300" />
        </button>

        {/* ── Animated thumbnail (Ken Burns) ─────────────────────────── */}
        <div className="relative aspect-video w-full overflow-hidden bg-black">
          <img
            src={heroImage}
            alt={storyTitle}
            loading="eager"
            className="absolute inset-0 w-full h-full object-cover vrp-kenburns"
            data-testid="vrp-thumbnail"
          />
          {/* dark gradient + subtle vignette */}
          <div className="absolute inset-0 bg-gradient-to-b from-black/0 via-black/30 to-black/85" />

          {/* Live preview chip */}
          <div className="absolute top-3 left-3 px-2 py-0.5 rounded-full bg-rose-500/90 text-white text-[10px] font-bold tracking-widest uppercase flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" /> Preview
          </div>

          {/* Title overlay */}
          <div className="absolute left-4 right-4 bottom-12 text-white">
            <p className="text-[11px] uppercase tracking-widest text-amber-300/90 font-semibold mb-1">
              Your Cinematic Reel
            </p>
            <h3 className="text-xl font-bold leading-tight" data-testid="vrp-title">{storyTitle}</h3>
          </div>

          {/* Burned-in subtitle preview */}
          <div className="absolute left-4 right-4 bottom-2 text-white/95 text-[13px] leading-snug font-medium drop-shadow-[0_1px_4px_rgba(0,0,0,0.9)] vrp-caption-fade" data-testid="vrp-subtitle">
            <Captions className="inline w-3.5 h-3.5 mr-1 text-amber-300" />
            "{subtitleHook}"
          </div>

          {/* Music waveform */}
          <div className="absolute top-3 right-12 flex items-end gap-0.5 h-5" aria-hidden="true">
            {[3, 5, 8, 4, 7, 9, 5, 6].map((h, i) => (
              <span
                key={i}
                className="w-0.5 bg-white/80 vrp-bar"
                style={{ animationDelay: `${i * 90}ms`, height: `${h * 2}px` }}
              />
            ))}
          </div>
        </div>

        {/* ── Social proof (real or qualitative) ─────────────────────── */}
        {socialProof && (
          <div className="px-5 pt-4 pb-1 text-center" data-testid="vrp-social-proof" data-kind={socialProof.kind}>
            <span className="inline-flex items-center gap-1.5 text-amber-300 text-xs font-medium">
              <Users className="w-3.5 h-3.5" />
              {socialProof.label}
            </span>
          </div>
        )}

        {/* ── ETA + CTA ─────────────────────────────────────────────── */}
        <div className="px-5 pt-3 pb-5 sm:pb-5" style={{ paddingBottom: 'max(1.25rem, env(safe-area-inset-bottom))' }}>
          <button
            onClick={handlePrimary}
            className="w-full py-4 px-5 rounded-xl font-bold text-white text-base flex items-center justify-center gap-2.5 vrp-cta active:scale-[0.98] transition-transform"
            data-testid="vrp-cta-primary"
          >
            <Zap className="w-5 h-5" />
            Make My Video — {priceLabel}
          </button>

          {/* Trust + Urgency micro-block (P1.6 — strictly 3 lines, no clutter) */}
          <div className="mt-3 space-y-1.5 text-center" data-testid="vrp-trust-block">
            <p className="text-emerald-300 text-[12px] flex items-center justify-center gap-1.5" data-testid="vrp-speed">
              <Clock className="w-3 h-3" />
              <span data-testid="vrp-eta">Ready in under {eta} seconds</span>
            </p>
            <p className="text-slate-400 text-[12px] flex items-center justify-center gap-1.5" data-testid="vrp-risk-reversal">
              <ShieldCheck className="w-3 h-3 text-emerald-400/70" />
              <span>Not happy? Regenerate free.</span>
            </p>
            <p className="text-amber-200/80 text-[12px] flex items-center justify-center gap-1.5" data-testid="vrp-urgency">
              <Sparkles className="w-3 h-3" />
              <span>{urgency}</span>
            </p>
          </div>
        </div>
      </div>

      <style>{`
        .vrp-slide-up { animation: vrpSlideUp 0.36s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
        @keyframes vrpSlideUp { from { transform: translateY(40px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        .vrp-kenburns { animation: vrpKenburns 9s ease-in-out infinite alternate; transform-origin: 60% 40%; }
        @keyframes vrpKenburns {
          0% { transform: scale(1.06) translate3d(0, 0, 0); }
          100% { transform: scale(1.18) translate3d(-12px, -8px, 0); }
        }
        .vrp-caption-fade { animation: vrpCaptionFade 4.5s ease-in-out infinite; }
        @keyframes vrpCaptionFade {
          0%, 8% { opacity: 0; transform: translateY(6px); }
          15%, 70% { opacity: 1; transform: translateY(0); }
          85%, 100% { opacity: 0; transform: translateY(-4px); }
        }
        .vrp-bar { animation: vrpBar 0.9s ease-in-out infinite alternate; transform-origin: bottom; }
        @keyframes vrpBar { from { transform: scaleY(0.4); } to { transform: scaleY(1); } }
        .vrp-cta {
          background: linear-gradient(135deg, #f59e0b 0%, #ef4444 50%, #ec4899 100%);
          box-shadow: 0 10px 32px -8px rgba(239, 68, 68, 0.55), inset 0 1px 0 rgba(255,255,255,0.18);
          animation: vrpCtaPulse 2.4s ease-in-out infinite;
        }
        @keyframes vrpCtaPulse {
          0%, 100% { box-shadow: 0 10px 32px -8px rgba(239, 68, 68, 0.55), inset 0 1px 0 rgba(255,255,255,0.18); }
          50% { box-shadow: 0 14px 44px -8px rgba(239, 68, 68, 0.75), inset 0 1px 0 rgba(255,255,255,0.22); }
        }
      `}</style>
    </div>
  );
}
