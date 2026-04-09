import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Play, Download, Share2, RefreshCw, AlertTriangle, Film, Loader2,
  ChevronDown, ChevronUp, Bell, BellOff, Check, Plus, X, Trash2,
  Edit, Eye, Info, CheckCircle, Circle, HelpCircle, Clock, ArrowRight,
  Coins, Sparkles, Palette, BookOpen, Zap, Users, Flame
} from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import { trackEvent } from '../utils/analytics';
import RemixGallery from '../components/RemixGallery';

// ─── STATUS COPY (EXACT PRODUCTION SPEC) ──────────────────────────────────────
const STATUS_COPY = {
  QUEUED: {
    label: 'Waiting in line',
    color: '#fbbf24',
    bgTint: 'bg-amber-500/5',
    borderTint: 'border-amber-500/20',
    badgeBg: 'bg-amber-500/15 text-amber-400',
    what_this_is: 'This is your AI-generated video project based on your story and selected style.',
    whats_happening: "Your project is waiting for processing. We'll start automatically as soon as capacity is available.",
    what_to_do: 'No action needed. You can safely leave this page.',
    what_next: "We'll begin generating scenes, narration, and video automatically.",
  },
  PROCESSING: {
    label: 'Creating your video',
    color: '#60a5fa',
    bgTint: 'bg-blue-500/5',
    borderTint: 'border-blue-500/20',
    badgeBg: 'bg-blue-500/15 text-blue-400',
    what_this_is: "We're turning your idea into a fully animated video with visuals, narration, and timing.",
    whats_happening: null,
    what_to_do: 'No action needed. This usually takes 2\u20135 minutes.',
    what_next: "Next, we'll add narration and assemble the final video.",
  },
  COMPLETED: {
    label: 'Your video is ready',
    color: '#34d399',
    bgTint: 'bg-emerald-500/5',
    borderTint: 'border-emerald-500/20',
    badgeBg: 'bg-emerald-500/15 text-emerald-400',
    what_this_is: 'This is your final AI-generated video created from your story, style, and narration settings.',
    whats_happening: 'Your video has been successfully generated and is ready to use.',
    what_to_do: 'Preview your video, then download, share, or create another version.',
    what_next: 'You can reuse this project to generate improved or different versions.',
  },
  PARTIAL: {
    label: 'Partially ready',
    color: '#34d399',
    bgTint: 'bg-emerald-500/5',
    borderTint: 'border-emerald-500/20',
    badgeBg: 'bg-emerald-500/15 text-emerald-400',
    what_this_is: 'Some assets from your project are ready, though the full video may not have completed.',
    whats_happening: 'Partial results are available for preview.',
    what_to_do: 'Preview the available assets or retry for a full render.',
    what_next: 'You can download what is ready or attempt to regenerate the full video.',
  },
  FAILED: {
    label: 'Needs attention',
    color: '#f87171',
    bgTint: 'bg-red-500/5',
    borderTint: 'border-red-500/20',
    badgeBg: 'bg-red-500/15 text-red-400',
    what_this_is: 'This project could not be completed due to an issue during generation.',
    whats_happening: 'Something went wrong while creating your video.',
    what_to_do: 'Try again. If the issue continues, adjust your inputs or try later.',
    what_next: 'A retry will start the generation process again.',
  },
};

// ─── PROGRESS TIMELINE ────────────────────────────────────────────────────────
const TIMELINE_STAGES = [
  { id: 'received', label: 'Story received' },
  { id: 'planning', label: 'Preparing your story' },
  { id: 'visuals', label: 'Creating visuals' },
  { id: 'narration', label: 'Recording narration' },
  { id: 'video', label: 'Building your video' },
  { id: 'ready', label: 'Ready' },
];

const STAGE_TO_TIMELINE = {
  'INIT': 0,
  'PLANNING': 1, 'BUILDING_CHARACTER_CONTEXT': 1, 'PLANNING_SCENE_MOTION': 1,
  'scenes': 1, 'scene_generation': 1,
  'GENERATING_KEYFRAMES': 2, 'GENERATING_SCENE_CLIPS': 2,
  'images': 2, 'image_generation': 2,
  'GENERATING_AUDIO': 3, 'voices': 3, 'voice_generation': 3, 'tts': 3,
  'ASSEMBLING_VIDEO': 4, 'render': 4, 'video_assembly': 4, 'rendering': 4,
  'VALIDATING': 5, 'upload': 5, 'uploading': 5,
  'READY': 5,
};

const SUB_STAGE_LABELS = {
  'INIT': 'Preparing your story',
  'PLANNING': 'Preparing your story',
  'BUILDING_CHARACTER_CONTEXT': 'Preparing your story',
  'PLANNING_SCENE_MOTION': 'Preparing your story',
  'GENERATING_KEYFRAMES': 'Creating visuals',
  'GENERATING_SCENE_CLIPS': 'Creating visuals',
  'GENERATING_AUDIO': 'Recording narration',
  'ASSEMBLING_VIDEO': 'Building your video',
  'VALIDATING': 'Finalizing output',
  'scenes': 'Preparing your story',
  'scene_generation': 'Preparing your story',
  'images': 'Creating visuals',
  'image_generation': 'Creating visuals',
  'voices': 'Recording narration',
  'voice_generation': 'Recording narration',
  'render': 'Building your video',
  'video_assembly': 'Building your video',
  'upload': 'Finalizing output',
  'uploading': 'Finalizing output',
  'tts': 'Recording narration',
  'rendering': 'Building your video',
};

function getTimelineIndex(job) {
  const state = job.engine_state || job.current_stage || '';
  return STAGE_TO_TIMELINE[state] ?? 1;
}

function getDynamicStageLabel(job) {
  const state = job.engine_state || job.current_stage || '';
  return SUB_STAGE_LABELS[state] || 'Processing your project';
}

function getStatusKey(job) {
  if (job.status === 'COMPLETED') return 'COMPLETED';
  if (job.status === 'PARTIAL') return 'PARTIAL';
  if (job.status === 'FAILED') return 'FAILED';
  if (job.status === 'QUEUED') return 'QUEUED';
  return 'PROCESSING';
}

