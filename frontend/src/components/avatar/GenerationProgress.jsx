import React, { useEffect, useRef, useState } from 'react';
import { Loader2, CheckCircle2, Download, Share2, Repeat, AlertTriangle, Copy, MessageCircle } from 'lucide-react';
import { API, authHeaders, DemoBadge, DEMO_LABEL, VISIBLE_LABEL } from './shared';

const POLL_INTERVAL_MS = 1200;

/**
 * Step 5 — Generation Progress + Result.
 * Polls the mock backend job. When it completes, shows the demo output
 * with share buttons + "Make another" CTA. Labels every surface with
 * DEMO / SIMULATED OUTPUT so the user is never misled.
 */
export default function GenerationProgress({
  jobId,
  etaSeconds,
  onMakeAnother,
  onBackToLibrary,
}) {
  const [job, setJob] = useState(null);
  const [err, setErr] = useState(null);
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef(null);
  const pollRef = useRef(null);

  useEffect(() => {
    if (!jobId) return;
    const start = Date.now();
    timerRef.current = setInterval(() => setElapsed(Math.floor((Date.now() - start) / 1000)), 500);
    const poll = async () => {
      try {
        const r = await fetch(`${API}/api/avatar/jobs/${jobId}`, { headers: authHeaders() });
        if (!r.ok) return;
        const d = await r.json();
        setJob(d);
        if (d.status === 'completed' || d.status === 'failed') {
          clearInterval(pollRef.current);
          clearInterval(timerRef.current);
        }
      } catch {}
    };
    poll();
    pollRef.current = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      clearInterval(pollRef.current);
      clearInterval(timerRef.current);
    };
  }, [jobId]);

  if (err) {
    return (
      <div className="space-y-4" data-testid="avatar-studio-progress-step">
        <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-200 flex items-start gap-2"
             data-testid="avatar-studio-progress-error">
          <AlertTriangle className="w-4 h-4 mt-0.5" /> {err}
        </div>
        <button onClick={onMakeAnother} className="px-4 py-2 rounded-lg bg-white/5 text-white text-sm border border-white/10"
                data-testid="avatar-studio-progress-retry-btn">
          Try again
        </button>
      </div>
    );
  }

  const completed = job?.status === 'completed';
  const failed = job?.status === 'failed';

  if (completed) {
    return <ResultView job={job} onMakeAnother={onMakeAnother} onBackToLibrary={onBackToLibrary} />;
  }

  if (failed) {
    return (
      <div className="space-y-4" data-testid="avatar-studio-progress-step">
        <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-200 flex items-start gap-2"
             data-testid="avatar-studio-progress-failed">
          <AlertTriangle className="w-4 h-4 mt-0.5" />
          <div>
            <div className="font-bold">Generation hiccuped</div>
            <div className="text-xs mt-1">{job?.error_code || 'MOCK_STUDIO_FAIL'} — please retry.</div>
          </div>
        </div>
        <button onClick={onMakeAnother} className="px-4 py-2 rounded-lg bg-violet-600 text-white text-sm font-bold"
                data-testid="avatar-studio-progress-retry-btn">
          Try again
        </button>
      </div>
    );
  }

  const progress = job?.progress ?? 0;
  const stageLabel = job?.stage_label || 'Queued — spinning up mock pipeline';

  return (
    <div className="space-y-6" data-testid="avatar-studio-progress-step">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-[10px] uppercase tracking-[0.18em] text-violet-300 font-bold mb-2">Step 5 of 5</div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white">Generating your avatar…</h1>
          <p className="text-sm text-slate-400 mt-2">Hang tight — this usually takes {etaSeconds || 30}s. You can leave this page and come back later.</p>
        </div>
        <DemoBadge />
      </div>

      <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-violet-500/10 via-fuchsia-500/5 to-transparent p-6 space-y-5"
           data-testid="avatar-studio-progress-card">
        <div className="flex items-center gap-3">
          <Loader2 className="w-5 h-5 animate-spin text-violet-300" />
          <div className="flex-1 min-w-0">
            <div className="text-sm text-white font-semibold truncate" data-testid="avatar-studio-progress-stage-label">{stageLabel}</div>
            <div className="text-[11px] text-slate-400">Elapsed: {elapsed}s · Target: ~{etaSeconds || 30}s</div>
          </div>
          <div className="text-3xl font-bold text-white tabular-nums" data-testid="avatar-studio-progress-percent">{progress}%</div>
        </div>
        <div className="h-2 rounded-full bg-white/10 overflow-hidden">
          <div className="h-full bg-gradient-to-r from-violet-500 via-fuchsia-500 to-cyan-400 transition-all duration-500"
               style={{ width: `${progress}%` }} />
        </div>
        <StageList progress={progress} stageLabel={stageLabel} />
      </div>

      <div className="text-xs text-slate-500 text-center">
        Every output carries a visible <span className="text-amber-300">"{VISIBLE_LABEL}"</span> label and a forensic watermark.
      </div>
    </div>
  );
}

