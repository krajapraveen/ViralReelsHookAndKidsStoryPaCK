import { useProductGuide } from '../../contexts/ProductGuideContext';
import { CheckCircle2 } from 'lucide-react';

const STEP_LABELS = ['Create', 'Customize', 'Generate', 'View', 'Share'];
const STEP_ICONS = ['1', '2', '3', '4', '5'];

export default function JourneyProgressBar() {
  const { progress, journeySteps } = useProductGuide();

  if (!progress || progress.guide_dismissed) return null;

  const completedSteps = progress.completed_steps || [];
  const completedCount = completedSteps.length;
  const percent = Math.round((completedCount / journeySteps.length) * 100);

  return (
    <div
      className="w-full bg-slate-900/80 backdrop-blur-lg border-b border-slate-800/60 px-3 py-2 z-[10000] sticky top-0"
      data-testid="journey-progress-bar"
    >
      <div className="max-w-4xl mx-auto">
        {/* Desktop: full step labels */}
        <div className="hidden md:flex items-center justify-between gap-1">
          {journeySteps.map((step, i) => {
            const done = completedSteps.includes(step.id);
            const isCurrent = step.id === progress.current_step;
            return (
              <div key={step.id} className="flex items-center flex-1">
                <div className="flex items-center gap-1.5">
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-all duration-300 ${
                      done
                        ? 'bg-emerald-500 text-white'
                        : isCurrent
                        ? 'bg-indigo-500 text-white ring-2 ring-indigo-400/50'
                        : 'bg-slate-700 text-slate-500'
                    }`}
                  >
                    {done ? <CheckCircle2 className="w-3.5 h-3.5" /> : STEP_ICONS[i]}
                  </div>
                  <span
                    className={`text-xs font-medium ${
                      done ? 'text-emerald-400' : isCurrent ? 'text-indigo-300' : 'text-slate-500'
                    }`}
                  >
                    {STEP_LABELS[i]}
                  </span>
                </div>
                {i < journeySteps.length - 1 && (
                  <div className={`flex-1 h-px mx-2 transition-colors duration-300 ${done ? 'bg-emerald-500/50' : 'bg-slate-700'}`} />
                )}
              </div>
            );
          })}
          <span className="text-xs font-bold text-indigo-400 ml-2 whitespace-nowrap">{percent}%</span>
        </div>

        {/* Mobile: compact progress bar */}
        <div className="md:hidden">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] text-slate-400 font-medium">
              {completedCount === 0
                ? 'Start your journey'
                : `Step ${Math.min(completedCount + 1, journeySteps.length)} of ${journeySteps.length}`}
            </span>
            <span className="text-[10px] text-indigo-400 font-bold">{percent}%</span>
          </div>
          <div className="flex gap-1">
            {journeySteps.map((step, i) => {
              const done = completedSteps.includes(step.id);
              const isCurrent = step.id === progress.current_step;
              return (
                <div
                  key={step.id}
                  className={`flex-1 h-1.5 rounded-full transition-all duration-300 ${
                    done ? 'bg-emerald-500' : isCurrent ? 'bg-indigo-500' : 'bg-slate-700'
                  }`}
                />
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
