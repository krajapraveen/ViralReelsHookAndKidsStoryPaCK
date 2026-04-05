import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '../components/ui/button';
import api from '../utils/api';
import { toast } from 'sonner';
import {
  TrendingUp, GitBranch, Share2, Users, BarChart3,
  RefreshCw, ArrowDown, Zap, Eye, Clock, AlertTriangle,
  ChevronRight, Target
} from 'lucide-react';

// ─── Metric Card ─────────────────────────────────────────────────────────────

function MetricCard({ icon: Icon, label, value, subtext, color, interpretation }) {
  const colors = {
    violet: 'border-violet-500/20 bg-violet-500/[0.04]',
    emerald: 'border-emerald-500/20 bg-emerald-500/[0.04]',
    amber: 'border-amber-500/20 bg-amber-500/[0.04]',
    rose: 'border-rose-500/20 bg-rose-500/[0.04]',
    sky: 'border-sky-500/20 bg-sky-500/[0.04]',
  };
  const iconColors = {
    violet: 'text-violet-400',
    emerald: 'text-emerald-400',
    amber: 'text-amber-400',
    rose: 'text-rose-400',
    sky: 'text-sky-400',
  };
  const interpColors = {
    'strong': 'text-emerald-400 bg-emerald-500/10',
    'decent': 'text-amber-400 bg-amber-500/10',
    'needs work': 'text-rose-400 bg-rose-500/10',
    'viral potential': 'text-emerald-400 bg-emerald-500/10',
    'okay': 'text-amber-400 bg-amber-500/10',
    'needs seeding': 'text-rose-400 bg-rose-500/10',
  };

  return (
    <div className={`rounded-xl border p-4 ${colors[color]}`} data-testid={`metric-${label.toLowerCase().replace(/\s+/g, '-')}`}>
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`w-4 h-4 ${iconColors[color]}`} />
        <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">{label}</span>
      </div>
      <div className="text-2xl font-black text-white mb-1">{value}</div>
      {interpretation && (
        <span className={`text-[10px] px-2 py-0.5 rounded-full font-mono font-bold ${interpColors[interpretation] || 'text-slate-400 bg-white/5'}`}>
          {interpretation}
        </span>
      )}
      {subtext && <p className="text-[10px] text-slate-500 mt-1">{subtext}</p>}
    </div>
  );
}

// ─── Funnel Step ─────────────────────────────────────────────────────────────

