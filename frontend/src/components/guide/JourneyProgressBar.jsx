import { useProductGuide } from '../../contexts/ProductGuideContext';
import { Check } from 'lucide-react';

export default function JourneyProgressBar() {
  const { progress, journeySteps } = useProductGuide();

  if (!progress || !journeySteps.length) return null;

  const completed = progress.completed_steps || [];
  const current = progress.current_step || 'create';
  const currentIdx = journeySteps.findIndex(s => s.id === current);

  return (
    <div
      className="w-full bg-slate-900/80 backdrop-blur-lg border-b border-slate-800/60 px-3 py-2 lg:hidden z-[10000] relative"
      data-testid="journey-progress-bar"
    >
      <div className="max-w-lg mx-auto flex items-center gap-1">
        {journeySteps.map((step, i) => {
          const isDone = completed.includes(step.id);
          const isCurrent = step.id === current;
          const isPast = i < currentIdx;

          return (
            <div key={step.id} className="flex items-center flex-1 min-w-0">
              {/* Step indicator */}
              <div className="flex flex-col items-center gap-0.5 flex-shrink-0">
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-all duration-300 ${
                    isDone
                      ? 'bg-emerald-500 text-white'
                      : isCurrent
                        ? 'bg-indigo-500 text-white ring-2 ring-indigo-400/50 ring-offset-1 ring-offset-slate-900'
                        : 'bg-slate-700 text-slate-500'
                  }`}
                  data-testid={`journey-step-${step.id}`}
                >
                  {isDone ? <Check className="w-3.5 h-3.5" /> : i + 1}
                </div>
                <span
                  className={`text-[9px] font-medium truncate max-w-[48px] text-center ${
                    isCurrent ? 'text-indigo-400' : isDone ? 'text-emerald-400' : 'text-slate-600'
                  }`}
                >
                  {step.label}
                </span>
              </div>

              {/* Connector line */}
              {i < journeySteps.length - 1 && (
                <div
                  className={`flex-1 h-[2px] mx-1 rounded-full transition-all duration-500 ${
                    isDone || isPast ? 'bg-emerald-500/60' : 'bg-slate-700/40'
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