// ─── FUZZY TIME ESTIMATE ──────────────────────────────────────────────────────
function getFuzzyTimeLabel(job, timeEstimates) {
  if (!timeEstimates || !job.created_at) return null;
  const elapsedSec = (Date.now() - new Date(job.created_at).getTime()) / 1000;
  const state = job.engine_state || job.current_stage || '';

  // Determine which stage estimate to use
  let estTotalSec = timeEstimates.total || 300;
  if (['ASSEMBLING_VIDEO', 'render', 'video_assembly', 'rendering'].includes(state)) {
    estTotalSec = timeEstimates.video_assembly || 300;
  } else if (['GENERATING_KEYFRAMES', 'GENERATING_SCENE_CLIPS', 'images', 'image_generation'].includes(state)) {
    estTotalSec = timeEstimates.image_generation || 90;
  } else if (['GENERATING_AUDIO', 'voices', 'voice_generation', 'tts'].includes(state)) {
    estTotalSec = timeEstimates.voice_generation || 30;
  } else if (['PLANNING', 'BUILDING_CHARACTER_CONTEXT', 'PLANNING_SCENE_MOTION', 'scenes', 'scene_generation'].includes(state)) {
    estTotalSec = timeEstimates.planning || 30;
  }

  const remaining = Math.max(0, estTotalSec - elapsedSec);

  if (remaining <= 15) return 'Almost ready';
  if (remaining <= 45) return 'Just finishing up';
  if (remaining <= 90) return 'About 1 minute left';
  if (remaining <= 180) return 'About 2\u20133 minutes left';
  return 'A few more minutes';
}

// ─── HELPERS ──────────────────────────────────────────────────────────────────
function timeAgo(dateStr) {
  if (!dateStr) return '';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function triggerDownload(job) {
  if (!job.output_url) { toast.error('Video not available for download'); return; }
  try {
    const a = document.createElement('a');
    a.href = job.output_url;
    a.download = `${(job.title || 'video').replace(/[^a-z0-9]/gi, '-').toLowerCase()}-visionary-suite.mp4`;
    a.target = '_blank';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  } catch { window.open(job.output_url, '_blank'); }
}

function requestNotificationPermission() {
  if ('Notification' in window && Notification.permission === 'default') Notification.requestPermission();
}

function fireBrowserNotification(title, body) {
  if ('Notification' in window && Notification.permission === 'granted') {
    try {
      const n = new Notification(title, { body, icon: '/favicon.ico', tag: 'video-complete', renotify: true });
      n.onclick = () => { window.focus(); n.close(); };
    } catch { /* silent */ }
  }
}

// ─── SKELETON LOADING ─────────────────────────────────────────────────────────
function SkeletonCard() {
  return (
    <div className="rounded-xl border border-white/[0.06] p-4 animate-pulse">
      <div className="flex items-start gap-3">
        <div className="w-14 h-14 rounded-lg bg-zinc-800/60" />
        <div className="flex-1 space-y-2">
          <div className="h-4 w-2/3 bg-zinc-800/60 rounded" />
          <div className="h-3 w-1/3 bg-zinc-800/40 rounded" />
        </div>
        <div className="w-8 h-4 bg-zinc-800/40 rounded" />
      </div>
      <div className="mt-3 space-y-2">
        <div className="h-3 w-full bg-zinc-800/30 rounded" />
        <div className="h-3 w-4/5 bg-zinc-800/30 rounded" />
      </div>
    </div>
  );
}

function SkeletonLoading() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6" data-testid="myspace-skeleton">
      <div className="flex items-center justify-between">
        <div className="h-6 w-24 bg-zinc-800/60 rounded animate-pulse" />
        <div className="flex gap-2">
          <div className="w-8 h-8 bg-zinc-800/40 rounded-lg animate-pulse" />
          <div className="w-8 h-8 bg-zinc-800/40 rounded-lg animate-pulse" />
        </div>
      </div>
      <div className="space-y-3">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    </div>
  );
}

