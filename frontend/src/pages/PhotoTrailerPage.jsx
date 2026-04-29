/* eslint-disable react/prop-types */
/* eslint-disable react-hooks/exhaustive-deps */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Upload, Camera, ShieldCheck, Sparkles, Film, Wand2, Loader2, X,
  CheckCircle2, AlertCircle, Trash2, Play, Download, Share2, RefreshCw,
} from 'lucide-react';
import { toast } from 'sonner';
import { trackFunnel } from '../utils/funnelTracker';

const API = process.env.REACT_APP_BACKEND_URL;
const MAX_PHOTOS = 10;
const MAX_BYTES = 10 * 1024 * 1024;
const ALLOWED = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];

const STAGE_COPY = {
  QUEUED: 'In line to start...',
  VALIDATING: 'Validating your trailer request',
  ANALYZING_PHOTOS: 'Analyzing your photos',
  BUILDING_CHARACTER: 'Building your hero character',
  WRITING_TRAILER_SCRIPT: 'Writing the trailer script',
  GENERATING_SCENES: 'Generating cinematic scenes',
  GENERATING_VOICEOVER: 'Recording the narrator',
  ADDING_MUSIC: 'Mixing music + sound',
  RENDERING_TRAILER: 'Rendering the final trailer',
  COMPLETED: 'Done! Your trailer is ready',
  FAILED: 'Something went wrong',
};

function authHeaders(extra = {}) {
  const t = localStorage.getItem('token');
  return { ...(t ? { Authorization: `Bearer ${t}` } : {}), ...extra };
}

