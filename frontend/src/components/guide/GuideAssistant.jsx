import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useProductGuide } from '../../contexts/ProductGuideContext';
import { X, ArrowRight, Lightbulb, HelpCircle, ChevronRight, Sparkles, MousePointerClick } from 'lucide-react';

// Auto-scroll + highlight a target element
function scrollAndHighlight(selector) {
  const el = document.querySelector(selector);
  if (!el) return null;
  el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  el.style.outline = '2px solid #818cf8';
  el.style.outlineOffset = '4px';
  el.style.borderRadius = '8px';
  el.style.position = 'relative';
  el.style.zIndex = '9960';
  el.style.transition = 'outline 0.3s, box-shadow 0.3s';
  el.style.boxShadow = '0 0 20px rgba(129,140,248,0.4)';
  // Pulse animation
  setTimeout(() => {
    el.style.outline = '3px solid #6366f1';
    setTimeout(() => { el.style.outline = '2px solid #818cf8'; }, 300);
  }, 500);
  return el;
}

// Clean up highlight from an element
function clearHighlight(el) {
  if (!el) return;
  el.style.outline = '';
  el.style.outlineOffset = '';
  el.style.zIndex = '';
  el.style.boxShadow = '';
}

export default function GuideAssistant() {
  const {
    progress, showStuckHint, stuckMessage,
    contextMessage, activeFeatureGuide, featureStep,
    dismissGuide, setShowStuckHint,
    nextFeatureStep, dismissFeatureGuide, journeySteps,
  } = useProductGuide();
  const navigate = useNavigate();
  const location = useLocation();
  const [isExpanded, setIsExpanded] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const [highlightedEl, setHighlightedEl] = useState(null);
  const bubbleRef = useRef(null);

  // Show after short delay
  useEffect(() => {
    if (!progress || progress.guide_dismissed) return;
    const t = setTimeout(() => setIsVisible(true), 1500);
    return () => clearTimeout(t);
  }, [progress]);

  // Cleanup highlight on unmount or navigation
  useEffect(() => {
    return () => { if (highlightedEl) clearHighlight(highlightedEl); };
  }, [highlightedEl, location.pathname]);

  if (!progress || progress.guide_dismissed) return null;

  // Handle CTA action — scroll to target or navigate
  const handleAction = (cta, targetSelector) => {
    setIsExpanded(false);
    if (highlightedEl) clearHighlight(highlightedEl);

    if (cta && !document.querySelector(targetSelector || '')) {
      // Target not on this page — navigate first
      navigate(cta);
      return;
    }

    if (targetSelector) {
      const el = scrollAndHighlight(targetSelector);
      setHighlightedEl(el);
      // Auto-clear after 5s
      if (el) setTimeout(() => { clearHighlight(el); setHighlightedEl(null); }, 5000);
    }
  };

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
        onAction={() => {
          if (step.target) {
            const el = scrollAndHighlight(step.target);
            if (el) setTimeout(() => clearHighlight(el), 5000);
          }
          nextFeatureStep();
        }}
      />
    );
  }

  // Stuck hint — action-driven floating prompt
  // GUARD: Never show during active generation/processing
  const generationActive = typeof document !== 'undefined' && document.querySelector('[data-testid="generation-progress"], [data-testid="waiting-experience"], [data-testid="real-time-progress"]');
  if (showStuckHint && stuckMessage && !generationActive) {
    const stuckTarget = getStuckTarget(location.pathname);
    // Double-check: if target selector doesn't exist in DOM, don't show the hint
    if (stuckTarget?.selector && !document.querySelector(stuckTarget.selector)) {
      // Target doesn't exist — silently suppress
    } else {
    return (
      <div
        className="fixed bottom-20 lg:bottom-24 right-4 z-[10000] animate-in slide-in-from-right-5 fade-in duration-300"
        data-testid="stuck-hint"
      >
        <div className="bg-amber-500/95 backdrop-blur-lg rounded-2xl px-4 py-3 shadow-xl max-w-[300px] border border-amber-400/50">
          <div className="flex items-start gap-2">
            <Lightbulb className="w-4 h-4 text-amber-900 mt-0.5 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-amber-950">{stuckMessage}</p>
              {stuckTarget && (
                <button
                  onClick={() => {
                    setShowStuckHint(false);
                    if (stuckTarget.navigate) {
                      navigate(stuckTarget.navigate);
                    } else if (stuckTarget.selector) {
                      const el = scrollAndHighlight(stuckTarget.selector);
                      if (el) setTimeout(() => clearHighlight(el), 5000);
                    }
                  }}
                  className="mt-2 flex items-center gap-1.5 px-3 py-1.5 bg-amber-900/30 hover:bg-amber-900/50 text-amber-950 text-xs font-bold rounded-lg transition-colors"
                  data-testid="stuck-hint-action"
                >
                  <MousePointerClick className="w-3 h-3" />
                  {stuckTarget.label}
                </button>
              )}
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
  }

  // Determine the action target for the current context
  const actionTarget = getActionTarget(contextMessage, location.pathname);

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
          className="mb-3 bg-slate-900/95 backdrop-blur-xl rounded-2xl border border-slate-700/60 shadow-2xl w-[320px] overflow-hidden animate-in slide-in-from-bottom-3 fade-in duration-200"
          data-testid="guide-panel"
        >
          {/* Header */}
          <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-indigo-400" />
              <span className="text-sm font-semibold text-white">Your Next Step</span>
            </div>
            <button onClick={() => setIsExpanded(false)} className="text-slate-500 hover:text-white p-1">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Context message + ACTION CTA */}
          <div className="px-4 py-3">
            <p className="text-sm text-slate-300 leading-relaxed mb-3">{contextMessage.message}</p>
            <button
              onClick={() => handleAction(actionTarget.navigate, actionTarget.selector)}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-bold rounded-xl transition-all hover:scale-[1.01] shadow-lg shadow-indigo-500/20"
              data-testid="guide-cta-btn"
            >
              <MousePointerClick className="w-4 h-4" />
              {actionTarget.label}
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          {/* Journey progress mini */}
          <div className="px-4 py-2 border-t border-slate-800">
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] text-slate-500 font-medium uppercase tracking-wider">Your Journey</p>
              <p className="text-[10px] text-indigo-400 font-bold">{getCompletionPercent(progress, journeySteps)}% complete</p>
            </div>
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
        {!isExpanded && (
          <span className="absolute -top-0.5 -right-0.5 w-3 h-3 bg-amber-400 rounded-full animate-pulse border-2 border-slate-900" />
        )}
      </button>
    </div>
  );
}

