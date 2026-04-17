import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from './ui/button';
import {
  Sparkles, Film, Users, Share2, Trophy,
  ChevronRight, ChevronLeft, X, Rocket
} from 'lucide-react';

const STEPS = [
  {
    id: 'create',
    icon: Sparkles,
    color: 'text-indigo-400',
    bg: 'bg-indigo-500/15',
    title: 'Create Your First Story',
    description: 'Type any idea — a bedtime tale, an adventure, a mystery — and AI turns it into a full cinematic video with scenes, illustrations, voiceover, and music.',
    action: { label: 'Try Story Video Studio', route: '/app/story-video-studio' },
    hint: 'Try: "A brave fox named Finn protects lost animals in an enchanted forest"',
  },
  {
    id: 'series',
    icon: Film,
    color: 'text-cyan-400',
    bg: 'bg-cyan-500/15',
    title: 'Continue Into Episodes',
    description: 'Loved your story? Turn it into a series. AI remembers your characters, world, and plot — each episode builds on the last.',
    action: { label: 'Start a Series', route: '/app/story-series' },
    hint: 'AI suggests what happens next with cliffhangers and story arcs',
  },
  {
    id: 'characters',
    icon: Users,
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/15',
    title: 'Build Persistent Characters',
    description: 'Your characters have memory. Their appearance, personality, and story arc stay consistent across every episode and every tool.',
    action: { label: 'Meet Your Characters', route: '/app/characters' },
    hint: 'Characters auto-detected from Episode 1 — confirm to lock their identity',
  },
  {
    id: 'share',
    icon: Share2,
    color: 'text-pink-400',
    bg: 'bg-pink-500/15',
    title: 'Share Characters & Go Viral',
    description: 'Every character gets a public page. Share it — anyone can create their own story with your character in 1 click.',
    action: null,
    hint: 'No login required for visitors to start creating',
  },
  {
    id: 'rewards',
    icon: Trophy,
    color: 'text-amber-400',
    bg: 'bg-amber-500/15',
    title: 'Earn Rewards & Keep Going',
    description: 'Hit milestones at 3, 5, and 10 episodes. Unlock Season 2, alternate endings, spinoffs — and bonus credits.',
    action: null,
    hint: 'Completion triggers the next creative loop automatically',
  },
];

export default function QuickStartGuide({ onDismiss }) {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const current = STEPS[step];
  const Icon = current.icon;

  const next = () => step < STEPS.length - 1 && setStep(step + 1);
  const prev = () => step > 0 && setStep(step - 1);

  const handleAction = () => {
    if (current.action?.route) {
      onDismiss();
      navigate(current.action.route);
    }
  };

  const handleFinish = () => {
    localStorage.setItem('quickstart_seen', 'true');
    onDismiss();
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4" data-testid="quick-start-guide">
      <div className="w-full max-w-lg mx-4 bg-slate-900 border border-slate-700/50 rounded-2xl overflow-hidden shadow-2xl">
        {/* Close */}
        <div className="flex justify-end p-3 pb-0">
          <button onClick={handleFinish} className="text-slate-500 hover:text-white transition-colors p-1" data-testid="close-quickstart">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="px-8 pb-4 text-center">
          {/* Step indicator */}
          <div className="flex items-center justify-center gap-1.5 mb-6">
            {STEPS.map((_, i) => (
              <div
                key={i}
                className={`h-1 rounded-full transition-all ${
                  i === step ? 'w-6 bg-indigo-500' : i < step ? 'w-3 bg-indigo-500/40' : 'w-3 bg-slate-700'
                }`}
              />
            ))}
          </div>

          {/* Icon */}
          <div className={`w-16 h-16 rounded-2xl ${current.bg} mx-auto mb-5 flex items-center justify-center`}>
            <Icon className={`w-8 h-8 ${current.color}`} />
          </div>

          {/* Title */}
          <h2 className="text-xl font-bold text-white mb-2" data-testid="quickstart-title">
            {current.title}
          </h2>

          {/* Description */}
          <p className="text-sm text-slate-300 leading-relaxed mb-4 max-w-sm mx-auto">
            {current.description}
          </p>

          {/* Hint */}
          <div className="bg-slate-800/60 border border-slate-700/40 rounded-lg px-4 py-2.5 mb-6 inline-block">
            <p className="text-xs text-slate-400">
              <span className="text-indigo-400 font-medium">Tip:</span> {current.hint}
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="px-8 pb-8 flex items-center gap-3">
          <Button
            onClick={prev}
            variant="ghost"
            disabled={step === 0}
            className="text-slate-400 hover:text-white h-10"
            data-testid="quickstart-prev"
          >
            <ChevronLeft className="w-4 h-4" />
          </Button>

          <div className="flex-1 flex gap-2">
            {current.action && (
              <Button
                onClick={handleAction}
                className="flex-1 h-10 bg-indigo-600 hover:bg-indigo-700 text-white text-sm"
                data-testid="quickstart-action"
              >
                {current.action.label}
                <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            )}

            {step < STEPS.length - 1 ? (
              <Button
                onClick={next}
                variant={current.action ? 'outline' : 'default'}
                className={current.action ? 'border-slate-700 text-slate-300 h-10' : 'flex-1 h-10 bg-indigo-600 hover:bg-indigo-700 text-white text-sm'}
                data-testid="quickstart-next"
              >
                Next
                <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            ) : (
              <Button
                onClick={handleFinish}
                className="flex-1 h-10 bg-emerald-600 hover:bg-emerald-700 text-white text-sm"
                data-testid="quickstart-finish"
              >
                <Rocket className="w-4 h-4 mr-1" />
                Start Creating
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
