import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Palette, Mic, Sparkles, Plus, Edit2, Trash2, Save, X, Loader2 } from 'lucide-react';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';

const api = {
  get: async (url) => {
    const token = localStorage.getItem('token');
    const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}${url}`, {
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw { response: { data: err, status: res.status } };
    }
    return { data: await res.json() };
  },
  post: async (url, body) => {
    const token = localStorage.getItem('token');
    const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}${url}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw { response: { data: err, status: res.status } };
    }
    return { data: await res.json() };
  },
  patch: async (url, body) => {
    const token = localStorage.getItem('token');
    const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}${url}`, {
      method: 'PATCH',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw { response: { data: err, status: res.status } };
    }
    return { data: await res.json() };
  },
  delete: async (url) => {
    const token = localStorage.getItem('token');
    const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}${url}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw { response: { data: err, status: res.status } };
    }
    return { data: await res.json() };
  },
};

const STYLES = ['Anime', 'Cartoon', 'Realistic', 'Watercolor', 'Pixel Art', 'Chibi'];
const VOICES = ['Male', 'Female', 'Narrator', 'Child', 'Custom'];
const COLORS = [
  'bg-purple-500', 'bg-blue-500', 'bg-emerald-500', 'bg-pink-500',
  'bg-amber-500', 'bg-teal-500', 'bg-rose-500', 'bg-indigo-500',
];

function CharacterCard({ char, onEdit, onDelete }) {
  const colorIdx = (char.name || '').charCodeAt(0) % COLORS.length;
  return (
    <div className="bg-slate-800/40 border border-slate-700/40 rounded-xl p-5 hover:border-purple-500/30 transition-all group" data-testid={`char-card-${char.id}`}>
      <div className="flex items-start gap-4">
        <div className={`w-14 h-14 rounded-xl ${COLORS[colorIdx]} flex items-center justify-center flex-shrink-0`}>
          <span className="text-white text-xl font-bold">{(char.name || '?')[0].toUpperCase()}</span>
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-white truncate">{char.name}</h4>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-[11px] text-slate-400 flex items-center gap-1"><Palette className="w-3 h-3" /> {char.style || 'Default'}</span>
            <span className="text-[11px] text-slate-400 flex items-center gap-1"><Mic className="w-3 h-3" /> {char.voice || 'Default'}</span>
          </div>
          {char.personality && <p className="text-xs text-slate-500 mt-2 line-clamp-2">{char.personality}</p>}
        </div>
      </div>
      <div className="flex gap-2 mt-4 opacity-0 group-hover:opacity-100 transition-opacity">
        <Button size="sm" variant="outline" className="flex-1 h-7 text-[11px] border-slate-600 text-slate-300" onClick={() => onEdit(char)}>
          <Edit2 className="w-3 h-3 mr-1" /> Edit
        </Button>
        <Button size="sm" variant="outline" className="h-7 px-2 border-red-500/30 text-red-400 hover:bg-red-500/10" onClick={() => onDelete(char)}>
          <Trash2 className="w-3 h-3" />
        </Button>
      </div>
    </div>
  );
}

