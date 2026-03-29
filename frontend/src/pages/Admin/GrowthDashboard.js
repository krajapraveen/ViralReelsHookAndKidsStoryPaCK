import React, { useState, useEffect, useCallback } from 'react';
import {
  TrendingUp, Flame, AlertTriangle, Activity, ArrowDown,
  RefreshCcw, Zap, Eye, MousePointerClick, Play, ArrowRight, Share2,
  UserPlus, Clock
} from 'lucide-react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

// ─── BENCHMARK HELPERS ────────────────────────────────────────────
function benchColor(benchmark) {
  if (benchmark === 'strong' || benchmark === 'viral' || benchmark === 'good') return 'text-emerald-400';
  if (benchmark === 'decent') return 'text-amber-400';
  return 'text-red-400';
}
function benchBg(benchmark) {
  if (benchmark === 'strong' || benchmark === 'viral' || benchmark === 'good') return 'bg-emerald-500/10 border-emerald-500/20';
  if (benchmark === 'decent') return 'bg-amber-500/10 border-amber-500/20';
  return 'bg-red-500/10 border-red-500/20';
}

// ─── SECTION 1: GROWTH LOOP HEALTH ────────────────────────────────
function HealthBar({ health }) {
  const metrics = [
    { label: 'Continue Rate', value: health.continue_rate, suffix: '%', benchmark: health.continue_benchmark, icon: ArrowRight },
    { label: 'Share Rate', value: health.share_rate, suffix: '%', benchmark: health.share_benchmark, icon: Share2 },
    { label: 'K-Factor', value: health.k_factor, suffix: '', benchmark: health.k_benchmark, icon: Flame },
  ];
  return (
    <div className="grid grid-cols-3 gap-3" data-testid="health-bar">
      {metrics.map(m => (
        <div key={m.label} className={`rounded-xl border p-4 ${benchBg(m.benchmark)}`}>
          <div className="flex items-center gap-2 mb-2">
            <m.icon className={`w-4 h-4 ${benchColor(m.benchmark)}`} />
            <span className="text-[10px] text-slate-500 uppercase tracking-wider">{m.label}</span>
          </div>
          <p className={`text-2xl font-black font-mono ${benchColor(m.benchmark)}`}>
            {m.value}{m.suffix}
          </p>
          <p className={`text-[10px] mt-1 font-bold uppercase ${benchColor(m.benchmark)}`}>{m.benchmark}</p>
        </div>
      ))}
    </div>
  );
}

