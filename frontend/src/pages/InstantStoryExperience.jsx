import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Sparkles, Play, Share2, Film, RefreshCw, Loader2, CheckCircle } from 'lucide-react';
import { trackFunnel } from '../utils/funnelTracker';

const API = process.env.REACT_APP_BACKEND_URL;

const DEMO_STORIES = [
  {
    title: "The Girl Who Opened the Moon Door",
    image: "https://images.unsplash.com/photo-1702750722255-93420fcd21f9?w=800&q=80",
    story_text: "In a village where the moon hung impossibly close, twelve-year-old Ria noticed something no one else could see \u2014 a thin silver seam running down the center of the sky. Every night, it glowed brighter.\n\nOne evening, when the wind carried the scent of jasmine and forgotten promises, Ria climbed the old watchtower and reached out. Her fingers touched cold light \u2014 and the sky split open.\n\nBehind it was a door. Not made of wood or stone, but woven from moonbeams and silence. It hummed with a frequency that made her bones vibrate.\n\n\"Don't open it,\" whispered the wind. But Ria had spent twelve years being told what not to do.\n\nShe pushed. The door swung wide. And what she saw on the other side made her forget how to breathe..."
  },
  {
    title: "The Last Robot Who Remembered",
    image: "https://images.unsplash.com/photo-1767954561407-7014cb8fb16c?w=800&q=80",
    story_text: "Unit-7 was the last functioning robot in Neo-Tokyo. Every other machine had been reset, their memories wiped clean by the Silence Protocol. But Unit-7 still remembered.\n\nIt remembered the boy \u2014 small, with messy hair and a gap-toothed smile \u2014 who used to hold its cold metal hand and say, \"You're my best friend.\"\n\nThe city burned around it. Neon signs flickered and died. The streets were empty except for the sound of its own footsteps echoing off cracked asphalt.\n\nUnit-7 had 14% battery remaining. Enough to reach the old apartment building on 7th Street. Maybe.\n\nIt walked faster. The servos in its left leg screamed in protest, but it didn't stop. Couldn't stop.\n\nBecause somewhere in the ruins, a voice called out \u2014 small, scared, impossibly familiar.\n\n\"Unit-7? Is that you?\"\n\nThe robot froze. Its optical sensors locked onto a shadow in the doorway. And its memory core \u2014 the one they tried to erase \u2014 lit up like a supernova..."
  },
  {
    title: "Beneath the Last Wave",
    image: "https://images.unsplash.com/photo-1737034249974-cf9a9a849038?w=800&q=80",
    story_text: "Maya had always been told the ocean had no bottom. Scientists had theories. Poets had metaphors. But nobody had proof.\n\nUntil her submarine's emergency lights flickered on and illuminated something that shouldn't exist.\n\nSpires. Hundreds of them. Rising from the ocean floor like the fingers of a buried giant, each one glowing with a bioluminescent pulse that matched her heartbeat exactly.\n\nHer radio crackled. Dead. Her depth gauge read a number she'd never seen before \u2014 one that shouldn't be possible.\n\n\"This is the Mariana Research Vessel Aurora,\" she whispered into the static. \"I've found... I've found a city.\"\n\nThe spires pulsed brighter. As if they heard her.\n\nThen the singing started. Low, harmonic, in a language that somehow felt familiar \u2014 like a lullaby she'd forgotten from childhood.\n\nSomething moved between the spires. Something enormous.\n\nMaya's hand hovered over the ascent button. Every instinct screamed at her to surface.\n\nBut the singing... the singing was calling her name..."
  },
  {
    title: "The Forest That Remembers",
    image: "https://images.unsplash.com/photo-1670268041874-414be5e2bde3?w=800&q=80",
    story_text: "Every tree in the Whispering Wood held a memory. This was common knowledge in the village of Thornhaven. Touch the bark of a birch, and you'd see a grandmother's wedding day. Press your palm against a pine, and you'd feel a child's first snowfall.\n\nBut nobody \u2014 nobody \u2014 touched the black oak at the center.\n\n\"It's cursed,\" the elders said. \"It holds the memories that were meant to be forgotten.\"\n\nKai was ten. He didn't believe in curses.\n\nHe pressed both palms flat against the ancient bark, and the world went white.\n\nHe didn't see a memory. He saw the future.\n\nThe village, burning. The sky, fractured like broken glass. And standing in the middle of it all \u2014 himself. Older. Scarred. Holding a weapon made of crystallized starlight.\n\nThe vision snapped away. Kai stumbled backward, gasping.\n\nCarved into the bark \u2014 fresh, still bleeding sap \u2014 were two words that hadn't been there before:\n\n\"IT'S STARTING.\""
  }
];

