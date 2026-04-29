/* eslint-disable react/prop-types */
/* eslint-disable react-hooks/exhaustive-deps */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Upload, Camera, ShieldCheck, Sparkles, Film, Wand2, Loader2, X,
  CheckCircle2, AlertCircle, Trash2, Play, Download, Share2, RefreshCw, MessageCircle, Check, Lock, Crown,
  ArrowLeft, Home,
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
function TemplateStep({ templates, templateId, setTemplateId, prompt, setPrompt, duration, setDuration, credits, onBack, onGenerate, busy, userPlan, userCredits }) {
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
      <div className="grid grid-cols-3 gap-2" data-testid="trailer-duration-picker">
        {/* Founder spec: 20s preview / 60s paid / 90s premium. Lock icon on
            tiers above the user's current plan. Server-side enforcement is
            authoritative — this is just UX guidance. */}
        {[
          { sec: 20, label: '20s', sub: 'Preview',  required: 'FREE'    },
          { sec: 60, label: '60s', sub: 'Paid',     required: 'PAID'    },
          { sec: 90, label: '90s', sub: 'Premium ✦', required: 'PREMIUM' },
        ].map(d => {
          const planRank = { FREE: 0, PAID: 1, PREMIUM: 2 };
          const userRank = planRank[(userPlan || 'FREE').toUpperCase()] ?? 0;
          const reqRank  = planRank[d.required] ?? 0;
          const locked = userRank < reqRank;
          return (
            <button
              key={d.sec}
              onClick={() => setDuration(d.sec)}
              className={`relative py-3 rounded-lg text-sm font-semibold border transition-colors ${
                duration === d.sec
                  ? 'border-violet-500 bg-violet-500/15 text-white'
                  : 'border-white/10 bg-white/[0.02] text-slate-300 hover:bg-white/[0.05]'
              } ${locked ? 'opacity-90' : ''}`}
              data-testid={`duration-${d.sec}`}
              data-locked={locked ? '1' : '0'}
            >
              <div className="text-base">{d.label}</div>
              <div className="text-[10px] mt-0.5 opacity-70 flex items-center justify-center gap-1">
                {locked && <Lock className="w-3 h-3" />}
                {d.sub}
              </div>
            </button>
          );
        })}
      </div>
      <div className="flex items-center justify-between rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3" data-testid="trailer-credit-estimate">
        <span className="text-sm text-slate-300">Estimated cost</span>
        <span className="text-lg font-bold text-amber-300">{credits} credits</span>
      </div>
      {/* P0 revenue UX: show "Need X / You are short by Y" right under the
          cost line so the user sees their balance vs the cost BEFORE they
          tap Generate. Removes the surprise that kills conversion. */}
      {typeof userCredits === 'number' && credits > 0 && (
        userCredits >= credits ? (
          <p className="text-[11px] text-slate-500" data-testid="credit-status-ok">
            Need {credits} credits · you have {userCredits}
          </p>
        ) : (
          <p className="text-[11px] text-amber-300 font-semibold" data-testid="credit-status-short">
            You are short by {credits - userCredits} credit{(credits - userCredits) === 1 ? '' : 's'}
          </p>
        )
      )}
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
  // P0 reliability fix: escalation copy gates on elapsed time, not on the
  // first paint. Founder spec: "Still working…" appears at 3 minutes — not
  // before. Earlier than that and we look broken when we're just slow.
  const [elapsedSec, setElapsedSec] = useState(0);
  const startTsRef = useRef(Date.now());

  useEffect(() => {
    const t = setInterval(() => {
      setElapsedSec(Math.floor((Date.now() - startTsRef.current) / 1000));
    }, 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    let stop = false;
    const tick = async () => {
      while (!stop) {
        try {
          const r = await fetch(`${API}/api/photo-trailer/jobs/${jobId}`, { headers: authHeaders() });
          if (r.ok) {
            const j = await r.json();
            setJob(j);
            // P0: ANY terminal status → exit progress screen immediately.
            // Trust the backend's status field (not progress_percent), so a
            // job that flipped to FAILED while pct was still at 88 transitions
            // cleanly to the FailedStep.
            if (j.status === 'COMPLETED') { onDone(j); return; }
            if (j.status === 'FAILED' || j.status === 'CANCELLED') { onFail(j); return; }
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
  // RELIABILITY SPRINT: progress_message gives sub-stage detail like
  // "Retrying scene 4/6" or "Recovering stalled job — auto-retrying".
  // It overrides the static stage copy when present so the user always
  // sees fresh signal — never a silent dead job.
  const progressMessage = job?.progress_message;
  const stageCopy = STAGE_COPY[stage] || stage;
  const isRetry = !!progressMessage && /retry|recover/i.test(progressMessage);
  // Escalation gates (founder spec)
  const ESCALATE_AT_SEC = 180;   // 3 min — show "you can leave this page"
  const STILL_WORKING_AT_SEC = 240; // 4 min — show stronger copy
  const showLeaveCard = elapsedSec >= ESCALATE_AT_SEC;
  const showStillWorking = elapsedSec >= STILL_WORKING_AT_SEC;

  return (
    <div className="space-y-6 text-center py-8" data-testid="trailer-step-progress">
      <div className="mx-auto w-16 h-16 rounded-full bg-violet-500/15 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-violet-300 animate-spin" />
      </div>
      <div>
        <h2 className="text-2xl font-bold text-white">Building your trailer</h2>
        <p className="text-sm text-slate-300 mt-1" data-testid="trailer-stage-copy">{stageCopy}</p>
        {progressMessage && (
          <p className={`text-sm mt-1 font-medium ${isRetry ? 'text-amber-300' : 'text-violet-300'}`}
             data-testid="trailer-progress-message">
            {progressMessage}
          </p>
        )}
      </div>
      <div className="w-full max-w-md mx-auto h-2 rounded-full bg-white/10 overflow-hidden">
        <div className="h-full bg-gradient-to-r from-violet-500 to-fuchsia-500 transition-all" style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-slate-500 font-mono" data-testid="trailer-progress-pct">{pct}% · {stage}</p>

      {/* P0 reliability fix: escalation copy is GATED to the 3-min mark. Users
          who finish in under 3 min never see this — keeps the sub-3-min flow
          feeling fast. After 3 min: "you can leave this page". After 4 min:
          stronger "Still working…" message + same escape hatches. */}
      {showStillWorking && (
        <div className="max-w-lg mx-auto rounded-xl border border-amber-500/30 bg-amber-500/[0.06] p-3 text-left"
             data-testid="trailer-still-working-card">
          <p className="text-sm text-amber-200 font-semibold">
            This is taking longer than usual.
          </p>
          <p className="text-xs text-amber-100/80 mt-1">
            You can leave this page — we'll notify you when it's ready, and your
            trailer will be saved in Profile → MySpace either way.
          </p>
        </div>
      )}

      {/* Reassurance copy + escape hatches — users should NOT feel trapped */}
      {showLeaveCard && (
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
      )}

      {showPlayground && <WaitingPlayground />}
    </div>
  );
}

// ─── Step 5: Result ───────────────────────────────────────────────────────────
function ResultStep({ job, onCreateAnother, onBackToWizard }) {
  const navigate = useNavigate();
  // Owner playback uses a fresh signed stream URL (10 min TTL). Sharing
  // points at the public /trailer/:slug page — that page re-signs server-side.
  const [streamUrl, setStreamUrl] = React.useState(null);
  const [thumbUrl, setThumbUrl] = React.useState(job.result_thumbnail_url || null);
  const [format, setFormat] = React.useState('wide'); // wide | vertical
  const [hasVertical, setHasVertical] = React.useState(false);
  const downloadHrefRef = React.useRef(null);
  React.useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const r = await fetch(`${API}/api/photo-trailer/jobs/${job._id || job.job_id}/stream?format=${format}`,
                              { headers: authHeaders() });
        if (!r.ok) return;
        const j = await r.json();
        if (!cancelled) {
          setStreamUrl(j.url);
          if (j.thumbnail_url) setThumbUrl(j.thumbnail_url);
          setHasVertical(!!j.has_vertical);
        }
      } catch {}
    };
    load();
    const timer = setInterval(load, 9 * 60 * 1000);
    return () => { cancelled = true; clearInterval(timer); };
  }, [job._id, job.job_id, format]);

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
    // P0 fix (2026-04-29): the OLD impl did `window.open(j.url, '_blank')`
    // AFTER an async fetch — popup blockers in Chrome / Safari silently kill
    // popups that don't originate from a *synchronous* user gesture, which
    // is exactly why the button "did nothing".
    //
    // Correct pattern (works in Chrome, Edge, Firefox, Safari):
    //   1. Toast "Preparing download…" so the user sees feedback immediately
    //   2. Always fetch a FRESH signed URL on click (handles 10+ min wait
    //      where the previous `streamUrl` may have expired)
    //   3. Trigger via temporary <a href download> element + programmatic
    //      click — counts as a gesture continuation, no popup blocker
    //   4. Safari treats `download` on cross-origin URLs as a hint only:
    //      fall back to window.location assignment which always navigates
    const fmt = format === 'vertical' ? 'vertical' : 'wide';
    const fname = `trailer_${(job._id || job.job_id || 'video').slice(0, 8)}${fmt === 'vertical' ? '_vertical' : ''}.mp4`;
    const prepToast = toast.loading('Preparing download…');
    try {
      const r = await fetch(
        `${API}/api/photo-trailer/jobs/${job._id || job.job_id}/stream?download=true&format=${fmt}`,
        { headers: authHeaders() },
      );
      if (!r.ok) {
        let why = 'Could not start download';
        try {
          const errBody = await r.json();
          why = errBody?.detail?.message || errBody?.detail || errBody?.message || why;
          if (typeof why !== 'string') why = JSON.stringify(why);
        } catch {}
        toast.error(`Download failed · ${why}`, { id: prepToast });
        return;
      }
      const j = await r.json();
      const url = j.url;
      if (!url) {
        toast.error('Download failed · server returned no link', { id: prepToast });
        return;
      }
      // 1. Try the <a download> path (works for same-origin and most CDNs that
      //    set Content-Disposition: attachment — our backend does this).
      try {
        const a = document.createElement('a');
        a.href = url;
        a.download = fname;
        a.rel = 'noopener';
        // Safari needs the anchor to be in the DOM for the click() to fire
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        // Yield once so Safari can pick up the click before we remove the node
        setTimeout(() => { try { document.body.removeChild(a); } catch {} }, 0);
        toast.success('Download started', { id: prepToast });
      } catch (clickErr) {
        // 2. Hard fallback for older Safari / very locked-down WebKit:
        //    just navigate the current tab to the signed URL. Browser will
        //    serve it inline thanks to the backend's Content-Disposition.
        toast.success('Opening file…', { id: prepToast });
        window.location.href = url;
      }
      // Track for the funnel — we now know download conversion is real
      try { trackFunnel('photo_trailer_download_clicked', { meta: { format: fmt } }); } catch {}
    } catch (netErr) {
      toast.error(`Download failed · ${netErr?.message || 'network error'}`, { id: prepToast });
    }
  };

  return (
    <div className="space-y-5" data-testid="trailer-step-result">
      {/* P0 UX escape-path fix (2026-04-29): the result page used to have NO
          way back. Users were trapped if they didn't want to download/share
          right now. Adding a Back (to wizard step 1) button on the left and
          a Home (to /app) button on the right — visible on every viewport,
          no horizontal overflow, doesn't disturb the existing primary CTAs. */}
      <div className="flex items-center justify-between gap-2"
           data-testid="trailer-result-nav">
        <button
          type="button"
          onClick={() => (onBackToWizard ? onBackToWizard() : navigate('/app/photo-trailer'))}
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-white/10 bg-white/[0.03] hover:bg-white/[0.07] text-slate-200 text-sm transition-colors"
          data-testid="trailer-result-back-btn"
          aria-label="Back"
        >
          <ArrowLeft className="w-4 h-4" />
          <span className="hidden sm:inline">Back</span>
        </button>
        <button
          type="button"
          onClick={() => navigate('/app')}
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-white/10 bg-white/[0.03] hover:bg-white/[0.07] text-slate-200 text-sm transition-colors"
          data-testid="trailer-result-home-btn"
          aria-label="Home"
        >
          <Home className="w-4 h-4" />
          <span className="hidden sm:inline">Home</span>
        </button>
      </div>
      <div className="text-center">
        <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto" />
        <h2 className="text-2xl font-bold text-white mt-2">Your trailer is ready</h2>
      </div>
      {/* Format toggle: Wide (16:9) ↔ Vertical (9:16). Vertical hidden if not rendered. */}
      {hasVertical && (
        <div className="flex justify-center" data-testid="trailer-format-toggle">
          <div className="inline-flex p-1 rounded-xl border border-white/10 bg-white/[0.04]">
            <button
              type="button"
              onClick={() => setFormat('wide')}
              className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-colors ${format === 'wide' ? 'bg-violet-600 text-white' : 'text-slate-300 hover:text-white'}`}
              data-testid="trailer-format-wide"
            >
              16:9 Wide
            </button>
            <button
              type="button"
              onClick={() => setFormat('vertical')}
              className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-colors ${format === 'vertical' ? 'bg-fuchsia-600 text-white' : 'text-slate-300 hover:text-white'}`}
              data-testid="trailer-format-vertical"
              title="Reels / Shorts / TikTok / WhatsApp Status"
            >
              9:16 Vertical
            </button>
          </div>
        </div>
      )}
      <video
        key={format}
        src={streamUrl || undefined}
        controls
        poster={thumbUrl || undefined}
        className={`w-full rounded-2xl border border-white/10 bg-black ${format === 'vertical' ? 'max-w-[360px] mx-auto block' : ''}`}
        data-testid="trailer-result-video"
      />
      <div className="flex flex-wrap gap-2">
        <button onClick={handleDownload} className="flex-1 min-w-[120px] py-3 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-sm font-semibold flex items-center justify-center gap-2 transition-colors" data-testid="trailer-download-btn">
          <Download className="w-4 h-4" /> Download {format === 'vertical' ? '9:16' : '16:9'}
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
        {hasVertical
          ? 'Tip: switch to 9:16 for Reels, Shorts, TikTok and WhatsApp Status. One tap.'
          : 'Want it bigger? Share via WhatsApp — your friends get a single tap to watch.'}
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
// ─── Paywall modal ────────────────────────────────────────────────────────────
// Shown when:
//   1. User picks a duration above their plan (client-side guard, instant).
//   2. Backend returns 402 UPGRADE_REQUIRED on /jobs (authoritative).
//   3. Backend returns 429 FREE_QUOTA_EXCEEDED on /jobs.
// Click "Upgrade" → /app/pricing (existing route).
function PaywallModal({ paywall, onClose, onUpgrade }) {
  if (!paywall) return null;
  const tier = (paywall.required_plan || 'PREMIUM').toUpperCase();
  const benefits = tier === 'PREMIUM' ? [
    { icon: Crown, label: 'Up to 90-second cinematic trailers' },
    { icon: Sparkles, label: 'Priority queue — your job runs first' },
    { icon: Film, label: 'Vertical 9:16 + widescreen, every time' },
    { icon: CheckCircle2, label: 'Premium templates (rolling out soon)' },
  ] : [
    { icon: Film, label: 'Up to 60-second cinematic trailers' },
    { icon: Sparkles, label: 'Vertical 9:16 + widescreen' },
    { icon: CheckCircle2, label: 'Unlimited monthly trailers' },
  ];
  const dur = paywall.duration_seconds;
  const headline = paywall.quota_exhausted
    ? 'You\'ve used your free trailers this month'
    : (dur ? `${dur}-second trailers need ${tier}` : `Upgrade to ${tier}`);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={onClose}
      data-testid="trailer-paywall-modal"
    >
      <div
        className="relative w-full max-w-md rounded-3xl border border-fuchsia-500/30 bg-gradient-to-br from-[#13101e] to-[#0a0a10] p-7 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white"
          data-testid="trailer-paywall-close"
          aria-label="Close"
        >
          <X className="w-5 h-5" />
        </button>
        <div className="flex items-center gap-2 mb-2">
          <Crown className="w-6 h-6 text-amber-300" />
          <p className="text-[11px] uppercase tracking-widest text-amber-300 font-bold">{tier}</p>
        </div>
        <h2 className="text-2xl font-bold text-white leading-tight" data-testid="trailer-paywall-headline">
          {headline}
        </h2>
        <p className="text-sm text-slate-400 mt-2">
          {paywall.message || 'Unlock longer, higher-impact trailers and skip the queue.'}
        </p>
        <ul className="mt-5 space-y-2.5">
          {benefits.map((b, i) => (
            <li key={i} className="flex items-start gap-3 text-sm text-slate-200">
              <b.icon className="w-4 h-4 text-fuchsia-300 mt-0.5 shrink-0" />
              <span>{b.label}</span>
            </li>
          ))}
        </ul>
        <div className="mt-6 grid grid-cols-2 gap-2">
          <button
            onClick={onClose}
            className="py-3 rounded-xl border border-white/10 text-white text-sm hover:bg-white/5 transition-colors"
            data-testid="trailer-paywall-not-now"
          >
            Maybe later
          </button>
          <button
            onClick={onUpgrade}
            className="py-3 rounded-xl bg-gradient-to-r from-fuchsia-600 to-amber-500 hover:from-fuchsia-500 hover:to-amber-400 text-white text-sm font-bold transition-all"
            data-testid="trailer-paywall-upgrade-btn"
          >
            Upgrade now
          </button>
        </div>
        <p className="mt-3 text-[11px] text-slate-500 text-center">
          Cancel anytime. Existing trailers unaffected.
        </p>
      </div>
    </div>
  );
}

// ─── Low-Credits Modal — P0 revenue UX ────────────────────────────────────────
// Replaces the old "Could not start trailer" red toast. Shows EXACTLY how many
// credits the user is short by, smart primary CTA based on current plan, and
// an inline "shorter duration that fits your wallet" downgrade option.
//
// Smart CTA logic (founder spec):
//   FREE     → primary = Subscribe Now      (revenue conversion path)
//   PAID     → primary = Buy Credits        (existing user, just needs top-up)
//   PREMIUM  → primary = Contact Support    (shouldn't happen; safety net)
//
// Optional copy variants based on missing_credits magnitude (founder upside):
//   <=5 short → "Subscribe now and get instant access"
//   >20 short → "Best value: Monthly plan"
function LowCreditsModal({ data, onClose, onSubscribe, onBuyCredits, onDowngrade, onContactSupport }) {
  if (!data) return null;
  const required = data.required_credits ?? 0;
  const have = data.current_credits ?? 0;
  const missing = data.missing_credits ?? Math.max(0, required - have);
  const dur = data.duration_seconds;
  const plan = (data.current_plan || 'FREE').toUpperCase();
  const suggested = (data.suggested_durations || []).filter((d) => d !== dur);
  // Variant copy (founder upside spec)
  const teaser = missing <= 5
    ? 'Subscribe now and get instant access — you\'re almost there.'
    : missing > 20
      ? 'Best value: Monthly plan unlocks longer trailers + priority queue.'
      : 'Add credits or subscribe to continue.';

  // Smart primary CTA per plan tier
  let primary;
  if (plan === 'FREE') {
    primary = { label: 'Subscribe Now', action: onSubscribe, testId: 'low-credits-subscribe' };
  } else if (plan === 'PAID') {
    primary = { label: 'Buy Credits', action: onBuyCredits, testId: 'low-credits-buy' };
  } else {
    primary = { label: 'Contact Support', action: onContactSupport, testId: 'low-credits-support' };
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={onClose}
      data-testid="trailer-low-credits-modal"
    >
      <div
        className="relative w-full max-w-md rounded-3xl border border-amber-500/30 bg-gradient-to-br from-[#1a1410] to-[#0a0a10] p-7 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white"
          aria-label="Close"
          data-testid="low-credits-close"
        >
          <X className="w-5 h-5" />
        </button>
        <div className="flex items-center gap-2 mb-2">
          <Sparkles className="w-6 h-6 text-amber-300" />
          <p className="text-[11px] uppercase tracking-widest text-amber-300 font-bold">Low Credits</p>
        </div>
        <h2 className="text-2xl font-bold text-white leading-tight" data-testid="low-credits-headline">
          You need {required} credits to generate this {dur ? `${dur}s ` : ''}trailer.
        </h2>
        <p className="text-sm text-slate-300 mt-2" data-testid="low-credits-balance">
          You currently have <span className="font-semibold text-white">{have}</span> credit{have === 1 ? '' : 's'}.
          You're short by <span className="font-bold text-amber-300">{missing}</span>.
        </p>
        <p className="text-sm text-slate-400 mt-3" data-testid="low-credits-teaser">{teaser}</p>

        {/* Suggested affordable downgrades */}
        {suggested.length > 0 && (
          <div className="mt-5 rounded-xl border border-violet-500/20 bg-violet-500/[0.05] p-3"
               data-testid="low-credits-downgrade-block">
            <p className="text-[11px] uppercase tracking-wider text-violet-300 font-bold mb-2">
              Or try a shorter trailer (free or cheaper)
            </p>
            <div className="flex gap-2">
              {suggested.map((d) => (
                <button
                  key={d}
                  onClick={() => onDowngrade && onDowngrade(d)}
                  className="px-3 py-2 rounded-lg border border-violet-500/30 text-sm text-violet-100 hover:bg-violet-500/10 transition-colors"
                  data-testid={`low-credits-downgrade-${d}`}
                >
                  {d}s
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="mt-6 grid grid-cols-2 gap-2">
          <button
            onClick={primary.action}
            className="col-span-2 py-3.5 rounded-xl bg-gradient-to-r from-amber-500 to-fuchsia-600 hover:from-amber-400 hover:to-fuchsia-500 text-white text-sm font-bold transition-all"
            data-testid={primary.testId}
          >
            {primary.label}
          </button>
          {plan !== 'PREMIUM' && (
            <button
              onClick={plan === 'FREE' ? onBuyCredits : onSubscribe}
              className="col-span-2 py-3 rounded-xl border border-white/10 text-white text-sm hover:bg-white/5 transition-colors"
              data-testid={plan === 'FREE' ? 'low-credits-buy-secondary' : 'low-credits-subscribe-secondary'}
            >
              {plan === 'FREE' ? 'Just buy credits this once' : 'See subscription plans'}
            </button>
          )}
        </div>
        <p className="mt-3 text-[11px] text-slate-500 text-center">
          You won't be charged until you confirm on the next screen.
        </p>
      </div>
    </div>
  );
}


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
  const [duration, setDuration] = useState(20);
  const [busy, setBusy] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [completedJob, setCompletedJob] = useState(null);
  const [failedJob, setFailedJob] = useState(null);
  // Plan & paywall
  const [userPlan, setUserPlan] = useState(null); // {plan, credits, max_duration_seconds, ...}
  const [paywall, setPaywall] = useState(null);   // { current_plan, required_plan, duration_seconds }
  const [lowCredits, setLowCredits] = useState(null); // structured 402 INSUFFICIENT_CREDITS payload

  useEffect(() => {
    try { trackFunnel('photo_trailer_page_viewed', {}); } catch {}
    fetch(`${API}/api/photo-trailer/templates`).then(r => r.json()).then(d => setTemplates(d.templates || [])).catch(() => {});
    // Probe plan once on mount — used for lock icons + duration default.
    fetch(`${API}/api/photo-trailer/me/plan`, { headers: authHeaders() })
      .then(r => r.ok ? r.json() : null)
      .then(p => { if (p) setUserPlan(p); })
      .catch(() => {});
  }, []);

  const credits = useMemo(() => {
    // Mirror backend DURATION_BUCKETS (15/20=0, 45=25, 60=35, 90=60).
    if (duration <= 20) return 0;
    if (duration <= 45) return 25;
    if (duration <= 60) return 35;
    return 60;
  }, [duration]);

  const onGenerate = async () => {
    // Client-side guard: open paywall if duration exceeds the user's max.
    // Server-side enforcement is authoritative — we still send the request
    // and rely on a clean 402 — but this avoids a wasteful round-trip when
    // we already know the answer.
    if (userPlan && userPlan.max_duration_seconds && duration > userPlan.max_duration_seconds) {
      setPaywall({
        current_plan: userPlan.plan,
        required_plan: duration >= 90 ? 'PREMIUM' : 'PAID',
        duration_seconds: duration,
        message: `${duration}s trailers require the ${duration >= 90 ? 'PREMIUM' : 'PAID'} plan.`,
      });
      try { trackFunnel('photo_trailer_paywall_shown', { meta: { duration, current_plan: userPlan.plan } }); } catch {}
      return;
    }
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
        const detail = e.detail;
        // Backend now returns structured 402 for upgrade-required errors
        if (r.status === 402 && detail && typeof detail === 'object' && detail.code === 'UPGRADE_REQUIRED') {
          setPaywall(detail);
          try { trackFunnel('photo_trailer_paywall_shown', { meta: { duration, code: 'UPGRADE_REQUIRED' } }); } catch {}
          setBusy(false);
          return;
        }
        // Free monthly quota exceeded → also a paywall opportunity
        if (r.status === 429 && detail && typeof detail === 'object' && detail.code === 'FREE_QUOTA_EXCEEDED') {
          setPaywall({
            current_plan: 'FREE',
            required_plan: 'PAID',
            message: detail.message,
            quota_exhausted: true,
          });
          setBusy(false);
          return;
        }
        // P0 revenue UX: structured 402 INSUFFICIENT_CREDITS → premium modal,
        // not a generic red toast. Confusion costs conversions.
        if (r.status === 402 && detail && typeof detail === 'object' && detail.code === 'INSUFFICIENT_CREDITS') {
          setLowCredits(detail);
          try {
            trackFunnel('photo_trailer_low_credit_seen', {
              meta: {
                required: detail.required_credits,
                have: detail.current_credits,
                missing: detail.missing_credits,
                duration: detail.duration_seconds,
                plan: detail.current_plan,
              },
            });
          } catch {}
          setBusy(false);
          return;
        }
        toast.error(typeof detail === 'string' ? detail : (detail?.message || 'Could not start trailer'));
        setBusy(false);
        return;
      }
      const j = await r.json();
      setJobId(j.job_id);
      try { trackFunnel('photo_trailer_generation_started', { meta: { job_id: j.job_id, template: templateId, duration } }); } catch {}
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
            <TemplateStep templates={templates} templateId={templateId} setTemplateId={setTemplateId} prompt={prompt} setPrompt={setPrompt} duration={duration} setDuration={setDuration} credits={credits} onBack={() => setStep(2)} onGenerate={onGenerate} busy={busy} userPlan={userPlan?.plan} userCredits={userPlan?.credits} />
          )}
          {step === 4 && jobId && !completedJob && !failedJob && (
            <ProgressStep jobId={jobId} onDone={(j) => { setCompletedJob(j); try { trackFunnel('photo_trailer_generation_completed', { meta: { job_id: j._id || jobId } }); } catch {} setStep(5); }} onFail={(j) => { setFailedJob(j); setStep(5); }} />
          )}
          {step === 5 && completedJob && (
            <ResultStep
              job={completedJob}
              onCreateAnother={() => { setStep(1); setPhotos([]); setConsent(false); setHero(null); setVillain(null); setSupporting([]); setTemplateId(null); setPrompt(''); setSessionId(null); setJobId(null); setCompletedJob(null); setFailedJob(null); }}
              onBackToWizard={() => { setStep(1); setPhotos([]); setConsent(false); setHero(null); setVillain(null); setSupporting([]); setTemplateId(null); setPrompt(''); setSessionId(null); setJobId(null); setCompletedJob(null); setFailedJob(null); }}
            />
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
      <PaywallModal
        paywall={paywall}
        onClose={() => setPaywall(null)}
        onUpgrade={() => {
          try { trackFunnel('photo_trailer_paywall_upgrade_clicked', { meta: { current_plan: paywall?.current_plan, required_plan: paywall?.required_plan } }); } catch {}
          navigate('/app/pricing');
        }}
      />
      <LowCreditsModal
        data={lowCredits}
        onClose={() => setLowCredits(null)}
        onSubscribe={() => {
          try { trackFunnel('photo_trailer_subscribe_clicked', { meta: { missing: lowCredits?.missing_credits, plan: lowCredits?.current_plan } }); } catch {}
          setLowCredits(null);
          navigate('/app/pricing');
        }}
        onBuyCredits={() => {
          try { trackFunnel('photo_trailer_buy_credit_clicked', { meta: { missing: lowCredits?.missing_credits, plan: lowCredits?.current_plan } }); } catch {}
          setLowCredits(null);
          navigate('/app/billing');
        }}
        onDowngrade={(newDur) => {
          try { trackFunnel('photo_trailer_duration_downgraded', { meta: { from: lowCredits?.duration_seconds, to: newDur } }); } catch {}
          setDuration(newDur);
          setLowCredits(null);
          // Re-trigger generate with the cheaper duration on next tick. The user
          // already confirmed intent — one click should "fix and ship".
          setTimeout(() => onGenerate(), 50);
          try { trackFunnel('photo_trailer_credit_fail_recovered', { meta: { recovered_via: 'downgrade', new_duration: newDur } }); } catch {}
        }}
        onContactSupport={() => {
          setLowCredits(null);
          window.location.href = 'mailto:support@visionary-suite.com?subject=Premium%20account%20credit%20issue';
        }}
      />
    </div>
  );
}
