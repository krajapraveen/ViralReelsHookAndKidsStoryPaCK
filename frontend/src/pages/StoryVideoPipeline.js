import React, { useState, useEffect, useRef, useCallback, useReducer } from 'react';
import { Link, useSearchParams, useNavigate, useLocation } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Progress } from '../components/ui/progress';
import { SafeImage } from '../components/SafeImage';
import { toast } from 'sonner';
import api from '../utils/api';
import {
  ArrowLeft, Wand2, Loader2, Film, Image, Mic, CheckCircle,
  Play, Download, RefreshCw, AlertCircle, Clock, Coins,
  Video, Upload, BookOpen, Sparkles, RotateCcw, XCircle, Eye, Package,
  Share2, Link2, Copy, ExternalLink, RefreshCcw as Remix, ShieldAlert,
  Shield, Check, X, Zap, ChevronDown, ArrowRight, GitBranch, Swords, BarChart2
} from 'lucide-react';
import FEATURES from '../config/featureFlags';
import { trackFunnel } from '../utils/funnelTracker';
import UpsellModal from '../components/UpsellModal';
import CreationActionsBar from '../components/CreationActionsBar';
import ProgressiveGeneration from '../components/ProgressiveGeneration';
import { useJobWebSocket } from '../hooks/useJobWebSocket';
import ContextualUpgrade from '../components/ContextualUpgrade';
import RemixBanner from '../components/RemixBanner';
import SharePromptModal from '../components/SharePromptModal';
import { ForceShareGate, ShareRewardBar } from '../components/ForceShareGate';
import ViralMomentumBadge from '../components/ViralMomentumBadge';
import ContinuationModal from '../components/ContinuationModal';
import CompetitionPulse from '../components/CompetitionPulse';
import { LiveViewerBadge } from '../components/AnimatedSocialProof';
import EntitledDownloadButton from '../components/EntitledDownloadButton';
import { useMediaEntitlement } from '../contexts/MediaEntitlementContext';

// ─── CONSTANTS ────────────────────────────────────────────────────────────────
const STAGE_ORDER = ['scenes', 'images', 'voices'];
const STAGE_ICONS = { scenes: BookOpen, images: Image, voices: Mic };
const STAGE_LABELS = { scenes: 'Scenes', images: 'Images', voices: 'Voices' };

// ─── CENTRALIZED FAILURE LABELS ──────────────────────────────────────────────
// Single source of truth: raw backend enums → human-readable copy.
// NEVER display engine_state directly in the UI.
const FAILED_STATE_LABELS = {
  FAILED_PLANNING: {
    title: "We couldn't complete story planning for this video",
    suggestion: 'The AI had trouble breaking your story into scenes. A retry usually fixes this.',
    stageLabel: 'Story Planning',
  },
  FAILED_IMAGES: {
    title: "Scene artwork generation didn't complete",
    suggestion: "Some scene images couldn't be generated. Retrying will pick up where it left off.",
    stageLabel: 'Scene Artwork',
  },
  FAILED_TTS: {
    title: 'Voice narration generation hit an issue',
    suggestion: "The voiceover couldn't be created. A retry usually resolves this.",
    stageLabel: 'Voice Narration',
  },
  FAILED_RENDER: {
    title: 'The final video assembly did not complete',
    suggestion: "All scenes were created but the final video couldn't be assembled. Retry to finish.",
    stageLabel: 'Video Assembly',
  },
  FAILED: {
    title: "This video didn't finish generating",
    suggestion: 'Something went wrong during generation. You can retry or start fresh.',
    stageLabel: 'Generation',
  },
};

function getFailureLabel(engineState, serverDetail) {
  if (serverDetail?.title) return { ...serverDetail, stageLabel: serverDetail.stage_label || serverDetail.stageLabel };
  return FAILED_STATE_LABELS[engineState] || FAILED_STATE_LABELS.FAILED;
}

// ─── ANALYTICS HELPER ─────────────────────────────────────────────────────────
function trackRecoveryEvent(event, jobId, engineState) {
  try {
    const token = localStorage.getItem('token');
    if (!token) return;
    fetch(`${process.env.REACT_APP_BACKEND_URL}/api/story-engine/recovery-event`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ event, job_id: jobId, engine_state: engineState }),
    }).catch(() => {});
  } catch {}
}

// ─── SAFE ACTION WRAPPER ────────────────────────────────────────────────────
// Prevents undefined handler crashes. Logs to monitoring endpoint.
function safeAction(fn, label = 'action') {
  if (typeof fn !== 'function') {
    console.error(`[StoryVideoStudio] Missing handler: ${label}`);
    try {
      const token = localStorage.getItem('token');
      if (token) {
        fetch(`${process.env.REACT_APP_BACKEND_URL}/api/monitoring/client-error`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({ module: 'story_video_studio', error: `Missing handler: ${label}`, timestamp: new Date().toISOString() }),
        }).catch(() => {});
      }
    } catch {}
    return () => {};
  }
  return async (...args) => {
    try {
      await fn(...args);
    } catch (error) {
      console.error(`[StoryVideoStudio] ${label} failed:`, error);
    }
  };
}

// Timeout thresholds
const SOFT_TIMEOUT_MS = 5 * 60 * 1000;   // 5 min → show "taking longer" message
const HARD_TIMEOUT_MS = 15 * 60 * 1000;  // 15 min → background + notify
// Stale detection: 90 seconds with no progress change
const STALE_THRESHOLD_MS = 90 * 1000;

// ─── COMPETITIVE COMPARISON COMPONENT ──────────────────────────────────────
function CompetitiveComparison({ posterUrl, displayTitle, navigate, storyText, currentStyle, jobId, job, onBeat, onImprove }) {
  const [topItem, setTopItem] = useState(null);

  useEffect(() => {
    const fetchTop = async () => {
      try {
        const res = await api.get('/api/gallery/remix-feed?limit=1');
        if (res.data?.items?.[0]) setTopItem(res.data.items[0]);
      } catch { /* silent */ }
    };
    fetchTop();
  }, []);

  if (!topItem || !posterUrl) return null;

  const handleBeat = () => {
    try { api.post('/api/funnel/track', { event: 'try_to_beat_clicked', data: { job_id: jobId, target: topItem.item_id } }); } catch {}
    if (onBeat) {
      onBeat(topItem);
    } else {
      navigate('/app/story-video-studio', {
        state: { prompt: storyText || '', remixFrom: { title: topItem.title, item_id: topItem.item_id }, isRemix: true },
      });
    }
  };

  const handleImprove = () => {
    try { api.post('/api/funnel/track', { event: 'improve_yours_clicked', data: { job_id: jobId } }); } catch {}
    if (onImprove) {
      onImprove();
    } else {
      localStorage.setItem('remix_video', JSON.stringify({
        parent_video_id: jobId, title: `Improved: ${displayTitle}`,
        story_text: storyText || job?.story_text || '', animation_style: currentStyle,
      }));
      navigate('/app/story-video-studio?remix=improve');
    }
  };

  return (
    <div className="bg-slate-900/50 border border-orange-500/10 rounded-xl p-4 space-y-3" data-testid="competitive-comparison">
      <h3 className="text-sm font-semibold text-white flex items-center gap-2">
        <Zap className="w-3.5 h-3.5 text-orange-400" /> Can you beat this version?
      </h3>
      <div className="grid grid-cols-2 gap-3">
        {/* Your version */}
        <div className="rounded-lg border border-emerald-500/20 overflow-hidden">
          <div className="aspect-video bg-zinc-800 overflow-hidden">
            <img src={posterUrl} alt="Your version" className="w-full h-full object-cover" />
          </div>
          <div className="p-2 bg-emerald-500/5">
            <p className="text-[10px] font-semibold text-emerald-400 uppercase tracking-wider">Your version</p>
            <p className="text-[11px] text-zinc-300 truncate">{displayTitle}</p>
          </div>
        </div>
        {/* Top version */}
        <div className="rounded-lg border border-orange-500/20 overflow-hidden">
          <div className="aspect-video bg-zinc-800 overflow-hidden">
            {topItem.thumbnail_url ? (
              <img src={topItem.thumbnail_url} alt="Trending" className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <Film className="w-6 h-6 text-zinc-700" />
              </div>
            )}
          </div>
          <div className="p-2 bg-orange-500/5">
            <p className="text-[10px] font-semibold text-orange-400 uppercase tracking-wider flex items-center gap-1">
              Trending
              {topItem.remixes_count > 0 && <span className="text-zinc-500">&middot; {topItem.remixes_count.toLocaleString()} remixes</span>}
            </p>
            <p className="text-[11px] text-zinc-300 truncate">{topItem.title}</p>
          </div>
        </div>
      </div>
      <div className="flex gap-2">
        <button
          onClick={handleBeat}
          className="flex-1 py-2.5 rounded-xl bg-orange-500/15 text-orange-300 text-xs font-bold hover:bg-orange-500/25 transition-colors flex items-center justify-center gap-1.5"
          data-testid="beat-this-btn"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Try to beat this
        </button>
        <button
          onClick={handleImprove}
          className="flex-1 py-2.5 rounded-xl bg-white/[0.06] text-zinc-300 text-xs font-medium hover:bg-white/10 transition-colors flex items-center justify-center gap-1.5"
          data-testid="improve-version-btn"
        >
          <Sparkles className="w-3.5 h-3.5" /> Improve yours
        </button>
      </div>
    </div>
  );
}


// ─── UI STATE MACHINE ─────────────────────────────────────────────────────────
// Single source of truth. Contradictory states are structurally impossible.
// States: IDLE | PROCESSING | VALIDATING | READY | PARTIAL_READY | FAILED
const INITIAL_POST_GEN_STATE = {
  uiState: 'IDLE',
  previewReady: false,
  downloadReady: false,
  shareReady: false,
  posterUrl: null,
  downloadUrl: null,
  shareUrl: null,
  storyPackUrl: null,
  failReason: '',
  stageDetail: '',
  jobTitle: '',
  canRetry: false,
  errorCode: null,
  creditsRefunded: 0,
};

function postGenReducer(state, action) {
  switch (action.type) {
    case 'START_VALIDATING':
      return {
        ...INITIAL_POST_GEN_STATE,
        uiState: 'VALIDATING',
        stageDetail: 'Validating assets...',
        jobTitle: action.title || state.jobTitle,
      };
    case 'SET_READY':
      return {
        ...state,
        uiState: 'READY',
        previewReady: true,
        downloadReady: true,
        shareReady: action.shareReady ?? false,
        posterUrl: action.posterUrl,
        downloadUrl: action.downloadUrl,
        shareUrl: action.shareUrl,
        storyPackUrl: action.storyPackUrl,
        stageDetail: action.stageDetail || 'Video ready',
      };
    case 'SET_PARTIAL_READY':
      return {
        ...state,
        uiState: 'PARTIAL_READY',
        previewReady: action.previewReady ?? false,
        downloadReady: action.downloadReady ?? false,
        shareReady: false,
        posterUrl: action.posterUrl,
        downloadUrl: action.downloadUrl,
        storyPackUrl: action.storyPackUrl,
        stageDetail: action.stageDetail || 'Video saved — download available, preview limited',
      };
    case 'SET_FAILED':
      return {
        ...INITIAL_POST_GEN_STATE,
        uiState: 'FAILED',
        failReason: action.reason || 'Generation failed',
        stageDetail: action.stageDetail || action.reason || 'Generation failed',
        posterUrl: action.posterUrl || null,
        downloadUrl: action.downloadUrl || null,
        storyPackUrl: action.storyPackUrl || null,
        downloadReady: action.downloadReady || false,
        canRetry: action.canRetry || false,
        errorCode: action.errorCode || null,
        creditsRefunded: action.creditsRefunded || 0,
      };
    case 'RESET':
      return INITIAL_POST_GEN_STATE;
    default:
      return state;
  }
}

