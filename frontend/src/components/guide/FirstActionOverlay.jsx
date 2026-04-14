import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useProductGuide } from '../../contexts/ProductGuideContext';
import { Play, ArrowRight, Sparkles, X } from 'lucide-react';

export default function FirstActionOverlay() {
  const { progress, loading } = useProductGuide();
  const navigate = useNavigate();
  const [show, setShow] = useState(false);
  const [animateIn, setAnimateIn] = useState(false);

  useEffect(() => {
    if (loading) return;
    if (!progress) return;

    const hasGenerated = (progress.total_generations || 0) > 0;
    const dismissed = progress.guide_dismissed;
    const overlayDismissed = sessionStorage.getItem('first_action_done');
    const permanentlyDismissed = localStorage.getItem('onboarding_dismissed');

    // Skip for admin users
    try {
      const user = JSON.parse(localStorage.getItem('user') || '{}');
      if (user.role === 'ADMIN' || user.role === 'admin') return;
    } catch { /* ignore */ }

    if (!hasGenerated && !dismissed && !overlayDismissed && !permanentlyDismissed) {
      setShow(true);
      requestAnimationFrame(() => {
        requestAnimationFrame(() => setAnimateIn(true));
      });
    }
  }, [progress, loading]);

  if (!show) return null;

  const handleStart = () => {
    setAnimateIn(false);
    sessionStorage.setItem('first_action_done', '1');
    setTimeout(() => {
      setShow(false);
      navigate('/app/story-video-studio', { state: { freshSession: true } });
    }, 300);
  };

  const handleDismiss = () => {
    setAnimateIn(false);
    sessionStorage.setItem('first_action_done', '1');
    localStorage.setItem('onboarding_dismissed', 'true');
    setTimeout(() => {
      setShow(false);
    }, 300);
  };

  return (
    <div
      className={`fixed inset-0 z-[10500] flex items-center justify-center transition-all duration-500 ${animateIn ? 'opacity-100' : 'opacity-0'}`}
      data-testid="first-action-overlay"
    >
      {/* Darkened background — click to dismiss */}
      <div className="absolute inset-0 bg-black/85 backdrop-blur-md" onClick={handleDismiss} />

      {/* Content card */}
      <div
        className={`relative z-10 max-w-md w-full mx-6 transition-all duration-500 ${animateIn ? 'translate-y-0 scale-100' : 'translate-y-8 scale-95'}`}
      >
        {/* Glowing accent */}
        <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 rounded-3xl opacity-20 blur-xl" />

        <div className="relative bg-slate-900/95 border border-slate-700/60 rounded-3xl p-8 shadow-2xl text-center">
          {/* Close button — top right */}
          <button
            onClick={handleDismiss}
            className="absolute top-4 right-4 w-10 h-10 flex items-center justify-center rounded-full bg-white/[0.06] hover:bg-white/[0.12] transition-colors"
            data-testid="first-action-close-btn"
            aria-label="Close"
          >
            <X className="w-5 h-5 text-white/60" />
          </button>

          {/* Icon */}
          <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
            <Sparkles className="w-8 h-8 text-white" />
          </div>

          {/* Title */}
          <h2
            className="text-2xl sm:text-3xl font-bold text-white mb-3 leading-tight"
            data-testid="first-action-title"
          >
            Create your first AI story in 10 seconds
          </h2>

          {/* Subtitle */}
          <p className="text-slate-400 text-base mb-8">
            Start here
          </p>

          {/* Single CTA */}
          <button
            onClick={handleStart}
            className="w-full flex items-center justify-center gap-3 px-8 py-4 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white text-lg font-bold rounded-2xl shadow-xl shadow-indigo-500/30 hover:shadow-indigo-500/50 hover:scale-[1.02] transition-all duration-200"
            data-testid="first-action-start-btn"
          >
            <Play className="w-5 h-5 fill-white" />
            Start Now
            <ArrowRight className="w-5 h-5" />
          </button>

          {/* Skip link */}
          <button
            onClick={handleDismiss}
            className="mt-4 text-sm text-slate-500 hover:text-slate-300 transition-colors"
            data-testid="first-action-skip-btn"
          >
            Skip for now
          </button>

          {/* Progress hint */}
          <div className="mt-5 flex items-center justify-center gap-2">
            <div className="flex gap-1.5">
              <div className="w-8 h-1.5 rounded-full bg-indigo-500" />
              <div className="w-8 h-1.5 rounded-full bg-slate-700" />
              <div className="w-8 h-1.5 rounded-full bg-slate-700" />
              <div className="w-8 h-1.5 rounded-full bg-slate-700" />
              <div className="w-8 h-1.5 rounded-full bg-slate-700" />
            </div>
          </div>
          <p className="text-xs text-slate-600 mt-2">Step 1 of 5</p>
        </div>
      </div>
    </div>
  );
}