// ─── Step 1: Upload + Consent ─────────────────────────────────────────────────
function UploadStep({ sessionId, setSessionId, photos, setPhotos, consent, setConsent, onNext }) {
  const inputRef = useRef(null);
  const [busy, setBusy] = useState(false);

  const beginSession = useCallback(async (files) => {
    if (sessionId) return sessionId;
    const init = await fetch(`${API}/api/photo-trailer/uploads/init`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({
        file_count: files.length,
        mime_types: files.map(f => f.type),
        file_sizes: files.map(f => f.size),
      }),
    });
    if (!init.ok) {
      const e = await init.json().catch(() => ({}));
      throw new Error(e.detail || 'Could not start upload');
    }
    const j = await init.json();
    setSessionId(j.upload_session_id);
    return j.upload_session_id;
  }, [sessionId, setSessionId]);

  const onPick = async (e) => {
    const list = Array.from(e.target.files || []);
    if (!list.length) return;
    if (photos.length + list.length > MAX_PHOTOS) {
      toast.error(`You can upload a maximum of ${MAX_PHOTOS} photos only.`);
      e.target.value = '';
      return;
    }
    for (const f of list) {
      if (!ALLOWED.includes(f.type)) { toast.error(`Unsupported file type: ${f.name}`); return; }
      if (f.size > MAX_BYTES) { toast.error(`${f.name} is over 10MB.`); return; }
    }
    setBusy(true);
    try {
      const sid = await beginSession([...photos.map(p => ({ type: p.mime, size: p.size })), ...list]);
      const newPhotos = [];
      for (const f of list) {
        const fd = new FormData();
        fd.append('upload_session_id', sid);
        fd.append('file', f);
        const r = await fetch(`${API}/api/photo-trailer/uploads/photo`, {
          method: 'POST', headers: authHeaders(), body: fd,
        });
        if (!r.ok) {
          const er = await r.json().catch(() => ({}));
          toast.error(er.detail || `Failed to upload ${f.name}`);
          continue;
        }
        const j = await r.json();
        newPhotos.push({
          asset_id: j.asset_id,
          url: j.storage_url,
          name: f.name,
          mime: f.type,
          size: f.size,
        });
      }
      setPhotos(p => [...p, ...newPhotos]);
      try { trackFunnel('photo_trailer_upload_completed', { meta: { count: newPhotos.length } }); } catch {}
    } catch (err) {
      toast.error(err.message || 'Upload failed');
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  const removePhoto = (asset_id) => setPhotos(p => p.filter(x => x.asset_id !== asset_id));

  const finalize = async () => {
    if (!consent) { toast.error('Please confirm photo rights to continue.'); return; }
    if (!photos.length) { toast.error('Upload at least one photo first.'); return; }
    const r = await fetch(`${API}/api/photo-trailer/uploads/complete`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ upload_session_id: sessionId, consent_confirmed: true }),
    });
    if (!r.ok) { const e = await r.json().catch(() => ({})); toast.error(e.detail || 'Could not save'); return; }
    try { trackFunnel('photo_trailer_consent_checked', {}); } catch {}
    onNext();
  };

  return (
    <div className="space-y-6" data-testid="trailer-step-upload">
      <div>
        <h2 className="text-2xl font-bold text-white">Upload your photos</h2>
        <p className="text-sm text-slate-400 mt-1">Upload 3–5 clear photos for best results. Max {MAX_PHOTOS}.</p>
      </div>
      <div className="rounded-2xl border-2 border-dashed border-violet-500/30 bg-violet-500/5 p-6 text-center">
        <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={onPick} className="hidden" data-testid="trailer-photo-input" />
        <button onClick={() => inputRef.current?.click()} disabled={busy || photos.length >= MAX_PHOTOS}
          className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white font-semibold disabled:opacity-50"
          data-testid="trailer-upload-btn">
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
          {busy ? 'Uploading...' : 'Add photos'}
        </button>
        <p className="mt-2 text-xs text-slate-500">JPG / PNG / WEBP · up to 10MB each · {photos.length}/{MAX_PHOTOS}</p>
      </div>
      {photos.length > 0 && (
        <div className="grid grid-cols-3 sm:grid-cols-5 gap-2" data-testid="trailer-photo-grid">
          {photos.map(p => (
            <div key={p.asset_id} className="relative group rounded-lg overflow-hidden aspect-square bg-black/40 border border-white/10">
              <img src={p.url} alt={p.name} className="w-full h-full object-cover" />
              <button onClick={() => removePhoto(p.asset_id)} className="absolute top-1 right-1 p-1 rounded-full bg-black/70 opacity-0 group-hover:opacity-100 transition-opacity" aria-label="Remove">
                <Trash2 className="w-3 h-3 text-white" />
              </button>
            </div>
          ))}
        </div>
      )}
      <label className="flex items-start gap-2.5 p-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5 cursor-pointer" data-testid="trailer-consent">
        <input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} className="mt-0.5 accent-emerald-500" data-testid="trailer-consent-checkbox" />
        <div className="text-sm text-slate-200">
          <div className="font-semibold flex items-center gap-1.5"><ShieldCheck className="w-4 h-4 text-emerald-400" /> I confirm I have rights or permission to use these photos.</div>
          <p className="text-xs text-slate-400 mt-0.5">Do not upload photos of people without permission.</p>
        </div>
      </label>
      <button onClick={finalize} disabled={!consent || photos.length === 0}
        className="w-full py-3.5 rounded-xl font-bold text-white bg-gradient-to-r from-violet-600 to-fuchsia-600 disabled:opacity-50"
        data-testid="trailer-step1-next">
        Continue → Choose your hero
      </button>
    </div>
  );
}

