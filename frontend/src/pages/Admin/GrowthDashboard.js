import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { TrendingUp, Users, Eye, RefreshCcw, Zap, BarChart3, ArrowUp, ArrowDown, Minus } from 'lucide-react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

function MetricCard({ title, value, subtitle, icon: Icon, trend, trendLabel, color = 'purple' }) {
  const colorMap = { purple: 'from-purple-500/20 to-purple-600/5', blue: 'from-blue-500/20 to-blue-600/5', green: 'from-green-500/20 to-green-600/5', amber: 'from-amber-500/20 to-amber-600/5', rose: 'from-rose-500/20 to-rose-600/5' };
  const TrendIcon = trend === 'up' ? ArrowUp : trend === 'down' ? ArrowDown : Minus;
  const trendColor = trend === 'up' ? 'text-green-400' : trend === 'down' ? 'text-red-400' : 'text-gray-400';

  return (
    <div className={`vs-panel p-5 bg-gradient-to-br ${colorMap[color] || colorMap.purple}`} data-testid={`metric-${title.toLowerCase().replace(/\s/g, '-')}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="w-10 h-10 rounded-xl bg-white/[0.06] flex items-center justify-center">
          <Icon className="w-5 h-5 text-[var(--vs-text-accent)]" />
        </div>
        {trend && (
          <div className={`flex items-center gap-1 text-xs ${trendColor}`}>
            <TrendIcon className="w-3 h-3" />
            {trendLabel}
          </div>
        )}
      </div>
      <p className="text-2xl font-bold text-white" style={{ fontFamily: 'var(--vs-font-mono)' }}>{value}</p>
      <p className="text-xs text-[var(--vs-text-muted)] mt-1">{title}</p>
      {subtitle && <p className="text-xs text-[var(--vs-text-secondary)] mt-0.5">{subtitle}</p>}
    </div>
  );
}

function TrendChart({ data }) {
  if (!data || data.length === 0) return null;
  const maxCount = Math.max(...data.map(d => d.count), 1);

  return (
    <div className="flex items-end gap-1.5 h-24" data-testid="trend-chart">
      {data.map((d, i) => (
        <div key={i} className="flex-1 flex flex-col items-center gap-1">
          <div
            className="w-full bg-gradient-to-t from-purple-500 to-purple-400 rounded-t-sm transition-all"
            style={{ height: `${(d.count / maxCount) * 80}px`, minHeight: '4px' }}
          />
          <span className="text-[9px] text-[var(--vs-text-muted)]">{d.date?.slice(5)}</span>
        </div>
      ))}
    </div>
  );
}

export default function GrowthDashboard() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchMetrics(); }, []);

  const fetchMetrics = async () => {
    try {
      const token = localStorage.getItem('token');
      const r = await axios.get(`${API}/api/public/growth-metrics`, { headers: { Authorization: `Bearer ${token}` } });
      setMetrics(r.data.metrics);
    } catch (e) {
      console.error('Failed to load growth metrics:', e);
    }
    setLoading(false);
  };

  if (loading) {
    return (
      <div className="p-6 space-y-4">
        <h1 className="vs-h2">Growth Dashboard</h1>
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          {[...Array(5)].map((_, i) => <div key={i} className="vs-panel p-5 animate-pulse h-32" />)}
        </div>
      </div>
    );
  }

  if (!metrics) {
    return <div className="p-6"><p className="text-[var(--vs-text-muted)]">Failed to load metrics.</p></div>;
  }

  const dc = metrics.daily_creations || {};
  const ca = metrics.creator_activation || {};
  const todayTrend = dc.today > dc.yesterday ? 'up' : dc.today < dc.yesterday ? 'down' : null;

  return (
    <div className="p-6 space-y-6" data-testid="growth-dashboard">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="vs-h2 flex items-center gap-2"><BarChart3 className="w-6 h-6 text-[var(--vs-text-accent)]" /> Growth Dashboard</h1>
          <p className="text-sm text-[var(--vs-text-muted)] mt-1">Platform health at a glance</p>
        </div>
        <button onClick={fetchMetrics} className="vs-btn-secondary h-8 px-3 text-xs">Refresh</button>
      </div>

      {/* 5 Core Metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <MetricCard
          title="Daily Creations"
          value={dc.today || 0}
          subtitle={`Yesterday: ${dc.yesterday || 0} | 7d avg: ${dc.avg_7d || 0}`}
          icon={Zap}
          color="purple"
          trend={todayTrend}
          trendLabel={todayTrend === 'up' ? `+${dc.today - dc.yesterday}` : todayTrend === 'down' ? `${dc.today - dc.yesterday}` : 'same'}
        />
        <MetricCard
          title="Remix Rate"
          value={`${metrics.remix_rate || 0}%`}
          subtitle={`${metrics.total_remixes || 0} total remixes`}
          icon={RefreshCcw}
          color={metrics.remix_rate >= 20 ? 'green' : metrics.remix_rate >= 10 ? 'blue' : 'rose'}
        />
        <MetricCard
          title="Public Page Views"
          value={metrics.public_page_traffic?.total_views || 0}
          icon={Eye}
          color="blue"
        />
        <MetricCard
          title="Creator Activation"
          value={`${ca.rate || 0}%`}
          subtitle={`${ca.active_creators || 0} / ${ca.total_users || 0} users`}
          icon={Users}
          color={ca.rate >= 40 ? 'green' : ca.rate >= 20 ? 'amber' : 'rose'}
        />
        <MetricCard
          title="Total Creations"
          value={metrics.total_creations || 0}
          icon={TrendingUp}
          color="green"
        />
      </div>

      {/* 7-Day Trend */}
      <div className="vs-panel p-5">
        <h3 className="text-sm font-medium text-white mb-3">7-Day Creation Trend</h3>
        <TrendChart data={metrics.trend_7d || []} />
      </div>

      {/* Trending Creations */}
      <div className="vs-panel p-5">
        <h3 className="text-sm font-medium text-white mb-3">Trending Creations</h3>
        <div className="space-y-2">
          {(metrics.trending_creations || []).map((item, i) => (
            <Link key={i} to={`/v/${item.slug || ''}`} className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-white/[0.04] transition-colors">
              <span className="text-sm text-[var(--vs-text-secondary)]">{item.title}</span>
              <div className="flex items-center gap-3 text-xs text-[var(--vs-text-muted)]">
                <span className="flex items-center gap-1"><Eye className="w-3 h-3" /> {item.views || 0}</span>
                <span className="flex items-center gap-1"><RefreshCcw className="w-3 h-3" /> {item.remix_count || 0}</span>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Health Indicators */}
      <div className="vs-panel p-5">
        <h3 className="text-sm font-medium text-white mb-3">Health Indicators</h3>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <p className={`text-lg font-bold ${metrics.remix_rate >= 10 ? 'text-green-400' : 'text-red-400'}`}>
              {metrics.remix_rate >= 20 ? 'Viral' : metrics.remix_rate >= 10 ? 'Healthy' : 'Low'}
            </p>
            <p className="text-xs text-[var(--vs-text-muted)]">Viral Loop</p>
          </div>
          <div>
            <p className={`text-lg font-bold ${(dc.avg_7d || 0) >= 20 ? 'text-green-400' : 'text-amber-400'}`}>
              {(dc.avg_7d || 0) >= 20 ? 'Active' : 'Growing'}
            </p>
            <p className="text-xs text-[var(--vs-text-muted)]">Content Velocity</p>
          </div>
          <div>
            <p className={`text-lg font-bold ${(ca.rate || 0) >= 40 ? 'text-green-400' : 'text-amber-400'}`}>
              {(ca.rate || 0) >= 40 ? 'Strong' : 'Needs Work'}
            </p>
            <p className="text-xs text-[var(--vs-text-muted)]">Activation</p>
          </div>
        </div>
      </div>
    </div>
  );
}
