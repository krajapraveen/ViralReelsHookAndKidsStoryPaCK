import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
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
  const [searchParams] = useSearchParams();
  const [step, setStep] = useState('form'); // 'form' | 'confirm'
  const [creating, setCreating] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [seriesData, setSeriesData] = useState(null);
  const [extractedChars, setExtractedChars] = useState([]);
  const [editingIdx, setEditingIdx] = useState(null);

  // P0 UX (2026-05-17) — preselected character from Character Detail handoff.
  // When the URL carries ?character_id=<id>, validate ownership against
  // GET /api/characters/{id} and stash the character so it auto-attaches
  // after series creation. Invalid ids surface a structured toast with
  // request_id so users have a debuggable reference.
  const preselectedCharacterId = searchParams.get('character_id') || null;
  const [preselectedCharacter, setPreselectedCharacter] = useState(null);
  const [preselectValidating, setPreselectValidating] = useState(false);
  const preselectAttachedRef = useRef(false);

  useEffect(() => {
    if (!preselectedCharacterId) return;
    setPreselectValidating(true);
    api.get(`/api/characters/${preselectedCharacterId}`)
      .then(res => {
        const c = res.data || {};
        if (!c.character_id && !c.id && !c.name) {
          throw new Error('empty');
        }
        setPreselectedCharacter({
          character_id: c.character_id || c.id || preselectedCharacterId,
          name: c.name || 'Selected character',
        });
      })
      .catch(err => {
        const status = err?.response?.status || 0;
        const detail = err?.response?.data?.detail;
        const requestId =
          err?.response?.headers?.['x-request-id'] ||
          (detail && typeof detail === 'object' ? detail.request_id : null) ||
          'unknown';
        const human =
          status === 404
            ? 'That character could not be found or you do not own it.'
            : 'Could not load the preselected character.';
        toast.error(`${human}  Ref: ${requestId}`, {
          duration: 6000,
          'data-testid': 'preselect-character-error-toast',
        });
        setPreselectedCharacter(null);
      })
      .finally(() => setPreselectValidating(false));
  }, [preselectedCharacterId]);

  const [form, setForm] = useState({
    title: '',
    initial_prompt: '',
    genre: 'adventure',
    audience: 'kids_5_8',
    style: 'cartoon_2d',
    tool: 'story_video',
  });

  const update = (key, val) => setForm(prev => ({ ...prev, [key]: val }));

  // Helper: attach the preselected character to a freshly created series.
  // Runs at most once per session via preselectAttachedRef to keep idempotent.
  const attachPreselectedCharacter = async (seriesId) => {
    if (!preselectedCharacter?.character_id) return;
    if (!seriesId) return;
    if (preselectAttachedRef.current) return;
    preselectAttachedRef.current = true;
    try {
      await api.post(
        `/api/characters/attach-to-series/${seriesId}`,
        { character_id: preselectedCharacter.character_id }
      );
      toast.success(`${preselectedCharacter.name} attached to this series.`);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const requestId =
        err?.response?.headers?.['x-request-id'] ||
        (detail && typeof detail === 'object' ? detail.request_id : null) ||
        'unknown';
      toast.error(
        `Could not attach ${preselectedCharacter.name} to the series. Ref: ${requestId}`,
        { duration: 6000 }
      );
    }
  };

  const handleCreate = async () => {
    if (!form.title.trim()) { toast.error('Title is required'); return; }
    if (!form.initial_prompt.trim()) { toast.error('Story prompt is required'); return; }
    if (creating) return;  // P0 2026-05-16 duplicate-click guard
    setCreating(true);
    // Instrumentation — pre-network click
    try {
      const { trackFunnel } = await import('../utils/funnelTracker');
      trackFunnel('create_series_clicked', { source_page: '/app/story-series', meta: { title: form.title, genre: form.genre, audience: form.audience } });
    } catch (_) { /* never block UX */ }
    try {
      // 60s frontend timeout — backend has its own 50s LLM cap; this is the safety net.
      const res = await api.post('/api/story-series/create', form, { timeout: 60000 });
      if (res.data.success) {
        if (res.data.duplicate) {
          toast.info('Series already exists from a recent submission.');
          await attachPreselectedCharacter(res.data.series_id);
          navigate(`/app/story-series/${res.data.series_id}`);
          return;
        }
        setSeriesData(res.data);
        // Auto-attach preselected character (from Character Detail handoff).
        // Done BEFORE entering the confirm step so the attach completes during
        // the same wall-clock moment as the create — keeps the trust flow tight.
        await attachPreselectedCharacter(res.data.series_id);
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
      // P0 2026-05-16 — actionable, code-aware error rendering.
      // Backend now returns: detail = { code, message, retryable, elapsed_s? }
      // OR detail = "string" (legacy 4xx paths)
      // OR detail = generic gateway shape from axios interceptor.
      const d = err?.response?.data;
      const status = err?.response?.status || 0;
      const isAxiosTimeout = err?.code === 'ECONNABORTED';

      let message;
      if (isAxiosTimeout) {
        message = 'Generation timed out. Tap Create Series to try again — your draft is preserved.';
      } else if (d?.detail && typeof d.detail === 'object' && d.detail.message) {
        // Structured backend error (new shape)
        message = d.detail.message;
        // P0 2026-05-16 — surface per-request correlation id in the toast
        // so users can paste it to support and ops can pull the trace.
        if (d.detail.request_id) {
          message = `${message}\nReference ID: ${d.detail.request_id}`;
        }
      } else if (typeof d?.detail === 'string') {
        message = d.detail;
      } else if (d?.gateway || status >= 502) {
        message = 'AI service is briefly unavailable. Tap Create Series again — this usually clears in 10 seconds.';
      } else {
        message = 'Could not create series. Tap Create Series to retry.';
      }

      toast.error(message);
      try {
        const { trackFunnel } = await import('../utils/funnelTracker');
        trackFunnel('create_series_failed', {
          source_page: '/app/story-series',
          meta: { status, code: d?.detail?.code, message_shown: message },
        });
      } catch (_) { /* */ }
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
        {/* P0 UX (2026-05-17) — Preselected character banner.
            Surfaces ONLY when CreateSeries was reached via the Character
            Detail "Create Series with this Character" CTA. After series
            creation we auto-attach this character via
            POST /api/characters/attach-to-series/{series_id}. */}
        {preselectedCharacterId && (
          <div
            className="bg-indigo-500/10 border border-indigo-500/30 rounded-xl p-4 flex items-start gap-3"
            data-testid="preselected-character-banner"
          >
            <Users className="w-5 h-5 text-indigo-300 flex-shrink-0 mt-0.5" />
            <div className="flex-1 text-sm">
              {preselectValidating ? (
                <span className="text-slate-300 flex items-center gap-2">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Validating character…
                </span>
              ) : preselectedCharacter ? (
                <>
                  <p className="text-slate-200 font-medium">
                    Linking <span data-testid="preselected-character-name">{preselectedCharacter.name}</span> to this series
                  </p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    They will be attached automatically after Episode 1 is created.
                  </p>
                </>
              ) : (
                <p className="text-amber-300/90 text-xs">
                  Preselected character could not be loaded. You can still create the series and attach a character later from My Characters.
                </p>
              )}
            </div>
            {preselectedCharacter && (
              <button
                onClick={() => {
                  setPreselectedCharacter(null);
                  navigate('/app/story-series/create', { replace: true });
                }}
                className="text-slate-400 hover:text-white"
                aria-label="Remove preselected character"
                data-testid="preselected-character-clear"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        )}

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
