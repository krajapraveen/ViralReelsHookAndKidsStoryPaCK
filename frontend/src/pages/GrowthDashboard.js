import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '../components/ui/button';
import api from '../utils/api';
import { toast } from 'sonner';
import {
  TrendingUp, GitBranch, Share2, Users, BarChart3,
  RefreshCw, ArrowDown, Zap, Eye, Clock, AlertTriangle,
  ChevronRight, Target, ArrowUpDown, Bookmark
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

export default function GrowthDashboard({ parentDays, parentRefreshSignal }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastFetched, setLastFetched] = useState(null);

  // Sync hours from parent days prop (7d=168h, 30d=720h, 90d=2160h)
  const dayToHoursMap = { 7: 168, 30: 720, 90: 2160 };
  const [hours, setHours] = useState(parentDays ? (dayToHoursMap[parentDays] || 720) : 720);

  // Sync when parent changes
  useEffect(() => {
    if (parentDays && dayToHoursMap[parentDays]) {
      setHours(dayToHoursMap[parentDays]);
    }
  }, [parentDays]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get(`/api/admin/metrics/growth?hours=${hours}`);
      setData(res.data);
      setLastFetched(new Date());
    } catch (err) {
      toast.error('Failed to load growth metrics');
    } finally {
      setLoading(false);
    }
  }, [hours]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Re-fetch when parent polling triggers
  useEffect(() => {
    if (parentRefreshSignal) {
      fetchData();
    }
  }, [parentRefreshSignal]);

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
      {/* Header + Period selector + Freshness */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <TrendingUp className="w-5 h-5 text-violet-400" />
          <h2 className="text-base font-semibold text-white">Growth Validation</h2>
          <span className="text-[10px] text-slate-500 bg-slate-800 px-2 py-0.5 rounded-full font-mono">DATA MODE</span>
          {lastFetched && (
            <span className={`text-[10px] px-2 py-0.5 rounded-full font-mono ${
              (Date.now() - lastFetched.getTime()) < 60000 ? 'text-emerald-400 bg-emerald-500/10' :
              (Date.now() - lastFetched.getTime()) < 600000 ? 'text-amber-400 bg-amber-500/10' :
              'text-rose-400 bg-rose-500/10'
            }`} data-testid="growth-freshness">
              {(Date.now() - lastFetched.getTime()) < 60000 ? 'LIVE' :
               (Date.now() - lastFetched.getTime()) < 600000 ? 'DELAYED' : 'STALE'}
              {' '}{Math.round((Date.now() - lastFetched.getTime()) / 1000)}s ago
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {[24, 72, 168, 720].map(h => (
            <button
              key={h}
              onClick={() => setHours(h)}
              className={`text-[10px] px-2 py-1 rounded font-mono transition-colors ${
                hours === h ? 'bg-violet-600 text-white' : 'text-slate-500 hover:text-white'
              }`}
              data-testid={`growth-period-${h}`}
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

      {/* ── STORY-LEVEL PERFORMANCE ── */}
      <StoryPerformance />
    </div>
  );
}

// ─── Story Performance Panel ────────────────────────────────────────────────
function StoryPerformance() {
  const [stories, setStories] = useState(null);
  const [summary, setSummary] = useState(null);
  const [genres, setGenres] = useState(null);
  const [sortBy, setSortBy] = useState('continuation_rate');
  const [loading, setLoading] = useState(true);

  const fetchPerf = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get(`/api/admin/metrics/story-performance?sort_by=${sortBy}&limit=30`);
      setStories(res.data.stories);
      setSummary(res.data.summary);
      setGenres(res.data.genre_breakdown);
    } catch {
      toast.error('Failed to load story performance');
    } finally {
      setLoading(false);
    }
  }, [sortBy]);

  useEffect(() => { fetchPerf(); }, [fetchPerf]);

  if (loading && !stories) {
    return (
      <div className="flex items-center justify-center py-8">
        <RefreshCw className="w-5 h-5 animate-spin text-violet-500" />
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="story-performance">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bookmark className="w-4 h-4 text-amber-400" />
          <h3 className="text-sm font-bold text-white">Story-Level Performance</h3>
          <span className="text-[10px] text-slate-500 bg-slate-800 px-2 py-0.5 rounded-full font-mono">
            {summary?.total_stories || 0} stories
          </span>
        </div>
        <div className="flex items-center gap-2">
          {['continuation_rate', 'views', 'forks'].map(s => (
            <button
              key={s}
              onClick={() => setSortBy(s)}
              className={`text-[10px] px-2 py-1 rounded font-mono transition-colors flex items-center gap-1 ${
                sortBy === s ? 'bg-amber-600 text-white' : 'text-slate-500 hover:text-white'
              }`}
              data-testid={`sort-${s}`}
            >
              <ArrowUpDown className="w-2.5 h-2.5" />
              {s === 'continuation_rate' ? 'Rate' : s === 'views' ? 'Views' : 'Forks'}
            </button>
          ))}
          <Button variant="outline" size="sm" onClick={fetchPerf} className="h-7 text-xs border-slate-700 text-slate-400" data-testid="refresh-perf">
            <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="rounded-lg border border-slate-700/40 bg-slate-900/40 p-3 text-center">
            <div className="text-lg font-black text-white">{summary.total_stories}</div>
            <div className="text-[10px] text-slate-500">Total Stories</div>
          </div>
          <div className="rounded-lg border border-slate-700/40 bg-slate-900/40 p-3 text-center">
            <div className="text-lg font-black text-white">{summary.total_views}</div>
            <div className="text-[10px] text-slate-500">Total Views</div>
          </div>
          <div className="rounded-lg border border-slate-700/40 bg-slate-900/40 p-3 text-center">
            <div className="text-lg font-black text-white">{summary.total_forks}</div>
            <div className="text-[10px] text-slate-500">Total Continuations</div>
          </div>
          <div className="rounded-lg border border-slate-700/40 bg-slate-900/40 p-3 text-center">
            <div className="text-lg font-black text-amber-400">{summary.avg_continuation_rate}%</div>
            <div className="text-[10px] text-slate-500">Avg Continuation Rate</div>
          </div>
        </div>
      )}

      {/* Genre breakdown */}
      {genres && Object.keys(genres).length > 0 && (
        <div className="bg-slate-900/40 border border-slate-700/40 rounded-xl p-4" data-testid="genre-breakdown">
          <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Genre Performance</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Object.entries(genres).map(([genre, stats]) => (
              <div key={genre} className="rounded-lg border border-slate-700/30 p-3">
                <div className="text-xs font-bold text-white capitalize mb-1">{genre}</div>
                <div className="flex items-baseline gap-1">
                  <span className="text-lg font-black text-amber-400">{stats.continuation_rate}%</span>
                  <span className="text-[10px] text-slate-500">cont. rate</span>
                </div>
                <div className="text-[10px] text-slate-500 mt-1">
                  {stats.count} stories / {stats.views} views / {stats.forks} forks
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Story table */}
      {stories && stories.length > 0 && (
        <div className="bg-slate-900/40 border border-slate-700/40 rounded-xl overflow-hidden" data-testid="story-table">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-slate-700/40">
                  <th className="text-[10px] text-slate-500 font-bold uppercase tracking-wider p-3">#</th>
                  <th className="text-[10px] text-slate-500 font-bold uppercase tracking-wider p-3">Story</th>
                  <th className="text-[10px] text-slate-500 font-bold uppercase tracking-wider p-3">Genre</th>
                  <th className="text-[10px] text-slate-500 font-bold uppercase tracking-wider p-3 text-right">Views</th>
                  <th className="text-[10px] text-slate-500 font-bold uppercase tracking-wider p-3 text-right">Continues</th>
                  <th className="text-[10px] text-slate-500 font-bold uppercase tracking-wider p-3 text-right">Rate</th>
                </tr>
              </thead>
              <tbody>
                {stories.map((s, i) => {
                  const rate = s.continuation_rate || 0;
                  const rateColor = rate >= 20 ? 'text-emerald-400' : rate >= 10 ? 'text-amber-400' : 'text-slate-500';
                  return (
                    <tr key={s.id || i} className="border-b border-slate-800/40 hover:bg-slate-800/20 transition-colors" data-testid={`story-row-${i}`}>
                      <td className="p-3 text-xs text-slate-600 font-mono">{i + 1}</td>
                      <td className="p-3">
                        <div className="text-sm text-white font-medium line-clamp-1">{s.title || 'Untitled'}</div>
                        {s.hookText && <p className="text-[10px] text-violet-300 italic line-clamp-1 mt-0.5">"{s.hookText}"</p>}
                      </td>
                      <td className="p-3">
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/5 text-slate-400 capitalize font-mono">{s.genre || '-'}</span>
                      </td>
                      <td className="p-3 text-right">
                        <span className="text-xs text-white font-mono">{s.views || 0}</span>
                      </td>
                      <td className="p-3 text-right">
                        <span className="text-xs text-white font-mono">{s.forks || 0}</span>
                      </td>
                      <td className="p-3 text-right">
                        <span className={`text-xs font-mono font-bold ${rateColor}`}>{rate}%</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