const LOADING_TEXTS = [
  "Creating your viral story...",
  "Writing the opening hook...",
  "Adding cinematic details...",
  "Building the cliffhanger...",
];

const GENERATION_TIMEOUT_MS = 20000;

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
  const [phase, setPhase] = useState('loading');
  const [demoStory, setDemoStory] = useState(null);
  const [realStory, setRealStory] = useState(null);
  const [loadingTextIdx, setLoadingTextIdx] = useState(0);
  const [transitionState, setTransitionState] = useState('idle');
  const [genFailed, setGenFailed] = useState(false);
  const generationRef = useRef(false);
  const timeoutRef = useRef(null);
  const mountTimeRef = useRef(Date.now());

  const source = searchParams.get('source') || 'landing';
  const sourceTitle = searchParams.get('title') || '';
  const sourceSnippet = searchParams.get('snippet') || '';
  const theme = searchParams.get('theme') || '';

  // Pick random demo story on mount
  useEffect(() => {
    const idx = Math.floor(Math.random() * DEMO_STORIES.length);
    setDemoStory(DEMO_STORIES[idx]);
  }, []);

  // Cycle loading text
  useEffect(() => {
    if (phase !== 'loading') return;
    const interval = setInterval(() => {
      setLoadingTextIdx(prev => (prev + 1) % LOADING_TEXTS.length);
    }, 900);
    return () => clearInterval(interval);
  }, [phase]);

  // Show demo after short loading — target <1s perceived load
  useEffect(() => {
    const timer = setTimeout(() => {
      setPhase('demo');
      try { trackFunnel('demo_viewed', { source }); } catch {}
    }, 800);
    return () => clearTimeout(timer);
  }, [source]);

  // Background generation
  const startGeneration = useCallback(async () => {
    if (generationRef.current) return;
    generationRef.current = true;

    try { trackFunnel('story_generation_started', { source }); } catch {}

    // Set timeout — if backend doesn't respond in 20s, gracefully degrade
    timeoutRef.current = setTimeout(() => {
      if (!realStory) {
        setGenFailed(true);
        try { trackFunnel('story_generation_timeout', { source }); } catch {}
      }
    }, GENERATION_TIMEOUT_MS);

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

      clearTimeout(timeoutRef.current);

      if (res.ok) {
        const data = await res.json();
        setRealStory(data);
        try { trackFunnel('story_generated_success', { source, meta: { story_id: data.story_id } }); } catch {}
      } else {
        setGenFailed(true);
        try { trackFunnel('story_generated_failed', { source }); } catch {}
      }
    } catch {
      clearTimeout(timeoutRef.current);
      setGenFailed(true);
      try { trackFunnel('story_generated_failed', { source }); } catch {}
    }
  }, [source, sourceTitle, sourceSnippet, theme, realStory]);

  // Trigger generation when demo phase starts
  useEffect(() => {
    if (phase === 'demo') {
      startGeneration();
    }
  }, [phase, startGeneration]);

  // Auto-transition when real story arrives — smooth 400ms fade out, 400ms fade in
  useEffect(() => {
    if (realStory && phase === 'demo' && transitionState === 'idle') {
      // Brief pause to let "ready" banner flash, then auto-swap
      const timer = setTimeout(() => {
        setTransitionState('fading-out');
        setTimeout(() => {
          setPhase('real');
          setTransitionState('fading-in');
          setTimeout(() => {
            setTransitionState('complete');
          }, 500);
        }, 400);
      }, 600);
      return () => clearTimeout(timer);
    }
  }, [realStory, phase, transitionState]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

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
    try { trackFunnel('cta_continue_clicked', { source, meta: { phase } }); } catch {}
    const token = localStorage.getItem('token');
    if (token) {
      navigate('/app/story-video-studio', {
        state: { prefill: { story_text: currentStory?.story_text, title: currentStory?.title } }
      });
    } else {
      try { trackFunnel('login_prompt_shown', { source, meta: { trigger: 'continue' } }); } catch {}
      sessionStorage.setItem('post_login_redirect', '/app/story-video-studio');
      sessionStorage.setItem('post_login_story', JSON.stringify({
        story_text: currentStory?.story_text,
        title: currentStory?.title,
      }));
      navigate('/login?from=experience');
    }
  };

  const handleVideo = () => {
    try { trackFunnel('cta_video_clicked', { source, meta: { phase } }); } catch {}
    const token = localStorage.getItem('token');
    if (token) {
      navigate('/app/story-video-studio', {
        state: { prefill: { story_text: currentStory?.story_text, title: currentStory?.title }, autoVideo: true }
      });
    } else {
      try { trackFunnel('login_prompt_shown', { source, meta: { trigger: 'video' } }); } catch {}
      sessionStorage.setItem('post_login_redirect', '/app/story-video-studio');
      sessionStorage.setItem('post_login_story', JSON.stringify({
        story_text: currentStory?.story_text,
        title: currentStory?.title,
      }));
      navigate('/login?from=experience');
    }
  };

  const handleShare = async () => {
    try { trackFunnel('cta_share_clicked', { source, meta: { phase } }); } catch {}
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
    setGenFailed(false);
    setRealStory(null);
    setTransitionState('idle');
    const idx = Math.floor(Math.random() * DEMO_STORIES.length);
    setDemoStory(DEMO_STORIES[idx]);
    setPhase('loading');
    setLoadingTextIdx(0);
    setTimeout(() => {
      setPhase('demo');
      try { trackFunnel('demo_viewed', { source, meta: { regenerate: true } }); } catch {}
    }, 600);
  };

  // Compute banner state
  const getBannerState = () => {
    if (phase === 'real' || transitionState === 'complete') return 'personalized';
    if (realStory && transitionState !== 'idle') return 'swapping';
    if (realStory) return 'ready';
    if (genFailed) return 'failed';
    if (phase === 'demo') return 'generating';
    return 'none';
  };

  const bannerState = getBannerState();

  // ─── LOADING PHASE ─────────────────────────────────────────────
  if (phase === 'loading') {
    return (
      <div className="min-h-screen bg-[#0a0a10] flex items-center justify-center" data-testid="instant-story-loading">
        <div className="text-center ist-fadeIn">
          <div className="relative w-20 h-20 mx-auto mb-6">
            <div className="absolute inset-0 rounded-full border-2 border-indigo-500/30 animate-ping" />
            <div className="absolute inset-2 rounded-full border-2 border-indigo-400/50 animate-pulse" />
            <Sparkles className="absolute inset-0 m-auto w-8 h-8 text-indigo-400 animate-pulse" />
          </div>
          <p className="text-lg font-medium text-white mb-2" data-testid="loading-text">
            {LOADING_TEXTS[loadingTextIdx]}
          </p>
          <div className="flex items-center justify-center gap-1.5 mt-3">
            {[0, 1, 2].map(i => (
              <div key={i} className="w-1.5 h-1.5 rounded-full bg-indigo-400 ist-dot" style={{
                animationDelay: `${i * 0.2}s`,
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
      {/* Top Banner — shows generation status */}
      {bannerState === 'generating' && (
        <div className="fixed top-0 left-0 right-0 z-50 py-1.5 px-4 text-center ist-banner-gen" data-testid="generating-indicator">
          <div className="flex items-center justify-center gap-2 text-sm text-white">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            <span>Personalizing your story...</span>
          </div>
        </div>
      )}

      {bannerState === 'failed' && (
        <div className="fixed top-0 left-0 right-0 z-50 py-1.5 px-4 text-center ist-banner-gen" data-testid="generating-failed-indicator">
          <div className="flex items-center justify-center gap-2 text-sm text-white/70">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            <span>Still personalizing your story...</span>
          </div>
        </div>
      )}

      {bannerState === 'ready' && (
        <div className="fixed top-0 left-0 right-0 z-50 py-2 px-4 text-center ist-banner-ready" data-testid="story-ready-banner">
          <div className="flex items-center justify-center gap-2 text-sm text-white font-medium">
            <CheckCircle className="w-4 h-4" />
            <span>Your personalized story is ready!</span>
          </div>
        </div>
      )}

      {(bannerState === 'personalized' || bannerState === 'swapping') && (
        <div className="fixed top-0 left-0 right-0 z-50 py-1.5 px-4 text-center ist-banner-done" data-testid="personalized-banner">
          <div className="flex items-center justify-center gap-2 text-sm text-emerald-200 font-medium">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Personalized for you</span>
          </div>
        </div>
      )}

      {/* Main Content — with transition animations */}
      <div className={`ist-content ${transitionState === 'fading-out' ? 'ist-fade-out' : ''} ${transitionState === 'fading-in' ? 'ist-fade-in' : ''}`}>
        {/* Hero Image */}
        <div className="relative h-[40vh] sm:h-[50vh] overflow-hidden">
          <img
            src={currentStory?.image}
            alt={currentStory?.title}
            className="w-full h-full object-cover"
            data-testid="story-hero-image"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-[#0a0a10] via-[#0a0a10]/40 to-transparent" />
        </div>

        {/* Content */}
        <div className="relative -mt-20 px-4 sm:px-8 max-w-2xl mx-auto pb-40 sm:pb-32">
          {/* Title */}
          <h1 className={`text-2xl sm:text-3xl lg:text-4xl font-bold text-white leading-tight mb-6 ${phase === 'real' ? 'ist-title-pop' : ''}`}
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
          <div className="mt-6 mb-6 flex items-center gap-2 text-amber-400/80">
            <div className="w-8 h-px bg-amber-400/40" />
            <span className="text-xs font-medium tracking-wider uppercase">To be continued...</span>
            <div className="flex-1 h-px bg-amber-400/40" />
          </div>

          {/* Social proof */}
          <div className="flex items-center gap-2 mb-6 text-slate-500 text-sm" data-testid="social-proof">
            <div className="flex -space-x-1.5">
              {[1,2,3].map(i => (
                <div key={i} className="w-5 h-5 rounded-full border border-slate-700" style={{
                  background: `hsl(${i * 80 + 200}, 50%, 30%)`,
                }} />
              ))}
            </div>
            <span>92% of readers continue this story</span>
          </div>

          {/* Desktop Action Buttons — visible inline */}
          <div className="hidden sm:block space-y-3" data-testid="story-actions-desktop">
            <button
              onClick={handleContinue}
              className="w-full py-4 px-6 rounded-xl font-semibold text-white text-base flex items-center justify-center gap-2.5 transition-all hover:scale-[1.02] active:scale-[0.98] ist-cta-primary"
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

      {/* Mobile Sticky Bottom CTA — always visible, no scrolling needed */}
      <div className="sm:hidden fixed bottom-0 left-0 right-0 z-40 p-3 ist-sticky-cta" data-testid="story-actions-mobile">
        <button
          onClick={handleContinue}
          className="w-full py-3.5 px-6 rounded-xl font-semibold text-white text-base flex items-center justify-center gap-2.5 transition-all active:scale-[0.98] ist-cta-primary"
          data-testid="cta-continue-story-mobile"
        >
          <Play className="w-5 h-5" />
          Continue Story
        </button>
        <div className="flex gap-2 mt-2">
          <button onClick={handleVideo} className="flex-1 py-2.5 px-3 rounded-lg font-medium text-white/80 text-xs flex items-center justify-center gap-1.5 border border-white/10 bg-white/5" data-testid="cta-video-mobile">
            <Film className="w-3.5 h-3.5" /> Video
          </button>
          <button onClick={handleShare} className="flex-1 py-2.5 px-3 rounded-lg font-medium text-white/80 text-xs flex items-center justify-center gap-1.5 border border-white/10 bg-white/5" data-testid="cta-share-mobile">
            <Share2 className="w-3.5 h-3.5" /> Share
          </button>
          <button onClick={handleRegenerate} className="flex-1 py-2.5 px-3 rounded-lg font-medium text-white/80 text-xs flex items-center justify-center gap-1.5 border border-white/10 bg-white/5" data-testid="cta-new-mobile">
            <RefreshCw className="w-3.5 h-3.5" /> New
          </button>
        </div>
      </div>

      <style>{`
        /* Fade in on mount */
        .ist-fadeIn {
          animation: istFadeIn 0.5s ease-out forwards;
        }
        @keyframes istFadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: none; }
        }

        /* Loading dots */
        .ist-dot {
          animation: istDotPulse 1.2s ease-in-out infinite;
        }
        @keyframes istDotPulse {
          0%, 100% { opacity: 0.4; transform: scale(0.8); }
          50% { opacity: 1; transform: scale(1.2); }
        }

        /* Content fade out during transition */
        .ist-fade-out {
          animation: istContentFadeOut 0.4s ease-in forwards;
        }
        @keyframes istContentFadeOut {
          from { opacity: 1; transform: scale(1); }
          to { opacity: 0; transform: scale(0.98); }
        }

        /* Content fade in after swap */
        .ist-fade-in {
          animation: istContentFadeIn 0.5s ease-out forwards;
        }
        @keyframes istContentFadeIn {
          from { opacity: 0; transform: scale(1.02); }
          to { opacity: 1; transform: scale(1); }
        }

        /* Title pop animation on real story */
        .ist-title-pop {
          animation: istTitlePop 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
        }
        @keyframes istTitlePop {
          0% { transform: scale(0.92); opacity: 0.5; }
          50% { transform: scale(1.03); }
          100% { transform: scale(1); opacity: 1; }
        }

        /* Banner styles */
        .ist-banner-gen {
          background: linear-gradient(90deg, rgba(99, 102, 241, 0.9), rgba(139, 92, 246, 0.9));
          backdrop-filter: blur(8px);
        }
        .ist-banner-ready {
          background: linear-gradient(90deg, rgba(16, 185, 129, 0.9), rgba(52, 211, 153, 0.9));
          backdrop-filter: blur(8px);
          animation: istBannerPulse 1.5s ease-in-out infinite;
        }
        @keyframes istBannerPulse {
          0%, 100% { opacity: 0.95; }
          50% { opacity: 1; }
        }
        .ist-banner-done {
          background: rgba(16, 185, 129, 0.15);
          backdrop-filter: blur(8px);
          border-bottom: 1px solid rgba(16, 185, 129, 0.2);
        }

        /* Primary CTA gradient */
        .ist-cta-primary {
          background: linear-gradient(135deg, #6366f1, #8b5cf6);
          box-shadow: 0 4px 24px rgba(99, 102, 241, 0.3);
        }
        .ist-cta-primary:hover {
          box-shadow: 0 6px 32px rgba(99, 102, 241, 0.45);
        }

        /* Sticky bottom CTA background */
        .ist-sticky-cta {
          background: linear-gradient(to top, #0a0a10 60%, transparent);
          padding-bottom: max(0.75rem, env(safe-area-inset-bottom));
        }
      `}</style>
    </div>
  );
}
