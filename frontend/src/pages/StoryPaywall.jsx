import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, Sparkles, BookOpen, Film, Share2, Zap, Clock, Shield } from 'lucide-react';
import { trackFunnel } from '../utils/funnelTracker';

function extractCliffhanger(text) {
  if (!text) return '';
  const paragraphs = text.split('\n').filter(p => p.trim());
  const last = paragraphs[paragraphs.length - 1]?.trim() || '';
  if (last.length > 120) {
    const sentences = last.match(/[^.!?…]+[.!?…]+/g) || [last];
    return sentences[sentences.length - 1]?.trim() || last.slice(-100);
  }
  return last;
}

export default function StoryPaywall({
  open,
  onClose,
  storyTitle,
  storyText,
  source,
  storyId,
  partNumber,
  viewCount = 1,
}) {
  const navigate = useNavigate();
  const [selectedPlan, setSelectedPlan] = useState('monthly');
  const [showExitOffer, setShowExitOffer] = useState(false);
  const [showNudge, setShowNudge] = useState(false);
  const [discountSeconds, setDiscountSeconds] = useState(120);
  const nudgeTimerRef = useRef(null);
  const discountTimerRef = useRef(null);
  const cliffhanger = extractCliffhanger(storyText);
  const showDiscount = viewCount >= 2;

  // Hesitation nudge after 5s
  useEffect(() => {
    if (!open) return;
    nudgeTimerRef.current = setTimeout(() => setShowNudge(true), 5000);
    return () => clearTimeout(nudgeTimerRef.current);
  }, [open]);

  // Discount countdown timer
  useEffect(() => {
    if (!open || !showDiscount) return;
    try { trackFunnel('discount_offer_shown', { meta: { part_number: partNumber, story_id: storyId, view_count: viewCount } }); } catch {}
    discountTimerRef.current = setInterval(() => {
      setDiscountSeconds(prev => {
        if (prev <= 1) {
          clearInterval(discountTimerRef.current);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(discountTimerRef.current);
  }, [open, showDiscount, partNumber, storyId, viewCount]);

  const handleClose = useCallback(() => {
    if (!showExitOffer) {
      setShowExitOffer(true);
      try { trackFunnel('exit_offer_shown', { meta: { part_number: partNumber, story_id: storyId } }); } catch {}
      return;
    }
    try { trackFunnel('paywall_dismissed', { meta: { part_number: partNumber, story_id: storyId } }); } catch {}
    onClose();
  }, [showExitOffer, onClose, partNumber, storyId]);

  const handleConvert = useCallback((plan) => {
    try { trackFunnel('paywall_converted', { meta: { part_number: partNumber, story_id: storyId, plan_selected: plan, entry_source: source } }); } catch {}

    // Store story state for after login/payment
    sessionStorage.setItem('post_login_redirect', '/app/story-video-studio');
    sessionStorage.setItem('post_login_story', JSON.stringify({ story_text: storyText, title: storyTitle }));

    const token = localStorage.getItem('token');
    if (token) {
      navigate('/app/pricing');
    } else {
      navigate('/login?from=experience');
    }
  }, [navigate, storyTitle, storyText, source, partNumber, storyId]);

  if (!open) return null;

  const discountMin = Math.floor(discountSeconds / 60);
  const discountSec = discountSeconds % 60;

  return (
    <div className="fixed inset-0 z-[9999] flex items-end sm:items-center justify-center" data-testid="story-paywall-overlay">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70 backdrop-blur-md" onClick={handleClose} />

      {/* Modal */}
      <div className="relative w-full max-w-md mx-auto sm:mx-4 bg-[#0d0d18] border border-white/10 sm:rounded-2xl rounded-t-2xl overflow-hidden max-h-[90vh] overflow-y-auto pw-slide-up" data-testid="story-paywall-modal">
        {/* Close button */}
        <button onClick={handleClose} className="absolute top-3 right-3 z-10 p-1.5 rounded-full bg-white/5 hover:bg-white/10 transition-colors" data-testid="paywall-close-btn">
          <X className="w-4 h-4 text-slate-400" />
        </button>

        {/* Cliffhanger hook */}
        <div className="px-6 pt-6 pb-4">
          <div className="text-amber-400 text-xs font-medium tracking-wider uppercase mb-2 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5" />
            Wait... it gets even better
          </div>
          <p className="text-slate-300 text-sm italic leading-relaxed line-clamp-3" data-testid="paywall-cliffhanger">
            "{cliffhanger}"
          </p>
        </div>

        {/* Divider */}
        <div className="h-px bg-gradient-to-r from-transparent via-indigo-500/30 to-transparent" />

        {/* Headline */}
        <div className="px-6 pt-5 pb-3 text-center">
          <h2 className="text-xl sm:text-2xl font-bold text-white mb-2" data-testid="paywall-headline">Unlock the next chapter</h2>
          <div className="flex flex-col gap-1.5 text-sm text-slate-400">
            <span className="flex items-center justify-center gap-2"><BookOpen className="w-4 h-4 text-indigo-400" /> Continue your story instantly</span>
            <span className="flex items-center justify-center gap-2"><Film className="w-4 h-4 text-indigo-400" /> Turn it into a video</span>
            <span className="flex items-center justify-center gap-2"><Share2 className="w-4 h-4 text-indigo-400" /> Share with friends</span>
          </div>
        </div>

        {/* Social proof */}
        <div className="px-6 py-2">
          <div className="flex items-center justify-center gap-3 text-xs text-slate-500">
            <span className="flex items-center gap-1"><Zap className="w-3 h-3 text-amber-400" /> 12,847 stories created today</span>
            <span className="w-1 h-1 rounded-full bg-slate-700" />
            <span className="flex items-center gap-1"><Shield className="w-3 h-3 text-emerald-400" /> Loved by creators</span>
          </div>
        </div>

        {/* Discount timer */}
        {showDiscount && discountSeconds > 0 && (
          <div className="mx-6 mt-2 mb-1 py-2 px-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-center" data-testid="discount-timer">
            <span className="text-amber-300 text-xs font-medium">Limited Offer ({discountMin}:{discountSec.toString().padStart(2, '0')}) &mdash; 20% OFF</span>
          </div>
        )}

        {/* Pricing */}
        <div className="px-6 pt-3 pb-2 space-y-2.5">
          {/* Primary: Monthly */}
          <button
            onClick={() => setSelectedPlan('monthly')}
            className={`w-full p-4 rounded-xl border transition-all text-left relative ${
              selectedPlan === 'monthly'
                ? 'border-indigo-500 bg-indigo-500/10 pw-glow'
                : 'border-white/10 bg-white/[0.02] hover:bg-white/5'
            }`}
            data-testid="plan-monthly"
          >
            <div className="absolute -top-2.5 left-4 px-2 py-0.5 rounded-full bg-indigo-500 text-[10px] font-bold text-white uppercase tracking-wider">Most Popular</div>
            <div className="flex items-center justify-between mt-1">
              <div>
                <div className="text-white font-semibold text-base">
                  {showDiscount && discountSeconds > 0 ? (
                    <><span className="line-through text-slate-500 text-sm mr-1.5">&#8377;99</span>&#8377;79</>
                  ) : (
                    <>&#8377;99</>
                  )}
                  <span className="text-slate-400 text-xs font-normal"> / month</span>
                </div>
                <div className="text-slate-500 text-xs mt-0.5">Unlimited stories + 10 videos</div>
              </div>
              <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${selectedPlan === 'monthly' ? 'border-indigo-500 bg-indigo-500' : 'border-slate-600'}`}>
                {selectedPlan === 'monthly' && <div className="w-2 h-2 rounded-full bg-white" />}
              </div>
            </div>
          </button>

          {/* Secondary: One-time */}
          <button
            onClick={() => setSelectedPlan('one_time')}
            className={`w-full p-3 rounded-xl border transition-all text-left ${
              selectedPlan === 'one_time'
                ? 'border-indigo-500/50 bg-indigo-500/5'
                : 'border-white/5 bg-transparent hover:bg-white/[0.02]'
            }`}
            data-testid="plan-one-time"
          >
            <div className="flex items-center justify-between">
              <div>
                <span className="text-white/80 text-sm font-medium">&#8377;29</span>
                <span className="text-slate-500 text-xs ml-1.5">Just want this story?</span>
              </div>
              <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${selectedPlan === 'one_time' ? 'border-indigo-500 bg-indigo-500' : 'border-slate-700'}`}>
                {selectedPlan === 'one_time' && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
              </div>
            </div>
          </button>

          {/* Tertiary: Pro */}
          <button
            onClick={() => setSelectedPlan('pro')}
            className={`w-full p-3 rounded-xl border transition-all text-left ${
              selectedPlan === 'pro'
                ? 'border-indigo-500/50 bg-indigo-500/5'
                : 'border-white/5 bg-transparent hover:bg-white/[0.02]'
            }`}
            data-testid="plan-pro"
          >
            <div className="flex items-center justify-between">
              <div>
                <span className="text-white/80 text-sm font-medium">&#8377;199</span>
                <span className="text-slate-500 text-xs ml-1.5">Need video too? Unlimited everything.</span>
              </div>
              <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${selectedPlan === 'pro' ? 'border-indigo-500 bg-indigo-500' : 'border-slate-700'}`}>
                {selectedPlan === 'pro' && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
              </div>
            </div>
          </button>
        </div>

        {/* CTA */}
        <div className="px-6 pt-3 pb-2">
          <button
            onClick={() => handleConvert(selectedPlan)}
            className="w-full py-4 px-6 rounded-xl font-semibold text-white text-base flex items-center justify-center gap-2.5 transition-all hover:scale-[1.02] active:scale-[0.98] pw-cta-btn"
            data-testid="paywall-cta-continue"
          >
            <Zap className="w-5 h-5" />
            Continue My Story
          </button>
          <p className="text-center text-slate-600 text-[11px] mt-2 mb-1">Instant access &middot; Cancel anytime</p>
        </div>

        {/* Hesitation nudge */}
        {showNudge && (
          <div className="px-6 pb-4 text-center pw-nudge-appear" data-testid="paywall-nudge">
            <p className="text-amber-400/70 text-xs flex items-center justify-center gap-1.5">
              <Clock className="w-3 h-3" /> Your story is waiting...
            </p>
          </div>
        )}

        {/* Bottom safe area */}
        <div className="h-2 sm:h-0" />
      </div>

      {/* Exit Offer Overlay */}
      {showExitOffer && (
        <div className="absolute inset-0 z-10 flex items-center justify-center pw-exit-appear" data-testid="exit-offer-overlay">
          <div className="absolute inset-0 bg-black/50" />
          <div className="relative bg-[#12121f] border border-white/10 rounded-2xl p-6 max-w-sm mx-4 text-center">
            <p className="text-lg font-semibold text-white mb-1">Don't lose your story</p>
            <p className="text-slate-400 text-sm mb-5">Continue now for just &#8377;29</p>
            <button
              onClick={() => handleConvert('one_time')}
              className="w-full py-3.5 px-6 rounded-xl font-semibold text-white text-sm flex items-center justify-center gap-2 pw-cta-btn mb-3"
              data-testid="exit-offer-cta"
            >
              <Zap className="w-4 h-4" />
              Continue for &#8377;29
            </button>
            <button
              onClick={() => { setShowExitOffer(false); onClose(); try { trackFunnel('paywall_dismissed', { meta: { part_number: partNumber, story_id: storyId, exit_offer: true } }); } catch {} }}
              className="text-slate-600 text-xs hover:text-slate-400 transition-colors"
              data-testid="exit-offer-dismiss"
            >
              No thanks, I'll pass
            </button>
          </div>
        </div>
      )}

      <style>{`
        .pw-slide-up {
          animation: pwSlideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
        @keyframes pwSlideUp {
          from { transform: translateY(30px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
        .pw-glow {
          box-shadow: 0 0 20px rgba(99, 102, 241, 0.15), inset 0 0 20px rgba(99, 102, 241, 0.05);
        }
        .pw-cta-btn {
          background: linear-gradient(135deg, #6366f1, #8b5cf6);
          box-shadow: 0 4px 24px rgba(99, 102, 241, 0.35);
          animation: pwCtaPulse 2.5s ease-in-out infinite;
        }
        @keyframes pwCtaPulse {
          0%, 100% { box-shadow: 0 4px 24px rgba(99, 102, 241, 0.35); }
          50% { box-shadow: 0 6px 36px rgba(99, 102, 241, 0.55); }
        }
        .pw-nudge-appear {
          animation: pwNudge 0.5s ease-out forwards;
        }
        @keyframes pwNudge {
          from { opacity: 0; transform: translateY(5px); }
          to { opacity: 1; transform: none; }
        }
        .pw-exit-appear {
          animation: pwExitIn 0.3s ease-out forwards;
        }
        @keyframes pwExitIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
      `}</style>
    </div>
  );
}
