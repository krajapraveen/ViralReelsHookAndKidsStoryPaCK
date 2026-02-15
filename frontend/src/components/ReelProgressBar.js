import React, { useState } from 'react';
import { toast } from 'sonner';

export default function ReelProgressBar({ isGenerating, onComplete }) {
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState('');

  React.useEffect(() => {
    if (!isGenerating) {
      setProgress(0);
      setStage('');
      return;
    }

    const stages = [
      { progress: 15, text: 'Analyzing topic...' },
      { progress: 30, text: 'Generating viral hooks...' },
      { progress: 50, text: 'Crafting script...' },
      { progress: 70, text: 'Creating captions...' },
      { progress: 85, text: 'Adding hashtags...' },
      { progress: 95, text: 'Finalizing...' },
    ];

    let currentStage = 0;
    const interval = setInterval(() => {
      if (currentStage < stages.length) {
        setProgress(stages[currentStage].progress);
        setStage(stages[currentStage].text);
        currentStage++;
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [isGenerating]);

  React.useEffect(() => {
    if (progress === 95 && onComplete) {
      // Wait a bit then call onComplete
      const timer = setTimeout(() => {
        setProgress(100);
        setStage('Complete!');
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [progress, onComplete]);

  if (!isGenerating && progress === 0) return null;

  return (
    <div className="mb-6 p-4 bg-gradient-to-r from-indigo-50 to-purple-50 rounded-xl border border-indigo-200">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-indigo-700">{stage}</span>
        <span className="text-sm font-bold text-indigo-600">{progress}%</span>
      </div>
      <div className="w-full bg-indigo-100 rounded-full h-3 overflow-hidden">
        <div 
          className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${progress}%` }}
        >
          <div className="w-full h-full bg-gradient-to-r from-transparent via-white/30 to-transparent animate-pulse" />
        </div>
      </div>
      <div className="flex justify-between mt-2 text-xs text-indigo-500">
        <span>Hooks</span>
        <span>Script</span>
        <span>Captions</span>
        <span>Hashtags</span>
      </div>
    </div>
  );
}
