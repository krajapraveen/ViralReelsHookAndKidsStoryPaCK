import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import {
  ArrowLeft, Loader2, User, Palette, BookOpen, Shield,
  ImageIcon, Clock, Target, AlertTriangle, CheckCircle,
  Volume2, Mic, Edit3, Save, Users, Heart, TrendingUp, Share2, Copy
} from 'lucide-react';

const VOICE_IDS = [
  { id: 'alloy', label: 'Alloy' }, { id: 'echo', label: 'Echo' },
  { id: 'fable', label: 'Fable' }, { id: 'onyx', label: 'Onyx' },
  { id: 'nova', label: 'Nova' }, { id: 'shimmer', label: 'Shimmer' },
];
const TONES = ['warm', 'serious', 'playful', 'mysterious', 'energetic', 'calm'];
const PACES = ['slow', 'moderate', 'fast'];

export default function CharacterDetail() {
  const { characterId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generatingPortrait, setGeneratingPortrait] = useState(false);
  const [voiceProfile, setVoiceProfile] = useState(null);
  const [voiceForm, setVoiceForm] = useState({ voice_id: 'alloy', tone: 'warm', pace: 'moderate', accent: '', energy_level: 'medium' });
  const [showVoiceEditor, setShowVoiceEditor] = useState(false);
  const [savingVoice, setSavingVoice] = useState(false);
  const [continuityData, setContinuityData] = useState(null);
  const [validating, setValidating] = useState(false);
  const [editingVB, setEditingVB] = useState(false);
  const [vbForm, setVbForm] = useState({});
  const [savingVB, setSavingVB] = useState(false);
  const [relationships, setRelationships] = useState([]);
  const [emotionalArc, setEmotionalArc] = useState(null);

  const fetchData = () => {
    api.get(`/api/characters/${characterId}`)
      .then(res => setData(res.data))
      .catch(() => toast.error('Character not found'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, [characterId]);

  // Load voice profile and continuity data
  useEffect(() => {
    if (!characterId) return;
    api.get(`/api/characters/${characterId}/voice-profile`)
      .then(r => {
        if (r.data.voice_profile) {
          setVoiceProfile(r.data.voice_profile);
          setVoiceForm(prev => ({ ...prev, ...r.data.voice_profile }));
        }
      }).catch(() => {});
    api.get(`/api/characters/${characterId}/continuity-history`)
      .then(r => setContinuityData(r.data))
      .catch(() => {});
    api.get(`/api/characters/${characterId}/relationships`)
      .then(r => setRelationships(r.data.relationships || []))
      .catch(() => {});
    api.get(`/api/characters/${characterId}/emotional-arc`)
      .then(r => setEmotionalArc(r.data))
      .catch(() => {});
  }, [characterId]);

  const handleValidateContinuity = async () => {
    setValidating(true);
    try {
      const res = await api.post(`/api/characters/${characterId}/validate-continuity`);
      if (res.data.success) {
        toast.success(`Continuity score: ${res.data.continuity_score}/100`);
        api.get(`/api/characters/${characterId}/continuity-history`).then(r => setContinuityData(r.data)).catch(() => {});
      }
    } catch (err) { toast.error(err.response?.data?.detail || 'Validation failed'); }
    finally { setValidating(false); }
  };

  const handleSaveVoice = async () => {
    setSavingVoice(true);
    try {
      const res = await api.post(`/api/characters/${characterId}/voice-profile`, voiceForm);
      if (res.data.success) {
        setVoiceProfile(res.data.voice_profile);
        setShowVoiceEditor(false);
        toast.success('Voice profile saved!');
      }
    } catch (err) { toast.error('Failed to save voice profile'); }
    finally { setSavingVoice(false); }
  };

  const handleSaveVB = async () => {
    setSavingVB(true);
    try {
      const res = await api.patch(`/api/characters/${characterId}/visual-bible`, vbForm);
      if (res.data.success) {
        toast.success(`Visual bible updated (v${res.data.new_version}). Continuity: ${res.data.continuity_check.score}/100`);
        if (res.data.impact_warning) toast.warning(res.data.impact_warning);
        setEditingVB(false);
        fetchData();
        api.get(`/api/characters/${characterId}/continuity-history`).then(r => setContinuityData(r.data)).catch(() => {});
      }
    } catch (err) {
      const detail = err.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : detail?.reason || 'Failed to save');
    }
    finally { setSavingVB(false); }
  };

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
            onClick={() => {
              const shareUrl = `${window.location.origin}/character/${characterId}`;
              navigator.clipboard.writeText(shareUrl).then(() => toast.success('Share link copied!'));
            }}
            className="border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/10 gap-1.5 text-xs"
            data-testid="share-character-btn"
          >
            <Share2 className="w-3 h-3" /> Share
          </Button>
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
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-slate-300 flex items-center gap-1.5">
                  <Palette className="w-3.5 h-3.5" /> Visual Bible
                  {vb?.version && <span className="text-[10px] text-slate-600 ml-1">v{vb.version}</span>}
                </h3>
                <Button size="sm" variant="ghost" onClick={() => {
                  if (!editingVB && vb) setVbForm({ clothing_description: vb.clothing_description, accessories: vb.accessories, color_palette: vb.color_palette, face_description: vb.face_description, hair_description: vb.hair_description });
                  setEditingVB(!editingVB);
                }} className="text-xs text-slate-500 h-6 px-2" data-testid="edit-vb-btn">
                  {editingVB ? 'Cancel' : <><Edit3 className="w-3 h-3 mr-1" />Edit</>}
                </Button>
              </div>
              {vb && !editingVB && (
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
              {editingVB && (
                <div className="space-y-2">
                  <div className="bg-amber-500/10 border border-amber-500/20 rounded p-2 text-[10px] text-amber-300/80 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3 flex-shrink-0" /> Changes may affect consistency across previous episodes. Version will be bumped.
                  </div>
                  {['face_description', 'hair_description', 'clothing_description', 'accessories', 'color_palette'].map(field => (
                    <div key={field}>
                      <label className="text-[10px] text-slate-500 capitalize">{field.replace('_', ' ')}</label>
                      <input type="text" value={vbForm[field] || ''} onChange={e => setVbForm(p => ({...p, [field]: e.target.value}))}
                        className="w-full bg-slate-800/60 border border-slate-700 rounded px-2 py-1 text-[11px] text-white outline-none focus:ring-1 focus:ring-indigo-500"
                      />
                    </div>
                  ))}
                  <Button size="sm" onClick={handleSaveVB} disabled={savingVB} className="w-full bg-indigo-600 hover:bg-indigo-500 text-xs h-7" data-testid="save-vb-btn">
                    {savingVB ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <Save className="w-3 h-3 mr-1" />}
                    Save & Validate
                  </Button>
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

            {/* Voice Profile */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-3" data-testid="voice-profile-zone">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-slate-300 flex items-center gap-1.5"><Volume2 className="w-3.5 h-3.5" /> Voice Profile</h3>
                <Button size="sm" variant="ghost" onClick={() => setShowVoiceEditor(!showVoiceEditor)} className="text-xs text-slate-500 h-6 px-2" data-testid="toggle-voice-editor">
                  {showVoiceEditor ? 'Cancel' : voiceProfile ? 'Edit' : 'Set Up'}
                </Button>
              </div>
              {voiceProfile && !showVoiceEditor && (
                <div className="text-xs space-y-1 text-slate-400">
                  <p>Voice: <span className="text-indigo-400">{voiceProfile.voice_id}</span></p>
                  <p>Tone: {voiceProfile.tone} | Pace: {voiceProfile.pace} | Energy: {voiceProfile.energy_level}</p>
                  {voiceProfile.accent && <p>Accent: {voiceProfile.accent}</p>}
                  {voiceProfile.do_not_change_rules?.length > 0 && (
                    <p className="text-amber-400/70">Rules: {voiceProfile.do_not_change_rules.join(', ')}</p>
                  )}
                </div>
              )}
              {!voiceProfile && !showVoiceEditor && (
                <p className="text-xs text-slate-500">No voice profile yet. Set one up for consistent narration.</p>
              )}
              {showVoiceEditor && (
                <div className="space-y-2">
                  <div>
                    <label className="text-[10px] text-slate-500">Voice</label>
                    <div className="flex flex-wrap gap-1">
                      {VOICE_IDS.map(v => (
                        <button key={v.id} onClick={() => setVoiceForm(p => ({...p, voice_id: v.id}))}
                          className={`px-2 py-0.5 rounded text-[10px] ${voiceForm.voice_id === v.id ? 'bg-indigo-500/20 text-indigo-300 ring-1 ring-indigo-500/30' : 'bg-slate-800 text-slate-400'}`}
                        >{v.label}</button>
                      ))}
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <label className="text-[10px] text-slate-500">Tone</label>
                      <select value={voiceForm.tone} onChange={e => setVoiceForm(p => ({...p, tone: e.target.value}))}
                        className="w-full bg-slate-800 border border-slate-700 rounded px-1.5 py-1 text-[10px] text-white outline-none"
                      >{TONES.map(t => <option key={t} value={t}>{t}</option>)}</select>
                    </div>
                    <div>
                      <label className="text-[10px] text-slate-500">Pace</label>
                      <select value={voiceForm.pace} onChange={e => setVoiceForm(p => ({...p, pace: e.target.value}))}
                        className="w-full bg-slate-800 border border-slate-700 rounded px-1.5 py-1 text-[10px] text-white outline-none"
                      >{PACES.map(p => <option key={p} value={p}>{p}</option>)}</select>
                    </div>
                    <div>
                      <label className="text-[10px] text-slate-500">Energy</label>
                      <select value={voiceForm.energy_level} onChange={e => setVoiceForm(p => ({...p, energy_level: e.target.value}))}
                        className="w-full bg-slate-800 border border-slate-700 rounded px-1.5 py-1 text-[10px] text-white outline-none"
                      >{['low','medium','high'].map(e => <option key={e} value={e}>{e}</option>)}</select>
                    </div>
                  </div>
                  <Button size="sm" onClick={handleSaveVoice} disabled={savingVoice} className="w-full bg-indigo-600 hover:bg-indigo-500 text-xs h-7" data-testid="save-voice-btn">
                    {savingVoice ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <Mic className="w-3 h-3 mr-1" />}
                    Save Voice Profile
                  </Button>
                </div>
              )}
            </div>

            {/* Continuity Validator */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-3" data-testid="continuity-zone">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-slate-300 flex items-center gap-1.5"><CheckCircle className="w-3.5 h-3.5" /> Continuity</h3>
                <Button size="sm" variant="ghost" onClick={handleValidateContinuity} disabled={validating} className="text-xs text-slate-500 h-6 px-2" data-testid="validate-continuity-btn">
                  {validating ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Validate'}
                </Button>
              </div>
              {continuityData && continuityData.total > 0 ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className={`text-lg font-bold ${continuityData.average_score >= 70 ? 'text-green-400' : continuityData.average_score >= 50 ? 'text-amber-400' : 'text-red-400'}`}>
                      {continuityData.average_score}
                    </div>
                    <div className="text-xs text-slate-500">avg score across {continuityData.total} checks</div>
                  </div>
                  {continuityData.validations?.slice(0, 3).map((v, i) => (
                    <div key={i} className="bg-slate-800/40 rounded p-2 text-[10px] space-y-0.5">
                      <div className="flex items-center justify-between">
                        <span className={`font-medium ${v.continuity_score >= 70 ? 'text-green-400' : v.continuity_score >= 50 ? 'text-amber-400' : 'text-red-400'}`}>
                          {v.continuity_score}/100
                        </span>
                        <span className="text-slate-600">{v.tool_type} · {new Date(v.validated_at).toLocaleDateString()}</span>
                      </div>
                      <p className="text-slate-400">{v.summary}</p>
                      {v.drift_flags?.length > 0 && v.drift_flags.slice(0, 2).map((f, fi) => (
                        <span key={fi} className={`inline-block mr-1 px-1 py-0.5 rounded ${f.severity === 'high' ? 'bg-red-500/15 text-red-400' : f.severity === 'medium' ? 'bg-amber-500/15 text-amber-400' : 'bg-slate-700 text-slate-400'}`}>
                          {f.type}: {f.detail?.slice(0, 40)}
                        </span>
                      ))}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-500">No continuity checks yet. Run a validation or generate episodes with this character attached.</p>
              )}
            </div>
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

            {/* Relationships */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4" data-testid="relationships-zone">
              <h3 className="text-sm font-medium text-slate-300 flex items-center gap-1.5 mb-3">
                <Users className="w-3.5 h-3.5" /> Relationships
                <span className="ml-auto text-xs text-slate-500">{relationships.length}</span>
              </h3>
              {relationships.length === 0 ? (
                <p className="text-xs text-slate-500 text-center py-2">No relationships yet. Add one from another character's page or attach characters to the same series.</p>
              ) : (
                <div className="space-y-1.5">
                  {relationships.map((r, i) => (
                    <button key={i} onClick={() => navigate(`/app/characters/${r.related_character_id}`)}
                      className="w-full flex items-center gap-2 p-2 rounded-lg bg-slate-800/40 hover:bg-slate-800 transition-all text-left"
                    >
                      {r.related_portrait_url ? (
                        <img src={r.related_portrait_url} alt="" className="w-6 h-6 rounded-md object-cover" />
                      ) : (
                        <div className="w-6 h-6 rounded-md bg-slate-700 flex items-center justify-center"><User className="w-3 h-3 text-slate-500" /></div>
                      )}
                      <div className="flex-1 min-w-0">
                        <span className="text-xs text-white">{r.related_name || 'Unknown'}</span>
                        <span className="text-[10px] text-slate-500 ml-1.5">{r.related_species} {r.related_role}</span>
                      </div>
                      <div className="text-right">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                          r.relationship_type === 'friend' || r.relationship_type === 'ally' ? 'bg-green-500/15 text-green-400' :
                          r.relationship_type === 'enemy' || r.relationship_type === 'rival' ? 'bg-red-500/15 text-red-400' :
                          'bg-slate-700 text-slate-400'
                        }`}>{r.relationship_type}</span>
                        <div className="text-[9px] text-slate-600 mt-0.5">{r.relationship_state}</div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Emotional Arc */}
            {emotionalArc && emotionalArc.total_entries > 0 && (
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4" data-testid="emotional-arc-zone">
                <h3 className="text-sm font-medium text-slate-300 flex items-center gap-1.5 mb-3">
                  <Heart className="w-3.5 h-3.5" /> Emotional Arc
                  <span className="ml-auto text-xs text-slate-500 flex items-center gap-1">
                    <TrendingUp className="w-3 h-3" /> {emotionalArc.trend}
                  </span>
                </h3>
                <div className="space-y-1">
                  {emotionalArc.arc.map((a, i) => {
                    const emojiMap = { happy: '😊', sad: '😢', tense: '😰', scared: '😨', confident: '😤', angry: '😠', neutral: '😐', hopeful: '🌟', determined: '💪' };
                    const barColor = { happy: 'bg-green-500', sad: 'bg-blue-500', tense: 'bg-amber-500', scared: 'bg-red-500', confident: 'bg-indigo-500', angry: 'bg-red-600', neutral: 'bg-slate-500', hopeful: 'bg-cyan-500', determined: 'bg-purple-500' };
                    return (
                      <div key={i} className="flex items-center gap-2 text-[10px]">
                        <span className="w-4 text-center">{emojiMap[a.emotion] || '😐'}</span>
                        <span className="w-16 text-slate-500 truncate capitalize">{a.emotion}</span>
                        <div className="flex-1 bg-slate-800 rounded-full h-1.5">
                          <div className={`h-full rounded-full ${barColor[a.emotion] || 'bg-slate-500'}`} style={{ width: `${(a.intensity / 5) * 100}%` }} />
                        </div>
                        <span className="text-slate-600 w-20 truncate">{a.event_summary?.slice(0, 20)}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
