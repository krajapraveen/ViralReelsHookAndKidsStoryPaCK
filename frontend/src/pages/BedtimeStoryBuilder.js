import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Moon, Sparkles, Volume2, Clock, ChevronRight,
  Download, Check, AlertCircle, Play, Pause, Star,
  Smile, CloudMoon, Rocket, Dog, Laugh, Music,
  Loader2, Copy, RotateCcw, Eye, EyeOff,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import api from '../utils/api';
import { useCredits } from '../contexts/CreditContext';

// ── Centralized API endpoints ──
const BEDTIME_API = {
  config: '/api/bedtime-story-builder/config',
  generate: '/api/bedtime-story-builder/generate',
  track: '/api/bedtime-story-builder/track',
};

// ── Lightweight event tracker (fire-and-forget) ──
const track = (eventType) => {
  api.post(BEDTIME_API.track, { event_type: eventType }).catch(() => {});
};

// ── Constants ──
const MOODS = [
  { id: 'calm', label: 'Calm', icon: CloudMoon },
  { id: 'funny', label: 'Funny', icon: Smile },
  { id: 'adventure', label: 'Adventure', icon: Rocket },
  { id: 'sleepy', label: 'Sleepy', icon: Moon },
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
  { id: 'animal', label: 'Animal Version', icon: Dog },
  { id: 'space', label: 'Space Version', icon: Rocket },
  { id: 'funny', label: 'Funny Version', icon: Laugh },
  { id: 'sleep', label: 'Extra Sleepy', icon: CloudMoon },
];

const THEMES = [
  'Enchanted Forest', 'Ocean Adventure', 'Cloud Kingdom', 'Magic Garden',
  'Moon Journey', 'Star Wishes', 'Bedtime Calm', 'Animals', 'Nature', 'Magic',
];

const MORALS = [
  'Be kind', 'Be brave', 'Try again', 'Tell truth', 'Help friends', 'Be thankful',
];

// ── Streak Logic (localStorage) ──
function getStreak() {
  try {
    const streak = parseInt(localStorage.getItem('bedtime_streak') || '0', 10);
    const lastDate = localStorage.getItem('bedtime_streak_date');
    if (!lastDate) return 0;
    const today = new Date().toDateString();
    const yesterday = new Date(Date.now() - 86400000).toDateString();
    if (lastDate === today || lastDate === yesterday) return streak;
    return 0;
  } catch { return 0; }
}

function bumpStreak() {
  try {
    const today = new Date().toDateString();
    const lastDate = localStorage.getItem('bedtime_streak_date');
    let streak = parseInt(localStorage.getItem('bedtime_streak') || '0', 10);
    if (lastDate === today) return streak;
    const yesterday = new Date(Date.now() - 86400000).toDateString();
    streak = lastDate === yesterday ? streak + 1 : 1;
    localStorage.setItem('bedtime_streak', String(streak));
    localStorage.setItem('bedtime_streak_date', today);
    return streak;
  } catch { return 1; }
}

// ── Web Speech Hook ──
function useSpeech() {
  const [playing, setPlaying] = useState(false);
  const [paused, setPaused] = useState(false);
  const [currentScene, setCurrentScene] = useState(-1);
  const voicesReady = useRef(false);
  const cancelledRef = useRef(false);

  useEffect(() => {
    const synth = window.speechSynthesis;
    if (!synth) return;
    const loadVoices = () => { synth.getVoices(); voicesReady.current = true; };
    loadVoices();
    synth.addEventListener('voiceschanged', loadVoices);
    return () => synth.removeEventListener('voiceschanged', loadVoices);
  }, []);

  const pickVoice = useCallback(() => {
    const voices = window.speechSynthesis?.getVoices() || [];
    return voices.find(v =>
      v.name.includes('Samantha') || v.name.includes('Google UK English Female') || v.lang.startsWith('en')
    ) || voices[0] || null;
  }, []);

  const cleanText = useCallback((text) => {
    return (text || '')
      .replace(/\[PAUSE \d+\.?\d*s\]/g, '. ')
      .replace(/\[(SLOW|WHISPER|EMPHASIZE)\]/g, '')
      .replace(/\[SFX:[^\]]*\]/g, '')
      .trim();
  }, []);

  const playScenes = useCallback((scenes) => {
    const synth = window.speechSynthesis;
    if (!synth) { toast.error('Speech not supported in this browser'); return; }
    synth.cancel();
    cancelledRef.current = false;
    setPlaying(true);
    setPaused(false);
    setCurrentScene(0);

    let idx = 0;
    const voice = pickVoice();
    const playNext = () => {
      if (cancelledRef.current || idx >= scenes.length) {
        setPlaying(false);
        setCurrentScene(-1);
        return;
      }
      setCurrentScene(idx);
      const raw = scenes[idx]?.text || (typeof scenes[idx] === 'string' ? scenes[idx] : '');
      const text = cleanText(raw);
      idx++;
      if (!text) { playNext(); return; }
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.85;
      utterance.pitch = 1.0;
      utterance.volume = 1.0;
      if (voice) utterance.voice = voice;
      utterance.onend = playNext;
      utterance.onerror = playNext;
      synth.speak(utterance);
    };
    playNext();
  }, [pickVoice, cleanText]);

  const pause = useCallback(() => {
    window.speechSynthesis?.pause();
    setPaused(true);
  }, []);

  const resume = useCallback(() => {
    window.speechSynthesis?.resume();
    setPaused(false);
  }, []);

  const stop = useCallback(() => {
    cancelledRef.current = true;
    window.speechSynthesis?.cancel();
    setPlaying(false);
    setPaused(false);
    setCurrentScene(-1);
  }, []);

  return { playing, paused, currentScene, playScenes, pause, resume, stop };
}

