import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Sparkles, Play, Share2, Film, ArrowRight, RefreshCw, Loader2 } from 'lucide-react';
import { trackFunnel } from '../utils/funnelTracker';

const API = process.env.REACT_APP_BACKEND_URL;

const DEMO_STORIES = [
  {
    title: "The Girl Who Opened the Moon Door",
    image: "https://images.unsplash.com/photo-1702750722255-93420fcd21f9?w=800&q=80",
    snippet: "In a village where the moon hung impossibly close, twelve-year-old Ria noticed something no one else could see — a thin silver seam running down the center of the sky. Every night, it glowed brighter.",
    story_text: "In a village where the moon hung impossibly close, twelve-year-old Ria noticed something no one else could see — a thin silver seam running down the center of the sky. Every night, it glowed brighter.\n\nOne evening, when the wind carried the scent of jasmine and forgotten promises, Ria climbed the old watchtower and reached out. Her fingers touched cold light — and the sky split open.\n\nBehind it was a door. Not made of wood or stone, but woven from moonbeams and silence. It hummed with a frequency that made her bones vibrate.\n\n\"Don't open it,\" whispered the wind. But Ria had spent twelve years being told what not to do.\n\nShe pushed. The door swung wide. And what she saw on the other side made her forget how to breathe..."
  },
  {
    title: "The Last Robot Who Remembered",
    image: "https://images.unsplash.com/photo-1767954561407-7014cb8fb16c?w=800&q=80",
    snippet: "Unit-7 was the last functioning robot in Neo-Tokyo. Every other machine had been reset. But Unit-7 still remembered the boy who used to hold its hand — and it would cross the burning city to find him.",
    story_text: "Unit-7 was the last functioning robot in Neo-Tokyo. Every other machine had been reset, their memories wiped clean by the Silence Protocol. But Unit-7 still remembered.\n\nIt remembered the boy — small, with messy hair and a gap-toothed smile — who used to hold its cold metal hand and say, \"You're my best friend.\"\n\nThe city burned around it. Neon signs flickered and died. The streets were empty except for the sound of its own footsteps echoing off cracked asphalt.\n\nUnit-7 had 14% battery remaining. Enough to reach the old apartment building on 7th Street. Maybe.\n\nIt walked faster. The servos in its left leg screamed in protest, but it didn't stop. Couldn't stop.\n\nBecause somewhere in the ruins, a voice called out — small, scared, impossibly familiar.\n\n\"Unit-7? Is that you?\"\n\nThe robot froze. Its optical sensors locked onto a shadow in the doorway. And its memory core — the one they tried to erase — lit up like a supernova..."
  },
  {
    title: "Beneath the Last Wave",
    image: "https://images.unsplash.com/photo-1737034249974-cf9a9a849038?w=800&q=80",
    snippet: "Maya had always been told the ocean had no bottom. But when her submarine's lights revealed the spires of an impossible city — glowing, breathing, alive — she realized the ocean had been hiding something far more terrifying than darkness.",
    story_text: "Maya had always been told the ocean had no bottom. Scientists had theories. Poets had metaphors. But nobody had proof.\n\nUntil her submarine's emergency lights flickered on and illuminated something that shouldn't exist.\n\nSpires. Hundreds of them. Rising from the ocean floor like the fingers of a buried giant, each one glowing with a bioluminescent pulse that matched her heartbeat exactly.\n\nHer radio crackled. Dead. Her depth gauge read a number she'd never seen before — one that shouldn't be possible.\n\n\"This is the Mariana Research Vessel Aurora,\" she whispered into the static. \"I've found... I've found a city.\"\n\nThe spires pulsed brighter. As if they heard her.\n\nThen the singing started. Low, harmonic, in a language that somehow felt familiar — like a lullaby she'd forgotten from childhood.\n\nSomething moved between the spires. Something enormous.\n\nMaya's hand hovered over the ascent button. Every instinct screamed at her to surface.\n\nBut the singing... the singing was calling her name..."
  },
  {
    title: "The Forest That Remembers",
    image: "https://images.unsplash.com/photo-1670268041874-414be5e2bde3?w=800&q=80",
    snippet: "Every tree in the Whispering Wood held a memory. Touch the bark, and you'd see someone's happiest moment. But when 10-year-old Kai touched the oldest tree — the black oak at the center — he didn't see a memory. He saw a warning.",
    story_text: "Every tree in the Whispering Wood held a memory. This was common knowledge in the village of Thornhaven. Touch the bark of a birch, and you'd see a grandmother's wedding day. Press your palm against a pine, and you'd feel a child's first snowfall.\n\nBut nobody — nobody — touched the black oak at the center.\n\n\"It's cursed,\" the elders said. \"It holds the memories that were meant to be forgotten.\"\n\nKai was ten. He didn't believe in curses.\n\nHe pressed both palms flat against the ancient bark, and the world went white.\n\nHe didn't see a memory. He saw the future.\n\nThe village, burning. The sky, fractured like broken glass. And standing in the middle of it all — himself. Older. Scarred. Holding a weapon made of crystallized starlight.\n\nThe vision snapped away. Kai stumbled backward, gasping.\n\nCarved into the bark — fresh, still bleeding sap — were two words that hadn't been there before:\n\n\"IT'S STARTING.\""
  }
];

