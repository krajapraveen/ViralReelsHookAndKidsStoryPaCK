import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Progress } from '../components/ui/progress';
import { toast } from 'sonner';
import api from '../utils/api';
import {
  ArrowLeft, Wand2, Loader2, Film, Image, Mic, CheckCircle,
  Play, Download, RefreshCw, AlertCircle, Clock, Coins,
  Video, Upload, BookOpen, Sparkles, RotateCcw, XCircle, Eye,
  Share2, Link2, Copy, ExternalLink, RefreshCcw as Remix
} from 'lucide-react';
import UpsellModal from '../components/UpsellModal';

const STAGE_ORDER = ['scenes', 'images', 'voices', 'render', 'upload'];
const STAGE_ICONS = { scenes: BookOpen, images: Image, voices: Mic, render: Video, upload: Upload };
const STAGE_LABELS = { scenes: 'Scenes', images: 'Images', voices: 'Voices', render: 'Render', upload: 'Upload' };

export default function StoryVideoPipeline() {
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
  const pollRef = useRef(null);
  const [searchParams] = useSearchParams();

  // Load options + check for onboarding prompt + check for active jobs
  useEffect(() => {
    api.get('/api/pipeline/options').then(r => setOptions(r.data)).catch(() => {});
    loadUserJobs();
    checkUpsell();

    // Check for remix data
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

    // Onboarding: check for prompt from signup flow
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
    } catch (e) { /* ignore */ }
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
          } else if (j.status === 'FAILED') {
            clearInterval(pollRef.current);
            pollRef.current = null;
            setPhase('error');
          }
        }
      } catch (e) { /* continue polling */ }
    };
    poll();
    pollRef.current = setInterval(poll, 3000);
  }, []);

  const handleGenerate = async () => {
    if (storyText.length < 50) { toast.error('Story must be at least 50 characters'); return; }
    if (!title.trim()) { toast.error('Please enter a title'); return; }
    setSubmitting(true);
    try {
      const res = await api.post('/api/pipeline/create', {
        title, story_text: storyText, animation_style: animStyle,
        age_group: ageGroup, voice_preset: voicePreset,
        parent_video_id: remixData?.parent_video_id || null,
      });
      if (res.data.success) {
        setJobId(res.data.job_id);
        setPhase('processing');
        toast.success(`Video queued! ${res.data.credits_charged} credits charged.`);
        startPolling(res.data.job_id);
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to create video job');
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
  };

  const viewJob = (j) => {
    setJobId(j.job_id);
    if (j.status === 'COMPLETED') { setJob(j); setPhase('done'); }
    else if (j.status === 'FAILED') { setJob(j); setPhase('error'); }
    else { setPhase('processing'); startPolling(j.job_id); }
  };

  // ─── RENDER ────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-purple-950/30 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-950/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link to="/app" className="text-slate-400 hover:text-white"><ArrowLeft className="w-5 h-5" /></Link>
            <Film className="w-5 h-5 text-purple-400" />
            <span className="font-semibold text-white text-lg">Story → Video</span>
          </div>
          {phase !== 'input' && (
            <Button onClick={handleNewVideo} variant="outline" size="sm" className="border-slate-700 text-slate-300">
              <Sparkles className="w-4 h-4 mr-1" /> New Video
            </Button>
          )}
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* Upsell Modal */}
        {showUpsell && <UpsellModal credits={userCredits} onClose={() => setShowUpsell(false)} />}

        {/* Remix banner */}
        {remixData && phase === 'input' && (
          <div className="mb-6 bg-pink-500/10 border border-pink-500/30 rounded-xl p-4 flex items-center gap-3" data-testid="remix-banner">
            <Remix className="w-5 h-5 text-pink-400" />
            <span className="text-pink-200 text-sm">Remixing: <strong>{remixData.title}</strong> — edit the story and make it your own!</span>
          </div>
        )}

        {/* Welcome overlay for onboarding */}
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
        />}
        {phase === 'processing' && <ProcessingPhase job={job} />}
        {phase === 'done' && <DonePhase job={job} jobId={jobId} onNew={handleNewVideo} />}
        {phase === 'error' && <ErrorPhase job={job} onResume={handleResume} onNew={handleNewVideo} />}
      </main>
    </div>
  );
}

// ─── INPUT PHASE ──────────────────────────────────────────────────────────

