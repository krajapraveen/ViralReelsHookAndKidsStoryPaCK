import React, { useState, useEffect } from 'react';
import api from '../../utils/api';
import { Loader2, TrendingUp, Users, Film, Share2, RefreshCcw, Coins } from 'lucide-react';
import { Button } from '../ui/button';

export default function GrowthFunnelTab({ dateRange }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchFunnel();
  }, [dateRange]);

  const fetchFunnel = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/api/pipeline/analytics/funnel?days=${dateRange || 30}`);
      if (res.data.success) setData(res.data);
    } catch (e) {
      console.error('Funnel fetch error', e);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return (
    <div className="flex items-center justify-center py-16">
      <Loader2 className="w-6 h-6 text-purple-400 animate-spin" />
    </div>
  );

  if (!data) return (
    <p className="text-slate-400 text-center py-16">No analytics data yet. Data will appear as users create videos.</p>
  );

  const funnel = data.funnel || {};
  const totals = data.totals || {};
  const daily = data.daily || {};
  const dailyKeys = Object.keys(daily).sort();

  const funnelSteps = [
    { key: 'video_generation_started', label: 'Videos Started', icon: Film, color: 'indigo' },
    { key: 'video_completed', label: 'Videos Completed', icon: Film, color: 'green' },
    { key: 'video_shared', label: 'Videos Shared', icon: Share2, color: 'blue' },
    { key: 'remix_created', label: 'Remixes Created', icon: RefreshCcw, color: 'pink' },
  ];

  return (
    <div className="space-y-8" data-testid="growth-funnel-tab">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-700/50 rounded-xl p-4 border border-slate-600/50">
          <div className="flex items-center gap-2 mb-2">
            <Film className="w-4 h-4 text-indigo-400" />
            <span className="text-xs text-slate-400 uppercase tracking-wide">Total Videos</span>
          </div>
          <p className="text-2xl font-bold text-white" data-testid="total-videos">{totals.total_videos || 0}</p>
        </div>
        <div className="bg-slate-700/50 rounded-xl p-4 border border-slate-600/50">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-green-400" />
            <span className="text-xs text-slate-400 uppercase tracking-wide">Completed</span>
          </div>
          <p className="text-2xl font-bold text-white" data-testid="completed-videos">{totals.completed_videos || 0}</p>
          <p className="text-xs text-slate-500 mt-1">
            {totals.total_videos ? `${Math.round((totals.completed_videos / totals.total_videos) * 100)}% completion` : '—'}
          </p>
        </div>
        <div className="bg-slate-700/50 rounded-xl p-4 border border-slate-600/50">
          <div className="flex items-center gap-2 mb-2">
            <RefreshCcw className="w-4 h-4 text-pink-400" />
            <span className="text-xs text-slate-400 uppercase tracking-wide">Remixes</span>
          </div>
          <p className="text-2xl font-bold text-white" data-testid="remix-count">{totals.remix_count || 0}</p>
        </div>
        <div className="bg-slate-700/50 rounded-xl p-4 border border-slate-600/50">
          <div className="flex items-center gap-2 mb-2">
            <Coins className="w-4 h-4 text-amber-400" />
            <span className="text-xs text-slate-400 uppercase tracking-wide">Credits Used</span>
          </div>
          <p className="text-2xl font-bold text-white" data-testid="credits-consumed">{totals.total_credits_consumed || 0}</p>
        </div>
      </div>

      {/* Funnel Visualization */}
      <div>
        <h3 className="text-sm font-medium text-slate-300 mb-4 uppercase tracking-wide">Growth Funnel</h3>
        <div className="space-y-3">
          {funnelSteps.map((step, i) => {
            const count = funnel[step.key] || 0;
            const maxCount = Math.max(...funnelSteps.map(s => funnel[s.key] || 0), 1);
            const pct = Math.round((count / maxCount) * 100);
            return (
              <div key={step.key} className="flex items-center gap-4" data-testid={`funnel-step-${step.key}`}>
                <div className="w-40 flex items-center gap-2 text-sm text-slate-300">
                  <step.icon className={`w-4 h-4 text-${step.color}-400`} />
                  {step.label}
                </div>
                <div className="flex-1 h-8 bg-slate-800 rounded-lg overflow-hidden">
                  <div
                    className={`h-full bg-${step.color}-500/40 rounded-lg flex items-center px-3 transition-all duration-500`}
                    style={{ width: `${Math.max(pct, 5)}%` }}
                  >
                    <span className="text-xs font-semibold text-white">{count}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Daily Activity Table */}
      {dailyKeys.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-slate-300 mb-4 uppercase tracking-wide">Daily Activity (Last {dateRange || 30} Days)</h3>
          <div className="overflow-x-auto rounded-lg border border-slate-700">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-800/80 text-slate-400">
                  <th className="text-left px-4 py-3 font-medium">Date</th>
                  <th className="text-right px-4 py-3 font-medium">Started</th>
                  <th className="text-right px-4 py-3 font-medium">Completed</th>
                  <th className="text-right px-4 py-3 font-medium">Shared</th>
                  <th className="text-right px-4 py-3 font-medium">Remixed</th>
                </tr>
              </thead>
              <tbody>
                {dailyKeys.slice(-14).map(date => {
                  const row = daily[date] || {};
                  return (
                    <tr key={date} className="border-t border-slate-700/50 hover:bg-slate-800/40">
                      <td className="px-4 py-2 text-slate-300">{date}</td>
                      <td className="px-4 py-2 text-right text-white">{row.video_generation_started || 0}</td>
                      <td className="px-4 py-2 text-right text-green-400">{row.video_completed || 0}</td>
                      <td className="px-4 py-2 text-right text-blue-400">{row.video_shared || 0}</td>
                      <td className="px-4 py-2 text-right text-pink-400">{row.remix_created || 0}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="text-center">
        <Button onClick={fetchFunnel} variant="outline" size="sm" className="border-slate-600 text-slate-400 hover:text-white">
          <RefreshCcw className="w-4 h-4 mr-2" /> Refresh Data
        </Button>
      </div>
    </div>
  );
}
