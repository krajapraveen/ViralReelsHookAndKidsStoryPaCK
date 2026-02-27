import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, RefreshCw, Shield, Search, Download, 
  Filter, Calendar, User, Activity, FileText, ChevronLeft, ChevronRight
} from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const AdminAuditLogs = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);
  
  // Data
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState(null);
  const [actionTypes, setActionTypes] = useState([]);
  
  // Pagination
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [limit] = useState(20);
  
  // Filters
  const [days, setDays] = useState(30);
  const [filterAction, setFilterAction] = useState('');
  const [filterAdmin, setFilterAdmin] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    checkAdminAccess();
  }, []);

  useEffect(() => {
    if (isAdmin) {
      fetchData();
    }
  }, [isAdmin, days, filterAction, filterAdmin, page]);

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
          toast.error('Access denied. Admin role required.');
          navigate('/app');
          return;
        }
        
        setIsAdmin(true);
        fetchActionTypes();
      } else {
        navigate('/login');
      }
    } catch (error) {
      navigate('/login');
    }
  };

  const fetchActionTypes = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/admin/audit-logs/actions`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setActionTypes(data.actions || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchData = async () => {
    setLoading(true);
    const token = localStorage.getItem('token');
    const headers = { 'Authorization': `Bearer ${token}` };

    try {
      // Build query params
      const params = new URLSearchParams({
        days: days.toString(),
        limit: limit.toString(),
        skip: (page * limit).toString()
      });
      if (filterAction) params.append('action', filterAction);
      if (filterAdmin) params.append('admin_id', filterAdmin);

      const [logsRes, statsRes] = await Promise.all([
        fetch(`${API_URL}/api/admin/audit-logs/logs?${params}`, { headers }),
        fetch(`${API_URL}/api/admin/audit-logs/stats?days=${days}`, { headers })
      ]);

      if (logsRes.ok) {
        const data = await logsRes.json();
        setLogs(data.logs || []);
        setTotal(data.total || 0);
      }

      if (statsRes.ok) {
        setStats(await statsRes.json());
      }
    } catch (error) {
      toast.error('Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format) => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/admin/audit-logs/export?days=${days}&format=${format}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (res.ok) {
        const data = await res.json();
        
        if (format === 'csv') {
          const blob = new Blob([data.data], { type: 'text/csv' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = data.filename;
          a.click();
        } else {
          const blob = new Blob([JSON.stringify(data.data, null, 2)], { type: 'application/json' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `audit_logs_${days}days.json`;
          a.click();
        }
        
        toast.success(`Exported ${format.toUpperCase()}`);
      }
    } catch (error) {
      toast.error('Export failed');
    }
  };

  const getActionColor = (action) => {
    if (action.includes('delete')) return 'bg-red-500/20 text-red-400';
    if (action.includes('create')) return 'bg-green-500/20 text-green-400';
    if (action.includes('update') || action.includes('activate')) return 'bg-blue-500/20 text-blue-400';
    if (action.includes('security') || action.includes('block')) return 'bg-amber-500/20 text-amber-400';
    return 'bg-slate-500/20 text-slate-400';
  };

  const filteredLogs = searchTerm 
    ? logs.filter(log => 
        JSON.stringify(log).toLowerCase().includes(searchTerm.toLowerCase())
      )
    : logs;

  if (!isAdmin) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-950 flex items-center justify-center">
        <Shield className="w-16 h-16 text-red-400" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-950 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link to="/app/admin" className="p-2 bg-slate-800 rounded-lg hover:bg-slate-700">
              <ArrowLeft className="w-5 h-5 text-slate-400" />
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-white flex items-center gap-2" data-testid="page-title">
                <Activity className="w-6 h-6 text-purple-400" />
                Admin Audit Logs
              </h1>
              <p className="text-slate-400 text-sm">Track all admin actions for security compliance</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={days}
              onChange={(e) => { setDays(Number(e.target.value)); setPage(0); }}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm"
            >
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
            <button
              onClick={fetchData}
              className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg"
            >
              <RefreshCw className="w-4 h-4" /> Refresh
            </button>
            <div className="relative">
              <button
                onClick={() => document.getElementById('export-menu').classList.toggle('hidden')}
                className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg"
              >
                <Download className="w-4 h-4" /> Export
              </button>
              <div id="export-menu" className="hidden absolute right-0 mt-2 w-40 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-10">
                <button onClick={() => handleExport('csv')} className="w-full px-4 py-2 text-left text-white hover:bg-slate-700 rounded-t-lg">
                  Export CSV
                </button>
                <button onClick={() => handleExport('json')} className="w-full px-4 py-2 text-left text-white hover:bg-slate-700 rounded-b-lg">
                  Export JSON
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
              <div className="text-2xl font-bold text-white">{stats.total_actions}</div>
              <div className="text-slate-400 text-sm">Total Actions</div>
            </div>
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
              <div className="text-2xl font-bold text-purple-400">{stats.actions_by_type?.length || 0}</div>
              <div className="text-slate-400 text-sm">Action Types</div>
            </div>
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
              <div className="text-2xl font-bold text-blue-400">{stats.actions_by_admin?.length || 0}</div>
              <div className="text-slate-400 text-sm">Active Admins</div>
            </div>
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
              <div className="text-2xl font-bold text-green-400">{days}</div>
              <div className="text-slate-400 text-sm">Days Analyzed</div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 mb-6">
          <div className="flex flex-wrap gap-4 items-center">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Search logs..."
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-white text-sm placeholder-slate-500"
                />
              </div>
            </div>
            <select
              value={filterAction}
              onChange={(e) => { setFilterAction(e.target.value); setPage(0); }}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm"
            >
              <option value="">All Actions</option>
              {actionTypes.map(a => (
                <option key={a.value} value={a.value}>{a.label}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Logs Table */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="animate-spin w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full" />
            </div>
          ) : filteredLogs.length === 0 ? (
            <div className="text-center py-20 text-slate-400">
              <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
              No audit logs found
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-800/50">
                  <tr>
                    <th className="text-left text-slate-400 text-xs font-medium px-4 py-3">Timestamp</th>
                    <th className="text-left text-slate-400 text-xs font-medium px-4 py-3">Admin</th>
                    <th className="text-left text-slate-400 text-xs font-medium px-4 py-3">Action</th>
                    <th className="text-left text-slate-400 text-xs font-medium px-4 py-3">Resource</th>
                    <th className="text-left text-slate-400 text-xs font-medium px-4 py-3">Details</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredLogs.map((log, i) => (
                    <tr key={log.id || i} className="border-t border-slate-800 hover:bg-slate-800/30">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2 text-slate-300 text-sm">
                          <Calendar className="w-4 h-4 text-slate-500" />
                          {new Date(log.timestamp).toLocaleString()}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <User className="w-4 h-4 text-slate-500" />
                          <span className="text-white text-sm">{log.admin_email || 'Unknown'}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs px-2 py-1 rounded ${getActionColor(log.action)}`}>
                          {log.action?.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-300 text-sm">
                        {log.resource_type}
                        {log.resource_id && (
                          <span className="text-slate-500 ml-1">({log.resource_id.slice(0, 8)}...)</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-slate-400 text-xs max-w-xs truncate">
                        {JSON.stringify(log.details || {})}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {total > limit && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-800">
              <div className="text-slate-400 text-sm">
                Showing {page * limit + 1}-{Math.min((page + 1) * limit, total)} of {total}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(p => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="p-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 rounded-lg"
                >
                  <ChevronLeft className="w-4 h-4 text-white" />
                </button>
                <button
                  onClick={() => setPage(p => p + 1)}
                  disabled={(page + 1) * limit >= total}
                  className="p-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 rounded-lg"
                >
                  <ChevronRight className="w-4 h-4 text-white" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminAuditLogs;
