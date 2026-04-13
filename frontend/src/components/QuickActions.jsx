import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Zap, Wand2, Sparkles, ArrowRight, Swords } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import { trackFunnel } from '../utils/funnelTracker';

/**
 * QuickActions — 3 big entry buttons below the hero.
 * No thinking required — instant action paths.
 */
export default function QuickActions() {
  const navigate = useNavigate();

  const actions = [
    {
      title: 'Quick Shot',
      description: 'We generate a competitive version for you — no typing, no waiting.',
      icon: Zap,
      gradient: 'from-violet-600/15 to-fuchsia-600/[0.06]',
      border: 'border-violet-500/15 hover:border-violet-400/30',
      cta: 'Post in 10 Seconds',
      recommended: true,
      onClick: async () => {
        trackFunnel('cta_clicked', { meta: { type: 'quick_actions_quick_shot' } });
        // Check credits first
        try {
          const statusRes = await api.get('/api/stories/battle-entry-status');
          if (statusRes.data?.needs_payment) {
            // Dispatch event for paywall — LiveBattleHero listens
            window.dispatchEvent(new CustomEvent('show-battle-paywall', { detail: { trigger: 'free_limit' } }));
            return;
          }
        } catch {}
        // Fire Quick Shot directly
        try {
          const hottest = await api.get('/api/stories/hottest-battle');
          const rootId = hottest.data?.battle?.root_story_id;
          if (!rootId) {
            navigate('/app/story-video-studio', { state: { freshSession: true } });
            return;
          }
          const res = await api.post('/api/stories/quick-shot', { root_story_id: rootId });
          if (res.data?.success && res.data.job_id) {
            navigate(`/app/story-video-studio?projectId=${res.data.job_id}`);
          }
        } catch (err) {
          if (err.response?.status === 402) {
            window.dispatchEvent(new CustomEvent('show-battle-paywall', { detail: { trigger: 'free_limit' } }));
          } else {
            toast.error('Quick Shot failed. Try again.');
          }
        }
      },
    },
    {
      title: 'Create Story',
      description: 'Full control — write your story, pick a style, own the result.',
      icon: Wand2,
      gradient: 'from-sky-600/15 to-cyan-600/[0.06]',
      border: 'border-sky-500/15 hover:border-sky-400/30',
      cta: 'Open Studio',
      recommended: false,
      onClick: () => {
        trackFunnel('cta_clicked', { meta: { type: 'quick_actions_create' } });
        navigate('/app/story-video-studio', { state: { freshSession: true } });
      },
    },
    {
      title: 'Remix Battle',
      description: 'Steal a trending idea. Put your spin on it. Outperform the leader.',
      icon: Sparkles,
      gradient: 'from-rose-600/15 to-orange-600/[0.06]',
      border: 'border-rose-500/15 hover:border-rose-400/30',
      cta: 'Remix Now',
      recommended: false,
      onClick: async () => {
        trackFunnel('cta_clicked', { meta: { type: 'quick_actions_remix' } });
        // Navigate to the hottest battle for remix context
        try {
          const hottest = await api.get('/api/stories/hottest-battle');
          const rootId = hottest.data?.battle?.root_story_id;
          if (rootId) {
            navigate(`/app/story-battle/${rootId}`);
            return;
          }
        } catch {}
        navigate('/app/explore');
      },
    },
  ];

  return (
    <section data-testid="quick-actions">
      <div className="flex items-center gap-2 mb-4">
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.03] p-2">
          <Swords className="w-4 h-4 text-violet-300" />
        </div>
        <h2 className="text-lg font-bold text-white">Jump In Instantly</h2>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {actions.map((a) => {
          const Icon = a.icon;
          return (
            <button
              key={a.title}
              onClick={a.onClick}
              className={`group rounded-2xl border bg-gradient-to-br ${a.gradient} ${a.border} p-4 text-left transition-all duration-200 hover:-translate-y-0.5 hover:bg-white/[0.02] relative`}
              data-testid={`quick-action-${a.title.toLowerCase().replace(/\s+/g, '-')}`}
            >
              {a.recommended && (
                <span className="absolute -top-2 left-4 text-[9px] font-bold uppercase tracking-wider bg-violet-600 text-white px-2 py-0.5 rounded-full">
                  Best move right now
                </span>
              )}
              <div className="flex items-start justify-between gap-3">
                <div className="rounded-xl border border-white/[0.06] bg-white/[0.05] p-2.5">
                  <Icon className="w-4 h-4 text-white" />
                </div>
                <ArrowRight className="w-4 h-4 text-slate-500 transition group-hover:translate-x-0.5 group-hover:text-white" />
              </div>
              <h3 className="mt-3 text-sm font-bold text-white">{a.title}</h3>
              <p className="mt-1 text-xs leading-relaxed text-slate-400">{a.description}</p>
              <p className="mt-3 text-xs font-bold text-white">{a.cta}</p>
            </button>
          );
        })}
      </div>
    </section>
  );
}
