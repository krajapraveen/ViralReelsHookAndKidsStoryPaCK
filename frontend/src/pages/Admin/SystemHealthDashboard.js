import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  ArrowLeft, RefreshCw, Database, Globe, CreditCard, Mail,
  CheckCircle, XCircle, AlertTriangle, Clock, Activity,
  Bell, History, Zap, Server, Shield, Send
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const SystemHealthDashboard = () => {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [healthData, setHealthData] = useState(null);
  const [alertHistory, setAlertHistory] = useState([]);
  const [activeTab, setActiveTab] = useState('overview');
  const [lastUpdate, setLastUpdate] = useState(null);

  useEffect(() => {
    fetchHealthData();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchHealthData, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchHealthData = async () => {
    const token = localStorage.getItem('token');
    const headers = { 'Authorization': `Bearer ${token}` };

    try {
      const [healthRes, alertsRes] = await Promise.all([
        fetch(`${API_URL}/api/system-health/status`, { headers }),
        fetch(`${API_URL}/api/system-health/alerts?days=7`, { headers })
      ]);

      if (healthRes.ok) {
        const data = await healthRes.json();
        setHealthData(data);
        setLastUpdate(new Date());
      }

      if (alertsRes.ok) {
        const data = await alertsRes.json();
        setAlertHistory(data.alerts || []);
      }
    } catch (error) {
      console.error('Failed to fetch health data:', error);
      toast.error('Failed to load system health');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    fetchHealthData();
    toast.success('Health data refreshed');
  };

  const handleTestAlert = async () => {
    const token = localStorage.getItem('token');
    try {
      const res = await fetch(`${API_URL}/api/system-health/test-alert`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.success) {
        toast.success(data.message);
      } else {
        toast.error(data.error || 'Failed to send test alert');
      }
    } catch (error) {
      toast.error('Failed to send test alert');
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'UP':
      case 'HEALTHY':
        return <CheckCircle className="h-6 w-6 text-green-500" />;
      case 'DOWN':
      case 'CRITICAL':
        return <XCircle className="h-6 w-6 text-red-500" />;
      case 'DEGRADED':
        return <AlertTriangle className="h-6 w-6 text-yellow-500" />;
      case 'NOT_CONFIGURED':
        return <AlertTriangle className="h-6 w-6 text-gray-400" />;
      default:
        return <Clock className="h-6 w-6 text-gray-400" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'UP':
      case 'HEALTHY':
        return 'bg-green-500';
      case 'DOWN':
      case 'CRITICAL':
        return 'bg-red-500';
      case 'DEGRADED':
        return 'bg-yellow-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getStatusBadge = (status) => {
    const colors = {
      'UP': 'bg-green-100 text-green-800 border-green-300',
      'HEALTHY': 'bg-green-100 text-green-800 border-green-300',
      'DOWN': 'bg-red-100 text-red-800 border-red-300',
      'CRITICAL': 'bg-red-100 text-red-800 border-red-300',
      'DEGRADED': 'bg-yellow-100 text-yellow-800 border-yellow-300',
      'NOT_CONFIGURED': 'bg-gray-100 text-gray-600 border-gray-300',
      'AUTH_ERROR': 'bg-orange-100 text-orange-800 border-orange-300'
    };
    return colors[status] || 'bg-gray-100 text-gray-600';
  };

  const getServiceIcon = (service) => {
    switch (service) {
      case 'database':
        return <Database className="h-8 w-8" />;
      case 'api':
        return <Globe className="h-8 w-8" />;
      case 'payment_gateway':
        return <CreditCard className="h-8 w-8" />;
      case 'email_service':
        return <Mail className="h-8 w-8" />;
      default:
        return <Server className="h-8 w-8" />;
    }
  };

  const formatServiceName = (name) => {
    return name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[600px]" data-testid="loading-spinner">
        <RefreshCw className="h-8 w-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  const services = healthData?.services || [];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6" data-testid="system-health-dashboard">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Link to="/app/admin" className="text-gray-500 hover:text-gray-700" data-testid="back-button">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <Shield className="h-6 w-6 text-indigo-500" />
              Production Health Dashboard
            </h1>
            <p className="text-gray-600 dark:text-gray-400 text-sm">
              Real-time monitoring of all critical systems
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={handleTestAlert} data-testid="test-alert-btn">
            <Send className="h-4 w-4 mr-2" />
            Test Alert
          </Button>
          <Button onClick={handleRefresh} disabled={refreshing} data-testid="refresh-btn">
            <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Overall Status Banner */}
      <div className={`mb-6 p-4 rounded-xl ${
        healthData?.overall_status === 'HEALTHY' ? 'bg-green-50 border-2 border-green-500' :
        healthData?.overall_status === 'CRITICAL' ? 'bg-red-50 border-2 border-red-500' :
        'bg-yellow-50 border-2 border-yellow-500'
      }`} data-testid="overall-status-banner">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {getStatusIcon(healthData?.overall_status)}
            <div>
              <h2 className="text-xl font-bold">
                System Status: {healthData?.overall_status || 'UNKNOWN'}
              </h2>
              <p className="text-sm text-gray-600">
                Last checked: {lastUpdate ? formatDate(lastUpdate.toISOString()) : 'Never'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`w-3 h-3 rounded-full ${getStatusColor(healthData?.overall_status)} animate-pulse`}></span>
            <span className="text-sm font-medium">
              Auto-refresh: 30s
            </span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        <Button
          variant={activeTab === 'overview' ? 'default' : 'outline'}
          onClick={() => setActiveTab('overview')}
          data-testid="tab-overview"
        >
          <Activity className="h-4 w-4 mr-2" />
          Overview
        </Button>
        <Button
          variant={activeTab === 'alerts' ? 'default' : 'outline'}
          onClick={() => setActiveTab('alerts')}
          data-testid="tab-alerts"
        >
          <Bell className="h-4 w-4 mr-2" />
          Alert History
        </Button>
      </div>

      {activeTab === 'overview' && (
        <>
          {/* Service Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {services.map((service, index) => (
              <Card 
                key={index} 
                className={`${
                  service.status === 'DOWN' ? 'border-2 border-red-500 bg-red-50' :
                  service.status === 'DEGRADED' ? 'border-2 border-yellow-500 bg-yellow-50' :
                  service.status === 'UP' ? 'border-2 border-green-500 bg-green-50' :
                  'border-gray-200'
                }`}
                data-testid={`service-card-${service.service}`}
              >
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className={`p-3 rounded-xl ${
                      service.status === 'UP' ? 'bg-green-500 text-white' :
                      service.status === 'DOWN' ? 'bg-red-500 text-white' :
                      service.status === 'DEGRADED' ? 'bg-yellow-500 text-white' :
                      'bg-gray-200 text-gray-600'
                    }`}>
                      {getServiceIcon(service.service)}
                    </div>
                    <Badge className={getStatusBadge(service.status)}>
                      {service.status}
                    </Badge>
                  </div>
                  <h3 className="text-lg font-bold mb-2">
                    {formatServiceName(service.service)}
                  </h3>
                  {service.response_time_ms && (
                    <p className="text-sm text-gray-600 flex items-center gap-1">
                      <Zap className="h-4 w-4" />
                      {service.response_time_ms}ms response
                    </p>
                  )}
                  {service.error && (
                    <p className="text-sm text-red-600 mt-2">
                      Error: {service.error}
                    </p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Detailed Service Info */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {services.map((service, index) => (
              <Card key={index} data-testid={`service-detail-${service.service}`}>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    {getServiceIcon(service.service)}
                    {formatServiceName(service.service)} Details
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex justify-between py-2 border-b">
                      <span className="text-gray-600">Status</span>
                      <Badge className={getStatusBadge(service.status)}>
                        {service.status}
                      </Badge>
                    </div>
                    {service.response_time_ms && (
                      <div className="flex justify-between py-2 border-b">
                        <span className="text-gray-600">Response Time</span>
                        <span className="font-medium">{service.response_time_ms}ms</span>
                      </div>
                    )}
                    {service.details && Object.entries(service.details).map(([key, value]) => (
                      <div key={key} className="flex justify-between py-2 border-b">
                        <span className="text-gray-600">{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
                        <span className="font-medium">
                          {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                        </span>
                      </div>
                    ))}
                    <div className="flex justify-between py-2">
                      <span className="text-gray-600">Last Checked</span>
                      <span className="font-medium text-sm">{formatDate(service.timestamp)}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </>
      )}

      {activeTab === 'alerts' && (
        <Card data-testid="alerts-panel">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5 text-red-500" />
              Alert History (Last 7 Days)
            </CardTitle>
            <CardDescription>
              {alertHistory.length} alerts recorded
            </CardDescription>
          </CardHeader>
          <CardContent>
            {alertHistory.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <CheckCircle className="h-16 w-16 mx-auto mb-4 text-green-500" />
                <p className="text-lg font-medium">No alerts in the last 7 days</p>
                <p className="text-sm">All systems have been running smoothly!</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left font-medium">Service</th>
                      <th className="px-4 py-3 text-left font-medium">Status</th>
                      <th className="px-4 py-3 text-left font-medium">Error</th>
                      <th className="px-4 py-3 text-left font-medium">Alert Sent To</th>
                      <th className="px-4 py-3 text-left font-medium">Time</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {alertHistory.map((alert, i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-4 py-3 font-medium">
                          {formatServiceName(alert.service)}
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant="destructive">{alert.status}</Badge>
                        </td>
                        <td className="px-4 py-3 text-gray-600 max-w-xs truncate">
                          {alert.error}
                        </td>
                        <td className="px-4 py-3 text-gray-600">
                          {Array.isArray(alert.alert_sent_to) 
                            ? alert.alert_sent_to.join(', ') 
                            : alert.alert_sent_to}
                        </td>
                        <td className="px-4 py-3 text-gray-600">
                          {formatDate(alert.timestamp)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Info Banner */}
      <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-xl">
        <div className="flex items-start gap-3">
          <Bell className="h-5 w-5 text-blue-500 mt-0.5" />
          <div>
            <h4 className="font-medium text-blue-900">Automatic Alerts Enabled</h4>
            <p className="text-sm text-blue-700 mt-1">
              When any system goes DOWN, alerts are automatically sent to: <br />
              <strong>krajapraveen@gmail.com</strong> and <strong>krajapraveen@visionary-suite.com</strong>
            </p>
            <p className="text-sm text-blue-600 mt-1">
              Alert cooldown: 15 minutes (prevents alert spam)
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SystemHealthDashboard;
