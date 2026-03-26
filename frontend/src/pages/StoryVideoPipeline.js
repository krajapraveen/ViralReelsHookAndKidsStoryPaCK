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
  Shield, Check, X, Zap, ChevronDown, ArrowRight
} from 'lucide-react';
import UpsellModal from '../components/UpsellModal';
import CreationActionsBar from '../components/CreationActionsBar';
import ProgressiveGeneration from '../components/ProgressiveGeneration';
import { useJobWebSocket } from '../hooks/useJobWebSocket';
import ContextualUpgrade from '../components/ContextualUpgrade';
import RemixBanner from '../components/RemixBanner';
import SharePromptModal from '../components/SharePromptModal';
import { ForceShareGate, ShareRewardBar } from '../components/ForceShareGate';
import { LiveViewerBadge } from '../components/AnimatedSocialProof';

// ─── CONSTANTS ────────────────────────────────────────────────────────────────
const STAGE_ORDER = ['scenes', 'images', 'voices'];
const STAGE_ICONS = { scenes: BookOpen, images: Image, voices: Mic };
const STAGE_LABELS = { scenes: 'Scenes', images: 'Images', voices: 'Voices' };

// Hard timeout: 5 minutes max for any generation
const HARD_TIMEOUT_MS = 5 * 60 * 1000;
// Stale detection: 90 seconds with no progress change
const STALE_THRESHOLD_MS = 90 * 1000;

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
      };
    case 'RESET':
      return INITIAL_POST_GEN_STATE;
    default:
      return state;
  }
}

