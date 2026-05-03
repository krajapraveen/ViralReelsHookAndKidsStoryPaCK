import React from 'react';
import { Zap, Mic, Users, LayoutTemplate, ArrowRight, ArrowLeft } from 'lucide-react';
import { SectionTitle, DemoBadge } from './shared';

const TYPES = [
  {
    id: 'quick_avatar',
    icon: Zap,
    name: 'Quick Avatar',
    tagline: 'One photo → talking clone',
    time: '~30s',
    description: 'Drop a selfie. We generate a short intro reel with a generic synthesized voice. Perfect for first reactions.',
    color: 'from-violet-500 to-fuchsia-500',
    border: 'border-violet-500/40',
  },
  {
    id: 'voice_matched',
    icon: Mic,
    name: 'Voice-Matched',
    tagline: 'Your face + your voice',
    time: '~45s',
    description: 'Add a 10-second voice sample. The avatar speaks in your cloned voice — not a synth preset.',
    color: 'from-cyan-500 to-sky-500',
    border: 'border-cyan-500/40',
  },
  {
    id: 'motion',
    icon: Users,
    name: 'Motion Avatar',
    tagline: 'Gestures + body language',
    time: '~60s',
    description: 'Full-body motion: gestures, nods, walking frame. Best for longer videos and storytelling.',
    color: 'from-emerald-500 to-teal-500',
    border: 'border-emerald-500/40',
  },
  {
    id: 'template',
    icon: LayoutTemplate,
    name: 'From Template',
    tagline: 'Pre-built scripts + styles',
    time: '~30s',
    description: 'Pick a proven format (Intro, Course Welcome, Product Demo). We prefill the script — just tweak.',
    color: 'from-amber-500 to-orange-500',
    border: 'border-amber-500/40',
  },
];

export default function AvatarTypeStep({ value, onChange, onBack, onNext }) {
  return (
    <div className="space-y-6" data-testid="avatar-studio-type-step">
      <div className="flex items-center justify-between">
        <button onClick={onBack} className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-white"
                data-testid="avatar-studio-type-back-btn">
          <ArrowLeft className="w-4 h-4" /> Library
        </button>
        <DemoBadge />
      </div>
      <SectionTitle
        eyebrow="Step 1 of 5"
        title="What kind of avatar do you want?"
        sub="Pick the style that matches your content. You can switch types later — this is just your starting point."
      />
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {TYPES.map(t => {
          const Icon = t.icon;
          const active = value === t.id;
          return (
            <button
              key={t.id}
              onClick={() => onChange(t.id)}
              className={`group text-left p-5 rounded-2xl border-2 transition-all ${
                active ? `${t.border} bg-white/[0.06] ring-2 ring-violet-500/30` : 'border-white/10 bg-white/[0.02] hover:border-white/20'
              }`}
              data-testid={`avatar-studio-type-tile-${t.id}`}
              aria-pressed={active}
            >
              <div className="flex items-start gap-3">
                <div className={`w-11 h-11 rounded-xl bg-gradient-to-br ${t.color} flex items-center justify-center shrink-0`}>
                  <Icon className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-base font-bold text-white">{t.name}</span>
                    <span className="text-[10px] font-semibold text-slate-400 bg-white/5 px-1.5 py-0.5 rounded border border-white/10">
                      {t.time}
                    </span>
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5">{t.tagline}</div>
                  <div className="text-xs text-slate-500 mt-2 leading-relaxed">{t.description}</div>
                </div>
              </div>
            </button>
          );
        })}
      </div>
      <div className="flex justify-end">
        <button
          onClick={onNext}
          disabled={!value}
          className="px-6 py-3 rounded-xl font-bold text-white bg-gradient-to-r from-violet-600 to-fuchsia-600 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
          data-testid="avatar-studio-type-next-btn"
        >
          Continue to upload <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
