import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useProductGuide } from '../../contexts/ProductGuideContext';
import { useCredits } from '../../contexts/CreditContext';
import { trackFunnel, incrementGenerationCount } from '../../utils/funnelTracker';
import { Sparkles, ArrowRight, Share2, Film, X } from 'lucide-react';

/**
 * Post-First-Value Overlay — shows after generation completes.
 * - After 1st gen: soft prompt (Continue / Share / Video)
 * - After 2nd gen: triggers inline paywall via onTriggerPaywall callback
 */
export default function PostValueOverlay({ onTriggerPaywall }) {
  const { progress } = useProductGuide();
  const navigate = useNavigate();
  const [show, setShow] = useState(false);
  const [animateIn, setAnimateIn] = useState(false);
  const [genCount, setGenCount] = useState(0);

  useEffect(() => {
    if (!progress) return;
    const gens = progress.total_generations || 0;
    const lastShown = parseInt(sessionStorage.getItem('post_value_shown_at') || '0', 10);

    // Don't show during active pipeline generation
    const onPipeline = window.location.pathname.includes('story-video-studio');
    const hasActiveProject = new URLSearchParams(window.location.search).get('projectId');
    if (onPipeline && hasActiveProject) return;

    // Show when a NEW generation is completed (not already shown for this count)
    if (gens > 0 && gens !== lastShown) {
      sessionStorage.setItem('post_value_shown_at', String(gens));
      setGenCount(gens);

      // Track the event
      trackFunnel(gens === 1 ? 'result_viewed' : 'second_action', {
        source_page: 'studio',
        generation_count: gens,
      });

      setShow(true);
      requestAnimationFrame(() => {
        requestAnimationFrame(() => setAnimateIn(true));
      });
    }
  }, [progress]);

  const close = useCallback((action) => {
    setAnimateIn(false);
    setTimeout(() => {
      setShow(false);
      if (action === 'continue') {
        trackFunnel('second_action', { meta: { action: 'continue' } });
        navigate('/app');
      } else if (action === 'video') {
        trackFunnel('second_action', { meta: { action: 'video' } });
        navigate('/app/story-video-studio');
      } else if (action === 'share') {
        trackFunnel('second_action', { meta: { action: 'share' } });
      } else if (action === 'upgrade') {
        if (onTriggerPaywall) onTriggerPaywall('post_value');
      }
    }, 200);
  }, [navigate, onTriggerPaywall]);

  if (!show) return null;

  const isSecondGen = genCount >= 2;

  return (
    <div
      className={`fixed inset-0 z-[10400] flex items-center justify-center transition-all duration-300 ${animateIn ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
      data-testid="post-value-overlay"
    >
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={() => close('dismiss')} />

      <div className={`relative z-10 max-w-sm w-full mx-6 transition-all duration-300 ${animateIn ? 'translate-y-0 scale-100' : 'translate-y-6 scale-95'}`}>
        <div className="absolute -inset-1 bg-gradient-to-r from-emerald-500 via-indigo-500 to-purple-500 rounded-3xl opacity-20 blur-xl" />

        <div className="relative bg-slate-900/95 border border-slate-700/60 rounded-3xl p-6 shadow-2xl text-center">
          <button
            onClick={() => close('dismiss')}
            className="absolute top-3 right-3 text-slate-500 hover:text-white transition-colors"
            data-testid="post-value-close"
          >
            <X className="w-4 h-4" />
          </button>

          <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-500/30">
            <Sparkles className="w-7 h-7 text-white" />
          </div>

          <h2 className="text-xl font-bold text-white mb-1" data-testid="post-value-title">
            {isSecondGen ? 'You\'re on fire!' : 'Your story is ready!'}
          </h2>
          <p className="text-sm text-slate-400 mb-6">
            {isSecondGen
              ? 'Unlock unlimited creations to keep the momentum'
              : 'Keep the momentum going \u2014 what\'s next?'}
          </p>

          <div className="space-y-2">
            {isSecondGen ? (
              <>
                <button
                  onClick={() => close('upgrade')}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white text-sm font-bold rounded-xl transition-all hover:scale-[1.01] shadow-lg shadow-indigo-500/20"
                  data-testid="post-value-upgrade"
                >
                  <Sparkles className="w-4 h-4" />
                  Unlock Unlimited
                </button>
                <button
                  onClick={() => close('continue')}
                  className="w-full text-xs text-slate-500 hover:text-slate-300 py-2 transition-colors"
                  data-testid="post-value-continue-free"
                >
                  Continue with limited access
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => close('continue')}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-bold rounded-xl transition-all hover:scale-[1.01] shadow-lg shadow-indigo-500/20"
                  data-testid="post-value-continue"
                >
                  <ArrowRight className="w-4 h-4" />
                  Continue Story
                </button>
                <button
                  onClick={() => close('video')}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-slate-800 hover:bg-slate-700 text-white text-sm font-medium rounded-xl transition-all border border-slate-700"
                  data-testid="post-value-video"
                >
                  <Film className="w-4 h-4" />
                  Generate Video
                </button>
                <button
                  onClick={() => close('share')}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-slate-800 hover:bg-slate-700 text-white text-sm font-medium rounded-xl transition-all border border-slate-700"
                  data-testid="post-value-share"
                >
                  <Share2 className="w-4 h-4" />
                  Share Now
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
