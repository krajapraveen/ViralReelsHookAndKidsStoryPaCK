import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Progress } from '../components/ui/progress';
import { toast } from 'sonner';
import api from '../utils/api';
import {
  ArrowLeft, Wand2, Loader2, Film, Image, Mic, CheckCircle,
  Play, Download, RefreshCw, AlertCircle, Clock, Coins,
  Video, Upload, BookOpen, Sparkles, RotateCcw, XCircle, Eye, Package,
  Share2, Link2, Copy, ExternalLink, RefreshCcw as Remix, ShieldAlert
} from 'lucide-react';
import UpsellModal from '../components/UpsellModal';
import CreationActionsBar from '../components/CreationActionsBar';
import ContextualUpgrade from '../components/ContextualUpgrade';

const STAGE_ORDER = ['scenes', 'images', 'voices', 'render', 'upload'];
const STAGE_ICONS = { scenes: BookOpen, images: Image, voices: Mic, render: Video, upload: Upload };
const STAGE_LABELS = { scenes: 'Scenes', images: 'Images', voices: 'Voices', render: 'Render', upload: 'Upload' };

// Error boundary to catch React render crashes
class StudioErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { hasError: false, error: null }; }
  static getDerivedStateFromError(error) { return { hasError: true, error }; }
  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-slate-950 flex items-center justify-center p-8">
          <div className="max-w-md text-center" data-testid="error-boundary">
            <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-white mb-2">Something went wrong</h2>
            <p className="text-slate-400 mb-6">The video studio encountered an error. Please try refreshing the page.</p>
            <Button onClick={() => window.location.reload()} className="bg-purple-600 hover:bg-purple-700">
              Refresh Page
            </Button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

