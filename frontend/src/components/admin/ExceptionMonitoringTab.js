import React, { useState, useEffect } from 'react';
import api from '../../utils/api';
import { toast } from 'sonner';
import { 
  AlertTriangle, AlertCircle, CheckCircle, RefreshCw, 
  Filter, Eye, XCircle, Clock, Bug
} from 'lucide-react';
import { Button } from '../ui/button';

export default function ExceptionMonitoringTab() {
  const [exceptions, setExceptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ total: 0, unresolved: 0, critical: 0 });
  const [filter, setFilter] = useState({ severity: '', resolved: null });
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [selectedExc, setSelectedExc] = useState(null);

  useEffect(() => {
    fetchExceptions();
  }, [filter, page]);

  const fetchExceptions = async () => {
    setLoading(true);
    try {
      let url = `/api/admin/exceptions/all?page=${page}&size=20`;
      if (filter.severity) url += `&severity=${filter.severity}`;
      if (filter.resolved !== null) url += `&resolved=${filter.resolved}`;
      
      const response = await api.get(url);
      setExceptions(response.data.exceptions || []);
      setTotal(response.data.total || 0);
      
      // Fetch stats
      const dashboardRes = await api.get('/api/admin/analytics/dashboard?days=30');
      if (dashboardRes.data) {
        const e = dashboardRes.data.exceptions || {};
        setStats({
          total: e.total || 0,
          unresolved: e.unresolved || 0,
          critical: e.critical || 0
        });
      }
    } catch (error) {
      console.error('Failed to fetch exceptions:', error);
      toast.error('Failed to load exception data');
    } finally {
      setLoading(false);
    }
  };

  const resolveException = async (exceptionId) => {
    try {
      await api.put(`/api/admin/exceptions/${exceptionId}/resolve`);
      toast.success('Exception marked as resolved');
      fetchExceptions();
    } catch (error) {
      toast.error('Failed to resolve exception');
    }
  };

  const deleteException = async (exceptionId) => {
    if (!window.confirm('Are you sure you want to delete this exception?')) return;
    try {
      await api.delete(`/api/admin/exceptions/${exceptionId}`);
      toast.success('Exception deleted');
      fetchExceptions();
    } catch (error) {
      toast.error('Failed to delete exception');
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleString();
  };

  const getSeverityColor = (severity) => {
    switch (severity?.toUpperCase()) {
      case 'CRITICAL': return 'text-red-500 bg-red-500/10';
      case 'ERROR': return 'text-orange-500 bg-orange-500/10';
      case 'WARNING': return 'text-yellow-500 bg-yellow-500/10';
      default: return 'text-blue-500 bg-blue-500/10';
    }
  };

  const getSeverityIcon = (severity) => {
    switch (severity?.toUpperCase()) {
      case 'CRITICAL': return <AlertTriangle className="w-4 h-4" />;
      case 'ERROR': return <AlertCircle className="w-4 h-4" />;
      case 'WARNING': return <AlertCircle className="w-4 h-4" />;
      default: return <Bug className="w-4 h-4" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-6 h-6 animate-spin text-purple-500" />
        <span className="ml-2 text-slate-400">Loading exceptions...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Stats Summary */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-slate-700/50 border border-slate-600 rounded-lg p-4">
          <div className="flex items-center gap-2 text-slate-300 mb-2">
            <Bug className="w-5 h-5" />
            <span className="font-medium">Total Exceptions</span>
          </div>
          <p className="text-2xl font-bold text-white">{stats.total}</p>
        </div>
        <div className="bg-orange-500/10 border border-orange-500/20 rounded-lg p-4">
          <div className="flex items-center gap-2 text-orange-400 mb-2">
            <Clock className="w-5 h-5" />
            <span className="font-medium">Unresolved</span>
          </div>
          <p className="text-2xl font-bold text-white">{stats.unresolved}</p>
        </div>
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
          <div className="flex items-center gap-2 text-red-400 mb-2">
            <AlertTriangle className="w-5 h-5" />
            <span className="font-medium">Critical</span>
          </div>
          <p className="text-2xl font-bold text-white">{stats.critical}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-4 items-center">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-400" />
          <span className="text-sm text-slate-400">Filter:</span>
        </div>
        <select
          value={filter.severity}
          onChange={(e) => setFilter({ ...filter, severity: e.target.value })}
          className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white"
        >
          <option value="">All Severities</option>
          <option value="CRITICAL">Critical</option>
          <option value="ERROR">Error</option>
          <option value="WARNING">Warning</option>
          <option value="INFO">Info</option>
        </select>
        <select
          value={filter.resolved === null ? '' : String(filter.resolved)}
          onChange={(e) => setFilter({ ...filter, resolved: e.target.value === '' ? null : e.target.value === 'true' })}
          className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white"
        >
          <option value="">All Status</option>
          <option value="false">Unresolved</option>
          <option value="true">Resolved</option>
        </select>
        <Button variant="outline" size="sm" onClick={fetchExceptions} className="ml-auto border-slate-600">
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Exception List */}
      <div className="space-y-3">
        {exceptions.length === 0 ? (
          <div className="text-center py-12 text-slate-400">
            <CheckCircle className="w-12 h-12 mx-auto mb-4 text-green-500" />
            <p>No exceptions found matching your filters</p>
          </div>
        ) : (
          exceptions.map((exc, index) => (
            <div
              key={exc.id || index}
              className={`bg-slate-700/50 border rounded-lg p-4 ${
                exc.resolved ? 'border-slate-600 opacity-70' : 'border-slate-500'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium ${getSeverityColor(exc.severity)}`}>
                      {getSeverityIcon(exc.severity)}
                      {exc.severity || 'UNKNOWN'}
                    </span>
                    <span className="text-sm text-purple-400 font-medium">
                      {exc.functionality || 'Unknown Feature'}
                    </span>
                    {exc.resolved && (
                      <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium text-green-400 bg-green-500/10">
                        <CheckCircle className="w-3 h-3" />
                        Resolved
                      </span>
                    )}
                  </div>
                  <p className="text-white font-medium mb-1">{exc.error_type || 'Error'}</p>
                  <p className="text-sm text-slate-300 mb-2">{exc.error_message}</p>
                  <div className="flex items-center gap-4 text-xs text-slate-400">
                    <span>User: {exc.user_email || exc.user_id || 'N/A'}</span>
                    <span>{formatDate(exc.created_at)}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 ml-4">
                  {exc.stack_trace && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setSelectedExc(selectedExc?.id === exc.id ? null : exc)}
                      className="text-slate-400 hover:text-white"
                    >
                      <Eye className="w-4 h-4" />
                    </Button>
                  )}
                  {!exc.resolved && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => resolveException(exc.id)}
                      className="text-green-400 hover:text-green-300"
                    >
                      <CheckCircle className="w-4 h-4" />
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => deleteException(exc.id)}
                    className="text-red-400 hover:text-red-300"
                  >
                    <XCircle className="w-4 h-4" />
                  </Button>
                </div>
              </div>
              
              {/* Stack Trace Expansion */}
              {selectedExc?.id === exc.id && exc.stack_trace && (
                <div className="mt-4 p-3 bg-slate-800 rounded border border-slate-600 overflow-x-auto">
                  <pre className="text-xs text-slate-300 whitespace-pre-wrap font-mono">
                    {exc.stack_trace}
                  </pre>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Pagination */}
      {total > 20 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-slate-400">
            Showing {page * 20 + 1} - {Math.min((page + 1) * 20, total)} of {total}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              className="border-slate-600"
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => p + 1)}
              disabled={(page + 1) * 20 >= total}
              className="border-slate-600"
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