// ─── ERROR BOUNDARY ───────────────────────────────────────────────────────────
class StudioErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null, retryCount: 0 };
  }
  static getDerivedStateFromError(error) { return { hasError: true, error }; }
  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    // Log to console for debugging
    console.error('[StoryVideoStudio] Error boundary caught:', {
      message: error?.message,
      stack: error?.stack?.split('\n').slice(0, 5).join('\n'),
      component: errorInfo?.componentStack?.split('\n').slice(0, 3).join('\n'),
      url: window.location.href,
      timestamp: new Date().toISOString(),
    });
    // Try to log to backend
    try {
      const token = localStorage.getItem('token');
      if (token) {
        fetch(`${process.env.REACT_APP_BACKEND_URL}/api/monitoring/client-error`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({
            module: 'story_video_studio',
            error: error?.message,
            stack: error?.stack?.slice(0, 1000),
            componentStack: errorInfo?.componentStack?.slice(0, 500),
            url: window.location.href,
            timestamp: new Date().toISOString(),
          }),
        }).catch(() => {});
      }
    } catch {}
  }
  handleRetry = () => {
    this.setState(prev => ({ hasError: false, error: null, errorInfo: null, retryCount: prev.retryCount + 1 }));
  };
  render() {
    if (this.state.hasError) {
      const { error, retryCount } = this.state;
      const errorMsg = error?.message || 'Unknown error';
      // Classify the error for user-facing message
      let category = 'render_error';
      let userMessage = 'The video studio hit an unexpected issue.';
      let suggestion = 'Try again or go back to the dashboard.';
      if (errorMsg.includes('undefined') || errorMsg.includes('null') || errorMsg.includes('Cannot read')) {
        category = 'data_error';
        userMessage = 'A data loading issue occurred.';
        suggestion = 'This is usually temporary — try refreshing or clearing your browser cache.';
      } else if (errorMsg.includes('network') || errorMsg.includes('fetch') || errorMsg.includes('Network')) {
        category = 'network_error';
        userMessage = 'A network connection issue occurred.';
        suggestion = 'Check your internet connection and try again.';
      } else if (errorMsg.includes('chunk') || errorMsg.includes('Loading chunk') || errorMsg.includes('import')) {
        category = 'cache_error';
        userMessage = 'The app needs a fresh reload.';
        suggestion = 'A new version may be available. Hard refresh (Ctrl+Shift+R) should fix this.';
      }
      return (
        <div className="vs-page flex items-center justify-center p-8" data-testid="studio-error-boundary">
          <div className="max-w-lg text-center space-y-4">
            <AlertCircle className="w-12 h-12 text-red-400 mx-auto" />
            <h2 className="text-xl font-bold text-white">{userMessage}</h2>
            <p className="text-sm text-slate-400">{suggestion}</p>
            <p className="text-xs text-slate-600 font-mono bg-slate-800/50 rounded px-3 py-2 text-left break-all">
              Error: {errorMsg.slice(0, 200)}
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center pt-2">
              {retryCount < 3 && (
                <button onClick={this.handleRetry} className="vs-btn-primary px-6 py-2.5 text-sm" data-testid="retry-btn">
                  <RefreshCw className="w-4 h-4 mr-2 inline" /> Try Again
                </button>
              )}
              <button onClick={() => window.location.reload()} className="px-6 py-2.5 text-sm rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-700 transition-colors" data-testid="refresh-btn">
                Refresh Page
              </button>
              <button onClick={() => window.location.href = '/app'} className="px-6 py-2.5 text-sm rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-700 transition-colors" data-testid="dashboard-btn">
                Go to Dashboard
              </button>
            </div>
            {retryCount >= 2 && (
              <p className="text-xs text-amber-400 mt-2">
                Still not working? Try clearing your browser cache or using an incognito window.
              </p>
            )}
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

// ─── MAIN COMPONENT ───────────────────────────────────────────────────────────
function StoryVideoPipelineInner() {
  const navigate = useNavigate();
  const location = useLocation();
  const [phase, setPhase] = useState('input'); // input | processing | postgen | error
  const [options, setOptions] = useState(null);
  const [title, setTitle] = useState('');
  const [storyText, setStoryText] = useState('');
  const [animStyle, setAnimStyle] = useState('cartoon_2d');
  const [challengeId, setChallengeId] = useState(null);
  const [challengeTitle, setChallengeTitle] = useState('');
  const [ageGroup, setAgeGroup] = useState('kids_5_8');
  const [voicePreset, setVoicePreset] = useState('narrator_warm');
  const [jobId, setJobId] = useState(null);
  const [job, setJob] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [userJobs, setUserJobs] = useState([]);
  const [showWelcome, setShowWelcome] = useState(false);
  const [showUpsell, setShowUpsell] = useState(false);
  const [userCredits, setUserCredits] = useState(null);
  const [creditGate, setCreditGate] = useState(null); // { required, current, shortfall }
  const [remixData, setRemixData] = useState(null);
  const [showRemixBanner, setShowRemixBanner] = useState(false);
  const [remixSourceTool, setRemixSourceTool] = useState(null);
  const [remixSourceTitle, setRemixSourceTitle] = useState(null);
  const [rateLimitStatus, setRateLimitStatus] = useState(null);
  const [formError, setFormError] = useState('');
  const [reuseInfo, setReuseInfo] = useState(null);
  const [qualityMode, setQualityMode] = useState('balanced');
  // Series context — when generating from a Story Series flow
  const [seriesContext, setSeriesContext] = useState(null);

  // ─── FUNNEL TRACKING (dedup guards) ──────────────────────────────────────
  const typingStartedRef = useRef(false);

  // ─── DRAFT PERSISTENCE ─────────────────────────────────────────────────────
  const [showResumeDraft, setShowResumeDraft] = useState(false);
  const [pendingDraft, setPendingDraft] = useState(null);
  const draftSaveTimer = useRef(null);
  const lastSavedRef = useRef({ title: '', storyText: '' });
  const isFreshSession = !!location.state?.freshSession;

  // Auto-save draft (debounced — saves 3s after last change, only if content changed)
  useEffect(() => {
    if (phase !== 'input') return;
    if (!title.trim() && !storyText.trim()) return;

    // Fire typing_started ONCE per session
    if (!typingStartedRef.current && (title.trim() || storyText.trim())) {
      typingStartedRef.current = true;
      trackFunnel('typing_started', { meta: { source: isFreshSession ? 'fresh' : 'return' } });
    }

    // Don't save if content hasn't changed
    if (title === lastSavedRef.current.title && storyText === lastSavedRef.current.storyText) return;

    if (draftSaveTimer.current) clearTimeout(draftSaveTimer.current);
    draftSaveTimer.current = setTimeout(() => {
      lastSavedRef.current = { title, storyText };
      api.post('/api/drafts/save', {
        title, story_text: storyText, animation_style: animStyle,
        age_group: ageGroup, voice_preset: voicePreset,
      }).catch(() => {}); // silent save
    }, 3000);

    return () => { if (draftSaveTimer.current) clearTimeout(draftSaveTimer.current); };
  }, [title, storyText, animStyle, ageGroup, voicePreset, phase]);

  // Check for existing draft on fresh session mount
  useEffect(() => {
    if (!isFreshSession) return;
    if (searchParams.get('projectId')) return; // deep-linked to a project
    api.get('/api/drafts/current').then(res => {
      const draft = res.data?.draft;
      if (draft && (draft.title?.trim() || draft.story_text?.trim())) {
        setPendingDraft(draft);
        setShowResumeDraft(true);
      }
    }).catch(() => {});
  }, [isFreshSession]);

  const handleResumeDraft = () => {
    if (pendingDraft) {
      setTitle(pendingDraft.title || '');
      setStoryText(pendingDraft.story_text || '');
      if (pendingDraft.animation_style) setAnimStyle(pendingDraft.animation_style);
      if (pendingDraft.age_group) setAgeGroup(pendingDraft.age_group);
      if (pendingDraft.voice_preset) setVoicePreset(pendingDraft.voice_preset);
      lastSavedRef.current = { title: pendingDraft.title || '', storyText: pendingDraft.story_text || '' };
    }
    setShowResumeDraft(false);
  };

  const handleDiscardDraft = () => {
    api.delete('/api/drafts/discard').catch(() => {});
    setShowResumeDraft(false);
  };

  // Clear draft when story is successfully generated (status-based, never delete)
  useEffect(() => {
    if (!FEATURES.draftPersistenceV2) return;
    if (phase === 'processing' && jobId) {
      // Mark draft as processing — NOT deleted. Recoverable on failure.
      api.post('/api/drafts/status', { status: 'processing' }).catch(() => {});
    }
    if (phase === 'postgen' && jobId) {
      // Generation succeeded — mark completed
      api.post('/api/drafts/status', { status: 'completed' }).catch(() => {});
    }
  }, [phase, jobId]);

  // ─── NAVIGATION GUARD (unsaved changes warning) ────────────────────────────
  useEffect(() => {
    const hasContent = title.trim().length > 20 || storyText.trim().length > 20;
    if (!hasContent || phase !== 'input') return;

    const handler = (e) => {
      e.preventDefault();
      e.returnValue = '';
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [title, storyText, phase]);

  // ─── DRAFT FAILURE RECOVERY ────────────────────────────────────────────────
  // (Moved after postGen useReducer — see below)

  const onViewJob = useCallback((job) => {
    if (job?.job_id) {
      navigate(`/app/story-video-studio?projectId=${job.job_id}`);
    }
  }, [navigate]);
  const [showLoginGate, setShowLoginGate] = useState(false);
  const pollRef = useRef(null);
  const [searchParams] = useSearchParams();

  // Duplicate click guard
  const createLockRef = useRef(false);

  // Post-generation state machine
  const [postGen, dispatchPostGen] = useReducer(postGenReducer, INITIAL_POST_GEN_STATE);

  // ─── DRAFT FAILURE RECOVERY (must be after postGen useReducer) ─────────────
  useEffect(() => {
    if (!FEATURES.draftPersistenceV2) return;
    if (postGen.uiState === 'FAILED') {
      api.post('/api/drafts/status', { status: 'draft' }).catch(() => {});
    }
  }, [postGen.uiState]);

  // Timeout tracking (soft + hard)
  const hardTimeoutRef = useRef(null);
  const softTimeoutRef = useRef(null);
  const staleTimeoutRef = useRef(null);
  const lastProgressRef = useRef(0);
  const lastProgressTimeRef = useRef(Date.now());
  const [softTimeoutReached, setSoftTimeoutReached] = useState(false);

  // WebSocket
  const token = localStorage.getItem('token');
  const { wsRef } = useJobWebSocket(jobId, token);

  // ─── INIT ─────────────────────────────────────────────────────────
  useEffect(() => {
    api.get('/api/story-engine/options').then(r => setOptions(r.data)).catch(() => {
      toast.error('Failed to load studio options. Some settings may be unavailable.');
    });
    loadUserJobs();
    checkUpsell();
    checkRateLimit();

    // ── Restore saved state (after login redirect) ──
    const savedState = localStorage.getItem('studio_saved_state');
    if (savedState) {
      try {
        const ss = JSON.parse(savedState);
        if (ss.timestamp && Date.now() - ss.timestamp < 15 * 60 * 1000) {
          if (ss.title) setTitle(ss.title);
          if (ss.storyText) setStoryText(ss.storyText);
          if (ss.animStyle) setAnimStyle(ss.animStyle);
          if (ss.ageGroup) setAgeGroup(ss.ageGroup);
          if (ss.voicePreset) setVoicePreset(ss.voicePreset);
          if (ss.remixData) setRemixData(ss.remixData);
          setShowWelcome(true);
        }
      } catch {}
      localStorage.removeItem('studio_saved_state');
    }

    // ── Handle location.state from Dashboard "Continue Story" ──
    const locState = location?.state || window.history?.state?.usr;
    if (locState?.prefill && !savedState) {
      const pf = locState.prefill;
      if (typeof pf === 'string') {
        // Legacy: bare string prompt
        setStoryText(pf);
      } else if (typeof pf === 'object') {
        // Full prefill: title, prompt, animation_style, parent_video_id, hook_text
        if (pf.title) setTitle(pf.title);
        if (pf.prompt) setStoryText(pf.prompt);
        if (pf.animation_style) setAnimStyle(pf.animation_style);
        if (pf.parent_video_id) {
          setRemixData({ parent_video_id: pf.parent_video_id, hook_text: pf.hook_text, characters: pf.characters });
        }
      }
    }
    // Only auto-reconnect to active jobs on page REFRESH (not fresh navigation from Dashboard)
    if (!locState?.freshSession) {
      if (locState?.continueFrom && !savedState) {
        setRemixData({ parent_video_id: locState.continueFrom });
      }
    }

    // Handle remix
    const isRemix = searchParams.get('remix');
    if (isRemix) {
      const saved = localStorage.getItem('remix_video');
      if (saved) {
        try {
          const rd = JSON.parse(saved);
          setRemixData(rd);
          setTitle(`Remix: ${rd.title || 'Untitled'}`);
          setStoryText(rd.story_text || '');
          if (rd.animation_style) setAnimStyle(rd.animation_style);
          if (rd.age_group) setAgeGroup(rd.age_group);
          if (rd.voice_preset) setVoicePreset(rd.voice_preset);
          localStorage.removeItem('remix_video');
        } catch { /* ignore */ }
      }
    }

    // Handle remix_data from Remix & Variations Engine / Cross-tool hooks
    const newRemixData = localStorage.getItem('remix_data');
    if (newRemixData && !isRemix) {
      try {
        const rd = JSON.parse(newRemixData);
        // TTL check (10 min)
        if (rd.timestamp && Date.now() - rd.timestamp > 10 * 60 * 1000) {
          localStorage.removeItem('remix_data');
        } else {
          if (rd.prompt) setStoryText(rd.prompt);
          // Capture series context if coming from Story Series flow
          if (rd.source_tool === 'series-continue' && rd.series_id) {
            setSeriesContext({
              series_id: rd.series_id,
              series_title: rd.series_title,
              episode_number: rd.episode_number,
              mode: rd.mode || 'create',
              character_ids: rd.character_ids || [],
            });
          }
          if (rd.remixFrom) {
            setRemixData(rd.remixFrom);
            if (rd.remixFrom.title) setTitle(rd.remixFrom.title.startsWith('From:') ? rd.remixFrom.title : `From: ${rd.remixFrom.title}`);
            if (rd.remixFrom.settings?.animation_style || rd.remixFrom.settings?.style) setAnimStyle(rd.remixFrom.settings.animation_style || rd.remixFrom.settings.style);
            if (rd.remixFrom.settings?.age_group || rd.remixFrom.settings?.ageGroup) setAgeGroup(rd.remixFrom.settings.age_group || rd.remixFrom.settings.ageGroup);
            if (rd.remixFrom.settings?.voice_preset) setVoicePreset(rd.remixFrom.settings.voice_preset);
            setRemixSourceTool(rd.remixFrom.tool || rd.source_tool);
            setRemixSourceTitle(rd.remixFrom.title);
            setShowRemixBanner(true);
            // Capture continuation context
            if (rd.remixFrom.hook_text || rd.remixFrom.characters) {
              setRemixData(prev => ({
                ...prev,
                hook_text: rd.remixFrom.hook_text || prev?.hook_text,
                characters: rd.remixFrom.characters || prev?.characters,
                parent_video_id: rd.remixFrom.parentId || prev?.parent_video_id,
              }));
            }
          }
          localStorage.removeItem('remix_data');
        }
      } catch { /* ignore */ }
    }

    // Handle onboarding prompt
    const urlPrompt = searchParams.get('prompt');
    const savedPrompt = localStorage.getItem('onboarding_prompt');
    const prompt = urlPrompt || savedPrompt;
    if (prompt && !isRemix) {
      setStoryText(prompt);
      setShowWelcome(true);
      localStorage.removeItem('onboarding_prompt');
    }

    // Handle daily challenge
    const challengeParam = searchParams.get('challenge');
    if (challengeParam) {
      setChallengeId(challengeParam);
      if (locState?.prompt) setStoryText(locState.prompt);
      if (locState?.challengeTitle) setChallengeTitle(locState.challengeTitle);
    }

    // ─── DEEP-LINK: projectId handled in separate useEffect after all hooks ───

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      if (hardTimeoutRef.current) clearTimeout(hardTimeoutRef.current);
      if (staleTimeoutRef.current) clearTimeout(staleTimeoutRef.current);
    };
  }, [searchParams]);

  // ─── LOAD USER JOBS + RECONNECT SAFETY ────────────────────────────
  const loadUserJobs = async () => {
    try {
      const res = await api.get('/api/story-engine/user-jobs');
      if (res.data.success) {
        setUserJobs(res.data.jobs || []);
        // Auto-reconnect ONLY if:
        // 1. Not a fresh session from Dashboard
        // 2. Job is genuinely recent (<10 min old)
        // 3. No projectId deep-link in URL (deep-link takes priority)
        const locState = location?.state || window.history?.state?.usr;
        const hasDeepLink = searchParams.get('projectId');
        if (!locState?.freshSession && !hasDeepLink) {
          const active = (res.data.jobs || []).find(j => {
            if (!['QUEUED', 'PROCESSING'].includes(j.status)) return false;
            // Don't auto-reconnect to stale jobs (>10 min old)
            const createdAt = new Date(j.created_at || j.createdAt || 0).getTime();
            const ageMs = Date.now() - createdAt;
            return ageMs < 10 * 60 * 1000; // Only reconnect if <10 min old
          });
          if (active) {
            setJobId(active.job_id);
            setJob(active);
            setPhase('processing');
            startPolling(active.job_id);
          }
        }
      }
    } catch {
      console.warn('Failed to load user jobs');
    }
  };

  const checkUpsell = async () => {
    try {
      const res = await api.get('/api/credits/check-upsell');
      setUserCredits(res.data.credits ?? null);
      // Don't auto-show UpsellModal — the credit gate modal handles this at click time
    } catch { /* ignore — user might not be logged in */ }
  };

  const checkRateLimit = async () => {
    try {
      const res = await api.get('/api/story-engine/rate-limit-status');
      setRateLimitStatus(res.data);
    } catch { /* ignore */ }
  };

  // ─── CLEAR TIMEOUTS ──────────────────────────────────────────────
  const clearAllTimeouts = useCallback(() => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    if (hardTimeoutRef.current) { clearTimeout(hardTimeoutRef.current); hardTimeoutRef.current = null; }
    if (softTimeoutRef.current) { clearTimeout(softTimeoutRef.current); softTimeoutRef.current = null; }
    if (staleTimeoutRef.current) { clearTimeout(staleTimeoutRef.current); staleTimeoutRef.current = null; }
  }, []);

  // ─── VALIDATE ASSETS (single source of truth) ────────────────────
  const validateAndResolve = useCallback(async (jid, jobData) => {
    dispatchPostGen({ type: 'START_VALIDATING', title: jobData?.title || '' });

    try {
      const res = await api.get(`/api/story-engine/validate-asset/${jid}`);
      const v = res.data;

      if (v.ui_state === 'READY') {
        dispatchPostGen({
          type: 'SET_READY',
          posterUrl: v.poster_url,
          downloadUrl: v.download_url,
          shareUrl: v.share_url,
          shareReady: v.share_ready,
          storyPackUrl: v.story_pack_url,
          stageDetail: v.stage_detail,
        });
      } else if (v.ui_state === 'PARTIAL_READY') {
        dispatchPostGen({
          type: 'SET_PARTIAL_READY',
          previewReady: v.preview_ready,
          downloadReady: v.download_ready,
          posterUrl: v.poster_url,
          downloadUrl: v.download_url,
          storyPackUrl: v.story_pack_url,
          stageDetail: v.stage_detail,
        });
      } else {
        dispatchPostGen({
          type: 'SET_FAILED',
          reason: v.stage_detail || 'Asset validation failed',
          posterUrl: v.poster_url,
          downloadUrl: v.download_url,
          storyPackUrl: v.story_pack_url,
          downloadReady: v.download_ready,
        });
      }
    } catch {
      // Validation endpoint failed — use job data as fallback
      const hasOutput = !!jobData?.output_url;
      const hasFallback = !!jobData?.fallback?.fallback_video_url || !!jobData?.fallback?.story_pack_url;
      if (hasOutput || hasFallback) {
        dispatchPostGen({
          type: 'SET_PARTIAL_READY',
          previewReady: false,
          downloadReady: true,
          downloadUrl: jobData?.output_url || jobData?.fallback?.fallback_video_url,
          storyPackUrl: jobData?.fallback?.story_pack_url,
          stageDetail: 'Assets may be available — validation check failed',
        });
      } else {
        dispatchPostGen({ type: 'SET_FAILED', reason: 'Could not verify assets' });
      }
    }
  }, []);

  // ─── POLLING with timeout/stale detection ────────────────────────
  const startPolling = useCallback((jid) => {
    clearAllTimeouts();
    lastProgressRef.current = 0;
    lastProgressTimeRef.current = Date.now();

    // Soft timeout — show "taking longer" message, don't kill the job
    softTimeoutRef.current = setTimeout(() => {
      setSoftTimeoutReached(true);
      toast.info('Taking longer than usual — your video is still being generated.', { duration: 5000 });
    }, SOFT_TIMEOUT_MS);

    // Hard timeout — switch to background mode, don't force-fail
    hardTimeoutRef.current = setTimeout(() => {
      clearAllTimeouts();
      toast.info('We will continue generating in the background. You will be notified when ready.', { duration: 8000 });
      // Enable notify and show graceful message instead of killing the page
      dispatchPostGen({
        type: 'SET_FAILED',
        reason: 'Generation is taking longer than expected. Your video is still being processed in the background.',
        stageDetail: 'Extended generation — processing continues safely',
      });
      setPhase('postgen');
    }, HARD_TIMEOUT_MS);

    const poll = async () => {
      try {
        const res = await api.get(`/api/story-engine/status/${jid}`);
        if (res.data.success) {
          const j = res.data.job;
          setJob(j);

          // Stale detection
          const now = Date.now();
          if (j.progress !== lastProgressRef.current) {
            lastProgressRef.current = j.progress;
            lastProgressTimeRef.current = now;
          } else if (now - lastProgressTimeRef.current > STALE_THRESHOLD_MS && j.status === 'PROCESSING') {
            // Progress hasn't changed in 90 seconds — but check if retries are happening
            const retrying = j.retry_info?.current_attempt > 1;
            if (!retrying) {
              toast.warning('Generation is taking longer than usual — the system is working on it.', { id: 'stale-warning' });
            }
          }

          if (j.status === 'COMPLETED' || j.status === 'PARTIAL') {
            clearAllTimeouts();
            setPhase('postgen');
            trackFunnel('generation_completed', { story_id: jid, meta: { status: j.status } });
            // Canonical activation funnel — story complete (founder spec)
            try {
              trackFunnel('story_generation_completed', {
                source_page: 'studio',
                story_id: jid,
                meta: { status: j.status, has_video: !!j.output_url },
              });
              if (typeof window !== 'undefined' && typeof window.__markActivated__ === 'function') {
                window.__markActivated__();
              }
            } catch (_) { /* noop */ }
            await validateAndResolve(jid, j);
          } else if (j.status === 'FAILED') {
            clearAllTimeouts();
            // Canonical activation funnel — generation failed
            try {
              trackFunnel('story_generation_failed', {
                source_page: 'studio',
                story_id: jid,
                meta: { error: j.error || 'unknown', view_mode: j.view_mode },
              });
            } catch (_) { /* noop */ }
            // Use server-authoritative view_mode
            if (j.view_mode === 'failed_recovery') {
              setPhase('failed_recovery');
              trackRecoveryEvent('failed_job_viewed', jid, j.engine_state);
            } else {
              // Fallback: recoverable assets → postgen, otherwise recovery
              const hasRecoverable = j.has_recoverable_assets || j.fallback?.has_preview || j.fallback?.story_pack_url;
              if (hasRecoverable) {
                setPhase('postgen');
                await validateAndResolve(jid, j);
              } else {
                setPhase('failed_recovery');
                trackRecoveryEvent('failed_job_viewed', jid, j.engine_state);
              }
            }
          }
        }
      } catch { /* continue polling */ }
    };
    poll();
    pollRef.current = setInterval(poll, 3000);
  }, [clearAllTimeouts, validateAndResolve]);

  // ─── DEEP-LINK: Load project by ID from URL ────────────────────
  const loadProjectById = useCallback(async (pid) => {
    try {
      const res = await api.get(`/api/story-engine/status/${pid}`);
      if (res.data.success) {
        const j = res.data.job;
        setJobId(pid);
        setJob(j);

        const viewMode = j.view_mode || 'progress';
        if (viewMode === 'failed_recovery') {
          setPhase('failed_recovery');
          trackRecoveryEvent('failed_job_viewed', pid, j.engine_state);
        } else if (viewMode === 'result') {
          setPhase('postgen');
          validateAndResolve(pid, j);
        } else {
          setPhase('processing');
          startPolling(pid);
        }
      }
    } catch {
      toast.error('Could not load the project. It may have been deleted.');
    }
  }, [validateAndResolve, startPolling]);

  // Deep-link effect — runs after all hooks are initialized
  useEffect(() => {
    const deepLinkProjectId = searchParams.get('projectId');
    if (deepLinkProjectId) {
      loadProjectById(deepLinkProjectId);
    }
  }, [searchParams, loadProjectById]);

  // ─── GENERATE (with duplicate guard) ──────────────────────────────
  const handleGenerate = async () => {
    if (createLockRef.current) return; // Prevent double-click
    setFormError('');

    // Track generate_clicked BEFORE validation — captures intent even on validation failure
    trackFunnel('generate_clicked', {
      story_id: jobId,
      meta: { title_length: title.trim().length, story_length: storyText.trim().length, style: animStyle },
    });

    if (!title.trim()) { setFormError('Please enter a title for your video.'); return; }
    if (title.trim().length < 3) { setFormError('Title must be at least 3 characters.'); return; }
    if (title.trim().length > 100) { setFormError('Title must be 100 characters or less.'); return; }
    if (!storyText.trim()) { setFormError('Please enter a story to generate a video from.'); return; }
    if (storyText.trim().length < 50) {
      setFormError(`Story must be at least 50 characters. You have ${storyText.trim().length} — need ${50 - storyText.trim().length} more.`);
      return;
    }
    if (rateLimitStatus && !rateLimitStatus.can_create) {
      setFormError(rateLimitStatus.reason || 'You cannot create a video right now.');
      return;
    }

    // ═══ STRICT CREDIT GATE — Pre-flight check before ANY generation ═══
    try {
      const creditRes = await api.get('/api/story-engine/credit-check');
      const { sufficient, required, current, shortfall } = creditRes.data;
      setUserCredits(current);
      if (!sufficient) {
        setCreditGate({ required, current, shortfall });
        return; // Block generation — modal will show
      }
    } catch (creditErr) {
      if (creditErr.response?.status === 401) {
        // Not logged in — let the create call handle the login gate
      } else {
        setFormError('Could not verify your credit balance. Please try again.');
        return;
      }
    }

    createLockRef.current = true;
    setSubmitting(true);

    // Canonical activation funnel — prompt submitted (founder spec Apr 2026)
    try {
      trackFunnel('prompt_submitted', {
        source_page: 'studio',
        meta: {
          length: storyText.trim().length,
          has_title: !!title.trim(),
          animation_style: animStyle,
          quality_mode: qualityMode,
        },
      });
    } catch (_) { /* never block create */ }

    try {
      const payload = {
        title: title.trim(),
        story_text: storyText.trim(),
        animation_style: animStyle,
        age_group: ageGroup,
        voice_preset: voicePreset,
        quality_mode: qualityMode,
      };
      if (remixData?.parent_video_id) payload.parent_video_id = remixData.parent_video_id;
      // Attach series context so the backend can link the episode to the series
      if (seriesContext?.series_id) {
        payload.series_id = seriesContext.series_id;
        payload.episode_number = seriesContext.episode_number;
      }
      // Attach challenge participation
      if (challengeId) {
        payload.challenge_id = challengeId;
      }

      const res = await api.post('/api/story-engine/create', payload);
      if (res.data.success) {
        setJobId(res.data.job_id);
        setPhase('processing');
        setFormError('');
        dispatchPostGen({ type: 'RESET' });

        // Canonical activation funnel — story generation kicked off
        try {
          trackFunnel('story_generation_started', {
            source_page: 'studio',
            meta: { job_id: res.data.job_id, is_guest: !!res.data.is_guest },
          });
          // Mark this session as "activated" so beforeunload won't fire session_abandoned
          if (typeof window !== 'undefined' && typeof window.__markActivated__ === 'function') {
            window.__markActivated__();
          }
        } catch (_) { /* never block UX */ }

        // Capture reuse info for status display
        if (res.data.reuse_mode && res.data.reuse_mode !== 'fresh') {
          setReuseInfo({
            reuse_mode: res.data.reuse_mode,
            reusable_stages: res.data.stages_reused || [],
            invalidated_stages: res.data.stages_to_generate || [],
          });
          const reusedCount = (res.data.stages_reused || []).length;
          toast.success(`Optimized! Reusing ${reusedCount} stage${reusedCount !== 1 ? 's' : ''} from previous video.`);
        } else {
          setReuseInfo(null);
        }

        if (res.data.is_guest) {
          toast.success('Your free video is being created! Sign up after to save it.');
        } else if (res.data.degraded) {
          toast.info(`System is busy — your video will use ${res.data.estimated_scenes} scenes for faster delivery.`);
        } else if (res.data.queue_warning) {
          toast.info(res.data.queue_warning);
        } else if (!res.data.reuse_mode || res.data.reuse_mode === 'fresh') {
          toast.success(`Video queued! ${res.data.credits_charged} credits charged.`);
        }

        // Show rewrite note if terms were sanitized
        if (res.data.rewrite_note) {
          toast.info(res.data.rewrite_note, { duration: 5000 });
        }

        // Auto-redirect to My Space so user can watch live progress
        toast.success('Redirecting to My Space to track progress...');
        setTimeout(() => {
          navigate(`/app/my-space?projectId=${res.data.job_id}`);
        }, 1500);
      } else {
        setFormError(res.data.detail || res.data.message || 'Failed to create video.');
      }
    } catch (e) {
      const status = e.response?.status;
      const rawDetail = e.response?.data?.detail;
      let detail = '';
      if (typeof rawDetail === 'string') detail = rawDetail;
      else if (Array.isArray(rawDetail)) {
        detail = rawDetail.map(err => {
          const field = err.loc?.slice(-1)?.[0] || '';
          const fieldName = field === 'story_text' ? 'Story' : field === 'title' ? 'Title' : field;
          return `${fieldName}: ${err.msg}`;
        }).join('. ');
      } else if (rawDetail && typeof rawDetail === 'object') {
        detail = rawDetail.message || rawDetail.msg || JSON.stringify(rawDetail);
      }

      if (!e.response) setFormError('Network error: Could not reach the server.');
      else if (status === 422) setFormError(detail || 'Check your input.');
      else if (status === 429) {
        const admissionMsg = rawDetail?.message || rawDetail?.reason || detail;
        setFormError(admissionMsg || 'All rendering slots are busy. Your current video is still being created — please wait for it to finish, then you can start a new one.');
        checkRateLimit();
      } else if (status === 402) {
        // Backend credit enforcement — show credit gate modal
        const match = detail.match(/Required:\s*(\d+).*Available:\s*(\d+)/i);
        if (match) {
          const required = parseInt(match[1], 10);
          const available = parseInt(match[2], 10);
          setUserCredits(available);
          setCreditGate({ required, current: available, shortfall: required - available });
        } else {
          setCreditGate({ required: 21, current: userCredits || 0, shortfall: Math.max(0, 21 - (userCredits || 0)) });
        }
      } else if (status === 401) {
        // Guest free trial already used OR auth needed — save form state and show login gate
        localStorage.setItem('studio_saved_state', JSON.stringify({
          title: title.trim(), storyText: storyText.trim(),
          animStyle, ageGroup, voicePreset,
          remixData: remixData || null, timestamp: Date.now()
        }));
        localStorage.setItem('remix_return_url', '/app/story-video-studio');
        setShowLoginGate(true);
      }
      else if (status === 500) setFormError(detail || 'Server error. Please try again.');
      else setFormError(detail || `Unexpected error (${status || 'network'}).`);
    } finally {
      setSubmitting(false);
      createLockRef.current = false;
    }
  };

  const handleResume = async () => {
    if (!jobId) return;
    try {
      await api.post(`/api/story-engine/resume/${jobId}`);
      setPhase('processing');
      dispatchPostGen({ type: 'RESET' });
      startPolling(jobId);
      toast.info('Resuming from last checkpoint...');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to resume');
    }
  };

  const handleNewVideo = () => {
    clearAllTimeouts();
    setPhase('input');
    setJobId(null);
    setJob(null);
    setTitle('');
    setStoryText('');
    setFormError('');
    setRemixData(null);
    setReuseInfo(null);
    setSoftTimeoutReached(false);
    dispatchPostGen({ type: 'RESET' });
    checkRateLimit();
  };

  const viewJob = async (j) => {
    setJobId(j.job_id);

    // Fetch full status (includes view_mode, characters, cliffhanger)
    const fetchFullJob = async (jid) => {
      try {
        const res = await api.get(`/api/story-engine/status/${jid}`);
        if (res.data.success) return res.data.job;
      } catch { /* fall through */ }
      return null;
    };

    const fullJob = await fetchFullJob(j.job_id);
    const jobData = fullJob || j;
    setJob(jobData);

    // Server-authoritative routing via view_mode
    const viewMode = jobData.view_mode;

    if (viewMode === 'failed_recovery') {
      setPhase('failed_recovery');
      trackRecoveryEvent('failed_job_viewed', j.job_id, jobData.engine_state);
    } else if (viewMode === 'result') {
      setPhase('postgen');
      validateAndResolve(j.job_id, jobData);
    } else {
      // Active job — show progress
      setPhase('processing');
      startPolling(j.job_id);
    }
  };

  // Retry validation
  const retryValidation = useCallback(() => {
    if (jobId) validateAndResolve(jobId, job);
  }, [jobId, job, validateAndResolve]);

  return (
    <div className="vs-page">
      <header className="vs-glass sticky top-0 z-40 border-b border-[var(--vs-border-subtle)]">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link to="/app" className="text-[var(--vs-text-muted)] hover:text-white transition-colors" data-testid="back-to-dashboard">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div className="w-8 h-8 rounded-lg vs-gradient-bg flex items-center justify-center">
              <Film className="w-4 h-4 text-white" />
            </div>
            <span className="font-semibold text-white text-lg" style={{ fontFamily: 'var(--vs-font-heading)' }}>Story Video Studio</span>
          </div>

          {/* Canvas step indicators */}
          <div className="hidden md:flex items-center gap-1">
            {[
              { key: 'prompt', label: 'Prompt', icon: Sparkles, active: phase === 'input' },
              { key: 'scenes', label: 'Scenes', icon: BookOpen, active: phase === 'processing' && (job?.current_stage === 'scenes' || !job) },
              { key: 'images', label: 'Images', icon: Image, active: phase === 'processing' && job?.current_stage === 'images' },
              { key: 'voices', label: 'Voice', icon: Mic, active: phase === 'processing' && job?.current_stage === 'voices' },
              { key: 'result', label: 'Result', icon: Eye, active: phase === 'postgen' || phase === 'failed_recovery' },
            ].map((step, i) => (
              <div key={step.key} className="flex items-center">
                {i > 0 && <div className={`w-6 h-px mx-1 ${step.active || (phase === 'postgen') || (phase === 'failed_recovery') || (phase === 'processing' && i <= ['prompt','scenes','images','voices','result'].indexOf(job?.current_stage || 'scenes')) ? 'bg-[var(--vs-primary-from)]' : 'bg-[var(--vs-border)]'}`} />}
                <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                  step.active ? (phase === 'failed_recovery' && step.key === 'result' ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30' : 'bg-[var(--vs-cta)]/15 text-[var(--vs-text-accent)] border border-[var(--vs-border-glow)]')
                  : (phase === 'postgen' || phase === 'failed_recovery' || (phase === 'processing' && i < ['prompt','scenes','images','voices','result'].indexOf(job?.current_stage || 'scenes') + 1))
                    ? 'text-[var(--vs-success)]'
                    : 'text-[var(--vs-text-muted)]'
                }`} data-testid={`canvas-step-${step.key}`}>
                  <step.icon className="w-3.5 h-3.5" />
                  <span className="hidden lg:inline">{step.label}</span>
                </div>
              </div>
            ))}
          </div>

          {phase !== 'input' && (
            <button onClick={handleNewVideo} className="vs-btn-secondary h-8 px-3 text-xs" data-testid="new-video-header-btn">
              <Sparkles className="w-3.5 h-3.5" /> New
            </button>
          )}
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {showUpsell && <UpsellModal credits={userCredits} onClose={() => setShowUpsell(false)} />}

        {/* ═══ RESUME DRAFT MODAL ═══ */}
        {showResumeDraft && pendingDraft && (
          <div className="fixed inset-0 z-[101] flex items-center justify-center bg-black/70 backdrop-blur-sm" data-testid="resume-draft-modal">
            <div className="bg-[#12121a] border border-white/10 rounded-2xl shadow-2xl max-w-md w-full mx-4 p-6 text-center">
              <div className="w-12 h-12 rounded-xl bg-indigo-500/15 flex items-center justify-center mx-auto mb-4">
                <BookOpen className="w-6 h-6 text-indigo-400" />
              </div>
              <h3 className="text-lg font-bold text-white mb-1">Resume your last draft?</h3>
              <p className="text-sm text-slate-400 mb-2">
                {pendingDraft.title ? `"${pendingDraft.title}"` : 'Untitled draft'}
              </p>
              {pendingDraft.story_text && (
                <p className="text-xs text-slate-500 mb-5 line-clamp-2">
                  {pendingDraft.story_text.slice(0, 120)}{pendingDraft.story_text.length > 120 ? '...' : ''}
                </p>
              )}
              <div className="flex gap-3">
                <button
                  onClick={handleDiscardDraft}
                  className="flex-1 h-10 rounded-xl border border-white/10 text-sm text-slate-300 hover:bg-white/5 transition-colors"
                  data-testid="draft-start-fresh"
                >
                  Start Fresh
                </button>
                <button
                  onClick={handleResumeDraft}
                  className="flex-1 h-10 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-sm font-semibold text-white transition-colors"
                  data-testid="draft-resume"
                >
                  Continue
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ═══ STRICT CREDIT GATE MODAL ═══ */}
        {creditGate && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm" data-testid="credit-gate-modal">
            <div className="bg-[#12121a] border border-white/10 rounded-2xl shadow-2xl max-w-md w-full mx-4 overflow-hidden">
              {/* Header */}
              <div className="px-6 pt-6 pb-4">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center">
                    <Coins className="w-5 h-5 text-amber-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-white" data-testid="credit-gate-title">Not enough credits</h3>
                    <p className="text-xs text-slate-400">You need more credits to generate this Story-to-Video</p>
                  </div>
                </div>

                {/* Credit breakdown */}
                <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-400">Credits required</span>
                    <span className="text-sm font-bold text-white" data-testid="credits-required">{creditGate.required}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-400">Your current credits</span>
                    <span className="text-sm font-bold text-amber-400" data-testid="credits-current">{creditGate.current}</span>
                  </div>
                  <div className="border-t border-white/[0.06] pt-3 flex items-center justify-between">
                    <span className="text-sm font-semibold text-rose-400">Additional credits needed</span>
                    <span className="text-sm font-black text-rose-400" data-testid="credits-shortfall">{creditGate.shortfall}</span>
                  </div>
                </div>

                <p className="text-xs text-slate-500 mt-3 text-center">
                  Buy <strong className="text-white">{creditGate.shortfall}</strong> more credits to generate your video
                </p>
              </div>

              {/* Actions */}
              <div className="px-6 pb-6 space-y-2">
                <button
                  onClick={() => { setCreditGate(null); navigate('/app/profile?tab=billing'); }}
                  className="w-full h-11 rounded-xl bg-gradient-to-r from-violet-600 to-rose-600 text-white font-bold text-sm hover:opacity-90 flex items-center justify-center gap-2"
                  data-testid="credit-gate-buy-btn"
                >
                  <Zap className="w-4 h-4" /> Buy Credits
                </button>
                <button
                  onClick={() => { setCreditGate(null); navigate('/pricing'); }}
                  className="w-full h-11 rounded-xl border border-white/10 text-slate-300 font-medium text-sm hover:bg-white/[0.03] flex items-center justify-center gap-2"
                  data-testid="credit-gate-plans-btn"
                >
                  View Plans
                </button>
                <button
                  onClick={() => setCreditGate(null)}
                  className="w-full h-9 text-slate-500 hover:text-slate-300 text-xs font-medium"
                  data-testid="credit-gate-cancel-btn"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {remixData && phase === 'input' && (
          <div className="mb-6 bg-pink-500/10 border border-pink-500/30 rounded-xl p-4 flex items-center gap-3" data-testid="remix-banner">
            <Remix className="w-5 h-5 text-pink-400" />
            <span className="text-pink-200 text-sm">Remixing: <strong>{remixData.title}</strong> — edit the story and make it your own!</span>
          </div>
        )}

        {showWelcome && phase === 'input' && (
          <div className="mb-8 bg-indigo-500/10 border border-indigo-500/30 rounded-2xl p-6 text-center" data-testid="welcome-overlay">
            <Sparkles className="w-8 h-8 text-indigo-400 mx-auto mb-3" />
            <h2 className="text-xl font-bold text-white mb-2">Let's turn your story into a cinematic video</h2>
            <p className="text-slate-400 text-sm max-w-md mx-auto mb-4">Your story is pre-filled below. Add a title, pick a style, and hit Generate.</p>
            <Button onClick={() => setShowWelcome(false)} variant="ghost" className="text-indigo-400 hover:text-indigo-300 text-sm">Got it</Button>
          </div>
        )}

        {/* Challenge banner in Studio */}
        {challengeId && challengeTitle && phase === 'input' && (
          <div className="mb-4 px-4 py-3 rounded-xl border border-emerald-500/20 bg-emerald-500/[0.06] flex items-center gap-3" data-testid="studio-challenge-banner">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/15 flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="flex-1 min-w-0">
              <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">Challenge Entry</span>
              <p className="text-xs text-zinc-300 truncate">{challengeTitle}</p>
            </div>
          </div>
        )}

        {phase === 'input' && <InputPhase
          options={options} title={title} setTitle={setTitle}
          storyText={storyText} setStoryText={setStoryText}
          animStyle={animStyle} setAnimStyle={setAnimStyle}
          ageGroup={ageGroup} setAgeGroup={setAgeGroup}
          voicePreset={voicePreset} setVoicePreset={setVoicePreset}
          qualityMode={qualityMode} setQualityMode={setQualityMode}
          onGenerate={handleGenerate} submitting={submitting}
          userJobs={userJobs} onViewJob={viewJob}
          rateLimitStatus={rateLimitStatus} formError={formError}
          showRemixBanner={showRemixBanner} remixSourceTool={remixSourceTool}
          remixSourceTitle={remixSourceTitle} onDismissRemix={() => setShowRemixBanner(false)}
          userCredits={userCredits}
          showLoginGate={showLoginGate}
          seriesContext={seriesContext}
          isFreshSession={!!location.state?.freshSession}
        />}

        {phase === 'processing' && (
          <ProgressiveGeneration
            jobId={jobId}
            wsRef={wsRef}
            initialProgress={job?.progress || 0}
            initialStage={job?.current_stage || 'scenes'}
            reuseInfo={reuseInfo}
            onComplete={(completedJob) => {
              setJob(completedJob);
              setPhase('postgen');
              validateAndResolve(jobId, completedJob);
            }}
          />
        )}

        {phase === 'postgen' && (
          <PostGenPhase
            postGen={postGen}
            job={job}
            jobId={jobId}
            onNew={handleNewVideo}
            onResume={handleResume}
            onRetryValidation={retryValidation}
            storyText={storyText}
            animStyle={animStyle}
          />
        )}

        {phase === 'failed_recovery' && (
          <FailedRecoveryScreen
            job={job}
            jobId={jobId}
            onNew={handleNewVideo}
            onRetryStarted={(data) => {
              // After successful retry, switch to processing phase
              setPhase('processing');
              startPolling(jobId);
            }}
          />
        )}
      </main>
    </div>
  );
}

export default function StoryVideoPipeline() {
  return (
    <StudioErrorBoundary>
      <StoryVideoPipelineInner />
    </StudioErrorBoundary>
  );
}


// ─── RECENT DRAFTS PANEL ──────────────────────────────────────────────────────
function RecentDraftsPanel({ onViewJob }) {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    api.get('/api/drafts/recent').then(res => {
      if (res.data?.items?.length) setItems(res.data.items);
    }).catch(() => {});
  }, []);

  if (!items.length) return null;

  return (
    <div className="space-y-2" data-testid="recent-drafts-panel">
      <button onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 text-xs text-slate-500 hover:text-slate-300 transition-colors w-full"
        data-testid="recent-drafts-toggle"
      >
        <ChevronDown className={`w-3 h-3 transition-transform ${expanded ? 'rotate-0' : '-rotate-90'}`} />
        <span className="uppercase tracking-wider font-medium">Your unfinished stories are waiting</span>
        <span className="text-slate-600">({items.length})</span>
      </button>
      {expanded && (
        <div className="space-y-1.5 pl-1">
          {items.map((item, i) => (
            <button key={item.project_id || `draft-${i}`}
              onClick={() => {
                if (item.type === 'project' && item.project_id) {
                  navigate(`/app/story-video-studio?projectId=${item.project_id}`);
                }
              }}
              disabled={item.type === 'draft'}
              className="w-full text-left p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04] hover:border-white/[0.08] transition-all flex items-center justify-between gap-2 disabled:opacity-50"
              data-testid={`recent-draft-${i}`}
            >
              <div className="min-w-0">
                <p className="text-xs font-medium text-white truncate">{item.title}</p>
                {item.last_edited && (
                  <p className="text-[10px] text-slate-500 mt-0.5">
                    {new Date(item.last_edited).toLocaleDateString()}
                  </p>
                )}
              </div>
              <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded-full flex-shrink-0 ${
                item.status === 'draft' ? 'bg-amber-500/10 text-amber-400' :
                item.status === 'processing' ? 'bg-blue-500/10 text-blue-400' :
                'bg-emerald-500/10 text-emerald-400'
              }`}>
                {item.status === 'draft' ? 'Draft' : item.status === 'processing' ? 'Rendering' : 'Ready'}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── INPUT PHASE ──────────────────────────────────────────────────────────────
function InputPhase({ options, title, setTitle, storyText, setStoryText,
  animStyle, setAnimStyle, ageGroup, setAgeGroup, voicePreset, setVoicePreset,
  qualityMode, setQualityMode,
  onGenerate, submitting, userJobs, onViewJob, rateLimitStatus, formError,
  showRemixBanner, remixSourceTool, remixSourceTitle, onDismissRemix, userCredits,
  showLoginGate, seriesContext, isFreshSession }) {

  const styles = options?.animation_styles || [];
  const ages = options?.age_groups || [];
  const voices = options?.voice_presets || [];
  const activeJobs = userJobs.filter(j => {
    if (!['QUEUED', 'PROCESSING'].includes(j.status)) return false;
    // Don't show stale jobs (>15 min old) — they're likely stuck/crashed
    const createdAt = new Date(j.created_at || j.createdAt || 0).getTime();
    return (Date.now() - createdAt) < 15 * 60 * 1000;
  });
  const failedRetryableJobs = userJobs.filter(j => {
    if (j.status !== 'FAILED') return false;
    // Show retryable failed jobs that are recent (< 1 hour)
    const retryInfo = j.retry_info;
    if (!retryInfo?.can_retry) return false;
    const createdAt = new Date(j.created_at || j.createdAt || 0).getTime();
    return (Date.now() - createdAt) < 60 * 60 * 1000;
  });
  const recentJobs = userJobs.filter(j => ['COMPLETED', 'PARTIAL'].includes(j.status)).slice(0, 3);
  const canCreate = rateLimitStatus?.can_create !== false;

  return (
    <div className="space-y-8 vs-fade-up-1" data-testid="input-phase">
      {activeJobs.length > 0 && (
        <div className="vs-panel p-4 flex items-center justify-between border-[var(--vs-border-glow)]" data-testid="active-job-banner">
          <div className="flex items-center gap-3">
            <Loader2 className="w-5 h-5 text-[var(--vs-text-accent)] animate-spin" />
            <span className="text-[var(--vs-text-accent)]">You have {activeJobs.length} video{activeJobs.length > 1 ? 's' : ''} in progress</span>
          </div>
          <button onClick={() => onViewJob(activeJobs[0])} className="vs-btn-primary h-8 px-4 text-xs" data-testid="view-progress-btn">
            <Eye className="w-4 h-4 mr-1" /> View Progress
          </button>
        </div>
      )}

      {rateLimitStatus && !rateLimitStatus.can_create && (
        <div className="vs-panel p-5 border-[var(--vs-border-glow)]" data-testid="rate-limit-warning">
          <div className="flex items-start gap-3 mb-3">
            <Clock className="w-5 h-5 text-[var(--vs-text-accent)] flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-white font-medium text-sm">All rendering slots are busy ({rateLimitStatus.concurrent}/{rateLimitStatus.max_concurrent})</p>
              <p className="text-[var(--vs-text-secondary)] text-xs mt-1">Your current video is still being created. Once it finishes, you'll be able to start a new one right away.</p>
            </div>
          </div>
          {rateLimitStatus.active_jobs?.length > 0 && (
            <div className="space-y-2 mt-3 pt-3 border-t border-white/[0.06]">
              <p className="text-[var(--vs-text-muted)] text-xs font-semibold uppercase tracking-wider">Your Videos In Progress</p>
              {rateLimitStatus.active_jobs.map((job) => (
                <div key={job.job_id} className="flex items-center justify-between gap-3 bg-white/[0.03] rounded-xl px-3 py-2.5">
                  <div className="flex items-center gap-2 min-w-0">
                    <Loader2 className="w-4 h-4 text-[var(--vs-text-accent)] animate-spin flex-shrink-0" />
                    <span className="text-white text-sm truncate">{job.title || 'Untitled Video'}</span>
                    <span className="text-[var(--vs-text-muted)] text-[10px] flex-shrink-0">{job.state_label || 'Processing'}</span>
                  </div>
                  <button
                    onClick={() => onViewJob(job)}
                    className="vs-btn-primary h-7 px-3 text-[11px] flex-shrink-0"
                    data-testid={`view-active-job-${job.job_id}`}
                  >
                    <Eye className="w-3 h-3 mr-1" /> View Progress
                  </button>
                </div>
              ))}
              <p className="text-[var(--vs-text-muted)] text-[10px] mt-2">Tip: You can view your video's progress or wait here — the slot will free up automatically once it's done.</p>
            </div>
          )}
          {/* Failed jobs recovery section */}
          {rateLimitStatus.failed_jobs?.length > 0 && (
            <div className="space-y-2 mt-3 pt-3 border-t border-amber-500/10">
              <p className="text-amber-400/70 text-xs font-semibold uppercase tracking-wider">Needs Attention</p>
              {rateLimitStatus.failed_jobs.map((fj) => (
                <div key={fj.job_id} className="flex items-center justify-between gap-3 bg-amber-500/[0.03] rounded-xl px-3 py-2.5 border border-amber-500/10">
                  <div className="flex items-center gap-2 min-w-0">
                    <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0" />
                    <span className="text-white text-sm truncate">{fj.title || 'Untitled Video'}</span>
                    <span className="text-amber-400/60 text-[10px] flex-shrink-0">{fj.state_label || 'Needs attention'}</span>
                  </div>
                  <div className="flex gap-1.5 flex-shrink-0">
                    <RetryButton jobId={fj.job_id} onRetryStarted={() => { window.location.reload(); }} />
                    <button
                      onClick={() => window.location.href = `/app/my-space?projectId=${fj.job_id}`}
                      className="h-7 px-2 text-[11px] rounded-lg border border-white/10 text-zinc-400 hover:text-white hover:bg-white/5 transition-colors"
                      data-testid={`view-failed-${fj.job_id}`}
                    >
                      Details
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Retryable failed jobs — show with retry option */}
      {failedRetryableJobs.length > 0 && (
        <div className="vs-panel p-4 border-amber-500/30" data-testid="retryable-failed-banner">
          <div className="flex items-start gap-3 mb-2">
            <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-white font-medium text-sm">A recent video had an issue — you can retry it</p>
            </div>
          </div>
          {failedRetryableJobs.map((fj) => (
            <div key={fj.job_id} className="flex items-center justify-between gap-3 bg-white/[0.03] rounded-xl px-3 py-2.5 mt-2">
              <div className="flex items-center gap-2 min-w-0">
                <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0" />
                <span className="text-white text-sm truncate">{fj.title || 'Untitled Video'}</span>
                {fj.credits_refunded > 0 && <span className="text-emerald-400 text-[10px] flex-shrink-0">Credits refunded</span>}
              </div>
              <RetryButton jobId={fj.job_id} onRetryStarted={() => { window.location.reload(); }} />
            </div>
          ))}
        </div>
      )}


      {showRemixBanner && <RemixBanner sourceTool={remixSourceTool} sourceTitle={remixSourceTitle} onDismiss={onDismissRemix} />}

      {/* Series Context Banner */}
      {seriesContext && (
        <div className="vs-panel p-4 border-violet-500/30 bg-violet-500/5" data-testid="series-context-banner">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-violet-500/20 flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-4 h-4 text-violet-400" />
            </div>
            <div className="min-w-0">
              <p className="text-white text-sm font-semibold truncate">{seriesContext.series_title}</p>
              <p className="text-violet-400/70 text-xs">Creating Episode {seriesContext.episode_number} — story context pre-loaded from your series</p>
            </div>
          </div>
        </div>
      )}

      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <div>
            <h1 className="vs-h1 mb-2">{seriesContext ? `Episode ${seriesContext.episode_number}` : 'Create a Story Video'}</h1>
            <p className="text-[var(--vs-text-secondary)]" style={{ fontFamily: 'var(--vs-font-body)' }}>
              {seriesContext
                ? `Continue your "${seriesContext.series_title}" series. The story prompt has been pre-loaded — customize it or generate directly.`
                : 'Enter your story and we\'ll create an animated video with AI-generated images and voiceover.'
              }
            </p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-[var(--vs-text-secondary)] mb-1 block">Title <span className="text-[var(--vs-error)]">*</span></label>
              <Input value={title} onChange={e => setTitle(e.target.value)} placeholder="My Amazing Story..."
                className="bg-[var(--vs-bg-panel)] border-[var(--vs-border)] text-white focus:border-[var(--vs-primary-from)] h-11" data-testid="title-input" maxLength={100} />
              {title.length > 0 && title.trim().length < 3 && <p className="text-xs text-amber-400 mt-1">Title needs at least 3 characters</p>}
            </div>

            <div>
              <label className="text-sm font-medium text-[var(--vs-text-secondary)] mb-1 block">Story Text <span className="text-[var(--vs-error)]">*</span></label>
              <Textarea value={storyText} onChange={e => {
                  setStoryText(e.target.value);
                  // Canonical activation funnel — first keystroke
                  if (!typingStartedRef.current && e.target.value.length > 0) {
                    typingStartedRef.current = true;
                    try {
                      trackFunnel('prompt_started_typing', {
                        source_page: 'studio',
                        meta: { source: isFreshSession ? 'fresh' : 'return' },
                      });
                    } catch (_) { /* noop */ }
                  }
                }}
                onFocus={() => {
                  try {
                    trackFunnel('prompt_input_focused', {
                      source_page: 'studio',
                      meta: { has_text: storyText.length > 0 },
                    });
                  } catch (_) { /* noop */ }
                }}
                placeholder="Write your story here... (minimum 50 characters)" rows={8}
                className="bg-[var(--vs-bg-panel)] border-[var(--vs-border)] text-white resize-none focus:border-[var(--vs-primary-from)]" data-testid="story-textarea" />
              <div className="flex justify-between mt-1">
                <p className={`text-xs ${storyText.trim().length < 50 && storyText.length > 0 ? 'text-amber-400' : 'text-[var(--vs-text-muted)]'}`}>
                  {storyText.length} / 10,000 characters {storyText.length > 0 && storyText.trim().length < 50 ? `(need ${50 - storyText.trim().length} more)` : '(min 50)'}
                </p>
              </div>

              {/* Guided Start V2 — Vibe picker + category ideas */}
              {isFreshSession && !storyText.trim() && (FEATURES.guidedStartV2 ? (
                <div className="mt-3 space-y-2" data-testid="guided-start">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-xs text-slate-500">What do you want to create?</span>
                    {[
                      { id: 'kids', label: 'Bedtime Magic' },
                      { id: 'drama', label: 'Emotional Story' },
                      { id: 'thriller', label: 'Mind-Blowing Twist' },
                      { id: 'viral', label: '1M Views Hook' },
                    ].map(v => (
                      <button key={v.id} type="button" data-testid={`vibe-${v.id}`}
                        onClick={async () => {
                          try {
                            const res = await api.get(`/api/drafts/idea?vibe=${v.id}`);
                            if (res.data?.idea) { setStoryText(res.data.idea); toast.success(`${v.label} idea loaded!`); }
                          } catch { toast.error('Could not generate idea'); }
                        }}
                        className="px-2.5 py-1 text-[11px] rounded-full border border-white/10 text-slate-300 hover:bg-white/5 hover:text-white transition-colors"
                      >{v.label}</button>
                    ))}
                  </div>
                  <div className="flex items-center gap-2">
                    <button type="button" data-testid="generate-idea-btn"
                      onClick={async () => {
                        try {
                          const res = await api.get('/api/drafts/idea');
                          if (res.data?.idea) { setStoryText(res.data.idea); toast.success('Idea generated!'); }
                        } catch { toast.error('Could not generate idea'); }
                      }}
                      className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors flex items-center gap-1"
                    ><Sparkles className="w-3 h-3" /> Random Idea</button>
                    <span className="text-slate-600 text-xs">or</span>
                    <button type="button" data-testid="use-sample-btn"
                      onClick={() => {
                        setTitle('The Secret Garden on Mars');
                        setStoryText('On a dusty red planet where nothing grows, a small girl named Zara discovers a hidden cave filled with glowing plants. Each plant whispers a story from Earth — tales of forests, rivers, and animals she has never seen. When the colony leaders want to seal the cave, Zara must convince them that these stories are worth saving, because without stories, what is a civilization?');
                        toast.success('Sample story loaded — feel free to edit!');
                      }}
                      className="text-xs text-slate-400 hover:text-slate-300 transition-colors flex items-center gap-1"
                    ><BookOpen className="w-3 h-3" /> Use Sample</button>
                  </div>
                </div>
              ) : isFreshSession && !storyText.trim() && (
                <div className="flex items-center gap-2 mt-2" data-testid="guided-start">
                  <button type="button" data-testid="generate-idea-btn"
                    onClick={async () => {
                      try { const res = await api.get('/api/drafts/idea'); if (res.data?.idea) { setStoryText(res.data.idea); toast.success('Idea generated!'); } } catch {}
                    }}
                    className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors flex items-center gap-1"
                  ><Sparkles className="w-3 h-3" /> Generate Idea</button>
                </div>
              ))}
            </div>
          </div>

          {/* Animation Style with Preview Thumbnails */}
          <div>
            <label className="text-sm font-medium text-slate-200 mb-2 block">Animation Style</label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2" data-testid="style-grid">
              {styles.map(s => {
                const previewGradients = {
                  cartoon_2d: 'from-yellow-400 to-orange-500',
                  anime_style: 'from-indigo-500 to-violet-400',
                  '3d_animation': 'from-sky-400 to-cyan-500',
                  watercolor: 'from-rose-300 to-pink-400',
                  comic_book: 'from-red-500 to-orange-400',
                  claymation: 'from-amber-500 to-yellow-400',
                  pixel_art: 'from-green-400 to-emerald-500',
                  oil_painting: 'from-amber-600 to-rose-500',
                  sketch: 'from-slate-400 to-slate-600',
                  neon: 'from-cyan-400 to-purple-500',
                };
                const grad = previewGradients[s.id] || 'from-slate-500 to-slate-700';
                return (
                  <button key={s.id} onClick={() => setAnimStyle(s.id)}
                    className={`rounded-[var(--vs-card-radius)] border text-left transition-all overflow-hidden ${animStyle === s.id
                      ? 'border-[var(--vs-primary-from)] ring-2 ring-[var(--vs-primary-from)]/50'
                      : 'border-slate-600 hover:border-slate-400 cursor-pointer'}`}
                    data-testid={`style-${s.id}`}>
                    <div className={`h-16 bg-gradient-to-br ${grad} flex items-center justify-center`}>
                      <span className="text-white/80 text-xs font-bold drop-shadow">{s.name}</span>
                    </div>
                    <div className={`px-3 py-2 ${animStyle === s.id ? 'bg-[var(--vs-cta)]/15' : 'bg-slate-800/60'}`}>
                      <span className="text-xs font-medium text-white">{s.name}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Age + Voice */}
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-slate-200 mb-2 block">Target Age</label>
              <div className="space-y-1">
                {ages.map(a => (
                  <button key={a.id} onClick={() => setAgeGroup(a.id)}
                    className={`w-full p-2 rounded-[var(--vs-btn-radius)] border text-left text-sm transition-all ${ageGroup === a.id
                      ? 'border-[var(--vs-primary-from)] bg-[var(--vs-cta)]/15 text-white ring-1 ring-[var(--vs-primary-from)]/50'
                      : 'border-slate-600 bg-slate-800/60 text-slate-200 hover:border-slate-400 hover:bg-slate-700/50 cursor-pointer'}`}
                    data-testid={`age-${a.id}`}>{a.name}</button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-200 mb-2 block">Narrator Voice</label>
              <div className="space-y-1">
                {voices.map(v => (
                  <button key={v.id} onClick={() => setVoicePreset(v.id)}
                    className={`w-full p-2 rounded-[var(--vs-btn-radius)] border text-left text-sm transition-all ${voicePreset === v.id
                      ? 'border-[var(--vs-primary-from)] bg-[var(--vs-cta)]/15 text-white ring-1 ring-[var(--vs-primary-from)]/50'
                      : 'border-slate-600 bg-slate-800/60 text-slate-200 hover:border-slate-400 hover:bg-slate-700/50 cursor-pointer'}`}
                    data-testid={`voice-${v.id}`}>{v.name}</button>
                ))}
              </div>
            </div>
          </div>

          {/* ─── QUALITY MODE ─── */}
          <div data-testid="quality-mode-section">
            <label className="text-sm font-medium text-slate-200 mb-2 block">Generation Quality</label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { id: 'fast', label: 'Fast', desc: '~1-2 min', icon: '⚡' },
                { id: 'balanced', label: 'Balanced', desc: '~2-4 min', icon: '⚖️' },
                { id: 'high_quality', label: 'High Quality', desc: '~4-8 min', icon: '✨' },
              ].map(mode => (
                <button
                  key={mode.id}
                  onClick={() => setQualityMode(mode.id)}
                  className={`p-3 rounded-xl border text-center transition-all ${
                    qualityMode === mode.id
                      ? 'border-purple-500/50 bg-purple-500/10 ring-1 ring-purple-500/30'
                      : 'border-slate-700/50 bg-slate-800/30 hover:border-slate-600'
                  }`}
                  data-testid={`quality-mode-${mode.id}`}
                >
                  <span className="text-lg block mb-1">{mode.icon}</span>
                  <span className={`text-xs font-semibold block ${qualityMode === mode.id ? 'text-purple-300' : 'text-slate-300'}`}>
                    {mode.label}
                  </span>
                  <span className="text-[10px] text-slate-500 block mt-0.5">{mode.desc}</span>
                </button>
              ))}
            </div>
          </div>

          {/* ─── CREDIT INFO ─── */}
          {userCredits !== null && userCredits < 21 && (
            <div className="vs-panel p-4 border-amber-500/30 rounded-xl" data-testid="credit-warning">
              <div className="flex items-start gap-3">
                <Coins className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-bold text-amber-200">Low credits — you have {userCredits}</p>
                  <p className="text-xs text-slate-400 mt-1">Story-to-Video generation requires 21 credits. You'll need {Math.max(0, 21 - userCredits)} more.</p>
                </div>
              </div>
            </div>
          )}

          {/* Form error — shown only for non-auth errors */}
          {formError && !showLoginGate && (
            <div className="vs-panel p-4 flex items-start gap-3 border-[var(--vs-error)]/30" data-testid="form-error">
              <AlertCircle className="w-5 h-5 text-[var(--vs-error)] flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-red-300 text-sm">{formError}</p>
                {formError.includes('session') && <button onClick={() => window.location.href = '/login'} className="text-xs text-[var(--vs-text-accent)] underline mt-1">Go to Login</button>}
                {formError.includes('credit') && <button onClick={() => window.location.href = '/app/billing'} className="text-xs text-[var(--vs-text-accent)] underline mt-1">Get More Credits</button>}
                {(formError.includes('slots') || formError.includes('rendering') || formError.includes('still being created')) && (
                  <p className="text-xs text-slate-400 mt-2">Your video is actively being processed. Check back shortly or view its progress above.</p>
                )}
              </div>
            </div>
          )}

          {/* ─── LOGIN GATE — gentle prompt, not an error ─── */}
          {showLoginGate && (
            <div className="rounded-2xl border border-indigo-500/30 bg-gradient-to-br from-indigo-500/10 to-purple-500/10 p-6 text-center space-y-4" data-testid="login-gate">
              <div className="w-14 h-14 mx-auto rounded-full bg-indigo-500/20 flex items-center justify-center">
                <Sparkles className="w-7 h-7 text-indigo-400" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Log in to generate your story</h3>
                <p className="text-sm text-slate-400 mt-1">Your story is saved. Create a free account to bring it to life.</p>
              </div>
              <div className="flex gap-3 justify-center">
                <button
                  onClick={() => window.location.href = '/login?redirect=/app/story-video-studio'}
                  className="h-11 px-8 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-500 text-white font-bold text-sm hover:opacity-90 transition-opacity flex items-center gap-2"
                  data-testid="login-gate-login-btn"
                >
                  <ArrowRight className="w-4 h-4" /> Log In
                </button>
                <button
                  onClick={() => window.location.href = '/signup'}
                  className="h-11 px-8 rounded-xl border border-slate-600 text-white font-bold text-sm hover:bg-white/5 transition-colors flex items-center gap-2"
                  data-testid="login-gate-signup-btn"
                >
                  Sign Up Free
                </button>
              </div>
              <p className="text-[10px] text-slate-500">50 free credits on signup</p>
            </div>
          )}

          {/* Generate — hidden when login gate is shown */}
          {!showLoginGate && (
            <button onClick={onGenerate} disabled={submitting}
              className={`w-full h-14 text-lg font-semibold rounded-[var(--vs-btn-radius)] flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed ${
                !canCreate ? 'bg-white/[0.06] hover:bg-white/[0.08] text-white/60 border border-white/[0.06]' : 'vs-btn-primary'
              }`}
              data-testid="generate-btn">
              {submitting ? <><Loader2 className="w-5 h-5 animate-spin" /> Creating Job...</>
                : !canCreate ? <><Clock className="w-5 h-5" /> Slots Busy — Wait or Cancel</>
                : <><Wand2 className="w-5 h-5" /> Generate Video</>}
            </button>
          )}

          {rateLimitStatus && !rateLimitStatus.exempt && (
            <p className="text-xs text-[var(--vs-text-muted)] text-center">
              {rateLimitStatus.concurrent > 0
                ? `${rateLimitStatus.concurrent} video${rateLimitStatus.concurrent > 1 ? 's' : ''} rendering`
                : `${rateLimitStatus.recent_count} of ${rateLimitStatus.max_per_hour} videos this hour`}
            </p>
          )}
        </div>

        {/* Sidebar — hidden in fresh session to keep creation focus */}
        {!isFreshSession && (
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-[var(--vs-text-muted)] uppercase tracking-wide">Recent Videos</h3>
          {recentJobs.length === 0 && <p className="text-sm text-[var(--vs-text-muted)]">No videos yet. Create your first!</p>}
          {recentJobs.map(j => (
            <button key={j.job_id} onClick={() => onViewJob(j)}
              className="w-full vs-card text-left hover:border-[var(--vs-border-glow)] transition-all"
              data-testid={`recent-job-${j.job_id}`}>
              <p className="text-sm font-medium text-white truncate">{j.title}</p>
              <p className="text-xs text-[var(--vs-text-muted)] mt-1">{new Date(j.created_at).toLocaleDateString()}</p>
            </button>
          ))}
        </div>
        )}

        {/* Recent Drafts Panel — appears in fresh session after typing 20+ chars */}
        {FEATURES.recentDraftsPanel && isFreshSession && storyText.trim().length >= 20 && (
          <RecentDraftsPanel onViewJob={onViewJob} />
        )}
      </div>
    </div>
  );
}

// ─── ANIMATION STYLE SWATCHES FOR REMIX ───────────────────────────────────────
const ANIM_STYLES = [
  { id: 'cartoon_2d', name: '2D Cartoon', gradient: 'from-yellow-400 to-orange-500' },
  { id: 'anime_style', name: 'Anime', gradient: 'from-indigo-500 to-violet-400' },
  { id: '3d_pixar', name: '3D Animation', gradient: 'from-sky-400 to-cyan-500' },
  { id: 'watercolor', name: 'Watercolor', gradient: 'from-rose-300 to-pink-400' },
  { id: 'comic_book', name: 'Comic Book', gradient: 'from-red-500 to-orange-400' },
  { id: 'claymation', name: 'Claymation', gradient: 'from-amber-500 to-yellow-400' },
];

// ─── CONTINUE DIRECTIONS ──────────────────────────────────────────────────────
const CONTINUE_DIRECTIONS = [
  { id: 'next', label: 'Continue the Story', desc: 'Pick up right where it left off', modifier: 'Continue this story seamlessly from where it ended. Keep the same characters, tone, and world.', icon: Play, color: 'border-blue-500/30 text-blue-400 hover:bg-blue-500/10' },
  { id: 'twist', label: 'Add a Plot Twist', desc: 'Surprise turn nobody expects', modifier: 'Add an unexpected plot twist that changes the direction of the story dramatically.', icon: Sparkles, color: 'border-amber-500/30 text-amber-400 hover:bg-amber-500/10' },
  { id: 'escalate', label: 'Raise the Stakes', desc: 'Bigger conflict, higher tension', modifier: 'Escalate the conflict dramatically. The hero faces a much bigger challenge than before.', icon: AlertCircle, color: 'border-red-500/30 text-red-400 hover:bg-red-500/10' },
  { id: 'episode', label: 'New Episode', desc: 'Fresh chapter, same universe', modifier: 'Create a brand new episode in the same universe with the same characters, but a completely new adventure.', icon: Film, color: 'border-purple-500/30 text-purple-400 hover:bg-purple-500/10' },
  { id: 'custom', label: 'Your Direction', desc: 'Write your own next chapter', modifier: '', icon: BookOpen, color: 'border-indigo-500/30 text-indigo-400 hover:bg-indigo-500/10' },
];

// ─── RETRY & CANCEL BUTTONS ─────────────────────────────────────────────────
function RetryButton({ jobId, onRetryStarted }) {
  const [retrying, setRetrying] = useState(false);
  const handleRetry = async () => {
    setRetrying(true);
    try {
      const res = await api.post(`/api/story-engine/retry/${jobId}`);
      if (res.data?.success) {
        toast.success(`Retrying from ${res.data.retrying_from || 'last failed stage'}...`);
        onRetryStarted?.(res.data);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Retry failed');
    } finally {
      setRetrying(false);
    }
  };
  return (
    <Button onClick={handleRetry} disabled={retrying} className="bg-purple-600 hover:bg-purple-700" data-testid="retry-failed-stage-btn">
      {retrying ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RotateCcw className="w-4 h-4 mr-2" />}
      {retrying ? 'Retrying...' : 'Retry Failed Stage'}
    </Button>
  );
}

function CancelButton({ jobId, onCancelled }) {
  const [cancelling, setCancelling] = useState(false);
  const handleCancel = async () => {
    setCancelling(true);
    try {
      const res = await api.post(`/api/story-engine/cancel/${jobId}`);
      if (res.data?.success) {
        toast.success('Job cancelled. Credits refunded.');
        onCancelled?.(res.data);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Cancel failed');
    } finally {
      setCancelling(false);
    }
  };
  return (
    <Button onClick={handleCancel} disabled={cancelling} variant="outline" className="border-red-500/30 text-red-400 hover:bg-red-500/10" data-testid="cancel-job-btn">
      {cancelling ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <XCircle className="w-4 h-4 mr-2" />}
      Cancel
    </Button>
  );
}



// ─── FAILED RECOVERY SCREEN ─────────────────────────────────────────────────
// Dedicated screen for failed jobs. Never shows Result page layout.
// Renders dynamic failure-specific messaging. Retry preserves all inputs.
function FailedRecoveryScreen({ job, jobId, onNew, onRetryStarted }) {
  const navigate = useNavigate();
  const [deleting, setDeleting] = useState(false);
  const [retrying, setRetrying] = useState(false);

  const engineState = job?.engine_state || job?.status || 'FAILED';
  const failDetail = getFailureLabel(engineState, job?.failure_detail);
  const canRetry = job?.retry_info?.can_retry === true;
  const creditsRefunded = job?.credits_refunded || 0;
  const displayTitle = job?.title || 'Untitled Video';
  const createdAt = job?.created_at ? new Date(job.created_at).toLocaleString() : '';

  const handleRetry = async () => {
    setRetrying(true);
    trackRecoveryEvent('retry_clicked', jobId, engineState);
    try {
      const res = await api.post(`/api/story-engine/retry/${jobId}`);
      if (res.data?.success) {
        toast.success('Retrying your video...');
        onRetryStarted?.(res.data);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Retry failed. Please try again.');
    } finally {
      setRetrying(false);
    }
  };

  const handleEditRetry = () => {
    trackRecoveryEvent('edit_retry_clicked', jobId, engineState);
    localStorage.setItem('remix_video', JSON.stringify({
      parent_video_id: jobId,
      title: job?.title || '',
      story_text: job?.story_text || '',
      animation_style: job?.animation_style || 'cartoon_2d',
      age_group: job?.age_group || 'kids_5_8',
      voice_preset: job?.voice_preset || 'narrator_warm',
    }));
    navigate('/app/story-video-studio?remix=edit-retry');
    toast.info('Edit your story and try again');
  };

  const handleDelete = async () => {
    if (!window.confirm('Delete this project? This cannot be undone.')) return;
    setDeleting(true);
    trackRecoveryEvent('delete_failed_project', jobId, engineState);
    try {
      await api.delete(`/api/story-engine/jobs/${jobId}`);
      toast.success('Project deleted');
      navigate('/app/my-space', { replace: true });
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not delete');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6 vs-fade-up-1" data-testid="failed-recovery-screen">
      {/* Status Header */}
      <div className="rounded-2xl border border-amber-500/30 bg-amber-500/[0.06] p-6" data-testid="recovery-status-header">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-amber-500/15 flex items-center justify-center flex-shrink-0">
            <ShieldAlert className="w-6 h-6 text-amber-400" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-xl font-bold text-white mb-1" data-testid="recovery-title">This video needs attention</h2>
            <p className="text-sm text-amber-300/90 leading-relaxed" data-testid="recovery-failure-title">{failDetail.title}</p>
          </div>
        </div>
      </div>

      {/* Project Info */}
      <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white truncate" data-testid="recovery-project-title">{displayTitle}</h3>
          {job?.animation_style && (
            <span className="text-[10px] font-medium text-zinc-500 bg-zinc-800 px-2 py-0.5 rounded-full" data-testid="recovery-style-badge">
              {job.animation_style.replace(/_/g, ' ')}
            </span>
          )}
        </div>
        {createdAt && <p className="text-xs text-zinc-500">Created: {createdAt}</p>}

        <div className="bg-amber-500/[0.04] border border-amber-500/10 rounded-lg p-3.5">
          <p className="text-xs font-semibold text-amber-400/80 uppercase tracking-wider mb-1">What happened</p>
          <p className="text-sm text-zinc-300 leading-relaxed" data-testid="recovery-suggestion">{failDetail.suggestion}</p>
        </div>

        {creditsRefunded > 0 && (
          <div className="flex items-center gap-2 bg-emerald-500/[0.06] border border-emerald-500/15 rounded-lg px-3.5 py-2.5" data-testid="recovery-credits-refunded">
            <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <span className="text-sm text-emerald-300">{creditsRefunded} credits refunded to your account</span>
          </div>
        )}

        <div className="flex items-center gap-2 bg-white/[0.02] rounded-lg px-3.5 py-2.5">
          <Sparkles className="w-4 h-4 text-indigo-400 flex-shrink-0" />
          <span className="text-xs text-zinc-400">Your story and settings are preserved. Retry keeps everything as-is.</span>
        </div>
      </div>

      {/* Recovery Actions */}
      <div className="space-y-3" data-testid="recovery-actions">
        {canRetry && (
          <button
            onClick={handleRetry}
            disabled={retrying}
            className="w-full group relative overflow-hidden rounded-xl p-4 text-left transition-all hover:scale-[1.005] active:scale-[0.995] disabled:opacity-60"
            data-testid="recovery-retry-btn"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-violet-600 to-indigo-600 opacity-90 group-hover:opacity-100 transition-opacity" />
            <div className="relative z-10 flex items-center gap-4">
              <div className="w-11 h-11 rounded-lg bg-white/10 flex items-center justify-center flex-shrink-0">
                {retrying ? <Loader2 className="w-5 h-5 text-white animate-spin" /> : <RefreshCw className="w-5 h-5 text-white" />}
              </div>
              <div className="flex-1">
                <span className="text-base font-bold text-white block">{retrying ? 'Retrying...' : 'Retry Generation'}</span>
                <span className="text-xs text-white/60">Pick up from {failDetail.stageLabel || 'where it stopped'} — your story is preserved</span>
              </div>
            </div>
          </button>
        )}

        <button
          onClick={handleEditRetry}
          className="w-full rounded-xl border border-white/10 bg-white/[0.03] p-4 text-left hover:bg-white/[0.06] transition-all flex items-center gap-4"
          data-testid="recovery-edit-retry-btn"
        >
          <div className="w-11 h-11 rounded-lg bg-amber-500/10 flex items-center justify-center flex-shrink-0">
            <BookOpen className="w-5 h-5 text-amber-400" />
          </div>
          <div className="flex-1">
            <span className="text-sm font-semibold text-white block">Edit Story & Retry</span>
            <span className="text-xs text-zinc-500">Modify your story or settings before regenerating</span>
          </div>
        </button>

        <button
          onClick={onNew}
          className="w-full rounded-xl border border-white/[0.06] bg-white/[0.015] p-4 text-left hover:bg-white/[0.04] transition-all flex items-center gap-4"
          data-testid="recovery-start-fresh-btn"
        >
          <div className="w-11 h-11 rounded-lg bg-indigo-500/10 flex items-center justify-center flex-shrink-0">
            <Sparkles className="w-5 h-5 text-indigo-400" />
          </div>
          <div className="flex-1">
            <span className="text-sm font-semibold text-white block">Start Fresh</span>
            <span className="text-xs text-zinc-500">Create a brand new video from scratch</span>
          </div>
        </button>

        <div className="pt-2 border-t border-white/[0.04]">
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs text-zinc-500 hover:text-red-400 hover:bg-red-500/[0.06] transition-colors disabled:opacity-40"
            data-testid="recovery-delete-btn"
          >
            <XCircle className="w-3.5 h-3.5" />
            {deleting ? 'Deleting...' : 'Delete this project'}
          </button>
        </div>
      </div>

      <div className="text-center pt-2">
        <button
          onClick={() => navigate('/app/my-space')}
          className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
          data-testid="recovery-back-btn"
        >
          <ArrowLeft className="w-3 h-3 inline mr-1" /> Back to My Space
        </button>
      </div>
    </div>
  );
}


// ─── POST-GENERATION PHASE (State Machine Driven) ─────────────────────────────
// Renders based on postGen.uiState ONLY. No contradictory states possible.
function PostGenPhase({ postGen, job, jobId, onNew, onResume, onRetryValidation, storyText, animStyle }) {
  const [copied, setCopied] = useState(false);
  const [showDirections, setShowDirections] = useState(false);
  const [customDirection, setCustomDirection] = useState('');
  const [showSharePrompt, setShowSharePrompt] = useState(false);
  const [userViralStats, setUserViralStats] = useState(null);
  const [showForceShare, setShowForceShare] = useState(false);
  const [showAutoNext, setShowAutoNext] = useState(false);
  const [continuationMode, setContinuationMode] = useState(null); // 'episode' | 'branch' | null
  const [continuationPreset, setContinuationPreset] = useState(null); // {title, instruction, label}
  const navigate = useNavigate();
  const { canDownload, upgradeRequired } = useMediaEntitlement();
  const { uiState, previewReady, downloadReady, shareReady, posterUrl, downloadUrl, shareUrl, storyPackUrl, failReason, stageDetail, jobTitle } = postGen;
  const displayTitle = jobTitle || job?.title || 'Your Video';
  const timing = job?.timing || {};
  const currentStyle = animStyle || job?.animation_style || 'cartoon_2d';

  // Session chaining: auto-next trigger after 8 seconds when video is ready
  useEffect(() => {
    if (uiState === 'READY') {
      const timer = setTimeout(() => setShowAutoNext(true), 8000);
      return () => clearTimeout(timer);
    }
  }, [uiState]);

  // Reward celebration: check for streak/episode rewards when video completes
  useEffect(() => {
    if (uiState === 'READY') {
      // Auto-redirect branches to Watch Page (Battle) after 3s
      if (job?.continuation_type === 'branch' && jobId) {
        const battleRoot = job?.root_story_id || job?.story_chain_id || job?.parent_job_id;
        const timer = setTimeout(() => {
          if (battleRoot) {
            navigate(`/app/story-battle/${battleRoot}`, { replace: true });
          } else {
            navigate(`/app/story-viewer/${jobId}`, { replace: true });
          }
        }, 3000);
        return () => clearTimeout(timer);
      }

      const token = localStorage.getItem('token');
      if (!token) return;
      // Fetch viral stats for personalized share prompt
      api.get('/api/viral/rewards/status')
        .then(r => setUserViralStats(r.data))
        .catch(() => {});
      (async () => {
        try {
          const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/retention/streak`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          const d = await res.json();
          if (d.success && d.current_streak > 0) {
            // Check if a milestone was just claimed (streak matches a milestone)
            const milestones = { 3: 10, 7: 25 };
            for (const [day, credits] of Object.entries(milestones)) {
              if (d.current_streak === parseInt(day) && d.milestones_claimed?.includes(parseInt(day))) {
                toast.success(
                  <div className="text-center">
                    <p className="font-black text-base">Day {day} Streak!</p>
                    <p className="text-xs opacity-80 mt-0.5">+{credits} credits earned</p>
                    <p className="text-[10px] opacity-60 mt-1">Keep creating to unlock more rewards</p>
                  </div>,
                  { duration: 5000, icon: '🎉' }
                );
                break;
              }
            }
          }
        } catch {}
      })();
    }
  }, [uiState]);

  // Detect if Ken Burns fallback was used (quick render mode)
  const usedQuickRender = job?.used_ken_burns_fallback || job?.fallback_clips_count > 0;

  // Status badge configuration — driven by uiState only
  const STATUS_CONFIG = {
    VALIDATING: { bg: 'bg-amber-500/10 border-amber-500/30', icon: <Loader2 className="w-5 h-5 text-amber-400 animate-spin" />, title: 'Validating Assets', subtitle: 'Checking preview and download availability...' },
    READY: { bg: 'bg-emerald-500/10 border-emerald-500/30', icon: <CheckCircle className="w-5 h-5 text-emerald-400" />, title: usedQuickRender ? 'Video Ready (Quick Render)' : 'Video Ready', subtitle: usedQuickRender ? 'Quick render mode used — full animation may vary' : 'Preview and download verified' },
    PARTIAL_READY: { bg: 'bg-amber-500/10 border-amber-500/30', icon: usedQuickRender ? <Zap className="w-5 h-5 text-amber-400" /> : <Shield className="w-5 h-5 text-amber-400" />, title: usedQuickRender ? 'Video Saved (Quick Render)' : 'Video Saved', subtitle: usedQuickRender ? 'Quick render mode used — full animation may vary' : (downloadReady ? 'Download available — preview may be limited' : 'Processing assets...') },
    FAILED: { bg: 'bg-amber-500/10 border-amber-500/30', icon: <AlertCircle className="w-5 h-5 text-amber-400" />, title: 'Something needs a quick fix', subtitle: failReason || 'A step in the generation process hit an issue' },
  };
  const statusCfg = STATUS_CONFIG[uiState] || STATUS_CONFIG.VALIDATING;

  const handleCopyLink = () => {
    const url = shareUrl;
    if (url) {
      navigator.clipboard.writeText(url).then(() => {
        setCopied(true);
        toast.success('Link copied!');
        setTimeout(() => setCopied(false), 2000);
      });
    }
  };

  const handleShare = (platform) => {
    const url = encodeURIComponent(shareUrl || '');
    const text = encodeURIComponent(`Check out this AI-generated story video: "${displayTitle}" — Made with Visionary Suite`);
    const urls = {
      twitter: `https://twitter.com/intent/tweet?text=${text}&url=${url}`,
      whatsapp: `https://wa.me/?text=${text}%20${url}`,
      copy: null,
    };
    // Analytics
    try { api.post('/api/funnel/track', { event: 'share_clicked', data: { platform, job_id: jobId || job?.job_id } }); } catch {}

    if (platform === 'copy') {
      navigator.clipboard?.writeText(shareUrl || window.location.href).then(() => {
        setCopied(true);
        toast.success('Link copied!');
        try { api.post('/api/funnel/track', { event: 'copied_link', data: { job_id: jobId || job?.job_id } }); } catch {}
        setTimeout(() => setCopied(false), 2000);
      });
      return;
    }
    if (urls[platform]) window.open(urls[platform], '_blank', 'width=600,height=400');
  };

  const handleContinue = (direction) => {
    const jid = jobId || job?.job_id;
    const baseStory = storyText || job?.story_text || '';
    const modifier = direction.id === 'custom' ? customDirection : direction.modifier;
    if (!modifier.trim()) return;

    const continuePrompt = `[Continuation of "${displayTitle}"]\n\nPrevious story:\n${baseStory.slice(0, 500)}...\n\nDirection: ${modifier}`;

    localStorage.setItem('remix_video', JSON.stringify({
      parent_video_id: jid,
      title: displayTitle,
      story_text: continuePrompt,
      animation_style: currentStyle,
      age_group: job?.age_group,
      voice_preset: job?.voice_preset,
    }));
    navigate(`/app/story-video-studio?remix=continue`);
    toast.success(`Creating continuation: ${direction.label}`);
  };

  const handleStyleRemix = (newStyleId) => {
    const jid = jobId || job?.job_id;
    localStorage.setItem('remix_video', JSON.stringify({
      parent_video_id: jid,
      title: `Remix: ${displayTitle}`,
      story_text: storyText || job?.story_text || '',
      animation_style: newStyleId,
      age_group: job?.age_group,
      voice_preset: job?.voice_preset,
    }));
    navigate(`/app/story-video-studio?remix=style`);
    toast.success('Remixing with new style...');
  };

  // Preset continuation openers — each opens ContinuationModal with pre-filled context
  const openPresetContinuation = (mode, preset) => {
    setContinuationPreset(preset);
    setContinuationMode(mode);
    // Fire analytics
    if (preset?.analyticsEvent) {
      try { api.post('/api/funnel/track', { event: preset.analyticsEvent, data: { job_id: jobId || job?.job_id } }); } catch {}
    }
  };

  const isActionable = uiState === 'READY' || uiState === 'PARTIAL_READY';

  // Auto-show FORCE SHARE GATE when video is ready (once per job)
  React.useEffect(() => {
    if (uiState === 'READY' && !showForceShare) {
      const prompted = sessionStorage.getItem(`force_share_${jobId}`);
      if (!prompted) {
        const timer = setTimeout(() => {
          setShowForceShare(true);
          sessionStorage.setItem(`force_share_${jobId}`, '1');
        }, 2000);
        return () => clearTimeout(timer);
      }
    }
  }, [uiState, jobId, showForceShare]);

  // Auto-show contextual SHARE PROMPT after ForceShareGate is dismissed (once per project)
  React.useEffect(() => {
    if (uiState === 'READY' && !showForceShare && !showSharePrompt) {
      const alreadyShown = sessionStorage.getItem(`share_prompt_${jobId}`);
      const forceShared = sessionStorage.getItem(`force_share_${jobId}`);
      if (!alreadyShown && forceShared) {
        const timer = setTimeout(() => {
          setShowSharePrompt(true);
          sessionStorage.setItem(`share_prompt_${jobId}`, '1');
        }, 3000);
        return () => clearTimeout(timer);
      }
    }
  }, [uiState, jobId, showForceShare, showSharePrompt]);

  // Extract character name and cliffhanger from job data for share prompts
  const characterName = job?.characters?.[0]?.name || job?.character_name || '';
  const cliffhanger = job?.cliffhanger || '';

  return (
    <div className="space-y-6 vs-fade-up-1" data-testid="postgen-phase">
      {/* Force Share Gate modal — Character-driven */}
      {showForceShare && (
        <ForceShareGate
          jobId={jobId}
          title={displayTitle}
          slug={job?.slug || jobId}
          shareUrl={shareUrl}
          characterName={characterName}
          cliffhanger={cliffhanger}
          characters={job?.characters}
          onContinue={() => {
            setShowForceShare(false);
            handleContinue(CONTINUE_DIRECTIONS[0]);
          }}
          onDismiss={() => setShowForceShare(false)}
        />
      )}
      {/* Contextual Auto-Share Prompt — shows after ForceShareGate, once per project */}
      {showSharePrompt && !showForceShare && (
        <SharePromptModal
          jobId={jobId}
          title={displayTitle}
          characterName={characterName}
          slug={job?.slug || jobId}
          onClose={() => setShowSharePrompt(false)}
          context={{
            isChallengeWinner: job?.is_challenge_winner || false,
            isTrending: (job?.views || 0) > 20,
            remixCount: job?.remix_count || 0,
            userViralStats: userViralStats,
          }}
        />
      )}
      {/* Status Badge — single truth from uiState */}
      <div className={`rounded-xl border p-5 ${statusCfg.bg}`} data-testid="status-badge">
        <div className="flex items-center gap-3">
          {statusCfg.icon}
          <div>
            <h2 className="text-lg font-bold text-white" data-testid="status-title">{statusCfg.title}</h2>
            <p className="text-sm text-[var(--vs-text-secondary)]" data-testid="status-subtitle">{statusCfg.subtitle}</p>
          </div>
        </div>
      </div>

      {/* Quick Render Mode Banner — shown when Ken Burns fallback was used */}
      {usedQuickRender && isActionable && (
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-5 py-3 flex items-center gap-3" data-testid="quick-render-banner">
          <Zap className="w-5 h-5 text-amber-400 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-amber-200">Quick render mode used — full animation may vary</p>
            <p className="text-xs text-amber-400/60 mt-0.5">
              {job?.sora_clips_count || 0} AI-animated scene{(job?.sora_clips_count || 0) !== 1 ? 's' : ''}, {job?.fallback_clips_count || 0} quick-rendered scene{(job?.fallback_clips_count || 0) !== 1 ? 's' : ''}
            </p>
          </div>
        </div>
      )}

      {/* ═══ BATTLE ENTRY BANNER — shown when this job is a competing branch ═══ */}
      {job?.continuation_type === 'branch' && (
        <div className="rounded-xl border border-rose-500/20 bg-gradient-to-r from-rose-500/[0.06] to-amber-500/[0.03] px-5 py-4 animate-in fade-in slide-in-from-top-2 duration-500" data-testid="battle-entry-banner">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-rose-500/20 flex items-center justify-center flex-shrink-0">
                <Swords className="w-5 h-5 text-rose-400" />
              </div>
              <div>
                <p className="text-sm font-bold text-white">You've entered the battle!</p>
                <p className="text-xs text-white/40">
                  {uiState === 'GENERATING' || uiState === 'VALIDATING'
                    ? 'Your version is generating... Once ready, it goes live.'
                    : 'Your version is LIVE and competing.'
                  }
                  {job?.source_story_title && (
                    <span className="text-white/30"> Competing with "{job.source_story_title}"</span>
                  )}
                </p>
              </div>
            </div>
            <div className="flex gap-2 flex-shrink-0">
              {job?.root_story_id && (
                <Link
                  to={`/app/story-battle/${job.root_story_id}`}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-white/[0.06] border border-white/10 text-white/70 text-xs font-medium hover:bg-white/10 transition-colors"
                  data-testid="view-leaderboard-btn"
                >
                  <BarChart2 className="w-3.5 h-3.5" /> Leaderboard
                </Link>
              )}
            </div>
          </div>
          {/* MySpace subtle note */}
          <p className="text-[10px] text-white/20 mt-2 flex items-center gap-1">
            <CheckCircle className="w-3 h-3" /> Saved to MySpace
          </p>
        </div>
      )}

      <div className="grid lg:grid-cols-5 gap-6">
        {/* LEFT: Preview Area */}
        <div className="lg:col-span-3">
          {/* ═══ GENERATING STATE — maintain dopamine, show competitive context ═══ */}
          {(['IDLE', 'GENERATING'].includes(uiState) && !previewReady && !posterUrl && !downloadReady) ? (
            <div className="rounded-xl border border-violet-500/20 bg-gradient-to-br from-violet-500/[0.04] to-rose-500/[0.02] p-6" data-testid="generating-preview">
              {job?.continuation_type === 'branch' || job?.quick_shot ? (
                <div className="text-center">
                  {/* Competition-first framing */}
                  <div className="w-14 h-14 rounded-2xl bg-rose-500/15 flex items-center justify-center mx-auto mb-4">
                    <Swords className="w-7 h-7 text-rose-400" />
                  </div>
                  <h3 className="text-lg font-bold text-white mb-1">Your entry is going live</h3>
                  <p className="text-sm text-amber-400 font-semibold mb-4">Competing for #1 right now</p>

                  {/* Fake-real competitive stats — maintain tension */}
                  <div className="flex items-center justify-center gap-6 mb-4">
                    <div className="text-center">
                      <p className="text-2xl font-black text-white">#{job?.chain_depth ? Math.min(job.chain_depth + 1, 5) : 3}</p>
                      <p className="text-[10px] text-white/30">Est. rank</p>
                    </div>
                    <div className="w-px h-8 bg-white/10" />
                    <div className="text-center">
                      <p className="text-2xl font-black text-white">{job?.source_story_title ? '2' : '1'}</p>
                      <p className="text-[10px] text-white/30">pts to #1</p>
                    </div>
                    <div className="w-px h-8 bg-white/10" />
                    <div className="text-center">
                      <div className="flex items-center gap-1">
                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                        <p className="text-2xl font-black text-emerald-400">Live</p>
                      </div>
                      <p className="text-[10px] text-white/30">Status</p>
                    </div>
                  </div>

                  <p className="text-xs text-white/30 mb-4">People can already view your entry while it renders</p>

                  {/* Progress */}
                  {postGen.stageDetail && (
                    <div className="inline-flex items-center gap-2 bg-white/[0.04] rounded-full px-4 py-2 text-xs text-white/40">
                      <Loader2 className="w-3 h-3 animate-spin" />
                      {postGen.stageDetail}
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center">
                  <div className="w-14 h-14 rounded-2xl bg-violet-500/10 flex items-center justify-center mx-auto mb-4">
                    <Loader2 className="w-7 h-7 text-violet-400 animate-spin" />
                  </div>
                  <h3 className="text-lg font-bold text-white mb-2">Generating your story...</h3>
                  <p className="text-sm text-white/40 mb-1">AI is crafting scenes, visuals, and narration.</p>
                  <p className="text-xs text-white/25 mb-4">This usually takes 30-60 seconds.</p>
                  {postGen.stageDetail && (
                    <div className="inline-flex items-center gap-2 bg-white/[0.04] rounded-full px-4 py-2 text-xs text-white/50">
                      <Loader2 className="w-3 h-3 animate-spin" />
                      {postGen.stageDetail}
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : uiState === 'VALIDATING' ? (
            <div className="rounded-xl overflow-hidden border border-[var(--vs-border)]" data-testid="preview-container">
              <div className="aspect-video bg-slate-800 flex items-center justify-center animate-pulse">
                <Loader2 className="w-8 h-8 text-amber-400 animate-spin" />
                <span className="ml-3 text-slate-400 text-sm">Validating your video...</span>
              </div>
            </div>
          ) : previewReady && posterUrl ? (
            <div className="rounded-xl overflow-hidden border border-[var(--vs-border)]" data-testid="preview-container">
              <SafeImage
                src={posterUrl}
                alt={displayTitle}
                aspectRatio="16/9"
                titleOverlay={displayTitle}
                className="rounded-xl"
                data-testid="preview-image"
              />
            </div>
          ) : downloadReady && downloadUrl ? (
            /* Video exists but no preview image — show action prompt instead of empty box */
            <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-8 text-center" data-testid="video-ready-no-preview">
              {job?.continuation_type === 'branch' ? (
                <>
                  <Swords className="w-12 h-12 text-rose-400 mx-auto mb-4" />
                  <h3 className="text-xl font-bold text-white mb-2">Your version is LIVE!</h3>
                  <p className="text-slate-400 text-sm mb-2">Competing now. Redirecting to your story...</p>
                  <p className="text-xs text-white/30 mb-4">Views, shares, and continuations determine rank</p>
                  <div className="flex gap-3 justify-center">
                    <Button
                      onClick={() => navigate(`/app/story-viewer/${jobId}`)}
                      className="bg-rose-600 hover:bg-rose-700"
                      data-testid="watch-your-version-btn"
                    >
                      <Play className="w-4 h-4 mr-2 fill-white" /> Watch Your Version
                    </Button>
                    {job?.root_story_id && (
                      <Link to={`/app/story-battle/${job.root_story_id}`}>
                        <Button variant="outline" className="border-white/10 text-white/60" data-testid="view-battle-btn">
                          <BarChart2 className="w-4 h-4 mr-2" /> View Leaderboard
                        </Button>
                      </Link>
                    )}
                  </div>
                </>
              ) : (
                <>
                  <CheckCircle className="w-12 h-12 text-emerald-400 mx-auto mb-4" />
                  <h3 className="text-xl font-bold text-white mb-2">Your video is ready!</h3>
                  <p className="text-slate-400 text-sm mb-6">{canDownload ? 'Click below to download your creation.' : 'Upgrade your plan to download this creation.'}</p>
                  <div className="flex gap-3 justify-center">
                    <EntitledDownloadButton
                      assetId={jobId}
                      label="Download Video"
                      upgradeLabel="Upgrade to Download"
                      data-testid="download-video-inline-btn"
                    />
                  </div>
                </>
              )}
            </div>
          ) : uiState === 'FAILED' ? (
            /* Generation failed — soft recovery UX */
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-8" data-testid="generation-failed-panel">
              <div className="text-center">
                <AlertCircle className="w-12 h-12 text-amber-400 mx-auto mb-4" />
                <h3 className="text-lg font-bold text-white mb-2">Something needs a quick fix</h3>
                <p className="text-amber-300/80 text-sm mb-2">{failReason || 'A step in the generation process hit an issue.'}</p>
                {postGen.errorCode && (
                  <p className="text-amber-400/40 text-[11px] font-mono mb-2">Ref: {postGen.errorCode}</p>
                )}
                {/* Encouraging recovery copy */}
                <div className="inline-block bg-emerald-500/10 border border-emerald-500/20 rounded-lg px-4 py-2 mb-4">
                  <p className="text-emerald-300/90 text-xs leading-relaxed">This usually works on retry. Your credits have been preserved.</p>
                  {(failReason || '').toLowerCase().includes('character') && (
                    <p className="text-emerald-300/70 text-[11px] mt-1">Tip: We'll automatically use simpler character descriptions on retry.</p>
                  )}
                </div>
                {postGen.creditsRefunded > 0 && (
                  <div className="inline-flex items-center gap-1.5 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-3 py-1 mb-4">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="text-emerald-300 text-xs">{postGen.creditsRefunded} credits refunded to your account</span>
                  </div>
                )}
              </div>
              {/* Actions — Retry is ALWAYS primary, Start Over is secondary */}
              <div className="flex flex-col items-center gap-2 mt-4" data-testid="failure-actions">
                <div className="flex gap-3 justify-center">
                  {(job?.allowed_actions || []).includes('retry') ? (
                    <RetryButton jobId={jobId} onRetryStarted={(j) => { onResume?.(j); }} />
                  ) : (
                    <Button onClick={onNew} className="bg-indigo-600 hover:bg-indigo-500" data-testid="retry-fresh-btn">
                      <RefreshCw className="w-4 h-4 mr-2" /> Try Again
                    </Button>
                  )}
                </div>
                <Button onClick={onNew} variant="ghost" className="text-zinc-500 hover:text-zinc-300 text-xs" data-testid="start-over-btn">
                  or start over with a new story
                </Button>
              </div>
            </div>
          ) : (
            /* PARTIAL_READY with no preview and no download — honest state */
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-8 text-center" data-testid="no-output-panel">
              <AlertCircle className="w-10 h-10 text-amber-400 mx-auto mb-3" />
              <h3 className="text-lg font-bold text-white mb-2">Output Not Available</h3>
              <p className="text-amber-300/80 text-sm mb-4">This generation did not produce a viewable output. No credits were charged for failed generations.</p>
              <Button onClick={onNew} className="bg-indigo-600 hover:bg-indigo-700" data-testid="create-new-btn">
                <Sparkles className="w-4 h-4 mr-2" /> Create New Video
              </Button>
            </div>
          )}

          {/* Scene thumbnails — use SafeImage */}
          {(job?.scene_progress || []).length > 0 && (
            <div className="mt-4" data-testid="scene-thumbnails">
              <h3 className="text-sm font-medium text-[var(--vs-text-muted)] mb-3">Scenes</h3>
              <div className="flex gap-2 flex-wrap">
                {(job.scene_progress || []).map(sp => (
                  <div key={sp.scene_number} className="w-24 rounded-lg overflow-hidden border border-[var(--vs-border-subtle)]">
                    <SafeImage
                      src={sp.image_url}
                      alt={sp.title || `Scene ${sp.scene_number}`}
                      aspectRatio="16/10"
                      titleOverlay={sp.title}
                      data-testid={`scene-thumb-${sp.scene_number}`}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* View Full Preview link */}
          {jobId && isActionable && (
            <div className="mt-4">
              <Link to={`/app/story-preview/${jobId}`} className="w-full">
                <Button className="w-full bg-purple-600 hover:bg-purple-700" data-testid="view-full-preview-btn">
                  <Eye className="w-4 h-4 mr-2" /> View Full Preview & Export MP4
                </Button>
              </Link>
            </div>
          )}
        </div>

        {/* RIGHT: Actions Panel — gated by uiState */}
        <div className="lg:col-span-2 space-y-4">
          <h3 className="text-white font-semibold text-lg" data-testid="video-title">{displayTitle}</h3>

          {/* SHARE & EARN — above download, prominent */}
          {isActionable && (
            <ShareRewardBar
              jobId={jobId}
              title={displayTitle}
              slug={job?.slug || jobId}
              shareUrl={shareUrl}
              characterName={characterName}
              cliffhanger={cliffhanger}
            />
          )}

          {/* Viral Momentum Meter — shows when story has traction */}
          {isActionable && jobId && (
            <div data-testid="postgen-momentum">
              <ViralMomentumBadge jobId={jobId} variant="card" showBadges={true} />
            </div>
          )}

          {/* Download — entitlement-gated, no raw URLs */}
          <EntitledDownloadButton
            assetId={jobId}
            label="Download Video"
            upgradeLabel="Upgrade to Download"
            disabled={!downloadReady || uiState === 'VALIDATING'}
            className="w-full"
            data-testid="download-btn"
          />

          {/* Story Pack — also gated */}
          {storyPackUrl && downloadReady && (
            <EntitledDownloadButton
              assetId={jobId}
              label="Download Story Pack"
              upgradeLabel="Upgrade to Download"
              className="w-full"
              variant="outline"
              data-testid="download-pack-btn"
            />
          )}

          {/* Share — only when shareReady is true */}
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleCopyLink} disabled={!shareReady} className="flex-1 border-slate-700 text-slate-300 hover:text-white text-xs disabled:opacity-40" data-testid="share-copy-btn">
              {copied ? <Check className="w-3.5 h-3.5 mr-1" /> : <Copy className="w-3.5 h-3.5 mr-1" />}
              {copied ? 'Copied' : 'Copy Link'}
            </Button>
            <Button variant="outline" size="sm" onClick={() => handleShare('twitter')} disabled={!shareReady} className="border-slate-700 text-slate-300 hover:text-white px-3 disabled:opacity-40" data-testid="share-twitter-btn">
              <ExternalLink className="w-3.5 h-3.5" />
            </Button>
            <Button variant="outline" size="sm" onClick={() => handleShare('whatsapp')} disabled={!shareReady} className="border-slate-700 text-slate-300 hover:text-white px-3 disabled:opacity-40" data-testid="share-whatsapp-btn">
              <Share2 className="w-3.5 h-3.5" />
            </Button>
          </div>

          {/* FAILED state: single source of truth — backend-driven actions only */}
          {uiState === 'FAILED' && job?.recovery_state !== 'NONE' && (
            <div className="bg-amber-500/5 border border-amber-500/20 rounded-lg p-4" data-testid="recovery-status">
              <p className="text-amber-300 text-sm">
                {job.recovery_state === 'AUTO_RECOVERING' ? 'Recovery in progress...' : 'Waiting for your action.'}
              </p>
            </div>
          )}
          {uiState === 'FAILED' && (
            <p className="text-xs text-slate-500">Credits have been preserved for retry.</p>
          )}

          {/* PARTIAL_READY: explain and offer retry */}
          {uiState === 'PARTIAL_READY' && !previewReady && (
            <div className="bg-amber-500/5 border border-amber-500/20 rounded-lg p-3" data-testid="partial-ready-info">
              <p className="text-amber-300 text-xs mb-2">Preview unavailable — {stageDetail}</p>
              <Button onClick={onRetryValidation} size="sm" variant="outline" className="border-amber-500/30 text-amber-400 hover:bg-amber-500/10 text-xs" data-testid="retry-validation-btn">
                <RefreshCw className="w-3 h-3 mr-1" /> Retry Preview
              </Button>
            </div>
          )}

          {/* Performance timing */}
          {(timing.total_ms || timing.scenes_ms) && (
            <div className="bg-slate-800/30 rounded-lg border border-slate-700/30 p-3" data-testid="timing-breakdown">
              <h4 className="text-xs font-medium text-slate-400 mb-2">Performance</h4>
              <div className="grid grid-cols-4 gap-1 text-center text-xs">
                {['scenes', 'images', 'voices', 'total'].map(k => (
                  <div key={k}>
                    <p className="text-slate-500 capitalize">{k}</p>
                    <p className="text-white font-medium">{timing[`${k}_ms`] ? `${(timing[`${k}_ms`] / 1000).toFixed(1)}s` : '-'}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Credits */}
          {job?.credits_charged > 0 && (
            <p className="text-xs text-slate-500 flex items-center gap-1">
              <Coins className="w-3 h-3" /> {job.credits_charged} credits used
            </p>
          )}

          {/* New Video */}
          {uiState !== 'FAILED' && (
            <Button onClick={onNew} variant="ghost" className="w-full text-slate-400 hover:text-white" data-testid="new-video-btn">
              <Sparkles className="w-4 h-4 mr-2" /> Create New Story
            </Button>
          )}
        </div>
      </div>

      {/* ── ENGAGEMENT LOOP ACTIONS (only when generation succeeded) ────── */}
      {isActionable && (
        <>
          {/* ═══ AUTO-NEXT TRIGGER — Session Chaining (Episode vs Branch) ═══ */}
          {showAutoNext && (
            <div className="relative overflow-hidden rounded-2xl border border-violet-500/30 bg-gradient-to-r from-violet-600/[0.08] to-rose-600/[0.08] p-5" style={{ animation: 'slideIn 0.4s ease-out' }} data-testid="auto-next-trigger">
              <div className="text-center mb-4">
                <p className="text-xs text-amber-400 font-bold uppercase tracking-wider mb-1">That was just the beginning...</p>
                <h3 className="text-lg font-black text-white">What happens next?</h3>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => setContinuationMode('episode')}
                  className="flex-1 h-12 rounded-xl bg-gradient-to-r from-violet-600 to-blue-600 text-white text-sm font-bold flex items-center justify-center gap-2 hover:opacity-90 shadow-lg shadow-violet-500/20"
                  style={{ animation: 'cta-glow 2s ease-in-out infinite' }}
                  data-testid="auto-next-episode-btn"
                >
                  <Play className="w-5 h-5" /> Next Episode <ArrowRight className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setContinuationMode('branch')}
                  className="flex-1 h-12 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-300 text-sm font-bold flex items-center justify-center gap-2 hover:bg-rose-500/20 transition-all"
                  data-testid="auto-next-branch-btn"
                >
                  <GitBranch className="w-5 h-5" /> Fork Story
                </button>
              </div>
              <style>{`
                @keyframes slideIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
                @keyframes cta-glow { 0%, 100% { box-shadow: 0 0 30px -8px rgba(139,92,246,0.4); } 50% { box-shadow: 0 0 50px -5px rgba(139,92,246,0.6); } }
              `}</style>
            </div>
          )}

          {/* ═══ CLIFFHANGER HOOK ═══ */}
          {(storyText || job?.story_text) && (
            <div className="bg-gradient-to-r from-amber-500/[0.06] to-rose-500/[0.06] border border-amber-500/20 rounded-2xl p-5" data-testid="cliffhanger-hook">
              <div className="flex items-center gap-2 mb-2">
                <BookOpen className="w-4 h-4 text-amber-400" />
                <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider">The story so far...</span>
              </div>
              <p className="text-sm text-slate-300 italic leading-relaxed mb-1">
                "{(() => {
                  const txt = storyText || job?.story_text || '';
                  const last200 = txt.slice(-200);
                  return last200.length < txt.length ? '...' + last200 : last200;
                })()}"
              </p>
              <p className="text-xs text-amber-400/80 font-semibold mt-2">But something unexpected happens next...</p>
            </div>
          )}

          {/* ═══ PRIMARY: Episode vs Branch (TWO DISTINCT PATHS) ═══ */}
          <div className="grid grid-cols-2 gap-3" data-testid="multiplayer-continue-actions">
            {/* Continue Next Episode */}
            <button
              onClick={() => setContinuationMode('episode')}
              className="group relative overflow-hidden rounded-2xl p-5 text-left transition-all hover:scale-[1.01] active:scale-[0.99]"
              data-testid="primary-episode-btn"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-violet-600 to-blue-600 opacity-90 group-hover:opacity-100 transition-opacity" />
              <div className="relative z-10">
                <div className="w-11 h-11 rounded-xl bg-white/10 flex items-center justify-center mb-3">
                  <Play className="w-6 h-6 text-white" />
                </div>
                <span className="text-base font-black text-white block mb-1">Next Episode</span>
                <span className="text-xs text-white/60">Continue the timeline — same world, next chapter</span>
              </div>
            </button>

            {/* Fork / Branch */}
            <button
              onClick={() => setContinuationMode('branch')}
              className="group relative overflow-hidden rounded-2xl p-5 text-left transition-all hover:scale-[1.01] active:scale-[0.99]"
              data-testid="primary-branch-btn"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-rose-600 to-orange-600 opacity-90 group-hover:opacity-100 transition-opacity" />
              <div className="relative z-10">
                <div className="w-11 h-11 rounded-xl bg-white/10 flex items-center justify-center mb-3">
                  <GitBranch className="w-6 h-6 text-white" />
                </div>
                <span className="text-base font-black text-white block mb-1">Fork Story</span>
                <span className="text-xs text-white/60">Create a rival version — compete for #1 spot</span>
              </div>
            </button>
          </div>

          {/* ═══ COMPETITION PULSE — Live rank + gap + re-engagement ═══ */}
          <CompetitionPulse
            jobId={jobId || job?.job_id}
            rootStoryId={job?.root_story_id || job?.story_chain_id}
            onTryAgain={() => openPresetContinuation('branch', {
              title: `${displayTitle} — Twist`,
              instruction: 'Add an unexpected twist. Something that completely changes the direction. Shock the reader.',
              analyticsEvent: 'quality_gate_twist_clicked',
            })}
            onNewJobCreated={(data) => {
              if (data?.job_id) {
                navigate(`/app/story-video-studio?projectId=${data.job_id}`);
              }
            }}
          />

          {/* ═══ SECONDARY: Add Twist / Make Funny / Next Episode ═══ */}
          <div className="grid grid-cols-3 gap-3" data-testid="secondary-actions">
            <button
              onClick={() => openPresetContinuation('branch', {
                title: `${displayTitle} — Twist`,
                instruction: 'Add an unexpected plot twist — a shocking reveal that changes everything while preserving the main characters and world.',
                analyticsEvent: 'add_twist_clicked',
              })}
              className="p-4 rounded-xl border border-amber-500/20 bg-amber-500/[0.04] hover:bg-amber-500/[0.08] transition-all text-center group"
              data-testid="add-twist-btn"
            >
              <Sparkles className="w-5 h-5 text-amber-400 mx-auto mb-2" />
              <span className="text-sm font-bold text-white block">Add Twist</span>
              <span className="text-[10px] text-slate-500">Unexpected reveal</span>
            </button>
            <button
              onClick={() => openPresetContinuation('branch', {
                title: `${displayTitle} — Funny Version`,
                instruction: 'Convert this story into a hilarious comedy version. Add funny dialogue, comedic timing, and absurd situations while keeping the core events.',
                analyticsEvent: 'make_funny_clicked',
              })}
              className="p-4 rounded-xl border border-pink-500/20 bg-pink-500/[0.04] hover:bg-pink-500/[0.08] transition-all text-center group"
              data-testid="make-funny-btn"
            >
              <AlertCircle className="w-5 h-5 text-pink-400 mx-auto mb-2" />
              <span className="text-sm font-bold text-white block">Make Funny</span>
              <span className="text-[10px] text-slate-500">Comedy version</span>
            </button>
            <button
              onClick={() => openPresetContinuation('episode', {
                title: `${displayTitle} — Episode ${(job?.episode_number || 1) + 1}`,
                instruction: 'Continue this storyline forward. Preserve all characters, world, and continuity. What happens next?',
                analyticsEvent: 'next_episode_clicked',
              })}
              className="p-4 rounded-xl border border-purple-500/20 bg-purple-500/[0.04] hover:bg-purple-500/[0.08] transition-all text-center group"
              data-testid="next-episode-btn"
            >
              <Film className="w-5 h-5 text-purple-400 mx-auto mb-2" />
              <span className="text-sm font-bold text-white block">Next Episode</span>
              <span className="text-[10px] text-slate-500">New adventure</span>
            </button>
          </div>

          {/* ═══ YOUR VERSION vs POPULAR — Competitive Comparison ═══ */}
          <CompetitiveComparison
            posterUrl={posterUrl}
            displayTitle={displayTitle}
            navigate={navigate}
            storyText={storyText || job?.story_text || ''}
            currentStyle={currentStyle}
            jobId={jobId || job?.job_id}
            job={job}
            onBeat={() => openPresetContinuation('branch', {
              title: `Beat: ${displayTitle}`,
              instruction: 'Create a stronger, more compelling version of this story. Outdo the original with better plot, deeper characters, and more engaging writing.',
              analyticsEvent: 'try_to_beat_clicked',
            })}
            onImprove={() => openPresetContinuation('branch', {
              title: `Improved: ${displayTitle}`,
              instruction: 'Refine and improve your current version. Better pacing, stronger dialogue, more vivid descriptions. Keep the core story but make everything sharper.',
              analyticsEvent: 'improve_yours_clicked',
            })}
          />

          {/* ═══ INSTANT REMIX VARIANTS — One-click generation ═══ */}
          <div className="bg-slate-900/50 border border-indigo-500/10 rounded-xl p-4 space-y-3" data-testid="instant-remix-section">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Zap className="w-3.5 h-3.5 text-indigo-400" /> Try a variation instantly
            </h3>
            <div className="grid grid-cols-4 gap-2" data-testid="instant-remix-buttons">
              {[
                { label: 'More dramatic', tone: 'dramatic', instruction: 'Rewrite with higher stakes, intense emotions, and dramatic tension. Make every scene feel urgent and gripping.', color: 'border-red-500/20 bg-red-500/[0.04] hover:bg-red-500/[0.08]', iconColor: 'text-red-400' },
                { label: 'Shorter', tone: 'short', instruction: 'Create a condensed, punchy version. Cut to the essential scenes only. Maximum impact, minimum length.', color: 'border-blue-500/20 bg-blue-500/[0.04] hover:bg-blue-500/[0.08]', iconColor: 'text-blue-400' },
                { label: 'Faster-paced', tone: 'fast', instruction: 'Increase the pacing dramatically. Quick scene changes, rapid dialogue, constant forward momentum.', color: 'border-amber-500/20 bg-amber-500/[0.04] hover:bg-amber-500/[0.08]', iconColor: 'text-amber-400' },
                { label: 'More emotional', tone: 'emotional', instruction: 'Amplify the emotional depth. Make the audience feel deeply connected to the characters. Add poignant moments.', color: 'border-pink-500/20 bg-pink-500/[0.04] hover:bg-pink-500/[0.08]', iconColor: 'text-pink-400' },
              ].map(v => (
                <button
                  key={v.tone}
                  onClick={() => openPresetContinuation('branch', {
                    title: `${v.label}: ${displayTitle}`,
                    instruction: v.instruction,
                    analyticsEvent: 'variation_clicked',
                  })}
                  className={`p-3 rounded-xl border transition-all text-center group ${v.color}`}
                  data-testid={`instant-remix-${v.tone}`}
                >
                  <Zap className={`w-4 h-4 ${v.iconColor} mx-auto mb-1.5`} />
                  <span className="text-[11px] font-bold text-white block">{v.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* ═══ VIRAL LOOP: Share to unlock + reward ═══ */}
          <div className="bg-slate-900/80 border border-emerald-500/20 rounded-xl p-5" data-testid="viral-loop-share">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Share2 className="w-4 h-4 text-emerald-400" />
                Share & Earn Credits
              </h3>
            </div>
            <div className="flex gap-2 mb-3 flex-wrap">
              <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full">+5 share</span>
              <span className="text-[10px] font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full">+15 friend continues</span>
              <span className="text-[10px] font-bold text-violet-400 bg-violet-500/10 px-2 py-0.5 rounded-full">+25 friend signs up</span>
            </div>
            <div className="grid grid-cols-4 gap-2">
              {[
                { platform: 'whatsapp', label: 'Message', color: 'bg-emerald-600 hover:bg-emerald-500' },
                { platform: 'twitter', label: 'Post', color: 'bg-slate-700 hover:bg-slate-600' },
                { platform: 'instagram', label: 'Story', color: 'bg-pink-600 hover:bg-pink-500' },
                { platform: 'copy', label: 'Copy Link', color: 'bg-slate-800 hover:bg-slate-700' },
              ].map(s => (
                <button
                  key={s.platform}
                  onClick={async () => {
                    if (s.platform === 'copy') {
                      handleShare('copy');
                    } else if (s.platform === 'instagram') {
                      // Use native share API for Story/Instagram (mobile)
                      if (navigator.share) {
                        try {
                          await navigator.share({ title: displayTitle, text: `Check out "${displayTitle}"`, url: shareUrl || window.location.href });
                        } catch {}
                      } else {
                        handleShare('copy'); // Fallback to copy link
                        toast.info('Link copied — paste it into your Story');
                      }
                    } else {
                      handleShare(s.platform);
                    }
                    // Claim share reward
                    try {
                      const token = localStorage.getItem('token');
                      if (token) {
                        const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/growth/share-reward`, {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                          body: JSON.stringify({ job_id: jobId || job?.job_id, platform: s.platform }),
                        });
                        const data = await res.json();
                        if (data.rewarded) toast.success('+5 credits earned for sharing!');
                      }
                    } catch {
                      // Share reward claim failed — non-blocking
                      console.warn('Share reward claim failed');
                    }
                  }}
                  disabled={!shareReady && !downloadReady}
                  className={`py-2.5 rounded-xl text-xs font-bold text-white transition-all disabled:opacity-40 ${s.color}`}
                  data-testid={`share-reward-${s.platform}`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          {/* ═══ TERTIARY: Download + More Options ═══ */}
          <div className="flex gap-2">
            <EntitledDownloadButton
              assetId={jobId}
              label="Download"
              upgradeLabel="Upgrade to Download"
              disabled={!downloadReady}
              className="flex-1"
              variant="outline"
              data-testid="download-btn"
            />
            {storyPackUrl && downloadReady && (
              <a href={storyPackUrl} target="_blank" rel="noopener noreferrer" className="flex-1">
                <Button variant="outline" className="w-full border-slate-700 text-slate-300 hover:text-white">
                  <Package className="w-4 h-4 mr-2" /> Story Pack
                </Button>
              </a>
            )}
          </div>

          {/* ── Advanced Continue Directions ──────────────────────── */}
          <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4" data-testid="advanced-continue-section">
            <button
              onClick={() => setShowDirections(!showDirections)}
              className="w-full flex items-center justify-between text-sm text-slate-400 hover:text-white transition-colors"
              data-testid="toggle-advanced-btn"
            >
              <span className="flex items-center gap-2">
                <BookOpen className="w-3.5 h-3.5" /> More continuation options
              </span>
              <ChevronDown className={`w-4 h-4 transition-transform ${showDirections ? 'rotate-180' : ''}`} />
            </button>
            {showDirections && (
              <div className="mt-3 space-y-2" data-testid="continue-directions">
                {CONTINUE_DIRECTIONS.map(d => (
                  <button
                    key={d.id}
                    onClick={() => {
                      if (d.id === 'custom') {
                        if (!customDirection.trim()) return;
                        openPresetContinuation('branch', {
                          title: `${displayTitle} — Custom`,
                          instruction: customDirection,
                          analyticsEvent: 'custom_direction_clicked',
                        });
                        return;
                      }
                      openPresetContinuation(
                        d.id === 'next_episode' ? 'episode' : 'branch',
                        {
                          title: `${displayTitle} — ${d.label}`,
                          instruction: d.modifier || d.desc,
                          analyticsEvent: `direction_${d.id}_clicked`,
                        }
                      );
                    }}
                    disabled={d.id === 'custom' && !customDirection.trim()}
                    className={`w-full text-left flex items-center gap-3 p-3 rounded-lg border transition-all disabled:opacity-40 ${d.color}`}
                    data-testid={`direction-${d.id}`}
                  >
                    <d.icon className="w-4 h-4 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-white">{d.label}</p>
                      <p className="text-[10px] text-slate-400">{d.desc}</p>
                    </div>
                    {d.id !== 'custom' && <Play className="w-3.5 h-3.5 text-slate-400" />}
                  </button>
                ))}
                <input
                  type="text"
                  value={customDirection}
                  onChange={(e) => setCustomDirection(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && customDirection.trim() && handleContinue(CONTINUE_DIRECTIONS[4])}
                  placeholder="Your custom direction for the next episode..."
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  data-testid="custom-direction-input"
                />
              </div>
            )}
          </div>

          {/* ── Remix — Visual Style Swatches ──────────────────────── */}
          <div className="bg-slate-900/50 border border-pink-500/10 rounded-xl p-4 space-y-3" data-testid="remix-section">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <RefreshCw className="w-3.5 h-3.5 text-pink-400" /> Remix with Different Style
            </h3>
            <div className="grid grid-cols-5 gap-2" data-testid="remix-style-grid">
              {ANIM_STYLES.filter(s => s.id !== currentStyle).map(s => (
                <button
                  key={s.id}
                  onClick={() => openPresetContinuation('branch', {
                    title: `${displayTitle} — ${s.name} Style`,
                    instruction: `Recreate this exact story in ${s.name} visual style. Keep the same plot, characters, and dialogue but reimagine all visuals in ${s.name} aesthetic.`,
                    analyticsEvent: 'style_remix_clicked',
                    targetStyle: s.id,
                  })}
                  className="rounded-lg overflow-hidden group hover:ring-2 hover:ring-pink-500 transition-all"
                  data-testid={`remix-style-${s.id}`}
                >
                  <div className={`aspect-square bg-gradient-to-br ${s.gradient} flex items-center justify-center`}>
                    <RefreshCw className="w-4 h-4 text-white/0 group-hover:text-white/80 transition-all" />
                  </div>
                  <p className="text-[9px] text-slate-500 text-center py-1 bg-slate-800 truncate px-1">{s.name}</p>
                </button>
              ))}
            </div>
          </div>

          {/* ── Cross-Tool Conversions via CreationActionsBar ─────── */}
          <CreationActionsBar
            toolType="story-video-studio"
            originalPrompt={storyText || job?.story_text || job?.title || ''}
            originalSettings={{ style: currentStyle, ageGroup: job?.age_group }}
            parentGenerationId={jobId || job?.job_id}
            remixSourceTitle={displayTitle}
          />

          {/* ═══ POST-GENERATION LOOP — Retention CTAs ═══ */}
          {FEATURES.postGenerationLoop && (
            <div className="space-y-2 pt-2 border-t border-white/[0.06]" data-testid="post-gen-loop">
              <p className="text-xs text-slate-500 uppercase tracking-wider font-medium">Keep creating</p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <button
                  onClick={() => {
                    trackFunnel('postgen_cta_clicked', { story_id: jobId || job?.job_id, meta: { type: 'rewrite_twist' } });
                    navigate('/app/story-video-studio', {
                      state: { freshSession: true, remixFrom: { title: displayTitle, type: 'rewrite_twist' } },
                    });
                  }}
                  className="flex items-center gap-2 p-3 rounded-xl border border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.04] hover:border-violet-500/20 transition-all text-left"
                  data-testid="loop-rewrite-twist"
                >
                  <Sparkles className="w-4 h-4 text-violet-400 flex-shrink-0" />
                  <div>
                    <p className="text-xs font-semibold text-white">Make it 10x better?</p>
                    <p className="text-[10px] text-slate-500">Add a twist and beat your current version</p>
                  </div>
                </button>
                <button
                  onClick={() => {
                    trackFunnel('postgen_cta_clicked', { story_id: jobId || job?.job_id, meta: { type: 'change_style', current_style: currentStyle } });
                    navigate('/app/story-video-studio', {
                      state: {
                        freshSession: true,
                        prefill: { title: displayTitle, storyText: storyText || job?.story_text || '' },
                      },
                    });
                  }}
                  className="flex items-center gap-2 p-3 rounded-xl border border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.04] hover:border-sky-500/20 transition-all text-left"
                  data-testid="loop-change-style"
                >
                  <Image className="w-4 h-4 text-sky-400 flex-shrink-0" />
                  <div>
                    <p className="text-xs font-semibold text-white">Not the vibe you wanted?</p>
                    <p className="text-[10px] text-slate-500">Switch style instantly</p>
                  </div>
                </button>
                <button
                  onClick={() => {
                    trackFunnel('postgen_cta_clicked', { story_id: jobId || job?.job_id, meta: { type: 'enter_battle' } });
                    trackFunnel('battle_enter_clicked', { story_id: jobId || job?.job_id, meta: { source: 'postgen' } });
                    const rootId = job?.parent_job_id || job?.root_story_id || jobId;
                    navigate(`/app/story-battle/${rootId}`);
                  }}
                  className="flex items-center gap-2 p-3 rounded-xl border border-rose-500/10 bg-rose-500/[0.03] hover:bg-rose-500/[0.06] hover:border-rose-500/20 transition-all text-left"
                  data-testid="loop-enter-battle"
                >
                  <Swords className="w-4 h-4 text-rose-400 flex-shrink-0" />
                  <div>
                    <p className="text-xs font-semibold text-white">You're Rank #3 right now</p>
                    <p className="text-[10px] text-rose-400/70">Only one story can take #1</p>
                  </div>
                </button>
              </div>
            </div>
          )}

          {/* New Video */}
          <Button onClick={() => {
            try { api.post('/api/funnel/track', { event: 'create_new_story_clicked', data: { from_job: jobId || job?.job_id } }); } catch {}
            onNew();
          }} variant="ghost" className="w-full text-slate-500 hover:text-white" data-testid="new-video-btn">
            <Sparkles className="w-4 h-4 mr-2" /> Create Entirely New Story
          </Button>
        </>
      )}

      {/* ═══ Continuation Modal — Episode vs Branch ═══ */}
      <ContinuationModal
        isOpen={!!continuationMode}
        onClose={() => { setContinuationMode(null); setContinuationPreset(null); }}
        mode={continuationMode || 'episode'}
        preset={continuationPreset}
        parentJob={{
          job_id: jobId || job?.job_id,
          title: displayTitle,
          story_text: storyText || job?.story_text || '',
          animation_style: currentStyle,
          age_group: job?.age_group,
          voice_preset: job?.voice_preset,
          quality_mode: job?.quality_mode,
          episode_number: job?.episode_number,
        }}
        onJobCreated={(data) => {
          if (data?.job_id) {
            navigate(`/app/story-video-studio?projectId=${data.job_id}`);
          }
        }}
      />
    </div>
  );
}
