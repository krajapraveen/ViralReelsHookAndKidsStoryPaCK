import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { ArrowLeft, Plus, Loader2, User, BookOpen, Search, AlertCircle, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

const ROLE_FILTERS = ['all', 'hero', 'villain', 'sidekick', 'narrator', 'mentor', 'trickster'];

export default function CharacterLibrary() {
  const navigate = useNavigate();
  const [characters, setCharacters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('all');
  const [sortBy, setSortBy] = useState('updated_at');

  const fetchCharacters = () => {
    const params = new URLSearchParams();
    if (searchQuery) params.set('q', searchQuery);
    if (roleFilter !== 'all') params.set('role', roleFilter);
    params.set('sort_by', sortBy);

    const url = searchQuery || roleFilter !== 'all'
      ? `/api/characters/search/query?${params}`
      : '/api/characters/my-characters';

    api.get(url)
      .then(res => {
        setCharacters(res.data.characters || []);
        setLoadError(false);
      })
      .catch(() => {
        setLoadError(true);
        toast.error('Failed to load characters');
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchCharacters(); }, [roleFilter, sortBy]);

  const handleSearch = (e) => {
    e.preventDefault();
    setLoading(true);
    fetchCharacters();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
      </div>
    );
  }

  if (loadError && characters.length === 0) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center" data-testid="character-library-error">
        <div className="text-center space-y-4">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto" />
          <h2 className="text-lg font-bold text-white">Failed to load characters</h2>
          <p className="text-sm text-slate-400">Check your connection and try again</p>
          <Button onClick={() => { setLoading(true); fetchCharacters(); }} className="bg-indigo-600 hover:bg-indigo-500" data-testid="character-library-retry-btn">
            <RefreshCw className="w-4 h-4 mr-2" /> Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950" data-testid="character-library-page">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate('/app')} data-testid="back-to-dashboard">
              <ArrowLeft className="w-4 h-4" />
            </Button>
            <div>
              <h1 className="text-xl font-bold text-white">My Characters</h1>
              <p className="text-sm text-slate-400">{characters.length} persistent character{characters.length !== 1 ? 's' : ''}</p>
            </div>
          </div>
          <Button size="sm" onClick={() => navigate('/app/characters/create')} className="bg-indigo-600 hover:bg-indigo-500 gap-1.5" data-testid="create-character-btn">
            <Plus className="w-4 h-4" /> New Character
          </Button>
        </div>

        {/* Search / Filter / Sort */}
        <div className="flex items-center gap-3 mb-6">
          <form onSubmit={handleSearch} className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
            <input
              type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search by name..."
              className="w-full bg-slate-900/60 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-slate-500 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
              data-testid="search-input"
            />
          </form>
          <div className="flex items-center gap-1.5">
            {ROLE_FILTERS.map(r => (
              <button key={r} onClick={() => { setRoleFilter(r); setLoading(true); }}
                className={`px-2.5 py-1.5 rounded-md text-xs capitalize transition-all ${roleFilter === r ? 'bg-indigo-500/20 text-indigo-300 ring-1 ring-indigo-500/30' : 'bg-slate-900/60 text-slate-500 hover:text-slate-300'}`}
                data-testid={`filter-${r}`}
              >{r}</button>
            ))}
          </div>
          <select value={sortBy} onChange={e => { setSortBy(e.target.value); setLoading(true); }}
            className="bg-slate-900/60 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-400 outline-none"
            data-testid="sort-select"
          >
            <option value="updated_at">Last used</option>
            <option value="created_at">Created</option>
            <option value="name">Name</option>
          </select>
        </div>

        {/* Empty state */}
        {characters.length === 0 ? (
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-12 text-center">
            <div className="w-16 h-16 mx-auto rounded-2xl bg-cyan-500/15 flex items-center justify-center mb-4">
              <User className="w-8 h-8 text-cyan-400" />
            </div>
            <h2 className="text-lg font-semibold text-white mb-2">Build Your Character Cast</h2>
            <p className="text-sm text-slate-400 mb-3 max-w-md mx-auto">
              Characters created here get persistent visual identity, personality memory, and stay consistent across every story tool.
            </p>
            <div className="bg-slate-800/60 border border-slate-700/40 rounded-lg px-4 py-2.5 inline-block mb-6">
              <p className="text-xs text-slate-500">
                <span className="text-cyan-400 font-medium">Tip:</span> Characters are also auto-detected when you create a Story Series
              </p>
            </div>
            <div>
              <Button size="sm" onClick={() => navigate('/app/characters/create')} className="bg-cyan-600 hover:bg-cyan-500 text-white">
                Create Your First Character
              </Button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {characters.map(c => (
              <button
                key={c.character_id}
                onClick={() => navigate(`/app/characters/${c.character_id}`)}
                className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 text-left hover:border-indigo-500/30 hover:bg-slate-900/80 transition-all group"
                data-testid={`character-card-${c.character_id}`}
              >
                <div className="flex items-center gap-3 mb-3">
                  {c.portrait_url ? (
                    <img src={c.portrait_url} alt={c.name} className="w-12 h-12 rounded-lg object-cover" />
                  ) : (
                    <div className="w-12 h-12 rounded-lg bg-indigo-500/15 flex items-center justify-center">
                      <User className="w-6 h-6 text-indigo-400" />
                    </div>
                  )}
                  <div className="min-w-0">
                    <div className="text-white font-medium truncate group-hover:text-indigo-300 transition-colors">{c.name}</div>
                    <div className="text-xs text-slate-500">{c.species_or_type} {c.role}</div>
                  </div>
                </div>
                {c.visual_summary && (
                  <p className="text-xs text-slate-400 line-clamp-2 mb-3">{c.visual_summary}</p>
                )}
                <div className="flex items-center justify-between text-xs text-slate-600">
                  <span className="capitalize">{c.style_lock?.replace('_', ' ')}</span>
                  <span className="flex items-center gap-1">
                    <BookOpen className="w-3 h-3" />
                    {c.memory_entries} memories
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
