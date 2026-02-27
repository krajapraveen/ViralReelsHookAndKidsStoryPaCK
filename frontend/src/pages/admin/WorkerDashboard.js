import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { 
  ArrowLeft, Activity, Server, Cpu, BarChart3, TrendingUp, 
  TrendingDown, Zap, Clock, RefreshCw, AlertTriangle, 
  CheckCircle, Users, Layers, Play, Pause, Settings
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Progress } from '../../components/ui/progress';
import { toast } from 'sonner';
import api from '../../utils/api';

// Simple mini bar chart component
const MiniBarChart = ({ data, height = 40, color = '#8b5cf6' }) => {
  const maxValue = Math.max(...data, 1);
  return (
    <div className="flex items-end gap-0.5" style={{ height }}>
      {data.map((value, idx) => (
        <div
          key={idx}
          className="flex-1 rounded-t transition-all duration-300"
          style={{
            height: `${(value / maxValue) * 100}%`,
            backgroundColor: color,
            opacity: 0.3 + (idx / data.length) * 0.7
          }}
        />
      ))}
    </div>
  );
};

// Gauge component for utilization
const UtilizationGauge = ({ value, label, color }) => {
  const rotation = (value / 100) * 180 - 90;
  return (
    <div className="relative w-24 h-12 mx-auto">
      <svg viewBox="0 0 100 50" className="w-full h-full">
        {/* Background arc */}
        <path
          d="M 10 50 A 40 40 0 0 1 90 50"
          fill="none"
          stroke="#334155"
          strokeWidth="8"
        />
        {/* Value arc */}
        <path
          d="M 10 50 A 40 40 0 0 1 90 50"
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeDasharray={`${value * 1.26} 126`}
        />
        {/* Needle */}
        <line
          x1="50"
          y1="50"
          x2="50"
          y2="15"
          stroke="#fff"
          strokeWidth="2"
          transform={`rotate(${rotation}, 50, 50)`}
        />
        <circle cx="50" cy="50" r="4" fill="#fff" />
      </svg>
      <div className="absolute bottom-0 left-0 right-0 text-center">
        <span className="text-lg font-bold text-white">{value}%</span>
        <p className="text-xs text-slate-400">{label}</p>
      </div>
    </div>
  );
};

