/**
 * RealTimeProgressPanel Component
 * Shows detailed phase-by-phase progress for Story to Video generation
 */
import React from 'react';
import { Progress } from './ui/progress';
import { 
  CheckCircle, Loader2, AlertCircle, FileText, Image, Mic, Film,
  Sparkles, Clock
} from 'lucide-react';

const STAGE_CONFIG = {
  preparing: { 
    icon: Sparkles, 
    label: 'Preparing', 
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/20'
  },
  scene_generation: { 
    icon: FileText, 
    label: 'Generating Scenes', 
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/20'
  },
  image_generation: { 
    icon: Image, 
    label: 'Creating Images', 
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-500/20'
  },
  voice_generation: { 
    icon: Mic, 
    label: 'Recording Voice', 
    color: 'text-amber-400',
    bgColor: 'bg-amber-500/20'
  },
  video_assembly: { 
    icon: Film, 
    label: 'Rendering Video', 
    color: 'text-pink-400',
    bgColor: 'bg-pink-500/20'
  },
  complete: { 
    icon: CheckCircle, 
    label: 'Complete', 
    color: 'text-green-400',
    bgColor: 'bg-green-500/20'
  },
  failed: { 
    icon: AlertCircle, 
    label: 'Failed', 
    color: 'text-red-400',
    bgColor: 'bg-red-500/20'
  }
};

const DEFAULT_STEPS = [
  { stage: 'scene_generation', label: 'Generating Scenes', detail: 'Breaking story into visual scenes' },
  { stage: 'image_generation', label: 'Creating Images', detail: 'Generating AI images for each scene' },
  { stage: 'voice_generation', label: 'Recording Voice', detail: 'Creating narration audio' },
  { stage: 'video_assembly', label: 'Rendering Video', detail: 'Assembling final video' }
];

export const RealTimeProgressPanel = ({ 
  progress, 
  title = 'Generation Progress',
  steps = DEFAULT_STEPS,
  className = ''
}) => {
  if (!progress) return null;

  const { 
    stage = 'preparing', 
    progress: progressPercent = 0, 
    current_step = 0, 
    total_steps = 1,
    message = 'Processing...', 
    status = 'running',
    estimated_remaining = null,
    metadata = {}
  } = progress;

  const config = STAGE_CONFIG[stage] || STAGE_CONFIG.preparing;
  const StageIcon = config.icon;
  
  // Find current step index
  const currentStepIndex = steps.findIndex(s => s.stage === stage);
  const isComplete = status === 'completed' || stage === 'complete';
  const isFailed = status === 'failed';

  return (
    <div className={`bg-slate-800/50 rounded-xl border border-slate-700/50 p-6 ${className}`} data-testid="progress-panel">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2" data-testid="progress-title">
          <StageIcon className={`w-5 h-5 ${config.color}`} />
          {title}
        </h3>
        {estimated_remaining && status === 'running' && (
          <div className="flex items-center gap-1 text-sm text-slate-400" data-testid="time-remaining">
            <Clock className="w-4 h-4" />
            {estimated_remaining}
          </div>
        )}
      </div>

      {/* Main Progress Bar */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className={`text-sm font-medium ${config.color}`} data-testid="current-stage">
            {config.label}
          </span>
          <span className="text-sm text-slate-400" data-testid="progress-percent">
            {Math.round(progressPercent)}%
          </span>
        </div>
        <Progress 
          value={progressPercent} 
          className="h-3 bg-slate-700"
          data-testid="main-progress-bar"
        />
        <p className="text-sm text-slate-400 mt-2" data-testid="progress-message">
          {message}
        </p>
      </div>

      {/* Step Indicators */}
      <div className="space-y-3" data-testid="step-indicators">
        {steps.map((step, idx) => {
          const stepConfig = STAGE_CONFIG[step.stage] || STAGE_CONFIG.preparing;
          const Icon = stepConfig.icon;
          const isCurrentStep = step.stage === stage;
          const isCompletedStep = currentStepIndex > idx || isComplete;
          const isPendingStep = currentStepIndex < idx && !isComplete;

          return (
            <div 
              key={step.stage}
              className={`flex items-center gap-3 p-3 rounded-lg transition-all ${
                isCurrentStep ? stepConfig.bgColor + ' border border-white/10' :
                isCompletedStep ? 'bg-green-500/10' :
                'bg-slate-900/30'
              }`}
              data-testid={`step-${step.stage}`}
            >
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                isCompletedStep ? 'bg-green-500/30' :
                isCurrentStep ? stepConfig.bgColor :
                'bg-slate-700/50'
              }`}>
                {isCompletedStep ? (
                  <CheckCircle className="w-4 h-4 text-green-400" />
                ) : isCurrentStep ? (
                  <Loader2 className="w-4 h-4 text-white animate-spin" />
                ) : (
                  <Icon className={`w-4 h-4 ${isPendingStep ? 'text-slate-500' : stepConfig.color}`} />
                )}
              </div>
              
              <div className="flex-1 min-w-0">
                <p className={`text-sm font-medium ${
                  isCompletedStep ? 'text-green-400' :
                  isCurrentStep ? 'text-white' :
                  'text-slate-500'
                }`}>
                  {step.label}
                </p>
                {isCurrentStep && current_step > 0 && total_steps > 1 && (
                  <p className="text-xs text-slate-400">
                    Step {current_step} of {total_steps}
                  </p>
                )}
              </div>

              {isCompletedStep && (
                <span className="text-xs text-green-400">Done</span>
              )}
            </div>
          );
        })}
      </div>

      {/* Completion or Error Message */}
      {isComplete && (
        <div className="mt-4 p-4 bg-green-500/20 border border-green-500/30 rounded-lg" data-testid="complete-message">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-green-400" />
            <span className="text-green-400 font-medium">Video Ready!</span>
          </div>
          {metadata?.result_url && (
            <p className="text-sm text-slate-300 mt-2">Your video is ready for download.</p>
          )}
        </div>
      )}

      {isFailed && (
        <div className="mt-4 p-4 bg-red-500/20 border border-red-500/30 rounded-lg" data-testid="error-message">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <span className="text-red-400 font-medium">Generation Failed</span>
          </div>
          <p className="text-sm text-slate-300 mt-2">{message}</p>
        </div>
      )}
    </div>
  );
};

export default RealTimeProgressPanel;
