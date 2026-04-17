import React, { useState, useEffect, useCallback } from 'react';
import api from '../../utils/api';
import { toast } from 'sonner';
import { Star, Play, Pause, RefreshCw, Trash2, MessageSquare, Users as UsersIcon } from 'lucide-react';

/**
 * Auto Freshness Engine — Admin controls for the daily geo-tagged review seeder.
 * Shows status, allows toggle/config/run-now, and lists recent reviews with delete.
 */
export default function ReviewFreshnessSection() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [dailyCount, setDailyCount] = useState(10);
  const [running, setRunning] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [saving, setSaving] = useState(false);

  const [reviews, setReviews] = useState([]);
  const [listLoading, setListLoading] = useState(false);
  const [filter, setFilter] = useState('approved'); // 'all' | 'approved' | 'pending'

  const fetchStatus = useCallback(async () => {
    try {
      const { data } = await api.get('/api/reviews/admin/scheduler');
      setStatus(data);
      setDailyCount(data.daily_count || 10);
    } catch (e) {
      toast.error('Failed to load scheduler status');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchList = useCallback(async () => {
    setListLoading(true);
    try {
      const params = filter === 'all' ? '' : `?approved=${filter === 'approved'}`;
      const { data } = await api.get(`/api/reviews/admin/list${params}&limit=25`.replace('?&', '?'));
      setReviews(data.reviews || []);
    } catch (e) {
      toast.error('Failed to load reviews');
    } finally {
      setListLoading(false);
    }
  }, [filter]);

  useEffect(() => { fetchStatus(); }, [fetchStatus]);
  useEffect(() => { fetchList(); }, [fetchList]);

  const handleToggle = async () => {
    setToggling(true);
    try {
      const newEnabled = !status?.enabled;
      await api.post('/api/reviews/admin/scheduler/config', { enabled: newEnabled });
      toast.success(newEnabled ? 'Scheduler resumed' : 'Scheduler paused');
      fetchStatus();
    } catch (e) {
      toast.error('Toggle failed');
    } finally {
      setToggling(false);
    }
  };

  const handleSaveCount = async () => {
    setSaving(true);
    try {
      await api.post('/api/reviews/admin/scheduler/config', { daily_count: Number(dailyCount) });
      toast.success(`Daily count set to ${dailyCount}`);
      fetchStatus();
    } catch (e) {
      toast.error('Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleRunNow = async () => {
    setRunning(true);
    try {
      const { data } = await api.post('/api/reviews/admin/scheduler/run-now');
      toast.success(`Added ${data.added} new review${data.added !== 1 ? 's' : ''}`);
      fetchStatus();
      fetchList();
    } catch (e) {
      toast.error('Run failed');
    } finally {
      setRunning(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this review?')) return;
    try {
      await api.delete(`/api/reviews/admin/${id}`);
      toast.success('Review deleted');
      fetchList();
      fetchStatus();
    } catch (e) {
      toast.error('Delete failed');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-5 h-5 text-slate-500 animate-spin" />
      </div>
    );
  }

  const s = status || {};
  const lastRunText = s.last_run_at
    ? new Date(s.last_run_at).toLocaleString()
    : 'Never run';

  return (
    <div className="space-y-6" data-testid="review-freshness-section">
      {/* Status hero */}
      <div className="bg-gradient-to-r from-amber-500/[0.06] to-orange-500/[0.06] border border-amber-500/20 rounded-xl p-6" data-testid="freshness-hero">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <p className="text-[10px] text-amber-400 font-bold uppercase tracking-wider mb-1">Auto Freshness Engine</p>
            <div className="flex items-center gap-3">
              <div className={`w-2.5 h-2.5 rounded-full ${s.enabled ? 'bg-emerald-500 animate-pulse' : 'bg-slate-600'}`} />
              <span className={`text-sm font-semibold ${s.enabled ? 'text-emerald-400' : 'text-slate-500'}`}>
                {s.enabled ? 'RUNNING' : 'PAUSED'}
              </span>
              <span className="text-xs text-slate-500">• Last run: {lastRunText}</span>
              {s.last_run_added > 0 && (
                <span className="text-xs text-slate-500">• Added {s.last_run_added} last batch</span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleToggle}
              disabled={toggling}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors flex items-center gap-1.5 ${
                s.enabled
                  ? 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
                  : 'bg-emerald-500/20 border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/30'
              }`}
              data-testid="freshness-toggle-btn"
            >
              {s.enabled ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
              {s.enabled ? 'Pause' : 'Resume'}
            </button>
            <button
              onClick={handleRunNow}
              disabled={running}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-amber-500/20 border border-amber-500/40 text-amber-400 hover:bg-amber-500/30 transition-colors flex items-center gap-1.5"
              data-testid="freshness-run-now-btn"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${running ? 'animate-spin' : ''}`} />
              {running ? 'Running…' : 'Run now'}
            </button>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-1">
            <MessageSquare className="w-3.5 h-3.5 text-slate-500" />
            <p className="text-[10px] text-slate-500 uppercase tracking-wider">Total Approved</p>
          </div>
          <p className="text-2xl font-bold text-white" data-testid="stat-total-approved">{s.total_approved ?? 0}</p>
        </div>
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-1">
            <UsersIcon className="w-3.5 h-3.5 text-slate-500" />
            <p className="text-[10px] text-slate-500 uppercase tracking-wider">Today</p>
          </div>
          <p className="text-2xl font-bold text-emerald-400" data-testid="stat-today">+{s.today_count ?? 0}</p>
        </div>
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-1">
            <Star className="w-3.5 h-3.5 text-amber-400" />
            <p className="text-[10px] text-slate-500 uppercase tracking-wider">Avg Rating</p>
          </div>
          <p className="text-2xl font-bold text-amber-400" data-testid="stat-avg-rating">{s.avg_rating ?? 0}</p>
        </div>
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-1">
            <RefreshCw className="w-3.5 h-3.5 text-slate-500" />
            <p className="text-[10px] text-slate-500 uppercase tracking-wider">Daily Count</p>
          </div>
          <p className="text-2xl font-bold text-white">{s.daily_count ?? 10}</p>
        </div>
      </div>

      {/* Daily count editor */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-white mb-3">Daily Seed Count</h3>
        <p className="text-xs text-slate-500 mb-4">Number of new geo-tagged reviews to add each day. Min 1, max 50.</p>
        <div className="flex items-center gap-3">
          <input
            type="number"
            min={1}
            max={50}
            value={dailyCount}
            onChange={e => setDailyCount(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white w-24 focus:border-amber-500/50 outline-none"
            data-testid="freshness-daily-count-input"
          />
          <button
            onClick={handleSaveCount}
            disabled={saving || Number(dailyCount) === s.daily_count}
            className="px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-500/20 border border-indigo-500/40 text-indigo-300 hover:bg-indigo-500/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            data-testid="freshness-save-count-btn"
          >
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>

      {/* Review list */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
          <h3 className="text-sm font-semibold text-white">Recent Reviews</h3>
          <div className="flex gap-1 bg-slate-800 rounded-lg p-0.5">
            {['approved', 'pending', 'all'].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1 rounded-md text-[11px] font-medium capitalize transition-colors ${
                  filter === f ? 'bg-slate-700 text-white' : 'text-slate-500 hover:text-slate-300'
                }`}
                data-testid={`review-filter-${f}`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>
        {listLoading ? (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="w-4 h-4 text-slate-500 animate-spin" />
          </div>
        ) : reviews.length === 0 ? (
          <p className="text-center text-slate-500 text-sm py-8">No reviews match this filter</p>
        ) : (
          <div className="space-y-2 max-h-[500px] overflow-y-auto" data-testid="review-admin-list">
            {reviews.map(r => (
              <div
                key={r.id}
                className="flex items-start gap-3 p-3 bg-slate-800/40 border border-slate-800 rounded-lg hover:bg-slate-800/70 transition-colors"
                data-testid={`review-admin-row-${r.id}`}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="text-sm font-medium text-white">{r.name}</span>
                    <div className="flex items-center gap-0.5">
                      {[1,2,3,4,5].map(i => (
                        <Star key={i} className={`w-3 h-3 ${i <= (r.rating || 0) ? 'text-amber-400 fill-amber-400' : 'text-slate-700'}`} />
                      ))}
                    </div>
                    <span className="text-[10px] text-slate-500">{r.rating}</span>
                    {r.city && <span className="text-[10px] text-slate-500">• {r.city}, {r.country}</span>}
                    {r.geo_seeded && <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">AUTO</span>}
                    <span className={`text-[9px] px-1.5 py-0.5 rounded border ${
                      r.approved ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-slate-700 text-slate-400 border-slate-600'
                    }`}>
                      {r.approved ? 'APPROVED' : 'PENDING'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 line-clamp-2">{r.message || r.comment}</p>
                  <p className="text-[10px] text-slate-600 mt-1">{r.createdAt ? new Date(r.createdAt).toLocaleString() : ''}</p>
                </div>
                <button
                  onClick={() => handleDelete(r.id)}
                  className="p-1.5 rounded-lg text-slate-500 hover:bg-red-500/20 hover:text-red-400 transition-colors"
                  title="Delete review"
                  data-testid={`review-admin-delete-${r.id}`}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
