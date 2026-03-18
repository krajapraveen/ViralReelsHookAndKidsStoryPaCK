import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import {
  ArrowLeft, Loader2, User, Palette, BookOpen, Shield,
  ImageIcon, Clock, Target, AlertTriangle
} from 'lucide-react';

export default function CharacterDetail() {
  const { characterId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generatingPortrait, setGeneratingPortrait] = useState(false);

  const fetchData = () => {
    api.get(`/api/characters/${characterId}`)
      .then(res => setData(res.data))
      .catch(() => toast.error('Character not found'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, [characterId]);

  const handleGeneratePortrait = async () => {
    setGeneratingPortrait(true);
    try {
      const res = await api.post(`/api/characters/${characterId}/generate-portrait`);
      if (res.data.success) {
        toast.success('Portrait generated!');
        fetchData();
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Portrait generation failed');
    } finally {
      setGeneratingPortrait(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400">
        Character not found
      </div>
    );
  }

  const { profile, visual_bible: vb, safety_profile: sp, memory_log: memories } = data;

  return (
    <div className="min-h-screen bg-slate-950" data-testid="character-detail-page">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <Button variant="ghost" size="sm" onClick={() => navigate('/app/characters')} data-testid="back-btn">
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div className="flex-1 min-w-0">
            <h1 className="text-xl font-bold text-white truncate" data-testid="char-name">{profile.name}</h1>
            <p className="text-sm text-slate-400">
              {profile.species_or_type} {profile.role} · {profile.age_band} · {profile.status}
            </p>
          </div>
          <Button
            size="sm" variant="outline"
            onClick={handleGeneratePortrait}
            disabled={generatingPortrait}
            className="border-slate-700 text-slate-400 hover:text-white gap-1.5 text-xs"
            data-testid="generate-portrait-btn"
          >
            {generatingPortrait ? <Loader2 className="w-3 h-3 animate-spin" /> : <ImageIcon className="w-3 h-3" />}
            {generatingPortrait ? 'Generating...' : profile.portrait_url ? 'Regenerate Portrait' : 'Generate Portrait'}
          </Button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Left: Portrait + Identity */}
          <div className="space-y-4">
            {/* Portrait */}
            {profile.portrait_url ? (
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden" data-testid="portrait-zone">
                <img src={profile.portrait_url} alt={profile.name} className="w-full aspect-[2/3] object-cover" />
              </div>
            ) : (
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-8 flex flex-col items-center justify-center aspect-[2/3]">
                <User className="w-12 h-12 text-slate-600 mb-3" />
                <p className="text-xs text-slate-500 text-center">No portrait yet. Generate one to anchor this character's visual identity.</p>
              </div>
            )}

            {/* Identity */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-2">
              <h3 className="text-sm font-medium text-slate-300 flex items-center gap-1.5"><User className="w-3.5 h-3.5" /> Identity</h3>
              <div className="space-y-1.5 text-xs">
                {profile.personality_summary && <p className="text-slate-400"><span className="text-slate-500">Personality:</span> {profile.personality_summary}</p>}
                {profile.backstory_summary && <p className="text-slate-400"><span className="text-slate-500">Backstory:</span> {profile.backstory_summary}</p>}
                {profile.core_goals && <p className="text-slate-400"><span className="text-slate-500">Goals:</span> {profile.core_goals}</p>}
                {profile.core_fears && <p className="text-slate-400"><span className="text-slate-500">Fears:</span> {profile.core_fears}</p>}
                {profile.speech_style && <p className="text-slate-400"><span className="text-slate-500">Speech:</span> {profile.speech_style}</p>}
              </div>
            </div>
          </div>

          {/* Center: Visual Bible */}
          <div className="space-y-4">
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-3">
              <h3 className="text-sm font-medium text-slate-300 flex items-center gap-1.5"><Palette className="w-3.5 h-3.5" /> Visual Bible</h3>
              {vb && (
                <div className="space-y-2 text-xs">
                  <p className="text-slate-400">{vb.canonical_description}</p>
                  {vb.do_not_change_rules?.length > 0 && (
                    <div>
                      <span className="text-amber-400/80 font-medium">Locked Rules:</span>
                      <ul className="mt-1 space-y-0.5">
                        {vb.do_not_change_rules.map((rule, i) => (
                          <li key={i} className="text-slate-400 flex items-center gap-1">
                            <Shield className="w-2.5 h-2.5 text-amber-500/60 flex-shrink-0" /> {rule}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {vb.style_lock && (
                    <p className="text-slate-500">Style: <span className="text-indigo-400">{vb.style_lock.replace('_', ' ')}</span></p>
                  )}
                  {vb.negative_constraints?.length > 0 && (
                    <div>
                      <span className="text-red-400/60 text-[10px]">Negative constraints:</span>
                      <p className="text-slate-500 text-[10px]">{vb.negative_constraints.join(', ')}</p>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Safety */}
            {sp && (
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-2">
                <h3 className="text-sm font-medium text-slate-300 flex items-center gap-1.5"><Shield className="w-3.5 h-3.5" /> Safety Profile</h3>
                <div className="space-y-1 text-xs text-slate-400">
                  <p>Origin: {sp.compliance_notes}</p>
                  <p>Consent: {sp.consent_status}</p>
                  {sp.is_minor_like && (
                    <p className="text-amber-400 flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" /> Minor-like character (extra restrictions)
                    </p>
                  )}
                  <p>Disallowed: {sp.disallowed_transformations?.join(', ')}</p>
                </div>
              </div>
            )}
          </div>

          {/* Right: Memory Timeline */}
          <div className="space-y-4">
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
              <h3 className="text-sm font-medium text-slate-300 flex items-center gap-1.5 mb-3">
                <BookOpen className="w-3.5 h-3.5" /> Memory Timeline
                <span className="ml-auto text-xs text-slate-500">{memories.length} entries</span>
              </h3>
              {memories.length === 0 ? (
                <p className="text-xs text-slate-500 text-center py-4">
                  No memories yet. Attach this character to a series and generate episodes to build memory.
                </p>
              ) : (
                <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                  {memories.map((m, i) => (
                    <div key={m.memory_log_id || i} className="bg-slate-800/40 rounded-lg p-2.5 text-xs space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-slate-500 flex items-center gap-1">
                          <Clock className="w-2.5 h-2.5" />
                          {new Date(m.timestamp).toLocaleDateString()}
                        </span>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                          m.emotion_state === 'happy' ? 'bg-green-500/15 text-green-400' :
                          m.emotion_state === 'scared' || m.emotion_state === 'afraid' ? 'bg-red-500/15 text-red-400' :
                          m.emotion_state === 'sad' ? 'bg-blue-500/15 text-blue-400' :
                          'bg-slate-700 text-slate-400'
                        }`}>
                          {m.emotion_state}
                        </span>
                      </div>
                      <p className="text-slate-300">{m.event_summary}</p>
                      {m.open_loops?.length > 0 && (
                        <p className="text-amber-400/70 flex items-center gap-1">
                          <Target className="w-2.5 h-2.5" /> {m.open_loops.join(', ')}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
