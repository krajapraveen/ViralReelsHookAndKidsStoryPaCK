import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCredits } from '../contexts/CreditContext';
import axios from 'axios';
import {
  Play, ChevronRight, Sparkles, Zap, Users,
  BookOpen, ArrowRight, Film, Star, Clock, Eye,
  ChevronDown, Flame, Target, Trophy,
  Search, MessageSquare, Wand2, Rocket
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const api = () => axios.create({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

/* ── Truth-based social proof: never shows zero ── */
function getProofLabel(count) {
  if (count >= 10) return { text: 'Trending', Icon: Flame, bg: 'bg-amber-500/20', fg: 'text-amber-400' };
  if (count > 0)   return { text: 'Early story', Icon: Zap, bg: 'bg-violet-500/20', fg: 'text-violet-400' };
  return { text: 'Just dropped', Icon: Sparkles, bg: 'bg-emerald-500/20', fg: 'text-emerald-400' };
}

/* ── Click Psychology: CTA variants for A/B testing ── */
const CTA_VARIANTS = [
  'See What Happens Next',
  'Continue This Story',
  'What Happens Next?',
];

/* ── Urgency messages: truth-based, no faking ── */
const URGENCY_ACTIVE = [
  'Someone just continued this',
  'This story is gaining momentum',
  'Others are watching this',
];
const URGENCY_FIRST = [
  'Your turn to continue',
  "This story isn\u2019t finished",
  'Be the one who writes what\u2019s next',
];

/* ── Hook formatter: 1 line, incomplete thought, curiosity-driven ── */
function formatHook(text) {
  if (!text) return 'A story waiting to unfold\u2026';
  const clean = text.replace(/\n/g, ' ').trim();
  if (clean.length <= 65) return clean.endsWith('...') || clean.endsWith('\u2026') ? clean : clean;
  const cut = clean.substring(0, 65).lastIndexOf(' ');
  return clean.substring(0, cut > 20 ? cut : 60) + '\u2026';
}

const SCROLL_HOOKS = [
  "But this story doesn\u2019t end here\u2026",
  "What happens next is up to you\u2026",
  "The next chapter is waiting\u2026",
  "This world is still being written\u2026",
];

export default function Dashboard() {
  const { credits } = useCredits();
  const navigate = useNavigate();
  const [storyFeed, setStoryFeed] = useState(null);
  const [resumeStory, setResumeStory] = useState(null);
  const [engagement, setEngagement] = useState(null);
  const [promptText, setPromptText] = useState('');
  const [showMoreTools, setShowMoreTools] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchFeed = useCallback(async () => {
    try {
      const [feedRes, engRes] = await Promise.all([
        axios.get(`${API}/api/engagement/story-feed`),
        api().get(`${API}/api/engagement/dashboard`).catch(() => null),
      ]);
      setStoryFeed(feedRes.data);
      if (engRes?.data) setEngagement(engRes.data);
    } catch (e) { console.error('Feed load failed:', e); }
    setLoading(false);
  }, []);

  const fetchResume = useCallback(async () => {
    try {
      const res = await api().get(`${API}/api/story-engine/user-jobs`);
      if (res.data?.jobs?.length > 0) setResumeStory(res.data.jobs[0]);
    } catch {}
  }, []);

  useEffect(() => { fetchFeed(); fetchResume(); }, [fetchFeed, fetchResume]);

  const handlePrompt = () => {
    if (!promptText.trim()) return;
    navigate('/app/story-video-studio', { state: { prefill: promptText } });
  };

  const hero = storyFeed?.hero;
  const trending = storyFeed?.trending || [];
  const characters = storyFeed?.characters || [];
  const liveStats = storyFeed?.live_stats || {};
  const challenge = engagement?.daily_challenge;
  const streak = engagement?.streak;

  /* Build hero pool for rotation: main hero + top trending */
  const heroPool = [];
  if (hero) heroPool.push(hero);
  trending.slice(0, 4).forEach(s => {
    if (!heroPool.find(h => h.job_id === s.job_id)) {
      heroPool.push({ ...s, hook_text: s.hook_text || s.title });
    }
  });

  if (loading) {
    return (
      <div className="min-h-screen bg-[#06060e] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#06060e] text-white" data-testid="story-dashboard">
      <style>{`
        @keyframes shimmer-glow {
          0%,100%{box-shadow:0 0 8px rgba(245,158,11,.15)}
          50%{box-shadow:0 0 22px rgba(245,158,11,.4)}
        }
        @keyframes hero-fade{from{opacity:0}to{opacity:1}}
        .shimmer-cta{animation:shimmer-glow 2.5s ease-in-out infinite}
        .hero-fade{animation:hero-fade .6s ease-out}
      `}</style>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        <HeroSection heroes={heroPool} navigate={navigate} />

        {/* Universal Prompt Bar */}
        <div className="mt-6 mb-8" data-testid="universal-prompt">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
            <input
              value={promptText}
              onChange={e => setPromptText(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handlePrompt()}
              placeholder="Type anything... A fox in a dark forest, a robot learning emotions, a mystery door..."
              className="w-full h-14 pl-12 pr-32 bg-slate-900/60 border border-slate-800/60 rounded-2xl text-white placeholder-slate-500 text-sm focus:outline-none focus:border-amber-500/40 transition-colors"
              data-testid="universal-prompt-input"
            />
            <button
              onClick={handlePrompt}
              className="absolute right-2 top-1/2 -translate-y-1/2 h-10 px-5 bg-gradient-to-r from-amber-600 to-rose-600 rounded-xl text-white text-sm font-bold flex items-center gap-2 hover:opacity-90 transition-opacity shimmer-cta"
              data-testid="universal-prompt-btn"
            >
              <Wand2 className="w-4 h-4" /> Create Story
            </button>
          </div>
          <div className="flex gap-2 mt-2 flex-wrap">
            {['A brave fox...', 'The door opened...', 'She trusted him...', 'The robot refused...'].map(chip => (
              <button key={chip} onClick={() => setPromptText(chip)}
                className="text-xs px-3 py-1.5 rounded-full bg-slate-800/60 text-slate-400 hover:text-white hover:bg-slate-700/60 transition-colors border border-slate-800/40"
              >{chip}</button>
            ))}
          </div>
        </div>

        <LiveStats stats={liveStats} />

        {resumeStory && <ResumeStoryBanner story={resumeStory} navigate={navigate} />}

        <TrendingStories stories={trending} navigate={navigate} />

        <ScrollTrap />

        {characters.length > 0 && <CharacterUniverse characters={characters} navigate={navigate} />}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
          {challenge && <DailyChallenge challenge={challenge} navigate={navigate} />}
          {streak && <StreakCard streak={streak} />}
          <CreditsCard credits={credits} navigate={navigate} />
        </div>

        <MoreTools show={showMoreTools} toggle={() => setShowMoreTools(!showMoreTools)} navigate={navigate} />
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════
   LIVE STATS — Truth-based, never shows zero
   ═══════════════════════════════════════════════════════════ */
function LiveStats({ stats }) {
  const total = stats.total_stories || 0;
  const today = stats.stories_today || 0;
  const conts = stats.total_continuations || 0;

  return (
    <div className="flex items-center justify-center gap-6 mb-8 text-xs text-slate-500 flex-wrap" data-testid="live-stats">
      {total > 0 ? (
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <strong className="text-emerald-400">{total}</strong> stories created
        </span>
      ) : (
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-emerald-400 font-semibold">Stories launching soon</span>
        </span>
      )}

      <span className="w-px h-4 bg-slate-800" />

      {today > 0 ? (
        <span className="flex items-center gap-1.5">
          <Flame className="w-3.5 h-3.5 text-amber-400" />
          <strong className="text-amber-400">{today}</strong> added today
        </span>
      ) : (
        <span className="flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
          <span className="text-amber-400 font-semibold">Fresh stories waiting</span>
        </span>
      )}

      <span className="w-px h-4 bg-slate-800" />

      {conts > 0 ? (
        <span className="flex items-center gap-1.5">
          <Users className="w-3.5 h-3.5 text-violet-400" />
          <strong className="text-violet-400">{conts}</strong> continuations
        </span>
      ) : (
        <span className="flex items-center gap-1.5">
          <Rocket className="w-3.5 h-3.5 text-violet-400" />
          <span className="text-violet-400 font-semibold">Be the first to continue</span>
        </span>
      )}
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════
   HERO SECTION — Rotating carousel with progress dots
   ═══════════════════════════════════════════════════════════ */
function HeroSection({ heroes, navigate }) {
  const [idx, setIdx] = useState(0);
  const [paused, setPaused] = useState(false);
  const timerRef = useRef(null);
  const count = heroes.length;

  const startTimer = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (count <= 1) return;
    timerRef.current = setInterval(() => setIdx(p => (p + 1) % count), 6000);
  }, [count]);

  useEffect(() => {
    if (!paused) startTimer();
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [paused, startTimer]);

  const goTo = (i) => {
    setIdx(i);
    if (timerRef.current) clearInterval(timerRef.current);
    if (!paused) startTimer();
  };

  if (!count) {
    return (
      <div className="relative rounded-2xl overflow-hidden bg-gradient-to-br from-slate-900 via-[#0c0c1a] to-slate-900 border border-slate-800/40 p-8 md:p-12" data-testid="hero-section">
        <div className="max-w-2xl">
          <p className="text-xs font-bold text-amber-400 tracking-widest mb-3">CREATE YOUR STORY</p>
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black text-white leading-tight mb-4">
            Create your own animated story in <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-rose-400">30 seconds</span>
          </h1>
          <p className="text-base text-slate-400 mb-6 max-w-lg">Continue viral stories. Build characters. Make episodes instantly.</p>
          <button onClick={() => navigate('/app/story-video-studio')}
            className="h-12 px-8 bg-gradient-to-r from-amber-500 to-rose-500 rounded-xl text-white font-bold text-sm flex items-center gap-2 hover:opacity-90 transition-opacity shadow-lg shadow-amber-500/20 shimmer-cta"
            data-testid="hero-create-btn">
            <Play className="w-5 h-5" /> Create a Story
          </button>
        </div>
      </div>
    );
  }

  const current = heroes[idx];
  const hookText = current.hook_text || current.title || 'A story waiting to be continued\u2026';

  return (
    <div className="relative rounded-2xl overflow-hidden border border-slate-800/40 group"
      data-testid="hero-section"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}>

      {/* Background: video or thumbnail */}
      <div className="absolute inset-0 z-0 hero-fade" key={`hero-bg-${idx}`}>
        {current.output_url ? (
          <video src={current.output_url} className="w-full h-full object-cover opacity-40"
            autoPlay muted loop playsInline onError={e => { e.target.style.display = 'none'; }} />
        ) : current.thumbnail_url ? (
          <img src={current.thumbnail_url} alt="" className="w-full h-full object-cover opacity-30" />
        ) : null}
        <div className="absolute inset-0 bg-gradient-to-r from-[#06060e] via-[#06060e]/80 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#06060e] via-transparent to-[#06060e]/40" />
      </div>

      {/* Content */}
      <div className="relative z-10 p-8 md:p-12 min-h-[300px] flex flex-col justify-center hero-fade" key={`hero-txt-${idx}`}>
        <p className="text-xs font-bold text-amber-400 tracking-widest mb-3">
          {(current.remix_count || 0) > 0 ? 'TRENDING NOW' : 'CONTINUE THIS STORY'}
        </p>
        <h1 className="text-2xl sm:text-3xl lg:text-4xl font-black text-white leading-tight mb-3 max-w-2xl">
          &ldquo;{hookText}&rdquo;
        </h1>
        <p className="text-sm text-slate-400 mb-6">{current.title}</p>
        <div className="flex gap-3 flex-wrap">
          <button onClick={() => {
              localStorage.setItem('remix_data', JSON.stringify({
                prompt: current.story_text || current.hook_text || '',
                timestamp: Date.now(), source_tool: 'dashboard-continue',
                remixFrom: { parent_video_id: current.job_id, title: current.title }
              }));
              navigate('/app/story-video-studio');
            }}
            className="h-12 px-8 bg-gradient-to-r from-amber-500 to-rose-500 rounded-xl text-white font-bold text-sm flex items-center gap-2 hover:opacity-90 transition-opacity shadow-lg shadow-amber-500/20 shimmer-cta"
            data-testid="hero-continue-btn">
            <Play className="w-5 h-5 fill-white" /> Continue This Story
          </button>
          <button onClick={() => navigate('/app/story-video-studio')}
            className="h-12 px-8 bg-slate-800/80 border border-slate-700/60 rounded-xl text-white font-bold text-sm flex items-center gap-2 hover:bg-slate-700/80 transition-colors"
            data-testid="hero-create-btn">
            <Sparkles className="w-5 h-5" /> Create Your Version
          </button>
        </div>
      </div>

      {/* Progress dots */}
      {count > 1 && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 flex items-center gap-2" data-testid="hero-dots">
          {heroes.map((_, i) => (
            <button key={i} onClick={() => goTo(i)}
              className={`rounded-full transition-all duration-300 ${i === idx ? 'w-6 h-2 bg-amber-400' : 'w-2 h-2 bg-slate-600 hover:bg-slate-400'}`}
              aria-label={`Go to story ${i + 1}`} />
          ))}
        </div>
      )}
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════
   RESUME STORY BANNER
   ═══════════════════════════════════════════════════════════ */
function ResumeStoryBanner({ story, navigate }) {
  return (
    <div className="mb-8 bg-gradient-to-r from-violet-500/[0.07] to-rose-500/[0.07] border border-violet-500/20 rounded-xl p-4 flex items-center justify-between cursor-pointer hover:border-violet-500/40 transition-colors"
      onClick={() => navigate('/app/story-video-studio', { state: { resumeJob: story.job_id } })}
      data-testid="resume-story-banner">
      <div className="flex items-center gap-4">
        {story.thumbnail_url && <img src={story.thumbnail_url} alt="" className="w-14 h-14 rounded-lg object-cover" />}
        <div>
          <p className="text-xs font-bold text-violet-400 tracking-wider">CONTINUE YOUR STORY</p>
          <p className="text-sm font-bold text-white">{story.title}</p>
          <p className="text-xs text-slate-500">Your episode is waiting&hellip;</p>
        </div>
      </div>
      <button className="h-10 px-5 bg-violet-600 hover:bg-violet-500 rounded-xl text-white text-xs font-bold flex items-center gap-2 transition-colors">
        <Play className="w-4 h-4 fill-white" /> Continue Episode
      </button>
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════
   TRENDING STORIES + STORY CARD
   ═══════════════════════════════════════════════════════════ */
function TrendingStories({ stories, navigate }) {
  if (!stories.length) return null;
  return (
    <section data-testid="trending-stories">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-black text-white flex items-center gap-2">
          <Flame className="w-5 h-5 text-amber-400" /> Trending Stories
        </h2>
        <button onClick={() => navigate('/app/explore')} className="text-xs text-slate-500 hover:text-white flex items-center gap-1 transition-colors">
          View All <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {stories.slice(0, 8).map((story, idx) => (
          <StoryCard key={story.job_id} story={story} navigate={navigate} index={idx} />
        ))}
      </div>
    </section>
  );
}

function StoryCard({ story, navigate, index = 0 }) {
  const [hovered, setHovered] = useState(false);
  const proof = getProofLabel(story.remix_count || 0);
  const ProofIcon = proof.Icon;
  const isActive = (story.remix_count || 0) > 0;

  const hook = formatHook(story.hook_text || story.title);
  const ctaText = CTA_VARIANTS[index % CTA_VARIANTS.length];
  const urgencyPool = isActive ? URGENCY_ACTIVE : URGENCY_FIRST;
  const urgency = urgencyPool[index % urgencyPool.length];

  const handleClick = () => {
    axios.post(`${API}/api/engagement/card-click`, {
      story_id: story.job_id, cta_variant: ctaText, source: 'dashboard'
    }).catch(() => {});
    localStorage.setItem('remix_data', JSON.stringify({
      prompt: story.hook_text || story.title || '',
      timestamp: Date.now(), source_tool: 'dashboard-continue',
      remixFrom: { parent_video_id: story.job_id, title: story.title }
    }));
    navigate('/app/story-video-studio');
  };

  return (
    <div
      className="group relative rounded-xl overflow-hidden cursor-pointer transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-amber-500/10 border border-slate-800/40 hover:border-amber-500/30"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={handleClick}
      data-testid="story-card"
    >
      {/* Full-bleed cinematic thumbnail */}
      <div className="aspect-[4/5] relative overflow-hidden bg-slate-900">
        {story.thumbnail_url ? (
          <img
            src={story.thumbnail_url}
            alt={story.title}
            className={`w-full h-full object-cover transition-all duration-700 ${
              hovered ? 'scale-110 brightness-110' : 'scale-100 brightness-[0.85]'
            }`}
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-slate-800 to-slate-900 flex items-center justify-center">
            <Film className="w-10 h-10 text-slate-700" />
          </div>
        )}

        {/* Dark gradient from bottom for text */}
        <div className="absolute inset-0 bg-gradient-to-t from-black via-black/40 to-transparent" />

        {/* Badge — top left */}
        <div className={`absolute top-2.5 left-2.5 flex items-center gap-1 backdrop-blur-md rounded-full px-2.5 py-1 ${proof.bg} ${proof.fg}`}>
          <ProofIcon className="w-3 h-3" />
          <span className="text-[10px] font-bold">{proof.text}</span>
        </div>

        {/* Hover play button — center */}
        <div className={`absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 transition-all duration-300 ${
          hovered ? 'opacity-100 scale-100' : 'opacity-0 scale-75'
        }`}>
          <div className="w-14 h-14 rounded-full bg-amber-500/90 flex items-center justify-center shadow-xl shadow-amber-500/30 shimmer-cta">
            <Play className="w-7 h-7 text-white fill-white ml-0.5" />
          </div>
        </div>

        {/* Content overlay — bottom */}
        <div className="absolute bottom-0 left-0 right-0 p-3.5 space-y-1.5">
          {/* HOOK — biggest element, bold */}
          <p className="text-sm font-black text-white leading-snug line-clamp-2" data-testid="story-hook">
            {hook}
          </p>

          {/* Urgency — subtle truth-based message */}
          <p className="text-[10px] text-slate-300/60 font-medium" data-testid="story-urgency">
            {urgency}
          </p>

          {/* CTA — always visible, transforms on hover */}
          <button
            className={`w-full py-2 rounded-lg text-[11px] font-bold flex items-center justify-center gap-1.5 transition-all duration-300 ${
              hovered
                ? 'bg-amber-500 text-black shadow-lg shadow-amber-500/30'
                : 'bg-white/10 backdrop-blur-sm text-white border border-white/10'
            }`}
            data-testid="story-cta"
          >
            <Play className={`w-3.5 h-3.5 ${hovered ? 'fill-black' : 'fill-white'}`} />
            {ctaText}
          </button>
        </div>
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════
   SCROLL TRAP — Appears on scroll with story-specific hook
   ═══════════════════════════════════════════════════════════ */
function ScrollTrap() {
  const [visible, setVisible] = useState(false);
  const ref = useRef(null);
  const [hookIdx] = useState(() => Math.floor(Math.random() * SCROLL_HOOKS.length));

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) setVisible(true);
    }, { threshold: 0.5 });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <div ref={ref} data-testid="scroll-trap"
      className={`my-10 py-6 text-center transition-all duration-700 ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
      <p className="text-lg font-black text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-rose-400">
        {SCROLL_HOOKS[hookIdx]}
      </p>
      <div className="mt-3 flex justify-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-500/60 animate-pulse" />
        <span className="w-1.5 h-1.5 rounded-full bg-rose-500/60 animate-pulse" style={{ animationDelay: '0.2s' }} />
        <span className="w-1.5 h-1.5 rounded-full bg-amber-500/60 animate-pulse" style={{ animationDelay: '0.4s' }} />
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════
   CHARACTER UNIVERSE
   ═══════════════════════════════════════════════════════════ */
function CharacterUniverse({ characters, navigate }) {
  return (
    <section className="mt-8" data-testid="character-universe">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-black text-white flex items-center gap-2">
          <Star className="w-5 h-5 text-violet-400" /> Popular Characters
        </h2>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {characters.map(char => (
          <div key={char.character_id || char.name}
            className="bg-slate-900/60 border border-slate-800/40 rounded-xl p-4 text-center hover:border-violet-500/30 cursor-pointer transition-colors"
            onClick={() => navigate('/app/character-studio')} data-testid="character-card">
            <div className="w-14 h-14 mx-auto rounded-full bg-gradient-to-br from-violet-600 to-rose-600 flex items-center justify-center mb-2 text-xl font-black text-white">
              {char.name?.[0] || '?'}
            </div>
            <p className="text-xs font-bold text-white truncate">{char.name}</p>
            <p className="text-[10px] text-slate-500 truncate mt-0.5">{char.description?.slice(0, 40) || 'AI Character'}</p>
            <button className="mt-2 w-full text-[10px] font-bold text-violet-400 hover:text-violet-300 transition-colors">
              Continue with {char.name?.split(' ')[0]}
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}


/* ═══════════════════════════════════════════════════════════
   ENGAGEMENT CARDS
   ═══════════════════════════════════════════════════════════ */
function DailyChallenge({ challenge, navigate }) {
  return (
    <div className="bg-gradient-to-br from-amber-500/[0.06] to-rose-500/[0.06] border border-amber-500/20 rounded-xl p-5" data-testid="daily-challenge">
      <div className="flex items-center gap-2 mb-2">
        <Target className="w-4 h-4 text-amber-400" />
        <p className="text-[10px] font-bold text-amber-400 tracking-wider">DAILY CHALLENGE</p>
      </div>
      <p className="text-sm font-bold text-white mb-1">{challenge.prompt}</p>
      <p className="text-xs text-slate-500 mb-3">Reward: +{challenge.reward} credits</p>
      <button onClick={() => navigate(`/app/${challenge.tool}`)}
        className="w-full h-9 bg-amber-500/10 border border-amber-500/20 rounded-lg text-amber-400 text-xs font-bold hover:bg-amber-500/20 transition-colors">
        Accept Challenge
      </button>
    </div>
  );
}

function StreakCard({ streak }) {
  return (
    <div className="bg-gradient-to-br from-emerald-500/[0.06] to-teal-500/[0.06] border border-emerald-500/20 rounded-xl p-5" data-testid="streak-card">
      <div className="flex items-center gap-2 mb-2">
        <Trophy className="w-4 h-4 text-emerald-400" />
        <p className="text-[10px] font-bold text-emerald-400 tracking-wider">YOUR STREAK</p>
      </div>
      <p className="text-3xl font-black text-white mb-1">{streak.current_streak || 0}</p>
      <p className="text-xs text-slate-500">days creating</p>
      <div className="flex gap-1 mt-3">
        {[1,2,3,4,5,6,7].map(d => (
          <div key={d} className={`flex-1 h-1.5 rounded-full ${d <= (streak.current_streak || 0) ? 'bg-emerald-400' : 'bg-slate-800'}`} />
        ))}
      </div>
    </div>
  );
}

function CreditsCard({ credits, navigate }) {
  return (
    <div className="bg-gradient-to-br from-violet-500/[0.06] to-indigo-500/[0.06] border border-violet-500/20 rounded-xl p-5" data-testid="credits-card">
      <div className="flex items-center gap-2 mb-2">
        <Zap className="w-4 h-4 text-violet-400" />
        <p className="text-[10px] font-bold text-violet-400 tracking-wider">CREDITS</p>
      </div>
      <p className="text-3xl font-black text-white mb-1">{credits ?? '...'}</p>
      <p className="text-xs text-slate-500">available credits</p>
      <button onClick={() => navigate('/app/pricing')}
        className="mt-3 w-full h-9 bg-violet-500/10 border border-violet-500/20 rounded-lg text-violet-400 text-xs font-bold hover:bg-violet-500/20 transition-colors">
        Get More Credits
      </button>
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════
   MORE TOOLS (DEMOTED)
   ═══════════════════════════════════════════════════════════ */
const TOOLS = [
  { id: 'story-video-studio', name: 'Story Video', icon: Film, color: 'amber', path: '/app/story-video-studio', primary: true },
  { id: 'story-series', name: 'Story Series', icon: BookOpen, color: 'violet', path: '/app/story-series' },
  { id: 'reels', name: 'Reel Generator', icon: Play, color: 'rose', path: '/app/reels' },
  { id: 'photo-to-comic', name: 'Photo to Comic', icon: Sparkles, color: 'cyan', path: '/app/photo-to-comic' },
  { id: 'comic-storybook', name: 'Comic Storybook', icon: BookOpen, color: 'emerald', path: '/app/comic-storybook-builder' },
  { id: 'bedtime-story', name: 'Bedtime Stories', icon: Star, color: 'purple', path: '/app/bedtime-story-builder' },
  { id: 'gif-maker', name: 'Reaction GIF', icon: Zap, color: 'pink', path: '/app/gif-maker' },
  { id: 'coloring-book', name: 'Coloring Book', icon: Wand2, color: 'orange', path: '/app/coloring-book' },
  { id: 'caption-rewriter', name: 'Caption Rewriter', icon: MessageSquare, color: 'teal', path: '/app/caption-rewriter' },
  { id: 'brand-story', name: 'Brand Story', icon: Target, color: 'blue', path: '/app/brand-story-builder' },
];

function MoreTools({ show, toggle, navigate }) {
  return (
    <section className="mt-8" data-testid="more-tools">
      <button onClick={toggle}
        className="flex items-center gap-2 text-sm font-bold text-slate-500 hover:text-white mb-4 transition-colors"
        data-testid="more-tools-toggle">
        <ChevronDown className={`w-4 h-4 transition-transform ${show ? 'rotate-180' : ''}`} />
        {show ? 'Hide Tools' : 'More Creative Tools'}
      </button>
      {show && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 animate-in fade-in duration-300">
          {TOOLS.map(tool => {
            const Icon = tool.icon;
            return (
              <button key={tool.id} onClick={() => navigate(tool.path)}
                className={`p-4 rounded-xl border transition-all duration-200 text-left hover:scale-[1.02] ${
                  tool.primary ? 'bg-amber-500/[0.06] border-amber-500/20 hover:border-amber-500/40'
                    : 'bg-slate-900/60 border-slate-800/40 hover:border-slate-700/60'}`}
                data-testid={`tool-${tool.id}`}>
                <Icon className={`w-5 h-5 text-${tool.color}-400 mb-2`} />
                <p className="text-xs font-bold text-white">{tool.name}</p>
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
}
