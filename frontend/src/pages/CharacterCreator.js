import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { ArrowLeft, ArrowRight, Loader2, Shield, Palette, User, Sparkles } from 'lucide-react';

const STYLES = [
  { id: 'cartoon_2d', label: 'Cartoon 2D', desc: 'Clean lines, bold colors' },
  { id: 'anime', label: 'Anime', desc: 'Dramatic, expressive' },
  { id: 'watercolor', label: 'Watercolor', desc: 'Soft edges, pastel' },
  { id: 'comic', label: 'Comic Book', desc: 'Dynamic, vivid' },
  { id: 'cinematic', label: 'Cinematic', desc: 'Realistic, dramatic' },
];

const ROLES = ['hero', 'villain', 'sidekick', 'narrator', 'mentor', 'trickster'];
const AGE_BANDS = ['child', 'teen', 'adult', 'elder', 'ageless fantasy'];
const SPECIES = ['human', 'fox', 'cat', 'dog', 'rabbit', 'wolf', 'bear', 'owl', 'dragon', 'fairy', 'robot', 'other'];

const STEPS = ['Identity', 'Personality', 'Appearance', 'Review'];

export default function CharacterCreator() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    name: '', species_or_type: 'fox', role: 'hero', age_band: 'ageless fantasy',
    gender_presentation: '', personality_summary: '', backstory_summary: '',
    core_goals: '', core_fears: '', speech_style: '',
    face_description: '', hair_description: '', body_description: '',
    clothing_description: '', color_palette: '', accessories: '',
    style_lock: 'cartoon_2d',
  });

  const set = (k, v) => setForm(p => ({ ...p, [k]: v }));

  const canNext = () => {
    if (step === 0) return form.name.trim() && form.species_or_type;
    if (step === 1) return form.personality_summary.trim();
    return true;
  };

  const handleCreate = async () => {
    setCreating(true);
    try {
      const res = await api.post('/api/characters/create', form);
      if (res.data.success) {
        toast.success(`${form.name} created!`);
        navigate(`/app/characters/${res.data.character_id}`);
      }
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (detail?.error === 'safety_block') {
        toast.error(detail.reason);
      } else {
        toast.error(typeof detail === 'string' ? detail : 'Character creation failed');
      }
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950" data-testid="character-creator-page">
      <div className="max-w-2xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <Button variant="ghost" size="sm" onClick={() => navigate('/app/characters')} data-testid="back-to-characters">
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div>
            <h1 className="text-xl font-bold text-white">Create Character</h1>
            <p className="text-sm text-slate-400">Persistent AI identity across your stories</p>
          </div>
        </div>

        {/* Step indicator */}
        <div className="flex items-center gap-2 mb-8">
          {STEPS.map((s, i) => (
            <div key={s} className="flex items-center gap-2">
              <button
                onClick={() => i < step && setStep(i)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                  i === step ? 'bg-indigo-500/20 text-indigo-300 ring-1 ring-indigo-500/30' :
                  i < step ? 'bg-slate-800 text-slate-300 hover:bg-slate-700 cursor-pointer' :
                  'bg-slate-900 text-slate-600'
                }`}
                data-testid={`step-${s.toLowerCase()}`}
              >
                {i === 0 && <User className="w-3 h-3" />}
                {i === 1 && <Sparkles className="w-3 h-3" />}
                {i === 2 && <Palette className="w-3 h-3" />}
                {i === 3 && <Shield className="w-3 h-3" />}
                {s}
              </button>
              {i < STEPS.length - 1 && <div className="w-6 h-px bg-slate-800" />}
            </div>
          ))}
        </div>

        {/* Step Content */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-5">

          {/* Step 0: Identity */}
          {step === 0 && (
            <>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Name</label>
                <input
                  type="text" value={form.name} onChange={e => set('name', e.target.value)}
                  placeholder="e.g., Finn, Luna, Zara..."
                  className="w-full bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2.5 text-white text-sm focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                  data-testid="char-name-input"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Species / Type</label>
                  <div className="flex flex-wrap gap-1.5">
                    {SPECIES.map(s => (
                      <button key={s} onClick={() => set('species_or_type', s)}
                        className={`px-2.5 py-1 rounded-md text-xs transition-all ${form.species_or_type === s ? 'bg-indigo-500/25 text-indigo-300 ring-1 ring-indigo-500/40' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'}`}
                        data-testid={`species-${s}`}
                      >{s}</button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Role</label>
                  <div className="flex flex-wrap gap-1.5">
                    {ROLES.map(r => (
                      <button key={r} onClick={() => set('role', r)}
                        className={`px-2.5 py-1 rounded-md text-xs capitalize transition-all ${form.role === r ? 'bg-indigo-500/25 text-indigo-300 ring-1 ring-indigo-500/40' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'}`}
                        data-testid={`role-${r}`}
                      >{r}</button>
                    ))}
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Age Band</label>
                  <div className="flex flex-wrap gap-1.5">
                    {AGE_BANDS.map(a => (
                      <button key={a} onClick={() => set('age_band', a)}
                        className={`px-2.5 py-1 rounded-md text-xs capitalize transition-all ${form.age_band === a ? 'bg-indigo-500/25 text-indigo-300 ring-1 ring-indigo-500/40' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'}`}
                      >{a}</button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Gender (optional)</label>
                  <input
                    type="text" value={form.gender_presentation} onChange={e => set('gender_presentation', e.target.value)}
                    placeholder="e.g., male, female, non-binary..."
                    className="w-full bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:ring-1 focus:ring-indigo-500 outline-none"
                  />
                </div>
              </div>
            </>
          )}

          {/* Step 1: Personality */}
          {step === 1 && (
            <>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Personality Summary</label>
                <textarea
                  value={form.personality_summary} onChange={e => set('personality_summary', e.target.value)}
                  placeholder="e.g., brave, kind, curious, protective, playful with a dry sense of humor..."
                  rows={3}
                  className="w-full bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2.5 text-white text-sm focus:ring-1 focus:ring-indigo-500 outline-none resize-none"
                  data-testid="char-personality-input"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Backstory</label>
                <textarea
                  value={form.backstory_summary} onChange={e => set('backstory_summary', e.target.value)}
                  placeholder="A young fox guide who helps lost forest animals find their way home..."
                  rows={2}
                  className="w-full bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2.5 text-white text-sm focus:ring-1 focus:ring-indigo-500 outline-none resize-none"
                  data-testid="char-backstory-input"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Core Goals</label>
                  <input type="text" value={form.core_goals} onChange={e => set('core_goals', e.target.value)}
                    placeholder="Help lost animals find home"
                    className="w-full bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:ring-1 focus:ring-indigo-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Core Fears</label>
                  <input type="text" value={form.core_fears} onChange={e => set('core_fears', e.target.value)}
                    placeholder="Failing his friends"
                    className="w-full bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:ring-1 focus:ring-indigo-500 outline-none"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Speech Style</label>
                <input type="text" value={form.speech_style} onChange={e => set('speech_style', e.target.value)}
                  placeholder="Warm and encouraging, uses nature metaphors"
                  className="w-full bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:ring-1 focus:ring-indigo-500 outline-none"
                />
              </div>
            </>
          )}

          {/* Step 2: Appearance */}
          {step === 2 && (
            <>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Style Lock</label>
                <div className="flex flex-wrap gap-2">
                  {STYLES.map(s => (
                    <button key={s.id} onClick={() => set('style_lock', s.id)}
                      className={`px-3 py-2 rounded-lg text-xs transition-all ${form.style_lock === s.id ? 'bg-indigo-500/25 text-indigo-300 ring-1 ring-indigo-500/40' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'}`}
                      data-testid={`style-${s.id}`}
                    >
                      <div className="font-medium">{s.label}</div>
                      <div className="text-[10px] text-slate-500 mt-0.5">{s.desc}</div>
                    </button>
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Face</label>
                  <input type="text" value={form.face_description} onChange={e => set('face_description', e.target.value)}
                    placeholder="Rounded cartoon face, large green eyes, small nose"
                    className="w-full bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:ring-1 focus:ring-indigo-500 outline-none"
                    data-testid="char-face-input"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Hair / Fur</label>
                  <input type="text" value={form.hair_description} onChange={e => set('hair_description', e.target.value)}
                    placeholder="Orange fur with white chest patch"
                    className="w-full bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:ring-1 focus:ring-indigo-500 outline-none"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Body</label>
                  <input type="text" value={form.body_description} onChange={e => set('body_description', e.target.value)}
                    placeholder="Small and nimble"
                    className="w-full bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:ring-1 focus:ring-indigo-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Clothing</label>
                  <input type="text" value={form.clothing_description} onChange={e => set('clothing_description', e.target.value)}
                    placeholder="Blue scarf, green backpack"
                    className="w-full bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:ring-1 focus:ring-indigo-500 outline-none"
                    data-testid="char-clothing-input"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Color Palette</label>
                  <input type="text" value={form.color_palette} onChange={e => set('color_palette', e.target.value)}
                    placeholder="Orange, green eyes, blue scarf, white chest"
                    className="w-full bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:ring-1 focus:ring-indigo-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Accessories</label>
                  <input type="text" value={form.accessories} onChange={e => set('accessories', e.target.value)}
                    placeholder="Blue scarf, compass, backpack"
                    className="w-full bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:ring-1 focus:ring-indigo-500 outline-none"
                  />
                </div>
              </div>
              <p className="text-xs text-slate-500">
                Leave blank fields for AI to generate. The more detail you provide, the more consistent your character will be.
              </p>
            </>
          )}

          {/* Step 3: Review */}
          {step === 3 && (
            <div className="space-y-4">
              <div className="bg-slate-800/40 rounded-lg p-4 space-y-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-indigo-500/20 flex items-center justify-center">
                    <User className="w-5 h-5 text-indigo-400" />
                  </div>
                  <div>
                    <div className="text-white font-medium" data-testid="review-name">{form.name || 'Unnamed'}</div>
                    <div className="text-xs text-slate-400">{form.species_or_type} {form.role} · {form.age_band} · {form.style_lock.replace('_', ' ')}</div>
                  </div>
                </div>
                {form.personality_summary && (
                  <div>
                    <span className="text-xs font-medium text-slate-500">Personality:</span>
                    <p className="text-sm text-slate-300">{form.personality_summary}</p>
                  </div>
                )}
                {form.backstory_summary && (
                  <div>
                    <span className="text-xs font-medium text-slate-500">Backstory:</span>
                    <p className="text-sm text-slate-300">{form.backstory_summary}</p>
                  </div>
                )}
                {form.face_description && (
                  <div>
                    <span className="text-xs font-medium text-slate-500">Appearance:</span>
                    <p className="text-sm text-slate-300">
                      {[form.face_description, form.hair_description, form.body_description, form.clothing_description]
                        .filter(Boolean).join('. ')}
                    </p>
                  </div>
                )}
              </div>
              <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 flex items-start gap-2">
                <Shield className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
                <div className="text-xs text-amber-300/80">
                  AI will generate a visual bible with strict consistency rules. Your character's appearance will be locked and maintained across all story episodes.
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-between mt-6">
          <Button
            variant="ghost" size="sm"
            onClick={() => step > 0 ? setStep(step - 1) : navigate('/app/characters')}
            className="text-slate-400"
            data-testid="step-back-btn"
          >
            <ArrowLeft className="w-4 h-4 mr-1" /> {step > 0 ? 'Back' : 'Cancel'}
          </Button>

          {step < 3 ? (
            <Button
              size="sm" disabled={!canNext()}
              onClick={() => setStep(step + 1)}
              className="bg-indigo-600 hover:bg-indigo-500"
              data-testid="step-next-btn"
            >
              Next <ArrowRight className="w-4 h-4 ml-1" />
            </Button>
          ) : (
            <Button
              size="sm" disabled={creating || !form.name.trim() || !form.personality_summary.trim()}
              onClick={handleCreate}
              className="bg-indigo-600 hover:bg-indigo-500"
              data-testid="create-character-btn"
            >
              {creating ? <><Loader2 className="w-4 h-4 mr-1 animate-spin" /> Creating...</> : 'Create Character'}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
