/* eslint-disable react/prop-types */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  X, Film, Swords, RefreshCw, ArrowRight, Sparkles, Clock, Lightbulb,
  CheckCircle2, AlertTriangle, ChevronRight, Wand2, Trophy, Users, BookOpen,
} from 'lucide-react';
import { trackFunnel } from './funnelTracker';

/**
 * P0 In-Product Guided Experience for Story-to-Video ecosystem.
 * One component, four actions, single config table.
 *
 *   useActionGuide('story_video') → { open, runWithGuide, hide }
 *
 *   runWithGuide(callback) opens the guide on first-time use OR fires
 *   `callback` immediately if the user has already seen it. The guide's
 *   primary CTA always invokes `callback`.
 *
 * Telemetry (every action, every event):
 *   guide_opened · guide_completed · skipped_guide
 *   started_after_guide · battle_after_guide · remix_after_guide · continue_after_guide
 */

const STORAGE_PREFIX = 'guide_seen_';

const GUIDES = {
  story_video: {
    id: 'story_video',
    title: 'Story to Video',
    accent: 'from-violet-500 to-fuchsia-500',
    accentRing: 'border-violet-500/30 shadow-[0_0_36px_rgba(168,85,247,0.18)]',
    icon: Film,
    iconBg: 'bg-violet-500/15 text-violet-300',
    eta: 'Usually takes ~1 minute',
    bestChoice: 'Best for completed videos',
    meaning: 'Turn any story idea into a cinematic AI video — scenes, voice-over, captions, music — ready to share.',
    steps: [
      { label: 'Enter your story prompt' },
      { label: 'Pick a style' },
      { label: 'Generate scenes' },
      { label: 'Preview & polish' },
      { label: 'Export & share' },
    ],
    bestPractices: [
      'Strong opening hook beats long setup — first 2 seconds matter most',
      'Concrete details ("a boy with a glowing pocket-watch") beat abstract ideas',
      'Pick a single emotion and lean into it (wonder, dread, joy, awe)',
    ],
    afterClick: 'Prompt → Scenes → Images → Voice → Preview → Final Video',
    expectedResult: 'A 30–60s polished video with voice-over and captions, exportable to YouTube Shorts, Reels and 9:16 mobile.',
    avoid: [
      'Vague prompts like "a cool story" — the AI will improvise',
      'Walls of text — keep it under 3 sentences',
      'Skipping the preview — small fixes save expensive re-renders',
    ],
    motivation: 'Top creators outline the hook before pressing generate.',
    primaryCta: 'Start Creating',
  },

  remix: {
    id: 'remix',
    title: 'Remix',
    accent: 'from-cyan-400 to-blue-500',
    accentRing: 'border-cyan-500/30 shadow-[0_0_36px_rgba(6,182,212,0.18)]',
    icon: RefreshCw,
    iconBg: 'bg-cyan-500/15 text-cyan-300',
    eta: 'Usually takes ~30 seconds',
    bestChoice: 'Best for growth & reach',
    meaning: 'Take any story already in the system and create your own better, weirder, funnier or more emotional version of it.',
    steps: [
      { label: 'Pick what to change (style / ending / tone)' },
      { label: 'Add your twist' },
      { label: 'Regenerate' },
      { label: 'Compare versions' },
      { label: 'Publish your remix' },
    ],
    bestPractices: [
      'Change ONE thing per remix — too many edits dilute the hook',
      'Match the audience: kids → wonder, teens → tension, adults → twist',
      'Reel-format remixes (9:16) outperform horizontal 3-to-1 in shares',
    ],
    afterClick: 'You land in the studio with the original story pre-filled. Edit. Regenerate. Publish.',
    expectedResult: 'Your own version, credited as a remix of the original. Both creators get credit weight.',
    avoid: [
      'Copying without changing anything meaningful',
      'Removing the emotional beat that made the original work',
    ],
    motivation: 'Top creators remix viral stories within hours of trending.',
    primaryCta: 'Remix This Story',
  },

  continue: {
    id: 'continue',
    title: 'Continue Story',
    accent: 'from-amber-400 to-orange-500',
    accentRing: 'border-amber-500/30 shadow-[0_0_36px_rgba(251,146,60,0.18)]',
    icon: ArrowRight,
    iconBg: 'bg-amber-500/15 text-amber-300',
    eta: 'Usually takes ~20 seconds',
    bestChoice: 'Best for retention',
    meaning: 'Generate Part 2 / sequel / next chapter of the story you just watched.',
    steps: [
      { label: 'Tap Continue' },
      { label: 'Pick a direction (twist / villain / new world)' },
      { label: 'Generate Part 2' },
      { label: 'Read & continue Part 3' },
      { label: 'Save the series' },
    ],
    bestPractices: [
      'Cliffhanger endings drive Part 2 clicks 2x more than tidy resolutions',
      'Bring back the villain — series with recurring antagonists go deeper',
      'Three parts is the sweet spot — viewers commit, you keep credit cost low',
    ],
    afterClick: 'Part 2 generates in ~20s, picking up exactly where Part 1 left off.',
    expectedResult: 'A continuation that respects the first part\'s tone, characters and emotional core.',
    avoid: [
      'Resetting characters or rules between parts',
      'Burning every plot card in Part 2 — leave room for Part 3',
    ],
    motivation: 'Series stories get more repeat viewers than one-shots.',
    primaryCta: 'Create Part 2',
  },

  battle: {
    id: 'battle',
    title: 'Story Battle',
    accent: 'from-rose-500 to-pink-500',
    accentRing: 'border-rose-500/30 shadow-[0_0_36px_rgba(244,63,94,0.18)]',
    icon: Swords,
    iconBg: 'bg-rose-500/15 text-rose-300',
    eta: 'Battle runs for 24h',
    bestChoice: 'Best for visibility',
    meaning: 'Your story competes head-to-head against another. Audience votes. Winner trends, loser learns.',
    steps: [
      { label: 'Pick or generate your contender story' },
      { label: 'Polish title + thumbnail (these win battles)' },
      { label: 'Enter the battle' },
      { label: 'Share the battle link' },
      { label: 'Track rank as votes come in' },
    ],
    bestPractices: [
      'Title carries 60% of the vote weight — front-load the hook',
      'Strong thumbnail = strong stop-the-scroll. Faces > objects',
      'Share within 30 minutes of entering — early votes compound',
    ],
    afterClick: 'You go to the Battle arena where your story is paired with a contender.',
    expectedResult: 'A live battle page with vote counts, share link, and a leaderboard slot.',
    avoid: [
      'Entering without polishing the title',
      'Forgetting to share — quiet battles die unseen',
    ],
    motivation: 'Battle winners trend faster across the platform.',
    primaryCta: 'Enter Battle',
  },
};

