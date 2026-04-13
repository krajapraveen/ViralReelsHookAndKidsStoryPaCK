import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Zap, PenLine, Target, ArrowRight, Swords, Loader2, Lock } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import { trackFunnel } from '../utils/funnelTracker';

/**
 * QuickActions — 3 differentiated entry paths below the hero.
 * Hero = urgency-driven ("This battle, right now").
 * QuickActions = intent-driven ("Choose YOUR path").
 *
 * Primary: "Enter Battle Instantly" (dominant, AI auto-gen)
 * Secondary: "Write Your Own Entry" (creative control)
 * Tertiary: "Beat the Leader" (competitive remix)
 */
export default function QuickActions() {
  const navigate = useNavigate();
  const [creditStatus, setCreditStatus] = useState(null);
  const [topEntry, setTopEntry] = useState(null);
  const [rootStoryId, setRootStoryId] = useState(null);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    const load = async () => {
      const [statusRes, battleRes] = await Promise.allSettled([
        api.get('/api/stories/battle-entry-status'),
        api.get('/api/stories/hottest-battle'),
      ]);
      if (statusRes.status === 'fulfilled') setCreditStatus(statusRes.value.data);
      if (battleRes.status === 'fulfilled') {
        const b = battleRes.value.data?.battle;
        if (b) {
          setRootStoryId(b.root_story_id);
          if (b.contenders?.[0]) setTopEntry(b.contenders[0]);
        }
      }
    };
    load();
  }, []);

  const freeLeft = creditStatus ? creditStatus.free_remaining : null;
  const needsPayment = creditStatus?.needs_payment;

  const handleAutoEnter = async () => {
    if (generating) return;
    trackFunnel('cta_clicked', { meta: { type: 'quick_actions_auto_enter' } });

    if (needsPayment) {
      window.dispatchEvent(new CustomEvent('show-battle-paywall', { detail: { trigger: 'free_limit' } }));
      return;
    }

    if (!rootStoryId) {
      navigate('/app/story-video-studio', { state: { freshSession: true } });
      return;
    }

    setGenerating(true);
    try {
      const res = await api.post('/api/stories/quick-shot', { root_story_id: rootStoryId });
      if (res.data?.success && res.data.job_id) {
        navigate(`/app/story-video-studio?projectId=${res.data.job_id}`);
      }
    } catch (err) {
      if (err.response?.status === 402) {
        window.dispatchEvent(new CustomEvent('show-battle-paywall', { detail: { trigger: 'free_limit' } }));
      } else {
        toast.error('Generation failed. Try again.');
      }
    } finally {
      setGenerating(false);
    }
  };

  const handleWriteOwn = () => {
    trackFunnel('cta_clicked', { meta: { type: 'quick_actions_write_own' } });
    navigate('/app/story-video-studio', { state: { freshSession: true } });
  };

  const handleBeatLeader = async () => {
    trackFunnel('cta_clicked', { meta: { type: 'quick_actions_beat_leader' } });
    if (topEntry) {
      navigate('/app/story-video-studio', {
        state: {
          freshSession: true,
          remixFrom: {
            title: topEntry.title,
            job_id: topEntry.job_id,
            source: 'beat_leader',
            type: 'battle_remix',
          },
        },
      });
    } else if (rootStoryId) {
      navigate(`/app/story-battle/${rootStoryId}`);
    } else {
      navigate('/app/story-video-studio', { state: { freshSession: true } });
    }
  };

  return (
    <section data-testid="quick-actions">
      <div className="flex items-center gap-2 mb-4">
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.03] p-2">
          <Swords className="w-4 h-4 text-violet-300" />
        </div>
        <h2 className="text-lg font-bold text-white">Choose Your Path</h2>
      </div>

      <div className="grid gap-3 grid-cols-1 sm:grid-cols-4">
        {/* PRIMARY — Enter Battle Instantly (spans 2 cols) */}
        <button
          onClick={handleAutoEnter}
          disabled={generating}
          className="group relative sm:col-span-2 rounded-2xl border border-violet-500/25 bg-gradient-to-br from-violet-600/20 via-violet-600/10 to-fuchsia-600/[0.05] p-5 text-left transition-all duration-200 hover:-translate-y-0.5 hover:border-violet-400/40 hover:shadow-lg hover:shadow-violet-900/20"
          data-testid="quick-action-auto-enter"
        >
          <span className="absolute -top-2.5 left-4 text-[9px] font-bold uppercase tracking-wider bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white px-2.5 py-0.5 rounded-full shadow-sm">
            Fastest path to the leaderboard
          </span>
          <div className="flex items-start justify-between gap-3">
            <div className="rounded-xl border border-violet-400/20 bg-violet-500/15 p-2.5">
              <Zap className="w-5 h-5 text-violet-300" />
            </div>
            {generating
              ? <Loader2 className="w-4 h-4 text-violet-400 animate-spin mt-1" />
              : <ArrowRight className="w-4 h-4 text-slate-500 transition group-hover:translate-x-0.5 group-hover:text-white mt-1" />
            }
          </div>
          <h3 className="mt-3 text-base font-bold text-white">Enter Battle Instantly</h3>
          <p className="mt-1 text-xs leading-relaxed text-slate-400">
            AI creates your battle entry in 10 seconds. You just watch it climb.
          </p>
          <div className="mt-3 flex items-center justify-between">
            <span className="text-xs font-bold text-white">Generate Now</span>
            {creditStatus && (
              <span className={`text-[10px] font-semibold flex items-center gap-1 ${needsPayment ? 'text-amber-400/80' : 'text-emerald-400/80'}`}>
                {needsPayment
                  ? <><Lock className="w-3 h-3" /> Credits required</>
                  : <>{freeLeft > 0 ? `${freeLeft} free entries left` : 'Credits available'}</>
                }
              </span>
            )}
          </div>
        </button>

        {/* SECONDARY — Write Your Own Entry */}
        <button
          onClick={handleWriteOwn}
          className="group rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4 text-left transition-all duration-200 hover:-translate-y-0.5 hover:border-sky-400/20 hover:bg-white/[0.03]"
          data-testid="quick-action-write-own"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="rounded-xl border border-white/[0.06] bg-white/[0.05] p-2.5">
              <PenLine className="w-4 h-4 text-slate-300" />
            </div>
            <ArrowRight className="w-4 h-4 text-slate-500 transition group-hover:translate-x-0.5 group-hover:text-white" />
          </div>
          <h3 className="mt-3 text-sm font-bold text-white">Write Your Own Entry</h3>
          <p className="mt-1 text-xs leading-relaxed text-slate-400">
            Your words, your style. Full creative control.
          </p>
          <p className="mt-3 text-xs font-bold text-slate-300">Open Studio</p>
        </button>

        {/* TERTIARY — Beat the Leader */}
        <button
          onClick={handleBeatLeader}
          className="group rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4 text-left transition-all duration-200 hover:-translate-y-0.5 hover:border-rose-400/20 hover:bg-white/[0.03]"
          data-testid="quick-action-beat-leader"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="rounded-xl border border-white/[0.06] bg-white/[0.05] p-2.5">
              <Target className="w-4 h-4 text-rose-300" />
            </div>
            <ArrowRight className="w-4 h-4 text-slate-500 transition group-hover:translate-x-0.5 group-hover:text-white" />
          </div>
          <h3 className="mt-3 text-sm font-bold text-white">Beat the Leader</h3>
          <p className="mt-1 text-xs leading-relaxed text-slate-400">
            {topEntry
              ? <>Currently #1: <span className="text-white/70">{topEntry.title}</span></>
              : 'See the top entry. Make something better.'
            }
          </p>
          <p className="mt-3 text-xs font-bold text-slate-300">Challenge Now</p>
        </button>
      </div>
    </section>
  );
}