function StageList({ progress, stageLabel }) {
  const stages = [
    { label: 'Analyzing your input',       pct: 10 },
    { label: 'Preparing avatar model',     pct: 30 },
    { label: 'Synthesizing voice',         pct: 55 },
    { label: 'Rendering motion + scene',   pct: 80 },
    { label: 'Applying disclosure label',  pct: 95 },
  ];
  return (
    <ul className="space-y-2" data-testid="avatar-studio-progress-stage-list">
      {stages.map((s, i) => {
        const done = progress >= s.pct;
        const active = !done && (stageLabel || '').toLowerCase().includes(s.label.toLowerCase().split(' ')[0]);
        return (
          <li key={i} className="flex items-center gap-2 text-xs" data-testid={`avatar-studio-progress-stage-${i}`}>
            {done ? (
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            ) : active ? (
              <Loader2 className="w-3.5 h-3.5 text-violet-300 animate-spin" />
            ) : (
              <span className="w-3.5 h-3.5 rounded-full border border-white/15 inline-block" />
            )}
            <span className={done ? 'text-emerald-200' : active ? 'text-white' : 'text-slate-500'}>
              {s.label}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function ResultView({ job, onMakeAnother, onBackToLibrary }) {
  const videoUrl = job?.output_url;
  const [copied, setCopied] = useState(false);

  const shareText = `I didn't record this video — my AI avatar did.\nMade in under a minute.\nWant your own? → ${window.location.origin}/avatar-demo`;

  const shareWA = () => {
    window.open(`https://wa.me/?text=${encodeURIComponent(shareText)}`, '_blank');
    trackShare('whatsapp');
  };
  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(`${window.location.origin}/avatar-demo`);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
      trackShare('copy_link');
    } catch {}
  };
  const download = () => {
    if (!videoUrl) return;
    const a = document.createElement('a');
    a.href = videoUrl;
    a.download = `ai_avatar_demo_${job?.id || 'output'}.mp4`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    trackShare('download');
  };

  const trackShare = (channel) => {
    try {
      fetch(`${API}/api/avatar/funnel/track`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ step: 'avatar_share_click', meta: { channel, job_id: job?.id, is_demo_output: true } }),
      }).catch(() => {});
    } catch {}
  };

  return (
    <div className="space-y-6" data-testid="avatar-studio-result-view">
      <div>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-[10px] uppercase tracking-[0.18em] font-bold text-emerald-300">Ready</span>
          <DemoBadge />
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold text-white">Your avatar video is ready</h1>
        <p className="text-sm text-slate-400 mt-2">Preview below. This is a <span className="text-amber-300 font-semibold">{DEMO_LABEL.toLowerCase()}</span> — real AI rendering with your face and voice ships in Phase 2.</p>
      </div>

      <div className="rounded-2xl overflow-hidden bg-black border border-white/10 relative" data-testid="avatar-studio-result-video-wrap">
        <video
          src={videoUrl}
          controls
          autoPlay
          muted
          playsInline
          className="w-full aspect-video object-cover"
          data-testid="avatar-studio-result-video"
        />
        <div className="absolute top-3 left-3 flex flex-col gap-1.5">
          <span className="px-2 py-1 rounded-md bg-black/70 text-amber-200 text-[10px] uppercase tracking-wider font-bold border border-amber-500/40"
                data-testid="avatar-studio-result-label-visible">
            {VISIBLE_LABEL}
          </span>
          <span className="px-2 py-1 rounded-md bg-amber-500/20 text-amber-100 text-[10px] uppercase tracking-wider font-bold border border-amber-500/40"
                data-testid="avatar-studio-result-label-demo">
            {DEMO_LABEL}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2" data-testid="avatar-studio-result-share-row">
        <button
          onClick={shareWA}
          className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-emerald-500/15 border border-emerald-500/40 text-emerald-100 text-sm font-bold hover:bg-emerald-500/20"
          data-testid="avatar-studio-result-share-whatsapp-btn"
        >
          <MessageCircle className="w-4 h-4" /> Share to WhatsApp
        </button>
        <button
          onClick={download}
          className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-fuchsia-500/15 border border-fuchsia-500/40 text-fuchsia-100 text-sm font-bold hover:bg-fuchsia-500/20"
          data-testid="avatar-studio-result-download-btn"
        >
          <Download className="w-4 h-4" /> Download MP4
        </button>
        <button
          onClick={copyLink}
          className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-white/5 border border-white/15 text-white text-sm font-bold hover:bg-white/10"
          data-testid="avatar-studio-result-copy-link-btn"
        >
          <Copy className="w-4 h-4" /> {copied ? 'Copied ✓' : 'Copy invite link'}
        </button>
      </div>

      <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 text-[11px] text-slate-400 leading-relaxed"
           data-testid="avatar-studio-result-metadata">
        <div className="font-bold text-white text-xs mb-1.5 flex items-center gap-1.5"><Share2 className="w-3.5 h-3.5" /> Provenance</div>
        <div>Forensic watermark: <code className="text-slate-300">{job?.output_export_id?.slice(0, 16) || 'DEMO-WM'}</code></div>
        <div>Avatar type: <span className="text-slate-300">{job?.input?.avatar_type}</span></div>
        <div>Motion style: <span className="text-slate-300">{job?.input?.motion_style}</span></div>
        <div>Duration: <span className="text-slate-300">{job?.input?.duration_seconds}s</span></div>
      </div>

      <div className="flex flex-col sm:flex-row gap-2">
        <button
          onClick={onMakeAnother}
          className="flex-1 py-3.5 rounded-xl font-bold text-white bg-gradient-to-r from-violet-600 to-fuchsia-600 flex items-center justify-center gap-2"
          data-testid="avatar-studio-result-make-another-btn"
        >
          <Repeat className="w-4 h-4" /> Make another avatar
        </button>
        <button
          onClick={onBackToLibrary}
          className="px-5 py-3.5 rounded-xl border border-white/10 text-slate-200 text-sm font-semibold hover:bg-white/5"
          data-testid="avatar-studio-result-library-btn"
        >
          Back to library
        </button>
      </div>
    </div>
  );
}
