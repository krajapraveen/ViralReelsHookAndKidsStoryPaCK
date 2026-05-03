import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Video, Mic, Sparkles, Send, AlertTriangle, ArrowLeft, ChevronRight, CheckCircle2, Loader2, FileText, Lock } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const REQUIRED_PHRASE = 'I consent to creating an AI avatar of myself and my content. I understand all output will be labeled AI-generated.';
const VISIBLE_LABEL = 'AI-generated avatar';

// Same safe-only normalization as the backend.
const normalizeConsent = (s) => (s || '').replace(/\s+/g, ' ').trim().toLowerCase();
const phraseMatches = (typed) => normalizeConsent(typed) === normalizeConsent(REQUIRED_PHRASE);

const authHeaders = (extra = {}) => {
  const t = localStorage.getItem('token');
  return { Authorization: `Bearer ${t}`, ...extra };
};

// ─── Header ────────────────────────────────────────────────────────────────
function Header({ onBack }) {
  const nav = useNavigate();
  return (
    <header className="sticky top-0 z-30 backdrop-blur-md bg-slate-950/80 border-b border-white/5">
      <div className="max-w-5xl mx-auto px-4 py-3 flex items-center gap-3">
        <button
          onClick={() => onBack ? onBack() : nav('/app')}
          className="text-slate-300 hover:text-white flex items-center gap-1.5 text-sm"
          data-testid="avatar-header-back"
        >
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <div className="ml-auto flex items-center gap-2 text-xs text-slate-400">
          <Lock className="w-3.5 h-3.5 text-emerald-400" /> Consent-verified avatars only
        </div>
      </div>
    </header>
  );
}

// ─── Disclosure banner — appears on every export-bearing screen ───────────
function DisclosureBanner({ inline = false }) {
  return (
    <div
      className={`flex items-start gap-2.5 p-3 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-100 ${inline ? '' : 'mb-4'}`}
      data-testid="avatar-disclosure-banner"
    >
      <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0 text-amber-300" />
      <div className="text-xs leading-relaxed">
        <span className="font-bold text-amber-200">{VISIBLE_LABEL}.</span> Every clip from this studio carries a visible label, an invisible forensic watermark, and complies with YouTube synthetic-media disclosure + EU AI Act marking. We do not generate impersonation, political, fraud, medical, legal, sexual, or non-consensual content.
      </div>
    </div>
  );
}

