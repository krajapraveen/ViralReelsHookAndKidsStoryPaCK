import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { ArrowLeft, Plus, Loader2, User, BookOpen } from 'lucide-react';

export default function CharacterLibrary() {
  const navigate = useNavigate();
  const [characters, setCharacters] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/api/characters/my-characters')
      .then(res => { setCharacters(res.data.characters || []); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
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

        {/* Empty state */}
        {characters.length === 0 ? (
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-12 text-center">
            <div className="w-16 h-16 mx-auto rounded-2xl bg-indigo-500/15 flex items-center justify-center mb-4">
              <User className="w-8 h-8 text-indigo-400" />
            </div>
            <h2 className="text-lg font-semibold text-white mb-2">No characters yet</h2>
            <p className="text-sm text-slate-400 mb-6 max-w-md mx-auto">
              Create persistent characters with locked visual identity, personality, and memory that stay consistent across every episode.
            </p>
            <Button size="sm" onClick={() => navigate('/app/characters/create')} className="bg-indigo-600 hover:bg-indigo-500">
              Create Your First Character
            </Button>
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