// ─── Step 2: Hero / Villain / Supporting ─────────────────────────────────────
function CharactersStep({ photos, hero, setHero, villain, setVillain, supporting, setSupporting, onBack, onNext }) {
  const pick = (asset_id) => {
    if (hero === asset_id) return;
    setHero(asset_id);
    try { trackFunnel('photo_trailer_hero_selected', { meta: { asset_id } }); } catch {}
  };
  const toggleVillain = (asset_id) => setVillain(v => v === asset_id ? null : asset_id);
  const toggleSupport = (asset_id) =>
    setSupporting(arr => arr.includes(asset_id) ? arr.filter(x => x !== asset_id) : [...arr, asset_id].slice(0, 4));
  return (
    <div className="space-y-6" data-testid="trailer-step-characters">
      <div>
        <h2 className="text-2xl font-bold text-white">Choose your hero</h2>
        <p className="text-sm text-slate-400 mt-1">Tap one photo to be the main hero. Optionally pick a villain and supporting cast.</p>
      </div>
      <div className="grid grid-cols-3 sm:grid-cols-5 gap-2.5">
        {photos.map(p => {
          const isHero = hero === p.asset_id;
          const isVillain = villain === p.asset_id;
          const isSupport = supporting.includes(p.asset_id);
          let badge = '';
          if (isHero) badge = 'border-amber-400 ring-2 ring-amber-400';
          else if (isVillain) badge = 'border-rose-500 ring-2 ring-rose-500';
          else if (isSupport) badge = 'border-cyan-400 ring-2 ring-cyan-400';
          else badge = 'border-white/10';
          return (
            <div key={p.asset_id} className={`relative rounded-lg overflow-hidden aspect-square bg-black/40 border-2 ${badge}`} data-testid={`character-card-${p.asset_id}`}>
              <img src={p.url} alt="" className="w-full h-full object-cover" />
              {isHero && <div className="absolute top-1 left-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-400 text-black">HERO</div>}
              {isVillain && <div className="absolute top-1 left-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-500 text-white">VILLAIN</div>}
              {isSupport && <div className="absolute top-1 left-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-cyan-500 text-white">SUPPORT</div>}
              <div className="absolute inset-x-0 bottom-0 grid grid-cols-3 text-[10px] font-semibold">
                <button onClick={() => pick(p.asset_id)} className={`py-1 ${isHero ? 'bg-amber-500 text-black' : 'bg-black/60 text-white'}`} data-testid={`pick-hero-${p.asset_id}`}>Hero</button>
                <button onClick={() => toggleVillain(p.asset_id)} className={`py-1 ${isVillain ? 'bg-rose-500 text-white' : 'bg-black/60 text-white'}`}>Villain</button>
                <button onClick={() => toggleSupport(p.asset_id)} className={`py-1 ${isSupport ? 'bg-cyan-500 text-white' : 'bg-black/60 text-white'}`}>Support</button>
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex gap-2">
        <button onClick={onBack} className="flex-1 py-3 rounded-xl border border-white/10 text-white text-sm" data-testid="trailer-step2-back">Back</button>
        <button onClick={onNext} disabled={!hero} className="flex-1 py-3.5 rounded-xl font-bold text-white bg-gradient-to-r from-violet-600 to-fuchsia-600 disabled:opacity-50" data-testid="trailer-step2-next">
          Continue → Pick template
        </button>
      </div>
    </div>
  );
}

// ─── Step 3: Template + prompt + duration ────────────────────────────────────
function TemplateStep({ templates, templateId, setTemplateId, prompt, setPrompt, duration, setDuration, credits, onBack, onGenerate, busy }) {
  return (
    <div className="space-y-6" data-testid="trailer-step-template">
      <div>
        <h2 className="text-2xl font-bold text-white">Pick a trailer template</h2>
        <p className="text-sm text-slate-400 mt-1">Each template defines tone, narrator and music mood.</p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3" data-testid="trailer-templates-grid">
        {templates.map(t => {
          const active = templateId === t.id;
          return (
            <button key={t.id} onClick={() => { setTemplateId(t.id); try { trackFunnel('photo_trailer_template_selected', { meta: { template_id: t.id } }); } catch {} }}
              className={`text-left rounded-xl border-2 p-4 transition-all ${active ? 'border-violet-500 bg-violet-500/10' : 'border-white/10 bg-white/[0.02] hover:bg-white/[0.05]'}`}
              data-testid={`template-${t.id}`}>
              <div className="flex items-center gap-2 mb-1.5">
                <Film className="w-4 h-4 text-violet-300" />
                <span className="text-sm font-bold text-white">{t.title}</span>
              </div>
              <p className="text-xs text-slate-400 leading-snug">{t.description}</p>
              <div className="mt-2 flex flex-wrap gap-1">
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-slate-400">{t.tone}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-slate-400">{t.scene_count} scenes</span>
              </div>
            </button>
          );
        })}
      </div>
      <div>
        <label className="text-sm font-semibold text-slate-200 block mb-1.5">Add any extra details (optional)</label>
        <textarea value={prompt} onChange={e => setPrompt(e.target.value.slice(0, 500))} rows={3}
          placeholder="e.g. set on a rainy Tokyo rooftop at midnight..."
          className="w-full px-3 py-2 rounded-lg bg-white/[0.03] border border-white/10 text-white text-sm placeholder:text-slate-600"
          data-testid="trailer-prompt" />
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2" data-testid="trailer-duration-picker">
        {[15, 20, 45, 60].map(d => (
          <button key={d} onClick={() => setDuration(d)}
            className={`py-2.5 rounded-lg text-sm font-semibold border ${duration === d ? 'border-violet-500 bg-violet-500/15 text-white' : 'border-white/10 bg-white/[0.02] text-slate-300'}`}
            data-testid={`duration-${d}`}>
            {d}s
          </button>
        ))}
      </div>
      <div className="flex items-center justify-between rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3" data-testid="trailer-credit-estimate">
        <span className="text-sm text-slate-300">Estimated cost</span>
        <span className="text-lg font-bold text-amber-300">{credits} credits</span>
      </div>
      <p className="text-[11px] text-slate-500 italic">AI preserves character inspiration and visual style, but exact likeness may vary.</p>
      <div className="flex gap-2">
        <button onClick={onBack} className="flex-1 py-3 rounded-xl border border-white/10 text-white text-sm" data-testid="trailer-step3-back">Back</button>
        <button onClick={onGenerate} disabled={!templateId || busy}
          className="flex-1 py-3.5 rounded-xl font-bold text-white bg-gradient-to-r from-violet-600 to-fuchsia-600 disabled:opacity-50 flex items-center justify-center gap-2"
          data-testid="trailer-generate-btn">
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />}
          {busy ? 'Submitting...' : `Generate trailer (${credits} cr)`}
        </button>
      </div>
    </div>
  );
}

// ─── Step 4: Progress ─────────────────────────────────────────────────────────
function ProgressStep({ jobId, onDone, onFail }) {
  const [job, setJob] = useState(null);
  useEffect(() => {
    let stop = false;
    const tick = async () => {
      while (!stop) {
        try {
          const r = await fetch(`${API}/api/photo-trailer/jobs/${jobId}`, { headers: authHeaders() });
          if (r.ok) {
            const j = await r.json();
            setJob(j);
            if (j.status === 'COMPLETED') { onDone(j); return; }
            if (j.status === 'FAILED') { onFail(j); return; }
          }
        } catch {}
        await new Promise(r => setTimeout(r, 2500));
      }
    };
    tick();
    return () => { stop = true; };
  }, [jobId]);
  const stage = job?.current_stage || 'QUEUED';
  const pct = job?.progress_percent ?? 0;
  return (
    <div className="space-y-6 text-center py-8" data-testid="trailer-step-progress">
      <div className="mx-auto w-16 h-16 rounded-full bg-violet-500/15 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-violet-300 animate-spin" />
      </div>
      <div>
        <h2 className="text-2xl font-bold text-white">Building your trailer</h2>
        <p className="text-sm text-slate-300 mt-1" data-testid="trailer-stage-copy">{STAGE_COPY[stage] || stage}</p>
      </div>
      <div className="w-full max-w-md mx-auto h-2 rounded-full bg-white/10 overflow-hidden">
        <div className="h-full bg-gradient-to-r from-violet-500 to-fuchsia-500 transition-all" style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-slate-500 font-mono" data-testid="trailer-progress-pct">{pct}% · {stage}</p>
    </div>
  );
}

// ─── Step 5: Result ───────────────────────────────────────────────────────────
function ResultStep({ job, onCreateAnother }) {
  const url = job.result_video_url;
  return (
    <div className="space-y-5" data-testid="trailer-step-result">
      <div className="text-center">
        <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto" />
        <h2 className="text-2xl font-bold text-white mt-2">Your trailer is ready</h2>
      </div>
      <video src={url} controls poster={job.result_thumbnail_url} className="w-full rounded-2xl border border-white/10 bg-black" data-testid="trailer-result-video" />
      <div className="flex flex-wrap gap-2">
        <a href={url} download className="flex-1 py-3 rounded-xl bg-violet-600 text-white text-sm font-semibold flex items-center justify-center gap-2" data-testid="trailer-download-btn">
          <Download className="w-4 h-4" /> Download
        </a>
        <button onClick={() => { try { trackFunnel('photo_trailer_shared', { meta: { job_id: job._id } }); } catch {}
          if (navigator.share) navigator.share({ title: 'My AI trailer', url }).catch(() => {});
          else { navigator.clipboard.writeText(url); toast.success('Link copied'); }
        }} className="flex-1 py-3 rounded-xl bg-white/10 text-white text-sm font-semibold flex items-center justify-center gap-2" data-testid="trailer-share-btn">
          <Share2 className="w-4 h-4" /> Share
        </button>
        <button onClick={onCreateAnother} className="flex-1 py-3 rounded-xl border border-white/10 text-white text-sm flex items-center justify-center gap-2" data-testid="trailer-create-another-btn">
          <RefreshCw className="w-4 h-4" /> Make another
        </button>
      </div>
    </div>
  );
}

// ─── Failure recovery ─────────────────────────────────────────────────────────
function FailedStep({ job, onRetry, onEdit, onDelete }) {
  return (
    <div className="space-y-5 text-center py-6" data-testid="trailer-step-failed">
      <AlertCircle className="w-10 h-10 text-rose-400 mx-auto" />
      <div>
        <h2 className="text-xl font-bold text-white">Trailer didn't render</h2>
        <p className="text-sm text-slate-300 mt-1">{job.error_message || 'Something went wrong. Your credits were refunded.'}</p>
      </div>
      <div className="flex flex-wrap gap-2 justify-center">
        <button onClick={onRetry} className="py-2.5 px-4 rounded-xl bg-violet-600 text-white text-sm font-semibold flex items-center gap-2" data-testid="trailer-retry-btn">
          <RefreshCw className="w-4 h-4" /> Retry
        </button>
        <button onClick={onEdit} className="py-2.5 px-4 rounded-xl bg-white/10 text-white text-sm" data-testid="trailer-edit-btn">Edit & retry</button>
        <button onClick={onDelete} className="py-2.5 px-4 rounded-xl border border-rose-500/30 text-rose-300 text-sm" data-testid="trailer-delete-btn">Delete</button>
      </div>
    </div>
  );
}

// ─── Library ──────────────────────────────────────────────────────────────────
function Library({ onOpen }) {
  const [items, setItems] = useState([]);
  useEffect(() => {
    fetch(`${API}/api/photo-trailer/my-trailers`, { headers: authHeaders() })
      .then(r => r.ok ? r.json() : { trailers: [] })
      .then(d => setItems(d.trailers || [])).catch(() => {});
  }, []);
  if (!items.length) return null;
  return (
    <div className="mt-10" data-testid="trailer-library">
      <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">Your trailers</h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {items.map(t => (
          <button key={t._id || t.public_share_slug} onClick={() => onOpen(t)} className="text-left rounded-xl bg-white/[0.03] border border-white/10 overflow-hidden hover:border-violet-500/40 transition-colors" data-testid={`library-item-${t._id || t.public_share_slug}`}>
            <div className="aspect-video bg-black flex items-center justify-center relative">
              {t.result_thumbnail_url ? <img src={t.result_thumbnail_url} alt="" className="w-full h-full object-cover" /> : <Film className="w-6 h-6 text-slate-600" />}
              <span className="absolute bottom-1 right-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-black/70 text-white">{t.duration_target_seconds}s</span>
            </div>
            <div className="p-2">
              <p className="text-xs text-white font-semibold truncate">{t.template_name}</p>
              <p className="text-[10px] text-slate-500 truncate">{t.status}</p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function PhotoTrailerPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [sessionId, setSessionId] = useState(null);
  const [photos, setPhotos] = useState([]);
  const [consent, setConsent] = useState(false);
  const [hero, setHero] = useState(null);
  const [villain, setVillain] = useState(null);
  const [supporting, setSupporting] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [templateId, setTemplateId] = useState(null);
  const [prompt, setPrompt] = useState('');
  const [duration, setDuration] = useState(45);
  const [busy, setBusy] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [completedJob, setCompletedJob] = useState(null);
  const [failedJob, setFailedJob] = useState(null);

  useEffect(() => {
    try { trackFunnel('photo_trailer_page_viewed', {}); } catch {}
    fetch(`${API}/api/photo-trailer/templates`).then(r => r.json()).then(d => setTemplates(d.templates || [])).catch(() => {});
  }, []);

  const credits = useMemo(() => {
    if (duration <= 15) return 5;
    if (duration <= 20) return 5;
    if (duration <= 45) return 25;
    return 35;
  }, [duration]);

  const onGenerate = async () => {
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/photo-trailer/jobs`, {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          upload_session_id: sessionId,
          hero_asset_id: hero,
          villain_asset_id: villain,
          supporting_asset_ids: supporting,
          template_id: templateId,
          custom_prompt: prompt,
          duration_target_seconds: duration,
        }),
      });
      if (!r.ok) {
        const e = await r.json().catch(() => ({}));
        toast.error(e.detail || 'Could not start trailer');
        setBusy(false);
        return;
      }
      const j = await r.json();
      setJobId(j.job_id);
      try { trackFunnel('photo_trailer_generation_started', { meta: { job_id: j.job_id, template: templateId } }); } catch {}
      setStep(4);
    } catch (e) {
      toast.error('Network error');
    } finally {
      setBusy(false);
    }
  };

  const onRetry = async () => {
    if (!jobId) return;
    const r = await fetch(`${API}/api/photo-trailer/jobs/${jobId}/retry`, { method: 'POST', headers: authHeaders() });
    if (r.ok) { setFailedJob(null); setStep(4); }
  };

  return (
    <div className="min-h-screen min-h-[100dvh] bg-[#0a0a10] text-white" data-testid="photo-trailer-page">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
        <header className="mb-8 flex items-center justify-between">
          <div>
            <p className="text-[11px] uppercase tracking-widest text-violet-300 font-bold">YouStar</p>
            <h1 className="text-3xl font-bold flex items-center gap-2">
              <Film className="w-7 h-7 text-violet-400" /> My Movie Trailer
            </h1>
            <p className="text-sm text-slate-400 mt-1">Upload photos · Pick a template · Generate a 20-60s cinematic AI trailer.</p>
          </div>
        </header>

        {/* step indicator */}
        <div className="flex items-center gap-2 mb-6" data-testid="trailer-stepper">
          {['Upload', 'Hero', 'Template', 'Render', 'Result'].map((label, i) => {
            const active = step === i + 1;
            const done = step > i + 1;
            return (
              <div key={label} className="flex-1 flex items-center gap-2">
                <span className={`shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold ${done ? 'bg-emerald-500 text-black' : active ? 'bg-violet-500 text-white' : 'bg-white/10 text-slate-500'}`}>{done ? '✓' : i + 1}</span>
                <span className={`text-xs ${active ? 'text-white font-semibold' : 'text-slate-500'}`}>{label}</span>
                {i < 4 && <span className="flex-1 h-px bg-white/10" />}
              </div>
            );
          })}
        </div>

        <div className="rounded-3xl border border-white/10 bg-white/[0.02] p-5 sm:p-7">
          {step === 1 && (
            <UploadStep sessionId={sessionId} setSessionId={setSessionId} photos={photos} setPhotos={setPhotos} consent={consent} setConsent={setConsent} onNext={() => setStep(2)} />
          )}
          {step === 2 && (
            <CharactersStep photos={photos} hero={hero} setHero={setHero} villain={villain} setVillain={setVillain} supporting={supporting} setSupporting={setSupporting} onBack={() => setStep(1)} onNext={() => setStep(3)} />
          )}
          {step === 3 && (
            <TemplateStep templates={templates} templateId={templateId} setTemplateId={setTemplateId} prompt={prompt} setPrompt={setPrompt} duration={duration} setDuration={setDuration} credits={credits} onBack={() => setStep(2)} onGenerate={onGenerate} busy={busy} />
          )}
          {step === 4 && jobId && !completedJob && !failedJob && (
            <ProgressStep jobId={jobId} onDone={(j) => { setCompletedJob(j); try { trackFunnel('photo_trailer_generation_completed', { meta: { job_id: j._id || jobId } }); } catch {} setStep(5); }} onFail={(j) => { setFailedJob(j); setStep(5); }} />
          )}
          {step === 5 && completedJob && (
            <ResultStep job={completedJob} onCreateAnother={() => { setStep(1); setPhotos([]); setConsent(false); setHero(null); setVillain(null); setSupporting([]); setTemplateId(null); setPrompt(''); setSessionId(null); setJobId(null); setCompletedJob(null); setFailedJob(null); }} />
          )}
          {step === 5 && failedJob && (
            <FailedStep job={failedJob} onRetry={onRetry} onEdit={() => { setFailedJob(null); setStep(3); }} onDelete={async () => {
              if (jobId) await fetch(`${API}/api/photo-trailer/jobs/${jobId}`, { method: 'DELETE', headers: authHeaders() });
              setFailedJob(null); setStep(1);
            }} />
          )}
        </div>

        <Library onOpen={(t) => { if (t.status === 'COMPLETED') { setCompletedJob(t); setStep(5); } }} />
      </div>
    </div>
  );
}