// ─── PROGRESS TIMELINE COMPONENT ──────────────────────────────────────────────
function ProgressTimeline({ currentIndex }) {
  return (
    <div className="space-y-1 py-2" data-testid="progress-timeline">
      {TIMELINE_STAGES.map((stage, idx) => {
        const isDone = idx < currentIndex;
        const isCurrent = idx === currentIndex;
        const isPending = idx > currentIndex;
        return (
          <div key={stage.id} className="flex items-center gap-2.5">
            {isDone && <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />}
            {isCurrent && (
              <span className="relative flex h-4 w-4 items-center justify-center flex-shrink-0">
                <span className="animate-ping absolute inline-flex h-3 w-3 rounded-full bg-blue-400 opacity-50" />
                <span className="relative inline-flex rounded-full h-3 w-3 bg-blue-500 border-2 border-blue-300" />
              </span>
            )}
            {isPending && <Circle className="w-4 h-4 text-zinc-600 flex-shrink-0" />}
            <span className={`text-xs ${isDone ? 'text-emerald-400/80' : isCurrent ? 'text-blue-300 font-medium' : 'text-zinc-600'}`}>
              {stage.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ─── INFO SECTION ─────────────────────────────────────────────────────────────
function InfoSection({ label, text, icon: Icon }) {
  return (
    <div className="py-1.5">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500 flex items-center gap-1 mb-0.5">
        <Icon className="w-3 h-3" /> {label}
      </p>
      <p className="text-xs text-zinc-300 leading-relaxed">{text}</p>
    </div>
  );
}

// ─── RE-ENGAGEMENT VARIANTS ───────────────────────────────────────────────────
const VARIATION_BUTTONS = [
  { label: 'Make it funnier', icon: Sparkles, tone: 'comedy', style: null, desc: 'Same story, comedy twist' },
  { label: 'Change style', icon: Palette, tone: null, style: 'explore', desc: 'Try anime, 3D, or watercolor' },
  { label: 'Turn into reel', icon: Zap, tone: 'short_reel', style: null, desc: 'Shorter, punchier version' },
  { label: 'Turn into storybook', icon: BookOpen, tone: null, style: 'storybook', desc: 'Classic illustrated style' },
];

// ─── PROJECT CARD (UNIFIED) ──────────────────────────────────────────────────
function ProjectCard({ job, highlighted, justCompleted, onShare, onRetry, onDelete, onNavigate, onImproveConsistency, timeEstimates, userCredits, remixCount }) {
  const navigate = useNavigate();
  const [expanded, setExpanded] = useState(() => {
    const s = getStatusKey(job);
    return s === 'QUEUED' || s === 'PROCESSING';
  });
  const [consistencyStatus, setConsistencyStatus] = useState(null); // null | 'loading' | 'success' | 'failed'
  const statusKey = getStatusKey(job);
  const copy = STATUS_COPY[statusKey] || STATUS_COPY.PROCESSING;
  const timelineIdx = statusKey === 'PROCESSING' ? getTimelineIndex(job) : -1;
  const dynamicStage = statusKey === 'PROCESSING' ? getDynamicStageLabel(job) : null;
  const fuzzyTime = statusKey === 'PROCESSING' ? getFuzzyTimeLabel(job, timeEstimates) : null;
  const creditsUsed = job.credits_charged || 0;

  const handleWatch = () => { if (job.output_url) window.open(job.output_url, '_blank'); };

  const handleVariation = (variant) => {
    const statePayload = {
      prompt: '',
      remixFrom: { title: job.title, job_id: job.job_id },
      source_tool: 'myspace-reengage',
    };
    let path = '/app/story-video-studio';
    if (variant.tone) path += `?tone=${variant.tone}`;
    if (variant.style) path += `?style=${variant.style}`;
    navigate(path, { state: statePayload });
  };

  return (
    <div
      data-testid={`project-card-${job.job_id}`}
      className={`relative rounded-xl border transition-all duration-300 overflow-hidden ${copy.bgTint} ${
        justCompleted
          ? 'border-emerald-400 ring-2 ring-emerald-400/30 animate-[pulse_2s_ease-in-out_3]'
          : highlighted
            ? `ring-1 ring-offset-0 ${copy.borderTint}`
            : 'border-white/[0.08]'
      }`}
    >
      {/* ─── Header Row ─── */}
      <div
        className="flex items-start gap-3 p-4 cursor-pointer"
        onClick={() => setExpanded(v => !v)}
        data-testid={`card-header-${job.job_id}`}
      >
        <div className="w-14 h-14 rounded-lg bg-zinc-800/80 flex items-center justify-center overflow-hidden flex-shrink-0">
          {job.thumbnail_url ? (
            <img src={job.thumbnail_url} alt="" className="w-full h-full object-cover" />
          ) : (
            <Film className="w-5 h-5 text-zinc-600" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-white truncate">{job.title || 'Untitled Project'}</h3>
          <div className="flex items-center gap-2 mt-1">
            <span className={`inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full ${copy.badgeBg}`}>
              {statusKey === 'PROCESSING' && (
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-60" style={{ backgroundColor: copy.color }} />
                  <span className="relative inline-flex rounded-full h-2 w-2" style={{ backgroundColor: copy.color }} />
                </span>
              )}
              {copy.label}
            </span>
            <span className="text-[10px] text-zinc-600">{timeAgo(job.created_at)}</span>
            {/* Credits badge for completed */}
            {(statusKey === 'COMPLETED' || statusKey === 'PARTIAL') && creditsUsed > 0 && (
              <span className="inline-flex items-center gap-0.5 text-[10px] text-amber-400/70 bg-amber-500/10 px-1.5 py-0.5 rounded-full" data-testid={`credits-badge-${job.job_id}`}>
                <Coins className="w-2.5 h-2.5" /> {creditsUsed} credit{creditsUsed !== 1 ? 's' : ''}
              </span>
            )}
            {/* Challenge Entry badge */}
            {job.challenge_id && (
              <span className="inline-flex items-center gap-0.5 text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded-full" data-testid={`challenge-entry-${job.job_id}`}>
                Challenge Entry
              </span>
            )}
          </div>
          {/* Dynamic sub-stage + fuzzy time for processing */}
          {statusKey === 'PROCESSING' && (
            <div className="flex items-center gap-2 mt-1">
              {dynamicStage && <p className="text-[11px] text-blue-400/80">Currently: {dynamicStage}</p>}
              {fuzzyTime && (
                <span className="text-[10px] text-blue-300/60 bg-blue-500/10 px-1.5 py-0.5 rounded-full" data-testid={`time-estimate-${job.job_id}`}>
                  {fuzzyTime}
                </span>
              )}
            </div>
          )}
          {/* Progress bar */}
          {(statusKey === 'PROCESSING' || statusKey === 'QUEUED') && (
            <div className="w-full h-1 bg-white/[0.06] rounded-full overflow-hidden mt-2">
              <div
                className="h-full rounded-full transition-all duration-[2s] ease-in-out"
                style={{
                  width: `${Math.min(job.progress || 0, 100)}%`,
                  backgroundColor: copy.color,
                  animation: statusKey === 'PROCESSING' ? 'pulse 2.5s ease-in-out infinite' : 'none',
                }}
              />
            </div>
          )}
        </div>
        <div className="flex flex-col items-end gap-1 flex-shrink-0">
          {(statusKey === 'PROCESSING' || statusKey === 'QUEUED') && (
            <span className="text-xs font-mono text-zinc-500">{job.progress || 0}%</span>
          )}
          {expanded ? <ChevronUp className="w-4 h-4 text-zinc-600" /> : <ChevronDown className="w-4 h-4 text-zinc-600" />}
        </div>
      </div>

      {/* ─── Expanded Detail ─── */}
      {expanded && (
        <div className="px-4 pb-4 pt-0 border-t border-white/[0.04] space-y-0">
          <InfoSection icon={Info} label="What this is" text={copy.what_this_is} />
          <InfoSection
            icon={Clock}
            label="What's happening now"
            text={
              statusKey === 'PROCESSING' && dynamicStage
                ? `Currently: ${dynamicStage}`
                : copy.whats_happening || 'Processing your project.'
            }
          />

          {/* Progress Timeline — PROCESSING only */}
          {statusKey === 'PROCESSING' && <ProgressTimeline currentIndex={timelineIdx} />}

          <InfoSection icon={ArrowRight} label="What you need to do" text={copy.what_to_do} />
          <InfoSection icon={Eye} label="What happens next" text={copy.what_next} />

          {/* ─── Failure Recovery Copy ─── */}
          {statusKey === 'FAILED' && (
            <div className="mt-2 p-2.5 rounded-lg bg-amber-500/5 border border-amber-500/10">
              <p className="text-[11px] text-amber-300/90 leading-relaxed">
                This usually works on retry. Tip: shorter stories generate faster and are less likely to fail.
              </p>
            </div>
          )}

          {/* ─── Asset Breakdown (completed) ─── */}
          {(statusKey === 'COMPLETED' || statusKey === 'PARTIAL') && (
            <div className="mt-2 pt-2 border-t border-white/[0.04]">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500 mb-1.5">Project Assets</p>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { name: 'Script', desc: 'The story text used to generate your video.' },
                  { name: 'Scenes', desc: 'The visuals created for each part of your story.' },
                  { name: 'Voiceover', desc: 'The narration audio using your selected voice.' },
                  { name: 'Final Video', desc: 'Your completed video with visuals, audio, and timing.' },
                ].map(asset => (
                  <div key={asset.name} className="bg-white/[0.03] rounded-lg px-2.5 py-2">
                    <p className="text-[11px] font-medium text-zinc-300">{asset.name}</p>
                    <p className="text-[10px] text-zinc-500 leading-snug">{asset.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ─── CTA BUTTONS ─── */}
          <div className="flex flex-wrap gap-2 mt-3 pt-2 border-t border-white/[0.04]">
            {/* QUEUED */}
            {statusKey === 'QUEUED' && (
              <button data-testid={`view-details-btn-${job.job_id}`} onClick={() => onNavigate(job)} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/15 text-amber-300 text-xs font-medium hover:bg-amber-500/25 transition-colors">
                <Eye className="w-3.5 h-3.5" /> View Details
              </button>
            )}
            {/* PROCESSING */}
            {statusKey === 'PROCESSING' && (
              <>
                <button data-testid={`view-progress-btn-${job.job_id}`} onClick={() => onNavigate(job)} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-500/15 text-blue-300 text-xs font-medium hover:bg-blue-500/25 transition-colors">
                  <Eye className="w-3.5 h-3.5" /> View Progress
                </button>
                <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.06] text-zinc-400 text-xs hover:bg-white/10 transition-colors" onClick={() => toast.info("Your generation continues in the background. We'll notify you when it's ready.", { duration: 5000 })} data-testid={`leave-btn-${job.job_id}`}>
                  <ArrowRight className="w-3.5 h-3.5" /> Leave & come back later
                </button>
              </>
            )}
            {/* COMPLETED / PARTIAL */}
            {(statusKey === 'COMPLETED' || statusKey === 'PARTIAL') && (
              <>
                <button data-testid={`preview-btn-${job.job_id}`} onClick={handleWatch} className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-500/20 text-emerald-300 text-xs font-bold hover:bg-emerald-500/30 transition-colors">
                  <Play className="w-4 h-4" /> Preview
                </button>
                <button data-testid={`download-btn-${job.job_id}`} onClick={(e) => { e.stopPropagation(); triggerDownload(job); }} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.06] text-zinc-300 text-xs hover:bg-white/10 transition-colors">
                  <Download className="w-3.5 h-3.5" /> Download
                </button>
                <button data-testid={`share-btn-${job.job_id}`} onClick={(e) => { e.stopPropagation(); onShare(job); }} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.06] text-zinc-300 text-xs hover:bg-white/10 transition-colors">
                  <Share2 className="w-3.5 h-3.5" /> Share
                </button>
                {/* Improve Consistency CTA — only for eligible story_engine jobs, not legacy */}
                {job.source !== 'legacy_pipeline' && (job.consistency_retry_count === undefined || job.consistency_retry_count < 1) ? (
                  consistencyStatus === 'success' ? (
                    <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 text-xs font-medium" data-testid={`consistency-success-${job.job_id}`}>
                      <Sparkles className="w-3.5 h-3.5" /> Your characters now appear more consistent across scenes
                    </div>
                  ) : consistencyStatus === 'failed' ? (
                    <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/10 text-red-400 text-xs" data-testid={`consistency-failed-${job.job_id}`}>
                      <AlertTriangle className="w-3.5 h-3.5" /> Couldn't improve consistency right now. Try again later.
                    </div>
                  ) : (
                    <button
                      data-testid={`improve-consistency-btn-${job.job_id}`}
                      disabled={consistencyStatus === 'loading'}
                      onClick={async (e) => {
                        e.stopPropagation();
                        setConsistencyStatus('loading');
                        trackEvent('improve_consistency_clicked', { job_id: job.job_id, title: job.title });
                        try {
                          await api.post(`/api/retention/improve-consistency/${job.job_id}`);
                          setConsistencyStatus('success');
                          trackEvent('improve_consistency_success', { job_id: job.job_id, title: job.title });
                          toast.success('Your characters now appear more consistent across scenes', { duration: 5000 });
                        } catch (err) {
                          const msg = err.response?.data?.detail || 'Could not improve consistency';
                          // If already attempted, show as success
                          if (msg.includes('already attempted')) {
                            setConsistencyStatus('success');
                          } else {
                            setConsistencyStatus('failed');
                            trackEvent('improve_consistency_failed', { job_id: job.job_id, error: msg });
                            toast.error(msg, { duration: 4000 });
                          }
                        }
                      }}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-semibold hover:bg-indigo-500/20 hover:border-indigo-500/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {consistencyStatus === 'loading' ? (
                        <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Improving...</>
                      ) : (
                        <><Sparkles className="w-3.5 h-3.5" /> Improve Consistency</>
                      )}
                    </button>
                  )
                ) : null}
                {onDelete && (
                  <button data-testid={`delete-btn-${job.job_id}`} onClick={(e) => { e.stopPropagation(); onDelete(job); }} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.04] text-zinc-500 text-xs hover:bg-red-500/10 hover:text-red-400 transition-colors">
                    <Trash2 className="w-3.5 h-3.5" /> Delete
                  </button>
                )}
              </>
            )}
            {/* FAILED */}
            {statusKey === 'FAILED' && (
              <>
                <button data-testid={`retry-btn-${job.job_id}`} onClick={() => onRetry(job)} className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-red-500/20 text-red-300 text-xs font-bold hover:bg-red-500/30 transition-colors">
                  <RefreshCw className="w-4 h-4" /> Retry
                </button>
                <button data-testid={`edit-retry-btn-${job.job_id}`} onClick={() => onNavigate(job, 'edit')} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.06] text-zinc-300 text-xs hover:bg-white/10 transition-colors">
                  <Edit className="w-3.5 h-3.5" /> Edit & Retry
                </button>
                {onDelete && (
                  <button data-testid={`delete-btn-${job.job_id}`} onClick={(e) => { e.stopPropagation(); onDelete(job); }} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.04] text-zinc-500 text-xs hover:bg-red-500/10 hover:text-red-400 transition-colors">
                    <Trash2 className="w-3.5 h-3.5" /> Delete
                  </button>
                )}
              </>
            )}
          </div>

          {/* ─── RE-ENGAGEMENT: Make another version (completed only) ─── */}
          {(statusKey === 'COMPLETED' || statusKey === 'PARTIAL') && (
            <div className="mt-3 pt-3 border-t border-white/[0.04]" data-testid={`reengage-section-${job.job_id}`}>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500 mb-2 flex items-center gap-1">
                <RefreshCw className="w-3 h-3" /> Make another version
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5">
                {VARIATION_BUTTONS.map(v => (
                  <button
                    key={v.label}
                    onClick={() => handleVariation(v)}
                    className="text-left p-2 rounded-lg bg-white/[0.03] border border-white/[0.05] hover:border-indigo-500/30 hover:bg-indigo-500/5 transition-all group"
                    data-testid={`variation-${v.label.toLowerCase().replace(/\s/g, '-')}-${job.job_id}`}
                  >
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <v.icon className="w-3 h-3 text-zinc-500 group-hover:text-indigo-400 transition-colors" />
                      <span className="text-[11px] font-medium text-zinc-300 group-hover:text-indigo-300 transition-colors">{v.label}</span>
                    </div>
                    <p className="text-[9px] text-zinc-600 leading-tight">{v.desc}</p>
                  </button>
                ))}
              </div>
              {/* Credit nudge */}
              <p className="text-[10px] text-zinc-500 mt-2 text-center" data-testid={`credit-nudge-${job.job_id}`}>
                Generate another version for just {creditsUsed || 1} credit{(creditsUsed || 1) !== 1 ? 's' : ''}
                {userCredits != null && <span className="text-zinc-600"> &middot; You have {userCredits} left</span>}
              </p>
            </div>
          )}
        </div>
      )}

      {/* ─── OWNERSHIP MESSAGING ─── */}
      {remixCount > 0 && (statusKey === 'COMPLETED' || statusKey === 'PARTIAL') && (
        <div className="mx-4 mb-3 px-3 py-2 rounded-lg bg-pink-500/[0.06] border border-pink-500/15" data-testid={`ownership-msg-${job.job_id}`}>
          <div className="flex items-center gap-2">
            <Users className="w-3.5 h-3.5 text-pink-400 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <span className="text-[11px] font-semibold text-pink-300">
                {remixCount === 1 ? 'Someone remixed your story!' : `${remixCount} people remixed your story`}
              </span>
              {remixCount >= 3 && (
                <span className="ml-1.5 text-[10px] text-pink-400/70 font-medium">
                  — people are remixing YOUR idea
                </span>
              )}
            </div>
            {remixCount >= 5 && (
              <span className="text-[9px] font-bold text-amber-400 bg-amber-500/15 px-1.5 py-0.5 rounded-full flex-shrink-0" data-testid={`trending-badge-${job.job_id}`}>
                Trending
              </span>
            )}
          </div>
        </div>
      )}

      {/* Just-completed badge + pulse */}
      {justCompleted && (
        <div className="absolute top-3 right-3 z-10 flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/90 text-[10px] font-bold text-white animate-bounce" data-testid="just-completed-badge">
          <Check className="w-3 h-3" /> Ready
        </div>
      )}
    </div>
  );
}

// ─── SECTION HEADER ───────────────────────────────────────────────────────────
function SectionHeader({ title, count, icon: Icon, color, collapsed, onToggle }) {
  return (
    <button onClick={onToggle} className="w-full flex items-center justify-between py-2 group" data-testid={`section-${title.toLowerCase().replace(/\s/g, '-')}`}>
      <div className="flex items-center gap-2">
        <Icon className="w-4 h-4" style={{ color }} />
        <span className="text-sm font-semibold text-zinc-300">{title}</span>
        {count > 0 && (
          <span className="text-[10px] px-1.5 py-0.5 rounded-full font-medium" style={{ backgroundColor: color + '20', color }}>{count}</span>
        )}
      </div>
      {collapsed ? <ChevronDown className="w-4 h-4 text-zinc-600" /> : <ChevronUp className="w-4 h-4 text-zinc-600" />}
    </button>
  );
}

// ─── HOW THIS WORKS ───────────────────────────────────────────────────────────
function HowThisWorks() {
  const [open, setOpen] = useState(false);
  const steps = [
    'You enter your story or idea',
    'We plan the scenes',
    'We generate visuals',
    'We create narration',
    'We build your video',
    'You preview and download',
    'You can regenerate improved versions',
  ];
  return (
    <div className="border border-white/[0.06] rounded-xl overflow-hidden" data-testid="how-this-works">
      <button onClick={() => setOpen(v => !v)} className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/[0.02] transition-colors">
        <span className="flex items-center gap-2 text-sm font-semibold text-zinc-300">
          <HelpCircle className="w-4 h-4 text-zinc-500" /> How this works
        </span>
        {open ? <ChevronUp className="w-4 h-4 text-zinc-600" /> : <ChevronDown className="w-4 h-4 text-zinc-600" />}
      </button>
      {open && (
        <div className="px-4 pb-4 space-y-2">
          {steps.map((step, idx) => (
            <div key={idx} className="flex items-start gap-2.5">
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-zinc-800 flex items-center justify-center text-[10px] font-bold text-zinc-400 mt-0.5">{idx + 1}</span>
              <p className="text-xs text-zinc-400 leading-relaxed">{step}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── COMPLETION PROMPT MODAL ──────────────────────────────────────────────────
function CompletionPromptModal({ job, onClose, onDownload, onShareWhatsApp, onCreateAnother }) {
  if (!job) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" data-testid="completion-prompt-modal">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-sm bg-zinc-900 border border-zinc-700/50 rounded-2xl overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        <style>{`@keyframes pulseShare { 0%,100% { box-shadow: 0 0 0 0 rgba(16,185,129,0.5); } 50% { box-shadow: 0 0 0 12px rgba(16,185,129,0); } }`}</style>
        <button onClick={onClose} className="absolute top-3 right-3 z-10 p-1 rounded-full bg-zinc-800/80 hover:bg-zinc-700 text-zinc-400 hover:text-white transition-colors" data-testid="completion-prompt-close">
          <X className="w-4 h-4" />
        </button>
        <div className="relative aspect-video bg-zinc-800">
          {job.thumbnail_url ? <img src={job.thumbnail_url} alt={job.title} className="w-full h-full object-cover" /> : <div className="w-full h-full flex items-center justify-center"><Film className="w-12 h-12 text-zinc-600" /></div>}
          <div className="absolute inset-0 bg-gradient-to-t from-zinc-900 via-transparent to-transparent" />
          <div className="absolute bottom-3 left-3 right-3">
            <div className="flex items-center gap-1.5 mb-1">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wider">Ready</span>
            </div>
            <h3 className="text-white font-semibold text-base truncate" data-testid="completion-prompt-title">{job.title}</h3>
          </div>
        </div>
        <div className="p-4 space-y-2">
          <p className="text-xs text-center text-amber-300/80 font-medium mb-1" data-testid="viral-nudge">This video can go viral — share it now</p>
          <button onClick={() => onShareWhatsApp(job)} className="w-full flex items-center justify-center gap-2 py-3.5 rounded-xl bg-emerald-600 text-white font-bold text-sm hover:bg-emerald-500 transition-colors" style={{ animation: 'pulseShare 2.5s infinite' }} data-testid="completion-prompt-whatsapp">
            <Share2 className="w-5 h-5" /> Share with Friends
          </button>
          <div className="flex gap-2">
            <button onClick={() => { onDownload(job); onClose(); }} className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-white/10 text-white text-sm hover:bg-white/15 transition-colors" data-testid="completion-prompt-download">
              <Download className="w-4 h-4" /> Download
            </button>
            <button onClick={() => { onCreateAnother(); onClose(); }} className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-white/10 text-zinc-300 text-sm hover:bg-white/15 hover:text-white transition-colors" data-testid="completion-prompt-create-another">
              <Plus className="w-4 h-4" /> Create Another
            </button>
          </div>
          {/* Remix Gallery in completion modal */}
          <div className="pt-2 border-t border-white/[0.06] mt-2">
            <RemixGallery placement="completion" limit={3} />
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── MAIN COMPONENT ───────────────────────────────────────────────────────────
export default function MySpacePage() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [collapsedSections, setCollapsedSections] = useState({});
  const [justCompletedIds, setJustCompletedIds] = useState(new Set());
  const [completionPromptJob, setCompletionPromptJob] = useState(null);
  const [timeEstimates, setTimeEstimates] = useState(null);
  const [userCredits, setUserCredits] = useState(null);
  const [autoDownload, setAutoDownload] = useState(() => {
    try { return localStorage.getItem('vs_auto_download') === 'true'; } catch { return false; }
  });
  const [notificationsEnabled, setNotificationsEnabled] = useState(
    'Notification' in window && Notification.permission === 'granted'
  );
  const [remixStats, setRemixStats] = useState({});
  const [viralMyStats, setViralMyStats] = useState(null);
  const [searchParams] = useSearchParams();
  const highlightId = searchParams.get('projectId');
  const highlightRef = useRef(null);
  const pollRef = useRef(null);
  const prevStatusMap = useRef({});
  const promptedJobIds = useRef(new Set());

  // Fetch time estimates + user credits on mount
  useEffect(() => {
    const fetchMeta = async () => {
      try {
        const [timeRes, credRes] = await Promise.allSettled([
          api.get('/api/story-video-studio/generation/time-estimates'),
          api.get('/api/credits/balance'),
        ]);
        if (timeRes.status === 'fulfilled' && timeRes.value?.data?.estimates) {
          setTimeEstimates(timeRes.value.data.estimates);
        }
        if (credRes.status === 'fulfilled') {
          setUserCredits(credRes.value?.data?.credits ?? credRes.value?.data?.balance ?? null);
        }
      } catch { /* silent */ }
    };
    fetchMeta();
    // Fetch viral stats
    api.get('/api/viral/rewards/status').then(r => setViralMyStats(r.data)).catch(() => {});
  }, []);

  const fetchJobs = useCallback(async () => {
    try {
      const [storyRes, reelRes] = await Promise.allSettled([
        api.get('/api/story-engine/user-jobs?limit=100'),
        api.get('/api/convert/user-reels').catch(() => ({ data: { reels: [] } })),
      ]);
      const allItems = [];
      if (storyRes.status === 'fulfilled' && storyRes.value?.data?.jobs) {
        for (const j of storyRes.value.data.jobs) allItems.push({ ...j, type: 'story_video' });
      }
      if (reelRes.status === 'fulfilled' && reelRes.value?.data?.reels) {
        for (const r of reelRes.value.data.reels) {
          allItems.push({
            job_id: r.reel_id || r.id, title: r.title || 'Reel', type: 'reel',
            status: r.status === 'completed' ? 'COMPLETED' : r.status === 'failed' ? 'FAILED' : 'PROCESSING',
            thumbnail_url: r.thumbnail_url, output_url: r.output_url || r.video_url,
            progress: r.status === 'completed' ? 100 : 50,
            created_at: r.created_at, completed_at: r.completed_at,
          });
        }
      }
      allItems.sort((a, b) => {
        const da = a.created_at ? new Date(a.created_at).getTime() : 0;
        const db_ = b.created_at ? new Date(b.created_at).getTime() : 0;
        return db_ - da;
      });

      // Detect newly completed
      const newlyCompleted = [];
      for (const item of allItems) {
        const prev = prevStatusMap.current[item.job_id];
        if (prev && prev !== 'COMPLETED' && item.status === 'COMPLETED') newlyCompleted.push(item);
      }
      const newMap = {};
      for (const item of allItems) newMap[item.job_id] = item.status;
      prevStatusMap.current = newMap;

      for (const item of newlyCompleted) {
        toast.success(`Your video "${item.title}" is ready!`, { duration: 8000, id: `complete-${item.job_id}` });
        fireBrowserNotification('Your video is ready!', `"${item.title}" has finished rendering. Watch it now.`);
        setJustCompletedIds(prev => new Set([...prev, item.job_id]));
        setTimeout(() => { setJustCompletedIds(prev => { const next = new Set(prev); next.delete(item.job_id); return next; }); }, 30000);
        if (autoDownload && item.output_url) { triggerDownload(item); toast.info(`Auto-downloading "${item.title}"`, { duration: 3000 }); }
        if (!promptedJobIds.current.has(item.job_id)) { promptedJobIds.current.add(item.job_id); setCompletionPromptJob(item); }
      }
      setJobs(allItems);

      // Fetch remix stats for completed jobs (ownership messaging)
      const completedIds = allItems
        .filter(j => j.status === 'COMPLETED' || j.status === 'PARTIAL')
        .map(j => j.job_id)
        .slice(0, 50);
      if (completedIds.length > 0) {
        try {
          const statsRes = await api.post('/api/retention/remix-stats', { job_ids: completedIds });
          if (statsRes.data?.stats) setRemixStats(statsRes.data.stats);
        } catch { /* silent */ }
      }
    } catch (err) { console.error('Failed to fetch jobs:', err); } finally { setLoading(false); }
  }, [autoDownload]);

  useEffect(() => { fetchJobs(); requestNotificationPermission(); }, [fetchJobs]);

  useEffect(() => {
    const hasInProgress = jobs.some(j => !['COMPLETED', 'FAILED', 'ARCHIVED', 'ORPHANED', 'PARTIAL'].includes(j.status));
    if (hasInProgress) { pollRef.current = setInterval(fetchJobs, 4000); }
    else if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [jobs, fetchJobs]);

  useEffect(() => {
    if (highlightId && highlightRef.current) {
      setTimeout(() => { highlightRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' }); }, 300);
    }
  }, [highlightId, jobs]);

  const handleRetry = async (job) => {
    try {
      const res = await api.post(`/api/story-engine/retry/${job.job_id}`);
      if (res.data?.success) {
        toast.success('Retrying generation...');
        // Navigate to studio to show progress
        navigate(`/app/story-video-studio?projectId=${job.job_id}`);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Retry failed. Please try again.');
      // Fallback: navigate to recovery screen
      navigate(`/app/story-video-studio?projectId=${job.job_id}`);
    }
  };
  const handleNavigate = (job, mode) => {
    if (mode === 'remix') navigate('/app/story-video-studio', { state: { prompt: '', remixFrom: { title: job.title, job_id: job.job_id } } });
    else if (mode === 'edit') {
      // Pre-load story data so the Studio opens in edit mode
      localStorage.setItem('remix_video', JSON.stringify({
        parent_video_id: job.job_id,
        title: job.title || '',
        story_text: job.story_text || '',
        animation_style: job.animation_style || 'cartoon_2d',
        age_group: job.age_group || 'kids_5_8',
        voice_preset: job.voice_preset || 'narrator_warm',
      }));
      navigate('/app/story-video-studio?remix=edit-retry');
    }
    else navigate(`/app/story-video-studio?projectId=${job.job_id}`);
  };
  const handleShare = async (job) => {
    try {
      const res = await api.post(`/api/story-engine/share-link/${job.job_id}`);
      if (res.data?.whatsapp_url) window.open(res.data.whatsapp_url, '_blank');
    } catch {
      const shareUrl = `${window.location.origin}/share/${job.job_id}`;
      const text = encodeURIComponent(`Check out my AI video: ${job.title}\n\n${shareUrl}\n\nMade with Visionary Suite`);
      window.open(`https://wa.me/?text=${text}`, '_blank');
    }
  };
  const handleDelete = async (job) => {
    if (!window.confirm(`Delete "${job.title}"? This cannot be undone.`)) return;
    try { await api.delete(`/api/story-engine/jobs/${job.job_id}`); toast.success('Project deleted'); fetchJobs(); }
    catch { toast.error('Failed to delete project'); }
  };
  const handleCreateAnother = () => navigate('/app/story-video-studio');
  const toggleSection = (section) => setCollapsedSections(prev => ({ ...prev, [section]: !prev[section] }));
  const toggleAutoDownload = () => {
    setAutoDownload(prev => {
      const next = !prev;
      try { localStorage.setItem('vs_auto_download', String(next)); } catch {}
      toast.success(next ? 'Auto-download enabled' : 'Auto-download disabled', { duration: 2000 });
      return next;
    });
  };
  const toggleNotifications = () => {
    if ('Notification' in window) {
      if (Notification.permission === 'granted') setNotificationsEnabled(prev => !prev);
      else if (Notification.permission === 'default') Notification.requestPermission().then(perm => setNotificationsEnabled(perm === 'granted'));
      else toast.error('Notifications are blocked. Enable them in browser settings.');
    }
  };

  const inProgress = jobs.filter(j => ['QUEUED', 'PROCESSING'].includes(j.status));
  const completed = jobs.filter(j => ['COMPLETED', 'PARTIAL'].includes(j.status));
  const failed = jobs.filter(j => ['FAILED'].includes(j.status));

  // ─── Skeleton Loading ───
  if (loading) return <SkeletonLoading />;

  if (jobs.length === 0) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6" data-testid="myspace-empty">
        <div className="flex flex-col items-center justify-center h-64 gap-4">
          <Film className="w-12 h-12 text-zinc-700" />
          <p className="text-zinc-500 text-sm">No projects yet</p>
          <a href="/app/story-video-studio" className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm rounded-lg transition-colors" data-testid="create-first-video-btn">
            Create your first video
          </a>
        </div>
        <HowThisWorks />
      </div>
    );
  }

  return (
    <>
      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6" data-testid="myspace-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-white">My Space</h1>
          <div className="flex items-center gap-1">
            <button onClick={toggleAutoDownload} className={`p-2 rounded-lg transition-colors ${autoDownload ? 'bg-indigo-600/20 text-indigo-400 hover:bg-indigo-600/30' : 'hover:bg-white/5 text-zinc-500 hover:text-white'}`} data-testid="toggle-auto-download-btn" title={autoDownload ? 'Auto-download on' : 'Auto-download off'}>
              <Download className="w-4 h-4" />
            </button>
            <button onClick={toggleNotifications} className={`p-2 rounded-lg transition-colors ${notificationsEnabled ? 'bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/30' : 'hover:bg-white/5 text-zinc-500 hover:text-white'}`} data-testid="toggle-notifications-btn" title={notificationsEnabled ? 'Notifications on' : 'Notifications off'}>
              {notificationsEnabled ? <Bell className="w-4 h-4" /> : <BellOff className="w-4 h-4" />}
            </button>
            <button onClick={fetchJobs} className="p-2 rounded-lg hover:bg-white/5 text-zinc-500 hover:text-white transition-colors" data-testid="refresh-btn">
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* VIRAL ATTRIBUTION BADGE */}
        {viralMyStats?.total_remix_conversions > 0 && (
          <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl bg-violet-500/[0.04] border border-violet-500/10" data-testid="myspace-viral-badge">
            <Flame className="w-4 h-4 text-violet-400 flex-shrink-0" />
            <span className="text-sm font-medium text-violet-300">
              Your stories generated <span className="font-bold text-white">{viralMyStats.total_remix_conversions}</span> viral remix{viralMyStats.total_remix_conversions !== 1 ? 'es' : ''} this week
              {viralMyStats.total_credits_earned > 0 && <span className="text-emerald-400 ml-1">(+{viralMyStats.total_credits_earned} bonus credits)</span>}
            </span>
          </div>
        )}

        {/* Session Streak */}
        {(() => {
          const today = new Date().toDateString();
          const todayCount = jobs.filter(j => j.created_at && new Date(j.created_at).toDateString() === today).length;
          if (todayCount < 1) return null;
          return (
            <div className="flex items-center gap-2 bg-orange-500/5 border border-orange-500/10 rounded-lg px-3 py-2" data-testid="session-streak">
              <Zap className="w-4 h-4 text-orange-400" />
              <p className="text-xs text-orange-300/90">
                You&apos;ve created <span className="font-bold text-orange-300">{todayCount}</span> video{todayCount !== 1 ? 's' : ''} today — keep going
              </p>
            </div>
          );
        })()}

        {/* In Progress */}
        {inProgress.length > 0 && (
          <section>
            <SectionHeader title="In Progress" count={inProgress.length} icon={Loader2} color="#60a5fa" collapsed={collapsedSections.inProgress} onToggle={() => toggleSection('inProgress')} />
            {!collapsedSections.inProgress && (
              <div className="space-y-3 mt-2">
                {inProgress.map(job => (
                  <div key={job.job_id} ref={job.job_id === highlightId ? highlightRef : null}>
                    <ProjectCard job={job} highlighted={job.job_id === highlightId} onShare={handleShare} onRetry={handleRetry} onDelete={handleDelete} onNavigate={handleNavigate} timeEstimates={timeEstimates} userCredits={userCredits} remixCount={remixStats[job.job_id] || 0} />
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* Completed */}
        <section>
          <SectionHeader title="Completed" count={completed.length} icon={CheckCircle} color="#34d399" collapsed={collapsedSections.completed} onToggle={() => toggleSection('completed')} />
          {!collapsedSections.completed && (
            <div className="space-y-3 mt-2">
              {completed.map(job => (
                <div key={job.job_id} ref={job.job_id === highlightId ? highlightRef : null}>
                  <ProjectCard job={job} highlighted={job.job_id === highlightId} justCompleted={justCompletedIds.has(job.job_id)} onShare={handleShare} onRetry={handleRetry} onDelete={handleDelete} onNavigate={handleNavigate} timeEstimates={timeEstimates} userCredits={userCredits} remixCount={remixStats[job.job_id] || 0} />
                </div>
              ))}
            </div>
          )}
          {completed.length === 0 && !collapsedSections.completed && (
            <p className="text-zinc-600 text-xs py-4 text-center">No completed projects yet</p>
          )}
        </section>

        {/* Remix Gallery — "People are remixing these" */}
        <RemixGallery placement="myspace" limit={8} />

        {/* Create Another */}
        <section className="border border-white/[0.06] rounded-xl p-4 bg-white/[0.02]" data-testid="create-another-section">
          <h3 className="text-sm font-semibold text-zinc-300 mb-3">Create another video</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {[
              { label: 'New story', desc: 'Start fresh', path: '/app/story-video-studio' },
              { label: 'Different style', desc: 'Try anime or 3D', path: '/app/story-video-studio?style=explore' },
              { label: 'Make it funny', desc: 'Comedy twist', path: '/app/story-video-studio?tone=comedy' },
              { label: 'Kids story', desc: 'Family friendly', path: '/app/story-video-studio?age=kids' },
            ].map(item => (
              <button key={item.label} onClick={() => navigate(item.path)} className="text-left p-3 rounded-lg bg-zinc-900/60 border border-white/[0.06] hover:border-indigo-500/30 hover:bg-indigo-500/5 transition-all group" data-testid={`create-${item.label.toLowerCase().replace(/\s/g, '-')}-btn`}>
                <p className="text-xs font-medium text-white group-hover:text-indigo-300 transition-colors">{item.label}</p>
                <p className="text-[10px] text-zinc-500 mt-0.5">{item.desc}</p>
              </button>
            ))}
          </div>
        </section>

        {/* Needs Attention */}
        {failed.length > 0 && (
          <section>
            <SectionHeader title="Needs Attention" count={failed.length} icon={AlertTriangle} color="#f87171" collapsed={collapsedSections.failed} onToggle={() => toggleSection('failed')} />
            {!collapsedSections.failed && (
              <div className="space-y-3 mt-2">
                {failed.map(job => (
                  <div key={job.job_id} ref={job.job_id === highlightId ? highlightRef : null}>
                    <ProjectCard job={job} highlighted={job.job_id === highlightId} onShare={handleShare} onRetry={handleRetry} onDelete={handleDelete} onNavigate={handleNavigate} timeEstimates={timeEstimates} userCredits={userCredits} remixCount={remixStats[job.job_id] || 0} />
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* How This Works */}
        <HowThisWorks />
      </div>

      {/* Completion Prompt Modal */}
      {completionPromptJob && (
        <CompletionPromptModal job={completionPromptJob} onClose={() => setCompletionPromptJob(null)} onDownload={triggerDownload} onShareWhatsApp={handleShare} onCreateAnother={handleCreateAnother} />
      )}
    </>
  );
}
