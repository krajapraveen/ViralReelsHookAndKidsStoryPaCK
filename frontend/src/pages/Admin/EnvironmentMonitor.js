import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  ArrowLeft, Database, Shield, AlertTriangle, CheckCircle,
  RefreshCw, Send, Clock, Activity, Server, Globe, Bell
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const EnvironmentMonitor = () => {
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState(null);
  const [dbInfo, setDbInfo] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [checking, setChecking] = useState(false);
  const [sendingTest, setSendingTest] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    const token = localStorage.getItem('token');
    const headers = { 'Authorization': `Bearer ${token}` };

    try {
      const [statusRes, dbRes, alertsRes] = await Promise.all([
        fetch(`${API_URL}/api/environment-monitor/status`, { headers }),
        fetch(`${API_URL}/api/environment-monitor/database-info`, { headers }),
        fetch(`${API_URL}/api/environment-monitor/alerts?days=30`, { headers })
      ]);

      if (statusRes.ok) {
        const data = await statusRes.json();
        setStatus(data.data);
      }

      if (dbRes.ok) {
        const data = await dbRes.json();
        setDbInfo(data);
      }

      if (alertsRes.ok) {
        const data = await alertsRes.json();
        setAlerts(data.alerts || []);
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
      toast.error('Failed to load environment status');
    } finally {
      setLoading(false);
    }
  };

  const runEnvironmentCheck = async () => {
    setChecking(true);
    const token = localStorage.getItem('token');

    try {
      const response = await fetch(`${API_URL}/api/environment-monitor/check-production`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const data = await response.json();
        if (data.production_check?.mismatch_detected) {
          toast.error('Environment mismatch detected! Alert sent.');
        } else {
          toast.success('Environment check passed - No issues detected');
        }
        fetchData();
      } else {
        toast.error('Failed to run environment check');
      }
    } catch (error) {
      toast.error('Error running environment check');
    } finally {
      setChecking(false);
    }
  };

  const sendTestAlert = async () => {
    setSendingTest(true);
    const token = localStorage.getItem('token');

    try {
      const response = await fetch(`${API_URL}/api/environment-monitor/test-alert`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          toast.success('Test alert sent to your email addresses');
        } else {
          toast.error('Failed to send test alert');
        }
      } else {
        toast.error('Failed to send test alert');
      }
    } catch (error) {
      toast.error('Error sending test alert');
    } finally {
      setSendingTest(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[600px]">
        <RefreshCw className="h-8 w-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  const isHealthy = status?.status === "HEALTHY" || status?.is_correct_production_db;
  const currentEnv = status?.current_environment || {};

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Link to="/app/admin" className="text-gray-500 hover:text-gray-700">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <Database className="h-6 w-6 text-indigo-500" />
              Database Environment Monitor
            </h1>
            <p className="text-gray-600 dark:text-gray-400 text-sm">
              Monitor www.visionary-suite.com database connections
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={sendTestAlert} disabled={sendingTest}>
            <Bell className="h-4 w-4 mr-2" />
            {sendingTest ? 'Sending...' : 'Send Test Alert'}
          </Button>
          <Button onClick={runEnvironmentCheck} disabled={checking}>
            <Shield className="h-4 w-4 mr-2" />
            {checking ? 'Checking...' : 'Run Check Now'}
          </Button>
          <Button variant="outline" onClick={fetchData}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Overall Status */}
      <Card className={`mb-6 border-2 ${isHealthy ? 'border-green-500 bg-green-50' : 'border-red-500 bg-red-50'}`}>
        <CardContent className="py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {isHealthy ? (
                <CheckCircle className="h-12 w-12 text-green-500" />
              ) : (
                <AlertTriangle className="h-12 w-12 text-red-500" />
              )}
              <div>
                <h2 className={`text-2xl font-bold ${isHealthy ? 'text-green-700' : 'text-red-700'}`}>
                  {isHealthy ? 'Environment Healthy' : 'Environment Mismatch Detected'}
                </h2>
                <p className="text-gray-600">
                  {isHealthy 
                    ? 'Production is using the correct database' 
                    : 'Production may be connected to wrong database - check alerts'}
                </p>
              </div>
            </div>
            <Badge variant={isHealthy ? "default" : "destructive"} className="text-lg px-4 py-2">
              {status?.status || 'UNKNOWN'}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <Database className="h-8 w-8 text-blue-500" />
              <div>
                <p className="text-sm text-gray-500">Current Database</p>
                <p className="font-bold text-lg">{dbInfo?.database?.name || 'Unknown'}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <Server className="h-8 w-8 text-purple-500" />
              <div>
                <p className="text-sm text-gray-500">Detected Environment</p>
                <p className="font-bold text-lg">{currentEnv.detected_environment || 'Unknown'}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <Globe className="h-8 w-8 text-green-500" />
              <div>
                <p className="text-sm text-gray-500">Connection Type</p>
                <p className="font-bold text-lg">
                  {currentEnv.is_localhost ? 'Localhost' : currentEnv.is_cloud_db ? 'Cloud' : 'Unknown'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <Activity className="h-8 w-8 text-amber-500" />
              <div>
                <p className="text-sm text-gray-500">Alerts (30 days)</p>
                <p className="font-bold text-lg">{alerts.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Monitoring Configuration */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-indigo-500" />
            Monitoring Configuration
          </CardTitle>
          <CardDescription>Automated environment checks and alert settings</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-4 bg-gray-50 rounded-lg">
              <h4 className="font-semibold mb-3">Automated Checks</h4>
              <div className="space-y-2 text-sm">
                <p className="flex justify-between">
                  <span className="text-gray-600">Check Interval:</span>
                  <span className="font-medium">Every 5 minutes</span>
                </p>
                <p className="flex justify-between">
                  <span className="text-gray-600">Status:</span>
                  <Badge variant="default">Active</Badge>
                </p>
                <p className="flex justify-between">
                  <span className="text-gray-600">Last Check:</span>
                  <span className="font-medium">{status?.last_check ? new Date(status.last_check).toLocaleString() : 'N/A'}</span>
                </p>
              </div>
            </div>

            <div className="p-4 bg-gray-50 rounded-lg">
              <h4 className="font-semibold mb-3">Alert Recipients</h4>
              <div className="space-y-2">
                {status?.alert_recipients?.map((email, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm">
                    <Send className="h-4 w-4 text-gray-400" />
                    <span>{email}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Database Details */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5 text-blue-500" />
            Database Information
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-3 bg-gray-50 rounded-lg text-center">
              <p className="text-2xl font-bold text-blue-600">{dbInfo?.stats?.collections || 0}</p>
              <p className="text-sm text-gray-500">Collections</p>
            </div>
            <div className="p-3 bg-gray-50 rounded-lg text-center">
              <p className="text-2xl font-bold text-green-600">{dbInfo?.stats?.objects || 0}</p>
              <p className="text-sm text-gray-500">Documents</p>
            </div>
            <div className="p-3 bg-gray-50 rounded-lg text-center">
              <p className="text-2xl font-bold text-purple-600">
                {dbInfo?.stats?.dataSize ? `${(dbInfo.stats.dataSize / 1024 / 1024).toFixed(1)} MB` : '0'}
              </p>
              <p className="text-sm text-gray-500">Data Size</p>
            </div>
            <div className="p-3 bg-gray-50 rounded-lg text-center">
              <p className="text-2xl font-bold text-amber-600">
                {currentEnv.is_production_db ? 'Yes' : 'No'}
              </p>
              <p className="text-sm text-gray-500">Is Production</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Recent Alerts */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-500" />
            Recent Alerts (Last 30 Days)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {alerts.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <CheckCircle className="h-12 w-12 mx-auto mb-3 text-green-500" />
              <p>No environment alerts in the last 30 days</p>
              <p className="text-sm">The system is operating normally</p>
            </div>
          ) : (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {alerts.map((alert, i) => (
                <div key={i} className="p-4 bg-red-50 border border-red-200 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant="destructive">{alert.severity}</Badge>
                    <span className="text-sm text-gray-500">
                      {new Date(alert.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <p className="font-medium text-red-700">{alert.mismatch_type}</p>
                  <p className="text-sm text-gray-600">Database: {alert.database_name}</p>
                  <p className="text-sm text-gray-600">Environment: {alert.detected_environment}</p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default EnvironmentMonitor;