const ICON_LIB = { Sparkles, Clock, Lightbulb, CheckCircle2, AlertTriangle, ChevronRight, Wand2, Trophy, Users, BookOpen };

const COMPLETION_EVENT = {
  story_video: 'started_after_guide',
  remix:       'remix_after_guide',
  continue:    'continue_after_guide',
  battle:      'battle_after_guide',
};

// ─── Imperative store (single drawer instance, anywhere) ───────────────────
let _setOpen = null;
function _emitOpen(payload) {
  if (_setOpen) _setOpen(payload);
}

/**
 * useActionGuide(actionId)
 *   → runWithGuide(callback): if first-time → open guide; on confirm fires callback.
 *                             else → fire callback immediately.
 *   → openGuide(): force-open regardless of seen state (e.g. "What should I do?" button)
 */
export function useActionGuide(actionId) {
  const runWithGuide = useCallback((onConfirm) => {
    const seen = (() => { try { return localStorage.getItem(STORAGE_PREFIX + actionId) === '1'; } catch { return false; } })();
    if (seen) {
      try { onConfirm?.(); } catch (e) { console.error(e); }
      return;
    }
    _emitOpen({ actionId, onConfirm });
  }, [actionId]);

  const openGuide = useCallback((onConfirm) => {
    _emitOpen({ actionId, onConfirm, forced: true });
  }, [actionId]);

  return { runWithGuide, openGuide };
}

/**
 * <ActionGuideMount /> — drop ONCE near root, listens to imperative open events.
 */