function CharacterEditor({ character, onSave, onCancel }) {
  const [name, setName] = useState(character?.name || '');
  const [style, setStyle] = useState(character?.style || 'Cartoon');
  const [voice, setVoice] = useState(character?.voice || 'Narrator');
  const [personality, setPersonality] = useState(character?.personality || '');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!name.trim()) { toast.error('Name is required'); return; }
    setSaving(true);
    try {
      await onSave({ ...character, name: name.trim(), style, voice, personality: personality.trim() });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" data-testid="character-editor-modal">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-md w-full p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-bold text-white">{character?.id ? 'Edit Character' : 'Create Character'}</h3>
          <button onClick={onCancel} className="text-slate-400 hover:text-white"><X className="w-5 h-5" /></button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-sm text-slate-300 mb-1.5 block">Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Character name"
              className="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-purple-500/50"
              data-testid="char-name-input" />
          </div>

          <div>
            <label className="text-sm text-slate-300 mb-1.5 block">Art Style</label>
            <div className="flex flex-wrap gap-2">
              {STYLES.map(s => (
                <button key={s} onClick={() => setStyle(s)}
                  className={`px-3 py-1 text-xs rounded-lg border transition-colors ${
                    style === s ? 'border-purple-500 bg-purple-500/10 text-purple-300' : 'border-slate-700 text-slate-400 hover:border-slate-600'
                  }`} data-testid={`style-${s.toLowerCase()}`}>
                  {s}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-sm text-slate-300 mb-1.5 block">Voice</label>
            <div className="flex flex-wrap gap-2">
              {VOICES.map(v => (
                <button key={v} onClick={() => setVoice(v)}
                  className={`px-3 py-1 text-xs rounded-lg border transition-colors ${
                    voice === v ? 'border-purple-500 bg-purple-500/10 text-purple-300' : 'border-slate-700 text-slate-400 hover:border-slate-600'
                  }`} data-testid={`voice-${v.toLowerCase()}`}>
                  {v}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-sm text-slate-300 mb-1.5 block">Personality</label>
            <textarea value={personality} onChange={(e) => setPersonality(e.target.value)}
              placeholder="Describe their personality, traits, quirks..."
              rows={3}
              className="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-purple-500/50 resize-none"
              data-testid="char-personality-input" />
          </div>
        </div>

        <div className="flex gap-3 mt-6">
          <Button onClick={handleSave} disabled={saving} className="flex-1 bg-purple-600 hover:bg-purple-700" data-testid="save-character-btn">
            {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Save className="w-4 h-4 mr-2" />}
            {character?.id ? 'Update' : 'Create'} Character
          </Button>
          <Button onClick={onCancel} variant="outline" className="border-slate-600 text-slate-300">Cancel</Button>
        </div>
      </div>
    </div>
  );
}

export default function CharactersPage() {
  const [characters, setCharacters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingChar, setEditingChar] = useState(null);
  const [showEditor, setShowEditor] = useState(false);

  const fetchCharacters = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/api/characters/my-characters');
      if (res.data.success) {
        const STYLE_REVERSE = {
          'anime': 'Anime', 'cartoon_2d': 'Cartoon', 'cinematic': 'Realistic',
          'watercolor': 'Watercolor', 'comic': 'Comic Book',
        };
        setCharacters((res.data.characters || []).map(c => ({
          ...c,
          id: c.character_id || c.id,
          style: STYLE_REVERSE[c.style_lock] || c.style_lock || c.species_or_type || 'Default',
          voice: c.gender_presentation || c.voice || 'Default',
          personality: c.personality_summary || c.personality || '',
        })));
      } else {
        setCharacters([]);
      }
    } catch {
      setCharacters([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchCharacters(); }, [fetchCharacters]);

  const handleSave = async (charData) => {
    try {
      if (charData.id) {
        // Update existing character
        await api.patch(`/api/characters/${charData.id}`, {
          name: charData.name,
          personality_summary: charData.personality,
        });
        toast.success('Character updated!');
      } else {
        // Create new — map simple form fields to backend schema
        const STYLE_MAP = {
          'Anime': 'anime', 'Cartoon': 'cartoon_2d', 'Realistic': 'cinematic',
          'Watercolor': 'watercolor', 'Pixel Art': 'comic', 'Chibi': 'cartoon_2d',
        };
        await api.post('/api/characters/create', {
          name: charData.name,
          personality_summary: charData.personality || 'A unique character',
          style_lock: STYLE_MAP[charData.style] || 'cartoon_2d',
          gender_presentation: charData.voice === 'Male' ? 'male' : charData.voice === 'Female' ? 'female' : charData.voice?.toLowerCase() || '',
          species_or_type: 'human',
          role: 'hero',
          age_band: 'adult',
        });
        toast.success('Character created!');
      }
      setShowEditor(false);
      setEditingChar(null);
      fetchCharacters();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      if (detail?.error === 'safety_block') {
        toast.error(detail.reason || 'Character blocked by safety filter');
      } else if (typeof detail === 'string') {
        toast.error(detail);
      } else {
        toast.error('Failed to save character');
      }
    }
  };

  const handleDelete = async (char) => {
    if (!window.confirm(`Delete "${char.name}"?`)) return;
    try {
      await api.delete(`/api/characters/${char.id}`);
      toast.success('Character deleted');
      fetchCharacters();
    } catch {
      toast.error('Failed to delete');
    }
  };

  const openNew = () => { setEditingChar(null); setShowEditor(true); };
  const openEdit = (char) => { setEditingChar(char); setShowEditor(true); };

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white" data-testid="characters-page">
      <div className="max-w-5xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-white">Character Studio</h1>
            <p className="text-slate-400 text-sm mt-1">Create and manage reusable characters for your stories</p>
          </div>
          <Button onClick={openNew} className="bg-purple-600 hover:bg-purple-700" data-testid="create-character-btn">
            <Plus className="w-4 h-4 mr-2" /> New Character
          </Button>
        </div>

        {/* Character Grid */}
        {loading ? (
          <div className="flex justify-center py-20">
            <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
          </div>
        ) : characters.length === 0 ? (
          <div className="text-center py-20" data-testid="char-empty-state">
            <User className="w-16 h-16 text-slate-700 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-slate-400 mb-2">No characters yet</h3>
            <p className="text-slate-500 text-sm mb-6">Create a character to use across your stories</p>
            <Button onClick={openNew} className="bg-purple-600 hover:bg-purple-700">
              <Plus className="w-4 h-4 mr-2" /> Create Your First Character
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="character-grid">
            {characters.map(char => (
              <CharacterCard key={char.id} char={char} onEdit={openEdit} onDelete={handleDelete} />
            ))}
          </div>
        )}

        {/* Editor Modal */}
        {showEditor && (
          <CharacterEditor
            character={editingChar}
            onSave={handleSave}
            onCancel={() => { setShowEditor(false); setEditingChar(null); }}
          />
        )}
      </div>
    </div>
  );
}
