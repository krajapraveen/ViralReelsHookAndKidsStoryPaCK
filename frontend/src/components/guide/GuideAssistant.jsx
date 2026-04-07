import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useProductGuide } from '../../contexts/ProductGuideContext';
import { X, ArrowRight, Lightbulb, HelpCircle, ChevronRight, Sparkles } from 'lucide-react';

export default function GuideAssistant() {
  const {
    progress, showGuide, showStuckHint, stuckMessage,
    contextMessage, activeFeatureGuide, featureStep,
    dismissGuide, setShowGuide, setShowStuckHint,
    nextFeatureStep, dismissFeatureGuide, journeySteps,
  } = useProductGuide();
  const navigate = useNavigate();
  const [isExpanded, setIsExpanded] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const bubbleRef = useRef(null);

  // Show after short delay
  useEffect(() => {
    if (!progress || progress.guide_dismissed) return;
    const t = setTimeout(() => setIsVisible(true), 1500);
    return () => clearTimeout(t);
  }, [progress]);

  if (!progress || progress.guide_dismissed) return null;

  // Feature walkthrough tooltip
  if (activeFeatureGuide) {
    const step = activeFeatureGuide.steps[featureStep];
    return (
      <FeatureTooltip
        guide={activeFeatureGuide}
        step={step}
        stepIdx={featureStep}
        totalSteps={activeFeatureGuide.steps.length}
        onNext={nextFeatureStep}
        onDismiss={dismissFeatureGuide}
      />
    );
  }

  // Stuck hint — small floating prompt
  if (showStuckHint && stuckMessage) {
    return (
      <div
        className="fixed bottom-20 lg:bottom-24 right-4 z-[10000] animate-in slide-in-from-right-5 fade-in duration-300"
        data-testid="stuck-hint"
      >
        <div className="bg-amber-500/95 backdrop-blur-lg rounded-2xl px-4 py-3 shadow-xl max-w-[280px] border border-amber-400/50">
          <div className="flex items-start gap-2">
            <Lightbulb className="w-4 h-4 text-amber-900 mt-0.5 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-amber-950">{stuckMessage}</p>
            </div>
            <button
              onClick={() => setShowStuckHint(false)}
              className="text-amber-800 hover:text-amber-950 p-0.5"
              data-testid="stuck-hint-close"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Main guide bubble
  return (
    <div
      className={`fixed bottom-20 lg:bottom-6 right-4 lg:right-20 z-[10000] transition-all duration-500 ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4 pointer-events-none'}`}
      ref={bubbleRef}
      data-testid="guide-wrapper"
    >
      {/* Expanded panel */}
      {isExpanded && (
        <div
          className="mb-3 bg-slate-900/95 backdrop-blur-xl rounded-2xl border border-slate-700/60 shadow-2xl w-[300px] overflow-hidden animate-in slide-in-from-bottom-3 fade-in duration-200"
          data-testid="guide-panel"
        >
          {/* Header */}
          <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-indigo-400" />
              <span className="text-sm font-semibold text-white">Your Next Step</span>
            </div>
            <button
              onClick={() => setIsExpanded(false)}
              className="text-slate-500 hover:text-white p-1"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Context message */}
          <div className="px-4 py-3">
            <p className="text-sm text-slate-300 leading-relaxed">{contextMessage.message}</p>
            {contextMessage.cta && (
              <button
                onClick={() => { navigate(contextMessage.cta); setIsExpanded(false); }}
                className="mt-3 w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium rounded-xl transition-colors"
                data-testid="guide-cta-btn"
              >
                Do it now <ArrowRight className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Journey progress mini */}
          <div className="px-4 py-2 border-t border-slate-800">
            <p className="text-[10px] text-slate-500 font-medium mb-2 uppercase tracking-wider">Your Journey</p>
            <div className="flex items-center gap-1">
              {journeySteps.map((step, i) => {
                const done = (progress.completed_steps || []).includes(step.id);
                const isCurrent = step.id === progress.current_step;
                return (
                  <div key={step.id} className="flex items-center flex-1">
                    <div
                      className={`w-5 h-5 rounded-full flex items-center justify-center text-[8px] font-bold ${
                        done ? 'bg-emerald-500 text-white' : isCurrent ? 'bg-indigo-500 text-white' : 'bg-slate-700 text-slate-500'
                      }`}
                    >
                      {i + 1}
                    </div>
                    {i < journeySteps.length - 1 && (
                      <div className={`flex-1 h-px mx-0.5 ${done ? 'bg-emerald-500/50' : 'bg-slate-700'}`} />
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Dismiss */}
          <div className="px-4 py-2 border-t border-slate-800">
            <button
              onClick={dismissGuide}
              className="text-xs text-slate-600 hover:text-slate-400 transition-colors"
              data-testid="guide-dismiss-btn"
            >
              Don't show again
            </button>
          </div>
        </div>
      )}

      {/* Bubble button */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-12 h-12 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/40 hover:scale-105 transition-all flex items-center justify-center group"
        data-testid="guide-bubble"
        aria-label="What should I do next?"
      >
        <HelpCircle className="w-5 h-5 text-white group-hover:scale-110 transition-transform" />
        {/* Pulse dot */}
        {!isExpanded && (
          <span className="absolute -top-0.5 -right-0.5 w-3 h-3 bg-amber-400 rounded-full animate-pulse border-2 border-slate-900" />
        )}
      </button>
    </div>
  );
}

// Feature walkthrough tooltip (anchored to target element)
function FeatureTooltip({ guide, step, stepIdx, totalSteps, onNext, onDismiss }) {
  const [pos, setPos] = useState(null);

  useEffect(() => {
    if (!step.target) return;
    const el = document.querySelector(step.target);
    if (el) {
      const rect = el.getBoundingClientRect();
      setPos({
        top: rect.bottom + 12,
        left: Math.min(rect.left, window.innerWidth - 320),
      });
      // Highlight
      el.style.outline = '2px solid #818cf8';
      el.style.outlineOffset = '4px';
      el.style.borderRadius = '8px';
      el.style.position = 'relative';
      el.style.zIndex = '9960';
      return () => {
        el.style.outline = '';
        el.style.outlineOffset = '';
        el.style.zIndex = '';
      };
    }
    // Fallback: center
    setPos({ top: window.innerHeight / 2 - 60, left: window.innerWidth / 2 - 150 });
  }, [step.target, stepIdx]);

  if (!pos) return null;

  return (
    <>
      {/* Dimmed backdrop */}
      <div className="fixed inset-0 bg-black/30 z-[9990]" onClick={onDismiss} />

      {/* Tooltip */}
      <div
        className="fixed z-[10000] w-[300px] bg-slate-900 border border-indigo-500/40 rounded-2xl shadow-2xl p-4 animate-in fade-in slide-in-from-bottom-2 duration-200"
        style={{ top: Math.min(pos.top, window.innerHeight - 200), left: Math.max(8, pos.left) }}
        data-testid="feature-tooltip"
      >
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-indigo-400 font-semibold">{guide.name} — Step {stepIdx + 1}/{totalSteps}</span>
          <button onClick={onDismiss} className="text-slate-500 hover:text-white p-0.5">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
        <p className="text-sm text-white font-medium mb-1">{step.hint}</p>
        <p className="text-xs text-slate-400 mb-3">{step.action}</p>
        <div className="flex items-center justify-between">
          <div className="flex gap-1">
            {Array.from({ length: totalSteps }).map((_, i) => (
              <div key={i} className={`w-1.5 h-1.5 rounded-full ${i <= stepIdx ? 'bg-indigo-400' : 'bg-slate-700'}`} />
            ))}
          </div>
          <button
            onClick={onNext}
            className="flex items-center gap-1 px-3 py-1.5 bg-indigo-500 hover:bg-indigo-600 text-white text-xs font-medium rounded-lg transition-colors"
            data-testid="feature-tooltip-next"
          >
            {stepIdx < totalSteps - 1 ? <>Next <ChevronRight className="w-3 h-3" /></> : 'Got it'}
          </button>
        </div>
      </div>
    </>
  );
}
