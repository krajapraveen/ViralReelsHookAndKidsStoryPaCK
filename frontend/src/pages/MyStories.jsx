import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, GitBranch, BookOpen, RefreshCw, ChevronRight,
  Loader2, Sparkles, Plus, Image
} from 'lucide-react';
import { Button } from '../components/ui/button';
import api from '../utils/api';

export default function MyStories() {
  const navigate = useNavigate();
  const [chains, setChains] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get('/api/photo-to-comic/my-chains');
        setChains(res.data.chains || []);
      } catch { /* noop */ }
      setLoading(false);
    })();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950">
      <header className="border-b border-slate-800/50 bg-slate-900/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link to="/app">
              <Button variant="ghost" size="sm" className="text-slate-400 hover:text-white px-2">
                <ArrowLeft className="w-4 h-4" />
              </Button>
            </Link>
            <div>
              <h1 className="text-base font-bold text-white">My Stories</h1>
              <p className="text-[10px] text-slate-500">{chains.length} story chain{chains.length !== 1 ? 's' : ''}</p>
            </div>
          </div>
          <Button size="sm" onClick={() => navigate('/app/photo-to-comic')} className="bg-indigo-600 hover:bg-indigo-700">
            <Plus className="w-4 h-4 mr-1" /> New Comic
          </Button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6" data-testid="my-stories-page">
        {chains.length === 0 ? (
          <div className="text-center py-20 space-y-4">
            <div className="w-16 h-16 bg-slate-800 rounded-2xl flex items-center justify-center mx-auto">
              <BookOpen className="w-8 h-8 text-slate-600" />
            </div>
            <h2 className="text-lg font-semibold text-slate-400">No stories yet</h2>
            <p className="text-sm text-slate-500">Create your first comic to start a story chain</p>
            <Button onClick={() => navigate('/app/photo-to-comic')} className="bg-indigo-600 hover:bg-indigo-700">
              <Sparkles className="w-4 h-4 mr-2" /> Create Comic
            </Button>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="chains-grid">
            {chains.map((chain) => {
              const progressPct = chain.progress_pct ?? (chain.total_episodes > 0 ? Math.round((chain.completed / chain.total_episodes) * 100) : 0);
              return (
                <Link
                  key={chain.chain_id}
                  to={`/app/story-chain/${chain.chain_id}`}
                  className="group block rounded-xl border border-slate-800 bg-slate-900/60 hover:border-indigo-500/40 transition-all overflow-hidden"
                  data-testid={`chain-card-${chain.chain_id}`}
                >
                  {/* Preview */}
                  <div className="aspect-video bg-slate-800 relative overflow-hidden">
                    {chain.preview_url ? (
                      <img src={chain.preview_url} alt="" className="w-full h-full object-cover" crossOrigin="anonymous" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Image className="w-8 h-8 text-slate-700" />
                      </div>
                    )}
                    <div className="absolute top-2 left-2 flex gap-1.5">
                      <span className="bg-slate-900/80 backdrop-blur text-[10px] text-white font-medium px-2 py-0.5 rounded-full flex items-center gap-1">
                        <GitBranch className="w-3 h-3" /> {chain.total_episodes} ep
                      </span>
                    </div>
                    <div className="absolute bottom-2 right-2 flex gap-1">
                      {chain.continuations > 0 && (
                        <span className="bg-blue-500/20 backdrop-blur text-[10px] text-blue-400 px-1.5 py-0.5 rounded-full">
                          {chain.continuations} cont
                        </span>
                      )}
                      {chain.remixes > 0 && (
                        <span className="bg-pink-500/20 backdrop-blur text-[10px] text-pink-400 px-1.5 py-0.5 rounded-full">
                          {chain.remixes} remix
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Info */}
                  <div className="p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex gap-1">
                        {chain.styles_used?.slice(0, 2).map(s => (
                          <span key={s} className="text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded">{s}</span>
                        ))}
                      </div>
                      <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-indigo-400 transition-colors" />
                    </div>

                    {/* Progress bar */}
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-cyan-400 transition-all duration-500"
                          style={{ width: `${progressPct}%` }}
                        />
                      </div>
                      <span className="text-[10px] text-slate-500">{progressPct}%</span>
                    </div>

                    <p className="text-xs text-slate-500">
                      {chain.completed}/{chain.total_episodes} completed
                    </p>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
