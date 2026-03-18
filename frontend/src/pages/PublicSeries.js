import React, { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import {
  BookOpen, Film, Users, Globe, ChevronRight,
  Eye, CheckCircle, Loader2, ArrowLeft, Sparkles
} from 'lucide-react';
import api from '../utils/api';

export default function PublicSeries() {
  const { seriesId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get(`/api/story-series/public/${seriesId}`);
        setData(res.data);
      } catch {
        setError('Series not found or not public');
      } finally {
        setLoading(false);
      }
    })();
  }, [seriesId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  if (error || !data?.series) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center gap-4 text-center px-4">
        <BookOpen className="w-12 h-12 text-slate-700" />
        <h1 className="text-xl font-bold text-white">Series Not Available</h1>
        <p className="text-sm text-slate-500 max-w-md">{error || 'This series is private or does not exist.'}</p>
        <Button onClick={() => navigate('/')} className="bg-indigo-600 hover:bg-indigo-700 text-white mt-4 gap-2" data-testid="go-home-btn">
          <ArrowLeft className="w-4 h-4" /> Go Home
        </Button>
      </div>
    );
  }

  const { series, episodes = [], character_bible, world_bible } = data;

  return (
    <div className="min-h-screen bg-slate-950" data-testid="public-series-page">
      <header className="border-b border-slate-800/50 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-white">{series.title}</h1>
            <p className="text-xs text-slate-500">{series.genre} &middot; {episodes.length} episodes</p>
          </div>
          <Button
            onClick={() => navigate('/app/story-series/create')}
            className="bg-indigo-600 hover:bg-indigo-700 text-white gap-2 text-xs"
            data-testid="create-your-own-btn"
          >
            <Sparkles className="w-3 h-3" /> Create Your Own
          </Button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* Series Description */}
        {series.description && (
          <p className="text-sm text-slate-400 mb-8 leading-relaxed max-w-2xl">{series.description}</p>
        )}

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Episodes */}
          <div className="lg:col-span-2 space-y-3">
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider mb-3 flex items-center gap-2">
              <Film className="w-4 h-4 text-indigo-400" /> Episodes
            </h2>
            {episodes.length === 0 ? (
              <p className="text-sm text-slate-600 py-8 text-center">No episodes available yet.</p>
            ) : (
              episodes.map((ep) => (
                <div key={ep.episode_id} className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center gap-4" data-testid={`public-ep-${ep.episode_id}`}>
                  <div className="w-10 h-10 rounded-lg flex items-center justify-center text-sm font-bold flex-shrink-0 text-emerald-400 bg-emerald-500/10 border border-emerald-500/20">
                    {ep.episode_number}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold text-white truncate">{ep.title}</h3>
                    <p className="text-xs text-slate-500 truncate">{ep.summary}</p>
                  </div>
                  {ep.thumbnail_url && (
                    <img src={ep.thumbnail_url} alt="" className="w-20 h-12 rounded object-cover flex-shrink-0" style={{ aspectRatio: '16/10' }} />
                  )}
                  {ep.output_asset_url && (
                    <a href={ep.output_asset_url} target="_blank" rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded-md flex-shrink-0"
                    >
                      <Eye className="w-3 h-3" /> Watch
                    </a>
                  )}
                </div>
              ))
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            {character_bible?.characters?.length > 0 && (
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
                <h4 className="text-xs font-medium text-slate-400 mb-3 flex items-center gap-1.5">
                  <Users className="w-3 h-3" /> Characters
                </h4>
                <div className="space-y-2">
                  {character_bible.characters.map((c, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-full bg-indigo-500/20 flex items-center justify-center text-[10px] text-indigo-400 font-bold flex-shrink-0">
                        {(c.name || '?')[0]}
                      </div>
                      <span className="text-xs text-white font-medium">{c.name}</span>
                      <span className="text-[10px] text-slate-500">{c.role}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {world_bible?.world_name && (
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
                <h4 className="text-xs font-medium text-slate-400 mb-2 flex items-center gap-1.5">
                  <Globe className="w-3 h-3" /> World
                </h4>
                <p className="text-xs text-slate-300">{world_bible.world_name}</p>
                {world_bible.setting_description && (
                  <p className="text-[11px] text-slate-500 mt-1 line-clamp-4">{world_bible.setting_description}</p>
                )}
              </div>
            )}

            <div className="bg-indigo-500/5 border border-indigo-500/20 rounded-xl p-5 text-center">
              <Sparkles className="w-6 h-6 text-indigo-400 mx-auto mb-2" />
              <p className="text-sm text-white font-medium mb-1">Create your own series</p>
              <p className="text-xs text-slate-500 mb-3">Turn any idea into a multi-episode story universe</p>
              <Button
                onClick={() => navigate('/app/story-series/create')}
                className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs w-full"
                data-testid="cta-create-series"
              >
                Start Creating
              </Button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