function FunnelStep({ stage, count, rate, isLast, prevCount }) {
  const dropoff = prevCount > 0 ? Math.round((1 - count / prevCount) * 100) : 0;
  const isDangerous = dropoff > 70;

  return (
    <div className="flex items-center gap-3">
      <div className="flex-1">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-medium text-slate-300">{stage}</span>
          <span className="text-xs text-slate-400 font-mono">{count}</span>
        </div>
        <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-700 ${isDangerous ? 'bg-rose-500' : 'bg-violet-500'}`}
            style={{ width: `${Math.min(parseInt(rate) || 0, 100)}%` }}
          />
        </div>
      </div>
      {!isLast && prevCount > 0 && count < prevCount && (
        <div className={`flex items-center gap-0.5 text-[10px] ${isDangerous ? 'text-rose-400' : 'text-slate-500'}`}>
          <ArrowDown className="w-2.5 h-2.5" /> {dropoff}%
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════

export default function GrowthDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [hours, setHours] = useState(72);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get(`/api/admin/metrics/growth?hours=${hours}`);
      setData(res.data);
    } catch (err) {
      toast.error('Failed to load growth metrics');
    } finally {
      setLoading(false);
    }
  }, [hours]);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center py-16">
        <RefreshCw className="w-6 h-6 animate-spin text-violet-500" />
      </div>
    );
  }

  if (data?.empty_state) {
    return (
      <div className="text-center py-16" data-testid="growth-empty">
        <Target className="w-12 h-12 text-slate-500 mx-auto mb-4" />
        <h3 className="text-lg font-bold text-white mb-2">No Growth Data Yet</h3>
        <p className="text-sm text-slate-400 max-w-md mx-auto">{data.empty_message}</p>
      </div>
    );
  }

  const cr = data?.continuation_rate;
  const bps = data?.branches_per_story;
  const funnel = data?.share_funnel;
  const fs = data?.first_session;
  const ab = data?.ab_test;

  return (
    <div className="space-y-6" data-testid="growth-dashboard">
      {/* Header + Period selector */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <TrendingUp className="w-5 h-5 text-violet-400" />
          <h2 className="text-base font-semibold text-white">Growth Validation</h2>
          <span className="text-[10px] text-slate-500 bg-slate-800 px-2 py-0.5 rounded-full font-mono">DATA MODE</span>
        </div>
        <div className="flex items-center gap-2">
          {[24, 72, 168, 720].map(h => (
            <button
              key={h}
              onClick={() => setHours(h)}
              className={`text-[10px] px-2 py-1 rounded font-mono transition-colors ${
                hours === h ? 'bg-violet-600 text-white' : 'text-slate-500 hover:text-white'
              }`}
            >
              {h <= 24 ? '24h' : h <= 72 ? '3d' : h <= 168 ? '7d' : '30d'}
            </button>
          ))}
          <Button variant="outline" size="sm" onClick={fetchData} className="h-7 text-xs border-slate-700 text-slate-400" data-testid="refresh-growth">
            <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* ── KEY METRICS ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard
          icon={GitBranch}
          label="Continuation Rate"
          value={cr?.label || '0%'}
          color="violet"
          interpretation={cr?.interpretation}
          subtext={`${cr?.total_forks || 0} forks / ${cr?.total_views || 0} views`}
        />
        <MetricCard
          icon={Zap}
          label="Branches / Story"
          value={bps?.value || 0}
          color="emerald"
          interpretation={bps?.interpretation}
          subtext={`${bps?.total_stories || 0} stories tracked`}
        />
        <MetricCard
          icon={Eye}
          label="Landing Conversion"
          value={fs?.conversion || '0%'}
          color="amber"
          subtext={`${fs?.cta_clicks || 0} clicks / ${fs?.impressions || 0} visits`}
        />
        <MetricCard
          icon={Share2}
          label="Share Rate"
          value={funnel?.rates?.share_rate || '0%'}
          color="sky"
          subtext={`${funnel?.shared || 0} shares / ${funnel?.created || 0} created`}
        />
      </div>

      {/* ── FUNNEL DROP-OFF ── */}
      <div className="bg-slate-900/40 border border-slate-700/40 rounded-xl p-4 space-y-3" data-testid="funnel-dropoff">
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
          <BarChart3 className="w-3.5 h-3.5" /> Share Funnel Drop-off
        </h3>
        {data?.funnel_dropoff?.map((step, i) => (
          <FunnelStep
            key={step.stage}
            stage={step.stage}
            count={step.count}
            rate={step.rate}
            isLast={i === data.funnel_dropoff.length - 1}
            prevCount={i > 0 ? data.funnel_dropoff[i - 1].count : step.count}
          />
        ))}
      </div>

      {/* ── A/B TEST RESULTS ── */}
      {ab && Object.keys(ab).length > 0 && (
        <div className="bg-slate-900/40 border border-slate-700/40 rounded-xl p-4" data-testid="ab-test-results">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">A/B Hero Test</h3>
          <div className="grid grid-cols-3 gap-3">
            {Object.entries(ab).sort((a, b) => (b[1].conversion || 0) - (a[1].conversion || 0)).map(([variant, stats]) => {
              const isWinner = Object.values(ab).every(s => stats.conversion >= s.conversion);
              return (
                <div
                  key={variant}
                  className={`rounded-lg border p-3 text-center ${
                    isWinner ? 'border-emerald-500/30 bg-emerald-500/[0.04]' : 'border-slate-700/40'
                  }`}
                >
                  <div className="text-lg font-black text-white">Variant {variant}</div>
                  <div className={`text-2xl font-black mt-1 ${isWinner ? 'text-emerald-400' : 'text-slate-300'}`}>
                    {stats.conversion}%
                  </div>
                  <div className="text-[10px] text-slate-500 mt-1 font-mono">
                    {stats.clicks} / {stats.impressions}
                  </div>
                  {isWinner && stats.impressions > 5 && (
                    <span className="text-[9px] text-emerald-400 mt-1 inline-block">LEADER</span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── TOP STORIES + WINNING HOOKS ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {data?.top_stories?.length > 0 && (
          <div className="bg-slate-900/40 border border-slate-700/40 rounded-xl p-4" data-testid="top-stories">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Top Stories (by forks)</h3>
            <div className="space-y-2">
              {data.top_stories.map((s, i) => (
                <div key={s.id || i} className="flex items-center justify-between py-1.5 border-b border-slate-800 last:border-0">
                  <div>
                    <span className="text-sm text-white font-medium line-clamp-1">{s.title || 'Untitled'}</span>
                    {s.hookText && <p className="text-[10px] text-violet-300 italic line-clamp-1">"{s.hookText}"</p>}
                  </div>
                  <div className="flex items-center gap-2 text-[10px] text-slate-500 font-mono flex-shrink-0 ml-2">
                    <span className="flex items-center gap-0.5"><GitBranch className="w-2.5 h-2.5" /> {s.forks || 0}</span>
                    <span className="flex items-center gap-0.5"><Eye className="w-2.5 h-2.5" /> {s.views || 0}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {data?.winning_hooks?.length > 0 && (
          <div className="bg-slate-900/40 border border-slate-700/40 rounded-xl p-4" data-testid="winning-hooks">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Winning Hooks (highest cont. rate)</h3>
            <div className="space-y-2">
              {data.winning_hooks.map((h, i) => (
                <div key={i} className="py-1.5 border-b border-slate-800 last:border-0">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-white font-medium line-clamp-1">{h.title || 'Untitled'}</span>
                    <span className="text-xs text-emerald-400 font-mono font-bold flex-shrink-0 ml-2">{h.cont_rate}%</span>
                  </div>
                  {h.hookText && <p className="text-[10px] text-violet-300 italic line-clamp-1">"{h.hookText}"</p>}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