export function ActionGuideMount() {
  const [state, setState] = useState(null);
  useEffect(() => {
    _setOpen = setState;
    return () => { _setOpen = null; };
  }, []);

  if (!state) return null;
  return (
    <ActionGuideDrawer
      payload={state}
      onClose={() => setState(null)}
    />
  );
}

// ─── The drawer itself (right on desktop, bottom sheet on mobile) ──────────

function ActionGuideDrawer({ payload, onClose }) {
  const guide = GUIDES[payload.actionId];
  const Icon = guide?.icon || Film;
  const openedAtRef = useRef(Date.now());
  const [dontShowAgain, setDontShowAgain] = useState(false);

  useEffect(() => {
    if (!guide) return;
    try {
      trackFunnel('guide_opened', {
        meta: { action_id: guide.id, forced: !!payload.forced },
      });
    } catch {}
  }, [guide, payload.forced]);

  const finishAndConfirm = useCallback(() => {
    if (!guide) return;
    try {
      const elapsed = Date.now() - openedAtRef.current;
      if (dontShowAgain || !payload.forced) {
        localStorage.setItem(STORAGE_PREFIX + guide.id, '1');
      }
      trackFunnel('guide_completed', {
        meta: { action_id: guide.id, elapsed_ms: elapsed, dont_show_again: dontShowAgain },
      });
      const ev = COMPLETION_EVENT[guide.id];
      if (ev) trackFunnel(ev, { meta: { action_id: guide.id } });
    } catch {}
    onClose();
    try { payload.onConfirm?.(); } catch (e) { console.error(e); }
  }, [guide, payload, dontShowAgain, onClose]);

  const skip = useCallback(() => {
    if (!guide) return;
    try {
      trackFunnel('skipped_guide', {
        meta: { action_id: guide.id, elapsed_ms: Date.now() - openedAtRef.current },
      });
      if (dontShowAgain) localStorage.setItem(STORAGE_PREFIX + guide.id, '1');
    } catch {}
    onClose();
  }, [guide, dontShowAgain, onClose]);

  if (!guide) return null;

  return (
    <div
      className="fixed inset-0 z-[10001] flex items-end sm:items-stretch sm:justify-end"
      data-testid={`action-guide-${guide.id}`}
      role="dialog"
      aria-modal="true"
      aria-label={`${guide.title} guide`}
    >
      <div className="absolute inset-0 bg-black/70 backdrop-blur-md ag-fade" onClick={skip} />

      <aside
        className={`relative w-full sm:max-w-md sm:h-full bg-[#0c0c14]/95 backdrop-blur-xl border ${guide.accentRing}
                    sm:rounded-l-3xl sm:border-l rounded-t-3xl overflow-hidden flex flex-col
                    max-h-[92vh] sm:max-h-none ag-slide`}
        data-testid="action-guide-drawer"
      >
        {/* Accent strip */}
        <div className={`h-1 w-full bg-gradient-to-r ${guide.accent}`} />

        {/* Header */}
        <header className="flex items-start gap-3 px-5 sm:px-6 pt-5 pb-3">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${guide.iconBg}`}>
            <Icon className="w-5 h-5" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-xl font-bold text-white truncate" data-testid="ag-title">{guide.title}</h2>
              <span className={`text-[10px] uppercase tracking-widest font-bold px-2 py-0.5 rounded-full bg-gradient-to-r ${guide.accent} text-white`}>
                {guide.bestChoice}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 flex items-center gap-1.5" data-testid="ag-eta">
              <Clock className="w-3 h-3" /> {guide.eta}
            </p>
          </div>
          <button
            onClick={skip}
            className="p-1.5 rounded-full hover:bg-white/10 transition-colors"
            aria-label="Close guide"
            data-testid="ag-close-btn"
          >
            <X className="w-4 h-4 text-slate-400" />
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-5 sm:px-6 pb-4 space-y-5">
          {/* Meaning */}
          <section data-testid="ag-meaning">
            <p className="text-sm text-slate-200 leading-relaxed">{guide.meaning}</p>
          </section>

          {/* Steps */}
          <section data-testid="ag-steps">
            <h3 className="text-[11px] font-bold uppercase tracking-widest text-slate-500 mb-2 flex items-center gap-1">
              <Wand2 className="w-3 h-3" /> What you'll do
            </h3>
            <ol className="space-y-1.5">
              {guide.steps.map((s, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-200">
                  <span className={`shrink-0 w-5 h-5 rounded-full bg-gradient-to-br ${guide.accent} text-white text-[11px] font-bold flex items-center justify-center mt-0.5`}>
                    {i + 1}
                  </span>
                  <span className="leading-snug">{s.label}</span>
                </li>
              ))}
            </ol>
          </section>

          {/* Best Practices */}
          <section data-testid="ag-best-practices">
            <h3 className="text-[11px] font-bold uppercase tracking-widest text-emerald-400 mb-2 flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" /> Best practices
            </h3>
            <ul className="space-y-1.5">
              {guide.bestPractices.map((bp, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                  <span className="text-emerald-400 shrink-0 mt-1">•</span>
                  <span className="leading-snug">{bp}</span>
                </li>
              ))}
            </ul>
          </section>

          {/* What happens next */}
          <section data-testid="ag-after-click" className="rounded-xl border border-white/5 bg-white/[0.02] p-3">
            <h3 className="text-[11px] font-bold uppercase tracking-widest text-slate-400 mb-1.5 flex items-center gap-1">
              <ChevronRight className="w-3 h-3" /> After you click
            </h3>
            <p className="text-xs text-slate-300 leading-relaxed">{guide.afterClick}</p>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed italic">→ {guide.expectedResult}</p>
          </section>

          {/* Avoid */}
          <section data-testid="ag-avoid">
            <h3 className="text-[11px] font-bold uppercase tracking-widest text-rose-400 mb-2 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" /> Mistakes to avoid
            </h3>
            <ul className="space-y-1.5">
              {guide.avoid.map((a, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                  <span className="text-rose-400 shrink-0 mt-1">×</span>
                  <span className="leading-snug">{a}</span>
                </li>
              ))}
            </ul>
          </section>

          {/* Motivation */}
          <section data-testid="ag-motivation" className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3">
            <p className="text-xs text-amber-200 leading-relaxed flex items-start gap-1.5">
              <Sparkles className="w-3 h-3 mt-0.5 shrink-0" />
              <span>{guide.motivation}</span>
            </p>
          </section>
        </div>

        {/* Footer */}
        <footer
          className="px-5 sm:px-6 pt-3 pb-5 border-t border-white/5 bg-[#0c0c14]/60"
          style={{ paddingBottom: 'max(1.25rem, env(safe-area-inset-bottom))' }}
        >
          <button
            onClick={finishAndConfirm}
            className={`w-full py-3.5 px-5 rounded-xl font-bold text-white text-base flex items-center justify-center gap-2 active:scale-[0.98] transition-transform bg-gradient-to-r ${guide.accent} shadow-lg`}
            data-testid="ag-primary-cta"
          >
            <Sparkles className="w-4 h-4" />
            {guide.primaryCta}
          </button>
          <div className="mt-3 flex items-center justify-between text-xs">
            <label className="flex items-center gap-2 text-slate-400 cursor-pointer">
              <input
                type="checkbox"
                checked={dontShowAgain}
                onChange={(e) => setDontShowAgain(e.target.checked)}
                className="accent-emerald-500"
                data-testid="ag-dont-show"
              />
              Don't show again
            </label>
            <button
              onClick={skip}
              className="text-slate-500 hover:text-white transition-colors"
              data-testid="ag-skip"
            >
              Skip
            </button>
          </div>
        </footer>
      </aside>

      <style>{`
        .ag-fade { animation: agFade 0.28s ease-out forwards; }
        @keyframes agFade { from { opacity: 0; } to { opacity: 1; } }
        .ag-slide { animation: agSlideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
        @keyframes agSlideUp { from { transform: translateY(40px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        @media (min-width: 640px) {
          .ag-slide { animation: agSlideRight 0.42s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
          @keyframes agSlideRight { from { transform: translateX(40px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        }
      `}</style>
    </div>
  );
}

export const ACTION_GUIDES = GUIDES;
export { ICON_LIB };
