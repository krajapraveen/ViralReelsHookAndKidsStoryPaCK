/**
 * Real-Time Progress Panel
 * Shows detailed progress during long-running generation jobs
 */
import React from 'react';
import { Progress } from './ui/progress';
import { 
  Loader2, CheckCircle, XCircle, Clock, 
  Sparkles, Image, Mic, Film, Wand2 
} from 'lucide-react';

// Stage icons mapping
const STAGE_ICONS = {
  scene_generation: Sparkles,
  image_generation: Image,
  voice_generation: Mic,
  video_assembly: Film,
  complete: CheckCircle,
  failed: XCircle,
  default: Wand2
};

// Stage colors
const STAGE_COLORS = {
  scene_generation: 'text-purple-400',
  image_generation: 'text-blue-400',
  voice_generation: 'text-green-400',
  video_assembly: 'text-amber-400',
  complete: 'text-emerald-400',
  failed: 'text-red-400',
  default: 'text-slate-400'
};

// Progress step component
const ProgressStep = ({ step, isActive, isComplete, isFailed }) => {
  const Icon = STAGE_ICONS[step.stage] || STAGE_ICONS.default;
  const colorClass = isComplete 
    ? 'text-emerald-400' 
    : isFailed 
    ? 'text-red-400' 
    : isActive 
    ? STAGE_COLORS[step.stage] || STAGE_COLORS.default
    : 'text-slate-600';
  
  return (
    <div className={`flex items-center gap-3 p-3 rounded-lg transition-all ${
      isActive ? 'bg-slate-800/50 border border-slate-600' : ''
    }`}>
      <div className={`relative ${colorClass}`}>
        {isActive && !isComplete && (
          <div className="absolute inset-0 animate-ping">
            <Icon className="w-5 h-5 opacity-50" />
          </div>
        )}
        <Icon className={`w-5 h-5 relative ${isActive && !isComplete ? 'animate-pulse' : ''}`} />
      </div>
      <div className="flex-1 min-w-0">
        <p className={`text-sm font-medium ${isComplete ? 'text-emerald-400' : isFailed ? 'text-red-400' : isActive ? 'text-white' : 'text-slate-500'}`}>
          {step.label}
        </p>
        {isActive && step.detail && (
          <p className="text-xs text-slate-400 truncate">{step.detail}</p>
        )}
      </div>
      {isComplete && <CheckCircle className="w-4 h-4 text-emerald-400" />}
      {isFailed && <XCircle className="w-4 h-4 text-red-400" />}
      {isActive && !isComplete && !isFailed && (
        <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
      )}
    </div>
  );
};

// Main progress panel
export const RealTimeProgressPanel = ({ 
  progress, 
  steps = [],
  title = "Generation Progress",
  className = "" 
}) => {
  if (!progress) return null;

  const {
    stage,
    progress: progressPercent = 0,
    current_step = 0,
    total_steps = 1,
    message = '',
    status = 'running',
    estimated_remaining
  } = progress;

  const isComplete = status === 'completed';
  const isFailed = status === 'failed';

  // Default steps if none provided
  const defaultSteps = [
    { stage: 'scene_generation', label: 'Generating Scenes', detail: '' },
    { stage: 'image_generation', label: 'Creating Images', detail: '' },
    { stage: 'voice_generation', label: 'Recording Narration', detail: '' },
    { stage: 'video_assembly', label: 'Rendering Video', detail: '' }
  ];

  const displaySteps = steps.length > 0 ? steps : defaultSteps;
  const currentStageIndex = displaySteps.findIndex(s => s.stage === stage);

  return (
    <div className={`bg-gradient-to-br from-slate-900 to-slate-800 rounded-xl border border-slate-700/50 p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          {isComplete ? (
            <CheckCircle className="w-5 h-5 text-emerald-400" />
          ) : isFailed ? (
            <XCircle className="w-5 h-5 text-red-400" />
          ) : (
            <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
          )}
          {title}
        </h3>
        {estimated_remaining && !isComplete && !isFailed && (
          <span className="flex items-center gap-1 text-sm text-slate-400">
            <Clock className="w-4 h-4" />
            {estimated_remaining}
          </span>
        )}
      </div>

      {/* Main progress bar */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-slate-400">{message}</span>
          <span className={`text-sm font-medium ${
            isComplete ? 'text-emerald-400' : isFailed ? 'text-red-400' : 'text-white'
          }`}>
            {progressPercent}%
          </span>
        </div>
        <Progress 
          value={progressPercent} 
          className={`h-2 ${
            isComplete ? '[&>div]:bg-emerald-500' : 
            isFailed ? '[&>div]:bg-red-500' : ''
          }`} 
        />
      </div>

      {/* Step progress (e.g., Scene 2/6) */}
      {total_steps > 1 && (
        <div className="mb-6 flex items-center gap-2">
          <div className="flex-1 flex gap-1">
            {Array.from({ length: total_steps }).map((_, i) => (
              <div
                key={i}
                className={`h-1.5 flex-1 rounded-full transition-colors ${
                  i < current_step 
                    ? 'bg-emerald-500' 
                    : i === current_step 
                    ? 'bg-blue-500 animate-pulse' 
                    : 'bg-slate-700'
                }`}
              />
            ))}
          </div>
          <span className="text-xs text-slate-400 ml-2">
            {current_step}/{total_steps}
          </span>
        </div>
      )}

      {/* Pipeline steps */}
      <div className="space-y-1">
        {displaySteps.map((step, index) => (
          <ProgressStep
            key={step.stage}
            step={step}
            isActive={index === currentStageIndex || (isComplete && index === displaySteps.length - 1)}
            isComplete={isComplete || index < currentStageIndex}
            isFailed={isFailed && index === currentStageIndex}
          />
        ))}
      </div>

      {/* Error message */}
      {isFailed && message && (
        <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
          <p className="text-sm text-red-400">{message}</p>
        </div>
      )}

      {/* Success message */}
      {isComplete && (
        <div className="mt-4 p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
          <p className="text-sm text-emerald-400">{message || 'Generation complete! Your content is ready.'}</p>
        </div>
      )}
    </div>
  );
};

// Compact progress indicator for smaller spaces
export const CompactProgressIndicator = ({ progress }) => {
  if (!progress) return null;

  const { progress: percent = 0, message = '', status = 'running' } = progress;
  const isComplete = status === 'completed';
  const isFailed = status === 'failed';

  return (
    <div className="flex items-center gap-3 p-2 bg-slate-800/50 rounded-lg">
      {isComplete ? (
        <CheckCircle className="w-4 h-4 text-emerald-400" />
      ) : isFailed ? (
        <XCircle className="w-4 h-4 text-red-400" />
      ) : (
        <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
      )}
      <div className="flex-1 min-w-0">
        <Progress value={percent} className="h-1.5" />
      </div>
      <span className="text-xs text-slate-400 whitespace-nowrap">{percent}%</span>
    </div>
  );
};

export default RealTimeProgressPanel;
