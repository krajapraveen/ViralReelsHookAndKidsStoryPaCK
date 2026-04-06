import { useState, useEffect, useCallback } from 'react';
import { Search, Filter, Eye, EyeOff, CheckCircle, Star, RefreshCw, ChevronLeft, ChevronRight, MessageSquare } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const RATING_COLORS = {
  great: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  good: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
  okay: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  poor: 'bg-red-500/15 text-red-400 border-red-500/30',
};

const SOURCE_LABELS = {
  logout_prompt: 'Logout',
  idle_prompt: 'Idle',
  manual_feedback: 'Manual',
};

export default function AdminFeedbackPage() {
  const [items, setItems] = useState([]);
  const [pagination, setPagination] = useState({ page: 1, total: 0, has_next: false });
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ rating: '', source: '', read_by_admin: '', search: '' });
  const token = localStorage.getItem('token');

  const fetchFeedback = useCallback(async (page = 1) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page, page_size: 20 });
      if (filters.rating) params.set('rating', filters.rating);
      if (filters.source) params.set('source', filters.source);
      if (filters.read_by_admin) params.set('read_by_admin', filters.read_by_admin);
      if (filters.search) params.set('search', filters.search);

      const res = await fetch(`${API}/api/admin/feedback?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (data.success) {
        setItems(data.data.items);
        setPagination(data.data.pagination);
      }
    } catch (err) {
      toast.error('Failed to load feedback');
    } finally {
      setLoading(false);
    }
  }, [filters, token]);

  const fetchUnread = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/admin/feedback/unread-count`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (data.success) setUnreadCount(data.data.unread_count);
    } catch {}
  }, [token]);

  useEffect(() => { fetchFeedback(1); fetchUnread(); }, [fetchFeedback, fetchUnread]);

  const markRead = async (id) => {
    try {
      const res = await fetch(`${API}/api/admin/feedback/${id}/mark-read`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (data.success) {
        setItems((prev) => prev.map((i) => (i.id === id ? { ...i, read_by_admin: true } : i)));
        setUnreadCount((c) => Math.max(0, c - 1));
        toast.success('Marked as read');
      }
    } catch {
      toast.error('Failed to mark as read');
    }
  };

  const markAllRead = async () => {
    const unreadIds = items.filter((i) => !i.read_by_admin).map((i) => i.id);
    if (!unreadIds.length) return;
    try {
      const res = await fetch(`${API}/api/admin/feedback/mark-read-bulk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ feedback_ids: unreadIds }),
      });
      const data = await res.json();
      if (data.success) {
        setItems((prev) => prev.map((i) => (unreadIds.includes(i.id) ? { ...i, read_by_admin: true } : i)));
        setUnreadCount((c) => Math.max(0, c - unreadIds.length));
        toast.success(`${unreadIds.length} marked as read`);
      }
    } catch {
      toast.error('Failed to mark as read');
    }
  };

  const formatDate = (iso) => {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch { return iso; }
  };

  return (
    <div className="space-y-6" data-testid="admin-feedback-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <MessageSquare className="w-6 h-6 text-indigo-400" />
          <div>
            <h1 className="text-xl font-bold text-white">User Feedback</h1>
            <p className="text-sm text-slate-400">Post-usage experience feedback from real users</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {unreadCount > 0 && (
            <span className="px-3 py-1 bg-red-500/20 text-red-400 text-sm font-bold rounded-full border border-red-500/30" data-testid="unread-badge">
              {unreadCount} unread
            </span>
          )}
          <Button onClick={() => { fetchFeedback(1); fetchUnread(); }} variant="outline" size="sm" className="border-slate-700 text-slate-300" data-testid="refresh-feedback">
            <RefreshCw className="w-4 h-4 mr-1.5" /> Refresh
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 bg-slate-900 border border-slate-800 rounded-xl p-4" data-testid="feedback-filters">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            value={filters.search}
            onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
            placeholder="Search by email or text..."
            className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-3 py-2 text-sm text-white placeholder-slate-500"
            data-testid="feedback-search"
          />
        </div>
        <select value={filters.rating} onChange={(e) => setFilters((f) => ({ ...f, rating: e.target.value }))} className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" data-testid="filter-rating">
          <option value="">All ratings</option>
          <option value="great">Great</option>
          <option value="good">Good</option>
          <option value="okay">Okay</option>
          <option value="poor">Poor</option>
        </select>
        <select value={filters.source} onChange={(e) => setFilters((f) => ({ ...f, source: e.target.value }))} className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" data-testid="filter-source">
          <option value="">All sources</option>
          <option value="logout_prompt">Logout</option>
          <option value="idle_prompt">Idle</option>
          <option value="manual_feedback">Manual</option>
        </select>
        <select value={filters.read_by_admin} onChange={(e) => setFilters((f) => ({ ...f, read_by_admin: e.target.value }))} className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" data-testid="filter-read">
          <option value="">All</option>
          <option value="false">Unread only</option>
          <option value="true">Read only</option>
        </select>
        {items.some((i) => !i.read_by_admin) && (
          <Button onClick={markAllRead} size="sm" className="bg-indigo-600 hover:bg-indigo-500 text-white" data-testid="mark-all-read">
            <CheckCircle className="w-3.5 h-3.5 mr-1" /> Mark page read
          </Button>
        )}
      </div>

      {/* List */}
      {loading ? (
        <div className="text-center py-12 text-slate-500">Loading feedback...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12" data-testid="no-feedback">
          <MessageSquare className="w-12 h-12 text-slate-700 mx-auto mb-3" />
          <p className="text-slate-400 text-sm">No feedback yet</p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((fb) => (
            <div
              key={fb.id}
              className={`bg-slate-900 border rounded-xl p-4 transition-all ${fb.read_by_admin ? 'border-slate-800 opacity-80' : 'border-indigo-500/30 ring-1 ring-indigo-500/10'}`}
              data-testid={`feedback-item-${fb.id}`}
            >
              <div className="flex items-start justify-between gap-4 mb-3">
                <div className="flex items-center gap-3 min-w-0">
                  <span className={`px-2.5 py-1 rounded-lg text-xs font-bold border ${RATING_COLORS[fb.rating] || 'bg-slate-800 text-slate-400 border-slate-700'}`}>
                    {fb.rating?.toUpperCase()}
                  </span>
                  <span className="text-sm text-white font-medium truncate">{fb.user_email}</span>
                  <span className="text-xs text-slate-500 shrink-0">{formatDate(fb.created_at)}</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-800 text-slate-400 border border-slate-700 shrink-0">
                    {SOURCE_LABELS[fb.source] || fb.source}
                  </span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {!fb.read_by_admin && (
                    <button onClick={() => markRead(fb.id)} className="p-1.5 text-indigo-400 hover:text-white hover:bg-indigo-500/20 rounded-lg transition-colors" data-testid={`mark-read-${fb.id}`}>
                      <Eye className="w-4 h-4" />
                    </button>
                  )}
                  {fb.read_by_admin && <EyeOff className="w-4 h-4 text-slate-600" />}
                </div>
              </div>

              <div className="grid gap-2 text-sm">
                {fb.liked && (
                  <div className="flex gap-2">
                    <span className="text-emerald-400 font-medium shrink-0">Liked:</span>
                    <span className="text-slate-300">{fb.liked}</span>
                  </div>
                )}
                <div className="flex gap-2">
                  <span className="text-amber-400 font-medium shrink-0">Improve:</span>
                  <span className="text-slate-300">{fb.improvements}</span>
                </div>
                <div className="flex items-center gap-4 text-xs text-slate-500">
                  <span>Reuse: <strong className="text-slate-300">{fb.reuse_intent}</strong></span>
                  {fb.feature_context?.length > 0 && (
                    <span>Features: {fb.feature_context.join(', ')}</span>
                  )}
                  {fb.meta?.device && <span>{fb.meta.device}</span>}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {pagination.total > 20 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-500">
            Page {pagination.page} of {Math.ceil(pagination.total / 20)} ({pagination.total} total)
          </span>
          <div className="flex gap-2">
            <Button
              onClick={() => fetchFeedback(pagination.page - 1)}
              disabled={pagination.page <= 1}
              variant="outline"
              size="sm"
              className="border-slate-700 text-slate-300"
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <Button
              onClick={() => fetchFeedback(pagination.page + 1)}
              disabled={!pagination.has_next}
              variant="outline"
              size="sm"
              className="border-slate-700 text-slate-300"
            >
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