function StoryVideoPipelineInner() {
  const navigate = useNavigate();
  const [phase, setPhase] = useState('input'); // input | processing | done | error
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
  const [remixData, setRemixData] = useState(null);
  const [rateLimitStatus, setRateLimitStatus] = useState(null);
  const [formError, setFormError] = useState('');
  const pollRef = useRef(null);
  const [searchParams] = useSearchParams();

  useEffect(() => {
    api.get('/api/pipeline/options').then(r => setOptions(r.data)).catch(() => {});
    loadUserJobs();
    checkUpsell();
    checkRateLimit();

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

    // Handle new remix_data from Remix & Variations Engine
    const newRemixData = localStorage.getItem('remix_data');
    if (newRemixData && !isRemix) {
      try {
        const rd = JSON.parse(newRemixData);
        if (rd.prompt) {
          setStoryText(rd.prompt);
        }
        if (rd.remixFrom) {
          setRemixData(rd.remixFrom);
          if (rd.remixFrom.title) setTitle(`Remix: ${rd.remixFrom.title}`);
          if (rd.remixFrom.settings?.animation_style) setAnimStyle(rd.remixFrom.settings.animation_style);
          if (rd.remixFrom.settings?.age_group) setAgeGroup(rd.remixFrom.settings.age_group);
          if (rd.remixFrom.settings?.voice_preset) setVoicePreset(rd.remixFrom.settings.voice_preset);
        }
        setTimeout(() => localStorage.removeItem('remix_data'), 1000);
      } catch { /* ignore */ }
    }

    const urlPrompt = searchParams.get('prompt');
    const savedPrompt = localStorage.getItem('onboarding_prompt');
    const prompt = urlPrompt || savedPrompt;
    if (prompt && !isRemix) {
      setStoryText(prompt);
      setShowWelcome(true);
      localStorage.removeItem('onboarding_prompt');
    }

    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [searchParams]);

  const loadUserJobs = async () => {
    try {
      const res = await api.get('/api/pipeline/user-jobs');
      if (res.data.success) {
        setUserJobs(res.data.jobs || []);
        const active = (res.data.jobs || []).find(j => ['QUEUED', 'PROCESSING'].includes(j.status));
        if (active) {
          setJobId(active.job_id);
          setPhase('processing');
          startPolling(active.job_id);
        }
      }
    } catch { /* ignore */ }
  };

  const checkUpsell = async () => {
    try {
      const res = await api.get('/api/credits/check-upsell');
      if (res.data.show_upsell) {
        setUserCredits(res.data.credits);
        setShowUpsell(true);
      }
    } catch { /* ignore */ }
  };

  const checkRateLimit = async () => {
    try {
      const res = await api.get('/api/pipeline/rate-limit-status');
      setRateLimitStatus(res.data);
    } catch { /* ignore */ }
  };

  const startPolling = useCallback((jid) => {
    if (pollRef.current) clearInterval(pollRef.current);
    const poll = async () => {
      try {
        const res = await api.get(`/api/pipeline/status/${jid}`);
        if (res.data.success) {
          const j = res.data.job;
          setJob(j);
          if (j.status === 'COMPLETED') {
            clearInterval(pollRef.current);
            pollRef.current = null;
            setPhase('done');
            toast.success('Video generated successfully!');
          } else if (j.status === 'PARTIAL') {
            clearInterval(pollRef.current);
            pollRef.current = null;
            if (j.fallback?.fallback_video_url) {
              toast.info('Slideshow video ready! Redirecting to preview...', { duration: 4000 });
            } else {
              toast.info('Story assets ready! Redirecting to preview...', { duration: 4000 });
            }
            setTimeout(() => navigate(`/app/story-preview/${jid}`), 1500);
          } else if (j.status === 'FAILED') {
            clearInterval(pollRef.current);
            pollRef.current = null;
            if (j.fallback?.has_preview || j.fallback?.story_pack_url) {
              toast.info('Video render failed but your story assets are available!', { duration: 5000 });
              setTimeout(() => navigate(`/app/story-preview/${jid}`), 1500);
            } else {
              setPhase('error');
            }
          }
        }
      } catch { /* continue polling */ }
    };
    poll();
    pollRef.current = setInterval(poll, 3000);
  }, [navigate]);

  const handleGenerate = async () => {
    setFormError('');

    // Validation
    if (!title.trim()) {
      setFormError('Please enter a title for your video.');
      return;
    }
    if (title.trim().length < 3) {
      setFormError('Title must be at least 3 characters.');
      return;
    }
    if (title.trim().length > 100) {
      setFormError('Title must be 100 characters or less.');
      return;
    }
    if (!storyText.trim()) {
      setFormError('Please enter a story to generate a video from.');
      return;
    }
    if (storyText.trim().length < 50) {
      setFormError(`Story must be at least 50 characters. You have ${storyText.trim().length} — need ${50 - storyText.trim().length} more.`);
      return;
    }

    // Check rate limit before calling API
    if (rateLimitStatus && !rateLimitStatus.can_create) {
      setFormError(rateLimitStatus.reason || 'You cannot create a video right now. Please wait.');
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        title: title.trim(),
        story_text: storyText.trim(),
        animation_style: animStyle,
        age_group: ageGroup,
        voice_preset: voicePreset,
      };
      if (remixData?.parent_video_id) {
        payload.parent_video_id = remixData.parent_video_id;
      }
      const res = await api.post('/api/pipeline/create', payload);
      if (res.data.success) {
        setJobId(res.data.job_id);
        setPhase('processing');
        setFormError('');
        toast.success(`Video queued! ${res.data.credits_charged} credits charged.`);
        startPolling(res.data.job_id);
      } else {
        setFormError(res.data.detail || res.data.message || 'Failed to create video. Please try again.');
      }
    } catch (e) {
      const status = e.response?.status;
      const rawDetail = e.response?.data?.detail;
      const detail = typeof rawDetail === 'string' ? rawDetail : (rawDetail ? JSON.stringify(rawDetail) : '');
      if (status === 429) {
        setFormError(detail || 'Rate limit reached. Please wait before generating another video.');
        checkRateLimit();
      } else if (status === 402 || (detail && detail.toLowerCase().includes('credit'))) {
        setFormError('Insufficient credits. Please purchase more credits to continue.');
        setShowUpsell(true);
      } else if (status === 401) {
        setFormError('Your session has expired. Please log in again.');
      } else {
        setFormError(detail || 'An error occurred while creating the video. Please try again.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleResume = async () => {
    if (!jobId) return;
    try {
      await api.post(`/api/pipeline/resume/${jobId}`);
      setPhase('processing');
      startPolling(jobId);
      toast.info('Resuming from last checkpoint...');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to resume');
    }
  };

  const handleNewVideo = () => {
    setPhase('input');
    setJobId(null);
    setJob(null);
    setTitle('');
    setStoryText('');
    setFormError('');
    setRemixData(null);
    checkRateLimit();
  };

  const viewJob = (j) => {
    setJobId(j.job_id);
    if (j.status === 'COMPLETED') { setJob(j); setPhase('done'); }
    else if (j.status === 'PARTIAL') { navigate(`/app/story-preview/${j.job_id}`); }
    else if (j.status === 'FAILED') {
      if (j.fallback_status && j.fallback_status !== 'none') {
        navigate(`/app/story-preview/${j.job_id}`);
      } else {
        setJob(j); setPhase('error');
      }
    }
    else { setPhase('processing'); startPolling(j.job_id); }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-purple-950/30 to-slate-950">
      <header className="border-b border-slate-800/50 bg-slate-950/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link to="/app" className="text-slate-400 hover:text-white"><ArrowLeft className="w-5 h-5" /></Link>
            <Film className="w-5 h-5 text-purple-400" />
            <span className="font-semibold text-white text-lg">Story → Video</span>
          </div>
          {phase !== 'input' && (
            <Button onClick={handleNewVideo} variant="outline" size="sm" className="border-slate-700 text-slate-300" data-testid="new-video-header-btn">
              <Sparkles className="w-4 h-4 mr-1" /> New Video
            </Button>
          )}
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {showUpsell && <UpsellModal credits={userCredits} onClose={() => setShowUpsell(false)} />}

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
            <p className="text-slate-400 text-sm max-w-md mx-auto mb-4">Your story is pre-filled below. Add a title, pick a style, and hit Generate. AI does the rest in ~90 seconds.</p>
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
        />}
        {phase === 'processing' && <ProcessingPhase job={job} />}
        {phase === 'done' && <DonePhase job={job} jobId={jobId} onNew={handleNewVideo} storyText={storyText} animStyle={animStyle} />}
        {phase === 'error' && <ErrorPhase job={job} onResume={handleResume} onNew={handleNewVideo} />}
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

// ─── INPUT PHASE ──────────────────────────────────────────────────────────

function InputPhase({ options, title, setTitle, storyText, setStoryText,
  animStyle, setAnimStyle, ageGroup, setAgeGroup, voicePreset, setVoicePreset,
  onGenerate, submitting, userJobs, onViewJob, rateLimitStatus, formError }) {

  const styles = options?.animation_styles || [];
  const ages = options?.age_groups || [];
  const voices = options?.voice_presets || [];
  const activeJobs = userJobs.filter(j => ['QUEUED', 'PROCESSING'].includes(j.status));
  const recentJobs = userJobs.filter(j => j.status === 'COMPLETED').slice(0, 3);

  const canCreate = rateLimitStatus?.can_create !== false;

  return (
    <div className="space-y-8" data-testid="input-phase">
      {/* Active jobs banner */}
      {activeJobs.length > 0 && (
        <div className="bg-purple-900/30 border border-purple-500/30 rounded-xl p-4 flex items-center justify-between" data-testid="active-job-banner">
          <div className="flex items-center gap-3">
            <Loader2 className="w-5 h-5 text-purple-400 animate-spin" />
            <span className="text-purple-200">You have {activeJobs.length} video{activeJobs.length > 1 ? 's' : ''} in progress</span>
          </div>
          <Button onClick={() => onViewJob(activeJobs[0])} size="sm" className="bg-purple-600 hover:bg-purple-700" data-testid="view-progress-btn">
            <Eye className="w-4 h-4 mr-1" /> View Progress
          </Button>
        </div>
      )}

      {/* Rate limit warning */}
      {rateLimitStatus && !rateLimitStatus.can_create && (
        <div className="bg-amber-900/20 border border-amber-500/30 rounded-xl p-4 flex items-start gap-3" data-testid="rate-limit-warning">
          <ShieldAlert className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-amber-200 font-medium text-sm">{rateLimitStatus.reason}</p>
            <p className="text-amber-400/60 text-xs mt-1">
              Videos this hour: {rateLimitStatus.recent_count}/{rateLimitStatus.max_per_hour} |
              Active: {rateLimitStatus.concurrent}/{rateLimitStatus.max_concurrent}
            </p>
          </div>
        </div>
      )}

      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Create a Story Video</h1>
            <p className="text-slate-400">Enter your story and we'll create an animated video with AI-generated images and voiceover.</p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-slate-300 mb-1 block">Title <span className="text-red-400">*</span></label>
              <Input value={title} onChange={e => setTitle(e.target.value)} placeholder="My Amazing Story..."
                className="bg-slate-800/50 border-slate-700 text-white" data-testid="title-input" maxLength={100} />
              {title.length > 0 && title.trim().length < 3 && (
                <p className="text-xs text-amber-400 mt-1">Title needs at least 3 characters</p>
              )}
            </div>

            <div>
              <label className="text-sm font-medium text-slate-300 mb-1 block">Story Text <span className="text-red-400">*</span></label>
              <Textarea value={storyText} onChange={e => setStoryText(e.target.value)}
                placeholder="Write your story here... (minimum 50 characters)" rows={8}
                className="bg-slate-800/50 border-slate-700 text-white resize-none" data-testid="story-textarea" />
              <div className="flex justify-between mt-1">
                <p className={`text-xs ${storyText.trim().length < 50 && storyText.length > 0 ? 'text-amber-400' : 'text-slate-500'}`}>
                  {storyText.length} / 10,000 characters {storyText.length > 0 && storyText.trim().length < 50 ? `(need ${50 - storyText.trim().length} more)` : '(min 50)'}
                </p>
              </div>
            </div>
          </div>

          {/* Animation Style */}
          <div>
            <label className="text-sm font-medium text-slate-300 mb-2 block">Animation Style</label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2" data-testid="style-grid">
              {styles.map(s => (
                <button key={s.id} onClick={() => setAnimStyle(s.id)}
                  className={`p-3 rounded-lg border text-left transition-all ${animStyle === s.id
                    ? 'border-purple-500 bg-purple-500/20 text-white'
                    : 'border-slate-700 bg-slate-800/30 text-slate-400 hover:border-slate-600'}`}
                  data-testid={`style-${s.id}`}>
                  <span className="text-sm font-medium">{s.name}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Age + Voice row */}
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-slate-300 mb-2 block">Target Age</label>
              <div className="space-y-1">
                {ages.map(a => (
                  <button key={a.id} onClick={() => setAgeGroup(a.id)}
                    className={`w-full p-2 rounded-lg border text-left text-sm transition-all ${ageGroup === a.id
                      ? 'border-purple-500 bg-purple-500/20 text-white'
                      : 'border-slate-700/50 bg-slate-800/30 text-slate-400 hover:border-slate-600'}`}
                    data-testid={`age-${a.id}`}>
                    {a.name}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-300 mb-2 block">Narrator Voice</label>
              <div className="space-y-1">
                {voices.map(v => (
                  <button key={v.id} onClick={() => setVoicePreset(v.id)}
                    className={`w-full p-2 rounded-lg border text-left text-sm transition-all ${voicePreset === v.id
                      ? 'border-purple-500 bg-purple-500/20 text-white'
                      : 'border-slate-700/50 bg-slate-800/30 text-slate-400 hover:border-slate-600'}`}
                    data-testid={`voice-${v.id}`}>
                    {v.name}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Form error */}
          {formError && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex items-start gap-3" data-testid="form-error">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-red-300 text-sm">{formError}</p>
            </div>
          )}

          {/* Generate Button — always clickable so user gets feedback */}
          <Button onClick={onGenerate} disabled={submitting}
            className={`w-full h-14 text-lg ${!canCreate ? 'bg-amber-700 hover:bg-amber-600' : 'bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700'} disabled:opacity-50 disabled:cursor-not-allowed`}
            data-testid="generate-btn">
            {submitting ? <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> Creating Job...</>
              : !canCreate ? <><ShieldAlert className="w-5 h-5 mr-2" /> Generation Unavailable — {rateLimitStatus?.reason || 'Rate limited'}</>
              : <><Wand2 className="w-5 h-5 mr-2" /> Generate Video</>}
          </Button>

          {/* Rate limit info */}
          {rateLimitStatus && (
            <p className="text-xs text-slate-600 text-center">
              {rateLimitStatus.recent_count}/{rateLimitStatus.max_per_hour} videos this hour
            </p>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wide">Recent Videos</h3>
          {recentJobs.length === 0 && <p className="text-sm text-slate-500">No videos yet. Create your first!</p>}
          {recentJobs.map(j => (
            <button key={j.job_id} onClick={() => onViewJob(j)}
              className="w-full p-3 rounded-lg border border-slate-700/50 bg-slate-800/30 text-left hover:border-purple-500/30 transition-all"
              data-testid={`recent-job-${j.job_id}`}>
              <p className="text-sm font-medium text-white truncate">{j.title}</p>
              <p className="text-xs text-slate-500 mt-1">{new Date(j.created_at).toLocaleDateString()}</p>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── PROCESSING PHASE ─────────────────────────────────────────────────────

function ProcessingPhase({ job }) {
  if (!job) return (
    <div className="flex items-center justify-center py-20" data-testid="processing-loading">
      <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
      <span className="ml-3 text-slate-400">Connecting to pipeline...</span>
    </div>
  );

  const sceneProgress = job.scene_progress || [];
  const stages = job.stages || {};

  return (
    <div className="space-y-8" data-testid="processing-phase">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-white">{job.title || 'Generating Video...'}</h2>
        <p className="text-slate-400 mt-1">{job.current_step || 'Processing...'}</p>
      </div>

      <div className="max-w-2xl mx-auto">
        <Progress value={job.progress || 0} className="h-3" />
        <p className="text-center text-sm text-slate-400 mt-2">{job.progress || 0}%</p>
      </div>

      <div className="flex justify-center gap-2" data-testid="stage-indicators">
        {STAGE_ORDER.map((name) => {
          const Icon = STAGE_ICONS[name];
          const s = stages[name] || {};
          const isComplete = s.status === 'COMPLETED';
          const isRunning = s.status === 'RUNNING' || s.status === 'RETRYING';
          const isFailed = s.status === 'FAILED';
          return (
            <div key={name} className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all
              ${isComplete ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                : isRunning ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30 animate-pulse'
                : isFailed ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                : 'bg-slate-800/50 text-slate-500 border border-slate-700/30'}`}
              data-testid={`stage-${name}`}>
              {isComplete ? <CheckCircle className="w-4 h-4" />
                : isRunning ? <Loader2 className="w-4 h-4 animate-spin" />
                : isFailed ? <XCircle className="w-4 h-4" />
                : <Icon className="w-4 h-4" />}
              {STAGE_LABELS[name]}
              {s.retry_count > 0 && <span className="text-xs opacity-60">(retry {s.retry_count})</span>}
            </div>
          );
        })}
      </div>

      {sceneProgress.length > 0 && (
        <div data-testid="filmstrip">
          <h3 className="text-sm font-medium text-slate-400 mb-3 text-center">Scene Progress</h3>
          <div className="flex justify-center gap-3 flex-wrap">
            {sceneProgress.map(sp => (
              <div key={sp.scene_number}
                className={`w-32 rounded-lg overflow-hidden border transition-all ${
                  sp.has_image ? 'border-green-500/40' : 'border-slate-700/40'}`}
                data-testid={`scene-thumb-${sp.scene_number}`}>
                {sp.has_image && sp.image_url ? (
                  <img src={sp.image_url} alt={`Scene ${sp.scene_number}`} className="w-32 h-20 object-cover" />
                ) : (
                  <div className="w-32 h-20 bg-slate-800/50 flex items-center justify-center">
                    {job.current_stage === 'images' ? <Loader2 className="w-5 h-5 text-purple-400 animate-spin" /> : <Image className="w-5 h-5 text-slate-600" />}
                  </div>
                )}
                <div className="p-1.5 bg-slate-900/80">
                  <p className="text-xs text-slate-400 truncate">{sp.title}</p>
                  <div className="flex gap-1 mt-0.5">
                    {sp.has_image && <CheckCircle className="w-3 h-3 text-green-400" />}
                    {sp.has_voice && <Mic className="w-3 h-3 text-blue-400" />}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="text-center">
        <p className="text-xs text-slate-500 flex items-center justify-center gap-1">
          <Clock className="w-3 h-3" /> Video generation continues safely in the background. You can leave and return.
        </p>
      </div>
    </div>
  );
}

// ─── DONE PHASE ───────────────────────────────────────────────────────────

function DonePhase({ job, jobId, onNew, storyText, animStyle }) {
  const [copied, setCopied] = useState(false);
  if (!job) return null;
  const timing = job.timing || {};

  const handleCopyLink = () => {
    if (job.output_url) {
      navigator.clipboard.writeText(job.output_url).then(() => {
        setCopied(true);
        toast.success('Video link copied!');
        setTimeout(() => setCopied(false), 2000);
      });
    }
  };

  const handleShare = (platform) => {
    const url = encodeURIComponent(job.output_url || '');
    const text = encodeURIComponent(`Check out this AI-generated story video: "${job.title}" — Made with Visionary Suite`);
    const urls = {
      twitter: `https://twitter.com/intent/tweet?text=${text}&url=${url}`,
      facebook: `https://www.facebook.com/sharer/sharer.php?u=${url}`,
      linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${url}`,
      whatsapp: `https://wa.me/?text=${text}%20${url}`,
    };
    if (urls[platform]) window.open(urls[platform], '_blank', 'width=600,height=400');
  };

  return (
    <div className="space-y-8" data-testid="done-phase">
      <div className="text-center">
        <div className="w-16 h-16 mx-auto bg-green-500/20 rounded-full flex items-center justify-center mb-4">
          <CheckCircle className="w-8 h-8 text-green-400" />
        </div>
        <h2 className="text-2xl font-bold text-white">{job.title}</h2>
        <p className="text-green-400 mt-1">Your AI video is ready!</p>
      </div>

      {job.output_url && (
        <div className="max-w-3xl mx-auto">
          <div className="rounded-xl overflow-hidden border border-slate-700/50 bg-black" data-testid="video-player">
            <video src={job.output_url} controls className="w-full" preload="metadata" />
          </div>

          <div className="flex justify-center gap-3 mt-6">
            <a href={job.output_url} download target="_blank" rel="noopener noreferrer">
              <Button className="bg-indigo-600 hover:bg-indigo-700" data-testid="download-btn">
                <Download className="w-4 h-4 mr-2" /> Download Video
              </Button>
            </a>
            <Button onClick={handleCopyLink} variant="outline" className="border-slate-700 text-slate-300" data-testid="copy-link-btn">
              {copied ? <CheckCircle className="w-4 h-4 mr-2 text-green-400" /> : <Link2 className="w-4 h-4 mr-2" />}
              {copied ? 'Copied!' : 'Copy Link'}
            </Button>
          </div>

          <div className="mt-6 p-4 rounded-xl bg-slate-800/30 border border-slate-700/30" data-testid="share-section">
            <p className="text-sm text-slate-400 text-center mb-3 flex items-center justify-center gap-2">
              <Share2 className="w-4 h-4" /> Share your creation
            </p>
            <div className="flex justify-center gap-3">
              <button onClick={() => handleShare('twitter')} className="p-2.5 rounded-xl bg-slate-700/50 hover:bg-[#1DA1F2]/20 border border-slate-600/50 hover:border-[#1DA1F2]/50 transition-all" data-testid="share-twitter"><span className="text-sm font-bold text-slate-300">X</span></button>
              <button onClick={() => handleShare('facebook')} className="p-2.5 rounded-xl bg-slate-700/50 hover:bg-[#1877F2]/20 border border-slate-600/50 hover:border-[#1877F2]/50 transition-all" data-testid="share-facebook"><span className="text-sm font-bold text-slate-300">f</span></button>
              <button onClick={() => handleShare('whatsapp')} className="p-2.5 rounded-xl bg-slate-700/50 hover:bg-[#25D366]/20 border border-slate-600/50 hover:border-[#25D366]/50 transition-all" data-testid="share-whatsapp"><span className="text-sm font-bold text-slate-300">W</span></button>
              <button onClick={() => handleShare('linkedin')} className="p-2.5 rounded-xl bg-slate-700/50 hover:bg-[#0A66C2]/20 border border-slate-600/50 hover:border-[#0A66C2]/50 transition-all" data-testid="share-linkedin"><span className="text-sm font-bold text-slate-300">in</span></button>
            </div>
          </div>

          <div className="text-center mt-6">
            <Button onClick={onNew} variant="ghost" className="text-slate-400 hover:text-white" data-testid="new-video-btn">
              <Sparkles className="w-4 h-4 mr-2" /> Create Another Video
            </Button>
          </div>

          {/* Remix & Variations Engine */}
          <CreationActionsBar
            toolType="story-video-studio"
            originalPrompt={storyText || job.story_text || job.title || ''}
            originalSettings={{ style: animStyle || job.animation_style, ageGroup: job.age_group }}
            parentGenerationId={jobId || job.job_id}
            remixSourceTitle={job.title}
          />

          {/* Contextual Upgrade */}
          <ContextualUpgrade trigger="after_generation" sourcePage="story_video_studio" />
        </div>
      )}

      {!job.output_url && (
        <div className="text-center py-8" data-testid="no-output-warning">
          <AlertCircle className="w-8 h-8 text-amber-400 mx-auto mb-3" />
          <p className="text-amber-300">Video completed but output URL is missing. Please try generating again.</p>
          <Button onClick={onNew} className="mt-4 bg-purple-600 hover:bg-purple-700">Create New Video</Button>
        </div>
      )}

      {(job.scene_progress || []).length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-slate-400 mb-3 text-center">Scenes</h3>
          <div className="flex justify-center gap-3 flex-wrap">
            {(job.scene_progress || []).map(sp => sp.has_image && sp.image_url && (
              <img key={sp.scene_number} src={sp.image_url} alt={`Scene ${sp.scene_number}`}
                className="w-28 h-18 object-cover rounded-lg border border-slate-700/40" />
            ))}
          </div>
        </div>
      )}

      <div className="max-w-xl mx-auto bg-slate-800/30 rounded-xl border border-slate-700/30 p-4" data-testid="timing-breakdown">
        <h4 className="text-sm font-medium text-slate-400 mb-2">Performance</h4>
        <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 text-center text-xs">
          {['scenes', 'images', 'voices', 'render', 'upload', 'total'].map(k => (
            <div key={k}>
              <p className="text-slate-500 capitalize">{k}</p>
              <p className="text-white font-medium">{timing[`${k}_ms`] ? `${(timing[`${k}_ms`] / 1000).toFixed(1)}s` : '-'}</p>
            </div>
          ))}
        </div>
      </div>

      <p className="text-center text-xs text-slate-500">
        <Coins className="w-3 h-3 inline mr-1" /> {job.credits_charged || 0} credits used
      </p>
    </div>
  );
}

// ─── ERROR PHASE ──────────────────────────────────────────────────────────

function ErrorPhase({ job, onResume, onNew }) {
  const stages = job?.stages || {};
  const failedStage = Object.entries(stages).find(([, v]) => v.status === 'FAILED');
  const hasFallback = job?.fallback?.has_preview || job?.fallback?.story_pack_url || job?.fallback?.fallback_video_url;

  return (
    <div className="max-w-lg mx-auto text-center space-y-6 py-12" data-testid="error-phase">
      <div className={`w-16 h-16 mx-auto rounded-full flex items-center justify-center ${hasFallback ? 'bg-amber-500/20' : 'bg-red-500/20'}`}>
        {hasFallback ? <Package className="w-8 h-8 text-amber-400" /> : <AlertCircle className="w-8 h-8 text-red-400" />}
      </div>
      <h2 className="text-xl font-bold text-white">
        {hasFallback ? 'Your Story Assets Are Ready' : 'Generation Failed'}
      </h2>
      <p className="text-slate-400">
        {hasFallback
          ? 'The cinematic render encountered an issue, but we saved your story assets — images, audio, and more.'
          : (job?.error || 'An error occurred during video generation.')}
      </p>
      {failedStage && !hasFallback && (
        <p className="text-sm text-slate-500">
          Failed at: <span className="text-red-400 font-medium">{failedStage[0]}</span>
          {failedStage[1].retry_count > 0 && ` (after ${failedStage[1].retry_count} retries)`}
        </p>
      )}

      <div className="flex justify-center gap-2">
        {STAGE_ORDER.map(name => {
          const s = stages[name] || {};
          return (
            <div key={name} className={`px-2 py-1 rounded text-xs font-medium ${
              s.status === 'COMPLETED' ? 'bg-green-500/20 text-green-400'
                : s.status === 'FAILED' ? 'bg-red-500/20 text-red-400'
                : 'bg-slate-800/50 text-slate-500'}`}>
              {STAGE_LABELS[name]}
            </div>
          );
        })}
      </div>

      <div className="flex justify-center gap-3">
        {hasFallback && (
          <Link to={`/app/story-preview/${job.job_id}`}>
            <Button className="bg-amber-600 hover:bg-amber-700" data-testid="view-assets-btn">
              <Eye className="w-4 h-4 mr-2" /> View Story Assets
            </Button>
          </Link>
        )}
        <Button onClick={onResume} className="bg-purple-600 hover:bg-purple-700" data-testid="resume-btn">
          <RotateCcw className="w-4 h-4 mr-2" /> Resume from Checkpoint
        </Button>
        <Button onClick={onNew} variant="outline" className="border-slate-700 text-slate-300" data-testid="new-video-btn-error">
          Start Over
        </Button>
      </div>

      <p className="text-xs text-slate-500">Credits have been refunded for the failed render.</p>
    </div>
  );
}
