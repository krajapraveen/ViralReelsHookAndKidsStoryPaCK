import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import {
  ArrowLeft, Loader2, Sparkles, BookOpen, Users,
  Globe, Palette, Check, X, Edit3, Shield, ChevronRight
} from 'lucide-react';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import api from '../utils/api';

const GENRES = ['adventure', 'mystery', 'comedy', 'fantasy', 'sci-fi', 'horror', 'romance', 'slice-of-life'];
const AUDIENCES = [
  { value: 'kids_2_5', label: '2-5 years' },
  { value: 'kids_5_8', label: '5-8 years' },
  { value: 'kids_8_12', label: '8-12 years' },
  { value: 'teens', label: 'Teens' },
  { value: 'adults', label: 'Adults' },
];
const STYLES = [
  { value: 'cartoon_2d', label: 'Cartoon 2D' },
  { value: 'anime', label: 'Anime' },
  { value: 'watercolor', label: 'Watercolor' },
  { value: 'pixel_art', label: 'Pixel Art' },
  { value: 'comic_book', label: 'Comic Book' },
  { value: 'realistic', label: 'Realistic' },
];

const ROLE_COLORS = {
  protagonist: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
  antagonist: 'text-red-400 bg-red-500/10 border-red-500/20',
  sidekick: 'text-sky-400 bg-sky-500/10 border-sky-500/20',
  mentor: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
  main: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
  supporting: 'text-sky-400 bg-sky-500/10 border-sky-500/20',
};

