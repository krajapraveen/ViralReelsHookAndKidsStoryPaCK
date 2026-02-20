import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import {
  ArrowLeft, Shield, Activity, Users, Server, AlertTriangle,
  BarChart3, Clock, RefreshCw, Lock, Unlock, Eye, TrendingUp,
  Database, Cpu, Globe, ChevronDown, ChevronUp, Filter
} from 'lucide-react';
import api from '../utils/api';

export default function AdminMonitoring() {
  const [overview, setOverview] = useState(null);
  const [threatStats, setThreatStats] = useState(null);
  const [appUsage, setAppUsage] = useState(null);
  const [performance, setPerformance] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [refreshing, setRefreshing] = useState(false);
  const [timeRange, setTimeRange] = useState(30);

  useEffect(() => {
    fetchAllData();
  }, [timeRange]);

  const fetchAllData = async () => {
    setRefreshing(true);
    try {
      const [overviewRes, threatRes, usageRes, perfRes] = await Promise.all([
        api.get('/api/analytics/admin/overview'),
        api.get('/api/analytics/admin/threat-stats'),
        api.get(`/api/analytics/admin/app-usage?days=${timeRange}`),
        api.get('/api/analytics/admin/performance')
      ]);
      
      setOverview(overviewRes.data);
      setThreatStats(threatRes.data);
      setAppUsage(usageRes.data);
      setPerformance(perfRes.data);
    } catch (error) {
      console.error('Failed to fetch admin data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to="/app/admin" className="text-slate-400 hover:text-white">
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div className="flex items-center gap-2">
                <Shield className="w-8 h-8 text-green-400" />
                <div>
                  <h1 className="text-xl font-bold text-white">Admin Monitoring</h1>
                  <p className="text-xs text-slate-400">Security & Performance Dashboard</p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <select
                value={timeRange}
                onChange={(e) => setTimeRange(Number(e.target.value))}
                className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                data-testid="time-range-select"
              >
                <option value={7}>Last 7 days</option>
                <option value={30}>Last 30 days</option>
                <option value={90}>Last 90 days</option>
              </select>
              <Button
                onClick={fetchAllData}
                disabled={refreshing}
                className="bg-slate-800 hover:bg-slate-700"
                data-testid="refresh-btn"
              >
                <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Tabs */}
      <div className="border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex gap-6">
            {['overview', 'security', 'usage', 'performance'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`py-4 px-2 font-medium capitalize transition-colors ${
                  activeTab === tab
                    ? 'text-purple-400 border-b-2 border-purple-400'
                    : 'text-slate-400 hover:text-white'
                }`}
                data-testid={`tab-${tab}`}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <StatCard
                title="Total Users"
                value={overview?.users?.total || 0}
                subValue={`${overview?.users?.newThisWeek || 0} new this week`}
                icon={Users}
                color="purple"
              />
              <StatCard
                title="Active Today"
                value={overview?.users?.activeToday || 0}
                subValue="Unique sessions"
                icon={Activity}
                color="green"
              />
              <StatCard
                title="Revenue This Month"
                value={`₹${(overview?.revenue?.thisMonth || 0).toLocaleString()}`}
                subValue={overview?.revenue?.currency || 'INR'}
                icon={TrendingUp}
                color="yellow"
              />
              <StatCard
                title="Job Success Rate"
                value={`${overview?.jobs?.successRate || 0}%`}
                subValue={`${overview?.jobs?.total || 0} total jobs`}
                icon={Server}
                color="blue"
              />
            </div>

            {/* Feature Usage */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Feature Usage</h3>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                {overview?.featureUsage && Object.entries(overview.featureUsage).map(([feature, count]) => (
                  <div key={feature} className="bg-slate-800/50 rounded-lg p-4 text-center">
                    <p className="text-2xl font-bold text-white">{count}</p>
                    <p className="text-xs text-slate-400 capitalize">{feature.replace(/([A-Z])/g, ' $1').trim()}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Jobs Overview */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-3 h-3 rounded-full bg-green-500"></div>
                  <h4 className="font-medium text-white">Successful Jobs</h4>
                </div>
                <p className="text-3xl font-bold text-green-400">{overview?.jobs?.successful || 0}</p>
              </div>
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-3 h-3 rounded-full bg-red-500"></div>
                  <h4 className="font-medium text-white">Failed Jobs</h4>
                </div>
                <p className="text-3xl font-bold text-red-400">{overview?.jobs?.failed || 0}</p>
              </div>
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                  <h4 className="font-medium text-white">Total Jobs</h4>
                </div>
                <p className="text-3xl font-bold text-blue-400">{overview?.jobs?.total || 0}</p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'security' && (
          <div className="space-y-6">
            {/* Threat Status */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Shield className="w-5 h-5 text-green-400" />
                Threat Detection Status
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <ThreatMetric
                  label="Blocked IPs"
                  value={threatStats?.currentStatus?.blocked_ips_count || 0}
                  color="red"
                />
                <ThreatMetric
                  label="Throttled IPs"
                  value={threatStats?.currentStatus?.throttled_ips_count || 0}
                  color="yellow"
                />
                <ThreatMetric
                  label="Active Sessions"
                  value={threatStats?.currentStatus?.active_sessions || 0}
                  color="green"
                />
                <ThreatMetric
                  label="High Risk IPs"
                  value={threatStats?.currentStatus?.high_risk_ips || 0}
                  color="orange"
                />
                <ThreatMetric
                  label="Recent Events"
                  value={threatStats?.currentStatus?.recent_events || 0}
                  color="purple"
                />
              </div>
            </div>

            {/* Rate Limits */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Clock className="w-5 h-5 text-blue-400" />
                Rate Limit Configuration
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                {threatStats?.rateWindows && Object.entries(threatStats.rateWindows).map(([endpoint, limit]) => (
                  <div key={endpoint} className="bg-slate-800/50 rounded-lg p-4">
                    <p className="text-sm font-medium text-white capitalize">{endpoint}</p>
                    <p className="text-xs text-slate-400 mt-1">{limit}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Recent Security Events */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-yellow-400" />
                Recent Security Events
              </h3>
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {threatStats?.recentEvents?.length > 0 ? (
                  threatStats.recentEvents.map((event, idx) => (
                    <div key={idx} className="bg-slate-800/50 rounded-lg p-3 flex items-start gap-3">
                      <div className={`w-2 h-2 rounded-full mt-2 ${
                        event.severity === 'CRITICAL' ? 'bg-red-500' :
                        event.severity === 'WARNING' ? 'bg-yellow-500' : 'bg-blue-500'
                      }`}></div>
                      <div className="flex-1">
                        <p className="text-sm text-white">{event.event_type}</p>
                        <p className="text-xs text-slate-400">{new Date(event.timestamp).toLocaleString()}</p>
                        {event.details && (
                          <p className="text-xs text-slate-500 mt-1">
                            {JSON.stringify(event.details).slice(0, 100)}...
                          </p>
                        )}
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-slate-400 text-sm">No recent security events. All systems secure.</p>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'usage' && (
          <div className="space-y-6">
            {/* Feature Totals */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Feature Usage Totals</h3>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                {appUsage?.featureTotals && Object.entries(appUsage.featureTotals).map(([feature, count]) => (
                  <div key={feature} className="bg-slate-800/50 rounded-lg p-4">
                    <p className="text-2xl font-bold text-white">{count}</p>
                    <p className="text-xs text-slate-400">{feature}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Daily Usage Chart */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Daily Usage ({appUsage?.period})</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-700">
                      <th className="text-left py-3 px-4 text-slate-400">Date</th>
                      <th className="text-center py-3 px-4 text-slate-400">Story Series</th>
                      <th className="text-center py-3 px-4 text-slate-400">Challenges</th>
                      <th className="text-center py-3 px-4 text-slate-400">Tone Rewrites</th>
                      <th className="text-center py-3 px-4 text-slate-400">Coloring Books</th>
                      <th className="text-center py-3 px-4 text-slate-400">GenStudio</th>
                    </tr>
                  </thead>
                  <tbody>
                    {appUsage?.dailyStats?.slice(-14).map((day, idx) => (
                      <tr key={idx} className="border-b border-slate-800">
                        <td className="py-3 px-4 text-white">{day.date}</td>
                        <td className="py-3 px-4 text-center text-purple-400">{day.storySeries}</td>
                        <td className="py-3 px-4 text-center text-blue-400">{day.challenges}</td>
                        <td className="py-3 px-4 text-center text-green-400">{day.toneRewrites}</td>
                        <td className="py-3 px-4 text-center text-pink-400">{day.coloringBooks}</td>
                        <td className="py-3 px-4 text-center text-yellow-400">{day.genstudioJobs}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'performance' && (
          <div className="space-y-6">
            {/* Job Processing Times */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Cpu className="w-5 h-5 text-purple-400" />
                Job Processing Times
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {performance?.jobProcessingTimes && Object.entries(performance.jobProcessingTimes).map(([jobType, times]) => (
                  <div key={jobType} className="bg-slate-800/50 rounded-lg p-4">
                    <p className="text-sm font-medium text-white capitalize mb-2">
                      {jobType.replace(/_/g, ' ')}
                    </p>
                    <div className="space-y-1 text-xs">
                      <div className="flex justify-between">
                        <span className="text-slate-400">Average:</span>
                        <span className="text-green-400">{times.average}s</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Min:</span>
                        <span className="text-blue-400">{times.min}s</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Max:</span>
                        <span className="text-yellow-400">{times.max}s</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Samples:</span>
                        <span className="text-slate-300">{times.samples}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Database Collections */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Database className="w-5 h-5 text-blue-400" />
                Database Collections
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {performance?.dbCollections && Object.entries(performance.dbCollections).map(([collection, count]) => (
                  <div key={collection} className="bg-slate-800/50 rounded-lg p-4 text-center">
                    <p className="text-2xl font-bold text-white">{count.toLocaleString()}</p>
                    <p className="text-xs text-slate-400 capitalize">{collection}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

// Helper Components
function StatCard({ title, value, subValue, icon: Icon, color }) {
  const colors = {
    purple: 'from-purple-500/20 to-purple-600/20 border-purple-500/30',
    green: 'from-green-500/20 to-green-600/20 border-green-500/30',
    yellow: 'from-yellow-500/20 to-yellow-600/20 border-yellow-500/30',
    blue: 'from-blue-500/20 to-blue-600/20 border-blue-500/30',
  };
  
  const iconColors = {
    purple: 'text-purple-400',
    green: 'text-green-400',
    yellow: 'text-yellow-400',
    blue: 'text-blue-400',
  };

  return (
    <div className={`bg-gradient-to-br ${colors[color]} border rounded-xl p-6`}>
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm text-slate-400">{title}</p>
        <Icon className={`w-5 h-5 ${iconColors[color]}`} />
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="text-xs text-slate-400 mt-1">{subValue}</p>
    </div>
  );
}

function ThreatMetric({ label, value, color }) {
  const colors = {
    red: 'bg-red-500/20 text-red-400',
    yellow: 'bg-yellow-500/20 text-yellow-400',
    green: 'bg-green-500/20 text-green-400',
    orange: 'bg-orange-500/20 text-orange-400',
    purple: 'bg-purple-500/20 text-purple-400',
  };

  return (
    <div className={`${colors[color]} rounded-lg p-4 text-center`}>
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-xs opacity-75">{label}</p>
    </div>
  );
}
