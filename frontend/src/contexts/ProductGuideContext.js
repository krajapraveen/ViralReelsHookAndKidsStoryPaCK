import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import api from '../utils/api';
import { toast } from 'sonner';

const GuideContext = createContext(null);

// Primary user journey steps
const JOURNEY_STEPS = [
  { id: 'create', label: 'Create', description: 'Start or continue a story' },
  { id: 'customize', label: 'Customize', description: 'Set style, tone, characters' },
  { id: 'generate', label: 'Generate', description: 'Generate your video' },
  { id: 'result', label: 'Result', description: 'View your creation' },
  { id: 'share', label: 'Share', description: 'Share or download' },
];

// Feature-specific guides
const FEATURE_GUIDES = {
  'story-video': {
    name: 'Story Video Studio',
    steps: [
      { hint: 'Enter your story idea or continue from a shared story', target: '[data-guide="story-input"]', action: 'Type or paste your story idea' },
      { hint: 'Choose your style and customize settings', target: '[data-guide="style-select"]', action: 'Pick a visual style' },
      { hint: 'Click Generate to create your video', target: '[data-guide="generate-btn"]', action: 'Click Generate' },
      { hint: 'Watch your generated story video', target: '[data-guide="preview-area"]', action: 'View the result' },
      { hint: 'Share your creation or download it', target: '[data-guide="share-btn"]', action: 'Share or Download' },
    ],
  },
  'reel-generator': {
    name: 'Reel Generator',
    steps: [
      { hint: 'Describe your reel topic or paste a script', target: '[data-guide="reel-input"]', action: 'Enter your topic' },
      { hint: 'Choose tone and platform', target: '[data-guide="reel-options"]', action: 'Set preferences' },
      { hint: 'Generate your reel script', target: '[data-guide="generate-btn"]', action: 'Click Generate' },
      { hint: 'Copy or share your reel script', target: '[data-guide="reel-output"]', action: 'Use your script' },
    ],
  },
  'story-generator': {
    name: 'Kids Story Generator',
    steps: [
      { hint: 'Enter a story theme or character', target: '[data-guide="story-input"]', action: 'Describe your story' },
      { hint: 'Generate your story pack', target: '[data-guide="generate-btn"]', action: 'Click Generate' },
      { hint: 'View and download your story scenes', target: '[data-guide="result-area"]', action: 'Browse results' },
    ],
  },
};

// Context-aware messages based on user state
function getContextMessage(progress) {
  if (!progress) return { message: 'Start your first story to begin', action: 'create' };

  const { completed_steps = [], total_generations = 0, total_shares = 0, current_step } = progress;

  if (!completed_steps.includes('create') && total_generations === 0) {
    return { message: 'Start your first story — click Continue Story or Create New', action: 'create', cta: '/app/story-video-studio' };
  }
  if (completed_steps.includes('create') && !completed_steps.includes('generate') && total_generations === 0) {
    return { message: 'Now generate your story to see the magic', action: 'generate' };
  }
  if (total_generations > 0 && total_shares === 0) {
    return { message: 'Share your creation to grow your audience', action: 'share' };
  }
  if (total_generations > 0 && total_shares > 0 && !completed_steps.includes('share')) {
    return { message: 'Great work! Try remixing or continuing another story', action: 'create', cta: '/app/story-video-studio' };
  }
  if (current_step === 'create') {
    return { message: 'Pick a story to continue, or start fresh', action: 'create' };
  }
  if (current_step === 'generate') {
    return { message: 'Your story is generating — sit tight!', action: 'wait' };
  }
  if (current_step === 'result') {
    return { message: 'Your video is ready — share it to go viral!', action: 'share' };
  }
  return { message: 'Explore your dashboard and create something new', action: 'explore' };
}

// Stuck detection messages — action-oriented
const STUCK_HINTS = {
  '/app': 'Start by clicking Continue Story below',
  '/app/story-video-studio': 'Enter your story idea above, then click Generate',
  '/app/reel-generator': 'Type your reel topic and click Generate',
  '/app/stories': 'Pick a story theme to get started',
  '/app/story-generator': 'Enter a story idea and generate',
  '/app/creator-tools': 'Pick a tool to boost your content',
};