export default function CreateSeries() {
  const navigate = useNavigate();
  const [step, setStep] = useState('form'); // 'form' | 'confirm'
  const [creating, setCreating] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [seriesData, setSeriesData] = useState(null);
  const [extractedChars, setExtractedChars] = useState([]);
  const [editingIdx, setEditingIdx] = useState(null);

  const [form, setForm] = useState({
    title: '',
    initial_prompt: '',
    genre: 'adventure',
    audience: 'kids_5_8',
    style: 'cartoon_2d',
    tool: 'story_video',
  });

  const update = (key, val) => setForm(prev => ({ ...prev, [key]: val }));

  const handleCreate = async () => {
    if (!form.title.trim()) { toast.error('Title is required'); return; }
    if (!form.initial_prompt.trim()) { toast.error('Story prompt is required'); return; }
    setCreating(true);
    try {
      const res = await api.post('/api/story-series/create', form);
      if (res.data.success) {
        setSeriesData(res.data);
        const chars = res.data.extracted_characters || [];
        // Mark all as confirmed by default
        setExtractedChars(chars.map(c => ({ ...c, confirmed: true })));
        if (chars.length > 0) {
          setStep('confirm');
          toast.success('Series created! Review detected characters.');
        } else {
          toast.success(`Series "${res.data.title}" created!`);
          navigate(`/app/story-series/${res.data.series_id}`);
        }
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create series');
    } finally {
      setCreating(false);
    }
  };

  const toggleChar = (idx) => {
    setExtractedChars(prev => prev.map((c, i) =>
      i === idx ? { ...c, confirmed: !c.confirmed } : c
    ));
  };

  const updateCharField = (idx, field, value) => {
    setExtractedChars(prev => prev.map((c, i) =>
      i === idx ? { ...c, [field]: value } : c
    ));
  };

  const handleConfirm = async () => {
    if (!seriesData?.series_id) return;
    setConfirming(true);
    try {
      const res = await api.post(`/api/story-series/${seriesData.series_id}/confirm-characters`, {
        characters: extractedChars,
      });
      if (res.data.success) {
        const count = res.data.created || 0;
        toast.success(count > 0 ? `${count} character${count > 1 ? 's' : ''} locked to series!` : 'Characters skipped.');
        navigate(`/app/story-series/${seriesData.series_id}`);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to confirm characters');
    } finally {
      setConfirming(false);
    }
  };

  const handleSkip = async () => {
    if (!seriesData?.series_id) return;
    try {
      await api.post(`/api/story-series/${seriesData.series_id}/dismiss-extraction`);
    } catch { /* non-critical */ }
    navigate(`/app/story-series/${seriesData.series_id}`);
  };

  // ─── Step 2: Character Confirmation ────────────────────────────────────
  if (step === 'confirm') {
    const confirmedCount = extractedChars.filter(c => c.confirmed).length;
    return (
      <div className="min-h-screen bg-slate-950" data-testid="character-confirmation-page">
        <header className="border-b border-slate-800/50 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
          <div className="max-w-2xl mx-auto px-4 py-4 flex items-center gap-4">
            <button onClick={() => { setStep('form'); }} className="text-slate-400 hover:text-white transition-colors">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-cyan-500/20 flex items-center justify-center">
                <Users className="w-5 h-5 text-cyan-400" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-white">Characters Detected</h1>
                <p className="text-xs text-slate-500">{seriesData?.title}</p>
              </div>
            </div>
          </div>
        </header>

        <main className="max-w-2xl mx-auto px-4 py-8 space-y-5">
          <div className="bg-gradient-to-r from-cyan-500/5 to-indigo-500/5 border border-cyan-500/20 rounded-xl p-5">
            <p className="text-sm text-slate-300">
              AI detected <span className="text-cyan-400 font-semibold">{extractedChars.length} character{extractedChars.length !== 1 ? 's' : ''}</span> from Episode 1. 
              Review and confirm to lock them into your series with persistent identity.
            </p>
          </div>

          <div className="space-y-3" data-testid="extracted-characters-list">
            {extractedChars.map((char, idx) => {
              const roleColor = ROLE_COLORS[char.role?.toLowerCase()] || ROLE_COLORS[char.role_importance] || 'text-slate-400 bg-slate-500/10 border-slate-500/20';
              const isEditing = editingIdx === idx;

              return (
                <div
                  key={char.extraction_id || idx}
                  className={`border rounded-xl overflow-hidden transition-all ${
                    char.confirmed
                      ? 'bg-slate-900/80 border-cyan-500/30'
                      : 'bg-slate-900/40 border-slate-800 opacity-60'
                  }`}
                  data-testid={`extracted-char-${idx}`}
                >
                  <div className="p-4">
                    <div className="flex items-start gap-3">
                      {/* Toggle */}
                      <button
                        onClick={() => toggleChar(idx)}
                        className={`mt-0.5 w-6 h-6 rounded-md border-2 flex items-center justify-center flex-shrink-0 transition-all ${
                          char.confirmed
                            ? 'bg-cyan-500 border-cyan-500 text-white'
                            : 'border-slate-600 hover:border-slate-500'
                        }`}
                        data-testid={`toggle-char-${idx}`}
                      >
                        {char.confirmed && <Check className="w-3.5 h-3.5" />}
                      </button>

                      {/* Character Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          {isEditing ? (
                            <input
                              value={char.name}
                              onChange={e => updateCharField(idx, 'name', e.target.value)}
                              className="bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-white font-semibold outline-none focus:border-cyan-500 w-40"
                              data-testid={`edit-name-${idx}`}
                              autoFocus
                            />
                          ) : (
                            <h3 className="text-sm font-semibold text-white">{char.name}</h3>
                          )}
                          <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium border ${roleColor}`}>
                            {char.role_importance || char.role}
                          </span>
                          <span className="text-[10px] text-slate-500 ml-auto">
                            {Math.round(char.confidence * 100)}% match
                          </span>
                        </div>

                        {/* Confidence bar */}
                        <div className="w-full h-1 bg-slate-800 rounded-full mb-2">
                          <div
                            className={`h-full rounded-full transition-all ${
                              char.confidence >= 0.8 ? 'bg-emerald-500' :
                              char.confidence >= 0.7 ? 'bg-cyan-500' : 'bg-amber-500'
                            }`}
                            style={{ width: `${Math.round(char.confidence * 100)}%` }}
                          />
                        </div>

                        {char.appearance && (
                          <p className="text-xs text-slate-400 line-clamp-2 mb-1">{char.appearance}</p>
                        )}

                        {char.personality_traits?.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-1">
                            {char.personality_traits.slice(0, 4).map((t, ti) => (
                              <span key={ti} className="text-[10px] bg-slate-800/80 text-slate-400 px-1.5 py-0.5 rounded">
                                {t}
                              </span>
                            ))}
                          </div>
                        )}

                        <div className="flex items-center gap-3 mt-2 text-[11px] text-slate-500">
                          <span>{char.scene_appearances || 0} scene appearances</span>
                          {char.goals && <span>Goal: {char.goals.slice(0, 50)}</span>}
                        </div>
                      </div>

                      {/* Edit toggle */}
                      <button
                        onClick={() => setEditingIdx(isEditing ? null : idx)}
                        className="text-slate-500 hover:text-white transition-colors p-1"
                        data-testid={`edit-char-${idx}`}
                      >
                        {isEditing ? <Check className="w-4 h-4 text-cyan-400" /> : <Edit3 className="w-4 h-4" />}
                      </button>
                    </div>

                    {/* Edit panel */}
                    {isEditing && (
                      <div className="mt-3 pt-3 border-t border-slate-800/50 grid grid-cols-2 gap-2">
                        <div>
                          <label className="text-[10px] text-slate-500 mb-1 block">Role</label>
                          <select
                            value={char.role}
                            onChange={e => updateCharField(idx, 'role', e.target.value)}
                            className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-white outline-none"
                            data-testid={`edit-role-${idx}`}
                          >
                            <option value="protagonist">Protagonist</option>
                            <option value="antagonist">Antagonist</option>
                            <option value="sidekick">Sidekick</option>
                            <option value="mentor">Mentor</option>
                            <option value="supporting">Supporting</option>
                          </select>
                        </div>
                        <div>
                          <label className="text-[10px] text-slate-500 mb-1 block">Voice</label>
                          <select
                            value={char.voice_style || 'warm'}
                            onChange={e => updateCharField(idx, 'voice_style', e.target.value)}
                            className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-white outline-none"
                          >
                            <option value="warm">Warm</option>
                            <option value="energetic">Energetic</option>
                            <option value="calm">Calm</option>
                            <option value="dramatic">Dramatic</option>
                          </select>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <Button
              onClick={handleConfirm}
              disabled={confirming || confirmedCount === 0}
              className="flex-1 h-12 bg-cyan-600 hover:bg-cyan-700 text-white font-medium text-sm"
              data-testid="confirm-characters-btn"
            >
              {confirming ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Locking characters...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Shield className="w-4 h-4" />
                  Lock {confirmedCount} Character{confirmedCount !== 1 ? 's' : ''} to Series
                </span>
              )}
            </Button>
            <Button
              onClick={handleSkip}
              variant="outline"
              className="border-slate-700 text-slate-400 hover:text-white px-6 h-12"
              data-testid="skip-characters-btn"
            >
              Skip
              <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </div>

          <p className="text-xs text-slate-600 text-center">
            Confirmed characters get persistent visual identity across all episodes.
          </p>
        </main>
      </div>
    );
  }

  // ─── Step 1: Create Form ───────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-slate-950" data-testid="create-series-page">
      <header className="border-b border-slate-800/50 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-2xl mx-auto px-4 py-4 flex items-center gap-4">
          <Link to="/app/story-series" className="text-slate-400 hover:text-white transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/20 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white">Create Series</h1>
              <p className="text-xs text-slate-500">Build a new story universe</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-8 space-y-6">
        {/* Title */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
          <label className="flex items-center gap-2 text-sm font-medium text-white mb-3">
            <BookOpen className="w-4 h-4 text-indigo-400" /> Series Title
          </label>
          <input
            type="text"
            value={form.title}
            onChange={e => update('title', e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
            placeholder="The Fox and the Magic Forest"
            maxLength={100}
            data-testid="series-title-input"
          />
        </div>

        {/* Story Prompt */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
          <label className="flex items-center gap-2 text-sm font-medium text-white mb-3">
            <Sparkles className="w-4 h-4 text-amber-400" /> Story Prompt
          </label>
          <textarea
            value={form.initial_prompt}
            onChange={e => update('initial_prompt', e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white text-sm min-h-[120px] focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none resize-none"
            placeholder="Describe your story world, main characters, and initial plot..."
            maxLength={2000}
            data-testid="series-prompt-input"
          />
          <p className="text-xs text-slate-600 mt-2 text-right">{form.initial_prompt.length}/2000</p>
          {!form.initial_prompt && (
            <div className="mt-2 bg-slate-800/40 border border-slate-700/30 rounded-lg px-3 py-2">
              <p className="text-xs text-slate-400">
                <span className="text-amber-400 font-medium">Try:</span> "A brave fox named Finn and a curious rabbit named Luna explore an enchanted forest, helping lost animals find their way home while uncovering an ancient mystery."
              </p>
            </div>
          )}
        </div>

        {/* Settings Grid */}
        <div className="grid sm:grid-cols-3 gap-4">
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
            <label className="flex items-center gap-2 text-xs font-medium text-slate-400 mb-2">
              <Globe className="w-3 h-3" /> Genre
            </label>
            <Select value={form.genre} onValueChange={v => update('genre', v)}>
              <SelectTrigger className="bg-slate-800 border-slate-700 text-white" data-testid="genre-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {GENRES.map(g => (
                  <SelectItem key={g} value={g}>{g.charAt(0).toUpperCase() + g.slice(1)}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
            <label className="flex items-center gap-2 text-xs font-medium text-slate-400 mb-2">
              <Users className="w-3 h-3" /> Audience
            </label>
            <Select value={form.audience} onValueChange={v => update('audience', v)}>
              <SelectTrigger className="bg-slate-800 border-slate-700 text-white" data-testid="audience-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {AUDIENCES.map(a => (
                  <SelectItem key={a.value} value={a.value}>{a.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
            <label className="flex items-center gap-2 text-xs font-medium text-slate-400 mb-2">
              <Palette className="w-3 h-3" /> Art Style
            </label>
            <Select value={form.style} onValueChange={v => update('style', v)}>
              <SelectTrigger className="bg-slate-800 border-slate-700 text-white" data-testid="style-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STYLES.map(s => (
                  <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Create Button */}
        <Button
          onClick={handleCreate}
          disabled={creating || !form.title.trim() || !form.initial_prompt.trim()}
          className="w-full h-12 bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm"
          data-testid="submit-create-series-btn"
        >
          {creating ? (
            <span className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              Creating universe...
            </span>
          ) : (
            <span className="flex items-center gap-2">
              <Sparkles className="w-4 h-4" />
              Create Series
            </span>
          )}
        </Button>

        <p className="text-xs text-slate-600 text-center">
          AI will generate characters, world, and Episode 1 plan from your prompt.
        </p>
        <p className="text-[10px] text-slate-700 text-center">
          All generated content is original. Do not reference copyrighted characters, brands, or real people without consent.
        </p>
      </main>
    </div>
  );
}
