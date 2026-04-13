import React, { useState, useEffect } from 'react';
import { ArrowLeft, TrendingUp, Eye, Zap, BarChart2, Users, Clock, ChevronDown } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../utils/api';

/**
 * Conversion Analytics Dashboard — Admin only.
 * Decision-grade metrics. No vanity charts.
 * Every number traces to tracked events or job state transitions.
 */
export default function ConversionDashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('7d');

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const res = await api.get(`/api/analytics/conversion-dashboard?period=${period}`);
        if (res.data?.success) setData(res.data);
      } catch {}
      setLoading(false);
    })();
  }, [period]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <p className="text-white/40 text-sm">Failed to load analytics. Admin access required.</p>
      </div>
    );
  }

  const { metrics, funnel, cta_breakdown, source_section_breakdown, job_stats, session_stats } = data;

  return (
    <div className="min-h-screen bg-slate-950 text-white" data-testid="conversion-dashboard">
      {/* Header */}
      <div className="sticky top-0 z-40 bg-slate-950/95 backdrop-blur-md border-b border-white/5">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate(-1)} className="text-white/40 hover:text-white">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <h1 className="text-sm font-bold text-white">Conversion Analytics</h1>
          </div>
          <div className="flex items-center gap-2">
            {['24h', '7d', '30d'].map(p => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  period === p ? 'bg-violet-600 text-white' : 'bg-white/5 text-white/40 hover:text-white/70'
                }`}
                data-testid={`period-${p}`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-6 space-y-8">

        {/* ═══ CORE METRICS — The numbers that matter ═══ */}
        <section data-testid="core-metrics">
          <h2 className="text-xs font-bold text-white/30 uppercase tracking-wider mb-4">Core Conversion</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <MetricCard
              label="Spectator → Player"
              value={`${metrics.spectator_to_player_pct}%`}
              formula={metrics.spectator_to_player_pct_formula}
              color={metrics.spectator_to_player_pct > 10 ? 'emerald' : metrics.spectator_to_player_pct > 5 ? 'amber' : 'rose'}
              icon={<Users className="w-4 h-4" />}
              testId="metric-spectator-to-player"
            />
            <MetricCard
              label="Watch Start Rate"
              value={`${metrics.watch_start_rate}%`}
              formula={metrics.watch_start_rate_formula}
              color={metrics.watch_start_rate > 50 ? 'emerald' : 'amber'}
              icon={<Eye className="w-4 h-4" />}
              testId="metric-watch-start"
            />
            <MetricCard
              label="Watch 50% Complete"
              value={`${metrics.watch_completion_50_pct}%`}
              color={metrics.watch_completion_50_pct > 40 ? 'emerald' : 'amber'}
              icon={<TrendingUp className="w-4 h-4" />}
              testId="metric-watch-50"
            />
            <MetricCard
              label="Watch 100% Complete"
              value={`${metrics.watch_completion_100_pct}%`}
              color={metrics.watch_completion_100_pct > 30 ? 'emerald' : 'amber'}
              icon={<TrendingUp className="w-4 h-4" />}
              testId="metric-watch-100"
            />
          </div>
        </section>

        {/* ═══ CTA PERFORMANCE ═══ */}
        <section data-testid="cta-metrics">
          <h2 className="text-xs font-bold text-white/30 uppercase tracking-wider mb-4">CTA Performance</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <MetricCard
              label="Make Your Version CTR"
              value={`${metrics.make_your_version_ctr}%`}
              color="violet"
              icon={<Zap className="w-4 h-4" />}
              testId="metric-myv-ctr"
            />
            <MetricCard
              label="Quick Shot CTR"
              value={`${metrics.quick_shot_ctr}%`}
              color="rose"
              icon={<Zap className="w-4 h-4" />}
              testId="metric-qs-ctr"
            />
            <MetricCard
              label="Next Episode CTR"
              value={`${metrics.next_episode_ctr}%`}
              color="blue"
              icon={<Zap className="w-4 h-4" />}
              testId="metric-next-ep-ctr"
            />
            <MetricCard
              label="Stories / Session"
              value={metrics.stories_per_session}
              formula={metrics.stories_per_session_formula}
              color="white"
              icon={<BarChart2 className="w-4 h-4" />}
              testId="metric-stories-per-session"
            />
            <MetricCard
              label="2nd Action Rate"
              value={`${metrics.second_action_rate}%`}
              formula={metrics.second_action_rate_formula}
              color={metrics.second_action_verdict === 'strong' ? 'emerald' : metrics.second_action_verdict === 'potential' ? 'amber' : 'rose'}
              icon={<TrendingUp className="w-4 h-4" />}
              testId="metric-second-action"
            />
          </div>
        </section>

        {/* ═══ QUEUE HEALTH ═══ */}
        <section data-testid="queue-metrics">
          <h2 className="text-xs font-bold text-white/30 uppercase tracking-wider mb-4">Queue Health</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <MetricCard
              label="Queue Rate"
              value={`${metrics.queue_rate}%`}
              formula={metrics.queue_rate_formula}
              color={metrics.queue_rate > 30 ? 'rose' : 'emerald'}
              icon={<Clock className="w-4 h-4" />}
              testId="metric-queue-rate"
            />
            <MetricCard
              label="Queue → Complete"
              value={`${metrics.queue_to_complete_rate}%`}
              formula={metrics.queue_to_complete_formula}
              color={metrics.queue_to_complete_rate > 70 ? 'emerald' : 'amber'}
              icon={<TrendingUp className="w-4 h-4" />}
              testId="metric-queue-complete"
            />
            <MetricCard
              label="Total Created"
              value={job_stats.total_created}
              color="white"
              icon={<BarChart2 className="w-4 h-4" />}
              testId="metric-total-created"
            />
            <MetricCard
              label="Total Failed"
              value={job_stats.total_failed}
              color={job_stats.total_failed > 10 ? 'rose' : 'white'}
              icon={<BarChart2 className="w-4 h-4" />}
              testId="metric-total-failed"
            />
          </div>
        </section>

        {/* ═══ FUNNEL ═══ */}
        <section data-testid="funnel-section">
          <h2 className="text-xs font-bold text-white/30 uppercase tracking-wider mb-4">Conversion Funnel</h2>

          {/* Attribution warnings */}
          {data.attribution_warnings?.length > 0 && (
            <div className="mb-3 bg-amber-500/5 border border-amber-500/15 rounded-lg p-3" data-testid="attribution-warnings">
              {data.attribution_warnings.map((w, i) => (
                <p key={i} className="text-[10px] text-amber-400/80">{w}</p>
              ))}
            </div>
          )}

          <div className="bg-white/[0.02] border border-white/5 rounded-xl overflow-hidden">
            {funnel.map((step, i) => {
              const maxCount = Math.max(...funnel.map(s => s.count), 1);
              const pct = (step.count / maxCount) * 100;
              const dropoff = i > 0 && funnel[i - 1].count > 0
                ? Math.round(((funnel[i - 1].count - step.count) / funnel[i - 1].count) * 100)
                : null;
              return (
                <div
                  key={step.step}
                  className="flex items-center gap-3 px-4 py-3 border-b border-white/[0.03] last:border-b-0"
                  data-testid={`funnel-step-${step.step}`}
                >
                  <div className="w-5 text-[10px] font-bold text-white/20 text-right">{i + 1}</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-semibold text-white/80">{step.step.replace(/_/g, ' ')}</span>
                      <div className="flex items-center gap-2">
                        {dropoff !== null && dropoff > 0 && (
                          <span className="text-[10px] text-rose-400 font-medium">-{dropoff}%</span>
                        )}
                        <span className="text-xs font-bold text-white tabular-nums">{step.count}</span>
                      </div>
                    </div>
                    <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-violet-500 to-blue-500 transition-all duration-500"
                        style={{ width: `${Math.max(pct, 1)}%` }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* ═══ QUICK SHOT RETENTION — is it real growth or junk? ═══ */}
        {data.quick_shot_retention && (
          <section data-testid="qs-retention">
            <h2 className="text-xs font-bold text-white/30 uppercase tracking-wider mb-4">
              Quick Shot Retention
              <span className={`ml-2 px-2 py-0.5 rounded text-[10px] font-bold ${
                data.quick_shot_retention.verdict === 'strong' ? 'bg-emerald-500/20 text-emerald-400' :
                data.quick_shot_retention.verdict === 'weak' ? 'bg-rose-500/20 text-rose-400' :
                data.quick_shot_retention.verdict === 'insufficient_data' ? 'bg-white/10 text-white/30' :
                'bg-amber-500/20 text-amber-400'
              }`}>
                {data.quick_shot_retention.verdict === 'strong' ? 'STRONG — double down' :
                 data.quick_shot_retention.verdict === 'weak' ? 'WEAK — restrict or kill' :
                 data.quick_shot_retention.verdict === 'insufficient_data' ? 'NEEDS MORE DATA' :
                 'AVERAGE — monitor'}
              </span>
            </h2>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <MetricCard
                label="QS Users"
                value={data.quick_shot_retention.total_quick_shot_users}
                color="white"
                icon={<Zap className="w-4 h-4" />}
                testId="metric-qs-users"
              />
              <MetricCard
                label="Returning"
                value={`${data.quick_shot_retention.retention_pct}%`}
                color={data.quick_shot_retention.retention_pct > 40 ? 'emerald' : data.quick_shot_retention.retention_pct > 20 ? 'amber' : 'rose'}
                icon={<TrendingUp className="w-4 h-4" />}
                testId="metric-qs-returning"
              />
              <MetricCard
                label="Second Action"
                value={`${data.quick_shot_retention.second_action_pct}%`}
                color={data.quick_shot_retention.second_action_pct > 30 ? 'emerald' : 'amber'}
                icon={<BarChart2 className="w-4 h-4" />}
                testId="metric-qs-second-action"
              />
              <MetricCard
                label="Verdict"
                value={data.quick_shot_retention.verdict}
                color={data.quick_shot_retention.verdict === 'strong' ? 'emerald' : data.quick_shot_retention.verdict === 'weak' ? 'rose' : 'white'}
                icon={<Eye className="w-4 h-4" />}
                testId="metric-qs-verdict"
              />
            </div>
          </section>
        )}

        {/* ═══ CTA BREAKDOWN TABLE ═══ */}
        {Object.keys(cta_breakdown).length > 0 && (
          <section data-testid="cta-breakdown">
            <h2 className="text-xs font-bold text-white/30 uppercase tracking-wider mb-4">CTA Click Breakdown</h2>
            <div className="bg-white/[0.02] border border-white/5 rounded-xl overflow-hidden">
              {Object.entries(cta_breakdown).sort((a, b) => b[1] - a[1]).map(([cta, count]) => (
                <div key={cta} className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.03] last:border-b-0">
                  <span className="text-xs text-white/60 capitalize">{cta.replace(/_/g, ' ')}</span>
                  <span className="text-xs font-bold text-white tabular-nums">{count}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* ═══ SOURCE SECTION BREAKDOWN ═══ */}
        {Object.keys(source_section_breakdown).length > 0 && (
          <section data-testid="source-breakdown">
            <h2 className="text-xs font-bold text-white/30 uppercase tracking-wider mb-4">Clicks by Section</h2>
            <div className="bg-white/[0.02] border border-white/5 rounded-xl overflow-hidden">
              {Object.entries(source_section_breakdown).sort((a, b) => b[1] - a[1]).map(([src, count]) => (
                <div key={src} className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.03] last:border-b-0">
                  <span className="text-xs text-white/60">{src}</span>
                  <span className="text-xs font-bold text-white tabular-nums">{count}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* ═══ SESSION STATS ═══ */}
        <section className="pb-8" data-testid="session-stats">
          <h2 className="text-xs font-bold text-white/30 uppercase tracking-wider mb-4">Session Info</h2>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-white/[0.02] border border-white/5 rounded-xl p-4">
              <p className="text-[10px] text-white/30 uppercase">Unique Sessions</p>
              <p className="text-2xl font-black text-white mt-1" data-testid="stat-sessions">{session_stats.unique_sessions}</p>
            </div>
            <div className="bg-white/[0.02] border border-white/5 rounded-xl p-4">
              <p className="text-[10px] text-white/30 uppercase">Unique Users</p>
              <p className="text-2xl font-black text-white mt-1" data-testid="stat-users">{session_stats.unique_users}</p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}


function MetricCard({ label, value, formula, color = 'white', icon, testId }) {
  const [showFormula, setShowFormula] = useState(false);
  const colorMap = {
    emerald: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/15',
    amber: 'text-amber-400 bg-amber-500/10 border-amber-500/15',
    rose: 'text-rose-400 bg-rose-500/10 border-rose-500/15',
    violet: 'text-violet-400 bg-violet-500/10 border-violet-500/15',
    blue: 'text-blue-400 bg-blue-500/10 border-blue-500/15',
    white: 'text-white/80 bg-white/[0.03] border-white/5',
  };
  const classes = colorMap[color] || colorMap.white;

  return (
    <div
      className={`rounded-xl border p-4 ${classes}`}
      data-testid={testId}
      onClick={() => formula && setShowFormula(!showFormula)}
    >
      <div className="flex items-center gap-2 mb-2">
        <span className="opacity-60">{icon}</span>
        <span className="text-[10px] font-semibold uppercase tracking-wider opacity-60">{label}</span>
        {formula && <ChevronDown className={`w-3 h-3 opacity-30 transition-transform ${showFormula ? 'rotate-180' : ''}`} />}
      </div>
      <p className="text-2xl font-black">{value}</p>
      {showFormula && formula && (
        <p className="text-[9px] opacity-40 mt-1 font-mono break-all">{formula}</p>
      )}
    </div>
  );
}