export function ProductGuideProvider({ children }) {
  const [progress, setProgress] = useState(null);
  const [showGuide, setShowGuide] = useState(false);
  const [showStuckHint, setShowStuckHint] = useState(false);
  const [stuckMessage, setStuckMessage] = useState('');
  const [activeFeatureGuide, setActiveFeatureGuide] = useState(null);
  const [featureStep, setFeatureStep] = useState(0);
  const [loading, setLoading] = useState(true);
  const location = useLocation();
  const idleTimerRef = useRef(null);
  const lastInteractionRef = useRef(Date.now());

  // Fetch progress on mount AND re-fetch when pathname changes (catches post-login navigation)
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) { setLoading(false); return; }
    if (!progress) fetchProgress();
  }, [location.pathname]);

  // Reset stuck hint on navigation
  useEffect(() => {
    setShowStuckHint(false);
    resetIdleTimer();
  }, [location.pathname]);

  // Idle detection — show stuck hint after 15s inactivity
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token || (progress && progress.guide_dismissed)) return;

    const handleInteraction = () => {
      lastInteractionRef.current = Date.now();
      setShowStuckHint(false);
      resetIdleTimer();
    };

    window.addEventListener('click', handleInteraction, { passive: true });
    window.addEventListener('keydown', handleInteraction, { passive: true });
    window.addEventListener('scroll', handleInteraction, { passive: true });

    resetIdleTimer();

    return () => {
      window.removeEventListener('click', handleInteraction);
      window.removeEventListener('keydown', handleInteraction);
      window.removeEventListener('scroll', handleInteraction);
      if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
    };
  }, [progress, location.pathname]);

  const resetIdleTimer = useCallback(() => {
    if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
    idleTimerRef.current = setTimeout(() => {
      if (progress && progress.guide_dismissed) return;
      // Don't show stuck hint during active generation/processing
      const generationActive = document.querySelector('[data-testid="generation-progress"], [data-testid="waiting-experience"], [data-testid="real-time-progress"]');
      if (generationActive) return;
      // Don't show if the target input doesn't exist in DOM
      const hint = STUCK_HINTS[location.pathname];
      if (hint) {
        const targetInput = document.querySelector('[data-guide="story-input"], [data-guide="reel-input"]');
        if (location.pathname.includes('story-video-studio') && !targetInput) return;
        setStuckMessage(hint);
        setShowStuckHint(true);
      }
    }, 15000);
  }, [location.pathname, progress]);

  const fetchProgress = async () => {
    try {
      const { data } = await api.get('/api/user/progress');
      if (data.success) {
        setProgress(data.data);
        if (!data.data.guide_dismissed && (data.data.completed_steps || []).length === 0) {
          setShowGuide(true);
        }
      }
    } catch { /* ignore */ }
    setLoading(false);
  };

  // Step success messages
  const STEP_SUCCESS = {
    create: 'Story started! Now customize it.',
    customize: 'Looking great! Hit Generate.',
    generate: 'Your story is ready!',
    result: 'Your video is live!',
    share: 'Shared! You are growing.',
  };

  const updateStep = useCallback(async (step, action, feature, meta) => {
    try {
      const prevCompleted = progress?.completed_steps || [];
      const { data } = await api.post('/api/user/progress/update', {
        step, action, feature, meta,
      });
      if (data.success) {
        setProgress(data.data);
        // Show success toast for newly completed steps
        const newCompleted = data.data.completed_steps || [];
        const justCompleted = newCompleted.filter(s => !prevCompleted.includes(s));
        if (justCompleted.length > 0) {
          const msg = STEP_SUCCESS[justCompleted[justCompleted.length - 1]];
          if (msg) toast.success(msg);
        }
      }
    } catch { /* ignore */ }
  }, [progress]);

  const dismissGuide = useCallback(async () => {
    setShowGuide(false);
    setShowStuckHint(false);
    try {
      await api.post('/api/user/progress/dismiss-guide');
      setProgress(prev => prev ? { ...prev, guide_dismissed: true } : prev);
    } catch { /* ignore */ }
  }, []);

  const startFeatureGuide = useCallback((featureKey) => {
    const guide = FEATURE_GUIDES[featureKey];
    if (guide) {
      setActiveFeatureGuide({ key: featureKey, ...guide });
      setFeatureStep(0);
    }
  }, []);

  const nextFeatureStep = useCallback(() => {
    if (!activeFeatureGuide) return;
    if (featureStep < activeFeatureGuide.steps.length - 1) {
      setFeatureStep(s => s + 1);
    } else {
      setActiveFeatureGuide(null);
      setFeatureStep(0);
    }
  }, [activeFeatureGuide, featureStep]);

  const dismissFeatureGuide = useCallback(() => {
    setActiveFeatureGuide(null);
    setFeatureStep(0);
  }, []);

  const contextMessage = getContextMessage(progress);

  const value = {
    progress,
    loading,
    showGuide,
    showStuckHint,
    stuckMessage,
    contextMessage,
    activeFeatureGuide,
    featureStep,
    journeySteps: JOURNEY_STEPS,
    updateStep,
    dismissGuide,
    startFeatureGuide,
    nextFeatureStep,
    dismissFeatureGuide,
    setShowGuide,
    setShowStuckHint,
  };

  return <GuideContext.Provider value={value}>{children}</GuideContext.Provider>;
}

export function useProductGuide() {
  const ctx = useContext(GuideContext);
  if (!ctx) return {
    progress: null, loading: false, showGuide: false, showStuckHint: false,
    stuckMessage: '', contextMessage: { message: '', action: '' },
    activeFeatureGuide: null, featureStep: 0, journeySteps: [],
    updateStep: () => {}, dismissGuide: () => {}, startFeatureGuide: () => {},
    nextFeatureStep: () => {}, dismissFeatureGuide: () => {},
    setShowGuide: () => {}, setShowStuckHint: () => {},
  };
  return ctx;
}

export { JOURNEY_STEPS, FEATURE_GUIDES };
