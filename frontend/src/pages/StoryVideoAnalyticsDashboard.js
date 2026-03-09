import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import api from '../utils/api';
import {
  ArrowLeft, BarChart3, TrendingUp, Users, Clock, 
  CheckCircle, XCircle, Activity, Zap, Calendar,
  Film, Image, Mic, FileText, RefreshCw, Loader2,
  PieChart, LineChart
} from 'lucide-react';

export default function StoryVideoAnalyticsDashboard() {
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState(null);
  const [realTimeData, setRealTimeData] = useState(null);
  const [selectedDays, setSelectedDays] = useState(7);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchDashboardData();
    fetchRealTimeData();
    
    // Auto-refresh real-time data every 30 seconds
    const interval = setInterval(fetchRealTimeData, 30000);
    return () => clearInterval(interval);
  }, [selectedDays]);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const res = await api.get(`/api/story-video-studio/analytics/dashboard?days=${selectedDays}`);
      if (res.data.success) {
        setDashboardData(res.data);
      }
    } catch (error) {
      toast.error('Failed to load analytics data');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const fetchRealTimeData = async () => {
    try {
      const res = await api.get('/api/story-video-studio/analytics/real-time');
      if (res.data.success) {
        setRealTimeData(res.data);
      }
    } catch (error) {
      console.error('Failed to fetch real-time data:', error);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await Promise.all([fetchDashboardData(), fetchRealTimeData()]);
    setRefreshing(false);
    toast.success('Data refreshed');
  };

  const getMetricIcon = (type) => {
    const icons = {
      'scene_generation': FileText,
      'image_generation': Image,
      'voice_generation': Mic,
      'video_assembly': Film
    };
    return icons[type] || Activity;
  };

  const getMetricColor = (type) => {
    const colors = {
      'scene_generation': 'text-purple-400',
      'image_generation': 'text-blue-400',
      'voice_generation': 'text-green-400',
      'video_assembly': 'text-pink-400'
    };
    return colors[type] || 'text-slate-400';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-purple-950 to-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-purple-950 to-slate-950">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-lg border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app/admin">
              <Button variant="ghost" size="icon" className="text-white">
                <ArrowLeft className="w-5 h-5" />
              </Button>
            </Link>
            <div>
              <h1 className="text-xl font-bold text-white flex items-center gap-2">
                <BarChart3 className="w-6 h-6 text-purple-400" />
                Story Video Analytics
              </h1>
              <p className="text-sm text-slate-400">Performance metrics & insights</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            {/* Time Range Selector */}
            <select
              value={selectedDays}
              onChange={(e) => setSelectedDays(Number(e.target.value))}
              className="bg-slate-800 border border-slate-600 text-white rounded-lg px-3 py-2 text-sm"
              data-testid="time-range-select"
            >
              <option value={7}>Last 7 days</option>
              <option value={14}>Last 14 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
            
            <Button
              onClick={handleRefresh}
              disabled={refreshing}
              variant="outline"
              className="text-white border-slate-600"
              data-testid="refresh-btn"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 space-y-8">
        {/* Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="summary-cards">
          <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center">
                <Activity className="w-5 h-5 text-blue-400" />
              </div>
              <span className="text-slate-400 text-sm">Total Requests</span>
            </div>
            <p className="text-3xl font-bold text-white">{dashboardData?.summary?.total_requests || 0}</p>
          </div>
          
          <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
                <CheckCircle className="w-5 h-5 text-green-400" />
              </div>
              <span className="text-slate-400 text-sm">Successful</span>
            </div>
            <p className="text-3xl font-bold text-green-400">{dashboardData?.summary?.successful_requests || 0}</p>
          </div>
          
          <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-full bg-red-500/20 flex items-center justify-center">
                <XCircle className="w-5 h-5 text-red-400" />
              </div>
              <span className="text-slate-400 text-sm">Failed</span>
            </div>
            <p className="text-3xl font-bold text-red-400">{dashboardData?.summary?.failed_requests || 0}</p>
          </div>
          
          <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-purple-400" />
              </div>
              <span className="text-slate-400 text-sm">Success Rate</span>
            </div>
            <p className="text-3xl font-bold text-purple-400">{dashboardData?.summary?.success_rate || 0}%</p>
          </div>
        </div>

        {/* Real-Time Status */}
        {realTimeData && (
          <div className="bg-gradient-to-r from-purple-500/20 to-pink-500/20 border border-purple-500/30 rounded-xl p-6" data-testid="realtime-status">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Zap className="w-5 h-5 text-yellow-400" />
                Real-Time Status
              </h2>
              <span className="text-xs text-slate-400">
                Updated: {new Date(realTimeData.timestamp).toLocaleTimeString()}
              </span>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-slate-900/50 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-yellow-400">{realTimeData.in_progress_count}</p>
                <p className="text-sm text-slate-400">In Progress</p>
              </div>
              <div className="bg-slate-900/50 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-white">{realTimeData.last_hour?.total || 0}</p>
                <p className="text-sm text-slate-400">Last Hour Total</p>
              </div>
              <div className="bg-slate-900/50 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-green-400">{realTimeData.last_hour?.successful || 0}</p>
                <p className="text-sm text-slate-400">Last Hour Success</p>
              </div>
              <div className="bg-slate-900/50 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-purple-400">{realTimeData.last_hour?.success_rate || 0}%</p>
                <p className="text-sm text-slate-400">Last Hour Rate</p>
              </div>
            </div>
          </div>
        )}

        {/* Metrics by Type */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6" data-testid="metrics-by-type">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <PieChart className="w-5 h-5 text-blue-400" />
            Performance by Generation Type
          </h2>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
            {dashboardData?.metrics_by_type?.map((metric) => {
              const Icon = getMetricIcon(metric.type);
              const colorClass = getMetricColor(metric.type);
              
              return (
                <div key={metric.type} className="bg-slate-900/50 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Icon className={`w-5 h-5 ${colorClass}`} />
                    <span className="text-white font-medium capitalize">
                      {metric.type.replace(/_/g, ' ')}
                    </span>
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-slate-400 text-sm">Total</span>
                      <span className="text-white">{metric.total}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400 text-sm">Success Rate</span>
                      <span className={metric.success_rate >= 90 ? 'text-green-400' : metric.success_rate >= 70 ? 'text-yellow-400' : 'text-red-400'}>
                        {metric.success_rate}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400 text-sm">Avg Duration</span>
                      <span className="text-white">{(metric.avg_duration_ms / 1000).toFixed(1)}s</span>
                    </div>
                  </div>
                  
                  {/* Progress bar for success rate */}
                  <div className="mt-3 h-2 bg-slate-700 rounded-full overflow-hidden">
                    <div 
                      className={`h-full ${metric.success_rate >= 90 ? 'bg-green-500' : metric.success_rate >= 70 ? 'bg-yellow-500' : 'bg-red-500'}`}
                      style={{ width: `${metric.success_rate}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Daily Active Users */}
        <div className="grid md:grid-cols-2 gap-6">
          <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6" data-testid="dau-chart">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Users className="w-5 h-5 text-green-400" />
              Daily Active Users
            </h2>
            
            <div className="space-y-3">
              {dashboardData?.daily_active_users?.slice(-7).map((day) => (
                <div key={day._id} className="flex items-center gap-3">
                  <span className="text-slate-400 text-sm w-24">{day._id}</span>
                  <div className="flex-1 h-6 bg-slate-700 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-green-500 to-emerald-500"
                      style={{ 
                        width: `${Math.min(day.unique_users * 5, 100)}%`
                      }}
                    />
                  </div>
                  <span className="text-white font-medium w-12 text-right">{day.unique_users}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Credit Usage */}
          <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6" data-testid="credit-usage">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <LineChart className="w-5 h-5 text-yellow-400" />
              Credit Usage Trend
            </h2>
            
            <div className="space-y-3">
              {dashboardData?.credit_usage?.slice(-7).map((day) => (
                <div key={day._id} className="flex items-center gap-3">
                  <span className="text-slate-400 text-sm w-24">{day._id}</span>
                  <div className="flex-1 h-6 bg-slate-700 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-yellow-500 to-amber-500"
                      style={{ 
                        width: `${Math.min(day.total_credits / 10, 100)}%`
                      }}
                    />
                  </div>
                  <span className="text-white font-medium w-16 text-right">{day.total_credits}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Feature Usage Breakdown */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6" data-testid="feature-usage">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-purple-400" />
            Feature Usage Breakdown
          </h2>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {dashboardData?.feature_usage?.map((feature) => {
              const Icon = getMetricIcon(feature._id);
              const colorClass = getMetricColor(feature._id);
              
              return (
                <div key={feature._id} className="bg-slate-900/50 rounded-lg p-4 text-center">
                  <Icon className={`w-8 h-8 ${colorClass} mx-auto mb-2`} />
                  <p className="text-white font-bold text-xl">{feature.count}</p>
                  <p className="text-slate-400 text-sm capitalize">{feature._id?.replace(/_/g, ' ')}</p>
                  <p className="text-slate-500 text-xs mt-1">
                    Avg: {(feature.avg_duration / 1000).toFixed(1)}s
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Top Users */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6" data-testid="top-users">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Users className="w-5 h-5 text-pink-400" />
            Top Users by Generation Volume
          </h2>
          
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-slate-400 text-sm border-b border-slate-700">
                  <th className="pb-3 pr-4">Rank</th>
                  <th className="pb-3 pr-4">User ID</th>
                  <th className="pb-3 pr-4">Total Generations</th>
                  <th className="pb-3 pr-4">Successful</th>
                  <th className="pb-3">Success Rate</th>
                </tr>
              </thead>
              <tbody>
                {dashboardData?.top_users?.map((user, idx) => (
                  <tr key={user._id} className="border-b border-slate-700/50">
                    <td className="py-3 pr-4">
                      <span className={`w-6 h-6 rounded-full flex items-center justify-center text-sm ${
                        idx === 0 ? 'bg-yellow-500 text-black' :
                        idx === 1 ? 'bg-slate-400 text-black' :
                        idx === 2 ? 'bg-amber-600 text-white' :
                        'bg-slate-700 text-slate-300'
                      }`}>
                        {idx + 1}
                      </span>
                    </td>
                    <td className="py-3 pr-4 text-white font-mono text-sm">
                      {user._id?.substring(0, 8)}...
                    </td>
                    <td className="py-3 pr-4 text-white">{user.total_generations}</td>
                    <td className="py-3 pr-4 text-green-400">{user.successful}</td>
                    <td className="py-3">
                      <span className={`px-2 py-1 rounded text-sm ${
                        user.successful / user.total_generations >= 0.9 ? 'bg-green-500/20 text-green-400' :
                        user.successful / user.total_generations >= 0.7 ? 'bg-yellow-500/20 text-yellow-400' :
                        'bg-red-500/20 text-red-400'
                      }`}>
                        {((user.successful / user.total_generations) * 100).toFixed(0)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}