// ─── Step 0: Dashboard / Pick or Create ────────────────────────────────────
function Dashboard({ clones, onCreate, onPick, onAdmin, onFunnel, isAdmin, onPricing }) {
  return (
    <div className="space-y-6" data-testid="avatar-step-dashboard">
      <div>
        <h1 className="text-3xl sm:text-4xl font-bold text-white">AI Personal Avatar Studio</h1>
        <p className="text-slate-400 text-sm mt-2 max-w-2xl">
          Create a verified clone of yourself for short-form content, coaching, sales and education. Every output is labeled AI-generated.
        </p>
      </div>
      <DisclosureBanner inline />
      <div className="flex flex-wrap gap-3">
        <button onClick={onCreate} data-testid="avatar-create-btn"
                className="px-5 py-3 rounded-xl font-bold text-white bg-gradient-to-r from-violet-600 to-fuchsia-600">
          + Create new avatar
        </button>
        <button onClick={onPricing} data-testid="avatar-pricing-btn"
                className="px-4 py-3 rounded-xl border border-white/10 text-slate-200 text-sm">
          See pricing
        </button>
        {isAdmin && (
          <>
            <button onClick={onAdmin} data-testid="avatar-admin-btn"
                    className="px-4 py-3 rounded-xl border border-amber-500/40 text-amber-200 text-sm">
              Admin moderation
            </button>
            <button onClick={onFunnel} data-testid="avatar-funnel-btn"
                    className="px-4 py-3 rounded-xl border border-cyan-500/40 text-cyan-200 text-sm">
              Funnel table
            </button>
          </>
        )}
      </div>
      <div>
        <h2 className="text-base font-semibold text-white mb-3">Your avatars</h2>
        {clones.length === 0 ? (
          <div className="p-6 rounded-2xl border border-white/10 bg-white/[0.02] text-slate-400 text-sm" data-testid="avatar-empty">
            No avatars yet. Click <strong className="text-white">+ Create new avatar</strong> to start with a 5-second consent video.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {clones.map(c => (
              <button key={c.id} onClick={() => onPick(c)}
                      data-testid={`avatar-clone-card-${c.id}`}
                      className="text-left p-4 rounded-2xl border border-white/10 bg-white/[0.03] hover:bg-white/[0.05] transition-colors">
                <div className="flex items-center justify-between mb-1.5">
                  <div className="font-semibold text-white truncate">{c.clone_name}</div>
                  <StatusPill status={c.status} />
                </div>
                <div className="text-xs text-slate-400">Type: {c.clone_type} · Created {new Date(c.created_at).toLocaleDateString()}</div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StatusPill({ status }) {
  const map = {
    consent_pending:  { c: 'bg-amber-500/15 text-amber-300 border-amber-500/30', l: 'Consent needed' },
    consent_review:   { c: 'bg-amber-500/15 text-amber-300 border-amber-500/30', l: 'Awaiting review' },
    consent_approved: { c: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30',     l: 'Consent approved' },
    consent_rejected: { c: 'bg-rose-500/15 text-rose-300 border-rose-500/30',     l: 'Consent rejected' },
    training:         { c: 'bg-violet-500/15 text-violet-300 border-violet-500/30', l: 'Training' },
    ready:            { c: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30', l: 'Ready' },
    disabled:         { c: 'bg-rose-500/15 text-rose-300 border-rose-500/30',     l: 'Disabled' },
  };
  const m = map[status] || { c: 'bg-white/10 text-slate-300 border-white/15', l: status };
  return (
    <span className={`text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full border ${m.c}`}>
      {m.l}
    </span>
  );
}

// ─── Step 1: Create clone (name + type) ────────────────────────────────────
function CreateStep({ onBack, onCreated }) {
  const [name, setName] = useState('');
  const [type, setType] = useState('self');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  const submit = async () => {
    setBusy(true); setErr(null);
    try {
      const res = await fetch(`${API}/api/avatar/clones`, {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ clone_name: name.trim(), clone_type: type }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || 'Could not create avatar');
      const data = await res.json();
      onCreated(data);
    } catch (e) {
      setErr(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-5" data-testid="avatar-step-create">
      <Header onBack={onBack} />
      <h2 className="text-2xl font-bold text-white">Name your avatar</h2>
      <DisclosureBanner inline />
      <label className="block">
        <span className="text-sm text-slate-300">Avatar name</span>
        <input value={name} onChange={e => setName(e.target.value)}
               className="mt-1 w-full px-3 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white"
               placeholder="e.g. My Coaching Avatar"
               data-testid="avatar-name-input" />
      </label>
      <fieldset className="space-y-2" data-testid="avatar-type-fieldset">
        <legend className="text-sm text-slate-300">Who are you cloning?</legend>
        {[
          { v: 'self', l: 'Myself (self-clone)', d: 'Required: 5-second consent video, you reading the consent phrase.' },
          { v: 'authorized_person', l: 'Someone else (with verified consent)', d: 'They must record the consent video themselves. Admin reviews every third-party clone.' },
        ].map(o => (
          <label key={o.v} className={`flex items-start gap-2.5 p-3 rounded-lg border cursor-pointer ${type === o.v ? 'border-violet-500 bg-violet-500/10' : 'border-white/10 bg-white/[0.02]'}`}
                 data-testid={`avatar-type-${o.v}`}>
            <input type="radio" name="ctype" checked={type === o.v}
                   onChange={() => setType(o.v)} className="mt-1" />
            <span>
              <span className="block text-sm font-semibold text-white">{o.l}</span>
              <span className="block text-xs text-slate-400">{o.d}</span>
            </span>
          </label>
        ))}
      </fieldset>
      {err && <div className="text-xs text-rose-300" data-testid="avatar-create-error">{err}</div>}
      <button onClick={submit} disabled={busy || name.trim().length < 2}
              className="w-full py-3.5 rounded-xl font-bold text-white bg-gradient-to-r from-violet-600 to-fuchsia-600 disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="avatar-create-submit">
        {busy ? 'Creating…' : 'Continue → Record consent'}
      </button>
    </div>
  );
}

// ─── Step 2: Consent capture ──────────────────────────────────────────────
function ConsentStep({ clone, onBack, onSubmitted }) {
  const [phrase, setPhrase] = useState('');
  const [recording, setRecording] = useState(false);
  const [recorded, setRecorded] = useState(null); // { blob, url, duration }
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const [copied, setCopied] = useState(false);
  const videoRef = useRef(null);
  const mediaRef = useRef(null);
  const chunksRef = useRef([]);
  const startTsRef = useRef(0);

  const start = async () => {
    setErr(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      videoRef.current.srcObject = stream;
      videoRef.current.muted = true;
      await videoRef.current.play();
      const mr = new MediaRecorder(stream, { mimeType: 'video/webm' });
      mediaRef.current = mr;
      chunksRef.current = [];
      mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      mr.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'video/webm' });
        const dur = (Date.now() - startTsRef.current) / 1000;
        const url = URL.createObjectURL(blob);
        setRecorded({ blob, url, duration: dur });
        stream.getTracks().forEach(t => t.stop());
      };
      startTsRef.current = Date.now();
      mr.start();
      setRecording(true);
    } catch (e) {
      setErr('Camera/mic permission denied. Please allow access and retry.');
    }
  };
  const stop = () => {
    mediaRef.current?.stop();
    setRecording(false);
  };
  useEffect(() => () => mediaRef.current?.state === 'recording' && mediaRef.current.stop(), []);

  const submit = async () => {
    if (!recorded) { setErr('Please record a 5-second consent video first.'); return; }
    if (recorded.duration < 5) { setErr('Consent video must be at least 5 seconds.'); return; }
    if (!phraseMatches(phrase)) { setErr('Typed phrase must exactly match the required consent phrase.'); return; }
    setBusy(true); setErr(null);
    try {
      const fd = new FormData();
      fd.append('consent_phrase', phrase);
      fd.append('duration_seconds', String(recorded.duration));
      fd.append('user_agent', navigator.userAgent || '');
      fd.append('selfie_video', recorded.blob, 'consent.webm');
      const res = await fetch(`${API}/api/avatar/clones/${clone.id}/consent`, {
        method: 'POST', headers: authHeaders(), body: fd,
      });
      if (!res.ok) {
        const d = await res.json();
        throw new Error(d.detail?.reason || d.detail || 'Consent rejected');
      }
      const data = await res.json();
      onSubmitted(data);
    } catch (e) {
      setErr(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  const copyRequiredPhrase = async () => {
    try { await navigator.clipboard.writeText(REQUIRED_PHRASE); setCopied(true); setTimeout(() => setCopied(false), 1800); } catch {}
  };

  const phraseOK = phrase.length > 0 && phraseMatches(phrase);
  const phraseDirty = phrase.length > 0;
  const durationOK = !!(recorded && recorded.duration >= 5);
  const canSubmit = !busy && durationOK && phraseOK;

  return (
    <div className="space-y-5" data-testid="avatar-step-consent">
      <Header onBack={onBack} />
      <h2 className="text-2xl font-bold text-white">Record your consent</h2>
      <p className="text-sm text-slate-400">
        Read the exact phrase below into your camera for 5+ seconds. This video is stored securely and reviewed before your clone is trained. You can revoke consent any time.
      </p>
      <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-100 relative" data-testid="avatar-consent-phrase">
        <div className="flex items-start justify-between gap-3 mb-1">
          <div className="text-[10px] uppercase tracking-wider font-bold text-amber-300">Required phrase</div>
          <button type="button" onClick={copyRequiredPhrase}
                  className="text-[10px] px-2 py-1 rounded-md bg-amber-500/20 text-amber-200 border border-amber-500/40 font-bold uppercase tracking-wider"
                  data-testid="avatar-consent-copy-required">
            {copied ? 'Copied ✓' : 'Copy required phrase'}
          </button>
        </div>
        <div className="text-sm leading-relaxed select-text" data-testid="avatar-consent-phrase-text">{REQUIRED_PHRASE}</div>
      </div>
      <div className="rounded-2xl overflow-hidden bg-black aspect-video border border-white/10">
        {recorded ? (
          <video src={recorded.url} controls className="w-full h-full" data-testid="avatar-consent-playback" />
        ) : (
          <video ref={videoRef} className="w-full h-full" muted playsInline />
        )}
      </div>
      <div className="flex gap-2">
        {!recording && !recorded && (
          <button onClick={start} className="flex-1 py-3 rounded-xl font-bold text-white bg-rose-500"
                  data-testid="avatar-consent-record">
            ● Start recording
          </button>
        )}
        {recording && (
          <button onClick={stop} className="flex-1 py-3 rounded-xl font-bold text-white bg-rose-700 animate-pulse"
                  data-testid="avatar-consent-stop">
            ■ Stop recording
          </button>
        )}
        {recorded && (
          <button onClick={() => { setRecorded(null); }}
                  className="px-4 py-3 rounded-xl border border-white/10 text-slate-200 text-sm"
                  data-testid="avatar-consent-retake">
            Retake
          </button>
        )}
      </div>
      <label className="block">
        <span className="text-sm text-slate-300">Type the phrase you just spoke (we cross-check):</span>
        <textarea value={phrase} onChange={e => setPhrase(e.target.value)}
                  rows={3} className={`mt-1 w-full px-3 py-2.5 rounded-lg bg-white/5 border text-white text-sm ${
                    !phraseDirty ? 'border-white/10' : (phraseOK ? 'border-emerald-500/50' : 'border-rose-500/50')
                  }`}
                  data-testid="avatar-consent-phrase-input"
                  placeholder="Paste or type the required phrase here…" />
        {phraseDirty && !phraseOK && (
          <div className="mt-1.5 text-xs text-rose-300" data-testid="avatar-consent-phrase-mismatch">
            Typed phrase must exactly match the required consent phrase.
          </div>
        )}
        {phraseDirty && phraseOK && (
          <div className="mt-1.5 text-xs text-emerald-300" data-testid="avatar-consent-phrase-match">
            Phrase matches ✓
          </div>
        )}
      </label>
      {recorded && !durationOK && (
        <div className="text-xs text-rose-300" data-testid="avatar-consent-duration-warning">
          Consent video must be at least 5 seconds. Please re-record.
        </div>
      )}
      {err && <div className="text-xs text-rose-300" data-testid="avatar-consent-error">{err}</div>}
      <button onClick={submit} disabled={!canSubmit}
              className="w-full py-3.5 rounded-xl font-bold text-white bg-gradient-to-r from-violet-600 to-fuchsia-600 disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="avatar-consent-submit">
        {busy ? 'Submitting…' : 'Submit consent for review'}
      </button>
    </div>
  );
}

// ─── Step 3: Train (mock job poller) ──────────────────────────────────────
function TrainStep({ clone, onBack, onReady }) {
  const [job, setJob] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const [voice, setVoice] = useState(false);

  const startTrain = async () => {
    setBusy(true); setErr(null);
    try {
      // ensure voice profile (mock) exists
      await fetch(`${API}/api/avatar/clones/${clone.id}/voice-profile`, {
        method: 'POST', headers: authHeaders(),
      });
      setVoice(true);
      const r = await fetch(`${API}/api/avatar/clones/${clone.id}/train`, {
        method: 'POST', headers: authHeaders({ 'Content-Type': 'application/json' }), body: '{}',
      });
      if (!r.ok) throw new Error((await r.json()).detail || 'Could not start training');
      const d = await r.json();
      if (d.job_id) setJob({ id: d.job_id, status: 'queued', progress: 0 });
      else onReady(); // already_ready
    } catch (e) {
      setErr(String(e.message || e));
    } finally { setBusy(false); }
  };

  useEffect(() => {
    if (!job?.id || job.status === 'completed' || job.status === 'failed') return;
    const t = setInterval(async () => {
      try {
        const r = await fetch(`${API}/api/avatar/jobs/${job.id}`, { headers: authHeaders() });
        if (!r.ok) return;
        const d = await r.json();
        setJob(j => ({ ...j, ...d }));
        if (d.status === 'completed') { clearInterval(t); setTimeout(onReady, 800); }
        if (d.status === 'failed') { clearInterval(t); setErr(d.error_code || 'Training failed'); }
      } catch {}
    }, 1500);
    return () => clearInterval(t);
  }, [job?.id, job?.status, onReady]);

  return (
    <div className="space-y-5" data-testid="avatar-step-train">
      <Header onBack={onBack} />
      <h2 className="text-2xl font-bold text-white">Train your avatar</h2>
      <DisclosureBanner inline />
      {!job && (
        <div className="space-y-3">
          <p className="text-sm text-slate-400">
            Consent approved. We'll create a mock voice profile and train your face model. (Real training lands next session — this run is a fast simulation.)
          </p>
          {err && <div className="text-xs text-rose-300" data-testid="avatar-train-error">{err}</div>}
          <button onClick={startTrain} disabled={busy}
                  className="w-full py-3.5 rounded-xl font-bold text-white bg-gradient-to-r from-violet-600 to-fuchsia-600 disabled:opacity-50"
                  data-testid="avatar-train-start">
            {busy ? 'Starting…' : 'Start training'}
          </button>
        </div>
      )}
      {job && (
        <div className="space-y-3" data-testid="avatar-train-progress">
          <div className="flex items-center gap-2 text-sm text-slate-300">
            <Loader2 className="w-4 h-4 animate-spin text-violet-400" /> Training… {job.progress}%
            <span className="ml-auto text-xs text-slate-500">{job.status}</span>
          </div>
          <div className="h-2 rounded-full bg-white/10 overflow-hidden">
            <div className="h-full bg-gradient-to-r from-violet-500 to-fuchsia-500 transition-all"
                 style={{ width: `${job.progress}%` }} />
          </div>
          <ul className="text-xs text-slate-400 space-y-1 pt-2">
            <li className="flex items-center gap-2">{voice ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <span className="w-3.5 h-3.5 inline-block" />} Voice profile (mock)</li>
            <li className="flex items-center gap-2">{job.progress >= 50 ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <span className="w-3.5 h-3.5 inline-block" />} Face model</li>
            <li className="flex items-center gap-2">{job.progress >= 100 ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <span className="w-3.5 h-3.5 inline-block" />} Watermark fingerprint registration</li>
          </ul>
        </div>
      )}
    </div>
  );
}

// ─── Step 4: Generate video ───────────────────────────────────────────────
function GenerateStep({ clone, onBack, onResult }) {
  const [script, setScript] = useState('');
  const [platform, setPlatform] = useState('youtube');
  const [job, setJob] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  const submit = async () => {
    setBusy(true); setErr(null);
    try {
      const r = await fetch(`${API}/api/avatar/generate-video`, {
        method: 'POST', headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ clone_id: clone.id, script, platform }),
      });
      if (!r.ok) {
        const d = await r.json();
        throw new Error(d.detail?.reason || d.detail || 'Generation failed');
      }
      const d = await r.json();
      setJob({ id: d.job_id, status: 'queued', progress: 0 });
    } catch (e) {
      setErr(String(e.message || e));
    } finally { setBusy(false); }
  };

  useEffect(() => {
    if (!job?.id || job.status === 'completed' || job.status === 'failed') return;
    const t = setInterval(async () => {
      try {
        const r = await fetch(`${API}/api/avatar/jobs/${job.id}`, { headers: authHeaders() });
        if (!r.ok) return;
        const d = await r.json();
        setJob(j => ({ ...j, ...d }));
        if (d.status === 'completed') { clearInterval(t); onResult(d); }
        if (d.status === 'failed') { clearInterval(t); setErr(d.error_code || 'Render failed'); }
      } catch {}
    }, 1500);
    return () => clearInterval(t);
  }, [job?.id, job?.status, onResult]);

  return (
    <div className="space-y-5" data-testid="avatar-step-generate">
      <Header onBack={onBack} />
      <h2 className="text-2xl font-bold text-white">Type a script — get a video</h2>
      <DisclosureBanner inline />
      <label className="block">
        <span className="text-sm text-slate-300">Script (max 1200 chars)</span>
        <textarea value={script} onChange={e => setScript(e.target.value)}
                  rows={6} maxLength={1200}
                  className="mt-1 w-full px-3 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white text-sm"
                  data-testid="avatar-script-input"
                  placeholder="Hello, welcome to my channel. Today I'll share three productivity tips…" />
        <div className="text-xs text-slate-500 mt-1">{script.length} / 1200</div>
      </label>
      <label className="block">
        <span className="text-sm text-slate-300">Target platform</span>
        <select value={platform} onChange={e => setPlatform(e.target.value)}
                className="mt-1 w-full px-3 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white text-sm"
                data-testid="avatar-platform-select">
          <option value="youtube">YouTube (auto-fills synthetic-media disclosure)</option>
          <option value="instagram">Instagram</option>
          <option value="whatsapp">WhatsApp</option>
          <option value="linkedin">LinkedIn</option>
          <option value="generic">Generic / download</option>
        </select>
      </label>
      <p className="text-xs text-slate-500">
        We refuse impersonation, political persuasion, fraud (OTP/banking/KYC), medical/legal advice, sexual material, and "this is real" deception flows.
      </p>
      {err && <div className="text-xs text-rose-300 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30" data-testid="avatar-generate-error">{err}</div>}
      {!job && (
        <button onClick={submit} disabled={busy || script.trim().length < 8}
                className="w-full py-3.5 rounded-xl font-bold text-white bg-gradient-to-r from-violet-600 to-fuchsia-600 disabled:opacity-50"
                data-testid="avatar-generate-submit">
          <Send className="w-4 h-4 inline mr-1.5" />
          {busy ? 'Submitting…' : 'Generate avatar video'}
        </button>
      )}
      {job && job.status !== 'completed' && (
        <div className="space-y-2" data-testid="avatar-generate-progress">
          <div className="flex items-center gap-2 text-sm text-slate-300">
            <Loader2 className="w-4 h-4 animate-spin text-violet-400" /> Rendering… {job.progress}%
          </div>
          <div className="h-2 rounded-full bg-white/10 overflow-hidden">
            <div className="h-full bg-gradient-to-r from-violet-500 to-fuchsia-500 transition-all"
                 style={{ width: `${job.progress}%` }} />
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Step 5: Result + exports list ────────────────────────────────────────
function ResultStep({ clone, lastJob, onBack, onMakeAnother }) {
  const [exports, setExports] = useState([]);
  useEffect(() => {
    fetch(`${API}/api/avatar/clones/${clone.id}/exports`, { headers: authHeaders() })
      .then(r => r.json()).then(d => setExports(d.exports || []));
  }, [clone.id, lastJob?.id]);

  // Share helpers
  const userId = (() => { try { return JSON.parse(localStorage.getItem('user') || 'null')?.id || ''; } catch { return ''; } })();
  const inviteUrl = `${window.location.origin}/avatar-demo?utm_source=user_share&utm_campaign=avatar_referral${userId ? `&ref=${encodeURIComponent(userId)}` : ''}`;
  const trackShare = (channel, exportId) => {
    fetch(`${API}/api/avatar/funnel/track`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ step: 'avatar_share_click', meta: { channel, export_id: exportId } }),
    }).catch(() => {});
  };
  const shareWA = (e) => {
    trackShare('whatsapp', e.id);
    const text =
      `I didn't record this video.\n` +
      `This is an AI version of me.\n` +
      `I used it to make 5 reels in under 10 minutes.\n` +
      `Want your own AI avatar? → ${inviteUrl}`;
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank');
  };
  const shareIG = async (e) => {
    trackShare('instagram', e.id);
    const caption =
      `I didn't record this video.\n` +
      `This is an AI version of me.\n` +
      `Made it in under a minute. Link in profile.`;
    try { await navigator.clipboard.writeText(caption); } catch {}
    const a = document.createElement('a');
    a.href = e.file_url; a.download = `ai_avatar_${e.id}.mp4`;
    document.body.appendChild(a); a.click(); a.remove();
  };
  const copyInvite = async () => {
    trackShare('copy_link', null);
    try { await navigator.clipboard.writeText(inviteUrl); } catch {}
  };

  return (
    <div className="space-y-5" data-testid="avatar-step-result">
      <Header onBack={onBack} />
      <h2 className="text-2xl font-bold text-white">Your avatar video is ready</h2>
      <DisclosureBanner inline />
      {exports.length === 0 ? (
        <div className="text-sm text-slate-400">No exports yet.</div>
      ) : (
        <ul className="space-y-3">
          {exports.map(e => (
            <li key={e.id} className="p-4 rounded-2xl border border-white/10 bg-white/[0.03]"
                data-testid={`avatar-export-${e.id}`}>
              <div className="aspect-video rounded-lg overflow-hidden bg-black mb-3 relative">
                <video src={e.file_url} controls className="w-full h-full" data-testid={`avatar-export-video-${e.id}`} />
                <div className="absolute top-2 left-2 px-2 py-1 rounded-md bg-black/70 text-amber-200 text-[10px] uppercase tracking-wider font-bold border border-amber-500/40"
                     data-testid={`avatar-export-label-${e.id}`}>
                  {e.visible_label_text}
                </div>
              </div>
              <div className="text-xs text-slate-400 space-y-0.5">
                <div><span className="text-slate-500">Forensic ID:</span> <code className="text-slate-300">{e.forensic_watermark_id}</code></div>
                <div><span className="text-slate-500">Platform:</span> {e.platform}</div>
                <div><span className="text-slate-500">Disclosure:</span> {e.disclosure_text}</div>
              </div>
              {/* Share row */}
              <div className="mt-3 flex flex-wrap gap-2" data-testid={`avatar-share-row-${e.id}`}>
                <button onClick={() => shareWA(e)}
                        className="px-3 py-2 rounded-lg bg-emerald-500/20 text-emerald-200 text-xs font-bold border border-emerald-500/40"
                        data-testid={`avatar-share-whatsapp-${e.id}`}>
                  Share to WhatsApp
                </button>
                <button onClick={() => shareIG(e)}
                        className="px-3 py-2 rounded-lg bg-fuchsia-500/20 text-fuchsia-200 text-xs font-bold border border-fuchsia-500/40"
                        data-testid={`avatar-share-instagram-${e.id}`}>
                  Download for Instagram
                </button>
                <button onClick={copyInvite}
                        className="px-3 py-2 rounded-lg bg-white/5 text-slate-200 text-xs font-bold border border-white/15"
                        data-testid={`avatar-share-copy-${e.id}`}>
                  Copy invite link
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
      <div className="flex gap-2">
        <button onClick={onMakeAnother}
                className="flex-1 py-3 rounded-xl font-bold text-white bg-gradient-to-r from-violet-600 to-fuchsia-600"
                data-testid="avatar-make-another">
          Make another
        </button>
        <button onClick={onBack}
                className="px-4 py-3 rounded-xl border border-white/10 text-slate-200 text-sm"
                data-testid="avatar-back-dashboard">
          Back to studio
        </button>
      </div>
    </div>
  );
}

// ─── Pricing display ──────────────────────────────────────────────────────
function PricingPanel({ onBack }) {
  const [data, setData] = useState({ plans: [], topups: [] });
  useEffect(() => {
    fetch(`${API}/api/avatar/billing/plans`).then(r => r.json()).then(setData);
  }, []);
  return (
    <div className="space-y-5" data-testid="avatar-pricing-panel">
      <Header onBack={onBack} />
      <h2 className="text-2xl font-bold text-white">Pricing</h2>
      <p className="text-xs text-slate-500">Billing rolls out in Phase 2. Until then, your account is granted access by an admin.</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {data.plans.map(p => (
          <div key={p.id} className="p-4 rounded-2xl border border-white/10 bg-white/[0.03]"
               data-testid={`avatar-plan-${p.id}`}>
            <div className="text-xs uppercase tracking-wider text-slate-400">{p.name}</div>
            <div className="text-2xl font-bold text-white mt-1">₹{p.price_inr}</div>
            <div className="text-xs text-slate-500">{p.credits} credits/mo</div>
            <ul className="mt-3 space-y-1 text-xs text-slate-300">
              {p.features.map((f, i) => (<li key={i} className="flex items-start gap-1.5"><CheckCircle2 className="w-3 h-3 mt-0.5 text-emerald-400 shrink-0" />{f}</li>))}
            </ul>
          </div>
        ))}
      </div>
      <h3 className="text-base font-semibold text-white mt-4">Top-ups</h3>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {data.topups.map(t => (
          <div key={t.id} className="p-3 rounded-xl border border-white/10 bg-white/[0.03] text-center"
               data-testid={`avatar-topup-${t.id}`}>
            <div className="text-lg font-bold text-white">₹{t.price_inr}</div>
            <div className="text-xs text-slate-400">{t.credits} credits</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Main page state machine ──────────────────────────────────────────────
export default function AvatarStudioPage() {
  const nav = useNavigate();
  const [step, setStep] = useState('dashboard'); // dashboard|create|consent|train|generate|result|pricing
  const [clones, setClones] = useState([]);
  const [active, setActive] = useState(null);
  const [lastJob, setLastJob] = useState(null);
  const [user, setUser] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/avatar/clones`, { headers: authHeaders() });
      if (!r.ok) {
        if (r.status === 401) { nav('/login'); return; }
        return;
      }
      const d = await r.json();
      setClones(d.clones || []);
    } catch {}
    try {
      const u = JSON.parse(localStorage.getItem('user') || 'null');
      setUser(u);
    } catch {}
  }, [nav]);

  useEffect(() => { refresh(); }, [refresh]);

  // Lazy referral attribution: first time the authenticated user lands on
  // the studio, attach any stored attribution to their account. Idempotent
  // both client-side (key flip) and server-side (no-op if already set).
  useEffect(() => {
    if (localStorage.getItem('avatar_attribution_attached') === '1') return;
    let attribution = null;
    try { attribution = JSON.parse(localStorage.getItem('avatar_attribution') || 'null'); } catch {}
    if (!attribution) return;
    const token = localStorage.getItem('token');
    if (!token) return;
    fetch(`${API}/api/avatar/referral/attribute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(attribution),
    })
      .then(r => r.ok && localStorage.setItem('avatar_attribution_attached', '1'))
      .catch(() => {});
  }, []);

  // Auto-advance: when a user clicks a clone card, route to the right step.
  const pick = (c) => {
    setActive(c);
    if (c.status === 'consent_pending' || c.status === 'consent_rejected') setStep('consent');
    else if (c.status === 'consent_review') setStep('consent');
    else if (c.status === 'consent_approved' || c.status === 'training') setStep('train');
    else if (c.status === 'ready') setStep('generate');
    else if (c.status === 'disabled') setStep('dashboard');
    else setStep('dashboard');
  };

  const isAdmin = (user?.role || '').toUpperCase() === 'ADMIN';

  return (
    <div className="min-h-[100dvh] bg-slate-950 text-white" data-testid="avatar-studio-page">
      <main className="max-w-4xl mx-auto px-4 py-6 sm:py-10">
        {step === 'dashboard' && (
          <Dashboard clones={clones}
            onCreate={() => setStep('create')}
            onPick={pick}
            onAdmin={() => nav('/app/admin/avatar/moderation')}
            onFunnel={() => nav('/app/admin/avatar/funnel')}
            isAdmin={isAdmin}
            onPricing={() => setStep('pricing')} />
        )}
        {step === 'create' && (
          <CreateStep onBack={() => setStep('dashboard')}
            onCreated={(c) => { setActive(c); refresh(); setStep('consent'); }} />
        )}
        {step === 'consent' && active && (
          <ConsentStep clone={active}
            onBack={() => { refresh(); setStep('dashboard'); }}
            onSubmitted={() => { refresh(); setStep('train'); }} />
        )}
        {step === 'train' && active && (
          <TrainStep clone={active}
            onBack={() => { refresh(); setStep('dashboard'); }}
            onReady={() => { refresh(); setStep('generate'); }} />
        )}
        {step === 'generate' && active && (
          <GenerateStep clone={active}
            onBack={() => { refresh(); setStep('dashboard'); }}
            onResult={(j) => { setLastJob(j); refresh(); setStep('result'); }} />
        )}
        {step === 'result' && active && (
          <ResultStep clone={active} lastJob={lastJob}
            onBack={() => setStep('dashboard')}
            onMakeAnother={() => setStep('generate')} />
        )}
        {step === 'pricing' && (
          <PricingPanel onBack={() => setStep('dashboard')} />
        )}
      </main>
    </div>
  );
}
