import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { 
  Activity, Users, Zap, TrendingUp, DollarSign, Clock, 
  RefreshCw, ArrowLeft, Sparkles, UserCheck, CreditCard,
  BarChart3, PieChart, ArrowUpRight, ArrowDownRight
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const RealtimeAnalytics = () => {
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState(null);
  const [trends, setTrends] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchMetrics = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      const [metricsRes, trendsRes] = await Promise.all([
        axios.get(`${API}/api/realtime-analytics/snapshot`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API}/api/realtime-analytics/generation-trends`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);
      
      setMetrics(metricsRes.data);
      setTrends(trendsRes.data.trends || []);
      setLastUpdate(new Date());
      setLoading(false);
    } catch (error) {
      console.error('Error fetching metrics:', error);
      if (error.response?.status === 403) {
        toast.error('Admin access required');
        navigate('/app');
      }
      setLoading(false);
    }
  }, [navigate]);

  useEffect(() => {
    fetchMetrics();
    
    // Auto-refresh every 30 seconds
    let interval;
    if (autoRefresh) {
      interval = setInterval(fetchMetrics, 30000);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [fetchMetrics, autoRefresh]);

  const formatNumber = (num) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num?.toLocaleString() || '0';
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount || 0);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <RefreshCw className="w-8 h-8 text-purple-500 animate-spin" />
          <p className="text-gray-400">Loading real-time analytics...</p>
        </div>
      </div>
    );
  }

  const live = metrics?.liveMetrics || {};
  const perf = metrics?.performance || {};
  const revenue = metrics?.revenue || {};

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white p-4 md:p-6">
      {/* Header */}
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => navigate('/app/admin')}
              className="text-gray-400 hover:text-white"
              data-testid="back-to-admin-btn"
            >
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="text-2xl md:text-3xl font-bold flex items-center gap-2">
                <Activity className="w-7 h-7 text-green-400" />
                Real-Time Analytics
              </h1>
              <p className="text-gray-400 text-sm mt-1">
                Live platform metrics and performance
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <div className={`w-2 h-2 rounded-full ${autoRefresh ? 'bg-green-400 animate-pulse' : 'bg-gray-500'}`} />
              {lastUpdate && `Updated ${lastUpdate.toLocaleTimeString()}`}
            </div>
            <Button
              variant={autoRefresh ? "default" : "outline"}
              size="sm"
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={autoRefresh ? "bg-green-600 hover:bg-green-700" : ""}
              data-testid="auto-refresh-toggle"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${autoRefresh ? 'animate-spin' : ''}`} />
              {autoRefresh ? 'Live' : 'Paused'}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={fetchMetrics}
              data-testid="refresh-btn"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
          </div>
        </div>

        {/* Live Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
          <Card className="bg-gradient-to-br from-green-500/20 to-green-600/10 border-green-500/30" data-testid="active-users-card">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <UserCheck className="w-5 h-5 text-green-400" />
                <span className="text-xs text-green-400 flex items-center">
                  <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse mr-1" />
                  LIVE
                </span>
              </div>
              <p className="text-2xl font-bold mt-2">{live.activeUsers || 0}</p>
              <p className="text-xs text-gray-400">Active Users</p>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-blue-500/20 to-blue-600/10 border-blue-500/30" data-testid="total-users-card">
            <CardContent className="p-4">
              <Users className="w-5 h-5 text-blue-400" />
              <p className="text-2xl font-bold mt-2">{formatNumber(live.totalUsers)}</p>
              <p className="text-xs text-gray-400">Total Users</p>
              <p className="text-xs text-green-400 mt-1">+{live.newUsersToday || 0} today</p>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-purple-500/20 to-purple-600/10 border-purple-500/30" data-testid="generations-card">
            <CardContent className="p-4">
              <Sparkles className="w-5 h-5 text-purple-400" />
              <p className="text-2xl font-bold mt-2">{formatNumber(live.todayGenerations)}</p>
              <p className="text-xs text-gray-400">Generations Today</p>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-yellow-500/20 to-yellow-600/10 border-yellow-500/30" data-testid="logins-card">
            <CardContent className="p-4">
              <Activity className="w-5 h-5 text-yellow-400" />
              <p className="text-2xl font-bold mt-2">{formatNumber(live.todayLogins)}</p>
              <p className="text-xs text-gray-400">Logins Today</p>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-cyan-500/20 to-cyan-600/10 border-cyan-500/30" data-testid="credits-card">
            <CardContent className="p-4">
              <CreditCard className="w-5 h-5 text-cyan-400" />
              <p className="text-2xl font-bold mt-2">{formatNumber(live.creditsUsedToday)}</p>
              <p className="text-xs text-gray-400">Credits Used</p>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-emerald-500/20 to-emerald-600/10 border-emerald-500/30" data-testid="revenue-card">
            <CardContent className="p-4">
              <DollarSign className="w-5 h-5 text-emerald-400" />
              <p className="text-2xl font-bold mt-2">{formatCurrency(revenue.today)}</p>
              <p className="text-xs text-gray-400">Revenue Today</p>
            </CardContent>
          </Card>
        </div>

        {/* Performance & Charts */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
          {/* Success Rate */}
          <Card className="bg-[#12121a] border-gray-800" data-testid="success-rate-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <TrendingUp className="w-5 h-5 text-green-400" />
                Generation Success Rate
              </CardTitle>
              <CardDescription>Last 24 hours</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-end gap-4">
                <span className="text-5xl font-bold text-green-400">{perf.successRate}%</span>
                <div className="text-sm text-gray-400 mb-2">
                  <p>{perf.successfulJobs24h || 0} successful</p>
                  <p>{perf.failedJobs24h || 0} failed</p>
                </div>
              </div>
              <Progress value={perf.successRate || 0} className="mt-4 h-2" />
            </CardContent>
          </Card>

          {/* 7-Day Revenue */}
          <Card className="bg-[#12121a] border-gray-800" data-testid="weekly-revenue-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <DollarSign className="w-5 h-5 text-emerald-400" />
                Weekly Revenue
              </CardTitle>
              <CardDescription>Last 7 days</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-end gap-4">
                <span className="text-4xl font-bold text-emerald-400">
                  {formatCurrency(revenue.last7Days)}
                </span>
              </div>
              <div className="mt-4 flex items-center gap-2 text-sm">
                <span className="text-gray-400">Today:</span>
                <span className="text-white font-medium">{formatCurrency(revenue.today)}</span>
                {revenue.today > 0 && (
                  <ArrowUpRight className="w-4 h-4 text-green-400" />
                )}
              </div>
            </CardContent>
          </Card>

          {/* Generation by Type */}
          <Card className="bg-[#12121a] border-gray-800" data-testid="gen-by-type-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <PieChart className="w-5 h-5 text-purple-400" />
                Generations by Type
              </CardTitle>
              <CardDescription>Last 24 hours</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {(metrics?.generationsByType || []).slice(0, 5).map((item, index) => (
                  <div key={index} className="flex items-center justify-between">
                    <span className="text-sm text-gray-300">{item.type}</span>
                    <div className="flex items-center gap-2">
                      <div className="w-24 h-2 bg-gray-700 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full"
                          style={{ 
                            width: `${Math.min((item.count / (metrics?.generationsByType?.[0]?.count || 1)) * 100, 100)}%` 
                          }}
                        />
                      </div>
                      <span className="text-sm font-medium w-8 text-right">{item.count}</span>
                    </div>
                  </div>
                ))}
                {(!metrics?.generationsByType || metrics.generationsByType.length === 0) && (
                  <p className="text-gray-500 text-sm">No data available</p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Hourly Activity & Recent Activity */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Hourly Activity Chart */}
          <Card className="bg-[#12121a] border-gray-800" data-testid="hourly-activity-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <BarChart3 className="w-5 h-5 text-blue-400" />
                Hourly Activity
              </CardTitle>
              <CardDescription>Generations in the last 24 hours</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-end gap-1 h-40">
                {(metrics?.hourlyActivity || []).map((hour, index) => {
                  const maxVal = Math.max(...(metrics?.hourlyActivity || []).map(h => h.generations), 1);
                  const height = (hour.generations / maxVal) * 100;
                  return (
                    <div 
                      key={index} 
                      className="flex-1 flex flex-col items-center gap-1"
                      title={`${hour.hour}: ${hour.generations} generations`}
                    >
                      <div 
                        className="w-full bg-gradient-to-t from-blue-600 to-blue-400 rounded-t transition-all duration-300 hover:from-blue-500 hover:to-blue-300"
                        style={{ height: `${Math.max(height, 2)}%` }}
                      />
                      {index % 4 === 0 && (
                        <span className="text-[10px] text-gray-500">{hour.hour}</span>
                      )}
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Recent Activity Feed */}
          <Card className="bg-[#12121a] border-gray-800" data-testid="recent-activity-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Clock className="w-5 h-5 text-orange-400" />
                Recent Activity
              </CardTitle>
              <CardDescription>Live activity feed</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 max-h-64 overflow-y-auto">
                {(metrics?.recentActivity || []).map((activity, index) => (
                  <div 
                    key={index} 
                    className="flex items-center gap-3 p-2 rounded-lg bg-gray-800/50 hover:bg-gray-800 transition-colors"
                  >
                    <div className={`p-2 rounded-full ${
                      activity.type === 'generation' ? 'bg-purple-500/20' : 'bg-green-500/20'
                    }`}>
                      {activity.type === 'generation' ? (
                        <Sparkles className="w-4 h-4 text-purple-400" />
                      ) : (
                        <Users className="w-4 h-4 text-green-400" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white truncate">{activity.event}</p>
                      <p className="text-xs text-gray-500">
                        {activity.timestamp ? new Date(activity.timestamp).toLocaleTimeString() : 'Just now'}
                      </p>
                    </div>
                  </div>
                ))}
                {(!metrics?.recentActivity || metrics.recentActivity.length === 0) && (
                  <p className="text-gray-500 text-sm text-center py-4">No recent activity</p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 7-Day Trend */}
        <Card className="bg-[#12121a] border-gray-800 mt-6" data-testid="weekly-trend-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <TrendingUp className="w-5 h-5 text-cyan-400" />
              7-Day Generation Trend
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end justify-between gap-2 h-32">
              {trends.map((day, index) => {
                const maxVal = Math.max(...trends.map(d => d.generations), 1);
                const height = (day.generations / maxVal) * 100;
                return (
                  <div key={index} className="flex-1 flex flex-col items-center gap-2">
                    <span className="text-xs text-gray-400">{day.generations}</span>
                    <div 
                      className="w-full bg-gradient-to-t from-cyan-600 to-cyan-400 rounded-t transition-all duration-300 hover:from-cyan-500 hover:to-cyan-300"
                      style={{ height: `${Math.max(height, 5)}%` }}
                    />
                    <span className="text-xs text-gray-500">{day.day}</span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default RealtimeAnalytics;
