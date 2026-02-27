import React, { useState, useEffect, useCallback } from 'react';
import { ArrowLeft, RefreshCw, Activity, Shield, AlertTriangle, CheckCircle, Clock, DollarSign, Loader2, TrendingUp, Server, Zap } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function SystemResilienceDashboard() {
  // Get user and token from localStorage (consistent with other admin pages)
  const [user, setUser] = useState(null);
  const token = localStorage.getItem('token');
  const navigate = useNavigate();
  
  // Load user data from localStorage on mount
  useEffect(() => {
    try {
      const storedUser = localStorage.getItem('user');
      if (storedUser) {
        const parsedUser = JSON.parse(storedUser);
        // Check if user is admin
        if (parsedUser.role === 'ADMIN' || parsedUser.isAdmin) {
          setUser(parsedUser);
        } else {
          // Not an admin, redirect
          navigate('/app');
        }
      } else if (!token) {
        navigate('/login');
      }
    } catch (err) {
      console.error('Failed to load user:', err);
      navigate('/login');
    }
  }, [token, navigate]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [dashboardData, setDashboardData] = useState(null);
  const [refundDetails, setRefundDetails] = useState(null);
  const [incidentDetails, setIncidentDetails] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [error, setError] = useState(null);

  const fetchDashboard = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/system-resilience/dashboard`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!response.ok) throw new Error('Failed to fetch dashboard');
      
      const data = await response.json();
      setDashboardData(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }, [token]);

  const fetchRefundDetails = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/system-resilience/auto-refunds?days=7`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!response.ok) throw new Error('Failed to fetch refund details');
      
      const data = await response.json();
      setRefundDetails(data);
    } catch (err) {
      console.error('Refund details error:', err);
    }
  }, [token]);

  const fetchIncidentDetails = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/system-resilience/self-healing/incidents?days=7`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!response.ok) throw new Error('Failed to fetch incidents');
      
      const data = await response.json();
      setIncidentDetails(data);
    } catch (err) {
      console.error('Incident details error:', err);
    }
  }, [token]);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([
        fetchDashboard(),
        fetchRefundDetails(),
        fetchIncidentDetails()
      ]);
      setLoading(false);
    };
    
    loadData();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchDashboard, 30000);
    return () => clearInterval(interval);
  }, [fetchDashboard, fetchRefundDetails, fetchIncidentDetails]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await Promise.all([
      fetchDashboard(),
      fetchRefundDetails(),
      fetchIncidentDetails()
    ]);
    setRefreshing(false);
  };

  const getHealthColor = (status) => {
    switch (status) {
      case 'excellent': return 'text-green-400';
      case 'good': return 'text-blue-400';
      case 'degraded': return 'text-yellow-400';
      case 'critical': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  const getHealthBg = (status) => {
    switch (status) {
      case 'excellent': return 'bg-green-500/20 border-green-500/30';
      case 'good': return 'bg-blue-500/20 border-blue-500/30';
      case 'degraded': return 'bg-yellow-500/20 border-yellow-500/30';
      case 'critical': return 'bg-red-500/20 border-red-500/30';
      default: return 'bg-gray-500/20 border-gray-500/30';
    }
  };

  if (!user?.isAdmin) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 flex items-center justify-center">
        <div className="text-center">
          <Shield className="w-16 h-16 text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-white mb-2">Admin Access Required</h2>
          <p className="text-slate-400">This dashboard is only accessible to administrators.</p>
          <Link to="/dashboard" className="mt-4 inline-block text-purple-400 hover:text-purple-300">
            Return to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950" data-testid="system-resilience-dashboard">
      {/* Header */}
      <div className="border-b border-slate-800/50 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to="/admin" className="text-slate-400 hover:text-white transition-colors">
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div>
                <h1 className="text-xl font-bold text-white flex items-center gap-2">
                  <Activity className="w-5 h-5 text-purple-400" />
                  System Resilience Dashboard
                </h1>
                <p className="text-sm text-slate-400">Real-time system health monitoring</p>
              </div>
            </div>
            
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors disabled:opacity-50"
              data-testid="refresh-dashboard-btn"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {error && (
          <div className="bg-red-500/20 border border-red-500/30 rounded-lg p-4 flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-red-400" />
            <span className="text-red-300">{error}</span>
          </div>
        )}

        {/* Health Score Card */}
        {dashboardData && (
          <div className={`p-6 rounded-xl border ${getHealthBg(dashboardData.health_status)}`}>
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-white mb-1">System Health Score</h2>
                <p className="text-slate-400 text-sm">Last updated: {new Date(dashboardData.timestamp).toLocaleString()}</p>
              </div>
              <div className="text-right">
                <div className={`text-5xl font-bold ${getHealthColor(dashboardData.health_status)}`}>
                  {dashboardData.health_score}
                </div>
                <div className={`text-sm font-medium uppercase ${getHealthColor(dashboardData.health_status)}`}>
                  {dashboardData.health_status}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 border-b border-slate-800">
          {['overview', 'refunds', 'incidents', 'circuits'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium capitalize transition-colors ${
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

        {/* Tab Content */}
        {activeTab === 'overview' && dashboardData && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Auto Refunds */}
            <div className="bg-slate-800/50 rounded-xl p-5 border border-slate-700/50">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 bg-green-500/20 rounded-lg">
                  <DollarSign className="w-5 h-5 text-green-400" />
                </div>
                <h3 className="font-medium text-white">Auto Refunds (24h)</h3>
              </div>
              <div className="text-3xl font-bold text-white mb-1">
                {dashboardData.auto_refunds.last_24h.count}
              </div>
              <div className="text-sm text-slate-400">
                {dashboardData.auto_refunds.last_24h.total_credits} credits refunded
              </div>
            </div>

            {/* Self-Healing Incidents */}
            <div className="bg-slate-800/50 rounded-xl p-5 border border-slate-700/50">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 bg-blue-500/20 rounded-lg">
                  <Shield className="w-5 h-5 text-blue-400" />
                </div>
                <h3 className="font-medium text-white">Incidents (24h)</h3>
              </div>
              <div className="text-3xl font-bold text-white mb-1">
                {dashboardData.self_healing.incidents_24h.total}
              </div>
              <div className="text-sm text-slate-400">
                {dashboardData.self_healing.incidents_24h.resolved} resolved
              </div>
            </div>

            {/* Worker Retries */}
            <div className="bg-slate-800/50 rounded-xl p-5 border border-slate-700/50">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 bg-yellow-500/20 rounded-lg">
                  <RefreshCw className="w-5 h-5 text-yellow-400" />
                </div>
                <h3 className="font-medium text-white">Worker Retries</h3>
              </div>
              <div className="text-3xl font-bold text-white mb-1">
                {dashboardData.worker_retries.retry_rate}%
              </div>
              <div className="text-sm text-slate-400">
                {dashboardData.worker_retries.retried_jobs} of {dashboardData.worker_retries.total_jobs} jobs
              </div>
            </div>

            {/* Payment Reconciliation */}
            <div className="bg-slate-800/50 rounded-xl p-5 border border-slate-700/50">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 bg-purple-500/20 rounded-lg">
                  <TrendingUp className="w-5 h-5 text-purple-400" />
                </div>
                <h3 className="font-medium text-white">Payment Recon</h3>
              </div>
              <div className="text-3xl font-bold text-white mb-1">
                {dashboardData.payment_reconciliation.reconciled}
              </div>
              <div className="text-sm text-slate-400">
                {dashboardData.payment_reconciliation.pending_delivery} pending
              </div>
            </div>
          </div>
        )}

        {activeTab === 'refunds' && refundDetails && (
          <div className="space-y-6">
            {/* Summary */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-slate-800/50 rounded-xl p-5 border border-slate-700/50">
                <h3 className="text-sm text-slate-400 mb-2">Total Refunds (7 days)</h3>
                <div className="text-3xl font-bold text-white">{refundDetails.total_refunds}</div>
              </div>
              <div className="bg-slate-800/50 rounded-xl p-5 border border-slate-700/50">
                <h3 className="text-sm text-slate-400 mb-2">Credits Refunded</h3>
                <div className="text-3xl font-bold text-green-400">{refundDetails.total_credits_refunded}</div>
              </div>
              <div className="bg-slate-800/50 rounded-xl p-5 border border-slate-700/50">
                <h3 className="text-sm text-slate-400 mb-2">Avg per Day</h3>
                <div className="text-3xl font-bold text-blue-400">
                  {Math.round(refundDetails.total_refunds / 7)}
                </div>
              </div>
            </div>

            {/* By Reason */}
            <div className="bg-slate-800/50 rounded-xl p-5 border border-slate-700/50">
              <h3 className="font-medium text-white mb-4">Refunds by Reason</h3>
              <div className="space-y-3">
                {refundDetails.by_reason.map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-slate-900/50 rounded-lg">
                    <span className="text-slate-300 capitalize">{item.reason.replace(/_/g, ' ')}</span>
                    <div className="flex items-center gap-4">
                      <span className="text-white font-medium">{item.count} refunds</span>
                      <span className="text-green-400">{item.credits} credits</span>
                    </div>
                  </div>
                ))}
                {refundDetails.by_reason.length === 0 && (
                  <p className="text-slate-400 text-center py-4">No refunds in the last 7 days</p>
                )}
              </div>
            </div>

            {/* Recent Refunds */}
            <div className="bg-slate-800/50 rounded-xl p-5 border border-slate-700/50">
              <h3 className="font-medium text-white mb-4">Recent Refunds</h3>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="text-left text-slate-400 text-sm">
                      <th className="pb-3">Time</th>
                      <th className="pb-3">Feature</th>
                      <th className="pb-3">Reason</th>
                      <th className="pb-3">Credits</th>
                    </tr>
                  </thead>
                  <tbody className="text-slate-300">
                    {refundDetails.recent_refunds.slice(0, 10).map((refund, idx) => (
                      <tr key={idx} className="border-t border-slate-700/50">
                        <td className="py-3">{new Date(refund.timestamp).toLocaleString()}</td>
                        <td className="py-3">{refund.feature || 'N/A'}</td>
                        <td className="py-3 capitalize">{refund.reason?.replace(/_/g, ' ')}</td>
                        <td className="py-3 text-green-400">{refund.credits_refunded}</td>
                      </tr>
                    ))}
                    {refundDetails.recent_refunds.length === 0 && (
                      <tr>
                        <td colSpan="4" className="py-4 text-center text-slate-400">No recent refunds</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'incidents' && incidentDetails && (
          <div className="space-y-6">
            {/* Summary */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-slate-800/50 rounded-xl p-5 border border-slate-700/50">
                <h3 className="text-sm text-slate-400 mb-2">Total Incidents</h3>
                <div className="text-3xl font-bold text-white">{incidentDetails.total_incidents}</div>
              </div>
              <div className="bg-slate-800/50 rounded-xl p-5 border border-slate-700/50">
                <h3 className="text-sm text-slate-400 mb-2">Resolved</h3>
                <div className="text-3xl font-bold text-green-400">{incidentDetails.resolved_count}</div>
              </div>
              <div className="bg-slate-800/50 rounded-xl p-5 border border-slate-700/50">
                <h3 className="text-sm text-slate-400 mb-2">Resolution Rate</h3>
                <div className="text-3xl font-bold text-blue-400">{incidentDetails.resolution_rate}%</div>
              </div>
              <div className="bg-slate-800/50 rounded-xl p-5 border border-slate-700/50">
                <h3 className="text-sm text-slate-400 mb-2">Unresolved</h3>
                <div className="text-3xl font-bold text-yellow-400">
                  {incidentDetails.total_incidents - incidentDetails.resolved_count}
                </div>
              </div>
            </div>

            {/* By Service */}
            <div className="bg-slate-800/50 rounded-xl p-5 border border-slate-700/50">
              <h3 className="font-medium text-white mb-4">Incidents by Service</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {incidentDetails.by_service.map((item, idx) => (
                  <div key={idx} className="p-3 bg-slate-900/50 rounded-lg text-center">
                    <div className="text-2xl font-bold text-white">{item.count}</div>
                    <div className="text-sm text-slate-400 capitalize">{item.service.replace(/_/g, ' ')}</div>
                  </div>
                ))}
                {incidentDetails.by_service.length === 0 && (
                  <p className="col-span-4 text-slate-400 text-center py-4">No incidents recorded</p>
                )}
              </div>
            </div>

            {/* Recent Incidents */}
            <div className="bg-slate-800/50 rounded-xl p-5 border border-slate-700/50">
              <h3 className="font-medium text-white mb-4">Recent Incidents</h3>
              <div className="space-y-3">
                {incidentDetails.recent_incidents.slice(0, 10).map((incident, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-slate-900/50 rounded-lg">
                    <div className="flex items-center gap-3">
                      {incident.resolved ? (
                        <CheckCircle className="w-5 h-5 text-green-400" />
                      ) : (
                        <Clock className="w-5 h-5 text-yellow-400" />
                      )}
                      <div>
                        <div className="text-white capitalize">{incident.type?.replace(/_/g, ' ')}</div>
                        <div className="text-sm text-slate-400">{incident.service}</div>
                      </div>
                    </div>
                    <div className="text-sm text-slate-400">
                      {new Date(incident.timestamp).toLocaleString()}
                    </div>
                  </div>
                ))}
                {incidentDetails.recent_incidents.length === 0 && (
                  <p className="text-slate-400 text-center py-4">No recent incidents</p>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'circuits' && dashboardData && (
          <div className="space-y-6">
            <div className="bg-slate-800/50 rounded-xl p-5 border border-slate-700/50">
              <h3 className="font-medium text-white mb-4">Circuit Breaker Status</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {Object.entries(dashboardData.circuit_breakers).map(([name, status]) => (
                  <div
                    key={name}
                    className={`p-4 rounded-lg border ${
                      status.healthy
                        ? 'bg-green-500/10 border-green-500/30'
                        : 'bg-red-500/10 border-red-500/30'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-white font-medium capitalize">{name.replace(/_/g, ' ')}</span>
                      {status.healthy ? (
                        <CheckCircle className="w-5 h-5 text-green-400" />
                      ) : (
                        <AlertTriangle className="w-5 h-5 text-red-400" />
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-1 text-xs rounded ${
                        status.state === 'closed' ? 'bg-green-500/20 text-green-400' :
                        status.state === 'open' ? 'bg-red-500/20 text-red-400' :
                        'bg-yellow-500/20 text-yellow-400'
                      }`}>
                        {status.state?.toUpperCase()}
                      </span>
                      {status.failures > 0 && (
                        <span className="text-xs text-slate-400">
                          {status.failures} failures
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Circuit Breaker Guide */}
            <div className="bg-slate-800/30 rounded-xl p-5 border border-slate-700/30">
              <h4 className="font-medium text-white mb-3">Circuit Breaker States</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                <div className="flex items-start gap-3">
                  <div className="px-2 py-1 bg-green-500/20 text-green-400 rounded">CLOSED</div>
                  <span className="text-slate-400">Service is healthy, all requests pass through normally.</span>
                </div>
                <div className="flex items-start gap-3">
                  <div className="px-2 py-1 bg-red-500/20 text-red-400 rounded">OPEN</div>
                  <span className="text-slate-400">Service is failing, requests are blocked to prevent cascading failures.</span>
                </div>
                <div className="flex items-start gap-3">
                  <div className="px-2 py-1 bg-yellow-500/20 text-yellow-400 rounded">HALF-OPEN</div>
                  <span className="text-slate-400">Recovery testing, limited requests allowed to check if service recovered.</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
