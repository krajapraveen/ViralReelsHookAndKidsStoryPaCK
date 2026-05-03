import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Sparkles, ShieldCheck, Clock, Users, ArrowRight, Play, AlertTriangle } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const ATTR_KEY = 'avatar_attribution';

function readAttribution(search) {
  const p = new URLSearchParams(search);
  return {
    utm_source: p.get('utm_source'),
    utm_campaign: p.get('utm_campaign'),
    referrer_user_id: p.get('ref'),
    landing_path: window.location.pathname,
    landed_at: new Date().toISOString(),
  };
}

function emit(step, meta = {}) {
  let session_id = localStorage.getItem('avatar_session_id');
  if (!session_id) {
    session_id = (crypto?.randomUUID?.() || `s_${Date.now()}_${Math.random().toString(36).slice(2)}`);
    localStorage.setItem('avatar_session_id', session_id);
  }
  fetch(`${API}/api/avatar/funnel/track`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ step, session_id, meta }),
  }).catch(() => {});
}

// Vertical 9:16 demo card
function DemoCard({ video, onPlay50 }) {
  const ref = useRef(null);
  const firedRef = useRef(false);

  const onTimeUpdate = () => {
    if (firedRef.current) return;
    const v = ref.current;
    if (!v || !v.duration) return;
    if (v.currentTime / v.duration >= 0.5) {
      firedRef.current = true;
      onPlay50(video.id);
    }
  };

  return (
    <div
      className="relative rounded-2xl overflow-hidden border border-white/10 bg-white/[0.03] flex flex-col"
      data-testid={`avatar-demo-card-${video.id}`}
    >
      <div className="relative aspect-[9/16] bg-black">
        <video
          ref={ref}
          src={video.url}
          poster={video.poster_url || undefined}
          autoPlay muted loop playsInline
          onTimeUpdate={onTimeUpdate}
          className="w-full h-full object-cover"
          data-testid={`avatar-demo-video-${video.id}`}
        />
        {/* Mandatory disclosure overlay — never optional. */}
        <div
          className="absolute top-2 left-2 px-2 py-1 rounded-md bg-black/70 text-amber-200 text-[10px] uppercase tracking-wider font-bold border border-amber-500/40"
          data-testid={`avatar-demo-label-${video.id}`}
        >
          AI-generated avatar
        </div>
        {video.is_placeholder && (
          <div
            className="absolute bottom-2 left-2 right-2 px-2 py-1 rounded-md bg-rose-950/90 text-rose-200 text-[10px] font-bold border border-rose-500/50"
            data-testid={`avatar-demo-placeholder-${video.id}`}
          >
            DEMO PLACEHOLDER — founder will replace with real recording
          </div>
        )}
      </div>
      <div className="p-3 space-y-1">
        <div className="text-sm font-bold text-white">{video.title}</div>
        <div className="text-xs text-slate-400 flex items-center gap-1.5">
          <Users className="w-3 h-3" /> Used by: <span className="text-slate-200">{video.used_by}</span>
        </div>
        <div className="text-xs text-slate-400 flex items-center gap-1.5">
          <Clock className="w-3 h-3" /> Time saved: <span className="text-slate-200">{video.time_saved}</span>
        </div>
        {video.caption && (
          <div className="text-xs text-slate-500 italic mt-1">"{video.caption}"</div>
        )}
      </div>
    </div>
  );
}

