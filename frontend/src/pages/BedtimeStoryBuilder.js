import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  Moon, Sparkles, Heart, BookOpen, Volume2, Clock, ChevronRight,
  Download, Check, AlertCircle, Play, Pause, Star, Zap,
  Smile, CloudMoon, Rocket, Dog, Laugh, Music, Eye, EyeOff,
  Loader2, Copy, RotateCcw, ChevronLeft,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import api from '../utils/api';
import { useCredits } from '../contexts/CreditContext';
import HelpGuide from '../components/HelpGuide';
import NextActionHooks from '../components/NextActionHooks';

// ── Constants ──
const MOODS = [
  { id: 'calm', label: 'Calm', icon: CloudMoon, color: 'indigo' },
  { id: 'funny', label: 'Funny', icon: Smile, color: 'amber' },
  { id: 'adventure', label: 'Adventure', icon: Rocket, color: 'emerald' },
  { id: 'sleepy', label: 'Sleepy', icon: Moon, color: 'purple' },
];

const AGES = [
  { id: '3-5', label: '3-5', desc: 'Toddlers' },
  { id: '6-8', label: '6-8', desc: 'Kids' },
  { id: '9-12', label: '9-12', desc: 'Tweens' },
];

const VOICES = [
  { id: 'calm_parent', label: 'Mom / Dad', desc: 'Warm & gentle' },
  { id: 'playful_storyteller', label: 'Storyteller', desc: 'Animated & fun' },
  { id: 'gentle_teacher', label: 'Teacher', desc: 'Calm & nurturing' },
];

const DURATIONS = [
  { id: '3', label: '3 min', desc: 'Quick' },
  { id: '5', label: '5 min', desc: 'Standard' },
  { id: '8', label: '8 min', desc: 'Extended' },
];

const REMIX_VARIANTS = [
  { id: 'animal', label: 'Animal Version', icon: Dog, color: 'from-amber-500 to-orange-500' },
  { id: 'space', label: 'Space Version', icon: Rocket, color: 'from-indigo-500 to-purple-500' },
  { id: 'funny', label: 'Funny Version', icon: Laugh, color: 'from-yellow-500 to-amber-500' },
  { id: 'sleep', label: 'Extra Sleepy', icon: CloudMoon, color: 'from-violet-500 to-indigo-500' },
];

const THEMES = [
  'Enchanted Forest', 'Ocean Adventure', 'Cloud Kingdom', 'Magic Garden',
  'Moon Journey', 'Star Wishes', 'Bedtime Calm', 'Animals', 'Nature', 'Magic',
];

const MORALS = [
  'Be kind', 'Be brave', 'Try again', 'Tell truth', 'Help friends', 'Be thankful',
];

const STREAK_KEY = 'bedtime_streak';
const STREAK_DATE_KEY = 'bedtime_streak_date';

// ── Streak Logic ──
function getStreak() {
  try {
    const streak = parseInt(localStorage.getItem(STREAK_KEY) || '0', 10);
    const lastDate = localStorage.getItem(STREAK_DATE_KEY);
    if (!lastDate) return 0;
    const today = new Date().toDateString();
    const yesterday = new Date(Date.now() - 86400000).toDateString();
    if (lastDate === today) return streak;
    if (lastDate === yesterday) return streak; // Still valid, will increment on play
    return 0; // Streak broken
  } catch { return 0; }
}

function updateStreak() {
  try {
    const today = new Date().toDateString();
    const lastDate = localStorage.getItem(STREAK_DATE_KEY);
    let streak = parseInt(localStorage.getItem(STREAK_KEY) || '0', 10);
    if (lastDate === today) return streak; // Already counted today
    const yesterday = new Date(Date.now() - 86400000).toDateString();
    if (lastDate === yesterday) {
      streak += 1;
    } else {
      streak = 1;
    }
    localStorage.setItem(STREAK_KEY, String(streak));
    localStorage.setItem(STREAK_DATE_KEY, today);
    return streak;
  } catch { return 1; }
}

