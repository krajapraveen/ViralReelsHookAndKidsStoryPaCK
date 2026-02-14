import React, { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';

export default function StoryProgressBar({ isGenerating }) {
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState('Initializing...');

  useEffect(() => {
    if (!isGenerating) {
      setProgress(0);
      return;
    }

    const stages = [
      { duration: 5000, progress: 15, text: 'Creating story outline...' },
      { duration: 10000, progress: 35, text: 'Developing characters...' },
      { duration: 15000, progress: 55, text: 'Writing scenes...' },
      { duration: 20000, progress: 75, text: 'Adding visual descriptions...' },
      { duration: 30000, progress: 90, text: 'Finalizing story pack...' },
      { duration: 45000, progress: 95, text: 'Almost done...' }
    ];

    let currentStage = 0;
    const startTime = Date.now();

    const interval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      
      // Find current stage based on elapsed time
      for (let i = 0; i < stages.length; i++) {
        if (elapsed < stages[i].duration) {
          if (i !== currentStage) {
            currentStage = i;
            setProgress(stages[i].progress);
            setStatusText(stages[i].text);
          }
          break;
        }
      }

      // If we've passed all stages, stay at 95%
      if (elapsed >= stages[stages.length - 1].duration) {
        setProgress(95);
        setStatusText('Almost done...');
      }
    }, 500);

    return () => clearInterval(interval);
  }, [isGenerating]);

  if (!isGenerating) return null;

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
          <span>Estimated time: {Math.max(0, Math.ceil((45 - progress * 0.45)))}s</span>
        </div>
      </div>

      <p className="text-sm text-purple-700">
        ✨ Generating your personalized story pack... This may take 30-45 seconds.
      </p>
    </div>
  );
}