// Get completion percentage
function getCompletionPercent(progress, steps) {
  if (!progress || !steps.length) return 0;
  const completed = (progress.completed_steps || []).length;
  return Math.round((completed / steps.length) * 100);
}

// Get the CTA target based on current context
function getActionTarget(contextMessage, pathname) {
  const { action } = contextMessage;

  // Already on studio — guide to the input
  if (pathname === '/app/story-video-studio') {
    if (action === 'generate') {
      return { label: 'Generate Now', selector: '[data-guide="generate-btn"]', navigate: null };
    }
    if (action === 'share') {
      return { label: 'Share Creation', selector: '[data-guide="share-btn"]', navigate: null };
    }
    return { label: 'Enter Your Story', selector: '[data-guide="story-input"]', navigate: null };
  }

  // On reel generator
  if (pathname === '/app/reel-generator') {
    if (action === 'generate') {
      return { label: 'Generate Reel', selector: '[data-guide="generate-btn"]', navigate: null };
    }
    return { label: 'Enter Your Topic', selector: '[data-guide="reel-input"]', navigate: null };
  }

  // On story generator
  if (pathname === '/app/story-generator' || pathname === '/app/stories') {
    if (action === 'generate') {
      return { label: 'Generate Story', selector: '[data-guide="generate-btn"]', navigate: null };
    }
    return { label: 'Start Your Story', selector: '[data-guide="story-input"]', navigate: null };
  }

  // Dashboard or other pages — navigate to studio
  return { label: 'Go to Studio', navigate: '/app/story-video-studio', selector: null };
}

// Get stuck hint action target
function getStuckTarget(pathname) {
  const targets = {
    '/app': { label: 'Go to Studio', navigate: '/app/story-video-studio' },
    '/app/story-video-studio': { label: 'Scroll to input', selector: '[data-guide="story-input"]' },
    '/app/reel-generator': { label: 'Scroll to input', selector: '[data-guide="reel-input"]' },
    '/app/story-generator': { label: 'Scroll to form', selector: '[data-guide="story-input"]' },
  };
  return targets[pathname] || null;
}

// Feature walkthrough tooltip — action-driven
function FeatureTooltip({ guide, step, stepIdx, totalSteps, onNext, onDismiss, onAction }) {
  const [pos, setPos] = useState(null);
  const highlightRef = useRef(null);

  useEffect(() => {
    if (!step.target) {
      setPos({ top: window.innerHeight / 2 - 60, left: window.innerWidth / 2 - 150 });
      return;
    }
    const el = document.querySelector(step.target);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      const rect = el.getBoundingClientRect();
      setPos({
        top: rect.bottom + 12,
        left: Math.min(rect.left, window.innerWidth - 320),
      });
      el.style.outline = '2px solid #818cf8';
      el.style.outlineOffset = '4px';
      el.style.borderRadius = '8px';
      el.style.position = 'relative';
      el.style.zIndex = '9960';
      el.style.boxShadow = '0 0 20px rgba(129,140,248,0.4)';
      highlightRef.current = el;
      return () => {
        el.style.outline = '';
        el.style.outlineOffset = '';
        el.style.zIndex = '';
        el.style.boxShadow = '';
      };
    }
    setPos({ top: window.innerHeight / 2 - 60, left: window.innerWidth / 2 - 150 });
  }, [step.target, stepIdx]);

  if (!pos) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/30 z-[9990]" onClick={onDismiss} />
      <div
        className="fixed z-[10000] bg-slate-900 border border-indigo-500/40 rounded-2xl shadow-2xl p-4 animate-in fade-in slide-in-from-bottom-2 duration-200"
        style={{
          top: Math.min(pos.top, window.innerHeight - 220),
          left: Math.max(12, Math.min(pos.left, window.innerWidth - 312)),
          width: Math.min(300, window.innerWidth - 24),
          maxWidth: 'calc(100vw - 24px)',
        }}
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
            onClick={onAction || onNext}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-500 hover:bg-indigo-600 text-white text-xs font-bold rounded-lg transition-colors"
            data-testid="feature-tooltip-next"
          >
            {stepIdx < totalSteps - 1 ? (
              <><MousePointerClick className="w-3 h-3" /> Do it</>
            ) : (
              'Got it'
            )}
          </button>
        </div>
      </div>
    </>
  );
}