// ─── SECTION 2: FUNNEL ────────────────────────────────────────────
function Funnel({ stages }) {
  const maxCount = Math.max(...stages.map(s => s.count), 1);
  const icons = { impression: Eye, click: MousePointerClick, watch_start: Play, watch_complete: Play, continue: ArrowRight, share: Share2 };
  return (
    <div className="space-y-1" data-testid="funnel-section">
      {stages.map((s, i) => {
        const Icon = icons[s.event] || Activity;
        const widthPct = Math.max(8, (s.count / maxCount) * 100);
        const isFirst = i === 0;
        return (
          <div key={s.event}>
            {!isFirst && s.rate !== undefined && (
              <div className="flex items-center gap-1.5 pl-3 py-0.5">
                <ArrowDown className={`w-3 h-3 ${s.rate < 30 ? 'text-red-400' : s.rate < 60 ? 'text-amber-400' : 'text-emerald-400'}`} />
                <span className={`text-[11px] font-mono font-bold ${s.rate < 30 ? 'text-red-400' : s.rate < 60 ? 'text-amber-400' : 'text-emerald-400'}`}>
                  {s.rate}%
                </span>
              </div>
            )}
            <div className="flex items-center gap-3">
              <div className="w-28 flex items-center gap-1.5 shrink-0">
                <Icon className="w-3.5 h-3.5 text-slate-500" />
                <span className="text-xs text-slate-400 truncate">{s.stage}</span>
              </div>
              <div className="flex-1 h-7 bg-slate-800/50 rounded-md overflow-hidden relative">
                <div
                  className={`h-full rounded-md transition-all ${isFirst ? 'bg-indigo-500/60' : s.rate && s.rate < 20 ? 'bg-red-500/60' : s.rate && s.rate < 50 ? 'bg-amber-500/60' : 'bg-emerald-500/60'}`}
                  style={{ width: `${widthPct}%` }}
                />
                <span className="absolute right-2 top-1/2 -translate-y-1/2 text-xs font-mono font-bold text-white/80">
                  {s.count.toLocaleString()}
                </span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── SECTION 3: DROP-OFF ──────────────────────────────────────────
function DropoffAnalysis({ dropoffs, worst }) {
  return (
    <div className="space-y-2" data-testid="dropoff-section">
      {dropoffs.map(d => {
        const isWorst = d.from === worst.from && d.to === worst.to;
        return (
          <div key={`${d.from}-${d.to}`} className={`flex items-center justify-between px-3 py-2 rounded-lg ${isWorst ? 'bg-red-500/10 border border-red-500/20' : 'bg-slate-800/30'}`}>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 capitalize">{d.from.replace('_', ' ')}</span>
              <ArrowRight className="w-3 h-3 text-slate-600" />
              <span className="text-xs text-slate-400 capitalize">{d.to.replace('_', ' ')}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-sm font-mono font-bold ${d.drop_pct > 70 ? 'text-red-400' : d.drop_pct > 40 ? 'text-amber-400' : 'text-emerald-400'}`}>
                {d.drop_pct}%
              </span>
              {isWorst && <AlertTriangle className="w-3.5 h-3.5 text-red-400" />}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── SECTION 4: TOP STORIES ───────────────────────────────────────
function TopStories({ stories }) {
  if (!stories.length) return <p className="text-xs text-slate-500">No story data yet</p>;
  return (
    <div className="overflow-x-auto" data-testid="top-stories-section">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-slate-500 border-b border-slate-800">
            <th className="text-left py-2 font-medium">Title</th>
            <th className="text-right py-2 font-medium">Continue%</th>
            <th className="text-right py-2 font-medium">Share%</th>
            <th className="text-right py-2 font-medium">Completes</th>
          </tr>
        </thead>
        <tbody>
          {stories.map((s, i) => (
            <tr key={s.story_id} className="border-b border-slate-800/50 hover:bg-slate-800/30">
              <td className="py-2 text-slate-300 max-w-[200px] truncate">{i + 1}. {s.title}</td>
              <td className={`py-2 text-right font-mono font-bold ${s.continue_pct >= 25 ? 'text-emerald-400' : s.continue_pct >= 15 ? 'text-amber-400' : 'text-red-400'}`}>
                {s.continue_pct}%
              </td>
              <td className={`py-2 text-right font-mono ${s.share_pct >= 10 ? 'text-emerald-400' : 'text-slate-400'}`}>{s.share_pct}%</td>
              <td className="py-2 text-right font-mono text-slate-400">{s.completions}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── SECTION 5: HOOK A/B ─────────────────────────────────────────
function HookPerformance({ hooks }) {
  if (!hooks.length) return <p className="text-xs text-slate-500">No hook A/B data yet. Pass <code>hook_variant</code> in event meta.</p>;
  return (
    <div className="overflow-x-auto" data-testid="hook-ab-section">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-slate-500 border-b border-slate-800">
            <th className="text-left py-2 font-medium">Hook Variant</th>
            <th className="text-right py-2 font-medium">CTR</th>
            <th className="text-right py-2 font-medium">Continue%</th>
          </tr>
        </thead>
        <tbody>
          {hooks.map(h => (
            <tr key={h.hook} className="border-b border-slate-800/50 hover:bg-slate-800/30">
              <td className="py-2 text-slate-300 max-w-[200px] truncate">"{h.hook}"</td>
              <td className="py-2 text-right font-mono text-slate-400">{h.ctr}%</td>
              <td className={`py-2 text-right font-mono font-bold ${h.continue_pct >= 30 ? 'text-emerald-400' : h.continue_pct >= 15 ? 'text-amber-400' : 'text-red-400'}`}>
                {h.continue_pct}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── SECTION 6: CATEGORIES ────────────────────────────────────────
function CategoryPerformance({ categories }) {
  if (!categories.length) return <p className="text-xs text-slate-500">No category data yet. Pass <code>category</code> in event meta.</p>;
  return (
    <div className="space-y-2" data-testid="category-section">
      {categories.map(c => (
        <div key={c.category} className="flex items-center justify-between px-3 py-2 bg-slate-800/30 rounded-lg">
          <span className="text-xs text-slate-300 capitalize">{c.category}</span>
          <div className="flex items-center gap-4">
            <span className="text-xs text-slate-500">Continue: <span className={`font-mono font-bold ${c.continue_pct >= 25 ? 'text-emerald-400' : 'text-amber-400'}`}>{c.continue_pct}%</span></span>
            <span className="text-xs text-slate-500">Share: <span className="font-mono text-slate-400">{c.share_pct}%</span></span>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── SECTION 7: LIVE FEED ─────────────────────────────────────────
function LiveFeed({ feed }) {
  const eventLabels = { continue: 'continued', share: 'shared', watch_complete: 'finished watching', signup_from_share: 'signed up from' };
  if (!feed.length) return <p className="text-xs text-slate-500">No recent activity</p>;
  return (
    <div className="space-y-1.5 max-h-60 overflow-y-auto" data-testid="live-feed-section">
      {feed.map((f, i) => (
        <div key={i} className="flex items-center gap-2 px-3 py-1.5 bg-slate-800/20 rounded-lg text-xs">
          <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${f.event === 'continue' ? 'bg-violet-400' : f.event === 'share' ? 'bg-blue-400' : f.event === 'signup_from_share' ? 'bg-emerald-400' : 'bg-slate-400'}`} />
          <span className="text-slate-400">
            User {f.location ? `in ${f.location} ` : ''}{eventLabels[f.event] || f.event} <span className="text-slate-300 font-medium">"{f.story_title}"</span>
          </span>
          <span className="ml-auto text-[10px] text-slate-600 flex-shrink-0">
            {f.timestamp ? new Date(f.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
          </span>
        </div>
      ))}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// MAIN DASHBOARD
// ═══════════════════════════════════════════════════════════════════
export default function GrowthDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(7);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem('token');
      const res = await axios.get(`${API}/api/growth/loop-dashboard?days=${days}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setData(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load metrics');
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCcw className="w-5 h-5 text-slate-500 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 text-center">
        <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
        <p className="text-sm text-red-400">{error}</p>
        <button onClick={fetchData} className="mt-3 text-xs text-slate-400 hover:text-white">Retry</button>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-6 max-w-5xl" data-testid="growth-loop-dashboard">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-black text-white tracking-tight">Addiction Loop Metrics</h1>
          <p className="text-xs text-slate-500 mt-0.5">Track behavior, not traffic</p>
        </div>
        <div className="flex items-center gap-2">
          {[7, 14, 30].map(d => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${days === d ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30' : 'text-slate-500 hover:text-slate-300'}`}
              data-testid={`period-${d}d`}
            >
              {d}d
            </button>
          ))}
          <button onClick={fetchData} className="p-1.5 rounded-lg text-slate-500 hover:text-white hover:bg-slate-800" data-testid="refresh-btn">
            <RefreshCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Section 1: Growth Loop Health */}
      <HealthBar health={data.health} />

      {/* Section 2 + 3 side by side */}
      <div className="grid lg:grid-cols-2 gap-4">
        <div className="bg-slate-900/40 border border-white/[0.06] rounded-xl p-4">
          <h2 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-indigo-400" /> Funnel
          </h2>
          <Funnel stages={data.funnel.stages} />
        </div>
        <div className="bg-slate-900/40 border border-white/[0.06] rounded-xl p-4">
          <h2 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" /> Drop-off Analysis
          </h2>
          <DropoffAnalysis dropoffs={data.dropoffs} worst={data.worst_dropoff} />
          {data.worst_dropoff?.from && (
            <div className="mt-3 p-2 bg-red-500/5 border border-red-500/10 rounded-lg">
              <p className="text-[10px] text-red-400">
                Biggest loss: <span className="font-bold capitalize">{data.worst_dropoff.from.replace('_', ' ')} → {data.worst_dropoff.to.replace('_', ' ')}</span> ({data.worst_dropoff.drop_pct}% drop, {data.worst_dropoff.lost} users lost)
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Section 4: Top Stories */}
      <div className="bg-slate-900/40 border border-white/[0.06] rounded-xl p-4">
        <h2 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
          <Zap className="w-4 h-4 text-violet-400" /> Top Performing Stories
        </h2>
        <TopStories stories={data.top_stories} />
      </div>

      {/* Section 5 + 6 side by side */}
      <div className="grid lg:grid-cols-2 gap-4">
        <div className="bg-slate-900/40 border border-white/[0.06] rounded-xl p-4">
          <h2 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
            <Activity className="w-4 h-4 text-blue-400" /> Hook A/B Performance
          </h2>
          <HookPerformance hooks={data.hooks} />
        </div>
        <div className="bg-slate-900/40 border border-white/[0.06] rounded-xl p-4">
          <h2 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
            <Eye className="w-4 h-4 text-teal-400" /> Category Performance
          </h2>
          <CategoryPerformance categories={data.categories} />
        </div>
      </div>

      {/* Section 7: Live Feed */}
      <div className="bg-slate-900/40 border border-white/[0.06] rounded-xl p-4">
        <h2 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
          <Clock className="w-4 h-4 text-emerald-400" /> Real-Time Activity
        </h2>
        <LiveFeed feed={data.live_feed} />
      </div>

      {/* Raw Numbers Footer */}
      <div className="grid grid-cols-4 sm:grid-cols-7 gap-2">
        {Object.entries(data.raw).map(([key, val]) => (
          <div key={key} className="bg-slate-900/30 rounded-lg p-2 text-center">
            <p className="text-[9px] text-slate-600 uppercase">{key.replace(/_/g, ' ')}</p>
            <p className="text-sm font-mono font-bold text-slate-300">{val.toLocaleString()}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