function InputPhase({ options, title, setTitle, storyText, setStoryText,
  animStyle, setAnimStyle, ageGroup, setAgeGroup, voicePreset, setVoicePreset,
  onGenerate, submitting, userJobs, onViewJob }) {

  const styles = options?.animation_styles || [];
  const ages = options?.age_groups || [];
  const voices = options?.voice_presets || [];
  const activeJobs = userJobs.filter(j => ['QUEUED', 'PROCESSING'].includes(j.status));
  const recentJobs = userJobs.filter(j => j.status === 'COMPLETED').slice(0, 3);

  return (
    <div className="space-y-8" data-testid="input-phase">
      {/* Active jobs banner */}
      {activeJobs.length > 0 && (
        <div className="bg-purple-900/30 border border-purple-500/30 rounded-xl p-4 flex items-center justify-between" data-testid="active-job-banner">
          <div className="flex items-center gap-3">
            <Loader2 className="w-5 h-5 text-purple-400 animate-spin" />
            <span className="text-purple-200">You have {activeJobs.length} video{activeJobs.length > 1 ? 's' : ''} in progress</span>
          </div>
          <Button onClick={() => onViewJob(activeJobs[0])} size="sm" className="bg-purple-600 hover:bg-purple-700">
            <Eye className="w-4 h-4 mr-1" /> View Progress
          </Button>
        </div>
      )}

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Main form */}
        <div className="lg:col-span-2 space-y-6">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Create a Story Video</h1>
            <p className="text-slate-400">Enter your story and we'll create an animated video with AI-generated images and voiceover.</p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-slate-300 mb-1 block">Title</label>
              <Input value={title} onChange={e => setTitle(e.target.value)} placeholder="My Amazing Story..."
                className="bg-slate-800/50 border-slate-700 text-white" data-testid="title-input" maxLength={100} />
            </div>

            <div>
              <label className="text-sm font-medium text-slate-300 mb-1 block">Story Text</label>
              <Textarea value={storyText} onChange={e => setStoryText(e.target.value)}
                placeholder="Once upon a time..." rows={8}
                className="bg-slate-800/50 border-slate-700 text-white resize-none" data-testid="story-textarea" />
              <p className="text-xs text-slate-500 mt-1">{storyText.length} / 10,000 characters (min 50)</p>
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

          {/* Generate Button */}
          <Button onClick={onGenerate} disabled={submitting || storyText.length < 50 || !title.trim()}
            className="w-full h-14 text-lg bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 disabled:opacity-50"
            data-testid="generate-btn">
            {submitting ? <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> Creating Job...</>
              : <><Wand2 className="w-5 h-5 mr-2" /> Generate Video</>}
          </Button>
        </div>

        {/* Sidebar: Recent videos */}
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
      {/* Title */}
      <div className="text-center">
        <h2 className="text-2xl font-bold text-white">{job.title || 'Generating Video...'}</h2>
        <p className="text-slate-400 mt-1">{job.current_step}</p>
      </div>

      {/* Progress bar */}
      <div className="max-w-2xl mx-auto">
        <Progress value={job.progress || 0} className="h-3" />
        <p className="text-center text-sm text-slate-400 mt-2">{job.progress || 0}%</p>
      </div>

      {/* Stage indicators */}
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

      {/* Filmstrip — per-scene thumbnails */}
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
                  <img src={sp.image_url} alt={`Scene ${sp.scene_number}`}
                    className="w-32 h-20 object-cover" />
                ) : (
                  <div className="w-32 h-20 bg-slate-800/50 flex items-center justify-center">
                    {job.current_stage === 'images'
                      ? <Loader2 className="w-5 h-5 text-purple-400 animate-spin" />
                      : <Image className="w-5 h-5 text-slate-600" />}
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

      {/* Info */}
      <div className="text-center">
        <p className="text-xs text-slate-500 flex items-center justify-center gap-1">
          <Clock className="w-3 h-3" /> Video generation continues safely in the background. You can leave and return.
        </p>
      </div>
    </div>
  );
}

// ─── DONE PHASE (with Share Screen) ───────────────────────────────────────

