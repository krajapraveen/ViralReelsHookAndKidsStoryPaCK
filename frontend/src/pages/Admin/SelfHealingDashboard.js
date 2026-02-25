import React, { useState, useEffect, useCallback } from 'react';
import { 
  Activity, AlertTriangle, CheckCircle, XCircle, Clock, Server, 
  Database, Zap, RefreshCw, Bell, Shield, TrendingUp, TrendingDown,
  Loader2, ChevronDown, ChevronRight, Users, Cpu, Gauge, Crown
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL || '';

// ============================================
// SCALING DASHBOARD COMPONENT
// ============================================

const ScalingDashboard = () => {
  const [scalingData, setScalingData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isScaling, setIsScaling] = useState(false);

  const fetchScalingData = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/api/scaling/dashboard`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        setScalingData(await response.json());
      }
    } catch (error) {
      console.error('Scaling data fetch failed:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchScalingData();
    const interval = setInterval(fetchScalingData, 15000);
    return () => clearInterval(interval);
  }, [fetchScalingData]);

  const handleManualScale = async (direction) => {
    if (!scalingData) return;
    
    const currentWorkers = scalingData.scaling.current_workers;
    const targetWorkers = direction === 'up' ? currentWorkers + 1 : currentWorkers - 1;
    
    setIsScaling(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/api/scaling/manual`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          target_workers: targetWorkers,
          reason: `Manual ${direction} from dashboard`
        })
      });
      
      if (response.ok) {
        toast.success(`Scaled ${direction} successfully`);
        fetchScalingData();
      } else {
        toast.error('Scaling failed');
      }
    } catch (error) {
      toast.error('Scaling request failed');
    } finally {
      setIsScaling(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  if (!scalingData) {
    return (
      <Card>
        <CardContent className="p-8 text-center text-gray-500">
          Failed to load scaling data
        </CardContent>
      </Card>
    );
  }

  const { scaling, priority_lanes, queue_by_tier, recent_scaling_events } = scalingData;

  return (
    <div className="space-y-4">
      {/* Worker Status */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2">
            <Cpu className="h-5 w-5" />
            Worker Auto-Scaling
          </CardTitle>
          <CardDescription>
            Automatically scales workers based on queue depth and latency
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div className="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <p className="text-sm text-gray-500 mb-1">Current Workers</p>
              <p className="text-4xl font-bold text-indigo-600">{scaling.current_workers}</p>
            </div>
            <div className="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <p className="text-sm text-gray-500 mb-1">Min / Max</p>
              <p className="text-2xl font-semibold">{scaling.min_workers} / {scaling.max_workers}</p>
            </div>
            <div className="text-center p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
              <p className="text-sm text-slate-500 mb-1">Queue Depth</p>
              <p className={`text-2xl font-semibold ${
                (scaling.metrics?.queue_depth || 0) > 50 ? 'text-amber-600' : 'text-emerald-600'
              }`}>
                {scaling.metrics?.queue_depth?.toFixed(0) || 0}
              </p>
            </div>
          </div>
          
          {/* Manual Scaling Controls */}
          <div className="flex items-center justify-center gap-4 pt-4 border-t">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleManualScale('down')}
              disabled={scaling.current_workers <= scaling.min_workers || isScaling}
            >
              <TrendingDown className="h-4 w-4 mr-1" />
              Scale Down
            </Button>
            <span className="text-sm text-gray-500">Manual Control</span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleManualScale('up')}
              disabled={scaling.current_workers >= scaling.max_workers || isScaling}
            >
              <TrendingUp className="h-4 w-4 mr-1" />
              Scale Up
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Priority Lanes */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2">
            <Crown className="h-5 w-5" />
            Priority Lanes
          </CardTitle>
          <CardDescription>
            Premium users get faster processing with dedicated resources
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {Object.entries(priority_lanes || {}).map(([tier, stats]) => (
              <div 
                key={tier}
                className={`p-4 rounded-lg border-2 ${
                  tier === 'enterprise' ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20' :
                  tier === 'pro' ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20' :
                  tier === 'basic' ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' :
                  'border-gray-300 bg-gray-50 dark:bg-gray-800'
                }`}
              >
                <div className="flex items-center gap-2 mb-2">
                  {tier === 'enterprise' && <Crown className="h-4 w-4 text-purple-500" />}
                  {tier === 'pro' && <Zap className="h-4 w-4 text-indigo-500" />}
                  {tier === 'basic' && <Users className="h-4 w-4 text-blue-500" />}
                  {tier === 'free' && <Users className="h-4 w-4 text-gray-500" />}
                  <span className="font-semibold capitalize">{tier}</span>
                </div>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Queued</span>
                    <span className="font-medium">{stats.queued || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Processing</span>
                    <span className="font-medium">{stats.processing || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">SLA</span>
                    <span className="font-medium">{stats.sla_seconds || 0}s</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Max Concurrent</span>
                    <span className="font-medium">{stats.max_concurrent || 0}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Queue by Tier */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2">
            <Gauge className="h-5 w-5" />
            Queue Distribution by Tier
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-end gap-2 h-32">
            {Object.entries(queue_by_tier || {}).map(([tier, count]) => {
              const maxCount = Math.max(...Object.values(queue_by_tier || {}), 1);
              const height = (count / maxCount) * 100;
              return (
                <div key={tier} className="flex-1 flex flex-col items-center">
                  <div 
                    className={`w-full rounded-t transition-all ${
                      tier === 'enterprise' ? 'bg-purple-500' :
                      tier === 'pro' ? 'bg-indigo-500' :
                      tier === 'basic' ? 'bg-blue-500' :
                      'bg-gray-400'
                    }`}
                    style={{ height: `${Math.max(height, 5)}%` }}
                  />
                  <span className="text-xs mt-1 capitalize">{tier}</span>
                  <span className="text-sm font-semibold">{count}</span>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Recent Scaling Events */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Recent Scaling Events
          </CardTitle>
        </CardHeader>
        <CardContent>
          {recent_scaling_events && recent_scaling_events.length > 0 ? (
            <div className="space-y-2">
              {recent_scaling_events.slice(0, 5).map((event, idx) => (
                <div key={idx} className="flex items-center justify-between p-2 bg-slate-50 dark:bg-slate-800 rounded">
                  <div className="flex items-center gap-2">
                    {event.direction === 'up' ? (
                      <TrendingUp className="h-4 w-4 text-emerald-600" />
                    ) : (
                      <TrendingDown className="h-4 w-4 text-amber-600" />
                    )}
                    <span className="text-sm">
                      Scaled {event.direction} by {event.amount}
                    </span>
                  </div>
                  <div className="text-sm text-slate-500">
                    <span className="mr-2">{event.old_workers} → {event.new_workers} workers</span>
                    <span>{new Date(event.timestamp).toLocaleTimeString()}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center text-gray-500 py-4">No scaling events yet</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

// ============================================
// MAIN DASHBOARD COMPONENT
// ============================================

const SelfHealingDashboard = () => {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [expandedSections, setExpandedSections] = useState({});

  const fetchDashboard = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/api/monitoring/dashboard`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        setDashboard(await response.json());
      }
    } catch (error) {
      console.error('Dashboard fetch failed:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
    
    if (autoRefresh) {
      const interval = setInterval(fetchDashboard, 30000);
      return () => clearInterval(interval);
    }
  }, [fetchDashboard, autoRefresh]);

  const getHealthColor = (status) => {
    switch (status) {
      case 'healthy': return 'text-emerald-600 bg-emerald-50 dark:bg-emerald-900/20';
      case 'degraded': return 'text-amber-600 bg-amber-50 dark:bg-amber-900/20';
      case 'critical': return 'text-red-600 bg-red-50 dark:bg-red-900/20';
      default: return 'text-slate-500 bg-slate-100 dark:bg-slate-800';
    }
  };

  const getHealthIcon = (status) => {
    switch (status) {
      case 'healthy': return <CheckCircle className="h-5 w-5 text-emerald-600" />;
      case 'degraded': return <AlertTriangle className="h-5 w-5 text-amber-600" />;
      case 'critical': return <XCircle className="h-5 w-5 text-red-600" />;
      default: return <Clock className="h-5 w-5 text-slate-500" />;
    }
  };

  const acknowledgeAlert = async (alertId) => {
    try {
      const token = localStorage.getItem('token');
      await fetch(`${API}/api/monitoring/alerts/${alertId}/acknowledge`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      toast.success('Alert acknowledged');
      fetchDashboard();
    } catch (error) {
      toast.error('Failed to acknowledge alert');
    }
  };

  const resolveAlert = async (alertId) => {
    try {
      const token = localStorage.getItem('token');
      await fetch(`${API}/api/monitoring/alerts/${alertId}/resolve`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      toast.success('Alert resolved');
      fetchDashboard();
    } catch (error) {
      toast.error('Failed to resolve alert');
    }
  };

  const resetCircuitBreaker = async (name) => {
    try {
      const token = localStorage.getItem('token');
      await fetch(`${API}/api/monitoring/circuit-breakers/${name}/reset`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      toast.success(`Circuit breaker ${name} reset`);
      fetchDashboard();
    } catch (error) {
      toast.error('Failed to reset circuit breaker');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[600px]">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  if (!dashboard) {
    return (
      <div className="p-6 text-center text-gray-500">
        Failed to load dashboard data
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 bg-gray-50 dark:bg-gray-900 min-h-screen">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Shield className="h-6 w-6 text-indigo-500" />
            Self-Healing System Monitor
          </h1>
          <p className="text-gray-600 dark:text-gray-400 text-sm mt-1">
            Real-time system health and automatic recovery status
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <Button
            variant={autoRefresh ? "default" : "outline"}
            size="sm"
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            <RefreshCw className={`h-4 w-4 mr-1 ${autoRefresh ? 'animate-spin' : ''}`} />
            {autoRefresh ? 'Auto-refreshing' : 'Paused'}
          </Button>
          
          <Button variant="outline" size="sm" onClick={fetchDashboard}>
            <RefreshCw className="h-4 w-4 mr-1" />
            Refresh Now
          </Button>
        </div>
      </div>

      {/* System Health Banner */}
      <Card className={`border-2 ${getHealthColor(dashboard.system_health)}`}>
        <CardContent className="py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {getHealthIcon(dashboard.system_health)}
              <div>
                <h2 className="font-semibold text-lg capitalize">
                  System Status: {dashboard.system_health}
                </h2>
                {dashboard.health_issues && dashboard.health_issues.length > 0 && (
                  <p className="text-sm opacity-80">
                    Issues: {dashboard.health_issues.join(', ')}
                  </p>
                )}
              </div>
            </div>
            
            <div className="text-right text-sm text-gray-600 dark:text-gray-400">
              <div>Uptime: {Math.floor(dashboard.metrics?.uptime_seconds / 3600)}h {Math.floor((dashboard.metrics?.uptime_seconds % 3600) / 60)}m</div>
              <div>Last Updated: {new Date(dashboard.timestamp).toLocaleTimeString()}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Error Rate (5min)</p>
                <p className={`text-2xl font-bold ${
                  dashboard.metrics?.error_rate_5min > 5 ? 'text-red-600' :
                  dashboard.metrics?.error_rate_5min > 1 ? 'text-amber-600' : 'text-emerald-600'
                }`}>
                  {dashboard.metrics?.error_rate_5min?.toFixed(2)}%
                </p>
              </div>
              <Activity className="h-8 w-8 text-slate-300" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">P95 Latency</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {dashboard.metrics?.latency_p95_ms?.toFixed(0)}ms
                </p>
              </div>
              <Zap className="h-8 w-8 text-gray-300" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Active Alerts</p>
                <p className={`text-2xl font-bold ${
                  dashboard.active_alerts_count > 0 ? 'text-red-500' : 'text-green-500'
                }`}>
                  {dashboard.active_alerts_count}
                </p>
              </div>
              <Bell className="h-8 w-8 text-gray-300" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Incidents (24h)</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {dashboard.recent_incidents_count}
                </p>
              </div>
              <AlertTriangle className="h-8 w-8 text-gray-300" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="alerts">
            Alerts
            {dashboard.active_alerts_count > 0 && (
              <Badge variant="destructive" className="ml-2">{dashboard.active_alerts_count}</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="circuits">Circuit Breakers</TabsTrigger>
          <TabsTrigger value="queues">Job Queues</TabsTrigger>
          <TabsTrigger value="scaling">Auto-Scaling</TabsTrigger>
          <TabsTrigger value="payments">Payments</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Payment Health */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <Database className="h-4 w-4" />
                  Payment System
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Status</span>
                    <Badge className={getHealthColor(dashboard.payment_health?.status)}>
                      {dashboard.payment_health?.status}
                    </Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Success Rate (24h)</span>
                    <span className="font-medium">{dashboard.payment_health?.metrics?.success_rate}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Stuck Payments</span>
                    <span className={`font-medium ${dashboard.payment_health?.metrics?.stuck_payments > 0 ? 'text-red-500' : ''}`}>
                      {dashboard.payment_health?.metrics?.stuck_payments}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Storage Health */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <Server className="h-4 w-4" />
                  Storage System
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Status</span>
                    <Badge className={getHealthColor(dashboard.storage_health?.overall)}>
                      {dashboard.storage_health?.overall}
                    </Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Primary</span>
                    <span className="font-medium">{dashboard.storage_health?.primary?.status}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Fallback</span>
                    <span className="font-medium">{dashboard.storage_health?.fallback?.status}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Recent Incidents */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Recent Incidents</CardTitle>
            </CardHeader>
            <CardContent>
              {dashboard.incidents && dashboard.incidents.length > 0 ? (
                <div className="space-y-2">
                  {dashboard.incidents.slice(0, 5).map((incident, index) => (
                    <div key={index} className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-800 last:border-0">
                      <div className="flex items-center gap-2">
                        <Badge variant={incident.severity === 'error' ? 'destructive' : 'secondary'}>
                          {incident.severity}
                        </Badge>
                        <span className="text-sm">{incident.type}</span>
                      </div>
                      <span className="text-sm text-gray-500">
                        {new Date(incident.created_at).toLocaleTimeString()}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-4">No recent incidents</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Alerts Tab */}
        <TabsContent value="alerts" className="space-y-4">
          {dashboard.alerts && dashboard.alerts.length > 0 ? (
            dashboard.alerts.map((alert, index) => (
              <Card key={index} className={`border-l-4 ${
                alert.severity === 'critical' ? 'border-l-red-500' :
                alert.severity === 'error' ? 'border-l-orange-500' :
                alert.severity === 'warning' ? 'border-l-yellow-500' : 'border-l-blue-500'
              }`}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base flex items-center gap-2">
                      <AlertTriangle className={`h-4 w-4 ${
                        alert.severity === 'critical' ? 'text-red-500' :
                        alert.severity === 'error' ? 'text-orange-500' : 'text-yellow-500'
                      }`} />
                      {alert.title}
                    </CardTitle>
                    <Badge variant={alert.acknowledged ? 'secondary' : 'destructive'}>
                      {alert.acknowledged ? 'Acknowledged' : alert.severity}
                    </Badge>
                  </div>
                  <CardDescription>{alert.message}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-500">
                      {new Date(alert.created_at).toLocaleString()}
                    </span>
                    <div className="flex gap-2">
                      {!alert.acknowledged && (
                        <Button size="sm" variant="outline" onClick={() => acknowledgeAlert(alert.alert_id)}>
                          Acknowledge
                        </Button>
                      )}
                      <Button size="sm" variant="default" onClick={() => resolveAlert(alert.alert_id)}>
                        Resolve
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          ) : (
            <Card>
              <CardContent className="py-8 text-center">
                <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-2" />
                <p className="text-gray-600 dark:text-gray-400">No active alerts</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Circuit Breakers Tab */}
        <TabsContent value="circuits" className="space-y-4">
          {dashboard.circuit_breakers && Object.entries(dashboard.circuit_breakers).map(([name, cb]) => (
            <Card key={name} className={`border-l-4 ${
              cb.state === 'closed' ? 'border-l-green-500' :
              cb.state === 'half_open' ? 'border-l-yellow-500' : 'border-l-red-500'
            }`}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">{name}</CardTitle>
                  <Badge className={
                    cb.state === 'closed' ? 'bg-green-100 text-green-800' :
                    cb.state === 'half_open' ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'
                  }>
                    {cb.state}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">Failures</span>
                    <p className="font-medium">{cb.failure_count}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Threshold</span>
                    <p className="font-medium">{cb.failure_threshold}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Recovery</span>
                    <p className="font-medium">{cb.recovery_timeout}s</p>
                  </div>
                </div>
                {cb.state !== 'closed' && (
                  <Button 
                    size="sm" 
                    variant="outline" 
                    className="mt-3"
                    onClick={() => resetCircuitBreaker(name)}
                  >
                    <RefreshCw className="h-3 w-3 mr-1" />
                    Reset
                  </Button>
                )}
              </CardContent>
            </Card>
          ))}
          
          {(!dashboard.circuit_breakers || Object.keys(dashboard.circuit_breakers).length === 0) && (
            <Card>
              <CardContent className="py-8 text-center text-gray-500">
                No circuit breakers configured
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Job Queues Tab */}
        <TabsContent value="queues" className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {dashboard.queue_depths && Object.entries(dashboard.queue_depths).map(([name, depth]) => (
              <Card key={name}>
                <CardContent className="pt-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-500 capitalize">{name} Queue</p>
                      <p className={`text-2xl font-bold ${depth > 50 ? 'text-yellow-500' : depth > 100 ? 'text-red-500' : 'text-green-500'}`}>
                        {depth}
                      </p>
                    </div>
                    {depth > 50 ? (
                      <TrendingUp className="h-8 w-8 text-yellow-300" />
                    ) : (
                      <TrendingDown className="h-8 w-8 text-green-300" />
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Auto-Scaling Tab */}
        <TabsContent value="scaling" className="space-y-4">
          <ScalingDashboard />
        </TabsContent>

        {/* Payments Tab */}
        <TabsContent value="payments" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Payment Health</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-sm text-gray-500">Total (24h)</p>
                  <p className="text-xl font-bold">{dashboard.payment_health?.metrics?.total_24h || 0}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Successful</p>
                  <p className="text-xl font-bold text-green-600">{dashboard.payment_health?.metrics?.successful_24h || 0}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Failed</p>
                  <p className="text-xl font-bold text-red-600">{dashboard.payment_health?.metrics?.failed_24h || 0}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Stuck</p>
                  <p className={`text-xl font-bold ${(dashboard.payment_health?.metrics?.stuck_payments || 0) > 0 ? 'text-yellow-600' : 'text-green-600'}`}>
                    {dashboard.payment_health?.metrics?.stuck_payments || 0}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default SelfHealingDashboard;
