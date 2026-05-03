import React from 'react';
import { ArrowLeft, ArrowRight, User, Hand, Film, Camera } from 'lucide-react';
import { SectionTitle } from './shared';

const MOTIONS = [
  {
    id: 'talking_head',
    icon: User,
    name: 'Talking Head',
    tagline: 'Classic reel / podcast framing',
    description: 'Static camera, your face in frame, lip-sync on a scripted voiceover. Best for ≤30s clips.',
  },
  {
    id: 'gesture',
    icon: Hand,
    name: 'Gesture-Led',
    tagline: 'Subtle hands + upper-body motion',
    description: 'Natural gestures make longer explanations feel alive. Best for 30–60s clips.',
  },
  {
    id: 'full_body',
    icon: Film,
    name: 'Full-Body Motion',
    tagline: 'Walking frame, full-body avatar',
    description: 'Wide shot with a walking or standing avatar. Best for cinematic intros or long-form.',
  },
  {
    id: 'static',
    icon: Camera,
    name: 'Static Portrait',
    tagline: 'No motion, pure voiceover',
    description: 'Still image with audio. Use when you want the voice to carry the message.',
  },
];

const DURATIONS = [
  { value: 15, label: '15s',  hint: 'Reel' },
  { value: 30, label: '30s',  hint: 'Short' },
  { value: 45, label: '45s',  hint: 'Standard' },
  { value: 60, label: '60s',  hint: 'Long reel' },
  { value: 90, label: '90s',  hint: 'Longform' },
];

export default function MotionStep({
  motionStyle,
  onMotionChange,
  duration,
  onDurationChange,
  onBack,
  onNext,
}) {
  return (
    <div className="space-y-6" data-testid="avatar-studio-motion-step">
      <div className="flex items-center justify-between">
        <button onClick={onBack} className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-white"
                data-testid="avatar-studio-motion-back-btn">
          <ArrowLeft className="w-4 h-4" /> Back to upload
        </button>
      </div>
      <SectionTitle
        eyebrow="Step 3 of 5"
        title="Choose motion + length"
        sub="This sets how your avatar moves on-screen and how long the final clip is. Longer clips take a bit more time."
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {MOTIONS.map(m => {
          const Icon = m.icon;
          const active = motionStyle === m.id;
          return (
            <button
              key={m.id}
              onClick={() => onMotionChange(m.id)}
              className={`text-left p-4 rounded-2xl border-2 transition-all ${
                active ? 'border-violet-500 bg-violet-500/10 ring-2 ring-violet-500/30' : 'border-white/10 bg-white/[0.02] hover:border-white/20'
              }`}
              data-testid={`avatar-studio-motion-tile-${m.id}`}
              aria-pressed={active}
            >
              <div className="flex items-start gap-3">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${active ? 'bg-violet-500/30' : 'bg-white/5'}`}>
                  <Icon className={`w-5 h-5 ${active ? 'text-violet-200' : 'text-slate-300'}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-bold text-white">{m.name}</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">{m.tagline}</div>
                  <div className="text-xs text-slate-500 mt-1.5 leading-relaxed">{m.description}</div>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      <div>
        <div className="text-sm font-semibold text-white mb-2">Output length</div>
        <div className="flex flex-wrap gap-2" data-testid="avatar-studio-motion-duration-group">
          {DURATIONS.map(d => {
            const active = duration === d.value;
            return (
              <button
                key={d.value}
                onClick={() => onDurationChange(d.value)}
                className={`px-4 py-2.5 rounded-xl border-2 text-sm font-bold transition-colors ${
                  active ? 'border-violet-500 bg-violet-500/20 text-white' : 'border-white/10 bg-white/[0.02] text-slate-300 hover:border-white/20'
                }`}
                data-testid={`avatar-studio-motion-duration-${d.value}`}
                aria-pressed={active}
              >
                <div>{d.label}</div>
                <div className="text-[10px] font-normal text-slate-400">{d.hint}</div>
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={onNext}
          disabled={!motionStyle || !duration}
          className="px-6 py-3 rounded-xl font-bold text-white bg-gradient-to-r from-violet-600 to-fuchsia-600 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
          data-testid="avatar-studio-motion-next-btn"
        >
          Continue to safety <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