// ── Main Component ──
export default function BedtimeStoryBuilder() {
  const { credits, creditsLoaded, refreshCredits } = useCredits();

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
  const { playing, paused, currentScene, playScenes, pause, resume, stop } = useSpeech();

  // Refs
  const sceneRefs = useRef([]);
  const resultRef = useRef(null);

  useEffect(() => {
    fetchConfig();
    setStreak(getStreak());
    // Track session_started + check for next-day return
    track('session_started');
    const lastVisit = localStorage.getItem('bedtime_last_visit');
    if (lastVisit) {
      const yesterday = new Date(Date.now() - 86400000).toDateString();
      if (lastVisit === yesterday) track('session_returned');
    }
    localStorage.setItem('bedtime_last_visit', new Date().toDateString());
  }, []);

  // Auto-scroll to current scene
  useEffect(() => {
    if (currentScene >= 0 && sceneRefs.current[currentScene]) {
      sceneRefs.current[currentScene].scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [currentScene]);

  // Bedtime mode: add/remove class on body
  useEffect(() => {
    if (bedtimeMode) {
      document.body.classList.add('bedtime-mode');
    } else {
      document.body.classList.remove('bedtime-mode');
    }
    return () => document.body.classList.remove('bedtime-mode');
  }, [bedtimeMode]);

  const fetchConfig = async () => {
    try {
      await api.get(BEDTIME_API.config);
    } catch { /* defaults work fine */ }
  };

  const handleGenerate = async (remixType = null) => {
    if (creditsLoaded && credits !== null && credits < 10) {
      toast.error('Need 10 credits. Buy more to continue.');
      return;
    }
    setGenerating(true);
    if (!remixType) setStory(null);

    // Step 1: Primary generation — ONLY this can show "Generation failed"
    let result = null;
    try {
      const res = await api.post(BEDTIME_API.generate, {
        age_group: ageGroup,
        theme,
        moral,
        length: duration,
        voice_style: voiceStyle,
        child_name: childName || null,
        mood,
        remix_type: remixType,
      });
      if (res.data?.success && res.data?.story) {
        result = res.data;
      } else {
        toast.error('Story generation returned empty result');
        setGenerating(false);
        return;
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Generation failed');
      setGenerating(false);
      return;
    }

    // Step 2: Post-success side effects — NEVER show "Generation failed"
    try { stop(); } catch (e) { console.warn('Speech stop error:', e); }
    setStory(result.story);
    setCreditsUsed(result.credits_used ?? 0);
    try { refreshCredits(); } catch (e) { console.warn('Credit refresh error:', e); }
    try {
      const newStreak = bumpStreak();
      setStreak(newStreak);
      toast.success(`Story created!${newStreak > 1 ? ` ${newStreak}-day streak!` : ''}`);
    } catch (e) { console.warn('Streak error:', e); toast.success('Story created!'); }
    track(remixType ? 'remix_clicked' : 'story_generated');
    setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth' }), 300);
    setGenerating(false);
  };

  const handlePlay = () => {
    if (playing && !paused) { pause(); return; }
    if (paused) { resume(); return; }
    track('play_clicked');
    if (story?.scenes?.length) {
      playScenes(story.scenes);
    } else if (story?.script) {
      const chunks = story.script.split('\n\n').filter(Boolean);
      playScenes(chunks.map(t => ({ text: t })));
    }
  };

  const handleStop = () => stop();

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
      `Character: ${story.metadata?.character || ''}`,
      `Setting: ${story.metadata?.place || ''}`,
      '',
      story.script || story.scenes?.map(s => s.text).join('\n\n') || '',
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

  const stripMarkers = (text) =>
    (text || '').replace(/\[(PAUSE \d+\.?\d*s|SLOW|WHISPER|EMPHASIZE)\]/g, '').replace(/\[SFX:[^\]]*\]/g, '').trim();

  // ── Render ──
  const bgClass = bedtimeMode
    ? 'min-h-screen transition-all duration-1000 bg-[#060A14]'
    : 'min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950/20 to-slate-950';

  return (
    <div className={bgClass}>
      {/* Bedtime Mode overlay filter */}
      {bedtimeMode && (
        <style>{`
          body.bedtime-mode { background: #060A14 !important; }
          body.bedtime-mode .navbar, body.bedtime-mode .sidebar, body.bedtime-mode footer { opacity: 0.15; pointer-events: none; }
        `}</style>
      )}

      <div className="max-w-3xl mx-auto px-4 py-6 sm:py-10">

        {/* ── Hero Section (only when no story) ── */}
        {!story && (
          <div className="text-center mb-8" data-testid="bedtime-hero">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 mb-4">
              <Moon className="w-3.5 h-3.5 text-indigo-400" />
              <span className="text-xs text-indigo-300 font-medium">Bedtime Experience Engine</span>
              {streak > 0 && (
                <span className="text-xs text-amber-400 font-bold ml-1" data-testid="streak-badge">
                  {streak}-day streak
                </span>
              )}
            </div>
            <h1 className="text-3xl sm:text-4xl font-bold text-white mb-2 leading-tight">
              A magical bedtime story
              <br />
              <span className="text-indigo-400">— ready in seconds</span>
            </h1>
            <p className="text-slate-400 text-sm max-w-lg mx-auto">
              AI creates personalized stories with voice playback, sound effects & calming endings.
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

            {/* Voice + Duration */}
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

            {/* Theme + Moral */}
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
            <p className="text-center text-[11px] text-slate-600">
              10 credits &middot; AI-powered &middot; {creditsLoaded ? `${credits >= 999999 ? 'Unlimited' : credits} credits available` : 'Loading credits...'}
            </p>
          </div>
        )}

        {/* ── Story Result ── */}
        {story && (
          <div ref={resultRef} data-testid="story-result">
            {/* Title */}
            <div className="text-center mb-6">
              <h2 className={`font-bold text-white mb-1 ${bedtimeMode ? 'text-2xl sm:text-3xl' : 'text-xl sm:text-2xl'}`} data-testid="story-title">
                {story.title || 'Your Bedtime Story'}
              </h2>
              <p className="text-slate-500 text-xs">
                {story.metadata?.character && `Starring ${story.metadata.character}`}
                {story.metadata?.place && ` in ${story.metadata.place}`}
                {creditsUsed > 0 && ` · ${creditsUsed} credits used`}
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
              {/* Play / Pause */}
              <Button onClick={handlePlay}
                className={`rounded-full px-5 py-2.5 font-bold text-sm ${
                  playing && !paused
                    ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30 hover:bg-amber-500/30'
                    : 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white hover:opacity-90'
                }`} data-testid="play-btn">
                {playing && !paused ? <><Pause className="w-4 h-4 mr-1.5" /> Pause</> : <><Play className="w-4 h-4 mr-1.5" /> {paused ? 'Resume' : 'Play Story'}</>}
              </Button>
              {/* Stop (only if playing) */}
              {playing && (
                <Button onClick={handleStop}
                  className="rounded-full px-4 py-2.5 text-sm bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30"
                  data-testid="stop-btn">
                  Stop
                </Button>
              )}
              {/* Bedtime Mode */}
              <Button variant="outline" onClick={() => { if (!bedtimeMode) track('bedtime_mode_enabled'); setBedtimeMode(!bedtimeMode); }}
                className={`rounded-full px-4 py-2.5 text-sm font-medium ${
                  bedtimeMode ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30' : 'border-slate-700 text-slate-400 hover:text-white'
                }`} data-testid="bedtime-mode-btn">
                {bedtimeMode ? <><EyeOff className="w-3.5 h-3.5 mr-1.5" /> Bedtime On</> : <><Moon className="w-3.5 h-3.5 mr-1.5" /> Bedtime Mode</>}
              </Button>
              {/* Download */}
              <Button variant="outline" onClick={downloadStory} className="rounded-full px-4 py-2.5 text-sm border-slate-700 text-slate-400 hover:text-white" data-testid="download-btn">
                <Download className="w-3.5 h-3.5 mr-1.5" /> Download
              </Button>
              {/* Copy */}
              <Button variant="outline" onClick={() => copySection(story.script || story.scenes?.map(s => s.text).join('\n\n'), 'full')}
                className={`rounded-full px-4 py-2.5 text-sm ${copiedSection === 'full' ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' : 'border-slate-700 text-slate-400 hover:text-white'}`}
                data-testid="copy-btn">
                {copiedSection === 'full' ? <><Check className="w-3.5 h-3.5 mr-1.5" />Copied</> : <><Copy className="w-3.5 h-3.5 mr-1.5" />Copy</>}
              </Button>
            </div>

            {/* Story Content — Scene by Scene */}
            <div className={`rounded-2xl border overflow-hidden ${
              bedtimeMode ? 'bg-[#0D1117] border-slate-800/50' : 'bg-slate-800/40 border-slate-700/50'
            }`} data-testid="story-scenes">
              {story.scenes?.length > 0 ? (
                <div className="divide-y divide-slate-800/50">
                  {story.scenes.map((scene, idx) => (
                    <div
                      key={idx}
                      ref={el => sceneRefs.current[idx] = el}
                      className={`p-4 sm:p-5 transition-all duration-700 ${
                        currentScene === idx
                          ? (bedtimeMode ? 'bg-indigo-500/5 border-l-2 border-l-indigo-400' : 'bg-indigo-500/10 border-l-2 border-l-indigo-500')
                          : 'border-l-2 border-l-transparent'
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
                          <span className="text-[10px] text-indigo-400 animate-pulse ml-auto flex items-center gap-1">
                            <Volume2 className="w-2.5 h-2.5" /> Speaking...
                          </span>
                        )}
                      </div>
                      <p className={`leading-relaxed ${
                        bedtimeMode ? 'text-slate-200 text-lg sm:text-xl font-light' : 'text-slate-300 text-sm sm:text-base'
                      }`}>
                        {stripMarkers(scene.text)}
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
              ) : story.script ? (
                <div className="p-5">
                  <pre className={`whitespace-pre-wrap font-sans leading-relaxed ${
                    bedtimeMode ? 'text-slate-200 text-lg' : 'text-slate-300 text-sm'
                  }`}>
                    {story.script}
                  </pre>
                </div>
              ) : null}
            </div>

            {/* Voice Notes + SFX (hidden in bedtime mode) */}
            {!bedtimeMode && (story.voice_notes?.length > 0 || story.sfx_cues?.length > 0) && (
              <div className="grid sm:grid-cols-2 gap-4 mt-4">
                {story.voice_notes?.length > 0 && (
                  <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-4" data-testid="voice-notes">
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
                  <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-4" data-testid="sfx-cues">
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

            {/* ── Remix Variants (instant, no page reload) ── */}
            <div className="mt-5" data-testid="remix-variants">
              <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-2 text-center">Instant Remix</p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {REMIX_VARIANTS.map(v => {
                  const Icon = v.icon;
                  return (
                    <button key={v.id} onClick={() => handleGenerate(v.id)} disabled={generating}
                      className="flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-slate-800/50 border border-slate-700/50 text-slate-300 hover:text-white hover:border-slate-600 transition-all disabled:opacity-50 text-xs font-medium"
                      data-testid={`remix-${v.id}`}>
                      {generating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Icon className="w-3.5 h-3.5" />} {v.label}
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
            <div className="flex justify-center mt-5">
              <Button variant="outline" onClick={() => { setStory(null); stop(); setBedtimeMode(false); }}
                className="rounded-full border-slate-700 text-slate-400 hover:text-white" data-testid="new-story-btn">
                <RotateCcw className="w-3.5 h-3.5 mr-1.5" /> New Story
              </Button>
            </div>
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
      </div>
    </div>
  );
}
