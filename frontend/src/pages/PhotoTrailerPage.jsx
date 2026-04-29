/* eslint-disable react/prop-types */
/* eslint-disable react-hooks/exhaustive-deps */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Upload, Camera, ShieldCheck, Sparkles, Film, Wand2, Loader2, X,
  CheckCircle2, AlertCircle, Trash2, Play, Download, Share2, RefreshCw, MessageCircle, Check,
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
      <label
        className={`flex items-start gap-3 p-4 rounded-xl border cursor-pointer transition-colors ${
          consent
            ? 'border-emerald-400/60 bg-emerald-500/10 ring-1 ring-emerald-400/30'
            : 'border-white/15 bg-white/[0.03] hover:border-emerald-500/40 hover:bg-emerald-500/[0.06]'
        }`}
        data-testid="trailer-consent"
      >
        <input
          type="checkbox"
          checked={consent}
          onChange={e => setConsent(e.target.checked)}
          className="sr-only peer"
          data-testid="trailer-consent-checkbox"
        />
        <span
          aria-hidden
          className={`mt-0.5 flex-shrink-0 w-6 h-6 sm:w-[22px] sm:h-[22px] rounded-[5px] border-[2.5px] flex items-center justify-center transition-all ${
            consent
              ? 'bg-emerald-500 border-emerald-500'
              : 'bg-white/[0.06] border-slate-300 hover:border-emerald-400'
          }`}
        >
          {consent && <Check className="w-4 h-4 text-white" strokeWidth={3.5} />}
        </span>
        <div className="text-sm text-slate-200 select-none">
          <div className="font-semibold flex items-center gap-1.5">
            <ShieldCheck className={`w-4 h-4 ${consent ? 'text-emerald-300' : 'text-slate-400'}`} />
            I confirm I have rights or permission to use these photos.
          </div>
          <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
            No celebrities, public figures, or copyrighted characters (Marvel, Disney, anime IP, etc.).
            No photos of minors without a parent's consent. Source photos are auto-deleted after 7 days.
          </p>
          <p className="text-[11px] text-slate-500 mt-1">
            Trailers carry a Visionary Suite watermark + provenance metadata for safety.
          </p>
        </div>
      </label>

      {/* Helper text — shows the EXACT reason the CTA is disabled */}
      {!busy && photos.length === 0 && (
        <p className="text-xs text-slate-400 text-center" data-testid="trailer-step1-hint">
          Add at least 1 photo to continue.
        </p>
      )}
      {!busy && photos.length > 0 && !consent && (
        <p className="text-xs text-amber-300/90 text-center" data-testid="trailer-step1-hint">
          Confirm photo rights to continue.
        </p>
      )}
      {busy && (
        <p className="text-xs text-violet-300 text-center inline-flex items-center gap-1.5 justify-center w-full" data-testid="trailer-step1-hint">
          <Loader2 className="w-3 h-3 animate-spin" /> Uploading photos…
        </p>
      )}

      <button
        onClick={finalize}
        disabled={!consent || photos.length === 0 || busy}
        className="w-full py-3.5 rounded-xl font-bold text-white bg-gradient-to-r from-violet-600 to-fuchsia-600 disabled:opacity-40 disabled:cursor-not-allowed enabled:hover:from-violet-500 enabled:hover:to-fuchsia-500 transition-colors"
        data-testid="trailer-step1-next"
      >
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
      {/* Each card stacks: photo on top, large 3-button role row below.
          Min 44px tap target on mobile. Clear color states. */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {photos.map(p => {
          const isHero = hero === p.asset_id;
          const isVillain = villain === p.asset_id;
          const isSupport = supporting.includes(p.asset_id);
          let frame = 'border-white/10';
          if (isHero)        frame = 'border-amber-400 ring-2 ring-amber-400/60 shadow-[0_0_24px_-8px_rgba(251,191,36,0.7)]';
          else if (isVillain) frame = 'border-rose-500 ring-2 ring-rose-500/60 shadow-[0_0_24px_-8px_rgba(244,63,94,0.7)]';
          else if (isSupport) frame = 'border-cyan-400 ring-2 ring-cyan-400/60 shadow-[0_0_24px_-8px_rgba(34,211,238,0.7)]';

          // Reusable role-button class generator. 44px tap target on mobile.
          const roleBtn = (active, activeCls, label, testid, onClick) => (
            <button
              type="button"
              onClick={onClick}
              data-testid={testid}
              aria-pressed={active}
              className={`flex-1 min-h-[44px] sm:min-h-[40px] px-2 text-sm font-bold tracking-wide rounded-lg border-2 transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-violet-400 ${
                active ? activeCls
                       : 'border-white/15 bg-white/[0.04] text-slate-300 hover:bg-white/[0.08] hover:border-white/25 cursor-pointer'
              }`}
            >
              {label}
            </button>
          );

          return (
            <div key={p.asset_id} className={`rounded-2xl bg-black/30 border-2 ${frame} overflow-hidden transition-all`} data-testid={`character-card-${p.asset_id}`}>
              <div className="relative aspect-square">
                <img src={p.url} alt="" className="w-full h-full object-cover" />
                {isHero    && <div className="absolute top-2 left-2 px-2 py-1 rounded-md text-xs font-extrabold bg-amber-400 text-black shadow-md">★ HERO</div>}
                {isVillain && <div className="absolute top-2 left-2 px-2 py-1 rounded-md text-xs font-extrabold bg-rose-500 text-white shadow-md">⚔ VILLAIN</div>}
                {isSupport && <div className="absolute top-2 left-2 px-2 py-1 rounded-md text-xs font-extrabold bg-cyan-500 text-white shadow-md">✓ SUPPORT</div>}
              </div>
              <div className="flex gap-2 p-2.5 bg-black/50 border-t border-white/10">
                {roleBtn(isHero,    'border-amber-400 bg-amber-500 text-black cursor-pointer',          'Hero',    `pick-hero-${p.asset_id}`,    () => pick(p.asset_id))}
                {roleBtn(isVillain, 'border-rose-500 bg-rose-500 text-white cursor-pointer',            'Villain', `pick-villain-${p.asset_id}`, () => toggleVillain(p.asset_id))}
                {roleBtn(isSupport, 'border-cyan-400 bg-cyan-500 text-white cursor-pointer',            'Support', `pick-support-${p.asset_id}`, () => toggleSupport(p.asset_id))}
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

// ─── Waiting Playground (lightweight anxiety reducer — NOT a game engine) ────
const WAITING_QUOTES = [
  '"The first step is the hardest. You already took it." — Unknown',
  '"Creativity is intelligence having fun." — Albert Einstein',
  '"Make it work, make it right, make it fast." — Kent Beck',
  '"You miss 100% of the shots you don\'t take." — Wayne Gretzky',
  '"Done is better than perfect." — Sheryl Sandberg',
  '"Storytelling is the most powerful way to put ideas into the world." — Robert McKee',
  '"Almost everything will work again if you unplug it for a few minutes." — Anne Lamott',
];
const WAITING_FACTS = [
  'A typical Hollywood movie trailer is between 90 and 150 seconds — yours will be shorter and punchier.',
  'The "Inception" trailer\'s "BWAAA" sound has its own name: a "braam". It defined a decade of trailers.',
  'Octopuses have three hearts. Two pump blood to the gills, one pumps to the rest of the body.',
  'Honey never spoils. Archaeologists found 3,000-year-old honey in Egyptian tombs that was still edible.',
  'The first 10 seconds of a film trailer determine whether viewers keep watching 78% of the time.',
  'A bolt of lightning is five times hotter than the surface of the sun.',
  'Bananas are berries, but strawberries are not.',
];
const WAITING_RIDDLES = [
  { q: 'I speak without a mouth and hear without ears. I have no body, but come alive with the wind. What am I?', choices: ['A cloud', 'An echo', 'A whisper', 'A shadow'], answer: 1 },
  { q: 'The more you take, the more you leave behind. What are they?', choices: ['Memories', 'Footsteps', 'Photos', 'Tears'], answer: 1 },
  { q: 'What has hands but cannot clap?', choices: ['A statue', 'A mannequin', 'A clock', 'A glove'], answer: 2 },
  { q: 'What can travel around the world while staying in a corner?', choices: ['A globe', 'A stamp', 'A satellite', 'The wind'], answer: 1 },
  { q: 'I\'m tall when I\'m young, and I\'m short when I\'m old. What am I?', choices: ['A tree', 'A candle', 'A shadow', 'A mountain'], answer: 1 },
];

function WaitingPlayground() {
  const [riddleIdx, setRiddleIdx] = useState(() => Math.floor(Math.random() * WAITING_RIDDLES.length));
  const [picked, setPicked] = useState(null);
  const [revealed, setRevealed] = useState(false);
  const [quoteIdx, setQuoteIdx] = useState(() => Math.floor(Math.random() * WAITING_QUOTES.length));
  const [factIdx, setFactIdx] = useState(() => Math.floor(Math.random() * WAITING_FACTS.length));

  const riddle = WAITING_RIDDLES[riddleIdx];
  const isCorrect = picked === riddle.answer;

  const nextRiddle = () => {
    setRiddleIdx((i) => (i + 1) % WAITING_RIDDLES.length);
    setPicked(null);
    setRevealed(false);
  };

  return (
    <div className="space-y-3 text-left max-w-md mx-auto" data-testid="trailer-waiting-playground">
      <div className="rounded-xl border border-violet-500/20 bg-violet-500/[0.04] p-4" data-testid="waiting-riddle">
        <p className="text-[10px] uppercase tracking-wider text-violet-300/80 font-bold mb-1.5">Quick brain teaser</p>
        <p className="text-sm text-slate-200">{riddle.q}</p>
        <div className="grid grid-cols-2 gap-1.5 mt-3">
          {riddle.choices.map((c, i) => {
            const isPicked = picked === i;
            const showCorrect = revealed && i === riddle.answer;
            const showWrong = revealed && isPicked && i !== riddle.answer;
            return (
              <button
                key={i}
                onClick={() => { setPicked(i); setRevealed(true); }}
                disabled={revealed}
                className={`text-xs rounded-lg px-2.5 py-1.5 border text-left transition-colors ${
                  showCorrect ? 'bg-emerald-500/20 border-emerald-400 text-emerald-200' :
                  showWrong   ? 'bg-rose-500/20 border-rose-400 text-rose-200' :
                  isPicked    ? 'bg-violet-500/20 border-violet-400 text-violet-100' :
                                'bg-white/[0.03] border-white/10 text-slate-300 hover:border-violet-500/40'
                }`}
                data-testid={`waiting-riddle-choice-${i}`}
              >
                {c}
              </button>
            );
          })}
        </div>
        {revealed && (
          <div className="mt-2.5 flex items-center justify-between text-xs">
            <span className={isCorrect ? 'text-emerald-300' : 'text-slate-400'}>
              {isCorrect ? '✓ Nice one.' : `Answer: ${riddle.choices[riddle.answer]}`}
            </span>
            <button onClick={nextRiddle} className="text-violet-300 hover:text-violet-200" data-testid="waiting-riddle-next">
              Next →
            </button>
          </div>
        )}
      </div>

      <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4" data-testid="waiting-quote">
        <p className="text-[10px] uppercase tracking-wider text-slate-500 font-bold mb-1.5">Inspiration</p>
        <p className="text-sm text-slate-200 italic leading-relaxed">{WAITING_QUOTES[quoteIdx]}</p>
        <button
          onClick={() => setQuoteIdx((i) => (i + 1) % WAITING_QUOTES.length)}
          className="text-xs text-violet-300 hover:text-violet-200 mt-2"
          data-testid="waiting-quote-next"
        >
          Another quote →
        </button>
      </div>

      <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4" data-testid="waiting-fact">
        <p className="text-[10px] uppercase tracking-wider text-slate-500 font-bold mb-1.5">Did you know</p>
        <p className="text-sm text-slate-200 leading-relaxed">{WAITING_FACTS[factIdx]}</p>
        <button
          onClick={() => setFactIdx((i) => (i + 1) % WAITING_FACTS.length)}
          className="text-xs text-violet-300 hover:text-violet-200 mt-2"
          data-testid="waiting-fact-next"
        >
          Another fact →
        </button>
      </div>
    </div>
  );
}

// ─── Step 4: Progress ─────────────────────────────────────────────────────────
function ProgressStep({ jobId, onDone, onFail }) {
  const navigate = useNavigate();
  const [job, setJob] = useState(null);
  const [showPlayground, setShowPlayground] = useState(false);
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

      {/* Reassurance copy + escape hatches — users should NOT feel trapped */}
      <div className="max-w-lg mx-auto rounded-xl border border-violet-400/20 bg-violet-500/[0.04] p-4 text-left" data-testid="trailer-leave-card">
        <p className="text-sm text-slate-200 leading-relaxed">
          Your trailer is being created. <span className="text-violet-200 font-semibold">You can leave this page</span> and use other Visionary Suite features — we'll notify you when it's ready.
        </p>
        <p className="text-xs text-slate-400 mt-1.5">
          Your trailer will be saved in <span className="text-violet-300">Profile → MySpace</span>.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mt-3">
          <button
            onClick={() => navigate('/app/my-space')}
            className="py-2 px-3 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-sm font-semibold transition-colors"
            data-testid="trailer-go-myspace-btn"
          >
            Go to MySpace
          </button>
          <button
            onClick={() => navigate('/app')}
            className="py-2 px-3 rounded-lg bg-white/10 hover:bg-white/15 text-white text-sm transition-colors"
            data-testid="trailer-explore-other-btn"
          >
            Explore other tools
          </button>
          <button
            onClick={() => setShowPlayground(v => !v)}
            className={`py-2 px-3 rounded-lg text-sm transition-colors ${
              showPlayground
                ? 'bg-fuchsia-500/20 text-fuchsia-200 border border-fuchsia-500/40'
                : 'bg-white/10 hover:bg-white/15 text-white'
            }`}
            data-testid="trailer-stay-play-btn"
          >
            {showPlayground ? 'Hide' : 'Stay and play while waiting'}
          </button>
        </div>
      </div>

      {showPlayground && <WaitingPlayground />}
    </div>
  );
}

// ─── Step 5: Result ───────────────────────────────────────────────────────────
function ResultStep({ job, onCreateAnother }) {
  // Owner playback uses a fresh signed stream URL (10 min TTL). Sharing
  // points at the public /trailer/:slug page — that page re-signs server-side.
  const [streamUrl, setStreamUrl] = React.useState(null);
  const [thumbUrl, setThumbUrl] = React.useState(job.result_thumbnail_url || null);
  const downloadHrefRef = React.useRef(null);
  React.useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const r = await fetch(`${API}/api/photo-trailer/jobs/${job._id || job.job_id}/stream`,
                              { headers: authHeaders() });
        if (!r.ok) return;
        const j = await r.json();
        if (!cancelled) { setStreamUrl(j.url); if (j.thumbnail_url) setThumbUrl(j.thumbnail_url); }
      } catch {}
    };
    load();
    // Re-sign 30s before the URL expires (default 10 min).
    const timer = setInterval(load, 9 * 60 * 1000);
    return () => { cancelled = true; clearInterval(timer); };
  }, [job._id, job.job_id]);

  const PUBLIC_BASE = window.location.origin;
  const slug = job.public_share_slug;
  const sharePageUrl = slug ? `${PUBLIC_BASE}/trailer/${slug}` : null;

  const buildShareLink = (medium) => {
    if (!sharePageUrl) return '';
    const sep = sharePageUrl.includes('?') ? '&' : '?';
    return `${sharePageUrl}${sep}utm_source=trailer_share&utm_medium=${medium}&utm_campaign=youstar`;
  };
  const PREFILL = (shareLink) =>
    `🎬 I just made my own movie trailer with YouStar on Visionary Suite. Watch it here: ${shareLink}`;

  const handleWhatsApp = () => {
    const shareLink = buildShareLink('whatsapp');
    if (!shareLink) { toast.error('Share link is not ready yet — please try again in a moment.'); return; }
    try {
      trackFunnel('photo_trailer_whatsapp_share_clicked', {
        meta: { job_id: job._id, template: job.template_id, share_url: sharePageUrl },
      });
    } catch {}
    window.open(`https://wa.me/?text=${encodeURIComponent(PREFILL(shareLink))}`, '_blank', 'noopener,noreferrer');
  };

  const handleNativeShare = async () => {
    const shareLink = buildShareLink('native');
    if (!shareLink) { toast.error('Share link is not ready yet'); return; }
    try {
      trackFunnel('photo_trailer_shared', {
        meta: { job_id: job._id, channel: navigator.share ? 'native' : 'clipboard' },
      });
    } catch {}
    if (navigator.share) {
      try {
        await navigator.share({ title: 'My AI movie trailer', text: PREFILL(shareLink), url: shareLink });
      } catch {}
    } else {
      try { await navigator.clipboard.writeText(PREFILL(shareLink)); toast.success('Link copied — paste it anywhere'); }
      catch { toast.error('Could not copy link'); }
    }
  };

  const handleDownload = async (e) => {
    e.preventDefault();
    try {
      const r = await fetch(`${API}/api/photo-trailer/jobs/${job._id || job.job_id}/stream?download=true`,
                            { headers: authHeaders() });
      if (!r.ok) { toast.error('Could not start download'); return; }
      const j = await r.json();
      // Open in a new tab so the browser handles the download via Content-Disposition
      window.open(j.url, '_blank', 'noopener');
    } catch {
      toast.error('Could not start download');
    }
  };

  return (
    <div className="space-y-5" data-testid="trailer-step-result">
      <div className="text-center">
        <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto" />
        <h2 className="text-2xl font-bold text-white mt-2">Your trailer is ready</h2>
      </div>
      <video src={streamUrl || undefined} controls poster={thumbUrl || undefined} className="w-full rounded-2xl border border-white/10 bg-black" data-testid="trailer-result-video" />
      <div className="flex flex-wrap gap-2">
        <button onClick={handleDownload} className="flex-1 min-w-[120px] py-3 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-sm font-semibold flex items-center justify-center gap-2 transition-colors" data-testid="trailer-download-btn">
          <Download className="w-4 h-4" /> Download
        </button>
        <button
          onClick={handleWhatsApp}
          className="flex-1 min-w-[120px] py-3 rounded-xl bg-[#25D366] hover:bg-[#1EA952] text-white text-sm font-semibold flex items-center justify-center gap-2 transition-colors"
          data-testid="trailer-whatsapp-share-btn"
        >
          <MessageCircle className="w-4 h-4" /> Share on WhatsApp
        </button>
        <button
          onClick={handleNativeShare}
          className="flex-1 min-w-[120px] py-3 rounded-xl bg-white/10 hover:bg-white/15 text-white text-sm font-semibold flex items-center justify-center gap-2 transition-colors"
          data-testid="trailer-share-btn"
        >
          <Share2 className="w-4 h-4" /> More
        </button>
        <button onClick={onCreateAnother} className="flex-1 min-w-[120px] py-3 rounded-xl border border-white/10 hover:bg-white/5 text-white text-sm flex items-center justify-center gap-2 transition-colors" data-testid="trailer-create-another-btn">
          <RefreshCw className="w-4 h-4" /> Make another
        </button>
      </div>
      <p className="text-xs text-slate-500 text-center">
        Want it bigger? Share via WhatsApp — your friends get a single tap to watch.
      </p>
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