// ── Web Speech Playback ──
function useSpeech() {
  const [playing, setPlaying] = useState(false);
  const [currentScene, setCurrentScene] = useState(-1);
  const synthRef = useRef(null);

  const speak = useCallback((text, onEnd) => {
    if (!window.speechSynthesis) { toast.error('Speech not supported in this browser'); return; }
    window.speechSynthesis.cancel();
    // Strip markers
    const clean = text
      .replace(/\[PAUSE \d+\.?\d*s\]/g, '. ')
      .replace(/\[(SLOW|WHISPER|EMPHASIZE)\]/g, '')
      .replace(/\[SFX:[^\]]*\]/g, '')
      .trim();
    const utterance = new SpeechSynthesisUtterance(clean);
    utterance.rate = 0.85;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;
    // Try to get a gentle voice
    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(v => v.name.includes('Samantha') || v.name.includes('Google UK English Female') || v.name.includes('Female'));
    if (preferred) utterance.voice = preferred;
    utterance.onend = () => { if (onEnd) onEnd(); };
    window.speechSynthesis.speak(utterance);
    synthRef.current = utterance;
  }, []);

  const playScenes = useCallback((scenes) => {
    setPlaying(true);
    setCurrentScene(0);
    let idx = 0;
    const playNext = () => {
      if (idx >= scenes.length) { setPlaying(false); setCurrentScene(-1); return; }
      setCurrentScene(idx);
      const text = scenes[idx].text || scenes[idx];
      idx++;
      speak(text, playNext);
    };
    playNext();
  }, [speak]);

  const stop = useCallback(() => {
    window.speechSynthesis?.cancel();
    setPlaying(false);
    setCurrentScene(-1);
  }, []);

  return { playing, currentScene, playScenes, stop };
}

