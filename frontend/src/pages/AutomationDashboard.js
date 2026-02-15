import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import api from '../utils/api';
import { toast } from 'sonner';
import { 
  ArrowLeft, Activity, Server, Database, RefreshCw, CheckCircle2, 
  XCircle, AlertTriangle, Clock, Zap, Shield, BarChart3, Loader2,
  Play, Settings
} from 'lucide-react';

export default function AutomationDashboard() {
  const [status, setStatus] = useState(null);
  const [healthReport, setHealthReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(null);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchStatus = async () => {
    try {
      // Fetch automation status
      const statusResp = await fetch('http://localhost:9090/status');
      if (statusResp.ok) {
        const data = await statusResp.json();
        setStatus(data);
      }
      
      // Fetch latest health report
      const reportResp = await fetch('/app/automation/reports/health_report.json');
      if (reportResp.ok) {
        const data = await reportResp.json();
        setHealthReport(data);
      }
    } catch (error) {
      console.log('Error fetching automation status');
    } finally {
      setLoading(false);
    }
  };

  const triggerAction = async (action) => {
    setTriggering(action);
    try {
      const resp = await fetch(`http://localhost:9090/trigger/${action}`);
      if (resp.ok) {
        toast.success(`${action} triggered successfully!`);
        setTimeout(fetchStatus, 3000);
      } else {
        toast.error(`Failed to trigger ${action}`);
      }
    } catch (error) {
      toast.error(`Error triggering ${action}`);
    } finally {
      setTriggering(null);
    }
  };

  const formatDate = (isoString) => {
    if (!isoString) return 'Never';
    return new Date(isoString).toLocaleString();
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle2 className="w-5 h-5 text-green-500" />;
      case 'degraded':
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
      case 'critical':
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Clock className="w-5 h-5 text-slate-400" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-100 text-green-700 border-green-200';
      case 'degraded':
        return 'bg-yellow-100 text-yellow-700 border-yellow-200';
      case 'critical':
        return 'bg-red-100 text-red-700 border-red-200';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-indigo-500 mx-auto mb-4" />
          <p className="text-slate-600">Loading automation status...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app/admin">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Admin
              </Button>
            </Link>
            <div className="flex items-center gap-2">
              <Settings className="w-6 h-6 text-indigo-500" />
              <span className="text-xl font-bold">Automation Dashboard</span>
            </div>
          </div>
          <Button onClick={fetchStatus} variant="outline" size="sm">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
        {/* Overall Status */}
        <div className={`rounded-xl border-2 p-6 ${getStatusColor(status?.health_status || 'unknown')}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {getStatusIcon(status?.health_status)}
              <div>
                <h2 className="text-2xl font-bold capitalize">{status?.health_status || 'Unknown'} Status</h2>
                <p className="text-sm opacity-75">
                  Running since: {formatDate(status?.started_at)}
                </p>
              </div>
            </div>
            <div className="flex gap-3">
              <Button 
                onClick={() => triggerAction('health')}
                disabled={triggering === 'health'}
                className="bg-blue-500 hover:bg-blue-600"
              >
                {triggering === 'health' ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Activity className="w-4 h-4 mr-2" />}
                Run Health Check
              </Button>
              <Button 
                onClick={() => triggerAction('recovery')}
                disabled={triggering === 'recovery'}
                className="bg-green-500 hover:bg-green-600"
              >
                {triggering === 'recovery' ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Play className="w-4 h-4 mr-2" />}
                Trigger Recovery
              </Button>
            </div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center gap-2 text-slate-500 text-sm mb-1">
              <Activity className="w-4 h-4" />
              Checks Performed
            </div>
            <p className="text-3xl font-bold text-slate-900">{status?.checks_performed || 0}</p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center gap-2 text-slate-500 text-sm mb-1">
              <Zap className="w-4 h-4" />
              Recoveries Run
            </div>
            <p className="text-3xl font-bold text-indigo-600">{status?.recoveries_performed || 0}</p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center gap-2 text-slate-500 text-sm mb-1">
              <Shield className="w-4 h-4" />
              Issues Fixed
            </div>
            <p className="text-3xl font-bold text-green-600">{status?.issues_fixed || 0}</p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center gap-2 text-slate-500 text-sm mb-1">
              <Clock className="w-4 h-4" />
              Last Health Check
            </div>
            <p className="text-sm font-medium text-slate-700">{formatDate(status?.last_health_check)}</p>
          </div>
        </div>

        {/* Service Status */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Server className="w-5 h-5 text-indigo-500" />
            Service Status
          </h3>
          <div className="grid md:grid-cols-3 gap-4">
            {healthReport?.services && Object.entries(healthReport.services).map(([key, service]) => (
              <div 
                key={key}
                className={`p-4 rounded-lg border ${service.healthy ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">{service.name}</span>
                  {service.healthy ? (
                    <CheckCircle2 className="w-5 h-5 text-green-500" />
                  ) : (
                    <XCircle className="w-5 h-5 text-red-500" />
                  )}
                </div>
                <div className="text-sm text-slate-600">
                  <div>Status: {service.supervisor_status}</div>
                  <div>HTTP: {service.http_status || 'N/A'}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Infrastructure Status */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Database className="w-5 h-5 text-indigo-500" />
            Infrastructure Status
          </h3>
          <div className="grid md:grid-cols-3 gap-4">
            {healthReport?.infrastructure && Object.entries(healthReport.infrastructure).map(([key, value]) => {
              if (key === 'queue_messages') return null;
              const isUp = value.status === 'up';
              return (
                <div 
                  key={key}
                  className={`p-4 rounded-lg border ${isUp ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium capitalize">{key}</span>
                    {isUp ? (
                      <CheckCircle2 className="w-5 h-5 text-green-500" />
                    ) : (
                      <XCircle className="w-5 h-5 text-red-500" />
                    )}
                  </div>
                  <p className="text-sm text-slate-600 mt-1">{value.message || value.status}</p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Actions Taken */}
        {healthReport?.actions_taken && healthReport.actions_taken.length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-indigo-500" />
              Recent Actions Taken
            </h3>
            <ul className="space-y-2">
              {healthReport.actions_taken.map((action, idx) => (
                <li key={idx} className="flex items-center gap-2 text-sm bg-blue-50 text-blue-700 p-3 rounded-lg">
                  <CheckCircle2 className="w-4 h-4" />
                  {action}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Issues */}
        {healthReport?.issues && healthReport.issues.length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-red-600">
              <AlertTriangle className="w-5 h-5" />
              Current Issues
            </h3>
            <ul className="space-y-2">
              {healthReport.issues.map((issue, idx) => (
                <li key={idx} className="flex items-center gap-2 text-sm bg-red-50 text-red-700 p-3 rounded-lg">
                  <XCircle className="w-4 h-4" />
                  {issue}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Automation Schedule */}
        <div className="bg-slate-100 rounded-xl p-6">
          <h3 className="font-semibold mb-4">Automation Schedule</h3>
          <div className="grid md:grid-cols-3 gap-4 text-sm">
            <div className="bg-white rounded-lg p-4">
              <div className="font-medium text-indigo-600">Health Check</div>
              <div className="text-slate-600">Every 1 minute</div>
              <div className="text-xs text-slate-400 mt-1">Auto-restarts failed services</div>
            </div>
            <div className="bg-white rounded-lg p-4">
              <div className="font-medium text-indigo-600">API Validation</div>
              <div className="text-slate-600">Every 5 minutes</div>
              <div className="text-xs text-slate-400 mt-1">Tests all API endpoints</div>
            </div>
            <div className="bg-white rounded-lg p-4">
              <div className="font-medium text-indigo-600">Database Maintenance</div>
              <div className="text-slate-600">Every 1 hour</div>
              <div className="text-xs text-slate-400 mt-1">Cleanup & optimization</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
