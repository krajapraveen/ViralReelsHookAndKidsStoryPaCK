import React, { useEffect, useRef, useState } from 'react';
import { Loader2, CheckCircle2, Download, Share2, Repeat, AlertTriangle, Copy, MessageCircle, Lock, Sparkles } from 'lucide-react';
import { API, authHeaders, DemoBadge, DEMO_LABEL, VISIBLE_LABEL } from './shared';

const POLL_INTERVAL_MS = 1200;

/**
 * Step 5 — Generation Progress + Result.
 * Two modes:
 *   • Authenticated: polls /api/avatar/jobs/{id} with Bearer token.
 *   • Anonymous (try-before-signup): polls /api/avatar/studio/anon-jobs/{id}?session_id=...
 *     and gates Save/Download/Copy/Make-another behind a sign-up CTA.
 */
export default function GenerationProgress({
  jobId,
  etaSeconds,
  onMakeAnother,
  onBackToLibrary,
  anonymous = false,
  anonSessionId = null,
  onSignupGate = null,   // called with a reason string when anon user hits a gated action
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
    let sawCompletion = false;
    const poll = async () => {
      try {
        const url = anonymous
          ? `${API}/api/avatar/studio/anon-jobs/${jobId}?session_id=${encodeURIComponent(anonSessionId || '')}`
          : `${API}/api/avatar/jobs/${jobId}`;
        const r = await fetch(url, { headers: anonymous ? {} : authHeaders() });
        if (!r.ok) return;
        const d = await r.json();
        setJob(d);
        try {
          // eslint-disable-next-line no-console
          console.log('[avatar-poll]', {
            job_id: d.id || jobId, status: d.status, progress: d.progress,
            stage: d.stage_label, duration: d?.input?.duration_seconds,
            elapsed: Math.floor((Date.now() - start) / 1000),
            eta: d.eta_seconds || etaSeconds,
          });
        } catch {}
        if (d.status === 'completed' || d.status === 'failed') {
          sawCompletion = true;
          clearInterval(pollRef.current);
          clearInterval(timerRef.current);
          return;
        }
        // Frontend hard timeout: if overdue by > eta + 10s and backend still
        // hasn't reconciled → force-fail with retry card.
        const elapsedSec = (Date.now() - start) / 1000;
        const target = d.eta_seconds || etaSeconds || 30;
        if (!sawCompletion && elapsedSec > target + 12) {
          try { console.warn('[avatar-poll] overdue, forcing local failure'); } catch {}
          clearInterval(pollRef.current);
          clearInterval(timerRef.current);
          setJob({ ...(d || {}), status: 'failed',
                   error_code: 'TIMEOUT_DEMO_GENERATION' });
        }
      } catch {}
    };
    poll();
    pollRef.current = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      clearInterval(pollRef.current);
      clearInterval(timerRef.current);
    };
  }, [jobId, anonymous, anonSessionId, etaSeconds]);

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
    return (
      <ResultView
        job={job}
        onMakeAnother={onMakeAnother}
        onBackToLibrary={onBackToLibrary}
        anonymous={anonymous}
        onSignupGate={onSignupGate}
      />
    );
  }

  if (failed) {
    const isTimeout = job?.error_code === 'TIMEOUT_DEMO_GENERATION';
    return (
      <div className="space-y-4" data-testid="avatar-studio-progress-step">
        <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-200 flex items-start gap-2"
             data-testid="avatar-studio-progress-failed">
          <AlertTriangle className="w-4 h-4 mt-0.5" />
          <div>
            <div className="font-bold">{isTimeout ? 'Demo generation took too long' : 'Generation hiccuped'}</div>
            <div className="text-xs mt-1">{isTimeout ? 'Please retry — this is a mocked Phase 1 demo and should finish in under a minute.' : (job?.error_code || 'MOCK_STUDIO_FAIL') + ' — please retry.'}</div>
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

function ResultView({ job, onMakeAnother, onBackToLibrary, anonymous = false, onSignupGate = null }) {
  const videoUrl = job?.output_url;
  const [copied, setCopied] = useState(false);
  const [videoError, setVideoError] = useState(false);
  const [videoKey, setVideoKey] = useState(0);    // forces reload on retry
  const videoRef = useRef(null);

  const retryVideo = () => {
    setVideoError(false);
    setVideoKey(k => k + 1);
    // defer play attempt to next tick after remount
    setTimeout(() => {
      try { videoRef.current?.play?.().catch(() => {}); } catch {}
    }, 100);
  };

  // Attempt playback once the element mounts. iOS Safari ignores autoplay
  // on some configs even with muted — we call .play() after mount and
  // silently catch rejections (user can still tap the big Play control).
  useEffect(() => {
    const t = setTimeout(() => {
      try { videoRef.current?.play?.().catch(() => {}); } catch {}
    }, 300);
    return () => clearTimeout(t);
  }, [videoKey, videoUrl]);

  const shareText = `I didn't record this video — my AI avatar did.\nMade in under a minute.\nWant your own? → ${window.location.origin}/avatar-demo`;

  const trackShare = (channel) => {
    try {
      fetch(`${API}/api/avatar/funnel/track`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          step: anonymous ? 'share_after_demo' : 'avatar_share_click',
          meta: { channel, job_id: job?.id, is_demo_output: true },
        }),
      }).catch(() => {});
    } catch {}
  };

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
  const requireSignup = (reason) => {
    if (onSignupGate) onSignupGate(reason);
  };
  const download = () => {
    if (anonymous) {
      requireSignup('download');
      return;
    }
    if (!videoUrl) return;
    const a = document.createElement('a');
    a.href = videoUrl;
    a.download = `ai_avatar_demo_${job?.id || 'output'}.mp4`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    trackShare('download');
  };
  const makeAnother = () => {
    if (anonymous) {
      // anonymous users get a retry tick *without* forcing signup; the gate
      // kicks in when they hit the free-demo limit at generation time.
      try {
        fetch(`${API}/api/avatar/funnel/track`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ step: 'retry_after_demo', meta: { prior_job_id: job?.id } }),
        }).catch(() => {});
      } catch {}
    }
    onMakeAnother?.();
  };

  return (
    <div className="space-y-6" data-testid="avatar-studio-result-view">
      <div>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-[10px] uppercase tracking-[0.18em] font-bold text-emerald-300">Ready</span>
          <DemoBadge />
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold text-white">Your avatar video is ready</h1>
        <p className="text-sm text-slate-400 mt-2">
          Preview below. This is a <span className="text-amber-300 font-semibold">{DEMO_LABEL.toLowerCase()}</span> — {anonymous ? 'sign up to save, download, or make it fully yours.' : 'real AI rendering with your face and voice ships in Phase 2.'}
        </p>
      </div>

      {/* Critical honesty banner — tells the user exactly what they're about
          to see so there's no "wait, that's not my face?" cognitive break. */}
      <div
        className="p-3 rounded-xl border-2 border-amber-500/40 bg-amber-500/10 text-amber-100 flex items-start gap-2.5"
        data-testid="avatar-studio-result-preview-notice"
      >
        <Sparkles className="w-4 h-4 mt-0.5 shrink-0 text-amber-300" />
        <div className="text-xs leading-relaxed">
          <span className="font-bold text-amber-200">This is a simulated preview.</span> In the full version, this will be <span className="font-bold text-amber-200">your face speaking in your voice</span>. We're collecting demand signal before wiring the real AI — that's why this is a stylized placeholder, not a stranger's video.
        </div>
      </div>

      <div className="rounded-2xl overflow-hidden bg-black border border-white/10 relative" data-testid="avatar-studio-result-video-wrap">
        {videoError ? (
          <div className="w-full aspect-video flex flex-col items-center justify-center bg-slate-900 text-center p-6" data-testid="avatar-studio-result-video-error">
            <AlertTriangle className="w-8 h-8 text-amber-300 mb-3" />
            <div className="text-sm font-bold text-white">Demo video failed to load</div>
            <div className="text-xs text-slate-400 mt-1 max-w-sm">Your network or browser blocked the demo sample. Tap below to retry.</div>
            <button
              onClick={retryVideo}
              className="mt-4 px-4 py-2 rounded-lg bg-violet-600 text-white text-sm font-bold"
              data-testid="avatar-studio-result-video-retry-btn"
            >
              Retry video
            </button>
          </div>
        ) : (
          <video
            key={videoKey}
            ref={videoRef}
            src={videoUrl}
            controls
            muted
            playsInline
            preload="auto"
            poster={undefined}
            className="w-full aspect-video object-contain bg-black"
            style={{ WebkitTapHighlightColor: 'transparent' }}
            onError={(e) => {
              try { console.error('video error', e?.nativeEvent || e); } catch {}
              setVideoError(true);
            }}
            onCanPlay={() => {
              try { videoRef.current?.play?.().catch(() => {}); } catch {}
            }}
            data-testid="avatar-studio-result-video"
          />
        )}
        <div className="absolute top-3 left-3 flex flex-col gap-1.5 pointer-events-none">
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

      {/* Anonymous gate CTA — lives above the (gated) action row */}
      {anonymous && (
        <div
          className="p-4 rounded-2xl border border-violet-500/40 bg-gradient-to-br from-violet-500/15 via-fuchsia-500/10 to-transparent"
          data-testid="avatar-studio-result-anon-signup-gate"
        >
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-violet-500/20 border border-violet-500/40 flex items-center justify-center shrink-0">
              <Sparkles className="w-5 h-5 text-violet-200" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-bold text-white">Sign up to download your video</div>
              <div className="text-xs text-slate-300 mt-0.5">Save this avatar for reuse · Export watermarked clip · Remix in your own voice.</div>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  onClick={() => requireSignup('signup_cta')}
                  className="px-4 py-2.5 rounded-xl font-bold text-white bg-gradient-to-r from-violet-600 to-fuchsia-600 text-sm flex items-center gap-1.5"
                  data-testid="avatar-studio-result-signup-btn"
                >
                  Sign up free <Lock className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={makeAnother}
                  className="px-4 py-2.5 rounded-xl border border-white/15 text-slate-200 text-sm font-semibold hover:bg-white/5"
                  data-testid="avatar-studio-result-anon-try-again-btn"
                >
                  Try a different style
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

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
          className={`flex items-center justify-center gap-2 px-4 py-3 rounded-xl border text-sm font-bold ${
            anonymous
              ? 'bg-white/5 border-white/15 text-slate-300 hover:bg-white/10'
              : 'bg-fuchsia-500/15 border-fuchsia-500/40 text-fuchsia-100 hover:bg-fuchsia-500/20'
          }`}
          data-testid="avatar-studio-result-download-btn"
        >
          {anonymous ? <Lock className="w-4 h-4" /> : <Download className="w-4 h-4" />}
          {anonymous ? 'Sign up to download' : 'Download MP4'}
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
          onClick={makeAnother}
          className="flex-1 py-3.5 rounded-xl font-bold text-white bg-gradient-to-r from-violet-600 to-fuchsia-600 flex items-center justify-center gap-2"
          data-testid="avatar-studio-result-make-another-btn"
        >
          <Repeat className="w-4 h-4" /> Make another avatar
        </button>
        {onBackToLibrary && (
          <button
            onClick={onBackToLibrary}
            className="px-5 py-3.5 rounded-xl border border-white/10 text-slate-200 text-sm font-semibold hover:bg-white/5"
            data-testid="avatar-studio-result-library-btn"
          >
            Back to library
          </button>
        )}
      </div>
    </div>
  );
}
