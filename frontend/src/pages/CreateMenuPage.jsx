import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  ArrowLeft, Zap, Film, BookOpen, Camera, Palette, ImageIcon,
  Megaphone, Lightbulb, Play, Star, User, UserCheck,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

// icon registry — mirrors Dashboard.ICON_MAP so server-provided icon names
// resolve identically.
const ICONS = {
  Film, BookOpen, User, UserCheck, Play, Camera, Palette,
  Star, ImageIcon, Megaphone, Lightbulb,
};

// Feature → category / outcome / time / CTA (copy-only layer)
const META = {
  'avatar':              { group: 'identity',         outcome: 'Your AI version speaks for you',               time: '~60 sec video',    cta: 'Create Now' },
  'story-video-studio':  { group: 'video',            outcome: 'Ideas become cinematic videos',                time: '~2 min video',     cta: 'Create Now' },
  'reels':               { group: 'video',            outcome: 'Short-form reels that ship daily',             time: '~30 sec reel',     cta: 'Create Now' },
  'brand-story-builder': { group: 'video',            outcome: 'Cinematic brand films',                        time: '~90 sec video',    cta: 'Create Now' },
  'story-series':        { group: 'stories',          outcome: 'Multi-episode sagas with memory',              time: '~5 min series',    cta: 'Create Now' },
  'bedtime-stories':     { group: 'stories',          outcome: 'Narrated sleep tales with visuals',            time: '~3 min story',     cta: 'Create Now' },
  'characters':          { group: 'stories',          outcome: 'Characters that remember their world',         time: '~1 min setup',     cta: 'Create Now' },
  'comic-storybook':     { group: 'visual',           outcome: 'Panel-by-panel illustrated stories',           time: '~2 min comic',     cta: 'Create Now' },
  'photo-to-comic':      { group: 'visual',           outcome: 'Your photo, as a comic panel',                 time: '~30 sec convert',  cta: 'Create Now' },
  'gif-maker':           { group: 'visual',           outcome: 'Photo-to-reaction GIF in seconds',             time: '~15 sec GIF',      cta: 'Create Now' },
  'daily-viral-ideas':   { group: 'growth',           outcome: "What's trending — pick and create",           time: '~10 sec pick',     cta: 'Try This'   },
  'photo-trailer':       { group: 'video',            outcome: 'Upload photos → 20-60s AI trailer',            time: '~45 sec trailer',  cta: 'Create Now' },
};

const GROUPS = [
  { id: 'video',    label: 'Video Creation',  icon: '🎥', testid: 'create-group-video' },
  { id: 'stories',  label: 'Story Engines',   icon: '📚', testid: 'create-group-stories' },
  { id: 'visual',   label: 'Visual Creation', icon: '🎨', testid: 'create-group-visual' },
  { id: 'growth',   label: 'Growth',          icon: '🧠', testid: 'create-group-growth' },
  { id: 'identity', label: 'Identity',        icon: '🧍', testid: 'create-group-identity' },
];

function FeatureCard({ feature }) {
  const nav = useNavigate();
  const Icon = ICONS[feature.icon] || Zap;
  const meta = META[feature.key] || { outcome: feature.desc || '', time: null, cta: 'Create Now' };
  const click = () => {
    // Lightweight analytics: feature_click_rate is the only new signal
    // this phase cares about. Uses existing /api/metrics/track.
    try {
      const t = localStorage.getItem('token');
      fetch(`${API}/api/metrics/track`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: t ? `Bearer ${t}` : '' },
        body: JSON.stringify({ event: 'feature_click', meta: { feature_key: feature.key, source: 'create_tab' } }),
      }).catch(() => {});
    } catch {}
    nav(feature.path, { state: { freshSession: true } });
  };

  return (
    <button onClick={click}
      className="group w-full rounded-2xl border border-white/[0.08] bg-[#121218] p-4 text-left hover:border-white/15 transition-all"
      data-testid={`create-feature-${feature.key}`}>
      <div className="flex items-start gap-3">
        <div className="h-11 w-11 shrink-0 rounded-xl bg-gradient-to-br from-[#6C5CE7]/25 to-[#00C2FF]/25 text-white border border-white/10 flex items-center justify-center">
          <Icon className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 flex-wrap">
            <h3 className="text-white text-base font-bold tracking-tight">{feature.name}</h3>
            {feature.badge && (
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-300 border border-violet-500/30">
                {feature.badge}
              </span>
            )}
          </div>
          <p className="mt-1 text-white/60 text-xs leading-relaxed line-clamp-2"
             data-testid={`create-feature-outcome-${feature.key}`}>{meta.outcome}</p>
          <div className="mt-2 flex items-center justify-between gap-2">
            {meta.time && (
              <span className="text-[10px] uppercase tracking-wider font-semibold text-white/40"
                    data-testid={`create-feature-time-${feature.key}`}>{meta.time}</span>
            )}
            <span className="ml-auto inline-flex items-center gap-1 text-xs font-bold text-violet-300 group-hover:text-violet-200"
                  data-testid={`create-feature-cta-${feature.key}`}>
              {meta.cta} →
            </span>
          </div>
        </div>
      </div>
    </button>
  );
}

export default function CreateMenuPage() {
  const nav = useNavigate();
  const [features, setFeatures] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) { nav('/login'); return; }
    axios.get(`${API}/api/engagement/story-feed`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => setFeatures(r.data?.features || []))
      .catch(() => setFeatures([]))
      .finally(() => setLoading(false));
  }, [nav]);

  const grouped = useMemo(() => {
    const m = {};
    for (const f of features) {
      const gid = META[f.key]?.group || 'video';
      (m[gid] = m[gid] || []).push(f);
    }
    return m;
  }, [features]);

  return (
    <div className="min-h-[100dvh] bg-[#0B0B0F] text-white pb-24" data-testid="create-menu-page">
      <header className="sticky top-0 z-30 backdrop-blur-md bg-[#0B0B0F]/90 border-b border-white/5">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center gap-3">
          <button onClick={() => nav(-1)}
                  className="text-slate-300 hover:text-white flex items-center gap-1.5 text-sm"
                  data-testid="create-menu-back">
            <ArrowLeft className="w-4 h-4" /> Back
          </button>
          <h1 className="ml-1 text-base sm:text-lg font-bold text-white flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-400" /> Create
          </h1>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 pt-4 pb-8 space-y-8">
        {loading && (
          <div className="text-center py-10 text-white/40 text-sm" data-testid="create-menu-loading">
            Loading tools…
          </div>
        )}
        {!loading && features.length === 0 && (
          <div className="text-center py-10 text-white/40 text-sm" data-testid="create-menu-empty">
            No tools available. Please refresh.
          </div>
        )}
        {!loading && GROUPS.map(g => {
          const items = grouped[g.id] || [];
          if (items.length === 0) return null;
          return (
            <section key={g.id} className="space-y-3" data-testid={g.testid}>
              <h2 className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] font-bold text-white/50">
                <span aria-hidden="true">{g.icon}</span> {g.label}
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {items.map(f => <FeatureCard key={f.key} feature={f} />)}
              </div>
            </section>
          );
        })}
      </main>
    </div>
  );
}
