import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Play, Download, Share2, RefreshCw, AlertTriangle, Film, Loader2,
  ChevronDown, ChevronUp, Bell, BellOff, Check, Plus, X, Trash2,
  Edit, Eye, Info, CheckCircle, Circle, HelpCircle, Clock, ArrowRight,
  Coins, Sparkles, Palette, BookOpen, Zap, Users, Flame, Layers
} from 'lucide-react';
import { toast } from 'sonner';
import { toastErrorSafe } from '../utils/toastSafe';
import api from '../utils/api';
import { trackEvent } from '../utils/analytics';
import { trackFunnel } from '../utils/funnelTracker';
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

async function triggerDownload(job) {
  // P0 2026-05-16 — modal trust-flow audit follow-up.
  //
  // PREVIOUS BEHAVIOR (broken on Safari/iOS): used a synchronous
  // <a href={job.output_url} download> click on the raw R2/S3 URL. For
  // cross-origin assets, browsers ignore the `download` attribute and
  // OPEN the asset in a new tab → users perceived "Download doesn't work."
  //
  // NEW BEHAVIOR: mirrors EntitledDownloadButton's canonical flow:
  //   1. POST /api/media/download-token/{job_id} — backend re-checks
  //      entitlement + asset state + issues a short-lived signed URL.
  //   2. Fetch the signed URL as a blob, create an Object URL, click an
  //      <a download> on THAT blob. Blob URLs honor `download` on every
  //      browser including Safari/iOS.
  //   3. All failure modes (403 paywall / 202 processing / 410 expired /
  //      404 missing / 5xx upstream) surface a structured toast with
  //      Reference ID from the X-Request-Id response header.
  if (!job?.job_id) {
    toast.error('Unable to download: missing project id.');
    return;
  }
  const apiUrl = process.env.REACT_APP_BACKEND_URL;
  const token = localStorage.getItem('token');
  let res;
  try {
    res = await fetch(`${apiUrl}/api/media/download-token/${job.job_id}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });
  } catch (_) {
    toast.error('Network error. Please check your connection and try again.');
    return;
  }
  const requestId = res.headers.get('X-Request-Id') || res.headers.get('x-request-id') || 'n/a';

  if (res.status === 403) {
    toast.error('Downloads are available on paid plans. Please upgrade.');
    return;
  }
  if (res.status === 202) {
    const data = await res.json().catch(() => ({}));
    toast.info(data?.detail?.message || 'Video is still processing. Please wait.');
    return;
  }
  if (res.status === 410 || res.status === 404) {
    const data = await res.json().catch(() => ({}));
    const msg = (typeof data?.detail === 'object' ? data?.detail?.message : data?.detail) ||
      'This video is no longer available for download.';
    toast.error(`${msg}\nReference ID: ${requestId}`);
    return;
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    const msg = (typeof data?.detail === 'object' ? data?.detail?.message : data?.detail) ||
      'Download not available yet.';
    toast.error(`${msg}\nReference ID: ${requestId}`);
    return;
  }

  const data = await res.json().catch(() => ({}));
  if (!data?.success || !data?.download_url) {
    toast.error(`Download response was empty. Please try again.\nReference ID: ${requestId}`);
    return;
  }

  // Fetch as blob so `download` attribute is honored on every browser.
  try {
    const dlRes = await fetch(data.download_url);
    if (!dlRes.ok) throw new Error('Download fetch failed');
    const blob = await dlRes.blob();
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = `${(job.title || 'video').replace(/[^a-z0-9]/gi, '-').toLowerCase()}-visionary-suite.mp4`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(blobUrl);
    toast.success('Download started!');
  } catch (_) {
    // Cross-origin blob fetch can fail if R2 CORS is missing.
    // Fall back to opening the SIGNED URL (still ephemeral, still safe).
    window.open(data.download_url, '_blank', 'noopener,noreferrer');
    toast.success('Download started!');
  }
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

function SkeletonLoading({ highlightId }) {
  // When arriving from Generate Video with ?projectId=<id>, show a focused
  // "preparing your video" card instead of the generic placeholder grid —
  // avoids the perceived blank-screen flash during the handoff.
  if (highlightId) {
    return (
      <div
        className="max-w-4xl mx-auto px-4 py-10 flex flex-col items-center justify-center min-h-[60vh]"
        data-testid="myspace-project-loading"
      >
        <div className="relative inline-flex items-center justify-center w-16 h-16 mb-5">
          <div className="absolute inset-0 rounded-full border-2 border-violet-500/20" />
          <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-violet-400 animate-spin" />
          <Sparkles className="w-6 h-6 text-violet-300" />
        </div>
        <h2 className="text-xl font-bold text-white mb-1.5">Loading your video progress...</h2>
        <p className="text-sm text-slate-400 mb-4">Fetching the latest status.</p>
        <p className="text-[11px] text-slate-500">Do not close this tab.</p>
      </div>
    );
  }
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
// P0 2026-05-16 — bounded fix for the four broken post-gen action cards.
// Each variant declares: destination route, remix mode, localStorage key,
// and an optional `injectComedy` flag. The click handler reads these and
// writes the correct shape so the destination tool's hydration code picks
// it up. Previously all four navigated to /app/story-video-studio with
// `state` payload only — which the studio doesn't read (it reads
// localStorage.getItem('remix_video')) → silent no-ops.
const VARIATION_BUTTONS = [
  {
    label: 'Make it funnier', icon: Sparkles, desc: 'Same story, comedy twist',
    route: '/app/story-video-studio',
    mode: 'funny',
    storageKey: 'remix_video',
    injectComedy: true,
  },
  {
    label: 'Change style', icon: Palette, desc: 'Try anime, 3D, or watercolor',
    route: '/app/story-video-studio',
    mode: 'style',
    storageKey: 'remix_video',
    injectComedy: false,
  },
  {
    label: 'Turn into reel', icon: Zap, desc: 'Shorter, punchier version',
    route: '/app/reel-generator',
    mode: 'reel',
    storageKey: 'remix_data',
    injectComedy: false,
  },
  {
    label: 'Turn into storybook', icon: BookOpen, desc: 'Classic illustrated style',
    route: '/app/comic-storybook',
    mode: 'storybook',
    storageKey: 'remix_data',
    injectComedy: false,
  },
];

// ─── PHOTO TRAILER CARD (YouStar — minimal, isolated from story-engine logic) ─
function PhotoTrailerCard({ job, justCompleted, isPulsing, onLeave, onNavigate }) {
  const navigate = useNavigate();
  const status = job.status || 'PROCESSING';
  const isProcessing = status === 'PROCESSING' || status === 'QUEUED';
  const isCompleted = status === 'COMPLETED';
  const isFailed = status === 'FAILED';
  const created = job.created_at ? new Date(job.created_at).toLocaleDateString() : '';

  const tint = isCompleted ? 'border-emerald-400/30 bg-emerald-500/[0.04]'
            : isFailed     ? 'border-rose-400/30 bg-rose-500/[0.04]'
            :                'border-violet-400/30 bg-violet-500/[0.04]';

  return (
    <div
      data-testid={`myspace-trailer-card-${job.job_id}`}
      className={`relative rounded-xl border transition-all duration-300 overflow-hidden ${tint} ${
        justCompleted
          ? 'ring-2 ring-emerald-400/40 animate-[pulse_2s_ease-in-out_3]'
          : isPulsing
            ? 'ring-2 ring-violet-400/60 animate-[pulse_1s_ease-in-out_2]'
            : ''
      }`}
    >
      <div className="flex items-start gap-3 p-4">
        <div className="w-16 h-16 rounded-lg bg-zinc-800/80 flex items-center justify-center overflow-hidden flex-shrink-0">
          {job.thumbnail_url
            ? <img src={job.thumbnail_url} alt="" className="w-full h-full object-cover" />
            : <span className="text-violet-300/60 text-[10px] font-mono">YouStar</span>}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-300 border border-violet-500/30">YouStar Trailer</span>
            <span className={`text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${
              isCompleted ? 'bg-emerald-500/20 text-emerald-300' :
              isFailed    ? 'bg-rose-500/20 text-rose-300' :
                            'bg-violet-500/20 text-violet-300'
            }`}>{status}</span>
            {/* Plan-tier badge — frozen at job creation time so MySpace
                accurately shows what the user paid for, even if they later
                downgrade. PREMIUM gets the gold crown treatment. */}
            {job.plan_tier_at_creation === 'PREMIUM' && (
              <span
                className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-gradient-to-r from-amber-500/30 to-fuchsia-500/30 text-amber-200 border border-amber-400/30"
                data-testid={`myspace-trailer-plan-${job.job_id}`}
              >
                ✦ Premium
              </span>
            )}
            {job.plan_tier_at_creation === 'PAID' && (
              <span
                className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-violet-500/15 text-violet-200 border border-violet-400/20"
                data-testid={`myspace-trailer-plan-${job.job_id}`}
              >
                Paid
              </span>
            )}
          </div>
          <h3 className="text-white font-semibold mt-1 truncate" data-testid={`myspace-trailer-title-${job.job_id}`}>
            {job.title || 'YouStar Trailer'}
          </h3>
          <p className="text-xs text-zinc-400 mt-0.5">{created}{job.duration_target_seconds ? ` · ${job.duration_target_seconds}s` : ''}</p>
          {isProcessing && (
            <div className="mt-2">
              <div className="h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-violet-500 to-fuchsia-500 transition-all duration-500"
                  style={{ width: `${job.progress || 0}%` }}
                />
              </div>
              <p className="text-[11px] text-zinc-500 mt-1">{job.current_stage || 'Working on it'} · {job.progress || 0}%</p>
            </div>
          )}
          {isFailed && job.error_message && (
            <p className="text-xs text-rose-300/90 mt-1.5">{job.error_message}</p>
          )}
        </div>
      </div>
      <div className="flex gap-2 px-4 pb-4">
        {isCompleted && (
          <button
            onClick={async () => {
              try {
                const r = await api.get(`/api/photo-trailer/jobs/${job.job_id}/stream`);
                if (r.data?.url) window.open(r.data.url, '_blank', 'noopener,noreferrer');
                else if (job.output_url) window.open(job.output_url, '_blank', 'noopener,noreferrer');
              } catch {
                if (job.output_url) window.open(job.output_url, '_blank', 'noopener,noreferrer');
              }
            }}
            className="flex-1 py-2 px-3 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-sm font-semibold transition-colors"
            data-testid={`myspace-trailer-play-${job.job_id}`}
          >
            ▶ Wide
          </button>
        )}
        {isCompleted && (
          <button
            onClick={async () => {
              try {
                const r = await api.get(`/api/photo-trailer/jobs/${job.job_id}/stream?format=vertical`);
                if (r.data?.url) window.open(r.data.url, '_blank', 'noopener,noreferrer');
                else if (job.output_url) window.open(job.output_url, '_blank', 'noopener,noreferrer');
              } catch {
                if (job.output_url) window.open(job.output_url, '_blank', 'noopener,noreferrer');
              }
            }}
            className="flex-1 py-2 px-3 rounded-lg bg-fuchsia-600 hover:bg-fuchsia-500 text-white text-sm font-semibold transition-colors"
            data-testid={`myspace-trailer-play-vertical-${job.job_id}`}
            title="Play vertical (Reels / Shorts / TikTok / WhatsApp Status)"
          >
            ▶ 9:16
          </button>
        )}
        {isFailed && (
          <button
            onClick={() => navigate('/app/photo-trailer')}
            className="flex-1 py-2 px-3 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-sm font-semibold transition-colors"
            data-testid={`myspace-trailer-retry-${job.job_id}`}
          >
            Try again
          </button>
        )}
        {isProcessing && (
          <>
            <button
              onClick={() => onNavigate ? onNavigate(job) : navigate('/app/photo-trailer')}
              className="flex-1 py-2 px-3 rounded-lg bg-violet-500/15 hover:bg-violet-500/25 active:scale-[0.97] text-violet-200 text-sm font-semibold transition-all"
              data-testid={`myspace-trailer-track-${job.job_id}`}
            >
              View progress
            </button>
            <button
              onClick={() => onLeave ? onLeave(job) : navigate('/app')}
              className="flex-1 py-2 px-3 rounded-lg bg-white/5 hover:bg-white/10 active:scale-[0.97] text-zinc-300 text-sm transition-all"
              data-testid={`myspace-trailer-leave-${job.job_id}`}
            >
              Leave & come back later
            </button>
          </>
        )}
      </div>
    </div>
  );
}

// ─── PROJECT CARD (UNIFIED) ──────────────────────────────────────────────────
// Dispatches between the legacy story-engine card and the new YouStar trailer
// card. Wrapper-only — keeps each component pure with no conditional hooks.
function ProjectCard(props) {
  if (props.job?.type === 'photo_trailer') {
    return <PhotoTrailerCard job={props.job} justCompleted={props.justCompleted} isPulsing={props.isPulsing} onLeave={props.onLeave} onNavigate={props.onNavigate} />;
  }
  return <StoryProjectCard {...props} />;
}

function StoryProjectCard({ job, highlighted, justCompleted, isPulsing, onShare, onRetry, onDelete, onNavigate, onLeave, onImproveConsistency, timeEstimates, userCredits, remixCount }) {
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

  const handleWatch = () => {
    // ─── P0 2026-05-21 — Bug-class elimination: false-success Preview CTA.
    // The Preview button used to silently no-op when `output_url` was
    // missing on a COMPLETED job. That made the entire success UI a
    // lie — "Your video is ready" + an enabled Preview that does
    // nothing. Trust-destroying.
    //
    // The button is now visually gated (disabled={!hasPlayableVideo})
    // below, but we ALSO defensively handle the case where this
    // function is invoked without a URL (e.g. via accessibility
    // tooling that ignores the disabled attribute, or via a race
    // where output_url is cleared after first render). Never let
    // a click vanish without feedback.
    if (job.output_url) {
      window.open(job.output_url, '_blank', 'noopener,noreferrer');
      return;
    }
    const requestId = window.lastRequestId || job.job_id || 'n/a';
    toastErrorSafe(
      'Preview unavailable — render asset is not yet attached to this project. Please refresh in a moment.',
      {
        requestId,
        code: 'MY_SPACE_PREVIEW_NOT_READY',
        page: '/app/my-space',
        id: `my-space-preview-not-ready-${job.job_id}`,
        duration: 7000,
      }
    );
    // Best-effort observability emit so we can see in production
    // how often a COMPLETED job lands without a playable URL.
    try {
      api.post('/api/diagnostics/beacon', {
        events: [{
          metric: 'my_space_preview_clicked_without_url_total',
          ts: Date.now(),
          page: '/app/my-space',
          meta: {
            job_id: job.job_id,
            status: job.status,
            request_id: requestId,
            has_thumbnail: Boolean(job.thumbnail_url),
          },
        }],
      }).catch(() => {});
    } catch (_) { /* never break UX */ }
  };
  // ─── P0 2026-05-21 — Canonical "is this actually playable?" predicate.
  // Used to gate the Preview / Watch CTAs visually. A job is playable
  // iff it has a non-empty output_url. This is the single source of
  // truth — NEVER trust `status === 'COMPLETED'` alone.
  const hasPlayableVideo = Boolean(job.output_url);

  const handleVariation = (variant) => {
    // P0 2026-05-16 — bounded fix for the four broken post-gen action cards.
    // ROOT CAUSE: previous handler did navigate(path, { state: payload }),
    // but the destination tools don't read location.state — they hydrate
    // from localStorage. So all four buttons silently no-op'd.
    //
    // FIX: validate source ids first, write to the CORRECT localStorage
    // key with the CORRECT shape, then navigate to the CORRECT route with
    // ?source_job=<id> for traceability.

    // Guard 1: source job must exist
    if (!job?.job_id) {
      const rid = (window.lastRequestId || 'n/a');
      toast.error(`Unable to load source project. Reference ID: ${rid}`);
      return;
    }

    // Guard 2: source must have story content (every variant needs it)
    const sourceStory = job.story_text || job.prompt || job.title || '';
    if (!sourceStory.trim()) {
      toast.error('Unable to load source project: missing story content.');
      return;
    }

    const sourceTitle = job.title || 'Untitled Project';
    const sourceJobId = job.job_id;

    if (variant.storageKey === 'remix_video') {
      // Story Video Studio shape — read in StoryVideoPipeline init when
      // ?remix=... query param is present.
      // For "Make it funnier" we inject a comedy directive at the head of
      // the story so the LLM generates a funnier variant of the same plot;
      // for "Change style" we keep the original story untouched and let
      // the user pick a new animation_style in the studio's style picker.
      const story = variant.injectComedy
        ? `[Make this funnier — same plot, comedy twist, exaggerated reactions]\n\n${sourceStory}`
        : sourceStory;
      try {
        localStorage.setItem('remix_video', JSON.stringify({
          parent_video_id: sourceJobId,
          title: sourceTitle,
          story_text: story,
          age_group: job.age_group,
          voice_preset: job.voice_preset,
          // Deliberately omit animation_style for "Change style" so the
          // studio's style picker prompts the user to choose a new one.
          ...(variant.injectComedy ? { animation_style: job.animation_style } : {}),
        }));
      } catch (e) {
        toast.error('Could not stage variation. Please try again.');
        return;
      }
      navigate(
        `${variant.route}?remix=${variant.mode}&source_job=${encodeURIComponent(sourceJobId)}`,
      );
      toast.success(`Opening: ${variant.label}`);
      return;
    }

    if (variant.storageKey === 'remix_data') {
      // Reel + Storybook shape — read by useRemixData hook on the
      // destination tool's mount.
      const sourceToolKey = variant.mode === 'reel' ? 'reels' : 'comic-storybook';
      try {
        localStorage.setItem('remix_data', JSON.stringify({
          timestamp: Date.now(),
          prompt: sourceStory,
          source_tool: 'myspace-reengage',
          source_slug: sourceJobId,
          remixFrom: {
            title: sourceTitle,
            prompt: sourceStory,
            tool: 'story-video-studio',
            parentId: sourceJobId,
          },
          // Provide canonical seed fields the destination tools accept
          ...(variant.mode === 'reel' ? {
            topic: sourceTitle,
            tone: 'energetic',
          } : {
            story_text: sourceStory,
            genre: 'adventure',
          }),
        }));
      } catch (e) {
        toast.error('Could not stage variation. Please try again.');
        return;
      }
      navigate(
        `${variant.route}?source_job=${encodeURIComponent(sourceJobId)}&source_tool=${sourceToolKey}`,
      );
      toast.success(`Opening: ${variant.label}`);
      return;
    }

    // Defensive: should never reach here. Surface structured error.
    toast.error('Unknown variation type. Please refresh and try again.');
  };

  return (
    <div
      data-testid={`project-card-${job.job_id}`}
      className={`relative rounded-xl border transition-all duration-300 overflow-hidden ${copy.bgTint} ${
        justCompleted
          ? 'border-emerald-400 ring-2 ring-emerald-400/30 animate-[pulse_2s_ease-in-out_3]'
          : isPulsing
            ? 'border-blue-400 ring-2 ring-blue-400/40 animate-[pulse_1s_ease-in-out_2]'
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
              <button data-testid={`view-details-btn-${job.job_id}`} onClick={() => onNavigate(job)} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/15 text-amber-300 text-xs font-medium hover:bg-amber-500/25 active:scale-[0.97] transition-all">
                <Eye className="w-3.5 h-3.5" /> View Details
              </button>
            )}
            {/* PROCESSING */}
            {statusKey === 'PROCESSING' && (
              <>
                <button data-testid={`view-progress-btn-${job.job_id}`} onClick={() => onNavigate(job)} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-500/15 text-blue-300 text-xs font-medium hover:bg-blue-500/25 active:scale-[0.97] transition-all">
                  <Eye className="w-3.5 h-3.5" /> View Progress
                </button>
                <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.06] text-zinc-400 text-xs hover:bg-white/10 active:scale-[0.97] transition-all" onClick={() => onLeave(job)} data-testid={`leave-btn-${job.job_id}`}>
                  <ArrowRight className="w-3.5 h-3.5" /> Leave & come back later
                </button>
              </>
            )}
            {/* COMPLETED / PARTIAL */}
            {(statusKey === 'COMPLETED' || statusKey === 'PARTIAL') && (
              <>
                {/* ─── P0 2026-05-21 — Preview CTA is gated on
                    hasPlayableVideo (Boolean(job.output_url)), NOT on
                    status === COMPLETED. A completed job without a
                    URL renders the button in a non-actionable
                    "Finalizing…" state instead of a lying enabled
                    Preview. */}
                {hasPlayableVideo ? (
                  <button data-testid={`preview-btn-${job.job_id}`} onClick={handleWatch} className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-500/20 text-emerald-300 text-xs font-bold hover:bg-emerald-500/30 transition-colors">
                    <Play className="w-4 h-4" /> Preview
                  </button>
                ) : (
                  <button
                    data-testid={`preview-btn-finalizing-${job.job_id}`}
                    onClick={handleWatch}
                    disabled
                    aria-disabled="true"
                    title="Preview will appear once the render asset is attached"
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-500/10 text-emerald-400/60 text-xs font-bold cursor-not-allowed opacity-70"
                  >
                    <Play className="w-4 h-4" /> Finalizing…
                  </button>
                )}
                <button data-testid={`download-btn-${job.job_id}`} onClick={(e) => { e.stopPropagation(); triggerDownload(job); }} disabled={!hasPlayableVideo} aria-disabled={!hasPlayableVideo} title={hasPlayableVideo ? undefined : 'Download will be available once the render is attached'} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-colors ${hasPlayableVideo ? 'bg-white/[0.06] text-zinc-300 hover:bg-white/10' : 'bg-white/[0.03] text-zinc-500 cursor-not-allowed opacity-60'}`}>
                  <Download className="w-3.5 h-3.5" /> Download
                </button>
                <button data-testid={`share-btn-${job.job_id}`} onClick={(e) => { e.stopPropagation(); onShare(job); }} disabled={!hasPlayableVideo} aria-disabled={!hasPlayableVideo} title={hasPlayableVideo ? undefined : 'Share will be available once the render is attached'} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-colors ${hasPlayableVideo ? 'bg-white/[0.06] text-zinc-300 hover:bg-white/10' : 'bg-white/[0.03] text-zinc-500 cursor-not-allowed opacity-60'}`}>
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
  // P0 2026-05-16 — modal trust-flow audit fixes:
  //   • ESC key closes modal (was: no keyboard support)
  //   • Body scroll-lock while open (was: page scrolled behind backdrop)
  //   • Listeners cleaned up on unmount / job change (no memory leak)
  React.useEffect(() => {
    if (!job) return undefined;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [job, onClose]);
  if (!job) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 overflow-y-auto"
      data-testid="completion-prompt-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="completion-prompt-heading"
    >
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} data-testid="completion-prompt-backdrop" />
      <div className="relative w-full max-w-sm my-auto bg-zinc-900 border border-zinc-700/50 rounded-2xl overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-200 max-h-[calc(100vh-2rem)] overflow-y-auto">
        <style>{`@keyframes pulseShare { 0%,100% { box-shadow: 0 0 0 0 rgba(16,185,129,0.5); } 50% { box-shadow: 0 0 0 12px rgba(16,185,129,0); } }`}</style>
        <button onClick={onClose} className="absolute top-3 right-3 z-10 p-1 rounded-full bg-zinc-800/80 hover:bg-zinc-700 text-zinc-400 hover:text-white transition-colors" data-testid="completion-prompt-close" aria-label="Close completion prompt">
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
            <h3 id="completion-prompt-heading" className="text-white font-semibold text-base truncate" data-testid="completion-prompt-title">{job.title}</h3>
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

  // P0 2026-05-16 — strict status allow-list for MySpace items.
  // ROOT-CAUSE GUARD: previous fetchJobs used the fallthrough pattern
  // `status === 'completed' ? 'COMPLETED' : status === 'failed' ? 'FAILED'
  //  : 'PROCESSING'` which contaminated unrelated cards as "processing".
  // This canonicalizer:
  //   • accepts both lower and upper case backend values
  //   • maps anything unknown / cancelled / expired / orphaned / archived
  //     / empty / null → ARCHIVED so it lands in a non-active section
  //   • never synthesizes 50% progress for unknown statuses
  const __ALLOWED_LIVE = new Set(['PROCESSING', 'QUEUED', 'PENDING', 'RENDERING']);
  const __ALLOWED_TERMINAL = new Set(['COMPLETED', 'FAILED', 'PARTIAL']);
  function normalizeJobStatus(raw) {
    const s = (raw || '').toString().toUpperCase();
    if (__ALLOWED_LIVE.has(s)) return s === 'PENDING' || s === 'RENDERING' ? 'PROCESSING' : s;
    if (__ALLOWED_TERMINAL.has(s)) return s;
    if (s === 'PARTIAL_READY') return 'PARTIAL';
    // Anything else — stale, archived, cancelled, orphaned, empty, null —
    // explicitly NOT in progress. Bucket it into ARCHIVED.
    return 'ARCHIVED';
  }

// ═══ LocatingProjectCard — canonical generation surface ═════════════════════
// P0 2026-05-24 invariant: when the user lands on MySpace with
// ?projectId=<id> they have JUST clicked Generate Video. This card is
// the primary surface they live on until generation completes.
// P0 2026-05-25 upgrade: real % progress bar with stage breakdown,
// estimated-progress fallback when backend returns 0, 90s stale-state
// escalation, hard timeout → retryable failed state, rotating
// engagement panel (copyright-free tips/quotes), success toast +
// auto-navigate to MySpace listing on COMPLETED. Trust-bug class
// eliminated: infinite "Preparing scenes" with no progress.
//
// Card states (machine):
//   LOCATING  → initial probe in flight or transient retry
//   RUNNING   → job found, polling every 4s
//   STALE     → no status change for 90s → "still rendering" copy
//   READY     → status === COMPLETED → toast + 3s auto-redirect to listing
//   FAILED    → status === FAILED or 8-min hard timeout → Retry CTA
//   NOT_FOUND → 3× 404 from status endpoint → recovery card

// Stage progress floor map — server returns canonical state via /status.
// We anchor a floor % per stage so that even when backend `progress` is
// momentarily 0 (between writes) the bar never moves backward.
const __STAGE_PROGRESS = [
  { key: 'INIT',                       floor: 4,  label: 'Request accepted' },
  { key: 'PLANNING',                   floor: 12, label: 'Writing story scenes' },
  { key: 'BUILDING_CHARACTER_CONTEXT', floor: 18, label: 'Building character profiles' },
  { key: 'PLANNING_SCENE_MOTION',      floor: 24, label: 'Planning scene compositions' },
  { key: 'GENERATING_KEYFRAMES',       floor: 35, label: 'Creating visuals' },
  { key: 'GENERATING_SCENE_CLIPS',     floor: 55, label: 'Adding motion' },
  { key: 'GENERATING_AUDIO',           floor: 72, label: 'Adding voice & music' },
  { key: 'ASSEMBLING_VIDEO',           floor: 86, label: 'Rendering final video' },
  { key: 'VALIDATING',                 floor: 95, label: 'Saving to My Space' },
  { key: 'READY',                      floor: 100, label: 'Your video is ready' },
];

// Copyright-free engagement copy — rotated every 10s.
// No brand names, scraped quotes, or third-party trademarks.
const __ENGAGEMENT_TIPS = [
  { kind: 'quote', text: 'The story you imagine is the story only you can tell.' },
  { kind: 'quote', text: 'Every great video starts with a single brave idea.' },
  { kind: 'quote', text: 'Patience is the secret ingredient of every great render.' },
  { kind: 'quote', text: 'Your audience is waiting for a story only you can give them.' },
  { kind: 'quote', text: 'Done is better than perfect — your first video is the spark.' },
  { kind: 'try',   text: 'Try Character Memory next — give your characters a persistent identity.' },
  { kind: 'try',   text: 'Reel Generator can turn this story into a short-form viral clip.' },
  { kind: 'try',   text: 'Bedtime Stories generates calming narrated journeys for kids.' },
  { kind: 'try',   text: 'My Movie Trailer turns your photos into a 60s cinematic teaser.' },
  { kind: 'tip',   text: 'Renders typically take 2–5 minutes depending on scene count.' },
  { kind: 'tip',   text: 'Higher quality mode adds detail but extends total render time.' },
  { kind: 'tip',   text: 'You can leave this page — we will save the result to My Space automatically.' },
];

const STALE_AFTER_MS = 90 * 1000;        // 90s of no state change → "Still rendering"
const HARD_TIMEOUT_MS = 8 * 60 * 1000;   // 8 minutes → fail + Retry
const TIP_ROTATION_MS = 10 * 1000;
const POLL_INTERVAL_MS = 4000;
const TERMINAL_OK = new Set(['COMPLETED', 'READY', 'PARTIAL', 'PARTIAL_READY']);
const TERMINAL_FAIL = new Set(['FAILED', 'FAILED_PLANNING', 'FAILED_IMAGES', 'FAILED_TTS', 'FAILED_RENDER']);

function _stageInfo(state) {
  const idx = __STAGE_PROGRESS.findIndex(s => s.key === (state || '').toString().toUpperCase());
  if (idx < 0) return { floor: 4, label: 'Preparing scenes', index: 0, total: __STAGE_PROGRESS.length };
  return { ...__STAGE_PROGRESS[idx], index: idx, total: __STAGE_PROGRESS.length };
}

function _estimateProgress({ backendProgress, state, startedAt, lastBackendProgress }) {
  // Authoritative backend % wins when it's a real positive number.
  if (typeof backendProgress === 'number' && backendProgress > 0) {
    return Math.max(lastBackendProgress || 0, Math.min(99, backendProgress));
  }
  // Else: floor for the current state + a small elapsed-time creep
  // bounded by the NEXT stage's floor so the bar advances honestly
  // without lying about completion.
  const stage = _stageInfo(state);
  const next = __STAGE_PROGRESS[stage.index + 1];
  const cap = (next?.floor ?? 99) - 1;
  const elapsedSec = (Date.now() - startedAt) / 1000;
  // 1% per ~6s of dwell time within a stage, capped by next floor.
  const creep = Math.min(cap - stage.floor, Math.floor(elapsedSec / 6));
  return Math.max(lastBackendProgress || 0, stage.floor + Math.max(0, creep));
}

function LocatingProjectCard({ projectId, onRefresh }) {
  const navigate = useNavigate();
  const [cardState, setCardState] = useState('LOCATING'); // LOCATING|RUNNING|STALE|READY|FAILED|NOT_FOUND
  const [job, setJob] = useState(null);
  const [tipIdx, setTipIdx] = useState(0);
  const [displayPct, setDisplayPct] = useState(2);
  const [redirectCountdown, setRedirectCountdown] = useState(null);
  const [hardError, setHardError] = useState(null);

  const cancelledRef = useRef(false);
  const startedAtRef = useRef(Date.now());
  const lastChangeAtRef = useRef(Date.now());
  const lastStateRef = useRef(null);
  const lastBackendProgressRef = useRef(0);
  const completedFiredRef = useRef(false);
  const missingCountRef = useRef(0);

  // Probe loop
  useEffect(() => {
    cancelledRef.current = false;
    let timer = null;

    const probe = async () => {
      // Hard timeout — refuse to wait forever
      if (Date.now() - startedAtRef.current > HARD_TIMEOUT_MS) {
        if (cancelledRef.current) return;
        setHardError('Generation took longer than expected. Please retry.');
        setCardState('FAILED');
        return;
      }
      try {
        const res = await api.get(`/api/story-engine/status/${projectId}`);
        if (cancelledRef.current) return;
        const data = res?.data || {};
        const rawStatus = (data.status || data.state || '').toString().toUpperCase();
        const rawState = (data.state || rawStatus || '').toString().toUpperCase();
        const stageLabel = _stageInfo(rawState).label;
        const friendly = data.current_step || data.current_stage || stageLabel;
        const backendProgress = typeof data.progress === 'number' ? data.progress : null;
        if (backendProgress != null && backendProgress > lastBackendProgressRef.current) {
          lastBackendProgressRef.current = backendProgress;
        }

        // Detect state change for stale-watchdog
        if (rawState !== lastStateRef.current) {
          lastStateRef.current = rawState;
          lastChangeAtRef.current = Date.now();
        }

        const nextJob = {
          job_id: projectId,
          title: data.title || 'Your new video',
          state: rawState,
          status: rawStatus,
          progress: backendProgress,
          current_stage: friendly,
          stage_label: stageLabel,
          output_url: data.output_url || null,
          thumbnail_url: data.thumbnail_url || null,
          error: data.error || data.error_message || null,
          retry_info: data.retry_info || null,
        };
        setJob(nextJob);
        missingCountRef.current = 0;

        // Terminal — success
        if (TERMINAL_OK.has(rawState) || TERMINAL_OK.has(rawStatus)) {
          setDisplayPct(100);
          setCardState('READY');
          // Refresh listing so the new card appears the moment we navigate
          try { onRefresh && onRefresh(); } catch (_) {}
          return; // stop polling
        }
        // Terminal — failure
        if (TERMINAL_FAIL.has(rawState) || TERMINAL_FAIL.has(rawStatus)) {
          setHardError(nextJob.error || 'Generation failed.');
          setCardState('FAILED');
          return;
        }
        // Stale watchdog — no state change for 90s
        const stale = Date.now() - lastChangeAtRef.current > STALE_AFTER_MS;
        setCardState(stale ? 'STALE' : 'RUNNING');
        timer = setTimeout(probe, POLL_INTERVAL_MS);
      } catch (err) {
        if (cancelledRef.current) return;
        const httpStatus = err?.response?.status;
        if (httpStatus === 404) {
          missingCountRef.current += 1;
          if (missingCountRef.current >= 3) {
            setCardState('NOT_FOUND');
            return;
          }
          timer = setTimeout(probe, 2500);
        } else if (httpStatus === 403) {
          setCardState('NOT_FOUND');
        } else {
          // Transient — keep trying (the watchdog will escalate to STALE)
          timer = setTimeout(probe, 3000);
        }
      }
    };

    probe();
    return () => {
      cancelledRef.current = true;
      if (timer) clearTimeout(timer);
    };
  }, [projectId, onRefresh]);

  // Tip rotation
  useEffect(() => {
    if (cardState === 'READY' || cardState === 'FAILED' || cardState === 'NOT_FOUND') return undefined;
    const t = setInterval(() => {
      setTipIdx(i => (i + 1) % __ENGAGEMENT_TIPS.length);
    }, TIP_ROTATION_MS);
    return () => clearInterval(t);
  }, [cardState]);

  // Progress animator — recomputes every second so the % moves even
  // when backend hasn't replied yet.
  useEffect(() => {
    if (cardState === 'READY') return undefined;
    if (cardState === 'FAILED' || cardState === 'NOT_FOUND') return undefined;
    const tick = () => {
      const next = _estimateProgress({
        backendProgress: job?.progress,
        state: job?.state,
        startedAt: startedAtRef.current,
        lastBackendProgress: lastBackendProgressRef.current,
      });
      setDisplayPct(prev => Math.max(prev, Math.min(99, next)));
    };
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
  }, [job, cardState]);

  // Completion handoff — toast + 3s auto-navigate to /app/my-space
  useEffect(() => {
    if (cardState !== 'READY' || completedFiredRef.current) return undefined;
    completedFiredRef.current = true;
    try {
      toast.success(`Your video is ready and saved to My Space.`, { duration: 4000, id: `ready-${projectId}` });
    } catch (_) {}
    setRedirectCountdown(3);
    const interval = setInterval(() => {
      setRedirectCountdown(c => (typeof c === 'number' ? c - 1 : c));
    }, 1000);
    const t = setTimeout(() => {
      try { onRefresh && onRefresh(); } catch (_) {}
      // Land on the listing (no projectId) so the new card is rendered cleanly.
      navigate('/app/my-space', { replace: true });
    }, 3000);
    return () => {
      clearInterval(interval);
      clearTimeout(t);
    };
  }, [cardState, navigate, onRefresh, projectId]);

  // ── Failure recovery: route to studio with retry context ──
  const handleRetry = () => {
    navigate(`/app/story-video-studio?retry=${encodeURIComponent(projectId)}`);
  };

  // ── Renderers ──
  const stage = _stageInfo(job?.state);
  const tip = __ENGAGEMENT_TIPS[tipIdx];

  // NOT_FOUND
  if (cardState === 'NOT_FOUND') {
    return (
      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6" data-testid="myspace-locating">
        <div className="rounded-2xl border border-amber-500/30 bg-gradient-to-br from-slate-900 via-slate-900 to-amber-950/30 p-6 space-y-4">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-amber-500/15 flex items-center justify-center shrink-0">
              <AlertTriangle className="w-6 h-6 text-amber-400" data-testid="locating-error-icon" />
            </div>
            <div className="flex-1">
              <h3 className="text-base font-bold text-white" data-testid="locating-title">
                We couldn&apos;t locate that project
              </h3>
              <p className="text-sm text-slate-400 mt-1">
                Your video may still be saving. Try refreshing, or go back to the studio.
                No credits were spent if the job was never recorded.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={() => onRefresh && onRefresh()} className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-white text-sm flex items-center gap-2 transition-colors" data-testid="locating-refresh-btn">
              <RefreshCw className="w-4 h-4" /> Refresh
            </button>
            <button onClick={() => navigate('/app/story-video-studio')} className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm flex items-center gap-2 transition-colors" data-testid="locating-studio-btn">
              <ArrowRight className="w-4 h-4" /> Back to studio
            </button>
          </div>
        </div>
      </div>
    );
  }

  // FAILED (timeout or terminal)
  if (cardState === 'FAILED') {
    return (
      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6" data-testid="myspace-locating">
        <div className="rounded-2xl border border-rose-500/30 bg-gradient-to-br from-slate-900 via-slate-900 to-rose-950/30 p-6 space-y-4">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-rose-500/15 flex items-center justify-center shrink-0">
              <AlertTriangle className="w-6 h-6 text-rose-400" data-testid="locating-fail-icon" />
            </div>
            <div className="flex-1">
              <h3 className="text-base font-bold text-white" data-testid="locating-title">
                Video generation failed
              </h3>
              {/* P0 2026-05-31 — credits-safe copy is canonical. Backend
                  auto-refunds + skips charge on retries; the UI must
                  state this plainly so the user does not assume they
                  were double-billed. */}
              <p
                className="text-sm text-slate-300 mt-1"
                data-testid="locating-fail-msg"
              >
                {hardError || 'Generation failed.'} Your credits are safe.
              </p>
              {job?.retry_info?.total_retries ? (
                <p
                  className="text-xs text-slate-500 mt-1"
                  data-testid="locating-fail-retry-count"
                >
                  Auto-recovery attempted {job.retry_info.total_retries} time
                  {job.retry_info.total_retries === 1 ? '' : 's'}
                  {job.retry_info.last_error_stage
                    ? ` (last failure: ${job.retry_info.last_error_stage.toLowerCase()})`
                    : ''}
                  .
                </p>
              ) : null}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={handleRetry} className="px-4 py-2 rounded-lg bg-rose-500 hover:bg-rose-400 text-white text-sm flex items-center gap-2 transition-colors" data-testid="locating-retry-btn">
              <RefreshCw className="w-4 h-4" /> Retry generation
            </button>
            <button onClick={() => navigate('/app/story-video-studio')} className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-white text-sm flex items-center gap-2 transition-colors" data-testid="locating-studio-btn">
              <ArrowRight className="w-4 h-4" /> Back to studio
            </button>
          </div>
        </div>
      </div>
    );
  }

  // READY — handoff card (auto-navigates in 3s)
  if (cardState === 'READY') {
    return (
      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6" data-testid="myspace-locating">
        <div className="rounded-2xl border border-emerald-500/30 bg-gradient-to-br from-slate-900 via-slate-900 to-emerald-950/40 p-6 space-y-4">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/15 flex items-center justify-center shrink-0">
              <Check className="w-6 h-6 text-emerald-400" data-testid="locating-ready-icon" />
            </div>
            <div className="flex-1">
              <h3 className="text-base font-bold text-white" data-testid="locating-title">
                Your video is ready
              </h3>
              <p className="text-sm text-slate-300 mt-1">
                Saved to My Space.
                {typeof redirectCountdown === 'number' && redirectCountdown >= 0
                  ? ` Opening in ${Math.max(0, redirectCountdown)}s…`
                  : ''}
              </p>
              <div className="mt-3 h-1.5 w-full bg-white/[0.06] rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-emerald-500 to-cyan-400" style={{ width: '100%' }} />
              </div>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={() => navigate('/app/my-space', { replace: true })} className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm flex items-center gap-2 transition-colors" data-testid="locating-go-myspace-btn">
              <ArrowRight className="w-4 h-4" /> Go to My Space
            </button>
          </div>
        </div>
      </div>
    );
  }

  // RUNNING / LOCATING / STALE — primary generation surface
  const pct = Math.min(99, Math.max(2, displayPct));
  // P0 2026-05-31 — retry visibility contract. When backend reports
  // is_retrying=true (i.e. an automatic in-stage retry is in flight),
  // surface a distinct banner so the user knows the system is
  // actively recovering — never let an honest retry look identical
  // to a healthy first attempt. Pinned by
  // test_retry_visibility_contract_2026_05.py.
  const ri = job?.retry_info || null;
  const isRetrying = !!(ri && ri.is_retrying);
  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6" data-testid="myspace-locating">
      <div className="rounded-2xl border border-indigo-500/30 bg-gradient-to-br from-slate-900 via-slate-900 to-indigo-950/50 p-6 space-y-5">
        {isRetrying && (
          <div
            className="rounded-xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 flex items-start gap-3"
            data-testid="locating-retry-banner"
          >
            <RefreshCw className="w-4 h-4 text-amber-300 mt-0.5 shrink-0 animate-spin" />
            <div className="text-sm">
              <p className="text-amber-100 font-semibold" data-testid="locating-retry-banner-title">
                Render failed once. Retrying automatically…
              </p>
              <p
                className="text-amber-200/80 mt-0.5"
                data-testid="locating-retry-banner-detail"
              >
                Attempt {ri.current_attempt} of {ri.max_attempts || ri.current_attempt}
                {ri.last_error_stage ? ` (${ri.last_error_stage.toLowerCase()})` : ''}
                {' '}— your credits are safe.
              </p>
            </div>
          </div>
        )}
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-indigo-500/15 flex items-center justify-center shrink-0">
            <Loader2 className="w-6 h-6 text-indigo-300 animate-spin" data-testid="locating-spinner" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-base font-bold text-white truncate" data-testid="locating-title">
              {job?.title ? `Creating "${job.title}"` : 'Creating your video'}
            </h3>
            <p className="text-sm text-slate-300 mt-1" data-testid="locating-stage-label">
              {cardState === 'STALE'
                ? 'Still rendering. This is taking longer than usual — your credits are safe.'
                : (job?.stage_label || job?.current_stage || 'Preparing scenes')}
            </p>
          </div>
          <div className="text-right shrink-0">
            <div className="text-2xl font-bold text-white tabular-nums" data-testid="locating-progress-pct">{pct}%</div>
            <div className="text-[11px] uppercase tracking-wide text-slate-500" data-testid="locating-stage-index">
              Step {Math.max(1, stage.index + 1)} / {stage.total - 1}
            </div>
          </div>
        </div>

        {/* Real progress bar */}
        <div className="h-2 w-full bg-white/[0.06] rounded-full overflow-hidden" data-testid="locating-progress-bar">
          <div
            className="h-full bg-gradient-to-r from-indigo-500 via-violet-500 to-fuchsia-500 transition-all duration-700"
            style={{ width: `${pct}%` }}
          />
        </div>

        {/* Stage strip */}
        <div className="flex flex-wrap gap-1.5" data-testid="locating-stages">
          {__STAGE_PROGRESS.slice(0, -1).map((s, i) => {
            const active = i === stage.index;
            const done = pct >= s.floor && !active;
            return (
              <span
                key={s.key}
                className={`text-[11px] px-2 py-1 rounded-full border transition-colors ${
                  active
                    ? 'bg-indigo-500/20 border-indigo-400/40 text-indigo-200'
                    : done
                      ? 'bg-emerald-500/10 border-emerald-400/30 text-emerald-300/80'
                      : 'bg-white/[0.03] border-white/[0.06] text-slate-500'
                }`}
              >
                {done ? '✓ ' : active ? '● ' : ''}{s.label}
              </span>
            );
          })}
        </div>

        {/* Engagement panel — rotating copyright-free tips */}
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4" data-testid="locating-tip">
          <div className="flex items-start gap-3">
            <Sparkles className="w-4 h-4 text-violet-300 mt-0.5 shrink-0" />
            <div>
              <div className="text-[11px] uppercase tracking-wide text-violet-300/70 mb-1">
                {tip.kind === 'quote' ? 'A thought while we render' : tip.kind === 'try' ? 'Explore next' : 'Tip'}
              </div>
              <p className="text-sm text-slate-200 leading-snug" data-testid="locating-tip-text">{tip.text}</p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <button onClick={() => onRefresh && onRefresh()} className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-white text-sm flex items-center gap-2 transition-colors" data-testid="locating-refresh-btn">
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
          <button onClick={() => navigate('/app/story-video-studio')} className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-white text-sm flex items-center gap-2 transition-colors" data-testid="locating-studio-btn">
            <ArrowRight className="w-4 h-4" /> Back to studio
          </button>
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
  const [viralChain, setViralChain] = useState(null);
  const [viralMilestones, setViralMilestones] = useState(null);
  const [momentumMeter, setMomentumMeter] = useState([]);
  const [viralNudges, setViralNudges] = useState([]);
  const [newMilestone, setNewMilestone] = useState(null);
  const [searchParams] = useSearchParams();
  const highlightId = searchParams.get('projectId');
  // Trailer-specific deep-link from notification: /app/my-space?trailer=<job_id>
  const highlightTrailerId = searchParams.get('trailer');
  const highlightRef = useRef(null);
  const trailerHighlightRef = useRef(null);
  const pollRef = useRef(null);
  const prevStatusMap = useRef({});
  const promptedJobIds = useRef(new Set());
  // 2026-05-16 P0 dead-button fix — bumping this re-runs the scroll/ring
  // effect even when the URL params don't change (i.e. user clicks
  // "View Progress" on a card while already on /app/my-space).
  const [focusKey, setFocusKey] = useState(0);
  const [pulsingJobId, setPulsingJobId] = useState(null);

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
    api.get('/api/viral/chain-stats').then(r => { if (r.data?.has_chain) setViralChain(r.data.top_story); }).catch(() => {});
    api.get('/api/viral/milestones').then(r => {
      setViralMilestones(r.data);
      // Check for newly earned milestones to show celebration
      if (r.data?.earned?.length > 0) {
        const lastEarned = r.data.earned[r.data.earned.length - 1];
        const seenKey = `milestone_seen_${lastEarned.id}`;
        if (!sessionStorage.getItem(seenKey)) {
          setNewMilestone(lastEarned);
          sessionStorage.setItem(seenKey, 'true');
        }
      }
    }).catch(() => {});
    api.get('/api/viral/momentum-meter').then(r => setMomentumMeter(r.data?.stories || [])).catch(() => {});
    api.get('/api/viral/my-nudges').then(r => setViralNudges(r.data?.nudges || [])).catch(() => {});
  }, []);

  const fetchJobs = useCallback(async () => {
    try {
      const [storyRes, reelRes, trailerRes] = await Promise.allSettled([
        api.get('/api/story-engine/user-jobs?limit=100'),
        api.get('/api/convert/user-reels').catch(() => ({ data: { reels: [] } })),
        api.get('/api/photo-trailer/my-trailers?limit=50').catch(() => ({ data: { trailers: [] } })),
      ]);
      const allItems = [];
      if (storyRes.status === 'fulfilled' && storyRes.value?.data?.jobs) {
        for (const j of storyRes.value.data.jobs) {
          // P0 2026-05-16 — defensive normalization so any unexpected
          // backend status doesn't drift into PROCESSING.
          allItems.push({ ...j, status: normalizeJobStatus(j.status), type: 'story_video' });
        }
      }
      if (reelRes.status === 'fulfilled' && reelRes.value?.data?.reels) {
        for (const r of reelRes.value.data.reels) {
          // P0 2026-05-16 — strict allow-list status mapping.
          // ROOT-CAUSE FIX for MySpace "every old reel shows as 50% processing"
          // contamination: the previous mapper had a fallthrough that turned
          // ANY non-canonical backend value (cancelled / expired / archived /
          // orphaned / partial / null / '') into PROCESSING + progress=50.
          // Now: explicit canonicalize; anything unknown → ARCHIVED.
          const normalizedStatus = normalizeJobStatus(r.status);
          let normalizedProgress;
          if (normalizedStatus === 'COMPLETED' || normalizedStatus === 'PARTIAL') {
            normalizedProgress = 100;
          } else if (normalizedStatus === 'PROCESSING' || normalizedStatus === 'QUEUED') {
            // Use REAL backend progress when present; never synthesize 50%.
            normalizedProgress = typeof r.progress_percent === 'number' ? r.progress_percent : 0;
          } else {
            // FAILED / ARCHIVED — explicit zero (no fake progress bar)
            normalizedProgress = 0;
          }
          allItems.push({
            job_id: r.reel_id || r.id, title: r.title || 'Reel', type: 'reel',
            status: normalizedStatus,
            thumbnail_url: r.thumbnail_url, output_url: r.output_url || r.video_url,
            progress: normalizedProgress,
            created_at: r.created_at, completed_at: r.completed_at,
          });
        }
      }
      // Photo Trailers (YouStar) — appear here so users can leave the
      // generation screen and find their trailer when it's ready.
      if (trailerRes.status === 'fulfilled' && trailerRes.value?.data?.trailers) {
        for (const t of trailerRes.value.data.trailers) {
          allItems.push({
            // Backend now returns job_id (renamed from _id). Fall back gracefully.
            job_id: t.job_id || t._id || t.public_share_slug,
            title: t.template_name || 'YouStar Trailer',
            type: 'photo_trailer',
            // P0 2026-05-16 — defensive normalize. Backend already returns
            // canonical QUEUED|PROCESSING|COMPLETED|FAILED, but any drift
            // (legacy STALE / future REFUNDED) shouldn't contaminate UI.
            status: normalizeJobStatus(t.status),
            thumbnail_url: t.result_thumbnail_url,
            output_url: t.result_video_url,
            public_share_slug: t.public_share_slug,
            progress: t.status === 'COMPLETED' ? 100 : (t.progress_percent || 0),
            current_stage: t.current_stage,
            created_at: t.created_at,
            completed_at: t.completed_at,
            error_message: t.error_message,
            template_id: t.template_id,
            duration_target_seconds: t.duration_target_seconds,
            plan_tier_at_creation: t.plan_tier_at_creation,
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
    } catch (err) {
      console.error('Failed to fetch jobs:', err);
      if (jobs.length === 0) {
        toast.error('Failed to load your projects. Pull down to retry.');
      }
    } finally { setLoading(false); }
  }, [autoDownload]);

  useEffect(() => { fetchJobs(); requestNotificationPermission(); }, [fetchJobs]);

  // Track return-to-inspect when user arrives from Dashboard traction banner
  useEffect(() => {
    const referrer = document.referrer;
    const fromDashboard = referrer.includes('/app') && !referrer.includes('/my-space');
    if (fromDashboard) {
      trackFunnel('return_to_inspect', { source_page: 'my_space', meta: { trigger: 'page_visit', referrer_path: referrer } });
    }
  }, []);


  useEffect(() => {
    const hasInProgress = jobs.some(j => !['COMPLETED', 'FAILED', 'ARCHIVED', 'ORPHANED', 'PARTIAL'].includes(j.status));
    if (hasInProgress) { pollRef.current = setInterval(fetchJobs, 4000); }
    else if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [jobs, fetchJobs]);

  useEffect(() => {
    if (highlightId && highlightRef.current) {
      setTimeout(() => { highlightRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' }); }, 300);
      // Brief ring pulse so the user gets <100ms confirmation the click did something.
      setPulsingJobId(highlightId);
      const t = setTimeout(() => setPulsingJobId(null), 1800);
      return () => clearTimeout(t);
    }
  }, [highlightId, jobs, focusKey]);

  // Deep-link from notification: /app/my-space?trailer=<job_id>
  // Smooth-scroll to the matching YouStar trailer card and apply a brief
  // ring highlight so the user instantly sees their video.
  useEffect(() => {
    if (highlightTrailerId && trailerHighlightRef.current) {
      setTimeout(() => {
        trailerHighlightRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 300);
      setPulsingJobId(highlightTrailerId);
      const t = setTimeout(() => setPulsingJobId(null), 1800);
      return () => clearTimeout(t);
    }
  }, [highlightTrailerId, jobs, focusKey]);

  const handleRetry = async (job) => {
    try {
      const res = await api.post(`/api/story-engine/retry/${job.job_id}`);
      if (res.data?.success) {
        toast.success('Retrying generation...');
        // Navigate to studio so user can monitor the in-flight retry
        navigate(`/app/story-video-studio?projectId=${job.job_id}`);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Retry failed. Please try again.');
      // Recovery fallback — go to canonical status surface, not back to studio.
      // `replace: true` so the broken-retry studio frame doesn't sit in history.
      if (job?.job_id) {
        navigate(`/app/my-space?projectId=${job.job_id}`, { replace: true });
      }
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
    // 2026-05-16 P0 dead-button fix — "View Progress" / "View Details" /
    // default tile click MUST produce visible feedback within 100ms even
    // when the user is already on /app/my-space. The previous implementation
    // navigated to the SAME route with the SAME projectId param, which
    // made the button look completely dead.
    else if (job?.job_id) {
      try {
        trackFunnel('progress_cta_clicked', {
          source_page: 'my_space',
          meta: { job_id: job.job_id, type: job.type || 'story_engine' },
        });
      } catch (_) { /* never block UX on telemetry */ }

      try {
        if (highlightId === job.job_id) {
          // Already focused on this card → re-trigger scroll + ring pulse
          // via focusKey bump (URL doesn't change, so useEffect needs help).
          setFocusKey(k => k + 1);
        } else {
          navigate(`/app/my-space?projectId=${job.job_id}`);
        }
        try { trackFunnel('progress_view_opened', { source_page: 'my_space', meta: { job_id: job.job_id } }); } catch (_) {}
      } catch (err) {
        console.error('[ProgressCTA] handler failed', err);
        try { trackFunnel('progress_view_failed', { source_page: 'my_space', meta: { job_id: job.job_id, error: String(err?.message || err) } }); } catch (_) {}
        toast.error('Could not open progress. Refresh and try again.');
      }
    } else {
      console.error('[ProgressCTA] missing job_id', job);
      try { trackFunnel('progress_view_failed', { source_page: 'my_space', meta: { reason: 'missing_job_id' } }); } catch (_) {}
      toast.error('Could not open progress because the video job ID is missing.');
    }
  };

  // 2026-05-16 P0 — "Leave & come back later" used to fire a toast only
  // and stay on /app/my-space, which directly contradicts the label.
  // Now we actually leave (to Dashboard) and confirm with a toast.
  const handleLeaveAndComeBack = (job) => {
    try {
      trackFunnel('progress_cta_clicked', {
        source_page: 'my_space',
        meta: { job_id: job?.job_id, cta: 'leave_and_come_back' },
      });
    } catch (_) {}
    toast.success("We'll notify you when your video is ready. It keeps generating in the background.", { duration: 4500 });
    navigate('/app');
  };
  const handleShare = async (job) => {
    // P0 2026-05-16 — modal trust-flow audit. Validate job_id BEFORE any
    // share URL is constructed (the silent `/share/undefined` URL leak is
    // gone). Surface a structured error toast on missing id.
    if (!job?.job_id && !job?.public_share_slug && !job?.share_slug) {
      const rid = (window.lastRequestId || 'n/a');
      toast.error(`Unable to share: missing project id. Reference ID: ${rid}`);
      return;
    }
    // Photo trailers share via the public /trailer/:slug page (server re-signs).
    if (job.type === 'photo_trailer') {
      // public_share_slug is on the raw API row, not always projected onto job;
      // fall back to job_id which the API also accepts via redirect.
      const slug = job.public_share_slug || job.share_slug;
      if (slug) {
        const shareUrl = `${window.location.origin}/trailer/${slug}`;
        const text = encodeURIComponent(`🎬 Watch my AI movie trailer on Visionary Suite: ${shareUrl}`);
        window.open(`https://wa.me/?text=${text}`, '_blank', 'noopener,noreferrer');
        return;
      }
      // No slug yet — degrade gracefully to text-only share, NEVER raw bucket URL.
      const text = encodeURIComponent('🎬 Just made my own movie trailer with Visionary Suite!');
      window.open(`https://wa.me/?text=${text}`, '_blank', 'noopener,noreferrer');
      return;
    }
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
  // P0 2026-05-16 — modal trust-flow audit. Create Another must produce a
  // CLEAN editor (the contract is "NOT stale previous generation"). If we
  // don't clear the localStorage shadows left by Make-it-funnier / Change
  // style / Remix Gallery, the studio's mount-time hydration will re-load
  // the OLD story. Clear them deterministically here.
  const handleCreateAnother = () => {
    try {
      localStorage.removeItem('remix_video');
      localStorage.removeItem('remix_data');
    } catch (_) { /* sessionStorage may be disabled — never break UX */ }
    // Cache-buster `t=` so even same-route mounts re-init cleanly.
    navigate(`/app/story-video-studio?t=${Date.now()}`);
  };
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
  if (loading) return <SkeletonLoading highlightId={highlightId} />;

  // ═══ P0 2026-05-24 — Empty-state trust invariant ═══
  // When the URL carries ?projectId=<id> the user JUST clicked
  // Generate Video and was navigated here. Showing "No projects yet"
  // + "Create your first video" in that moment lies to the user —
  // they did exactly that action seconds ago. Causes covered:
  //   (a) /user-jobs query race with the just-written job document
  //   (b) user_id shape mismatch between create and read (Google
  //       OAuth vs JWT body — different shape on `current_user`)
  //   (c) auth cookie temporarily missing on the read call
  // The contract: when projectId is present and the list is empty,
  // render a "Locating your video..." card that polls
  // /api/story-engine/status/<id> directly (status uses get_optional_user
  // + ownership check by user_id). If status returns 200 → render
  // an in-progress card synthesized from the status payload. If it
  // 404s after a few attempts → render a clear recovery card with
  // a path back to the studio. The blank empty state is reserved
  // ONLY for users who arrived without a ?projectId param.
  if (jobs.length === 0 && highlightId) {
    return <LocatingProjectCard projectId={highlightId} onRefresh={fetchJobs} />;
  }

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

        {/* VIRAL CHAIN TIMELINE — Top story with momentum + share again */}
        {viralChain && (
          <div className="bg-gradient-to-br from-rose-500/[0.04] to-violet-500/[0.04] border border-white/[0.06] rounded-2xl p-4" data-testid="viral-chain-timeline">
            <div className="flex items-center gap-2 mb-3">
              <Flame className="w-4 h-4 text-rose-400" />
              <h3 className="text-sm font-bold text-white">Your Top Viral Story</h3>
              {/* Momentum Meter Badge */}
              {(() => {
                const m = momentumMeter.find(s => s.job_id === viralChain.job_id);
                if (!m || m.momentum_level === 'steady') return null;
                const mColors = { rising_fast: 'text-amber-400 bg-amber-500/10', trending: 'text-rose-400 bg-rose-500/10', spreading_widely: 'text-cyan-400 bg-cyan-500/10' };
                const mIcons = { rising_fast: Flame, trending: Zap, spreading_widely: Sparkles };
                const MIcon = mIcons[m.momentum_level] || Flame;
                return (
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full animate-pulse inline-flex items-center gap-1 ${mColors[m.momentum_level] || ''}`} data-testid="momentum-meter-badge">
                    <MIcon className="w-3 h-3" /> {m.momentum_label}
                  </span>
                );
              })()}
              {!momentumMeter.find(s => s.job_id === viralChain.job_id && s.momentum_level !== 'steady') && viralChain.remixes_today > 0 && (
                <span className="text-[10px] font-bold text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded-full animate-pulse" data-testid="chain-momentum-badge">
                  +{viralChain.remixes_today} new remix{viralChain.remixes_today !== 1 ? 'es' : ''} today
                </span>
              )}
              {viralChain.remixes_this_week > 0 && viralChain.remixes_today === 0 && (
                <span className="text-[10px] font-semibold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full">
                  {viralChain.remixes_this_week} this week
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-rose-500/20 to-violet-500/20 flex items-center justify-center flex-shrink-0">
                <Film className="w-5 h-5 text-rose-300" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-white truncate">{viralChain.title}</p>
                <p className="text-[11px] text-slate-500 mt-0.5">Your most viral creation</p>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                {viralChain.slug && (
                  <button
                    onClick={() => { navigate(`/v/${viralChain.slug}`); trackEvent('viral_chain_viewed', { job_id: viralChain.job_id }); }}
                    className="text-xs text-violet-400 hover:text-violet-300 font-medium"
                    data-testid="chain-view-btn"
                  >
                    View
                  </button>
                )}
                {viralChain.slug && viralChain.total_remixes > 0 && (
                  <button
                    onClick={() => {
                      const url = `${window.location.origin}/v/${viralChain.slug}`;
                      navigator.clipboard.writeText(url).then(() => toast.success('Link copied — share it to keep the momentum going!'));
                      trackEvent('reshare_from_chain', { job_id: viralChain.job_id, total_remixes: viralChain.total_remixes });
                    }}
                    className="px-2.5 py-1 text-[10px] font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-lg hover:bg-emerald-500/20 transition-colors"
                    data-testid="chain-share-again-btn"
                  >
                    <Share2 className="w-3 h-3 inline mr-1" /> Share Again
                  </button>
                )}
              </div>
            </div>
            {/* Chain stats */}
            <div className="grid grid-cols-3 gap-2">
              <div className="bg-white/[0.03] rounded-lg px-3 py-2 text-center">
                <p className="text-lg font-bold text-white">{viralChain.total_remixes}</p>
                <p className="text-[10px] text-slate-500">remix{viralChain.total_remixes !== 1 ? 'es' : ''} inspired</p>
              </div>
              <div className="bg-white/[0.03] rounded-lg px-3 py-2 text-center">
                <p className="text-lg font-bold text-white">{viralChain.unique_creators_inspired}</p>
                <p className="text-[10px] text-slate-500">new creator{viralChain.unique_creators_inspired !== 1 ? 's' : ''}</p>
              </div>
              <div className="bg-white/[0.03] rounded-lg px-3 py-2 text-center">
                <p className="text-lg font-bold text-white">{viralChain.chain_depth}</p>
                <p className="text-[10px] text-slate-500">creator level{viralChain.chain_depth !== 1 ? 's' : ''}</p>
              </div>
            </div>
            {/* Reshare nudge — contextual, momentum-driven */}
            {viralChain.remixes_this_week > 0 && (
              <div className="mt-3 p-2.5 rounded-lg bg-emerald-500/[0.04] border border-emerald-500/10 flex items-center gap-2" data-testid="chain-reshare-nudge">
                <Zap className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                <span className="text-[11px] text-emerald-300 flex-1">Your story got {viralChain.remixes_this_week} new remix{viralChain.remixes_this_week !== 1 ? 'es' : ''} since you shared — share again to keep momentum</span>
              </div>
            )}
          </div>
        )}

        {/* VIRAL PROGRESS NUDGE — 24h curiosity trigger */}
        {viralNudges.length > 0 && viralNudges[0]?.type === 'progress' && (
          <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-violet-500/[0.04] border border-violet-500/10 animate-[fadeIn_0.5s_ease-out]" data-testid="viral-progress-nudge">
            <Sparkles className="w-4 h-4 text-violet-400 flex-shrink-0" />
            <span className="text-sm text-violet-300 flex-1">{viralNudges[0].title}</span>
            <button
              onClick={() => { api.post('/api/viral/dismiss-nudge').catch(() => {}); setViralNudges([]); }}
              className="text-slate-500 hover:text-slate-300 text-xs flex-shrink-0"
              data-testid="nudge-dismiss-btn"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* MILESTONE CELEBRATION — Animated entrance for new badges */}
        {newMilestone && (
          <div className="bg-gradient-to-r from-amber-500/[0.08] to-rose-500/[0.08] border border-amber-500/20 rounded-2xl p-4 animate-[fadeIn_0.6s_ease-out]" data-testid="milestone-celebration">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-amber-500/20 flex items-center justify-center animate-[bounceIn_0.8s_ease-out]">
                {newMilestone.icon === 'sparkles' && <Sparkles className="w-5 h-5 text-amber-400" />}
                {newMilestone.icon === 'users' && <Users className="w-5 h-5 text-amber-400" />}
                {newMilestone.icon === 'layers' && <Layers className="w-5 h-5 text-amber-400" />}
                {newMilestone.icon === 'flame' && <Flame className="w-5 h-5 text-amber-400" />}
              </div>
              <div className="flex-1">
                <p className="text-sm font-bold text-amber-300">{newMilestone.label}</p>
                <p className="text-[11px] text-slate-400 mt-0.5">This is how creator momentum begins</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    const shareText = `I just earned the "${newMilestone.label}" badge on Visionary Suite! Creating with AI is incredible.`;
                    navigator.clipboard.writeText(shareText).then(() => toast.success('Milestone copied — share it with your audience!'));
                    trackEvent('milestone_badge_shared', { milestone_id: newMilestone.id });
                  }}
                  className="px-2.5 py-1 text-[10px] font-bold text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-lg hover:bg-amber-500/20 transition-colors"
                  data-testid="share-milestone-btn"
                >
                  <Share2 className="w-3 h-3 inline mr-1" /> Share Milestone
                </button>
                <button onClick={() => setNewMilestone(null)} className="text-slate-500 hover:text-slate-300" data-testid="dismiss-celebration-btn">
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* VIRAL MILESTONE BADGES */}
        {viralMilestones?.earned?.length > 0 && (
          <div className="flex items-center gap-2 flex-wrap" data-testid="viral-milestones">
            {viralMilestones.earned.map(m => (
              <div key={m.id} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/15 text-xs font-semibold text-amber-300 transition-all hover:bg-amber-500/15 hover:scale-[1.02] cursor-default" data-testid={`milestone-${m.id}`}>
                {m.icon === 'sparkles' && <Sparkles className="w-3 h-3" />}
                {m.icon === 'users' && <Users className="w-3 h-3" />}
                {m.icon === 'layers' && <Layers className="w-3 h-3" />}
                {m.icon === 'flame' && <Flame className="w-3 h-3" />}
                {m.label}
              </div>
            ))}
            {viralMilestones.upcoming?.length > 0 && (
              <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/[0.03] border border-white/[0.06] text-xs text-slate-500" data-testid="milestone-upcoming">
                Next: {viralMilestones.upcoming[0].label} ({viralMilestones.upcoming[0].remaining} more)
              </div>
            )}
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
                  <div
                    key={job.job_id}
                    ref={
                      job.job_id === highlightId ? highlightRef
                      : (job.type === 'photo_trailer' && job.job_id === highlightTrailerId) ? trailerHighlightRef
                      : null
                    }
                  >
                    <ProjectCard
                      job={job}
                      highlighted={
                        job.job_id === highlightId ||
                        (job.type === 'photo_trailer' && job.job_id === highlightTrailerId)
                      }
                      onShare={handleShare} onRetry={handleRetry} onDelete={handleDelete} onNavigate={handleNavigate} onLeave={handleLeaveAndComeBack} isPulsing={pulsingJobId === job.job_id} timeEstimates={timeEstimates} userCredits={userCredits} remixCount={remixStats[job.job_id] || 0}
                    />
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
                <div
                  key={job.job_id}
                  ref={
                    job.job_id === highlightId ? highlightRef
                    : (job.type === 'photo_trailer' && job.job_id === highlightTrailerId) ? trailerHighlightRef
                    : null
                  }
                >
                  <ProjectCard
                    job={job}
                    highlighted={
                      job.job_id === highlightId ||
                      (job.type === 'photo_trailer' && job.job_id === highlightTrailerId)
                    }
                    justCompleted={
                      justCompletedIds.has(job.job_id) ||
                      (job.type === 'photo_trailer' && job.job_id === highlightTrailerId)
                    }
                    onShare={handleShare} onRetry={handleRetry} onDelete={handleDelete} onNavigate={handleNavigate} onLeave={handleLeaveAndComeBack} isPulsing={pulsingJobId === job.job_id} timeEstimates={timeEstimates} userCredits={userCredits} remixCount={remixStats[job.job_id] || 0}
                  />
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
                  <div
                    key={job.job_id}
                    ref={
                      job.job_id === highlightId ? highlightRef
                      : (job.type === 'photo_trailer' && job.job_id === highlightTrailerId) ? trailerHighlightRef
                      : null
                    }
                  >
                    <ProjectCard
                      job={job}
                      highlighted={
                        job.job_id === highlightId ||
                        (job.type === 'photo_trailer' && job.job_id === highlightTrailerId)
                      }
                      onShare={handleShare} onRetry={handleRetry} onDelete={handleDelete} onNavigate={handleNavigate} onLeave={handleLeaveAndComeBack} isPulsing={pulsingJobId === job.job_id} timeEstimates={timeEstimates} userCredits={userCredits} remixCount={remixStats[job.job_id] || 0}
                    />
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
