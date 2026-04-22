import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import api from '../utils/api';
import { toast } from 'sonner';
import {
  RefreshCw, Shield, AlertTriangle, Clock, CheckCircle,
  Search, Filter, ExternalLink,
} from 'lucide-react';

const STATUS_VALUES = ['NEW', 'ACKNOWLEDGED', 'TRIAGING', 'NEED_MORE_INFO', 'ACCEPTED', 'DUPLICATE', 'OUT_OF_SCOPE', 'INFORMATIVE', 'RESOLVED', 'CLOSED'];
const SEVERITY_VALUES = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
const REWARD_VALUES = ['NONE', 'PENDING', 'GRANTED', 'REJECTED'];

const SEV_COLOR = {
  LOW: 'bg-slate-500/10 text-slate-300 border-slate-500/30',
  MEDIUM: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
  HIGH: 'bg-orange-500/10 text-orange-300 border-orange-500/30',
  CRITICAL: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
};

const STATUS_COLOR = {
  NEW: 'bg-blue-500/10 text-blue-300 border-blue-500/30',
  ACKNOWLEDGED: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
  TRIAGING: 'bg-violet-500/10 text-violet-300 border-violet-500/30',
  NEED_MORE_INFO: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
  ACCEPTED: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
  DUPLICATE: 'bg-slate-600/20 text-slate-400 border-slate-600/30',
  OUT_OF_SCOPE: 'bg-slate-600/20 text-slate-400 border-slate-600/30',
  INFORMATIVE: 'bg-slate-600/20 text-slate-400 border-slate-600/30',
  RESOLVED: 'bg-emerald-600/20 text-emerald-400 border-emerald-600/30',
  CLOSED: 'bg-slate-700/30 text-slate-500 border-slate-700/40',
};