// ── Main Component ──
export default function BedtimeStoryBuilder() {
  const { credits, setCredits } = useCredits();
  const [config, setConfig] = useState(null);

  // Input state
  const [childName, setChildName] = useState('');
  const [ageGroup, setAgeGroup] = useState('6-8');
  const [mood, setMood] = useState('calm');
  const [voiceStyle, setVoiceStyle] = useState('calm_parent');
  const [duration, setDuration] = useState('5');
  const [theme, setTheme] = useState('Enchanted Forest');
  const [moral, setMoral] = useState('Be kind');

  // Generation state
  const [generating, setGenerating] = useState(false);
  const [story, setStory] = useState(null);
  const [creditsUsed, setCreditsUsed] = useState(0);

  // UI state
  const [bedtimeMode, setBedtimeMode] = useState(false);
  const [streak, setStreak] = useState(0);
  const [copiedSection, setCopiedSection] = useState(null);

  // Speech
  const { playing, currentScene, playScenes, stop } = useSpeech();

  // Scene ref for auto-scroll
  const sceneRefs = useRef([]);
  const resultRef = useRef(null);

  useEffect(() => {
    fetchConfig();
    setStreak(getStreak());
    // Load voices
    if (window.speechSynthesis) window.speechSynthesis.getVoices();
  }, []);

  // Auto-scroll to current scene in bedtime mode
  useEffect(() => {
    if (bedtimeMode && currentScene >= 0 && sceneRefs.current[currentScene]) {
      sceneRefs.current[currentScene].scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [currentScene, bedtimeMode]);

  const fetchConfig = async () => {
    try {
      const res = await api.get('/api/bedtime-story/config');
      setConfig(res.data);
    } catch { /* defaults work fine */ }
  };

  const handleGenerate = async (remixType = null) => {
    if ((credits ?? 0) < 10) { toast.error('Need 10 credits. Buy more to continue.'); return; }
    setGenerating(true);
    setStory(null);
    try {
      const res = await api.post('/api/bedtime-story/generate', {
        age_group: ageGroup,
        theme,
        moral,
        length: duration,
        voice_style: voiceStyle,
        child_name: childName || null,
        mood,
        remix_type: remixType,
      });
      if (res.data.success) {
        setStory(res.data.story);
        setCreditsUsed(res.data.credits_used);
        setCredits(res.data.remaining_credits);
        const newStreak = updateStreak();
        setStreak(newStreak);
        toast.success(`Story created! ${newStreak > 1 ? `${newStreak}-day streak!` : ''}`);
        setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth' }), 300);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Generation failed');
    }
    setGenerating(false);
  };

  const handleRemix = (variant) => {
    handleGenerate(variant.id);
  };

  const handlePlay = () => {
    if (playing) { stop(); return; }
    if (story?.scenes) {
      playScenes(story.scenes);
    } else if (story?.script) {
      const chunks = story.script.split('\n\n').filter(Boolean);
      playScenes(chunks.map(t => ({ text: t })));
    }
  };

  const copySection = (text, section) => {
    navigator.clipboard?.writeText(text);
    setCopiedSection(section);
    toast.success('Copied!');
    setTimeout(() => setCopiedSection(null), 2000);
  };

  const downloadStory = () => {
    if (!story) return;
    const content = [
      `# ${story.title || 'Bedtime Story'}`,
      `Character: ${story.metadata?.character}`,
      `Setting: ${story.metadata?.place}`,
      '',
      story.script || story.scenes?.map(s => s.text).join('\n\n'),
      '',
      '## Voice Notes',
      ...(story.voice_notes || []).map(v => `[${v.scene}] ${v.note}`),
      '',
      '## Sound Effects',
      ...(story.sfx_cues || []).map(s => `[${s.scene}] ${s.cue}`),
    ].join('\n');
    const blob = new Blob([content], { type: 'text/plain' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `bedtime_story_${Date.now()}.txt`;
    a.click();
  };

  // ── Render ──
  const bgClass = bedtimeMode
    ? 'bg-[#0B0F1A] min-h-screen transition-colors duration-1000'
    : 'bg-gradient-to-b from-slate-900 via-indigo-950/30 to-slate-900 min-h-screen';

  return (
    <div className={bgClass}>
      <div className="max-w-3xl mx-auto px-4 py-6 sm:py-10">

        {/* ── Hero Section ── */}
        {!story && (
          <div className="text-center mb-8" data-testid="hero-section">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 mb-4">
              <Moon className="w-3.5 h-3.5 text-indigo-400" />
              <span className="text-xs text-indigo-300 font-medium">Bedtime Story Engine</span>
              {streak > 0 && (
                <span className="text-xs text-amber-400 font-bold ml-1" data-testid="streak-badge">
                  {streak}-day streak
                </span>
              )}
            </div>
            <h1 className="text-3xl sm:text-4xl font-bold text-white mb-2 leading-tight">
              A magical bedtime story for your child
              <br />
              <span className="text-indigo-400">— ready in seconds</span>
            </h1>
            <p className="text-slate-400 text-sm sm:text-base max-w-lg mx-auto">
              AI creates personalized stories with voice pacing, sound effects & calming endings. One tap.
            </p>
          </div>
        )}

        {/* ── One-Screen Smart Input ── */}
        {!story && (
          <div className="bg-slate-800/40 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-5 sm:p-7 space-y-5" data-testid="smart-input">

            {/* Child Name */}
            <div>
              <label className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-1.5 block">Child's Name (optional)</label>
              <input
                type="text"
                value={childName}
                onChange={(e) => setChildName(e.target.value)}
                placeholder="Makes the story personal"
                className="w-full bg-slate-900/60 border border-slate-700/50 rounded-xl px-4 py-3 text-white placeholder:text-slate-600 focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/20 outline-none text-base"
                data-testid="child-name-input"
              />
            </div>

            {/* Age */}
            <div>
              <label className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-1.5 block">Age</label>
              <div className="grid grid-cols-3 gap-2">
                {AGES.map(a => (
                  <button key={a.id} onClick={() => setAgeGroup(a.id)}
                    className={`py-2.5 rounded-xl text-center transition-all ${
                      ageGroup === a.id
                        ? 'bg-indigo-500/20 border-2 border-indigo-500/50 text-white'
                        : 'bg-slate-800/50 border-2 border-transparent text-slate-400 hover:border-slate-600'
                    }`} data-testid={`age-${a.id}`}>
                    <div className="font-bold text-base">{a.label}</div>
                    <div className="text-[10px] text-slate-500">{a.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Mood */}
            <div>
              <label className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-1.5 block">Mood</label>
              <div className="grid grid-cols-4 gap-2">
                {MOODS.map(m => {
                  const Icon = m.icon;
                  return (
                    <button key={m.id} onClick={() => setMood(m.id)}
                      className={`py-2.5 rounded-xl text-center transition-all ${
                        mood === m.id
                          ? 'bg-indigo-500/20 border-2 border-indigo-500/50 text-white'
                          : 'bg-slate-800/50 border-2 border-transparent text-slate-400 hover:border-slate-600'
                      }`} data-testid={`mood-${m.id}`}>
                      <Icon className="w-4 h-4 mx-auto mb-0.5" />
                      <div className="text-[11px] font-medium">{m.label}</div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Voice + Duration row */}
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-1.5 block">Voice</label>
                <div className="space-y-1.5">
                  {VOICES.map(v => (
                    <button key={v.id} onClick={() => setVoiceStyle(v.id)}
                      className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg transition-all text-left ${
                        voiceStyle === v.id
                          ? 'bg-indigo-500/15 border border-indigo-500/40 text-white'
                          : 'bg-slate-800/40 border border-transparent text-slate-400 hover:border-slate-600'
                      }`} data-testid={`voice-${v.id}`}>
                      <Volume2 className={`w-3.5 h-3.5 ${voiceStyle === v.id ? 'text-indigo-400' : 'text-slate-600'}`} />
                      <div>
                        <span className="text-xs font-medium">{v.label}</span>
                        <span className="text-[10px] text-slate-500 ml-1.5">{v.desc}</span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-1.5 block">Duration</label>
                <div className="space-y-1.5">
                  {DURATIONS.map(d => (
                    <button key={d.id} onClick={() => setDuration(d.id)}
                      className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg transition-all text-left ${
                        duration === d.id
                          ? 'bg-indigo-500/15 border border-indigo-500/40 text-white'
                          : 'bg-slate-800/40 border border-transparent text-slate-400 hover:border-slate-600'
                      }`} data-testid={`duration-${d.id}`}>
                      <Clock className={`w-3.5 h-3.5 ${duration === d.id ? 'text-indigo-400' : 'text-slate-600'}`} />
                      <span className="text-xs font-medium">{d.label}</span>
                      <span className="text-[10px] text-slate-500 ml-1">{d.desc}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Theme + Moral row */}
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-1.5 block">Theme</label>
                <select value={theme} onChange={(e) => setTheme(e.target.value)}
                  className="w-full bg-slate-900/60 border border-slate-700/50 rounded-lg px-3 py-2.5 text-white text-sm focus:border-indigo-500/50 outline-none"
                  data-testid="theme-select">
                  {THEMES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-1.5 block">Moral / Lesson</label>
                <select value={moral} onChange={(e) => setMoral(e.target.value)}
                  className="w-full bg-slate-900/60 border border-slate-700/50 rounded-lg px-3 py-2.5 text-white text-sm focus:border-indigo-500/50 outline-none"
                  data-testid="moral-select">
                  {MORALS.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
            </div>

            {/* Generate Button */}
            <button
              onClick={() => handleGenerate()}
              disabled={generating || (credits ?? 0) < 10}
              className="w-full py-4 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 disabled:opacity-50 text-white font-bold text-base transition-all flex items-center justify-center gap-2"
              data-testid="generate-btn"
            >
              {generating ? (
                <><Loader2 className="w-5 h-5 animate-spin" /> Creating your story...</>
              ) : (
                <><Moon className="w-5 h-5" /> Create Magic Story</>
              )}
            </button>
            <p className="text-center text-[11px] text-slate-600">10 credits &middot; AI-powered &middot; {credits !== null ? `${credits >= 999999 ? 'Unlimited' : credits} credits available` : ''}</p>
          </div>
        )}

        {/* ── Story Result ── */}
        {story && (
          <div ref={resultRef} data-testid="story-result">
            {/* Title + Controls */}
            <div className="text-center mb-6">
              <h2 className={`font-bold text-white mb-1 ${bedtimeMode ? 'text-2xl' : 'text-xl sm:text-2xl'}`} data-testid="story-title">
                {story.title || 'Your Bedtime Story'}
              </h2>
              <p className="text-slate-500 text-xs">
                {story.metadata?.character && `Starring ${story.metadata.character}`}
                {story.metadata?.place && ` in ${story.metadata.place}`}
                {creditsUsed > 0 && ` &middot; ${creditsUsed} credits used`}
              </p>
              {streak > 0 && (
                <div className="inline-flex items-center gap-1 mt-2 px-2.5 py-1 rounded-full bg-amber-500/10 border border-amber-500/20" data-testid="streak-result">
                  <Star className="w-3 h-3 text-amber-400" />
                  <span className="text-[11px] text-amber-400 font-bold">{streak}-day bedtime streak!</span>
                </div>
              )}
            </div>

            {/* Action Bar */}
            <div className="flex items-center justify-center gap-2 mb-5 flex-wrap">
              <Button onClick={handlePlay}
                className={`rounded-full px-5 py-2.5 font-bold text-sm ${
                  playing ? 'bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30' : 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white hover:opacity-90'
                }`} data-testid="play-btn">
                {playing ? <><Pause className="w-4 h-4 mr-1.5" /> Stop</> : <><Play className="w-4 h-4 mr-1.5" /> Play Story</>}
              </Button>
              <Button variant="outline" onClick={() => setBedtimeMode(!bedtimeMode)}
                className={`rounded-full px-4 py-2.5 text-sm font-medium ${
                  bedtimeMode ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30' : 'border-slate-700 text-slate-400 hover:text-white'
                }`} data-testid="bedtime-mode-btn">
                {bedtimeMode ? <><EyeOff className="w-3.5 h-3.5 mr-1.5" /> Bedtime On</> : <><Moon className="w-3.5 h-3.5 mr-1.5" /> Bedtime Mode</>}
              </Button>
              <Button variant="outline" onClick={downloadStory} className="rounded-full px-4 py-2.5 text-sm border-slate-700 text-slate-400 hover:text-white" data-testid="download-btn">
                <Download className="w-3.5 h-3.5 mr-1.5" /> Download
              </Button>
              <Button variant="outline" onClick={() => copySection(story.script || story.scenes?.map(s => s.text).join('\n\n'), 'full')}
                className={`rounded-full px-4 py-2.5 text-sm ${copiedSection === 'full' ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' : 'border-slate-700 text-slate-400 hover:text-white'}`}>
                {copiedSection === 'full' ? <Check className="w-3.5 h-3.5 mr-1.5" /> : <Copy className="w-3.5 h-3.5 mr-1.5" />}
                {copiedSection === 'full' ? 'Copied' : 'Copy'}
              </Button>
            </div>

            {/* Story Content — Scene by Scene */}
            <div className={`rounded-2xl border overflow-hidden ${
              bedtimeMode ? 'bg-[#0D1117] border-slate-800' : 'bg-slate-800/40 border-slate-700/50'
            }`}>
              {story.scenes ? (
                <div className="divide-y divide-slate-800/50">
                  {story.scenes.map((scene, idx) => (
                    <div
                      key={idx}
                      ref={el => sceneRefs.current[idx] = el}
                      className={`p-4 sm:p-5 transition-all duration-700 ${
                        currentScene === idx ? (bedtimeMode ? 'bg-indigo-500/5' : 'bg-indigo-500/10') : ''
                      }`}
                      data-testid={`scene-${idx}`}
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <span className={`text-[10px] font-bold uppercase tracking-wider ${
                          currentScene === idx ? 'text-indigo-400' : 'text-slate-600'
                        }`}>
                          {scene.scene_type?.replace(/_/g, ' ') || `Scene ${idx + 1}`}
                        </span>
                        {scene.emotion && (
                          <span className="text-[10px] text-slate-600 bg-slate-800 px-1.5 py-0.5 rounded">{scene.emotion}</span>
                        )}
                        {currentScene === idx && playing && (
                          <span className="text-[10px] text-indigo-400 animate-pulse ml-auto">Speaking...</span>
                        )}
                      </div>
                      <p className={`leading-relaxed ${
                        bedtimeMode ? 'text-slate-200 text-lg sm:text-xl' : 'text-slate-300 text-sm sm:text-base'
                      }`}>
                        {scene.text?.replace(/\[(PAUSE \d+\.?\d*s|SLOW|WHISPER|EMPHASIZE)\]/g, '').replace(/\[SFX:[^\]]*\]/g, '').trim()}
                      </p>
                      {scene.sfx && !bedtimeMode && (
                        <div className="flex items-center gap-1 mt-2 text-[10px] text-pink-400/60">
                          <Music className="w-2.5 h-2.5" /> {scene.sfx}
                        </div>
                      )}
                      {scene.voice_hint && !bedtimeMode && (
                        <div className="flex items-center gap-1 mt-1 text-[10px] text-indigo-400/50">
                          <Volume2 className="w-2.5 h-2.5" /> {scene.voice_hint}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                /* Fallback: raw script display */
                <div className="p-5">
                  <pre className={`whitespace-pre-wrap font-sans leading-relaxed ${
                    bedtimeMode ? 'text-slate-200 text-lg' : 'text-slate-300 text-sm'
                  }`}>
                    {story.script}
                  </pre>
                </div>
              )}
            </div>

            {/* Voice Notes + SFX (collapsed in bedtime mode) */}
            {!bedtimeMode && (story.voice_notes?.length > 0 || story.sfx_cues?.length > 0) && (
              <div className="grid sm:grid-cols-2 gap-4 mt-4">
                {story.voice_notes?.length > 0 && (
                  <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-4">
                    <p className="text-xs font-bold text-indigo-400 uppercase tracking-wider mb-2">Voice Pacing Notes</p>
                    <div className="space-y-2">
                      {story.voice_notes.map((v, i) => (
                        <div key={i} className="text-[11px]">
                          <span className="text-slate-500 font-medium">{v.scene}:</span>
                          <span className="text-slate-400 ml-1">{v.note}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {story.sfx_cues?.length > 0 && (
                  <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-4">
                    <p className="text-xs font-bold text-pink-400 uppercase tracking-wider mb-2">Sound Effects</p>
                    <div className="space-y-2">
                      {story.sfx_cues.map((s, i) => (
                        <div key={i} className="text-[11px]">
                          <span className="text-slate-500 font-medium">{s.scene}:</span>
                          <span className="text-slate-400 ml-1">{s.cue}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* ── Remix Variants ── */}
            <div className="mt-5" data-testid="remix-variants">
              <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-2 text-center">Instant Remix</p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {REMIX_VARIANTS.map(v => {
                  const Icon = v.icon;
                  return (
                    <button key={v.id} onClick={() => handleRemix(v)} disabled={generating}
                      className="flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-slate-800/50 border border-slate-700/50 text-slate-300 hover:text-white hover:border-slate-600 transition-all disabled:opacity-50 text-xs font-medium"
                      data-testid={`remix-${v.id}`}>
                      <Icon className="w-3.5 h-3.5" /> {v.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* ── Come Back Tonight Hook ── */}
            <div className="mt-6 text-center bg-indigo-500/5 border border-indigo-500/15 rounded-xl py-4 px-5" data-testid="comeback-hook">
              <Moon className="w-5 h-5 text-indigo-400/60 mx-auto mb-1.5" />
              <p className="text-sm text-white font-medium">Come back tomorrow for a new magical story</p>
              <p className="text-[11px] text-slate-500 mt-1">
                {streak > 0
                  ? `You're on a ${streak}-day streak! Don't break it.`
                  : 'Start your bedtime streak tonight!'}
              </p>
            </div>

            {/* New Story button */}
            <div className="flex justify-center mt-5 gap-3">
              <Button variant="outline" onClick={() => { setStory(null); stop(); }}
                className="rounded-full border-slate-700 text-slate-400 hover:text-white" data-testid="new-story-btn">
                <RotateCcw className="w-3.5 h-3.5 mr-1.5" /> New Story
              </Button>
            </div>

            {/* NextActionHooks */}
            <NextActionHooks
              toolType="bedtime-story-builder"
              prompt={`${theme} bedtime story about ${story?.metadata?.character || 'a character'}`}
              settings={{ ageGroup, theme, moral }}
              title={story?.title || 'Bedtime Story'}
            />
          </div>
        )}

        {/* Disclaimer */}
        {!bedtimeMode && (
          <div className="mt-6 p-3 bg-amber-500/5 border border-amber-500/20 rounded-xl">
            <div className="flex gap-2 items-center">
              <AlertCircle className="w-4 h-4 text-amber-400/60 shrink-0" />
              <p className="text-[11px] text-amber-200/60">
                All stories are original, AI-generated, and family-friendly. No copyrighted characters.
              </p>
            </div>
          </div>
        )}

        <HelpGuide pageId="bedtime-story-builder" />
      </div>
    </div>
  );
}