export default function WorkerDashboard() {
  const [metrics, setMetrics] = useState(null);
  const [loadBalancer, setLoadBalancer] = useState(null);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [history, setHistory] = useState({
    utilization: Array(20).fill(0),
    requests: Array(20).fill(0),
    queue: Array(20).fill(0)
  });

  const fetchMetrics = useCallback(async () => {
    try {
      const [metricsRes, loadBalancerRes] = await Promise.all([
        api.get('/api/admin/workers/metrics'),
        api.get('/api/admin/workers/load-balancer/status')
      ]);
      
      setMetrics(metricsRes.data);
      setLoadBalancer(loadBalancerRes.data);
      
      // Update history
      setHistory(prev => ({
        utilization: [...prev.utilization.slice(1), loadBalancerRes.data.overall_utilization || 0],
        requests: [...prev.requests.slice(1), metricsRes.data.pools?.length || 0],
        queue: [...prev.queue.slice(1), loadBalancerRes.data.total_queue_size || 0]
      }));
      
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch metrics:', error);
      if (error.response?.status === 403) {
        toast.error('Admin access required');
      }
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
    
    if (autoRefresh) {
      const interval = setInterval(fetchMetrics, 5000);
      return () => clearInterval(interval);
    }
  }, [fetchMetrics, autoRefresh]);

  const toggleAutoScaling = async (enabled) => {
    try {
      await api.post(`/api/admin/workers/auto-scaling/toggle?enabled=${enabled}`);
      toast.success(`Auto-scaling ${enabled ? 'enabled' : 'disabled'}`);
      fetchMetrics();
    } catch (error) {
      toast.error('Failed to toggle auto-scaling');
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy': return 'text-green-400 bg-green-500/20';
      case 'high_load': return 'text-yellow-400 bg-yellow-500/20';
      case 'critical': return 'text-red-400 bg-red-500/20';
      default: return 'text-slate-400 bg-slate-500/20';
    }
  };

  const getUtilizationColor = (util) => {
    if (util >= 90) return '#ef4444';
    if (util >= 70) return '#f59e0b';
    if (util >= 50) return '#8b5cf6';
    return '#22c55e';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-indigo-400 mx-auto mb-4" />
          <p className="text-slate-400">Loading worker metrics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link to="/admin" className="p-2 hover:bg-slate-800 rounded-lg transition-colors">
              <ArrowLeft className="w-5 h-5 text-slate-400" />
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                <Activity className="w-6 h-6 text-indigo-400" />
                Worker Dashboard
              </h1>
              <p className="text-slate-400 text-sm">Real-time worker utilization and metrics</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={autoRefresh ? 'border-green-500 text-green-400' : 'border-slate-600'}
            >
              {autoRefresh ? <Play className="w-4 h-4 mr-1" /> : <Pause className="w-4 h-4 mr-1" />}
              Auto-refresh: {autoRefresh ? 'ON' : 'OFF'}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={fetchMetrics}
            >
              <RefreshCw className="w-4 h-4 mr-1" />
              Refresh
            </Button>
          </div>
        </div>

        {/* System Status Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          {/* System Status */}
          <div className="bg-slate-900/50 border border-slate-700 rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-400 text-sm">System Status</span>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(loadBalancer?.status)}`}>
                {loadBalancer?.status?.toUpperCase() || 'UNKNOWN'}
              </span>
            </div>
            <div className="flex items-center gap-2">
              {loadBalancer?.status === 'healthy' ? (
                <CheckCircle className="w-8 h-8 text-green-400" />
              ) : loadBalancer?.status === 'critical' ? (
                <AlertTriangle className="w-8 h-8 text-red-400" />
              ) : (
                <Activity className="w-8 h-8 text-yellow-400" />
              )}
              <div>
                <p className="text-white font-bold text-lg">{loadBalancer?.total_workers || 0}</p>
                <p className="text-slate-400 text-xs">Total Workers</p>
              </div>
            </div>
          </div>

          {/* Overall Utilization */}
          <div className="bg-slate-900/50 border border-slate-700 rounded-xl p-4">
            <span className="text-slate-400 text-sm">Overall Utilization</span>
            <UtilizationGauge 
              value={loadBalancer?.overall_utilization || 0}
              label="CPU Load"
              color={getUtilizationColor(loadBalancer?.overall_utilization || 0)}
            />
            <MiniBarChart 
              data={history.utilization} 
              height={30}
              color={getUtilizationColor(loadBalancer?.overall_utilization || 0)}
            />
          </div>

          {/* Busy Workers */}
          <div className="bg-slate-900/50 border border-slate-700 rounded-xl p-4">
            <span className="text-slate-400 text-sm">Busy Workers</span>
            <div className="flex items-center justify-between mt-2">
              <div className="flex items-center gap-2">
                <Cpu className="w-6 h-6 text-purple-400" />
                <span className="text-2xl font-bold text-white">
                  {loadBalancer?.busy_workers || 0}
                </span>
                <span className="text-slate-500">/ {loadBalancer?.total_workers || 0}</span>
              </div>
            </div>
            <Progress 
              value={(loadBalancer?.busy_workers / Math.max(loadBalancer?.total_workers, 1)) * 100} 
              className="mt-3 h-2"
            />
          </div>

          {/* Queue Size */}
          <div className="bg-slate-900/50 border border-slate-700 rounded-xl p-4">
            <span className="text-slate-400 text-sm">Total Queue</span>
            <div className="flex items-center justify-between mt-2">
              <div className="flex items-center gap-2">
                <Layers className="w-6 h-6 text-amber-400" />
                <span className="text-2xl font-bold text-white">
                  {loadBalancer?.total_queue_size || 0}
                </span>
                <span className="text-slate-500">jobs</span>
              </div>
            </div>
            <MiniBarChart data={history.queue} height={30} color="#f59e0b" />
          </div>
        </div>

        {/* Auto-Scaling Controls */}
        <div className="bg-slate-900/50 border border-slate-700 rounded-xl p-4 mb-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Settings className="w-5 h-5 text-indigo-400" />
              <div>
                <h3 className="text-white font-semibold">Auto-Scaling Configuration</h3>
                <p className="text-slate-400 text-sm">
                  Scale up at {loadBalancer?.auto_scaling?.scale_up_threshold || 80}% utilization, 
                  scale down at {loadBalancer?.auto_scaling?.scale_down_threshold || 30}%
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className={`px-3 py-1 rounded-full text-sm ${loadBalancer?.auto_scaling?.enabled ? 'bg-green-500/20 text-green-400' : 'bg-slate-500/20 text-slate-400'}`}>
                {loadBalancer?.auto_scaling?.enabled ? 'Enabled' : 'Disabled'}
              </span>
              <Button
                size="sm"
                onClick={() => toggleAutoScaling(!loadBalancer?.auto_scaling?.enabled)}
                className={loadBalancer?.auto_scaling?.enabled ? 'bg-red-600 hover:bg-red-700' : 'bg-green-600 hover:bg-green-700'}
              >
                {loadBalancer?.auto_scaling?.enabled ? 'Disable' : 'Enable'}
              </Button>
            </div>
          </div>
        </div>

        {/* Worker Pools Grid */}
        <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
          <Server className="w-5 h-5 text-indigo-400" />
          Feature Worker Pools
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
          {loadBalancer?.pools?.map((pool, idx) => (
            <div key={idx} className="bg-slate-900/50 border border-slate-700 rounded-xl p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-white font-semibold capitalize">
                  {pool.feature?.replace(/_/g, ' ') || `Pool ${idx + 1}`}
                </h3>
                <span className={`px-2 py-1 rounded-full text-xs ${
                  pool.utilization >= 80 ? 'bg-red-500/20 text-red-400' :
                  pool.utilization >= 50 ? 'bg-yellow-500/20 text-yellow-400' :
                  'bg-green-500/20 text-green-400'
                }`}>
                  {pool.utilization || 0}% load
                </span>
              </div>
              
              <div className="grid grid-cols-3 gap-2 text-center mb-3">
                <div className="bg-slate-800/50 rounded-lg p-2">
                  <p className="text-lg font-bold text-white">{pool.workers || 0}</p>
                  <p className="text-xs text-slate-400">Workers</p>
                </div>
                <div className="bg-slate-800/50 rounded-lg p-2">
                  <p className="text-lg font-bold text-amber-400">{pool.busy || 0}</p>
                  <p className="text-xs text-slate-400">Busy</p>
                </div>
                <div className="bg-slate-800/50 rounded-lg p-2">
                  <p className="text-lg font-bold text-purple-400">{pool.queue || 0}</p>
                  <p className="text-xs text-slate-400">Queue</p>
                </div>
              </div>
              
              <Progress 
                value={pool.utilization || 0} 
                className="h-2"
              />
              
              <div className="flex items-center justify-between mt-3 text-xs text-slate-500">
                <span className="flex items-center gap-1">
                  {pool.utilization > 50 ? (
                    <TrendingUp className="w-3 h-3 text-amber-400" />
                  ) : (
                    <TrendingDown className="w-3 h-3 text-green-400" />
                  )}
                  {pool.utilization > 50 ? 'High demand' : 'Normal load'}
                </span>
                <span className="flex items-center gap-1">
                  <Zap className="w-3 h-3" />
                  Auto-scale ready
                </span>
              </div>
            </div>
          ))}
          
          {(!loadBalancer?.pools || loadBalancer.pools.length === 0) && (
            <div className="col-span-3 text-center py-12 text-slate-400">
              <Server className="w-12 h-12 mx-auto mb-4 text-slate-600" />
              <p>No worker pools active. Start generating content to see metrics.</p>
            </div>
          )}
        </div>

        {/* Performance Metrics */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Utilization Timeline */}
          <div className="bg-slate-900/50 border border-slate-700 rounded-xl p-4">
            <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-indigo-400" />
              Utilization Timeline (Last 2 minutes)
            </h3>
            <div className="h-32 flex items-end gap-1">
              {history.utilization.map((value, idx) => (
                <div
                  key={idx}
                  className="flex-1 rounded-t transition-all duration-300"
                  style={{
                    height: `${Math.max(value, 2)}%`,
                    backgroundColor: getUtilizationColor(value),
                    opacity: 0.4 + (idx / history.utilization.length) * 0.6
                  }}
                />
              ))}
            </div>
            <div className="flex justify-between text-xs text-slate-500 mt-2">
              <span>2 min ago</span>
              <span>Now</span>
            </div>
          </div>

          {/* Quick Stats */}
          <div className="bg-slate-900/50 border border-slate-700 rounded-xl p-4">
            <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
              <Clock className="w-5 h-5 text-indigo-400" />
              Performance Summary
            </h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Average Response Time</span>
                <span className="text-white font-mono">~250ms</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Jobs Processed (24h)</span>
                <span className="text-white font-mono">{metrics?.pools?.reduce((acc, p) => acc + (p.total_jobs_completed || 0), 0) || 0}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Failed Jobs (24h)</span>
                <span className="text-red-400 font-mono">{metrics?.pools?.reduce((acc, p) => acc + (p.total_jobs_failed || 0), 0) || 0}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Auto-scale Events</span>
                <span className="text-purple-400 font-mono">
                  <TrendingUp className="w-4 h-4 inline mr-1" />
                  {metrics?.pools?.reduce((acc, p) => acc + (p.scale_up_count || 0), 0) || 0}
                  <TrendingDown className="w-4 h-4 inline mx-1" />
                  {metrics?.pools?.reduce((acc, p) => acc + (p.scale_down_count || 0), 0) || 0}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center mt-8 text-slate-500 text-xs">
          Last updated: {new Date().toLocaleTimeString()} | Auto-refresh: {autoRefresh ? 'every 5s' : 'disabled'}
        </div>
      </div>
    </div>
  );
}
