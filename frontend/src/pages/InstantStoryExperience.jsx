import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Sparkles, Play, Share2, Film, RefreshCw, Loader2, CheckCircle, ChevronDown, Zap, BookOpen } from 'lucide-react';
import { toast } from 'sonner';
import { trackFunnel } from '../utils/funnelTracker';
import StoryPaywall from './StoryPaywall';
import VideoRewardPreview from './VideoRewardPreview';

const API = process.env.REACT_APP_BACKEND_URL;

// Persistent device token — survives refresh, new tabs, sessions
function getDeviceToken() {
  let token = localStorage.getItem('vs_device_token');
  if (!token) {
    token = 'dt_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem('vs_device_token', token);
  }
  return token;
}

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

const CONTINUE_LOADING_TEXTS = [
  "Writing Part {n}...",
  "Building the next twist...",
  "Raising the stakes...",
  "Crafting the cliffhanger...",
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

// Speed SLA thresholds (founder directive Apr 2026):
// CTA → first paint <1.5s, CTA → wow <3s, teaser ready <5s.
const SLA_THRESHOLDS_MS = {
  cta_to_first_paint: 1500,
  cta_to_wow: 3000,
  teaser_ready: 5000,
};

function emitSpeedSla(eventName, elapsedMs, extra = {}) {
  if (!Number.isFinite(elapsedMs) || elapsedMs < 0) return;
  const threshold = SLA_THRESHOLDS_MS[eventName];
  const breached = threshold ? elapsedMs > threshold : false;
  const meta = { event: eventName, elapsed_ms: Math.round(elapsedMs), threshold_ms: threshold || null, ...extra };
  try {
    trackFunnel(eventName, { meta });
    trackFunnel(breached ? 'speed_sla_breached' : 'speed_sla_met', { meta });
    if (breached) {
      // eslint-disable-next-line no-console
      console.warn('[SLA breach]', eventName, 'elapsed', elapsedMs, 'ms (threshold', threshold, ')');
    }
  } catch (_) { /* never block UI */ }
}

// ─── P1.1 Outcome-led CTA copy A/B test ─────────────────────────────────
// Sticky per-session assignment. Variant impressions/clicks tracked via
// trackFunnel with meta.video_cta_variant for downstream analysis.
const VIDEO_CTA_VARIANTS = [
  { id: 'control',     label: 'Turn Into Video' },
  { id: 'cinematic',   label: 'Turn This Into a Cinematic Video' },
  { id: 'kids_reel',   label: 'Make This a Reel Kids Will Love' },
  { id: 'one_tap',     label: 'Create a Shareable Video in 1 Tap' },
  { id: 'bring_alive', label: 'Bring This Story to Life' },
];

function getVideoCtaVariant() {
  let id = sessionStorage.getItem('video_cta_variant');
  if (id && VIDEO_CTA_VARIANTS.some(v => v.id === id)) return VIDEO_CTA_VARIANTS.find(v => v.id === id);
  // Random uniform across 5 — small N, treat as exploration.
  const picked = VIDEO_CTA_VARIANTS[Math.floor(Math.random() * VIDEO_CTA_VARIANTS.length)];
  sessionStorage.setItem('video_cta_variant', picked.id);
  return picked;
}

function getLastCliffhanger(text) {
  if (!text) return '';
  const paragraphs = text.split('\n').filter(p => p.trim());
  const last = paragraphs[paragraphs.length - 1]?.trim() || '';
  if (last.length > 120) {
    const sentences = last.match(/[^.!?…]+[.!?…]+/g) || [last];
    return sentences[sentences.length - 1]?.trim() || last.slice(-100);
  }
  return last;
}

export default function InstantStoryExperience() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // ─── Initial load state ────────────────────────────────────────
  // P0 Apr 2026 — paint demo on first frame (no loading spinner gap).
  const [phase, setPhase] = useState('demo');
  const [demoStory, setDemoStory] = useState(() => DEMO_STORIES[Math.floor(Math.random() * DEMO_STORIES.length)]);
  const [realStory, setRealStory] = useState(null);
  const [loadingTextIdx, setLoadingTextIdx] = useState(0);
  const [transitionState, setTransitionState] = useState('idle');
  const [genFailed, setGenFailed] = useState(false);
  const generationRef = useRef(false);
  const timeoutRef = useRef(null);

  // ─── Continuation loop state ───────────────────────────────────
  const [continuations, setContinuations] = useState([]);
  const [isGeneratingPart, setIsGeneratingPart] = useState(false);
  const [continueLoadingIdx, setContinueLoadingIdx] = useState(0);
  const [showTeaser, setShowTeaser] = useState(false);
  const [showPaywall, setShowPaywall] = useState(false);
  const [paywallViewCount, setPaywallViewCount] = useState(() =>
    parseInt(sessionStorage.getItem('pw_view_count') || '0', 10)
  );
  const [allowFreeView, setAllowFreeView] = useState(false);
  const [showFreeViewTooltip, setShowFreeViewTooltip] = useState(false);
  const continueEndRef = useRef(null);
  const teaserDismissedRef = useRef(false);
  // P1.2 Visual reward preview before paywall
  const [showVideoReward, setShowVideoReward] = useState(false);
  // P1.1 — sticky CTA copy variant for this session
  const videoCtaVariant = useRef(getVideoCtaVariant()).current;
  // Has user clicked Continue at least once? Drives sticky footer (P1.5).
  const hasContinuedRef = useRef(false);
  const videoCtaImpressionFiredRef = useRef(false);

  const source = searchParams.get('source') || 'landing';
  const sourceTitle = searchParams.get('title') || '';
  const sourceSnippet = searchParams.get('snippet') || '';
  const theme = searchParams.get('theme') || '';

  // Computed values
  const partNumber = 1 + continuations.length;
  const activeStory = phase === 'real' && realStory
    ? { title: realStory.title, story_text: realStory.story_text, image: demoStory?.image, story_id: realStory.story_id }
    : demoStory
    ? { title: demoStory.title, story_text: demoStory.story_text, image: demoStory.image, story_id: null }
    : null;

  const fullStoryText = activeStory
    ? [activeStory.story_text, ...continuations.map(c => c.text)].join('\n\n')
    : '';
  const latestText = continuations.length > 0
    ? continuations[continuations.length - 1].text
    : activeStory?.story_text || '';

  // ─── Initial Load Logic — INSTANT DEMO (P0 Apr 2026) ──────────
  // Demo is painted synchronously on first render via lazy useState.
  // This effect only fires telemetry + kicks off background generation.
  useEffect(() => {
    try { trackFunnel('demo_viewed', { source }); } catch {}
    const ctaTs = Number(sessionStorage.getItem('cta_clicked_ts') || 0);
    if (ctaTs > 0) emitSpeedSla('cta_to_first_paint', Date.now() - ctaTs);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (phase !== 'loading') return;
    const interval = setInterval(() => setLoadingTextIdx(prev => (prev + 1) % LOADING_TEXTS.length), 900);
    return () => clearInterval(interval);
  }, [phase]);

  const startGeneration = useCallback(async () => {
    if (generationRef.current) return;
    generationRef.current = true;
    const ctaTs = Number(sessionStorage.getItem('cta_clicked_ts') || 0) || Date.now();
    const genStartedAt = Date.now();
    try { trackFunnel('story_generation_started', { source }); } catch {}

    timeoutRef.current = setTimeout(() => {
      if (!realStory) {
        setGenFailed(true);
        try { trackFunnel('story_generation_timeout', { source }); } catch {}
      }
    }, GENERATION_TIMEOUT_MS);

    try {
      const body = { mode: sourceSnippet ? 'continue' : 'fresh', session_id: getSessionId(), device_token: getDeviceToken() };
      if (sourceSnippet) { body.source_title = sourceTitle; body.source_snippet = sourceSnippet; }
      if (theme) body.theme = theme;

      const headers = { 'Content-Type': 'application/json' };
      const authToken = localStorage.getItem('token');
      if (authToken) headers['Authorization'] = `Bearer ${authToken}`;

      const res = await fetch(`${API}/api/public/quick-generate`, {
        method: 'POST', headers, body: JSON.stringify(body),
      });
      clearTimeout(timeoutRef.current);

      if (res.ok) {
        const data = await res.json();
        setRealStory(data);
        if (data.allow_free_view) setAllowFreeView(true);
        // SLA: teaser ready = CTA click → quick-generate response received.
        emitSpeedSla('teaser_ready', Date.now() - ctaTs, {
          api_duration_ms: Date.now() - genStartedAt,
          story_id: data.story_id,
        });
        // Canonical funnel name (matches activation dashboard).
        try {
          trackFunnel('story_generated_success', { source, meta: { story_id: data.story_id, allow_free_view: data.allow_free_view } });
          trackFunnel('story_generation_completed', { source, meta: { story_id: data.story_id } });
        } catch {}
      } else {
        setGenFailed(true);
        try { trackFunnel('story_generated_failed', { source, meta: { status: res.status } }); } catch {}
      }
    } catch (err) {
      clearTimeout(timeoutRef.current);
      setGenFailed(true);
      try { trackFunnel('story_generated_failed', { source, meta: { error: String(err).slice(0, 120) } }); } catch {}
    }
  }, [source, sourceTitle, sourceSnippet, theme, realStory]);

  useEffect(() => { if (phase === 'demo') startGeneration(); }, [phase, startGeneration]);

  useEffect(() => {
    if (realStory && phase === 'demo' && transitionState === 'idle') {
      const timer = setTimeout(() => {
        setTransitionState('fading-out');
        setTimeout(() => {
          setPhase('real');
          setTransitionState('fading-in');
          // SLA: WOW moment = CTA click → personalized story rendered on screen.
          const ctaTs = Number(sessionStorage.getItem('cta_clicked_ts') || 0);
          if (ctaTs > 0) emitSpeedSla('cta_to_wow', Date.now() - ctaTs, { story_id: realStory?.story_id });
          setTimeout(() => setTransitionState('complete'), 500);
        }, 400);
      }, 600);
      return () => clearTimeout(timer);
    }
  }, [realStory, phase, transitionState]);

  useEffect(() => { return () => { if (timeoutRef.current) clearTimeout(timeoutRef.current); }; }, []);

  // ─── Continuation loading text cycle ───────────────────────────
  useEffect(() => {
    if (!isGeneratingPart) return;
    const interval = setInterval(() => setContinueLoadingIdx(prev => (prev + 1) % CONTINUE_LOADING_TEXTS.length), 1100);
    return () => clearInterval(interval);
  }, [isGeneratingPart]);

  // Auto-scroll to new continuation
  useEffect(() => {
    if (continuations.length > 0 || isGeneratingPart) {
      setTimeout(() => continueEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 200);
    }
  }, [continuations.length, isGeneratingPart]);

  // Show soft teaser after Part 2 renders
  useEffect(() => {
    if (continuations.length === 1 && !teaserDismissedRef.current) {
      const timer = setTimeout(() => {
        setShowTeaser(true);
        try { trackFunnel('paywall_teaser_shown', { meta: { part_number: 2, story_id: activeStory?.story_id, entry_source: source } }); } catch {}
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [continuations.length, source, activeStory?.story_id]);

  // Free-view tooltip: show after 5-10s on Part 2 or Part 3 (first-time users only)
  useEffect(() => {
    if (!allowFreeView || continuations.length < 1 || continuations.length > 2 || isGeneratingPart) return;
    const delay = 5000 + Math.random() * 5000;
    const timer = setTimeout(() => {
      setShowFreeViewTooltip(true);
      try { trackFunnel('free_view_tooltip_shown', { meta: { part_number: continuations.length + 1, story_id: activeStory?.story_id } }); } catch {}
    }, delay);
    return () => clearTimeout(timer);
  }, [allowFreeView, continuations.length, isGeneratingPart, activeStory?.story_id]);

  // Auto-dismiss tooltip after 7 seconds
  useEffect(() => {
    if (!showFreeViewTooltip) return;
    const timer = setTimeout(() => setShowFreeViewTooltip(false), 7000);
    return () => clearTimeout(timer);
  }, [showFreeViewTooltip]);

  // ─── Continuation Generation ───────────────────────────────────
  const generateContinuation = useCallback(async (nextPartNum) => {
    setIsGeneratingPart(true);
    setContinueLoadingIdx(0);

    try {
      const snippetText = latestText.slice(-800);
      const headers = { 'Content-Type': 'application/json' };
      const authToken = localStorage.getItem('token');
      if (authToken) headers['Authorization'] = `Bearer ${authToken}`;

      const res = await fetch(`${API}/api/public/quick-generate`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          mode: 'continue',
          source_title: activeStory?.title || 'Story',
          source_snippet: snippetText,
          session_id: getSessionId(),
          device_token: getDeviceToken(),
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setContinuations(prev => [...prev, { text: data.story_text, partNumber: nextPartNum, story_id: data.story_id }]);
        try { trackFunnel('story_part_generated', { meta: { part_number: nextPartNum, story_id: data.story_id, entry_source: source } }); } catch {}
      }
    } catch {
      toast.error('Failed to generate the next part. Tap continue to try again.');
    }
    setIsGeneratingPart(false);
  }, [latestText, activeStory?.title, source]);

  // ─── Continue Button Handler ───────────────────────────────────
  const handleContinueStory = useCallback(() => {
    const nextPart = partNumber + 1;
    hasContinuedRef.current = true;

    // P1.1 — fire impression for the video CTA variant on first Continue
    // (the moment the user is engaged and the sticky footer becomes visible).
    if (!videoCtaImpressionFiredRef.current) {
      videoCtaImpressionFiredRef.current = true;
      try {
        trackFunnel('video_cta_variant_impression', {
          source,
          meta: {
            video_cta_variant: videoCtaVariant.id,
            video_cta_label: videoCtaVariant.label,
            story_id: activeStory?.story_id,
            part_number: partNumber,
          },
        });
      } catch {}
    }

    try { trackFunnel('continue_clicked', { meta: { part_number: nextPart, story_id: activeStory?.story_id, entry_source: source, allow_free_view: allowFreeView } }); } catch {}

    if (partNumber === 1) {
      // Part 1 → generate Part 2 (no gate)
      generateContinuation(2);
    } else if (partNumber === 2 && allowFreeView) {
      // First-time user: allow Part 3 without hard paywall
      generateContinuation(3);
      try { trackFunnel('first_time_free_view_used', { meta: { part_number: 3, story_id: activeStory?.story_id, entry_source: source } }); } catch {}
    } else if (partNumber >= 2) {
      // Returning user or Part 4+: hard paywall
      const newCount = paywallViewCount + 1;
      setPaywallViewCount(newCount);
      sessionStorage.setItem('pw_view_count', String(newCount));
      setShowPaywall(true);
      try { trackFunnel('paywall_shown', { meta: { part_number: nextPart, story_id: activeStory?.story_id, view_count: newCount, entry_source: source } }); } catch {}
    }
  }, [partNumber, generateContinuation, activeStory?.story_id, source, paywallViewCount, allowFreeView, videoCtaVariant]);

  // ─── Other Handlers ────────────────────────────────────────────
  const handleVideo = () => {
    // P1.1 — fire CTA click with variant
    try {
      trackFunnel('cta_video_clicked', {
        source,
        meta: {
          phase, part_number: partNumber,
          video_cta_variant: videoCtaVariant.id,
          video_cta_label: videoCtaVariant.label,
          story_id: activeStory?.story_id,
        },
      });
    } catch {}
    // P1.2 — show visual reward preview FIRST (motion + captions + waveform + ETA)
    // BEFORE asking for login/payment. This converts curiosity into intent.
    setShowVideoReward(true);
  };

  const proceedToVideoCheckout = () => {
    // Called after user confirms in VideoRewardPreview.
    try {
      trackFunnel('checkout_started', {
        source,
        meta: {
          intent: 'video',
          phase, part_number: partNumber,
          video_cta_variant: videoCtaVariant.id,
          story_id: activeStory?.story_id,
        },
      });
    } catch {}
    const token = localStorage.getItem('token');
    const storyData = { story_text: fullStoryText, title: activeStory?.title };
    if (token) {
      navigate('/app/story-video-studio', { state: { prefill: storyData, autoVideo: true } });
    } else {
      sessionStorage.setItem('post_login_redirect', '/app/story-video-studio');
      sessionStorage.setItem('post_login_story', JSON.stringify(storyData));
      navigate('/login?from=experience');
    }
  };

  const handleShare = async () => {
    try { trackFunnel('cta_share_clicked', { source, meta: { phase, part_number: partNumber } }); } catch {}
    if (navigator.share) {
      try { await navigator.share({ title: activeStory?.title, text: activeStory?.story_text?.slice(0, 200) + '...', url: window.location.href }); } catch {}
    } else {
      navigator.clipboard?.writeText(window.location.href);
    }
  };

  const handleRegenerate = () => {
    generationRef.current = false;
    setGenFailed(false);
    setRealStory(null);
    setTransitionState('idle');
    setContinuations([]);
    setShowTeaser(false);
    teaserDismissedRef.current = false;
    setDemoStory(DEMO_STORIES[Math.floor(Math.random() * DEMO_STORIES.length)]);
    setPhase('loading');
    setLoadingTextIdx(0);
    setTimeout(() => {
      setPhase('demo');
      try { trackFunnel('demo_viewed', { source, meta: { regenerate: true } }); } catch {}
    }, 600);
  };

  // ─── Banner State ──────────────────────────────────────────────
  const getBannerState = () => {
    if (phase === 'real' || transitionState === 'complete') return 'personalized';
    if (realStory && transitionState !== 'idle') return 'swapping';
    if (realStory) return 'ready';
    if (genFailed) return 'failed';
    if (phase === 'demo') return 'generating';
    return 'none';
  };
  const bannerState = getBannerState();

  // ─── CTA Text ─────────────────────────────────────────────────
  const ctaText = partNumber === 1 ? 'Continue Story' : 'Continue to Part ' + (partNumber + 1);
  const continueLoadingText = CONTINUE_LOADING_TEXTS[continueLoadingIdx].replace('{n}', String(partNumber + 1));

  // ═══════════════════════════════════════════════════════════════
  // LOADING PHASE
  // ═══════════════════════════════════════════════════════════════
  if (phase === 'loading') {
    return (
      <div className="min-h-screen bg-[#0a0a10] flex items-center justify-center" data-testid="instant-story-loading">
        <div className="text-center ist-fadeIn">
          <div className="relative w-20 h-20 mx-auto mb-6">
            <div className="absolute inset-0 rounded-full border-2 border-indigo-500/30 animate-ping" />
            <div className="absolute inset-2 rounded-full border-2 border-indigo-400/50 animate-pulse" />
            <Sparkles className="absolute inset-0 m-auto w-8 h-8 text-indigo-400 animate-pulse" />
          </div>
          <p className="text-lg font-medium text-white mb-2" data-testid="loading-text">{LOADING_TEXTS[loadingTextIdx]}</p>
          <div className="flex items-center justify-center gap-1.5 mt-3">
            {[0, 1, 2].map(i => (
              <div key={i} className="w-1.5 h-1.5 rounded-full bg-indigo-400 ist-dot" style={{ animationDelay: `${i * 0.2}s` }} />
            ))}
          </div>
        </div>
      </div>
    );
  }

  // ═══════════════════════════════════════════════════════════════
  // STORY EXPERIENCE
  // ═══════════════════════════════════════════════════════════════
  return (
    <div className="min-h-screen min-h-[100dvh] bg-[#0a0a10]" data-testid="instant-story-experience">
      {/* ── Top Banner ──────────────────────────────────────── */}
      {bannerState === 'generating' && (
        <div className="fixed top-0 left-0 right-0 z-50 py-1.5 px-4 text-center ist-banner-gen" data-testid="generating-indicator">
          <div className="flex items-center justify-center gap-2 text-sm text-white">
            <Loader2 className="w-3.5 h-3.5 animate-spin" /><span>Personalizing your story...</span>
          </div>
        </div>
      )}
      {bannerState === 'failed' && (
        <div className="fixed top-0 left-0 right-0 z-50 py-1.5 px-4 text-center ist-banner-gen" data-testid="generating-failed-indicator">
          <div className="flex items-center justify-center gap-2 text-sm text-white/70">
            <Loader2 className="w-3.5 h-3.5 animate-spin" /><span>Still personalizing your story...</span>
          </div>
        </div>
      )}
      {bannerState === 'ready' && (
        <div className="fixed top-0 left-0 right-0 z-50 py-2 px-4 text-center ist-banner-ready" data-testid="story-ready-banner">
          <div className="flex items-center justify-center gap-2 text-sm text-white font-medium">
            <CheckCircle className="w-4 h-4" /><span>Your personalized story is ready!</span>
          </div>
        </div>
      )}
      {(bannerState === 'personalized' || bannerState === 'swapping') && (
        <div className="fixed top-0 left-0 right-0 z-50 py-1.5 px-4 text-center ist-banner-done" data-testid="personalized-banner">
          <div className="flex items-center justify-center gap-2 text-sm text-emerald-200 font-medium">
            <Sparkles className="w-3.5 h-3.5" /><span>Personalized for you</span>
          </div>
        </div>
      )}

      {/* ── Main Content ────────────────────────────────────── */}
      <div className={`ist-content ${transitionState === 'fading-out' ? 'ist-fade-out' : ''} ${transitionState === 'fading-in' ? 'ist-fade-in' : ''}`}>
        {/* Hero Image */}
        <div className="relative h-[35vh] sm:h-[45vh] overflow-hidden">
          <img src={activeStory?.image} alt={activeStory?.title} loading="eager" fetchpriority="high" decoding="async" className="w-full h-full object-cover" data-testid="story-hero-image" />
          <div className="absolute inset-0 bg-gradient-to-t from-[#0a0a10] via-[#0a0a10]/40 to-transparent" />
        </div>

        {/* Content */}
        <div className="relative -mt-20 px-4 sm:px-8 max-w-2xl mx-auto pb-48 sm:pb-36">
          {/* Title */}
          <h1 className={`text-2xl sm:text-3xl lg:text-4xl font-bold text-white leading-tight mb-6 ${phase === 'real' ? 'ist-title-pop' : ''}`} data-testid="story-title">
            {activeStory?.title}
          </h1>

          {/* Part 1 — Initial Story */}
          <div className="prose prose-invert prose-lg max-w-none" data-testid="story-text-part-1">
            {activeStory?.story_text?.split('\n').map((p, i) => (
              p.trim() && <p key={i} className="text-slate-300 leading-relaxed text-base sm:text-lg mb-4">{p}</p>
            ))}
          </div>

          {/* ── Continuation Parts ───────────────────────────── */}
          {continuations.map((cont, idx) => (
            <div key={idx} className="mt-8 ist-part-appear" data-testid={`story-text-part-${idx + 2}`}>
              <div className="flex items-center gap-2 mb-4 text-indigo-400/60">
                <div className="h-px flex-1 bg-indigo-400/20" />
                <span className="text-[10px] font-bold tracking-widest uppercase">Part {idx + 2}</span>
                <div className="h-px flex-1 bg-indigo-400/20" />
              </div>
              <div className="prose prose-invert prose-lg max-w-none">
                {cont.text.split('\n').map((p, pi) => (
                  p.trim() && <p key={pi} className="text-slate-300 leading-relaxed text-base sm:text-lg mb-4">{p}</p>
                ))}
              </div>
            </div>
          ))}

          {/* ── Soft Upgrade CTA (first-time users after Part 3) ─── */}
          {allowFreeView && continuations.length >= 2 && !isGeneratingPart && (
            <div className="mt-8 p-5 rounded-xl bg-gradient-to-r from-indigo-500/10 to-purple-500/10 border border-indigo-500/20 ist-part-appear" data-testid="soft-upgrade-cta">
              <p className="text-white font-semibold text-sm mb-1">Upgrade to download, create more, and unlock premium quality</p>
              <p className="text-slate-400 text-xs mb-4">You've experienced the full story — unlock premium features to do even more.</p>
              <div className="flex gap-3">
                <button
                  onClick={() => {
                    try { trackFunnel('soft_upgrade_clicked', { meta: { part_number: partNumber, story_id: activeStory?.story_id } }); } catch {}
                    const token = localStorage.getItem('token');
                    if (token) navigate('/app/pricing');
                    else navigate('/login?from=experience');
                  }}
                  className="flex-1 py-3 px-4 rounded-xl font-semibold text-white text-sm flex items-center justify-center gap-2 ist-cta-primary"
                  data-testid="soft-upgrade-btn"
                >
                  <Zap className="w-4 h-4" />
                  Upgrade Now
                </button>
                <button
                  onClick={() => {
                    try { trackFunnel('soft_upgrade_dismissed', { meta: { part_number: partNumber } }); } catch {}
                  }}
                  className="flex-1 py-3 px-4 rounded-xl font-medium text-slate-400 text-sm flex items-center justify-center gap-2 border border-white/10 hover:bg-white/5 transition-all"
                  data-testid="soft-continue-exploring-btn"
                >
                  Continue exploring for free
                </button>
              </div>
            </div>
          )}

          {/* ── Continuation Loading ─────────────────────────── */}
          {isGeneratingPart && (
            <div className="mt-8 text-center py-8 ist-part-appear" data-testid="continuation-loading">
              <div className="relative w-12 h-12 mx-auto mb-4">
                <div className="absolute inset-0 rounded-full border-2 border-indigo-500/30 animate-ping" />
                <Sparkles className="absolute inset-0 m-auto w-5 h-5 text-indigo-400 animate-pulse" />
              </div>
              <p className="text-sm text-slate-400">{continueLoadingText}</p>
            </div>
          )}

          {/* ── Cliffhanger + CTA Section ────────────────────── */}
          {!isGeneratingPart && (
            <div ref={continueEndRef}>
              {/* Cliffhanger */}
              <div className="mt-6 mb-4 flex items-center gap-2 text-amber-400/80">
                <div className="w-8 h-px bg-amber-400/40" />
                <span className="text-xs font-medium tracking-wider uppercase">To be continued...</span>
                <div className="flex-1 h-px bg-amber-400/40" />
              </div>

              {/* "What happens next?" prompt */}
              <div className="mb-6 p-4 rounded-xl bg-white/[0.03] border border-white/[0.06]" data-testid="what-happens-next">
                <p className="text-xs text-slate-500 uppercase tracking-wider font-medium mb-2">What happens next?</p>
                <p className="text-slate-400 text-sm italic leading-relaxed">
                  {getLastCliffhanger(latestText)}
                </p>
              </div>

              {/* Social proof */}
              <div className="flex items-center gap-2 mb-5 text-slate-500 text-sm" data-testid="social-proof">
                <div className="flex -space-x-1.5">
                  {[1,2,3].map(i => (
                    <div key={i} className="w-5 h-5 rounded-full border border-slate-700" style={{ background: `hsl(${i * 80 + 200}, 50%, 30%)` }} />
                  ))}
                </div>
                <span>92% of readers continue this story</span>
              </div>

              {/* Desktop CTAs */}
              <div className="hidden sm:block space-y-3" data-testid="story-actions-desktop">
                <button onClick={handleContinueStory} className={`w-full py-4 px-6 rounded-xl font-semibold text-white text-base flex items-center justify-center gap-2.5 transition-all hover:scale-[1.02] active:scale-[0.98] ist-cta-primary ${showFreeViewTooltip ? 'ist-cta-enhanced-pulse' : 'ist-cta-pulse'}`} data-testid="cta-continue-story">
                  <Play className="w-5 h-5" />{ctaText}
                </button>
                <button onClick={handleVideo} className="w-full py-3.5 px-6 rounded-xl font-semibold text-white text-sm flex items-center justify-center gap-2.5 ist-video-cta active:scale-[0.98] transition-all" data-testid="cta-generate-video" data-variant={videoCtaVariant.id}>
                  <Film className="w-4 h-4" />{videoCtaVariant.label} <span className="opacity-80 ml-1">— ₹29</span>
                </button>
                <div className="flex gap-3">
                  <button onClick={handleShare} className="flex-1 py-3 px-4 rounded-xl font-medium text-slate-400 text-sm flex items-center justify-center gap-2 border border-white/5 hover:bg-white/5 transition-all" data-testid="cta-share">
                    <Share2 className="w-4 h-4" />Share
                  </button>
                  <button onClick={handleRegenerate} className="flex-1 py-3 px-4 rounded-xl font-medium text-slate-400 text-sm flex items-center justify-center gap-2 border border-white/5 hover:bg-white/5 transition-all" data-testid="cta-regenerate">
                    <RefreshCw className="w-4 h-4" />New Story
                  </button>
                </div>
              </div>
            </div>
          )}
          <div ref={continueEndRef} />
        </div>
      </div>

      {/* ── Mobile Sticky CTA ───────────────────────────────── */}
      {!isGeneratingPart && !showPaywall && !showVideoReward && (
        <div className="sm:hidden fixed bottom-0 left-0 right-0 z-40 p-3 ist-sticky-cta" data-testid="story-actions-mobile">
          <button onClick={handleContinueStory} className={`w-full py-3.5 px-6 rounded-xl font-semibold text-white text-base flex items-center justify-center gap-2.5 transition-all active:scale-[0.98] ist-cta-primary ${showFreeViewTooltip ? 'ist-cta-enhanced-pulse' : 'ist-cta-pulse'}`} data-testid="cta-continue-story-mobile">
            <Play className="w-5 h-5" />{ctaText}
          </button>
          <div className="flex gap-2 mt-2">
            <button onClick={handleVideo} className="flex-1 py-2.5 px-3 rounded-lg font-semibold text-white text-xs flex items-center justify-center gap-1.5 ist-video-cta" data-testid="cta-video-mobile" data-variant={videoCtaVariant.id}>
              <Film className="w-3.5 h-3.5" /> Video — ₹29
            </button>
            <button onClick={handleShare} className="flex-1 py-2.5 px-3 rounded-lg font-medium text-white/80 text-xs flex items-center justify-center gap-1.5 border border-white/10 bg-white/5" data-testid="cta-share-mobile">
              <Share2 className="w-3.5 h-3.5" /> Share
            </button>
            <button onClick={handleRegenerate} className="flex-1 py-2.5 px-3 rounded-lg font-medium text-white/80 text-xs flex items-center justify-center gap-1.5 border border-white/10 bg-white/5" data-testid="cta-new-mobile">
              <RefreshCw className="w-3.5 h-3.5" /> New
            </button>
          </div>
        </div>
      )}

      {/* ── P1.5 Always-on Sticky Video CTA (desktop) ─────────────────
           Once the user has continued at least once, an outcome-led video
           CTA is always reachable without scrolling. */}
      {hasContinuedRef.current && !isGeneratingPart && !showPaywall && !showVideoReward && (
        <div className="hidden sm:flex fixed bottom-6 right-6 z-40 ist-sticky-video-fade" data-testid="sticky-video-cta-desktop">
          <button
            onClick={handleVideo}
            className="px-5 py-3 rounded-full font-bold text-white text-sm flex items-center gap-2 ist-video-cta active:scale-[0.97] transition-transform"
            data-variant={videoCtaVariant.id}
          >
            <Film className="w-4 h-4" />
            <span>{videoCtaVariant.label}</span>
            <span className="ml-1 px-2 py-0.5 rounded-full bg-black/25 text-[11px]">₹29</span>
          </button>
        </div>
      )}

      {/* ── Free View Onboarding Tooltip (non-blocking) ── */}
      {showFreeViewTooltip && (
        <div className="fixed bottom-24 sm:bottom-auto sm:top-20 left-1/2 -translate-x-1/2 z-50 max-w-sm mx-auto ist-tooltip-appear" data-testid="free-view-tooltip">
          <div className="bg-indigo-600/95 backdrop-blur-sm rounded-xl px-5 py-3 shadow-lg shadow-indigo-500/25 border border-indigo-400/30">
            <div className="flex items-start gap-3">
              <Zap className="w-5 h-5 text-amber-300 mt-0.5 shrink-0 ist-tooltip-icon-pulse" />
              <div>
                <p className="text-white text-sm font-semibold">You're seeing this for free</p>
                <p className="text-indigo-200 text-xs mt-0.5">Upgrade to download, create more, and unlock premium quality</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Soft Paywall Teaser (bottom sheet after Part 2) ── */}
      {showTeaser && !showPaywall && (
        <div className="fixed bottom-0 left-0 right-0 z-50 ist-teaser-slide" data-testid="paywall-teaser">
          <div className="mx-auto max-w-lg bg-[#12121f] border-t border-x border-indigo-500/20 rounded-t-2xl px-5 py-5 sm:px-6">
            <button onClick={() => { setShowTeaser(false); teaserDismissedRef.current = true; }} className="absolute top-3 right-4 text-slate-600 hover:text-slate-400 text-xs" data-testid="teaser-dismiss">
              Dismiss
            </button>
            <div className="flex items-start gap-3">
              <div className="shrink-0 w-9 h-9 rounded-full bg-amber-500/10 flex items-center justify-center mt-0.5">
                <Zap className="w-4 h-4 text-amber-400" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-white font-semibold text-sm mb-1">Your story is getting intense...</p>
                <p className="text-slate-400 text-xs mb-3">Unlock the next chapter, video, and sharing.</p>
                <button onClick={handleContinueStory} className="w-full py-3 px-4 rounded-xl font-semibold text-white text-sm flex items-center justify-center gap-2 ist-cta-primary transition-all active:scale-[0.98]" data-testid="teaser-cta">
                  <BookOpen className="w-4 h-4" />Continue My Story
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Hard Paywall Modal ───────────────────────────────── */}
      <StoryPaywall
        open={showPaywall}
        onClose={() => setShowPaywall(false)}
        storyTitle={activeStory?.title}
        storyText={latestText}
        source={source}
        storyId={activeStory?.story_id}
        partNumber={partNumber}
        viewCount={paywallViewCount}
      />

      {/* ── P1.2 Visual Reward Preview ────────────────────────── */}
      <VideoRewardPreview
        open={showVideoReward}
        onClose={() => setShowVideoReward(false)}
        onContinue={() => { setShowVideoReward(false); proceedToVideoCheckout(); }}
        storyTitle={activeStory?.title}
        storyText={fullStoryText}
        heroImage={activeStory?.image}
        storyId={activeStory?.story_id}
        source={source}
        priceLabel="₹29"
      />

      <style>{`
        .ist-fadeIn { animation: istFadeIn 0.5s ease-out forwards; }
        @keyframes istFadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
        .ist-dot { animation: istDotPulse 1.2s ease-in-out infinite; }
        @keyframes istDotPulse { 0%, 100% { opacity: 0.4; transform: scale(0.8); } 50% { opacity: 1; transform: scale(1.2); } }
        .ist-fade-out { animation: istContentFadeOut 0.4s ease-in forwards; }
        @keyframes istContentFadeOut { from { opacity: 1; transform: scale(1); } to { opacity: 0; transform: scale(0.98); } }
        .ist-fade-in { animation: istContentFadeIn 0.5s ease-out forwards; }
        @keyframes istContentFadeIn { from { opacity: 0; transform: scale(1.02); } to { opacity: 1; transform: scale(1); } }
        .ist-title-pop { animation: istTitlePop 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) forwards; }
        @keyframes istTitlePop { 0% { transform: scale(0.92); opacity: 0.5; } 50% { transform: scale(1.03); } 100% { transform: scale(1); opacity: 1; } }
        .ist-banner-gen { background: linear-gradient(90deg, rgba(99,102,241,0.9), rgba(139,92,246,0.9)); backdrop-filter: blur(8px); }
        .ist-banner-ready { background: linear-gradient(90deg, rgba(16,185,129,0.9), rgba(52,211,153,0.9)); backdrop-filter: blur(8px); animation: istBannerPulse 1.5s ease-in-out infinite; }
        @keyframes istBannerPulse { 0%, 100% { opacity: 0.95; } 50% { opacity: 1; } }
        .ist-banner-done { background: rgba(16,185,129,0.15); backdrop-filter: blur(8px); border-bottom: 1px solid rgba(16,185,129,0.2); }
        .ist-cta-primary { background: linear-gradient(135deg, #6366f1, #8b5cf6); box-shadow: 0 4px 24px rgba(99,102,241,0.3); }
        .ist-cta-primary:hover { box-shadow: 0 6px 32px rgba(99,102,241,0.45); }
        .ist-cta-pulse { animation: istCtaPulse 3s ease-in-out infinite; }
        @keyframes istCtaPulse { 0%, 100% { box-shadow: 0 4px 24px rgba(99,102,241,0.3); } 50% { box-shadow: 0 6px 36px rgba(99,102,241,0.5); } }
        .ist-sticky-cta { background: linear-gradient(to top, #0a0a10 60%, transparent); padding-bottom: max(0.75rem, env(safe-area-inset-bottom)); }
        .ist-part-appear { animation: istPartAppear 0.6s ease-out forwards; }
        @keyframes istPartAppear { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: none; } }
        .ist-teaser-slide { animation: istTeaserSlide 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
        @keyframes istTeaserSlide { from { transform: translateY(100%); } to { transform: translateY(0); } }
        .ist-tooltip-appear { animation: istTooltipIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
        @keyframes istTooltipIn { from { opacity: 0; transform: translateX(-50%) translateY(10px); } to { opacity: 1; transform: translateX(-50%) translateY(0); } }
        .ist-tooltip-icon-pulse { animation: istTooltipIconPulse 2s ease-in-out infinite; }
        @keyframes istTooltipIconPulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.6; transform: scale(1.15); } }
        .ist-cta-enhanced-pulse { animation: istCtaEnhancedPulse 1.5s ease-in-out infinite; }
        @keyframes istCtaEnhancedPulse { 0%, 100% { box-shadow: 0 4px 24px rgba(99,102,241,0.3); transform: scale(1); } 50% { box-shadow: 0 8px 40px rgba(99,102,241,0.6); transform: scale(1.02); } }
        /* P1 Revenue CTA — outcome-led, attention-grabbing */
        .ist-video-cta {
          background: linear-gradient(135deg, #f59e0b 0%, #ef4444 50%, #ec4899 100%);
          box-shadow: 0 8px 24px -6px rgba(239, 68, 68, 0.5), inset 0 1px 0 rgba(255,255,255,0.18);
        }
        .ist-video-cta:hover { filter: brightness(1.06); }
        .ist-sticky-video-fade { animation: istStickyVideoIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
        @keyframes istStickyVideoIn { from { opacity: 0; transform: translateY(16px) scale(0.95); } to { opacity: 1; transform: translateY(0) scale(1); } }
      `}</style>
    </div>
  );
}
