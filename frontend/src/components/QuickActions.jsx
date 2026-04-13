import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Zap, Wand2, Sparkles, ArrowRight, Swords } from 'lucide-react';
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
      onClick: () => {
        trackFunnel('cta_clicked', { meta: { type: 'quick_actions_quick_shot' } });
        const el = document.querySelector('[data-testid="quick-shot-btn"]');
        if (el) el.click();
        else navigate('/app');
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
      onClick: () => {
        trackFunnel('cta_clicked', { meta: { type: 'quick_actions_remix' } });
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