export default function AdminSecurityReports() {
  const [stats, setStats] = useState(null);
  const [reports, setReports] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ status: '', severity: '', category: '', reward_status: '', search: '' });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const qs = new URLSearchParams();
      Object.entries(filters).forEach(([k, v]) => { if (v) qs.set(k, v); });
      qs.set('limit', '100');
      const [listResp, statsResp] = await Promise.all([
        api.get(`/api/security/admin/reports?${qs.toString()}`),
        api.get('/api/security/admin/reports/stats'),
      ]);
      setReports(listResp.data.reports || []);
      setTotal(listResp.data.total || 0);
      setStats(statsResp.data);
    } catch (e) {
      toast.error('Failed to load security reports');
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => { fetchData(); }, [fetchData]);

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6" data-testid="admin-security-reports">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3">
              <Shield className="w-6 h-6 text-violet-400" />
              Security Reports
            </h1>
            <p className="text-sm text-slate-500 mt-1">Vulnerability Disclosure Program — triage queue</p>
          </div>
          <button
            onClick={fetchData}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-800 text-sm"
            data-testid="refresh-btn"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3 mb-6">
          <StatBox icon={AlertTriangle} label="Open Critical" value={stats?.open_critical} color="rose" testId="stat-open-critical" />
          <StatBox icon={Clock} label="New" value={stats?.new} color="blue" testId="stat-new" />
          <StatBox icon={RefreshCw} label="Triaging" value={stats?.triaging} color="violet" testId="stat-triaging" />
          <StatBox icon={CheckCircle} label="Accepted" value={stats?.accepted} color="emerald" testId="stat-accepted" />
          <StatBox icon={CheckCircle} label="Resolved" value={stats?.resolved} color="slate" testId="stat-resolved" />
          <StatBox icon={Shield} label="Total" value={stats?.total} color="slate" testId="stat-total" />
        </div>

        {/* Filters */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 mb-5 flex flex-wrap items-center gap-2">
          <Filter className="w-4 h-4 text-slate-500" />
          <FilterSelect value={filters.status} onChange={v => setFilters(f => ({ ...f, status: v }))} options={STATUS_VALUES} placeholder="All statuses" testId="filter-status" />
          <FilterSelect value={filters.severity} onChange={v => setFilters(f => ({ ...f, severity: v }))} options={SEVERITY_VALUES} placeholder="All severities" testId="filter-severity" />
          <FilterSelect value={filters.reward_status} onChange={v => setFilters(f => ({ ...f, reward_status: v }))} options={REWARD_VALUES} placeholder="All rewards" testId="filter-reward" />
          <div className="flex items-center gap-2 bg-slate-800 rounded-lg px-3 py-1.5 flex-1 min-w-[200px]">
            <Search className="w-3.5 h-3.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search by subject, email, or ID"
              value={filters.search}
              onChange={e => setFilters(f => ({ ...f, search: e.target.value }))}
              className="bg-transparent outline-none text-sm text-white placeholder:text-slate-500 flex-1"
              data-testid="filter-search"
            />
          </div>
          {(filters.status || filters.severity || filters.reward_status || filters.search) && (
            <button
              onClick={() => setFilters({ status: '', severity: '', category: '', reward_status: '', search: '' })}
              className="text-[11px] text-slate-500 hover:text-white"
              data-testid="clear-filters"
            >
              Clear
            </button>
          )}
        </div>

        {/* Table */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-900 border-b border-slate-800">
                <tr className="text-left text-[10px] uppercase tracking-wider text-slate-500">
                  <th className="px-4 py-3">Report ID</th>
                  <th className="px-4 py-3">Subject</th>
                  <th className="px-4 py-3">Reporter</th>
                  <th className="px-4 py-3">Category</th>
                  <th className="px-4 py-3">Severity</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Reward</th>
                  <th className="px-4 py-3">Received</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={9} className="py-16 text-center"><RefreshCw className="w-5 h-5 text-slate-500 animate-spin mx-auto" /></td></tr>
                ) : reports.length === 0 ? (
                  <tr><td colSpan={9} className="py-16 text-center text-slate-500 text-sm">No reports match these filters</td></tr>
                ) : reports.map(r => {
                  const sev = r.internal_severity || r.severity;
                  return (
                    <tr
                      key={r.report_id}
                      className="border-b border-slate-800/50 hover:bg-slate-800/40 transition-colors"
                      data-testid={`report-row-${r.report_id}`}
                    >
                      <td className="px-4 py-3 font-mono text-[12px] text-white">{r.report_id}</td>
                      <td className="px-4 py-3 text-slate-200 max-w-xs truncate">{r.subject}</td>
                      <td className="px-4 py-3 text-slate-400 text-[12px]">{r.from_email}</td>
                      <td className="px-4 py-3 text-slate-400 text-[12px]">{r.category}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-medium border ${SEV_COLOR[sev] || ''}`}>
                          {sev}
                          {r.internal_severity && r.internal_severity !== r.severity && <span className="opacity-60"> ({r.severity})</span>}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-medium border ${STATUS_COLOR[r.status] || ''}`}>
                          {r.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-[11px] text-slate-400">
                        {r.reward_status === 'GRANTED' ? (
                          <span className="text-emerald-400">+{r.reward_amount} credits</span>
                        ) : r.reward_status === 'REJECTED' ? (
                          <span className="text-slate-500">Rejected</span>
                        ) : (
                          <span className="text-slate-500">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-[11px] text-slate-500 whitespace-nowrap">
                        {new Date(r.created_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-3">
                        <Link
                          to={`/app/admin/security-reports/${r.report_id}`}
                          className="inline-flex items-center gap-1 text-violet-400 hover:text-violet-300 text-[11px]"
                          data-testid={`open-report-${r.report_id}`}
                        >
                          Open <ExternalLink className="w-3 h-3" />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {!loading && reports.length > 0 && (
            <div className="px-4 py-3 text-[11px] text-slate-500 border-t border-slate-800">
              Showing {reports.length} of {total}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatBox({ icon: Icon, label, value, color, testId }) {
  const colors = {
    rose: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
    blue: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
    violet: 'bg-violet-500/10 text-violet-400 border-violet-500/30',
    emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    slate: 'bg-slate-500/10 text-slate-300 border-slate-500/30',
  };
  return (
    <div className={`rounded-xl border p-4 ${colors[color]}`} data-testid={testId}>
      <Icon className="w-4 h-4 mb-2" />
      <p className="text-[10px] uppercase tracking-wider opacity-80 mb-1">{label}</p>
      <p className="text-2xl font-bold text-white">{value ?? 0}</p>
    </div>
  );
}

function FilterSelect({ value, onChange, options, placeholder, testId }) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-[12px] text-white outline-none"
      data-testid={testId}
    >
      <option value="">{placeholder}</option>
      {options.map(o => <option key={o} value={o}>{o}</option>)}
    </select>
  );
}
