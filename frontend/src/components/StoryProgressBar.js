import React, { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';

export default function StoryProgressBar({ isGenerating }) {
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState('Initializing...');
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!isGenerating) {
      setProgress(0);
      setElapsed(0);
      return;
    }

    // More realistic stages for 60-90 second generation
    const stages = [
      { duration: 5000, progress: 10, text: 'Connecting to AI...' },
      { duration: 15000, progress: 25, text: 'Creating story outline...' },
      { duration: 30000, progress: 45, text: 'Developing characters & plot...' },
      { duration: 50000, progress: 65, text: 'Writing scene narrations...' },
      { duration: 70000, progress: 80, text: 'Adding visual descriptions...' },
      { duration: 85000, progress: 90, text: 'Finalizing story pack...' },
      { duration: 120000, progress: 95, text: 'Almost done...' }
    ];

    let currentStage = 0;
    const startTime = Date.now();

    const interval = setInterval(() => {
      const elapsedMs = Date.now() - startTime;
      setElapsed(Math.floor(elapsedMs / 1000));
      
      // Find current stage based on elapsed time
      for (let i = 0; i < stages.length; i++) {
        if (elapsedMs < stages[i].duration) {
          if (i !== currentStage) {
            currentStage = i;
            setProgress(stages[i].progress);
            setStatusText(stages[i].text);
          }
          break;
        }
      }

      // If we've passed all stages, stay at 95%
      if (elapsedMs >= stages[stages.length - 1].duration) {
        setProgress(95);
        setStatusText('Almost done...');
      }
    }, 500);

    return () => clearInterval(interval);
  }, [isGenerating]);

  if (!isGenerating) return null;

  const estimatedRemaining = Math.max(0, 75 - elapsed);

  return (
    <div className="space-y-4 p-6 bg-purple-50 rounded-lg border border-purple-200" data-testid="story-progress">
      <div className="flex items-center gap-3">
        <Loader2 className="w-5 h-5 text-purple-500 animate-spin" />
        <span className="font-medium text-purple-900">{statusText}</span>
      </div>
      
      <div className="space-y-2">
        <div className="w-full bg-purple-100 rounded-full h-3 overflow-hidden">
          <div 
            className="bg-gradient-to-r from-purple-500 to-purple-600 h-3 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="flex justify-between text-sm text-purple-700">
          <span>{progress}% complete</span>
          <span>~{estimatedRemaining > 0 ? `${estimatedRemaining}s remaining` : 'Finishing up...'}</span>
        </div>
      </div>

      <p className="text-sm text-purple-700">
        ✨ Creating your personalized story pack with AI... This typically takes 60-90 seconds for high-quality results.
      </p>
    </div>
  );
}