// ─── ERROR BOUNDARY ───────────────────────────────────────────────────────────
class StudioErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { hasError: false, error: null }; }
  static getDerivedStateFromError(error) { return { hasError: true, error }; }
  render() {
    if (this.state.hasError) {
      return (
        <div className="vs-page flex items-center justify-center p-8">
          <div className="max-w-md text-center" data-testid="error-boundary">
            <AlertCircle className="w-12 h-12 text-[var(--vs-error)] mx-auto mb-4" />
            <h2 className="vs-h2 mb-2">Something went wrong</h2>
            <p className="text-[var(--vs-text-secondary)] mb-6">The video studio encountered an error. Please try refreshing.</p>
            <button onClick={() => window.location.reload()} className="vs-btn-primary">Refresh Page</button>
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
  const [showLoginGate, setShowLoginGate] = useState(false);
  const pollRef = useRef(null);
  const [searchParams] = useSearchParams();

  // Duplicate click guard
  const createLockRef = useRef(false);

  // Post-generation state machine
  const [postGen, dispatchPostGen] = useReducer(postGenReducer, INITIAL_POST_GEN_STATE);

  // Hard timeout tracking
  const hardTimeoutRef = useRef(null);
  const staleTimeoutRef = useRef(null);
  const lastProgressRef = useRef(0);
  const lastProgressTimeRef = useRef(Date.now());

  // WebSocket
  const token = localStorage.getItem('token');
  const { wsRef } = useJobWebSocket(jobId, token);

  // ─── INIT ─────────────────────────────────────────────────────────
  useEffect(() => {
    api.get('/api/story-engine/options').then(r => setOptions(r.data)).catch(() => {});
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
      setStoryText(locState.prefill);
    }
    if (locState?.continueFrom && !savedState) {
      setRemixData({ parent_video_id: locState.continueFrom });
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
          if (rd.remixFrom) {
            setRemixData(rd.remixFrom);
            if (rd.remixFrom.title) setTitle(rd.remixFrom.title.startsWith('From:') ? rd.remixFrom.title : `From: ${rd.remixFrom.title}`);
            if (rd.remixFrom.settings?.animation_style || rd.remixFrom.settings?.style) setAnimStyle(rd.remixFrom.settings.animation_style || rd.remixFrom.settings.style);
            if (rd.remixFrom.settings?.age_group || rd.remixFrom.settings?.ageGroup) setAgeGroup(rd.remixFrom.settings.age_group || rd.remixFrom.settings.ageGroup);
            if (rd.remixFrom.settings?.voice_preset) setVoicePreset(rd.remixFrom.settings.voice_preset);
            setRemixSourceTool(rd.remixFrom.tool || rd.source_tool);
            setRemixSourceTitle(rd.remixFrom.title);
            setShowRemixBanner(true);
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
        // Reconnect to active job if any (refresh safety)
        const active = (res.data.jobs || []).find(j => ['QUEUED', 'PROCESSING'].includes(j.status));
        if (active) {
          setJobId(active.job_id);
          setJob(active);
          setPhase('processing');
          startPolling(active.job_id);
        }
      }
    } catch { /* ignore */ }
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

    // Hard timeout
    hardTimeoutRef.current = setTimeout(() => {
      clearAllTimeouts();
      setPhase('postgen');
      dispatchPostGen({
        type: 'SET_FAILED',
        reason: 'Generation timed out after 5 minutes. Your credits have been preserved.',
        stageDetail: 'Hard timeout — generation took too long',
      });
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
            // Progress hasn't changed in 90 seconds
            toast.warning('Generation is taking longer than usual...', { id: 'stale-warning' });
          }

          if (j.status === 'COMPLETED' || j.status === 'PARTIAL') {
            clearAllTimeouts();
            setPhase('postgen');
            await validateAndResolve(jid, j);
          } else if (j.status === 'FAILED') {
            clearAllTimeouts();
            // Check if there are recoverable assets
            const hasRecoverable = j.has_recoverable_assets || j.fallback?.has_preview || j.fallback?.story_pack_url;
            if (hasRecoverable) {
              setPhase('postgen');
              await validateAndResolve(jid, j);
            } else {
              setPhase('postgen');
              dispatchPostGen({
                type: 'SET_FAILED',
                reason: j.error || 'Generation failed',
                stageDetail: j.error || 'No recoverable assets',
              });
            }
          }
        }
      } catch { /* continue polling */ }
    };
    poll();
    pollRef.current = setInterval(poll, 3000);
  }, [clearAllTimeouts, validateAndResolve]);

  // ─── GENERATE (with duplicate guard) ──────────────────────────────
  const handleGenerate = async () => {
    if (createLockRef.current) return; // Prevent double-click
    setFormError('');

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
    try {
      const payload = {
        title: title.trim(),
        story_text: storyText.trim(),
        animation_style: animStyle,
        age_group: ageGroup,
        voice_preset: voicePreset,
      };
      if (remixData?.parent_video_id) payload.parent_video_id = remixData.parent_video_id;

      const res = await api.post('/api/story-engine/create', payload);
      if (res.data.success) {
        setJobId(res.data.job_id);
        setPhase('processing');
        setFormError('');
        dispatchPostGen({ type: 'RESET' });

        if (res.data.degraded) {
          toast.info(`System is busy — your video will use ${res.data.estimated_scenes} scenes for faster delivery.`);
        } else if (res.data.queue_warning) {
          toast.info(res.data.queue_warning);
        } else {
          toast.success(`Video queued! ${res.data.credits_charged} credits charged.`);
        }
        startPolling(res.data.job_id);
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
        setFormError(admissionMsg || 'Rate limit reached.');
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
        // Zero-friction: save ALL form state, then show gentle login gate
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
    dispatchPostGen({ type: 'RESET' });
    checkRateLimit();
  };

  const viewJob = (j) => {
    setJobId(j.job_id);
    if (['COMPLETED', 'PARTIAL'].includes(j.status)) {
      setJob(j);
      setPhase('postgen');
      validateAndResolve(j.job_id, j);
    } else if (j.status === 'FAILED') {
      if (j.has_recoverable_assets || j.fallback_status) {
        setJob(j);
        setPhase('postgen');
        validateAndResolve(j.job_id, j);
      } else {
        setJob(j);
        setPhase('postgen');
        dispatchPostGen({ type: 'SET_FAILED', reason: j.error || 'Generation failed' });
      }
    } else {
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
              { key: 'result', label: 'Result', icon: Eye, active: phase === 'postgen' },
            ].map((step, i) => (
              <div key={step.key} className="flex items-center">
                {i > 0 && <div className={`w-6 h-px mx-1 ${step.active || (phase === 'postgen') || (phase === 'processing' && i <= ['prompt','scenes','images','voices','result'].indexOf(job?.current_stage || 'scenes')) ? 'bg-[var(--vs-primary-from)]' : 'bg-[var(--vs-border)]'}`} />}
                <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                  step.active ? 'bg-[var(--vs-cta)]/15 text-[var(--vs-text-accent)] border border-[var(--vs-border-glow)]'
                  : (phase === 'postgen' || (phase === 'processing' && i < ['prompt','scenes','images','voices','result'].indexOf(job?.current_stage || 'scenes') + 1))
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

        {phase === 'input' && <InputPhase
          options={options} title={title} setTitle={setTitle}
          storyText={storyText} setStoryText={setStoryText}
          animStyle={animStyle} setAnimStyle={setAnimStyle}
          ageGroup={ageGroup} setAgeGroup={setAgeGroup}
          voicePreset={voicePreset} setVoicePreset={setVoicePreset}
          onGenerate={handleGenerate} submitting={submitting}
          userJobs={userJobs} onViewJob={viewJob}
          rateLimitStatus={rateLimitStatus} formError={formError}
          showRemixBanner={showRemixBanner} remixSourceTool={remixSourceTool}
          remixSourceTitle={remixSourceTitle} onDismissRemix={() => setShowRemixBanner(false)}
          userCredits={userCredits}
          showLoginGate={showLoginGate}
        />}

        {phase === 'processing' && (
          <ProgressiveGeneration
            jobId={jobId}
            wsRef={wsRef}
            initialProgress={job?.progress || 0}
            initialStage={job?.current_stage || 'scenes'}
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

// ─── INPUT PHASE ──────────────────────────────────────────────────────────────
function InputPhase({ options, title, setTitle, storyText, setStoryText,
  animStyle, setAnimStyle, ageGroup, setAgeGroup, voicePreset, setVoicePreset,
  onGenerate, submitting, userJobs, onViewJob, rateLimitStatus, formError,
  showRemixBanner, remixSourceTool, remixSourceTitle, onDismissRemix, userCredits,
  showLoginGate }) {

  const styles = options?.animation_styles || [];
  const ages = options?.age_groups || [];
  const voices = options?.voice_presets || [];
  const activeJobs = userJobs.filter(j => ['QUEUED', 'PROCESSING'].includes(j.status));
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
        <div className="vs-panel p-4 flex items-start gap-3 border-amber-500/30" data-testid="rate-limit-warning">
          <ShieldAlert className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-amber-200 font-medium text-sm">{rateLimitStatus.reason}</p>
            <p className="text-amber-400/60 text-xs mt-1" style={{ fontFamily: 'var(--vs-font-mono)' }}>
              Videos this hour: {rateLimitStatus.recent_count}/{rateLimitStatus.max_per_hour} |
              Active: {rateLimitStatus.concurrent}/{rateLimitStatus.max_concurrent}
            </p>
          </div>
        </div>
      )}

      {showRemixBanner && <RemixBanner sourceTool={remixSourceTool} sourceTitle={remixSourceTitle} onDismiss={onDismissRemix} />}

      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <div>
            <h1 className="vs-h1 mb-2">Create a Story Video</h1>
            <p className="text-[var(--vs-text-secondary)]" style={{ fontFamily: 'var(--vs-font-body)' }}>Enter your story and we'll create an animated video with AI-generated images and voiceover.</p>
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
              <Textarea value={storyText} onChange={e => setStoryText(e.target.value)}
                placeholder="Write your story here... (minimum 50 characters)" rows={8}
                className="bg-[var(--vs-bg-panel)] border-[var(--vs-border)] text-white resize-none focus:border-[var(--vs-primary-from)]" data-testid="story-textarea" />
              <div className="flex justify-between mt-1">
                <p className={`text-xs ${storyText.trim().length < 50 && storyText.length > 0 ? 'text-amber-400' : 'text-[var(--vs-text-muted)]'}`}>
                  {storyText.length} / 10,000 characters {storyText.length > 0 && storyText.trim().length < 50 ? `(need ${50 - storyText.trim().length} more)` : '(min 50)'}
                </p>
              </div>
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
                  '3d_pixar': 'from-sky-400 to-cyan-500',
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
                !canCreate ? 'bg-amber-700 hover:bg-amber-600 text-white' : 'vs-btn-primary'
              }`}
              data-testid="generate-btn">
              {submitting ? <><Loader2 className="w-5 h-5 animate-spin" /> Creating Job...</>
                : !canCreate ? <><ShieldAlert className="w-5 h-5" /> Generation Unavailable</>
                : <><Wand2 className="w-5 h-5" /> Generate Video</>}
            </button>
          )}

          {rateLimitStatus && (
            <p className="text-xs text-[var(--vs-text-muted)] text-center" style={{ fontFamily: 'var(--vs-font-mono)' }}>
              {rateLimitStatus.recent_count}/{rateLimitStatus.max_per_hour} videos this hour
            </p>
          )}
        </div>

        {/* Sidebar */}
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

// ─── POST-GENERATION PHASE (State Machine Driven) ─────────────────────────────
// Renders based on postGen.uiState ONLY. No contradictory states possible.
function PostGenPhase({ postGen, job, jobId, onNew, onResume, onRetryValidation, storyText, animStyle }) {
  const [copied, setCopied] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [showDirections, setShowDirections] = useState(false);
  const [customDirection, setCustomDirection] = useState('');
  const [showSharePrompt, setShowSharePrompt] = useState(false);
  const [showForceShare, setShowForceShare] = useState(false);
  const [showAutoNext, setShowAutoNext] = useState(false);
  const navigate = useNavigate();
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
      const token = localStorage.getItem('token');
      if (!token) return;
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
    FAILED: { bg: 'bg-red-500/10 border-red-500/30', icon: <AlertCircle className="w-5 h-5 text-red-400" />, title: 'Generation Issue', subtitle: failReason || 'Something went wrong' },
  };
  const statusCfg = STATUS_CONFIG[uiState] || STATUS_CONFIG.VALIDATING;

  const handleCopyLink = () => {
    const url = shareUrl || downloadUrl;
    if (url) {
      navigator.clipboard.writeText(url).then(() => {
        setCopied(true);
        toast.success('Link copied!');
        setTimeout(() => setCopied(false), 2000);
      });
    }
  };

  const handleDownload = async () => {
    if (!downloadReady || !downloadUrl) return;
    setDownloading(true);
    try {
      window.open(downloadUrl, '_blank');
      toast.success('Download started!');
    } catch {
      toast.error('Download failed');
    } finally {
      setDownloading(false);
    }
  };

  const handleShare = (platform) => {
    const url = encodeURIComponent(shareUrl || downloadUrl || '');
    const text = encodeURIComponent(`Check out this AI-generated story video: "${displayTitle}" — Made with Visionary Suite`);
    const urls = {
      twitter: `https://twitter.com/intent/tweet?text=${text}&url=${url}`,
      whatsapp: `https://wa.me/?text=${text}%20${url}`,
    };
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
          downloadUrl={downloadUrl}
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

      <div className="grid lg:grid-cols-5 gap-6">
        {/* LEFT: Preview Area */}
        <div className="lg:col-span-3">
          {/* Preview — TRUTH: only show when we have a real asset */}
          {uiState === 'VALIDATING' ? (
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
              <CheckCircle className="w-12 h-12 text-emerald-400 mx-auto mb-4" />
              <h3 className="text-xl font-bold text-white mb-2">Your video is ready!</h3>
              <p className="text-slate-400 text-sm mb-6">Click below to view or download your creation.</p>
              <div className="flex gap-3 justify-center">
                <Button onClick={() => window.open(downloadUrl, '_blank')} className="bg-emerald-600 hover:bg-emerald-700" data-testid="view-video-btn">
                  <Play className="w-4 h-4 mr-2" /> View Video
                </Button>
                <Button onClick={handleDownload} variant="outline" className="border-emerald-500/50 text-emerald-400 hover:bg-emerald-500/10" data-testid="download-video-inline-btn">
                  <Download className="w-4 h-4 mr-2" /> Download
                </Button>
              </div>
            </div>
          ) : uiState === 'FAILED' ? (
            /* Generation failed — no fake preview */
            <div className="rounded-xl border border-red-500/30 bg-red-500/5 p-8 text-center" data-testid="generation-failed-panel">
              <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
              <h3 className="text-lg font-bold text-white mb-2">Generation Issue</h3>
              <p className="text-red-300 text-sm mb-4">{failReason || 'Video generation did not produce output.'}</p>
              <div className="flex gap-3 justify-center">
                <Button onClick={onResume} className="bg-purple-600 hover:bg-purple-700" data-testid="retry-failed-btn">
                  <RotateCcw className="w-4 h-4 mr-2" /> Retry
                </Button>
                <Button onClick={onNew} variant="outline" className="border-slate-600 text-slate-300" data-testid="start-fresh-btn">
                  Start Fresh
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
              downloadUrl={downloadUrl}
            />
          )}

          {/* Download — only when downloadReady is true */}
          <Button
            onClick={handleDownload}
            disabled={!downloadReady || downloading || uiState === 'VALIDATING'}
            className="w-full bg-emerald-600 hover:bg-emerald-700 disabled:opacity-40 disabled:cursor-not-allowed"
            data-testid="download-btn"
          >
            {downloading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Download className="w-4 h-4 mr-2" />}
            {downloading ? 'Downloading...' : !downloadReady ? (uiState === 'VALIDATING' ? 'Verifying...' : 'Unavailable') : 'Download Video'}
          </Button>

          {/* Story Pack */}
          {storyPackUrl && downloadReady && (
            <a href={storyPackUrl} target="_blank" rel="noopener noreferrer" className="block">
              <Button variant="outline" className="w-full border-teal-500/50 text-teal-400 hover:bg-teal-500/10" data-testid="download-pack-btn">
                <Package className="w-4 h-4 mr-2" /> Download Story Pack
              </Button>
            </a>
          )}

          {/* Share — only when shareReady is true */}
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleCopyLink} disabled={!shareReady && !downloadReady} className="flex-1 border-slate-700 text-slate-300 hover:text-white text-xs disabled:opacity-40" data-testid="share-copy-btn">
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

          {/* FAILED state: show reason + retry/resume */}
          {uiState === 'FAILED' && (
            <div className="bg-red-500/5 border border-red-500/20 rounded-lg p-4 space-y-3" data-testid="fail-details">
              <p className="text-red-300 text-sm">{failReason}</p>
              <div className="flex gap-2">
                <Button onClick={onResume} size="sm" className="bg-purple-600 hover:bg-purple-700 flex-1" data-testid="resume-btn">
                  <RotateCcw className="w-3.5 h-3.5 mr-1" /> Resume
                </Button>
                <Button onClick={onNew} size="sm" variant="outline" className="border-slate-700 text-slate-300 flex-1" data-testid="start-over-btn">
                  Start Over
                </Button>
              </div>
              <p className="text-xs text-slate-500">Credits have been preserved for retry.</p>
            </div>
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
          {/* ═══ AUTO-NEXT TRIGGER — Session Chaining ═══ */}
          {showAutoNext && (
            <div className="relative overflow-hidden rounded-2xl border border-violet-500/30 bg-gradient-to-r from-violet-600/[0.08] to-rose-600/[0.08] p-5" style={{ animation: 'slideIn 0.4s ease-out' }} data-testid="auto-next-trigger">
              <div className="text-center mb-4">
                <p className="text-xs text-amber-400 font-bold uppercase tracking-wider mb-1">That was just the beginning...</p>
                <h3 className="text-lg font-black text-white">What happens next?</h3>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => handleContinue(CONTINUE_DIRECTIONS[0])}
                  className="flex-1 h-12 rounded-xl bg-gradient-to-r from-violet-600 to-rose-600 text-white text-sm font-bold flex items-center justify-center gap-2 hover:opacity-90 shadow-lg shadow-violet-500/20"
                  style={{ animation: 'cta-glow 2s ease-in-out infinite' }}
                  data-testid="auto-next-continue-btn"
                >
                  <Play className="w-5 h-5" /> Continue Next Episode <ArrowRight className="w-4 h-4" />
                </button>
                {shareReady && (
                  <button
                    onClick={() => handleShare('copy')}
                    className="h-12 px-5 rounded-xl border border-white/[0.1] bg-white/[0.03] text-sm text-slate-300 font-semibold flex items-center gap-2 hover:text-white hover:border-white/20 transition-all"
                    data-testid="auto-next-share-btn"
                  >
                    <Share2 className="w-4 h-4" /> Share
                  </button>
                )}
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

          {/* ═══ PRIMARY: Continue Story (BIGGEST BUTTON, FIRST POSITION) ═══ */}
          <button
            onClick={() => handleContinue(CONTINUE_DIRECTIONS[0])}
            className="w-full group relative overflow-hidden rounded-2xl p-6 text-left transition-all hover:scale-[1.01] active:scale-[0.99]"
            data-testid="primary-continue-btn"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-violet-600 to-rose-600 opacity-90 group-hover:opacity-100 transition-opacity" />
            <div className="relative z-10 flex items-center gap-4">
              <div className="w-14 h-14 rounded-xl bg-white/10 flex items-center justify-center flex-shrink-0">
                <Play className="w-7 h-7 text-white" />
              </div>
              <div className="flex-1">
                <span className="text-xl font-black text-white block mb-1">Continue Story</span>
                <span className="text-sm text-white/70">Pick up right where it left off — higher stakes await</span>
              </div>
              <ArrowRight className="w-6 h-6 text-white/40 group-hover:text-white group-hover:translate-x-1 transition-all" />
            </div>
          </button>

          {/* ═══ SECONDARY: Add Twist / Make Funny / Next Episode ═══ */}
          <div className="grid grid-cols-3 gap-3" data-testid="secondary-actions">
            <button
              onClick={() => handleContinue(CONTINUE_DIRECTIONS[1])}
              className="p-4 rounded-xl border border-amber-500/20 bg-amber-500/[0.04] hover:bg-amber-500/[0.08] transition-all text-center group"
              data-testid="add-twist-btn"
            >
              <Sparkles className="w-5 h-5 text-amber-400 mx-auto mb-2" />
              <span className="text-sm font-bold text-white block">Add Twist</span>
              <span className="text-[10px] text-slate-500">Unexpected reveal</span>
            </button>
            <button
              onClick={() => {
                const baseStory = storyText || job?.story_text || '';
                const funnyPrompt = `[Funny Version of "${displayTitle}"]\n\nOriginal story:\n${baseStory.slice(0, 500)}...\n\nDirection: Convert this into a hilariously funny version while keeping core events. Add comedic timing, funny dialogue, and absurd situations.`;
                localStorage.setItem('remix_video', JSON.stringify({
                  parent_video_id: jobId || job?.job_id,
                  title: `Funny: ${displayTitle}`,
                  story_text: funnyPrompt,
                  animation_style: currentStyle,
                  age_group: job?.age_group,
                  voice_preset: job?.voice_preset,
                }));
                navigate('/app/story-video-studio?remix=funny');
                toast.success('Creating funny version!');
              }}
              className="p-4 rounded-xl border border-pink-500/20 bg-pink-500/[0.04] hover:bg-pink-500/[0.08] transition-all text-center group"
              data-testid="make-funny-btn"
            >
              <AlertCircle className="w-5 h-5 text-pink-400 mx-auto mb-2" />
              <span className="text-sm font-bold text-white block">Make Funny</span>
              <span className="text-[10px] text-slate-500">Comedy version</span>
            </button>
            <button
              onClick={() => handleContinue(CONTINUE_DIRECTIONS[3])}
              className="p-4 rounded-xl border border-purple-500/20 bg-purple-500/[0.04] hover:bg-purple-500/[0.08] transition-all text-center group"
              data-testid="next-episode-btn"
            >
              <Film className="w-5 h-5 text-purple-400 mx-auto mb-2" />
              <span className="text-sm font-bold text-white block">Next Episode</span>
              <span className="text-[10px] text-slate-500">New adventure</span>
            </button>
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
                { platform: 'whatsapp', label: 'WhatsApp', color: 'bg-emerald-600 hover:bg-emerald-500' },
                { platform: 'twitter', label: 'X', color: 'bg-slate-700 hover:bg-slate-600' },
                { platform: 'instagram', label: 'IG', color: 'bg-pink-600 hover:bg-pink-500' },
                { platform: 'copy', label: 'Copy Link', color: 'bg-slate-800 hover:bg-slate-700' },
              ].map(s => (
                <button
                  key={s.platform}
                  onClick={async () => {
                    if (s.platform === 'copy') {
                      handleCopyLink();
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
                    } catch {}
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
            <Button
              onClick={handleDownload}
              disabled={!downloadReady || downloading}
              variant="outline"
              className="flex-1 border-slate-700 text-slate-300 hover:text-white disabled:opacity-40"
              data-testid="download-btn"
            >
              {downloading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Download className="w-4 h-4 mr-2" />}
              Download
            </Button>
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
                        if (customDirection.trim()) handleContinue(d);
                        return;
                      }
                      handleContinue(d);
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
                  onClick={() => handleStyleRemix(s.id)}
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

          {/* New Video */}
          <Button onClick={onNew} variant="ghost" className="w-full text-slate-500 hover:text-white" data-testid="new-video-btn">
            <Sparkles className="w-4 h-4 mr-2" /> Create Entirely New Story
          </Button>
        </>
      )}
    </div>
  );
}