function DonePhase({ job, jobId, onNew }) {
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
      {/* Success header */}
      <div className="text-center">
        <div className="w-16 h-16 mx-auto bg-green-500/20 rounded-full flex items-center justify-center mb-4">
          <CheckCircle className="w-8 h-8 text-green-400" />
        </div>
        <h2 className="text-2xl font-bold text-white">{job.title}</h2>
        <p className="text-green-400 mt-1">Your AI video is ready!</p>
      </div>

      {/* Video player */}
      {job.output_url && (
        <div className="max-w-3xl mx-auto">
          <div className="rounded-xl overflow-hidden border border-slate-700/50 bg-black" data-testid="video-player">
            <video src={job.output_url} controls className="w-full" preload="metadata" />
          </div>

          {/* Primary actions */}
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

          {/* Share section */}
          <div className="mt-6 p-4 rounded-xl bg-slate-800/30 border border-slate-700/30" data-testid="share-section">
            <p className="text-sm text-slate-400 text-center mb-3 flex items-center justify-center gap-2">
              <Share2 className="w-4 h-4" /> Share your creation
            </p>
            <div className="flex justify-center gap-3">
              <button onClick={() => handleShare('twitter')} className="p-2.5 rounded-xl bg-slate-700/50 hover:bg-[#1DA1F2]/20 border border-slate-600/50 hover:border-[#1DA1F2]/50 transition-all" data-testid="share-twitter" title="Share on X">
                <span className="text-sm font-bold text-slate-300 hover:text-[#1DA1F2]">X</span>
              </button>
              <button onClick={() => handleShare('facebook')} className="p-2.5 rounded-xl bg-slate-700/50 hover:bg-[#1877F2]/20 border border-slate-600/50 hover:border-[#1877F2]/50 transition-all" data-testid="share-facebook" title="Share on Facebook">
                <span className="text-sm font-bold text-slate-300 hover:text-[#1877F2]">f</span>
              </button>
              <button onClick={() => handleShare('whatsapp')} className="p-2.5 rounded-xl bg-slate-700/50 hover:bg-[#25D366]/20 border border-slate-600/50 hover:border-[#25D366]/50 transition-all" data-testid="share-whatsapp" title="Share on WhatsApp">
                <span className="text-sm font-bold text-slate-300 hover:text-[#25D366]">W</span>
              </button>
              <button onClick={() => handleShare('linkedin')} className="p-2.5 rounded-xl bg-slate-700/50 hover:bg-[#0A66C2]/20 border border-slate-600/50 hover:border-[#0A66C2]/50 transition-all" data-testid="share-linkedin" title="Share on LinkedIn">
                <span className="text-sm font-bold text-slate-300 hover:text-[#0A66C2]">in</span>
              </button>
            </div>
          </div>

          {/* Create another */}
          <div className="text-center mt-6">
            <Button onClick={onNew} variant="ghost" className="text-slate-400 hover:text-white" data-testid="new-video-btn">
              <Sparkles className="w-4 h-4 mr-2" /> Create Another Video
            </Button>
          </div>
        </div>
      )}

      {/* Filmstrip */}
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

      {/* Timing breakdown */}
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

      {/* Credits */}
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

  return (
    <div className="max-w-lg mx-auto text-center space-y-6 py-12" data-testid="error-phase">
      <div className="w-16 h-16 mx-auto bg-red-500/20 rounded-full flex items-center justify-center">
        <AlertCircle className="w-8 h-8 text-red-400" />
      </div>
      <h2 className="text-xl font-bold text-white">Generation Failed</h2>
      <p className="text-slate-400">{job?.error || 'An error occurred during video generation.'}</p>
      {failedStage && (
        <p className="text-sm text-slate-500">
          Failed at: <span className="text-red-400 font-medium">{failedStage[0]}</span>
          {failedStage[1].retry_count > 0 && ` (after ${failedStage[1].retry_count} retries)`}
        </p>
      )}

      {/* Show what was completed */}
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
        <Button onClick={onResume} className="bg-purple-600 hover:bg-purple-700" data-testid="resume-btn">
          <RotateCcw className="w-4 h-4 mr-2" /> Resume from Checkpoint
        </Button>
        <Button onClick={onNew} variant="outline" className="border-slate-700 text-slate-300" data-testid="new-video-btn-error">
          Start Over
        </Button>
      </div>

      <p className="text-xs text-slate-500">Credits will be refunded for failed jobs.</p>
    </div>
  );
}
