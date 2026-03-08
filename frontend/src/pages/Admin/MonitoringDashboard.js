import React, { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, RefreshCw, Activity, Server, Zap, Clock, AlertTriangle,
  CheckCircle, XCircle, Play, Pause, Calendar, TrendingUp, Users,
  Database, Cpu, HardDrive, BarChart3, Timer, Target, Gauge
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Metric Card Component
const MetricCard = ({ title, value, subValue, icon: Icon, color, trend }) => {
  const colorClasses = {
    green: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    blue: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    purple: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    amber: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    red: 'bg-red-500/20 text-red-400 border-red-500/30',
    cyan: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30'
  };
  
  return (
    <div className={`p-4 rounded-xl border ${colorClasses[color]} backdrop-blur-sm`}>
      <div className="flex items-center justify-between mb-2">
        <Icon className="w-5 h-5" />
        {trend !== undefined && (
          <span className={`text-xs ${trend >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {trend >= 0 ? '↑' : '↓'} {Math.abs(trend)}%
          </span>
        )}
      </div>
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-sm opacity-70">{title}</p>
      {subValue && <p className="text-xs opacity-50 mt-1">{subValue}</p>}
    </div>
  );
};

// Health Status Badge
const HealthBadge = ({ status }) => {
  const config = {
    healthy: { color: 'bg-emerald-500', text: 'Healthy' },
    degraded: { color: 'bg-amber-500', text: 'Degraded' },
    critical: { color: 'bg-red-500', text: 'Critical' },
    busy: { color: 'bg-amber-500', text: 'Busy' },
    overloaded: { color: 'bg-red-500', text: 'Overloaded' }
  };
  const c = config[status] || config.healthy;
  
  return (
    <span className={`inline-flex items-center gap-2 px-3 py-1 rounded-full ${c.color}/20 text-sm`}>
      <span className={`w-2 h-2 rounded-full ${c.color} animate-pulse`}></span>
      {c.text}
    </span>
  );
};

export default function MonitoringDashboard() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  
  // Data states
  const [queueStatus, setQueueStatus] = useState(null);
  const [systemHealth, setSystemHealth] = useState(null);
  const [featureUsage, setFeatureUsage] = useState(null);
  const [loadTests, setLoadTests] = useState([]);
  const [scheduledTests, setScheduledTests] = useState([]);
  
  // Load test modal
  const [showLoadTestModal, setShowLoadTestModal] = useState(false);
  const [loadTestConfig, setLoadTestConfig] = useState({
    testType: 'api',
    numRequests: 20,
    concurrentUsers: 5
  });
  const [runningTest, setRunningTest] = useState(null);

  useEffect(() => {
    checkAdminAccess();
  }, []);

  useEffect(() => {
    if (isAdmin) {
      fetchAllData();
    }
  }, [isAdmin]);

  useEffect(() => {
    let interval;
    if (isAdmin && autoRefresh) {
      interval = setInterval(fetchAllData, 30000); // Refresh every 30 seconds
    }
    return () => clearInterval(interval);
  }, [isAdmin, autoRefresh]);

  const checkAdminAccess = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        navigate('/login');
        return;
      }

      const response = await fetch(`${API_URL}/api/auth/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const data = await response.json();
        const user = data.user || data;
        
        if (user.role?.toUpperCase() !== 'ADMIN') {
          toast.error('Admin access required');
          navigate('/app');
          return;
        }
        setIsAdmin(true);
      } else {
        navigate('/login');
      }
    } catch (error) {
      navigate('/login');
    }
  };

  const fetchWithAuth = async (url) => {
    const token = localStorage.getItem('token');
    const response = await fetch(url, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error(`Failed: ${url}`);
    return response.json();
  };

  const fetchAllData = async () => {
    try {
      const [queueRes, healthRes, usageRes, testsRes, scheduledRes] = await Promise.all([
        fetchWithAuth(`${API_URL}/api/monitoring/queue-status`).catch(() => null),
        fetchWithAuth(`${API_URL}/api/monitoring/system-health`).catch(() => null),
        fetchWithAuth(`${API_URL}/api/monitoring/feature-usage?days=7`).catch(() => null),
        fetchWithAuth(`${API_URL}/api/monitoring/load-test/history?limit=5`).catch(() => null),
        fetchWithAuth(`${API_URL}/api/monitoring/scheduled-tests`).catch(() => null)
      ]);

      if (queueRes?.success) setQueueStatus(queueRes);
      if (healthRes?.success) setSystemHealth(healthRes);
      if (usageRes?.success) setFeatureUsage(usageRes);
      if (testsRes?.success) setLoadTests(testsRes.tests || []);
      if (scheduledRes?.success) setScheduledTests(scheduledRes.schedules || []);
      
    } catch (error) {
      console.error('Fetch error:', error);
    } finally {
      setLoading(false);
    }
  };

  const startLoadTest = async () => {
    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams({
        test_type: loadTestConfig.testType,
        num_requests: loadTestConfig.numRequests,
        concurrent_users: loadTestConfig.concurrentUsers
      });

      const response = await fetch(`${API_URL}/api/monitoring/load-test/start?${params}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const data = await response.json();
        setRunningTest(data.testId);
        toast.success(`Load test started: ${data.testId}`);
        setShowLoadTestModal(false);
        
        // Poll for results
        pollTestResult(data.testId);
      }
    } catch (error) {
      toast.error('Failed to start load test');
    }
  };

  const pollTestResult = async (testId) => {
    const interval = setInterval(async () => {
      try {
        const result = await fetchWithAuth(`${API_URL}/api/monitoring/load-test/${testId}`);
        if (result.test?.status === 'completed' || result.test?.status === 'failed') {
          clearInterval(interval);
          setRunningTest(null);
          fetchAllData();
          toast.success('Load test completed!');
        }
      } catch (error) {
        clearInterval(interval);
      }
    }, 2000);
  };

  const scheduleTest = async (schedule) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/monitoring/schedule-test`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(schedule)
      });

      if (response.ok) {
        toast.success('Test scheduled successfully');
        fetchAllData();
      }
    } catch (error) {
      toast.error('Failed to schedule test');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-cyan-500 mx-auto mb-4" />
          <p className="text-slate-400">Loading monitoring data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 text-white" data-testid="monitoring-dashboard">
      {/* Header */}
      <header className="bg-slate-800/50 border-b border-slate-700 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app/admin">
              <button className="flex items-center gap-2 text-slate-300 hover:text-white transition-colors">
                <ArrowLeft className="w-5 h-5" />
                Back
              </button>
            </Link>
            <div className="flex items-center gap-2">
              <Activity className="w-6 h-6 text-cyan-500" />
              <h1 className="text-xl font-bold">System Monitoring</h1>
            </div>
            {systemHealth?.health && (
              <HealthBadge status={systemHealth.health.status} />
            )}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                autoRefresh ? 'bg-cyan-500/20 text-cyan-400' : 'bg-slate-700/50 text-slate-400'
              }`}
            >
              {autoRefresh ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
              Auto-refresh
            </button>
            <Button
              onClick={() => setShowLoadTestModal(true)}
              className="bg-gradient-to-r from-purple-500 to-indigo-500"
              disabled={runningTest}
            >
              <Zap className="w-4 h-4 mr-2" />
              {runningTest ? 'Test Running...' : 'Run Load Test'}
            </Button>
            <button
              onClick={fetchAllData}
              className="p-2 bg-slate-700/50 hover:bg-slate-600/50 rounded-lg"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* System Health Overview */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <MetricCard
            title="Health Score"
            value={`${systemHealth?.health?.score || 0}%`}
            icon={Gauge}
            color={systemHealth?.health?.score >= 80 ? 'green' : systemHealth?.health?.score >= 50 ? 'amber' : 'red'}
          />
          <MetricCard
            title="Queue Health"
            value={queueStatus?.queueStatus?.health || 'Unknown'}
            subValue={`${queueStatus?.queueStatus?.pending || 0} pending`}
            icon={Server}
            color={queueStatus?.queueStatus?.health === 'healthy' ? 'green' : 'amber'}
          />
          <MetricCard
            title="Success Rate"
            value={`${queueStatus?.queueStatus?.successRate || 0}%`}
            icon={Target}
            color={queueStatus?.queueStatus?.successRate >= 95 ? 'green' : 'amber'}
          />
          <MetricCard
            title="Active Users"
            value={systemHealth?.metrics?.activeUsers || 0}
            icon={Users}
            color="blue"
          />
          <MetricCard
            title="Credits/Hour"
            value={systemHealth?.metrics?.creditsUsedHour || 0}
            icon={Zap}
            color="purple"
          />
          <MetricCard
            title="DB Status"
            value={systemHealth?.health?.dbConnected ? 'Connected' : 'Error'}
            icon={Database}
            color={systemHealth?.health?.dbConnected ? 'green' : 'red'}
          />
        </div>

        {/* Queue Status Details */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Server className="w-5 h-5 text-cyan-400" />
              Generation Queue Status
            </h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-slate-700/30 rounded-lg">
                <p className="text-3xl font-bold text-amber-400">{queueStatus?.queueStatus?.pending || 0}</p>
                <p className="text-sm text-slate-400">Pending Jobs</p>
              </div>
              <div className="p-4 bg-slate-700/30 rounded-lg">
                <p className="text-3xl font-bold text-blue-400">{queueStatus?.queueStatus?.processing || 0}</p>
                <p className="text-sm text-slate-400">Processing</p>
              </div>
              <div className="p-4 bg-slate-700/30 rounded-lg">
                <p className="text-3xl font-bold text-emerald-400">{queueStatus?.queueStatus?.completedToday || 0}</p>
                <p className="text-sm text-slate-400">Completed Today</p>
              </div>
              <div className="p-4 bg-slate-700/30 rounded-lg">
                <p className="text-3xl font-bold text-red-400">{queueStatus?.queueStatus?.failedToday || 0}</p>
                <p className="text-sm text-slate-400">Failed Today</p>
              </div>
            </div>
            
            {/* Recent Failures */}
            {queueStatus?.recentFailures?.length > 0 && (
              <div className="mt-4">
                <h3 className="text-sm font-medium text-slate-400 mb-2">Recent Failures</h3>
                <div className="space-y-2 max-h-32 overflow-y-auto">
                  {queueStatus.recentFailures.map((failure, idx) => (
                    <div key={idx} className="flex items-center gap-2 p-2 bg-red-500/10 rounded-lg text-sm">
                      <XCircle className="w-4 h-4 text-red-400" />
                      <span className="text-slate-300">{failure.type}</span>
                      <span className="text-slate-500 text-xs">{failure.error?.substring(0, 50)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Feature Usage */}
          <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-purple-400" />
              Feature Usage (7 Days)
            </h2>
            <div className="space-y-3">
              {featureUsage?.featureUsage?.slice(0, 6).map((feature, idx) => {
                const maxCredits = Math.max(...(featureUsage.featureUsage.map(f => f.totalCredits) || [1]));
                const percentage = (feature.totalCredits / maxCredits) * 100;
                
                return (
                  <div key={idx}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm text-slate-300">{feature.feature}</span>
                      <span className="text-sm text-purple-400">{feature.totalCredits} credits</span>
                    </div>
                    <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-purple-500 to-indigo-500 rounded-full"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                    <p className="text-xs text-slate-500 mt-1">{feature.usageCount} uses • {feature.uniqueUsers} users</p>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Load Test History */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Timer className="w-5 h-5 text-amber-400" />
            Recent Load Tests
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-slate-400 border-b border-slate-700">
                  <th className="pb-3 font-medium">Test ID</th>
                  <th className="pb-3 font-medium">Type</th>
                  <th className="pb-3 font-medium">Requests</th>
                  <th className="pb-3 font-medium">Success Rate</th>
                  <th className="pb-3 font-medium">Avg Latency</th>
                  <th className="pb-3 font-medium">Req/Sec</th>
                  <th className="pb-3 font-medium">Status</th>
                  <th className="pb-3 font-medium">Date</th>
                </tr>
              </thead>
              <tbody>
                {loadTests.map((test) => (
                  <tr key={test.id} className="border-b border-slate-700/50">
                    <td className="py-3 font-mono text-sm text-cyan-400">{test.id}</td>
                    <td className="py-3 capitalize">{test.type}</td>
                    <td className="py-3">{test.numRequests}</td>
                    <td className="py-3">
                      <span className={test.stats?.successRate >= 95 ? 'text-emerald-400' : 'text-amber-400'}>
                        {test.stats?.successRate || 0}%
                      </span>
                    </td>
                    <td className="py-3">{test.stats?.avgLatencyMs?.toFixed(0) || 0}ms</td>
                    <td className="py-3">{test.stats?.requestsPerSecond?.toFixed(1) || 0}</td>
                    <td className="py-3">
                      <span className={`px-2 py-1 rounded-full text-xs ${
                        test.status === 'completed' ? 'bg-emerald-500/20 text-emerald-400' :
                        test.status === 'running' ? 'bg-amber-500/20 text-amber-400' :
                        'bg-red-500/20 text-red-400'
                      }`}>
                        {test.status}
                      </span>
                    </td>
                    <td className="py-3 text-sm text-slate-400">
                      {new Date(test.startedAt).toLocaleString()}
                    </td>
                  </tr>
                ))}
                {loadTests.length === 0 && (
                  <tr>
                    <td colSpan="8" className="py-8 text-center text-slate-500">
                      No load tests yet. Click "Run Load Test" to start.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Scheduled Tests */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <Calendar className="w-5 h-5 text-emerald-400" />
              Scheduled Tests
            </h2>
            <Button
              onClick={() => scheduleTest({
                type: 'api',
                numRequests: 50,
                concurrentUsers: 10,
                interval: 'daily',
                time: '03:00'
              })}
              variant="outline"
              size="sm"
              className="border-emerald-500/50 text-emerald-400"
            >
              <Clock className="w-4 h-4 mr-2" />
              Schedule Daily Test
            </Button>
          </div>
          <div className="space-y-3">
            {scheduledTests.length > 0 ? (
              scheduledTests.map((schedule, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg">
                  <div>
                    <p className="font-medium">{schedule.type} Test</p>
                    <p className="text-sm text-slate-400">
                      {schedule.numRequests} requests • {schedule.interval} at {schedule.time}
                    </p>
                  </div>
                  <span className="px-2 py-1 bg-emerald-500/20 text-emerald-400 rounded-full text-xs">
                    Active
                  </span>
                </div>
              ))
            ) : (
              <p className="text-slate-500 text-center py-4">
                No scheduled tests. Set up automated testing for continuous monitoring.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Load Test Modal */}
      {showLoadTestModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800 rounded-xl border border-slate-700 max-w-md w-full p-6">
            <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
              <Zap className="w-5 h-5 text-purple-400" />
              Configure Load Test
            </h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-slate-400 mb-2">Test Type</label>
                <select
                  value={loadTestConfig.testType}
                  onChange={(e) => setLoadTestConfig(prev => ({ ...prev, testType: e.target.value }))}
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2"
                >
                  <option value="api">API Endpoint Test</option>
                  <option value="generation">Generation Queue Test</option>
                  <option value="concurrent">Concurrent User Test</option>
                  <option value="stress">Stress Test (Heavy Load)</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm text-slate-400 mb-2">Number of Requests</label>
                <input
                  type="number"
                  value={loadTestConfig.numRequests}
                  onChange={(e) => setLoadTestConfig(prev => ({ ...prev, numRequests: parseInt(e.target.value) }))}
                  min="1"
                  max="100"
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2"
                />
              </div>
              
              <div>
                <label className="block text-sm text-slate-400 mb-2">Concurrent Users</label>
                <input
                  type="number"
                  value={loadTestConfig.concurrentUsers}
                  onChange={(e) => setLoadTestConfig(prev => ({ ...prev, concurrentUsers: parseInt(e.target.value) }))}
                  min="1"
                  max="20"
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2"
                />
              </div>
            </div>
            
            <div className="flex gap-3 mt-6">
              <Button
                onClick={() => setShowLoadTestModal(false)}
                variant="outline"
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                onClick={startLoadTest}
                className="flex-1 bg-gradient-to-r from-purple-500 to-indigo-500"
              >
                <Play className="w-4 h-4 mr-2" />
                Start Test
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
