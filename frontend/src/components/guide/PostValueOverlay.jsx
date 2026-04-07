import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useProductGuide } from '../../contexts/ProductGuideContext';
import { Sparkles, ArrowRight, Share2, Film } from 'lucide-react';

/**
 * Post-First-Value Overlay — shows after first generation completes.
 * Pushes immediate second action (Continue / Generate Video / Share).
 */
export default function PostValueOverlay() {
  const { progress } = useProductGuide();
  const navigate = useNavigate();
  const [show, setShow] = useState(false);
  const [animateIn, setAnimateIn] = useState(false);

  useEffect(() => {
    if (!progress) return;
    const gens = progress.total_generations || 0;
    const shown = sessionStorage.getItem('post_value_shown');
    // Show exactly once: when user has completed their first generation
    if (gens === 1 && !shown) {
      sessionStorage.setItem('post_value_shown', '1');
      setShow(true);
      requestAnimationFrame(() => {
        requestAnimationFrame(() => setAnimateIn(true));
      });
    }
  }, [progress]);

  if (!show) return null;

  const close = (action) => {
    setAnimateIn(false);
    setTimeout(() => {
      setShow(false);
      if (action === 'continue') navigate('/app/story-video-studio', { state: { freshSession: true } });
      else if (action === 'video') navigate('/app/story-video-studio');
      else if (action === 'share') {/* stay on page, trigger share */}
    }, 250);
  };

  return (
    <div
      className={`fixed inset-0 z-[10400] flex items-center justify-center transition-all duration-400 ${animateIn ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
      data-testid="post-value-overlay"
    >
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={() => close('continue')} />

      <div className={`relative z-10 max-w-sm w-full mx-6 transition-all duration-400 ${animateIn ? 'translate-y-0 scale-100' : 'translate-y-6 scale-95'}`}>
        <div className="absolute -inset-1 bg-gradient-to-r from-emerald-500 via-indigo-500 to-purple-500 rounded-3xl opacity-25 blur-xl" />

        <div className="relative bg-slate-900/95 border border-slate-700/60 rounded-3xl p-6 shadow-2xl text-center">
          {/* Success icon */}
          <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-500/30">
            <Sparkles className="w-7 h-7 text-white" />
          </div>

          <h2 className="text-xl font-bold text-white mb-1" data-testid="post-value-title">
            Your story is ready!
          </h2>
          <p className="text-sm text-slate-400 mb-6">
            Keep the momentum going — what's next?
          </p>

          {/* 3 action buttons */}
          <div className="space-y-2">
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
          </div>
        </div>
      </div>
    </div>
  );
}