export default function AvatarDemoPage() {
  const nav = useNavigate();
  const loc = useLocation();
  const [cfg, setCfg] = useState(null);
  const [err, setErr] = useState(null);

  // 1. Capture attribution + emit landing view ONCE
  useEffect(() => {
    const attribution = readAttribution(loc.search);
    // Persist (only if not already set; we don't overwrite a previous attribution)
    try {
      const existing = JSON.parse(localStorage.getItem(ATTR_KEY) || 'null');
      if (!existing) localStorage.setItem(ATTR_KEY, JSON.stringify(attribution));
    } catch {
      localStorage.setItem(ATTR_KEY, JSON.stringify(attribution));
    }
    emit('avatar_landing_view', {
      utm_source: attribution.utm_source,
      utm_campaign: attribution.utm_campaign,
      ref: attribution.referrer_user_id,
    });
  }, [loc.search]);

  // 2. Load demo config from backend (admin can swap real URLs in)
  useEffect(() => {
    fetch(`${API}/api/avatar/demo-config`)
      .then(r => r.json())
      .then(setCfg)
      .catch(e => setErr(String(e)));
  }, []);

  const onPlay50 = useCallback((video_id) => {
    emit('avatar_demo_played', { video_id });
  }, []);

  const goSignup = (campaign = 'hero') => {
    const attribution = readAttribution(loc.search);
    const params = new URLSearchParams();
    if (attribution.referrer_user_id) params.set('ref', attribution.referrer_user_id);
    params.set('utm_source', attribution.utm_source || 'avatar_demo');
    params.set('utm_campaign', attribution.utm_campaign || campaign);
    nav(`/signup?${params.toString()}`);
  };

  return (
    <div className="min-h-[100dvh] bg-slate-950 text-white" data-testid="avatar-demo-page">
      {/* Slim header */}
      <header className="sticky top-0 z-30 backdrop-blur-md bg-slate-950/80 border-b border-white/5">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center gap-3">
          <button onClick={() => nav('/')}
                  className="font-bold text-white text-sm" data-testid="avatar-demo-logo">
            Visionary Suite
          </button>
          <div className="ml-auto flex items-center gap-2">
            <button onClick={() => nav('/login')}
                    className="text-sm text-slate-300 hover:text-white"
                    data-testid="avatar-demo-signin">Sign in</button>
            <button onClick={() => goSignup('header')}
                    className="px-3 py-1.5 rounded-lg bg-white text-slate-950 text-sm font-bold"
                    data-testid="avatar-demo-signup-header">Sign up</button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8 sm:py-14 space-y-12">
        {/* Above-the-fold killer copy */}
        <section className="space-y-5 max-w-3xl" data-testid="avatar-demo-hero">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-amber-500/30 bg-amber-500/10 text-amber-200 text-xs">
            <ShieldCheck className="w-3.5 h-3.5" /> Consent-verified · Disclosure-labeled · YouTube + EU AI Act safe
          </div>
          <h1 className="text-3xl sm:text-5xl lg:text-6xl font-bold text-white leading-tight"
              data-testid="avatar-demo-headline">
            {cfg?.above_fold_headline || 'I replaced 2 hours of daily content creation with this AI avatar.'}
          </h1>
          <p className="text-base sm:text-lg text-slate-300 max-w-2xl"
             data-testid="avatar-demo-subhead">
            {cfg?.above_fold_subhead || 'Verified personal AI avatar. Disclosure-labeled. YouTube + Instagram safe.'}
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <button onClick={() => goSignup('hero_above_fold')}
                    className="px-5 py-3 rounded-xl font-bold text-slate-950 bg-white hover:bg-slate-100 inline-flex items-center gap-2"
                    data-testid="avatar-demo-cta-hero">
              <Sparkles className="w-4 h-4" /> Make yours in 60 seconds — try free <ArrowRight className="w-4 h-4" />
            </button>
            <a href="#demos"
               className="px-4 py-3 rounded-xl border border-white/15 text-slate-200 text-sm inline-flex items-center gap-2"
               data-testid="avatar-demo-watch-anchor">
              <Play className="w-4 h-4" /> Watch real examples
            </a>
          </div>
        </section>

        {err && <div className="text-xs text-rose-300">Could not load demos: {err}</div>}

        {/* Demo grid */}
        <section id="demos" className="space-y-5" data-testid="avatar-demo-grid">
          <h2 className="text-xl font-bold text-white">Real examples — every clip clearly labeled AI-generated</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {(cfg?.videos || []).map(v => (
              <DemoCard key={v.id} video={v} onPlay50={onPlay50} />
            ))}
          </div>
        </section>

        {/* How it works */}
        <section className="space-y-4" data-testid="avatar-demo-howitworks">
          <h2 className="text-xl font-bold text-white">How it works</h2>
          <ol className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
            <li className="p-4 rounded-2xl border border-white/10 bg-white/[0.03]">
              <div className="text-2xl font-bold text-violet-400 mb-1">1</div>
              <div className="font-semibold text-white">Record a 5-second consent video.</div>
              <div className="text-xs text-slate-400 mt-1">You read a required phrase. We verify, then admin reviews.</div>
            </li>
            <li className="p-4 rounded-2xl border border-white/10 bg-white/[0.03]">
              <div className="text-2xl font-bold text-violet-400 mb-1">2</div>
              <div className="font-semibold text-white">We train your personal avatar.</div>
              <div className="text-xs text-slate-400 mt-1">Voice + face. Yours only. Never used for anyone else.</div>
            </li>
            <li className="p-4 rounded-2xl border border-white/10 bg-white/[0.03]">
              <div className="text-2xl font-bold text-violet-400 mb-1">3</div>
              <div className="font-semibold text-white">Type a script. Get a video.</div>
              <div className="text-xs text-slate-400 mt-1">Every export carries a visible "AI-generated avatar" label and a forensic watermark.</div>
            </li>
          </ol>
        </section>

        {/* Disclosure-first manifesto */}
        <section className="p-5 rounded-2xl border border-amber-500/30 bg-amber-500/5"
                 data-testid="avatar-demo-disclosure-manifesto">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-300 mt-0.5 shrink-0" />
            <div>
              <h3 className="font-bold text-amber-200 mb-1">Disclosure-first. Always.</h3>
              <p className="text-sm text-amber-100/90 leading-relaxed">
                Every avatar video includes a visible label, a forensic watermark, and machine-readable metadata that complies with YouTube's synthetic-media disclosure rules and the EU AI Act. We refuse impersonation, political persuasion, fraud, medical/legal impersonation, sexual content, and "this is real" deception. If a viewer asks "is this AI?", the answer is on-screen before they finish typing.
              </p>
            </div>
          </div>
        </section>

        {/* Final CTA */}
        <section className="text-center py-8 space-y-4" data-testid="avatar-demo-cta-final">
          <h2 className="text-2xl sm:text-3xl font-bold text-white">Make yours in 60 seconds.</h2>
          <p className="text-sm text-slate-400 max-w-xl mx-auto">3 free generations. Watermarked. No credit card.</p>
          <button onClick={() => goSignup('final_cta')}
                  className="px-6 py-3.5 rounded-xl font-bold text-slate-950 bg-white hover:bg-slate-100 inline-flex items-center gap-2"
                  data-testid="avatar-demo-cta-final-btn">
            <Sparkles className="w-4 h-4" /> Try free — no credit card <ArrowRight className="w-4 h-4" />
          </button>
        </section>
      </main>
    </div>
  );
}
