import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { 
  Activity, Users, Zap, TrendingUp, DollarSign, Clock, 
  RefreshCw, ArrowLeft, Sparkles, UserCheck, CreditCard,
  BarChart3, PieChart, ArrowUpRight, ArrowDownRight, Download,
  FileText, Bell, BellOff, AlertTriangle, CheckCircle, Calendar,
  Filter, Settings, Heart, Wifi, WifiOff
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
  const [revenueBreakdown, setRevenueBreakdown] = useState(null);
  const [alertHistory, setAlertHistory] = useState([]);
  const [systemHealth, setSystemHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [wsConnected, setWsConnected] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  
  // Date range filter
  const [dateRange, setDateRange] = useState('7d');
  const [customStartDate, setCustomStartDate] = useState('');
  const [customEndDate, setCustomEndDate] = useState('');
  const [trendDays, setTrendDays] = useState(7);
  
  // WebSocket ref
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  // Calculate date range
  const getDateRange = () => {
    const now = new Date();
    let start, end = now.toISOString();
    
    switch (dateRange) {
      case '1d':
        start = new Date(now - 24 * 60 * 60 * 1000).toISOString();
        break;
      case '7d':
        start = new Date(now - 7 * 24 * 60 * 60 * 1000).toISOString();
        break;
      case '30d':
        start = new Date(now - 30 * 24 * 60 * 60 * 1000).toISOString();
        break;
      case '90d':
        start = new Date(now - 90 * 24 * 60 * 60 * 1000).toISOString();
        break;
      case 'custom':
        start = customStartDate ? new Date(customStartDate).toISOString() : null;
        end = customEndDate ? new Date(customEndDate).toISOString() : now.toISOString();
        break;
      default:
        start = new Date(now - 7 * 24 * 60 * 60 * 1000).toISOString();
    }
    
    return { start, end };
  };

  // WebSocket connection with exponential backoff
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 10;
  const baseReconnectDelay = 1000; // 1 second
  
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    
    const wsUrl = API.replace('https://', 'wss://').replace('http://', 'ws://');
    const token = localStorage.getItem('token');
    
    try {
      wsRef.current = new WebSocket(`${wsUrl}/api/realtime-analytics/ws?token=${token}`);
      
      wsRef.current.onopen = () => {
        setWsConnected(true);
        reconnectAttemptsRef.current = 0; // Reset on successful connection
        console.log('WebSocket connected');
      };
      
      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'snapshot' || data.type === 'update') {
            setMetrics(data.data);
            setLastUpdate(new Date());
          }
        } catch (e) {
          console.error('WebSocket message error:', e);
        }
      };
      
      wsRef.current.onclose = (event) => {
        setWsConnected(false);
        
        // Exponential backoff reconnection
        if (autoRefresh && reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = Math.min(
            baseReconnectDelay * Math.pow(2, reconnectAttemptsRef.current),
            30000 // Max 30 seconds
          );
          reconnectAttemptsRef.current++;
          console.log(`WebSocket closed. Reconnecting in ${delay/1000}s (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`);
          reconnectTimeoutRef.current = setTimeout(connectWebSocket, delay);
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          console.log('Max reconnection attempts reached. Using polling fallback.');
        }
      };
      
      wsRef.current.onerror = (error) => {
        setWsConnected(false);
        console.error('WebSocket error:', error);
      };
    } catch (e) {
      console.error('WebSocket connection error:', e);
      setWsConnected(false);
    }
  }, [autoRefresh]);

  const fetchMetrics = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      const { start, end } = getDateRange();
      
      const params = new URLSearchParams();
      if (start) params.append('start_date', start);
      if (end) params.append('end_date', end);
      
      const [metricsRes, trendsRes] = await Promise.all([
        axios.get(`${API}/api/realtime-analytics/snapshot?${params.toString()}`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API}/api/realtime-analytics/generation-trends?days=${trendDays}`, {
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
  }, [navigate, dateRange, customStartDate, customEndDate, trendDays]);

  const fetchRevenueBreakdown = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      const days = dateRange === '1d' ? 1 : dateRange === '7d' ? 7 : dateRange === '30d' ? 30 : 90;
      
      const res = await axios.get(`${API}/api/realtime-analytics/revenue-breakdown?days=${days}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setRevenueBreakdown(res.data);
    } catch (error) {
      console.error('Error fetching revenue:', error);
    }
  }, [dateRange]);

  const fetchAlertHistory = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await axios.get(`${API}/api/realtime-analytics/alerts/history?days=7`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setAlertHistory(res.data.alerts || []);
    } catch (error) {
      console.error('Error fetching alerts:', error);
    }
  }, []);

  const fetchSystemHealth = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await axios.get(`${API}/api/realtime-analytics/monitoring/health`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSystemHealth(res.data);
    } catch (error) {
      console.error('Error fetching health:', error);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
    fetchRevenueBreakdown();
    fetchAlertHistory();
    fetchSystemHealth();
    
    // Try WebSocket connection
    connectWebSocket();
    
    // Fallback polling if WebSocket fails
    let interval;
    if (autoRefresh && !wsConnected) {
      interval = setInterval(() => {
        fetchMetrics();
        fetchSystemHealth();
      }, 30000);
    }
    
    return () => {
      if (interval) clearInterval(interval);
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [fetchMetrics, fetchRevenueBreakdown, fetchAlertHistory, fetchSystemHealth, autoRefresh, wsConnected, connectWebSocket]);

  // Export functions
  const exportCSV = async (dataType) => {
    try {
      const token = localStorage.getItem('token');
      const days = dateRange === '1d' ? 1 : dateRange === '7d' ? 7 : dateRange === '30d' ? 30 : 90;
      
      const response = await axios.get(
        `${API}/api/realtime-analytics/export/csv?data_type=${dataType}&days=${days}`,
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `creatorstudio_${dataType}_${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success(`${dataType} data exported to CSV`);
    } catch (error) {
      toast.error('Export failed');
    }
  };

  const exportPDF = async () => {
    try {
      const token = localStorage.getItem('token');
      const days = dateRange === '1d' ? 1 : dateRange === '7d' ? 7 : dateRange === '30d' ? 30 : 7;
      
      const response = await axios.get(
        `${API}/api/realtime-analytics/export/pdf?days=${days}`,
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `creatorstudio_analytics_${new Date().toISOString().split('T')[0]}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success('Analytics report exported to PDF');
    } catch (error) {
      toast.error('PDF export failed');
    }
  };

  const sendTestAlert = async () => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/api/realtime-analytics/alerts/test`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Test alert sent to admin email');
      fetchAlertHistory();
    } catch (error) {
      toast.error('Failed to send test alert');
    }
  };

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
      <div className="max-w-7xl mx-auto">
        {/* Header */}
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
              <p className="text-gray-400 text-sm mt-1 flex items-center gap-2">
                Live platform metrics and performance
                {wsConnected ? (
                  <span className="flex items-center gap-1 text-green-400 text-xs">
                    <Wifi className="w-3 h-3" /> WebSocket
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-yellow-400 text-xs">
                    <WifiOff className="w-3 h-3" /> Polling
                  </span>
                )}
              </p>
            </div>
          </div>
          
          <div className="flex flex-wrap items-center gap-2">
            {/* Date Range Filter */}
            <select
              value={dateRange}
              onChange={(e) => setDateRange(e.target.value)}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
              data-testid="date-range-filter"
            >
              <option value="1d">Last 24 hours</option>
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
              <option value="90d">Last 90 days</option>
              <option value="custom">Custom range</option>
            </select>
            
            {dateRange === 'custom' && (
              <div className="flex items-center gap-2">
                <input
                  type="date"
                  value={customStartDate}
                  onChange={(e) => setCustomStartDate(e.target.value)}
                  className="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1 text-sm"
                />
                <span className="text-gray-500">to</span>
                <input
                  type="date"
                  value={customEndDate}
                  onChange={(e) => setCustomEndDate(e.target.value)}
                  className="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1 text-sm"
                />
              </div>
            )}
            
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <div className={`w-2 h-2 rounded-full ${autoRefresh ? 'bg-green-400 animate-pulse' : 'bg-gray-500'}`} />
              {lastUpdate && lastUpdate.toLocaleTimeString()}
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
            
            <Button variant="outline" size="sm" onClick={fetchMetrics} data-testid="refresh-btn">
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {['overview', 'revenue', 'monitoring', 'alerts', 'export'].map((tab) => (
            <Button
              key={tab}
              variant={activeTab === tab ? "default" : "outline"}
              size="sm"
              onClick={() => setActiveTab(tab)}
              className={activeTab === tab ? "bg-purple-600" : ""}
              data-testid={`tab-${tab}`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </Button>
          ))}
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <>
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

              <Card className="bg-gradient-to-br from-blue-500/20 to-blue-600/10 border-blue-500/30">
                <CardContent className="p-4">
                  <Users className="w-5 h-5 text-blue-400" />
                  <p className="text-2xl font-bold mt-2">{formatNumber(live.totalUsers)}</p>
                  <p className="text-xs text-gray-400">Total Users</p>
                  <p className="text-xs text-green-400 mt-1">+{live.newUsersToday || 0} today</p>
                </CardContent>
              </Card>

              <Card className="bg-gradient-to-br from-purple-500/20 to-purple-600/10 border-purple-500/30">
                <CardContent className="p-4">
                  <Sparkles className="w-5 h-5 text-purple-400" />
                  <p className="text-2xl font-bold mt-2">{formatNumber(live.todayGenerations)}</p>
                  <p className="text-xs text-gray-400">Generations Today</p>
                </CardContent>
              </Card>

              <Card className="bg-gradient-to-br from-yellow-500/20 to-yellow-600/10 border-yellow-500/30">
                <CardContent className="p-4">
                  <Activity className="w-5 h-5 text-yellow-400" />
                  <p className="text-2xl font-bold mt-2">{formatNumber(live.todayLogins)}</p>
                  <p className="text-xs text-gray-400">Logins Today</p>
                </CardContent>
              </Card>

              <Card className="bg-gradient-to-br from-cyan-500/20 to-cyan-600/10 border-cyan-500/30">
                <CardContent className="p-4">
                  <CreditCard className="w-5 h-5 text-cyan-400" />
                  <p className="text-2xl font-bold mt-2">{formatNumber(live.creditsUsedToday)}</p>
                  <p className="text-xs text-gray-400">Credits Used</p>
                </CardContent>
              </Card>

              <Card className="bg-gradient-to-br from-emerald-500/20 to-emerald-600/10 border-emerald-500/30">
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
              <Card className="bg-[#12121a] border-gray-800">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <TrendingUp className="w-5 h-5 text-green-400" />
                    Generation Success Rate
                  </CardTitle>
                  <CardDescription>Last 24 hours</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-end gap-4">
                    <span className={`text-5xl font-bold ${perf.successRate >= 80 ? 'text-green-400' : perf.successRate >= 50 ? 'text-yellow-400' : 'text-red-400'}`}>
                      {perf.successRate}%
                    </span>
                    <div className="text-sm text-gray-400 mb-2">
                      <p>{perf.successfulJobs24h || 0} successful</p>
                      <p>{perf.failedJobs24h || 0} failed</p>
                    </div>
                  </div>
                  <Progress value={perf.successRate || 0} className="mt-4 h-2" />
                </CardContent>
              </Card>

              {/* Weekly Revenue */}
              <Card className="bg-[#12121a] border-gray-800">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <DollarSign className="w-5 h-5 text-emerald-400" />
                    Weekly Revenue
                  </CardTitle>
                  <CardDescription>Last 7 days</CardDescription>
                </CardHeader>
                <CardContent>
                  <span className="text-4xl font-bold text-emerald-400">
                    {formatCurrency(revenue.last7Days)}
                  </span>
                  <div className="mt-4 flex items-center gap-2 text-sm">
                    <span className="text-gray-400">Today:</span>
                    <span className="text-white font-medium">{formatCurrency(revenue.today)}</span>
                    {revenue.today > 0 && <ArrowUpRight className="w-4 h-4 text-green-400" />}
                  </div>
                </CardContent>
              </Card>

              {/* Generations by Type */}
              <Card className="bg-[#12121a] border-gray-800">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <PieChart className="w-5 h-5 text-purple-400" />
                    Generations by Type
                  </CardTitle>
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
                              style={{ width: `${Math.min((item.count / (metrics?.generationsByType?.[0]?.count || 1)) * 100, 100)}%` }}
                            />
                          </div>
                          <span className="text-sm font-medium w-8 text-right">{item.count}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Hourly Activity & Recent Activity */}
            <div className="grid lg:grid-cols-2 gap-6 mb-6">
              {/* Hourly Activity Chart */}
              <Card className="bg-[#12121a] border-gray-800">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <BarChart3 className="w-5 h-5 text-blue-400" />
                    Hourly Activity
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-end gap-1 h-40">
                    {(metrics?.hourlyActivity || []).map((hour, index) => {
                      const maxVal = Math.max(...(metrics?.hourlyActivity || []).map(h => h.generations), 1);
                      const height = (hour.generations / maxVal) * 100;
                      return (
                        <div key={index} className="flex-1 flex flex-col items-center gap-1" title={`${hour.hour}: ${hour.generations}`}>
                          <div 
                            className="w-full bg-gradient-to-t from-blue-600 to-blue-400 rounded-t transition-all duration-300 hover:from-blue-500"
                            style={{ height: `${Math.max(height, 2)}%` }}
                          />
                          {index % 4 === 0 && <span className="text-[10px] text-gray-500">{hour.hour}</span>}
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>

              {/* Recent Activity Feed */}
              <Card className="bg-[#12121a] border-gray-800">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Clock className="w-5 h-5 text-orange-400" />
                    Recent Activity
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3 max-h-64 overflow-y-auto">
                    {(metrics?.recentActivity || []).map((activity, index) => (
                      <div key={index} className="flex items-center gap-3 p-2 rounded-lg bg-gray-800/50">
                        <div className={`p-2 rounded-full ${activity.type === 'generation' ? 'bg-purple-500/20' : 'bg-green-500/20'}`}>
                          {activity.type === 'generation' ? <Sparkles className="w-4 h-4 text-purple-400" /> : <Users className="w-4 h-4 text-green-400" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-white truncate">{activity.event}</p>
                          <p className="text-xs text-gray-500">{activity.timestamp ? new Date(activity.timestamp).toLocaleTimeString() : 'Just now'}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* 7-Day Trend */}
            <Card className="bg-[#12121a] border-gray-800">
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <TrendingUp className="w-5 h-5 text-cyan-400" />
                    Generation Trend
                  </CardTitle>
                </div>
                <select
                  value={trendDays}
                  onChange={(e) => setTrendDays(Number(e.target.value))}
                  className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm"
                >
                  <option value={7}>7 days</option>
                  <option value={14}>14 days</option>
                  <option value={30}>30 days</option>
                </select>
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
                          className="w-full bg-gradient-to-t from-cyan-600 to-cyan-400 rounded-t"
                          style={{ height: `${Math.max(height, 5)}%` }}
                        />
                        <span className="text-xs text-gray-500">{day.day}</span>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          </>
        )}

        {/* Revenue Tab */}
        {activeTab === 'revenue' && revenueBreakdown && (
          <div className="space-y-6">
            {/* Summary */}
            <div className="grid md:grid-cols-3 gap-4">
              <Card className="bg-gradient-to-br from-emerald-500/20 to-emerald-600/10 border-emerald-500/30">
                <CardContent className="p-6">
                  <p className="text-sm text-gray-400">Total Revenue</p>
                  <p className="text-3xl font-bold text-emerald-400">{formatCurrency(revenueBreakdown.summary?.totalRevenue)}</p>
                  <p className="text-xs text-gray-500 mt-1">{revenueBreakdown.period}</p>
                </CardContent>
              </Card>
              <Card className="bg-[#12121a] border-gray-800">
                <CardContent className="p-6">
                  <p className="text-sm text-gray-400">Total Transactions</p>
                  <p className="text-3xl font-bold">{revenueBreakdown.summary?.totalTransactions || 0}</p>
                </CardContent>
              </Card>
              <Card className="bg-[#12121a] border-gray-800">
                <CardContent className="p-6">
                  <p className="text-sm text-gray-400">Avg Transaction</p>
                  <p className="text-3xl font-bold">{formatCurrency(revenueBreakdown.summary?.avgTransactionValue)}</p>
                </CardContent>
              </Card>
            </div>

            {/* Revenue by Plan */}
            <Card className="bg-[#12121a] border-gray-800">
              <CardHeader>
                <CardTitle>Revenue by Plan</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {(revenueBreakdown.byPlan || []).map((plan, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
                      <div>
                        <p className="font-medium">{plan.plan}</p>
                        <p className="text-xs text-gray-400">{plan.transactions} transactions</p>
                      </div>
                      <div className="text-right">
                        <p className="font-bold text-emerald-400">{formatCurrency(plan.revenue)}</p>
                        <p className="text-xs text-gray-400">Avg: {formatCurrency(plan.avgTransaction)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Daily Revenue Trend */}
            <Card className="bg-[#12121a] border-gray-800">
              <CardHeader>
                <CardTitle>Daily Revenue Trend</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-end gap-2 h-40">
                  {(revenueBreakdown.dailyTrend || []).map((day, index) => {
                    const maxVal = Math.max(...(revenueBreakdown.dailyTrend || []).map(d => d.revenue), 1);
                    const height = (day.revenue / maxVal) * 100;
                    return (
                      <div key={index} className="flex-1 flex flex-col items-center gap-1" title={`${day.date}: ${formatCurrency(day.revenue)}`}>
                        <div 
                          className="w-full bg-gradient-to-t from-emerald-600 to-emerald-400 rounded-t"
                          style={{ height: `${Math.max(height, 2)}%` }}
                        />
                        {index % 5 === 0 && <span className="text-[10px] text-gray-500">{day.day}</span>}
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>

            {/* Top Users */}
            <Card className="bg-[#12121a] border-gray-800">
              <CardHeader>
                <CardTitle>Top Spending Users</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {(revenueBreakdown.topUsers || []).map((user, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <span className="w-6 h-6 rounded-full bg-purple-500/20 flex items-center justify-center text-xs font-bold text-purple-400">
                          {index + 1}
                        </span>
                        <div>
                          <p className="font-medium">{user.email}</p>
                          <p className="text-xs text-gray-400">{user.transactions} transactions</p>
                        </div>
                      </div>
                      <p className="font-bold text-emerald-400">{formatCurrency(user.totalSpent)}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Monitoring Tab */}
        {activeTab === 'monitoring' && systemHealth && (
          <div className="space-y-6">
            {/* System Status */}
            <Card className={`border-2 ${systemHealth.status === 'healthy' ? 'border-green-500/50 bg-green-500/10' : 'border-yellow-500/50 bg-yellow-500/10'}`}>
              <CardContent className="p-6">
                <div className="flex items-center gap-4">
                  {systemHealth.status === 'healthy' ? (
                    <CheckCircle className="w-12 h-12 text-green-400" />
                  ) : (
                    <AlertTriangle className="w-12 h-12 text-yellow-400" />
                  )}
                  <div>
                    <h2 className="text-2xl font-bold">System Status: {systemHealth.status.toUpperCase()}</h2>
                    <p className="text-gray-400">Last checked: {new Date(systemHealth.timestamp).toLocaleString()}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Components Status */}
            <div className="grid md:grid-cols-3 gap-4">
              {Object.entries(systemHealth.components || {}).map(([name, status]) => (
                <Card key={name} className="bg-[#12121a] border-gray-800">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <span className="capitalize">{name}</span>
                      <span className={`px-2 py-1 rounded text-xs ${status === 'healthy' ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'}`}>
                        {status}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Metrics */}
            <Card className="bg-[#12121a] border-gray-800">
              <CardHeader>
                <CardTitle>Performance Metrics (Last Hour)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-4 gap-4">
                  <div className="p-4 bg-gray-800/50 rounded-lg">
                    <p className="text-sm text-gray-400">Error Rate</p>
                    <p className="text-2xl font-bold">{systemHealth.metrics?.errorRate1h}</p>
                  </div>
                  <div className="p-4 bg-gray-800/50 rounded-lg">
                    <p className="text-sm text-gray-400">Total Jobs</p>
                    <p className="text-2xl font-bold">{systemHealth.metrics?.totalJobs1h}</p>
                  </div>
                  <div className="p-4 bg-gray-800/50 rounded-lg">
                    <p className="text-sm text-gray-400">Failed Jobs</p>
                    <p className="text-2xl font-bold">{systemHealth.metrics?.failedJobs1h}</p>
                  </div>
                  <div className="p-4 bg-gray-800/50 rounded-lg">
                    <p className="text-sm text-gray-400">Recent Activity (5min)</p>
                    <p className="text-2xl font-bold">{systemHealth.metrics?.recentActivity5min}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* System Resources */}
            <Card className="bg-[#12121a] border-gray-800">
              <CardHeader>
                <CardTitle>System Resources</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <div className="flex justify-between mb-2">
                      <span>CPU Usage</span>
                      <span>{systemHealth.system?.cpuPercent}%</span>
                    </div>
                    <Progress value={typeof systemHealth.system?.cpuPercent === 'number' ? systemHealth.system.cpuPercent : 0} className="h-2" />
                  </div>
                  <div>
                    <div className="flex justify-between mb-2">
                      <span>Memory Usage</span>
                      <span>{systemHealth.system?.memoryPercent}%</span>
                    </div>
                    <Progress value={typeof systemHealth.system?.memoryPercent === 'number' ? systemHealth.system.memoryPercent : 0} className="h-2" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Alerts Tab */}
        {activeTab === 'alerts' && (
          <div className="space-y-6">
            {/* Alert Actions */}
            <Card className="bg-[#12121a] border-gray-800">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bell className="w-5 h-5 text-yellow-400" />
                  Alert Configuration
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-4">
                  <Button onClick={sendTestAlert} variant="outline" data-testid="test-alert-btn">
                    <Bell className="w-4 h-4 mr-2" />
                    Send Test Alert
                  </Button>
                  <div className="flex items-center gap-2 text-sm text-gray-400">
                    <CheckCircle className="w-4 h-4 text-green-400" />
                    Email alerts configured
                  </div>
                </div>
                
                <div className="mt-4 p-4 bg-gray-800/50 rounded-lg">
                  <h4 className="font-medium mb-2">Alert Thresholds</h4>
                  <div className="grid md:grid-cols-2 gap-2 text-sm">
                    <p>Failed Jobs Rate: &gt;20%</p>
                    <p>Failed Logins (15min): &gt;10</p>
                    <p>New User Spike (1h): &gt;50</p>
                    <p>Alert Cooldown: 30 minutes</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Alert History */}
            <Card className="bg-[#12121a] border-gray-800">
              <CardHeader>
                <CardTitle>Recent Alerts</CardTitle>
                <CardDescription>Last 7 days</CardDescription>
              </CardHeader>
              <CardContent>
                {alertHistory.length > 0 ? (
                  <div className="space-y-3">
                    {alertHistory.map((alert, index) => (
                      <div key={index} className="p-4 bg-gray-800/50 rounded-lg border-l-4 border-yellow-500">
                        <div className="flex justify-between">
                          <h4 className="font-medium">{alert.subject}</h4>
                          <span className="text-xs text-gray-400">
                            {new Date(alert.sentAt).toLocaleString()}
                          </span>
                        </div>
                        <p className="text-sm text-gray-400 mt-1">{alert.message}</p>
                        <p className="text-xs text-gray-500 mt-2">Type: {alert.type}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-8">No alerts in the last 7 days</p>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* Export Tab */}
        {activeTab === 'export' && (
          <div className="space-y-6">
            <Card className="bg-[#12121a] border-gray-800">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Download className="w-5 h-5 text-blue-400" />
                  Export Analytics Data
                </CardTitle>
                <CardDescription>Download analytics data in CSV or PDF format</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-2 gap-6">
                  {/* CSV Exports */}
                  <div>
                    <h4 className="font-medium mb-4 flex items-center gap-2">
                      <FileText className="w-4 h-4" />
                      CSV Exports
                    </h4>
                    <div className="space-y-3">
                      <Button onClick={() => exportCSV('overview')} variant="outline" className="w-full justify-start" data-testid="export-overview-csv">
                        <Download className="w-4 h-4 mr-2" />
                        Overview Data (Daily Stats)
                      </Button>
                      <Button onClick={() => exportCSV('generations')} variant="outline" className="w-full justify-start" data-testid="export-generations-csv">
                        <Download className="w-4 h-4 mr-2" />
                        Generation History
                      </Button>
                      <Button onClick={() => exportCSV('revenue')} variant="outline" className="w-full justify-start" data-testid="export-revenue-csv">
                        <Download className="w-4 h-4 mr-2" />
                        Revenue & Payments
                      </Button>
                      <Button onClick={() => exportCSV('users')} variant="outline" className="w-full justify-start" data-testid="export-users-csv">
                        <Download className="w-4 h-4 mr-2" />
                        User Data
                      </Button>
                    </div>
                  </div>

                  {/* PDF Export */}
                  <div>
                    <h4 className="font-medium mb-4 flex items-center gap-2">
                      <FileText className="w-4 h-4" />
                      PDF Report
                    </h4>
                    <div className="space-y-3">
                      <Button onClick={exportPDF} className="w-full bg-purple-600 hover:bg-purple-700" data-testid="export-pdf">
                        <Download className="w-4 h-4 mr-2" />
                        Download Analytics Report (PDF)
                      </Button>
                      <p className="text-sm text-gray-400">
                        Includes: Live metrics, performance stats, revenue summary, and generation breakdown
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
};

export default RealtimeAnalytics;