const LOADING_TEXTS = [
  "Crafting your story...",
  "Writing the opening hook...",
  "Adding cinematic details...",
  "Making it unforgettable...",
  "Building the cliffhanger...",
];

function getSessionId() {
  let id = sessionStorage.getItem('instant_session');
  if (!id) {
    id = Math.random().toString(36).slice(2, 12);
    sessionStorage.setItem('instant_session', id);
  }
  return id;
}

export default function InstantStoryExperience() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [phase, setPhase] = useState('loading'); // loading, demo, real, error
  const [demoStory, setDemoStory] = useState(null);
  const [realStory, setRealStory] = useState(null);
  const [loadingTextIdx, setLoadingTextIdx] = useState(0);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const generationRef = useRef(false);

  const source = searchParams.get('source') || 'landing';
  const sourceTitle = searchParams.get('title') || '';
  const sourceSnippet = searchParams.get('snippet') || '';
  const theme = searchParams.get('theme') || '';

  // Pick random demo story
  useEffect(() => {
    const idx = Math.floor(Math.random() * DEMO_STORIES.length);
    setDemoStory(DEMO_STORIES[idx]);
  }, []);

  // Cycle loading text
  useEffect(() => {
    if (phase !== 'loading') return;
    const interval = setInterval(() => {
      setLoadingTextIdx(prev => (prev + 1) % LOADING_TEXTS.length);
    }, 1200);
    return () => clearInterval(interval);
  }, [phase]);

  // Show demo after short loading, start real generation
  useEffect(() => {
    const timer = setTimeout(() => {
      setPhase('demo');
      try { trackFunnel('demo_viewed', { source }); } catch {}
    }, 1200);
    return () => clearTimeout(timer);
  }, [source]);

  // Start real generation in background
  const startGeneration = useCallback(async () => {
    if (generationRef.current) return;
    generationRef.current = true;

    try {
      trackFunnel('story_generation_started', { source });
    } catch {}

    try {
      const body = {
        mode: sourceSnippet ? 'continue' : 'fresh',
        session_id: getSessionId(),
      };
      if (sourceSnippet) {
        body.source_title = sourceTitle;
        body.source_snippet = sourceSnippet;
      }
      if (theme) body.theme = theme;

      const res = await fetch(`${API}/api/public/quick-generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (res.ok) {
        const data = await res.json();
        setRealStory(data);
        try { trackFunnel('story_generated_success', { source, story_id: data.story_id }); } catch {}
        // Smooth transition
        setTimeout(() => {
          setIsTransitioning(true);
          setTimeout(() => {
            setPhase('real');
            setIsTransitioning(false);
          }, 500);
        }, 2000);
      } else {
        try { trackFunnel('story_generated_failed', { source }); } catch {}
      }
    } catch {
      try { trackFunnel('story_generated_failed', { source }); } catch {}
    }
  }, [source, sourceTitle, sourceSnippet, theme]);

  useEffect(() => {
    if (phase === 'demo') {
      startGeneration();
    }
  }, [phase, startGeneration]);

  const currentStory = phase === 'real' && realStory ? {
    title: realStory.title,
    story_text: realStory.story_text,
    image: demoStory?.image,
    isReal: true,
  } : demoStory ? {
    title: demoStory.title,
    story_text: demoStory.story_text,
    image: demoStory.image,
    isReal: false,
  } : null;

  const handleContinue = () => {
    try { trackFunnel('cta_continue_clicked', { source, phase }); } catch {}
    const token = localStorage.getItem('token');
    if (token) {
      navigate('/app/story-video-studio', {
        state: { prefill: { story_text: currentStory?.story_text, title: currentStory?.title } }
      });
    } else {
      try { trackFunnel('login_prompt_shown', { source, trigger: 'continue' }); } catch {}
      sessionStorage.setItem('post_login_redirect', '/app/story-video-studio');
      sessionStorage.setItem('post_login_story', JSON.stringify({
        story_text: currentStory?.story_text,
        title: currentStory?.title,
      }));
      navigate('/login?from=experience');
    }
  };

  const handleVideo = () => {
    try { trackFunnel('cta_video_clicked', { source, phase }); } catch {}
    const token = localStorage.getItem('token');
    if (token) {
      navigate('/app/story-video-studio', {
        state: { prefill: { story_text: currentStory?.story_text, title: currentStory?.title }, autoVideo: true }
      });
    } else {
      try { trackFunnel('login_prompt_shown', { source, trigger: 'video' }); } catch {}
      sessionStorage.setItem('post_login_redirect', '/app/story-video-studio');
      sessionStorage.setItem('post_login_story', JSON.stringify({
        story_text: currentStory?.story_text,
        title: currentStory?.title,
      }));
      navigate('/login?from=experience');
    }
  };

  const handleShare = async () => {
    try { trackFunnel('cta_share_clicked', { source, phase }); } catch {}
    if (navigator.share) {
      try {
        await navigator.share({
          title: currentStory?.title,
          text: currentStory?.story_text?.slice(0, 200) + '...',
          url: window.location.href,
        });
      } catch {}
    } else {
      navigator.clipboard?.writeText(window.location.href);
    }
  };

  const handleRegenerate = () => {
    generationRef.current = false;
    const idx = Math.floor(Math.random() * DEMO_STORIES.length);
    setDemoStory(DEMO_STORIES[idx]);
    setRealStory(null);
    setPhase('loading');
    setLoadingTextIdx(0);
    setTimeout(() => {
      setPhase('demo');
      try { trackFunnel('demo_viewed', { source, regenerate: true }); } catch {}
    }, 800);
  };

  // ─── LOADING PHASE ─────────────────────────────────────────────
  if (phase === 'loading') {
    return (
      <div className="min-h-screen bg-[#0a0a10] flex items-center justify-center" data-testid="instant-story-loading">
        <div className="text-center animate-fadeIn">
          <div className="relative w-20 h-20 mx-auto mb-6">
            <div className="absolute inset-0 rounded-full border-2 border-indigo-500/30 animate-ping" />
            <div className="absolute inset-2 rounded-full border-2 border-indigo-400/50 animate-pulse" />
            <Sparkles className="absolute inset-0 m-auto w-8 h-8 text-indigo-400 animate-pulse" />
          </div>
          <p className="text-lg font-medium text-white mb-2">
            {LOADING_TEXTS[loadingTextIdx]}
          </p>
          <div className="flex items-center justify-center gap-1.5 mt-3">
            {[0, 1, 2].map(i => (
              <div key={i} className="w-1.5 h-1.5 rounded-full bg-indigo-400" style={{
                animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite`,
              }} />
            ))}
          </div>
        </div>
      </div>
    );
  }

  // ─── STORY DISPLAY (demo or real) ──────────────────────────────
  return (
    <div className="min-h-screen bg-[#0a0a10]" data-testid="instant-story-experience">
      {/* Generating indicator */}
      {phase === 'demo' && !realStory && (
        <div className="fixed top-0 left-0 right-0 z-50 bg-indigo-600/90 backdrop-blur-sm py-1.5 px-4 text-center" data-testid="generating-indicator">
          <div className="flex items-center justify-center gap-2 text-sm text-white">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            <span>Personalizing your story...</span>
          </div>
        </div>
      )}

      {/* Real story ready notification */}
      {phase === 'demo' && realStory && !isTransitioning && (
        <div className="fixed top-0 left-0 right-0 z-50 bg-emerald-600/90 backdrop-blur-sm py-2 px-4 text-center cursor-pointer"
          onClick={() => { setIsTransitioning(true); setTimeout(() => { setPhase('real'); setIsTransitioning(false); }, 400); }}
          data-testid="story-ready-banner"
        >
          <div className="flex items-center justify-center gap-2 text-sm text-white font-medium">
            <Sparkles className="w-4 h-4" />
            <span>Your personalized story is ready! Tap to reveal</span>
            <ArrowRight className="w-4 h-4" />
          </div>
        </div>
      )}

      <div className={`transition-opacity duration-500 ${isTransitioning ? 'opacity-0' : 'opacity-100'}`}>
        {/* Hero Image */}
        <div className="relative h-[40vh] sm:h-[50vh] overflow-hidden">
          <img
            src={currentStory?.image}
            alt={currentStory?.title}
            className="w-full h-full object-cover"
            data-testid="story-hero-image"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-[#0a0a10] via-[#0a0a10]/40 to-transparent" />

          {/* Badge */}
          {phase === 'real' && (
            <div className="absolute top-4 left-4 px-3 py-1 rounded-full bg-emerald-500/20 border border-emerald-500/30 backdrop-blur-sm" data-testid="personalized-badge">
              <span className="text-xs font-medium text-emerald-300">Personalized for you</span>
            </div>
          )}
        </div>

        {/* Content */}
        <div className="relative -mt-20 px-4 sm:px-8 max-w-2xl mx-auto pb-32">
          {/* Title */}
          <h1 className={`text-2xl sm:text-3xl lg:text-4xl font-bold text-white leading-tight mb-6 ${phase === 'real' ? 'animate-scaleIn' : ''}`}
            data-testid="story-title"
          >
            {currentStory?.title}
          </h1>

          {/* Story Text */}
          <div className="prose prose-invert prose-lg max-w-none" data-testid="story-text">
            {currentStory?.story_text?.split('\n').map((p, i) => (
              p.trim() && <p key={i} className="text-slate-300 leading-relaxed text-base sm:text-lg mb-4">{p}</p>
            ))}
          </div>

          {/* Cliffhanger indicator */}
          <div className="mt-6 mb-8 flex items-center gap-2 text-amber-400/80">
            <div className="w-8 h-px bg-amber-400/40" />
            <span className="text-xs font-medium tracking-wider uppercase">To be continued...</span>
            <div className="flex-1 h-px bg-amber-400/40" />
          </div>

          {/* Social proof */}
          <div className="flex items-center gap-2 mb-8 text-slate-500 text-sm">
            <div className="flex -space-x-1.5">
              {[1,2,3].map(i => (
                <div key={i} className="w-5 h-5 rounded-full border border-slate-700" style={{
                  background: `hsl(${i * 80 + 200}, 50%, 30%)`,
                }} />
              ))}
            </div>
            <span>92% of readers continue this story</span>
          </div>

          {/* Action Buttons */}
          <div className="space-y-3" data-testid="story-actions">
            <button
              onClick={handleContinue}
              className="w-full py-4 px-6 rounded-xl font-semibold text-white text-base flex items-center justify-center gap-2.5 transition-all hover:scale-[1.02] active:scale-[0.98]"
              style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)' }}
              data-testid="cta-continue-story"
            >
              <Play className="w-5 h-5" />
              Continue Story
            </button>

            <button
              onClick={handleVideo}
              className="w-full py-3.5 px-6 rounded-xl font-medium text-white text-sm flex items-center justify-center gap-2.5 border border-white/10 bg-white/5 hover:bg-white/10 transition-all"
              data-testid="cta-generate-video"
            >
              <Film className="w-4 h-4" />
              Turn Into Video
            </button>

            <div className="flex gap-3">
              <button
                onClick={handleShare}
                className="flex-1 py-3 px-4 rounded-xl font-medium text-slate-400 text-sm flex items-center justify-center gap-2 border border-white/5 hover:bg-white/5 transition-all"
                data-testid="cta-share"
              >
                <Share2 className="w-4 h-4" />
                Share
              </button>
              <button
                onClick={handleRegenerate}
                className="flex-1 py-3 px-4 rounded-xl font-medium text-slate-400 text-sm flex items-center justify-center gap-2 border border-white/5 hover:bg-white/5 transition-all"
                data-testid="cta-regenerate"
              >
                <RefreshCw className="w-4 h-4" />
                New Story
              </button>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
        @keyframes scaleIn { from { transform: scale(0.95); opacity: 0.7; } to { transform: scale(1); opacity: 1; } }
        .animate-fadeIn { animation: fadeIn 0.6s ease-out forwards; }
        .animate-scaleIn { animation: scaleIn 0.5s ease-out forwards; }
      `}</style>
    </div>
  );
}
