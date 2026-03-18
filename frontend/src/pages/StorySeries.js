import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import {
  ArrowLeft, Loader2, Plus, BookOpen, Clock,
  ChevronRight, Film, Sparkles
} from 'lucide-react';
import api from '../utils/api';

export default function StorySeries() {
  const [loading, setLoading] = useState(true);
  const [series, setSeries] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    fetchSeries();
  }, []);

  const fetchSeries = async () => {
    try {
      const res = await api.get('/api/story-series/my-series');
      setSeries(res.data.series || []);
    } catch (err) {
      toast.error('Failed to load series');
    } finally {
      setLoading(false);
    }
  };

  const statusColor = (status) => {
    if (status === 'ready') return 'text-emerald-400 bg-emerald-500/10';
    if (status === 'generating') return 'text-amber-400 bg-amber-500/10';
    if (status === 'planned') return 'text-indigo-400 bg-indigo-500/10';
    if (status === 'failed') return 'text-red-400 bg-red-500/10';
    return 'text-slate-400 bg-slate-500/10';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950" data-testid="story-series-hub">
      <header className="border-b border-slate-800/50 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app" className="text-slate-400 hover:text-white transition-colors">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-indigo-500/20 flex items-center justify-center">
                <BookOpen className="w-5 h-5 text-indigo-400" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-white">Story Series</h1>
                <p className="text-xs text-slate-500">Your narrative universes</p>
              </div>
            </div>
          </div>
          <Button
            onClick={() => navigate('/app/story-series/create')}
            className="bg-indigo-600 hover:bg-indigo-700 text-white gap-2"
            data-testid="create-series-btn"
          >
            <Plus className="w-4 h-4" /> New Series
          </Button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-8">
        {series.length === 0 ? (
          <div className="text-center py-24" data-testid="empty-series-state">
            <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-slate-800 flex items-center justify-center">
              <Film className="w-10 h-10 text-slate-600" />
            </div>
            <h2 className="text-xl font-semibold text-white mb-2">No series yet</h2>
            <p className="text-sm text-slate-500 mb-8 max-w-md mx-auto">
              Create your first story series — a multi-episode universe with characters,
              world-building, and narrative continuity.
            </p>
            <Button
              onClick={() => navigate('/app/story-series/create')}
              className="bg-indigo-600 hover:bg-indigo-700 text-white gap-2"
              data-testid="create-first-series-btn"
            >
              <Sparkles className="w-4 h-4" /> Create Your First Series
            </Button>
          </div>
        ) : (
          <div className="grid gap-4" data-testid="series-list">
            {series.map((s) => (
              <button
                key={s.series_id}
                onClick={() => navigate(`/app/story-series/${s.series_id}`)}
                className="w-full text-left bg-slate-900/60 border border-slate-800 rounded-xl p-5 hover:border-indigo-500/40 transition-all group"
                data-testid={`series-card-${s.series_id}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-base font-semibold text-white truncate">{s.title}</h3>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusColor(s.status)}`}>
                        {s.status}
                      </span>
                    </div>
                    <p className="text-sm text-slate-400 line-clamp-2 mb-3">{s.description}</p>
                    <div className="flex items-center gap-4 text-xs text-slate-500">
                      <span className="flex items-center gap-1">
                        <Film className="w-3 h-3" />
                        {s.episode_count || 0} episode{(s.episode_count || 0) !== 1 ? 's' : ''}
                      </span>
                      <span>{s.genre}</span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(s.updated_at || s.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    {s.next_hook && (
                      <p className="mt-3 text-xs text-amber-400/80 italic line-clamp-1">
                        Next: "{s.next_hook}"
                      </p>
                    )}
                  </div>
                  <ChevronRight className="w-5 h-5 text-slate-600 group-hover:text-indigo-400 transition-colors mt-1 flex-shrink-0" />
                </div>
              </button>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
