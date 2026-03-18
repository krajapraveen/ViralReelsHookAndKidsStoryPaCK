import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import {
  ArrowLeft, Loader2, Sparkles, BookOpen, Users,
  Globe, Palette
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

export default function CreateSeries() {
  const navigate = useNavigate();
  const [creating, setCreating] = useState(false);
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
        toast.success(`Series "${res.data.title}" created!`);
        navigate(`/app/story-series/${res.data.series_id}`);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create series');
    } finally {
      setCreating(false);
    }
  };

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
      </main>
    </div>
  );
}
